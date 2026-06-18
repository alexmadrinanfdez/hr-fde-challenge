#!/usr/bin/env python3

import csv
import os
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation

import psycopg
from dotenv import load_dotenv


REQUIRED_COLUMNS = [
    "call_id",
    "call_time",
    "call_duration",
    "mc_number",
    "carrier_authorized",
    "final_outcome",
    "sentiment",
]


VALID_FINAL_OUTCOMES = {
    "booked",
    "no_agreement",
    "no_match",
    "not_verified",
    "not_interested",
    "incomplete"}


VALID_SENTIMENTS = {
    "positive",
    "neutral",
    "negative",
}


def parse_iso_datetime(value: str) -> datetime:
    value = (value or "").strip()
    if not value:
        raise ValueError("datetime is empty")

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_decimal(value: str, field_name: str, required: bool = False):
    value = (value or "").strip()
    if not value:
        if required:
            raise ValueError(f"{field_name} is required")
        return None

    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"{field_name} must be a valid number")

    if result < 0:
        raise ValueError(f"{field_name} must be >= 0")

    return result


def parse_int(value: str, field_name: str, required: bool = False):
    value = (value or "").strip()
    if not value:
        if required:
            raise ValueError(f"{field_name} is required")
        return None

    try:
        result = int(value)
    except ValueError:
        raise ValueError(f"{field_name} must be a valid integer")

    if result < 0:
        raise ValueError(f"{field_name} must be >= 0")

    return result


def parse_bool(value: str, field_name: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"true", "t", "1", "yes"}:
        return True
    if normalized in {"false", "f", "0", "no"}:
        return False
    raise ValueError(f"{field_name} must be a valid boolean")


def require_non_empty(row: dict, field_name: str) -> str:
    value = (row.get(field_name) or "").strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def validate_columns(fieldnames):
    if fieldnames is None:
        raise ValueError("CSV file is missing a header row")

    missing = [col for col in REQUIRED_COLUMNS if col not in fieldnames]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")


def normalize_row(row: dict) -> dict:
    normalized = {}

    normalized["call_id"] = require_non_empty(row, "call_id")
    normalized["call_time"] = parse_iso_datetime(require_non_empty(row, "call_time"))
    normalized["call_duration"] = parse_int(row.get("call_duration"), "call_duration", required=True)
    normalized["mc_number"] = require_non_empty(row, "mc_number")
    normalized["carrier_authorized"] = parse_bool(row.get("carrier_authorized"), "carrier_authorized")

    normalized["requested_origin"] = (row.get("requested_origin") or "").strip() or None
    normalized["requested_destination"] = (row.get("requested_destination") or "").strip() or None
    normalized["requested_equipment"] = (row.get("requested_equipment") or "").strip() or None
    normalized["requested_pickup_window"] = (row.get("requested_pickup_window") or "").strip() or None
    normalized["matched_load_id"] = (row.get("matched_load_id") or "").strip() or None
    normalized["agreed_rate"] = parse_decimal(row.get("agreed_rate"), "agreed_rate")
    normalized["negotiation_turns"] = parse_int(row.get("negotiation_turns"), "negotiation_turns")

    normalized["final_outcome"] = require_non_empty(row, "final_outcome")
    if normalized["final_outcome"] not in VALID_FINAL_OUTCOMES:
        raise ValueError("final_outcome is invalid")

    normalized["sentiment"] = require_non_empty(row, "sentiment")
    if normalized["sentiment"] not in VALID_SENTIMENTS:
        raise ValueError("sentiment is invalid")

    return normalized


def get_anchor_offset_hours() -> int:
    raw_value = os.getenv("CALLS_ANCHOR_OFFSET_HOURS", "0").strip()
    try:
        return int(raw_value)
    except ValueError:
        raise ValueError("CALLS_ANCHOR_OFFSET_HOURS must be a valid integer")


def shift_call_datetimes(rows: list[dict], anchor_offset_hours: int) -> list[dict]:
    if not rows:
        return rows

    earliest_start = min(row["call_time"] for row in rows)
    target_anchor = datetime.now(timezone.utc) + timedelta(hours=anchor_offset_hours)
    delta = target_anchor - earliest_start

    shifted_rows = []
    for row in rows:
        shifted = dict(row)
        shifted["call_time"] = row["call_time"] + delta
        shifted_rows.append(shifted)

    return shifted_rows


def upsert_calls(conn, rows):
    sql = """
    INSERT INTO calls (
        call_id,
        call_time,
        call_duration,
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
        sentiment
    ) VALUES (
        %(call_id)s,
        %(call_time)s,
        %(call_duration)s,
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
        %(sentiment)s
    )
    ON CONFLICT (call_id) DO UPDATE SET
        call_time = EXCLUDED.call_time,
        call_duration = EXCLUDED.call_duration,
        mc_number = EXCLUDED.mc_number,
        carrier_authorized = EXCLUDED.carrier_authorized,
        requested_origin = EXCLUDED.requested_origin,
        requested_destination = EXCLUDED.requested_destination,
        requested_equipment = EXCLUDED.requested_equipment,
        requested_pickup_window = EXCLUDED.requested_pickup_window,
        matched_load_id = EXCLUDED.matched_load_id,
        agreed_rate = EXCLUDED.agreed_rate,
        negotiation_turns = EXCLUDED.negotiation_turns,
        final_outcome = EXCLUDED.final_outcome,
        sentiment = EXCLUDED.sentiment
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def main():
    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    csv_path = os.getenv("CALLS_CSV_PATH", "data/calls.csv")

    if not db_url:
        print(
            "ERROR: DATABASE_URL is required. "
            "Set it in the environment or create a .env file from .env.template.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    try:
        anchor_offset_hours = get_anchor_offset_hours()
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    parsed_rows = []
    error_count = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        validate_columns(reader.fieldnames)

        for row_number, row in enumerate(reader, start=2):
            try:
                parsed_rows.append(normalize_row(row))
            except Exception as e:
                error_count += 1
                print(f"Row {row_number}: {e}", file=sys.stderr)

    if error_count > 0:
        print(
            f"ERROR: Validation failed for {error_count} row(s). Nothing was imported.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not parsed_rows:
        print("No rows found in CSV. Nothing to import.")
        sys.exit(0)

    shifted_rows = shift_call_datetimes(parsed_rows, anchor_offset_hours)

    try:
        with psycopg.connect(db_url) as conn:
            with conn.transaction():
                upsert_calls(conn, shifted_rows)
        print(
            f"Successfully imported {len(shifted_rows)} call(s) from {csv_path} "
            f"with call times shifted by anchor offset {anchor_offset_hours} hour(s)."
        )
    except Exception as e:
        print(f"ERROR: Database import failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()