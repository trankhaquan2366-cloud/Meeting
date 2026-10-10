"""Add the missing meeting_link column to meetings.

Revision ID: 33c26788d6a2
Revises: cf70acc36382
Create Date: 2026-10-09 19:15:47.700439
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "33c26788d6a2"
down_revision: Union[str, Sequence[str], None] = "cf70acc36382"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meeting_link if the existing database does not already have it."""
    inspector = sa.inspect(op.get_bind())
    if "meetings" not in inspector.get_table_names():
        raise RuntimeError("The meetings table must exist before applying this migration.")

    columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "meeting_link" not in columns:
        op.add_column("meetings", sa.Column("meeting_link", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove meeting_link if present."""
    inspector = sa.inspect(op.get_bind())
    if "meetings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "meeting_link" in columns:
        op.drop_column("meetings", "meeting_link")
