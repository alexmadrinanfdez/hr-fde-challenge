from common.db import get_connection


def fetch_one(query: str, params: dict | None = None) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            row = cur.fetchone()
    return row or {}

def fetch_all(query: str, params: dict | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            rows = cur.fetchall()
    return rows

def get_core_funnel_metrics() -> dict:
    query = """
    SELECT
        COUNT(*)::int AS total_saved_calls,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE carrier_authorized = TRUE) / NULLIF(COUNT(*), 0),
            2
        ) AS authorized_carrier_rate,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE matched_load_id IS NOT NULL) / NULLIF(COUNT(*), 0),
            2
        ) AS load_match_rate,
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE final_outcome = 'transferred_after_agreement'
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS transfer_rate,
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE final_outcome = 'no_matching_load'
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS no_match_rate,
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE final_outcome = 'carrier_not_verified'
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS not_authorized_rate,
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE final_outcome = 'caller_not_interested'
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS caller_not_interested_rate,
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE final_outcome = 'incomplete_call'
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS incomplete_call_rate
    FROM calls
    """
    return fetch_one(query)

def get_negotiation_metrics() -> dict:
    query = """
    SELECT
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE final_outcome = 'transferred_after_agreement'
            ) / NULLIF(
                COUNT(*) FILTER (
                    WHERE final_outcome IN (
                        'transferred_after_agreement',
                        'negotiation_failed'
                    )
                ),
                0
            ),
            2
        ) AS negotiation_success_rate,
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE final_outcome = 'negotiation_failed'
            ) / NULLIF(
                COUNT(*) FILTER (
                    WHERE final_outcome IN (
                        'transferred_after_agreement',
                        'negotiation_failed'
                    )
                ),
                0
            ),
            2
        ) AS negotiation_failed_rate,
        ROUND(AVG(agreed_rate) FILTER (WHERE agreed_rate IS NOT NULL), 2) AS average_agreed_rate,
        ROUND(AVG(negotiation_turns) FILTER (WHERE negotiation_turns IS NOT NULL), 2) AS average_negotiation_turns
    FROM calls
    """
    return fetch_one(query)

def get_sentiment_distribution() -> list[dict]:
    query = """
    SELECT
        sentiment,
        COUNT(*)::int AS count,
        ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM calls), 0), 2) AS percentage
    FROM calls
    GROUP BY sentiment
    ORDER BY sentiment
    """
    return fetch_all(query)

def get_negative_sentiment_by_outcome() -> list[dict]:
    query = """
    SELECT
        final_outcome,
        COUNT(*) FILTER (WHERE sentiment = 'negative')::int AS negative_count,
        COUNT(*)::int AS total_count,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE sentiment = 'negative') / NULLIF(COUNT(*), 0),
            2
        ) AS negative_rate
    FROM calls
    GROUP BY final_outcome
    ORDER BY final_outcome
    """
    return fetch_all(query)

def get_successful_origin_facility_usage() -> list[dict]:
    query = """
    SELECT
        l.origin,
        COUNT(*)::int AS successful_call_count
    FROM calls c
    JOIN loads l ON c.matched_load_id = l.load_id
    WHERE c.final_outcome = 'transferred_after_agreement'
    GROUP BY l.origin
    ORDER BY successful_call_count DESC, l.origin
    """
    return fetch_all(query)

def get_successful_destination_facility_usage() -> list[dict]:
    query = """
    SELECT
        l.destination,
        COUNT(*)::int AS successful_call_count
    FROM calls c
    JOIN loads l ON c.matched_load_id = l.load_id
    WHERE c.final_outcome = 'transferred_after_agreement'
    GROUP BY l.destination
    ORDER BY successful_call_count DESC, l.destination
    """
    return fetch_all(query)

def get_origin_facility_usage_by_hour() -> list[dict]:
    query = """
    SELECT
        l.origin,
        EXTRACT(HOUR FROM c.call_started_at)::int AS hour_of_day,
        COUNT(*)::int AS call_count
    FROM calls c
    JOIN loads l ON c.matched_load_id = l.load_id
    WHERE c.final_outcome = 'transferred_after_agreement'
    GROUP BY l.origin, hour_of_day
    ORDER BY l.origin, hour_of_day
    """
    return fetch_all(query)

def get_destination_facility_usage_by_hour() -> list[dict]:
    query = """
    SELECT
        l.destination,
        EXTRACT(HOUR FROM c.call_started_at)::int AS hour_of_day,
        COUNT(*)::int AS call_count
    FROM calls c
    JOIN loads l ON c.matched_load_id = l.load_id
    WHERE c.final_outcome = 'transferred_after_agreement'
    GROUP BY l.destination, hour_of_day
    ORDER BY l.destination, hour_of_day
    """
    return fetch_all(query)

def get_top_origin_facilities(limit: int = 10) -> list[dict]:
    query = """
    SELECT
        l.origin,
        COUNT(*)::int AS call_count
    FROM calls c
    JOIN loads l ON c.matched_load_id = l.load_id
    GROUP BY l.origin
    ORDER BY call_count DESC, l.origin
    LIMIT %(limit)s
    """
    return fetch_all(query, {"limit": limit})

def get_top_destination_facilities(limit: int = 10) -> list[dict]:
    query = """
    SELECT
        l.destination,
        COUNT(*)::int AS call_count
    FROM calls c
    JOIN loads l ON c.matched_load_id = l.load_id
    GROUP BY l.destination
    ORDER BY call_count DESC, l.destination
    LIMIT %(limit)s
    """
    return fetch_all(query, {"limit": limit})

def get_facility_transfer_rate() -> list[dict]:
    query = """
    SELECT
        l.origin,
        l.destination,
        COUNT(*)::int AS total_matched_calls,
        COUNT(*) FILTER (
            WHERE c.final_outcome = 'transferred_after_agreement'
        )::int AS transferred_calls,
        ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE c.final_outcome = 'transferred_after_agreement'
            ) / NULLIF(COUNT(*), 0),
            2
        ) AS transfer_rate
    FROM calls c
    JOIN loads l ON c.matched_load_id = l.load_id
    GROUP BY l.origin, l.destination
    ORDER BY transfer_rate DESC NULLS LAST, total_matched_calls DESC, l.origin, l.destination
    """
    return fetch_all(query)

def get_operational_metrics() -> dict:
    query = """
    SELECT
        ROUND(
            AVG(EXTRACT(EPOCH FROM (call_ended_at - call_started_at))),
            2
        ) AS average_call_duration_seconds
    FROM calls
    """
    return fetch_one(query)

def get_average_call_duration_by_outcome() -> list[dict]:
    query = """
    SELECT
        final_outcome,
        ROUND(
            AVG(EXTRACT(EPOCH FROM (call_ended_at - call_started_at))),
            2
        ) AS average_call_duration_seconds
    FROM calls
    GROUP BY final_outcome
    ORDER BY final_outcome
    """
    return fetch_all(query)

def get_calls_by_hour() -> list[dict]:
    query = """
    SELECT
        EXTRACT(HOUR FROM call_started_at)::int AS hour_of_day,
        COUNT(*)::int AS call_count
    FROM calls
    GROUP BY hour_of_day
    ORDER BY hour_of_day
    """
    return fetch_all(query)

def get_recent_calls(limit: int = 100) -> list[dict]:
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
    LIMIT %(limit)s
    """
    return fetch_all(query, {"limit": limit})