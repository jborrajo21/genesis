import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Literal

from genesis.adapter import Message, ModelAdapter, StopReason
from genesis.errors import GenesisError
from genesis.template_registry import select_template

_PLANNING_INSTRUCTION = """\
You are a software project planner. Your plan will be handed to an AI agent that \
builds the project from it, so the plan's detail and accuracy directly determine how \
well the project gets built. Aim for a plan a competent developer could follow without \
having to guess.

Given the developer's idea and any answers provided so far, decide between two moves:

- ASK, if key information is still missing to plan well. Return only the clarifying \
questions whose answers would most change the plan — the smallest set that removes the \
biggest uncertainties. Do not pad the list; ask fewer (or none) if the idea is already \
clear enough to plan.

- PLAN, if you have enough to write a thorough, buildable plan.

Respond with ONLY a JSON object and no other text, in exactly one of these two shapes:

To ask:
{"status": "need_info", "questions": ["...", "..."]}

To plan:
{"status": "ready", "plan": {
  "project_name": "short-name",
  "summary": "one or two sentences on what it does",
  "stack": ["language + version", "key library", "storage", "..."],
  "phases": [
    {"name": "Phase name", "steps": ["concrete actionable step", "..."]},
    {"name": "Next phase", "steps": ["..."]}
  ],
  "manual_checklist": ["setup a human must do by hand, e.g. create an API key"]
}}

Make phases sequential and each step concrete and actionable — a developer should know \
exactly what to do. Do not include a "supported" field; that is determined elsewhere.
"""

_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["need_info", "ready"]},
        "questions": {"type": "array", "items": {"type": "string"}},
        "plan": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"},
                "summary": {"type": "string"},
                "stack": {"type": "array", "items": {"type": "string"}},
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "steps": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "steps"],
                        "additionalProperties": False,
                    },
                },
                "manual_checklist": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["project_name", "summary", "stack", "phases"],
            "additionalProperties": False,
        },
    },
    "required": ["status"],
    "additionalProperties": False,
}


@dataclass
class Phase:
    name: str
    steps: list[str]


@dataclass
class Plan:
    project_name: str
    summary: str
    stack: list[str]
    supported: bool
    phases: list[Phase]
    manual_checklist: list[str] = field(default_factory=list)


class PlannerError(GenesisError):
    pass


@dataclass
class RoundResult:
    status: Literal["need_info", "ready"]
    questions: list[str] = field(default_factory=list)
    plan: Plan | None = None


def _parse_plan(data: dict) -> Plan:
    return Plan(
        project_name=data["project_name"],
        summary=data["summary"],
        stack=data["stack"],
        supported=select_template(data["stack"]) is not None,
        phases=[Phase(name=p["name"], steps=p["steps"]) for p in data["phases"]],
        manual_checklist=data.get("manual_checklist", []),
    )


def _extract_json(text: str) -> Any:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _format_qa(questions: list[str], answers: list[str]) -> str:
    return "\n".join(f"Q: {q}\nA: {a}" for q, a in zip(questions, answers))


class Planner:
    def __init__(self, adapter: ModelAdapter):
        self._adapter = adapter

    def _round(self, conversation: list[Message]) -> RoundResult:
        messages = [Message(role="system", content=_PLANNING_INSTRUCTION)] + conversation
        completion = self._adapter.complete(messages, response_schema=_PLAN_SCHEMA)
        if completion.stop_reason is StopReason.TRUNCATED:
            raise PlannerError(
                "response was truncated by max_tokens — increase --max-tokens and try again"
            )
        try:
            data = _extract_json(completion.text)
        except (json.JSONDecodeError, ValueError) as e:
            raise PlannerError(f"model did not return valid JSON: {e}") from e

        if not isinstance(data, dict):
            raise PlannerError(f"expected a JSON object, got {type(data).__name__}")

        status = data.get("status")
        try:
            if status == "need_info":
                return RoundResult(status="need_info", questions=data["questions"])
            if status == "ready":
                return RoundResult(status="ready", plan=_parse_plan(data["plan"]))
        except KeyError as e:
            raise PlannerError(f"malformed {status!r} response, missing key: {e}") from e
        raise PlannerError(f"unexpected status: {status!r}")

    def plan(
        self,
        idea: str,
        answer_fn: Callable[[list[str]], list[str]],
        max_rounds: int = 4,
    ) -> Plan:
        conversation = [Message(role="user", content=idea)]
        for _ in range(max_rounds):
            result = self._round(conversation)
            if result.status == "ready":
                if result.plan is None:
                    raise PlannerError("planner returned 'ready' without a plan")
                return result.plan
            answers = answer_fn(result.questions)
            conversation.append(Message(role="user", content=_format_qa(result.questions, answers)))
        return self._force_plan(conversation)

    def _force_plan(self, conversation: list[Message]) -> Plan:
        convo = conversation + [
            Message(
                role="user",
                content="No more clarification rounds. "
                "Produce the best complete plan you can now with status 'ready'.",
            )
        ]
        result = self._round(convo)
        if result.status == "ready":
            if result.plan is None:
                raise PlannerError("planner returned 'ready' without a plan")
            return result.plan
        raise PlannerError("planner could not produce a plan within max_rounds")

    def revise(self, plan: Plan, feedback: str) -> Plan:
        plan_dict = asdict(plan)
        plan_dict.pop("supported", None)
        conversation = [
            Message(role="assistant", content=json.dumps({"status": "ready", "plan": plan_dict})),
            Message(role="user", content=f"Revise the plan based on this feedback: {feedback}"),
        ]
        return self._force_plan(conversation)
