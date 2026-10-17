.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory
.PHONY: build cd check ci clean help init install test test-template

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
	@echo "  make install                  Install development dependencies"
	@echo "  make check                    Validate code"
	@echo "  make test                     Run tests"
	@echo "  make build                    Build wheel/sdist"
	@echo "  make ci                       check + test + build"
	@echo "  make cd                       Publish package"
	@echo "  make clean                    Remove build artifacts"
	@echo ""
	@echo "All targets:"
	@awk '/^## / {desc=$$0; sub(/^## /,"",desc)} /^[a-zA-Z_-]+:/ && $$0 !~ /^[a-zA-Z_-]+:[[:space:]]*export/ {target=$$1; sub(/:$$/,"",target); printf "  %-28s %s\n", target, desc; desc=""}' $(MAKEFILE_LIST) | sort
	@echo ""

## Install dependencies and the development tools.
install: pyproject.toml
	$(UV) sync --group dev --quiet
	$(UV) run --quiet prek install

## Validate code.
check:
	@$(UV) lock --check
	@$(UV) run --quiet python scripts/add_ruff_rule_links.py
	@$(UV) run --quiet python scripts/lint_makefile.py
	@$(UV) run --quiet python scripts/check.py

## Run tests.
test:
	@$(UV) run --quiet pytest -q

## Build wheel/sdist.
build:
	$(UV) build

# Mark the commands below as running in CI so tools that adapt to it can tell.
# An existing CI value wins, so a provider's own setting is never overwritten.
## Run check + test + build.
ci: export CI := $(if $(CI),$(CI),true)
ci: check test build

## Deploy application (app) or publish package (package).
cd: build
	@echo "Publish not configured. Add your publish steps here."
	@echo "Example: uv publish"

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
