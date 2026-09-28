"""Tests for the Makefile linter used by this repository.

The linter is repository-specific tooling rather than something the template
ships, so these tests live beside the template sources and are not part of the
generated project.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import lint_makefile


def test_get_targets_skips_a_repeated_target_line() -> None:
    lines = [
        "## Run the checks.",
        "ci: export CI := true",
        "ci: check",
        "\t@echo hi",
    ]

    assert lint_makefile.get_targets(lines) == [("ci", 3)]


def test_get_targets_reports_each_target_once() -> None:
    lines = [
        "## One.",
        "check:",
        "\t@echo hi",
        "## Two.",
        "ci: check",
        "\t@echo hi",
    ]

    assert [name for name, _ in lint_makefile.get_targets(lines)] == ["check", "ci"]


def test_comment_is_found_past_a_target_specific_export() -> None:
    lines = [
        "## Run the checks.",
        "ci: export CI := true",
        "ci: check",
    ]

    assert lint_makefile.has_comment(lines, 2) is True
    assert lint_makefile.get_comment(lines, 2) == "Run the checks."


def test_export_line_does_not_need_its_own_comment() -> None:
    lines = [
        "## Run the checks.",
        "ci: export CI := true",
        "ci: check",
    ]

    assert lint_makefile.check_comments(lines) == []


def test_target_without_any_comment_is_reported() -> None:
    lines = ["ci: export CI := true", "ci: check"]

    errors = lint_makefile.check_comments(lines)

    assert len(errors) == 1
    assert "ci" in errors[0]


def test_phony_declaration_lists_every_target_once(tmp_path: Path) -> None:
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        ".PHONY: check\n\n"
        "## Run the quality checks.\n"
        "check:\n"
        "\t@echo hi\n\n"
        "## Run the checks and the tests.\n"
        "ci: export CI := true\n"
        "ci: check\n"
        "\t@echo hi\n",
        encoding="utf-8",
    )

    errors = lint_makefile.lint_file(makefile)

    assert errors == []
    assert makefile.read_text(encoding="utf-8").splitlines()[0] == ".PHONY: check ci"


def test_jinja_phony_list_contains_names_not_line_numbers() -> None:
    lines = [
        '{%- set phony_targets = ["stale"] %}',
        "## Run the checks.",
        "ci: check",
    ]
    targets = ["check", "ci"]

    updated = lint_makefile.update_jinja_phony(lines, targets)

    assert updated[0] == '{%- set phony_targets = ["check", "ci"] %}'


def test_jinja_phony_list_omits_the_conditional_only_targets() -> None:
    lines = ['{%- set phony_targets = ["stale"] %}', "## Run it.", "ci: check"]
    targets = ["check", "ci", "run", "test-template"]

    updated = lint_makefile.update_jinja_phony(lines, targets)

    assert updated[0] == '{%- set phony_targets = ["check", "ci"] %}'
