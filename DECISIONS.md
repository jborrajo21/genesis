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
## D-011: Genesis package layout

- **Options:** flat layout vs `src/` layout · hatchling vs setuptools
- **Choice:** `src/genesis/`, hatchling build backend, `requires-python = ">=3.11"`
- **Reason:** reuses the template's proven layout (D-002, D-007) so root CI covers
Genesis and the template the same way, and `src/` prevents the accidental
working-directory import that a flat layout allows — the failure mode the template's
tests exist to catch. Genesis-the-app has no reason to diverge from template-the-artefact
on packaging; one mental model for both.
- **Scope:** template-constant
- **Eval hook:** `pip install -e .` at repo root builds `genesis` in a fresh venv; `import genesis` succeeds; root CI runs Genesis's checks alongside the template's via `working-directory`
## D-012: Adapter interface via typing.Protocol

- **Options:** `typing.Protocol` (structural) · `abc.ABC` + `@abstractmethod` (nominal)
- **Choice:** `typing.Protocol`
- **Reason:** structural typing lets a provider adapter satisfy the interface without
importing or inheriting from Genesis core — any class with a matching `complete(...)`
conforms. This is exactly the Task 1 success criterion: the consumer never knows or
imports which provider answered. Cost accepted: conformance is checked statically
(type checker / editor), not enforced at runtime — a missing method surfaces at
type-check time, not as a loud instantiation error, unless `@runtime_checkable` is added.
- **Scope:** template-constant
- **Eval hook:** the interface module imports with no provider SDK present; `FakeAdapter` satisfies the Protocol without importing the Protocol class; a type check flags a non-conforming adapter
## D-013: Message and response shape

- **Options:** raw strings (`complete(str) -> str`) · list of role dicts · typed dataclasses
- **Choice:** typed `Message(role, content)` and `Completion(text, usage=None)` dataclasses
- **Reason:** the Block 3 agent loop needs multi-turn conversations and cost caps;
cost caps require token counts, so the response must carry metadata beyond text —
which rules out raw strings. A typed boundary keeps provider-shaped dicts from leaking
through the codebase: `Message`/`Completion` are Genesis's own types, so swapping
providers never changes the signature the agent sees. dataclasses give a generated
constructor, `__repr__`, and `__eq__` (the last makes them trivial to assert on) for
zero dependencies. `usage` is `int | None = None` — optional token count, defaulted.
- **Scope:** template-constant
- **Eval hook:** `Completion(text="x").usage is None`; `Completion(text="x") == Completion(text="x")` (dataclass equality); adapter signature is `complete(list[Message]) -> Completion` with no provider type in it
## D-014: FakeAdapter placement

- **Options:** in-package (`src/genesis/fakes.py`) · test-only (`tests/conftest.py`)
- **Choice:** in-package, `src/genesis/fakes.py`
- **Reason:** a deterministic, zero-network adapter is reusable infrastructure, not a
test artefact — the Block 6 eval harness and the agent loop's own tests will want it
too, so it earns a place in the package rather than being trapped in `tests/`. It
imports the data types (`Message`, `Completion`) it constructs, but NOT the
`ModelAdapter` Protocol — conformance is structural (D-012).
- **Scope:** template-constant
- **Eval hook:** `from genesis.fakes import FakeAdapter` works from the installed package; `fakes.py` does not import `ModelAdapter`; `FakeAdapter(reply="x").complete([]).text == "x"`
## D-015: Scope root pytest collection to tests/

- **Options:** `testpaths = ["tests"]` in root pyproject · install `greetly` into the Genesis env · `--ignore`/`norecursedirs` blocklist
- **Choice:** `[tool.pytest.ini_options] testpaths = ["tests"]` in the root `pyproject.toml`
- **Reason:** the repo holds two independent packages (`genesis` at root, `greetly`
under `templates/`); bare `pytest` from root discovers both test trees, but the Genesis
env only installs `genesis`, so the template's imports fail during collection. Each
package must test itself in its own environment — the template's tests run under its
own CI job via `working-directory` (D-001). Allowlist (`testpaths`) over blocklist
(`--ignore`): state what to include, not what to avoid. Installing `greetly` into the
Genesis env is rejected — the template is a generated artefact, not a Genesis dependency.
NOTE: this is the config Phase 0 deliberately deferred until an observed constraint
demanded it (see the D-005 area) — it is now added against a real collection failure,
not speculatively.
- **Scope:** template-constant
- **Eval hook:** bare `pytest` from repo root collects only `tests/` and passes with only `genesis` installed; the template's tests are never collected by the root run
## D-016: First real provider — Anthropic

- **Options:** Anthropic first · OpenAI first · defer
- **Choice:** Anthropic
- **Reason:** the owner holds an Anthropic API key with credit in hand; the adapter
interface is the deliverable and either provider proves it equally, so the choice is
driven purely by which key is available now. Cost of live testing is bounded by using
the cheapest model tier, low `max_tokens`, and tiny prompts on manual runs only — the
automated suite never calls the API (it runs against `FakeAdapter`), so credit is not
spent by CI or by `pytest`.
- **Scope:** render-variable (adapter identity; a second provider is an October extension)
- **Eval hook:** with `ANTHROPIC_API_KEY` set, a manual smoke call returns a real `Completion`; with the key absent, that test skips and the suite still passes
## D-017: Provider SDK lives in an optional extra, not core dependencies

- **Options:** `anthropic` in `dependencies` · in `[project.optional-dependencies]` · raw HTTP with no SDK
- **Choice:** official `anthropic` SDK, declared in `[project.optional-dependencies]` (e.g. `anthropic = ["anthropic"]`); installed via `pip install "genesis[anthropic]"`
- **Reason:** putting the SDK in core `dependencies` would break the D-012 invariant
that Genesis core imports with no provider SDK present — the whole point of the adapter
seam. An optional extra keeps `pip install genesis` SDK-free while `genesis[anthropic]`
opts in. Official SDK over raw HTTP because it handles auth, retries, response parsing,
and API versioning, keeping the adapter a thin mapping rather than hand-rolled request
code — right trade for a piece meant to last. Consequence: the adapter module imports
`anthropic` at module load, so it must NOT be imported by `genesis` core or anything on
the core import path; only code that has opted into the extra may import it.
- **Scope:** template-constant
- **Eval hook:** `pip install genesis` (no extra) still imports `genesis.adapter` with no `anthropic` present; `pip install "genesis[anthropic]"` makes `import anthropic` succeed; `genesis.adapter`/core never imports the provider adapter module
## D-018: Live provider smoke test skips without a key

- **Options:** run the live API call in CI · skip the smoke test when no key is present · no live test at all
- **Choice:** a single smoke test decorated with `@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), ...)`; CI never sets the key
- **Reason:** the eval surface must stay deterministic and secret-free — CI must not depend on provider uptime, cost credit, or a stored secret. The `FakeAdapter` unit tests already give full offline coverage of the interface; the live smoke test only proves the real provider wiring, so it runs when a developer explicitly exports a key and skips otherwise. Gating on the `ANTHROPIC_API_KEY` env var (not an OAuth profile or a credit check) is a deliberately simple, explicit "I have API access" signal. This is the concrete form of the plan's honest-limitations principle: Genesis builds and passes CI with no provider access.
- **Scope:** template-constant
- **Eval hook:** bare `pytest` with no `ANTHROPIC_API_KEY` reports the smoke test as skipped and the suite stays green; with a funded key exported, the smoke test runs and returns a real `Completion`
## D-019: Pin the ruff ruleset, not the ruff version

- **Options:** fix code and keep inheriting ruff's implicit defaults · pin the ruff version in the dev extra · pin the ruleset via explicit `[tool.ruff.lint] select`
- **Choice:** explicit `[tool.ruff.lint]` with `select = ["E", "F", "I"]` in both the template and root `pyproject.toml`; ruff itself stays unpinned (D-004 intact)
- **Reason:** a green build broke with zero code change when unpinned ruff (D-004) upgraded from a defaults set of `E,F` to one that also enforced `I001` and `PLW1510` — the exact reproducibility risk D-004 accepted. Pinning the *ruleset* rather than the *version* fixes the actual cause (inheriting ruff's implicit, drifting defaults) while keeping generated repos on current ruff: a future ruff release can no longer spontaneously add rules and fail CI. Making the lint contract explicit is correct for an eval surface — the harness must enforce a known, stable set, not "whatever ruff defaults to this month." `I` (import sorting) is kept because it is genuinely useful and auto-fixable; `PLW1510` is dropped by not selecting `PL`.
- **Scope:** template-constant
- **Eval hook:** `ruff check .` result is independent of the installed ruff version (a newer ruff cannot add enforced rules); `ruff check .` passes on both the template and root after import sorting; `select` present in both pyprojects
## D-020: Tool-use representation in the adapter interface

- **Options:** one "fat" `Message` with optional tool fields · a union of distinct message types (`TextMessage`/`ToolCallMessage`/`ToolResultMessage`)
- **Choice:** fat `Message`. Tool definitions enter `complete(messages, tools)` as `ToolDef(name, description, input_schema)`; tool calls leave in `Completion.tool_calls` as `ToolCall(id, name, arguments)`; a tool-result turn is `Message(role="tool", content=..., tool_call_id=...)`; an assistant tool-request turn is `Message(role="assistant", tool_calls=[...])`. No `stop_reason` field — the loop derives done-ness from whether `tool_calls` is empty.
- **Reason:** minimalism — one message type with defaulted fields keeps every consumer touching a single shape; a union would triple the surface for marginal cleanliness. The `id`/`tool_call_id` pairing is the load-bearing part of the protocol: one assistant turn fans out to N `ToolCall`s, and each result message answers exactly one via its `tool_call_id`. `stop_reason` is omitted as speculative surface — nothing needs it while `tool_calls` presence is the termination signal; it is a one-line add later if a guardrail must distinguish "finished" from "hit max_tokens." `tools` defaults to `None` and `content` to `""`, preserving every existing no-tool call site. Provider-specific batching (Anthropic wants multiple `tool_result` blocks in one user message) is hidden in the adapter, not the interface.
- **Scope:** template-constant
- **Eval hook:** `genesis.adapter` imports with no provider SDK; a `Message(role="assistant", tool_calls=[ToolCall(...)])` and a `Message(role="tool", tool_call_id=...)` construct and round-trip; existing no-tool tests still pass unchanged
## D-021: Executable tools live in genesis/tools.py, composing ToolDef

- **Options:** new `genesis/tools.py` (a `Tool` composing `ToolDef` + a callable, plus a registry) · put `Tool` in `adapter.py` next to `ToolDef` · `Tool` re-declaring name/description/schema instead of composing `ToolDef`
- **Choice:** new `src/genesis/tools.py`. `Tool` = `ToolDef` (the wire definition) + `func: Callable[..., str]` (the executable body). A `ToolRegistry` maps tool name → `Tool` and exposes `definitions()` (the `ToolDef`s, for the adapter to send the model) and `run(name, arguments)` (looks up the callable and executes it, for the loop). Trivial example tools live here too for now.
- **Reason:** layering — `adapter.py` is the provider-neutral wire boundary and must have no notion that tools can be *executed* (no callables); an executable `Tool` is an agent-side concept one layer up, so it belongs in its own module that depends *down* on `adapter.py`, never up. Composing `ToolDef` (rather than duplicating its three fields) keeps a single source of truth for name/description/schema. The registry's two methods serve two different consumers — the adapter *describes* tools to the model, the loop *executes* them — which is the "model asks / your code runs" split made concrete. `func` returns `str` because a tool result is text that goes back into a `Message` and then to the model.
- **Scope:** template-constant
- **Eval hook:** `ToolRegistry([...]).run(name, args)` executes the callable and returns its string result; `definitions()` returns the `ToolDef`s; `tools.py` imports only from `genesis.adapter` (no provider SDK); a tool's `func` is importable and unit-testable without the loop
## D-022: Agent guardrails and stop signalling

- **Options for the stop signal:** return a plain string · raise an exception on a cap · return a structured `AgentResult(text, stop_reason)`
- **Choice:** structured `AgentResult(text: str, stop_reason: Literal["done", "max_turns", "budget"])`. Guardrails: `max_turns` expressed as `for _ in range(max_turns)` (structural termination); a `token_budget` accumulated from each `Completion.usage` and checked after every turn. Order: the `done` check precedes the `budget` check.
- **Reason:** "why did you stop" is load-bearing for an agent — the caller, and later the Block 6 eval harness, must distinguish "the model answered" from "we cut it off at a cap". A bare string conflates the two (a real answer could read like a timeout message); an exception forces `try/except` around a normal, expected outcome. `done` is checked before `budget` so a completed answer is never discarded to a spend limit — the budget bounds *future* spend, not an answer already in hand. `completion.usage or 0` keeps the accumulator `None`-safe; tracking `last_text` (not `completion`) makes the `max_turns`-exhausted return safe even for `max_turns=0`. The caps exist to stop a malfunctioning or looping agent from running forever or draining usage.
- **Scope:** template-constant
- **Eval hook:** a fake scripted to always request a tool returns `stop_reason="max_turns"`; a fake whose `usage` exceeds a small `token_budget` returns `stop_reason="budget"`; a normal completion returns `stop_reason="done"`; the loop provably cannot exceed `max_turns` iterations or `token_budget` tokens
## D-023: Multiple tool calls in one turn run sequentially

- **Options:** execute a turn's tool calls sequentially in loop order, each result its own message · execute them concurrently (async)
- **Choice:** sequential. The loop iterates `for call in completion.tool_calls`, dispatches each to the registry by name, and appends each result as its own `Message(role="tool", tool_call_id=...)`. The adapter batches consecutive `tool` messages into one provider user message (D-020).
- **Reason:** minimalism and determinism — sequential execution needs no concurrency machinery and gives repeatable, testable ordering; the registry's name→callable dispatch already routes each call to the correct tool, so several distinct tools in one turn work with no extra code. One-result-per-message keeps the interface uniform (D-020) with provider-specific batching hidden in the adapter. Async/concurrent tool execution is explicitly out of Phase 2 scope.
- **Scope:** template-constant
- **Eval hook:** a completion carrying two `ToolCall`s for different tools (e.g. `add` and `multiply`) in one turn executes both and feeds both results back, each tagged with its own `tool_call_id`