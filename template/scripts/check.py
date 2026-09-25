#!/usr/bin/env python3
"""Run the project's quality checks with a single retry after auto-fixes.

Some hooks fix files and still report failure. Re-running once after such a
change turns a spurious failure into a pass, while a genuine failure is still
reported. Any extra commands given on the command line run after the hooks
have settled, which is how project-specific checks are plugged in.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys

TOOLS = ("prek", "pre_commit")


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


def _run_hooks(tool: str) -> tuple[int, str]:
    """Run the hooks, retrying once when they only failed to auto-fix."""
    before = _worktree_diff()
    first = _run([tool, "run", "--all-files"], capture=True)
    if first.returncode == 0:
        return 0, ""
    if _worktree_diff() == before:
        return first.returncode, first.stdout + first.stderr
    print("Hooks applied fixes; re-running.")
    second = _run([tool, "run", "--all-files"], capture=True)
    return second.returncode, second.stdout + second.stderr


def check(tool: str, extra: list[str]) -> int:
    """Run the hook suite followed by any extra check commands."""
    status, output = _run_hooks(tool)
    if status != 0:
        sys.stdout.write(output)
        return status
    for command in extra:
        result = _run(shlex.split(command))
        if result.returncode != 0:
            print(f"Check failed: {command}", file=sys.stderr)
            return result.returncode
    print("Quality checks passed.")
    return 0


def main() -> int:
    """Run the quality checks."""
    parser = argparse.ArgumentParser(description="Run the quality checks.")
    parser.add_argument(
        "--tool",
        choices=TOOLS,
        default="prek",
        help="Pre-commit runner to use.",
    )
    parser.add_argument(
        "commands",
        nargs="*",
        help="Extra commands to run after the hooks pass.",
    )
    args = parser.parse_args()
    return check(str(args.tool), list(args.commands))


if __name__ == "__main__":
    raise SystemExit(main())
