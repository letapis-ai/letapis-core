# The other embedder: vllm-mlx

The kit ships **llama.cpp** for both models, and that is the supported path — nothing on this
page is needed to run letapis. It is here because we run a different embedder ourselves, and a
recipient who wants the same thing should not have to rediscover it.

**vllm-mlx** is a vLLM-shaped server for Apple silicon. We use it for the embedder only; the
reranker stays on `llama-server` either way. It answers on **the same port as the default
embedder, `12436`**, and speaks the same OpenAI-shaped `/v1/embeddings` — so the engine's
configuration and the panel's service card do not change when you swap the runtime. That is the
whole reason the port is shared: the runtime is a choice, the address is not.

| | Default | This page |
|---|---|---|
| Runtime | `llama-server` (llama.cpp) | `vllm-mlx` |
| Weights | `~/models/harrier-oss-v1-0.6b-Q8_0.gguf` (GGUF) | `~/models/harrier-oss-v1-0.6b` (MLX directory) |
| Port | 12436 | 12436 |
| Health | `/v1/models` | `/v1/models` |
| Dimensions | 1024 | 1024 |

Same model, same width, same address — vectors from one are comparable with vectors from the
other. A different **model** would not be; that is a re-index, not a swap.

## Where it comes from

Install from PyPI with `uv` — a wheel, not a git checkout:

```bash
uv venv ~/.venv-vllm-mlx --python 3.12
uv pip install --python ~/.venv-vllm-mlx vllm-mlx
```

**The source repository is [`github.com/waybarrios/vllm-mlx`](https://github.com/waybarrios/vllm-mlx).**
The package metadata points somewhere else — its `Homepage`, `Documentation` and `Repository`
fields all name `github.com/vllm-mlx/vllm-mlx`, which **does not exist**: GitHub answers 404 for
it `[checked 2026-08-09]`. Do not read that as "the project is gone". Go to `waybarrios/vllm-mlx`,
which is public and carries the tags the releases are cut from.

Versions we have measured: **0.3.0** is what we run; the source repository also carries a
**v0.4.0** tag `[checked 2026-08-09]`.

## Running it

```bash
~/.venv-vllm-mlx/bin/vllm-mlx serve ~/models/harrier-oss-v1-0.6b \
  --embedding-model ~/models/harrier-oss-v1-0.6b \
  --served-model-name harrier-0.6b \
  --port 12436 --host 0.0.0.0 \
  --continuous-batching --lazy-load-model
```

The panel's embedder card does not need editing: its health probe, its stop strategy and its
port already say `12436`. What you do change is the card's `start:` line — it invokes
`~/.config/letapis-app/services/embedder.sh`, and that script knows `llama-cpp` only. Point the
card at your own script, or add a branch to that one; the panel passes `config.params` through as
`LETAPIS_SVC_*` environment and never interprets them
(see [services.md](https://github.com/letapis-ai/letapis-panel/blob/main/docs/services.md)).

## The patch, and why it does not go away with an upgrade

`sitecustomize.py` in this folder is the one modification we make. Copy it into the virtual
environment's `site-packages` and Python loads it on every interpreter start — no wrapper, no
flag:

```bash
cp docs/vllm/sitecustomize.py ~/.venv-vllm-mlx/lib/python3.12/site-packages/
```

**What it does.** It caps the MLX Metal buffer cache at 512 MB. Without it MLX leaves the cache
at the device working set: on our machine the limit the shim replaced was **~45.6 GB**, read from
the value MLX itself returned when the cap was applied `[measured on the running server,
2026-08-09]`. The embedding forward needs a small scratch pool; the cache simply grows into
whatever it is allowed and the process footprint follows.

**Why a patch and not a setting.** The library never asks for a limit on this path. In the
version we run, `vllm_mlx/embedding.py` contains no call to `set_cache_limit`, `set_memory_limit`
or `set_wired_limit` at all `[checked in the installed 0.3.0, 2026-08-09]`. The calls do exist in
the library — in the batched **generation** engine — which is exactly why the embedding server
never receives one.

**Why upgrading does not fix it.** `vllm_mlx/embedding.py` at the upstream **v0.4.0** tag is
byte-for-byte the file we run: both are sha256 `95cdb5fa…8bf2ef9d`, and neither calls any of the
three `[compared 2026-08-09 — installed 0.3.0 against the raw file at v0.4.0]`. An earlier
internal investigation reached the same conclusion for `0.4.0rc1` and `main` on **2026-06-13**;
that half is cited, not re-measured here.

So: upgrade freely, and re-copy the shim afterwards. A fresh virtual environment is a fresh
`site-packages`, and the file does not survive one.

**How to tell it is working.** The server prints one line to stderr at startup:

```
[sitecustomize] MLX cache_limit set to 512MB (prev=48962627174)
```

No line at all means Python never loaded the file — it is in the wrong `site-packages`, or the
server is being started from a different environment. A `NOT set` line means MLX is present but
exposes no `set_cache_limit`, and the note after it says what went wrong.
