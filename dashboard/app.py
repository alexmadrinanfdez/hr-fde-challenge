from dotenv import load_dotenv

load_dotenv()

import pandas as pd
import streamlit as st

from dashboard.queries import get_calls, get_loads
from dashboard.metrics import compute, label


TEAL = "#2A9D8F"
NAVY = "#16324F"
SLATE = "#8B9DAF"

st.set_page_config(page_title="Inbound Carrier Sales Dashboard", layout="wide")
st.title("Inbound Carrier Sales Dashboard")
st.caption("Operational analytics for inbound carrier call performance and freight matching.")


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


calls_raw, loads = load_data()

# Date range filter
st.sidebar.header("Filters")
min_date = calls_raw["call_started_at"].min().date()
max_date = calls_raw["call_started_at"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if len(date_range) == 2:
    start, end = date_range
    calls = calls_raw[
        (calls_raw["call_started_at"].dt.date >= start)
        & (calls_raw["call_started_at"].dt.date <= end)
    ]
else:
    calls = calls_raw

m = compute(calls, loads)

# Core funnel
st.header("Core Funnel Metrics")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Saved Calls", m["core"]["total_saved_calls"], format="localized")
c2.metric("Authorized Carrier Rate", m["core"]["authorized_carrier_rate"], format="percent")
c3.metric("Load Match Rate", m["core"]["load_match_rate"], format="percent")
c4.metric("Transfer Rate", m["core"]["transfer_rate"], format="percent")

c5, c6, c7, c8 = st.columns(4)
c5.metric("No Match Rate", m["core"]["no_match_rate"], format="percent")
c6.metric("Not Authorized Rate", m["core"]["not_authorized_rate"], format="percent")
c7.metric("Not Interested Rate", m["core"]["not_interested_rate"], format="percent")
c8.metric("Incomplete Rate", m["core"]["incomplete_rate"], format="percent")

st.subheader("Conversion Funnel")
st.bar_chart(m["funnel"], color=TEAL, horizontal=True, sort=False)

# Negotiation
st.header("Negotiation Metrics")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Negotiation Success Rate", m["negotiation"]["negotiation_success_rate"], format="percent")
c2.metric("Negotiation Failed Rate", m["negotiation"]["negotiation_failed_rate"], format="percent")
c3.metric(
    "Average Agreed Rate",
    m["negotiation"]["average_agreed_rate"],
    delta=f"{m['negotiation']['agreed_delta_pct']}%",
    delta_color="inverse",
    delta_description="vs. recommended",
    format="dollar",
)
c4.metric("Average Negotiation Turns", m["negotiation"]["average_negotiation_turns"], format="localized")

# Sentiment
st.header("Sentiment")
left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    st.bar_chart(m["sentiment_distribution"].set_index("sentiment")[["count"]], color=TEAL)

with right:
    st.subheader("Sentiment By Outcome")
    st.bar_chart(m["sentiment_by_outcome"], color=[TEAL, SLATE, NAVY], stack="normalize")

# Facility
st.header("Freight Facility Usage")
left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage")
    st.bar_chart(m["origin_usage"], color=[NAVY, TEAL], stack=False)

with right:
    st.subheader("Destination Facility Usage")
    st.bar_chart(m["destination_usage"], color=[NAVY, TEAL], stack=False)

st.subheader("Facility Transfer Rate")
st.dataframe(m["facility_transfer"], use_container_width=True, hide_index=True)

left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Activity By Hour")
    st.dataframe(m["origin_by_hour"], use_container_width=True)

with right:
    st.subheader("Destination Facility Activity By Hour")
    st.dataframe(m["destination_by_hour"], use_container_width=True)

# Operational
st.header("Operational Call Metrics")
left, right = st.columns(2)

with left:
    st.subheader("Calls Per Hour")
    st.bar_chart(m["calls_per_hour"], color=TEAL)

with right:
    st.subheader("Average Call Duration By Outcome")
    st.bar_chart(m["duration_by_outcome"], color=TEAL)

# Recent calls
st.header("Recent Calls")
recent = m["recent_calls"].copy()
recent["final_outcome"] = recent["final_outcome"].map(label)
recent["sentiment"] = recent["sentiment"].map(label)
recent.columns = [c.replace("_", " ").title() for c in recent.columns]
st.dataframe(recent, use_container_width=True, hide_index=True)