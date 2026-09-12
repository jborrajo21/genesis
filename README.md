# Genesis

An AI agent that turns a project idea into a **structured, buildable plan** and a **scaffolded starter repo that installs and passes its own tests** — built **model-agnostic** and designed for **engineering rigour over vibe-coding**. Every architectural choice is written down in a decision log, every component is tested offline without touching a live API, and CI stays green.

![CI](https://github.com/jborrajo21/genesis/actions/workflows/ci.yml/badge.svg)

> **Status: in active development.** Blocks 1–6 of 8 are built, plus a user-facing CLI, a second (local, free) model backend, and a three-tier eval harness measured across three models ([results](#eval-numbers)). The live deploy is **scheduled, not skipped** — deferred to late Oct / Nov so the hosted URL is funded and alive when it matters, rather than lapsing after a month (D-050). See the [roadmap](#roadmap).

## What it is

Genesis takes a project idea, asks the clarifying questions that would most change the outcome, and produces a typed, phased plan good enough for an AI to build from — while being **honest about what it can't scaffold**.

Most of Genesis is not the model call. The scaffolder runs with no LLM in the loop and is gated in CI on every push. The planner's output contract is enforced by a JSON schema. Where the pipeline succeeds and fails is **measured across three models and written down**, including the results that were inconvenient. Every non-trivial choice is in a decision log with the constraint that drove it.

```
idea → clarifying questions → structured Plan → scaffolded repo (installs + tests pass)
                                    ↑ gated in CI by the deterministic eval harness
```

## Quick start

```bash
pip install -e ".[dev,anthropic]"
genesis create "a cli todo app" ~/my-todo
```

Genesis asks a few clarifying questions, plans, scaffolds the repo, then installs it in a fresh
venv and runs its tests — so you know it works before you open it.

Two backends, same commands:

| | Hosted (Anthropic) | Local (Ollama) |
|---|---|---|
| Setup | `export ANTHROPIC_API_KEY=...` | `ollama serve` |
| Invoke | `genesis create "idea" ./out` | `genesis create "idea" ./out --adapter ollama --model <your-model>` |
| Cost | tokens | free |
| Needs network | yes | no |
| Plan quality | deeper plans (≈30 steps) | thinner (≈14 steps) — but **higher end-to-end success**, see [eval numbers](#eval-numbers) |

Or run the steps separately — `genesis plan "idea" --output plan.json`, then
`genesis scaffold plan.json ./out`. `scaffold` takes any valid plan JSON, including one you wrote
yourself. Every argument is prompted for interactively if you omit it; `--help` lists the rest.


## Using the CLI

Three commands. `plan` and `scaffold` are each independently useful; `create` chains them (D-033).

```
genesis plan      idea            → Plan JSON        (needs a model)
genesis scaffold  plan JSON file  → working repo     (no model, no network beyond pip)
genesis create    idea            → plan + repo      (both of the above)
```

**Every positional argument is optional.** Omit one and Genesis prompts for it, so `genesis create`
with no arguments walks you through the whole thing. Pass them all and it never asks, which is what
makes it scriptable.

| Flag | Commands | Default | Notes |
|---|---|---|---|
| `--adapter` | `plan`, `create` | prompts | `anthropic` or `ollama` |
| `--model` | `plan`, `create` | prompts | Menu of known models, or type any name — the list is a menu, not a whitelist (D-047) |
| `--output` | `plan`, `create` | — | Save the plan JSON to a path |
| `--force` | `scaffold`, `create` | off | Overwrite an existing output directory |
| `--max-rounds` | `plan`, `create` | 6 | Cap on clarifying rounds — a ceiling, not a target |
| `--max-tokens` | `plan`, `create` | 10000 | Per model call. Raise it if a plan is truncated |

### End to end

```
$ genesis create "a cli todo app with local storage" ~/my-todo \
    --adapter anthropic --model claude-haiku-4-5

→ Planning...
[Q1/3] What programming language and/or platform do you prefer (e.g., Python, Node.js, Go, Rust)?
→ Python 3.11
[Q2/3] Should todos support additional metadata like due dates, priority levels, or just a simple
       text description?
→ title and completion status only
[Q3/3] What CLI interface style do you want: interactive menu-driven, command-based, or both?
→ command-based
✓ Plan created

→ Scaffolding... ✓ Scaffolded to ~/my-todo
✓ Build and tests passed
```

That last line is the point: Genesis created a fresh virtualenv, installed the generated repo into
it, and ran the repo's own test suite before telling you it worked.

### Planning on its own

```bash
$ genesis plan "a log file parser that summarises errors" --output plan.json
```

Without `--output` the plan goes to stdout as JSON, so it pipes:

```bash
$ genesis plan "a git commit message linter" --adapter ollama --model gemma4:latest | jq .stack
```

A plan is a typed object — `project_name`, `summary`, `stack`, `phases[]`, `manual_checklist[]`,
and `supported`. **`supported` is computed by Genesis from the recommended stack, never by the
model** (D-028). When it is `false`, scaffolding writes `PLAN.md` and a `README.md` explaining that
no code was generated, rather than forcing a Python CLI template onto a stack that does not fit.

### Scaffolding a plan you already have

```bash
$ genesis scaffold plan.json ~/my-todo --force
```

`scaffold` takes **any** valid plan JSON — one Genesis produced, or one you wrote by hand. It runs
no model and needs no API key, so it is the fast, free, deterministic half of the pipeline.

### Running locally with Ollama

```bash
$ ollama serve
$ genesis create "a csv to json converter" ./out --adapter ollama --model llama3.1
```

No API key, no token cost. Plan quality tracks the local model — see [`EVAL.md`](EVAL.md), where
the local model turns out to win end-to-end for a reason worth reading. Point Genesis at a remote
Ollama with `GENESIS_OLLAMA_BASE_URL`. If the server is not running, Genesis says so and tells you
how to start it rather than failing with a stack trace.

### Running it in a container

```bash
docker build -t genesis .
docker run --rm -v "$PWD:/work" genesis scaffold plan.json out
```

The image is `python:3.11-slim`, runs as a non-root user, and carries the template inside the
installed package — so a container can scaffold and then **verify the result builds**, creating a
virtualenv and running the generated repo's tests inside itself. CI builds the image on every push
and fails if a repo scaffolded *inside the container* doesn't install and pass its own tests.

**For local use, `pip install` is better.** A CLI that writes files to your disk fits a container
badly: you need a volume mount, and the output is owned by the container's user. The image exists
so Genesis can be deployed, not so it can be installed.

### Exit codes

`0` success · `1` failure · `2` usage error from argument parsing. Failures print one actionable
line to stderr — a missing plan key names the key; an unreachable Ollama server names the command
to start it.

## Built so far

- **CLI** — three subcommands: `plan` (idea → plan JSON, printed to stdout or saved with `--output`, with an interactive save prompt when run in a terminal without the flag), `scaffold` (a plan JSON file → repo, with `--force` to overwrite an existing directory), and `create` (plan + scaffold end-to-end, prompting before overwriting an existing output directory). Idea, output directory, adapter, and model are prompted for interactively when not passed as arguments; `--max-rounds` (default 6) and `--max-tokens` (default 10000) are flag-only, since their defaults cover the common case.
- **Python CLI template** — a minimal, correct reference repo (packaging, tests, lint, CI) that the scaffolder renders. Hand-built first, so its generated output is evaluated against something understood line-by-line.
- **Model-agnostic backend adapter** — a `ModelAdapter` Protocol that hides the provider behind a uniform `complete()` call, carrying tool definitions, a provider-neutral stop reason, and an optional response schema. **Two** adapters implement it: Anthropic (hosted) and Ollama (local). The rest of the system never imports a provider SDK, so models are swappable and everything is testable offline against a `FakeAdapter`.
- **Ollama adapter — free, local, no API key** — talks to Ollama's OpenAI-compatible endpoint over stdlib `urllib`, adding no dependency. Planning runs entirely on your own machine at zero token cost. Small local models struggle to emit strictly-shaped JSON, so the planner sends a JSON schema and the adapter constrains decoding to it. That turned out to be decisive: in the eval, the schema-constrained local model produced valid plans **20/20**, beating both hosted models.
- **Agent loop** — a hand-built tool-using loop (an LLM autonomously calling tools until done) with guardrails (`max_turns`, a token budget) and per-run telemetry (tools called, tokens, turns). Runs on the adapter Protocol, verified live and offline.
- **Planner** — an adaptive, bounded loop that turns an idea into a typed `Plan`: it decides each round whether to ask more or plan, capped so it can never interrogate forever, with honest limitations (a stack it can't scaffold still gets a plan plus a manual checklist).
- **Scaffolder** — a deterministic (no-LLM, no-network) renderer that turns a `Plan` into a real Python-CLI repo: it copies the vendored template, atomically renames the package across every coupled site, ships the plan alongside the code as `PLAN.md`, and **verifies the result installs and passes its own tests in a fresh venv**. Unsupported stacks fall back to a generic scaffold (`PLAN.md` + `README.md`, no build/test step) rather than forcing the plan into a template that doesn't fit. This is the deterministic half of the eval harness — the check that a generated repo *builds and its tests pass*.
- **Eval harness as a CI gate** — the scaffolder's `build_and_test()` check (which creates a fresh venv, installs the generated repo, and runs its tests) is wired into GitHub Actions. Every push runs the same deterministic check: if a generated repo cannot install or pass its own tests, the build fails. No model calls, no subjective grading — reproducible and offline.
- **A container image** — `python:3.11-slim`, non-root, no compiled dependencies and no `apt-get` layer. CI builds it on every push and proves a repo scaffolded *inside the image* still installs and passes its tests, which extends the eval gate to the artefact that would actually be deployed.
- **A three-tier eval** — deterministic CI gates, a measured pipeline success rate across a local 8B model, Haiku and Sonnet, and a structural rubric over the saved plans. Runs are persisted so they can be re-analysed without re-spending them. [The numbers, and what they don't say →](#eval-numbers)

## Eval numbers

Genesis is evaluated in three tiers, because the questions are different kinds and cannot share a
method: what gates CI must be deterministic and free, what measures a language model can be neither.

| Tier | Asks | Runs | Status |
|---|---|---|---|
| **1 — Gates** | Does the render produce a valid, installable, test-passing repo? Byte-identical run to run? Does the CLI fail gracefully on junk? | CI, every push | ✅ |
| **2 — Pipeline success rate** | Across diverse ideas, how many become a valid plan, get classified correctly, and build green — and how does that change with model capability? | On demand | ✅ two runs |
| **3 — Plan quality** | Are the plans structurally sound? | On demand | ✅ structural half only |

**Tier 1**, the CI gate: ten renders under project names chosen to stress name normalisation —
`Todo App`, `7guis`, `!!!`, `Ünicode Tool` — each installed into a fresh venv with its own tests
run. **10/10 installed, 10/10 passed, 5.1 s mean.** Two of them run on every push, so a rendered
repo that cannot install or pass its tests fails the build.

**Tier 2**, 20 ideas × 3 models, twice (Sept 2 and Sept 12, 2026):

| Model | Plan valid | Idea → buildable repo | Median tokens |
|---|---|---|---|
| gemma4:latest *(local 8B, free)* | 100% | **90%** (9/10) | 4,667 |
| claude-haiku-4-5 | 100% | 70% (7/10) | 5,298 |
| claude-sonnet-5 | 100% | 70% (7/10) | 3,210 |

### The result we did not expect

**The free local model beat both hosted models end-to-end, and success was inversely correlated
with capability.** Not "the small model is better" — the mechanism is in the failures. Genesis
scaffolds *Python CLIs only*, and the stronger models reached outside Python for exactly the tasks
where another ecosystem is idiomatic: Node with Commander for a CLI todo app, TypeScript for a git
commit linter, JS tooling for a static site generator. Those are defensible engineering calls this
pipeline cannot consume. The 8B model doesn't know the JS ecosystem and defaults to Python.

**Capability correlates with ecosystem awareness, and ecosystem awareness anti-correlates with
fitting this pipeline.** The constraint being violated is ours, not the model's.

Two more results worth the click: constraining output to a JSON schema took hosted plan validity
from 90% to **100% — zero parse failures in 60 plans**; and `supported` turned out **not to be a
stable property of an idea** — for identical input, Sonnet chose Python twice out of four runs.

**[Full results, methodology, scored predictions, and what these numbers don't say → `EVAL.md`](EVAL.md)**
— including the bug this eval found in our own classifier, and a criticism of the eval's own idea set.

## Roadmap

| Block | Deliverable | Status |
|---|---|---|
| 1 | Python CLI template | ✅ |
| 2 | Model-agnostic backend adapter | ✅ |
| 3 | Agent loop + guardrails | ✅ |
| 4 | Planner (idea → structured plan) | ✅ |
| 5 | Scaffolder — generate a repo that builds and passes its own tests | ✅ |
| 6 | Eval harness — the scaffolder eval as a CI gate | ✅ |
| — | CLI (`plan`/`scaffold`/`create`) + Ollama adapter — added outside the original 8 | ✅ |
| — | Three-tier eval — CI gates, pipeline sweep across three models, structural rubric | ✅ |
| — | Container image, CI-verified by scaffolding inside it | ✅ |
| 7 | Live deploy — [deliberately deferred](DECISIONS.md) to late Oct / Nov (D-050) | ⏸️ |
| 8 | README + eval numbers + polish | ✅ |

**Next, in order:** implement `response_schema` for the Anthropic adapter and re-run the Tier 2 eval
(the current hosted numbers measure *unconstrained* Claude) → fix `_extract_json` so valid output
followed by prose stops being reported as a model failure → stop leaving a verification virtualenv
inside generated repos → the deferred deploy.

## Architecture & practices

- **One model-agnostic seam.** The adapter Protocol is the boundary; the agent loop and planner depend on it, never on a provider SDK. Swap the model by swapping one class.
- **Testable offline.** A scripted `FakeAdapter` drives the agent loop and planner in tests, and the Ollama adapter is tested against a patched HTTP layer — no network, no keys, no spend. Live tests exist but skip automatically without credentials or a local server, so CI stays secret-free and deterministic.
- **A decision log.** Every non-trivial choice is recorded in [`DECISIONS.md`](DECISIONS.md) with constraint-based reasoning (D-001 … D-057 so far) — architecture, dependencies, trade-offs, and accepted costs.
- **Minimalism as policy.** Every config line and schema field is generation + eval surface, so surface is added only when a constraint demands it.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # add the anthropic extra for live use: ".[dev,anthropic]"
pytest                        # offline suite — no API key needed
ruff check . && ruff format --check .
```

Live tests are opt-in: the Anthropic smoke test runs only when `ANTHROPIC_API_KEY` is exported (D-018), and the Ollama one only when a local server with models is reachable. Both skip otherwise, so a bare `pytest` never spends tokens and CI stays secret-free. The CLI itself also authenticates from an `ant auth login` profile.

## Honest limitations (today)

- The scaffolder renders **one template** (Python CLI) and generates a **skeleton, not the finished project** — it proves generation *correctness* (a valid, installable, test-passing repo for any name), not that the app does what the plan describes; the plan rides along in `PLAN.md` to build from.
- Only one scaffold target exists; other stacks get an honest "unsupported" plan + manual checklist, determined by a **keyword heuristic** on the recommended stack.
- **Ollama works, with caveats.** Planning is constrained to a JSON schema (D-049), and that is load-bearing: with it, the local 8B model produced valid JSON in **20/20** runs — the *best* of the three models. Without it, an earlier sample failed to parse in 2 of 3 runs. What local models still get wrong is content placement: a third of gemma4's plans named a phase "Manual Checklist" instead of filling the `manual_checklist` field, and over a third of its unsupported plans shipped with an empty checklist. **Tool-calling is not supported** on this backend by design (it degrades to text-only), so the agent loop stays Anthropic-first.
- **Planning depth is the model's judgement, not a setting.** The loop is adaptive (D-026): each round the model decides whether to ask more or plan now, and `--max-rounds` caps that rather than driving it. Measured over 20 ideas: the local 8B model asked a median of **5 rounds** and produced **14 steps**, while both Claude models asked **2** and produced **30–32**. So more questions does not mean a deeper plan — the weaker model asks more and delivers less. Depth tracks capability; round count tracks something closer to uncertainty.
- **The Anthropic adapter ignores `response_schema`** — it accepts the parameter for Protocol conformance and drops it (D-049), on the assumption that Claude returns valid JSON reliably without constraint. The eval says otherwise: both Claude models parsed at 90%, against 100% for the schema-constrained local model, and 4 of 5 total failures were hosted. Implementing it is the top fix, and **the eval must be re-run afterwards** — every hosted number published here measures *unconstrained* Claude and does not transfer.
- **`_extract_json` rejects valid model output** that is followed by prose, which caused 2 of the 5 observed failures. Reported to the user as "model did not return valid JSON", which blames the model for our bug.
- **The Anthropic adapter has no offline tests**, so its stop-reason and tool-call mapping are unverified in CI — its only test is a live smoke test gated on an explicit `ANTHROPIC_API_KEY` opt-in (D-018), which CI never sets. The newer Ollama adapter has twelve offline tests; the older, more intricate one has none.
- The plan's shape is stated **twice** — as prose in the planning instruction and as a JSON schema — so the two can drift, with the schema winning for Ollama and the prose for Anthropic.
- Name normalisation **drops non-ASCII characters** rather than transliterating them: `Ünicode Tool` becomes `nicode_tool`. Valid and installable, but not what you'd have named it.
- The planner's budget is a **soft, forward-looking cap** — it bounds the next round, not the current one, so usage can overshoot by up to a turn.
- The planner resends its instruction each round; **prompt caching** is a future optimization, not yet applied.
- The agent loop is **infrastructure, not part of the v1 user workflow** — the CLI never invokes it.
- **Every generated repo arrives with a 63 MB `.venv` inside it.** `build_and_test()` creates its verification virtualenv *in* the generated repo and never removes it — so a brand-new project ships with someone else's virtualenv, and if you scaffolded via Docker its binaries are Linux ones that won't run on your machine.
- The live deploy is **not built yet** (Block 7) — deferred by decision, not oversight (D-050). The image exists and is CI-verified, so the containerisation half is done; nothing is hosted, and there is no IAM or TLS work to show.

## Docs

- [`EVAL.md`](EVAL.md) — full eval results: two runs, three models, scored predictions, findings, and limitations.
- [`DECISIONS.md`](DECISIONS.md) — the decision log (every non-trivial choice, with constraint-based reasoning).
