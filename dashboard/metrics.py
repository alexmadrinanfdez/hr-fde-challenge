import pandas as pd


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def compute(calls: pd.DataFrame, loads: pd.DataFrame) -> dict:
    total = len(calls)

    matched = calls[calls["matched_load_id"].notna()].merge(
        loads, left_on="matched_load_id", right_on="load_id", how="inner"
    )
    transferred = matched[matched["final_outcome"] == "booked"]

    calls = calls.copy()
    calls["duration_seconds"] = (
        calls["call_ended_at"] - calls["call_started_at"]
    ).dt.total_seconds()

    core = {
        "total_saved_calls": total,
        "authorized_carrier_rate": _rate(int(calls["carrier_authorized"].sum()), total),
        "load_match_rate": _rate(int(calls["matched_load_id"].notna().sum()), total),
        "transfer_rate": _rate(
            int((calls["final_outcome"] == "booked").sum()), total
        ),
        "no_match_rate": _rate(
            int((calls["final_outcome"] == "no_match").sum()), total
        ),
        "not_authorized_rate": _rate(
            int((calls["final_outcome"] == "not_verified").sum()), total
        ),
        "caller_not_interested_rate": _rate(
            int((calls["final_outcome"] == "not_interested").sum()), total
        ),
        "incomplete_call_rate": _rate(
            int((calls["final_outcome"] == "incomplete").sum()), total
        ),
    }

    stages = ["Total Calls", "Authorized", "Load Matched", "Booked"]
    funnel = pd.DataFrame(
        {
            "count": [
                total,
                int(calls["carrier_authorized"].sum()),
                int(calls["matched_load_id"].notna().sum()),
                int((calls["final_outcome"] == "booked").sum()),
            ],
        },
        index=pd.CategoricalIndex(stages, categories=stages, ordered=True),
    )

    negotiation_outcomes = calls[
        calls["final_outcome"].isin(["booked", "no_agreement"])
    ]
    negotiation_total = len(negotiation_outcomes)

    average_agreed_rate = (
        round(calls["agreed_rate"].dropna().mean(), 2)
        if calls["agreed_rate"].notna().any()
        else 0.0
    )

    average_loadboard_rate = (
        matched["loadboard_rate"].dropna().mean()
        if "loadboard_rate" in matched.columns and matched["loadboard_rate"].notna().any()
        else 0.0
    )

    agreed_delta_pct = 100 * _rate(average_agreed_rate - average_loadboard_rate, average_loadboard_rate)

    negotiation = {
        "negotiation_success_rate": _rate(
            int((negotiation_outcomes["final_outcome"] == "booked").sum()),
            negotiation_total,
        ),
        "negotiation_failed_rate": _rate(
            int((negotiation_outcomes["final_outcome"] == "no_agreement").sum()),
            negotiation_total,
        ),
        "average_agreed_rate": average_agreed_rate,
        "agreed_delta_pct": agreed_delta_pct,
        "average_negotiation_turns": round(calls["negotiation_turns"].dropna().mean(), 2)
        if calls["negotiation_turns"].notna().any()
        else 0.0,
    }

    sentiment_distribution = (
        calls.groupby("sentiment").size().reset_index(name="count")
    )

    sentiment_by_outcome = (
        calls[calls["sentiment"].isin(["positive", "neutral", "negative"])]
        .groupby(["final_outcome", "sentiment"])
        .size()
        .reset_index(name="count")
        .pivot_table(index="final_outcome", columns="sentiment", values="count", fill_value=0)
    )
    for col in ["positive", "neutral", "negative"]:
        if col not in sentiment_by_outcome.columns:
            sentiment_by_outcome[col] = 0
    sentiment_by_outcome = sentiment_by_outcome.rename(
        columns={"positive": "Positive", "neutral": "Neutral", "negative": "Negative"}
    )[["Positive", "Neutral", "Negative"]]

    def facility_grouped(key):
        total_counts = matched.groupby(key).size().reset_index(name="Total Calls")
        success_counts = transferred.groupby(key).size().reset_index(name="Successful Calls")
        merged = total_counts.merge(success_counts, on=key, how="outer").fillna(0)
        return merged.set_index(key)

    origin_usage = facility_grouped("origin")
    destination_usage = facility_grouped("destination")

    facility_transfer = (
        matched.groupby(["origin", "destination"])
        .agg(
            total_matched_calls=("call_id", "count"),
            transferred_calls=(
                "final_outcome",
                lambda x: (x == "booked").sum(),
            ),
        )
        .reset_index()
    )
    facility_transfer["transfer_rate"] = facility_transfer.apply(
        lambda row: _rate(int(row["transferred_calls"]), int(row["total_matched_calls"])), axis=1
    )
    facility_transfer = facility_transfer.sort_values(
        by=["transfer_rate", "total_matched_calls"],
        ascending=[False, False],
    )

    def facility_by_hour(key):
        df = transferred.copy()
        df["hour_of_day"] = df["call_started_at"].dt.hour
        pivot = df.pivot_table(
            index=key, columns="hour_of_day", values="call_id", aggfunc="count", fill_value=0
        )
        pivot = pivot.reindex(columns=range(24), fill_value=0)
        pivot = pivot.map(lambda v: v > 0)
        return pivot

    origin_by_hour = facility_by_hour("origin")
    destination_by_hour = facility_by_hour("destination")

    calls_per_hour = calls.groupby(calls["call_started_at"].dt.hour).size()
    calls_per_hour = calls_per_hour.reindex(range(24), fill_value=0)
    calls_per_hour.index.name = "hour_of_day"
    calls_per_hour = calls_per_hour.to_frame(name="call_count")

    duration_by_outcome = (
        calls.groupby("final_outcome")["duration_seconds"]
        .mean()
        .round(2)
        .to_frame(name="average_call_duration_seconds")
    )

    recent_calls = calls.drop(columns=["duration_seconds"]).head(100)

    return {
        "core": core,
        "funnel": funnel,
        "negotiation": negotiation,
        "sentiment_distribution": sentiment_distribution,
        "sentiment_by_outcome": sentiment_by_outcome,
        "origin_usage": origin_usage,
        "destination_usage": destination_usage,
        "facility_transfer": facility_transfer,
        "origin_by_hour": origin_by_hour,
        "destination_by_hour": destination_by_hour,
        "calls_per_hour": calls_per_hour,
        "duration_by_outcome": duration_by_outcome,
        "recent_calls": recent_calls,
    }