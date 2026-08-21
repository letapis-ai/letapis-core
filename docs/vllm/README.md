# The other embedder: vllm-mlx

The kit ships **llama.cpp** for both models, and that is the supported path — nothing on this
page is needed to run letapis. **vllm-mlx** is a vLLM-shaped server for Apple silicon and an
alternative for the embedder only; the reranker stays on `llama-server` either way.

It answers on **the same port as the default embedder, `12436`**, and speaks the same
OpenAI-shaped `/v1/embeddings`. The address is a constant here and the runtime is a choice —
that is why the port is shared.

**Use 0.4.1 or newer.** Earlier versions cap every input at 512 tokens and drop the rest without
saying so, which silently truncates any chunk longer than about a thousand characters. From
0.4.1 the limit comes from the model's own configuration.

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

**A green health lamp does not mean embeddings work.** `/v1/models` lists both names and answers
200 to both, and that route is the panel's health probe. The card goes green, the install check
passes, and every embedding call fails — which surfaces much later as an index that produced
nodes and not one vector.

**So check the runtime with a real embedding, never with `/v1/models`:**

```bash
curl -sS http://127.0.0.1:12436/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d "{\"model\": \"$HOME/models/harrier-oss-v1-0.6b\", \"input\": \"probe\"}" \
  | jq '.data[0].embedding | length'
```

`1024` means the embedder works. An HTTP 400 with the text above means the model name is the
alias — fix `embeddings.model`, not the server.

**Why the other two settings differ.** The shipped `embedder.sh` starts llama.cpp with
`--parallel 1` and `--batch-size 512 --ubatch-size 512`, so the engine sends one request at a
time and packs 512 tokens into it. vllm-mlx runs with `--continuous-batching` and takes
concurrent requests, so four senders and a larger batch are useful rather than queued.

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
  api_url: "http://127.0.0.1:12436"
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
uv pip install --python ~/.venv-vllm-mlx 'vllm-mlx>=0.4.1'
```

**The source repository is [`github.com/waybarrios/vllm-mlx`](https://github.com/waybarrios/vllm-mlx).**
The package metadata names `github.com/vllm-mlx/vllm-mlx` in its `Homepage`, `Documentation` and
`Repository` fields; that address does not exist. Go to `waybarrios/vllm-mlx`, which is public
and carries the tags the releases are cut from.

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
(see [services.md](../services.md)).

**Add a branch to the shipped script rather than replacing the file.** The `llama-cpp` branch
carries guards and a flag set of its own, and a copy taken today freezes them. Next to the
existing `llama-cpp)` case:

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
