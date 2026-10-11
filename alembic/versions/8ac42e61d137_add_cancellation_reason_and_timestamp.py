"""Add cancellation reason and timestamp to meetings.

Revision ID: 8ac42e61d137
Revises: 6b1d9f4a2c70
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8ac42e61d137"
down_revision: Union[str, Sequence[str], None] = "6b1d9f4a2c70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "meetings" not in inspector.get_table_names():
        raise RuntimeError("The meetings table must exist before this migration.")

    columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "cancellation_reason" not in columns:
        op.add_column(
            "meetings",
            sa.Column("cancellation_reason", sa.Text(), nullable=True),
        )
    if "cancelled_at" not in columns:
        op.add_column(
            "meetings",
            sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        )

    meeting_table = sa.table(
        "meetings",
        sa.column("status", sa.String()),
        sa.column("cancellation_reason", sa.Text()),
        sa.column("cancelled_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
        sa.column("created_at", sa.DateTime()),
    )
    bind.execute(
        meeting_table.update()
        .where(
            sa.func.upper(meeting_table.c.status) == "CANCELLED_NO_SHOW",
            meeting_table.c.cancellation_reason.is_(None),
        )
        .values(cancellation_reason="Tự động hủy do quá 15 phút không check-in")
    )
    bind.execute(
        meeting_table.update()
        .where(
            sa.func.upper(meeting_table.c.status).in_(
                ["CANCELLED", "CANCELLED_NO_SHOW"]
            ),
            meeting_table.c.cancelled_at.is_(None),
        )
        .values(
            cancelled_at=sa.func.coalesce(
                meeting_table.c.updated_at,
                meeting_table.c.created_at,
            )
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "meetings" not in sa.inspect(bind).get_table_names():
        return

    columns = {column["name"] for column in sa.inspect(bind).get_columns("meetings")}
    if "cancelled_at" in columns:
        op.drop_column("meetings", "cancelled_at")
    if "cancellation_reason" in columns:
        op.drop_column("meetings", "cancellation_reason")
