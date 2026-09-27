"""Extract CRM tables and load them into the warehouse raw layer.

This replaces the manual step of exporting CRM reports to Excel. It is:

- incremental: only rows changed since the last run (per-table watermark)
- idempotent: re-running with no source changes loads nothing and changes nothing
- auditable: every batch is logged with row counts, and every raw row carries
  its batch id and load time

Raw tables are loaded as-is (no cleaning). Cleaning happens in the dbt
staging layer, so the raw layer always matches what the source actually said.
"""

from __future__ import annotations

import argparse
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

TABLES = {
    "locations": "location_id",
    "customers": "customer_id",
    "services": "service_id",
    "memberships": "membership_id",
    "appointments": "appointment_id",
    "payments": "payment_id",
    "leads": "lead_id",
}


def _ensure_meta(wh: duckdb.DuckDBPyConnection) -> None:
    wh.execute("CREATE SCHEMA IF NOT EXISTS raw")
    wh.execute("CREATE SCHEMA IF NOT EXISTS meta")
    wh.execute(
        "CREATE TABLE IF NOT EXISTS meta.load_watermarks "
        "(table_name VARCHAR PRIMARY KEY, high_watermark VARCHAR)"
    )
    wh.execute(
        "CREATE TABLE IF NOT EXISTS meta.load_log (batch_id VARCHAR, table_name VARCHAR, "
        "rows_loaded BIGINT, high_watermark VARCHAR, loaded_at TIMESTAMP)"
    )


def extract_load(source: Path, warehouse: Path) -> dict[str, int]:
    src = sqlite3.connect(source)
    wh = duckdb.connect(str(warehouse))
    _ensure_meta(wh)
    batch_id = uuid.uuid4().hex[:12]
    loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    results = {}

    for table, pk in TABLES.items():
        row = wh.execute(
            "SELECT high_watermark FROM meta.load_watermarks WHERE table_name = ?", [table]
        ).fetchone()
        watermark = row[0] if row else ""
        df = pd.read_sql_query(
            f"SELECT * FROM {table} WHERE updated_at > ? ORDER BY updated_at", src, params=[watermark]
        )
        # Keep every source column as text in raw; typing is a staging concern.
        df = df.astype("string")
        df["_batch_id"] = batch_id
        df["_loaded_at"] = loaded_at
        target = f"raw.crm_{table}"

        if len(df):
            exists = wh.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'raw' AND table_name = ?", [f"crm_{table}"]
            ).fetchone()[0]
            wh.register("incoming", df)
            if not exists:
                wh.execute(f"CREATE TABLE {target} AS SELECT * FROM incoming")
            else:
                # upsert: replace any existing versions of the incoming keys
                wh.execute(f"DELETE FROM {target} WHERE {pk} IN (SELECT {pk} FROM incoming)")
                wh.execute(f"INSERT INTO {target} SELECT * FROM incoming")
            wh.unregister("incoming")
            new_mark = str(df["updated_at"].max())
            wh.execute(
                "INSERT OR REPLACE INTO meta.load_watermarks VALUES (?, ?)", [table, new_mark]
            )
        else:
            new_mark = watermark

        wh.execute(
            "INSERT INTO meta.load_log VALUES (?, ?, ?, ?, ?)",
            [batch_id, table, len(df), new_mark, loaded_at],
        )
        results[table] = len(df)

    src.close()
    wh.close()
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="data/crm.sqlite")
    ap.add_argument("--warehouse", default="data/warehouse.duckdb")
    a = ap.parse_args()
    for t, n in extract_load(Path(a.source), Path(a.warehouse)).items():
        print(f"{t:<14}{n:>8,} rows")
