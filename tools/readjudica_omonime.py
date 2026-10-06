#!/usr/bin/env python
"""Re-adjudica cu photojudge omonimele marcate de auditul portretelor.

Auditul (tools/audit_portrete_omonime.py) a identificat numele cu >=2 candidati
foto-worthy al caror qid din cache coincide mereu cu candidatul cel mai celebru
(logica veche pe faima, clasa de risc JFK). Acest tool le trece prin
generator.photojudge.pick_candidate cu contextul primului articol care-i
mentioneaza azi si aplica rezultatul in data/portraits.json:

  - pick == qid din cache          -> OK, nemodificat (confirmat de judecator)
  - pick == alt candidat           -> cache + imagine rescrise cu noul candidat
  - pick == -1 (neclar)            -> NEMODIFICAT (doar raportat: stergerea ar
                                      pierde poze legitime pe contextul unui
                                      singur articol incidental; cache-ul e
                                      per-nume, contextul per-articol)
  - numele nu mai apare in articole -> SARIT (fara context nu judecam; raportat)

  python tools/readjudica_omonime.py --dry-run          # doar verdict, nimic scris
  python tools/readjudica_omonime.py                    # aplica in cache + imagini

Env: cheile AI din .env (Gemini implicit). Budget: 1 apel AI per nume omonim.
"""
import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from generator import photojudge, state  # noqa: E402
from generator.process import get_provider  # noqa: E402
from tools.fetch_portraits import (  # noqa: E402
    CACHE, OUTDIR, commons_info, norm, slugish, _worthy_candidates,
)

REPORT = os.path.join(ROOT, "notes", "audit-portrete-omonime-2026-10-06.md")


def names_din_raport(path: str) -> list:
    """Numele omonime din raportul de audit (anteturile `### ` din lista finala)."""
    text = open(path, encoding="utf-8").read()
    bloc = text.split("## Lista omonimelor", 1)[-1]
    return [m.group(1).strip() for m in re.finditer(r"^### (.+)$", bloc, re.M)]


def context_din_articole(arts: list) -> dict:
    """nume -> (titlu, teaser) ale PRIMULUI articol care-l mentioneaza (aceaasi
    regula ca in fetch_portraits.main)."""
    ctx: dict = {}
    for a in arts:
        for e in a.get("entities") or []:
            if e and e not in ctx and len(e.split()) >= 2:
                ctx[e] = (a.get("title") or "", a.get("teaser") or "")
    return ctx


def load_env() -> None:
    """Incarca .env (cheile AI) daca exista — aceeasi semantica ca in CI."""
    env = os.path.join(ROOT, ".env")
    if not os.path.exists(env):
        return
    for line in open(env, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(
        ROOT, "notes", "readjudicare-omonime-raport.md"))
    args = ap.parse_args()

    names = names_din_raport(args.report)
    if args.limit:
        names = names[:args.limit]
    cache = json.load(open(CACHE, encoding="utf-8"))
    ctx = context_din_articole(state.load())
    load_env()
    provider = get_provider()
    print(f">> {len(names)} omonime de re-adjudicat; provider {type(provider).__name__}; "
          f"{'DRY-RUN' if args.dry_run else 'APLIC'}")

    schimbat, confirmat, neclar, fara_ctx, erori = [], [], [], [], []
    for i, name in enumerate(names, 1):
        key = norm(name)
        entry = cache.get(key)
        if entry is None:
            erori.append((name, "lipsa din cache (key diferita)"))
            continue
        title, summary = ctx.get(name, ("", ""))
        if not title:
            fara_ctx.append(name)
            continue
        verdict = "(eroare)"
        try:
            worthy = _worthy_candidates(name)
            if len(worthy) < 2:
                # intre timp un singur candidat: decizia e determinata; daca difera
                # de cache, aplic direct (nu mai e nevoie de judecator)
                if worthy and worthy[0][0] != entry.get("qid"):
                    idx, verdict = 0, "determinat-intre-timp"
                elif worthy:
                    confirmat.append((name, entry.get("qid"), "singur candidat azi"))
                    continue
                else:
                    neclar.append((name, "fara candidati azi"))
                    idx, verdict = -1, "fara candidati azi"   # ramane nemodificat
            else:
                # apel vizibil (pick_candidate inghite erorile in -1): o eroare de
                # API nu are voie sa para "neclar" si sa stearga un portret bun
                raw = provider.complete(photojudge._SYSTEM_PICK,
                                        photojudge.build_pick_user(
                                            title, summary,
                                            [d for _, _, d in worthy]))
                idx = photojudge.parse_pick(raw)
                idx = idx if 0 <= idx < len(worthy) else -1
                verdict = f"photojudge idx={idx}"
            if idx == -1:
                # neclar pe contextul articolului actual: NU stergem portretul —
                # cache-ul e per-nume iar contextul per-articol (limitare cunoscuta,
                # Sarcina E pas 3); stergerea ar pierde poze legitime pe baza
                # unui singur articol incidental. Ramane nemodificat, doar raportat.
                neclar.append((name, verdict))
            elif worthy[idx][0] == entry.get("qid"):
                confirmat.append((name, entry.get("qid"), verdict))
            else:
                schimbat.append((name, entry.get("qid"), worthy[idx][0], verdict,
                                 title))
                if not args.dry_run:
                    info = commons_info(worthy[idx][1])
                    if info and info.get("thumb"):
                        fn = f"{slugish(name)}.jpg"
                        import urllib.request
                        UA = {"User-Agent": "izz.ro-portraits/1.0 (contact@izz.ro)"}
                        data = urllib.request.urlopen(
                            urllib.request.Request(info["thumb"], headers=UA),
                            timeout=30).read()
                        if len(data) > 2000:
                            open(os.path.join(OUTDIR, fn), "wb").write(data)
                            cache[key] = {"name": name, "qid": worthy[idx][0],
                                          "img": f"portraits/{fn}",
                                          "artist": info["artist"],
                                          "license": info["license"],
                                          "page": info["page"]}
                        else:
                            cache[key] = {"miss": True,
                                          "why": "omonim: imagine prea mica"}
                    else:
                        cache[key] = {"miss": True,
                                      "why": "omonim: resursa fara imagine libera"}
        except Exception as exc:
            erori.append((name, str(exc)))
        print(f"  [{i}/{len(names)}] {name}: {verdict}", flush=True)
        time.sleep(1)   # politete API Wikidata

    print(f">> rezultat: {len(schimbat)} schimbate, {len(confirmat)} confirmate, "
          f"{len(neclar)} neclar (nemodificate), {len(fara_ctx)} fara context, "
          f"{len(erori)} erori")
    if not args.dry_run:
        json.dump(cache, open(CACHE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
    _raport(args, schimbat, confirmat, neclar, fara_ctx, erori)
    return 0


def _raport(args, schimbat, confirmat, neclar, fara_ctx, erori) -> None:
    from datetime import datetime, timezone
    lines = [
        "# Re-adjudicare omonime portrete — raport",
        f"*Generat: {datetime.now(timezone.utc).isoformat(timespec='seconds')} · "
        f"{'DRY-RUN (nimic aplicat)' if args.dry_run else 'APLICAT in cache'} · "
        "judecator: generator/photojudge.pick_candidate pe contextul primului articol*",
        "",
        f"- Schimbate (qid nou + imagine noua): **{len(schimbat)}**",
        f"- Confirmate (photojudge a ales acelasi candidat): {len(confirmat)}",
        f"- Neclar -> fara portret: {len(neclar)}",
        f"- Fara context in articolele actuale (sarite, nemodificate): {len(fara_ctx)}",
        f"- Erori: {len(erori)}",
        "",
    ]
    if schimbat:
        lines += ["## Schimbari", ""]
        for name, old, new, verdict, title in schimbat:
            lines.append(f"- **{name}**: `{old}` → `{new}` ({verdict}) — «{title[:80]}»")
    if neclar:
        lines += ["", "## Neclar (nemodificate — fara verdict sigur pe contextul actual)", ""]
        for name, v in neclar:
            lines.append(f"- {name} ({v})")
    if fara_ctx:
        lines += ["", "## Fara context (sarite)", ""]
        lines += [f"- {n}" for n in fara_ctx]
    if erori:
        lines += ["", "## Erori", ""]
        lines += [f"- {n}: {v}" for n, v in erori]
    outp = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    open(outp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f">> raport: {outp}")


if __name__ == "__main__":
    sys.exit(main())
