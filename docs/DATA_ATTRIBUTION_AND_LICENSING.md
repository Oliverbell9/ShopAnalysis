# ShopAnalysis — Dataset Attribution and Licensing

## 1. Source Dataset

**Dataset:** Brazilian E-Commerce Public Dataset by Olist
**Publisher:** Olist
**Provider:** Kaggle
**Source:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
**Dataset license:** Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International (CC BY-NC-SA 4.0)
**License text:** https://creativecommons.org/licenses/by-nc-sa/4.0/

ShopAnalysis uses the Olist dataset as a source for demonstrating governed data ingestion, transformation, reconciliation, analytics, and data engineering practices.

## 2. Educational and Portfolio Purpose

ShopAnalysis is intended as a noncommercial educational and professional portfolio demonstration.

The project demonstrates technical methods and analytical workflows. It is not intended to sell, license commercially, or otherwise commercially exploit the Olist source data or its derived analytical datasets.

Any future commercial use requires a separate licensing review.

## 3. Data Transformations

ShopAnalysis processes the source dataset through governed ingestion and analytical transformations.

The project derives aggregate datasets covering:

- Executive revenue and order metrics
- Revenue by reporting period
- Revenue by customer state
- Revenue by product category
- Payment reconciliation classifications
- Repeat-customer distributions

These outputs are derived from the Olist source data and are not original datasets published by Olist.

Financial values are retained in source-supplied monetary units. ShopAnalysis does not establish net revenue, refunds, returns, or currency conversions without supporting source evidence.

## 4. Attribution and Modification Notice

**Attribution:** Contains analytical aggregates derived from the *Brazilian E-Commerce Public Dataset by Olist*, published by Olist and made available through Kaggle under CC BY-NC-SA 4.0.

**Changes made:** The original data has been processed, joined, classified, reconciled, grouped, and aggregated for educational analytics. The published analytical outputs are not unchanged copies of the source files.

Olist does not sponsor, endorse, or certify ShopAnalysis.

## 5. Redistribution and ShareAlike

The Olist source dataset remains subject to its applicable CC BY-NC-SA 4.0 license.

Where published aggregate outputs qualify as adapted material under that license, the applicable Attribution, NonCommercial, and ShareAlike obligations must be satisfied.

The precise licensing treatment of the aggregate outputs must be confirmed before public redistribution. This document does not grant additional rights beyond those provided by the applicable source license.

## 6. Software and Data Licensing Separation

The Olist dataset license and the license governing original ShopAnalysis software are separate.

A software license for ShopAnalysis has not yet been selected.

Selecting a software license does not override restrictions on the Olist source dataset or qualifying adaptations.

## 7. Publication Controls

The intended public dashboard must use approved aggregate data rather than connecting directly to internal DuckDB marts containing order-level, customer-level, or seller-level information.

Raw source files and internal database artifacts are not intended for publication.

Public release remains subject to completion of the licensing review, attribution implementation, disclosure review, and separate deployment authorization.

## 8. Status

**Document status:** Draft — pending review
**Intended use:** Noncommercial educational/portfolio demonstration
**Public data release:** Not yet approved
**Public deployment:** Not authorized
