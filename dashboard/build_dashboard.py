"""Build the executive dashboard from the certified KPI table only.

Outputs:
  docs/dashboard.html            self-contained, interactive (Chart.js from CDN)
  docs/img/dashboard_preview.png static preview for the README
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

QUERY = """
select location_id, location_name, brand, ownership, strftime(month_start, '%Y-%m') as month,
       net_revenue, membership_revenue, service_revenue, appointments_scheduled, completed_visits, no_shows,
       active_members, new_members, churned_members, leads, converted_leads, lead_conversion_rate
from metrics.kpi_location_monthly
order by month, location_id
"""

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executive Overview - Certified KPIs</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1" integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ" crossorigin="anonymous"></script>
<style>
:root{--bg:#f4f6f8;--card:#fff;--ink:#1d2733;--muted:#5d6b7a;--head:#1f4e5f;--pos:#1a7f4b;--neg:#b3261e;--gap:16px;--r:10px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);padding:24px}
.wrap{max-width:1280px;margin:0 auto}
header{background:var(--head);color:#fff;padding:18px 24px;border-radius:var(--r);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:var(--gap)}
header h1{font-size:19px;font-weight:600}header p{font-size:12px;opacity:.75;margin-top:2px}
select{padding:6px 10px;border-radius:6px;border:1px solid rgba(255,255,255,.3);background:rgba(255,255,255,.12);color:#fff;font-size:13px}
select option{color:#000}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:var(--gap);margin-bottom:var(--gap)}
.card{background:var(--card);border-radius:var(--r);padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.value{font-size:28px;font-weight:700;margin:4px 0}
.chg{font-size:13px;font-weight:500}.pos{color:var(--pos)}.neg{color:var(--neg)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:var(--gap);margin-bottom:var(--gap)}
h3{font-size:14px;margin-bottom:12px}canvas{max-height:300px}
.tbl{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:9px 10px;border-bottom:2px solid #dde3e8;color:var(--muted);font-size:12px;text-transform:uppercase;cursor:pointer;white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid #eef1f4}tr:hover td{background:#f8fafb}
td.n{text-align:right;font-variant-numeric:tabular-nums}th.n{text-align:right}
footer{font-size:12px;color:var(--muted);margin-top:14px}
@media(max-width:700px){.charts{grid-template-columns:1fr}}
</style>
</head>
<body><div class="wrap">
<header>
  <div><h1>Executive Overview</h1><p>Certified KPIs &middot; synthetic data for a fictional two-brand clinic chain</p></div>
  <label>Brand&nbsp; <select id="brand"><option value="All">All brands</option></select></label>
</header>
<section class="kpis">
  <div class="card"><div class="label">Net revenue, <span class="lm"></span></div><div class="value" id="k-rev"></div><div class="chg" id="k-rev-c"></div></div>
  <div class="card"><div class="label">Active members</div><div class="value" id="k-mem"></div><div class="chg" id="k-mem-c"></div></div>
  <div class="card"><div class="label">Member churn rate</div><div class="value" id="k-churn"></div><div class="chg" id="k-churn-c"></div></div>
  <div class="card"><div class="label">No-show rate</div><div class="value" id="k-ns"></div><div class="chg" id="k-ns-c"></div></div>
</section>
<section class="charts">
  <div class="card"><h3>Net revenue by month</h3><canvas id="c-rev"></canvas></div>
  <div class="card"><h3>Active members by month</h3><canvas id="c-mem"></canvas></div>
</section>
<section class="card tbl"><h3>Location leaderboard, <span class="lm"></span></h3>
  <table><thead><tr>
    <th data-k="location_name">Location</th><th data-k="brand">Brand</th><th data-k="ownership">Ownership</th>
    <th class="n" data-k="net_revenue">Net revenue</th><th class="n" data-k="active_members">Members</th>
    <th class="n" data-k="member_churn_rate">Churn</th><th class="n" data-k="lead_conversion_rate">Lead conv.</th>
  </tr></thead><tbody id="rows"></tbody></table>
</section>
<footer>Source: <code>metrics.kpi_location_monthly</code> (certified, tier: board). Definitions: docs/kpi_bible.md.</footer>
</div>
<script>
const DATA = __DATA__;
const $ = id => document.getElementById(id);
const usd = v => v >= 1e6 ? '$' + (v/1e6).toFixed(2) + 'M' : v >= 1e3 ? '$' + (v/1e3).toFixed(1) + 'K' : '$' + v.toFixed(0);
const pct = v => (v * 100).toFixed(1) + '%';
const months = [...new Set(DATA.map(r => r.month))].sort();
const last = months[months.length - 1], prev = months[months.length - 2];
document.querySelectorAll('.lm').forEach(e => e.textContent = last);
[...new Set(DATA.map(r => r.brand))].sort().forEach(b => $('brand').add(new Option(b, b)));
let charts = {}, sortKey = 'net_revenue', sortDir = -1;

function agg(rows) {
  const s = k => rows.reduce((a, r) => a + (r[k] || 0), 0);
  const start = s('active_members') - s('new_members'), sched = s('appointments_scheduled');
  return {rev: s('net_revenue'), mem_rev: s('membership_revenue'), svc_rev: s('service_revenue'), mem: s('active_members'),
          churn: start > 0 ? s('churned_members') / start : 0, ns: sched > 0 ? s('no_shows') / sched : 0};
}
function card(id, now, before, fmt, goodUp) {
  $(id).textContent = fmt(now);
  let d = before ? (now - before) / before : 0; if (Math.abs(d) < 0.0005) d = 0;
  const up = d >= 0, good = d === 0 || up === goodUp;
  $(id + '-c').textContent = (up ? '+' : '') + (d * 100).toFixed(1) + '% vs ' + prev;
  $(id + '-c').className = 'chg ' + (good ? 'pos' : 'neg');
}
function render() {
  const b = $('brand').value, rows = DATA.filter(r => b === 'All' || r.brand === b);
  const byMonth = months.map(m => agg(rows.filter(r => r.month === m)));
  const L = byMonth[byMonth.length - 1], P = byMonth[byMonth.length - 2];
  card('k-rev', L.rev, P.rev, usd, true); card('k-mem', L.mem, P.mem, v => v.toLocaleString(), true);
  card('k-churn', L.churn, P.churn, pct, false); card('k-ns', L.ns, P.ns, pct, false);
  const ds = (label, data, color) => ({label, data, backgroundColor: color, borderColor: color});
  const revData = {labels: months, datasets: [ds('Membership', byMonth.map(x => x.mem_rev), '#1f4e5f'), ds('Service', byMonth.map(x => x.svc_rev), '#6fa8b8')]};
  const memData = {labels: months, datasets: [{...ds('Active members', byMonth.map(x => x.mem), '#1f4e5f'), tension: .3, fill: false}]};
  const opts = (stacked, money) => ({responsive: true, animation: false, plugins: {legend: {position: 'bottom'}},
    scales: {x: {stacked}, y: {stacked, beginAtZero: true, ticks: {callback: v => money ? usd(v) : v.toLocaleString()}}}});
  if (charts.rev) { charts.rev.data = revData; charts.rev.update('none'); charts.mem.data = memData; charts.mem.update('none'); }
  else { charts.rev = new Chart($('c-rev'), {type: 'bar', data: revData, options: opts(true, true)});
         charts.mem = new Chart($('c-mem'), {type: 'line', data: memData, options: opts(false, false)}); }
  const t = rows.filter(r => r.month === last).map(r => ({...r,
    member_churn_rate: (r.active_members - r.new_members) > 0 ? r.churned_members / (r.active_members - r.new_members) : 0}));
  t.sort((a, c) => (a[sortKey] > c[sortKey] ? 1 : -1) * sortDir);
  $('rows').innerHTML = t.map(r => `<tr><td>${r.location_name}</td><td>${r.brand}</td><td>${r.ownership}</td>
    <td class="n">${usd(r.net_revenue)}</td><td class="n">${r.active_members}</td>
    <td class="n">${pct(r.member_churn_rate)}</td><td class="n">${r.lead_conversion_rate != null ? pct(r.lead_conversion_rate) : '-'}</td></tr>`).join('');
}
document.querySelectorAll('th').forEach(th => th.onclick = () => {
  const k = th.dataset.k; sortDir = sortKey === k ? -sortDir : -1; sortKey = k; render(); });
$('brand').onchange = render;
render();
</script>
</body></html>
"""


def build(warehouse: Path = ROOT / "data/warehouse.duckdb", docs: Path = ROOT / "docs") -> None:
    con = duckdb.connect(str(warehouse), read_only=True)
    df = con.execute(QUERY).df()
    con.close()
    records = json.loads(df.to_json(orient="records"))
    (docs / "dashboard.html").write_text(HTML.replace("__DATA__", json.dumps(records)))

    # --- static preview -----------------------------------------------------
    (docs / "img").mkdir(parents=True, exist_ok=True)
    m = df.groupby(["month", "brand"], as_index=False)[
        ["net_revenue", "active_members", "churned_members", "new_members"]
    ].sum()
    colors = {"Vitality Clinics": "#1f4e5f", "Lumen Wellness": "#6fa8b8"}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for brand, g in m.groupby("brand"):
        axes[0].plot(g["month"], g["net_revenue"] / 1e3, label=brand, color=colors[brand], lw=2)
        axes[1].plot(g["month"], g["active_members"], label=brand, color=colors[brand], lw=2)
        start = (g["active_members"] - g["new_members"]).where(lambda s: s >= 100)
        axes[2].plot(g["month"], g["churned_members"] / start * 100, label=brand, color=colors[brand], lw=2)
    for ax, title, unit in zip(axes, ["Net revenue", "Active members", "Member churn rate"], ["$K", "members", "%"]):
        ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color="#1d2733")
        ax.set_ylabel(unit, color="#5d6b7a")
        ax.tick_params(axis="x", rotation=60, labelsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("Certified KPIs by brand (synthetic data)", x=0.01, ha="left", fontsize=13, color="#1f4e5f")
    fig.tight_layout()
    fig.savefig(docs / "img/dashboard_preview.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    build()
    print("Dashboard written to docs/dashboard.html and docs/img/dashboard_preview.png")
