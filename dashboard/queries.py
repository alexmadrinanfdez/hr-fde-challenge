from common.db import get_connection


def get_calls() -> list[dict]:
    query = """
    SELECT
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
    FROM calls
    ORDER BY call_started_at DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()


def get_loads() -> list[dict]:
    query = """
    SELECT
        load_id,
        origin,
        destination,
        equipment_type,
        loadboard_rate
    FROM loads
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()