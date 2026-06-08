import pandas as pd
import streamlit as st

import dashboard.queries as queries


st.set_page_config(
    page_title="Inbound Carrier Sales Dashboard",
    layout="wide",
)

st.title("Inbound Carrier Sales Dashboard")


def dict_as_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def metric_value(data: dict, key: str, default="0"):
    value = data.get(key)
    if value is None:
        return default
    return value


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def build_total_origin_facility_usage() -> pd.DataFrame:
    df = dict_as_dataframe(queries.get_top_origin_facilities(limit=1000))
    if df.empty:
        return df
    return df.rename(columns={"call_count": "total_call_count"})


def build_total_destination_facility_usage() -> pd.DataFrame:
    df = dict_as_dataframe(queries.get_top_destination_facilities(limit=1000))
    if df.empty:
        return df
    return df.rename(columns={"call_count": "total_call_count"})


def build_combined_origin_usage() -> pd.DataFrame:
    total_df = build_total_origin_facility_usage()
    success_df = dict_as_dataframe(queries.get_successful_origin_facility_usage())

    if success_df.empty and total_df.empty:
        return pd.DataFrame()

    if success_df.empty:
        merged = total_df.copy()
        merged["successful_call_count"] = 0
    elif total_df.empty:
        merged = success_df.copy()
        merged["total_call_count"] = merged["successful_call_count"]
    else:
        merged = total_df.merge(success_df, on="origin", how="outer")

    merged["total_call_count"] = pd.to_numeric(merged["total_call_count"], errors="coerce").fillna(0)
    merged["successful_call_count"] = pd.to_numeric(
        merged["successful_call_count"], errors="coerce"
    ).fillna(0)

    merged = merged.sort_values(
        by=["total_call_count", "successful_call_count", "origin"],
        ascending=[False, False, True],
    )

    return merged


def build_combined_destination_usage() -> pd.DataFrame:
    total_df = build_total_destination_facility_usage()
    success_df = dict_as_dataframe(queries.get_successful_destination_facility_usage())

    if success_df.empty and total_df.empty:
        return pd.DataFrame()

    if success_df.empty:
        merged = total_df.copy()
        merged["successful_call_count"] = 0
    elif total_df.empty:
        merged = success_df.copy()
        merged["total_call_count"] = merged["successful_call_count"]
    else:
        merged = total_df.merge(success_df, on="destination", how="outer")

    merged["total_call_count"] = pd.to_numeric(merged["total_call_count"], errors="coerce").fillna(0)
    merged["successful_call_count"] = pd.to_numeric(
        merged["successful_call_count"], errors="coerce"
    ).fillna(0)

    merged = merged.sort_values(
        by=["total_call_count", "successful_call_count", "destination"],
        ascending=[False, False, True],
    )

    return merged


# Load all dashboard data
core = queries.get_core_funnel_metrics()
negotiation = queries.get_negotiation_metrics()
operational = queries.get_operational_metrics()

sentiment_distribution_df = dict_as_dataframe(queries.get_sentiment_distribution())
negative_sentiment_by_outcome_df = dict_as_dataframe(queries.get_negative_sentiment_by_outcome())

combined_origin_usage_df = build_combined_origin_usage()
combined_destination_usage_df = build_combined_destination_usage()
origin_by_hour_df = dict_as_dataframe(queries.get_origin_facility_usage_by_hour())
destination_by_hour_df = dict_as_dataframe(queries.get_destination_facility_usage_by_hour())
facility_transfer_df = dict_as_dataframe(queries.get_facility_transfer_rate())

duration_by_outcome_df = dict_as_dataframe(queries.get_average_call_duration_by_outcome())
calls_by_hour_df = dict_as_dataframe(queries.get_calls_by_hour())
recent_calls_df = dict_as_dataframe(queries.get_recent_calls())


# Section 1: Core funnel metrics
st.header("Core Funnel Metrics")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Saved Calls", metric_value(core, "total_saved_calls", 0))
col2.metric("Authorized Carrier Rate", f"{metric_value(core, 'authorized_carrier_rate', 0)}%")
col3.metric("Load Match Rate", f"{metric_value(core, 'load_match_rate', 0)}%")
col4.metric("Transfer Rate", f"{metric_value(core, 'transfer_rate', 0)}%")

col5, col6, col7, col8 = st.columns(4)
col5.metric("No Match Rate", f"{metric_value(core, 'no_match_rate', 0)}%")
col6.metric("Not Authorized Rate", f"{metric_value(core, 'not_authorized_rate', 0)}%")
col7.metric("Caller Not Interested Rate", f"{metric_value(core, 'caller_not_interested_rate', 0)}%")
col8.metric("Incomplete Call Rate", f"{metric_value(core, 'incomplete_call_rate', 0)}%")


# Section 2: Negotiation metrics
st.header("Negotiation Metrics")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Negotiation Success Rate", f"{metric_value(negotiation, 'negotiation_success_rate', 0)}%")
col2.metric("Negotiation Failed Rate", f"{metric_value(negotiation, 'negotiation_failed_rate', 0)}%")
col3.metric("Average Agreed Rate", metric_value(negotiation, "average_agreed_rate", 0))
col4.metric("Average Negotiation Turns", metric_value(negotiation, "average_negotiation_turns", 0))


# Section 3: Sentiment and QA
st.header("Sentiment and QA")

left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    if not sentiment_distribution_df.empty:
        sentiment_distribution_df = coerce_numeric(sentiment_distribution_df, ["count", "percentage"])
        chart_df = sentiment_distribution_df.set_index("sentiment")[["count"]]
        st.bar_chart(chart_df)
        st.dataframe(sentiment_distribution_df, use_container_width=True)
    else:
        st.info("No sentiment data available.")

with right:
    st.subheader("Negative Sentiment by Outcome")
    if not negative_sentiment_by_outcome_df.empty:
        negative_sentiment_by_outcome_df = coerce_numeric(
            negative_sentiment_by_outcome_df,
            ["negative_count", "total_count", "negative_rate"],
        )
        chart_df = negative_sentiment_by_outcome_df.set_index("final_outcome")[["negative_rate"]]
        st.bar_chart(chart_df)
        st.dataframe(negative_sentiment_by_outcome_df, use_container_width=True)
    else:
        st.info("No negative sentiment by outcome data available.")


# Section 4: Freight facility usage
st.header("Freight Facility Usage")

left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage: Total vs Successful")
    if not combined_origin_usage_df.empty:
        chart_df = combined_origin_usage_df.set_index("origin")[
            ["total_call_count", "successful_call_count"]
        ]
        st.bar_chart(chart_df)
    else:
        st.info("No origin facility usage data available.")

with right:
    st.subheader("Destination Facility Usage: Total vs Successful")
    if not combined_destination_usage_df.empty:
        chart_df = combined_destination_usage_df.set_index("destination")[
            ["total_call_count", "successful_call_count"]
        ]
        st.bar_chart(chart_df)
    else:
        st.info("No destination facility usage data available.")

st.subheader("Facility Transfer Rate")
if not facility_transfer_df.empty:
    facility_transfer_df = coerce_numeric(
        facility_transfer_df,
        ["total_matched_calls", "transferred_calls", "transfer_rate"],
    )
    st.dataframe(facility_transfer_df, use_container_width=True)
else:
    st.info("No facility transfer rate data available.")

left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage by Hour")
    if not origin_by_hour_df.empty:
        origin_by_hour_df = coerce_numeric(origin_by_hour_df, ["hour_of_day", "call_count"])
        st.dataframe(origin_by_hour_df, use_container_width=True)
    else:
        st.info("No origin facility usage-by-hour data available.")

with right:
    st.subheader("Destination Facility Usage by Hour")
    if not destination_by_hour_df.empty:
        destination_by_hour_df = coerce_numeric(destination_by_hour_df, ["hour_of_day", "call_count"])
        st.dataframe(destination_by_hour_df, use_container_width=True)
    else:
        st.info("No destination facility usage-by-hour data available.")


# Section 5: Operational call metrics
st.header("Operational Call Metrics")

col1, col2 = st.columns(2)
col1.metric(
    "Average Call Duration (Seconds)",
    metric_value(operational, "average_call_duration_seconds", 0),
)

with col2:
    st.subheader("Calls by Hour")
    if not calls_by_hour_df.empty:
        calls_by_hour_df = coerce_numeric(calls_by_hour_df, ["hour_of_day", "call_count"])
        chart_df = calls_by_hour_df.set_index("hour_of_day")[["call_count"]]
        st.bar_chart(chart_df)
    else:
        st.info("No calls-by-hour data available.")

st.subheader("Average Call Duration by Outcome")
if not duration_by_outcome_df.empty:
    duration_by_outcome_df = coerce_numeric(duration_by_outcome_df, ["average_call_duration_seconds"])
    chart_df = duration_by_outcome_df.set_index("final_outcome")[["average_call_duration_seconds"]]
    st.bar_chart(chart_df)
    st.dataframe(duration_by_outcome_df, use_container_width=True)
else:
    st.info("No call duration by outcome data available.")


# Section 6: Drill-down table
st.header("Recent Calls")

if not recent_calls_df.empty:
    st.dataframe(recent_calls_df, use_container_width=True)
else:
    st.info("No recent call data available.")