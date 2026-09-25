#!/usr/bin/env python3
"""Initialize a project repository, install tooling, and commit the result.

``git init`` is performed first so the remaining steps have a repository to
work with, then the Makefile's ``sync`` and ``check`` targets are invoked. When
the repository has no commits yet the staged tree is offered for an initial
commit, which is pushed only if a remote is already configured.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

COMMIT_MESSAGE = "chore: initialize project"


def _run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=capture,
        text=True,
    )


def _prompt(message: str) -> bool:
    return input(message).strip().casefold() in {"y", "yes"}


def _ensure_repository() -> None:
    probe = _run(["git", "rev-parse", "--is-inside-work-tree"], capture=True)
    if probe.returncode == 0:
        print("Git repository already exists.")
        return
    print("Initializing git repository (main branch)...")
    _run(["git", "init", "-b", "main"])


def _has_commits() -> bool:
    return _run(["git", "rev-parse", "--verify", "HEAD"], capture=True).returncode == 0


def _make(target: str) -> int:
    result = _run(["make", target])
    return result.returncode


def _initial_commit(*, assume_yes: bool) -> bool:
    add = _run(["git", "add", "-A"])
    if add.returncode != 0:
        return False
    if _run(["git", "diff", "--cached", "--quiet"], capture=True).returncode == 0:
        print("Nothing to commit.")
        return False
    print("\nInitial commit:")
    _run(["git", "diff", "--cached", "--stat"])
    print()
    if not assume_yes and not _prompt("Commit initial project? [y/N] "):
        print("Initial commit skipped.")
        return False
    commit = _run(["git", "commit", "-m", COMMIT_MESSAGE])
    return commit.returncode == 0


def _push_initial() -> None:
    if _run(["git", "remote", "get-url", "origin"], capture=True).returncode != 0:
        return
    print("Pushing initial commit...")
    branch = _run(["git", "branch", "--show-current"], capture=True).stdout.strip()
    _run(["git", "push", "-u", "origin", branch])


def initialize(extra_targets: list[str], *, assume_yes: bool) -> int:
    """Initialize the repository and run the requested setup steps."""
    _ensure_repository()
    for target in ("sync", *extra_targets, "check"):
        status = _make(target)
        if status != 0:
            print(f"Setup step failed: make {target}", file=sys.stderr)
            return status
    committed = _initial_commit(assume_yes=assume_yes) if not _has_commits() else False
    if committed:
        _push_initial()
    return 0


def main() -> int:
    """Run the project initializer."""
    parser = argparse.ArgumentParser(description="Initialize the project.")
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help="Extra make target to run between sync and check.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Create the initial commit without prompting.",
    )
    args = parser.parse_args()
    return initialize(list(args.target), assume_yes=bool(args.yes))


if __name__ == "__main__":
    raise SystemExit(main())
