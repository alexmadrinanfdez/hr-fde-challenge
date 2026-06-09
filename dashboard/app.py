import pandas as pd
import streamlit as st

from dashboard.queries import get_calls, get_loads
from dashboard.metrics import compute


TEAL = "#2A9D8F"
NAVY = "#16324F"
SLATE = "#8B9DAF"

st.set_page_config(page_title="Inbound Carrier Sales Dashboard", layout="wide")
st.title("Inbound Carrier Sales Dashboard")

OUTCOME_SHORT = {
    "Transferred After Agreement": "Transferred",
    "Negotiation Failed": "Neg. Failed",
    "No Matching Load": "No Match",
    "Carrier Not Verified": "Not Verified",
    "Caller Not Interested": "Not Interested",
    "Incomplete Call": "Incomplete",
}


def titleize(value):
    if value is None:
        return "Unknown"
    if not isinstance(value, str):
        return value
    return value.replace("_", " ").strip().title() or "Unknown"


def prettify(df, index=False, columns=False, values=None):
    df = df.copy()
    if index:
        df.index = [titleize(v) for v in df.index]
    if columns:
        df.columns = [str(c).replace("_", " ").strip().title() for c in df.columns]
    if values:
        for col in values:
            if col in df.columns:
                df[col] = df[col].map(titleize)
    return df


def shorten_index(df):
    df = df.copy()
    df.index = [OUTCOME_SHORT.get(v, v) for v in df.index]
    return df


def format_percent(v):
    return f"{v:.2f}%"


def format_currency(v):
    return f"${v:,.2f}"


def format_number(v):
    return f"{v:,.2f}"


def format_integer(v):
    return f"{int(v):,}"


@st.cache_data(ttl=60)
def load_data():
    calls = pd.DataFrame(get_calls())
    loads = pd.DataFrame(get_loads())
    calls["call_started_at"] = pd.to_datetime(calls["call_started_at"])
    calls["call_ended_at"] = pd.to_datetime(calls["call_ended_at"])
    calls["carrier_authorized"] = calls["carrier_authorized"].astype(bool)
    calls["agreed_rate"] = pd.to_numeric(calls["agreed_rate"], errors="coerce")
    calls["negotiation_turns"] = pd.to_numeric(calls["negotiation_turns"], errors="coerce")
    return calls, loads


calls, loads = load_data()
m = compute(calls, loads)

# KPI rows
st.header("Core Funnel Metrics")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Saved Calls", format_integer(m["core"]["total_saved_calls"]))
c2.metric("Authorized Carrier Rate", format_percent(m["core"]["authorized_carrier_rate"]))
c3.metric("Load Match Rate", format_percent(m["core"]["load_match_rate"]))
c4.metric("Transfer Rate", format_percent(m["core"]["transfer_rate"]))

c5, c6, c7, c8 = st.columns(4)
c5.metric("No Match Rate", format_percent(m["core"]["no_match_rate"]))
c6.metric("Not Authorized Rate", format_percent(m["core"]["not_authorized_rate"]))
c7.metric("Caller Not Interested Rate", format_percent(m["core"]["caller_not_interested_rate"]))
c8.metric("Incomplete Call Rate", format_percent(m["core"]["incomplete_call_rate"]))

st.header("Negotiation Metrics")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Negotiation Success Rate", format_percent(m["negotiation"]["negotiation_success_rate"]))
c2.metric("Negotiation Failed Rate", format_percent(m["negotiation"]["negotiation_failed_rate"]))
c3.metric("Average Agreed Rate", format_currency(m["negotiation"]["average_agreed_rate"]))
c4.metric("Average Negotiation Turns", format_number(m["negotiation"]["average_negotiation_turns"]))

# Sentiment charts
st.header("Sentiment")
left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    df = m["sentiment_distribution"].copy()
    df["sentiment"] = df["sentiment"].map(titleize)
    st.bar_chart(df.set_index("sentiment")[["count"]], color=TEAL)

with right:
    st.subheader("Sentiment By Outcome")
    df = shorten_index(prettify(m["sentiment_by_outcome"], index=True))
    st.bar_chart(df, color=[TEAL, SLATE, NAVY], stack="normalize")

# Facility charts and tables
st.header("Freight Facility Usage")
left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage")
    st.bar_chart(prettify(m["origin_usage"], index=True), color=[NAVY, TEAL], stack=False)

with right:
    st.subheader("Destination Facility Usage")
    st.bar_chart(prettify(m["destination_usage"], index=True), color=[NAVY, TEAL], stack=False)

st.subheader("Facility Transfer Rate")
st.dataframe(
    prettify(m["facility_transfer"], columns=True, values=["origin", "destination"]),
    use_container_width=True,
)

left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage By Hour")
    st.dataframe(prettify(m["origin_by_hour"], index=True), use_container_width=True)

with right:
    st.subheader("Destination Facility Usage By Hour")
    st.dataframe(prettify(m["destination_by_hour"], index=True), use_container_width=True)

# Operational charts
st.header("Operational Call Metrics")
left, right = st.columns(2)

with left:
    st.subheader("Calls Per Hour")
    st.bar_chart(m["calls_per_hour"], color=TEAL)

with right:
    st.subheader("Average Call Duration By Outcome")
    df = shorten_index(prettify(m["duration_by_outcome"], index=True))
    st.bar_chart(df, color=TEAL)

# Drill-down table
st.header("Recent Calls")
st.dataframe(
    prettify(m["recent_calls"], columns=True, values=["final_outcome", "sentiment"]),
    use_container_width=True,
)