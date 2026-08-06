#!/usr/bin/env python3
"""Lint Makefile targets."""

from __future__ import annotations

import re
from pathlib import Path

TARGET_RE = re.compile(r"^([A-Za-z0-9_.%/@+-]+):(?:\s|$)")
PHONY_RE = re.compile(r"^\.PHONY:\s*(.*)$")


def get_targets(lines: list[str]) -> list[tuple[str, int]]:
    """Get Makefile targets with line numbers."""
    targets: list[tuple[str, int]] = []

    for lineno, line in enumerate(lines, start=1):
        match = TARGET_RE.match(line)
        if match is None:
            continue

        target = match.group(1)

        if target.startswith("."):
            continue

        targets.append((target, lineno))

    return targets


def has_comment(lines: list[str], index: int) -> bool:
    """Check if a target has a preceding comment."""
    return index > 0 and lines[index - 1].startswith("## ")


def get_comment(lines: list[str], index: int) -> str:
    """Get target comment text."""
    return lines[index - 1].removeprefix("## ")


def check_comment_format(comment: str) -> list[str]:
    """Check comment capitalization and punctuation."""
    errors: list[str] = []

    if not comment:
        errors.append("Comment is empty.")
        return errors

    if not comment[0].isupper():
        errors.append("Comment must start with an uppercase letter.")

    if not comment.endswith("."):
        errors.append("Comment must end with a period.")

    return errors


def check_comments(lines: list[str]) -> list[str]:
    """Check that targets have valid comments."""
    errors: list[str] = []

    for index, line in enumerate(lines):
        match = TARGET_RE.match(line)

        if match is None:
            continue

        target = match.group(1)

        if target.startswith("."):
            continue

        if not has_comment(lines, index):
            errors.append(f"Target '{target}' is missing a comment (line {index + 1}).")
            continue

        errors.extend(
            f"Target '{target}': {error}"
            for error in check_comment_format(get_comment(lines, index))
        )

    return errors


def is_jinja(lines: list[str]) -> bool:
    """Check if the Makefile is a Jinja template."""
    return any("{%" in line or "{{" in line for line in lines)


def update_phony(lines: list[str], targets: list[tuple[str, int]]) -> list[str]:
    """Update phony declaration."""
    updated = lines.copy()
    target_names = sorted(target for target, _ in targets)

    if is_jinja(updated):
        return update_jinja_phony(updated, target_names)

    for index, line in enumerate(updated):
        if PHONY_RE.match(line):
            updated[index] = f".PHONY: {' '.join(target_names)}"
            break

    return updated


def update_jinja_phony(lines: list[str], targets: list[str]) -> list[str]:
    """Update Jinja phony target list."""
    updated = lines.copy()
    target_list = ", ".join(f'"{target}"' for target in targets)
    phony_line = f"{{%- set phony_targets = [{target_list}] %}}"

    for index, line in enumerate(updated):
        if "set phony_targets =" in line:
            updated[index] = phony_line
            break

    return updated


def lint_file(path: Path) -> list[str]:
    """Lint one Makefile."""
    lines = path.read_text(encoding="utf-8").splitlines()

    targets = get_targets(lines)
    errors = check_comments(lines)

    if errors:
        return [f"{path}: {error}" for error in errors]

    updated = update_phony(lines, targets)

    if updated != lines:
        print(f"{path}: fixed .PHONY declaration")

        path.write_text(
            "\n".join(updated) + "\n",
            encoding="utf-8",
        )

    return []


def main() -> int:
    """Lint Makefiles."""
    files = [
        Path("Makefile"),
        Path("template/Makefile.jinja"),
    ]

    errors: list[str] = []

    for path in files:
        if not path.exists():
            continue

        errors.extend(lint_file(path))

    if errors:
        print("\n".join(errors))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
