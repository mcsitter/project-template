#!/usr/bin/env python3
"""Remove build artifacts and generated files from a project.

Two independent stages are available so that callers keep control over how
much is deleted:

* the *artifacts* stage removes well-known build output such as caches,
  ``build/`` and ``dist/``; it never touches tracked files and supports
  ``--dry-run``;
* the *untracked* stage additionally removes everything Git reports as
  untracked or ignored, which is what a fresh clone leaves behind.

Both stages preview what they would delete and ask for confirmation unless
``--yes`` is given. The untracked stage always keeps the virtualenv, ``.env``
files, untracked Python sources, the lockfile, and the Copier answers file.

Project-specific generated output is removed by the artifacts stage through
``--pattern``, a repeatable regular expression matched against repo-relative
paths, for example ``--pattern '^generated/'``.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_PATTERNS = (
    r"(^|/)build$",
    r"(^|/)dist$",
    r"\.egg-info$",
    r"(^|/)__pycache__$",
    r"^\.import_linter_cache$",
    r"^\.mypy_cache$",
    r"^\.pytest_cache$",
    r"^\.ruff_cache$",
)
PROTECTED = (
    ".venv/",
    ".env*",
    "*.py",
    "uv.lock",
    ".copier-answers.yml",
)
PRUNED_DIRECTORIES = frozenset(
    {".git", ".venv", ".tox", ".nox", "node_modules", "site-packages"}
)


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


def _git_tracked() -> set[str]:
    result = _run(["git", "ls-files"], capture=True)
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def _compile(patterns: list[str]) -> list[re.Pattern[str]]:
    """Compile the default patterns together with any user patterns."""
    return [re.compile(pattern) for pattern in (*DEFAULT_PATTERNS, *patterns)]


def _walk_artifacts(patterns: list[re.Pattern[str]]) -> list[Path]:
    """Find artifact directories, skipping virtualenvs and VCS metadata."""
    found: list[Path] = []
    for root, directories, _ in os.walk(".", topdown=True):
        kept: list[str] = []
        for name in sorted(directories):
            if name in PRUNED_DIRECTORIES:
                continue
            path = Path(root) / name
            relative = path.as_posix().removeprefix("./")
            if any(pattern.search(relative) for pattern in patterns):
                found.append(path)
                continue
            kept.append(name)
        directories[:] = kept
    return found


def _collect_artifacts(patterns: list[re.Pattern[str]]) -> list[Path]:
    """Return artifact paths that exist and are not tracked by Git."""
    tracked = _git_tracked()
    found: list[Path] = []

    def add(path: Path) -> None:
        if path.exists() and str(path) not in tracked and path not in found:
            found.append(path)

    for artifact in _walk_artifacts(patterns):
        if str(artifact) not in tracked:
            add(artifact)
    return found


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def clean_artifacts(
    patterns: list[re.Pattern[str]], *, dry_run: bool, assume_yes: bool
) -> int:
    """Remove well-known build artifacts and registered generated paths."""
    artifacts = _collect_artifacts(patterns)
    if not artifacts:
        print("No generated artifacts found.")
        return 0
    print("Generated artifacts:")
    for path in artifacts:
        print(f"  {path}")
    if dry_run:
        print("Dry run: nothing was removed.")
        return 0
    if not assume_yes and not _prompt("Remove these artifacts? [y/N] "):
        print("Artifact removal skipped.")
        return 0
    for path in artifacts:
        _remove(path)
    print(f"Removed {len(artifacts)} artifact(s).")
    return 0


def clean_untracked(*, dry_run: bool, assume_yes: bool) -> int:
    """Remove untracked and ignored files, keeping virtualenvs and secrets."""
    excludes: list[str] = []
    for pattern in PROTECTED:
        excludes += ["-e", pattern]
    listed = _run(["git", "clean", "-xdn", *excludes], capture=True)
    if listed.returncode != 0:
        message = listed.stderr.strip() or "Could not list untracked files."
        print(message, file=sys.stderr)
        return listed.returncode
    files = [line for line in listed.stdout.splitlines() if line.strip()]
    if not files:
        print("No untracked files found.")
        return 0
    print("Untracked and ignored files:")
    for line in files:
        print(f"  {line}")
    if dry_run:
        print("Dry run: nothing was removed.")
        return 0
    if not assume_yes and not _prompt("Delete these files? [y/N] "):
        print("File removal skipped.")
        return 0
    remove = _run(["git", "clean", "-xdf", *excludes])
    if remove.returncode != 0:
        print(remove.stderr.strip() or "Could not remove files.", file=sys.stderr)
        return remove.returncode
    print("Removed untracked files.")
    return 0


def main() -> int:
    """Run the project cleaner."""
    parser = argparse.ArgumentParser(
        description="Remove build artifacts and generated files.",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        default=[],
        metavar="REGEX",
        help="Extra regex matched against repo-relative paths. Repeatable.",
    )
    parser.add_argument(
        "--artifacts-only",
        action="store_true",
        help="Only remove build artifacts, not untracked files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without removing anything.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Remove without prompting.",
    )
    args = parser.parse_args()
    status = clean_artifacts(
        _compile([str(pattern) for pattern in args.pattern]),
        dry_run=bool(args.dry_run),
        assume_yes=bool(args.yes),
    )
    if status != 0 or args.artifacts_only:
        return status
    return clean_untracked(
        dry_run=bool(args.dry_run),
        assume_yes=bool(args.yes),
    )


if __name__ == "__main__":
    raise SystemExit(main())
