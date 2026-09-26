"""Add editable user profile fields.

Revision ID: 004_add_user_profile_fields
Revises: 003_add_conversations_and_messages
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_add_user_profile_fields"
down_revision: Union[str, None] = "003_add_conversations_and_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "avatar_url",
            existing_type=sa.String(length=1024),
            type_=sa.Text(),
            existing_nullable=True,
        )
        batch_op.add_column(sa.Column("phone_number", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("phone_number")
        batch_op.alter_column(
            "avatar_url",
            existing_type=sa.Text(),
            type_=sa.String(length=1024),
            existing_nullable=True,
        )