#!/usr/bin/env python3
"""Update a generated project from its Copier template."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

COPIER_SPEC = "copier@latest"


def _run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=capture,
        text=True,
    )


def _clean_worktree() -> bool:
    result = _run(["git", "status", "--porcelain"], capture=True)
    if result.returncode != 0:
        print(result.stderr.strip() or "Could not inspect Git status.", file=sys.stderr)
        return False
    if result.stdout.strip():
        print("Git working tree is not clean. Commit or stash changes first.")
        return False
    return True


def _changed_files() -> list[str]:
    result = _run(["git", "status", "--short"], capture=True)
    if result.returncode != 0:
        return []
    return [line[3:] for line in result.stdout.splitlines() if line]


def _prompt() -> bool:
    try:
        answer = input("Commit template changes? [y/N] ")
    except EOFError:
        return False
    return answer.strip().casefold() in {"y", "yes"}


def update_template(*, assume_yes: bool = False) -> int:
    """Update the template and optionally commit the result."""
    if not _clean_worktree():
        return 1
    if shutil.which("uvx") is None:
        print("uvx is required to update from the template.", file=sys.stderr)
        return 1
    result = _run(
        [
            "uvx",
            "--isolated",
            "--refresh",
            "--from",
            COPIER_SPEC,
            "copier",
            "update",
            # No --defaults here: `copier update` replays the answers recorded
            # in .copier-answers.yml, and --defaults would overwrite them with
            # the template's defaults, renaming the project.
            "--quiet",
        ]
    )
    if result.returncode != 0:
        print("Copier update failed.", file=sys.stderr)
        return result.returncode
    changed = _changed_files()
    if not changed:
        print("Template unchanged.")
        return 0
    print("Template updated:")
    for path in changed:
        print(f"  {path}")
    diff_check = _run(["git", "diff", "--check"], capture=True)
    if diff_check.returncode != 0:
        print(diff_check.stdout, file=sys.stderr)
        return diff_check.returncode
    if not assume_yes and not _prompt():
        print("Template commit skipped.")
        return 0
    add = _run(["git", "add", "-A"])
    if add.returncode != 0:
        return add.returncode
    commit = _run(["git", "commit", "-m", "chore: update from template"])
    if commit.returncode != 0:
        return commit.returncode
    print("Template changes committed.")
    return 0


def main() -> int:
    """Run the template updater."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Commit template changes without prompting.",
    )
    args = parser.parse_args()
    return update_template(assume_yes=bool(args.yes))


if __name__ == "__main__":
    raise SystemExit(main())
