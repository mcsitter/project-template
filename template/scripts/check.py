#!/usr/bin/env python3
"""Run the project's quality checks with a single retry after auto-fixes.

Some hooks fix files and still report failure. Re-running once after such a
change turns a spurious failure into a pass, while a genuine failure is still
reported. Any extra commands given on the command line run after the hooks
have settled, which is how project-specific checks are plugged in.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

TOOL = "prek"


def _run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=capture,
        text=True,
    )


def _worktree_diff() -> str:
    result = _run(["git", "diff"], capture=True)
    return result.stdout if result.returncode == 0 else ""


def _run_hooks(*, verbose: bool) -> tuple[int, str]:
    """Run the hooks, retrying once when they only failed to auto-fix."""
    if verbose:
        first = _run([TOOL, "run", "--all-files"])
        if first.returncode == 0:
            return 0, ""
        print("Hooks failed; re-running.")
        second = _run([TOOL, "run", "--all-files"])
        return second.returncode, ""
    before = _worktree_diff()
    first = _run([TOOL, "run", "--all-files"], capture=True)
    if first.returncode == 0:
        return 0, ""
    if _worktree_diff() == before:
        return first.returncode, first.stdout + first.stderr
    print("Hooks applied fixes; re-running.")
    second = _run([TOOL, "run", "--all-files"], capture=True)
    return second.returncode, second.stdout + second.stderr


def check(extra: list[str], *, verbose: bool = False) -> int:
    """Run the hook suite followed by an extra check command."""
    status, output = _run_hooks(verbose=verbose)
    if status != 0:
        sys.stdout.write(output)
        return status
    if extra:
        result = _run(extra)
        if result.returncode != 0:
            print(f"Check failed: {' '.join(extra)}", file=sys.stderr)
            return result.returncode
    print("Quality checks passed.")
    return 0


def main() -> int:
    """Run the quality checks."""
    parser = argparse.ArgumentParser(description="Run the quality checks.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream hook output instead of only showing it on failure.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="One extra command to run after the hooks pass, after '--'.",
    )
    args = parser.parse_args()
    command = [item for item in args.command if item != "--"]
    return check(command, verbose=bool(args.verbose))


if __name__ == "__main__":
    raise SystemExit(main())
