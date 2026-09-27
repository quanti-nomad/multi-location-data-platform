"""Validate the KPI Bible against the certified warehouse and render it as docs.

A KPI passes only if its source model is certified in dbt (meta.certified),
its column is documented on that model, and the column actually exists in
the warehouse. Any failure exits non-zero so the pipeline stops before a
dashboard or AI tool can use an uncertified number.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate(bible_path: Path, manifest_path: Path, warehouse: Path) -> list[str]:
    bible = yaml.safe_load(bible_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    models = {n["name"]: n for n in manifest["nodes"].values() if n["resource_type"] == "model"}
    con = duckdb.connect(str(warehouse), read_only=True)
    errors, seen = [], set()

    for k in bible["kpis"]:
        kid = k["id"]
        if kid in seen:
            errors.append(f"{kid}: duplicate KPI id")
        seen.add(kid)
        node = models.get(k["source_model"])
        if node is None:
            errors.append(f"{kid}: source model '{k['source_model']}' does not exist")
            continue
        if not node["config"].get("meta", {}).get("certified"):
            errors.append(f"{kid}: source model '{k['source_model']}' is not certified")
        if k["column"] not in node.get("columns", {}):
            errors.append(f"{kid}: column '{k['column']}' is not documented on {k['source_model']}")
        cols = {
            r[0]
            for r in con.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ?",
                [node["schema"], node["name"]],
            ).fetchall()
        }
        if k["column"] not in cols:
            errors.append(f"{kid}: column '{k['column']}' not found in {node['schema']}.{node['name']}")
    con.close()
    return errors


def render(bible_path: Path, out: Path) -> None:
    bible = yaml.safe_load(bible_path.read_text())
    rows = "\n".join(
        f"| **{k['name']}** | {k['definition']} | `{k['formula']}` | {k['tier']} | "
        f"`{k['source_model']}.{k['column']}` |"
        for k in bible["kpis"]
    )
    out.write_text(
        "# KPI Bible\n\n"
        "*Generated from `kpis/kpi_bible.yml` on every pipeline run. Do not edit by hand.*\n\n"
        "Every KPI below is validated against the certified warehouse: its source model is "
        "certified, and its column is documented and present.\n\n"
        "| KPI | Definition | Formula | Tier | Source |\n| --- | --- | --- | --- | --- |\n"
        f"{rows}\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bible", default=ROOT / "kpis/kpi_bible.yml", type=Path)
    ap.add_argument("--manifest", default=ROOT / "transform/target/manifest.json", type=Path)
    ap.add_argument("--warehouse", default=ROOT / "data/warehouse.duckdb", type=Path)
    ap.add_argument("--docs", default=ROOT / "docs/kpi_bible.md", type=Path)
    a = ap.parse_args()
    errors = validate(a.bible, a.manifest, a.warehouse)
    if errors:
        print("KPI Bible validation FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    render(a.bible, a.docs)
    n = len(yaml.safe_load(a.bible.read_text())["kpis"])
    print(f"KPI Bible valid: {n} KPIs certified. Docs written to {a.docs.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
