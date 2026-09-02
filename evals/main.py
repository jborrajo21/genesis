import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from evals.run_eval import IDEAS, run_one

MODELS = [
    ("anthropic", "claude-haiku-4-5"),
    ("anthropic", "claude-sonnet-5"),
    ("ollama", "gemma4:latest"),
]

REPEAT_IDEA_INDEXES = (0, 10)  # one expected-supported, one expected-unsupported
REPEATS = 3


def _write(handle, record):
    """Append one record as a JSON line and force it to disk."""
    handle.write(json.dumps(asdict(record)) + "\n")
    handle.flush()


def main(smoke=False):
    ideas = IDEAS[:1] if smoke else IDEAS
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "smoke" if smoke else "run"
    out = Path(__file__).parent / "results" / f"{prefix}-{stamp}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w") as handle:
        for adapter_name, model in MODELS:
            for idea, expected in ideas:
                record = run_one(idea, expected, adapter_name, model)
                _write(handle, record)
                _progress(model, record)

            if smoke:
                continue
            for i in REPEAT_IDEA_INDEXES:
                idea, expected = IDEAS[i]
                for n in range(1, REPEATS + 1):
                    record = run_one(idea, expected, adapter_name, model, repeat=n)
                    _write(handle, record)
                    _progress(model, record)
    print(out)
    return out


def _progress(model, record):
    status = "ok " if record.plan_ok else "FAIL"
    build = "" if record.installed is None else f" build={record.installed and record.tested}"
    print(
        f"[{status}] {model:22} {record.seconds:6.1f}s "
        f"rounds={record.rounds} tokens={record.tokens}{build} :: {record.idea[:45]}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(smoke="--smoke" in sys.argv)
