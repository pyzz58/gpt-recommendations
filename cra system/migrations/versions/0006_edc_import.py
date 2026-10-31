"""Add EDC Excel previews, reusable mappings and immutable lab snapshots.

Revision ID: 0006_edc_import
Revises: 0005_issues_monitoring
Create Date: 2026-10-31
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0006_edc_import'
down_revision: str | None = '0005_issues_monitoring'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_source_documents_purpose",
        "source_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_source_documents_purpose",
        "source_documents",
        "purpose IN ('rule','fact','edc_export','carryover_report','track',"
        "'directory','template','other')",
    )
    op.drop_constraint(
        "ck_source_documents_type",
        "source_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_source_documents_type",
        "source_documents",
        "document_type IN ('protocol','ib','sop','monitoring_plan','qa',"
        "'manual','report','track','edc_export','directory','template',"
        "'text','other')",
    )
    op.create_table('edc_import_mappings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.String(length=128), nullable=False),
    sa.Column('study_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('header_signature', sa.String(length=64), nullable=False),
    sa.Column('mapping_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=128), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('revision >= 1', name='ck_edc_import_mappings_revision'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'site_id'], ['sites.tenant_id', 'sites.study_id', 'sites.id'], name='fk_edc_import_mappings_site', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'study_id', 'id', name='uq_edc_import_mappings_study_id'),
    sa.UniqueConstraint('tenant_id', 'study_id', 'site_id', 'name', name='uq_edc_import_mappings_name')
    )
    op.create_index('ix_edc_import_mappings_signature', 'edc_import_mappings', ['tenant_id', 'study_id', 'site_id', 'header_signature', 'revision'], unique=False)
    op.create_table('edc_import_previews',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.String(length=128), nullable=False),
    sa.Column('study_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('source_document_version_id', sa.UUID(), nullable=False),
    sa.Column('source_sha256', sa.String(length=64), nullable=False),
    sa.Column('parser_name', sa.String(length=64), nullable=False),
    sa.Column('parser_version', sa.String(length=32), nullable=False),
    sa.Column('header_signature', sa.String(length=64), nullable=False),
    sa.Column('export_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('scope_status', sa.String(length=16), nullable=False),
    sa.Column('export_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('export_completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('included_sheets', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('suggested_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('mapping_profile_id', sa.UUID(), nullable=True),
    sa.Column('identity_namespace', sa.String(length=64), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('snapshot_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('confirmed_by', sa.String(length=128), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("scope_status IN ('declared','unknown')", name='ck_edc_import_previews_scope_status'),
    sa.CheckConstraint("state IN ('preview','confirmed','failed')", name='ck_edc_import_previews_state'),
    sa.CheckConstraint('export_completed_at IS NULL OR export_started_at IS NULL OR export_completed_at >= export_started_at', name='ck_edc_import_previews_export_window'),
    sa.CheckConstraint('revision >= 1', name='ck_edc_import_previews_revision'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'mapping_profile_id'], ['edc_import_mappings.tenant_id', 'edc_import_mappings.study_id', 'edc_import_mappings.id'], name='fk_edc_import_previews_mapping', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'site_id'], ['sites.tenant_id', 'sites.study_id', 'sites.id'], name='fk_edc_import_previews_site', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'source_document_version_id'], ['document_versions.tenant_id', 'document_versions.study_id', 'document_versions.id'], name='fk_edc_import_previews_source', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'study_id', 'id', name='uq_edc_import_previews_study_id')
    )
    op.create_index('ix_edc_import_previews_source', 'edc_import_previews', ['tenant_id', 'study_id', 'site_id', 'source_sha256'], unique=False)
    op.create_table('edc_preview_cells',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.String(length=128), nullable=False),
    sa.Column('study_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('preview_id', sa.UUID(), nullable=False),
    sa.Column('sheet_name', sa.String(length=255), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=False),
    sa.Column('column_number', sa.Integer(), nullable=False),
    sa.Column('coordinate', sa.String(length=32), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=True),
    sa.Column('formula', sa.Text(), nullable=True),
    sa.Column('cached_text', sa.Text(), nullable=True),
    sa.Column('cell_type', sa.String(length=32), nullable=False),
    sa.Column('number_format', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('row_number >= 1 AND column_number >= 1', name='ck_edc_preview_cells_coordinate'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'preview_id'], ['edc_import_previews.tenant_id', 'edc_import_previews.study_id', 'edc_import_previews.id'], name='fk_edc_preview_cells_preview', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('preview_id', 'sheet_name', 'row_number', 'column_number', name='uq_edc_preview_cell_coordinate')
    )
    op.create_index('ix_edc_preview_cells_row', 'edc_preview_cells', ['preview_id', 'sheet_name', 'row_number', 'column_number'], unique=False)
    op.create_table('edc_preview_sheets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.String(length=128), nullable=False),
    sa.Column('study_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('preview_id', sa.UUID(), nullable=False),
    sa.Column('sheet_name', sa.String(length=255), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('sheet_state', sa.String(length=16), nullable=False),
    sa.Column('max_row', sa.Integer(), nullable=False),
    sa.Column('max_column', sa.Integer(), nullable=False),
    sa.Column('header_row', sa.Integer(), nullable=True),
    sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('populated_rows', sa.Integer(), nullable=False),
    sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("sheet_state IN ('visible','hidden','veryHidden')", name='ck_edc_preview_sheets_state'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'preview_id'], ['edc_import_previews.tenant_id', 'edc_import_previews.study_id', 'edc_import_previews.id'], name='fk_edc_preview_sheets_preview', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('preview_id', 'sheet_name', name='uq_edc_preview_sheets_name')
    )
    op.create_table('edc_snapshots',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.String(length=128), nullable=False),
    sa.Column('study_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('preview_id', sa.UUID(), nullable=False),
    sa.Column('source_document_version_id', sa.UUID(), nullable=False),
    sa.Column('mapping_profile_id', sa.UUID(), nullable=True),
    sa.Column('mapping_revision', sa.Integer(), nullable=True),
    sa.Column('source_sha256', sa.String(length=64), nullable=False),
    sa.Column('mapping_digest', sa.String(length=64), nullable=False),
    sa.Column('scope_digest', sa.String(length=64), nullable=False),
    sa.Column('snapshot_key', sa.String(length=64), nullable=False),
    sa.Column('mapping_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('export_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('scope_status', sa.String(length=16), nullable=False),
    sa.Column('export_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('export_completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sheet_manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('row_count', sa.Integer(), nullable=False),
    sa.Column('record_count', sa.Integer(), nullable=False),
    sa.Column('absence_semantics', sa.String(length=32), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("absence_semantics = 'not_seen_in_export'", name='ck_edc_snapshots_absence_semantics'),
    sa.CheckConstraint("scope_status IN ('declared','unknown')", name='ck_edc_snapshots_scope_status'),
    sa.CheckConstraint('row_count >= 0 AND record_count >= 0', name='ck_edc_snapshots_counts'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'mapping_profile_id'], ['edc_import_mappings.tenant_id', 'edc_import_mappings.study_id', 'edc_import_mappings.id'], name='fk_edc_snapshots_mapping', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'preview_id'], ['edc_import_previews.tenant_id', 'edc_import_previews.study_id', 'edc_import_previews.id'], name='fk_edc_snapshots_preview', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'site_id'], ['sites.tenant_id', 'sites.study_id', 'sites.id'], name='fk_edc_snapshots_site', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'source_document_version_id'], ['document_versions.tenant_id', 'document_versions.study_id', 'document_versions.id'], name='fk_edc_snapshots_source', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('preview_id', name='uq_edc_snapshots_preview'),
    sa.UniqueConstraint('tenant_id', 'study_id', 'id', name='uq_edc_snapshots_study_id'),
    sa.UniqueConstraint('tenant_id', 'study_id', 'site_id', 'snapshot_key', name='uq_edc_snapshots_key')
    )
    op.create_table('edc_snapshot_rows',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.String(length=128), nullable=False),
    sa.Column('study_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('snapshot_id', sa.UUID(), nullable=False),
    sa.Column('sheet_name', sa.String(length=255), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=False),
    sa.Column('row_anchor', sa.String(length=512), nullable=False),
    sa.Column('raw_values', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('formulas', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('cached_values', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('row_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'snapshot_id'], ['edc_snapshots.tenant_id', 'edc_snapshots.study_id', 'edc_snapshots.id'], name='fk_edc_snapshot_rows_snapshot', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('snapshot_id', 'sheet_name', 'row_number', name='uq_edc_snapshot_row'),
    sa.UniqueConstraint('tenant_id', 'study_id', 'id', name='uq_edc_snapshot_rows_study_id')
    )
    op.create_table('edc_lab_records',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.String(length=128), nullable=False),
    sa.Column('study_id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('snapshot_id', sa.UUID(), nullable=False),
    sa.Column('snapshot_row_id', sa.UUID(), nullable=False),
    sa.Column('subject_id', sa.UUID(), nullable=True),
    sa.Column('subject_external_id', sa.String(length=128), nullable=True),
    sa.Column('visit_key', sa.String(length=128), nullable=True),
    sa.Column('analyte', sa.String(length=255), nullable=False),
    sa.Column('value_raw', sa.Text(), nullable=True),
    sa.Column('value_type', sa.String(length=16), nullable=False),
    sa.Column('operator', sa.String(length=8), nullable=True),
    sa.Column('numeric_value', sa.Numeric(precision=30, scale=10), nullable=True),
    sa.Column('unit_raw', sa.String(length=64), nullable=True),
    sa.Column('collected_on', sa.Date(), nullable=True),
    sa.Column('collected_at', sa.DateTime(), nullable=True),
    sa.Column('precision', sa.String(length=16), nullable=False),
    sa.Column('timezone_status', sa.String(length=16), nullable=False),
    sa.Column('instance_type_raw', sa.String(length=128), nullable=True),
    sa.Column('instance_type', sa.String(length=32), nullable=False),
    sa.Column('repeat_instance', sa.String(length=128), nullable=False),
    sa.Column('instance_key', sa.String(length=512), nullable=False),
    sa.Column('report_on', sa.Date(), nullable=True),
    sa.Column('specimen', sa.String(length=128), nullable=True),
    sa.Column('lower_limit', sa.String(length=128), nullable=True),
    sa.Column('upper_limit', sa.String(length=128), nullable=True),
    sa.Column('identity_status', sa.String(length=16), nullable=False),
    sa.Column('validation_status', sa.String(length=24), nullable=False),
    sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('source_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("identity_status IN ('mapped','unmatched','ambiguous')", name='ck_edc_lab_records_identity_status'),
    sa.CheckConstraint("timezone_status IN ('unknown','explicit','date_only')", name='ck_edc_lab_records_timezone_status'),
    sa.CheckConstraint("validation_status IN ('ready_for_match','needs_review')", name='ck_edc_lab_records_validation_status'),
    sa.CheckConstraint("value_type IN ('exact','bound','text','unknown')", name='ck_edc_lab_records_value_type'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'snapshot_id'], ['edc_snapshots.tenant_id', 'edc_snapshots.study_id', 'edc_snapshots.id'], name='fk_edc_lab_records_snapshot', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'snapshot_row_id'], ['edc_snapshot_rows.tenant_id', 'edc_snapshot_rows.study_id', 'edc_snapshot_rows.id'], name='fk_edc_lab_records_row', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id', 'study_id', 'subject_id'], ['subjects.tenant_id', 'subjects.study_id', 'subjects.id'], name='fk_edc_lab_records_subject', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('snapshot_id', 'snapshot_row_id', 'analyte', 'instance_key', name='uq_edc_lab_records_instance')
    )
    op.create_index('ix_edc_lab_records_match', 'edc_lab_records', ['tenant_id', 'study_id', 'site_id', 'subject_external_id', 'analyte', 'collected_on', 'instance_type'], unique=False)
    op.execute(
        """
        CREATE FUNCTION cra_reject_edc_snapshot_change()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'EDC snapshots are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table_name in (
        "edc_snapshots",
        "edc_snapshot_rows",
        "edc_lab_records",
    ):
        op.execute(
            f"""
            CREATE TRIGGER cra_{table_name}_immutable
            BEFORE UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION cra_reject_edc_snapshot_change()
            """
        )


def downgrade() -> None:
    for table_name in (
        "edc_lab_records",
        "edc_snapshot_rows",
        "edc_snapshots",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS cra_{table_name}_immutable "
            f"ON {table_name}"
        )
    op.execute("DROP FUNCTION IF EXISTS cra_reject_edc_snapshot_change()")
    op.drop_index('ix_edc_lab_records_match', table_name='edc_lab_records')
    op.drop_table('edc_lab_records')
    op.drop_table('edc_snapshot_rows')
    op.drop_table('edc_snapshots')
    op.drop_table('edc_preview_sheets')
    op.drop_index('ix_edc_preview_cells_row', table_name='edc_preview_cells')
    op.drop_table('edc_preview_cells')
    op.drop_index('ix_edc_import_previews_source', table_name='edc_import_previews')
    op.drop_table('edc_import_previews')
    op.drop_index('ix_edc_import_mappings_signature', table_name='edc_import_mappings')
    op.drop_table('edc_import_mappings')
    # Preserve source files while restoring the pre-W07 closed enum values.
    op.execute(
        "UPDATE source_documents SET purpose = 'other', "
        "document_type = 'other' WHERE purpose = 'edc_export' "
        "OR document_type = 'edc_export'"
    )
    op.drop_constraint(
        "ck_source_documents_type",
        "source_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_source_documents_type",
        "source_documents",
        "document_type IN ('protocol','ib','sop','monitoring_plan','qa',"
        "'manual','report','track','directory','template','text','other')",
    )
    op.drop_constraint(
        "ck_source_documents_purpose",
        "source_documents",
        type_="check",
    )
    op.create_check_constraint(
        "ck_source_documents_purpose",
        "source_documents",
        "purpose IN ('rule','fact','carryover_report','track',"
        "'directory','template','other')",
    )
