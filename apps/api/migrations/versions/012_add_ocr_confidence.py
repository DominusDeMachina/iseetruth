"""add ocr_confidence to documents

Revision ID: 012
Revises: 011
Create Date: 2026-04-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "ocr_confidence")
