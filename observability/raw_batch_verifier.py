"""Read-only, single-snapshot RAW batch verification."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import duckdb

from observability.ingestion_config import EXPECTED_RAW_TABLES


EXPECTED_TABLES = EXPECTED_RAW_TABLES


def inspect_raw_batch(
    database: Path,
    expected_batch_id: str,
    expected_rows: Mapping[str, int],
) -> tuple[bool, str, Mapping[str, int] | None]:
    """Verify and measure nine RAW tables in one read-only transaction."""

    database = Path(database).resolve()

    if not isinstance(expected_batch_id, str) or not expected_batch_id.strip():
        raise ValueError("A nonempty expected batch ID is required")

    expected = dict(expected_rows)

    if set(expected) != set(EXPECTED_TABLES):
        raise ValueError(
            "Expected row counts must cover exactly the nine RAW tables"
        )

    if any(
        type(value) is not int or value < 0
        for value in expected.values()
    ):
        raise ValueError("Expected row counts must be nonnegative integers")

    if not database.is_file():
        return False, "RAW_DATABASE_MISSING", None

    connection = duckdb.connect(str(database), read_only=True)
    transaction_active = False

    try:
        connection.execute("BEGIN TRANSACTION")
        transaction_active = True

        observed = {}

        for table in EXPECTED_TABLES:
            exists = connection.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'raw'
                  AND table_name = ?
                  AND table_type = 'BASE TABLE'
                """,
                [table],
            ).fetchone()[0]

            if exists != 1:
                return False, f"TABLE_MISSING:{table}", None

            columns = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'raw'
                      AND table_name = ?
                    """,
                    [table],
                ).fetchall()
            }

            if "_batch_id" not in columns:
                return False, f"BATCH_COLUMN_MISSING:{table}", None

            total, populated, distinct, actual_batch = connection.execute(
                f"""
                SELECT
                    COUNT(*),
                    COUNT(_batch_id),
                    COUNT(DISTINCT _batch_id),
                    MIN(_batch_id)
                FROM raw.{table}
                """
            ).fetchone()

            observed[table] = total

            if total != expected[table]:
                return False, f"ROW_COUNT_MISMATCH:{table}", None

            if total == 0:
                continue

            if populated != total:
                return False, f"NULL_BATCH_ID:{table}", None

            if distinct != 1 or actual_batch != expected_batch_id:
                return False, f"BATCH_MISMATCH:{table}", None

        connection.execute("COMMIT")
        transaction_active = False

        return (
            True,
            "RAW_BATCH_VERIFIED",
            MappingProxyType(observed),
        )

    finally:
        try:
            if transaction_active:
                connection.execute("ROLLBACK")
        finally:
            connection.close()


def verify_raw_batch(
    database: Path,
    expected_batch_id: str,
    expected_rows: dict[str, int],
) -> tuple[bool, str]:
    """Preserve the existing verification interface and failure codes."""

    verified, reason, _ = inspect_raw_batch(
        database=database,
        expected_batch_id=expected_batch_id,
        expected_rows=expected_rows,
    )

    return verified, reason
