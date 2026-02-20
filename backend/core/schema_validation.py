"""Schema validation for scraped data output.

Validates extracted data against expected schemas before storage.
Ensures data quality and catches extraction errors early.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)


class ProductData(BaseModel):
    """Validated product data from any marketplace."""
    product_id: str = Field(..., description="ASIN, EAN, SKU etc.")
    title: Optional[str] = None
    price: Optional[float] = None
    currency: str = "EUR"
    rating: Optional[float] = Field(None, ge=0, le=5)
    reviews_count: Optional[int] = Field(None, ge=0)
    rank: Optional[int] = Field(None, ge=0)
    url: Optional[str] = None
    marketplace: str = "unknown"
    extra: Optional[Dict[str, Any]] = None

    @validator("price", pre=True)
    def parse_price(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.replace(",", ".").replace("\u20ac", "").replace("$", "").replace("EUR", "").strip()
            try:
                return float(v)
            except ValueError:
                return None
        return float(v) if v else None

    @validator("rating", pre=True)
    def parse_rating(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.replace(",", ".").strip()
            try:
                return min(float(v), 5.0)
            except ValueError:
                return None
        return float(v) if v else None


class ScrapeResult(BaseModel):
    """Validated scrape execution result."""
    marketplace: str
    products: List[ProductData] = []
    total_found: int = 0
    errors: List[str] = []
    warnings: List[str] = []

    @validator("total_found", pre=True, always=True)
    def set_total(cls, v, values):
        return v or len(values.get("products", []))


def validate_scrape_output(
    data: List[Dict[str, Any]],
    marketplace: str = "unknown",
    product_id_key: str = "asin",
) -> ScrapeResult:
    """Validate a list of raw scraped dicts into structured ProductData.

    Args:
        data: Raw list of dicts from scraper
        marketplace: Source marketplace name
        product_id_key: Key in dict that holds the product identifier

    Returns:
        ScrapeResult with validated products and any errors
    """
    products = []
    errors = []
    warnings = []

    KEY_MAP = {
        "asin": "product_id", "ean": "product_id", "sku": "product_id",
        "product_id": "product_id", "id": "product_id",
        "name": "title", "title": "title", "product_title": "title",
        "price": "price", "current_price": "price",
        "rating": "rating", "stars": "rating", "avg_rating": "rating",
        "reviews": "reviews_count", "review_count": "reviews_count",
        "reviews_count": "reviews_count", "num_reviews": "reviews_count",
        "rank": "rank", "position": "rank", "best_seller_rank": "rank",
        "url": "url", "link": "url", "product_url": "url",
    }

    for i, item in enumerate(data):
        try:
            mapped = {"marketplace": marketplace}
            for k, v in item.items():
                mapped_key = KEY_MAP.get(k.lower())
                if mapped_key:
                    mapped[mapped_key] = v
                else:
                    if "extra" not in mapped:
                        mapped["extra"] = {}
                    mapped["extra"][k] = v

            if "product_id" not in mapped:
                if product_id_key in item:
                    mapped["product_id"] = str(item[product_id_key])
                else:
                    mapped["product_id"] = f"unknown-{i}"
                    warnings.append(f"Row {i}: no product_id found, using fallback")

            product = ProductData(**mapped)
            products.append(product)
        except Exception as e:
            errors.append(f"Row {i}: validation error: {str(e)}")

    if errors:
        logger.warning(f"Schema validation: {len(errors)} errors in {len(data)} items")

    return ScrapeResult(
        marketplace=marketplace,
        products=products,
        total_found=len(products),
        errors=errors,
        warnings=warnings,
    )
