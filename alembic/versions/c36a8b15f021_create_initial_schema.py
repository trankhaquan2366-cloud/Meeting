"""Create the initial database schema.

Revision ID: c36a8b15f021
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c36a8b15f021"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

metadata = sa.MetaData()

users = sa.Table(
    "users",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column("username", sa.String(length=50), nullable=False),
    sa.Column("email", sa.String(length=150), nullable=True),
    sa.Column("full_name", sa.String(length=150), nullable=True),
    sa.Column("hashed_password", sa.String(length=255), nullable=False),
    sa.Column("role", sa.String(length=20), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
    sa.UniqueConstraint("email"),
)
sa.Index("ix_users_id", users.c.id)
sa.Index("ix_users_username", users.c.username, unique=True)

rooms = sa.Table(
    "rooms",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column("name", sa.String(length=100), nullable=False),
    sa.Column("location", sa.String(length=255), nullable=True),
    sa.Column("capacity", sa.Integer(), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("amenities", sa.Text(), nullable=True),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
)
sa.Index("ix_rooms_id", rooms.c.id)
sa.Index("ix_rooms_name", rooms.c.name, unique=True)

meetings = sa.Table(
    "meetings",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column("title", sa.String(length=200), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column(
        "meeting_type",
        sa.String(length=20),
        nullable=False,
        server_default="offline",
    ),
    sa.Column("online_link", sa.String(length=500), nullable=True),
    sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("recurring_type", sa.String(length=20), nullable=True),
    sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="SET NULL")),
    sa.Column(
        "organizer_id",
        sa.Integer(),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
    ),
    sa.Column("start_time", sa.DateTime(), nullable=False),
    sa.Column("end_time", sa.DateTime(), nullable=False),
    sa.Column("status", sa.String(length=20), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
)
sa.Index("ix_meetings_id", meetings.c.id)
sa.Index("ix_meetings_title", meetings.c.title)
sa.Index("ix_meetings_room_id", meetings.c.room_id)
sa.Index("ix_meetings_organizer_id", meetings.c.organizer_id)

meeting_participants = sa.Table(
    "meeting_participants",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column(
        "meeting_id",
        sa.Integer(),
        sa.ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "user_id",
        sa.Integer(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "response_status",
        sa.String(length=20),
        nullable=False,
        server_default="pending",
    ),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("meeting_id", "user_id", name="uq_meeting_participant"),
)
sa.Index("ix_meeting_participants_id", meeting_participants.c.id)
sa.Index("ix_meeting_participants_meeting_id", meeting_participants.c.meeting_id)
sa.Index("ix_meeting_participants_user_id", meeting_participants.c.user_id)

equipments = sa.Table(
    "equipments",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column("name", sa.String(length=150), nullable=False),
    sa.Column("code", sa.String(length=50), nullable=True, unique=True),
    sa.Column("category", sa.String(length=50), nullable=True),
    sa.Column("total_qty", sa.Integer(), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("is_active", sa.Boolean(), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
)
sa.Index("ix_equipments_id", equipments.c.id)

meeting_equipments = sa.Table(
    "meeting_equipments",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column(
        "meeting_id",
        sa.Integer(),
        sa.ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "equipment_id",
        sa.Integer(),
        sa.ForeignKey("equipments.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    sa.Column("quantity", sa.Integer(), nullable=False),
    sa.Column("note", sa.String(length=255), nullable=True),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("meeting_id", "equipment_id", name="uq_meeting_equipment"),
)
sa.Index("ix_meeting_equipments_id", meeting_equipments.c.id)

room_equipments = sa.Table(
    "room_equipments",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column(
        "room_id",
        sa.Integer(),
        sa.ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "equipment_id",
        sa.Integer(),
        sa.ForeignKey("equipments.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("quantity", sa.Integer(), nullable=False),
    sa.UniqueConstraint("room_id", "equipment_id", name="uq_room_equipment"),
)
sa.Index("ix_room_equipments_id", room_equipments.c.id)

notifications = sa.Table(
    "notifications",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column(
        "user_id",
        sa.Integer(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "meeting_id",
        sa.Integer(),
        sa.ForeignKey("meetings.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("title", sa.String(length=200), nullable=False),
    sa.Column("content", sa.Text(), nullable=False),
    sa.Column("is_read", sa.Boolean(), nullable=True),
    sa.Column("created_at", sa.DateTime(), nullable=True),
)
sa.Index("ix_notifications_id", notifications.c.id)
sa.Index("ix_notifications_meeting_id", notifications.c.meeting_id)

meeting_reminders = sa.Table(
    "meeting_reminders",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column(
        "meeting_id",
        sa.Integer(),
        sa.ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "user_id",
        sa.Integer(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("reminder_type", sa.String(length=50), nullable=False),
    sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint(
        "meeting_id",
        "user_id",
        "reminder_type",
        name="uq_meeting_user_reminder",
    ),
)
sa.Index("ix_meeting_reminders_id", meeting_reminders.c.id)
sa.Index("ix_meeting_reminders_meeting_id", meeting_reminders.c.meeting_id)
sa.Index("ix_meeting_reminders_user_id", meeting_reminders.c.user_id)

google_calendar_events = sa.Table(
    "google_calendar_events",
    metadata,
    sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
    sa.Column(
        "user_id",
        sa.Integer(),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "meeting_id",
        sa.Integer(),
        sa.ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("google_event_id", sa.String(length=255), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    sa.UniqueConstraint("user_id", "meeting_id", name="uq_google_event_user_meeting"),
    sa.UniqueConstraint("user_id", "google_event_id", name="uq_google_event_user_event"),
)


def upgrade() -> None:
    metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    metadata.drop_all(bind=op.get_bind(), checkfirst=True)
