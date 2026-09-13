# greetly

A tiny greeting CLI.

## Install

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"

## Usage

    greetly greet <name>
    greetly --help

## Test

    ruff check . && ruff format --check . && pytest
