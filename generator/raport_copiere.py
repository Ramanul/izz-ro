"""Jurnal de suprapunere rezumat<->sursa. RAPORTEAZA, nu blocheaza nimic.

De ce exista: §2.2 din REGULI-SINTEZA.md („reformulare integrala, ZERO propozitii
copiate") e regula cu cea mai mare expunere de drept de autor si singura care traia
doar in prompt. Un prompt cu 17 reguli obtine respectare partiala — observatia e din
antetul lui `verifica_sinteza.py` — iar regulile de la coada listei sunt cele scapate.

Ce face: pentru fiecare rezumat produs de model, masoara cat text apare cuvant-cu-cuvant
si in sursa, si scrie un rand in `data/raport_copiere.jsonl`. Atat. Nicio respingere,
niciun prag: pragul se stabileste dupa ce se citesc cifre de pe rulari reale
(`tools/citeste_raport_copiere.py`), nu ghicit.

DOUA REGULI DE PROIECTARE, amandoua deliberate:

1. NU se salveaza textul sursei. `process.py` il sterge intentionat dupa procesare —
   comentariul de la `process_cluster` ii spune „scrub juridic". Aici se scriu doar
   cifrele plus fragmentul COMUN, adica text care e oricum publicat pe izz.ro, deci
   nu adauga nicio expunere noua.

2. NICIO exceptie de aici nu are voie sa iasa. O masuratoare care raporteaza nu poate
   fi motivul pentru care un articol nu se publica; ar transforma o plasa de siguranta
   in punct unic de esec. De aceea totul e invelit in `try/except Exception`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .verifica_sinteza import suprapunere_sursa

CALE = Path(__file__).resolve().parents[1] / "data" / "raport_copiere.jsonl"


def _cale() -> Path:
    """Calea jurnalului, cu `IZZ_RAPORT_COPIERE` ca redirectare.

    De ce e nevoie: sase fisiere din `tests/` cheama functiile din `process.py`, deci
    fiecare rulare a suitei scria randuri sintetice exact in jurnalul din care trebuie
    ales pragul (masurat 2026-08-20: 17 randuri au devenit 33 dintr-o rulare de teste).
    Datele de calibrare si datele de test nu au voie sa stea in acelasi fisier.
    """
    din_mediu = os.environ.get("IZZ_RAPORT_COPIERE")
    return Path(din_mediu) if din_mediu else CALE

_MAX_FRAGMENT = 120   # aceeasi taietura ca `Problema.detaliu` din `verifica_sinteza.py`


def noteaza(model: str, identificator: str, titlu: str, rezumat: str, sursa: str) -> None:
    """Masoara si scrie un rand. Nu ridica niciodata exceptii.

    `model` e „B" sau „C" (fluxul care a produs textul), `identificator` e link-ul sau
    slug-ul, ca randul sa poata fi urmarit inapoi la articol.

    Titlul si rezumatul se masoara SEPARAT, nu concatenate: un titlu de stire are
    suprapunere legitim mare („Guvernul a aprobat ordonanta de urgenta privind...") si,
    lipit de rezumat, ar trage procentul in sus si ar ineca semnalul real.
    """
    try:
        if not sursa or not (titlu or rezumat):
            return
        s_titlu = suprapunere_sursa(titlu or "", sursa)
        s_text = suprapunere_sursa(rezumat or "", sursa)
        rand = {
            "cand": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": model,
            "id": (identificator or "")[:200],
            "titlu_procent": s_titlu.procent,
            "titlu_max_cuvinte": s_titlu.max_cuvinte,
            "text_procent": s_text.procent,
            "text_max_cuvinte": s_text.max_cuvinte,
            "fragment": (s_text.fragment or s_titlu.fragment)[:_MAX_FRAGMENT],
        }
        cale = _cale()
        cale.parent.mkdir(parents=True, exist_ok=True)
        with cale.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rand, ensure_ascii=False) + "\n")
    except Exception:
        # Deliberat mut: vezi regula 2 din antetul modulului.
        return
