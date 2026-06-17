from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import verify_api_key
from api.db import get_connection
from api.schemas import LoadOut


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
):
    filters = []
    params = {}

    if origin is not None:
        filters.append("origin ILIKE %(origin)s")
        params["origin"] = f"%{origin}%"

    if destination is not None:
        filters.append("destination ILIKE %(destination)s")
        params["destination"] = f"%{destination}%"

    if equipment_type is not None:
        filters.append("equipment_type ILIKE %(equipment_type)s")
        params["equipment_type"] = f"%{equipment_type}%"

    query = "SELECT * FROM loads"
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