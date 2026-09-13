"""Add Google OAuth and profile fields to users table.

Revision ID: 002_add_google_oauth_to_users
Revises: 001_initial_schema
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_google_oauth_to_users"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add google_id and unique index
    op.add_column("users", sa.Column("google_id", sa.String(length=255), nullable=True))
    op.create_index("idx_users_google_id", "users", ["google_id"], unique=True)

    # 2. Add avatar_url and auth_provider
    op.add_column("users", sa.Column("avatar_url", sa.String(length=1024), nullable=True))
    op.add_column("users", sa.Column("auth_provider", sa.String(length=50), nullable=False, server_default="local"))

    # 3. Make hashed_password nullable for OAuth accounts
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    # 1. Revert hashed_password nullability
    op.alter_column("users", "hashed_password", existing_type=sa.String(length=255), nullable=False)

    # 2. Drop auth_provider and avatar_url
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "avatar_url")

    # 3. Drop google_id index and column
    op.drop_index("idx_users_google_id", table_name="users")
    op.drop_column("users", "google_id")
