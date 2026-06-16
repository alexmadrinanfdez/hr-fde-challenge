#!/usr/bin/env python3

import csv
import os
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation

import psycopg
from dotenv import load_dotenv


REQUIRED_COLUMNS = [
    "load_id",
    "origin",
    "destination",
    "pickup_datetime",
    "delivery_datetime",
    "equipment_type",
    "loadboard_rate",
]


def parse_iso_datetime(value: str) -> datetime:
    value = value.strip()
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

    normalized["load_id"] = int(require_non_empty(row, "load_id"))
    normalized["origin"] = require_non_empty(row, "origin")
    normalized["destination"] = require_non_empty(row, "destination")
    normalized["pickup_datetime"] = parse_iso_datetime(require_non_empty(row, "pickup_datetime"))
    normalized["delivery_datetime"] = parse_iso_datetime(require_non_empty(row, "delivery_datetime"))
    normalized["equipment_type"] = require_non_empty(row, "equipment_type")
    normalized["loadboard_rate"] = parse_decimal(row.get("loadboard_rate"), "loadboard_rate", required=True)

    if normalized["delivery_datetime"] < normalized["pickup_datetime"]:
        raise ValueError("delivery_datetime must be >= pickup_datetime")

    normalized["notes"] = (row.get("notes") or "").strip() or None
    normalized["weight"] = parse_decimal(row.get("weight"), "weight")
    normalized["commodity_type"] = (row.get("commodity_type") or "").strip() or None
    normalized["num_of_pieces"] = parse_int(row.get("num_of_pieces"), "num_of_pieces")
    normalized["miles"] = parse_decimal(row.get("miles"), "miles")
    normalized["dimensions"] = (row.get("dimensions") or "").strip() or None

    return normalized


def get_anchor_offset_hours() -> int:
    raw_value = os.getenv("LOADS_ANCHOR_OFFSET_HOURS", "24").strip()
    try:
        return int(raw_value)
    except ValueError:
        raise ValueError("LOADS_ANCHOR_OFFSET_HOURS must be a valid integer")


def shift_load_datetimes(rows: list[dict], anchor_offset_hours: int) -> list[dict]:
    if not rows:
        return rows

    earliest_pickup = min(row["pickup_datetime"] for row in rows)
    target_anchor = datetime.now(timezone.utc) + timedelta(hours=anchor_offset_hours)
    delta = target_anchor - earliest_pickup

    shifted_rows = []
    for row in rows:
        shifted = dict(row)
        shifted["pickup_datetime"] = row["pickup_datetime"] + delta
        shifted["delivery_datetime"] = row["delivery_datetime"] + delta
        shifted_rows.append(shifted)

    return shifted_rows


def upsert_loads(conn, rows):
    sql = """
    INSERT INTO loads (
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
    ) VALUES (
        %(load_id)s,
        %(origin)s,
        %(destination)s,
        %(pickup_datetime)s,
        %(delivery_datetime)s,
        %(equipment_type)s,
        %(loadboard_rate)s,
        %(notes)s,
        %(weight)s,
        %(commodity_type)s,
        %(num_of_pieces)s,
        %(miles)s,
        %(dimensions)s
    )
    ON CONFLICT (load_id) DO UPDATE SET
        origin = EXCLUDED.origin,
        destination = EXCLUDED.destination,
        pickup_datetime = EXCLUDED.pickup_datetime,
        delivery_datetime = EXCLUDED.delivery_datetime,
        equipment_type = EXCLUDED.equipment_type,
        loadboard_rate = EXCLUDED.loadboard_rate,
        notes = EXCLUDED.notes,
        weight = EXCLUDED.weight,
        commodity_type = EXCLUDED.commodity_type,
        num_of_pieces = EXCLUDED.num_of_pieces,
        miles = EXCLUDED.miles,
        dimensions = EXCLUDED.dimensions
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)


def reset_sequence(conn):
    sql = "SELECT setval('loads_load_id_seq', (SELECT COALESCE(MAX(load_id), 1) FROM loads))"
    with conn.cursor() as cur:
        cur.execute(sql)


def main():
    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    csv_path = os.getenv("LOADS_CSV_PATH", "data/loads.csv")

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

    shifted_rows = shift_load_datetimes(parsed_rows, anchor_offset_hours)

    try:
        with psycopg.connect(db_url) as conn:
            with conn.transaction():
                upsert_loads(conn, shifted_rows)
                reset_sequence(conn)
        print(
            f"Successfully imported {len(shifted_rows)} load(s) from {csv_path} "
            # f"with pickup times shifted by anchor offset {anchor_offset_hours} hour(s)."
        )
    except Exception as e:
        print(f"ERROR: Database import failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()