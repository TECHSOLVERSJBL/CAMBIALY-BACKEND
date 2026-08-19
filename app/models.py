# app/models.py
from sqlalchemy import BigInteger, Float, Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RateHistory(Base):
    """Una fila por captura de tasa: categoría, fuente, timestamp unix y payload JSON."""

    __tablename__ = "rate_history"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    last_updated: Mapped[float] = mapped_column(Float, nullable=False)  # Unix timestamp
    rates: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )

    __table_args__ = (
        Index("idx_history_cat_ts", "category", "last_updated"),
    )