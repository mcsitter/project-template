.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
.PHONY: check ci clean help init sync test-template

UV ?= uv

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
	@echo "  make ci                       Run the checks and the test suite"
	@echo "  make clean                    Remove build artifacts and untracked files"
	@echo ""
	@echo "All targets:"
	@awk '/^## / {desc=$$0; sub(/^## /,"",desc)} /^[a-zA-Z_-]+:/ && $$0 !~ /^[a-zA-Z_-]+:[[:space:]]*export/ {target=$$1; sub(/:$$/,"",target); printf "  %-28s %s\n", target, desc; desc=""}' $(MAKEFILE_LIST) | sort
	@echo ""

## Synchronize dependencies and install development tools.
sync: pyproject.toml
	$(UV) sync --group dev --quiet
	$(UV) run --quiet prek install

## Run code quality checks.
check:
	@$(UV) lock --check
	@$(UV) run --quiet python scripts/add_ruff_rule_links.py
	@$(UV) run --quiet python scripts/lint_makefile.py
	@$(UV) run --quiet python scripts/check.py

# Mark the commands below as running in CI so tools that adapt to it can tell.
# An existing CI value wins, so a provider's own setting is never overwritten.
## Run the checks and the test suite under coverage.
ci: export CI := $(if $(CI),$(CI),true)
ci: check
	@$(UV) run --quiet coverage run -m pytest -q
	@$(UV) run --quiet coverage report

## Remove build artifacts and untracked files (keeps the .venv folder and .env files).
clean:
	@$(UV) run --quiet python scripts/clean.py

## Initialize a Git repository, install dependencies, and create the initial commit.
init:
	@$(UV) run --quiet python scripts/init.py

## Re-apply the template to this repo, rewriting the files it generates.
test-template:
	uvx --isolated --refresh --from copier@latest copier copy . . --overwrite --vcs-ref=HEAD --quiet \
		--data project_name=project_template \
		--data project_type=package \
		--data project_description="A Python package that does things." \
		--data python_version=3.12 \
		--data with_conventional_commits=true \
		--data typing=false \
		--data is_template=true
