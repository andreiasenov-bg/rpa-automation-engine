"""Price history API routes for price tracking and arbitrage.

Provides endpoints for:
- Storing price snapshots after scraping
- Querying price history for products
- Price comparison across marketplaces
- Price trend analysis
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from db.models.price_history import PriceHistory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/price-history", tags=["price-history"])


# --- Request/Response Models ---

class PriceSnapshotIn(BaseModel):
    workflow_id: str
    marketplace: str
    product_id: str
    product_title: Optional[str] = None
    price: float
    currency: str = "EUR"
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    rank: Optional[int] = None
    url: Optional[str] = None
    execution_id: Optional[str] = None
    extra_data: Optional[dict] = None


class PriceBulkIn(BaseModel):
    items: List[PriceSnapshotIn]


class PriceSnapshotOut(BaseModel):
    id: str
    product_id: str
    marketplace: str
    product_title: Optional[str]
    price: float
    currency: str
    rating: Optional[float]
    reviews_count: Optional[int]
    rank: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class PriceTrendOut(BaseModel):
    product_id: str
    marketplace: str
    current_price: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]
    avg_price: Optional[float]
    price_change_pct: Optional[float]
    data_points: int
    history: List[PriceSnapshotOut]


# --- Endpoints ---

@router.post("/bulk", response_model=dict)
async def store_prices_bulk(
    data: PriceBulkIn,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Store multiple price snapshots at once (after scraping)."""
    created = 0
    for item in data.items:
        ph = PriceHistory(
            workflow_id=item.workflow_id,
            marketplace=item.marketplace,
            product_id=item.product_id,
            product_title=item.product_title,
            price=item.price,
            currency=item.currency,
            rating=item.rating,
            reviews_count=item.reviews_count,
            rank=item.rank,
            url=item.url,
            execution_id=item.execution_id,
            extra_data=item.extra_data,
        )
        db.add(ph)
        created += 1
    await db.commit()
    logger.info(f"Stored {created} price snapshots")
    return {"stored": created}


@router.get("/product/{product_id}", response_model=PriceTrendOut)
async def get_product_history(
    product_id: str,
    marketplace: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get price history for a specific product."""
    since = datetime.utcnow() - timedelta(days=days)

    q = "SELECT * FROM price_history WHERE product_id = :pid AND created_at >= :since AND is_deleted = false"
    params = {"pid": product_id, "since": since}

    if marketplace:
        q += " AND marketplace = :mp"
        params["mp"] = marketplace

    q += " ORDER BY created_at DESC"

    result = await db.execute(text(q), params)
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(404, "No price history found")

    prices = [r["price"] for r in rows if r["price"]]
    history = [PriceSnapshotOut(**dict(r)) for r in rows]

    current = prices[0] if prices else None
    oldest = prices[-1] if len(prices) > 1 else current
    change_pct = ((current - oldest) / oldest * 100) if oldest and current else None

    return PriceTrendOut(
        product_id=product_id,
        marketplace=marketplace or rows[0]["marketplace"],
        current_price=current,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        avg_price=sum(prices) / len(prices) if prices else None,
        price_change_pct=round(change_pct, 2) if change_pct else None,
        data_points=len(rows),
        history=history,
    )


@router.get("/workflow/{workflow_id}/summary")
async def get_workflow_price_summary(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get price summary for all products tracked by a workflow."""
    q = text("""
        SELECT product_id, marketplace, product_title,
               MIN(price) as min_price, MAX(price) as max_price,
               AVG(price) as avg_price, COUNT(*) as data_points,
               (SELECT price FROM price_history ph2
                WHERE ph2.product_id = ph.product_id
                AND ph2.marketplace = ph.marketplace
                AND ph2.is_deleted = false
                ORDER BY ph2.created_at DESC LIMIT 1) as current_price
        FROM price_history ph
        WHERE workflow_id = :wid AND is_deleted = false
        GROUP BY product_id, marketplace, product_title
        ORDER BY product_id
    """)

    result = await db.execute(q, {"wid": workflow_id})
    rows = result.mappings().all()

    return {
        "workflow_id": workflow_id,
        "total_products": len(rows),
        "products": [dict(r) for r in rows],
    }


@router.get("/compare/{product_id}")
async def compare_prices(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Compare latest prices for a product across all marketplaces."""
    q = text("""
        SELECT DISTINCT ON (marketplace) marketplace, price, currency,
               product_title, rating, reviews_count, rank, url, created_at
        FROM price_history
        WHERE product_id = :pid AND is_deleted = false
        ORDER BY marketplace, created_at DESC
    """)

    result = await db.execute(q, {"pid": product_id})
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(404, "No prices found for this product")

    prices = [dict(r) for r in rows]
    min_price = min(prices, key=lambda x: x["price"])
    max_price = max(prices, key=lambda x: x["price"])

    return {
        "product_id": product_id,
        "marketplaces": len(prices),
        "best_price": min_price,
        "highest_price": max_price,
        "spread": round(max_price["price"] - min_price["price"], 2),
        "spread_pct": round(
            (max_price["price"] - min_price["price"]) / min_price["price"] * 100, 2
        ) if min_price["price"] > 0 else None,
        "all_prices": prices,
    }
