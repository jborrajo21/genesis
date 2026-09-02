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

```bash
$ genesis create "a cli todo app with local storage" ~/my-todo     --adapter anthropic --model claude-haiku-4-5

→ Planning... 
[Q1/2] Should todos support due dates and priorities, or stay minimal?
→ minimal
[Q2/2] Where should the data file live — project directory or user home?
→ user home
✓ Plan created
→ Scaffolding... ✓ Scaffolded to /Users/you/my-todo
✓ Build and tests passed
```

That last line is the point: Genesis created a fresh virtualenv, installed the generated repo into
it, and ran the repo's own test suite before telling you it worked.

### Planning on its own

```bash
$ genesis plan "a log file parser that summarises errors" --output plan.json
```

Without `--output`, the plan goes to stdout as JSON, so it pipes:

```bash
$ genesis plan "a git commit message linter" --adapter ollama --model gemma4:latest | jq .stack
```

A plan looks like this (real output, truncated):

```json
{
  "project_name": "cli-todo",
  "summary": "A command-line todo application with local file-based storage...",
  "stack": ["Python 3.10+", "click (CLI framework)", "JSON (local storage format)"],
  "supported": true,
  "phases": [
    {"name": "Core Setup", "steps": ["Create project directory and initialize git", "..."]},
    {"name": "Data Storage Layer", "steps": ["Create storage.py module with...", "..."]}
  ],
  "manual_checklist": ["Ensure Python 3.10+ is installed on the system", "..."]
}
```

`supported` is computed by Genesis from the recommended stack, never by the model (D-028). When it
is `false`, scaffolding writes `PLAN.md` and a `README.md` explaining that no code was generated,
rather than forcing a Python CLI template onto a stack that does not fit.

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

No API key, no token cost. Plan quality tracks the local model — see
[honest limitations](#honest-limitations-today). If the server is not running, Genesis says so and
tells you how to start it rather than failing with a stack trace.

### Exit codes

`0` on success, `1` on any failure, `2` on a usage error from argument parsing. Failures print a
single actionable line to stderr — a missing plan key names the key, an unreachable Ollama server
names the command to run.

## Built so far

- **CLI** — three subcommands: `plan` (idea → plan JSON, printed to stdout or saved with `--output`, with an interactive save prompt when run in a terminal without the flag), `scaffold` (a plan JSON file → repo, with `--force` to overwrite an existing directory), and `create` (plan + scaffold end-to-end, prompting before overwriting an existing output directory). Idea, output directory, adapter, and model are prompted for interactively when not passed as arguments; `--max-rounds` (default 6) and `--max-tokens` (default 10000) are flag-only, since their defaults cover the common case.
- **Python CLI template** — a minimal, correct reference repo (packaging, tests, lint, CI) that the scaffolder renders. Hand-built first, so its generated output is evaluated against something understood line-by-line.
- **Model-agnostic backend adapter** — a `ModelAdapter` Protocol that hides the provider behind a uniform `complete()` call, carrying tool definitions, a provider-neutral stop reason, and an optional response schema. **Two** adapters implement it: Anthropic (hosted) and Ollama (local). The rest of the system never imports a provider SDK, so models are swappable and everything is testable offline against a `FakeAdapter`.
- **Ollama adapter — free, local, no API key** — talks to Ollama's OpenAI-compatible endpoint over stdlib `urllib`, adding no dependency. Planning runs entirely on your own machine at zero token cost. Small local models struggle to emit strictly-shaped JSON, so the planner sends a JSON schema and the adapter constrains decoding to it. That turned out to be decisive: in the eval, the schema-constrained local model produced valid plans **20/20**, beating both hosted models.
- **Agent loop** — a hand-built tool-using loop (an LLM autonomously calling tools until done) with guardrails (`max_turns`, a token budget) and per-run telemetry (tools called, tokens, turns). Runs on the adapter Protocol, verified live and offline.
- **Planner** — an adaptive, bounded loop that turns an idea into a typed `Plan`: it decides each round whether to ask more or plan, capped so it can never interrogate forever, with honest limitations (a stack it can't scaffold still gets a plan plus a manual checklist).
- **Scaffolder** — a deterministic (no-LLM, no-network) renderer that turns a `Plan` into a real Python-CLI repo: it copies the vendored template, atomically renames the package across every coupled site, ships the plan alongside the code as `PLAN.md`, and **verifies the result installs and passes its own tests in a fresh venv**. Unsupported stacks fall back to a generic scaffold (`PLAN.md` + `README.md`, no build/test step) rather than forcing the plan into a template that doesn't fit. This is the deterministic half of the eval harness — the check that a generated repo *builds and its tests pass*.
- **Eval harness as a CI gate** — the scaffolder's `build_and_test()` check (which creates a fresh venv, installs the generated repo, and runs its tests) is wired into GitHub Actions. Every push runs the same deterministic check: if a generated repo cannot install or pass its own tests, the build fails. No model calls, no subjective grading — reproducible and offline.
- **A three-tier eval** — deterministic CI gates, a measured pipeline success rate across a local 8B model, Haiku and Sonnet, and a structural rubric over the saved plans. Runs are persisted so they can be re-analysed without re-spending them. [The numbers, and what they don't say →](#eval-numbers)

## Eval numbers

Genesis is evaluated in three tiers, because the questions are different kinds and cannot share a
method. What gates CI must be deterministic and free; what measures a language model can be neither.
Keeping those apart is the point — a flaky gate gets disabled, and a measurement that must be free
stops measuring anything interesting.

| Tier | What it asks | Determinism | Where it runs | Status |
|---|---|---|---|---|
| **1 — Gates** | Does the render produce a valid, installable, test-passing repo? Is it byte-identical run to run? Does the CLI fail gracefully on junk input? | Deterministic, no model, no network beyond `pip` | CI, every push | ✅ |
| **2 — Pipeline success rate** | Across a set of diverse ideas, how many produce a schema-valid plan, get classified supported/unsupported correctly, and scaffold into a repo that builds green? At what token cost and latency — and how does that change as the model gets more capable? | Non-deterministic; a measurement, not a gate | On demand, with credentials | ✅ run Sept 2, 2026 |
| **3 — Plan quality** | Are the plans any *good* — all fields present, phases sequential, steps concrete and actionable, no placeholder text? | Structural checks deterministic; judged quality is not | On demand, over saved Tier 2 output | ✅ structural half only |

### Tier 1 — render correctness (the CI gate)

Tier 1 asks one deterministic question, with no model in the loop: **does the rendered
repo install and pass its own tests in a fresh venv?** No API key, no scoring, no judgement — it
either builds or it doesn't.

| Render variants | Installed | Tests passed | Mean wall time |
|---|---|---|---|
| 10 | 10/10 | 10/10 | 5.1 s |

Each variant renders the template under a different project name, creates a venv, runs
`pip install -e ".[dev]"`, and runs the generated repo's `pytest`. The names are chosen to stress
name normalisation, which is the part of the render that can actually break:

```
Todo App → todo_app     my-cli → my_cli        7guis → p_7guis      !!! → project
Data Pipeline → data_pipeline    log-parser → log_parser    CSV Munger → csv_munger
note taker → note_taker     Ünicode Tool → nicode_tool      a → a
```

**Read this number precisely.** It is 10 *renders*, not 10 different projects: the project name is
the only thing that varies, and "its own tests" means the template's test suite passing after the
package rename. What it proves is **render correctness** — valid packaging, an importable package,
a working console script, and no stray template identifiers left behind, for any project name a
planner might produce. What it does *not* prove is that the generated app does what the plan
describes; the plan contributes `PLAN.md` and a description string, nothing executable.

Two of these run on **every push** as a CI gate — if a rendered repo cannot install or pass its
tests, the build fails. Reproduce locally with `pytest -m slow`.

Tier 1 also gates two things the table above promises and this number doesn't cover, both in the
fast suite:

- **Determinism** — the same `Plan` rendered twice produces byte-identical output, and no cache
  directories leak from the template into a generated repo. The README calls the scaffolder
  deterministic; this is what backs the claim.
- **Graceful degradation** — malformed plan JSON (missing keys, a top-level list, `null`, a
  non-list `phases`) is rejected with an actionable message and no half-written directory, never a
  traceback.

### Tier 2 — pipeline success rate

**Run Sept 2, 2026. 20 ideas × 3 models, single run each (n=20 per model), plus 3 repeats on two
ideas for variance — 78 runs total.** Ideas are split 10 expected-supported / 10
expected-unsupported, each carrying an expected label so *classification accuracy* is a metric
rather than a pass count. Clarifying questions are answered with a fixed `"no preference"` for
every idea and every model: identical treatment keeps the comparison fair and honestly measures
planning from an underspecified idea. Every plan is persisted to `evals/results/` so the run can be
re-analysed without re-spending it.

#### The result we did not expect

```
Idea → buildable repo:    gemma4 (local 8B) 90%    ·    Haiku 75%    ·    Sonnet 60%
```

**The free local model beat both hosted models end-to-end, and success was inversely correlated
with capability.** That is not "the small model is better," and reading it that way is exactly the
mistake a single blended accuracy number would have caused. The decomposition below shows the
mechanism: Genesis scaffolds *Python CLIs only*, and the weaker model reaches for the conventional
choice while the stronger models exercise judgement. Sonnet recommended Node.js with Commander and
lowdb for a CLI todo app — a perfectly defensible engineering call that this pipeline cannot
consume.

**Capability and pipeline-fit are different axes.** The stronger model produced better *plans* and
worse *outcomes*, because the constraint being violated was ours, not the model's.

#### Per-model summary

| Model | n | Plan valid | Built green | Rounds | Phases | Steps | Tokens | Secs |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | 20 | 90% (18/20) | 100% (6/6) | 2 | 6 | 30 | 2,406 | 16 |
| claude-sonnet-5 | 20 | 90% (18/20) | 100% (6/6) | 2 | 6 | 32 | 3,948 | 33 |
| gemma4:latest (local) | 20 | **100%** (20/20) | 100% (9/9) | 5 | 4 | 14 | 6,291 | 166 |

Rounds, phases, steps, tokens and seconds are medians. `Built green` counts only plans that were
classified supported, since unsupported plans deliberately skip the build.

#### Classification, decomposed

One accuracy number would conflate three different questions with three different owners:

| Model | Recommended Python | Classified correctly | Idea → buildable repo |
|---|---|---|---|
| claude-haiku-4-5 | 75% (6/8) | 89% (16/18) | 75% (6/8) |
| claude-sonnet-5 | 60% (6/10) | 78% (14/18) | 60% (6/10) |
| gemma4:latest | 90% (9/10) | 95% (19/20) | 90% (9/10) |

- **Recommended Python** is a property of the *model's* stack choice on the 10 ideas where a Python
  CLI was the reasonable answer.
- **Classified correctly** is a property of *Genesis* — whether `_is_supported` read the recommended
  stack right. Sonnet's Node.js plan was classified **correctly**; Genesis did the right thing with
  the stack it was handed.
- **Idea → buildable repo** is what a *user* experiences, and is the product of both.

Denominators differ because failed plans are excluded, and Haiku's two failures both happened to be
expected-supported ideas — so its supported-set n is 8, not 10.

#### Accuracy by expectation

| Model | Expected supported | Expected unsupported |
|---|---|---|
| claude-haiku-4-5 | 75% (6/8) | 100% (10/10) |
| claude-sonnet-5 | 60% (6/10) | 100% (8/8) |
| gemma4:latest | 90% (9/10) | 100% (10/10) |

**Every model was perfect on the unsupported half.** iOS, Android, Rust, Go, Unity, Swift, React,
Django — all correctly refused, with a plan and a manual checklist instead of a forced scaffold.
The honesty behaviour is the most reliable thing in the pipeline, which is worth stating because it
is the behaviour most projects skip.

#### Run-to-run variance

| Model | Idea | n | supported | steps | rounds |
|---|---|---|---|---|---|
| claude-haiku-4-5 | a CLI todo app | 4 | T,T,T,T | 24,19,18,24 | 2,1,1,7 |
| claude-haiku-4-5 | an iOS habit tracker | 4 | F,F,F,F | 30,37,33,38 | 2,2,6,4 |
| claude-sonnet-5 | a CLI todo app | 4 | **T,F,F,F** | 28,31,39,26 | 1,1,1,1 |
| claude-sonnet-5 | an iOS habit tracker | 4 | F,F,F,F | 42,44,28,— | 2,2,2,2 |
| gemma4:latest | a CLI todo app | 4 | T,T,T,T | 17,16,13,16 | 2,2,3,2 |
| gemma4:latest | an iOS habit tracker | 4 | F,F,F,F | 11,14,17,17 | 4,5,6,2 |

The `T,F,F,F` row is the most important line in this section. **`supported` is not a stable property
of an idea** — Sonnet picked Python once and Node three times for identical input. Any single-run
accuracy figure is therefore a sample from a distribution, not a measurement of the system, and the
variance runs were the most cuttable item in the plan.

Haiku's `2,1,1,7` is a second finding: one run exhausted `--max-rounds` and was force-planned,
because `"no preference"` never resolves the uncertainty that prompted the question. That is a
limitation of *this eval design*, not of the planner.

#### Failures — two modes wearing one message

5 of 60 plans failed to parse, and they split cleanly:

| Model | Error | Cause |
|---|---|---|
| Haiku ×2 | `Extra data: line 2 column 1` | Valid JSON **followed by prose** — `_extract_json` stops at the first object and rejects the rest. **A Genesis bug, not a model failure.** |
| Sonnet ×3 | `Expecting ',' delimiter` (char 2536–3671) | Genuinely malformed JSON deep inside a long plan |

Both surface as `model did not return valid JSON`, which blames the model for a defect that is
sometimes ours. Splitting that message is on the fix list.

### Tier 3 — structural plan quality

A **quality signal, not a gate**. Deterministic checks only, run over the persisted plans:

| Check | Haiku | Sonnet | gemma4 |
|---|---|---|---|
| all fields present | 100% | 100% | 100% |
| 2+ phases | 100% | 100% | 100% |
| every phase has steps | 100% | 100% | 100% |
| steps are substantive | 100% | 100% | 95% |
| no vague filler text | 67% | 89% | 80% |
| no field name used as a phase | 100% | 100% | **65%** |
| unsupported plan has a checklist | 100% | 100% | **64%** |

**Five of seven checks do not discriminate.** They are floor checks — valuable as regression
detection, uninformative as quality measurement. The honest conclusion is that Tier 3 confirms the
planner's *output contract* holds and says almost nothing about whether a plan is good.

The two that do discriminate invert the headline: gemma4 wins the pipeline and loses on plan
hygiene. It names a phase "Manual Checklist" instead of filling the `manual_checklist` field in a
third of plans, and over a third of its unsupported plans ship with an empty checklist — so the
honest refusal lands while the useful fallback does not. **Better outcomes, worse plans.** Both are
true.

There is deliberately **no mean score**. Averaging seven checks where five are pinned at 100%
produces a number that looks like a quality ranking, compresses the only real signal, and would be
quoted out of context.

### What we predicted, and what happened

Predictions were written down *before* the run — the table below is that record. Without stated
predictions every result reads as "about what I expected", and the genuinely interesting findings
become invisible.

| | Prediction | Outcome |
|---|---|---|
| H1 | Claude ≈100% valid JSON; local ≥90% | ❌ **Inverted** — local 100%, both Claude models 90% |
| H2 | Claude asks fewer clarifying rounds | ✅ 2 vs 5 median |
| H3 | Sonnet recommends Python less than Haiku | ✅ 60% vs 75% |
| H4 | ≥90% correct on unsupported ideas | ✅ 100% across the board |
| H5 | Build rate 100% on supported plans | ✅ — the only prediction whose failure would have implicated our code |
| H6 | Plan depth scales with capability | ⚠️ Partial — a real gap to the local model (14 steps), essentially flat between Haiku (30) and Sonnet (32) |

### Conclusions, including one that changes the code

**1. Schema-constrained decoding beat model capability.** H1 inverted for a specific, actionable
reason: the local model is the *only* one receiving a JSON schema. Genesis sends `response_schema`
to Ollama, which constrains decoding; `AnthropicAdapter` accepts the parameter and ignores it
(D-049), because Claude was assumed reliable enough without it. The data says otherwise — 90% is
not reliable enough, and 4 of the 5 total failures were hosted models.

> **Next step: implement `response_schema` in the Anthropic adapter, then re-run this entire eval.**
> Every hosted number here is a measurement of *unconstrained* Claude, and would need to be
> regenerated before it could be compared against a constrained run. The persisted results make the
> re-run cheap to compare against; the numbers themselves do not transfer.

**2. `_extract_json` rejects valid model output.** Two of five failures were plans that parsed fine
and simply had prose after them. Fixing the extractor is likely to move Haiku from 90% to 100%
without touching a model.

**3. A keyword heuristic on the recommended stack is doing more work than it should.** `_is_supported`
was correct in 89–95% of cases, but the pipeline's success is dominated by whether the model happens
to choose Python — something Genesis never asks for and cannot currently influence. Whether the
planner *should* be told about the scaffolding constraint is a real design question, deliberately
left open: tuning the prompt in response to these results would fit the system to its own eval set.

### What these numbers do not say

- **n=20 per model, one date, one version of each model.** With no failures observed, the 95% upper
  bound on a true failure rate is still ~15%. This is evidence, not proof.
- **They are a measurement under conditions**, not a property of the code — different models,
  prompts or ideas would move them.
- **The idea set embeds a judgement.** "Expected supported" means *a competent planner should
  recommend a Python CLI for this*, which is our opinion, not ground truth.
- **The fixed `"no preference"` answers are unrealistic.** A real user resolves ambiguity; this eval
  measures planning from an idea that stays underspecified.
- **Nothing here measures whether a generated repo does what the plan describes.** Tier 1 proves the
  render is correct; nothing proves the app is right.

Tier 1 is the only tier that can fail a build. Tier 2 and 3 are reported with the model, the date,
and the sample size attached, because a number produced by a language model is a measurement under
conditions, not a property of the code. Tier 3's judged half — scoring plan quality with another
model — is deliberately **not** claimed: it is the easiest kind of eval to run and the hardest to
defend, and an unverifiable score would undercut the numbers that are verifiable.

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
| 7 | Live deploy — [deliberately deferred](DECISIONS.md) to late Oct / Nov (D-050) | ⏸️ |
| 8 | README + eval numbers + polish | ✅ |

**Next, in order:** implement `response_schema` for the Anthropic adapter and re-run the Tier 2 eval
(the current hosted numbers measure *unconstrained* Claude) → fix `_extract_json` so valid output
followed by prose stops being reported as a model failure → containerise, with CI proving a repo
scaffolded inside the image still builds → the deferred deploy.

## Architecture & practices

- **One model-agnostic seam.** The adapter Protocol is the boundary; the agent loop and planner depend on it, never on a provider SDK. Swap the model by swapping one class.
- **Testable offline.** A scripted `FakeAdapter` drives the agent loop and planner in tests, and the Ollama adapter is tested against a patched HTTP layer — no network, no keys, no spend. Live tests exist but skip automatically without credentials or a local server, so CI stays secret-free and deterministic.
- **A decision log.** Every non-trivial choice is recorded in [`DECISIONS.md`](DECISIONS.md) with constraint-based reasoning (D-001 … D-053 so far) — architecture, dependencies, trade-offs, and accepted costs.
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
- The live deploy is **not built yet** (Block 7) — deferred by decision, not oversight (D-050). Until it lands, the repo demonstrates no ops work: no containerisation, IAM, or TLS.

## Docs

- [`DECISIONS.md`](DECISIONS.md) — the decision log (every non-trivial choice, with constraint-based reasoning).
