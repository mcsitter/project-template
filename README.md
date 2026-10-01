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

## The development environment

`make init` (or `make sync`) creates a virtualenv in `.venv` with [uv](https://docs.astral.sh/uv/).
Every Makefile target goes through `uv run`, so you never have to activate it.

If you do want a shell inside the virtualenv, `activate` has to be sourced, not executed:

```sh
source .venv/bin/activate
```

Running `./.venv/bin/activate` instead reports `Permission denied`.
That is intentional: the file only exports shell variables, and it is not marked executable.

## Maintenance scripts

`python3 scripts/` lists the maintenance scripts with a one-line summary of each.
The two you are most likely to reach for:

```sh
uv run python scripts/update_precommit_hooks.py   # bump hook revisions, then commit
uv run python scripts/update_from_template.py     # pull template changes into a generated project
```

In the template repository the hook updater also patches
`template/.pre-commit-config.yaml.jinja`, because `make test-template` re-renders
`.pre-commit-config.yaml` from that template, so a bump that skipped it would be
reverted on the next run.
In a generated project there is no template, so only the config is touched.

Makefile targets do not forward arguments to the scripts they wrap, so `make init -- --yes`
fails with `No rule to make target '--yes'`.
Reach the flags by calling the script:

```sh
uv run python scripts/init.py --yes
```

`scripts/check.py` backs `make check`.
It takes `--verbose` to stream hook output rather than print it only on failure, and one extra
command to run once the hooks have settled:

```sh
uv run python scripts/check.py -- uv lock --check
```

## Working on the template

This repository is the template applied to itself, so it has the same targets plus
`make test-template`, which re-applies the template over the repo with Copier.
Run it after changing anything under `template/`: it should leave the working tree clean, and
any diff it leaves behind is drift between the template and its own generated output.
`make ci` is what runs on every push.

`uv.lock` and `src/` are gitignored here, because Copier regenerates both and the template's
own generated output is not meant to be tracked.
A fresh clone therefore has no lockfile, so run `make sync` once before `make check` or
`make ci`, which fail on a missing `uv.lock`.

The template switches on its own extra targets, scripts, and coverage settings through a hidden
`is_template` copier question rather than by comparing the project name.
`make test-template` passes `--data is_template=true`; every other copy gets `false`.
A name comparison would collide, because "Project Template" and "project_template" snake-case
to the same value.

CI scaffolds a project for every combination of app or package, Conventional Commits, and
mypy, then runs the pre-commit hooks in it.
It does not run the generated project's `make check` or `make ci`, so the generated Makefile
is only verified by `make test-template` locally.
