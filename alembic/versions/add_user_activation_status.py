"""Add a persisted account status for activation and administration.

Revision ID: f4a9b2c7d610
Revises: e8f2c6a9b314
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a9b2c7d610"
down_revision: Union[str, Sequence[str], None] = "e8f2c6a9b314"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        raise RuntimeError("The users table must exist before this migration.")

    columns = {column["name"] for column in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "status" not in columns:
            batch_op.add_column(
                sa.Column(
                    "status",
                    sa.String(length=20),
                    nullable=False,
                    server_default="ACTIVE",
                )
            )
        if "can_book" not in columns:
            batch_op.add_column(
                sa.Column(
                    "can_book",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )
        if "can_attend" not in columns:
            batch_op.add_column(
                sa.Column(
                    "can_attend",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )

    op.execute(
        sa.text(
            "UPDATE users SET status = 'INACTIVE' "
            "WHERE is_active = :inactive AND status = 'ACTIVE'"
        ).bindparams(inactive=False)
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        with op.batch_alter_table("users") as batch_op:
            if "can_attend" in columns:
                batch_op.drop_column("can_attend")
            if "can_book" in columns:
                batch_op.drop_column("can_book")
            if "status" in columns:
                batch_op.drop_column("status")
