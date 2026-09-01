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
- **`token_budget` is a soft, forward-looking cap, not a hard ceiling.** It is checked only when the model wants to continue (the completion has tool calls), so it prevents the *next* round rather than truncating the current one. Because a turn's token cost is unknown until the call returns, cumulative usage can **overshoot the budget by up to one turn's worth**. And since `done` is checked first, a completion that produces a *final answer* on the turn that crosses the budget still reports `stop_reason="done"` (the answer is kept), not `"budget"`. A hard pre-emptive cap would require estimating each call's cost with `count_tokens` before making it — an extra round-trip per turn, not worth it here. This is an honest limitation to surface in the README.
- **Scope:** template-constant
- **Eval hook:** a fake scripted to always request a tool returns `stop_reason="max_turns"`; a fake whose `usage` exceeds a small `token_budget` (while still requesting a tool) returns `stop_reason="budget"`; a normal completion returns `stop_reason="done"`; the loop provably cannot exceed `max_turns` iterations, though cumulative usage may exceed `token_budget` by up to one turn's usage, and a final-answer turn that crosses the budget reports `done`
## D-023: Multiple tool calls in one turn run sequentially

- **Options:** execute a turn's tool calls sequentially in loop order, each result its own message · execute them concurrently (async)
- **Choice:** sequential. The loop iterates `for call in completion.tool_calls`, dispatches each to the registry by name, and appends each result as its own `Message(role="tool", tool_call_id=...)`. The adapter batches consecutive `tool` messages into one provider user message (D-020).
- **Reason:** minimalism and determinism — sequential execution needs no concurrency machinery and gives repeatable, testable ordering; the registry's name→callable dispatch already routes each call to the correct tool, so several distinct tools in one turn work with no extra code. One-result-per-message keeps the interface uniform (D-020) with provider-specific batching hidden in the adapter. Async/concurrent tool execution is explicitly out of Phase 2 scope.
- **Scope:** template-constant
- **Eval hook:** a completion carrying two `ToolCall`s for different tools (e.g. `add` and `multiply`) in one turn executes both and feeds both results back, each tagged with its own `tool_call_id`
## D-024: AgentResult exposes per-run telemetry (tool calls, usage, turns)

- **Options:** expose a bounded set of scalar/telemetry fields on `AgentResult` (`tool_calls`, `usage`, `turns`) · a full transcript (calls + results, or the whole message list) · only `print()` in the loop
- **Choice:** `AgentResult` carries three telemetry fields alongside `text`/`stop_reason`, all computed in `run()` and defaulted: `tool_calls: list[ToolCall]` (executed calls, in order), `usage: int` (cumulative input+output tokens), `turns: int` (loop iterations taken). This is treated as the closed telemetry set — richer detail would come from a transcript, not more scalar fields.
- **Reason:** an agent's behaviour must be *observable* to be *verifiable* and *reportable*. (1) `tool_calls`: a test asserting only on final text proves nothing about tool use — a model can compute simple answers itself and never call a tool — so recording dispatched calls lets a live/eval test assert tools were genuinely used (`{"add","multiply"} <= {c.name for c in result.tool_calls}`); it holds *executed* not merely requested calls (the `budget` stop returns before the execution loop). (2) `usage`: already accumulated for the budget guardrail — exposing it answers "what did this run cost" and feeds the README's eval numbers; it pairs with `token_budget` (the cap) as the actual. (3) `turns`: pairs with `max_turns` the same way, the natural measure of how much work the loop did. All three are already computed internally, so exposing them is near-free; a full transcript (per-turn results) is a heavier surface deferred until debugging needs it. Dataclass ordering: telemetry fields carry defaults and follow the two non-default outcome fields.
- **Scope:** template-constant
- **Eval hook:** after a run, `AgentResult.tool_calls` lists executed calls in order (a two-tool run records both distinct tools; a `budget`-stopped turn's requested calls are excluded); `usage` equals the summed `Completion.usage`; `turns` equals the number of `complete()` calls made (and `== max_turns` on the `max_turns` stop)
## D-025: Structured plan output — mechanism and schema

- **Options (mechanism):** prompt for JSON and parse `Completion.text` · tool-as-structured-output (a `submit_plan` tool whose `input_schema` is the plan schema, read from `tool_calls`) · provider `output_config.format`
- **Options (schema depth):** flat `steps: list[str]` · phases (`list[Phase]`, each a name + steps) · recursive sub-plan objects
- **Choice:** prompt for JSON, tolerant-parse into typed dataclasses. Schema: `Plan(project_name, summary, stack: list[str], supported: bool, phases: list[Phase], manual_checklist: list[str])`, `Phase(name, steps: list[str])`.
- **Reason:** the mechanism must stay model-agnostic (D-012) — prompt-for-JSON works with any adapter and needs no provider structured-output coupling and no `tool_choice` adapter extension (which the tool-as-structured-output option would require, since the current adapter can't force a tool call). It's also transparent — it *is* the lesson in getting structure out of a text model. Provider `output_config.format` is rejected as provider-specific. The schema is deliberately **shallow (two levels, no recursion)** because parse reliability under Option 1 degrades with nesting depth — richer nesting trades directly against valid-JSON reliability, so recursive sub-plans are rejected (fragile to prompt and parse, and not cleanly gradeable). `stack` is `list[str]` because a stack is inherently several components; `phases` (name + steps) mirror how projects actually decompose and are gradeable. Clarifying questions are **not** stored on `Plan` — they are a separate stage's input, and storing them would conflate the interview with the answer. Richer fields (risks, dependencies, file tree) are deferred until Block 6's rubric shows the plan is too thin — add surface when a constraint demands it, not speculatively. Cost accepted: parsing free-text JSON is fragile (prose wrapping, markdown fences) — mitigated by a tolerant parser plus one retry (Task 3).
- **Scope:** template-constant (the schema is fixed; project-specific content fills it — the values are render-variable, the shape is not)
- **Eval hook:** `genesis.planner` imports with no provider SDK; a scripted JSON completion parses into a `Plan` with populated `phases`/`stack`; a malformed completion is handled gracefully (Task 3); the `Plan` schema has at most two levels of nesting
## D-026: The planner is an adaptive, bounded planning loop (not one-shot)

- **Options:** two-method one-shot (`clarify` once → `plan`) · adaptive bounded loop (each round the model asks more *or* emits the plan, capped by `max_rounds`) · full open-ended iterative Q&A
- **Choice:** adaptive bounded loop. `idea → [the model either returns clarifying questions or the final Plan]* → Plan`, capped by a hard `max_rounds`. Human answers are supplied between rounds via an injected callback (`answer_fn(questions) -> answers`), so the loop is caller-orchestrated and testable. A `revise(plan, feedback)` path re-plans on user pushback. The impact-based clarify prompt (soft cap, "ask fewer if clear") is reused *within* each round, not discarded.
- **Reason:** the plan's consumer is the Block 5 scaffolder AI, which builds from it — so plan *quality* drives build *accuracy*, and an under-specified plan is the real failure mode. Empirically, one-shot clarify on a vague idea ("build a todo app") yields ~5 general questions and a too-thin plan. The loop's key property is **adaptive depth**: the model decides each round whether it has enough, so a clear idea plans immediately (low burden) and a vague one gets more clarification — reconciling thoroughness with the human-answer burden that argued against fixed multi-round interrogation. `max_rounds` is the same guardrail idea as the agent loop's `max_turns`: it can never interrogate forever. Unlike the Phase 2 agent loop (which auto-runs tools), this loop **pauses for a human** between rounds — hence the injected `answer_fn`, which also keeps it CLI-agnostic and unit-testable (inject scripted answers). This supersedes the earlier "two-method flow" framing.
- **Scope:** template-constant
- **Eval hook:** a `FakeAdapter` scripted to return questions then a plan drives the loop, via a scripted `answer_fn`, to a typed `Plan`; a fake that never emits a plan hits `max_rounds` and returns a forced final plan (no infinite loop); `revise` produces an updated `Plan`; live (skip-gated) — a vague idea triggers at least one clarification round, a specific idea can plan in one
## D-027: The round returns a status-tagged discriminated result; all malformed output is PlannerError

- **Options (signal):** a JSON object with a `status` field · two provider-structured responses · a tool-call signal (needs `tool_choice`)
- **Options (errors):** raise a clear `PlannerError` on any malformed response · tolerant retry · let raw exceptions propagate
- **Choice:** each round returns one JSON object — `{"status": "need_info", "questions": [...]}` or `{"status": "ready", "plan": {...}}` — parsed by `_extract_json` and dispatched into a `RoundResult`. Every malformed response (invalid JSON, non-dict value, missing keys, unknown status) is normalised to `PlannerError` via two guards. `supported` is computed by `_is_supported` in our code, never read from the model's JSON.
- **Reason:** the status field is consistent with D-025 (prompt-for-JSON, no `tool_choice` adapter extension) and is what makes the loop adaptive — a *single* model call decides ask-vs-plan (D-026), rather than the caller deciding. Uniform `PlannerError` makes the failure mode testable (`pytest.raises`) and honest, and gives a message naming the missing key — useful when tuning the prompt live. The model is barred from setting `supported` because Genesis, not the model, is the authority on what it can scaffold (D-001/D-028) — the planning instruction forbids the field and `_parse_plan` computes it. Tolerant retry is deferred (cut-order item) — a clear error is enough for v1.
- **Scope:** template-constant
- **Eval hook:** a `need_info` fake yields questions, a `ready` fake parses into a `Plan`, and fakes with bad JSON / missing `questions` / missing plan keys / unknown status each raise `PlannerError`; a live round returns a well-formed `RoundResult` in whichever branch the model chooses
## D-028: "Supported" is a keyword heuristic on the stack, computed by us

- **Options:** keyword heuristic on the `stack` list · have the model report a `project_type` we map · let the model set `supported`
- **Choice:** `_is_supported(stack)` — `"python"` appears in the joined lowercased stack AND none of a fixed set of unsupported markers does (`react`, `vue`, `flask`, `django`, `fastapi`, `node`, `ios`, `android`, `swift`, `kotlin`, `web`, `mobile`, `gui`, `electron`). Computed in our code; `_parse_plan` sets `Plan.supported` from it, and the planning instruction forbids the model from emitting a `supported` field.
- **Reason:** only the Python CLI template exists (D-001), so "supported" means "maps to a Python CLI," and **Genesis, not the model, is the authority on what it can scaffold** — so the determination lives in our code, not the model's JSON. A keyword heuristic is minimal (no extra schema field, unlike the `project_type` option) and explicit. Cost accepted: it *is* a heuristic and therefore imperfect — a Python web backend using an unlisted framework could slip through as supported, and a genuine CLI whose description happens to contain a marker word could be misflagged. This is an honest limitation to name in the README. The honesty behaviour falls out for free: an unsupported stack yields `supported=False` while the model-populated `manual_checklist` still gives useful by-hand steps.
- **Scope:** template-constant
- **Eval hook:** `_is_supported(["Python 3.11", "argparse"])` is `True`; `["React", "Node"]` and `["Python 3.11", "Flask"]` are `False`; a parsed unsupported plan has `supported=False` and a non-empty `manual_checklist`
## D-029: Render mechanism — replace the concrete name, not placeholder tokens

- **Options:** replace the concrete `greetly` string in a copy of the tree · placeholder tokens (`{{name}}`) in the template that the scaffolder fills in
- **Choice:** the template stays a real, working `greetly` repo; `scaffold` copies the tree and substitutes `greetly` → the normalized project name in file contents and the `src/greetly/` directory name
- **Reason:** the template is vendored and runs its own install/lint/test as a CI job (D-001). Placeholder tokens would make the template itself invalid — `name = "{{name}}"` won't `pip install` and `{{name}}.cli:main` won't import — so the template could no longer test itself, defeating the point of vendoring a CI-covered artefact. Replacing the concrete name keeps the template a live, importable, green repo; substitution happens only on a copy at generation time. Cost accepted: the mechanism relies on `greetly` not colliding with an unrelated word in the template (it currently does not); a template that reused a common word would need a more targeted replace.
- **Scope:** template-constant
- **Eval hook:** the vendored template installs and `pytest` passes as-is (no substitution needed to be valid); after `scaffold`, no file content or path under the generated repo contains the string `greetly`
## D-030: Name normalization — slugify the project name to a valid Python identifier

- **Options:** minimal rule (lowercase + spaces/hyphens → `_`) with weird input accepted as a known gap · full slugify to a guaranteed-valid identifier · raise on any non-identifier input
- **Choice:** `normalize(name)` slugifies: lowercase → replace any run of non-alphanumeric chars with a single `_` → strip leading/trailing `_` → prefix `p_` if it now starts with a digit → fall back to `project` if empty. The one normalized string is used atomically in all four coupled sites (D-002/D-009): `pyproject.toml` `name`, `src/<name>/`, the `[project.scripts]` import path, and the test imports.
- **Reason:** a package/import name must be a valid Python identifier — a hyphen is the minus operator, so `import my-cli` is a syntax error, and the same holds for spaces, dots, and other non-identifier chars. The scaffolder is the deterministic eval harness, so it must never emit an invalid name that would break install/import — a guaranteed-valid output matters more than the couple of lines it costs, which is why the full slugify beats the minimal rule (which lets `a.b.c` slip through) and beats raising (the planner's free-text name shouldn't be able to abort generation). Keeping the distribution `name` identical to the import name is required for hatchling's zero-config `src/<name>/` discovery (D-002), so both derive from the single normalized string.
- **Scope:** template-constant
- **Eval hook:** `normalize("Todo App") == "todo_app"`; `normalize("my-cli") == "my_cli"`; `normalize("7guis") == "p_7guis"`; `normalize("!!!") == "project"`; the result is always a valid Python identifier
## D-031: The plan travels into the generated repo as PLAN.md

- **Options:** write the `Plan` into the generated repo as `PLAN.md` · generate the bare skeleton only, discarding the plan's content
- **Choice:** `scaffold` renders the `Plan` (summary, stack, phases/steps, manual checklist) into a `PLAN.md` at the root of the generated repo
- **Reason:** the scaffolder deliberately renders only the skeleton (one template, D-001) — it does not turn `plan.phases` into code — so without PLAN.md the planner's entire output is discarded at the scaffold boundary. Writing PLAN.md is the one place the planner→scaffolder pipeline produces a visible, connected artefact: the skeleton ships with the plan a human or AI then builds against. Cost is one formatted-markdown file write, and it is a documentation artefact (not part of the build/test eval), so it can be cut under time pressure (cut-order item #2) without touching the floor.
- **Scope:** template-constant
- **Eval hook:** after `scaffold(plan, dir)`, `dir/PLAN.md` exists and contains the plan's summary and each phase name; removing it does not affect whether the repo installs or `pytest` passes
## D-032: Build+test check runs in a fresh venv via subprocess, returning a structured result

- **Options (isolation):** subprocess into a fresh `venv` · install into the current Genesis interpreter · a runner like tox/nox
- **Options (return):** bool · structured `BuildResult(installed, tested, output)`
- **Choice:** `build_and_test(repo_dir)` creates a throwaway `venv`, `pip install -e ".[dev]"` and `pytest` inside it via `subprocess`, and returns `BuildResult(installed: bool, tested: bool, output: str)` (with an `ok` = installed and tested).
- **Reason:** the eval's claim is "a freshly generated repo installs from clean and passes its own tests" — only a fresh venv proves it. Installing into the Genesis interpreter can false-pass (deps already satisfied) and mutates the working env; tox/nox adds a dependency and hides the mechanism, against the no-scaffolding-library / learning constraints. Structured result over bool because the Block 6 eval harness must report which half failed and surface `output` to diagnose, which a bool discards; `installed`/`tested` are separate so an install failure is distinguishable from a test failure. Cost accepted: the check needs network (pip fetches hatchling to build) and is slow, so it is the marked-slow integration test, not a fast unit test.
- **Scope:** template-constant
- **Eval hook:** `build_and_test(dir)` on a scaffolded repo returns `installed=True`, `tested=True`, `ok=True`; a repo with a deliberately broken test yields `installed=True, tested=False`

## D-033: CLI design — three separate commands vs unified

- **Options:** single `genesis` command with subcommands (plan|scaffold|create) vs three separate commands vs one unified "do-everything" command
- **Choice:** three separate commands: `genesis plan`, `genesis scaffold`, `genesis create`
- **Reason:** decouples the workflows. A user who only wants planning output can use `plan` standalone. Someone with an external plan can use `scaffold`. The `create` command is the convenience wrapper for end-to-end. Each is independently useful and composable, and the mental model is simpler than mode-flags on a single command. Argparse subcommands are still unified under one entry point, so this is syntactically clean (not literal file-based commands).
- **Scope:** CLI interface
- **Eval hook:** `genesis plan --help`, `genesis scaffold --help`, `genesis create --help` each show distinct usage; running any command with invalid args shows command-specific error

## D-034: Argument parsing — argparse vs Click/Typer

- **Options:** stdlib `argparse` vs Click (third-party) vs Typer (async, modern)
- **Choice:** argparse (stdlib only)
- **Reason:** minimalism (no new dependency), aligns with D-006 (no scaffolding libs) and the no-dependencies philosophy. Argparse is verbose but clear and zero-cost. Click and Typer would add runtime deps to Genesis, which users who import the library as a module (not just the CLI) would inherit.
- **Scope:** CLI implementation
- **Eval hook:** `pip install genesis` (no extra) runs all three CLI commands with `--help` using only stdlib

## D-035: Ollama adapter implementation — OpenAI-compatible endpoint

- **Options:** use Ollama SDK directly vs OpenAI-compatible `/v1/chat/completions` endpoint vs raw REST wrapper
- **Choice:** OpenAI-compatible `/v1/chat/completions` endpoint (default: `http://localhost:11434/v1`)
- **Reason:** Ollama provides this for free, no new dependency beyond stdlib `urllib`, and it is provider-agnostic — the endpoint is a generic interface, not Ollama-specific. Using the SDK would couple Genesis to Ollama; the endpoint is both simpler and more portable. Cost accepted: simpler error handling and no automatic retries (raw HTTP), but acceptable for a local server.
- **Scope:** adapter implementation
- **Eval hook:** with Ollama running, `OllamaAdapter(model="mistral").complete([...])` returns a `Completion`; with Ollama not running, connection error is raised and caught gracefully by the CLI

## D-036: Tool-calling with Ollama — accept but return empty

- **Options:** try to use tools with Ollama (unreliable) vs accept tools param but return `tool_calls=[]` vs raise an error if tools requested
- **Choice:** accept `tools` param in `complete()` but return `tool_calls=[]` (no tool calls). Stay Protocol-compatible; silently degrade when tools are present.
- **Reason:** Ollama's tool-calling is unreliable and most open-source models don't support function-calling well. Rather than raise an exception (which would fail the loop), accepting but returning empty tool calls lets Ollama degrade gracefully — it will answer text-only, and the agent loop will treat it as done. This preserves Protocol conformance (D-012). For the planner (which has no tools in its calls), Ollama works identically. Honest limitation: documented as "tool-calling not supported with Ollama."
- **Scope:** adapter implementation
- **Eval hook:** `OllamaAdapter.complete([...], tools=[...])` returns a `Completion` with `tool_calls=[]` (not an exception); the same call without tools returns text normally

## D-037: Token counting for Ollama — track 0 / no budget enforcement

- **Options:** estimate tokens from prompt/response length vs track 0 (no budget enforcement) vs try to infer from Ollama API
- **Choice:** `OllamaAdapter.complete()` returns `Completion.usage = 0` always. Cost cap guardrails become a no-op with Ollama.
- **Reason:** Ollama doesn't report token counts in its responses and estimation is unreliable. Users choosing Ollama accept "free local" means "no token tracking." The `max_turns` guardrail still works (structural iteration cap), but the `token_budget` cap is disabled by always reporting 0 usage. This is an honest trade-off: free local execution vs cost visibility. Documented in README as a limitation.
- **Scope:** adapter implementation
- **Eval hook:** `OllamaAdapter.complete(...)` returns `Completion` with `usage=0`; a loop with Ollama respects `max_turns` but ignores `token_budget`
## D-038: Truncation is a first-class stop reason on the adapter Protocol

- **Options:** let the planner fail on the resulting JSON parse error · have each adapter raise its own truncation exception · add a provider-neutral `StopReason` enum to `Completion` and map it in each adapter
- **Choice:** `StopReason{DONE, TRUNCATED, TOOL_USE, OTHER}` on `Completion`; `AnthropicAdapter` maps the provider's `stop_reason` string through `_STOP_REASON_MAP`.
- **Reason:** "the model ran out of output tokens" is a fact every provider reports and every caller needs, so it belongs on the Protocol (D-012), not in provider-specific exception types that would leak the provider back into the planner. An enum keeps the mapping total: unknown provider strings collapse to `OTHER` rather than crashing on a new API value. Cost accepted: every future adapter must supply a mapping, and Ollama's will be approximate.
- **Scope:** adapter interface
- **Eval hook:** `Completion(text="x").stop_reason is StopReason.DONE` (the default); an Anthropic response with `stop_reason="max_tokens"` yields `StopReason.TRUNCATED`

## D-039: The planner fails fast on truncation instead of parsing a partial response

- **Options:** attempt to salvage the partial JSON · silently retry with a larger budget · raise `PlannerError` naming the fix
- **Choice:** `Planner._round` raises `PlannerError("response was truncated by max_tokens — increase --max-tokens and try again")` before attempting `_extract_json`.
- **Reason:** a truncated plan is not a recoverable parse problem — the tail is simply absent, so salvage produces a plausible-looking plan that is missing phases, which is worse than an error. Silent retry would spend the user's tokens twice without consent and hide a mis-set budget. Naming `--max-tokens` in the message makes the failure self-servicing. Cost accepted: a user who hits the cap loses the round's spend and must re-run.
- **Scope:** planner behaviour
- **Eval hook:** a `FakeAdapter` returning `Completion(text="{partial", stop_reason=StopReason.TRUNCATED)` makes `Planner.plan()` raise `PlannerError` mentioning `--max-tokens`, not `json.JSONDecodeError`

## D-040: Unsupported stacks get a generic scaffold, not a forced template render

- **Options:** refuse to scaffold and exit non-zero · render the Python CLI template anyway and let the user delete it · write a docs-only directory (`PLAN.md` + `README.md`) with no build step
- **Choice:** `scaffold()` branches on `plan.supported` and delegates to `_scaffold_generic()`, which writes `PLAN.md` and a `README.md` explaining that no code was generated for this stack.
- **Reason:** this is the honesty behaviour the project committed to (`genesis-plan.md`) made real in code — the user gets the plan they paid tokens for plus an explicit statement of the limitation, rather than either nothing or a Python skeleton for their Rust project. Skipping `build_and_test()` on this path keeps the eval gate meaningful: the harness only ever claims "builds and passes tests" about repos it actually built and tested.
- **Scope:** scaffolder behaviour
- **Eval hook:** `scaffold(plan_with_supported_false, tmp)` produces exactly `PLAN.md` and `README.md`, no `pyproject.toml`; `cmd_scaffold` returns 0 without invoking `build_and_test`

## D-041: Each adapter module owns its `SUPPORTED_MODELS` list, with a custom-name escape hatch

- **Options:** a central model registry in `core.py` · hard-code model names in the CLI · a `SUPPORTED_MODELS` constant per adapter module, plus a free-text option in the picker
- **Choice:** `SUPPORTED_MODELS` lives beside the adapter that can serve those models; `_select_model` renders it as a numbered menu and offers a final "enter custom model name" entry.
- **Reason:** a central registry would have to be edited every time any provider ships a model, re-coupling the CLI to provider specifics that D-012 pushed behind the Protocol. Keeping the list in the adapter module means adding a provider is one new file. The escape hatch exists because the curated list goes stale between releases and a hard-coded menu would make a brand-new model unreachable without a Genesis upgrade. Cost accepted: `_create_plan` validates against the list, so a custom name typed at the menu is passed to the provider unvalidated and fails at the API boundary instead of the CLI boundary.
- **Superseded in part by D-047.** As first written, `_create_plan` validated the chosen model against `SUPPORTED_MODELS` and rejected anything outside it, which made the custom-name option unreachable — the cost described above was not actually the behaviour. D-047 removes that validation and makes the list a menu, as this entry always intended.
- **Scope:** adapter + CLI interface
- **Eval hook:** `from genesis.anthropic_adapter import SUPPORTED_MODELS` succeeds and `core.py` imports no model names of its own; selecting the last menu index prompts for a free-text model name

## D-042: Missing CLI arguments are prompted for interactively; tuning knobs stay flag-only

- **Options:** require every argument as a flag and error out when absent · prompt for everything · make positionals optional and prompt only for what a run cannot proceed without, leaving tuning knobs flag-only with defaults
- **Choice:** `idea`, `output_dir`, `plan_json`, `--adapter` and `--model` are prompted for when omitted; `--max-rounds` (6) and `--max-tokens` (10000) are flag-only with defaults and are never prompted for.
- **Reason:** the two audiences pull in opposite directions — a first-time user typing `genesis create` should be walked through it, while a scripted run needs every value settable non-interactively. Optional positionals satisfy both from one code path. The line between the two groups is whether a sensible default exists: there is no default project idea, but there is a defensible default round and token budget, and prompting for numbers a user has no basis to choose is friction, not help. Cost accepted: a non-interactive run that omits a required value blocks on `input()` against a closed stdin instead of printing a usage error.
- **Scope:** CLI interface
- **Eval hook:** `genesis plan --help` shows `idea` as optional and `--max-rounds`/`--max-tokens` with defaults; `genesis plan` with no arguments in a terminal prompts for the idea

## D-043: Presentation is extracted to `genesis/interface.py` (partially)

- **Options:** leave `print`/`input` inline in `core.py` · adopt a TUI library (rich, textual) · extract a stdlib-only presentation module
- **Choice:** `genesis/interface.py` holds `print_progress/print_success/print_error` and the `_get_*`/`_select_*` prompts; `core.py` imports them and holds command logic.
- **Reason:** the `cmd_*` functions are the units worth testing, and inline `input()` makes them untestable without stdin mocking — which Phase 7 explicitly declined to do. One presentation module is the seam that lets those tests stub prompting instead. A TUI library was rejected on the same grounds as D-034: it would add a runtime dependency inherited by anyone importing Genesis as a library, for output that plain `print` already produces.
- **Gap closed by D-045.** The extraction was initially incomplete: three `input()` calls remained in `core.py` (the save-path prompt, the overwrite confirmation, and `answer_fn`), leaving `cmd_plan`, `cmd_create` and the planner answer callback unstubbable through `interface`. D-045 states the boundary rule and finishes the move.
- **Scope:** CLI implementation
- **Eval hook:** `grep -c "input(" src/genesis/core.py` returns 3 today; the seam is complete when it returns 0 and every prompt is reachable through `genesis.interface`

## D-044: `cmd_scaffold`'s plan parameter means content, not a path

- **Options:** the parameter is a filesystem path and `cmd_create` writes a temp file to hand one over · the parameter is plan JSON text and path resolution happens at the CLI edge · accept either and sniff which one was passed
- **Choice:** `cmd_scaffold(plan_json: str, ...)` takes plan JSON **text** and never touches the filesystem. A sibling `cmd_scaffold_file(plan_path: str | None, ...)` owns "get me the text" — it prompts when the path is absent, reads the file, and delegates. `cli.py` dispatches `scaffold` to `cmd_scaffold_file`; `cmd_create` calls `cmd_scaffold` directly with the JSON it already holds.
- **Reason:** the parameter previously meant *path* for one caller and *content* for the other, so `genesis create` passed a JSON string to `Path(...).read_text()` and failed on every invocation — the floor deliverable of the CLI block was broken in the only code path that had two callers. One meaning per parameter is what prevents that class of drift, and content is the right meaning because it makes `cmd_scaffold` testable with no filesystem, which the CLI test task depends on. Sniffing was rejected outright: guessing whether a string is a path or JSON is how the ambiguity arose. Cost accepted: two entry points where there was one, and `cmd_create` cannot reuse the path-reading error handling.
- **Scope:** CLI implementation
- **Eval hook:** `cmd_scaffold(json_text, out, force)` returns 0 and writes the repo; `cmd_scaffold_file("missing.json", out, force)` returns 1 printing `Could not read plan file:` (not `Unexpected error`); `genesis create` scaffolds end-to-end

## D-045: The `interface` / `core` boundary is presentation vs filesystem

- **Options:** move all I/O out of `core.py` into `interface.py` · leave the remaining prompts inline and test around them by always passing arguments · split on presentation vs filesystem — `interface` owns human interaction, `core` owns files
- **Choice:** `interface.py` owns everything that talks to a human (`input()` and message `print()`) and never touches the filesystem; `core.py` keeps every `open(...)`. `answer_fn`, `_get_save_path` and `_confirm_overwrite` moved to `interface`; the `open(...)` writes and the plan's stdout emission stayed in `core`.
- **Reason:** "move all I/O" is the rule that produced the `_get_json_path` defect — a presentation helper doing a file read, whose name then lied about its return type (see D-044). Splitting on *who the code talks to* keeps each module's name honest. The constraint driving the move is testability: `cmd_plan` and `cmd_create` were unstubbable while they called `input()` directly, and the CLI test task needs to drive them without stdin. `print(plan_json)` deliberately stayed in `core` — it is the command's machine-parseable stdout contract, not a message, and routing it through a presentation helper invites a decorative prefix that would break callers piping `genesis plan` into `jq`. Cost accepted: `core.py:149`'s build-log dump to stderr is still an inline `print`, an acknowledged exception on the grounds that it is a log dump rather than a message.
- **Scope:** CLI implementation
- **Eval hook:** `grep -c "input(" src/genesis/core.py` returns 0; `grep -c "open(" src/genesis/interface.py` returns 0

## D-046: Adapter construction is a seam — `_build_adapter`

- **Options:** keep constructing `AnthropicAdapter` inline in `_create_plan` and monkeypatch the class in tests · extract `_build_adapter(adapter_str, model, max_tokens) -> ModelAdapter` · add an `adapter=None` injection parameter to `_create_plan`
- **Choice:** `_build_adapter` in `core.py` owns the name → live adapter mapping and is the only place that names a concrete adapter class; `_create_plan` resolves choices, calls it, and plans.
- **Reason:** `_create_plan` had no seam, so no test could reach it without a network call and a real API key — blocking the CLI test task entirely. Patching the concrete class in each test was rejected because every test would then have to know which provider class is current, and would break the moment a second adapter lands. An injection parameter was rejected for putting a test-only argument in a production signature. The decisive reason is not testing, though: "which adapter does this string mean" was smeared across `core.py` and `interface.py` as commented-out fragments in three files, so adding a provider meant finding all of them. One function makes that a one-branch edit. Cost accepted: one more indirection between the CLI and the adapter.
- **Scope:** CLI implementation
- **Eval hook:** `_build_adapter("anthropic", m, n)` returns an `AnthropicAdapter`; `_build_adapter("nope", m, n)` raises `ValueError("Unknown adapter: nope")`; `grep -c AnthropicAdapter src/genesis/core.py` counts only the import and the one construction site

## D-047: `SUPPORTED_MODELS` is a menu, not a whitelist

- **Options:** validate the model against `SUPPORTED_MODELS` and reject anything outside it (deleting the custom-name menu option) · drop the validation and let the provider reject unknown models · validate only values that came from the menu
- **Choice:** no model validation in Genesis. `_create_plan`'s `valid_models` block is deleted; any model name — menu-chosen, `--model`-supplied, or free-typed — is passed to the adapter.
- **Reason:** the curated list goes stale between Genesis releases, so a whitelist makes a model the provider ships tomorrow unreachable until Genesis is upgraded — the opposite of the model-agnostic seam D-012 exists to provide. The provider already rejects unknown model names with a clear error, so Genesis validating too was duplicated authority with a shorter shelf life. Provenance-tracking (validating only menu values) was rejected as complexity for no gain. Cost accepted: a typo'd `--model` now costs an API round trip and surfaces the provider's error text rather than failing instantly at the CLI boundary; `core.py` no longer names any model, which is the intended consequence.
- **Scope:** CLI interface
- **Eval hook:** `_build_adapter("anthropic", "some-future-model-9", 500)` constructs an adapter rather than raising; `grep -c ANTHROPIC_MODELS src/genesis/core.py` returns 0 while `interface.py` still imports it for the menu
