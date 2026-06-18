from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

from api.auth import verify_api_key
from api.db import get_connection
from api.schemas import CallCreate, CallCreateResponse, CallOut


router = APIRouter(tags=["calls"])


@router.get(
    "/calls",
    response_model=list[CallOut],
    dependencies=[Depends(verify_api_key)],
)
def list_calls():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM calls ORDER BY call_time DESC")
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch calls: {e}")

    return [CallOut(**row) for row in rows]


@router.post(
    "/calls",
    response_model=CallCreateResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
)
def create_call(payload: CallCreate):
    insert_sql = """
    INSERT INTO calls (
        call_id, call_time, call_duration, mc_number, carrier_authorized,
        requested_origin, requested_destination, requested_equipment,
        requested_pickup_window, matched_load_id, agreed_rate, negotiation_turns,
        final_outcome, sentiment
    ) VALUES (
        %(call_id)s, %(call_time)s, %(call_duration)s, %(mc_number)s,
        %(carrier_authorized)s, %(requested_origin)s, %(requested_destination)s,
        %(requested_equipment)s, %(requested_pickup_window)s, %(matched_load_id)s,
        %(agreed_rate)s, %(negotiation_turns)s, %(final_outcome)s, %(sentiment)s
    )
    """

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_sql, payload.model_dump())
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
        call_id=payload.call_id,
        message="Call saved successfully",
    )