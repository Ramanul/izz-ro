#!/usr/bin/env python3
"""Probe HTTP care nu transformă un challenge sau o eroare în «site sănătos».

Exit: 0 conținut verificat; 1 eroare HTTP/conținut; 2 observare neconcludentă
(challenge dovedit, 403 fără dovezi sau rețea indisponibilă). Un 200 cu pagina
Cloudflare de challenge este tot neconcludent. Manifestul leagă prospețimea de
data articolului, nu de ceasul ultimei randări.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CHALLENGE_MARKS = (b"cf-chl", b"challenge-platform", b"just a moment", b"__cf_chl")
UA = "izz-public-probe/1.0 (+https://izz.ro)"


@dataclass(frozen=True)
class Observation:
    state: str
    detail: str
    status: int = 0

    @property
    def exit_code(self) -> int:
        return {"ok": 0, "error": 1, "unknown": 2}[self.state]


def _is_challenge(headers, body: bytes) -> bool:
    return (str(headers.get("cf-mitigated", "")).lower() == "challenge"
            or any(mark in body[:8192].lower() for mark in CHALLENGE_MARKS))


def classify_response(status: int, headers, body: bytes, *, expect: str = "") -> Observation:
    challenge = _is_challenge(headers, body)
    if challenge and status in {200, 403, 503}:
        return Observation("unknown", f"HTTP {status}: challenge anti-bot, nu conținut verificat", status)
    if status == 403:
        return Observation("unknown", "HTTP 403 fără dovadă de challenge: acces neconfirmat", status)
    if not 200 <= status < 300:
        return Observation("error", f"HTTP {status}", status)
    if expect and expect.casefold() not in body.decode("utf-8", "replace").casefold():
        return Observation("error", f"HTTP {status}: markerul de conținut {expect!r} lipsește", status)
    return Observation("ok", f"HTTP {status}: conținut verificat", status)


def fetch(url: str, *, expect: str = "", timeout: float = 25) -> Observation:
    request = Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    try:
        with urlopen(request, timeout=timeout) as response:  # nosec B310 - URL explicit de monitorizare
            return classify_response(response.status, response.headers, response.read(2_000_000), expect=expect)
    except HTTPError as exc:
        try:
            body = exc.read(2_000_000)
        except Exception:
            body = b""
        return classify_response(exc.code, exc.headers or {}, body, expect=expect)
    except (URLError, OSError, TimeoutError) as exc:
        return Observation("unknown", f"rețea indisponibilă ({type(exc).__name__}: {exc})")


def content_freshness(manifest: dict, *, now: datetime | None = None,
                      max_age_hours: float = 48) -> Observation:
    if not isinstance(manifest, dict):
        return Observation("error", "manifestul nu este un obiect JSON")
    raw = manifest.get("latest_article")
    if not isinstance(raw, str) or not raw:
        return Observation("error", "manifest fără latest_article: prospețimea nu e dovedită")
    try:
        latest = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return Observation("error", f"latest_article invalid: {raw!r}")
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    age = ((now or datetime.now(timezone.utc)) - latest).total_seconds() / 3600
    if age < -5 / 60:
        return Observation("error", "latest_article este în viitor")
    if age > max_age_hours:
        return Observation("error", f"conținut înghețat: ultimul articol are {age:.1f}h (prag {max_age_hours:g}h)")
    return Observation("ok", f"ultimul articol: {raw} ({age:.1f}h)")


def probe_site(base: str, *, max_age_hours: float = 48) -> Observation:
    home = fetch(base.rstrip("/") + "/", expect="IZZ.ro")
    if home.state != "ok":
        return home
    request = Request(base.rstrip("/") + "/build.json", headers={"User-Agent": UA})
    try:
        with urlopen(request, timeout=25) as response:  # nosec B310 - aceeași origine configurată
            body = response.read(2_000_000)
            checked = classify_response(response.status, response.headers, body, expect="latest_article")
            if checked.state != "ok":
                return checked
            manifest = json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        return classify_response(exc.code, exc.headers or {}, exc.read(2_000_000))
    except (URLError, OSError, ValueError) as exc:
        return Observation("unknown", f"manifest indisponibil ({type(exc).__name__}: {exc})")
    return content_freshness(manifest, max_age_hours=max_age_hours)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    parser.add_argument("--max-age-hours", type=float, default=48)
    args = parser.parse_args()
    result = probe_site(args.base, max_age_hours=args.max_age_hours)
    print(f"{result.state.upper()}: {args.base}: {result.detail}")
    return result.exit_code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
