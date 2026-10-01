"""Tests for the GitHub metadata script that every generated project ships."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from update_github_metadata import _login, repository_name, update_metadata

ANSWERS = (
    "_commit: 1\n"
    "_src_path: .\n"
    "project_description: Do things.\n"
    "project_name: My Project\n"
)


def _completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["gh"], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.fixture
def in_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Write a Copier answers file and run from the directory holding it."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".copier-answers.yml").write_text(ANSWERS, encoding="utf-8")


def _fake_gh(
    monkeypatch: pytest.MonkeyPatch,
    *,
    login: str = "octocat",
    view_found: bool = False,
    description: str = "Do things.",
    write_error: str = "",
) -> list[list[str]]:
    """Record every gh call, answering as a GitHub CLI would."""
    calls: list[list[str]] = []

    def _run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        verb = command[1:3]
        if verb == ["api", "user"]:
            return _completed(stdout=f"{login}\n")
        if verb == ["repo", "view"]:
            if not view_found:
                return _completed(returncode=1)
            return _completed(stdout=json.dumps({"description": description}))
        if verb[0] == "repo" and write_error:
            return _completed(returncode=1, stderr=f"{write_error}\n")
        return _completed()

    monkeypatch.setattr("update_github_metadata._run", _run)
    return calls


def test_repository_name_is_kebab_case() -> None:
    assert repository_name("My Project") == "my-project"


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        (_completed(stdout="octocat\n"), "octocat"),
        (_completed(stdout="\n"), None),
        (_completed(returncode=1), None),
    ],
)
def test_login_reads_the_authenticated_user(
    reply: subprocess.CompletedProcess[str],
    expected: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("update_github_metadata._run", lambda *_a, **_k: reply)

    assert _login() == expected


@pytest.mark.usefixtures("in_project")
def test_update_asks_gh_for_the_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _fake_gh(monkeypatch)

    assert update_metadata() == 0
    assert calls[0] == ["gh", "auth", "status"]
    assert calls[1] == ["gh", "api", "user", "--jq", ".login"]


@pytest.mark.usefixtures("in_project")
def test_update_creates_an_owner_qualified_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_gh(monkeypatch)

    assert update_metadata() == 0
    create = next(c for c in calls if c[1:3] == ["repo", "create"])
    assert create[3] == "octocat/my-project"


@pytest.mark.usefixtures("in_project")
def test_update_edits_an_owner_qualified_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_gh(monkeypatch, view_found=True, description="Stale.")

    assert update_metadata() == 0
    edit = next(c for c in calls if c[1:3] == ["repo", "edit"])
    assert edit[3] == "octocat/my-project"
    assert not any(c[1:3] == ["repo", "create"] for c in calls)


@pytest.mark.usefixtures("in_project")
def test_update_skips_a_repository_that_already_matches(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _fake_gh(monkeypatch, view_found=True, description="Do things.")

    assert update_metadata() == 0
    assert "unchanged" in capsys.readouterr().out
    assert not any(c[1] == "repo" and c[2] in {"edit", "create"} for c in calls)


@pytest.mark.usefixtures("in_project")
def test_update_reports_a_gh_failure_instead_of_crashing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_gh(monkeypatch, write_error="name already exists")

    assert update_metadata() == 1
    assert "name already exists" in capsys.readouterr().err


@pytest.mark.usefixtures("in_project")
def test_update_skips_when_the_account_is_unknown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _fake_gh(monkeypatch, login="")

    assert update_metadata() == 0
    assert "Could not determine the GitHub account" in capsys.readouterr().out
    assert not any(c[1:2] == ["repo"] for c in calls)
