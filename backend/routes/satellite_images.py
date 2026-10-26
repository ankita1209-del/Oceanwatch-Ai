"""Read-only inventory of satellite TIFF image metadata."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import SatelliteImage

router = APIRouter()


@router.get("/satellite-images")
async def get_satellite_images(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    product_type: str | None = Query(default=None, min_length=1, max_length=80),
    session: AsyncSession = Depends(get_db),
):
    """Return inventory metadata only; TIFF file contents are not served."""
    filters = []
    if product_type:
        filters.append(
            func.lower(SatelliteImage.product_type) == product_type.strip().lower()
        )

    count_statement = select(func.count(SatelliteImage.id))
    records_statement = select(SatelliteImage)

    if filters:
        count_statement = count_statement.where(*filters)
        records_statement = records_statement.where(*filters)

    total = await session.scalar(count_statement)
    result = await session.scalars(
        records_statement.order_by(SatelliteImage.id).limit(limit).offset(offset)
    )

    items = [
        {
            "id": item.id,
            "image_filename": item.image_filename,
            "image_path": item.image_path,
            "sha256": item.sha256,
            "product_type": item.product_type,
            "filename_date_token": item.filename_date_token,
            "already_in_manifest": item.already_in_manifest,
            "hab_label": item.hab_label,
            "label_status": item.label_status,
            "validation_status": item.validation_status,
            "created_at": item.created_at,
        }
        for item in result.all()
    ]

    return {
        "total": total or 0,
        "limit": limit,
        "offset": offset,
        "items": items,
    }
