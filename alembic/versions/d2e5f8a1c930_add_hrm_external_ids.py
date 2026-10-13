"""Add external HRM identifiers and department codes.

Revision ID: d2e5f8a1c930
Revises: b1c4e7a9206d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e5f8a1c930"
down_revision: Union[str, Sequence[str], None] = "b1c4e7a9206d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexed nullable HRM identity columns on SQLite and MySQL."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("external_id", sa.String(length=50), nullable=True))
        batch_op.create_index("ix_users_external_id", ["external_id"], unique=False)

    with op.batch_alter_table("departments") as batch_op:
        batch_op.add_column(sa.Column("code", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("external_id", sa.String(length=50), nullable=True))
        batch_op.create_index("ix_departments_code", ["code"], unique=True)
        batch_op.create_index(
            "ix_departments_external_id",
            ["external_id"],
            unique=False,
        )


def downgrade() -> None:
    """Remove HRM identity columns and their indexes."""
    with op.batch_alter_table("departments") as batch_op:
        batch_op.drop_index("ix_departments_external_id")
        batch_op.drop_index("ix_departments_code")
        batch_op.drop_column("external_id")
        batch_op.drop_column("code")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_external_id")
        batch_op.drop_column("external_id")
