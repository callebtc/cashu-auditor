"""Add latitude and longitude columns to mints

Revision ID: add_mint_location
Revises: 75d17d60b8db
Create Date: 2024-11-21 16:35:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_mint_location"
down_revision: Union[str, None] = "75d17d60b8db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add latitude and longitude columns to mints table
    op.add_column("mints", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("mints", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove latitude and longitude columns from mints table
    op.drop_column("mints", "longitude")
    op.drop_column("mints", "latitude")
