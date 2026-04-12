"""add document_type to documents

Revision ID: 008
Revises: 007
Create Date: 2026-04-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("document_type", sa.String(10), nullable=False, server_default="pdf"),
    )


def downgrade() -> None:
    op.drop_column("documents", "document_type")
