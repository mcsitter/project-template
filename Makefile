.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
.PHONY: check clean git help init test-template venv
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/python -m pip

help: ## Show available commands.
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS=":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
	@echo ""

check: $(VENV_DIR)/bin/prek ## Run code quality checks.
	$(VENV_PYTHON) -m prek run --all-files

venv: ## Create or update the virtual environment.
	rm -rf $(VENV_DIR)
	@$(MAKE) $(VENV_DIR)

$(VENV_DIR)/bin/%: $(VENV_DIR)
	@test -f $@ || (rm -rf $(VENV_DIR) && $(MAKE) $(VENV_DIR))

$(VENV_DIR): pyproject.toml
	rm -rf $(VENV_DIR)
	python -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip setuptools wheel
	$(VENV_PIP) install -e .[dev]
	$(VENV_PYTHON) -m prek install
	$(VENV_PYTHON) -m prek install --hook-type commit-msg commitizen
	$(VENV_PYTHON) -m prek autoupdate

clean: ## Remove untracked files (keeps the .venv folder and .env files).
	@FILES="$$(git clean -xdn \
		-e $(VENV_DIR)/ \
		-e '*.py' \
		-e .env )"; \
	if [ -z "$$FILES" ]; then \
		echo "Nothing to clean."; \
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

git:
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		echo "Git repository already exists."; \
	else \
		echo "Initializing git repository (master branch)..."; \
		git init -b master; \
	fi

init: git clean venv check ## Clean, install dependencies, and run checks.

test-template: $(VENV_DIR)/bin/copier ## Test the Copier template by applying it to itself.
	$(VENV_PYTHON) scripts/update_precommit_template.py || true
	$(VENV_PYTHON) -m copier copy --defaults --overwrite --vcs-ref=HEAD . .
