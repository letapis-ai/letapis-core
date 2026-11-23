"""Every place the proxy answers or logs an engine failure, listed from the source.

Not a test. Run `uv run python tests/enumerate_failure_paths.py`: it prints each call of
`engine_failure` with whether it may still run, each `journal.record` with what it is
handed, and the answer for every kind of no-answer on both sides of `may_still_run`.
"""
from __future__ import annotations

import ast
from pathlib import Path

from letapis_mcp.answers import NoAnswer, engine_failure

SRC = Path(__file__).resolve().parent.parent / "src" / "letapis_mcp"


def _calls(tree: ast.AST, name: str):
    for func in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for node in ast.walk(func):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            called = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", "")
            if called == name:
                yield func.name, node


def main() -> None:
    for path in sorted(SRC.glob("*.py")):
        tree = ast.parse(path.read_text())
        for func, node in _calls(tree, "engine_failure"):
            kw = {k.arg: ast.unparse(k.value) for k in node.keywords}
            print(f"engine_failure {path.name}:{node.lineno} in {func}: "
                  f"may_still_run={kw.get('may_still_run', 'False')} asked_for={kw.get('asked_for')}")
        for func, node in _calls(tree, "record"):
            print(f"journal.record {path.name}:{node.lineno} in {func}: "
                  f"{' | '.join(ast.unparse(a) for a in node.args)}")
    print()
    for kind in ("refused", "not_connected", "timeout", "dropped"):
        for may_still_run in (False, True):
            answer = engine_failure(
                NoAnswer(kind, "E", "d"), url="u", asked_for="x", may_still_run=may_still_run
            )
            advises_again = "call again" in answer["message"] or "retry" in answer["message"].lower()
            print(f"{kind:14} may_still_run={may_still_run!s:5} -> status={answer['status']:12} "
                  f"advises calling again={advises_again}")


if __name__ == "__main__":
    main()
