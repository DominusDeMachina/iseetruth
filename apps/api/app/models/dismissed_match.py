import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DismissedMatch(Base):
    """Tracks cross-investigation entity matches dismissed as false positives."""

    __tablename__ = "dismissed_matches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "entity_name",
            "entity_type",
            "source_investigation_id",
            "target_investigation_id",
            name="uq_dismissed_match",
        ),
    )
