"""Merge existing migration heads and create RoomSync chat tables.

Revision ID: b1c4e7a9206d
Revises: 9d7c4a2f1b63, c36a8b15f021
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c4e7a9206d"
down_revision: Union[str, Sequence[str], None] = (
    "9d7c4a2f1b63",
    "c36a8b15f021",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "chat_sessions" not in tables:
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey(
                    "users.id",
                    name="fk_chat_sessions_user_id_users",
                    ondelete="CASCADE",
                ),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if "chat_messages" not in tables:
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "session_id",
                sa.Integer(),
                sa.ForeignKey(
                    "chat_sessions.id",
                    name="fk_chat_messages_session_id_chat_sessions",
                    ondelete="CASCADE",
                ),
                nullable=False,
            ),
            sa.Column(
                "sender",
                sa.Enum("user", "bot", name="chat_message_sender", native_enum=False),
                nullable=False,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("intent", sa.String(length=100), nullable=True),
            sa.Column("slots", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    for table_name, index_name, column_name in (
        ("chat_sessions", "ix_chat_sessions_id", "id"),
        ("chat_sessions", "ix_chat_sessions_user_id", "user_id"),
        ("chat_messages", "ix_chat_messages_id", "id"),
        ("chat_messages", "ix_chat_messages_session_id", "session_id"),
    ):
        indexes = {
            index["name"] for index in sa.inspect(bind).get_indexes(table_name)
        }
        if index_name not in indexes:
            op.create_index(index_name, table_name, [column_name])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    for table_name in ("chat_messages", "chat_sessions"):
        if table_name in tables:
            op.drop_table(table_name)
