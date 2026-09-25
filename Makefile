.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
.PHONY: check clean clean-generated clean-venv git help init sync test-template

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
	@echo ""
	@echo "Scripts:"
	@echo "  $(UV) run python scripts/update_from_template.py"
	@echo "  $(UV) run python scripts/update_github_metadata.py"
	@echo "  $(UV) run python scripts/update_precommit_hooks.py"
	@echo "  $(UV) run python scripts/update_vscode_extensions.py"
	@echo ""
	@echo "All targets:"
	@awk '/^## / {desc=$$0; sub(/^## /,"",desc)} /^[a-zA-Z_-]+:/ {target=$$1; sub(/:$$/,"",target); printf "  %-28s %s\n", target, desc; desc=""}' $(MAKEFILE_LIST) | sort
	@echo ""

## Synchronize dependencies and install development tools.
sync: pyproject.toml
	$(UV) sync --group dev --quiet
	$(UV) run --quiet prek install

## Remove the virtual environment.
clean-venv:
	@if [ -d "$(VENV_DIR)" ]; then \
		rm -rf "$(VENV_DIR)"; \
	else \
		echo "Virtual environment does not exist."; \
	fi

## Run code quality checks.
check:
	@$(UV) run --quiet prek run ruff-format --all-files >/dev/null 2>&1 || echo "ruff-format updated files"
	@$(UV) run --quiet python scripts/add_ruff_rule_links.py
	@$(UV) run --quiet python scripts/lint_makefile.py
	@LOG=$$(mktemp); \
	if $(UV) run --quiet prek run --all-files >"$$LOG" 2>&1; then \
		rm -f "$$LOG"; \
	else \
		cat "$$LOG"; \
		rm -f "$$LOG"; \
		exit 1; \
	fi
	@echo "Quality checks passed."

## Remove generated files and untracked files (keeps the .venv folder and .env files).
clean: clean-generated
	@FILES="$$(git clean -xdn \
		-e $(VENV_DIR)/ \
		-e '*.py' \
		-e .env* )"; \
	if [ -z "$$FILES" ]; then \
		echo "Nothing else to clean."; \
	else \
		printf "%s\n" "$$FILES"; \
		read -p "Delete these files? [y/N] " ANSWER; \
		if [ "$$ANSWER" = "y" ] || [ "$$ANSWER" = "Y" ]; then \
			git clean -xd -f \
				-e $(VENV_DIR)/ \
				-e '*.py' \
				-e .env* ; \
		fi \
	fi

## Remove generated Python artifacts.
clean-generated:
	@find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find . -type d -name ".import_linter_cache" -prune -exec rm -rf {} +
	@rm -rf \
		build \
		dist \
		.mypy_cache \
		.pytest_cache \
		.ruff_cache

## Initialize a Git repository.
git:
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		echo "Git repository already exists."; \
	else \
		echo "Initializing git repository (main branch)..."; \
		git init -b main; \
	fi

## Initialize the project, install dependencies, run checks, and create the initial commit.
init:
	@$(MAKE) git
	@$(MAKE) sync
	@$(MAKE) check
	@$(UV) run --quiet python scripts/update_github_metadata.py
	@INITIAL_COMMIT=0; \
	if ! git rev-parse --verify HEAD >/dev/null 2>&1; then \
		git add -A; \
		if git diff --cached --quiet; then \
			echo "Nothing to commit."; \
		else \
			echo ""; \
			echo "Initial commit:"; \
			git diff --cached --stat; \
			echo ""; \
			read -p "Commit initial project? [y/N] " ANSWER; \
			if [ "$$ANSWER" = "y" ] || [ "$$ANSWER" = "Y" ]; then \
				git commit -m "chore: initialize project"; \
				INITIAL_COMMIT=1; \
			else \
				echo "Initial commit skipped."; \
			fi; \
		fi; \
	fi; \
	if [ "$$INITIAL_COMMIT" = "1" ] && git remote get-url origin >/dev/null 2>&1; then \
		echo "Pushing initial commit..."; \
		git push -u origin "$$(git branch --show-current)"; \
	fi
	@$(UV) run --quiet python scripts/update_vscode_extensions.py

## Test the Copier template by applying it to itself.
test-template:
	uvx --isolated --refresh --from copier@latest copier copy --defaults --overwrite --vcs-ref=HEAD . . --quiet
