"""add entity_count and extraction_confidence to documents

Revision ID: 005
Revises: 004
Create Date: 2026-03-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("entity_count", sa.Integer(), nullable=True))
    op.add_column(
        "documents", sa.Column("extraction_confidence", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("documents", "extraction_confidence")
    op.drop_column("documents", "entity_count")
