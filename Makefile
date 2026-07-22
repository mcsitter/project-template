.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
.PHONY: check clean clean-generated git help init test-template venv

VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/python -m pip

## Show available commands.
help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@awk '/^## / {desc=$$0; sub(/^## /,"",desc)} /^[a-zA-Z_-]+:/ {target=$$1; sub(/:$$/,"",target); printf "  %-16s %s\n", target, desc; desc=""}' $(MAKEFILE_LIST) | sort
	@echo ""

## Run code quality checks.
check: $(VENV_DIR)/bin/prek
	$(VENV_PYTHON) -m prek run --all-files

## Create or update the virtual environment.
venv:
	rm -rf $(VENV_DIR)
	@$(MAKE) $(VENV_DIR)

$(VENV_DIR)/bin/%:
	@test -f $@ || $(MAKE) venv

$(VENV_DIR): pyproject.toml
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		python -m venv $(VENV_DIR); \
	fi
	$(VENV_PIP) install --upgrade pip setuptools wheel
	$(VENV_PIP) install -e .[dev]
	$(VENV_PYTHON) -m prek install
	$(VENV_PYTHON) -m prek install --hook-type commit-msg commitizen
	$(VENV_PYTHON) -m prek autoupdate
	touch $@

## Update project files from the Copier template.
copier-update: $(VENV_DIR)/bin/copier
	$(VENV_PYTHON) -m copier update

## Remove generated files and untracked files (keeps the .venv folder and .env files).
clean: clean-generated
	@FILES="$$(git clean -xdn \
		-e $(VENV_DIR)/ \
		-e '*.py' \
		-e .env )"; \
	if [ -z "$$FILES" ]; then \
		echo "Nothing else to clean."; \
	else \
		printf "%s\n" "$$FILES"; \
		read -p "Delete these files? [y/N] " ANSWER; \
		if [ "$$ANSWER" = "y" ] || [ "$$ANSWER" = "Y" ]; then \
			git clean -xd -f \
				-e $(VENV_DIR)/ \
				-e '*.py' \
				-e .env ; \
		fi \
	fi

## Remove generated Python artifacts.
clean-generated:
	@find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@rm -rf \
		.mypy_cache \
		.ruff_cache

## Initialize a Git repository.
git:
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		echo "Git repository already exists."; \
	else \
		echo "Initializing git repository (main branch)..."; \
		git init -b main; \
	fi

## Clean, install dependencies, and run checks.
init: git clean venv check

## Test the Copier template by applying it to itself.
test-template: $(VENV_DIR)/bin/copier
	$(VENV_PYTHON) scripts/update_precommit_template.py || true
	$(VENV_PYTHON) -m copier copy --defaults --overwrite --vcs-ref=HEAD . .
