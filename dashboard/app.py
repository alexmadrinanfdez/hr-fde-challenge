import altair as alt
import pandas as pd
import streamlit as st

import dashboard.queries as queries


TEAL = "#2A9D8F"
NAVY = "#16324F"


st.set_page_config(
    page_title="Inbound Carrier Sales Dashboard",
    layout="wide",
)

st.title("Inbound Carrier Sales Dashboard")


def dict_as_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def titleize(value):
    if value is None:
        return "Unknown"
    if isinstance(value, str):
        value = value.replace("_", " ").strip()
        return value.title() if value else "Unknown"
    return value


def prettify_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [col.replace("_", " ").strip().title() for col in df.columns]
    return df


def prepare_dataframe(rows, numeric_columns=None, text_columns=None) -> pd.DataFrame:
    df = dict_as_dataframe(rows)

    if numeric_columns:
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    if text_columns:
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].map(titleize)

    return df


def format_percent(value) -> str:
    return f"{value:.2f}%"


def format_number(value) -> str:
    return f"{value:,.2f}"


def format_currency(value) -> str:
    return f"${value:,.2f}"


def format_integer(value) -> str:
    return f"{int(value):,}"


def bar_chart(df: pd.DataFrame, x: str, y: str, color: str = TEAL, sort=None, height: int = 320):
    chart = (
        alt.Chart(df)
        .mark_bar(color=color, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(x, sort=sort, title=None),
            y=alt.Y(y, title=None),
            tooltip=list(df.columns),
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def grouped_bar_chart(df: pd.DataFrame, x: str, y: str, group: str, height: int = 360):
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(x, title=None),
            xOffset=alt.XOffset(group),
            y=alt.Y(y, title=None),
            color=alt.Color(
                group,
                scale=alt.Scale(
                    domain=["Total Calls", "Successful Calls"],
                    range=[NAVY, TEAL],
                ),
                title=None,
            ),
            tooltip=list(df.columns),
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def heatmap(df: pd.DataFrame, x: str, y: str, color: str, height: int = 320):
    chart = (
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X(x, title=None),
            y=alt.Y(y, title=None),
            color=alt.Color(color, scale=alt.Scale(scheme="teals"), title="Call Count"),
            tooltip=list(df.columns),
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def combined_usage(total_rows, success_rows, key_column: str) -> pd.DataFrame:
    total_df = prepare_dataframe(total_rows, numeric_columns=["call_count"])
    success_df = prepare_dataframe(success_rows, numeric_columns=["successful_call_count"])

    merged = total_df.merge(success_df, on=key_column, how="outer")
    merged[key_column] = merged[key_column].map(titleize)
    merged["call_count"] = pd.to_numeric(merged["call_count"], errors="coerce").fillna(0)
    merged["successful_call_count"] = pd.to_numeric(
        merged["successful_call_count"], errors="coerce"
    ).fillna(0)

    merged = merged.melt(
        id_vars=[key_column],
        value_vars=["call_count", "successful_call_count"],
        var_name="series",
        value_name="count",
    )

    merged["series"] = merged["series"].replace(
        {
            "call_count": "Total Calls",
            "successful_call_count": "Successful Calls",
        }
    )
    return merged.sort_values(by=[key_column, "series"])


def calls_by_hour_dataframe(rows) -> pd.DataFrame:
    df = prepare_dataframe(rows, numeric_columns=["hour_of_day", "call_count"])
    all_hours = pd.DataFrame({"hour_of_day": list(range(24))})
    df = all_hours.merge(df, on="hour_of_day", how="left")
    df["call_count"] = df["call_count"].fillna(0)
    return df


core = queries.get_core_funnel_metrics()
negotiation = queries.get_negotiation_metrics()
operational = queries.get_operational_metrics()

sentiment_distribution_df = prepare_dataframe(
    queries.get_sentiment_distribution(),
    numeric_columns=["count", "percentage"],
    text_columns=["sentiment"],
)

negative_sentiment_by_outcome_df = prepare_dataframe(
    queries.get_negative_sentiment_by_outcome(),
    numeric_columns=["negative_count", "total_count", "negative_rate"],
    text_columns=["final_outcome"],
)

origin_usage_df = combined_usage(
    queries.get_top_origin_facilities(limit=1000),
    queries.get_successful_origin_facility_usage(),
    key_column="origin",
)

destination_usage_df = combined_usage(
    queries.get_top_destination_facilities(limit=1000),
    queries.get_successful_destination_facility_usage(),
    key_column="destination",
)

facility_transfer_df = prepare_dataframe(
    queries.get_facility_transfer_rate(),
    numeric_columns=["total_matched_calls", "transferred_calls", "transfer_rate"],
    text_columns=["origin", "destination"],
)

origin_by_hour_df = prepare_dataframe(
    queries.get_origin_facility_usage_by_hour(),
    numeric_columns=["hour_of_day", "call_count"],
    text_columns=["origin"],
)

destination_by_hour_df = prepare_dataframe(
    queries.get_destination_facility_usage_by_hour(),
    numeric_columns=["hour_of_day", "call_count"],
    text_columns=["destination"],
)

calls_by_hour_df = calls_by_hour_dataframe(queries.get_calls_by_hour())

duration_by_outcome_df = prepare_dataframe(
    queries.get_average_call_duration_by_outcome(),
    numeric_columns=["average_call_duration_seconds"],
    text_columns=["final_outcome"],
)

recent_calls_df = prepare_dataframe(
    queries.get_recent_calls(),
    numeric_columns=["agreed_rate", "negotiation_turns"],
    text_columns=["final_outcome", "sentiment"],
)


st.header("Core Funnel Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Saved Calls", format_integer(core["total_saved_calls"]))
c2.metric("Authorized Carrier Rate", format_percent(core["authorized_carrier_rate"]))
c3.metric("Load Match Rate", format_percent(core["load_match_rate"]))
c4.metric("Transfer Rate", format_percent(core["transfer_rate"]))

c5, c6, c7, c8 = st.columns(4)
c5.metric("No Match Rate", format_percent(core["no_match_rate"]))
c6.metric("Not Authorized Rate", format_percent(core["not_authorized_rate"]))
c7.metric("Caller Not Interested Rate", format_percent(core["caller_not_interested_rate"]))
c8.metric("Incomplete Call Rate", format_percent(core["incomplete_call_rate"]))


st.header("Negotiation Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Negotiation Success Rate", format_percent(negotiation["negotiation_success_rate"]))
c2.metric("Negotiation Failed Rate", format_percent(negotiation["negotiation_failed_rate"]))
c3.metric("Average Agreed Rate", format_currency(negotiation["average_agreed_rate"]))
c4.metric("Average Negotiation Turns", format_number(negotiation["average_negotiation_turns"]))


st.header("Sentiment")
left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    bar_chart(sentiment_distribution_df, x="sentiment:N", y="count:Q")

with right:
    st.subheader("Negative Sentiment By Outcome")
    bar_chart(
        negative_sentiment_by_outcome_df,
        x="final_outcome:N",
        y="negative_rate:Q",
    )


st.header("Freight Facility Usage")
left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage")
    grouped_bar_chart(origin_usage_df, x="origin:N", y="count:Q", group="series:N")

with right:
    st.subheader("Destination Facility Usage")
    grouped_bar_chart(destination_usage_df, x="destination:N", y="count:Q", group="series:N")

st.subheader("Facility Transfer Rate")
st.dataframe(prettify_columns(facility_transfer_df), use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("Origin Facility Usage By Hour")
    heatmap(origin_by_hour_df, x="hour_of_day:O", y="origin:N", color="call_count:Q")

with right:
    st.subheader("Destination Facility Usage By Hour")
    heatmap(destination_by_hour_df, x="hour_of_day:O", y="destination:N", color="call_count:Q")


st.header("Operational Call Metrics")
left, right = st.columns(2)

with left:
    st.metric(
        "Average Call Duration (Seconds)",
        format_number(operational["average_call_duration_seconds"]),
    )

with right:
    st.subheader("Calls Per Hour")
    bar_chart(
        calls_by_hour_df,
        x="hour_of_day:O",
        y="call_count:Q",
        color=NAVY,
        sort=list(range(24)),
    )

st.subheader("Average Call Duration By Outcome")
bar_chart(
    duration_by_outcome_df,
    x="final_outcome:N",
    y="average_call_duration_seconds:Q",
)


st.header("Recent Calls")
st.dataframe(prettify_columns(recent_calls_df), use_container_width=True)