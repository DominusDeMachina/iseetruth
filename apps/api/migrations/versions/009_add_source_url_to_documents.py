"""add source_url to documents

Revision ID: 009
Revises: 008
Create Date: 2026-04-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source_url", sa.String(2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "source_url")
