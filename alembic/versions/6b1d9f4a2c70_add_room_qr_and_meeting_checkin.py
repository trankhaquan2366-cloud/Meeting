"""Add room QR tokens and meeting check-in lifecycle fields.

Revision ID: 6b1d9f4a2c70
Revises: 33c26788d6a2
Create Date: 2026-10-10
"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "6b1d9f4a2c70"
down_revision: Union[str, Sequence[str], None] = "33c26788d6a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "rooms" not in tables or "meetings" not in tables:
        raise RuntimeError("The rooms and meetings tables must exist before this migration.")

    room_columns = {column["name"] for column in inspector.get_columns("rooms")}
    if "qr_token" not in room_columns:
        op.add_column("rooms", sa.Column("qr_token", sa.String(length=64), nullable=True))

    meeting_columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "check_in_time" not in meeting_columns:
        op.add_column("meetings", sa.Column("check_in_time", sa.DateTime(), nullable=True))
    if "check_out_time" not in meeting_columns:
        op.add_column("meetings", sa.Column("check_out_time", sa.DateTime(), nullable=True))
    if "reminder_sent" not in meeting_columns:
        op.add_column(
            "meetings",
            sa.Column(
                "reminder_sent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    room_table = sa.table(
        "rooms",
        sa.column("id", sa.Integer()),
        sa.column("qr_token", sa.String(length=64)),
    )
    for room_id, in bind.execute(
        sa.select(room_table.c.id).where(room_table.c.qr_token.is_(None))
    ):
        bind.execute(
            room_table.update()
            .where(room_table.c.id == room_id)
            .values(qr_token=str(uuid4()))
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("rooms")}
    unique_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("rooms")
    }
    if "ix_rooms_qr_token" not in indexes and "uq_rooms_qr_token" not in unique_constraints:
        op.create_index("ix_rooms_qr_token", "rooms", ["qr_token"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rooms" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("rooms")}
        if "ix_rooms_qr_token" in indexes:
            op.drop_index("ix_rooms_qr_token", table_name="rooms")
        columns = {column["name"] for column in inspector.get_columns("rooms")}
        if "qr_token" in columns:
            op.drop_column("rooms", "qr_token")

    if "meetings" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("meetings")}
        for column_name in ("reminder_sent", "check_out_time", "check_in_time"):
            if column_name in columns:
                op.drop_column("meetings", column_name)
