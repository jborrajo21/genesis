# Decisions

<!--      DECISIONS TEMPLATE

## D-00X: <decision topic>
- **Options:** <alternative A> · <alternative B> · <alternative C>
- **Choice:** <the answer>
- **Reason:** <constraint- or cost-based justification, 1–3 sentences>
- **Scope:** template-constant | render-variable
- **Eval hook:** <command + expected outcome> | none — <why not checkable>
-->

## D-001: Template location

- **Options:** standalone `genesis-cli-template` repo · vendored inside Genesis at `templates/python-cli/`
- **Choice:** vendored inside Genesis (`templates/python-cli/`)
- **Reason:** the scaffolder reads the template from the local filesystem at
generation time — vendoring removes a cross-repo fetch/sync problem and keeps
one commit graph, which is itself part of the Sept 1 signal. Cost accepted:
template gets no independent CI badge and isn't separately clonable; its
correctness is only visible through Genesis's eval numbers in the README.
- **Scope:** template-constant
- **Eval hook:** `templates/python-cli/` exists; root CI workflow runs the
template's install/lint/test steps via `working-directory` and is green


## D-002: Build backend
- **Options:** hatchling · setuptools
- **Choice:** hatchling
- **Reason:** zero-config auto-discovery of `src/<pkg>/` when the directory name
matches `project.name` — fewer lines the scaffolder must generate and verify.
Cost accepted: the name↔directory coupling means Block 5 must rename both together.
- **Scope:** template-constant
- **Eval hook:** `pip install -e .` builds in a fresh venv with no backend config beyond `[build-system]`

## D-003: Runtime dependencies 
- **Options:** empty · click/typer for CLI ergonomics · rich for output
- **Choice:** `dependencies = []` — zero runtime deps
- **Reason:** every template dep is inherited by every repo Genesis ever generates;
stdlib does everything this skeleton needs. Generated repos install instantly and
can't hit dependency conflicts. Note for October: if the planner ever adds deps
per project, this flips to render-variable — parked, not built.
- **Scope:** template-constant
- **Eval hook:** generated `pyproject.toml` contains `dependencies = []`; `pip install .` in a clean venv pulls nothing beyond the package itself

## D-004: Dev dependencies — selection and pinning 
- **Options:** pinned versions · unpinned · no dev extra (global tools)
- **Choice:** `dev = ["pytest", "ruff"]`, unpinned, as a `[project.optional-dependencies]` extra
- **Reason:** the template should get current tooling at generation time; pins ship
stale versions into every generated repo and create an update burden Genesis can't
service. Counterargument acknowledged: reproducibility — accepted risk at this size.
Extra (not runtime deps) keeps the install footprint at zero.
- **Scope:** template-constant
- **Eval hook:** `pip install -e ".[dev]"` succeeds; `pytest` and `ruff` on PATH afterwards; plain `pip install .` does NOT install them

## D-005: Tool configuration location 
- **Options:** `pyproject.toml` `[tool.*]` tables · separate files (`ruff.toml`, `pytest.ini`)
- **Choice:** everything in `pyproject.toml`
- **Reason:** one file carries the whole project contract — fewer files for the
scaffolder to generate and the eval to verify. Config stays minimal: every line is
generation + eval surface.
- **Scope:** template-constant
- **Eval hook:** no `ruff.toml`/`pytest.ini`/`setup.cfg` in the generated repo; `ruff check .` and bare `pytest` still work

## D-006: Ruff line length 
- **Options:** 88 (ruff default) · 100 · 120
- **Choice:** 100
- **Reason:** genuine style choice with no strong constraint — 88 forces awkward
wraps in CLI help strings; 120 invites long lines. Decided once here so the
scaffolder never has to reason about it.
- **Scope:** template-constant
- **Eval hook:** `ruff format --check .` passes on the generated repo with `line-length = 100` present

## D-007: Python version floor 
- **Options:** `>=3.9` · `>=3.11` · `>=3.12`
- **Choice:** `requires-python = ">=3.11"`
- **Reason:** sane 2026 floor; claims must match verification — CI runs one Python
version, so the floor is set to exactly what CI tests. Claiming older support the
eval never exercises would be dishonest surface.
- **Scope:** template-constant
- **Eval hook:** CI workflow's Python version satisfies `requires-python`; install fails cleanly on an older interpreter

## D-008: Versioning scheme 
- **Options:** hardcoded `0.1.0` · dynamic (git-tag/VCS-based)
- **Choice:** hardcoded `version = "0.1.0"`
- **Reason:** dynamic versioning is release machinery a starter template doesn't
need; every generated project reasonably begins at 0.1.0. Zero config, zero
failure modes.
- **Scope:** template-constant
- **Eval hook:** `pip show <pkg>` reports 0.1.0 after install

## D-009: Render-variable set for pyproject 
- **Options:** none — falls out of D-002/D-003 and the entry-point mechanism
- **Choice:** exactly three substitution sites: `name`, `description`, and the
`[project.scripts]` table (key + import path)
- **Reason:** these are the only values that change per generated project. `name`
is coupled to the `src/` directory name, the scripts import path, and test imports —
the four must be renamed atomically, which IS the Block 5 rename operation.
Everything else in the file is frozen (D-002–D-008).
- **Scope:** render-variable
- **Eval hook:** generated repo for project "X": `name = "x"`, `src/x/` exists, command `x` on PATH after install, `pytest` imports succeed
## D-010: CLI argument-parsing library

- **Options:** argparse (stdlib) · click · typer
- **Choice:** argparse
- **Reason:** forced by D-003 — click and typer are runtime dependencies, and the
template ships `dependencies = []`; every template dep would be inherited by every
generated repo. Cost accepted: plain help/error output, no shell completion, no
in-process test runner (CLI tests go through `subprocess` instead, which exercises
the real entry point anyway).
- **Scope:** template-constant
- **Eval hook:** `dependencies = []` still holds in the generated pyproject; `<tool> --help` exits 0 using only stdlib imports