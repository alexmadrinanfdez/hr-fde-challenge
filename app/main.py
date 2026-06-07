import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

from common.db import get_connection
from app.schemas import CallCreate, CallCreateResponse, LoadOut


app = FastAPI(title="Inbound Carrier Sales API")


@app.on_event("startup")
def startup_check():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
    except Exception as e:
        raise RuntimeError(f"Database connection failed during startup: {e}") from e

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/loads", response_model=list[LoadOut])
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

@app.post("/calls", response_model=CallCreateResponse, status_code=201)
def create_call(payload: CallCreate):
    call_id = payload.call_id or str(uuid.uuid4())

    insert_sql = """
    INSERT INTO calls (
        call_id,
        call_started_at,
        call_ended_at,
        mc_number,
        carrier_authorized,
        requested_origin,
        requested_destination,
        requested_equipment,
        requested_pickup_window,
        matched_load_id,
        agreed_rate,
        negotiation_turns,
        final_outcome,
        sentiment,
        transcript_url
    ) VALUES (
        %(call_id)s,
        %(call_started_at)s,
        %(call_ended_at)s,
        %(mc_number)s,
        %(carrier_authorized)s,
        %(requested_origin)s,
        %(requested_destination)s,
        %(requested_equipment)s,
        %(requested_pickup_window)s,
        %(matched_load_id)s,
        %(agreed_rate)s,
        %(negotiation_turns)s,
        %(final_outcome)s,
        %(sentiment)s,
        %(transcript_url)s
    )
    """

    values = {
        "call_id": call_id,
        "call_started_at": payload.call_started_at,
        "call_ended_at": payload.call_ended_at,
        "mc_number": payload.mc_number,
        "carrier_authorized": payload.carrier_authorized,
        "requested_origin": payload.requested_origin,
        "requested_destination": payload.requested_destination,
        "requested_equipment": payload.requested_equipment,
        "requested_pickup_window": payload.requested_pickup_window,
        "matched_load_id": payload.matched_load_id,
        "agreed_rate": payload.agreed_rate,
        "negotiation_turns": payload.negotiation_turns,
        "final_outcome": payload.final_outcome,
        "sentiment": payload.sentiment,
        "transcript_url": payload.transcript_url,
    }

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_sql, values)
            conn.commit()
    except ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail="matched_load_id does not reference an existing load",
        )
    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="call_id already exists",
        )
    except CheckViolation as e:
        raise HTTPException(
            status_code=400,
            detail=f"Constraint violation: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save call: {e}",
        )

    return CallCreateResponse(
        call_id=call_id,
        message="Call saved successfully",
    )