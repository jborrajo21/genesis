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
- **Amended by D-080 (Sept 18, 2026):** both halves of this entry's economics were inverted by facts that arrived later. The platform is **Lambda, not ECS Express Mode** — per-request billing means idle cost is ~$0, so the budget argument for waiting evaporates, and unspent credits (now known to **expire Dec 16, 2026**) are worth nothing. The date moves *earlier*, to **live by mid-October**. The deferral recorded here was still correct on the information available; the reasoning behind it no longer is.
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

## D-069: MIT licence, with the commercialisation path deliberately left open

- **Options:** no licence (the status quo until Sept 13) · MIT · Apache-2.0 · AGPL-3.0 · a source-available licence such as BSL
- **Choice:** **MIT**, shipped now. Copyright remains solely with the author (all 43 commits to date).
- **Reason:** the licence's job right now is to remove friction for the people this repo exists to reach — engineers evaluating it from December onward. **No licence is the one clearly wrong answer:** a public repo without one is all-rights-reserved, so nobody may legally use it, and several employers' policies bar engagement outright. AGPL is the genuine answer to "I may sell this as a service later", and it was rejected because many companies ban AGPL outright — it works directly against the *current* goal at exactly the wrong moment. A source-available licence (BSL) would forfeit the open-source credibility signal, which is part of what the repo is for. MIT over Apache-2.0 on brevity and recognisability; Apache's patent grant matters little for a project with no patents.
- **What this does and does not foreclose:** version 0.1.0 and everything released under MIT is **permanently MIT** — it cannot be revoked, and anyone who takes a copy keeps those rights. But the author owns the copyright on every line, so **future versions can be licensed however he likes, without anyone's consent.** Deleting the licence commit was considered and rejected as pointless: it would not revoke rights already granted, unreferenced commits remain reachable, and with 0 forks and 1 star the exposure window closed harmlessly. **Open core does not require relicensing** — it *uses* a permissive core; MIT and open core are not alternatives.
- **The real cost is not the code, it is accumulated expectation.** A snapshot of ~1,500 lines with no users is worth nothing to a competitor. What grows over time is the cost of a *later* relicense: Elastic, HashiCorp, Redis and Terraform all triggered immediate community forks. That cost is proportional to adoption under the permissive terms — zero today, material with a real user base.
- **The move if this becomes a product:** build commercial value where a fork cannot follow — hosted infrastructure, brand, development velocity, support and SLAs — rather than in code, which is always forkable. The preferred path is **open core with no relicensing at all**: the CLI stays MIT as marketing and credibility, and the commercial part is simply *never published*. The deploy plan (`docs/phase10-deploy.md`) already has this shape — a keyless free tier plus BYOK.
- **Cost accepted:** anyone may sell copies of any MIT-released version, including this one. Judged remote and cheap at current scale, and not avoidable without sacrificing the adoption the repo is being published for.
- **Contributions: DCO, no CLA, and the consequence accepted.** Sole authorship is what makes future relicensing unilateral, and the first merged external pull request ends that, since contributors hold copyright in their own work. **A DCO does not change this** — it certifies provenance and the right to submit under MIT; it transfers nothing. Only a CLA with a relicensing grant would preserve the option, and it is deliberately **not** adopted: a CLA is real friction that deters contributors, and the option it protects is one this very entry recommends against using. The chosen path is open core *without* relicensing, so unilateral relicensing is not needed, and refusing or gating contributions would weaken the open-source signal the repo is published for. `CONTRIBUTING.md` therefore asks for `git commit -s` and states the consequence plainly rather than pre-empting it.
- **Scope:** project
- **Eval hook:** none — a legal and strategic decision. `LICENSE` exists, `pyproject.toml` declares `license = "MIT"` with `license-files = ["LICENSE"]`, and `git log --format='%an'` returns exactly one name. Not legal advice; revisit with a lawyer before money is attached.

## D-070: `genesis/__init__.py` exports a public API surface

- **Options:** leave it empty and require submodule imports (`from genesis.planner import Planner`) · export a curated set of names · export everything
- **Choice:** ten names — `Completion`, `Message`, `ModelAdapter`, `ToolDef`, `Phase`, `Plan`, `Planner`, `BuildResult`, `build_and_test`, `scaffold` — with a matching `__all__`. Shipped in 0.1.1.
- **Reason:** the package is now installable by strangers, and an empty `__init__.py` meant `import genesis` yielded nothing: a library user had to know the internal module layout before importing anything. The exported set is the three things someone would actually use — the adapter Protocol and its data types (to write their own backend), the planner and its output type, and the scaffolder entry points. Deliberately **not** exported: `agent`, `tools`, `fakes`, `cli`, `core`, `interface`, `template_registry`. `agent` and `tools` are importable and tested but the CLI does not use them, so promoting them to the front door would advertise them as the supported path; the rest are internals or test support.
- **Cost accepted:** whatever appears in `__all__` is now API, and moving or renaming any of it is a breaking change requiring a major version. That is the point of choosing a small set — the alternative (export everything) would have frozen the entire module layout. `agent` and `tools` remain importable by their full path, so nothing is hidden, merely not promoted.
- **Related and deliberately absent:** no `py.typed` marker ships, so consumers' type-checkers treat the package as untyped despite the annotations. Adding it commits to keeping those annotations correct across releases; until that commitment is made, the `Typing :: Typed` classifier must stay off the metadata, since claiming it without the marker would be false.
- **Scope:** distribution
- **Eval hook:** `python -c "import genesis; print(genesis.__all__)"` from a clean index install returns the ten names; `genesis.Planner` and `genesis.scaffold` resolve without importing a submodule

## D-071: `status` is constrained by enum, not by prose

- **Options:** leave `status` as `{"type": "string"}` and rely on the planning instruction · validate and retry on an unexpected value · constrain it in the schema with `enum: ["need_info", "ready"]`
- **Choice:** `"status": {"type": "string", "enum": ["need_info", "ready"]}` in `_PLAN_SCHEMA`. Verified accepted by Anthropic's `output_config.format` and by Ollama's grammar-constrained decoding.
- **Reason:** the schema told the grammar "a string goes here" when the contract has exactly two legal values. What kept output valid was the **prose** in `_PLANNING_INSTRUCTION`, which shows both shapes — and instruction-following is a capability, so the guarantee held only while models were capable enough. Across **156 recorded runs** the three larger models never deviated. The 1–1.5B models deviated **7 times in 52**, emitting `plan` (×5), `neutral`, and `need-info` — the last being *correct apart from a hyphen*, rejected on punctuation by a contract the grammar could have enforced outright. Same class of gap as D-058: a constraint mechanism available and not fully used, and the same shape as `additionalProperties: false`, which made stray keys structurally impossible rather than merely discouraged.
- **Not eval-tuning.** `docs/phase8-eval-tiers.md` forbids changing the system in response to eval findings, and this is deliberately outside that: the field was under-specified for **every input from every model**, so this is a correctness fix the eval revealed rather than a fit to the eval set. The precedent is D-058 — found by the eval, fixed, re-measured.
- **Re-run scope, decided on evidence:** the larger models are **not** re-run. D-063's replay method does not apply — a schema change affects *generation*, not parsing, so there are no recorded outputs to replay it against. The judgment instead rests on the 156/156 compliance above: the constraint never binds for them, and a re-run would cost roughly 75 minutes and produce differences indistinguishable from the run-to-run variance already measured (Sonnet chose Python 2 of 4 then 3 of 4 on identical input). The two small models **are** re-run, because the constraint binds for them 7 times in 52. Same change, opposite answer, decided by whether it can alter a recorded outcome.
- **Cost accepted:** the plan's legal statuses are now stated in three places — the prose instruction, the enum, and `_round`'s branching — so a fourth status would need adding to all three. The Sept 14 small-model figures therefore come from a different schema than the Sept 12 ladder, which must be stated wherever they are compared.
- **What it will not fix:** 4 of the 11 observed failures are unrelated — three are the model looping inside the grammar (valid structure, repeated, one reaching 18,000 characters at only ~2,000 tokens, well under the 10,000 cap) and one is the adapter's 120s-per-call timeout. Those are genuine limits of models this size and are expected to survive.
- **Scope:** planner contract
- **Eval hook:** `llama3.2:1b` and `qwen2.5:1.5b` on *a Kubernetes operator in Go* — which produced `unexpected status: 'plan'` twice before — both return `need_info` with the enum in place; Anthropic accepts the schema without a 400

## D-072: The free planning tier is measured, declined, and documented

- **Options:** ship Tier C with `qwen2.5:1.5b` anyway, for the sake of a free open endpoint · test a larger model that still fits Lambda · drop the tier entirely · **decline it now, publish the measurement, and name the conditions for revival**
- **Choice:** the deploy ships **Tier A (keyless `/scaffold`) and Tier B (BYOK `/plan`) only.** The Tier C measurement is published in `EVAL.md` with the pre-registered thresholds shown beside the results.
- **Reason:** both candidates missed the binding metric — idea → buildable repo of 20% (llama3.2:1b) and 50% (qwen2.5:1.5b) against a threshold of 60% fixed before the run. qwen2.5 is close enough that overriding would have been tempting, which is precisely why the number was fixed in advance: a threshold that moves to admit the thing that missed it was never a threshold. **The purpose matters more than the margin, though.** Tier C was specified to answer "is a free planning tier *usable*", and at 50% half of visitors would get a broken or refused plan — worse than not offering it. A separate case exists for shipping it as a *demonstration* of packaging a model into a Lambda container, which the threshold does not govern; that case is rejected on two independent grounds below.
- **The constraint nobody has measured.** Every latency figure was taken on Apple Silicon with GPU acceleration; Lambda is CPU-only, plausibly 3–4× slower, plus a cold start loading the model from the image. qwen2.5's 12-second median could be 50–70 seconds in production. **The free tier would be slow as well as mediocre**, and quality was being optimised while the binding constraint went untested. This also settles the "try a larger model" option: a 3B fits the 10 GB image at ~2 GB but is roughly twice as slow again, trading a failed quality threshold for a failed latency one.
- **Tier A already provides the free clickable experience**, and does it better: a prefilled plan through the keyless endpoint returns a verified repo instantly and every time. Tier C's marginal value is only "type your own idea" versus "generate from a prepared one" — narrow, against a 60-second wait for a coin-flip result.
- **The negative result is the artefact.** This is the one place in the project where a bar was set in advance, missed, and said so. That is worth more than a slow endpoint nobody would use twice, and it is not something that can be retrofitted.
- **Revival conditions, in order:** (1) close the Flask veto — three of qwen2.5's five losses trace to it, and whether that lifts it past 60% is genuinely unknown; (2) measure real Lambda CPU latency with one throwaway function and a single timed invocation — that is the untested gate, and no further local model comparison tells you anything about it; (3) re-test against the same thresholds. If it then clears both, ship it *and* say it was the second attempt.
- **Cost accepted:** the deploy demonstrates no ML-infra work — no model packaging, no inference hosting — which was Tier C's strongest argument. Small models also remain in `evals/main.py` as commented rungs, so the ladder is reproducible without being re-run by default.
- **Scope:** deployment — closes the open question in `docs/phase10-deploy.md`
- **Eval hook:** `EVAL.md` publishes both models' figures against the thresholds; `docs/phase10-deploy.md` records Tier C as declined with the revival conditions

## D-073: Genesis errors get a base class

- **Options:** raise `ValueError` for deliberate failures and lean on existing clauses · one flat `InputUnavailableError(Exception)`, matching how `PlannerError` was defined · a `GenesisError(Exception)` base with typed subclasses under it · no new types at all, reusing `EOFError` and adding clauses per handler
- **Choice:** `src/genesis/errors.py` defines `GenesisError(Exception)` and `InputUnavailableError(GenesisError)`; `PlannerError` is reparented onto `GenesisError`; `GenesisError` is exported from `genesis/__init__.py` (eleventh name, amending D-070's ten).
- **Reason:** the Lambda handler in `docs/phase10-deploy.md` Task 1 has to map exceptions to status codes, and a handler cannot distinguish *Genesis raised this deliberately* from *a stdlib call blew up* unless the two have different types. A base class makes that mapping one clause (`except GenesisError` → 400, `except Exception` → 500) instead of an enumeration that must be revisited every time a typed error is added. The flat option was cheaper today and re-opens the same question at every future error; reusing `ValueError`/`EOFError` cannot express the distinction at all, which is the distinction the status mapping is made of.
- **The mechanism this introduces, and the cost of it.** Clause matching is top-to-bottom, first match wins, so **the type an error is raised as decides which handler claims it** — and changing that type silently reroutes it. Both directions were hit while implementing this: reparenting `PlannerError` under `GenesisError` means an `except GenesisError` placed *above* `except PlannerError` would swallow planner failures under the wrong message; and moving the missing-template failure from `FileNotFoundError` to `GenesisError` took it out of `cmd_scaffold`'s `OSError` clause and dropped it into the catch-all, which printed a correct message prefixed `Unexpected error:` — a message contradicting itself. Neither is caught by the type checker or by the suite. The cost accepted is that every new subclass requires re-reading the four handler stacks in `core.py`, and `test_planner_error_is_a_genesis_error` exists to stop the reparenting being undone by tidying.
- **Cost accepted:** a new public name that a major version is now needed to move (D-070's terms), and one more module. `InputUnavailableError` is deliberately **not** exported — a consumer catching Genesis failures needs the base; the leaf is an implementation detail until something outside the package needs to branch on it.
- **Scope:** distribution — public API surface
- **Eval hook:** `python -c "from genesis import GenesisError; from genesis.planner import PlannerError; assert issubclass(PlannerError, GenesisError)"` exits 0; `pytest -q tests/test_core.py -k genesis_error` passes

## D-074: Interactive input goes through one boundary wrapper

- **Options:** add `except EOFError` clauses to the handler stacks in `core.py` · wrap every `input()` call in `interface.py` behind one function that raises a typed error · guard each of the nine call sites individually
- **Choice:** `interface._prompt(message)` is the only way the package reads a line. It catches `EOFError`, raises `InputUnavailableError` with a message naming the fix, suppresses the exception chain with `from None`, and owns the `.strip()` that all nine call sites previously repeated.
- **Reason:** handler clauses protect the nine prompts that exist; the wrapper protects the ones not yet written. It is **more** edits today — nine call sites against three clauses — and the payoff is that a tenth prompt added later cannot leak, because there is only one way to read a line. Same argument as `additionalProperties: false` in D-071: make the wrong thing structurally impossible rather than currently absent. `KeyboardInterrupt` is deliberately **not** caught here — it is a `BaseException`, it can arrive anywhere rather than only at a prompt, and it belongs one layer up in `cli.py`, which returns 130 (128 + SIGINT).
- **What was actually broken.** Confirmed on a clean 0.1.2 install, not inferred: `genesis create` and `genesis plan` under `< /dev/null` printed `Unexpected error: EOF when reading a line`, and **`genesis scaffold` printed a 16-line traceback** — `cmd_scaffold_file` wrapped `_get_json_path()` in a `try` catching only `OSError`, with no catch-all on that path at all. `cmd_scaffold` was also missing an `OSError` clause its two siblings had, so `shutil.rmtree` and scaffold write failures reached users as `Unexpected error:` too. Five distinct failures behind one symptom; `docs/phase10-deploy.md` B1 had recorded three.
- **Why it is a deploy prerequisite, not tidying:** a Lambda turns an uncaught exception into a 502 with no body, and every one of these is an error a stranger with no logs would hit. The typed-to-status mapping in Task 1 can only be as good as what the core raises.
- **Cost accepted:** `interface.py` grows a layer that a reader must go through to see what a prompt does, and `_prompt` now owns stripping, so a future prompt wanting raw input has to bypass it deliberately. Both are acceptable against nine call sites that can no longer be got wrong individually.
- **Scope:** CLI behaviour
- **Eval hook:** `genesis create`, `genesis plan` and `genesis scaffold`, each with `< /dev/null`, print `✗ Genesis needs interactive input here…` and exit 1 with no traceback; `pytest -q tests/test_core.py -k "prompt or stdin"` passes

## D-075: `py.typed` ships, and mypy enforces it in CI

- **Options:** keep D-070's position and stay untyped to consumers · ship the marker and the `Typing :: Typed` classifier with nothing checking the annotations · ship the marker **and** gate `mypy` in CI · ship the marker and gate `mypy --strict`
- **Choice:** `src/genesis/py.typed`, the `Typing :: Typed` classifier, `mypy` in the `dev` extra, `[tool.mypy]` pointed at `src/genesis`, and one `- run: mypy` step in the existing `genesis` CI job. Default settings, **not** `--strict`.
- **Reason:** D-070 refused the marker because it is a promise — PEP 561 tells every consumer's type checker to rely on these annotations — and nothing in the project verified the annotations were correct. That objection is answered by enforcement, not by intention, so the marker and the checker land together or not at all. **The measurement made the commitment affordable:** mypy at default settings found 5 errors, 4 real (the fifth being the optional `anthropic` import), and **none of them were live bugs** — two were an invariant a flat dataclass cannot express, one a needlessly loose parameter, one a missing annotation. Four small fixes, not a refactor.
- **Why not `--strict`:** 24 errors, mostly missing annotations on internals and bare generics — a real piece of work whose payoff is internal, while the marker's payoff is external and is fully delivered by the public signatures being correct. `--strict` stays available as a later tightening; shipping the marker does not depend on it.
- **Cost accepted:** a third tool in the dev extra and a third gate on every push, against a minimalism policy whose default answer is no. Bought with the October deploy in view: `lambda_handler.py` is new code written against an event-shape contract, and a wrong annotation there costs debugging time against CloudWatch logs rather than a red local run. The step was added to the existing `genesis` job rather than a new job, so the CI surface grows by one line.
- **Environment dependence, learned the hard way:** `mypy` gives different answers depending on whether the optional `anthropic` extra is installed, because `[[tool.mypy.overrides]] ignore_missing_imports` silences the module when absent. A green run in an environment without the extra is a weaker statement than it looks. This is why D-076 changes the CI job to install `.[dev,anthropic]`.
- **Scope:** distribution — amends D-070, whose "deliberately absent" note no longer holds
- **Eval hook:** `mypy` exits 0 in an environment with the `anthropic` extra installed; `unzip -l dist/*.whl | grep py.typed` shows `genesis/py.typed`; the built wheel's `METADATA` contains `Classifier: Typing :: Typed`

## D-076: The Anthropic call is checked by the type checker, not by a hand-written assertion

- **Options:** a test asserting against the SDK's typed parameter model, as `docs/phase10-deploy.md` B3 framed it · a second stub server (rejected by D-059) · `# type: ignore[call-overload]` on the call and close B3 another way · **pass explicit keyword arguments so mypy resolves the real overload, and install the extra in CI so it is checked there**
- **Choice:** `complete()` calls `messages.create(...)` with every parameter named, using `anthropic.omit` where a value is absent, instead of building a `kwargs` dict and splatting it. `_to_anthropic` is annotated `-> "MessageParam"` under `if TYPE_CHECKING:`, so no runtime import is added and the package still imports without the extra. CI installs `.[dev,anthropic]`.
- **Reason:** B3's concern was that the offline tests stub the `anthropic` module and would pass even if the SDK stopped accepting `output_config`. The dict form made that worse than recorded: `kwargs` inferred as `dict[str, object]` erases which key holds what, so **mypy could verify nothing about the call at all** — it reported `No overload variant matches`, which is the same hole seen from the other side. Explicit keywords let the overload resolve, and then `output_config`, `system`, `tools`, `model` and `max_tokens` are all checked against whatever SDK version is installed. That is a continuously-maintained assertion with nothing to maintain, and it is strictly stronger than the hand-written test B3 asked for, which would have pinned one parameter at one point in time.
- **The CI install line is the load-bearing part.** With `.[dev]` alone the `ignore_missing_imports` override silences the adapter and the gate does not exist — the developer's laptop would be a stricter check than CI, which is the failure mode D-059 and the Phase 9 container gate both exist to prevent.
- **Two latent defects found while doing it**, neither ever observed: `Message.tool_call_id` is optional but the API requires it, so a tool message without one would have produced a 400 at runtime — it now raises `ValueError` naming the field; and `_STOP_REASON_MAP` does not cover `pause_turn` or `model_context_window_exceeded`, which currently fall through to `StopReason.OTHER`. **The map is deliberately not changed here** — mapping `model_context_window_exceeded` to `TRUNCATED` would alter planner behaviour, since `_round` raises on `TRUNCATED`, and that is a behaviour change rather than a bug fix. It belongs on the open-findings list.
- **One test's premise genuinely expired.** `test_no_output_config_without_schema` asserted `"output_config" not in captured`; with explicit keywords every parameter is always passed, with `omit` standing in, so the assertion now reads `captured["output_config"] is stub_omit`. Nothing changes on the wire — the SDK strips `omit` before serialising — but the stub sees the key. Recorded because changing a test to make it pass is normally the suspicious move, and the distinction is that the old assertion described an implementation detail of the call, not the behaviour under test.
- **Cost accepted:** CI installs one more package on the `genesis` job, and the adapter now names every parameter, so adding one means editing the call rather than a dict. Both are the point: the call site is now the thing mypy reads.
- **Scope:** adapter — closes B3
- **Eval hook:** `pip install -e ".[dev,anthropic]" && mypy` exits 0; renaming `output_config=` to a parameter the SDK does not accept fails `mypy` with `No overload variant of "create" matches` — verified by doing it. **Note the limit:** *deleting* the argument type-checks fine, because it is optional on the SDK's side. The type checker guards the parameter's name and value type, not its presence; presence is what `test_response_schema_becomes_output_config` covers. The two gates are complementary, and neither replaces the other.

## D-077: The `anthropic` extra declares a floor and no ceiling

- **Options:** leave it bare (status quo) · floor only, `anthropic>=0.119` · floor plus a tight ceiling, `>=0.119,<0.120` · floor plus ceiling plus a scheduled CI run that installs the latest SDK
- **Choice:** `anthropic = ["anthropic>=0.119"]` in `pyproject.toml`. `Dockerfile:27` is deliberately left unpinned to match.
- **Reason:** the framing in `docs/phase10-deploy.md` was off by one — **`anthropic` is pre-1.0 (0.119.0)**, and for a `0.y.z` package SemVer puts breaking changes in *minor* bumps, so the `<1.0` ceiling the doc implied would protect against nothing. A tight ceiling would work, and is rejected on maintenance grounds: it goes stale at the SDK's next release and needs a bump-and-test cycle a weekends-only project will not perform. Worse, a stale ceiling **breaks users whose environment already has a newer `anthropic`** — a resolver conflict at install time, which is a more confusing failure than the one being prevented.
- **What makes the floor defensible is new as of today.** D-076 put `mypy` in CI against the *real installed SDK*, so a changed `messages.create` signature — precisely the shape of "a bump lands unannounced" — now fails the build. Combined with the live smoke test, the project detects the break rather than preventing it. That is the right trade for one maintainer: a clear failure at build time beats a stale constraint nobody maintains.
- **Cost accepted, stated plainly:** CI only runs when something is pushed. A user installing fresh during a three-week quiet spell hits a breaking SDK release **before** the project does. A scheduled weekly CI run would close that gap and was rejected — a new workflow, a recurring notification to triage, and CI minutes spent on a dependency that has never broken this project, against a minimalism policy whose default answer is no.
- **The container is unaffected either way:** an image is immutable once pushed to ECR, so drift exists only at rebuild time. Pinning the Dockerfile separately would create a second place to keep in sync for no benefit the floor does not already give.
- **Revisit if:** a breaking release actually lands, or the hosted `/plan` tier acquires enough traffic that a bad install window costs real users. Either turns the floor into evidence rather than a guess.
- **Scope:** distribution — closes the open dependency-policy question in `docs/phase10-deploy.md`
- **Eval hook:** `pip install -e ".[dev,anthropic]" && mypy` exits 0 on the current SDK; a fresh resolve installs the newest `anthropic` rather than failing, and CI type-checks against whatever that is

## D-078: The planner validates its own response shape at the round boundary

- **Options:** leave it to the schema and treat contract-invalid responses as out of scope · validate inside `_parse_plan`, where the parsing lives · validate in `_round`, at the point where `status` is branched on · express the constraint in `_PLAN_SCHEMA` with `oneOf` so the grammar makes it unreachable
- **Choice:** `_round` checks the companion field's *type* before constructing a `RoundResult` — `plan` must be an object, `questions` must be a list of strings — and raises `PlannerError` otherwise. `_parse_plan`'s contract is unchanged. The schema half is **not** done and is scheduled (`docs/template-registry.md`). Bundled with the same pass: `cmd_scaffold` and `cmd_create` reject an empty output directory, because `Path("")` is `Path(".")` — pressing Enter at the scaffold prompt silently targeted the current working directory, and the error read `✗  already exists` with a blank name.
- **Reason:** five payloads that are schema-shaped but contract-invalid reached users as `Unexpected error: 'NoneType' object is not subscriptable` and similar — the exact category D-074 closed, leaking through the one path D-074 did not sweep. Reproduced directly against `FakeAdapter`, not inferred. `_round`'s existing `except KeyError` covered only the *missing* key; a present-but-null or wrongly-typed value walked straight into `_parse_plan`'s subscripting. The `questions` case is the one worth remembering: a string is iterable, so `{"status": "need_info", "questions": "one question"}` would have asked the user twelve single-character questions.
- **Reachability, stated honestly:** both shipped adapters constrain decoding against a schema where `plan` is `{"type": "object"}`, so `null` is unreachable today. It was fixed anyway because it cost three lines and the alternative, on Tier B, is a 502 with no body for a stranger with no logs. (The `ModelAdapter` Protocol also does not *require* a backend to honour `response_schema` — `FakeAdapter` does not — so today's guarantee is a property of two implementations, not of the contract.)
- **Why `_round` and not `_parse_plan`:** `_parse_plan` is also called by `cmd_scaffold` on a **user-supplied plan file**, where a non-dict raises `TypeError` and produces *"Plan JSON is not a plan object — expected an object with plan fields."* Raising `PlannerError` from inside it would make that a `GenesisError`, which `cmd_scaffold` now catches **ahead of** `TypeError` — so the file-path message would have silently changed to the planner's wording. **Third instance in one day of the same mechanism** (after reparenting `PlannerError` under `GenesisError`, and moving the missing-template failure out of `OSError` into the catch-all): changing the type an error is raised as silently changes which handler claims it, and neither the type checker nor the suite catches it. Treat it as a standing hazard when adding typed errors, including in the Lambda handler's status-code mapping.
- **The empty-directory guard's boundary is deliberate:** an explicit `.` still works and is still protected by D-066's `PLAN.md` check; only the *empty* answer is refused. Someone who types `.` meant it; someone who pressed Enter did not. Without the guard, Enter plus `--force` inside a Genesis-scaffolded repo would have deleted the working directory — the same disaster D-066 fixed, reached by a different route.
- **Amended Sept 18, 2026 — the `isinstance` guards alone did not close the category.** They validate the two top-level companion fields, but `_parse_plan` then indexes `p["name"]` on every phase, and `_round`'s `except KeyError` does not catch indexing a non-dict. `phases: ["juststring"]` and `phases: [None]` still escaped as raw `TypeError`. **The clause that actually closes it is one line** — `except TypeError as e: raise PlannerError(f"malformed {status!r} response: {e}") from e`, beside the existing `except KeyError` — and it holds at arbitrary depth rather than at the depths someone remembered to check. The explicit guards above it are kept for **message quality, not coverage**: *"'ready' response has a plan that is not an object"* tells a user what is wrong, where the catch-all can only relay *"'NoneType' object is not subscriptable"*. Layering is deliberate — specific guards for the fields worth naming, a typed backstop for everything else.
- **Where this stops.** `steps: "notalist"` still passes, because a string is iterable and each character becomes a step. Closing it needs per-field `isinstance` checks at every level, which is the point where defensive validation stops paying for itself — the schema already constrains this for both shipped backends, and the remaining exposure is a cosmetically wrong `PLAN.md`, not a crash or a wrong repo. Recorded as an open finding rather than fixed.
- **Cost accepted:** the planner contract is now enforced in two places — the schema and `_round` — so a future field change needs both. That duplication is the price of the schema half being deferred; it collapses back to one place if and when the tagged union lands.
- **Scope:** planner contract and CLI behaviour — half-closes open item (3), which `docs/phase10-deploy.md` recorded as documented-not-closed
- **Eval hook:** `{"status": "ready", "plan": null}`, `"plan": []`, `"plan": "s"`, `{"status": "need_info", "questions": null}` and `"questions": "one question"` each raise `PlannerError` rather than `TypeError`/`IndexError`; `genesis scaffold plan.json ""` exits 1 with `No output directory given.` while `genesis scaffold plan.json .` still reaches D-066's guard

## D-079: The open-findings list is triaged to empty, not carried

- **Context:** six findings accumulated on Sept 18 from sweeping surfaces the bug window had not touched. Rather than let them sit as "look at this later" — the state that let four of five earlier items go stale within four days — each was decided the day it was found. Two fixed, two rejected, two scheduled. `docs/open-items.md` is now the single consolidated list, and `CLAUDE.md` points at it rather than duplicating it.
- **Fixed: `_STOP_REASON_MAP` gains `model_context_window_exceeded` → `TRUNCATED`.** It previously fell through to `OTHER`, so a response cut off by the context window reached `_extract_json` and surfaced as `model did not return valid JSON: Unterminated string…` rather than `response was truncated by max_tokens — increase --max-tokens and try again`. **This was first recorded as a behaviour change and it is not one:** both paths already raised `PlannerError` and exited 1, so the only thing that changes is whether the message tells the user what to do. Verified by simulating both stop reasons through `FakeAdapter`. **`pause_turn` stays unmapped deliberately** — it arises only with server-side tool use, which Genesis never requests, so it is unreachable rather than unhandled; encoding a guess for a path that cannot fire is how dead code gets written. The two were treated differently on purpose.
- **Fixed: `_select_model` rejects indices below 1.** `idx = int(choice) - 1` went straight into `models[idx]`, and Python's negative indexing meant `0` silently returned the *last* model and `-1` the second-to-last, while `99` and `abc` both raised `Invalid choice`. Silently handing someone a model they did not choose is worse than refusing them. The guard raises inside the existing `try` so it re-raises through the same clause as every other bad input, rather than creating a second path to the same message.
- **Rejected: rewording `cmd_create`'s `OSError` message.** It reads *"Could not write output"*, which looked like the same message-accuracy defect fixed in `cmd_scaffold` that morning. Tracing the paths rather than trusting the note: the only `OSError` source in that `try` is `open(output_path, "w")` — the idea and directory prompts raise `InputUnavailableError` now (D-074). The message is accurate for every failure a user can reach; the misleading instance was pytest's synthetic stdin guard. **Rewording it to also cover reads would make it vaguer for the case that actually occurs**, which is a net loss. Recorded because the first instinct was wrong and the reason is worth not rediscovering.
- **Rejected: relabelling the two questionable eval ideas, and bundling a fresh idea set into the post-deploy re-run.** Relabelling is already forbidden. The bundling question is the live one, and the answer is no: that re-run exists to measure **one** change — planner-emitted labels — and moving the idea set at the same time means two variables move at once and neither result is attributable. Keeping the idea set fixed is what makes the re-run mean anything, and the run is the project's strongest asset. A fresh set is a separate, deliberately-budgeted exercise with no date.
- **Scheduled into the post-deploy block:** `steps` validation, because `_parse_plan` serves both the planner and user-supplied plan files and a new raise inside it needs the clause-routing check that bit three times in one day (D-078) — and because the tagged-union work may make the runtime check unnecessary. And **per-module `--strict` mypy for `genesis.lambda_handler` only**, applied in Task 1: the existing 24 `--strict` errors are missing annotations on internals whose payoff is entirely internal, while the handler is new code against an event-shape contract nobody here has used, where a wrong annotation costs debugging against CloudWatch logs rather than a red local run.
- **Cost accepted:** deciding six findings at the end of a long session risks deciding them badly, and two of these were reconsidered mid-decision (the stop-reason "behaviour change" and the `OSError` "defect") — both times by tracing the code rather than trusting the note written hours earlier. That is the argument for triaging while the context is live, and also the argument for recording the reversals rather than only the conclusions.
- **Scope:** process, plus two one-line fixes
- **Eval hook:** `docs/open-items.md` section C contains no undecided item; a truncated-by-context response raises `response was truncated by max_tokens…` rather than a JSON parse error; `_select_model` with `0`, `-1` or `-2` raises `Invalid choice`


## D-080: Deploy platform — Lambda, reversing the ECS Express Mode choice

- **Options:** ECS Express Mode behind an ALB (the locked choice) · AWS Lambda behind a Function URL · App Runner (closed to new AWS accounts since Apr 2026, so not a real option)
- **Choice:** Lambda + Function URL, deployed early and never paused.
- **Reason:** the constraint that originally picked ECS was App Runner's unavailability, not any need for container orchestration — and that reasoning said nothing about idle cost, which is what now decides it. Three constraints, none of which existed in the original framing. **(1) Idle cost.** An ALB bills ~$16/month whether or not anything runs; Lambda bills per request and idles at ~$0. The $71.11 of credits **expire Dec 16, 2026**, and ECS + ALB would exhaust them precisely as the December job hunt starts, so the URL would die at the moment it is most needed. Lambda outlives the credits. **(2) TLS.** Tier B asks a stranger to send an API key, which over plain HTTP is indefensible. An ALB needs an ACM certificate, which needs a domain you own — a purchase and a dependency. A Function URL is HTTPS free on an AWS-provided domain. **(3) Nothing Genesis does needs what ECS uniquely offers** — long-lived processes, unbounded runtime, persistent local disk, no cold starts. Measured against Lambda's limits, none binds: a plan is 15–30s against a 15-minute ceiling, and a scaffolded repo is 1.5 KB gzipped against a 6 MB response cap.
- **What this amends:** D-050 deferred the deploy on a budget-lapse argument. Per-request billing inverts it — unspent credits are worth nothing, so waiting saves nothing, and the seasonal timing question disappears entirely. D-050's deferral stands as history; its platform framing does not.
- **Cost accepted:** cold starts of ~1–3s on a 264 MB image, and a hostname that looks like infrastructure rather than a product. Both are cosmetic against a URL that stays alive.
- **Two ways this gets expensive, and both are guarded in Task 4:** never put the function in a VPC (it would then need a NAT gateway at ~$32/month — *more* than the ECS option being avoided, and Genesis reaches no private resources), and set reserved concurrency ~5 plus a billing alarm, because the real risk is abuse spinning up concurrent large invocations, not idle spend.
- **Scope:** infrastructure
- **Eval hook:** the Function URL answers from a browser on a machine that has never authenticated to AWS; the AWS cost explorer shows ~$0 for a month with no traffic

## D-081: Handler packaging — `awslambdaric` on the Phase 9 image, declared in the Dockerfile

- **Options:** rebase the image on the AWS Python base image · add the Runtime Interface Client to the existing `python:3.11-slim-bookworm` image · two separate images, one for CLI and one for Lambda
- **Choice:** `awslambdaric` on the existing Phase 9 image, installed by a bare `pip install` line in the `Dockerfile`. `pyproject.toml` is untouched.
- **Reason:** AWS documents "an alternative base image with the runtime interface client" as one of three first-class ways to build a Python Lambda image, so this is supported rather than a workaround — and it is the only option that keeps **one image**, which is what keeps the Phase 9 CI gate covering the artefact that actually deploys. Lambda's `ImageConfig` overrides entrypoint and command per function, so the image keeps `ENTRYPOINT ["genesis"]` for CLI use while Lambda points at `python -m awslambdaric` with `genesis.lambda_handler.handler`. Two images would double the build surface and let the deployed one drift away from the tested one; rebasing on the AWS base image would discard a working, CI-verified image to solve a problem that does not exist.
- **Why the Dockerfile and not a `[lambda]` extra:** `awslambdaric` is a deployment-target concern, not a property of the `genesis-agent` package — it is meaningless outside a Lambda image and nobody installing from PyPI wants it. An extra would advertise a deployment detail in public package metadata, and would add one more extra that mypy's answer varies by, which is exactly the trap B2 surfaced (a green mypy run without an extra installed is a weaker statement than it looks).
- **What this reverses:** `docs/phase10-deploy.md` framed this as an open choice. It was settled against current AWS docs on Sept 18, 2026, and two facts were missing when that framing was written: **`--provenance=false` is a compatibility requirement**, not a performance hint, for a hand-run `docker buildx build`; and **the Runtime Interface Emulator is not shipped in non-AWS base images**, only in AWS base and OS-only images. The second is why local testing goes through `sam local invoke`, which supplies the emulator.
- **Unverified, and the first thing Task 2 tests:** the Phase 9 image sets `USER genesis`, while AWS's examples deliberately omit `USER` because Lambda defines its own least-privileged user. Whether Lambda honours it, ignores it, or fails on it is not documented and has not been tried. If it fails, the fix is a Lambda-specific build stage — which costs the single-image property this decision is built on, so it is tested on the laptop rather than discovered in CloudWatch.
- **Scope:** infrastructure
- **Eval hook:** `sam local invoke` against the image returns a 200 with a base64 zip; the Phase 9 CI job still builds the same `Dockerfile` and its scaffold-inside-the-container gate stays green

## D-082: Infrastructure as code — a tracked AWS SAM template

- **Options:** hand-run `aws` CLI commands, recorded in the gitignored phase doc · a tracked AWS SAM `template.yaml` · CDK in Python · Terraform · IaC written but gitignored
- **Choice:** one **tracked** AWS SAM `template.yaml` at the repo root, describing the image, function, `ImageConfig`, Function URL and the cost guardrails.
- **Reason:** the decisive property is **that the guardrails become verifiable rather than claimed**. "No VPC, reserved concurrency 5, right-sized memory" is currently prose in a gitignored doc; in a tracked template those are lines a reader can check, which matters for a repo whose entire public argument is that its claims are measured rather than asserted. Two supporting reasons: reproducible teardown and redeploy, which is concretely relevant because credits expire Dec 16, 2026 and the billing situation will change underneath this; and no config drift, since a hand-built function's real configuration exists only in the console.
- **Why tracked and not gitignored:** gitignored IaC has no audience, and therefore does strictly less than a list of CLI commands while costing more. If it is not tracked, do not write it. The corollary is that `samconfig.toml` and `.aws-sam/` **are** gitignored — `samconfig.toml` carries the ECR repo URI and therefore the AWS account ID.
- **Why the usual objection does not apply:** IaC would normally be refused here under the minimalism policy and because a new toolchain beside the phase's only genuine unknown is how a weekend gets eaten. That objection is void — the owner already knows AWS IaC, so there is no learning cost and nothing new on the critical path. **Had that not been true, the answer would have been the CLI.**
- **Explicitly *not* a reason: scalability.** This is one function behind a Function URL with concurrency deliberately capped at 5 to bound abuse. Scaling is a non-goal, and citing it would be taste rather than constraint.
- **SAM over CDK and Terraform:** purpose-built for this exact shape (`sam deploy` handles the ECR push, function, `ImageConfig` and Function URL from one template), the smallest of the three, no bootstrap stack, and no state file to manage. CDK costs a Node toolchain and a `cdk bootstrap` CloudFormation stack; Terraform costs state management and a separate image push.
- **Cost accepted:** `template.yaml` is a `.yml` and therefore owner-written under the Sept 1 rule, even though "AWS/IaC config in the deploy block" is otherwise inside the Claude-writes exception — the ambiguity is resolved toward owner-writes. And SAM builds the image itself, so the `--provenance=false` requirement in D-081 must be **verified** under SAM rather than assumed: the classic Docker builder adds no provenance attestation, buildx with the containerd image store may.
- **Sequencing, unchanged by this:** the template lands in Task 4, not earlier. Weekend 1 still ends with the handler green under `sam local invoke`, because a broken handler and a broken template simultaneously is a bad debugging position regardless of tool familiarity. **The cut order stands** — if the template fights back on Oct 10, fall back to `aws lambda create-function` and ship. The floor is a URL that works, not a URL that was declared.
- **Scope:** infrastructure
- **Eval hook:** `sam deploy` from a clean checkout produces a working Function URL; `template.yaml` is tracked and contains the reserved-concurrency and no-VPC settings; `git check-ignore samconfig.toml .aws-sam` matches both


## D-083: Lambda handler design — routing, normalisation, error mapping and response headers

- **Context:** `src/genesis/lambda_handler.py`, written Sept 18, 2026 (Phase 10 Task 1). The handler is an **adapter**, in the same role `cli.py` plays for argv: it translates one calling convention into library calls and holds no Genesis logic of its own. It lives inside the package so it reaches the wheel and stays covered by the Phase 9 packaging gate (D-081), and it calls the library directly — `scaffold()`, `_parse_plan` — never `core.py`, whose `cmd_*` functions print and return exit codes, the wrong currency for a status code and a body.

- **Normalise the event once, into a typed `Request`.** Options: decode and read the raw event inside each route · one normalisation step producing a dataclass. **Chosen: one step.** `event: dict[str, Any]` erases the shape, so `--strict` mypy can verify *nothing* about `event["requestContext"]["http"]["method"]` — the identical hole D-076 found in `kwargs: dict[str, object]`, and it would be incoherent to put this module under strict (per `docs/open-items.md` A4) and then hand the checker something it cannot reason about. The real benefit is not that `_normalise` is checked — it cannot be — but that it **confines the unchecked region to ten lines**, with everything downstream receiving real types. It also gives header access exactly one home, which is what makes the BYOK no-logging promise (D-084) true by construction rather than by vigilance.

- **Wrong method on a known path returns 405 with `Allow`, not 404.** Options: a single fallthrough 404 · a `{path: methods}` table. **Chosen: 405.** The cost is a routing table instead of one branch; the reason is that the request is **guaranteed, not hypothetical** — Task 5's landing page names the endpoints, browsers can only issue `GET` from the address bar, so a visitor pasting `/scaffold` is the predictable second interaction with the deploy. A 404 there asserts the path is wrong when it is exactly right, sending someone to hunt a typo that does not exist. RFC 9110 requires `Allow` on a 405, which is the part that makes it actionable.

- **Error mapping: 4xx may echo the exception, 5xx may not.** A 4xx describes input the caller sent; a 5xx would describe our internals to a public unauthenticated endpoint. `OSError` **flips meaning between the two worlds** — in the CLI it is the user's chosen output directory and their fault, but in Lambda it is `/tmp`, which is ours, so it is a 500 and its `str(e)` (which carries absolute paths) never reaches the caller. **Every 5xx path logs via `logging.exception`;** a 500 with no CloudWatch record is the single failure that cannot be debugged, since there is no terminal and no stderr the caller can paste.

- **`TypeError` → 400 logs, because it also catches our own bugs.** Two real bugs during this task (`_normalise` called with a string, `Ellipsis` passed as a headers mapping) both raised `TypeError` and would have been reported to a stranger as *"your plan is malformed"* — indistinguishable from a caller sending rubbish, and invisible forever. **The general rule this instance demonstrates: the broader the clause, the more it lies.** For the same reason `json.JSONDecodeError`, `binascii.Error` and `UnicodeDecodeError` are listed explicitly rather than caught as one `ValueError`, which would also absorb any library-internal `ValueError` and blame the caller for it.

- **`/tmp` is per-invocation, never a fixed path.** Lambda freezes and reuses execution environments, so `/tmp` survives between invocations: a fixed scaffold path would collide on the second request, or — worse — zip up **a previous caller's files**. `tempfile.mkdtemp()` per request with `shutil.rmtree(..., ignore_errors=True)` in a `finally`. This is also why `_zip_dir` builds the archive in an `io.BytesIO` rather than on disk: the bytes are already in memory when cleanup runs, so cleanup cannot destroy the response.

- **Two response headers on `/scaffold`, status 200 either way.** `Genesis-Supported: true|false` — the generic README already states it in prose, but a programmatic caller (and Task 5's page) would otherwise have to unzip and parse English to learn it. `Content-Disposition: attachment; filename="<name>.zip"` — without it a browser names the download `scaffold`, with no extension. **Both filenames use `normalize(plan.project_name)`, not the raw name:** `project_name` is model output and therefore attacker-influenceable, and a quote or CRLF in a header value is header injection; `normalize` emits `[a-z0-9_]` only, so it is safe by construction. Neither header uses an `X-` prefix, deprecated for new headers by RFC 6648. The status stays 200 for an unsupported stack because the caller received a real, useful artefact — a 4xx would claim they did something wrong.

- **CORS is configured on the Function URL, never written in the handler.** A page served from GitHub Pages (open decision 5) triggers a preflight `OPTIONS /scaffold`, which the routing table answers with 405 and the fetch dies before it starts. SAM's `FunctionUrlConfig.Cors` answers preflights without invoking the function at all, keeps `OPTIONS` out of `_ROUTES`, and puts the allowed origin in the tracked template where it is reviewable (D-082). This is also a point in favour of the GitHub Pages option: with platform CORS it costs a template block rather than handler code.

- **Cost accepted:** a two-route module carries a routing table, a dataclass and four response helpers — more structure than minimalism would normally allow. The justification is that each piece pays for a specific failure that would otherwise reach a stranger with no way to report it.
- **Scope:** infrastructure / public behaviour
- **Eval hook:** `GET /scaffold` → 405 with `Allow: POST`; unknown path → 404; malformed body → 400; a valid plan → 200 whose base64 unzips to one folder named `<normalized>/`, with `Genesis-Supported` and `Content-Disposition` set; no temp directory survives either the success or the failure path

## D-084: Hosted planning is BYOK, multi-turn, and keyed by an explicitly-named header

- **Options:** single-shot planning (force a plan, no clarifying questions) · multi-turn with the client carrying the conversation · no hosted planning at all
- **Choice:** **multi-turn.** `/plan` takes `{"idea": ..., "rounds": [{"questions": [...], "answers": [...]}]}` and returns either `{"status": "need_info", "questions": [...]}` or `{"status": "ready", "plan": {...}}`. The server stays stateless; the client carries the conversation and re-posts it.
- **Reason:** the adaptive clarifying loop is the planner's most distinctive behaviour (Phase 3's adaptive bounded loop), and single-shot would have demoed the pipeline while hiding the part that is actually interesting. The server holds no state, so nothing about this requires a session store. The output composes: `_parse_plan` recomputes `supported` and ignores extra keys, so a `ready` plan **POSTs straight into `/scaffold`** and two stateless calls reconstruct the full pipeline.
- **Cost accepted, and it is not small:** Task 5's page must now render questions and collect answers rather than being one button, and each round is a separate 15–30 s request. **This raises the stakes on the cut order** — if weekend 2 runs short, the page degrades to the keyless `/scaffold` button and `/plan` stays curl-only.
- **Key transport: an `Anthropic-Api-Key` request header.** Rejected `Authorization: Bearer` — it means *"I am authenticating to this service"*, which is false, since Genesis has no accounts and forwards the key without checking it; it also gets special handling from proxies and log scrubbers in ways that would be guesswork. Rejected `X-Api-Key` for the deprecated prefix (RFC 6648) and for not saying whose key it is. Naming the vendor is a small honesty signal on a request to paste a credential that bills the caller.
- **`AnthropicAdapter` gains an `api_key` parameter** (default `None`, falling through to the SDK's env-var behaviour, so no existing caller changes). **Rejected: setting `os.environ` per request** — Lambda reuses execution environments, so the variable would survive into the *next* caller's invocation and a request that omitted its key would silently plan on someone else's credential and bill them. That is the `/tmp` reuse problem again, with money attached. Also rejected: constructing `anthropic.Anthropic` inside the handler, which would move model and retry policy out of the adapter and into an adapter-shaped module that is supposed to hold no Genesis logic (D-083).
- **Never logged, never persisted**, and the commitment goes in the README in the same sitting — a trust promise nobody can read is not one. D-083's single normalisation step is what makes this enforceable: header access has one home, and `logging.exception` is never handed a `Request`.
- **Still open, to settle when Task 3 is written:** whether the handler reaches into `Planner._round`, `_format_qa` and `_force_plan`, or whether `Planner` gains one public stateless method (`step(idea, rounds)`) that rebuilds the conversation and enforces the round cap server-side. **Recommendation: the public method** — three private imports would put conversation-rebuilding logic in the handler, which contradicts D-083's framing, and a public `step` is testable offline against `FakeAdapter` where the handler version is not. `core.py` already imports `_parse_plan`, so one private import has precedent; three is a different claim.
- **Consequence for Task 4:** a planning round takes 15–30 s and **Lambda's default timeout is 3 s**. The SAM template must raise it or `/plan` fails on every call.
- **Scope:** public behaviour, plus one public-API change to `anthropic_adapter.py`
- **Eval hook:** `/plan` without the header → 401 naming it; with a valid key and `rounds: []` → either questions or a plan; a returned plan POSTs to `/scaffold` unmodified and yields 200; no test or log line ever contains the key


## D-085: The image is two stages, not one — `USER genesis` is incompatible with the local Lambda path

- **Context:** D-081 chose `awslambdaric` on the Phase 9 image and rested on a **single-image property**: one artefact serving both the CLI and Lambda, so the Phase 9 CI gate keeps covering what deploys. It named one unverified risk — the image sets `USER genesis` while AWS's container examples deliberately omit `USER`, because Lambda defines its own least-privileged user — and said to test it early, since the fix would be a Lambda-specific build stage costing that property. **Tested Sept 19, 2026, first thing in Task 2. It breaks.**
- **The failure, measured not guessed:** `sam local invoke` builds a *derived* image that installs the Runtime Interface Emulator into `/var/rapid`, and its `mv`/`chmod` steps run as the image's `USER`. The image runs as `uid=1000(genesis)`; `/var` is root-owned; `mkdir /var/rapid` returns `Permission denied`. **Pre-creating the directory owned by `genesis` does not help** — SAM's `COPY` lands a root-owned binary inside it, and `chmod +x` on a file you do not own fails whatever the directory permissions are. There is no one-image configuration that satisfies both.
- **What this does and does not prove.** It proves `USER genesis` is incompatible with **SAM's local emulator**. It does **not** prove real Lambda rejects it — Lambda does not inject the RIE this way, since the image ships its own client. That half stays unverified and is now moot: a local loop that works is required either way, and the emulator is the thing that makes weekend 1 debuggable.
- **Options:** drop `USER genesis` entirely · split the Dockerfile into a shared base plus two final stages · abandon `sam local invoke` for the hand-mounted RIE.
- **Choice:** **base + `lambda` + `cli` stages in one Dockerfile.** `lambda` sets no `USER`, matching AWS's own examples. `cli` keeps `USER genesis` and `WORKDIR /work` exactly as Phase 9 had them.
- **Reason:** dropping `USER genesis` would regress the CLI path to fix a Lambda-path problem — generated repos land in a volume-mounted `/work`, so as root every file a CLI user generates arrives on their disk root-owned, which is the reason Phase 9 added the user. Abandoning `sam local invoke` would keep one image but make the locally-tested artefact assembled differently from what `sam deploy` ships, which is the exact gap Task 2 exists to close.
- **`cli` is the last stage on purpose.** `docker build` with no `--target` builds the final stage, so the **Phase 9 CI gate needs no edit** and keeps building and testing the same non-root CLI image. SAM reaches the other stage explicitly via `DockerBuildTarget: lambda` in `template.yaml`. Verified both ways: default build → `genesis` / `/work` / `ENTRYPOINT ["genesis"]`; `--target lambda` → root, with `awslambdaric` and `genesis.lambda_handler` both importable.
- **`ImageConfig` was removed from the template.** With the `lambda` stage setting its own `ENTRYPOINT` and `CMD`, the template block became a second declaration of the same fact, and two sources of truth drift. D-081's `ImageConfig` mechanism is no longer load-bearing.
- **Cost accepted, and it amends D-081:** the image is no longer strictly single. The cost is contained — one Dockerfile, one base, one build context, and the two final stages differ only in their last three lines — but it is a real weakening of the argument D-081 made, and pretending otherwise would make that entry a lie. What survives is the property that mattered: the CI-gated build and the deployed build share every layer that contains Genesis.
- **Scope:** infrastructure
- **Eval hook:** `docker build .` yields a non-root image entrypointed at `genesis`; `sam local invoke -e tests/fixtures/scaffold_event.json` returns a 200 whose zip installs, passes its own tests and runs its console script
