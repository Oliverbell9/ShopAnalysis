"""Approved identifiers for governed Olist RAW ingestion."""

PIPELINE_NAME = "olist_raw_ingestion"
STAGE_NAME = "load_olist_raw"

EXPECTED_RAW_TABLES = (
    "olist_customers",
    "olist_geolocation",
    "olist_order_items",
    "olist_payments",
    "olist_reviews",
    "olist_orders",
    "olist_products",
    "olist_sellers",
    "olist_translation",
)


def validate_ingestion_identity(
    pipeline_name: str,
    stage_name: str,
) -> None:
    """Reject identifiers outside the approved RAW ingestion workflow."""

    if pipeline_name != PIPELINE_NAME:
        raise ValueError(
            f"Unexpected pipeline name: {pipeline_name!r}"
        )

    if stage_name != STAGE_NAME:
        raise ValueError(
            f"Unexpected stage name: {stage_name!r}"
        )
