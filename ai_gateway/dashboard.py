"""Dashboard-ul de cotă (spec secțiunile 6, 18) — tabel HTML + tabel text pentru CLI.

Fiecare rând: Provider | Model | Status | Used | Remaining | Reset | Safety | Billing.
"""
from __future__ import annotations

from ai_gateway.usage_store import Totals

_HTML_SHELL = """<!doctype html>
<html lang="ro"><head><meta charset="utf-8">
<title>FreeQuotaGuard — cotă AI</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #111; color: #eee; }}
 h1 {{ font-size: 1.2rem; }}
 table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
 th, td {{ border: 1px solid #444; padding: 0.35rem 0.6rem; text-align: left; }}
 th {{ background: #222; }}
 .BLOCKED {{ color: #ff6b6b; font-weight: 700; }}
 .HIGH {{ color: #ffb347; }}
 .WARNING {{ color: #ffe066; }}
 .FREE {{ color: #7bd88f; }}
 .NO_KEY, .DISABLED, .UNVERIFIED, .CAUTION, .FREE_QUOTA_DISABLED, .NOT_ALLOWED {{ color: #999; }}
 .alerts {{ margin-top: 1.5rem; font-size: 0.85rem; }}
</style></head><body>
<h1>FreeQuotaGuard — cote AI (totul UTC)</h1>
<p>free_only: {free_only} · openai_free_only: {openai_free_only} · dry_run: {dry_run}</p>
<table><thead><tr><th>Provider</th><th>Model</th><th>Status</th><th>Used</th>
<th>Remaining</th><th>Reset</th><th>Safety</th><th>Billing</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="alerts"><h2>Alerte recente</h2>{alerts}</div>
</body></html>"""


def _fmt_tokens(value: int | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def _used_str(used: Totals) -> str:
    base = f"{_fmt_tokens(used.total_tokens)}"
    detail = f" ({_fmt_tokens(used.estimated_tokens)} est.)" if used.estimated_tokens else ""
    req = f" · {used.requests} req" if used.requests else ""
    return base + detail + req


def dashboard_rows(status_rows: list[dict]) -> list[list[str]]:
    rows = []
    for r in status_rows:
        remaining = "n/a" if r["remaining"] is None else _fmt_tokens(r["remaining"])
        safety = "—" if not r["safe_limit"] else (
            f"{_fmt_tokens(r['safe_limit'])} (−{r['margin']:.0%})")
        rows.append([
            r["provider"], r["model"], r["status"], _used_str(r["used"]),
            remaining, r["reset"], safety,
            "POSIBIL (protejat)" if r["billing_possible"] else "IMPOSIBIL",
        ])
    return rows


def render_dashboard_html(status_rows: list[dict], alerts: list[dict],
                          settings=None) -> str:
    rows_html = []
    for cells in dashboard_rows(status_rows):
        css = cells[2]  # coloana Status primește clasa CSS cu același nume
        tds = "".join(f'<td class="{css if i == 2 else ""}">{c}</td>' for i, c in enumerate(cells))
        rows_html.append(f"<tr>{tds}</tr>")
    alerts_html = ("<ul>" + "".join(
        f"<li>[{a['level']}] {a['provider']}: {a['message']}</li>" for a in alerts) + "</ul>") \
        if alerts else "<p>nicio alertă</p>"
    flags = {
        "free_only": getattr(settings, "global_free_only", "?"),
        "openai_free_only": getattr(settings, "openai_free_only", "?"),
        "dry_run": getattr(settings, "dry_run", "?"),
    }
    return _HTML_SHELL.format(rows="".join(rows_html), alerts=alerts_html, **flags)


def render_status_text(status_rows: list[dict], alerts: list[dict], settings=None) -> str:
    lines = ["", "FreeQuotaGuard — cotă AI (UTC)", "=" * 78]
    header = (f"{'Provider':<22} {'Model':<34} {'Status':<18} {'Used':>10} "
              f"{'Remaining':>10}")
    lines.append(header)
    lines.append("-" * len(header))
    for r in status_rows:
        used = r["used"]
        used_s = _fmt_tokens(used.total_tokens) + ("e" if used.estimated_tokens else "")
        remaining = "n/a" if r["remaining"] is None else _fmt_tokens(r["remaining"])
        lines.append(f"{r['provider']:<22} {r['model']:<34} {r['status']:<18} "
                     f"{used_s:>10} {remaining:>10}")
    lines.append("")
    totals = Totals()
    for r in status_rows:
        totals = totals.add(r["used"])
    lines.append(f"TOTAL AZI: {totals.total_tokens} tokeni "
                 f"(in {totals.input_tokens} / out {totals.output_tokens} / "
                 f"cache {totals.cached_tokens} / estimat {totals.estimated_tokens}), "
                 f"{totals.requests} cereri")
    if alerts:
        lines.append("")
        lines.append("Alerte:")
        for a in alerts:
            lines.append(f"  [{a['level']}] {a['provider']}: {a['message']}")
    if getattr(settings, "dry_run", False):
        lines.append("")
        lines.append("DRY_RUN este ACTIV — nimic nu pleacă spre provideri.")
    lines.append("")
    return "\n".join(lines)
