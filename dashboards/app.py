"""ShopAnalysis governed BI dashboard. Local development, read-only."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from dashboards.data_access import database_path, read_marts
    from dashboards.metrics import assert_reconciled, delivered_metrics
except ModuleNotFoundError:
    from data_access import database_path, read_marts
    from metrics import assert_reconciled, delivered_metrics

st.set_page_config(page_title='ShopAnalysis | Governed BI', layout='wide')
st.title('ShopAnalysis | Governed BI')
st.caption('Revenue governance: PROPOSED — delivered-order recognition; source-supplied monetary units. Not net revenue.')

@st.cache_data(show_spinner='Loading governed marts…', ttl=300)
def load_data(db_path: str):
    return read_marts(Path(db_path))

try:
    marts = load_data(str(database_path()))
except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
    st.error(f'Data source unavailable: {exc}')
    st.stop()

orders = marts['orders']
orders['order_purchased_at'] = pd.to_datetime(orders['order_purchased_at'])
delivered = orders.loc[orders['is_delivered'].eq(True)].copy()
delivered['purchase_month'] = delivered['order_purchased_at'].dt.to_period('M').dt.to_timestamp()

st.sidebar.header('Order-level filters')
months = sorted(delivered['purchase_month'].dropna().dt.date.unique())
if not months:
    st.error('No delivered-order purchase months available.')
    st.stop()
start, end = st.sidebar.select_slider('Purchase month range', options=months, value=(months[0], months[-1]), format_func=lambda d: d.strftime('%b %Y'))
states = sorted(delivered['customer_state'].dropna().unique().tolist())
selected_states = st.sidebar.multiselect('Customer state', states, default=states)
filtered = delivered.loc[(delivered['purchase_month'].dt.date >= start) & (delivered['purchase_month'].dt.date <= end) & delivered['customer_state'].isin(selected_states)]
metrics = delivered_metrics(filtered)
try:
    assert_reconciled(metrics)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric('Delivered orders', f"{metrics['delivered_orders']:,}")
c2.metric('Gross merchandise revenue', f"{metrics['merchandise']:,.2f}")
c3.metric('Freight', f"{metrics['freight']:,.2f}")
c4.metric('Gross order value', f"{metrics['gross']:,.2f}")
st.caption('KPI filters apply to order-grain delivered orders. Amounts use source monetary units; currency is not converted.')

monthly = filtered.groupby('purchase_month', as_index=False).agg(gross_order_value=('gross_order_value', 'sum'), delivered_orders=('order_id', 'count'))
st.subheader('Delivered-order purchase cohorts')
st.plotly_chart(px.line(monthly, x='purchase_month', y='gross_order_value', markers=True, title='Gross order value by original purchase month'), width="stretch")
st.caption('Only populated purchase months are plotted. Missing months are not imputed as zero. This is not a physical delivery-month chart.')

state = filtered.groupby('customer_state', dropna=False, as_index=False).agg(gross_order_value=('gross_order_value', 'sum'), delivered_orders=('order_id', 'count')).sort_values('gross_order_value', ascending=False)
st.subheader('Customer geography')
st.plotly_chart(px.bar(state.head(15), x='customer_state', y='gross_order_value', title='Top customer states by delivered-order gross value'), width="stretch")

st.subheader('Payment reconciliation — all order statuses')
recon = orders.groupby('reconciliation_status', dropna=False).size().reset_index(name='orders').sort_values('orders', ascending=False)
st.dataframe(recon, width="stretch", hide_index=True)
st.caption('Reconciliation statuses are classifications, not automatic financial-error determinations. Counts are unfiltered and cover all order statuses.')

st.subheader('Unfiltered delivered-order mart rankings')
st.caption('Category, seller, and customer marts are lifetime aggregates and are NOT affected by purchase-month or customer-state filters. Distinct order counts across categories/sellers must not be summed.')
left, right = st.columns(2)
with left:
    st.markdown('**Top categories by gross order value**')
    category = marts['category'].copy()
    category['display_category'] = category['product_category_name_english'].fillna(category['product_category_name']).fillna('(missing source category)')
    st.dataframe(category.sort_values('gross_order_value', ascending=False)[['display_category','category_translation_status','gross_order_value']].head(15), hide_index=True, width="stretch")
with right:
    st.markdown('**Top sellers by gross order value**')
    seller = marts['seller'].sort_values('gross_order_value', ascending=False)
    st.dataframe(seller[['seller_id','seller_state','gross_order_value']].head(15), hide_index=True, width="stretch")

st.markdown('**Customer revenue and repeat-purchase distribution (unfiltered)**')
customer = marts['customer']
repeat = customer.groupby('is_repeat_customer', dropna=False).agg(customers=('customer_unique_id','count'), gross_order_value=('gross_order_value','sum')).reset_index()
st.dataframe(repeat, width="stretch", hide_index=True)
st.caption('No refunds, returns, discounts, or adjustments have been established; net revenue is unavailable.')
