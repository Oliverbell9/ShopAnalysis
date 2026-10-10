"""Validated result metadata for Olist RAW ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from observability.ingestion_config import EXPECTED_RAW_TABLES


@dataclass(frozen=True)
class RawIngestionResult:
    database_path: Path
    batch_id: str
    source_rows: Mapping[str, int]

    def __post_init__(self) -> None:
        database = Path(self.database_path).resolve()

        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            raise ValueError("A nonempty batch ID is required")

        rows = dict(self.source_rows)

        if set(rows) != set(EXPECTED_RAW_TABLES):
            raise ValueError(
                "Source row counts must cover exactly nine RAW tables"
            )

        if any(
            type(count) is not int or count < 0
            for count in rows.values()
        ):
            raise ValueError(
                "Source row counts must be nonnegative integers"
            )

        object.__setattr__(self, "database_path", database)
        object.__setattr__(
            self,
            "source_rows",
            MappingProxyType(rows),
        )
