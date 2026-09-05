"""Jurnal persistent al aruncarilor din pipeline (PLAN UNIFICAT #5, triage blockers).

De ce exista: rapoartele de aruncare sunt printate in log-ul rularii, iar log-urile CI
se pastreaza limitat. Analiza de over-blocking (ce garda arunca prea mult, pe ce surse,
ce cazuri legitime mor la prag) are nevoie de istorie comisa: o rulare = un rand JSONL
in `data/triage_log.jsonl`, comis de pipeline alaturi de restul starii.

Ce NU inregistreaza: respingerile din `moderation.apply` (garda de moderare ruleaza pe
tot stocul la fiecare build; aceleasi articole ar produce randuri duplicate fara valoare
noua). Jurnalul acopera INGESTIA: pierderile de fetch pe motive, itemele fara substanta
(respinse definitiv, inainte de bugetul AI) si itemele expirate.

Scrierea esuata NU opreste pipeline-ul: jurnalul e observabilitate, nu control-plane —
spre deosebire de moderation.yaml, unde lipsa configuratiei opreste publicarea.
"""
import json
import os
from datetime import datetime, timezone

from . import config


def cale() -> str:
    return os.path.join(config.ROOT, "data", "triage_log.jsonl")


def inregistreaza(pierderi: dict | None, respinse_substanta: set | None, stale_skipped: int) -> None:
    rand = {
        "cand": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ingestie": {str(k): int(v) for k, v in (pierderi or {}).items()},
        "fara_substanta": len(respinse_substanta or set()),
        "fara_substanta_exemple": sorted(respinse_substanta or set())[:10],
        "expirate": int(stale_skipped or 0),
    }
    try:
        os.makedirs(os.path.dirname(cale()), exist_ok=True)
        with open(cale(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rand, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"   !! jurnal triage nescris ({exc}) — rularea continua")
