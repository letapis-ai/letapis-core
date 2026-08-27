# Embedding settings — what depends on what

The panel writes a working config on first launch, and you do not have to read this to use
letapis. Read it when you change an embedder, tune for a bigger machine, or wonder why a value
is what it is.

## One rule everything else follows from

A chunk, **together with the context prefix the engine puts in front of it**, must fit inside
the embedder's window.

The window is not written down anywhere. It is computed:

```
window (chars) = token_batch_size (tokens) × chars_per_token (chars per token)
```

and two things have to fit in it:

```
chunk_size + prefix ≤ window
```

The prefix is a short header the engine prepends to each chunk; its length is capped at **192
characters**.

**A chunk that outgrows the window is refused by name, not silently trimmed.** The engine treats
it as a wiring fault, because a chunk cut to fit is a chunk that no longer means what the file
said.

### Checking it by eye

| Settings | Window | Chunk + prefix | Verdict |
|---|---|---|---|
| batch 512, chars/token 2, chunk 1024 | 1024 | up to 1216 | tight — no room for the prefix |
| batch 2048, chars/token 2, chunk 1024 | 4096 | up to 1216 | roomy |

If you raise `token_batch_size`, raise it — do not raise `chunk_size` instead. A larger chunk
buys worse search: the piece returned to you is coarser.

## The batch size is not yours to choose freely

`token_batch_size` must match **what your embedding server actually accepts**, and servers
differ. The panel writes a value matched to the server it set up for you.

### llama-server (what the panel installs by default)

The panel launches it with these flags, and each one is there for a reason:

| Flag | Why |
|---|---|
| `--batch-size 512 --ubatch-size 512` | in embedding mode the server refuses a batch larger than the micro-batch and silently clamps both to 512. Saying 512 out loud is what lets the engine's `token_batch_size` be matched to the limit instead of guessed |
| `--parallel 1` | the default is auto=4, and four slots embedding at once race and corrupt memory inside the library |
| `--cache-ram 0` | the prompt cache (8192 MiB by default) buys nothing here — chunks share no prefixes, so nothing is reused |
| `--ctx-size` | the default is 32768 **per slot**, and the server reserves a KV cache for inputs sixty times larger than anything we send |

**Do not remove these.** A flag lost here costs the whole installation, and nothing will say so:
the panel's lamp goes green on a server that is about to die.

With this server, `token_batch_size: 512` is correct. It is the server's ceiling, not a
conservative guess.

### Other servers

If you replace the embedder with one that accepts larger inputs, raise `token_batch_size` to
match it — and do not add a batch-limiting flag on the server side. A server that splits long
input into sub-batches on its own can die without a word: we have seen a process abort with
code 133 on the second sub-batch, three times in a row, having logged nothing.

Measure before you change: send the embedder inputs of growing length and see where it stops
answering. On our machine, inputs from 600 to 16 000 characters all returned a vector, taking
0.04 s at 1024 characters and 3.2 s at 16 000.

## What must match everywhere, and what may differ

**Must match — these define the SHAPE of the data.** Change one after indexing and the corpus
becomes unsearchable by the new settings; the only cure is a full rebuild.

- `dimensions` — the width of the vector; must equal what your model produces
- `chunk_size`, `chunk_overlap` — how text is cut
- `chars_per_token` — the estimate the window is computed from

**May differ — these are pace, and they depend on your machine.**

- `delay_ms`, `idle_timeout_ms`, `timeout_seconds`, `sender_workers`

`token_batch_size` sits in between: it is a pace setting that the window is computed from, which
is why it gets a section of its own above.

## Where the settings live

| Place | What it is |
|---|---|
| `~/.config/letapis/config.yaml` (or wherever `LETAPIS_CONFIG_FILE` points) | your engine's settings — the panel wrote it once and never touches it again |
| `~/.config/letapis-app/services/*.yaml` and `*.sh` | the service cards and launch scripts — **these start the programs**, and every address in the config mirrors them |
| this repository, `config/default/letapis/config.yaml` | a sample: what a working file looks like |

The cards are the source of truth for addresses. Change a port there and change it in the config
to match, not the other way round.

## Checking your own setup

```sh
# is the embedder up and which model does it serve
curl -s 127.0.0.1:12436/v1/models

# does it answer with a vector, and how wide
curl -s -X POST 127.0.0.1:12436/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model":"<the alias from your card>","input":"probe"}' \
  | head -c 200
```

If the model name is refused, use exactly the name the server reports in `/v1/models` — some
servers accept only the name they were started with, not an alias.
