"""Add google_refresh_token to users

Revision ID: cf70acc36382
Revises: 
Create Date: 2026-10-09 17:49:57.088496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf70acc36382'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Google Calendar OAuth columns to users when they are missing."""
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        raise RuntimeError("The users table must exist before applying this migration.")

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "google_refresh_token" not in existing_columns:
        op.add_column("users", sa.Column("google_refresh_token", sa.Text(), nullable=True))
    if "google_calendar_connected_at" not in existing_columns:
        op.add_column("users", sa.Column("google_calendar_connected_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove the Google Calendar OAuth columns when present."""
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "google_calendar_connected_at" in existing_columns:
        op.drop_column("users", "google_calendar_connected_at")
    if "google_refresh_token" in existing_columns:
        op.drop_column("users", "google_refresh_token")