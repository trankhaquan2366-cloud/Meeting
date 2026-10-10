"""Add departments and link users to departments.

Revision ID: 9d7c4a2f1b63
Revises: 8ac42e61d137
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d7c4a2f1b63"
down_revision: Union[str, Sequence[str], None] = "8ac42e61d137"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "departments" not in tables:
        op.create_table(
            "departments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        )
        op.create_index("ix_departments_id", "departments", ["id"])
        op.create_index("ix_departments_name", "departments", ["name"], unique=True)

    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        raise RuntimeError("The users table must exist before this migration.")
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "department_id" not in columns:
        op.add_column(
            "users",
            sa.Column("department_id", sa.Integer(), nullable=True),
        )
        op.create_index("ix_users_department_id", "users", ["department_id"])
        op.create_foreign_key(
            "fk_users_department_id_departments",
            "users",
            "departments",
            ["department_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "department_id" in columns:
            foreign_keys = inspector.get_foreign_keys("users")
            for foreign_key in foreign_keys:
                if foreign_key.get("constrained_columns") == ["department_id"]:
                    op.drop_constraint(foreign_key["name"], "users", type_="foreignkey")
            indexes = {index["name"] for index in inspector.get_indexes("users")}
            if "ix_users_department_id" in indexes:
                op.drop_index("ix_users_department_id", table_name="users")
            op.drop_column("users", "department_id")

    if "departments" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("departments")}
        for index_name in ("ix_departments_name", "ix_departments_id"):
            if index_name in indexes:
                op.drop_index(index_name, table_name="departments")
        op.drop_table("departments")
