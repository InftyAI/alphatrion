"""Add default user

Revision ID: 264cf17e65e0
Revises: e35d91c5a67d
Create Date: 2026-03-01 13:39:06.564507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '264cf17e65e0'
down_revision: Union[str, Sequence[str], None] = 'e35d91c5a67d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        INSERT INTO users (uuid, username, email, avatar_url, meta, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000001', 'neo', 'neo@hiverge.ai', NULL, NULL, NOW(), NOW())
        ON CONFLICT (uuid) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO teams (uuid, name, description, meta, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000001', 'Default Team', 'This is the default team.', NULL, NOW(), NOW())
        ON CONFLICT (uuid) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO team_members (uuid, team_id, user_id, created_at, updated_at)
        VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', NOW(), NOW())
        ON CONFLICT (uuid) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DELETE FROM team_members WHERE uuid = '00000000-0000-0000-0000-000000000001';
        """
    )
    op.execute(
        """
        DELETE FROM teams WHERE uuid = '00000000-0000-0000-0000-000000000001';
        """
    )
    op.execute(
        """
        DELETE FROM users WHERE uuid = '00000000-0000-0000-0000-000000000001';
        """
    )
