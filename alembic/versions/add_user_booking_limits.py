"""Add per-day booking limits and room-approval bypass to users.

Revision ID: 7c2a9e4b1d63
Revises: f4a9b2c7d610
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c2a9e4b1d63"
down_revision: Union[str, Sequence[str], None] = "f4a9b2c7d610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        raise RuntimeError("The users table must exist before applying this migration.")

    columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "daily_booking_hours_limit" not in columns:
            batch_op.add_column(
                sa.Column("daily_booking_hours_limit", sa.Float(), nullable=True)
            )
        if "can_bypass_room_approval" not in columns:
            batch_op.add_column(
                sa.Column(
                    "can_bypass_room_approval",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "can_bypass_room_approval" in columns:
            batch_op.drop_column("can_bypass_room_approval")
        if "daily_booking_hours_limit" in columns:
            batch_op.drop_column("daily_booking_hours_limit")
