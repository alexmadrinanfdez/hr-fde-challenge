import pandas as pd


LABELS = {
    "booked": "Booked",
    "no_agreement": "No Agmt.",
    "no_match": "No Match",
    "not_verified": "Not Verif.",
    "not_interested": "Not Int.",
    "incomplete": "Incomplete",
    "positive": "Positive",
    "neutral": "Neutral",
    "negative": "Negative",
}


def label(value):
    if not isinstance(value, str):
        return value or "Unknown"
    return LABELS.get(value, value.replace("_", " ").title())


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _outcome_count(df: pd.DataFrame, outcome: str) -> int:
    return int((df["final_outcome"] == outcome).sum())


def compute(calls: pd.DataFrame, loads: pd.DataFrame) -> dict:
    total = len(calls)

    calls = calls.copy()
    calls["duration_seconds"] = (
        calls["call_ended_at"] - calls["call_started_at"]
    ).dt.total_seconds()

    matched = calls[calls["matched_load_id"].notna()].merge(
        loads, left_on="matched_load_id", right_on="load_id", how="inner"
    )
    booked = matched[matched["final_outcome"] == "booked"]

    authorized_count = int(calls["carrier_authorized"].sum())
    matched_count = int(calls["matched_load_id"].notna().sum())
    booked_count = _outcome_count(calls, "booked")

    # Core
    core = {
        "total_saved_calls": total,
        "authorized_carrier_rate": _rate(authorized_count, total),
        "load_match_rate": _rate(matched_count, total),
        "transfer_rate": _rate(booked_count, total),
        "no_match_rate": _rate(_outcome_count(calls, "no_match"), total),
        "not_authorized_rate": _rate(_outcome_count(calls, "not_verified"), total),
        "not_interested_rate": _rate(_outcome_count(calls, "not_interested"), total),
        "incomplete_rate": _rate(_outcome_count(calls, "incomplete"), total),
    }

    # Funnel
    stages = ["Total Calls", "Authorized", "Load Matched", "Booked"]
    funnel = pd.DataFrame(
        {"count": [total, authorized_count, matched_count, booked_count]},
        index=pd.CategoricalIndex(stages, categories=stages, ordered=True),
    )

    # Negotiation
    neg = calls[calls["final_outcome"].isin(["booked", "no_agreement"])]
    neg_total = len(neg)

    avg_agreed = (
        round(calls["agreed_rate"].dropna().mean(), 2)
        if calls["agreed_rate"].notna().any()
        else 0.0
    )
    avg_loadboard = (
        round(matched["loadboard_rate"].dropna().mean(), 2)
        if "loadboard_rate" in matched.columns and matched["loadboard_rate"].notna().any()
        else None
    )

    negotiation = {
        "negotiation_success_rate": _rate(_outcome_count(neg, "booked"), neg_total),
        "negotiation_failed_rate": _rate(_outcome_count(neg, "no_agreement"), neg_total),
        "average_agreed_rate": avg_agreed,
        "agreed_delta_pct": _rate(avg_agreed - avg_loadboard, avg_loadboard) * 100,
        "average_negotiation_turns": (
            round(calls["negotiation_turns"].dropna().mean(), 2)
            if calls["negotiation_turns"].notna().any()
            else 0.0
        ),
    }

    # Sentiment
    sentiment_dist = calls.groupby("sentiment").size().reset_index(name="count")
    sentiment_dist["sentiment"] = sentiment_dist["sentiment"].map(label)

    sentiment_by_outcome = (
        calls.groupby(["final_outcome", "sentiment"]).size()
        .reset_index(name="count")
        .pivot_table(index="final_outcome", columns="sentiment", values="count", fill_value=0)
    )
    for col in ["positive", "neutral", "negative"]:
        if col not in sentiment_by_outcome.columns:
            sentiment_by_outcome[col] = 0
    sentiment_by_outcome = sentiment_by_outcome[["positive", "neutral", "negative"]]
    sentiment_by_outcome.columns = ["Positive", "Neutral", "Negative"]
    sentiment_by_outcome.index = sentiment_by_outcome.index.map(label)

    # Facility usage
    def facility_grouped(key):
        totals = matched.groupby(key).size().reset_index(name="Total Calls")
        successes = booked.groupby(key).size().reset_index(name="Successful Calls")
        return totals.merge(successes, on=key, how="outer").fillna(0).set_index(key)

    # Facility transfer
    ft = (
        matched.groupby(["origin", "destination"])
        .agg(
            total_matched_calls=("call_id", "count"),
            booked_calls=("final_outcome", lambda x: (x == "booked").sum()),
        )
        .reset_index()
    )
    ft["transfer_rate"] = ft.apply(
        lambda r: _rate(int(r["booked_calls"]), int(r["total_matched_calls"])), axis=1
    )
    ft = ft.sort_values(["transfer_rate", "total_matched_calls"], ascending=[False, False])

    # Facility by hour
    def facility_by_hour(key):
        df = booked.copy()
        df["hour_of_day"] = df["call_started_at"].dt.hour
        pivot = df.pivot_table(
            index=key, columns="hour_of_day", values="call_id", aggfunc="count", fill_value=0
        )
        return pivot.reindex(columns=range(24), fill_value=0).map(lambda v: v > 0)

    # Calls per hour
    calls_per_hour = calls.groupby(calls["call_started_at"].dt.hour).size()
    calls_per_hour = calls_per_hour.reindex(range(24), fill_value=0)
    calls_per_hour.index.name = "hour_of_day"
    calls_per_hour = calls_per_hour.to_frame(name="call_count")

    # Duration by outcome
    duration_by_outcome = (
        calls.groupby("final_outcome")["duration_seconds"]
        .mean().round(2)
        .to_frame(name="average_call_duration_seconds")
    )
    duration_by_outcome.index = duration_by_outcome.index.map(label)

    return {
        "core": core,
        "funnel": funnel,
        "negotiation": negotiation,
        "sentiment_distribution": sentiment_dist,
        "sentiment_by_outcome": sentiment_by_outcome,
        "origin_usage": facility_grouped("origin"),
        "destination_usage": facility_grouped("destination"),
        "facility_transfer": ft,
        "origin_by_hour": facility_by_hour("origin"),
        "destination_by_hour": facility_by_hour("destination"),
        "calls_per_hour": calls_per_hour,
        "duration_by_outcome": duration_by_outcome,
        "recent_calls": calls.drop(columns=["duration_seconds"]).head(100),
    }