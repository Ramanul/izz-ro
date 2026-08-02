#!/usr/bin/env python
"""Extrage entitățile din data/entities/*.yaml și emite public/data/entities.json.

Validare fail-fast: orice entitate fără câmpurile obligatorii blochează build-ul.
Reguli nenegociabile:
- fiecare valoare are act_normativ + sursa_url + in_vigoare_de
- fără sursă → nu se publică
- istoric e append-only
- ultima_verificare e obligatoriu
- `verificat` e obligatoriu ȘI explicit bool: prezența unui sursa_url dovedea doar că
  cineva a scris o adresă, nu că cifrele au fost confruntate cu ea. Un câmp care lipsește
  nu poate deveni „verificat" din omisiune — asta ținea trei ghiduri cu valori placeholder
  publicate sub eticheta „✅ Verificat".
"""
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTITIES_DIR = os.path.join(ROOT, "data", "entities")
OUT_DIR = os.path.join(ROOT, "output", "data")

REQUIRED = (
    "id",
    "nume",
    "tip",
    "categorie_ghid",
    "valoare_curenta",
    "ultima_verificare",
    "verificat",
)
REQUIRED_VAL: tuple[str, ...] = (
    "act_normativ",
    "sursa_url",
    "in_vigoare_de",
)
VALID_TIPURI = {"valoare_monetara", "acte", "auto", "locuinte", "educatie", "sanatate"}

CATEGORII_GHID = {
    "bani": "💰 Bani",
    "acte": "📄 Acte",
    "auto": "🚗 Auto",
    "locuinte": "🏠 Locuințe",
    "educatie": "🎓 Educație",
    "sanatate": "🩺 Sănătate",
}


def validate(ent: dict) -> list[str]:
    errors: list[str] = []
    eid = ent.get("id", "???")
    for field in REQUIRED:
        if field not in ent or ent[field] is None:
            errors.append(f"[{eid}] câmp obligatoriu lipsă: {field}")
    if ent.get("tip") not in VALID_TIPURI:
        errors.append(f"[{eid}] tip invalid: {ent.get('tip')}. Valid: {', '.join(sorted(VALID_TIPURI))}")
    if ent.get("categorie_ghid") not in CATEGORII_GHID:
        errors.append(f"[{eid}] categorie_ghid invalidă: {ent.get('categorie_ghid')}")
    # Un link catre homepage-ul unui minister nu e o citare: cititorul trimis acolo nu
    # gaseste cifra. Regula musca exact cand cineva DECLARA verificarea, deci nu blocheaza
    # entitatile care isi recunosc cinstit starea de neverificate.
    if ent.get("verificat") is True:
        url = (ent.get("valoare_curenta") or {}).get("sursa_url") or ""
        cale = re.sub(r"^https?://[^/]+", "", url).strip("/")
        if not cale:
            errors.append(f"[{eid}] verificat: true cere sursa_url catre pagina exacta cu "
                          f"valoarea, nu catre homepage ({url})")
    if "verificat" in ent and not isinstance(ent.get("verificat"), bool):
        errors.append(f"[{eid}] verificat trebuie să fie true sau false, nu {ent.get('verificat')!r} "
                      "(un șir precum 'da' e adevărat în Python și ar publica date neverificate)")
    vc = ent.get("valoare_curenta") or {}
    for field in REQUIRED_VAL:
        if not vc.get(field):
            errors.append(f"[{eid}] valoare_curenta.{field} lipsă (regulă: fără sursă → nu se publică)")
    errors += _validate_sectiuni(ent, eid)
    return errors


def _validate_sectiuni(ent: dict, eid: str) -> list[str]:
    """`sectiuni` e OPTIONAL: ghidurile de valoare (salariu, pensie) n-au nevoie de el, cele
    procedurale (acte, permis auto, Noua Casă) sunt facute din el. Dar daca exista, forma se
    verifica — o sectiune fara titlu sau fara continut se randeaza ca un <h2> gol urmat de
    nimic, adica exact „output degradat" din regula Zero Zgomot, publicat tacut."""
    sectiuni = ent.get("sectiuni")
    if sectiuni is None:
        return []
    if not isinstance(sectiuni, list):
        return [f"[{eid}] sectiuni trebuie să fie o listă, nu {type(sectiuni).__name__}"]
    errors = []
    for i, s in enumerate(sectiuni):
        if not isinstance(s, dict):
            errors.append(f"[{eid}] sectiuni[{i}] nu e un dict")
            continue
        for field in ("titlu", "continut"):
            if not (s.get(field) or "").strip():
                errors.append(f"[{eid}] sectiuni[{i}].{field} lipsă sau gol")
    return errors


def load_all() -> list[dict]:
    if not os.path.isdir(ENTITIES_DIR):
        print(">> build_entities: niciun fișier YAML în data/entities/ — se iese fără eroare")
        return []
    all_errors = []
    entities = []
    for fn in sorted(os.listdir(ENTITIES_DIR)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(ENTITIES_DIR, fn)
        try:
            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            all_errors.append(f"[{fn}] YAML invalid: {e}")
            continue
        if not isinstance(data, dict):
            all_errors.append(f"[{fn}] conținut invalid (nu e dict)")
            continue
        errs = validate(data)
        if errs:
            all_errors.extend(errs)
            continue
        entities.append(data)
    if all_errors:
        print(">> build_entities: erori de validare — build blocat:")
        for e in all_errors:
            print(f"    {e}")
        sys.exit(1)
    return entities


def write_json(entities: list[dict]) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "entities.json")
    payload = {
        "categorii_ghid": CATEGORII_GHID,
        "entity_kwargs": {e["id"]: e for e in entities},
        "total": len(entities),
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return out_path


def main() -> int:
    entities = load_all()
    if not entities:
        return 0
    out = write_json(entities)
    print(f">> build_entities: {len(entities)} entitati validate -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
