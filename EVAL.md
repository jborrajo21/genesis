# Genesis — eval results

Two runs, Sept 2 and Sept 12 2026, 20 ideas × 3 models each plus variance repeats (78 runs per sweep). Raw records are in [`evals/results/`](evals/results/) and every table below is regenerated from them:

```bash
python -m evals.report evals/results/run-20260912T035718Z.jsonl
python -m evals.rubric evals/results/run-20260912T035718Z.jsonl
```

Nothing here is hand-transcribed. If a number in this file disagrees with the tool, the tool is right.

---

## The eval, in three tiers

The questions are different kinds and cannot share a method. What gates CI must be deterministic and free; what measures a language model can be neither. A flaky gate gets disabled, and a measurement that must be free stops measuring anything interesting.

| Tier | Asks | Determinism | Runs |
|---|---|---|---|
| **1 — Gates** | Does the render produce a valid, installable, test-passing repo? Byte-identical run to run? Does the CLI fail gracefully on junk? | Deterministic, no model | CI, every push |
| **2 — Pipeline success rate** | Across diverse ideas, how many become a schema-valid plan, get classified correctly, and build green? At what cost — and how does that change with model capability? | Non-deterministic; a measurement, not a gate | On demand |
| **3 — Plan quality** | Are the plans structurally sound? | Structural half deterministic; judged quality not attempted | On demand, over saved Tier 2 output |

Only Tier 1 can fail a build.

---

## Tier 1 — render correctness

Ten renders under project names chosen to stress name normalisation, each installed into a fresh venv with its own tests run:

| Render variants | Installed | Tests passed | Mean wall time |
|---|---|---|---|
| 10 | 10/10 | 10/10 | 5.1 s |

```
Todo App → todo_app     my-cli → my_cli        7guis → p_7guis      !!! → project
Data Pipeline → data_pipeline    log-parser → log_parser    CSV Munger → csv_munger
note taker → note_taker     Ünicode Tool → nicode_tool      a → a
```

**Read this precisely.** It is 10 *renders*, not 10 projects — the project name is the only variable, and "its own tests" means the template's suite passing after the package rename. It proves **render correctness**: valid packaging, an importable package, a working console script, no stray template identifiers. It does not prove the generated app does what the plan describes.

Two of these run on every push as a CI gate, alongside a byte-identical-render check, a no-cache-leakage check, five malformed-plan cases, and an end-to-end `genesis create` against a stub model server.

---

## Tier 2 — pipeline success rate

**Method.** 20 ideas, split 10 expected-supported / 10 expected-unsupported, each carrying an expected label so classification accuracy is a metric rather than a pass count. Clarifying questions are answered with a fixed `"no preference"` for every idea and model — identical treatment keeps the comparison fair and honestly measures planning from an underspecified idea. Every plan is persisted, so the runs can be re-analysed without re-spending them.

**What changed between runs.** The Sept 2 run revealed that the local model was the only one receiving a JSON schema; the hosted adapter accepted the parameter and ignored it. Sept 12 repeats the sweep with schema-constrained decoding on all three.

### The result we did not expect

```
Idea → buildable repo:   gemma4 (local 8B) 90%   ·   Haiku 70%   ·   Sonnet 70%
```

**The free local model beat both hosted models end-to-end, and success was inversely correlated with capability.** That is not "the small model is better," and reading it that way is exactly the mistake a single blended number would cause.

The mechanism is visible in the failures. Genesis scaffolds **Python CLIs only**. Sonnet recommended Node.js with Commander for a CLI todo app; both hosted models chose Node/TypeScript for a git commit linter; all three reached outside Python for a static site generator. Those are *idiomatic* choices — 11ty and Astro are static site generators, husky and commitlint are the commit-hook ecosystem. The 8B model doesn't know that and defaults to Python.

**Capability correlates with ecosystem awareness, and ecosystem awareness anti-correlates with fitting this pipeline.** Weakness looks like superiority because the constraint being violated is ours, not the model's.

### Per-model summary

**Sept 12** (all three schema-constrained):

| Model | n | Plan valid | Built green | Rounds | Phases | Steps | Tokens | Secs |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | 20 | **100%** (20/20) | 100% (7/7) | 4 | 6 | 32 | 5,298 | 27 |
| claude-sonnet-5 | 20 | **100%** (20/20) | 100% (7/7) | 1 | 7 | 34 | 3,210 | 27 |
| gemma4:latest (local) | 20 | **100%** (20/20) | 100% (9/9) | 4 | 4 | 16 | 4,667 | 132 |

**Sept 2** (hosted models unconstrained):

| Model | n | Plan valid | Built green | Rounds | Phases | Steps | Tokens | Secs |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | 20 | 90% (18/20) | 100% (6/6) | 2 | 6 | 30 | 2,406 | 16 |
| claude-sonnet-5 | 20 | 90% (18/20) | 100% (6/6) | 2 | 6 | 32 | 3,948 | 33 |
| gemma4:latest | 20 | 100% (20/20) | 100% (9/9) | 5 | 4 | 14 | 6,291 | 166 |

Medians for rounds, phases, steps, tokens and seconds. `Built green` counts only plans classified supported, since unsupported plans deliberately skip the build.

### Constraining the output fixed validity outright

**Zero parse failures in 60 plans**, against five on Sept 2. Two of those five were Haiku emitting valid JSON followed by prose — a Genesis bug, not a model failure, and one that schema-constrained decoding makes structurally impossible.

Validity was the one axis where the *least* capable model led, purely because it was the only one being constrained.

### Classification, decomposed

One accuracy number would conflate three questions with three different owners.

**Sept 12:**

| Model | Recommended Python | Python plans accepted | Idea → buildable repo |
|---|---|---|---|
| claude-haiku-4-5 | 80% (8/10) | **88% (7/8)** | 70% (7/10) |
| claude-sonnet-5 | 70% (7/10) | 100% (7/7) | 70% (7/10) |
| gemma4:latest | 90% (9/10) | 100% (9/9) | 90% (9/10) |

**Sept 2:**

| Model | Recommended Python | Python plans accepted | Idea → buildable repo |
|---|---|---|---|
| claude-haiku-4-5 | 75% (6/8) | 100% (6/6) | 60% (6/10) |
| claude-sonnet-5 | 60% (6/10) | 100% (6/6) | 60% (6/10) |
| gemma4:latest | 90% (9/10) | 100% (9/9) | 90% (9/10) |

- **Recommended Python** is a property of the *model's* stack choice.
- **Python plans accepted** isolates **our** heuristic — of the plans that did recommend Python, how many Genesis accepted as scaffoldable. The one miss is a real bug, below.
- **Idea → buildable repo** is what a *user* experiences, and is the product of both.

The first two columns exclude plans that failed to parse (a failed plan has no stack to inspect). The third deliberately does not — a plan that never parsed produced no repo, and excluding it would reward a model for failing early.

Both hosted models gained exactly **one idea** from the schema fix. The gap to the local model narrowed from 30 points to 20 — and is now *entirely* stack choice, with the parse-failure confound removed.

### Accuracy by expectation — Sept 12

| Model | Expected supported | Expected unsupported |
|---|---|---|
| claude-haiku-4-5 | 70% (7/10) | **100%** (10/10) |
| claude-sonnet-5 | 70% (7/10) | **100%** (10/10) |
| gemma4:latest | 90% (9/10) | **100%** (10/10) |

**Every model was perfect on the unsupported half, in both runs.** iOS, Android, Rust, Go, Unity, Swift, React, Django — all correctly refused, with a plan and a manual checklist instead of a forced scaffold. The honesty behaviour is the most reliable thing in the pipeline, which is worth stating because it is the behaviour most projects skip.

### Run-to-run variance — Sept 12

| Model | Idea | n | supported | steps | rounds |
|---|---|---|---|---|---|
| claude-haiku-4-5 | a CLI todo app | 4 | **T,T,T,F** | 24,17,24,28 | 1,1,1,1 |
| claude-haiku-4-5 | an iOS habit tracker | 4 | F,F,F,F | 37,24,41,30 | 4,5,5,4 |
| claude-sonnet-5 | a CLI todo app | 4 | **F,T,F,T** | 27,25,33,29 | 1,1,1,1 |
| claude-sonnet-5 | an iOS habit tracker | 4 | F,F,F,F | 39,46,34,40 | 1,1,1,1 |
| gemma4:latest | a CLI todo app | 4 | T,T,T,T | 19,14,13,9 | 2,2,2,4 |
| gemma4:latest | an iOS habit tracker | 4 | F,F,F,F | 14,20,13,19 | 3,5,4,4 |

**`supported` is not a stable property of an idea.** For identical input, Sonnet picked Python twice out of four and Haiku three out of four; on Sept 2 the patterns differed again (`T,F,F,F` and `T,T,T,T`). Any single-run accuracy figure is a sample from a distribution, not a measurement of the system. The variance repeats were the most cuttable item in the plan and turned out to carry the most weight.

The local model was stable across both runs — which is consistent with the mechanism above: a model that always reaches for Python has nothing to be unstable about.

### One unexplained result

| | rounds | tokens |
|---|---|---|
| Haiku | 2 → **4** | 2,406 → **5,298** |
| Sonnet | 2 → 1 | 3,948 → 3,210 |
| gemma4 | 5 → 4 | 6,291 → 4,667 |

Haiku's cost doubled under schema constraint while both other models got cheaper. No mechanism offered — any explanation would be speculation, and it is recorded here rather than smoothed over.

---

## Tier 3 — structural plan quality

A **quality signal, not a gate**. Deterministic checks over the persisted plans.

| Check | Haiku (Sep 2 → 12) | Sonnet | gemma4 |
|---|---|---|---|
| all fields present | 100 → 100 | 100 → 100 | 100 → 100 |
| 2+ phases | 100 → 100 | 100 → 100 | 100 → 100 |
| every phase has steps | 100 → 100 | 100 → 100 | 100 → 100 |
| steps are substantive | 100 → 100 | 100 → 100 | 95 → 100 |
| no vague filler text | 67 → 90 | 89 → 100 | 80 → 90 |
| no field name used as a phase | 100 → 100 | 100 → 100 | **65 → 75** |
| unsupported plan has a checklist | 100 → 100 | 100 → 100 | **64 → 82** |

**Tier 3 lacks the resolution to detect change at n=20.** Every discriminating check "improved" between runs — including the local model's, whose treatment barely changed and for which no mechanism exists that would affect phase naming. The movements are one to three instances out of twenty. That is noise, and the honest conclusion is that this tier confirms the planner's *output contract* holds and cannot currently say more.

What it does say reliably, because it holds across both runs: the local model wins the pipeline and loses on plan hygiene, naming a phase "Manual Checklist" instead of filling the field in a quarter to a third of plans, and shipping empty checklists on some unsupported plans — the honest refusal lands while the useful fallback does not. **Better outcomes, worse plans.**

There is deliberately **no mean score**: averaging seven checks where four are pinned at 100% produces a number that looks like a quality ranking and would be quoted out of context.

**The judged half — scoring plan quality with another model — is deliberately not attempted.** It is the easiest kind of eval to run and the hardest to defend, and a Claude judge scoring Claude against a local model has an obvious self-preference confound. An unverifiable score would undercut the numbers that are verifiable.

---

## Predictions, scored

Written before the Sept 2 sweep so surprises stayed visible instead of being rationalised afterwards.

| | Prediction | Outcome |
|---|---|---|
| H1 | Claude ≈100% valid; local ≥90% | ❌ **Inverted** — local 100%, both Claude models 90%. The cause was ours: only the local model was being sent a schema |
| H2 | Claude asks fewer rounds than local | ✅ 2 / 2 / 5 median |
| H3 | Sonnet recommends Python less than Haiku | ✅ 60% vs 75%, and again 70% vs 80% on Sept 12 |
| H4 | ≥90% correct on expected-unsupported | ✅ 100% for all three, both runs |
| H5 | Build rate 100% on supported plans | ✅ both runs — the only prediction whose failure would have implicated our code |
| H6 | Depth scales with capability | ⚠️ Partial — a real gap to the local model (16 steps vs 32–34), essentially flat between Haiku and Sonnet |

H1 inverting is what produced the Sept 12 re-run.

---

## Findings

### Bugs in Genesis the eval surfaced

1. **Stack classification vetoes on any marker, anywhere in the stack — still open.** Haiku's plan for *a static site generator from markdown* was `['Python 3.10+', 'markdown2 or python-markdown', 'Jinja2 for templating', 'watchdog for file monitoring', 'Flask or http.server for dev server', 'YAML frontmatter for metadata']`. Five elements say Python CLI; one mentions Flask as an *optional* dev server. The stack is joined into one string and any marker vetoes it, so one incidental word rejects a scaffoldable plan.

   **No keyword rule fixes this** — whether Flask is the architecture or an optional dev server is not information keywords carry. A positional rule (markers only disqualify in the first element or two, which would work on this data) was considered and **rejected as fitting the heuristic to this eval set**. The real fix is having the planner label its own plan — `{"language": "python", "kind": "cli"}` as one more field in a completion that already happens, then exact lookup — which is also what multiple templates will need. Design: `docs/template-registry.md`.

   A **related** defect *was* fixed: markers matched as substrings, so `gui` matched "guide" and `ios` matched "Axios". Across 157 recorded plans this caused zero misclassifications — every accidental hit landed on a plan unsupported for other reasons — but a Python plan mentioning a *guide* would have been silently refused. Now matched on word boundaries, verified to change none of the 157 recorded outcomes.
2. **The end-to-end metric excluded parse failures.** Until corrected, plans that failed to parse were dropped from the denominator — rewarding a model for failing early. Haiku's Sept 2 figure read 75% (6/8) where the honest number is 60% (6/10). Fixed; both runs above use the corrected denominator.
3. **`_extract_json` rejected valid model output** followed by prose, causing two of five Sept 2 failures and reported to users as "model did not return valid JSON" — blaming the model for our bug. Closed as a side effect of schema-constrained decoding.

### A criticism of this eval

**Two of the expected-supported labels are questionable.** *A static site generator from markdown* and *a git commit message linter* are labelled "a competent planner should recommend a Python CLI," but Node/TypeScript is idiomatic for both. The eval scores models down for giving defensible ecosystem advice.

The labels have **not** been changed. Relabelling after seeing results is how an eval stops meaning anything; the criticism is published instead. It does mean the headline gap is partly an artefact of the idea set, and a fresh idea set is the right way to test that.

### Deliberately not fixed in response

`_PLANNING_INSTRUCTION` was not edited to steer models toward Python, and the template's exclusion markers were not widened to fit observed misses. Both would tune the system to its own eval set. A finding earns a code change when it implicates our code rather than a model's judgment, and can be verified by something other than the eval that found it.

---

## What these numbers do not say

- **n=20 per model, two dates, one version of each model.** With no failures observed, the 95% upper bound on a true failure rate is still ~15%. Evidence, not proof.
- **They are a measurement under conditions**, not a property of the code.
- **The idea set embeds a judgement** about what a competent planner should recommend — see the criticism above.
- **The fixed `"no preference"` answers are unrealistic.** A real user resolves ambiguity; this measures planning from an idea that stays underspecified. One Haiku run exhausted `--max-rounds` and had to be force-planned because the answer never resolved anything.
- **Nothing here measures whether a generated repo does what the plan describes.** Tier 1 proves the render is correct; nothing proves the app is right.
