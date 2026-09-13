"""EvaluationRun model for recording high-level benchmark experiment results."""

from typing import Optional
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin


class EvaluationRun(Base, UUIDMixin, TimestampMixin):
    """High-level metadata and summary metrics of an evaluation experiment.

    Note: The raw datasets remain in file storage ('evaluation/datasets/')
    to keep the application database lean and performant.
    """

    __tablename__ = "evaluation_runs"

    run_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    metrics_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
