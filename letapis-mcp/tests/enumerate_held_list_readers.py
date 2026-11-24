"""Every place the proxy reads what it holds about the engine's tool list, listed from the source.

Not a test. Run `uv run python tests/enumerate_held_list_readers.py`: it prints each read of
the held list (`_tool_list`, `tool_list()`, `kept_tool_list()`, `reload_tool_list()`) and of
the state derived from it (`_shown`, `_last_failure`), with the function that reads it, so
each can be judged: does the answer it feeds promise the engine as it is now?
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "letapis_mcp"

HELD = {"_tool_list", "tool_list", "kept_tool_list", "reload_tool_list", "_shown", "_last_failure"}


def _functions(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def main() -> None:
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text())
        seen: set[tuple[int, str]] = set()
        for func in _functions(tree):
            for node in ast.walk(func):
                name = None
                if isinstance(node, ast.Attribute) and node.attr in HELD:
                    name = node.attr
                elif isinstance(node, ast.Name) and node.id in HELD:
                    name = node.id
                if name is None or (node.lineno, name) in seen:
                    continue
                inner = [f for f in _functions(func) if f is not func and f.lineno <= node.lineno <= f.end_lineno]
                if inner:
                    continue
                seen.add((node.lineno, name))
                kind = "write" if isinstance(getattr(node, "ctx", None), ast.Store) else "read"
                print(f"{path.name}:{node.lineno}\t{func.name}\t{name}\t{kind}")


if __name__ == "__main__":
    main()
