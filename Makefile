.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
.PHONY: check clean clean-generated clean-venv git help init sync test-template update-from-template update-github update-pre-commit-hooks vscode-extensions

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
	@echo "Maintenance:"
	@echo "  make update-from-template     Update files from the project template"
	@echo "  make update-github            Update GitHub repository metadata"
	@echo "  make update-pre-commit-hooks  Update pre-commit hook versions"
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

## Update project files from the template.
update-from-template:
	@if ! git diff --quiet || ! git diff --cached --quiet; then \
		echo "Git tree is not clean. Commit or stash changes first."; \
		exit 1; \
	fi
	$(UV) run --quiet copier update --defaults --quiet
	@if ! git diff --quiet; then \
		git diff --check; \
		if [ $$? -eq 0 ]; then \
			git add -A && git commit -m "chore: update from template"; \
		else \
			echo "Resolve merge conflicts, then commit with:"; \
			echo "  git add -A && git commit -m \"chore: update from template\""; \
			exit 1; \
		fi; \
	fi

## Update pre-commit hook versions, validate, and commit changes.
update-pre-commit-hooks:
	@if ! git diff --quiet || ! git diff --cached --quiet; then \
		echo "Git tree is not clean. Commit or stash changes first."; \
		exit 1; \
	fi; \
	$(UV) run --quiet python scripts/update_precommit_template.py || true; \
	$(UV) run --quiet prek autoupdate; \
	if git diff --quiet -- .pre-commit-config.yaml template/.pre-commit-config.yaml.jinja; then \
		echo "No pre-commit updates available."; \
		exit 0; \
	fi; \
	echo ""; \
	echo "Changes:"; \
	git --no-pager diff --unified=0 -- .pre-commit-config.yaml template/.pre-commit-config.yaml.jinja; \
	echo ""; \
	echo "Running checks..."; \
	CHECK_LOG=$$(mktemp); \
	if ! $(MAKE) check >"$$CHECK_LOG" 2>&1; then \
		echo "Checks failed:"; \
		cat "$$CHECK_LOG"; \
		rm -f "$$CHECK_LOG"; \
		exit 1; \
	fi; \
	rm -f "$$CHECK_LOG"; \
	echo "Checks passed."; \
	echo ""; \
	read -r -p "Commit these changes? [y/N] " ANSWER; \
	if [ "$$ANSWER" = "y" ] || [ "$$ANSWER" = "Y" ]; then \
		git add .pre-commit-config.yaml template/.pre-commit-config.yaml.jinja && \
		git commit -m "chore: update pre-commit hooks"; \
	else \
		echo "Aborted."; \
	fi

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

## Update GitHub repository metadata from project configuration.
update-github:
	@if command -v gh >/dev/null 2>&1; then \
		if ! gh auth status >/dev/null 2>&1; then \
			echo "GitHub CLI is not authenticated; skipping GitHub update."; \
		elif [ ! -f .copier-answers.yml ]; then \
			echo ".copier-answers.yml not found; skipping GitHub update."; \
		else \
			name="$$(awk '/^project_name:/ {sub(/^project_name: /, ""); print}' .copier-answers.yml | tr '[:upper:]' '[:lower:]' | tr ' _' '--')"; \
			owner="$$(gh api user --jq '.login')"; \
			repo="$$owner/$$name"; \
			description="$$(awk '/^project_description:/ {sub(/^project_description:/, ""); print}' .copier-answers.yml)"; \
			if gh repo view "$$repo" >/dev/null 2>&1; then \
				echo "Updating GitHub repository metadata..."; \
				gh repo edit "$$repo" \
					--description "$$description"; \
			else \
				echo "Creating GitHub repository..."; \
				gh repo create "$$repo" \
					--private \
					--description "$$description" \
					--source . \
					--remote origin; \
			fi; \
		fi; \
	else \
		echo "GitHub CLI (gh) not available; skipping GitHub update."; \
	fi

## Initialize the project, install dependencies, run checks, and create the initial commit.
init:
	@$(MAKE) git
	@$(MAKE) sync
	@$(MAKE) check
	@$(MAKE) update-github
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
	$(MAKE) vscode-extensions

## Test the Copier template by applying it to itself.
test-template:
	$(UV) run --quiet copier copy --defaults --overwrite --vcs-ref=HEAD . . --quiet

## Install missing VS Code extensions.
vscode-extensions:
	@if [ "$${TERM_PROGRAM:-}" = "vscode" ]; then \
		installed="$$(code --list-extensions)"; \
		missing="$$(jq -r '.recommendations[]' .vscode/extensions.json | while read -r extension; do \
			if ! printf '%s\n' "$$installed" | grep -ixq "$$extension"; then \
				echo "$$extension"; \
			fi; \
		done)"; \
		if [ -z "$$missing" ]; then \
			echo "All recommended VS Code extensions are already installed"; \
			exit 0; \
		fi; \
		echo "Missing VS Code extensions:"; \
		printf '%s\n' "$$missing"; \
		if [ -t 0 ]; then \
			printf "Install missing extensions? [y/N] "; \
			read -r answer; \
			case "$$answer" in \
				y|Y|yes|YES) ;; \
				*) echo "Skipping VS Code extensions"; exit 0 ;; \
			esac; \
		else \
			echo "Running non-interactively, installing extensions"; \
		fi; \
		printf '%s\n' "$$missing" | while read -r extension; do \
			echo "Installing VS Code extension: $$extension"; \
			code --install-extension "$$extension"; \
		done; \
	else \
		echo "Not running inside VS Code, skipping extensions"; \
	fi
