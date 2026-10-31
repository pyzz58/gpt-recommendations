"""Add subject identities, facts, visit requirements and check decisions.

Revision ID: 0004_subjects_coverage
Revises: 0003_rules_versions
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_subjects_coverage"
down_revision: str | None = "0003_rules_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deidentified_label", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(length=128), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("revision >= 1", name="ck_subjects_revision"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id"],
            ["studies.tenant_id", "studies.id"],
            name="fk_subjects_study_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "site_id"],
            ["sites.tenant_id", "sites.study_id", "sites.id"],
            name="fk_subjects_site_scope",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_subjects_study_id",
        ),
    )
    op.create_index(
        "ix_subjects_site_created",
        "subjects",
        ["tenant_id", "study_id", "site_id", "created_at"],
    )

    op.create_table(
        "subject_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_namespace", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "identity_namespace <> '' AND external_id <> ''",
            name="ck_subject_identifiers_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_subject_identifiers_subject",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "site_id",
            "identity_namespace",
            "external_id",
            name="uq_subject_identifiers_source",
        ),
    )

    op.create_table(
        "clinical_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fact_key", sa.String(length=128), nullable=False),
        sa.Column("repeat_instance", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("value_type", sa.String(length=16), nullable=False),
        sa.Column(
            "value_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("value_raw", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("observed_on", sa.Date(), nullable=True),
        sa.Column(
            "observed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("precision", sa.String(length=16), nullable=False),
        sa.Column("source_kind", sa.String(length=24), nullable=False),
        sa.Column(
            "verification_status", sa.String(length=24), nullable=False
        ),
        sa.Column(
            "source_ref",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "supersedes_fact_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_clinical_facts_revision"
        ),
        sa.CheckConstraint(
            "value_type IN ('date','datetime','decimal','string','boolean','json')",
            name="ck_clinical_facts_value_type",
        ),
        sa.CheckConstraint(
            "precision IN ('date','minute','second','unknown')",
            name="ck_clinical_facts_precision",
        ),
        sa.CheckConstraint(
            "source_kind IN ('original_record','cra_confirmation',"
            "'other_response','model_suggestion')",
            name="ck_clinical_facts_source_kind",
        ),
        sa.CheckConstraint(
            "verification_status IN ('original_record','cra_confirmed',"
            "'reported_by_other','model_candidate')",
            name="ck_clinical_facts_verification",
        ),
        sa.CheckConstraint(
            "(observed_on IS NOT NULL)::int + (observed_at IS NOT NULL)::int = 1",
            name="ck_clinical_facts_one_observed_time",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_clinical_facts_subject",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "supersedes_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_clinical_facts_supersedes",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_id",
            "fact_key",
            "repeat_instance",
            "revision",
            name="uq_clinical_facts_revision",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "study_id",
            "id",
            name="uq_clinical_facts_study_id",
        ),
    )
    op.create_index(
        "ix_clinical_facts_subject_key_revision",
        "clinical_facts",
        [
            "tenant_id",
            "study_id",
            "subject_id",
            "fact_key",
            "repeat_instance",
            "revision",
        ],
    )

    op.create_table(
        "visit_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_key", sa.String(length=64), nullable=False),
        sa.Column("repeat_instance", sa.String(length=128), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column(
            "planned_fact_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column(
            "actual_fact_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("planned_on", sa.Date(), nullable=True),
        sa.Column("actual_on", sa.Date(), nullable=True),
        sa.Column("precision", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "supersedes_visit_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_visit_instances_revision"
        ),
        sa.CheckConstraint(
            "(planned_fact_id IS NOT NULL OR actual_fact_id IS NOT NULL)",
            name="ck_visit_instances_has_fact",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_visit_instances_subject",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "planned_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_visit_instances_planned_fact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "actual_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_visit_instances_actual_fact",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_id",
            "visit_key",
            "repeat_instance",
            "revision",
            name="uq_visit_instances_revision",
        ),
    )
    op.create_index(
        "ix_visit_instances_subject_order",
        "visit_instances",
        [
            "tenant_id",
            "study_id",
            "subject_id",
            "visit_key",
            "revision",
        ],
    )

    op.create_table(
        "visit_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "rule_version_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("visit_key", sa.String(length=128), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("anchor_fact_key", sa.String(length=128), nullable=False),
        sa.Column("event_fact_key", sa.String(length=128), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column(
            "anchor_fact_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("anchor_date", sa.Date(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("min_days", sa.Integer(), nullable=False),
        sa.Column("max_days", sa.Integer(), nullable=False),
        sa.Column("inclusive", sa.Boolean(), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=True),
        sa.Column("window_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "required_fact_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "allowed_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "affected_paths",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "can_continue",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "input_fact_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "input_fact_revisions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "min_days <= max_days", name="ck_visit_requirements_days"
        ),
        sa.CheckConstraint(
            "status IN ('ready','in_window','out_of_window',"
            "'unknown_anchor','unknown_actual','not_checked_by_user',"
            "'needs_review')",
            name="ck_visit_requirements_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_visit_requirements_subject",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_visit_requirements_rule_version",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "anchor_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_visit_requirements_anchor_fact",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_id",
            "rule_version_id",
            "visit_key",
            "event_date",
            "content_hash",
            name="uq_visit_requirements_snapshot",
        ),
    )
    op.create_index(
        "ix_visit_requirements_subject_event",
        "visit_requirements",
        ["tenant_id", "study_id", "subject_id", "event_date"],
    )

    op.create_table(
        "fact_change_impacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_fact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("new_fact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dependent_type", sa.String(length=32), nullable=False),
        sa.Column("dependent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dependent_type IN ('visit_requirement','coverage_breakpoint',"
            "'check_decision')",
            name="ck_fact_change_impacts_dependent_type",
        ),
        sa.CheckConstraint(
            "status IN ('needs_review','reviewed')",
            name="ck_fact_change_impacts_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "old_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_fact_change_impacts_old_fact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "new_fact_id"],
            [
                "clinical_facts.tenant_id",
                "clinical_facts.study_id",
                "clinical_facts.id",
            ],
            name="fk_fact_change_impacts_new_fact",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fact_change_impacts_subject",
        "fact_change_impacts",
        ["tenant_id", "study_id", "subject_id", "created_at"],
    )

    op.create_table(
        "coverage_breakpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("scope_key", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("checked_through", sa.String(length=128), nullable=True),
        sa.Column("normal_scope_note", sa.String(length=1000), nullable=True),
        sa.Column(
            "unverified_scope",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "supersedes_breakpoint_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('laboratory','documents','consent','medication',"
            "'safety','visit_window','other')",
            name="ck_coverage_breakpoints_category",
        ),
        sa.CheckConstraint(
            "status IN ('in_progress','complete','not_checked')",
            name="ck_coverage_breakpoints_status",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_coverage_breakpoints_revision"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_coverage_breakpoints_subject",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_id",
            "category",
            "scope_key",
            "revision",
            name="uq_coverage_breakpoint_revision",
        ),
    )
    op.create_index(
        "ix_coverage_breakpoints_subject",
        "coverage_breakpoints",
        ["tenant_id", "study_id", "subject_id", "category", "revision"],
    )

    op.create_table(
        "check_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("study_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False),
        sa.Column("check_type", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("scope_start", sa.Date(), nullable=True),
        sa.Column("scope_end", sa.Date(), nullable=True),
        sa.Column(
            "missing_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "affected_paths",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "can_continue",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "rule_version_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("recovery_available", sa.Boolean(), nullable=False),
        sa.Column(
            "recovery_detected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resumed_by", sa.String(length=128), nullable=True),
        sa.Column(
            "resumed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("resume_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "category IN ('laboratory','documents','consent','medication',"
            "'safety','visit_window','other')",
            name="ck_check_decisions_category",
        ),
        sa.CheckConstraint(
            "reason IN ('declined_missing_data','unreadable_skip')",
            name="ck_check_decisions_reason",
        ),
        sa.CheckConstraint(
            "state IN ('active','resumed')",
            name="ck_check_decisions_state",
        ),
        sa.CheckConstraint(
            "revision >= 1", name="ck_check_decisions_revision"
        ),
        sa.CheckConstraint(
            "scope_end IS NULL OR scope_start IS NULL OR scope_end >= scope_start",
            name="ck_check_decisions_scope",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "subject_id"],
            ["subjects.tenant_id", "subjects.study_id", "subjects.id"],
            name="fk_check_decisions_subject",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "study_id", "rule_version_id"],
            [
                "rule_versions.tenant_id",
                "rule_versions.study_id",
                "rule_versions.id",
            ],
            name="fk_check_decisions_rule_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_check_decisions_subject_state",
        "check_decisions",
        ["tenant_id", "study_id", "subject_id", "state", "created_at"],
    )

    op.execute(
        """
        CREATE FUNCTION cra_reject_clinical_fact_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'clinical fact history is immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_clinical_fact_immutable
        BEFORE UPDATE OR DELETE ON clinical_facts
        FOR EACH ROW EXECUTE FUNCTION cra_reject_clinical_fact_change()
        """
    )
    op.execute(
        """
        CREATE FUNCTION cra_reject_coverage_breakpoint_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'coverage breakpoint versions are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER cra_coverage_breakpoint_immutable
        BEFORE UPDATE OR DELETE ON coverage_breakpoints
        FOR EACH ROW EXECUTE FUNCTION cra_reject_coverage_breakpoint_change()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS cra_coverage_breakpoint_immutable "
        "ON coverage_breakpoints"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS cra_reject_coverage_breakpoint_change()"
    )
    op.execute(
        "DROP TRIGGER cra_clinical_fact_immutable ON clinical_facts"
    )
    op.execute("DROP FUNCTION cra_reject_clinical_fact_change()")
    op.drop_index(
        "ix_check_decisions_subject_state", table_name="check_decisions"
    )
    op.drop_table("check_decisions")
    op.drop_index(
        "ix_coverage_breakpoints_subject",
        table_name="coverage_breakpoints",
    )
    op.drop_table("coverage_breakpoints")
    op.drop_index(
        "ix_fact_change_impacts_subject",
        table_name="fact_change_impacts",
    )
    op.drop_table("fact_change_impacts")
    op.drop_index(
        "ix_visit_requirements_subject_event",
        table_name="visit_requirements",
    )
    op.drop_table("visit_requirements")
    op.drop_index(
        "ix_visit_instances_subject_order", table_name="visit_instances"
    )
    op.drop_table("visit_instances")
    op.drop_index(
        "ix_clinical_facts_subject_key_revision",
        table_name="clinical_facts",
    )
    op.drop_table("clinical_facts")
    op.drop_table("subject_identifiers")
    op.drop_index("ix_subjects_site_created", table_name="subjects")
    op.drop_table("subjects")
