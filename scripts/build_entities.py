#!/usr/bin/env python
"""Extrage entitățile din data/entities/*.yaml și emite public/data/entities.json.

Validare fail-fast: orice entitate fără câmpurile obligatorii blochează build-ul.
Reguli nenegociabile:
- fiecare valoare are act_normativ + sursa_url + in_vigoare_de
- fără sursă → nu se publică
- istoric e append-only
- ultima_verificare e obligatoriu
"""
import json
import os
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
    vc = ent.get("valoare_curenta") or {}
    for field in REQUIRED_VAL:
        if not vc.get(field):
            errors.append(f"[{eid}] valoare_curenta.{field} lipsă (regulă: fără sursă → nu se publică)")
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
