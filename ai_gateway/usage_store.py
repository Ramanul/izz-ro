"""Evidența persistentă a consumului (spec secțiunea 6) — SQLite, conexiune per operație.

Fiecare apel scrie un rând; totalurile se agregoarează la interogare. Cheia de timp e
data UTC (string ISO) + luna UTC + epoch — resetele zilnice/lunare ies naturale, fără
cronoare locale Windows (spec secțiunea 7: totul normalizat UTC).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_epoch INTEGER NOT NULL,
  date_utc TEXT NOT NULL,
  ym TEXT NOT NULL,
  provider TEXT NOT NULL,
  quota_group TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  requests INTEGER NOT NULL DEFAULT 0,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cached_tokens INTEGER NOT NULL DEFAULT 0,
  estimated INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_usage_key ON usage (provider, quota_group, date_utc);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_epoch INTEGER NOT NULL,
  date_utc TEXT NOT NULL,
  provider TEXT NOT NULL,
  quota_group TEXT NOT NULL DEFAULT '',
  level TEXT NOT NULL,
  message TEXT NOT NULL
);
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Totals:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    estimated_tokens: int = 0
    exact_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def as_dict(self) -> dict:
        return {
            "requests": self.requests,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "estimated_tokens": self.estimated_tokens,
            "exact_tokens": self.exact_tokens,
            "total_tokens": self.total_tokens,
        }

    def add(self, other: "Totals") -> "Totals":
        return Totals(
            requests=self.requests + other.requests,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            estimated_tokens=self.estimated_tokens + other.estimated_tokens,
            exact_tokens=self.exact_tokens + other.exact_tokens,
        )


@dataclass
class UsageStore:
    path: Path
    now_fn: Callable[[], datetime] = field(default=utc_now)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        if self.path.parent and str(self.path.parent):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # citiri concurente fără blocaje
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def record(self, provider: str, quota_group: str, model: str, *, requests: int = 1,
               input_tokens: int = 0, output_tokens: int = 0, cached_tokens: int = 0,
               estimated: bool = False) -> None:
        now = self.now_fn()
        epoch = int(now.timestamp())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO usage (ts_epoch, date_utc, ym, provider, quota_group, model,"
                " requests, input_tokens, output_tokens, cached_tokens, estimated)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (epoch, now.strftime("%Y-%m-%d"), now.strftime("%Y-%m"), provider,
                 quota_group, model, requests, int(input_tokens), int(output_tokens),
                 int(cached_tokens), 1 if estimated else 0),
            )

    def _sum(self, where: str, params: tuple) -> Totals:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(requests),0) AS requests,"
                " COALESCE(SUM(input_tokens),0) AS input_tokens,"
                " COALESCE(SUM(output_tokens),0) AS output_tokens,"
                " COALESCE(SUM(cached_tokens),0) AS cached_tokens,"
                " COALESCE(SUM(CASE WHEN estimated=1 THEN input_tokens+output_tokens ELSE 0 END),0)"
                "   AS estimated_tokens,"
                " COALESCE(SUM(CASE WHEN estimated=0 THEN input_tokens+output_tokens ELSE 0 END),0)"
                "   AS exact_tokens"
                f" FROM usage WHERE {where}", params).fetchone()
        return Totals(
            requests=int(row["requests"]),
            input_tokens=int(row["input_tokens"]),
            output_tokens=int(row["output_tokens"]),
            cached_tokens=int(row["cached_tokens"]),
            estimated_tokens=int(row["estimated_tokens"]),
            exact_tokens=int(row["exact_tokens"]),
        )

    def totals(self, provider: str, quota_group: str = "", *, scope: str = "daily") -> Totals:
        now = self.now_fn()
        group_sql = "AND quota_group = ?" if quota_group else ""
        params: list = [provider] + ([quota_group] if quota_group else [])
        if scope == "daily":
            params.append(now.strftime("%Y-%m-%d"))
            return self._sum(f"provider = ? {group_sql} AND date_utc = ?", tuple(params))
        if scope == "monthly":
            params.append(now.strftime("%Y-%m"))
            return self._sum(f"provider = ? {group_sql} AND ym = ?", tuple(params))
        if scope == "lifetime":
            return self._sum(f"provider = ? {group_sql}", tuple(params))
        if scope == "window":
            window_end = int(now.timestamp())
            params.append(window_end)
            return self._sum(f"provider = ? {group_sql} AND ts_epoch >= ?", tuple(params))
        raise ValueError(f"scope necunoscut: {scope}")

    def record_alert(self, provider: str, quota_group: str, level: str, message: str) -> None:
        now = self.now_fn()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO alerts (ts_epoch, date_utc, provider, quota_group, level, message)"
                " VALUES (?,?,?,?,?,?)",
                (int(now.timestamp()), now.strftime("%Y-%m-%d"), provider, quota_group,
                 level, message),
            )

    def latest_alert_today(self, provider: str, quota_group: str) -> str | None:
        now = self.now_fn()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT level FROM alerts WHERE provider = ? AND quota_group = ?"
                " AND date_utc = ? ORDER BY id DESC LIMIT 1",
                (provider, quota_group, now.strftime("%Y-%m-%d"))).fetchone()
        return row["level"] if row else None

    def recent_alerts(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts_epoch, provider, quota_group, level, message FROM alerts"
                " ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
