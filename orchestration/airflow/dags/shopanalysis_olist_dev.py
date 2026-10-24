"""Manually triggered, isolated ShopAnalysis Olist pipeline."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from airflow.sdk import DAG, task

SOURCE_DIR = Path("/opt/airflow/sources/olist")
MANIFEST = Path("/opt/airflow/manifests/olist_manifest.json")

WORKSPACE = Path("/opt/airflow/workspace")
PARQUET_ROOT = WORKSPACE / "parquet" / "olist"
RAW_DATABASE = WORKSPACE / "shopanalysis_airflow.duckdb"
AUDIT_DATABASE = WORKSPACE / "shopanalysis_airflow_audit.duckdb"

PROJECT_ROOT = Path("/opt/airflow/shopanalysis")
DBT_PROJECT = PROJECT_ROOT / "dbt"
DBT_PROFILES = Path("/opt/airflow/config")


def run_command(arguments: list[str]) -> None:
    subprocess.run(
        arguments,
        check=True,
        cwd=str(PROJECT_ROOT),
    )


with DAG(
    dag_id="shopanalysis_olist_dev",
    description="Governed Olist ingestion and dbt in isolated development storage",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    max_active_tasks=1,
    is_paused_upon_creation=True,
    default_args={"retries": 0},
    tags=["shopanalysis", "development", "governed"],
) as dag:

    @task
    def validate_sources() -> None:
        from ingestion.landing.olist_csv_to_parquet import (
            load_manifest,
            verify_source,
        )

        manifest = load_manifest(MANIFEST)
        verify_source(SOURCE_DIR, manifest)
        print("OLIST SOURCE VALIDATION: PASS")

    @task
    def land_parquet() -> None:
        run_command([
            sys.executable,
            "-m",
            "ingestion.landing.olist_csv_to_parquet",
            "--source-dir",
            str(SOURCE_DIR),
            "--output-dir",
            str(PARQUET_ROOT),
            "--manifest",
            str(MANIFEST),
        ])

    @task
    def initialize_audit() -> None:
        run_command([
            sys.executable,
            "-m",
            "observability.init_observability_db",
            "--database",
            str(AUDIT_DATABASE),
        ])

    @task
    def ingest_governed_raw() -> None:
        from observability.governed_raw_entrypoint import (
            run_governed_raw_ingestion,
        )

        result = run_governed_raw_ingestion(
            raw_database=RAW_DATABASE,
            audit_database=AUDIT_DATABASE,
            parquet_root=PARQUET_ROOT,
            environment="airflow_dev",
        )

        print("Governed RAW ingestion completed.")
        print(f"Result: {result}")

    @task
    def run_dbt() -> None:
        environment = os.environ.copy()
        environment["DBT_PROFILES_DIR"] = str(DBT_PROFILES)

        dbt_log_path = WORKSPACE / "dbt-logs"
        dbt_target_path = WORKSPACE / "dbt-target"

        dbt_log_path.mkdir(parents=True, exist_ok=True)
        dbt_target_path.mkdir(parents=True, exist_ok=True)

        for command in ("run", "test"):
            subprocess.run(
                [
                    "dbt",
                    command,
                    "--project-dir",
                    str(DBT_PROJECT),
                    "--profiles-dir",
                    str(DBT_PROFILES),
                    "--target",
                    "airflow",
                    "--log-path",
                    str(dbt_log_path),
                    "--target-path",
                    str(dbt_target_path),
                ],
                check=True,
                cwd=str(DBT_PROJECT),
                env=environment,
            )
    validated = validate_sources()
    landed = land_parquet()
    audit_ready = initialize_audit()
    ingested = ingest_governed_raw()
    transformed = run_dbt()

    validated >> landed >> audit_ready >> ingested >> transformed
