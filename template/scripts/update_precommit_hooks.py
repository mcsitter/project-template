#!/usr/bin/env python3
"""Update pre-commit hook revisions and commit the resulting changes.

A generated project only has ``.pre-commit-config.yaml``. The template
repository also owns ``template/.pre-commit-config.yaml.jinja``, and Copier
leaves the real config alone, so both have to end up on the same revisions.
Rather than overwrite the real config with a de-Jinjad template and put it back
afterwards, the template is rendered into a scratch config, that scratch config
is what gets autoupdated, and the revisions it settled on are written back to
both files. Only files this script actually changed are staged and committed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CONFIG_FILE = Path(".pre-commit-config.yaml")
TEMPLATE_FILE = Path("template/.pre-commit-config.yaml.jinja")
JINJA_PATTERN = re.compile(r"({{[\s\S]*?}}|{%[\s\S]*?%})")
COMMIT_MESSAGE = "chore: update pre-commit hooks"


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


def _patch(text: str, revisions: dict[str, str]) -> str:
    """Return ``text`` with every known repository's ``rev`` set to the new one.

    Repositories missing from ``revisions`` are left alone, so a config that
    lists a hook the template does not keep its own revision.
    """
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


def _autoupdate(config: Path) -> int:
    """Point every ``repo`` in ``config`` at its latest release."""
    result = _run(
        [sys.executable, "-m", "prek", "autoupdate", "--config", str(config)],
    )
    return result.returncode


def _template_revisions() -> tuple[dict[str, str], int]:
    """Return the latest revisions for the template's repositories.

    The template is rendered into a scratch file so the repositories it holds
    conditionally, such as the ``mypy`` mirror, are covered too. The exit status
    is returned alongside the revisions so a failed run is never mistaken for an
    up-to-date template.
    """
    template_text = TEMPLATE_FILE.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory) / CONFIG_FILE.name
        scratch.write_text(_strip_jinja(template_text), encoding="utf-8")
        status = _autoupdate(scratch)
        if status != 0:
            return {}, status
        return _revisions(scratch.read_text(encoding="utf-8")), 0


def _prompt() -> bool:
    try:
        answer = input("Commit these changes? [y/N] ")
    except EOFError:
        return False
    return answer.strip().casefold() in {"y", "yes"}


def _commit(paths: list[Path]) -> int:
    """Stage the given paths and commit them."""
    for path in paths:
        add = _run(["git", "add", str(path)])
        if add.returncode != 0:
            return add.returncode
    commit = _run(
        ["git", "commit", "-m", COMMIT_MESSAGE, "--", *(str(path) for path in paths)],
    )
    return commit.returncode


def update_hooks(*, assume_yes: bool = False) -> int:
    """Update hook revisions, validate, and optionally commit them."""
    template_mode = TEMPLATE_FILE.is_file()
    targets = [CONFIG_FILE, TEMPLATE_FILE] if template_mode else [CONFIG_FILE]
    before = {path: path.read_text(encoding="utf-8") for path in targets}

    if template_mode:
        revisions, status = _template_revisions()
        if status != 0:
            return status
        for path in targets:
            path.write_text(_patch(before[path], revisions), encoding="utf-8")
    else:
        status = _autoupdate(CONFIG_FILE)
        if status != 0:
            return status

    changed = [
        path for path in targets if path.read_text(encoding="utf-8") != before[path]
    ]
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
    status = _commit(changed)
    if status != 0:
        return status
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
