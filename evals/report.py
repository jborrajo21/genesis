import json
import statistics
import sys
from pathlib import Path

RESULTS = Path(__file__).parent / "results"


def load(path=None):
    """Load a run's records. Defaults to the most recent run-*.jsonl (never smoke-*)."""
    if path is None:
        runs = sorted(RESULTS.glob("run-*.jsonl"))
        if not runs:
            raise SystemExit("no run-*.jsonl found in evals/results/")
        path = runs[-1]
    path = Path(path)
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    return path, [json.loads(ln) for ln in lines]


def models(records):
    """Model names in first-seen order."""
    seen = []
    for r in records:
        if r["model"] not in seen:
            seen.append(r["model"])
    return seen


def _pct(hits, total):
    return "—" if not total else f"{100 * hits / total:.0f}% ({hits}/{total})"


def _median(values):
    vals = [v for v in values if v is not None]
    return "—" if not vals else f"{statistics.median(vals):.0f}"


def _recommends_python(record):
    plan = record.get("plan") or {}
    return "python" in " ".join(plan.get("stack") or []).lower()


def _sweep(records):
    """The main sweep only — variance repeats excluded so they don't skew averages."""
    return [r for r in records if r["repeat"] == 0]


def summary(records):
    print("\n## Per-model summary\n")
    print("| Model | n | Plan valid | Built green | Rounds | Phases | Steps | Tokens | Secs |")
    print("|---|---|---|---|---|---|---|---|---|")
    for model in models(records):
        rs = [r for r in _sweep(records) if r["model"] == model]
        ok = [r for r in rs if r["plan_ok"]]
        attempted = [r for r in rs if r["installed"] is not None]
        green = [r for r in attempted if r["installed"] and r["tested"]]
        print(
            f"| {model} | {len(rs)} | {_pct(len(ok), len(rs))} "
            f"| {_pct(len(green), len(attempted))} "
            f"| {_median([r['rounds'] for r in rs])} "
            f"| {_median([r['phases'] for r in ok])} "
            f"| {_median([r['total_steps'] for r in ok])} "
            f"| {_median([r['tokens'] for r in rs])} "
            f"| {_median([r['seconds'] for r in rs])} |"
        )


def classification(records):
    print("\n## Classification, decomposed\n")
    print("Three different questions that a single accuracy number would conflate.\n")
    print("| Model | Recommended Python | Python plans accepted | Idea → buildable repo |")
    print("|---|---|---|---|")
    for model in models(records):
        parsed = [r for r in _sweep(records) if r["model"] == model and r["plan_ok"]]
        want = [r for r in parsed if r["expected_supported"]]
        py = [r for r in want if _recommends_python(r)]
        accepted = [r for r in py if r["supported"]]
        attempted = [r for r in _sweep(records) if r["model"] == model and r["expected_supported"]]
        built = [r for r in attempted if r["installed"] and r["tested"]]
        print(
            f"| {model} | {_pct(len(py), len(want))} | {_pct(len(accepted), len(py))} "
            f"| {_pct(len(built), len(attempted))} |"
        )
    print(
        "\n*Recommended Python* is a model-choice property — did the model reach for a stack "
        "Genesis can scaffold. *Python plans we accepted* isolates **our** heuristic: of the "
        "plans that did recommend Python, "
        "how many Genesis accepted as scaffoldable. *Idea → buildable "
        "repo* is what a user experiences, and is the product of both.\n\n"
        "The first two columns exclude plans that failed to parse — a failed plan has no "
        "stack to inspect and no `supported` value — which is why their n can be lower. "
        "*Idea → buildable repo* deliberately does not exclude them: a plan that never "
        "parsed produced no repo, and excluding it would reward a model for failing early."
    )


def by_expectation(records):
    print("\n## Accuracy, split by expectation\n")
    print("| Model | Expected supported | Expected unsupported |")
    print("|---|---|---|")
    for model in models(records):
        rs = [r for r in _sweep(records) if r["model"] == model and r["plan_ok"]]
        halves = []
        for expected in (True, False):
            half = [r for r in rs if r["expected_supported"] is expected]
            hits = [r for r in half if r["supported"] is expected]
            halves.append(_pct(len(hits), len(half)))
        print(f"| {model} | {halves[0]} | {halves[1]} |")


def variance(records):
    repeated = {}
    for r in records:
        key = (r["model"], r["idea"])
        repeated.setdefault(key, []).append(r)
    repeated = {k: v for k, v in repeated.items() if len(v) > 1}
    if not repeated:
        print("\n## Run-to-run variance\n\nNo repeated runs in this file.")
        return
    print("\n## Run-to-run variance\n")
    print("| Model | Idea | n | supported | steps | rounds |")
    print("|---|---|---|---|---|---|")
    for (model, idea), rs in repeated.items():
        sup = ",".join("T" if r["supported"] else "F" for r in rs)
        steps = ",".join(str(r["total_steps"]) for r in rs)
        rounds = ",".join(str(r["rounds"]) for r in rs)
        print(f"| {model} | {idea[:38]} | {len(rs)} | {sup} | {steps} | {rounds} |")


def failures(records):
    bad = [r for r in records if not r["plan_ok"]]
    broken = [
        r for r in records if r["installed"] is not None and not (r["installed"] and r["tested"])
    ]
    print("\n## Failures\n")
    if not bad and not broken:
        print("None.")
        return
    for r in bad:
        print(f"- **{r['model']}** · {r['idea']} → `{r['error']}`")
    for r in broken:
        stage = "install" if not r["installed"] else "tests"
        print(f"- **{r['model']}** · {r['idea']} → build failed at **{stage}**")


def main():
    path, records = load(sys.argv[1] if len(sys.argv) > 1 else None)
    print("# Tier 2 eval report\n")
    print(f"Source `{path.name}` · {len(records)} records · {len(_sweep(records))} in main sweep")
    summary(records)
    classification(records)
    by_expectation(records)
    variance(records)
    failures(records)


if __name__ == "__main__":
    main()
