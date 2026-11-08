"""Commands for reusable template-driven monitoring review."""
from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReviewItemStatus = Literal[
    "not_checked",
    "checked",
    "needs_clarification",
    "not_applicable",
    "skipped",
]


class ReviewContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewTemplateItemInput(ReviewContract):
    item_key: str = Field(min_length=1, max_length=96)
    section_key: str = Field(min_length=1, max_length=96)
    section_order: int = Field(ge=0)
    section_title: str = Field(min_length=1, max_length=255)
    question_order: int = Field(ge=0)
    question_text: str = Field(min_length=1, max_length=10000)
    source_locator: str = Field(min_length=1, max_length=512)
    source_quote: str = Field(min_length=1, max_length=10000)
    report_locator: str = Field(min_length=1, max_length=512)
    applicability: dict[str, Any] = Field(default_factory=dict)


class CreateReviewTemplateCommand(ReviewContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    source_document_version_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    items: list[ReviewTemplateItemInput] = Field(min_length=1, max_length=1000)
    warnings: list[dict[str, Any]] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_item_keys(self) -> "CreateReviewTemplateCommand":
        keys = [item.item_key for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("review template item keys must be unique")
        return self


class BindReviewTemplateCommand(ReviewContract):
    expected_revision: Literal[0] = 0
    idempotency_key: str = Field(min_length=1, max_length=128)
    review_template_version_id: uuid.UUID


class UpdateMonitoringReviewItemCommand(ReviewContract):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)
    status: ReviewItemStatus
    note: str | None = Field(default=None, max_length=10000)
    subject_id: uuid.UUID | None = None
    rule_version_ids: list[uuid.UUID] = Field(
        default_factory=list, max_length=100
    )
    linked_issue_id: uuid.UUID | None = None
    linked_comparison_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_unique_rules(self) -> "UpdateMonitoringReviewItemCommand":
        if len(self.rule_version_ids) != len(set(self.rule_version_ids)):
            raise ValueError("rule_version_ids must be unique")
        if self.status in {"needs_clarification", "skipped"} and not (
            self.note and self.note.strip()
        ):
            raise ValueError(
                "needs_clarification and skipped require a CRA note"
            )
        return self
