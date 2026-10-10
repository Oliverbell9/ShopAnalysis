"""Independent, single-snapshot RAW reconciliation measurements."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from observability.raw_batch_verifier import inspect_raw_batch


def measure_verified_raw_batch(
    database: Path,
    expected_batch_id: str,
    expected_rows: Mapping[str, int],
) -> Mapping[str, int]:
    """Return immutable counts from the verified RAW snapshot."""

    verified, reason, observed = inspect_raw_batch(
        database=database,
        expected_batch_id=expected_batch_id,
        expected_rows=expected_rows,
    )

    if not verified:
        raise RuntimeError(
            f"Independent RAW verification failed: {reason}"
        )

    if observed is None:
        raise RuntimeError(
            "RAW verification succeeded without observed counts"
        )

    return observed
