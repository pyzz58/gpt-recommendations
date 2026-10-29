"""Typed action examples for CRA-R021/R025/R027/R029; in-memory, synthetic only."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json


@dataclass
class Action:
    id: str
    kind: str
    status: str = "open"
    completion_basis: dict | None = None
    history: list[dict] = field(default_factory=list)


@dataclass
class Issue:
    id: str
    finding: str
    location: str
    recommendation: str
    source_refs: list[dict]
    actions: list[Action]

    @property
    def complete(self) -> bool:
        return bool(self.actions) and all(action.status == "completed" for action in self.actions)


def confirm_pd_reported(action: Action, user_statement: str, actor: str) -> None:
    if action.kind != "pd_reporting":
        raise ValueError("This completion path is only for PD reporting.")
    if not user_statement.strip() or not actor.strip():
        raise ValueError("An explicit user statement and its actor are required.")
    action.status = "completed"
    action.completion_basis = {"type": "user_confirmation", "statement": user_statement, "actor": actor}
    action.history.append({"event": "confirmed_reported", **deepcopy(action.completion_basis)})


def record_reported_correction(action: Action, statement: str, actor: str) -> None:
    if action.kind == "pd_reporting":
        raise ValueError("Use explicit PD reporting confirmation.")
    if not statement.strip() or not actor.strip():
        raise ValueError("Record what was reported and by whom.")
    action.status = "reported_done"
    action.completion_basis = None
    action.history.append({"event": "reported_correction", "statement": statement, "actor": actor})


def verify_correction(action: Action, correct: bool, location: str, actor: str, note: str = "") -> None:
    if action.kind == "pd_reporting":
        raise ValueError("PD reporting does not require this extra verification gate.")
    if not location.strip() or not actor.strip():
        raise ValueError("A verification location and actor are required.")
    if not correct and not note.strip():
        raise ValueError("Describe the remaining problem.")
    result = {"event": "cra_verification", "correct": correct, "location": location, "actor": actor, "note": note}
    action.history.append(result)
    action.status = "completed" if correct else "needs_correction"
    action.completion_basis = deepcopy(result) if correct else None


def previsit_selection(issues: list[Issue], selected_ids: list[str]) -> list[dict]:
    by_id = {issue.id: issue for issue in issues}
    if len(selected_ids) != len(set(selected_ids)) or set(selected_ids) - by_id.keys():
        raise ValueError("Selected issue IDs must exist and be unique.")
    return [deepcopy(asdict(by_id[issue_id])) for issue_id in selected_ids]


@dataclass(frozen=True)
class Snapshot:
    content_json: str
    sha256: str


def make_snapshot(issues: list[Issue], coverage: dict) -> Snapshot:
    # The string is immutable; later changes to mutable Issue objects cannot rewrite it.
    payload = {"issues": [asdict(issue) for issue in issues], "coverage": deepcopy(coverage)}
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return Snapshot(content, hashlib.sha256(content.encode("utf-8")).hexdigest())
