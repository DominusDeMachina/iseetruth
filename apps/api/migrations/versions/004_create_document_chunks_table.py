"""create document_chunks table

Revision ID: 004
Revises: 003
Create Date: 2026-03-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("char_offset_start", sa.Integer(), nullable=False),
        sa.Column("char_offset_end", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
    )

    # Composite index for ordered chunk retrieval per document
    op.create_index(
        "ix_document_chunks_document_id_sequence_number",
        "document_chunks",
        ["document_id", "sequence_number"],
    )

    # Index for querying chunks by investigation
    op.create_index(
        "ix_document_chunks_investigation_id",
        "document_chunks",
        ["investigation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunks_investigation_id", table_name="document_chunks"
    )
    op.drop_index(
        "ix_document_chunks_document_id_sequence_number", table_name="document_chunks"
    )
    op.drop_table("document_chunks")
