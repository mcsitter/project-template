#!/usr/bin/env python3
"""Commit the current changes and push the current branch.

Used as the final step of maintenance workflows. The staged file list is shown
before committing, and whitespace errors abort the commit so a broken diff is
never pushed. Pass ``--message`` to override the default commit subject.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

DEFAULT_MESSAGE = "chore: update"


def _run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=capture,
        text=True,
    )


def _porcelain() -> str:
    result = _run(["git", "status", "--porcelain"], capture=True)
    return result.stdout if result.returncode == 0 else ""


def _check_whitespace(*, staged: bool) -> bool:
    command = (
        ["git", "diff", "--cached", "--check"] if staged else ["git", "diff", "--check"]
    )
    result = _run(command)
    return result.returncode == 0


def commit_and_push(message: str) -> int:
    """Commit pending changes and push the current branch."""
    if not _porcelain().strip():
        print("Nothing to commit.")
    else:
        if not _check_whitespace(staged=False):
            print("Whitespace errors found; not committing.", file=sys.stderr)
            return 1
        add = _run(["git", "add", "-A"])
        if add.returncode != 0:
            return add.returncode
        if not _check_whitespace(staged=True):
            print("Whitespace errors found; not committing.", file=sys.stderr)
            return 1
        print("Committing changes:")
        staged = _run(["git", "diff", "--cached", "--name-only"], capture=True)
        for path in staged.stdout.splitlines():
            if path.strip():
                print(f"  {path.strip()}")
        commit = _run(["git", "commit", "-m", message])
        if commit.returncode != 0:
            return commit.returncode
        revision = _run(["git", "rev-parse", "--short", "HEAD"], capture=True)
        print(f"Committed {revision.stdout.strip()}.")
    push = _run(["git", "push"])
    if push.returncode != 0:
        return push.returncode
    branch = _run(["git", "branch", "--show-current"], capture=True).stdout.strip()
    print(f"Pushed {branch}.")
    return 0


def main() -> int:
    """Commit and push the current changes."""
    parser = argparse.ArgumentParser(description="Commit and push changes.")
    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
        help="Commit message to use.",
    )
    args = parser.parse_args()
    return commit_and_push(str(args.message))


if __name__ == "__main__":
    raise SystemExit(main())
