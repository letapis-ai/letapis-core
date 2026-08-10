#!/usr/bin/env bash
# Own the log — rotate 1 generation on start, then redirect self.
# Launch params come from services.yaml as LETAPIS_SVC_* env. The
# supervisor passes raw k/v and knows no flags; the case below is the only place that
# knows how an engine spells them. A new engine = a new branch here, no panel rebuild.
: "${LETAPIS_SVC_ENGINE:=llama-cpp}"
: "${LETAPIS_SVC_MODEL:=$HOME/models/harrier-oss-v1-0.6b-Q8_0.gguf}"
: "${LETAPIS_SVC_ALIAS:=harrier-0.6b}"
: "${LETAPIS_SVC_PORT:=12436}"
: "${LETAPIS_SVC_HOST:=127.0.0.1}"
# Embedding inputs are chunks, not conversations: chunk_size 1024 chars / chars_per_token 2
# = ~512 tokens. llama.cpp's default n_ctx is 32768 PER SLOT, which reserved a 3584 MiB KV
# cache for inputs 64x smaller than it.
: "${LETAPIS_SVC_CTX:=8192}"
# The config may spell the model path with a leading `~` (same style as the
# card's `file:`). Nothing expands it for us — the value arrives as an env var, and `~`
# inside a quoted expansion reaches llama-server verbatim as a directory named "~".
LETAPIS_SVC_MODEL="${LETAPIS_SVC_MODEL/#\~/$HOME}"
# The runtime binary comes from PATH, not from a fixed prefix: brew, a manual build and a
# package manager all put it elsewhere. Overridable for an install outside PATH.
: "${LETAPIS_SVC_BIN:=llama-server}"

LOG=/tmp/letapis-embedder.log
[ -f "$LOG" ] && mv -f "$LOG" "$LOG.1"
exec >> "$LOG" 2>&1

# The engine is decided FIRST, resources second. A wrong `engine:` is a config
# fault and must be named as one — checking weights first would answer "weights not found"
# to a user whose actual mistake was the engine value.
case "$LETAPIS_SVC_ENGINE" in
  llama-cpp)
    # Destructive: no runtime / no weights → say so and exit. Without this the `exec` dies
    # into the log with the shell's own wording and the card stays red for no readable reason.
    if ! command -v "$LETAPIS_SVC_BIN" >/dev/null 2>&1; then
      echo "FATAL: '$LETAPIS_SVC_BIN' not found in PATH — install llama.cpp or set bin: in this service's yaml"
      exit 1
    fi
    if [ ! -f "$LETAPIS_SVC_MODEL" ]; then
      echo "FATAL: model weights not found: $LETAPIS_SVC_MODEL"
      exit 1
    fi
    # `--embedding` is the server's MODE, not tuning: without it /v1/models still answers
    # while /v1/embeddings does not exist. Deliberately not configurable.
    #
    # The rest are not tuning either — on defaults this server aborts under indexing load:
    #   --parallel 1   default is auto=4, and four slots embedding concurrently is the race
    #                  that corrupts the heap in llama_ubatch::data_t (libllama 7910).
    #   --batch-size / --ubatch-size 512
    #                  in embedding mode the server refuses n_batch > n_ubatch and silently
    #                  clamps both to 512 "to avoid assertion failure". Say 512 out loud so
    #                  the engine's token_batch_size can be matched to it instead of guessed.
    #   --cache-ram 0  the prompt cache (8192 MiB by default) buys nothing here: chunks share
    #                  no prefixes, so nothing is ever reused.
    exec "$LETAPIS_SVC_BIN" --model "$LETAPIS_SVC_MODEL" \
      --alias "$LETAPIS_SVC_ALIAS" --embedding \
      --port "$LETAPIS_SVC_PORT" --host "$LETAPIS_SVC_HOST" \
      --ctx-size "$LETAPIS_SVC_CTX" \
      --batch-size 512 --ubatch-size 512 --parallel 1 --cache-ram 0
    ;;
  *)
    echo "FATAL: unknown engine '$LETAPIS_SVC_ENGINE' (expected: llama-cpp)"
    exit 1
    ;;
esac
