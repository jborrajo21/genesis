# Genesis

An AI agent that turns a project idea into a **structured, buildable plan** and a **scaffolded starter repo that installs and passes its own tests** — built **model-agnostic** and designed for **engineering rigour over vibe-coding**. Every architectural choice is written down in a decision log, every component is tested offline without touching a live API, and CI stays green.

![CI](https://github.com/jborrajo21/genesis/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/jborrajo21/genesis/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/genesis-agent.svg)](https://pypi.org/project/genesis-agent/)

> **Status: in active development.** Everything works end to end — CLI, two model backends, a deterministic scaffolder gated in CI, and a three-tier eval measured across three models ([results](#eval-numbers)). The one thing missing is a **live deploy**, which is scheduled rather than skipped: targeted for mid-October, timed so the URL is alive through the winter rather than lapsing before anyone looks (D-050). See the [roadmap](#roadmap).

## What it is

Genesis takes a project idea, asks the clarifying questions that would most change the outcome, and produces a typed, phased plan good enough for an AI to build from — while being **honest about what it can't scaffold**.

Most of Genesis is not the model call. The scaffolder runs with no LLM in the loop and is gated in CI on every push. The planner's output contract is enforced by a JSON schema. Where the pipeline succeeds and fails is **measured across three models and written down**, including the results that were inconvenient. Every non-trivial choice is in a decision log with the constraint that drove it.

```
idea → clarifying questions → structured Plan → scaffolded repo (installs + tests pass)
                                    ↑ gated in CI by the deterministic eval harness
```

## Quick start

```bash
pip install "genesis-agent[anthropic]"
genesis create "a cli todo app" ~/my-todo
```

Installs as **`genesis-agent`** (the name `genesis` was taken on PyPI); imports and runs as
`genesis`. Drop the `[anthropic]` extra if you only plan to use a local model via Ollama.

Genesis asks a few clarifying questions, plans, scaffolds the repo, then proves it works — in a
throwaway virtualenv it installs the result, runs its command, runs its tests, and deletes the
virtualenv again. What you get is the project, not the proof.

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
yourself. Every argument is prompted for interactively if you omit it.

**→ [Full command reference](#using-the-cli)** — all three commands, every flag, worked examples,
running it in a container, and exit codes.

### Credentials

**Genesis never stores, caches or transmits your API key anywhere except to the provider you chose.**
It holds no config file and reads no `.env` — the Anthropic SDK resolves credentials itself, from
`ANTHROPIC_API_KEY` or an `ant auth login` profile, and Genesis passes nothing of its own.

The local path needs no credential at all: `--adapter ollama` talks to a server on your own machine,
and `genesis scaffold` needs no model whatsoever, so plans you already have cost nothing to build.

## Built so far

- **CLI** — `plan`, `scaffold`, `create`. Every positional argument is optional and prompted for when omitted, so it works interactively or scripted. Details in [Using the CLI](#using-the-cli).
- **Python CLI template** — a minimal, correct reference repo (packaging, tests, lint, CI) that the scaffolder renders. Hand-built first, so its generated output is checked against something understood line by line.
- **Model-agnostic adapter** — a `ModelAdapter` Protocol hiding the provider behind one `complete()` call, carrying tool definitions, a provider-neutral stop reason, and an optional response schema. Two adapters implement it: Anthropic (hosted) and Ollama (local). Nothing outside them imports a provider SDK, so models are swappable and the rest of the system is testable offline against a `FakeAdapter`.
- **Ollama adapter — free, local, no API key** — talks to Ollama's OpenAI-compatible endpoint over stdlib `urllib`, adding no dependency. Planning runs on your own machine at zero token cost.
- **Schema-constrained planning** — the planner sends a JSON schema and **both** adapters constrain decoding to it. That turned out to be decisive: it took hosted plan validity from 90% to 100%, and eliminated a failure mode where valid JSON followed by prose was rejected.
- **Planner** — an adaptive, bounded loop: each round the model decides whether to ask more or plan, capped so it can never interrogate forever. A stack it can't scaffold still gets a plan plus a manual checklist rather than a refusal.
- **Scaffolder** — deterministic, no LLM and no network beyond `pip`. Copies the template, renames the package across every coupled site, ships the plan as `PLAN.md`, and **verifies it installs, that its command actually runs, and that its tests pass** — in a throwaway virtualenv that is then removed, so the repo you get contains only its own files (36 KB, not 47 MB). CI runs that check on every push, so a broken render fails the build. Which template applies is a registry lookup on the recommended stack, so "unsupported" is the absence of a match rather than a maintained denylist.
- **Agent loop** — a hand-built tool-using loop with guardrails (`max_turns`, a token budget) and per-run telemetry. Importable and tested (`from genesis.agent import Agent`), but the CLI does not use it — it is infrastructure for later work, not a dormant stub.
- **Container image** — `python:3.11-slim`, non-root, no compiled dependencies and no `apt-get` layer. CI builds it every push and proves a repo scaffolded *inside the image* still installs and passes its tests.
- **A three-tier eval** — deterministic CI gates, a measured pipeline success rate across a local 8B model, Haiku and Sonnet, and a structural rubric over the saved plans. Every run is persisted, so it can be re-analysed without re-spending it. [The numbers, and what they don't say →](#eval-numbers)

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

**[Full results, methodology, scored predictions, and what these numbers don't say → `EVAL.md`](https://github.com/jborrajo21/genesis/blob/main/EVAL.md)**
— including the bug this eval found in our own classifier, and a criticism of the eval's own idea set.

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

Run:
  cd ~/my-todo
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
```

`Build and tests passed` is the point: Genesis created a throwaway virtualenv, installed the
generated repo into it, ran its command and its test suite — then **deleted the virtualenv**, so
what you get is 36 KB of project rather than 47 MB of someone else's environment.

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

No API key, no token cost. Plan quality tracks the local model — see [`EVAL.md`](https://github.com/jborrajo21/genesis/blob/main/EVAL.md), where
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
| 7 | Live deploy — [deliberately deferred](https://github.com/jborrajo21/genesis/blob/main/DECISIONS.md) to mid-October (D-050) | ⏸️ |
| 8 | README + eval numbers + polish | ✅ |
| — | Published to PyPI as [`genesis-agent`](https://pypi.org/project/genesis-agent/) | ✅ |

**Next, in order:** measure a 1–2B local model as a fourth rung on the eval ladder → the deploy →
a template registry with a second template, which is the only thing that would move the measured
bottleneck.

## Architecture & practices

- **One model-agnostic seam.** The adapter Protocol is the boundary; the agent loop and planner depend on it, never on a provider SDK. Swap the model by swapping one class.
- **Testable offline.** A scripted `FakeAdapter` drives the agent loop and planner in tests, and the Ollama adapter is tested against a patched HTTP layer — no network, no keys, no spend. Live tests exist but skip automatically without credentials or a local server, so CI stays secret-free and deterministic.
- **A decision log.** Every non-trivial choice is recorded in [`DECISIONS.md`](https://github.com/jborrajo21/genesis/blob/main/DECISIONS.md) with constraint-based reasoning (D-001 … D-069 so far) — architecture, dependencies, trade-offs, and accepted costs.
- **Minimalism as policy.** Every config line and schema field is generation + eval surface, so surface is added only when a constraint demands it.

## Working on Genesis itself

```bash
git clone https://github.com/jborrajo21/genesis && cd genesis
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # add the anthropic extra for live use: ".[dev,anthropic]"
pytest                        # offline suite — no API key needed
ruff check . && ruff format --check .
```

Live tests are opt-in: the Anthropic smoke test runs only when `ANTHROPIC_API_KEY` is exported (D-018), and the Ollama one only when a local server with models is reachable. Both skip otherwise, so a bare `pytest` never spends tokens and CI stays secret-free. The CLI itself also authenticates from an `ant auth login` profile.

## Honest limitations (today)

**What it generates**

- The scaffolder renders **one template** (Python CLI) and produces a **skeleton, not a finished project**. It proves generation *correctness* — a valid, installable, test-passing repo for any project name — not that the app does what the plan describes. The plan rides along in `PLAN.md` to build from.
- Anything else gets an honest "unsupported" plan plus a manual checklist. Which template applies is a **keyword match on the recommended stack**, which is the weak link below.
- Name normalisation **drops non-ASCII** rather than transliterating: `Ünicode Tool` becomes `nicode_tool`. Valid and installable, not what you'd have named it.

**Stack classification — the known weak point**

- **One incidental word can veto a scaffoldable plan.** A plan listing `Python 3.10+`, `Jinja2`, `watchdog` and *"Flask or http.server for dev server"* is refused, because the stack is matched as one string and any excluded marker wins. No keyword rule fixes this — whether Flask is the architecture or an optional dev server isn't information keywords carry. The fix is having the planner label its own plan (`{"language": "python", "kind": "cli"}`) and doing exact lookup; it is designed but not built.
- **Stack choice is the whole remaining gap** in end-to-end success, and it is **unstable run to run** for the hosted models: for identical input, Sonnet chose Python twice out of four runs. Single-run numbers are samples, not measurements.

**Planning**

- **Depth is the model's judgement, not a setting.** `--max-rounds` caps the loop rather than driving it. Measured over 20 ideas: the local 8B model asked a median of 5 rounds and produced 14 steps; both Claude models asked 2 and produced 30–34. More questions does not mean a deeper plan.
- The plan's shape is stated **twice** — as prose in the planning instruction and as a JSON schema — so the two can drift.
- The planner's token budget is a **soft, forward-looking cap**: it bounds the next round, not the current one, so usage can overshoot by up to a turn. It resends its instruction each round; **prompt caching** is not applied yet.
- **Tool-calling is unsupported on Ollama** by design (it degrades to text-only), so the agent loop stays Anthropic-first. The agent loop itself is infrastructure — the CLI never invokes it.

**Testing and errors**

- **Three failure paths still surface as `Unexpected error`** through a catch-all: a missing template, stdin running out mid-questioning, and filesystem errors during scaffolding. Each deserves a typed clause naming the cause.
- **The offline Anthropic tests stub the SDK module**, so they would pass even if the installed SDK stopped accepting the `output_config` parameter. That gap is caught only by the live opt-in smoke test.
- **Nothing verifies the generated app matches the plan.** Tier 1 proves the render is correct; nothing proves the app is right.

**Not built**

- The **live deploy** (Block 7) — deferred by decision, not oversight (D-050). The container image exists and is CI-verified, so the packaging half is done; nothing is hosted, and there is no IAM or TLS work to show.

## Docs

- [`CONTRIBUTING.md`](https://github.com/jborrajo21/genesis/blob/main/CONTRIBUTING.md) — how to run it, how the project is organised, and why external pull requests cannot be merged yet.
- [`EVAL.md`](https://github.com/jborrajo21/genesis/blob/main/EVAL.md) — full eval results: two runs, three models, scored predictions, findings, and limitations.
- [`DECISIONS.md`](https://github.com/jborrajo21/genesis/blob/main/DECISIONS.md) — the decision log (every non-trivial choice, with constraint-based reasoning).

## Licence

[MIT](https://github.com/jborrajo21/genesis/blob/main/LICENSE).
