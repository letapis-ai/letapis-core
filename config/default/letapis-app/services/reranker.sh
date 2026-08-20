#!/usr/bin/env bash
# Own the log — rotate 1 generation on start, then redirect self.
# Params from services.yaml via LETAPIS_SVC_* env. `--reranking` /
# `--pooling rank` are deliberately NOT configurable: they are the reranker's MODE, not
# tuning — drop one and /health stays green on a server that is no longer a reranker.
: "${LETAPIS_SVC_ENGINE:=llama-cpp}"
: "${LETAPIS_SVC_MODEL:=$HOME/models/Qwen3-Reranker-0.6B.Q8_0.gguf}"
: "${LETAPIS_SVC_ALIAS:=qwen3-reranker-0.6b}"
: "${LETAPIS_SVC_PORT:=8086}"
: "${LETAPIS_SVC_HOST:=127.0.0.1}"
: "${LETAPIS_SVC_CTX:=8192}"
# Batch defaults to the context size: an input that fits the context must be processable in one
# go. A batch smaller than the context makes the server reject an oversized document with
# `input is too large to process` and cancel the WHOLE batch, discarding neighbours it had
# already scored; the engine then loses the call and silently stops ranking for 30 seconds.
: "${LETAPIS_SVC_BATCH:=$LETAPIS_SVC_CTX}"
: "${LETAPIS_SVC_UBATCH:=$LETAPIS_SVC_CTX}"
# Expand a leading `~` — see the note in embedder.sh.
LETAPIS_SVC_MODEL="${LETAPIS_SVC_MODEL/#\~/$HOME}"
: "${LETAPIS_SVC_BIN:=llama-server}"

LOG=/tmp/letapis-reranker.log
[ -f "$LOG" ] && mv -f "$LOG" "$LOG.1"
exec >> "$LOG" 2>&1

# Engine first, resources second — see the note in embedder.sh.
case "$LETAPIS_SVC_ENGINE" in
  llama-cpp)
    # Destructive: missing runtime / missing weights → loud, not a silent zombie.
    if ! command -v "$LETAPIS_SVC_BIN" >/dev/null 2>&1; then
      echo "FATAL: '$LETAPIS_SVC_BIN' not found in PATH — install llama.cpp or set bin: in this service's yaml"
      exit 1
    fi
    if [ ! -f "$LETAPIS_SVC_MODEL" ]; then
      echo "FATAL: model weights not found: $LETAPIS_SVC_MODEL"
      exit 1
    fi
    exec "$LETAPIS_SVC_BIN" --model "$LETAPIS_SVC_MODEL" \
      --alias "$LETAPIS_SVC_ALIAS" --reranking --pooling rank \
      --port "$LETAPIS_SVC_PORT" --host "$LETAPIS_SVC_HOST" \
      --ctx-size "$LETAPIS_SVC_CTX" \
      --batch-size "$LETAPIS_SVC_BATCH" --ubatch-size "$LETAPIS_SVC_UBATCH" \
      --parallel 1 --n-gpu-layers 99 \
      --flash-attn on --no-mmap --cache-ram 0
    ;;
  *)
    echo "FATAL: unknown engine '$LETAPIS_SVC_ENGINE' (expected: llama-cpp)"
    exit 1
    ;;
esac
