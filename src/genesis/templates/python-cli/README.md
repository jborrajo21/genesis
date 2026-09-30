# greetly

Describe your project here. `PLAN.md` holds the plan this repo was generated from.

## Install

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"

## Usage

    greetly run <target>
    greetly --help

## Where to start

`src/greetly/core.py` holds a placeholder `run()`. Replace it with the real
behaviour, then update `tests/test_core.py`. `cli.py` maps `AppError` to exit
code 1 and `KeyboardInterrupt` to 130 — raise `AppError` for anything a user
could reasonably cause, and it is reported on stderr.

This directory is not a git repository yet — a `.gitignore` is included, but
nothing is tracked until you run:

    git init && git add . && git commit -m "Initial commit"

## Licence

No `LICENSE` file is included, which legally means all rights reserved. If you
intend to publish or share this, add one — MIT is the usual choice for a small
tool. The choice is deliberately left to you.

## Test

    ruff check . && ruff format --check . && mypy && pytest
