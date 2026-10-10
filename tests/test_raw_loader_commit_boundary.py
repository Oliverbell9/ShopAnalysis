"""Isolated regression tests for Olist RAW loader commit boundaries."""

from pathlib import Path
from unittest.mock import patch

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from ingestion.duckdb import load_olist_raw as loader
from observability.commit_state import CommitState, CommitTracker


class InjectedPrecommitFailure(RuntimeError):
    pass


class InjectedCommitFailure(RuntimeError):
    pass


class InjectedPostcommitFailure(RuntimeError):
    pass


class ConnectionProxy:
    def __init__(self, connection, failure_mode):
        self.connection = connection
        self.failure_mode = failure_mode
        self.commit_attempts = 0
        self.rollback_attempts = 0
        self.commit_completed = False
        self.failure_injected = False

    def execute(self, query, parameters=None):
        sql = query.strip().upper()

        if (
            self.failure_mode == "precommit"
            and not self.failure_injected
            and sql.startswith("CREATE OR REPLACE TABLE")
        ):
            self.failure_injected = True
            raise InjectedPrecommitFailure(
                "INJECTED_PRECOMMIT_FAILURE"
            )

        if sql == "COMMIT":
            self.commit_attempts += 1

            if self.failure_mode == "commit":
                self.failure_injected = True
                raise InjectedCommitFailure(
                    "INJECTED_COMMIT_FAILURE"
                )

            if self.failure_mode == "postcommit":
                self.connection.execute(query)
                self.commit_completed = True
                self.failure_injected = True
                raise InjectedPostcommitFailure(
                    "INJECTED_AFTER_SUCCESSFUL_COMMIT"
                )

        if sql == "ROLLBACK":
            self.rollback_attempts += 1

        if parameters is None:
            return self.connection.execute(query)

        return self.connection.execute(query, parameters)

    def close(self):
        return self.connection.close()


@pytest.fixture
def raw_loader_fixture(tmp_path):
    parquet_root = tmp_path / "parquet"
    parquet_root.mkdir()

    database = tmp_path / "isolated_warehouse.duckdb"
    batch_id = "isolated_loader_commit_boundary"

    table = pa.table({
        "_source_file": ["isolated_fixture.csv"],
        "_file_row_number": [1],
        "_loaded_at": ["2026-10-10T00:00:00Z"],
        "_batch_id": [batch_id],
        "fixture_value": [1],
    })

    for stem in loader.EXPECTED_ENTITIES:
        pq.write_table(
            table,
            parquet_root / f"{stem}.parquet",
        )

    return database, parquet_root, batch_id


def execute_with_failure(
    database: Path,
    parquet_root: Path,
    failure_mode: str,
    expected_exception: type[Exception],
):
    original_connect = duckdb.connect
    connections = []
    tracker = CommitTracker()

    def injected_connect(*args, **kwargs):
        proxy = ConnectionProxy(
            original_connect(*args, **kwargs),
            failure_mode,
        )
        connections.append(proxy)
        return proxy

    with patch.object(
        loader.duckdb,
        "connect",
        side_effect=injected_connect,
    ):
        with pytest.raises(expected_exception):
            loader.main(
                database_path=database,
                parquet_root=parquet_root,
                commit_tracker=tracker,
            )

    assert len(connections) == 1
    assert connections[0].failure_injected

    return tracker, connections[0], original_connect


def inspect_raw_tables(database, original_connect):
    connection = original_connect(
        str(database),
        read_only=True,
    )

    try:
        rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
              AND table_name LIKE 'olist_%'
            """
        ).fetchall()

        return {name for (name,) in rows}

    finally:
        connection.close()


def test_loader_precommit_failure_rolls_back(raw_loader_fixture):
    database, parquet_root, _ = raw_loader_fixture

    tracker, proxy, original_connect = execute_with_failure(
        database,
        parquet_root,
        "precommit",
        InjectedPrecommitFailure,
    )

    assert proxy.commit_attempts == 0
    assert proxy.rollback_attempts == 1
    assert tracker.state == CommitState.ROLLED_BACK

    assert inspect_raw_tables(database, original_connect) == set()


def test_loader_commit_exception_remains_unknown(raw_loader_fixture):
    database, parquet_root, _ = raw_loader_fixture

    tracker, proxy, original_connect = execute_with_failure(
        database,
        parquet_root,
        "commit",
        InjectedCommitFailure,
    )

    assert proxy.commit_attempts == 1
    assert proxy.rollback_attempts == 1
    assert tracker.state == CommitState.UNKNOWN

    assert inspect_raw_tables(database, original_connect) == set()


def test_loader_postcommit_exception_preserves_unknown(
    raw_loader_fixture,
):
    database, parquet_root, batch_id = raw_loader_fixture

    tracker, proxy, original_connect = execute_with_failure(
        database,
        parquet_root,
        "postcommit",
        InjectedPostcommitFailure,
    )

    assert proxy.commit_attempts == 1
    assert proxy.commit_completed
    assert proxy.rollback_attempts == 1
    assert tracker.state == CommitState.UNKNOWN

    expected_tables = {
        f"olist_{entity}"
        for entity in loader.EXPECTED_ENTITIES.values()
    }

    assert inspect_raw_tables(
        database,
        original_connect,
    ) == expected_tables

    connection = original_connect(
        str(database),
        read_only=True,
    )

    try:
        for table_name in sorted(expected_tables):
            row_count, observed_batch = connection.execute(
                f"""
                SELECT COUNT(*), MIN(_batch_id)
                FROM raw.{table_name}
                """
            ).fetchone()

            assert row_count == 1
            assert observed_batch == batch_id

    finally:
        connection.close()
