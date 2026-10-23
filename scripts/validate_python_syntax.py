"""Validate Python syntax across ShopAnalysis source and test directories without imports."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = (
    "ingestion", "data_gen", "analytics", "orchestration",
    "observability", "dashboards", "tests", "scripts",
)


def main() -> int:
    files = sorted(
        path
        for directory in SOURCE_DIRS
        for path in (ROOT / directory).rglob("*.py")
        if path.is_file()
    )
    if not files:
        raise RuntimeError("No Python source files discovered")
    failures = []
    for path in files:
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc}")
    if failures:
        raise RuntimeError("Python syntax validation failed:\n" + "\n".join(failures))
    print(f"PASS: Python syntax validation ({len(files)} files in {len(SOURCE_DIRS)} configured directories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
