"""End-to-end tests on a small synthetic CRM, isolated in a temp folder."""

import os
import sqlite3
import subprocess
from pathlib import Path

import duckdb
import pytest
import yaml

from ingestion.extract_load import extract_load
from kpis.validate_kpis import validate
from source.generate_crm import build

ROOT = Path(__file__).resolve().parents[1]


def dbt_build(warehouse: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "WAREHOUSE_PATH": str(warehouse)}
    return subprocess.run(
        ["dbt", "build", "--project-dir", "transform", "--profiles-dir", "transform"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )


@pytest.fixture(scope="module")
def platform(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("platform")
    source, warehouse = tmp / "crm.sqlite", tmp / "warehouse.duckdb"
    build(source, seed=3, n_customers=1500)
    first_load = extract_load(source, warehouse)
    result = dbt_build(warehouse)
    assert result.returncode == 0, result.stdout[-2000:]
    return {"source": source, "warehouse": warehouse, "first_load": first_load}


def q(warehouse, sql):
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def test_first_load_brings_every_table(platform):
    assert all(n > 0 for n in platform["first_load"].values())


def test_statuses_collapse_to_controlled_vocabulary(platform):
    raw = q(platform["warehouse"], "SELECT COUNT(DISTINCT status) FROM raw.crm_appointments")[0][0]
    clean = {r[0] for r in q(platform["warehouse"], "SELECT DISTINCT status FROM certified.fct_appointments")}
    assert raw > 3 and clean == {"completed", "cancelled", "no_show"}


def test_test_accounts_and_duplicates_are_removed(platform):
    wh = platform["warehouse"]
    raw_customers = q(wh, "SELECT COUNT(*) FROM raw.crm_customers")[0][0]
    certified = q(wh, "SELECT COUNT(*), SUM(source_records_merged) FROM certified.dim_customer")[0]
    tests_removed = q(wh, "SELECT COUNT(*) FROM staging.stg_crm__customers WHERE is_test_account")[0][0]
    assert certified[1] == raw_customers - tests_removed  # every real record accounted for
    assert certified[0] < certified[1]  # and duplicates were merged


def test_kpi_bible_validates(platform):
    assert validate(ROOT / "kpis/kpi_bible.yml", ROOT / "transform/target/manifest.json", platform["warehouse"]) == []


def test_kpi_validator_rejects_undefined_columns(platform, tmp_path):
    bible = yaml.safe_load((ROOT / "kpis/kpi_bible.yml").read_text())
    bible["kpis"].append({**bible["kpis"][0], "id": "bogus", "column": "made_up_metric"})
    bible["kpis"].append({**bible["kpis"][0], "id": "raw_read", "source_model": "stg_crm__payments",
                          "column": "amount_cents"})
    path = tmp_path / "bible.yml"
    path.write_text(yaml.safe_dump(bible))
    errors = validate(path, ROOT / "transform/target/manifest.json", platform["warehouse"])
    assert any("made_up_metric" in e for e in errors)
    assert any("not certified" in e for e in errors)


def test_incremental_load_is_idempotent_and_picks_up_changes(platform):
    source, wh = platform["source"], platform["warehouse"]
    assert sum(extract_load(source, wh).values()) == 0  # nothing new, nothing loaded

    con = sqlite3.connect(source)
    con.execute(
        "INSERT INTO payments VALUES (999999, 1, 1, NULL, NULL, 'service', '$1,000.00', "
        "'settled', '2026-06-30 12:00:00', '2099-01-01 00:00:00')"
    )
    con.commit()
    con.close()
    loaded = extract_load(source, wh)
    assert loaded["payments"] == 1 and sum(loaded.values()) == 1

    before = q(wh, "SELECT SUM(amount_cents) FROM certified.fct_payments")[0][0]
    assert dbt_build(wh).returncode == 0  # all tie-out tests still pass
    after = q(wh, "SELECT SUM(amount_cents) FROM certified.fct_payments")[0][0]
    customer_is_test = q(wh, "SELECT is_test_account FROM staging.stg_crm__customers WHERE customer_id = 1")[0][0]
    assert after - before == (0 if customer_is_test else 100000)
