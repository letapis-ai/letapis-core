# The other embedder: vllm-mlx

The kit ships **llama.cpp** for both models, and that is the supported path — nothing on this
page is needed to run letapis. It is here because we run a different embedder ourselves, and a
recipient who wants the same thing should not have to rediscover it.

**vllm-mlx** is a vLLM-shaped server for Apple silicon. We use it for the embedder only; the
reranker stays on `llama-server` either way. It answers on **the same port as the default
embedder, `12436`**, and speaks the same OpenAI-shaped `/v1/embeddings`. The address is a
constant here and the runtime is a choice — that is the whole reason the port is shared.

**One engine setting must change, or embeddings stop working entirely.** Two more are worth
changing for throughput. Everything else — the port, the health route, the panel card's stop
strategy — stays as it is.

| | Shipped llama.cpp profile | This page (vllm-mlx) |
|---|---|---|
| Runtime | `llama-server` (llama.cpp) | `vllm-mlx` |
| Weights | `~/models/harrier-oss-v1-0.6b-Q8_0.gguf` (GGUF) | `~/models/harrier-oss-v1-0.6b` (MLX directory) |
| Port | 12436 | 12436 |
| Health | `/v1/models` | `/v1/models` |
| Dimensions | 1024 | 1024 |
| **`embeddings.model`** | `harrier-0.6b` (the alias) | **the absolute model path** |

The left column is the profile this kit ships, not the schema's own defaults — those are
different for `embeddings.model`, which defaults to `nomic-embed-text` and is set to
`harrier-0.6b` by the shipped configuration.

**`embeddings.model` is the only hard requirement of the two runtimes.** The next two settings
are throughput: vllm-mlx works at the shipped values, just slower.

| | Shipped llama.cpp profile | Suggested for vllm-mlx |
|---|---|---|
| `embeddings.sender_workers` | 1 | 4 |
| `embeddings.token_batch_size` | 512 | 2048 |

Same model, same width, same address — vectors from one are comparable with vectors from the
other. A different **model** would not be; that is a re-index, not a swap.

## The name in `embeddings.model` is not the alias

`--served-model-name` registers a name for `/v1/models` and for nothing else. The embeddings
path refuses it and says so plainly:

```
POST /v1/embeddings  {"model": "harrier-0.6b"}   -> 400
{"detail": "Embedding model 'harrier-0.6b' is not available. This server was started with
--embedding-model /absolute/path/to/harrier-oss-v1-0.6b. Only
'/absolute/path/to/harrier-oss-v1-0.6b' can be used for embeddings."}

POST /v1/embeddings  {"model": "/absolute/path/to/harrier-oss-v1-0.6b"}  -> 200, 1024 floats
```

So `embeddings.model` in the engine's config carries **the path the server was started with** —
the one it names back at you in that 400 — and not the alias. On llama.cpp the alias is the
right value; here it is the one setting that must change.

**Write it absolute.** The engine does not expand `~` in config values: the file is parsed as
plain YAML and `embeddings.model` travels into the request body untouched, so `~/models/…`
reaches the server as a directory literally named `~` and is refused exactly like the alias.
(The panel's service card is a different consumer — `embedder.sh` does expand `~` there.)

**Why nothing warns you.** `/v1/models` lists both names and answers 200 to both, and that route
is the panel's health probe. The card goes green, the install check passes, and every embedding
call fails — which surfaces much later as an index that produced nodes and not one vector.

**So check the runtime with a real embedding, never with `/v1/models`:**

```bash
curl -sS http://127.0.0.1:12436/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d "{\"model\": \"$HOME/models/harrier-oss-v1-0.6b\", \"input\": \"probe\"}" \
  | jq '.data[0].embedding | length'
```

`1024` means the embedder works. An HTTP 400 with the text above means the model name is the
alias — fix `embeddings.model`, not the server.

**The other two settings follow from how each server takes work.** The shipped `embedder.sh`
starts llama.cpp with `--parallel 1` (its `auto=4` default races and corrupts the heap) and with
`--batch-size 512 --ubatch-size 512`, because in embedding mode that server clamps the batch to
512 anyway. One slot and a 512-token batch — so the engine sends one request at a time and packs
512 tokens into it. vllm-mlx runs with `--continuous-batching` and takes concurrent requests, so
four senders and a larger batch are useful rather than queued.

## What changes in your configuration

The panel's service card — four values, and the rest of the card is untouched:

```yaml
config:
  params:
    engine: vllm
    model: ~/models/harrier-oss-v1-0.6b     # an MLX directory, not a .gguf file
    served_model_name: harrier-0.6b         # llama.cpp spells this one `alias`
    host: 127.0.0.1
    port: '12436'
logs:
  kind: file
  path: /tmp/vllm-mlx.log                   # llama.cpp writes /tmp/letapis-embedder.log
```

`health`, `port` and `stop` are shared and stay as they are.

The engine's `embeddings` section — the three settings from the table, in place:

```yaml
embeddings:
  provider: "openai"
  api_url: "http://localhost:12436"
  model: "/absolute/path/to/harrier-oss-v1-0.6b"   # no `~` here — see above
  dimensions: 1024
  token_batch_size: 2048                  # llama.cpp: 512, matching its own clamp
  chars_per_token: 2
  chunk_size: 1024
  chunk_overlap: 128
  sender_workers: 4                       # llama.cpp: 1, the server takes one at a time
```

`sender_workers` belongs **inside** `embeddings`, not beside it.

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
  --port 12436 --host 127.0.0.1 \
  --continuous-batching --lazy-load-model
```

Whatever path you pass to `--embedding-model` is the string the engine must put in
`embeddings.model` — see above.

The panel's health probe, stop strategy and port already say `12436` and need no editing. What
you do change is the card's `start:` line — it invokes
`~/.config/letapis-app/services/embedder.sh`, and that script knows `llama-cpp` only. The panel
passes `config.params` through as `LETAPIS_SVC_*` environment and never interprets them
(see [services.md](https://github.com/letapis-ai/letapis-panel/blob/main/docs/services.md)).

**Add a branch to the shipped script — do not replace the file with a copy.** The `llama-cpp`
branch carries guards and a flag set that exist for measured reasons, and a copy taken today
freezes them at today's version. Next to the existing `llama-cpp)` case:

**First move one line.** The script sets `: "${LETAPIS_SVC_BIN:=llama-server}"` above the
`case`, so any branch you add inherits `llama-server` and dies on its own executable check
before it ever looks for `vllm-mlx`. A per-engine default belongs in its own branch: move that
line into the `llama-cpp)` case, then add this one beside it.

```bash
  vllm)
    : "${LETAPIS_SVC_BIN:=$HOME/.venv-vllm-mlx/bin/vllm-mlx}"
    : "${LETAPIS_SVC_SERVED_MODEL_NAME:=harrier-0.6b}"
    LETAPIS_SVC_MODEL="${LETAPIS_SVC_MODEL/#\~/$HOME}"
    if [ ! -x "$LETAPIS_SVC_BIN" ]; then
      echo "FATAL: '$LETAPIS_SVC_BIN' not executable — create the venv or set bin: in this service's yaml"
      exit 1
    fi
    if [ ! -d "$LETAPIS_SVC_MODEL" ]; then
      echo "FATAL: MLX model directory not found: $LETAPIS_SVC_MODEL"
      exit 1
    fi
    exec "$LETAPIS_SVC_BIN" serve "$LETAPIS_SVC_MODEL" \
      --embedding-model "$LETAPIS_SVC_MODEL" \
      --served-model-name "$LETAPIS_SVC_SERVED_MODEL_NAME" \
      --port "$LETAPIS_SVC_PORT" --host "$LETAPIS_SVC_HOST" \
      --continuous-batching --lazy-load-model
    ;;
```

The `*)` case below already refuses an unknown engine by name; extend its message so `vllm` is
listed as expected.

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

**The shim is not permanent, and here is the condition that ends it.** Upstream `main` carries
`6b41b1ad`, "fix(embeddings): release MLX buffers after each batch", which calls
`mx.clear_cache()` after every batch — their own note describes this exact growth, 2.3 GB to
24 GB over 320 texts, and blames the padded batch length changing from batch to batch. It is
**not** in the `v0.4.0` tag, so no release carries it yet and `pip install` will not bring it
`[compared v0.3.0…v0.4.0 and main, 2026-08-10]`. When a release does:

1. upgrade, then confirm the fix is actually installed — `grep clear_cache` in the installed
   `vllm_mlx/embedding.py`;
2. remove the shim and **measure**. The two approaches are not the same trade: theirs frees the
   pool after every batch, ours holds a 512 MB ceiling and keeps cache hits on repeating sizes.
   Which one is cheaper on your load is a measurement, not a deduction.

**How to tell it is working.** The server prints one line to stderr at startup:

```
[sitecustomize] MLX cache_limit set to 512MB (prev=48962627174)
```

No line at all means Python never loaded the file — it is in the wrong `site-packages`, or the
server is being started from a different environment. A `NOT set` line means MLX is present but
exposes no `set_cache_limit`, and the note after it says what went wrong.
