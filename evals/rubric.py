import re
import sys

from evals.report import load, models

PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b|\betc\.")
FIELD_NAMES = {
    "summary",
    "stack",
    "phases",
    "manual checklist",
    "manual_checklist",
    "project name",
    "project_name",
}
MIN_STEP_CHARS = 15
MAX_EXAMPLES = 3


def _steps(plan):
    return [s for ph in plan.get("phases") or [] for s in (ph.get("steps") or [])]


def _fields_present(plan):
    return all(bool(plan.get(k)) for k in ("project_name", "summary", "stack", "phases"))


def _enough_phases(plan):
    return len(plan.get("phases") or []) >= 2


def _phases_have_steps(plan):
    phases = plan.get("phases") or []
    return bool(phases) and all(len(ph.get("steps") or []) >= 1 for ph in phases)


def _no_vague_filler(plan):
    text = " ".join([plan.get("summary") or ""] + _steps(plan))
    return not PLACEHOLDER.search(text)


def _steps_substantive(plan):
    steps = _steps(plan)
    return bool(steps) and all(len(s.strip()) >= MIN_STEP_CHARS for s in steps)


def _no_field_as_phase(plan):
    names = [(ph.get("name") or "").strip().lower() for ph in plan.get("phases") or []]
    return not any(n in FIELD_NAMES for n in names)


def _checklist_when_unsupported(plan):
    """N/A for supported plans — returns None so they leave the denominator."""
    if plan.get("supported"):
        return None
    return bool(plan.get("manual_checklist"))


CHECKS = [
    ("all fields present", _fields_present),
    ("2+ phases", _enough_phases),
    ("every phase has steps", _phases_have_steps),
    ("no vague filler text", _no_vague_filler),
    ("steps are substantive", _steps_substantive),
    ("no field name used as a phase", _no_field_as_phase),
    ("unsupported plan has a checklist", _checklist_when_unsupported),
]


def _pct(hits, total):
    return "—" if not total else f"{100 * hits / total:.0f}% ({hits}/{total})"


def scored(records):
    """Plans from the main sweep only, as (model, idea, plan)."""
    return [
        (r["model"], r["idea"], r["plan"])
        for r in records
        if r["repeat"] == 0 and r["plan_ok"] and r.get("plan")
    ]


def table(records):
    names = models(records)
    rows = scored(records)
    print("\n## Tier 3 — structural plan quality\n")
    print("A **quality signal, not a gate**. Deterministic checks only; no judged scoring.\n")
    print("| Check | " + " | ".join(names) + " |")
    print("|---" * (len(names) + 1) + "|")
    for label, fn in CHECKS:
        cells = []
        for model in names:
            results = [fn(plan) for m, _, plan in rows if m == model]
            applicable = [x for x in results if x is not None]
            cells.append(_pct(sum(applicable), len(applicable)))
        print(f"| {label} | " + " | ".join(cells) + " |")


def examples(records):
    print("\n## Example violations\n")
    shown = 0
    for label, fn in CHECKS:
        for model, idea, plan in scored(records):
            if fn(plan) is False:
                print(f"- **{label}** — {model} · {idea}")
                shown += 1
                break
        if shown >= MAX_EXAMPLES * len(CHECKS):
            break
    if not shown:
        print("None.")


def main():
    path, records = load(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"# Tier 3 rubric · `{path.name}`")
    table(records)
    examples(records)


if __name__ == "__main__":
    main()
