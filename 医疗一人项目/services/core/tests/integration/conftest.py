from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def database_url() -> str:
    value = os.getenv("MEDICAL_ONE_TEST_DATABASE_URL", "")
    if not value:
        pytest.skip("Set MEDICAL_ONE_TEST_DATABASE_URL to run PostgreSQL integration tests")
    database_name = make_url(value).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("Integration tests require a database name ending in _test")
    return value


@pytest.fixture(scope="session")
def database(database_url: str) -> Iterator[Engine]:
    os.environ["MEDICAL_ONE_DATABASE_URL"] = database_url
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    core_root = Path(__file__).resolve().parents[2]
    config = Config(core_root / "alembic.ini")
    config.set_main_option("script_location", str(core_root / "migrations"))
    config.attributes["database_url"] = database_url
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def app_database_url(database: Engine, database_url: str) -> str:
    parsed = make_url(database_url)
    return URL.create(
        drivername=parsed.drivername,
        username="medical_one_app",
        password=None,
        host=parsed.host,
        port=parsed.port,
        database=parsed.database,
        query=parsed.query,
    ).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def app_database(database: Engine, app_database_url: str) -> Iterator[Engine]:
    engine = create_engine(app_database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        role = connection.execute(
            text(
                "SELECT current_user, rolsuper, rolbypassrls "
                "FROM pg_roles WHERE rolname = current_user"
            )
        ).one()
    assert role.current_user == "medical_one_app"
    assert role.rolsuper is False
    assert role.rolbypassrls is False
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(app_database: Engine, database: Engine) -> Iterator[sessionmaker[Session]]:
    with database.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                  policy_migration_operations,
                  policy_impacts,
                  policy_states,
                  policy_bundles,
                  restore_checks,
                  backup_snapshots,
                  trash_entries,
                  audit_evaluations,
                  audit_findings,
                  audit_runs,
                  analysis_reviews,
                  analysis_runs,
                  statistical_plans,
                  dataset_rows,
                  dataset_versions,
                  datasets,
                  stage_decisions,
                  stage_assessments,
                  task_reviews,
                  plan_nodes,
                  plans,
                  decisions,
                  opportunity_versions,
                  opportunities,
                  scientific_briefs,
                  evidence_links,
                  citations,
                  retrieval_snapshots,
                  claim_versions,
                  claims,
                  source_reviews,
                  impact_reviews,
                  provenance_edges,
                  knowledge_chunks,
                  source_passages,
                  extraction_tables,
                  document_extractions,
                  ingest_jobs,
                  upload_parts,
                  upload_sessions,
                  knowledge_document_versions,
                  knowledge_documents,
                  knowledge_blobs,
                  library_grants,
                  libraries,
                  skill_runs,
                  agent_runs,
                  agent_instances,
                  task_attempts,
                  outbox,
                  jobs,
                  task_versions,
                  task_dependencies,
                  tasks,
                  budget_ledger_entries,
                  budget_reservations,
                  budgets,
                  tool_audit_events,
                  external_authorizations,
                  professional_records,
                  external_deliverables,
                  external_contracts,
                  external_quotes,
                  external_engagements,
                  external_experts,
                  external_contacts,
                  external_organizations,
                  mail_send_attempts,
                  mail_send_authorizations,
                  mail_draft_attachments,
                  mail_drafts,
                  mail_messages,
                  mail_threads,
                  mail_accounts,
                  artifact_exports,
                  artifact_versions,
                  artifacts,
                  messages,
                  conversations,
                  events,
                  project_versions,
                  projects,
                  command_receipts,
                  sessions,
                  users,
                  workspaces
                CASCADE
                """
            )
        )
    yield sessionmaker(bind=app_database, expire_on_commit=False)
