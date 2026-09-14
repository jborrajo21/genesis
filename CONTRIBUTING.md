# Contributing

Thanks for looking. Please read the licensing note below **before** writing code — it affects whether a pull request can be accepted at all.

## Licensing and contributions

Contributions are accepted under the MIT licence. Sign your commits with `git commit -s`, which adds a `Signed-off-by:` line certifying you wrote the code and may submit it under that licence (the [Developer Certificate of Origin](https://developercertificate.org/)).

One consequence, stated here because it is easy to discover too late: a DCO certifies provenance, it does **not** transfer copyright. Once external contributions are merged, relicensing future versions would need every contributor's agreement. That is accepted — the intended path if this is ever commercialised is open core, which keeps the CLI MIT either way ([`DECISIONS.md`](DECISIONS.md), D-069). There is no CLA and none is planned.

Particularly welcome, beyond code:

- **Bug reports.** Especially anything that produces a broken generated repo, since that is the claim the project stakes itself on.
- **Eval results.** Running the harness against a model that is not in the ladder, and reporting what you got.
- **Disagreement with a decision.** `DECISIONS.md` records reasoning precisely so it can be argued with. An issue explaining why one is wrong is more valuable than a patch.

If you want to work on something substantial, open an issue first so nobody wastes an evening.

## Running it

```bash
git clone https://github.com/jborrajo21/genesis && cd genesis
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest                              # offline; no API key, no network beyond pip
pytest -m "not slow"                # skips the two tests that build a venv
ruff check . && ruff format --check .
```

Live tests are opt-in and skip by default: the Anthropic one needs `ANTHROPIC_API_KEY` exported, the Ollama one needs a local server with a model pulled. CI never sets either, so it stays secret-free and deterministic.

Run `ruff check . && pytest -q` **immediately before committing**, not only while working — more than one red build here has come from a final edit made after the last check.

## How the project is organised

| | |
|---|---|
| `src/genesis/` | the package — adapters, planner, scaffolder, CLI |
| `src/genesis/templates/` | template *data*; must stay inside the package or it will not ship in the wheel (D-054) |
| `tests/` | offline suite; two tests marked `slow` build a real venv |
| `evals/` | the eval harness — deliberately **not** under `tests/`, because it is non-deterministic, costs money and needs credentials (D-051) |
| `evals/results/` | persisted runs. Also a regression corpus: stack classification is asserted against every recorded plan |

## Things worth knowing before changing anything

- **Every non-trivial change gets a `DECISIONS.md` entry** with constraint-based reasoning — what was chosen, what was rejected, and what it costs. "It's cleaner" is not a reason.
- **Do not tune the planner or the template matchers against the eval set.** Fitting the system to the twenty ideas it is measured on destroys the meaning of the numbers. Findings go in `EVAL.md`; fixes are a separate, later decision.
- **Re-run the eval only when a change can alter a recorded outcome.** When it provably cannot, replay the persisted plans instead — it is a second and free.
- **`genesis scaffold` must never require an API key.** That is what allows the CI gate, the offline tests, and the planned keyless hosted tier.
- **CI and Docker steps assert against public API**, and over whole sets rather than one hardcoded path. Two failures here have come from assertions on private names.

## Reporting a bug

Include the plan JSON if there is one — it is the input that reproduces most failures, and `genesis plan --output plan.json` will give you it. Exit codes are meaningful: `0` success, `1` failure, `2` a usage error from argument parsing.
