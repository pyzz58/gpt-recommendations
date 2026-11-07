"""W22 live adapter state

Revision ID: a1c9e7f2d304
Revises: f4a2c7d9e601
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1c9e7f2d304"
down_revision: str | None = "f4a2c7d9e601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_mail_accounts_mail_account_state"),
        "mail_accounts",
        type_="check",
    )
    op.create_check_constraint(
        "mail_account_state",
        "mail_accounts",
        "state IN ('mock_ready', 'connected', 'send_only', 'unconfigured', 'disabled')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE mail_accounts SET state = 'connected' "
        "WHERE state = 'send_only'"
    )
    op.drop_constraint(
        op.f("ck_mail_accounts_mail_account_state"),
        "mail_accounts",
        type_="check",
    )
    op.create_check_constraint(
        "mail_account_state",
        "mail_accounts",
        "state IN ('mock_ready', 'connected', 'unconfigured', 'disabled')",
    )
