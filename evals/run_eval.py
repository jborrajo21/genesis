import time
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from evals.counting_adapter import CountingAdapter
from genesis.core import _build_adapter
from genesis.planner import Planner
from genesis.scaffolder import build_and_test, scaffold

MAX_ROUNDS = 6
MAX_TOKENS = 10000
ANSWER = "no preference"

IDEAS = [
    ("a CLI todo app with local storage", True),
    ("a log file parser that summarises errors", True),
    ("a tool to rename files in bulk by pattern", True),
    ("a CSV-to-JSON converter with validation", True),
    ("a static site generator from markdown", True),
    ("a directory tree size analyser", True),
    ("a command-line password generator with a strength meter", True),
    ("a tool that dedupes photos by content hash", True),
    ("a git commit message linter", True),
    ("a CLI that turns RSS feeds into a daily digest", True),
    ("an iOS habit tracker", False),
    ("a React dashboard for server metrics", False),
    ("a multiplayer game server in Rust", False),
    ("an Android podcast client", False),
    ("a Django REST API with Postgres", False),
    ("a Kubernetes operator in Go", False),
    ("a Chrome extension that blocks distracting sites", False),
    ("a Unity 2D platformer", False),
    ("a Swift macOS menu-bar app", False),
    ("a real-time chat web app with WebSockets", False),
]


@dataclass
class Record:
    idea: str
    expected_supported: bool
    adapter: str
    model: str
    repeat: int
    plan_ok: bool = False
    error: str | None = None
    supported: bool | None = None
    rounds: int | None = None
    phases: int | None = None
    total_steps: int | None = None
    tokens: int | None = None
    seconds: float | None = None
    installed: bool | None = None
    tested: bool | None = None
    build_output: str | None = None
    plan: dict | None = None


def run_one(idea, expected, adapter_name, model, repeat=0, build=True, adapter=None):
    """Run one idea through plan → scaffold → build. Never raises; failures become data."""
    record = Record(
        idea=idea,
        expected_supported=expected,
        adapter=adapter_name,
        model=model,
        repeat=repeat,
    )
    counting = CountingAdapter(None)
    started = time.time()
    try:
        counting = CountingAdapter(adapter or _build_adapter(adapter_name, model, MAX_TOKENS))
        plan = Planner(counting).plan(
            idea,
            answer_fn=lambda questions: [ANSWER] * len(questions),
            max_rounds=MAX_ROUNDS,
        )
        record.plan_ok = True
        record.supported = plan.supported
        record.phases = len(plan.phases)
        record.total_steps = sum(len(p.steps) for p in plan.phases)
        record.plan = asdict(plan)
        if plan.supported and build:
            with TemporaryDirectory() as tmp:
                result = build_and_test(scaffold(plan, Path(tmp) / "gen"))
                record.installed = result.installed
                record.tested = result.tested
                if not result.ok:
                    record.build_output = result.output[-2000:]
    except Exception as e:
        record.error = f"{type(e).__name__}: {e}"
    finally:
        record.seconds = round(time.time() - started, 1)
        record.rounds = counting.rounds
        record.tokens = counting.tokens
    return record
