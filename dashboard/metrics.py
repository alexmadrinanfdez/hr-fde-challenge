import pandas as pd


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(100.0 * numerator / denominator, 2)


def compute(calls: pd.DataFrame, loads: pd.DataFrame) -> dict:
    total = len(calls)

    matched = calls[calls["matched_load_id"].notna()].merge(
        loads, left_on="matched_load_id", right_on="load_id", how="inner"
    )
    transferred = matched[matched["final_outcome"] == "transferred_after_agreement"]

    calls = calls.copy()
    calls["duration_seconds"] = (
        calls["call_ended_at"] - calls["call_started_at"]
    ).dt.total_seconds()

    core = {
        "total_saved_calls": total,
        "authorized_carrier_rate": _rate(calls["carrier_authorized"].sum(), total),
        "load_match_rate": _rate(calls["matched_load_id"].notna().sum(), total),
        "transfer_rate": _rate(
            (calls["final_outcome"] == "transferred_after_agreement").sum(), total
        ),
        "no_match_rate": _rate(
            (calls["final_outcome"] == "no_matching_load").sum(), total
        ),
        "not_authorized_rate": _rate(
            (calls["final_outcome"] == "carrier_not_verified").sum(), total
        ),
        "caller_not_interested_rate": _rate(
            (calls["final_outcome"] == "caller_not_interested").sum(), total
        ),
        "incomplete_call_rate": _rate(
            (calls["final_outcome"] == "incomplete_call").sum(), total
        ),
    }

    negotiation_outcomes = calls[
        calls["final_outcome"].isin(["transferred_after_agreement", "negotiation_failed"])
    ]
    negotiation_total = len(negotiation_outcomes)

    negotiation = {
        "negotiation_success_rate": _rate(
            (negotiation_outcomes["final_outcome"] == "transferred_after_agreement").sum(),
            negotiation_total,
        ),
        "negotiation_failed_rate": _rate(
            (negotiation_outcomes["final_outcome"] == "negotiation_failed").sum(),
            negotiation_total,
        ),
        "average_agreed_rate": round(calls["agreed_rate"].dropna().mean(), 2)
        if calls["agreed_rate"].notna().any()
        else 0.0,
        "average_negotiation_turns": round(calls["negotiation_turns"].dropna().mean(), 2)
        if calls["negotiation_turns"].notna().any()
        else 0.0,
    }

    sentiment_distribution = (
        calls.groupby("sentiment").size().reset_index(name="count")
    )

    # Stacked: positive + neutral + negative, with zero-fill
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
                lambda x: (x == "transferred_after_agreement").sum(),
            ),
        )
        .reset_index()
    )
    facility_transfer["transfer_rate"] = facility_transfer.apply(
        lambda row: _rate(row["transferred_calls"], row["total_matched_calls"]), axis=1
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