"""The failure log as a file: what a line may hold, and when the file is moved aside."""
from __future__ import annotations

from datetime import datetime, timezone

from letapis_mcp import journal

NOW = datetime(2026, 11, 23, 16, 0, tzinfo=timezone.utc)


def test_a_line_names_process_engine_entry_and_fields():
    text = journal.line(NOW, 42, "http://127.0.0.1:3131", "call search", "kind=http code=500")
    assert text == (
        "2026-11-23T16:00:00+00:00 pid=42 engine=http://127.0.0.1:3131 "
        "entry=call search kind=http code=500\n"
    )


def test_free_text_handed_to_a_line_does_not_reach_it_as_text():
    text = journal.line(NOW, 42, "http://e", "call se'arch\n", "kind=http body=«a secret, here»")
    assert "\n" not in text[:-1]
    assert "secret," not in text and "«" not in text


def test_a_line_is_never_longer_than_the_limit():
    text = journal.line(NOW, 42, "http://" + "h" * 5000, "call " + "n" * 5000, "kind=" + "k" * 5000)
    assert len(text) <= journal.LINE_LIMIT + 1


def test_a_file_past_the_threshold_is_moved_aside_before_the_next_line(tmp_path):
    log = tmp_path / "letapis-mcp.log"
    log.write_text("x" * journal.ROTATE_AT)
    journal.append(log, "new line\n")
    assert log.read_text() == "new line\n"
    assert (tmp_path / "letapis-mcp.log.1").stat().st_size == journal.ROTATE_AT


def test_a_file_below_the_threshold_keeps_growing(tmp_path):
    log = tmp_path / "letapis-mcp.log"
    log.write_text("old line\n")
    journal.append(log, "new line\n")
    assert log.read_text() == "old line\nnew line\n"
    assert not (tmp_path / "letapis-mcp.log.1").exists()
