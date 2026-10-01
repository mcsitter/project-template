#!/usr/bin/env python3
"""Update GitHub repository metadata from Copier answers."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ANSWERS_FILE = Path(".copier-answers.yml")


def _answer(text: str, key: str) -> str | None:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip().strip("'\"")
    return None


def repository_name(project_name: str) -> str:
    """Return the GitHub repository name for a project name."""
    return project_name.lower().replace(" ", "-").replace("_", "-")


def _run(
    command: list[str], *, capture: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=capture,
        text=True,
    )


def _login() -> str | None:
    """Return the authenticated GitHub login, or None when it is unreadable."""
    result = _run(["gh", "api", "user", "--jq", ".login"], capture=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _description(name: str) -> str | None:
    """Return a repository description, or None when the repository is missing."""
    result = _run(["gh", "repo", "view", name, "--json", "description"], capture=True)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    description = payload.get("description")
    return description.strip() if isinstance(description, str) else ""


def update_metadata() -> int:
    """Create or update the configured GitHub repository."""
    if shutil.which("gh") is None:
        print("GitHub CLI unavailable; skipping.")
        return 0
    auth = _run(["gh", "auth", "status"], capture=True)
    if auth.returncode != 0:
        print("GitHub CLI is not authenticated; skipping.")
        return 0
    if not ANSWERS_FILE.is_file():
        print("Copier answers not found; skipping.")
        return 0
    answers = ANSWERS_FILE.read_text(encoding="utf-8")
    project_name = _answer(answers, "project_name")
    description = _answer(answers, "project_description")
    if not project_name or not description:
        print("Copier answers are missing project metadata; skipping.")
        return 0
    owner = _login()
    if not owner:
        print("Could not determine the GitHub account; skipping.")
        return 0
    # gh spells repositories as [HOST/]OWNER/REPO, so the owner is not optional.
    name = f"{owner}/{repository_name(project_name)}"
    current = _description(name)
    if current is not None and current == description:
        print(f"GitHub repository unchanged: {name}")
        return 0
    if current is not None:
        result = _run(
            ["gh", "repo", "edit", name, "--description", description],
            capture=True,
        )
        action = "updated"
    else:
        result = _run(
            [
                "gh",
                "repo",
                "create",
                name,
                "--private",
                "--description",
                description,
                "--source",
                ".",
                "--remote",
                "origin",
            ],
            capture=True,
        )
        action = "created"
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        print(f"GitHub repository {action} failed: {detail}", file=sys.stderr)
        return 1
    print(f"GitHub repository {action}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(update_metadata())
