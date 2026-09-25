#!/usr/bin/env python3
"""Update pre-commit hook revisions and commit the resulting changes."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

CONFIG_FILE = Path(".pre-commit-config.yaml")
TEMPLATE_FILE = Path("template/.pre-commit-config.yaml.jinja")
JINJA_PATTERN = re.compile(r"({{[\s\S]*?}}|{%[\s\S]*?%})")


def _run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=capture,
        text=True,
    )


def _strip_jinja(text: str) -> str:
    return JINJA_PATTERN.sub("", text)


def _revisions(text: str) -> dict[str, str]:
    """Extract ``repo`` to ``rev`` pairs from a pre-commit config.

    The config only ever contains a flat ``repos`` list of ``repo``/``rev``
    keys, so a line scan avoids depending on a YAML library.
    """
    revisions: dict[str, str] = {}
    current_repo: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- repo:"):
            current_repo = stripped.split("repo:", 1)[1].strip().strip("'\"")
        elif stripped.startswith("rev:") and current_repo is not None:
            revisions[current_repo] = stripped.split("rev:", 1)[1].strip().strip("'\"")
    return revisions


def _patch_template(text: str, revisions: dict[str, str]) -> str:
    output: list[str] = []
    current_repository: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        output_line = line
        if stripped.startswith("- repo:"):
            current_repository = stripped.split("repo:", 1)[1].strip()
        if current_repository in revisions and stripped.startswith("rev:"):
            indent = line[: line.index("rev:")]
            output_line = f"{indent}rev: {revisions[current_repository]}"
        output.append(output_line)
    return "\n".join(output) + "\n"


def _autoupdate() -> int:
    result = _run([sys.executable, "-m", "prek", "autoupdate"])
    return result.returncode


def _changed_files() -> list[str]:
    result = _run(["git", "status", "--short"], capture=True)
    if result.returncode != 0:
        return []
    return [line[3:] for line in result.stdout.splitlines() if line]


def _prompt() -> bool:
    return input("Commit these changes? [y/N] ").strip().casefold() in {"y", "yes"}


def update_hooks(*, assume_yes: bool = False) -> int:
    """Update hook revisions, validate, and optionally commit them."""
    template_mode = TEMPLATE_FILE.is_file()
    if template_mode:
        original_config = CONFIG_FILE.read_text(encoding="utf-8")
        template_text = TEMPLATE_FILE.read_text(encoding="utf-8")
        CONFIG_FILE.write_text(_strip_jinja(template_text), encoding="utf-8")
        try:
            status = _autoupdate()
        finally:
            CONFIG_FILE.write_text(original_config, encoding="utf-8")
        if status != 0:
            return status
        config_text = CONFIG_FILE.read_text(encoding="utf-8")
        updated_template = _patch_template(template_text, _revisions(config_text))
        if updated_template != template_text:
            TEMPLATE_FILE.write_text(updated_template, encoding="utf-8")
    else:
        status = _autoupdate()
        if status != 0:
            return status

    changed = _changed_files()
    if not changed:
        print("Pre-commit hooks unchanged.")
        return 0
    print("Pre-commit hook changes:")
    for path in changed:
        print(f"  {path}")
    checks = _run(["make", "check"], capture=True)
    if checks.returncode != 0:
        print(checks.stdout, file=sys.stderr)
        print(checks.stderr, file=sys.stderr)
        return checks.returncode
    if not assume_yes and not _prompt():
        print("Pre-commit hook commit skipped.")
        return 0
    add = _run(["git", "add", str(CONFIG_FILE)])
    if add.returncode != 0:
        return add.returncode
    files = [str(CONFIG_FILE)]
    if template_mode:
        add_template = _run(["git", "add", str(TEMPLATE_FILE)])
        if add_template.returncode != 0:
            return add_template.returncode
        files.append(str(TEMPLATE_FILE))
    commit = _run(
        ["git", "commit", "-m", "chore: update pre-commit hooks", "--", *files]
    )
    if commit.returncode != 0:
        return commit.returncode
    print("Pre-commit hooks updated and committed.")
    return 0


def main() -> int:
    """Run the pre-commit hook updater."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Commit hook changes without prompting.",
    )
    args = parser.parse_args()
    return update_hooks(assume_yes=bool(args.yes))


if __name__ == "__main__":
    raise SystemExit(main())
