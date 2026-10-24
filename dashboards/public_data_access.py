"""CSV-only access to approved ShopAnalysis public aggregates."""

from __future__ import annotations

import csv
import stat
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMAS = {
    "executive_kpis": (
        "delivered_orders", "merchandise", "freight", "gross"
    ),
    "revenue_periods": (
        "reporting_period", "delivered_orders",
        "merchandise", "freight", "gross"
    ),
    "customer_states": (
        "customer_state", "delivered_orders",
        "merchandise", "freight", "gross"
    ),
    "product_categories": (
        "public_category", "distinct_delivered_orders",
        "merchandise", "freight", "gross"
    ),
    "payment_reconciliation": ("public_status", "orders"),
    "repeat_customers": (
        "is_repeat_customer", "customers", "gross_order_value"
    ),
}

EXPECTED_ROWS = {
    "executive_kpis": 1,
    "revenue_periods": 21,
    "customer_states": 27,
    "product_categories": 72,
    "payment_reconciliation": 5,
    "repeat_customers": 2,
}

EXPECTED_MONEY = (
    Decimal("13221498.11"),
    Decimal("2198275.64"),
    Decimal("15419773.75"),
)

MONEY = ("merchandise", "freight", "gross")
MAX_CSV_BYTES = 1_048_576
MAX_FIELD_CHARS = 4096

EXPECTED_PAYMENTS = {
    "exact_match": 98089,
    "missing_payment_or_item_records": 776,
    "within_one_cent": 273,
    "payment_above_item_plus_freight": 264,
    "payment_below_item_plus_freight": 39,
}

EXPECTED_PERIODS = (
    {"2016 launch period"}
    | {f"2017-{month:02d}" for month in range(1, 13)}
    | {f"2018-{month:02d}" for month in range(1, 9)}
)


class PublicDataValidationError(ValueError):
    """The supplied aggregate export failed validation."""


def _fail(message: str) -> None:
    raise PublicDataValidationError(message)


def _integer(value: str) -> int:
    if not value or not value.isascii() or not value.isdecimal():
        _fail("Invalid nonnegative integer")
    return int(value)


def _money(value: str) -> Decimal:
    if not value:
        _fail("Missing monetary value")
    try:
        amount = Decimal(value)
    except InvalidOperation:
        _fail("Invalid monetary value")
    if not amount.is_finite():
        _fail("Non-finite monetary value")
    if amount.as_tuple().exponent < -2:
        _fail("Monetary precision exceeds two decimal places")
    return amount


def _check_path_components(path: Path) -> None:
    """Reject existing symlinks and Windows junctions in a path."""
    absolute = path.absolute()
    for component in (absolute, *absolute.parents):
        if component.is_symlink() or component.is_junction():
            _fail("Linked or junction-backed path is not permitted")


def _read_csv(
    path: Path, columns: tuple[str, ...], expected_rows: int
) -> list[dict]:
    _check_path_components(path)

    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            _fail("Aggregate input must be a regular file")
        if info.st_size > MAX_CSV_BYTES:
            _fail("Aggregate file exceeds size limit")

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)

            if tuple(reader.fieldnames or ()) != columns:
                _fail("Unexpected aggregate schema")

            rows = []
            for row in reader:
                if len(rows) >= expected_rows:
                    _fail("Aggregate row limit exceeded")
                if None in row or any(value is None for value in row.values()):
                    _fail("Malformed aggregate row")
                if any(
                    value == "" or len(value) > MAX_FIELD_CHARS
                    for value in row.values()
                ):
                    _fail("Empty or oversized aggregate value")
                rows.append(row)

        return rows

    except (OSError, UnicodeError, csv.Error) as exc:
        raise PublicDataValidationError(
            "Cannot read valid aggregate CSV"
        ) from exc


def _validate(data: dict[str, list[dict]]) -> None:
    if set(data) != set(SCHEMAS):
        _fail("Unexpected aggregate datasets")

    for name, rows in data.items():
        if len(rows) != EXPECTED_ROWS[name]:
            _fail("Unexpected aggregate row count")

        for row in rows:
            if tuple(row) != SCHEMAS[name]:
                _fail("Unexpected aggregate columns")

            for column in MONEY:
                if column in row:
                    row[column] = _money(row[column])

            if (all(column in row for column in MONEY)
                    and row["merchandise"] + row["freight"] != row["gross"]):
                _fail("Financial reconciliation failed")

        key = {
            "revenue_periods": "reporting_period",
            "customer_states": "customer_state",
            "product_categories": "public_category",
            "payment_reconciliation": "public_status",
            "repeat_customers": "is_repeat_customer",
        }.get(name)

        if key is not None:
            values = [row[key] for row in rows]
            if len(values) != len(set(values)):
                _fail("Duplicate aggregate grouping key")

    integer_columns = {
        "executive_kpis": ("delivered_orders",),
        "revenue_periods": ("delivered_orders",),
        "customer_states": ("delivered_orders",),
        "product_categories": ("distinct_delivered_orders",),
        "payment_reconciliation": ("orders",),
        "repeat_customers": ("customers",),
    }

    for name, columns in integer_columns.items():
        for row in data[name]:
            for column in columns:
                row[column] = _integer(row[column])

    kpi = data["executive_kpis"][0]

    if kpi["delivered_orders"] != 96478:
        _fail("Unexpected delivered-order total")

    if tuple(kpi[column] for column in MONEY) != EXPECTED_MONEY:
        _fail("Unexpected executive monetary totals")

    for name in (
        "revenue_periods",
        "customer_states",
        "product_categories",
    ):
        totals = tuple(
            sum(
                (row[column] for row in data[name]),
                Decimal(0),
            )
            for column in MONEY
        )
        if totals != EXPECTED_MONEY:
            _fail("Cross-dataset monetary parity failed")

    for name in ("revenue_periods", "customer_states"):
        rows = data[name]
        if sum(row["delivered_orders"] for row in rows) != 96478:
            _fail("Delivered-order parity failed")
        if min(row["delivered_orders"] for row in rows) < 10:
            _fail("Small aggregate group")

    if min(
        row["distinct_delivered_orders"]
        for row in data["product_categories"]
    ) < 10:
        _fail("Small category group")

    if {
        row["reporting_period"]
        for row in data["revenue_periods"]
    } != EXPECTED_PERIODS:
        _fail("Unexpected reporting periods")

    payments = {
        row["public_status"]: row["orders"]
        for row in data["payment_reconciliation"]
    }

    if payments != EXPECTED_PAYMENTS:
        _fail("Unexpected payment classifications")

    repeat = {
        row["is_repeat_customer"]: row
        for row in data["repeat_customers"]
    }

    if set(repeat) != {"True", "False"}:
        _fail("Unexpected repeat-customer classifications")

    if (
        repeat["False"]["customers"] != 90557
        or repeat["True"]["customers"] != 2801
    ):
        _fail("Unexpected repeat-customer counts")

    for row in repeat.values():
        row["gross_order_value"] = _money(row["gross_order_value"])

    if sum(
        (row["gross_order_value"] for row in repeat.values()),
        Decimal(0),
    ) != EXPECTED_MONEY[2]:
        _fail("Repeat-customer gross parity failed")


def load_public_aggregates(export_dir: str | Path) -> dict[str, list[dict]]:
    """Load and validate one explicitly supplied aggregate CSV directory."""
    directory = Path(export_dir)
    _check_path_components(directory)

    try:
        if not directory.is_dir():
            _fail("Invalid aggregate directory")

        expected_files = {f"{name}.csv" for name in SCHEMAS}
        actual_files = {
            path.name
            for path in directory.iterdir()
            if path.suffix.lower() == ".csv"
        }

        if actual_files != expected_files:
            _fail("Missing or unexpected aggregate CSV files")

        data = {
            name: _read_csv(
                directory / f"{name}.csv",
                columns,
                EXPECTED_ROWS[name],
            )
            for name, columns in SCHEMAS.items()
        }

        _validate(data)
        return data

    except OSError as exc:
        raise PublicDataValidationError(
            "Cannot access aggregate directory"
        ) from exc
