"""Add Ruff rule documentation links to a template."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

RUFF_RULE_URL = "https://docs.astral.sh/ruff/rules/{slug}/"
RUFF_RULE_PATTERN = re.compile(r'"([A-Z]+\d+)"')
RUFF_RULE_HEADER_PATTERN = re.compile(r"#\s+([a-z0-9-]+)\s+\(([A-Z]+\d+)\)")
RUFF_RULE_COMMENT_PATTERN = re.compile(r"\s+# https://docs\.astral\.sh/ruff/rules/\S+")


def extract_rules(path: Path) -> list[str]:
    """Extract Ruff rule codes from a template."""
    return sorted(set(RUFF_RULE_PATTERN.findall(path.read_text())))


def get_rule_slug(rule: str) -> str:
    """Get the Ruff rule slug."""
    uvx_path = shutil.which("uvx")
    if uvx_path is None:
        msg = "uvx is required to generate Ruff links. "
        raise RuntimeError(msg)

    result = subprocess.run(  # noqa: S603 - uvx is resolved from PATH
        [uvx_path, "ruff", "rule", rule],
        check=True,
        capture_output=True,
        text=True,
    )
    match = RUFF_RULE_HEADER_PATTERN.search(result.stdout)
    if match is None:
        msg = f"Couldn't find slug for Ruff rule {rule} in uvx output:\n{result.stdout}"
        raise RuntimeError(msg)
    return match.group(1)


def align_comments(lines: list[str]) -> list[str]:
    """Align consecutive trailing comments."""
    result: list[str] = []
    block: list[str] = []

    def flush() -> None:
        """Flush aligned comment block."""
        if not block:
            return

        column = max(line.index("#") for line in block)
        for line in block:
            value, comment = line.split("#", 1)
            result.append(f"{value.rstrip():<{column - 1}}# {comment.strip()}\n")
        block.clear()

    for line in lines:
        if re.search(r'"[A-Z]+\d+",\s*#', line):
            block.append(line)
        else:
            flush()
            result.append(line)

    flush()
    return result


def add_links(path: Path, links: dict[str, str]) -> None:
    """Add Ruff documentation links."""
    lines = path.read_text().splitlines(keepends=True)
    updated: list[str] = []

    for line in lines:
        match = RUFF_RULE_PATTERN.search(line)
        if match is None:
            updated.append(line)
            continue

        rule = match.group(1)
        url = links.get(rule)
        if url is None:
            updated.append(line)
            continue
        clean_line = RUFF_RULE_COMMENT_PATTERN.sub("", line.rstrip("\n"))
        updated.append(f"{clean_line}  # {url}\n")

    path.write_text("".join(align_comments(updated)))


def main() -> int:
    """Update Ruff links."""
    path = Path("template/pyproject.toml.jinja")
    rules = extract_rules(path)

    links = {rule: RUFF_RULE_URL.format(slug=get_rule_slug(rule)) for rule in rules}

    add_links(path, links)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
