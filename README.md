# Genesis

An AI agent that turns a project idea into a **structured, buildable plan** and a **scaffolded starter repo that installs and passes its own tests** — built **model-agnostic** and designed for **engineering rigour over vibe-coding**.

![CI](https://github.com/jborrajo21/genesis/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/jborrajo21/genesis/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/genesis-agent.svg)](https://pypi.org/project/genesis-agent/)

> **Status: live.** Everything works end to end — CLI, two model backends, a deterministic scaffolder gated in CI, a three-tier eval measured across three models ([results](#eval-numbers)), and a **hosted API you can use without installing anything**: [try it](https://jborrajo21.github.io/genesis/). See the [roadmap](#roadmap).

## What it is

Genesis takes a project idea, asks the clarifying questions that would most change the outcome, and produces a typed, phased plan good enough for an AI to build from — while being **honest about what it can't scaffold**.

Most of Genesis is not the model call. The scaffolder runs with no LLM in the loop and is gated in CI on every push. The planner's output contract is enforced by a JSON schema. Where the pipeline succeeds and fails is **measured across three models and written down**, including the results that were inconvenient. Every non-trivial choice is in a decision log with the constraint that drove it.

```
idea → clarifying questions → structured Plan → scaffolded repo (installs + tests pass)
                                    ↑ gated in CI by the deterministic eval harness
```

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

## Quick start

**Without installing anything —** [jborrajo21.github.io/genesis](https://jborrajo21.github.io/genesis/), or straight at the API:

```bash
# A plan in, a repo that installs and passes its own tests out. No API key.
curl -X POST https://ggn3ce4m7r6f5surc5vosqwoai0oekcx.lambda-url.us-east-2.on.aws/scaffold \
  -H 'content-type: application/json' -d @plan.json -o repo.zip
```

**From PyPI:**

```bash
pip install "genesis-agent[anthropic]"
genesis create "a cli todo app" ~/my-todo
```

**Locally, free, no key** — needs [Ollama](https://ollama.com) running:

```bash
pip install genesis-agent
genesis create "a cli todo app" ~/my-todo --adapter ollama --model <your-model>
```

Genesis asks a few clarifying questions, plans, scaffolds the repo, then proves it works — in a
throwaway virtualenv it installs the result, runs its command, runs its tests, and deletes the
virtualenv again. What you get is the project, not the proof.

**→ [Full command reference](https://github.com/jborrajo21/genesis/blob/main/USAGE.md)** — every
command and flag, both backends, credentials, running it in a container, and exit codes.

## Hosted API

Three endpoints, no account, nothing stored. The [demo page](https://jborrajo21.github.io/genesis/) is a thin frontend over them.

`https://ggn3ce4m7r6f5surc5vosqwoai0oekcx.lambda-url.us-east-2.on.aws`

| Endpoint | Key | Returns |
|---|---|---|
| `POST /scaffold` | no | a zip of a repo that installs and passes its own tests |
| `POST /plan` | yes | clarifying questions, or a finished plan |
| `POST /create` | yes | clarifying questions, then the built repo as a zip |

**Your key is used for that one request and never stored, logged, or written to disk.** Send it as an `anthropic-api-key` header. Genesis keeps no session either — `/plan` and `/create` are stateless, so each call carries the rounds completed so far and the conversation lives in your request rather than on a server. If that isn't a trade you want to make, `pip install` does the same work locally and the key never leaves your machine.

Scaffolding is keyless because template selection is deterministic — the same property that makes the CI gate and the offline test suite possible. Planning costs a round trip of 15–30 seconds each time it asks.

## Built so far

- **CLI** — `plan`, `scaffold`, `create`. Every positional argument is optional and prompted for when omitted, so it works interactively or scripted. Details in [Using the CLI](https://github.com/jborrajo21/genesis/blob/main/USAGE.md).
- **Python CLI template** — a minimal, correct reference repo (packaging, tests, lint, CI) that the scaffolder renders. Hand-built first, so its generated output is checked against something understood line by line.
- **Model-agnostic adapter** — a `ModelAdapter` Protocol hiding the provider behind one `complete()` call, carrying tool definitions, a provider-neutral stop reason, and an optional response schema. Two adapters implement it: Anthropic (hosted) and Ollama (local). Nothing outside them imports a provider SDK, so models are swappable and the rest of the system is testable offline against a `FakeAdapter`.
- **Ollama adapter — free, local, no API key** — talks to Ollama's OpenAI-compatible endpoint over stdlib `urllib`, adding no dependency. Planning runs on your own machine at zero token cost.
- **Schema-constrained planning** — the planner sends a JSON schema and **both** adapters constrain decoding to it. That turned out to be decisive for plan validity, and eliminated a failure mode where valid JSON followed by prose was rejected.
- **Planner** — an adaptive, bounded loop: each round the model decides whether to ask more or plan, capped so it can never interrogate forever. A stack it can't scaffold still gets a plan plus a manual checklist rather than a refusal.
- **Scaffolder** — deterministic, no LLM and no network beyond `pip`. Copies the template, renames the package across every coupled site, ships the plan as `PLAN.md`, and **verifies it installs, that its command actually runs, and that its tests pass** — in a throwaway virtualenv that is then removed, so the repo you get contains only its own files (36 KB, not 47 MB). CI runs that check on every push, so a broken render fails the build. Which template applies is a registry lookup on the recommended stack, so "unsupported" is the absence of a match rather than a maintained denylist.
- **Agent loop** — a hand-built tool-using loop with guardrails (`max_turns`, a token budget) and per-run telemetry. Importable and tested (`from genesis.agent import Agent`), but the CLI does not use it — it is infrastructure for later work, not a dormant stub.
- **Container image** — `python:3.11-slim`, no compiled dependencies and no `apt-get` layer. One Dockerfile, two final stages from a shared base: the CLI image runs non-root, the Lambda image omits `USER` because Lambda supplies its own least-privileged one. CI builds the CLI image every push and proves a repo scaffolded *inside it* still installs and passes its tests.
- **Typed failures, top to bottom** — every deliberate failure raises a `GenesisError` subclass rather than leaking a stdlib exception, so a missing template names the reinstall, an exhausted stdin names the argument to pass, and Ctrl-C exits 130 instead of printing a traceback. The package ships a `py.typed` marker, and `mypy` runs in CI **against the real Anthropic SDK**, so a change to the SDK's parameters fails the build rather than reaching users.
- **Live on AWS Lambda** — an HTTPS Function URL that costs nothing while idle, serving a keyless `/scaffold` and bring-your-own-key `/plan` and `/create`. Memory was sized from measurement (41 MB peak), not guesswork, and the guardrails are declared in a tracked SAM template rather than clicked into a console.
- **A three-tier eval** — deterministic CI gates, a measured pipeline success rate across a local 8B model, Haiku and Sonnet, and a structural rubric over the saved plans. Every run is persisted, so it can be re-analysed without re-spending it. [The numbers, and what they don't say →](#eval-numbers)

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
| 7 | Live deploy — Lambda + Function URL, [hosted demo](https://jborrajo21.github.io/genesis/) | ✅ |
| 8 | README + eval numbers + polish | ✅ |
| — | Published to PyPI as [`genesis-agent`](https://pypi.org/project/genesis-agent/) | ✅ |

**Next:** a template registry with planner-emitted labels, which is the only thing that would move
the measured bottleneck.

The fourth rung on the eval ladder — a 1–2B local model, to see whether a free hosted planning tier
was viable — was measured in September and **declined**: both candidates missed a threshold fixed
before the run (D-072). The numbers are in [`EVAL.md`](https://github.com/jborrajo21/genesis/blob/main/EVAL.md); there is no free planning tier, and that is a
measurement rather than an omission.

## Architecture & practices

- **One model-agnostic seam.** The adapter Protocol is the boundary; the agent loop and planner depend on it, never on a provider SDK. Swap the model by swapping one class.
- **Testable offline.** A scripted `FakeAdapter` drives the agent loop and planner in tests, and the Ollama adapter is tested against a patched HTTP layer — no network, no keys, no spend. Live tests exist but skip automatically without credentials or a local server, so CI stays secret-free and deterministic.
- **A decision log.** Every non-trivial choice is recorded in [`DECISIONS.md`](https://github.com/jborrajo21/genesis/blob/main/DECISIONS.md) with constraint-based reasoning (D-001 … D-089 so far) — architecture, dependencies, trade-offs, and accepted costs.
- **Minimalism as policy.** Every config line and schema field is generation + eval surface, so surface is added only when a constraint demands it.

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

- **Nothing verifies the generated app matches the plan.** Tier 1 proves the render is correct; nothing proves the app is right.
- **The planner's contract is enforced at runtime, not by the schema.** The schema cannot express *"if the status is `ready`, a plan must be present"* without `oneOf` or `if`/`then`, whose constrained-decoding support varies by backend. Genesis raises a typed error instead — the invalid response is caught rather than made unreachable.
- **Plan fields are checked by shape, not exhaustively by type.** `steps` supplied as a string passes, because a string is iterable, and each character becomes a step — a cosmetically wrong `PLAN.md`, not a crash or a wrong repo.

**Not built**

- **A free planning tier.** The hosted `/plan` and `/create` need your own Anthropic key. A small local model was measured against a threshold fixed before the run and missed it (D-072), so there is no free planning tier and [`EVAL.md`](https://github.com/jborrajo21/genesis/blob/main/EVAL.md) says why.
- **Rate limiting on the hosted API.** Concurrency is bounded by the AWS account and a billing alarm, not by per-caller limits. It is a demo, and it can be busy.

## Docs

- [`USAGE.md`](https://github.com/jborrajo21/genesis/blob/main/USAGE.md) — the command reference: every command and flag, both backends, the container, exit codes.
- [`EVAL.md`](https://github.com/jborrajo21/genesis/blob/main/EVAL.md) — full eval results: two runs, three models, scored predictions, findings, and limitations.
- [`DECISIONS.md`](https://github.com/jborrajo21/genesis/blob/main/DECISIONS.md) — the decision log (every non-trivial choice, with constraint-based reasoning).
- [`CONTRIBUTING.md`](https://github.com/jborrajo21/genesis/blob/main/CONTRIBUTING.md) — how to run the project and work on it — pull requests are welcome under MIT with a `git commit -s` sign-off; there is no CLA.

## Licence

[MIT](https://github.com/jborrajo21/genesis/blob/main/LICENSE).
