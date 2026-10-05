# Revenue Metric Specification

## Purpose

This document defines the governed revenue-related metrics used by ShopAnalysis

for the Olist source. The definitions separate merchandise value, freight,

customer order value, and payment value so that financially distinct measures

are not treated as interchangeable.

These definitions are based on observed source behavior and reconciliation

results. They do not infer unsupported discounts, refunds, financing charges,

interest, or other business events.

---

## Source Grain

Primary analytical grain:

- One row per Olist order.

Primary governed intermediate models:

- `int_olist__orders_enriched`

- `int_olist__order_reconciliation`

Persistent customer identity:

- `customer_unique_id`

Transactional order/customer identifier:

- `customer_id`

---

## Recognition Population

Revenue-related Olist metrics use:

`order_status = 'delivered'`

as the recognition population.

Observed delivered population:

- Orders: 96,478

- Merchandise value: 13,221,498.11

- Freight value: 2,198,275.64

- Gross order value: 15,419,773.75

The population is based on delivered status rather than requiring a non-null

delivery timestamp.

Eight delivered orders have no recorded customer-delivery timestamp. Those

orders contain valid item and payment records and reconcile exactly between

item-plus-freight and payment value.

They therefore remain in the delivered financial population and are treated as

timestamp-completeness exceptions rather than excluded transactions.

---

## Gross Merchandise Revenue

### Technical Name

`gross_merchandise_revenue`

### Definition

Sum of observed Olist item prices for orders whose order status is `delivered`.

### Formula

`SUM(item_revenue) WHERE order_status = 'delivered'`

### Grain

Additive from order grain across supported analytical dimensions.

### Observed Control Total

`13,221,498.11`

### Exclusions

- Freight is excluded.

- Payment differences are excluded.

- Non-delivered orders are excluded.

### Interpretation

This metric represents delivered merchandise value in the Olist source. It

must not be interpreted as accounting net revenue.

---

## Freight Value

### Technical Name

`freight_value`

### Definition

Sum of observed freight amounts associated with delivered Olist order items.

### Formula

`SUM(freight_revenue) WHERE order_status = 'delivered'`

### Observed Control Total

`2,198,275.64`

Freight remains separately identifiable and must not be silently merged into

Gross Merchandise Revenue.

---

## Gross Order Value

### Technical Name

`gross_order_value`

### Definition

Delivered merchandise value plus delivered freight value.

### Formula

`SUM(item_plus_freight) WHERE order_status = 'delivered'`

Equivalent order-level expression:

`item_revenue + freight_revenue`

### Observed Control Total

`15,419,773.75`

### Interpretation

Gross Order Value represents the observed item-plus-freight value associated

with delivered orders.

It is distinct from payment value.

---

## Payment Value

### Technical Name

`payment_value`

### Definition

Sum of payment records associated with an order.

Payment value belongs to the payment and reconciliation domain. It is not

designated as the authoritative revenue metric.

Observed delivered-order payment value:

`15,422,461.77`

Differences between payment value and item-plus-freight are preserved through

the governed reconciliation layer and must not automatically be classified as

discounts, refunds, interest, financing charges, or fees.

---

## Net Revenue

### Technical Name

`net_revenue`

### Current Status

Not derivable from the Olist source alone with the currently available

evidence.

A governed net-revenue metric requires explicit evidence supporting deductions

such as refunds, returns, discounts, credits, or other adjustments.

ShopAnalysis will not manufacture net revenue by subtracting unexplained

payment/item differences.

---

## Time Basis

### Delivery Analysis

`delivered_to_customer_at` is the preferred event timestamp for analyses based

on physical delivery.

Observed completeness among delivered orders:

- Delivered orders: 96,478

- Delivered orders with delivery timestamp: 96,470

- Timestamp exceptions: 8

The eight exceptions remain financially included but must be identifiable as

missing-delivery-timestamp records.

No synthetic delivery timestamp is assigned.

### Purchase Analysis

`order_purchased_at` is retained as a separate booking/demand timestamp.

Purchase-date and delivery-date analyses answer different business questions

and must not be silently substituted for one another.

---

## Reconciliation Policy

The governed reconciliation layer classifies orders as:

- `exact_match`

- `within_one_cent`

- `payment_above_item_plus_freight`

- `payment_below_item_plus_freight`

- `missing_items`

- `missing_payment`

The classification is mechanical and does not assign unsupported business

causes to observed differences.

A tolerance of one cent is used only for reconciliation classification. It

does not alter the underlying monetary values.

---

## Currency

The Olist monetary fields are preserved as supplied by the source dataset.

ShopAnalysis does not perform currency conversion for the Olist source unless

a separately governed currency rule and supporting source evidence are added.

All governed monetary calculations use exact decimal arithmetic.

---

## Governance Status

Status: Proposed

The definitions in this document are supported by the current Olist source

profiling and reconciliation evidence. They remain subject to revision if

additional authoritative refund, return, adjustment, currency, or accounting

data is introduced.

---

## Ownership

Project owner: ShopAnalysis

Metric implementation must remain consistent across:

- dbt marts

- semantic definitions

- dashboards

- reconciliation outputs

- analytical notebooks

- technical report
