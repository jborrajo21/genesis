# Genesis

An AI agent that turns a project idea into a **structured, buildable plan** — and (soon) a scaffolded starter repo — built **model-agnostic** and designed for **engineering rigour over vibe-coding**. Every architectural choice is written down in a decision log, every component is tested offline without touching a live API, and CI stays green.

![CI](https://github.com/jborrajo21/genesis/actions/workflows/ci.yml/badge.svg)

> **Status: in active development.** Blocks 1–4 of 8 are built; the scaffolder, eval harness, and live deploy are next. See the [roadmap](#roadmap).

## What it is

Genesis takes a project idea, asks the clarifying questions that would most change the outcome, and produces a typed, phased plan good enough for an AI to build from — while being **honest about what it can't scaffold**. It's deliberately framed as a scaffolding agent with engineering discipline, not an LLM wrapper: the two things that make it worth anything are the (upcoming) deterministic eval harness and a live deploy.

```
idea → clarifying questions → structured Plan → scaffolded repo (Block 5)
                                    ↑ verified by a deterministic eval harness (Block 6)
```

## Built so far

- **Python CLI template** — a minimal, correct reference repo (packaging, tests, lint, CI) that the scaffolder will later generate. Hand-built first, so its generated output can be evaluated against something understood line-by-line.
- **Model-agnostic backend adapter** — a `ModelAdapter` Protocol that hides the provider behind a uniform `complete()` call. An Anthropic adapter implements it; the rest of the system never imports a provider SDK, so models are swappable and everything is testable offline against a `FakeAdapter`.
- **Agent loop** — a hand-built tool-using loop (an LLM autonomously calling tools until done) with guardrails (`max_turns`, a token budget) and per-run telemetry (tools called, tokens, turns). Runs on the adapter Protocol, verified live and offline.
- **Planner** — an adaptive, bounded loop that turns an idea into a typed `Plan`: it decides each round whether to ask more or plan, capped so it can never interrogate forever, with honest limitations (a stack it can't scaffold still gets a plan plus a manual checklist).

## Roadmap

| Block | Deliverable | Status |
|---|---|---|
| 1 | Python CLI template | ✅ |
| 2 | Model-agnostic backend adapter | ✅ |
| 3 | Agent loop + guardrails | ✅ |
| 4 | Planner (idea → structured plan) | ✅ |
| 5 | Scaffolder — generate a repo that builds and passes its own tests | ⬜ |
| 6 | Eval harness — the scaffolder eval as a CI gate | ⬜ |
| 7 | Live deploy (ECS Express Mode) | ⬜ |
| 8 | README + eval numbers + polish | ⬜ |

## Architecture & practices

- **One model-agnostic seam.** The adapter Protocol is the boundary; the agent loop and planner depend on it, never on a provider SDK. Swap the model by swapping one class.
- **Testable offline.** A scripted `FakeAdapter` drives the agent loop and planner in tests — no network, no keys, no spend. Live tests exist but skip in CI (secret-free, deterministic).
- **A decision log.** Every non-trivial choice is recorded in [`DECISIONS.md`](DECISIONS.md) with constraint-based reasoning (D-001 … D-028 so far) — architecture, dependencies, trade-offs, and accepted costs.
- **Minimalism as policy.** Every config line and schema field is generation + eval surface, so surface is added only when a constraint demands it.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"      # add the anthropic extra for live use: ".[dev,anthropic]"
pytest                        # offline suite — no API key needed
ruff check . && ruff format --check .
```

Live paths (planner, real adapter) authenticate from the environment (`ANTHROPIC_API_KEY` or an `ant auth login` profile) and skip automatically when no credentials are present.

## Honest limitations (today)

- Only one scaffold target exists (Python CLI); other stacks get an honest "unsupported" plan + manual checklist, determined by a **keyword heuristic** on the recommended stack.
- The planner's budget is a **soft, forward-looking cap** — it bounds the next round, not the current one, so usage can overshoot by up to a turn.
- The planner resends its instruction each round; **prompt caching** is a future optimization, not yet applied.
- The scaffolder, eval harness, and live deploy are **not built yet** (Blocks 5–7).

## Docs

- [`docs/genesis-plan.md`](docs/genesis-plan.md) — the full plan and constraints.
- [`DECISIONS.md`](DECISIONS.md) — the decision log.
- `docs/phase*.md` — per-phase task breakdowns.
