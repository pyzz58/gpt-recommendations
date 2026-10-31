"""Stage policy for checklist selection and concise handover summaries."""
from __future__ import annotations

from typing import Iterable, Protocol

STAGE_LABELS = {
    "previsit": "访前准备",
    "carryover_review": "遗留复核",
    "subject_review": "逐患者核查",
    "closeout": "中心关闭",
    "handover": "交接",
}

CHECKLIST_LABELS = {
    "startup": "中心启动清单",
    "closeout": "中心关闭清单",
}


class ChecklistItemLike(Protocol):
    title: str
    status: str


def checklist_stage_for_visit(stage: str) -> str | None:
    """Return the stage checklist most relevant to a workbench stage."""
    if stage == "previsit":
        return "startup"
    if stage in {"closeout", "handover"}:
        return "closeout"
    return None


def incomplete_checklist_items(
    items: Iterable[ChecklistItemLike],
) -> list[ChecklistItemLike]:
    return [
        item
        for item in items
        if item.status in {"open", "unknown"}
    ]


def concise_handover_summary(
    issue_count: int,
    issue_progress: Iterable[str],
    checklist_titles: Iterable[str],
) -> str:
    """Compose a brief factual handover statement without adding approval."""
    progress = [item for item in issue_progress if item.strip()]
    titles = [item for item in checklist_titles if item.strip()]
    if issue_count == 0 and not titles:
        return "本次交接无未完成遗留；后续按原记录继续。"
    parts: list[str] = []
    if issue_count:
        parts.append(f"{issue_count}项未完成遗留")
    if progress:
        parts.append("当前进展：" + "；".join(progress))
    if titles:
        parts.append("待继续清单：" + "、".join(titles))
    return "；".join(parts) + "。"
