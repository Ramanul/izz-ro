"""Jurnal de suprapunere rezumat<->sursa plus semnale mecanice de grounding.

De ce exista: §2.2 din REGULI-SINTEZA.md („reformulare integrala, ZERO propozitii
copiate") si regulile mecanice din `generator.verifica_sinteza` trebuie sa lase dovada
masurabila. Raportul clasic ramane observational, dar scriem separat si un raport
tranzitoriu pentru un release gate: citatele inventate si cifrele straine sunt suficiente
pentru a opri publicarea, fiind verificari deterministe cu semnal direct.

Ce face: pentru fiecare rezumat produs de model, masoara suprapunerea si executa
verificarile mecanice (`citate_inventate`, `cifre_straine`, `rezerva_pierduta`). Jurnalul
istoric continua sa fie scris in `data/raport_copiere.jsonl`. Un raport separat, cand
`IZZ_RAPORT_COPIERE_GATE` este setat, contine doar identificatorul, scorurile si problemele;
nu pastreaza textul sursei.

Regula de siguranta: esecul scrierii raportului observational nu blocheaza singur pipeline-ul.
Gate-ul explicit (`tools/grounding_gate.py`) decide blocarea pe baza raportului tranzitoriu.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .verifica_sinteza import suprapunere_sursa, verifica

CALE = Path(__file__).resolve().parents[1] / "data" / "raport_copiere.jsonl"


def _cale() -> Path:
    """Calea jurnalului, cu `IZZ_RAPORT_COPIERE` ca redirectare."""
    din_mediu = os.environ.get("IZZ_RAPORT_COPIERE")
    return Path(din_mediu) if din_mediu else CALE


def _gate_cale() -> Path | None:
    raw = os.environ.get("IZZ_RAPORT_COPIERE_GATE", "").strip()
    return Path(raw) if raw else None

_MAX_FRAGMENT = 120


def _scrie_jsonl(cale: Path, rand: dict) -> None:
    cale.parent.mkdir(parents=True, exist_ok=True)
    with cale.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rand, ensure_ascii=False) + "\n")


def noteaza(model: str, identificator: str, titlu: str, rezumat: str, sursa: str) -> None:
    """Masoara si scrie rapoartele. Nu ridica exceptii.

    `model` e „B" sau „C"; `identificator` e link-ul/slug-ul, ca randul sa poata fi urmarit
    inapoi la articol. Niciun raport nu pastreaza textul brut al sursei.
    """
    try:
        if not sursa or not (titlu or rezumat):
            return
        s_titlu = suprapunere_sursa(titlu or "", sursa)
        s_text = suprapunere_sursa(rezumat or "", sursa)
        probleme = verifica(titlu or "", rezumat or "", sursa)
        blocking = [
            {"cod": p.cod, "detaliu": p.detaliu[:_MAX_FRAGMENT]}
            for p in probleme
            if p.cod in {"citat_inventat", "cifra_straina"}
        ]
        advisory = [
            {"cod": p.cod, "detaliu": p.detaliu[:_MAX_FRAGMENT]}
            for p in probleme
            if p.cod not in {"citat_inventat", "cifra_straina"}
        ]
        rand = {
            "cand": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": model,
            "id": (identificator or "")[:200],
            "titlu_procent": s_titlu.procent,
            "titlu_max_cuvinte": s_titlu.max_cuvinte,
            "text_procent": s_text.procent,
            "text_max_cuvinte": s_text.max_cuvinte,
            "fragment": (s_text.fragment or s_titlu.fragment)[:_MAX_FRAGMENT],
            "blocking_issues": blocking,
            "advisory_issues": advisory,
        }
        # Jurnalul de calibrare existent; ramane observational si nu este comis de build.
        _scrie_jsonl(_cale(), rand)
        # Raportul tranzitoriu pentru gate traieste in RUNNER_TEMP/alt path si poate fi
        # sters la sfarsitul rularii; contine numai dovezi minime, nu textul sursei.
        gate_cale = _gate_cale()
        if gate_cale is not None:
            _scrie_jsonl(gate_cale, rand)
    except Exception:
        # O problema de jurnalizare nu trebuie sa devina singurul punct de esec al pipeline-ului.
        return
