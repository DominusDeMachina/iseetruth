"""Create dismissed_matches table for cross-investigation false positive tracking.

Revision ID: 010
Revises: 009
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dismissed_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_name", sa.String(512), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("source_investigation_id", sa.Uuid(), nullable=False),
        sa.Column("target_investigation_id", sa.Uuid(), nullable=False),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_investigation_id"],
            ["investigations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_investigation_id"],
            ["investigations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_name",
            "entity_type",
            "source_investigation_id",
            "target_investigation_id",
            name="uq_dismissed_match",
        ),
    )
    op.create_index(
        "ix_dismissed_matches_entity_name",
        "dismissed_matches",
        ["entity_name"],
    )
    op.create_index(
        "ix_dismissed_matches_source_investigation_id",
        "dismissed_matches",
        ["source_investigation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_dismissed_matches_source_investigation_id", "dismissed_matches")
    op.drop_index("ix_dismissed_matches_entity_name", "dismissed_matches")
    op.drop_table("dismissed_matches")
