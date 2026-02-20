"""Price history model for tracking product prices over time."""

from typing import Optional
from sqlalchemy import Float, ForeignKey, Index, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from db.base import BaseModel


class PriceHistory(BaseModel):
    """Tracks historical prices for products across marketplaces.
    
    Used for price monitoring, arbitrage detection, and trend analysis.
    """
    __tablename__ = "price_history"

    workflow_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflows.id"), nullable=False
    )
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    product_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    execution_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("executions.id"), nullable=True
    )

    __table_args__ = (
        Index("idx_ph_workflow_product", "workflow_id", "product_id"),
        Index("idx_ph_marketplace_product", "marketplace", "product_id"),
        Index("idx_ph_created", "created_at"),
        Index("idx_ph_product_price", "product_id", "price"),
    )
