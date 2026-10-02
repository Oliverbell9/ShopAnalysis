from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

DEFAULT_SOURCE = Path("data/raw/olist")
DEFAULT_OUTPUT = Path("data/parquet/olist")
DEFAULT_MANIFEST = Path("data/manifests/olist_manifest.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_source(source_dir: Path, manifest: dict) -> None:
    expected = {
        entry["file_name"]: entry
        for entry in manifest["files"]
    }

    physical = {
        path.name: path
        for path in source_dir.glob("*.csv")
    }

    if set(expected) != set(physical):
        missing = sorted(set(expected) - set(physical))
        unexpected = sorted(set(physical) - set(expected))

        raise RuntimeError(
            "Source inventory mismatch. "
            f"Missing={missing}; Unexpected={unexpected}"
        )

    for file_name, entry in expected.items():
        path = physical[file_name]

        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)

        if actual_size != entry["size_bytes"]:
            raise RuntimeError(
                f"Size mismatch for {file_name}: "
                f"expected={entry['size_bytes']}, actual={actual_size}"
            )

        if actual_hash.lower() != entry["sha256"].lower():
            raise RuntimeError(
                f"SHA256 mismatch for {file_name}: "
                f"expected={entry['sha256']}, actual={actual_hash}"
            )


def deterministic_batch_id(manifest: dict) -> str:
    source_fingerprint = "|".join(
        f"{entry['file_name']}:{entry['sha256']}"
        for entry in sorted(
            manifest["files"],
            key=lambda x: x["file_name"],
        )
    )

    digest = hashlib.sha256(
        source_fingerprint.encode("utf-8")
    ).hexdigest()

    return f"olist_{digest[:16]}"


def convert_file(
    csv_path: Path,
    parquet_path: Path,
    batch_id: str,
    loaded_at: datetime,
) -> dict:
    df = pd.read_csv(
        csv_path,
        encoding="utf-8-sig",
    )

    source_columns = list(df.columns)

    df["_source_file"] = csv_path.name
    df["_file_row_number"] = range(1, len(df) + 1)
    df["_loaded_at"] = loaded_at
    df["_batch_id"] = batch_id

    table = pa.Table.from_pandas(
        df,
        preserve_index=False,
    )

    parquet_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pq.write_table(
        table,
        parquet_path,
        compression="snappy",
    )

    return {
        "source_file": csv_path.name,
        "parquet_file": parquet_path.name,
        "rows": len(df),
        "source_columns": len(source_columns),
        "output_columns": len(df.columns),
        "parquet_bytes": parquet_path.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert immutable Olist CSV source files into "
            "lineage-enriched Parquet landing files."
        )
    )

    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )

    args = parser.parse_args()

    manifest = load_manifest(args.manifest)

    verify_source(
        args.source_dir,
        manifest,
    )

    batch_id = deterministic_batch_id(manifest)
    loaded_at = datetime.now(timezone.utc)

    temporary_output = args.output_dir.parent / (
        f".{args.output_dir.name}.tmp"
    )

    if temporary_output.exists():
        shutil.rmtree(temporary_output)

    temporary_output.mkdir(
        parents=True,
        exist_ok=False,
    )

    results = []

    try:
        for csv_path in sorted(
            args.source_dir.glob("*.csv")
        ):
            parquet_path = temporary_output / (
                f"{csv_path.stem}.parquet"
            )

            result = convert_file(
                csv_path=csv_path,
                parquet_path=parquet_path,
                batch_id=batch_id,
                loaded_at=loaded_at,
            )

            results.append(result)

        if args.output_dir.exists():
            shutil.rmtree(args.output_dir)

        temporary_output.replace(args.output_dir)

    except Exception:
        if temporary_output.exists():
            shutil.rmtree(temporary_output)

        raise

    print("OLIST PARQUET LANDING: PASS")
    print(f"Batch ID:       {batch_id}")
    print(f"Loaded at UTC:  {loaded_at.isoformat()}")
    print(f"Files written:  {len(results)}")
    print(
        "Rows written:   "
        f"{sum(x['rows'] for x in results):,}"
    )

    print()
    print(
        f"{'FILE':45} "
        f"{'ROWS':>12} "
        f"{'COLS':>6} "
        f"{'PARQUET BYTES':>15}"
    )
    print("-" * 82)

    for result in results:
        print(
            f"{result['parquet_file']:45} "
            f"{result['rows']:12,} "
            f"{result['output_columns']:6} "
            f"{result['parquet_bytes']:15,}"
        )


if __name__ == "__main__":
    main()
