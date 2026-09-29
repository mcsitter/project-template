# project-template

A [Copier](https://copier.readthedocs.io/) template for Python projects.

Scaffold a project with a `pyproject.toml`, a `Makefile`, pre-commit hooks, a devcontainer, and editor settings already wired together.
Commit and push are always manual and always confirmed, so nothing leaves your machine unasked.

## Usage

```sh
uvx copier copy https://github.com/mcsitter/project-template.git my-project
cd my-project
make init
```

Copier asks for the project name, whether it is an `app` or a `package`, a one-line description, the minimum Python version, and whether to enable Conventional Commits and `mypy`.
To refresh an existing project after the template changes:

```sh
copier update
```

## What you get

- `make init` — install dependencies and create the initial commit
- `make check` — format and run quality checks (Ruff)
- `make ci` — run the checks and the test suite
- `make clean` — remove build artifacts and untracked files
- `make run` — apps only

The generated pre-commit config pulls two hooks from [`mcsitter/pre-commit-hooks`](https://github.com/mcsitter/pre-commit-hooks).
That repository must be public for generated projects to work.

## Working on the template

This repository is the template applied to itself, so it has the same targets plus `make test-template`, which re-runs Copier over the repo to check the template and its generated output agree.
`make ci` is what runs on every push.
