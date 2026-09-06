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
Daca masurarea nu poate fi executata sau a evidencia de gate nu poate fi scrisa, rularea de
producao este tratata ca stare necunoscuta si esueaza closed, nu ca „nicio problema".
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
_BLOCKING = {"citat_inventat", "cifra_straina", "text_copiat", "titlu_copiat"}


def _scrie_jsonl(cale: Path, rand: dict) -> None:
    cale.parent.mkdir(parents=True, exist_ok=True)
    with cale.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rand, ensure_ascii=False) + "\n")


def _rand_de_eroare(model: str, identificator: str, exc: Exception) -> dict:
    """Produce o dovada blocanta cand verificarea insasi nu poate fi executata."""
    return {
        "cand": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "id": (identificator or "")[:200],
        "titlu_procent": 0,
        "titlu_max_cuvinte": 0,
        "text_procent": 0,
        "text_max_cuvinte": 0,
        "fragment": "",
        "blocking_issues": [{
            "cod": "grounding_measurement_error",
            "detaliu": f"{type(exc).__name__}: {exc}"[:_MAX_FRAGMENT],
        }],
        "advisory_issues": [],
    }


def noteaza(model: str, identificator: str, titlu: str, rezumat: str, sursa: str) -> None:
    """Masoara si scrie rapoartele.

    Jurnalul observational ramane best-effort. Raportul tranzitoriu este insa parte din
    release contract: cand este configurat, orice eroare de masurare devine o dovada
    blocanta, iar orice eroare de scriere a dovezii se propaga si opreste pipeline-ul.
    """
    if not sursa or not (titlu or rezumat):
        return

    gate_cale = _gate_cale()
    try:
        s_titlu = suprapunere_sursa(titlu or "", sursa)
        s_text = suprapunere_sursa(rezumat or "", sursa)
        probleme = verifica(titlu or "", rezumat or "", sursa)
        blocking = [
            {"cod": p.cod, "detaliu": p.detaliu[:_MAX_FRAGMENT]}
            for p in probleme
            if p.cod in _BLOCKING
        ]
        advisory = [
            {"cod": p.cod, "detaliu": p.detaliu[:_MAX_FRAGMENT]}
            for p in probleme
            if p.cod not in _BLOCKING
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
    except Exception as exc:
        if gate_cale is None:
            # Development/legacy callers fara gate isi pastreaza comportamentul best-effort.
            return
        # Dovada de eroare trebuie SCRISA. Daca scrierea esueaza, exceptia se propaga:
        # release-ul nu are voie sa transforme „nu am putut masura" in „curat".
        _scrie_jsonl(gate_cale, _rand_de_eroare(model, identificator, exc))
        return

    # Jurnalul de calibrare existent; ramane observational si nu este comis de build.
    try:
        _scrie_jsonl(_cale(), rand)
    except Exception:
        pass

    # Raportul tranzitoriu pentru gate traieste in RUNNER_TEMP/alt path si poate fi
    # sters la sfarsitul rularii; contine numai dovezi minime, nu textul sursei.
    if gate_cale is not None:
        _scrie_jsonl(gate_cale, rand)


def url_uri_blocate(cale_raport: str) -> set[str]:
    """ID-urile (URL-uri) cu probleme blocante din raportul tranzitoriu al gate-ului."""
    blocate: set[str] = set()
    try:
        with open(cale_raport, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rand = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rand, dict) and rand.get("blocking_issues"):
                    blocate.add(str(rand.get("id", "")))
    except OSError:
        pass
    return blocate


def pastreaza_doar_curate(cale_raport: str) -> int:
    """Scoate din raportul gate randurile cu probleme blocante; intoarce cate au fost scoase.

    Raportul gate este dovada pentru CE SE PUBLICE in rularea asta. Itemele cu incalcari
    deterministe sunt amanate inainte de salvarea starii (mecanismul existent de defer:
    revin ca iteme noi la rularea urmatoare), deci randurile lor ies din dovada — gate-ul
    de dupa commit ramane fail-closed pentru orice scapare. Jurnalul observational din
    `data/raport_copiere.jsonl` pastreaza neatinse toate masuratorile.
    """
    try:
        with open(cale_raport, "r", encoding="utf-8") as fh:
            randuri = [json.loads(line) for line in fh if line.strip()]
    except (OSError, json.JSONDecodeError):
        return 0
    curate = [r for r in randuri if isinstance(r, dict) and not r.get("blocking_issues")]
    scoase = len(randuri) - len(curate)
    if scoase:
        try:
            with open(cale_raport, "w", encoding="utf-8") as fh:
                for r in curate:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        except OSError:
            return 0
    return scoase
