#!/usr/bin/env python3
"""Run everything a continuous integration job would run.

The order mirrors a CI pipeline: prove the lockfile is current, run the
quality hooks, then run the test suite under coverage. Coverage is a floor,
not a goal: it catches a large regression without turning into a reason to
write tests that only execute lines.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

UV = "uv"
SCRIPT_DIR = Path(__file__).resolve().parent
CHECK_SCRIPT = SCRIPT_DIR / "check.py"
PROJECT_DIR = SCRIPT_DIR.parent


def _test_files() -> list[Path]:
    """Return the project's test files, if it has any."""
    return sorted(PROJECT_DIR.glob("tests/**/test_*.py"))


def _run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=capture, text=True)


def lockfile_is_current(*, verbose: bool) -> bool:
    """Verify that the lockfile still matches the declared dependencies."""
    result = _run([UV, "lock", "--check"], capture=not verbose)
    if result.returncode != 0:
        if not verbose:
            sys.stderr.write(result.stderr or result.stdout)
        print("Lockfile is out of date; run 'make sync'.", file=sys.stderr)
        return False
    return True


def tests_pass(*, verbose: bool) -> bool:
    """Run the test suite under coverage and report the result.

    A project scaffold may have no tests yet, which is not a failure.
    """
    if not _test_files():
        print("No tests found; skipping the test suite.")
        return True
    run = _run([UV, "run", "--quiet", "coverage", "run", "-m", "pytest", "-q"])
    if run.returncode != 0:
        return False
    report = _run([UV, "run", "--quiet", "coverage", "report"], capture=not verbose)
    if verbose:
        return report.returncode == 0
    sys.stdout.write(report.stdout)
    if report.returncode != 0:
        sys.stderr.write(report.stderr)
    return report.returncode == 0


def _run_extra(command: list[str], *, verbose: bool) -> bool:
    """Run a project-specific check after the generic ones pass."""
    if not command:
        return True
    result = _run(command, capture=not verbose)
    if result.returncode != 0 and not verbose:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
    return result.returncode == 0


def ci(extra: list[str], *, verbose: bool = False) -> int:
    """Run the lockfile check, the quality hooks, the tests, and any extra check.

    ``extra`` is the project-specific check a CI job should also run, such as a
    consistency command. It runs last, because the generic checks are cheaper.
    """
    if not lockfile_is_current(verbose=verbose):
        return 1
    status = _run(
        [sys.executable, str(CHECK_SCRIPT), *(["--verbose"] if verbose else [])],
        capture=not verbose,
    )
    if status.returncode != 0:
        if not verbose:
            sys.stdout.write(status.stdout)
            sys.stderr.write(status.stderr)
        return status.returncode
    if not tests_pass(verbose=verbose):
        print("Tests or coverage failed.", file=sys.stderr)
        return 1
    if not _run_extra(extra, verbose=verbose):
        print(f"Extra check failed: {' '.join(extra)}", file=sys.stderr)
        return 1
    print("CI checks passed.")
    return 0


def main() -> int:
    """Run the continuous integration checks."""
    parser = argparse.ArgumentParser(
        description="Run the lockfile, quality, and test checks."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream command output instead of only showing failures.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="One extra check command to run after the tests, after '--'.",
    )
    args = parser.parse_args()
    command = [item for item in args.command if item != "--"]
    return ci(command, verbose=bool(args.verbose))


if __name__ == "__main__":
    raise SystemExit(main())
