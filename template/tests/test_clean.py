"""Tests for the clean script that every generated project ships."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from clean import (
    _compile,
    _remove,
    _walk_artifacts,
    clean_artifacts,
)

NothingTracked = "nothing-tracked"


def _no_tracked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the script behave as if the working tree tracks no files."""

    def _tracked() -> set[str]:
        return set()

    monkeypatch.setattr("clean._git_tracked", _tracked)


def _tracked_as(monkeypatch: pytest.MonkeyPatch, paths: set[str]) -> None:
    """Make the script behave as if only the given paths are tracked."""

    def _tracked() -> set[str]:
        return paths

    monkeypatch.setattr("clean._git_tracked", _tracked)


@pytest.fixture
def in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run inside an empty directory so artifact walking sees only test files."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_walk_artifacts_finds_a_known_build_directory(in_tmp_path: Path) -> None:
    (in_tmp_path / "dist").mkdir()
    (in_tmp_path / "src").mkdir()

    assert _walk_artifacts(_compile([])) == [Path("dist")]


def test_walk_artifacts_does_not_descend_into_an_artifact(in_tmp_path: Path) -> None:
    (in_tmp_path / "dist" / "nested" / "__pycache__").mkdir(parents=True)

    found = _walk_artifacts(_compile([]))

    assert found == [Path("dist")]
    assert not any("nested" in str(path) for path in found)


def test_walk_artifacts_skips_virtualenvs_and_git(in_tmp_path: Path) -> None:
    (in_tmp_path / ".venv" / "dist").mkdir(parents=True)
    (in_tmp_path / ".git" / "dist").mkdir(parents=True)

    assert _walk_artifacts(_compile([])) == []


def test_compile_includes_extra_user_patterns() -> None:
    patterns = _compile(["custom-artifacts"])

    assert any(pattern.search("some/custom-artifacts") for pattern in patterns)


def test_compile_keeps_the_default_patterns() -> None:
    assert any(pattern.search("dist") for pattern in _compile([]))


def test_clean_artifacts_dry_run_removes_nothing(
    in_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (in_tmp_path / "dist").mkdir()
    _no_tracked(monkeypatch)

    clean_artifacts(_compile([]), dry_run=True, assume_yes=False)

    assert (in_tmp_path / "dist").is_dir()
    assert "Dry run" in capsys.readouterr().out


def test_clean_artifacts_removes_untracked_artifacts(
    in_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (in_tmp_path / "dist").mkdir()
    _no_tracked(monkeypatch)

    clean_artifacts(_compile([]), dry_run=False, assume_yes=True)

    assert not (in_tmp_path / "dist").exists()
    assert "Removed 1 artifact" in capsys.readouterr().out


def test_clean_artifacts_keeps_a_tracked_directory(
    in_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (in_tmp_path / "dist").mkdir()
    _tracked_as(monkeypatch, {"dist"})

    clean_artifacts(_compile([]), dry_run=False, assume_yes=True)

    assert (in_tmp_path / "dist").is_dir()


def test_clean_artifacts_reports_nothing_to_do(
    in_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not any(in_tmp_path.iterdir())
    _no_tracked(monkeypatch)

    clean_artifacts(_compile([]), dry_run=False, assume_yes=True)

    assert "No generated artifacts found." in capsys.readouterr().out


def test_clean_artifacts_declines_without_confirmation(
    in_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (in_tmp_path / "dist").mkdir()
    _no_tracked(monkeypatch)
    monkeypatch.setattr("clean._prompt", lambda _message: False)

    clean_artifacts(_compile([]), dry_run=False, assume_yes=False)

    assert (in_tmp_path / "dist").is_dir()


def test_remove_handles_a_directory_and_a_file(tmp_path: Path) -> None:
    directory = tmp_path / "dist"
    directory.mkdir()
    file_path = tmp_path / "artifact.txt"
    file_path.write_text("x", encoding="utf-8")

    _remove(directory)
    _remove(file_path)

    assert not directory.exists()
    assert not file_path.exists()
