#!/usr/bin/env bash
# Own the log — rotate 1 generation on start, then redirect self.
# The vector database, native. Storage sits on APFS directly — Qdrant maps its
# segments into memory and wants honest fsync semantics, which the Mac to VM file layer does
# not always give.
#
# Both parameters come from qdrant.yaml as LETAPIS_SVC_* env, and both are PATHS: the
# binary you unpacked and the config the panel wrote beside it. Everything else about Qdrant —
# where the storage goes, which ports it binds — lives in that config, which is yours to edit.
: "${LETAPIS_SVC_BIN:=$HOME/.local/letapis-qdrant/bin/qdrant}"
: "${LETAPIS_SVC_CONFIG:=$HOME/.local/letapis-qdrant/config.yaml}"
# The card spells these with a leading `~`; nothing expands it for us — see the note in
# embedder.sh.
LETAPIS_SVC_BIN="${LETAPIS_SVC_BIN/#\~/$HOME}"
LETAPIS_SVC_CONFIG="${LETAPIS_SVC_CONFIG/#\~/$HOME}"

LOG=/tmp/letapis-qdrant.log
[ -f "$LOG" ] && mv -f "$LOG" "$LOG.1"
exec >> "$LOG" 2>&1

# Destructive: no binary / no config -> say which file is missing and exit. The `exec` alone
# would die into the log with the shell's own wording and leave the card red for no readable
# reason. The binary is not in the kit, so "not unpacked yet" is the ordinary first state here.
[ -x "$LETAPIS_SVC_BIN" ] || {
  echo "FATAL: qdrant binary not executable: $LETAPIS_SVC_BIN — unpack the release archive there or set bin: in this service's yaml"
  exit 1
}
[ -f "$LETAPIS_SVC_CONFIG" ] || {
  echo "FATAL: no config: $LETAPIS_SVC_CONFIG"
  exit 1
}

# Paths inside the config are absolute, so cwd does not decide where the storage lands.
exec "$LETAPIS_SVC_BIN" --config-path "$LETAPIS_SVC_CONFIG"
