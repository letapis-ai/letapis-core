# The two models

**What this page is:** the specification the engine is built against — which models, which
addresses, which checksums, which vector width — and what the panel does with them once they
are on disk.


letapis uses two small models, and it needs both. They do different jobs at different moments
of a single search:

* the **embedder** turns text into a vector. Every file the engine indexes goes through it
  once, and so does every query you type.
* the **reranker** takes the handful of candidates the vector search returned and re-orders
  them by actually reading each one against the query. It is what makes the top result the
  top result.

Both run under `llama-server`, which comes with llama.cpp (`brew install llama.cpp`). One
runtime for both is deliberate: it is the same binary on every Mac, it needs no Python
environment, and it uses the GPU through Metal without any further setup.


## Specification

| | Embedder | Reranker |
|---|---|---|
| Model | Harrier-OSS v1 0.6B | Qwen3-Reranker 0.6B |
| Format | GGUF, `Q8_0` | GGUF, `Q8_0` |
| File the card expects | `~/models/harrier-oss-v1-0.6b-Q8_0.gguf` | `~/models/Qwen3-Reranker-0.6B.Q8_0.gguf` |
| Weights on disk | ~610 MiB | ~610 MiB |
| Resident memory, idle | **~4.2 GB** | **1.3–1.5 GB** |
| Listens on | `127.0.0.1:12436` | `127.0.0.1:8086` |
| Health endpoint | `/v1/models` | `/health` |
| Output dimensions | **1024** | — (returns scores) |
| Context window | the model's own, 32768 | 4096 |
| Batch it processes at once | 512 (embedding mode clamps to it) | the context size |
| Alias it serves under | `harrier-0.6b` | `qwen3-reranker-0.6b` |
| Log | `/tmp/letapis-embedder.log` | `/tmp/letapis-reranker.log` |

The memory figures are measured at idle, with the command each card produces; serving traffic
adds to them. The reranker is a range because it is one — repeated runs settle anywhere in it.

**Why the reranker's batch follows its context.** A batch smaller than the context makes the
server refuse any document that does not fit it — `input is too large to process` — and cancel
the whole batch, throwing away the neighbours it had already scored. The engine loses that call
and stops ranking for half a minute; results keep coming, in raw fusion order, and nothing says
so. The trap is that the two numbers are counted in different units: the engine trims documents
by **characters** (`reranker.max_doc_chars`), the server measures **tokens**, and Cyrillic or
dense text crosses the line first. Keeping the batch at the context size is what removes the
gap; if you raise `ctx` on the card, the batch follows it on its own.

**Why the embedder is the hungry one.** Its 4.2 GB is almost all key-value cache, not weights:
the server allocates the model's full 32k context across its slots. If memory is tight, the
context window is the knob — see [services.md](services.md) for where `ctx` lives.


## The dimension contract

The engine's configuration declares the size of the vectors it stores, and the Qdrant
collection is created with that size. The embedder must produce vectors of exactly that size —
**1024** with the model above.

Change the embedder for one with a different output size and the existing collection stops
accepting writes; a collection built at the new size cannot be searched with vectors from the
old one. Changing embedder means re-indexing from scratch.


## Where the weights come from

| | Embedder | Reranker |
|---|---|---|
| Repository | [majentik/harrier-oss-v1-0.6b-GGUF-Q8_0](https://huggingface.co/majentik/harrier-oss-v1-0.6b-GGUF-Q8_0) | [ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF](https://huggingface.co/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF) |
| File there | `harrier-0.6b-Q8_0.gguf` | `qwen3-reranker-0.6b-q8_0.gguf` |
| Licence | MIT | Apache-2.0 |
| Upstream model | `microsoft/harrier-oss-v1-0.6b` | `Qwen/Qwen3-Reranker-0.6B` |

Both files are named differently on the hub than the cards expect — [the install guide](../ONBOARDING.md#5-the-two-models)
downloads them straight into the right names.

**Checksums, and one honest gap.** Verify what you downloaded:

```bash
shasum -a 256 ~/models/harrier-oss-v1-0.6b-Q8_0.gguf ~/models/Qwen3-Reranker-0.6B.Q8_0.gguf
```

* the embedder should be `072a0be84fae7673bc1391d493580336b84d798a1a0bb504a5c5da3d7d00c4b9`
  — the same bytes this stack was built and measured against;
* the reranker from that repository is
  `22c9979ce4fbcdc5acdc310c6641c32797eff1aa980b8f7a2db8a8ea23429a48`, and the build **we**
  tested is a different one:
  `6ddab39a36c6c87fdb76f0e5f05657012d5dbc97034c0983c157f17ef9f34d55`. Same model, same
  quantisation, a different conversion run — 160 bytes apart. We have no reason to expect it
  to behave differently and no measurement saying it does not, so you are told rather than
  reassured.


## The flags that are not optional

Both launch scripts pass one flag that is the server's **mode**, not a tuning choice, and
neither is exposed as configuration:

* the embedder runs with `--embedding`. Without it the server still answers `/v1/models`, and
  `/v1/embeddings` simply does not exist — so the health lamp goes green on a server that
  cannot do the one thing it is there for.
* the reranker runs with `--reranking --pooling rank`. Drop either and you get the same trap:
  a green lamp on a server that is no longer a reranker.

If you replace a model, keep the flags. The scripts are `~/.config/letapis-app/services/embedder.sh`
and `reranker.sh`, and they are yours to edit — but that pair of lines is load-bearing.


## Replacing a model

The cards do not care which file they point at, as long as the runtime can load it. To try a
different quantisation — a smaller `Q4_K_M`, say, to save a couple of hundred megabytes — put
the file in `~/models/` and change the `model:` line in the service's card. The panel's pencil
button on the row opens exactly that file.

Two things to check before you do:

1. **Dimensions**, for the embedder — see the dimension contract above.
2. **That it is the right kind of model.** A reranker and an embedder are not interchangeable,
   and neither will tell you it is the wrong one; you will simply get poor results from a green
   stack.


## If a model will not start

Both scripts fail loudly rather than dying into the log, and there are exactly three things
they say:

| In the log | Means |
|---|---|
| `FATAL: 'llama-server' not found in PATH` | llama.cpp is not installed, or is somewhere `PATH` does not reach. Install it, or add a `bin:` line to the card with the full path |
| `FATAL: model weights not found: <path>` | the file is not there, or is named differently |
| `FATAL: unknown engine '<value>'` | the card's `engine:` value is misspelt — it must be `llama-cpp` |

Open the log from the panel with the **Logs** button on the row.
