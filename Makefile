.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
.PHONY: check clean help init sync test-template

UV ?= uv
VENV_DIR := .venv

## Show available commands.
help:
	@echo ""
	@echo "project_template"
	@echo ""
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Typical workflow:"
	@echo "  make init                     Set up the project and development environment"
	@echo "  make check                    Format and run quality checks"
	@echo "  make clean                    Remove build artifacts and untracked files"
	@echo ""
	@echo "All targets:"
	@awk '/^## / {desc=$$0; sub(/^## /,"",desc)} /^[a-zA-Z_-]+:/ {target=$$1; sub(/:$$/,"",target); printf "  %-28s %s\n", target, desc; desc=""}' $(MAKEFILE_LIST) | sort
	@echo ""

## Synchronize dependencies and install development tools.
sync: pyproject.toml
	$(UV) sync --group dev --quiet
	$(UV) run --quiet prek install

## Run code quality checks.
check:
	@$(UV) run --quiet python scripts/add_ruff_rule_links.py
	@$(UV) run --quiet python scripts/lint_makefile.py
	@$(UV) run --quiet python scripts/check.py --tool prek

## Remove build artifacts and untracked files (keeps the .venv folder and .env files).
clean:
	@$(UV) run --quiet python scripts/clean.py

## Initialize a Git repository, install dependencies, and create the initial commit.
init:
	@$(UV) run --quiet python scripts/init.py

## Test the Copier template by applying it to itself.
test-template:
	uvx --isolated --refresh --from copier@latest copier copy --defaults --overwrite --vcs-ref=HEAD . . --quiet
