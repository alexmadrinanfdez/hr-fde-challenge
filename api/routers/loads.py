from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import verify_api_key
from api.schemas import LoadOut
from common.db import get_connection


router = APIRouter(tags=["loads"])


@router.get(
    "/loads",
    response_model=list[LoadOut],
    dependencies=[Depends(verify_api_key)],
)
def get_loads(
    origin: Optional[str] = Query(default=None),
    destination: Optional[str] = Query(default=None),
    equipment_type: Optional[str] = Query(default=None),
    pickup_datetime: Optional[datetime] = Query(default=None),
    delivery_datetime: Optional[datetime] = Query(default=None),
    weight: Optional[float] = Query(default=None),
    commodity_type: Optional[str] = Query(default=None),
    num_of_pieces: Optional[int] = Query(default=None),
    miles: Optional[float] = Query(default=None),
    dimensions: Optional[str] = Query(default=None),
):
    filters = []
    params = {}

    if origin is not None:
        filters.append("LOWER(origin) = LOWER(%(origin)s)")
        params["origin"] = origin

    if destination is not None:
        filters.append("LOWER(destination) = LOWER(%(destination)s)")
        params["destination"] = destination

    if equipment_type is not None:
        filters.append("LOWER(equipment_type) = LOWER(%(equipment_type)s)")
        params["equipment_type"] = equipment_type

    if pickup_datetime is not None:
        filters.append("pickup_datetime = %(pickup_datetime)s")
        params["pickup_datetime"] = pickup_datetime

    if delivery_datetime is not None:
        filters.append("delivery_datetime = %(delivery_datetime)s")
        params["delivery_datetime"] = delivery_datetime

    if weight is not None:
        filters.append("weight = %(weight)s")
        params["weight"] = weight

    if commodity_type is not None:
        filters.append("LOWER(commodity_type) = LOWER(%(commodity_type)s)")
        params["commodity_type"] = commodity_type

    if num_of_pieces is not None:
        filters.append("num_of_pieces = %(num_of_pieces)s")
        params["num_of_pieces"] = num_of_pieces

    if miles is not None:
        filters.append("miles = %(miles)s")
        params["miles"] = miles

    if dimensions is not None:
        filters.append("LOWER(dimensions) = LOWER(%(dimensions)s)")
        params["dimensions"] = dimensions

    query = """
    SELECT
        load_id,
        origin,
        destination,
        pickup_datetime,
        delivery_datetime,
        equipment_type,
        loadboard_rate,
        notes,
        weight,
        commodity_type,
        num_of_pieces,
        miles,
        dimensions
    FROM loads
    """

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY pickup_datetime DESC"

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch loads: {e}")

    return [LoadOut(**row) for row in rows]