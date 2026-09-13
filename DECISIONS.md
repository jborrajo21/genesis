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
- **Superseded in part by D-054:** the vendoring decision stands, but the path is now
`src/genesis/templates/python-cli/` — outside `src/` the template never reached the wheel, so a
non-editable install could not scaffold.
- **Eval hook:** `src/genesis/templates/python-cli/` exists; root CI workflow runs the
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

## D-037: Token counting for Ollama — read usage when the endpoint reports it

- **Options:** estimate tokens from prompt/response length · always report 0 and disable the budget guardrail · read the `usage` block the OpenAI-compatible endpoint returns, falling back to `None`
- **Choice:** `OllamaAdapter.complete()` reads `body["usage"]["total_tokens"]` and passes it through as `Completion.usage`, or `None` when the endpoint omits it. The `token_budget` guardrail works with Ollama exactly as it does with Anthropic.
- **Reason:** D-035 put the adapter on the OpenAI-compatible `/v1/chat/completions` endpoint, which returns a standard `usage` block (`prompt_tokens`/`completion_tokens`/`total_tokens`). Reporting 0 would discard data the server already sends and would silently disable a guardrail for no gain. Reading defensively (`.get`, falling back to `None`) costs nothing if a given Ollama build omits the block, and `None` is already the `Completion.usage` type's "unknown" value, so callers need no Ollama-specific branch. Estimation was rejected outright: a wrong number in a budget guardrail is worse than an honest absent one.
- **Revised Sept 1, 2026.** As first written this entry chose `usage = 0` always, on the stated ground that "Ollama doesn't report token counts." That is true of Ollama's *native* `/api/chat` (which reports `prompt_eval_count`/`eval_count`) but not of the `/v1` endpoint D-035 selected in the same session — the two entries were written against different assumptions about which API the adapter would call, and this one was wrong. Writing the adapter surfaced the conflict.
- **Scope:** adapter implementation
- **Eval hook:** with Ollama running, `OllamaAdapter(model=m).complete([...]).usage` is a positive int; against a stubbed response with no `usage` key it is `None`, and neither case raises

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

## D-048: An unreachable Ollama server fails at `complete()`, not at construction

- **Options:** health-check the server in `OllamaAdapter.__init__` so `_build_adapter` can fail fast · no check, let `complete()` raise `ConnectionError` and have the CLI report it · let the raw `URLError` propagate
- **Choice:** construction does no I/O. `complete()` converts `urllib.error.URLError` into `ConnectionError` carrying an actionable message, and `cmd_plan`/`cmd_create` each catch `ConnectionError` explicitly, above their existing `except OSError` clause.
- **Reason:** a health check would put network I/O in a constructor, which is surprising and would force every offline adapter test to patch the network merely to build an object; it would also break D-046's premise that `_build_adapter` is a pure name-to-object mapping. Failing at `complete()` loses almost nothing, because `Planner.plan()` calls `_round()` immediately — the error arrives before the user has answered a single clarifying question. The explicit CLI clause is mandatory rather than cosmetic: `ConnectionError` subclasses `OSError`, so without a clause above it a stopped Ollama server would be reported as `Could not write output`, since Python matches `except` clauses in source order rather than by specificity. Cost accepted: two near-identical handlers in `core.py`, and any future adapter raising `OSError` subclasses needs the same treatment.
- **Scope:** adapter + CLI implementation
- **Eval hook:** with Ollama stopped, `genesis plan --adapter ollama` exits 1 printing `Run: ollama serve` and not `Could not write output`; `tests/test_core.py::test_cmd_plan_reports_unreachable_server` asserts both halves

## D-049: Structured output is a Protocol capability — `response_schema`

- **Options:** document malformed local-model JSON as an honest limitation and move on · have `OllamaAdapter` always request the plan schema · add an optional `response_schema` parameter to `ModelAdapter.complete()` that callers pass and adapters transmit
- **Choice:** `complete(messages, tools=None, response_schema=None)`. `Planner` passes `_PLAN_SCHEMA`; `OllamaAdapter` forwards it as `response_format: {"type": "json_schema", ...}`; `AnthropicAdapter` accepts and ignores it.
- **Reason:** measured, not assumed. Against a local gemma4, an unconstrained prompt produced malformed JSON (a `}` closing an array) roughly half the time; `response_format: {"type": "json_object"}` removed the code fence but stayed malformed, showing Ollama treats it as a prompt hint; `json_schema` produced valid, parseable output first try. The parameter rather than adapter-side cleverness because the plan's shape is the planner's knowledge (D-025) — adapters transmit a schema, they never know one. Anthropic ignoring it is honest rather than lazy: those models already return valid JSON reliably, and inventing a tool-forcing translation would be untested surface. The plan's form is unchanged; the schema describes the existing shape and constrains reliability only.
- **Cost accepted:** the plan's shape is now stated twice — as prose in `_PLANNING_INSTRUCTION` and as `_PLAN_SCHEMA` — and the two can drift, with the schema silently winning for Ollama and the prose for Anthropic. They are kept adjacent in `planner.py` to make drift visible. `additionalProperties` is deliberately unset, so a model may emit stray keys; `_parse_plan` reads named keys and ignores extras.
- **Scope:** adapter interface (amends D-012)
- **Eval hook:** `OllamaAdapter.complete(msgs, response_schema=s)` puts `response_format.json_schema.schema == s` on the wire and omits `response_format` entirely without a schema; a live `Planner(OllamaAdapter(...)).plan(...)` returns a `Plan` whose `dataclasses.asdict` keys match the `Plan` dataclass exactly

## D-050: Live deploy is deferred to late October / November, not dropped

- **Options:** deploy today as the Sept 1 plan requires · defer to a named date before the job hunt · drop the deploy from the project entirely
- **Choice:** defer. Target late October / November, funded as a deliberate spend decision, so the URL is live through the December job-hunt window. The Sept 1 block goes to the Tier 2 eval and the two-model comparison instead.
- **Reason:** three constraints that were not in view when the deploy was locked as non-negotiable. **Budget:** an always-on load-balanced service costs roughly $25–30/month against a remaining AWS balance of $60–80, so a deploy today runs dry around early November. **Timing:** `genesis-plan.md` targets the job hunt from December onward, so today's deploy produces a *dead* URL exactly when it would be clicked — worse than no URL, because it reads as abandonment rather than scope. **Differentiation:** containerise-and-deploy is table stakes for a portfolio repo, whereas a layered eval with a two-model comparison, honest limitations, and a decision log is not; with one block left, the block buys more in eval than in ops. Deploy is also the only remaining item that is fully decoupled — nothing else depends on it and no code decays before October — which makes it the correct thing to move when something has to move.
- **Cost accepted:** one line of the Sept 1 presentability bar goes unmet and the roadmap keeps an open row; the repo reads as in-progress rather than shipped, mitigated by stating in the README that the deploy is scheduled and deliberately timed rather than missing. The project also ships with no ops evidence — no containerisation, ECR, IAM, or TLS work visible — which is a real gap in the skills the repo demonstrates until the deploy lands. Standing risk: "later" becomes "never"; the mitigation is that this entry names a date and a reason, and the deferral is worth less than a shipped deploy if that date slips.
- **Amends:** the "non-negotiable deliverables" framing in `genesis-plan.md` and `CLAUDE.md`, which listed the live deploy alongside the eval harness as uncuttable. The eval harness remains uncuttable and is done; the deploy is rescheduled, not cut.
- **Scope:** project plan
- **Eval hook:** none — a scheduling decision. Verifiable only by the deploy existing by end of November; if it does not, this entry was wrong.

## D-051: Eval code lives in `evals/`, outside the test suite, with results persisted as JSONL

- **Options:** put the eval in `tests/` behind a marker · add a `genesis eval` subcommand · a standalone `evals/` package run as a script
- **Choice:** `evals/` holding `run_eval.py` (idea set, `Record`, `run_one`), `main.py` (the driver), `report.py` and `rubric.py`. Results are appended to `evals/results/run-<UTC>.jsonl`, one JSON object per run, flushed after every record. `testpaths = ["tests"]` already scopes pytest, so none of it is collected.
- **Reason:** the eval is non-deterministic, costs money, needs credentials, and takes about an hour — every property that makes something a bad test. In `tests/` it would either poison CI or be permanently skipped, and D-015 already scoped collection to `tests/` for exactly this kind of reason. A `genesis eval` subcommand was rejected for putting eval machinery in the shipped CLI and handing users a command they have no reason to run. JSONL over one-file-per-record because it is append-only, survives a crash mid-sweep with everything before it intact, and is trivially re-readable. **The persistence is the load-bearing part:** because every generated plan is written to disk with its metrics, the Tier 3 rubric scores saved plans with no re-run, and a metric invented later costs nothing. `CountingAdapter` also lives here rather than in the package — unlike `FakeAdapter` (D-014), it has exactly one consumer, so it does not earn package surface.
- **Cost accepted:** eval code is unlinted by CI's test job and untested itself, so a bug in `report.py` is caught only by reading output — which is how a placeholder regex silently measured domain vocabulary instead of plan quality until the numbers were spot-checked. Results committed to the repo also grow it over time.
- **Scope:** project structure
- **Eval hook:** `pytest` collects nothing under `evals/`; `python -m evals.main --smoke` writes `smoke-*.jsonl`; `python -m evals.report` renders a table from a partially-written file

## D-052: The model comparison is a capability ladder, not a pairing

- **Options:** hosted vs local (two models) · a three-model ladder (local 8B → Haiku → Sonnet) · include Opus as a fourth
- **Choice:** three models — `gemma4:latest` via Ollama, `claude-haiku-4-5`, `claude-sonnet-5` — over the same 20 ideas, with 3 repeats on two of them.
- **Reason:** this reverses part of the v1 cut, which banned a "model-comparison leaderboard" (`genesis-plan.md`), so it is a deliberate unlock rather than scope drift. Two models give one contrast, and if both perform similarly the result says nothing; three give a *trend*, which is much harder to dismiss as cherry-picking and answers the question that matters — does plan quality actually scale with capability, and what does the extra spend buy? It also converts D-012's model-agnostic claim from architecture into measurement. Opus was considered and dropped: planning a small CLI project is not an Opus-hard task, so it would add cost and latency for a result likely indistinguishable from Sonnet's. The unlock is narrow — no ranking UI, no public leaderboard, no models added for their own sake.
- **Cost accepted:** the local leg dominates runtime (~84s per idea against ~15s hosted), making the sweep an unattended hour rather than fifteen minutes. Results are a measurement under conditions — model versions, one date, n=20 — not a property of the code, and must be reported with all three attached.
- **Scope:** eval design
- **Eval hook:** `evals/report.py` renders one row per model with n on every rate; the run file records the model name against every record

## D-053: Malformed plan JSON gets typed error clauses, not the catch-all

- **Options:** leave `except Exception` to report it · one combined clause for `KeyError` and `TypeError` · separate clauses with different messages
- **Choice:** `cmd_scaffold` catches `KeyError` and `TypeError` separately, above `except Exception`. `KeyError` interpolates the missing key; `TypeError` prints a fixed message and deliberately does **not** interpolate the exception.
- **Reason:** D-044 made `scaffold` accept any plan JSON including hand-written files, which makes it the one place untrusted input enters. Valid JSON that is not a valid plan previously landed in the catch-all and printed `Unexpected error: 'project_name'` — correct exit code, useless message. The two clauses are split because their messages have different value: a missing key names the thing to fix, whereas every `TypeError` here is a Python indexing message (`string indices must be integers`, `'NoneType' object is not subscriptable`) that describes our internals rather than the user's file. The failure is always the same thing — "this parsed as JSON but is not a plan object" — so it says that instead. Clause order matters and follows D-048: Python matches `except` in source order, so narrower clauses must precede `except Exception`.
- **Scope:** CLI behaviour
- **Eval hook:** `cmd_scaffold('{"project_name": "x"}', out, False)` returns 1, prints a message naming the missing key, does not print `Unexpected error`, and leaves no directory behind; the same holds for `[]`, `null`, a bare string, and a non-list `phases`

## D-054: The template lives inside the package, not beside it

- **Options:** leave the template at the repo root and install the container editably · `hatch force-include` it into the wheel at its existing path · move it to `src/genesis/templates/python-cli/` and resolve it relative to the package
- **Choice:** moved inside the package. `_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "python-cli"` — one parent, not three.
- **Reason:** D-001 vendored the template to remove a cross-repo fetch, but the *packaging* never followed the decision. `templates/` sat outside `src/`, so hatchling never put it in the wheel, and `_TEMPLATE_DIR` walked three parents up from `scaffolder.py` — which resolves to the repo root under `pip install -e .` and to `lib/pythonX.Y/` inside site-packages. **A non-editable install therefore produced a Genesis that could plan but not scaffold**, and nothing failed until a user tried to generate a repo. It was invisible because every install to date was editable; writing the Dockerfile surfaced it, since a container is the first place a normal install happens. Inside the package the template is package data: it ships in the wheel, and the path resolves relative to the artefact that actually gets installed. `force-include` was rejected because the code would still resolve a path outside the package, so the code change is needed either way — and then the config is redundant.
- **Cost accepted:** the package directory now contains a nested project with its own `pyproject.toml`, which is unusual to read and depends on the build backend not being clever about nested project files (verified: hatchling ships it verbatim, and excludes the untracked `.pytest_cache`/`.ruff_cache` via VCS ignore). CI's `working-directory` and every doc reference to the template path move one level deeper.
- **Scope:** project structure — **amends D-001**, whose recorded location `templates/python-cli/` is superseded by `src/genesis/templates/python-cli/`. The vendoring rationale in D-001 is unchanged and still correct.
- **Eval hook:** `pip wheel . --no-deps` then `unzip -l *.whl | grep templates` lists all 8 template files including the template's own `pyproject.toml`, and no cache directories; installing that wheel into a fresh venv **non-editably** and running `genesis scaffold plan.json out` prints `Build and tests passed`.

## D-055: Container base image — `python:3.11-slim-bookworm`

- **Options:** `python:3.11-alpine` · `python:3.11-slim-bookworm` · a distroless base · a bare Debian image with Python installed via apt
- **Choice:** `python:3.11-slim-bookworm`, pinned to the Debian release rather than the floating `3.11-slim` tag.
- **Reason:** Alpine uses musl libc, so the manylinux wheels that make Python installs fast do not apply and pip falls back to compiling from source — slower builds, a toolchain to install, and occasional outright breakage, all to save tens of megabytes on an image whose size is irrelevant because nothing pulls it on a hot path. Distroless was rejected on a Genesis-specific ground: `build_and_test()` shells out to `python -m venv` and `pip install` at runtime (D-032), so the image needs a working Python environment and a shell, which is precisely what distroless removes. The release is pinned because the bare `3.11-slim` tag follows whatever base OS Docker Hub currently points it at, so an unchanged Dockerfile can silently change its operating system between builds.
- **Cost accepted:** the image is 264 MB, almost entirely base image against roughly 30 KB of Genesis. Multi-stage builds and size optimisation were deliberately skipped — the base dominates, and shaving it is not where the value is.
- **Scope:** deployment packaging
- **Eval hook:** `docker build` succeeds with no `apt-get` layer; `docker run --rm genesis:dev --version` prints the version; `python -m venv` works inside the container, verified by a scaffold whose `build_and_test` passes

## D-056: The image's entrypoint is the CLI, not a server

- **Options:** `ENTRYPOINT` the `genesis` CLI · build an HTTP service now and serve it · no entrypoint, leaving `docker run` to take an arbitrary command
- **Choice:** `ENTRYPOINT ["genesis"]` with `CMD ["--help"]`, running as a non-root user from `/work`, a writable directory intended as a volume mount.
- **Reason:** the HTTP service does not exist, and building one here would smuggle the deferred deploy block (D-050) into a phase whose whole point is that it costs nothing and commits to nothing. Fixing the entrypoint to the CLI makes `docker run <image> plan "an idea"` read naturally while `docker run <image>` prints help. The `/app` (installed from) and `/work` (runtime cwd) split exists because generated repos are written relative to the working directory, so that directory must be writable by the non-root user — a detail that only fails when someone actually scaffolds, which is the worst time to discover it. When the deploy block adds a service, it becomes a second entrypoint or a second image; nothing here blocks that, and both ECS and Lambda consume images either way.
- **Cost accepted:** `docker run` is a poor way to use a CLI that writes files to the user's disk — it needs a volume mount and leaves container-owned output. `pip install` remains the better path for local use, and the README says so. The image exists for deployment, not distribution.
- **Scope:** deployment packaging
- **Eval hook:** `docker run --rm <image>` prints help; `docker run --rm -v <dir>:/work <image> scaffold plan.json out` writes a repo to the host as a non-root user

## D-057: The image installs the `anthropic` extra

- **Options:** install the bare package (`pip install .`) · install with the `anthropic` extra · install `.[dev,anthropic]` including test tooling
- **Choice:** `pip install --no-cache-dir ".[anthropic]"`.
- **Reason:** D-017 made the provider SDK an optional extra so that Genesis installs and its CI runs with no provider dependency. That reasoning is about the *library*; a deployable image is a different artefact, and an image whose hosted adapter raises `ImportError` on first use is not deployable. The Ollama adapter needs nothing extra (stdlib `urllib`, D-035) but needs a reachable server, which a container will not have by default — so the hosted path is the one that must work out of the box. `dev` is excluded: the image is verified by scaffolding a repo and building it, not by running Genesis's own test suite, and `tests/` is excluded from the build context anyway.
- **Cost accepted:** a deliberate divergence between what the wheel requires and what the image installs, so "Genesis has no dependencies" is true of the package and not of the container. The image also carries the SDK for users who only ever run Ollama.
- **Scope:** deployment packaging — narrows D-017 for the container only
- **Eval hook:** `docker run --rm --entrypoint python <image> -c "import anthropic"` succeeds; the same import from a plain `pip install genesis` still fails, as D-017 intends

## D-058: `AnthropicAdapter` implements `response_schema` via native structured output

- **Options:** leave it accepted-and-ignored as D-049 had it · force a tool whose `input_schema` is the plan schema and read the `tool_use` block · pass the schema to the API's native structured-output parameter (`output_config.format`)
- **Choice:** native structured output. `complete()` forwards a schema as `output_config={"format": {"type": "json_schema", "schema": response_schema}}`, conditionally, exactly as `OllamaAdapter` forwards it as `response_format`. `_PLAN_SCHEMA` gains `"additionalProperties": False` on all three of its object nodes.
- **Reason:** D-049 left this unimplemented on the assumption that Claude returns valid JSON reliably enough without constraint. The Tier 2 eval falsified that: both hosted models produced valid plans in 18/20 runs against 20/20 for the schema-constrained local model, and **4 of the 5 total failures were hosted**. Schema constraint beat model capability outright, so the asymmetry was backwards — the capable models were the ones running unconstrained. Tool-forcing was the intended implementation and turned out to be unnecessary: the Messages API has a first-class structured-output parameter, which makes the two adapters near-symmetric (one schema, each adapter knows only how to put it on the wire) and avoids inventing a tool that exists solely to shape output.
- **Measured constraint, load-bearing and invisible at the call site:** Anthropic **rejects with a 400** any `object` in the schema that does not set `additionalProperties: false` explicitly — verified directly against the existing schema. Ollama neither requires it nor objects to it, and both backends accept `required: ["status"]` alone, so the two-branch `need_info` / `ready` shape is preserved and **one shared schema still satisfies both** — D-049's "the schema belongs to the caller, the transport to the adapter" design is unchanged. Whoever next adds a nested object to `_PLAN_SCHEMA` must add the flag or Anthropic will 400 at runtime with no hint from the call site; hence the note in `complete()`'s docstring.
- **Consequence for D-039 and `_extract_json`:** with `output_config.format` set, the response is a text block of valid JSON, so the "valid JSON followed by prose" failures (`Extra data: line 2 column 1`) become impossible on the hosted path. That accounted for both Haiku failures in the eval. `_extract_json` stays, because it is still needed when no schema is passed — the agent loop sends none.
- **Cost accepted:** **every hosted number in the README measures *unconstrained* Claude and does not transfer.** The Tier 2 eval must be re-run across all three models before those figures can be quoted again; the prior run is retained on disk so constrained and unconstrained can be compared on the same 20 ideas rather than silently replaced. A single constrained sample also showed Sonnet choosing Python for an idea where it chose Node.js during the eval — n=1 on an idea already known to be unstable across runs, so it is a reason to re-measure, not a finding.
- **Scope:** adapter implementation — completes D-049
- **Eval hook:** `AnthropicAdapter.complete(msgs, response_schema=s)` puts `output_config.format.schema == s` in the request and omits `output_config` entirely without a schema (both offline tests, no credentials required); a live call with `_PLAN_SCHEMA` returns parseable JSON on `claude-haiku-4-5` and `claude-sonnet-5`; removing `additionalProperties` from any object in the schema produces a 400 naming that field

## D-059: The Ollama base URL is configurable by environment variable, and CI runs the full pipeline against a stub server

- **Options:** leave the base URL hardcoded and test `plan`/`create` only at unit level with `FakeAdapter` · add a `--base-url` CLI flag · read a `GENESIS_OLLAMA_BASE_URL` environment variable · put a real API key in CI as a secret and exercise the hosted path
- **Choice:** `OllamaAdapter.__init__` takes `base_url: str | None = None` and resolves **explicit argument > `GENESIS_OLLAMA_BASE_URL` > `DEFAULT_BASE_URL`**. `ci/stub_server.py` is a stdlib HTTP server returning a canned `ready` plan, and CI runs `genesis create ... --adapter ollama` against it.
- **Reason:** Tier 1 gated only the deterministic scaffolder; everything upstream — argparse dispatch, the planner's round loop, `_extract_json`, `cmd_create`'s hand-off to `cmd_scaffold` — was covered by unit tests with `FakeAdapter` and by Tier 2's on-demand measurement, but **nothing ran the actual command on every push**. Both bugs found this session lived exactly there: `cmd_create` passed plan *content* to a parameter read as a *path* (D-044), and `--force` was ignored by `create` so scripted runs failed after paying for a plan. Unit tests covered those functions; nothing ran the CLI. A stub needs no key, no network and no model, so the gate stays deterministic and secret-free (D-018). An env var rather than a flag because a flag adds user-facing CLI surface for a niche case and must be documented in `--help`, while the variable also serves the genuine power-user case of Ollama on another host — and `OLLAMA_HOST` makes an env var the idiomatic shape. A real key in CI was rejected outright: it would spend money per push, make the gate non-deterministic, and behave differently on fork PRs, which receive no secrets.
- **The stub rejects a request carrying no `response_format`,** returning 400. That makes D-049's schema plumbing *gated* rather than assumed — verified both directions locally: with a schema the pipeline scaffolds and builds green, without one the adapter raises. A gate never observed failing is not known to work.
- **Cost accepted:** a fake server is a fake, and asserts nothing about real model behaviour — that is Tier 2's job, and the layering stays clean (deterministic gate here, measurement there). The equivalent is deliberately **not** built for Anthropic: the SDK honours `ANTHROPIC_BASE_URL` so it is possible, but a stub would have to imitate content blocks, usage and stop reasons well enough for the SDK's own response parsing, drifting whenever those expectations change — a fake of an API we do not control. The residual gap is that the offline Anthropic tests stub `messages.create` with a `**kwargs` function, so they would pass even if the installed SDK stopped accepting `output_config`; that is a dependency-upgrade risk caught by the live opt-in smoke test, and it is recorded in the README's limitations rather than papered over with a second stub.
- **Scope:** adapter configuration + CI
- **Eval hook:** `OllamaAdapter(base_url="x").`url` uses `x` even with the env var set; with only the env var set it is used; with neither, `DEFAULT_BASE_URL`. In CI, `genesis create "a cli todo app" out --adapter ollama --model stub --force` against the stub exits 0 having scaffolded a repo that installs and passes its own tests; a request without `response_format` makes the stub return 400

## D-060: Deploy target is AWS Lambda, not ECS Express Mode

- **Options:** ECS Express Mode behind an ALB, as originally locked · ECS with a public-IP task and no load balancer · Lambda with a Function URL
- **Choice:** Lambda + Function URL. Deploy early (target live mid-October) and **never pause**.
- **Reason:** the constraint that originally picked ECS was that App Runner closed to new AWS accounts — it said nothing about idle cost, and three constraints have since decided it. **(1) Credits expire.** The account holds $71.11 expiring Dec 16, 2026, so unspent credits are worth nothing and waiting saves nothing; an ALB bills ~$16/month whether or not anything runs, so ECS would exhaust the credits right as the December job hunt begins, while Lambda idles at ~$0 and outlives them on cash for pennies. **(2) HTTPS.** BYOK means users send their own API key, which is indefensible over plain HTTP; an ALB needs an ACM certificate and therefore a domain we own, whereas a Function URL includes HTTPS on an AWS-provided domain. **(3) A free planning tier is only feasible on Lambda** — 10 GB of memory and a 15-minute timeout make a small model baked into the container image possible, where the ECS equivalent is a 16 GB always-on task. Per-request billing also removes the seasonal pause/play question entirely: there is nothing to optimise when nothing idles.
- **Cost accepted:** cold starts, a 15-minute execution ceiling, and a 10 GB image limit constrain what the service can do — in particular `build_and_test()`'s runtime `pip install` is awkward in Lambda, so build verification stays a local and CI concern (the eval already proves that claim). Genesis also ships no container-orchestration experience, which ECS would have demonstrated.
- **Amends:** D-050, whose deferral rested on a budget-lapse premise that expiring credits invert, and closes the platform question left open in `docs/phase10-deploy.md`. Full reasoning and the comparison table: `docs/genesis-expansion.md`.
- **Scope:** deployment
- **Eval hook:** a Function URL serves `/scaffold` over HTTPS with no certificate of ours; AWS cost explorer shows ~$0 for a month in which the URL is live but unused

## D-061: Genesis is published to PyPI

- **Options:** clone-and-install only, as today · publish to PyPI · publish only after the deploy exists
- **Choice:** publish, ahead of the deploy (Sept 19–20 block).
- **Reason:** this is the largest accessibility gain available and the work is already done. `pip install <name> && genesis create "an idea" ./out` is one command against clone + venv + editable install + credentials — and **D-054 is what made it possible**: until the template moved inside the package, a published wheel would have installed a Genesis that could plan but not scaffold, so publishing before that fix would have shipped a broken product. It is also the honest answer to accessibility, where the deploy is the answer to credibility: anyone who can use Genesis and has a key gets a better experience from `pip install` than from a hosted service, because files land on their disk and no credential is handed to an unfamiliar server. Roughly half a block, no hosting, no bill, no abuse surface.
- **Cost accepted:** a public package name is effectively permanent and implies a versioning commitment — `0.1.0` stops being private. The distribution name will likely differ from the import name (`genesis` is almost certainly taken), which is a small, lasting inconsistency. `pyproject.toml` also needs `readme`, `license`, `classifiers` and `urls`, and adding `readme = "README.md"` will break the Docker build until `.dockerignore` stops excluding it.
- **Scope:** distribution
- **Eval hook:** `pip install <name>` into a clean venv on a machine with no source tree, then `genesis scaffold plan.json out` prints `Build and tests passed` — the same check that verified D-054, run against the published artefact rather than a local wheel

## D-062: Publish and deploy before a second template

- **Options:** build the template registry and a second template next, since the eval identified stack choice as the bottleneck · publish and deploy first, templates after · deploy only, and treat templates as a later extension
- **Choice:** README → `.venv` cleanup + PyPI → small-model experiment → deploy live by mid-October → template registry (~3 blocks from late October). Schedule in `docs/genesis-expansion.md`.
- **Reason:** the two optimise different things and it is worth being explicit about which. **For the CV, deploy first:** it fills the only *category* gap — nothing in the repo demonstrates cloud, IAM, TLS, or credential handling — whereas templates deepen design/eval/decision-log evidence that is already abundant. **For product quality, templates first:** they are the only remaining item that improves the success rate, and the Sept 12 eval measured the bottleneck precisely (roughly 3 of 10 expected-supported ideas lost per hosted model to stack choice, now that parse failures are gone). The tiebreaker is risk: a second template **doubles the eval surface**, and the eval is this project's strongest asset — D-001 already chose one verified template over three unverified ones on exactly that reasoning. Done without first extending the eval to score template *selection* (a distinct failure from selecting none), it would weaken the thing that makes the project good. Deploy and publish are also date-bound — credits expire Dec 16, the hunt starts in December — while templates are not.
- **Cost accepted:** the product's measured weakest point stays unfixed for roughly six weeks, and the README must keep reporting it. Templates land close enough to December that they may slip entirely; if that happens, the registry design (`docs/template-registry.md`) is what survives, which is a worse outcome than building it but better than having neither.
- **Scope:** project plan
- **Eval hook:** none — a sequencing decision. Verifiable only by the deploy being live by mid-October and the registry being started by late October; if neither holds, this ordering was wrong.

## D-063: Stack classification moves to a template registry; `supported` becomes derived

- **Options:** patch `_is_supported` in place · add a positional or scoring heuristic to fix the observed false negative · restructure into a registry where each template declares its own markers, keeping keyword matching for now
- **Choice:** a new module `genesis/template_registry.py` holding a frozen `Template` dataclass, an ordered `TEMPLATES` tuple, and `select_template(stack) -> Template | None`. `_is_supported` and `_UNSUPPORTED_MARKERS` are deleted; `_parse_plan` computes `supported = select_template(stack) is not None`, and `scaffold()` dispatches on the returned template rather than on `plan.supported`. Markers are matched on **word boundaries** instead of as substrings.
- **Reason:** the eval surfaced a false negative — a plan reading `['Python 3.10+', 'Jinja2 for templating', 'watchdog', 'Flask or http.server for dev server', ...]` was refused because one element mentions Flask as an optional dev server. **No keyword rule fixes that**, because whether Flask is the architecture or an incidental mention is not information keywords carry; a positional rule would have worked on this data and was **rejected as fitting the heuristic to its own eval set**, which is the standing rule in `docs/phase8-eval-tiers.md`. So the mechanism is unchanged and the *shape* is fixed instead, for three reasons that only matter once a second template exists: `supported: bool` is a degenerate case of "which template" and `scaffold` will need the template's identity, not a bool; the exclusion list is the **complement of the template set** rather than a property of Genesis (`flask`/`django`/`fastapi` are excluded only because no API template exists, and adding one moves them into that template's `requires`); and the ordered tuple makes precedence something written down rather than an artefact of iteration order. `select_template` is also the single seam the planner-label upgrade will swap, leaving every caller untouched. The module is new rather than living in `planner` or `scaffolder` because `scaffolder` already imports `Plan` from `planner`, so both need something neither can own.
- **Verified behaviour-preserving, so no eval re-run:** replaying all **157 persisted plans** through the new classifier produced **zero disagreements** with the recorded `supported` values. The word-boundary fix closes a latent defect (`gui` matched "guide", `ios` matched "Axios") that had caused no observed misclassification — every accidental hit landed on a plan already unsupported for other reasons — but would silently have refused a Python plan mentioning a guide. The general rule: **re-run when a change can alter a recorded outcome; when it provably cannot, replaying the persisted plans is the cheaper proof.**
- **Cost accepted:** the Flask false negative **remains open** and is published as such in `EVAL.md`. A behaviour change also lands: a hand-written plan claiming `"supported": true` alongside a non-Python stack now receives the generic scaffold rather than a forced Python render — `plan.supported` is still serialised and reported, but `scaffold` no longer consults it, so the two cannot disagree. `select_template` assumes every template is src-layout with a package directory; a flat-layout template would need a `package_dir` field.
- **Path resolution is public API, learned the hard way.** The registry also exposes `template_dir(template)`, resolving `Template.path` against the package's `templates/` directory — it lives beside the `path` field it resolves rather than in `scaffolder`. This exists because the Docker CI job asserted against `genesis.scaffolder._TEMPLATE_DIR`, a **private** name, and broke the moment this refactor renamed it. The replacement check iterates the whole registry (`all(template_dir(t).is_dir() for t in TEMPLATES)`), so a second template is verified automatically with no CI edit. General rule now in CLAUDE.md: **CI and Docker steps assert against public API, and against the whole set rather than one hardcoded path.**
- **Scope:** project structure — supersedes D-028's implementation, not its reasoning
- **Eval hook:** `select_template(['Python 3.11', 'a guide to usage'])` returns the python-cli template (previously refused via `gui`); `select_template(['Rust', 'tokio'])` returns `None`; replaying `evals/results/*.jsonl` yields zero disagreements with recorded `supported` values

## D-064: Verification leaves no trace, and proves the entry point runs

- **Options (residue):** leave the verification venv in the generated repo as today · add `.venv` to the template's `.gitignore` · build the venv outside the repo · prevent what can be prevented and delete the rest
- **Options (entry point):** keep asserting the console script *file* exists · run it · fold the check into `tested`
- **Choice:** `build_and_test()` prevents two residues and deletes the third, and runs the generated repo's console script with `--help` between install and test. `BuildResult` gains `entrypoint: bool`; `ok` becomes `installed and entrypoint and tested`. The template also ships a `.gitignore` (`.venv/`, `__pycache__/`, caches, `.DS_Store`) — a consequence of the above: the user now creates their own virtualenv inside the repo, and a generated project that does not ignore it would show thousands of files in `git status` on day one. Verified to survive both `copytree` and the wheel build, since build backends sometimes drop dotfiles — the same failure mode as D-054.
- **Reason (residue):** every generated repo arrived with **47 MB** of verification leftovers against 28 KB of project — a `.venv`, a `.pytest_cache`, and `__pycache__` directories. Worse than size, **a venv is non-portable by construction**: `pyvenv.cfg` records absolute paths (`home`, `executable`, and the creation `command`) and `bin/python` is a symlink to the base interpreter, so a repo scaffolded inside a container carries paths to an interpreter that does not exist on the host. Gitignoring was rejected as making the mess invisible rather than absent — the megabytes and the broken symlinks remain, and it is the *user's* repo to gitignore. Building the venv elsewhere was rejected because it fixes only one of the three: pytest still runs inside the repo, so `.pytest_cache` and `__pycache__` appear regardless. So: **prevention where possible, deletion where not** — `PYTHONDONTWRITEBYTECODE=1` in the subprocess environment and `-p no:cacheprovider` on pytest mean those two are never created (nothing to forget, and nothing left behind if the process is killed mid-run), while the venv must exist during verification and is removed in a `finally`, which covers all four exit paths including the failure returns. `ignore_errors=True` so a cleanup failure cannot mask the real error — the same shape as the `finally` bug found in `CountingAdapter`.
- **Reason (entry point):** the slow eval test proved the console script was installed by asserting a *file existed* at `.venv/bin/<name>`. Deleting the venv removed that file, and the check was weak anyway — a path existing says nothing about whether it runs. Running `<name> --help` proves three things at once: the script installed, it is executable, and its imports resolve. It is a **third** `BuildResult` field rather than folded into `tested` for D-032's own reason — the failure modes have different diagnoses: install failing means packaging is broken, the entry point failing means `[project.scripts]` wiring or an import error, tests failing means the code is wrong. The name is read from the generated repo's own `[project.scripts]` rather than guessed from the directory, so it still works for a template with a different layout.
- **Cost accepted:** `ok` is now **stricter** — a repo whose console script does not run fails the CI gate where it previously passed. Verification is marginally slower for the extra subprocess. `cmd_scaffold` was switched from `res.installed and res.tested` to `res.ok`, which had been correct only by accident. The generated repo no longer arrives with a working environment, so the template's README must tell users to create one.
- **Amends:** D-032 — the fresh-venv-via-subprocess mechanism is unchanged; the result shape, the success condition, and the cleanup are not.
- **Scope:** template-constant
- **Eval hook:** after `build_and_test()` on a scaffolded repo, the directory contains only `.gitignore`, `PLAN.md`, `README.md`, `pyproject.toml`, `src/`, `tests/` — **36 KB, no `.venv`, no `.pytest_cache`, no `__pycache__`** — and `BuildResult(installed=True, entrypoint=True, tested=True)`; a template whose `.gitignore` stops shipping in the wheel fails `test_scaffold_structure`

## D-065: The CLI prints setup commands on success; it does not run them

- **Options:** print nothing and rely on the generated README · print the setup commands after a successful build · run `venv` + `pip install` automatically for the user · add a `--setup` flag
- **Choice:** on the supported path, after `build_and_test()` reports `ok`, print the three commands (`cd`, create-and-activate a venv, editable install). The helper lives in `interface.py` per D-045. Nothing is executed on the user's behalf.
- **Reason for printing:** D-064 stopped shipping a virtualenv, so the generated repo no longer arrives with a working environment. Without a venv, `pip install -e ".[dev]"` fails on modern Homebrew, Debian, Ubuntu and Fedora with `error: externally-managed-environment` (PEP 668) — verified on this machine. So the message does not save a lookup, it **prevents a wall**: a beginner's first action in a brand-new project would otherwise produce an opaque error about system package management that has nothing to do with their project. Relying on the README was rejected as unrealistic for the *immediate* next action, though the README keeps the same instructions for whoever opens the repo later — different moments, both cheap.
- **Reason for not executing:** running the commands would **recreate exactly what D-064 removed**. The distinction between "verification leftover" and "helpfully provided environment" is intent only; the artefact is identical — tens of megabytes, absolute paths in `pyvenv.cfg`, and via Docker a venv whose interpreter does not exist on the host. Three further objections stand independently: `genesis scaffold` means "make me a repo", and silently creating environments and installing packages is a surprising side effect; `.venv` + pip is one workflow among several (uv, poetry, conda, containers) and choosing for the user is a stronger claim than a scaffolder should make; and it roughly doubles scaffold time for something that may be deleted immediately. A `--setup` flag would mute the surprise objection and none of the artefact ones. **`source` cannot be automated in any case** — activation mutates the parent shell's environment, which a child process cannot do — so even the executing version would still leave the user a command to type.
- **General principle:** tell the user what to run; do not run it for them. The exception is running something for *our own* purposes, which is what `build_and_test` does — and why it cleans up after itself.
- **Cost accepted:** four lines of output after every successful scaffold, and the instructions assume pip rather than `uv`, which is increasingly the default for this workflow. Adapting to a detected `uv` is a future option, not worth a conditional on a tool that may not be installed.
- **Scope:** CLI behaviour
- **Eval hook:** `genesis scaffold plan.json out` on a supported plan prints a `Run:` block; the same command on an unsupported plan prints the "unsupported stack" line and **no** `Run:` block, since there is no package to install

## D-066: `--force` overwrites a previous Genesis scaffold, and refuses anything else

- **Options:** keep `--force` meaning "delete whatever is at this path" · refuse unless the directory is empty · refuse unless the directory looks like a previous Genesis scaffold · prompt for confirmation
- **Choice:** `cmd_scaffold` removes the target only when it is empty **or** contains a `PLAN.md`. Otherwise it prints a refusal naming the directory and exits 1, deleting nothing.
- **Reason:** found in a pre-publication review, and it is a data-loss bug rather than a rough edge. `--force` ran `shutil.rmtree(target_path)` on *any* existing path, so `genesis scaffold plan.json ~/Documents --force` deleted `~/Documents`. With `.` the outcome was worse than deletion alone: the working directory's contents were destroyed **and the command then failed** (exit 1), because `rmtree` removed the cwd out from under the scaffold — the user lost everything and got no repo. Both `.` and a project-parent directory are entirely plausible arguments, and the tool is about to be installable by strangers. `PLAN.md` is the ownership marker because **every** scaffold writes one on both the template path and the generic path, so it is a reliable signal and needs no extra state. `--force` therefore now means "overwrite **my** previous scaffold", which is what anyone typing it intends; "delete this arbitrary directory" was never the intent, only the implementation.
- **Cost accepted:** a user who genuinely wants to scaffold over a non-Genesis directory must remove it themselves — a deliberate extra step, and the right default when the alternative is irreversible. The marker is also spoofable (`touch PLAN.md`), which is fine: this guards against typos, not against a determined user.
- **Scope:** CLI behaviour
- **Eval hook:** in a directory containing `thesis.txt` and no `PLAN.md`, `genesis scaffold plan.json . --force` exits 1, prints `Refusing to delete`, and **leaves the file intact**; the same command in a directory containing `PLAN.md` overwrites it and exits 0

## D-067: Untrusted plan fields are escaped, and slugs are always valid identifiers

- **Options:** trust plan fields because they come from our own planner · validate and reject malformed fields · escape on the way out and coerce slugs to valid identifiers
- **Choice:** `plan.summary` is written into the generated `pyproject.toml` via `json.dumps` — TOML basic strings are JSON-compatible for this case — replacing the quoted placeholder rather than its bare text. `normalize()` extends its leading-digit guard to Python keywords and any slug that is not a valid identifier, prefixing `p_`.
- **Reason:** D-044 made `scaffold` accept **any** plan JSON, explicitly including hand-written files, so plan fields are untrusted input reaching a config file and a package name. A summary containing a `"`, a newline or a trailing backslash produced **invalid TOML** and therefore a generated repo that could not install; a project named `Class` or `Import` produced a package directory that installs but cannot be imported (`SyntaxError` on the entry point). Both were **latent — zero occurrences across 157 recorded plans** — and that is precisely the argument for fixing them: the corpus is model output, and a human writing a summary with a quotation mark has no corpus at all. Escaping was chosen over validate-and-reject because a quoted summary is *legitimate* input; refusing it would be a worse answer than handling it.
- **Noted:** the keyword case was localised immediately by the `entrypoint` field added in D-064 for an unrelated reason (`installed=True, entrypoint=False, tested=False`). Before that it would have surfaced as a confusing pytest failure.
- **Cost accepted:** `p_class` is an ugly package name, but it is valid and installable, and it matches the existing treatment of `7guis` → `p_7guis`. The TOML replacement is now coupled to the placeholder being quoted in the template's `pyproject.toml` — if that formatting changes, the substitution silently stops matching.
- **Scope:** template-constant
- **Eval hook:** `normalize("Class") == "p_class"`; a plan whose summary is `A "quoted" tool.\nWith a newline` scaffolds a repo whose `pyproject.toml` parses with `tomllib` and whose `build_and_test` returns `ok=True`

## D-068: Published to PyPI as `genesis-agent`; the import name stays `genesis`

- **Options:** `genesis` (taken) · `genesis-cli` (taken) · `genesis-scaffold` / `genesis-scaffolder` · `genesis-project` · `genesis-agent`
- **Choice:** distribution name **`genesis-agent`**. The import name (`import genesis`), the package directory (`src/genesis/`) and the console script (`genesis`) are all unchanged. `pip install genesis-agent`, then `genesis create "an idea" ./out`.
- **Reason:** `genesis` on PyPI is a live, maintained FreeSWITCH ESL library (v2026.7.1), so it is genuinely occupied rather than squatted, and `genesis-cli` is taken too. Of what remains, `genesis-agent` is the only candidate that describes the **whole** pipeline: the package ships the planner, both adapters, and all three commands, so a name built on "scaffold" would advertise half of it. It also matches the README's own first sentence — "An AI agent that turns a project idea into a structured, buildable plan and a scaffolded starter repo". `genesis-project` was the runner-up: accurate but says nothing.
- **Cost accepted:** "agent" is an inflated term, and this project's README deliberately works against that inflation ("Most of Genesis is not the model call") — so the name leans on a word the project is otherwise understated about. Accepted because the distribution name is typed once at install time, while everything encountered thereafter is `genesis`. A PyPI name is also effectively permanent, so this is not cheaply revisited. The split needs one line in the README ("Installs as `genesis-agent`; imports and runs as `genesis`") or it reads as a mistake.
- **Packaging consequence, found by building it:** hatchling infers the wheel's package directory from the project name, so any distribution name other than literally `genesis` makes it search for `src/genesis_agent/` and fail with an opaque *"Unable to determine which files to ship inside the wheel"*. **`[tool.hatch.build.targets.wheel] packages = ["src/genesis"]` is mandatory**, not optional — the previous build only worked because the two names coincided.
- **Also required by the metadata:** `readme = "README.md"` makes the README a build input, which breaks the Docker build until `.dockerignore` stops excluding it *and* the Dockerfile copies it. A `LICENSE` file is needed for `license-files`; MIT chosen, since an unlicensed repo is legally all-rights-reserved and unusable by the people most likely to look at it. No `Typing :: Typed` classifier: the code is annotated but ships no `py.typed` marker, and claiming it without one would be false.
- **Scope:** distribution — implements D-061
- **Eval hook:** `python -m build --wheel` produces `genesis_agent-0.1.0-py3-none-any.whl` whose `METADATA` reads `Name: genesis-agent`, containing the `genesis/` package and all nine template files; installing it into a clean venv and running `genesis scaffold plan.json out` prints `Build and tests passed`
