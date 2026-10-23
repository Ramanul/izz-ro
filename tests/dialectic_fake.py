"""Răspunsul unui model fals în formatul sintezei dialectice (E2), construit DIN prompt.

Fake-urile vechi întorceau `{"title", "synthesis"}` — formatul narativ, care nu mai există
(`specs/plan-paradigma-izz.md` §5). Un răspuns dialectic valid trebuie să citeze propozițiile
pe care modelul chiar le-a primit, deci se construiește din `user`: pentru fiecare eveniment
`[i]`, un fapt comun care citează prima propoziție a primelor două publicații.
"""
from __future__ import annotations

import json
import re


def raspuns(user: str, title: str, statement: str, category: str = "general", **extra) -> str:
    out = []
    for ev in re.findall(r"^\[(\d+)\]$", user, re.M):
        prime: dict[str, str] = {}
        for chunk, src in re.findall(rf"\[(C{ev}S(\d+)\.\d+)\]", user):
            prime.setdefault(src, chunk)
        obj = {"id": int(ev), "title": title, "epistemic_state": "SYNTHESIS_VALID",
               "common_facts": [{"statement": statement, "chunk_ids": list(prime.values())[:2],
                                 "has_hedging": False}],
               "divergences": [], "uncorroborated_claims": [], "is_milestone": False,
               "category": category, "entities": [], "icon": None}
        obj.update(extra)
        out.append(obj)
    return json.dumps(out)


def e_prompt_dialectic(user: str) -> bool:
    return "[C0S1]" in user or bool(re.search(r"\[C\d+S\d+\]", user))
