#!/usr/bin/env python
"""Audit REPORT-ONLY: rata de ambiguitate a deciziilor de portret din cache.

Pentru fiecare intrare cu qid din data/portraits.json (o decizie catre o
entitate Wikidata), re-deriveaza candidatii cu nume exact identic si numara
cati sunt foto-worthy. 0-1 candidati => decizia era determinata (sigura).
>=2 => omonim: alegerea din cache poate fi gresita daca a fost luata de
logica veche pe faima (inainte de PR #439). Nu scrie nimic in cache, nu
descarca imagini — doar raport MD pe stdout sau in fisier.

  python tools/audit_portrete_omonime.py [--input data/portraits.json]
                                         [--out notes/raport.md] [--sleep 0.2]
                                         [--limit N]

Env: none. Iesire 0 = audit efectuat (inclusiv cu erori partiale raportate).
"""
import argparse
import importlib.util
import json
import os
import sys
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_fetch_portraits():
    """Incarca tools/fetch_portraits.py ca modul (reutilizeaza EXACT aceeasi
    logica de candidati ca pipeline-ul, fara duplicare)."""
    path = os.path.join(ROOT, "tools", "fetch_portraits.py")
    spec = importlib.util.spec_from_file_location("fetch_portraits", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, ROOT)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(ROOT, "data", "portraits.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--state", default=os.path.join(ROOT, "build", "tmp",
                                                   "audit-portrete-state.jsonl"))
    args = ap.parse_args()

    fp = _load_fetch_portraits()
    with open(args.input, encoding="utf-8") as f:
        cache = json.load(f)

    hits = [(k, v) for k, v in cache.items()
            if not v.get("miss") and v.get("qid") and v.get("name")]
    if args.limit:
        hits = hits[:args.limit]

    unambig = 0            # 0-1 candidati foto-worthy: decizia era determinata
    omonime: list = []     # >=2 candidati foto-worthy: alegere posibila gresita
    zero_acum = []         # cached hit care azi n-ar mai avea candidat foto-worthy
    erori = 0
    t0 = time.time()

    def _classify(item):
        """Clasifica un nume, cu backoff pe 429 (Wikimedia rate limit):
        30s, 60s, 120s — apoi renunta si il marcheaza eroare."""
        key, entry = item
        name = entry["name"]
        delay = 30
        for attempt in range(4):
            try:
                worthy = fp._worthy_candidates(name)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == 3:
                    return ("eroare", name, f"HTTP {exc.code}", entry["qid"])
                print(f"  .. 429 la {name}, backoff {delay}s", flush=True)
                time.sleep(delay)
                delay *= 2
            except Exception as exc:
                return ("eroare", name, str(exc), entry["qid"])
        qids = [q for q, _, _ in worthy]
        if not worthy:
            return ("zero", name, entry["qid"], [d for _, _, d in worthy])
        if len(qids) == 1:
            return ("unambig", name, entry["qid"], None)
        return ("omonim", name, {
            "name": name,
            "qid": entry["qid"],
            "qids": qids,
            "descs": [d for _, _, d in worthy],
            "primul_faima": qids[0] == entry["qid"],
        }, None)

    unambig = 0            # 0-1 candidati foto-worthy: decizia era determinata
    omonime: list = []     # >=2 candidati foto-worthy: alegere posibila gresita
    zero_acum = []         # cached hit care azi n-ar mai avea candidat foto-worthy
    erori = 0
    t0 = time.time()

    # progres incremental (JSONL): o relansare nu re-intreaba ce e deja clasificat
    os.makedirs(os.path.dirname(args.state), exist_ok=True)
    facute: dict = {}
    if os.path.exists(args.state):
        with open(args.state, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    facute[r["name"]] = r
                except Exception:
                    pass
    hits = [(k, v) for k, v in hits if v["name"] not in facute]
    if facute:
        print(f"  .. {len(facute)} nume deja clasificate in state, sarite", flush=True)
    statef = open(args.state, "a", encoding="utf-8")

    def _record(kind, name, payload):
        statef.write(json.dumps({"name": name, "kind": kind,
                                 "payload": payload}, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(max_workers=max(args.workers, 1)) as ex:
        for i, (kind, name, payload, _x) in enumerate(ex.map(_classify, hits), 1):
            if kind == "eroare":
                erori += 1
                print(f"  ! {name}: {payload}", flush=True)
            elif kind == "zero":
                zero_acum.append((name, payload))
            elif kind == "unambig":
                unambig += 1
            else:
                omonime.append(payload)
            _record(kind, name, payload)
            if i % 200 == 0:
                statef.flush()
                rate = 100.0 * len(omonime) / i
                print(f"  ... {i}/{len(hits)} ({rate:.1f}% omonime pana acum, "
                      f"{time.time() - t0:.0f}s)", flush=True)
            time.sleep(args.sleep / max(args.workers, 1))
    statef.close()

    # statistica finala DIN state (aceasta rulare + eventualele anterioare)
    omonime, zero_acum = [], []
    unambig = erori = 0
    with open(args.state, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            k, p = r["kind"], r["payload"]
            if k == "eroare":
                erori += 1
            elif k == "zero":
                zero_acum.append((r["name"], p))
            elif k == "unambig":
                unambig += 1
            else:
                omonime.append(p)
    total = unambig + len(omonime) + len(zero_acum)
    lines = [
        "# Audit portrete omonime — report-only",
        f"*Generat: {datetime.now(timezone.utc).isoformat(timespec='seconds')} · "
        f"sursa: `{os.path.relpath(args.input, ROOT)}` · logica candidati: "
        "`tools/fetch_portraits.py` (aceași funcție `_worthy_candidates` ca în pipeline) · "
        f"statistică din `{os.path.relpath(args.state, ROOT)}`*",
        "",
        f"- Decizii auditate (hits cu qid): **{total}**",
        f"- Determinate (0-1 candidati foto-worthy): **{unambig}** "
        f"({100.0 * unambig / total:.1f}% din total)" if total else "- (fara hits)",
        f"- Omonime (>=2 candidati foto-worthy): **{len(omonime)}** "
        + (f"({100.0 * len(omonime) / total:.1f}% — rata de ambiguitate)" if total else ""),
        f"- Cached hits fara candidat azi (P18/licenta s-a schimbat intre timp): {len(zero_acum)}",
        f"- Erori de retea/API (excluse din totalurile de mai sus): {erori}",
        f"- Dintre omonime, alegerea cached coincide cu candidatul cel mai celebru "
        f"(prima pozitie): {sum(1 for o in omonime if o['primul_faima'])} — la astea nu se "
        "poate spune local daca sunt corecte sau nu; celelalte fie au fost alese de "
        "photojudge pe context (fix #439), fie de logica veche.",
        "",
        "## Lista omonimelor (pentru revizuire manuala)",
        "",
    ]
    for o in omonime:
        lines.append(f"### {o['name']}")
        lines.append(f"- cached: `{o['qid']}`"
                     + (" (= cel mai celebru)" if o["primul_faima"] else " (NU e primul)"))
        for q, d in zip(o["qids"], o["descs"]):
            mark = " ← cached" if q == o["qid"] else ""
            lines.append(f"- {q}: {d}{mark}")
        lines.append("")

    report = "\n".join(lines)
    if args.out:
        outp = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with open(outp, "w", encoding="utf-8") as f:
            f.write(report)
        print(f">> raport scris: {outp}")
    else:
        print(report)

    print(f">> audit: {total} decizii, {len(omonime)} omonime, {unambig} determinate, "
          f"{len(zero_acum)} fara candidat azi, {erori} erori")
    return 0


if __name__ == "__main__":
    sys.exit(main())
