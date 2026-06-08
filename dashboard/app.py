import pandas as pd
import streamlit as st

from dashboard.queries import (
    get_average_call_duration_by_outcome,
    get_calls_by_hour,
    get_core_funnel_metrics,
    get_facility_transfer_rate,
    get_negative_sentiment_by_outcome,
    get_negative_sentiment_rate,
    get_negotiation_metrics,
    get_operational_metrics,
    get_origin_facility_usage_by_hour,
    get_qa_metrics,
    get_recent_calls,
    get_sentiment_distribution,
    get_successful_destination_facility_usage,
    get_successful_origin_facility_usage,
    get_top_destination_facilities,
    get_top_origin_facilities,
    get_destination_facility_usage_by_hour,
)


st.set_page_config(
    page_title="Inbound Carrier Sales Dashboard",
    layout="wide",
)

st.title("Inbound Carrier Sales Dashboard")
st.caption("Phase 3 reporting dashboard powered by PostgreSQL")


def as_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def metric_value(data: dict, key: str, default="0"):
    value = data.get(key)
    if value is None:
        return default
    return value


# Load all dashboard data
core = get_core_funnel_metrics()
negotiation = get_negotiation_metrics()
negative_sentiment = get_negative_sentiment_rate()
qa = get_qa_metrics()
operational = get_operational_metrics()

sentiment_distribution_df = as_dataframe(get_sentiment_distribution())
negative_sentiment_by_outcome_df = as_dataframe(get_negative_sentiment_by_outcome())

successful_origin_df = as_dataframe(get_successful_origin_facility_usage())
successful_destination_df = as_dataframe(get_successful_destination_facility_usage())
origin_by_hour_df = as_dataframe(get_origin_facility_usage_by_hour())
destination_by_hour_df = as_dataframe(get_destination_facility_usage_by_hour())
top_origins_df = as_dataframe(get_top_origin_facilities())
top_destinations_df = as_dataframe(get_top_destination_facilities())
facility_transfer_df = as_dataframe(get_facility_transfer_rate())

duration_by_outcome_df = as_dataframe(get_average_call_duration_by_outcome())
calls_by_hour_df = as_dataframe(get_calls_by_hour())
recent_calls_df = as_dataframe(get_recent_calls())


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

col1, col2, col3 = st.columns(3)
col1.metric("Negative Sentiment Rate", f"{metric_value(negative_sentiment, 'negative_sentiment_rate', 0)}%")
col2.metric("Missing Transcript Rate", f"{metric_value(qa, 'missing_transcript_rate', 0)}%")
col3.metric("Missing Key Fields Rate", f"{metric_value(qa, 'missing_key_fields_rate', 0)}%")

left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    if not sentiment_distribution_df.empty:
        chart_df = sentiment_distribution_df.set_index("sentiment")[["count"]]
        st.bar_chart(chart_df)
        st.dataframe(sentiment_distribution_df, use_container_width=True)
    else:
        st.info("No sentiment data available.")

with right:
    st.subheader("Negative Sentiment by Outcome")
    if not negative_sentiment_by_outcome_df.empty:
        chart_df = negative_sentiment_by_outcome_df.set_index("final_outcome")[["negative_rate"]]
        st.bar_chart(chart_df)
        st.dataframe(negative_sentiment_by_outcome_df, use_container_width=True)
    else:
        st.info("No negative sentiment by outcome data available.")


# Section 4: Freight facility usage
st.header("Freight Facility Usage")

left, right = st.columns(2)

with left:
    st.subheader("Successful Origin Facility Usage")
    if not successful_origin_df.empty:
        chart_df = successful_origin_df.set_index("origin")[["successful_call_count"]]
        st.bar_chart(chart_df)
        st.dataframe(successful_origin_df, use_container_width=True)
    else:
        st.info("No successful origin facility data available.")

with right:
    st.subheader("Successful Destination Facility Usage")
    if not successful_destination_df.empty:
        chart_df = successful_destination_df.set_index("destination")[["successful_call_count"]]
        st.bar_chart(chart_df)
        st.dataframe(successful_destination_df, use_container_width=True)
    else:
        st.info("No successful destination facility data available.")

left, right = st.columns(2)

with left:
    st.subheader("Top Origin Facilities")
    if not top_origins_df.empty:
        chart_df = top_origins_df.set_index("origin")[["call_count"]]
        st.bar_chart(chart_df)
        st.dataframe(top_origins_df, use_container_width=True)
    else:
        st.info("No top origin facility data available.")

with right:
    st.subheader("Top Destination Facilities")
    if not top_destinations_df.empty:
        chart_df = top_destinations_df.set_index("destination")[["call_count"]]
        st.bar_chart(chart_df)
        st.dataframe(top_destinations_df, use_container_width=True)
    else:
        st.info("No top destination facility data available.")

st.subheader("Facility Transfer Rate")
if not facility_transfer_df.empty:
    st.dataframe(facility_transfer_df, use_container_width=True)
else:
    st.info("No facility transfer rate data available.")

left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage by Hour")
    if not origin_by_hour_df.empty:
        st.dataframe(origin_by_hour_df, use_container_width=True)
    else:
        st.info("No origin facility usage-by-hour data available.")

with right:
    st.subheader("Destination Facility Usage by Hour")
    if not destination_by_hour_df.empty:
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
        chart_df = calls_by_hour_df.set_index("hour_of_day")[["call_count"]]
        st.bar_chart(chart_df)
    else:
        st.info("No calls-by-hour data available.")

st.subheader("Average Call Duration by Outcome")
if not duration_by_outcome_df.empty:
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