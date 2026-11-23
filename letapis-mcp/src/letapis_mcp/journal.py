"""The proxy's own record of engine failures, readable after the session that saw them is gone.

The host keeps the proxy's stderr only while it connects, so a failure in mid-session leaves
no trace anywhere else. Every proxy on a machine appends to one file; each line names the
process and the engine it talks to.

A line carries fields that hold no content — time, process, engine address, entry, kind of
outcome, HTTP code, exception class — and nothing the engine said or the agent asked: the
agent gets those in the tool answer, while this file stays on disk long after the session.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROTATE_AT = 1 << 20
"""Past this size the file is moved aside before the next line: a threshold, not a cap."""

LINE_LIMIT = 400

_path: Path | None = None
_TOKEN = re.compile(r"[^A-Za-z0-9_.:/=\-]")
_ENTRY = re.compile(r"[^A-Za-z0-9_ /\-]")


def default_path() -> Path:
    """Where a platform keeps a user program's logs."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "letapis-mcp" / "letapis-mcp.log"
    state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "letapis-mcp" / "letapis-mcp.log"


def open_at(path: Path | None) -> None:
    """Start writing to `path`; None keeps the record on stderr only."""
    global _path
    _path = path


def line(now: datetime, pid: int, url: str, entry: str, fields: str) -> str:
    """One log line. Every free-form part is reduced to plain tokens, so nothing longer
    than a word or a number reaches the file, whatever a caller passes."""
    parts = [
        now.isoformat(timespec="seconds"),
        f"pid={pid}",
        f"engine={_token(url)}",
        f"entry={_ENTRY.sub('_', entry)[:120]}",
        *(_token(f) for f in fields.split()),
    ]
    return " ".join(parts)[:LINE_LIMIT] + "\n"


def append(path: Path, text: str) -> None:
    """Add `text` to the file at `path`, moving a file past `ROTATE_AT` to `<name>.1` first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size >= ROTATE_AT:
        os.replace(path, path.with_name(path.name + ".1"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def record(url: str, entry: str, fields: str) -> None:
    """Note that `entry` failed against the engine at `url`; `fields` are `key=value` words."""
    text = line(datetime.now(timezone.utc), os.getpid(), url, entry, fields)
    sys.stderr.write(f"[letapis-mcp] {text}")
    sys.stderr.flush()
    if _path is None:
        return
    try:
        append(_path, text)
    except OSError as e:
        sys.stderr.write(f"[letapis-mcp] cannot write the failure log {_path}: {type(e).__name__}\n")
        sys.stderr.flush()


def _token(value: str) -> str:
    return _TOKEN.sub("_", value)[:120]
