"""Print an overview of the maintenance scripts in this directory.

Run as ``python3 scripts/``. The summaries are read from each module's
docstring, so the listing never drifts from the scripts themselves.
"""

from __future__ import annotations

import ast
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
HIDDEN = {"__init__.py", "__main__.py"}
GUTTER = 2


def _summary(path: Path) -> str:
    """Return the first line of a module's docstring."""
    docstring = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
    if not docstring:
        return ""
    return docstring.strip().splitlines()[0].strip()


def _scripts() -> list[tuple[str, str]]:
    """Return the name and summary of every public script."""
    found: list[tuple[str, str]] = []
    for path in sorted(DIRECTORY.glob("*.py")):
        if path.name in HIDDEN or path.name.startswith("_"):
            continue
        found.append((path.name, _summary(path)))
    return found


def main() -> int:
    """Print the script overview."""
    scripts = _scripts()
    width = max((len(name) for name, _ in scripts), default=0) + GUTTER
    print(f"{_summary(DIRECTORY / '__init__.py')}\n")
    for name, summary in scripts:
        print(f"  {name.ljust(width)}{summary}")
    print("\nDetails: python3 scripts/<name>.py --help")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
