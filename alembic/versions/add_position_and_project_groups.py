"""Add user positions and project groups.

Revision ID: e8f2c6a9b314
Revises: d2e5f8a1c930
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f2c6a9b314"
down_revision: Union[str, Sequence[str], None] = "d2e5f8a1c930"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        raise RuntimeError("The users table must exist before this migration.")

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "position" not in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("position", sa.String(length=100), nullable=True))

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "project_groups" not in tables:
        op.create_table(
            "project_groups",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("code", sa.String(length=50), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_project_groups_id", "project_groups", ["id"])
        op.create_index(
            "ix_project_groups_code",
            "project_groups",
            ["code"],
            unique=True,
        )

    inspector = sa.inspect(bind)
    if "user_project_groups" not in inspector.get_table_names():
        op.create_table(
            "user_project_groups",
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "project_group_id",
                sa.Integer(),
                sa.ForeignKey("project_groups.id", ondelete="CASCADE"),
                primary_key=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "user_project_groups" in tables:
        op.drop_table("user_project_groups")
    if "project_groups" in tables:
        indexes = {
            index["name"] for index in inspector.get_indexes("project_groups")
        }
        for index_name in ("ix_project_groups_code", "ix_project_groups_id"):
            if index_name in indexes:
                op.drop_index(index_name, table_name="project_groups")
        op.drop_table("project_groups")

    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "position" in user_columns:
            with op.batch_alter_table("users") as batch_op:
                batch_op.drop_column("position")
