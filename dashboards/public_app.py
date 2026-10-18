"""Local-only public aggregate dashboard for ShopAnalysis.

Run:
    python -m streamlit run dashboards/public_app.py -- \
        --export-dir PATH_TO_APPROVED_AGGREGATE_EXPORT

This application reads only six validated aggregate CSV files.
It does not access the internal DuckDB database.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from dashboards.public_data_access import (
        PublicDataValidationError,
        load_public_aggregates,
    )
except ModuleNotFoundError as exc:
    if exc.name not in {"dashboards", "dashboards.public_data_access"}:
        raise
    from public_data_access import (
        PublicDataValidationError,
        load_public_aggregates,
    )


st.set_page_config(
    page_title="ShopAnalysis | Public Analytics",
    page_icon="📊",
    layout="wide",
)


SOURCE_URL = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"

STATUS_LABELS = {
    "exact_match": "Exact match",
    "missing_payment_or_item_records": "Missing payment or item records",
    "within_one_cent": "Within one cent",
    "payment_above_item_plus_freight": "Payment above item + freight",
    "payment_below_item_plus_freight": "Payment below item + freight",
}

PERIOD_ORDER = (
    ["2016 launch period"]
    + [f"2017-{month:02d}" for month in range(1, 13)]
    + [f"2018-{month:02d}" for month in range(1, 9)]
)


def parse_export_directory() -> Path:
    parser = argparse.ArgumentParser(
        description="ShopAnalysis local public aggregate dashboard"
    )
    parser.add_argument(
        "--export-dir",
        required=True,
        help="Explicit directory containing the six validated CSV exports",
    )
    args = parser.parse_args(sys.argv[1:])
    return Path(args.export_dir)


def money_text(value: Decimal) -> str:
    return f"{value:,.2f}"


def money_frame(rows: list[dict], columns: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.DataFrame(rows).copy()
    for column in columns:
        frame[column] = frame[column].map(float)
    return frame


def section_heading(title: str, explanation: str) -> None:
    st.subheader(title)
    st.caption(explanation)


def show_executive(data: dict[str, list[dict]]) -> None:
    section_heading(
        "1. Executive overview",
        "Delivered orders and source-supplied monetary amounts. "
        "Gross = merchandise + freight; gross is not verified net revenue.",
    )

    kpi = data["executive_kpis"][0]
    columns = st.columns(4)

    columns[0].metric("Delivered orders", f"{kpi['delivered_orders']:,}")
    columns[1].metric(
        "Merchandise amount",
        money_text(kpi["merchandise"]),
    )
    columns[2].metric(
        "Freight amount",
        money_text(kpi["freight"]),
    )
    columns[3].metric(
        "Gross amount",
        money_text(kpi["gross"]),
    )

    st.caption(
        "Monetary figures are in source-supplied units. "
        "No independent currency conversion, refund adjustment, "
        "or net-revenue determination is represented."
    )


def show_periods(data: dict[str, list[dict]]) -> None:
    section_heading(
        "2. Revenue by reporting period",
        "Purchase-period reporting for delivered orders. "
        "The 2016 launch period is consolidated and is not a single month.",
    )
    frame = money_frame(data["revenue_periods"], ("merchandise", "freight", "gross"))
    frame["reporting_period"] = pd.Categorical(
        frame["reporting_period"], categories=PERIOD_ORDER, ordered=True
    )
    frame = frame.sort_values("reporting_period")

    with st.popover("Choose reporting periods", use_container_width=True):
        selected_periods = st.multiselect(
            "Reporting periods", options=PERIOD_ORDER, default=PERIOD_ORDER,
            key="public_reporting_periods",
        )
    st.caption(f"{len(selected_periods)} of {len(PERIOD_ORDER)} reporting periods selected")
    measure = st.selectbox(
        "Monetary measure", options=("gross", "merchandise", "freight"),
        format_func=lambda value: value.capitalize(), key="public_period_measure",
    )
    filtered = frame.loc[frame["reporting_period"].isin(selected_periods)].copy()
    if filtered.empty:
        st.info("Select at least one reporting period to display results.")
        return

    figure = px.bar(
        filtered, x="reporting_period", y=measure,
        labels={
            "reporting_period": "Reporting period",
            measure: f"{measure.capitalize()} amount (source units)",
        },
        title=f"{measure.capitalize()} amount by purchase reporting period",
    )
    visible_periods = [period for period in PERIOD_ORDER if period in selected_periods]
    tick_step = 3 if len(visible_periods) > 12 else (2 if len(visible_periods) > 8 else 1)
    tick_periods = visible_periods[::tick_step]
    if visible_periods[-1] not in tick_periods:
        tick_periods.append(visible_periods[-1])
    figure.update_xaxes(
        type="category", categoryorder="array", categoryarray=PERIOD_ORDER,
        tickmode="array", tickvals=tick_periods,
        ticktext=["2016 launch" if p == "2016 launch period" else p for p in tick_periods],
        tickangle=-30, automargin=True,
    )
    figure.update_layout(height=470, margin=dict(b=75))
    st.caption(
        "Only selected reporting periods are displayed. "
        "The 2016 launch period combines the available 2016 months."
    )
    st.plotly_chart(figure, width="stretch")
    st.dataframe(
        filtered[["reporting_period", "delivered_orders", "merchandise", "freight", "gross"]],
        hide_index=True, width="stretch",
    )


def show_geography(data: dict[str, list[dict]]) -> None:
    section_heading(
        "3. Customer geography",
        "Delivered-order counts and monetary amounts grouped by customer state.",
    )
    frame = money_frame(data["customer_states"], ("merchandise", "freight", "gross"))
    states = sorted(frame["customer_state"].unique().tolist())
    with st.popover("Choose customer states", use_container_width=True):
        selected_states = st.multiselect(
            "Customer states", options=states, default=states,
            key="public_customer_states",
        )
    st.caption(f"{len(selected_states)} of {len(states)} customer states selected")
    measure = st.selectbox(
        "Monetary measure", options=("gross", "merchandise", "freight"),
        format_func=lambda value: value.capitalize(), key="public_state_measure",
    )
    filtered = frame.loc[frame["customer_state"].isin(selected_states)].copy()
    if filtered.empty:
        st.info("Select at least one customer state to display results.")
        return
    filtered = filtered.sort_values(measure, ascending=False)
    figure = px.bar(
        filtered, x="customer_state", y=measure,
        labels={
            "customer_state": "Customer state",
            measure: f"{measure.capitalize()} amount (source units)",
        },
        title=f"{measure.capitalize()} amount by customer state",
    )
    st.plotly_chart(figure, width="stretch")
    st.dataframe(filtered, hide_index=True, width="stretch")


def show_categories(data: dict[str, list[dict]]) -> None:
    section_heading(
        "4. Product categories",
        "Monetary amounts by public product category. "
        "Distinct delivered-order counts are not additive across categories.",
    )
    frame = money_frame(data["product_categories"], ("merchandise", "freight", "gross"))
    measure = st.selectbox(
        "Monetary measure", options=("gross", "merchandise", "freight"),
        format_func=lambda value: value.capitalize(), key="public_category_measure",
    )
    top_count = st.slider(
        "Number of top categories", min_value=1, max_value=len(frame),
        value=min(15, len(frame)), key="public_category_top_n",
    )
    frame = frame.sort_values(measure, ascending=False)
    top = frame.head(top_count).sort_values(measure)
    figure = px.bar(
        top, x=measure, y="public_category", orientation="h",
        labels={
            measure: f"{measure.capitalize()} amount (source units)",
            "public_category": "Public product category",
        },
        title=f"Top {top_count} categories by {measure} amount",
    )
    figure.update_traces(texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False)
    figure.update_yaxes(
        categoryorder="array", categoryarray=list(top["public_category"]), automargin=True,
    )
    max_value = float(top[measure].max())
    if max_value > 0:
        figure.update_xaxes(rangemode="tozero", range=[0, max_value * 1.20])
    figure.update_layout(
        height=max(420, min(1800, top_count * 32 + 150)),
        margin=dict(l=180, r=90),
    )
    st.plotly_chart(figure, width="stretch")
    st.warning(
        "A delivered order may contain items from multiple categories. "
        "Do not sum distinct delivered-order counts across categories."
    )
    st.caption(
        "The chart displays the selected top N categories. "
        "The table retains all categories, sorted by the selected measure."
    )
    st.dataframe(frame, hide_index=True, width="stretch")


def show_payments(data: dict[str, list[dict]]) -> None:
    section_heading(
        "5. Payment reconciliation",
        "Order-level classifications comparing payment records with "
        "item-plus-freight amounts. Missing records are not automatically "
        "payment discrepancies.",
    )
    frame = pd.DataFrame(data["payment_reconciliation"])
    frame["classification"] = frame["public_status"].map(STATUS_LABELS)
    frame = frame.sort_values("orders", ascending=False)
    with st.popover("Choose payment classifications", use_container_width=True):
        selected_statuses = st.multiselect(
            "Payment classifications", options=frame["public_status"].tolist(),
            default=frame["public_status"].tolist(),
            format_func=lambda value: STATUS_LABELS[value],
            key="public_payment_statuses",
        )
    st.caption(f"{len(selected_statuses)} of {len(frame)} payment classifications selected")
    filtered = frame.loc[frame["public_status"].isin(selected_statuses)].copy()
    if filtered.empty:
        st.info("Select at least one payment classification.")
        return
    figure = px.bar(
        filtered, x="orders", y="classification", orientation="h",
        labels={"orders": "Orders", "classification": "Reconciliation classification"},
        title="Selected payment reconciliation classifications",
    )
    st.plotly_chart(figure, width="stretch")
    st.dataframe(filtered[["classification", "orders"]], hide_index=True, width="stretch")
    non_exact = filtered.loc[
        filtered["public_status"] != "exact_match"
    ].sort_values("orders", ascending=True)
    if not non_exact.empty:
        detail_figure = px.bar(
            non_exact, x="orders", y="classification", orientation="h", text="orders",
            labels={"orders": "Orders", "classification": "Non-exact-match classification"},
            title="Detail: selected classifications other than exact match",
        )
        detail_figure.update_traces(textposition="outside", cliponaxis=False)
        max_orders = float(non_exact["orders"].max())
        if max_orders > 0:
            detail_figure.update_xaxes(rangemode="tozero", range=[0, max_orders * 1.20])
        detail_figure.update_layout(height=350, margin=dict(l=220, r=70))
        st.plotly_chart(detail_figure, width="stretch")
    st.caption(
        "Selections affect only this reconciliation section. "
        "Missing records and within-one-cent classifications should "
        "not automatically be interpreted as confirmed payment errors."
    )
    st.caption(
        "This classification covers the validated payment reconciliation "
        "population, which is not the same as the delivered-order KPI population."
    )


def show_repeat_customers(data: dict[str, list[dict]]) -> None:
    section_heading(
        "6. Repeat customers",
        "Customers classified by whether they have more than one "
        "delivered order. This is not a retention-rate or cohort metric.",
    )

    frame = money_frame(
        data["repeat_customers"],
        ("gross_order_value",),
    )
    frame["customer_group"] = frame["is_repeat_customer"].map(
        {
            "True": "Repeat customers",
            "False": "Non-repeat customers",
        }
    )

    total_customers = int(frame["customers"].sum())
    repeat_customers = int(
        frame.loc[
            frame["is_repeat_customer"] == "True",
            "customers",
        ].sum()
    )

    left, right = st.columns(2)
    left.metric("Customers", f"{total_customers:,}")
    right.metric(
        "Repeat-customer share",
        f"{repeat_customers / total_customers:.2%}",
    )

    figure = px.bar(
        frame,
        x="customer_group",
        y="customers",
        labels={
            "customer_group": "Customer group",
            "customers": "Customers",
        },
        title="Customer distribution by delivered-order frequency",
    )
    st.plotly_chart(figure, width="stretch")

    st.dataframe(
        frame[
            [
                "customer_group",
                "customers",
                "gross_order_value",
            ]
        ],
        hide_index=True,
        width="stretch",
    )


def show_attribution() -> None:
    st.divider()
    st.subheader("Dataset attribution and methodology")

    st.markdown(
        "Contains analytical aggregates derived from the "
        f"[Brazilian E-Commerce Public Dataset by Olist]({SOURCE_URL}), "
        "published by Olist and made available through Kaggle under "
        f"[CC BY-NC-SA 4.0]({LICENSE_URL})."
    )

    st.markdown(
        "**Changes made:** The source data was processed, joined, "
        "classified, reconciled, grouped, and aggregated for "
        "educational analytics. These outputs are not unchanged "
        "copies of the Olist source files."
    )

    st.caption(
        "Noncommercial educational and professional portfolio "
        "demonstration. Olist does not sponsor, endorse, or certify "
        "ShopAnalysis."
    )

    st.info(
        "Publication status: Not approved. Dataset attribution and "
        "licensing documentation remains a draft pending review. "
        "Local development does not authorize public redistribution."
    )


def main() -> None:
    st.title("ShopAnalysis | Public Analytics")
    st.caption(
        "Local development preview — validated aggregate CSV data only"
    )

    try:
        export_dir = parse_export_directory()
        data = load_public_aggregates(export_dir)
    except (SystemExit, PublicDataValidationError, OSError, ValueError) as exc:
        st.error(
            "The approved aggregate export directory was not supplied "
            "or its contents failed validation. Analytical results "
            "will not be displayed."
        )
        st.caption(f"Validation detail: {exc}")
        st.stop()

    st.success("Aggregate export validation passed.")

    show_executive(data)
    show_periods(data)
    show_geography(data)
    show_categories(data)
    show_payments(data)
    show_repeat_customers(data)
    show_attribution()


if __name__ == "__main__":
    main()
