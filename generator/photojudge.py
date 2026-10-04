"""Judecator AI al potrivirii foto<->articol: previne imaginile inselatoare.

Inainte de a folosi fotografia P18 a unei entitati ca imagine PRINCIPALA (lead) a
unui articol, intreaba providerul AI (Gemini free-tier implicit; setabil pe
Claude/fable prin AI_PROVIDER=anthropic) daca poza e o ilustratie EXACTA si nu
induce in eroare -- ex. respinge poza echipei X pe o stire "Y a batut X".

Fail-safe (regula sect. 7 "No mangled output"): provider absent -> nu poate judeca,
lasa regulile deterministe sa decida (True). Provider prezent dar apel/raspuns
esuat sau ambiguu -> RESPINGE (False): mai bine fara poza decat una gresita.

Ruleaza in pipeline (GitHub Actions, are cheia API). Partile pure (prompt, parsare)
sunt testabile offline.
"""
import json
import re

_SYSTEM = (
    "You are a careful photo editor for a Romanian news site. Decide whether using a "
    "photo of a specific ENTITY as the MAIN image of an ARTICLE is accurate and NOT "
    "misleading. Answer ok=false when: the entity is a losing or opposing side in a "
    "competition or conflict the article describes; the entity is not the central "
    "subject of the article; or the photo caption implies an outcome the article "
    "contradicts (e.g. a team celebrating when the article says that team lost). "
    "When in doubt, answer false. Respond with ONLY a JSON object of the form "
    '{"ok": true, "reason": "<=12 words"}.'
)


def build_user(title: str, summary: str, entity: str, caption: str) -> str:
    return (f"ARTICLE TITLE: {title}\n"
            f"ARTICLE SUMMARY: {(summary or '')[:600]}\n\n"
            f"CANDIDATE ENTITY (the photo's subject): {entity}\n"
            f"PHOTO CAPTION / FILENAME: {caption}\n\n"
            "Is a photo of this entity an accurate, non-misleading MAIN image for this article?")


def parse_verdict(raw: str) -> bool:
    """True DOAR daca modelul spune explicit ok=true. Orice altceva -> False (fail-safe)."""
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", (raw or "").strip(), flags=re.MULTILINE).strip()
        return json.loads(cleaned).get("ok") is True
    except (ValueError, AttributeError, TypeError):
        return False


def photo_fits(provider, title: str, summary: str, entity: str, caption: str) -> bool:
    """Poza entitatii e potrivita ca lead pt. articol?
    provider None -> True (nu poate judeca; deciziile deterministe raman in vigoare).
    provider prezent -> verdictul AI; orice eroare de apel -> False (fail-safe)."""
    if provider is None:
        return True
    try:
        raw = provider.complete(_SYSTEM, build_user(title, summary, entity, caption))
    except Exception:
        return False
    return parse_verdict(raw)


# === Dezambiguizare omonime =====================================================
# Nume-omonime (ex. "John Kennedy": presedintele decedat 1963 vs. senatorul de
# Louisiana in viata) NU se rezolva prin popularitate -- primul rezultat Wikidata
# e mereu cel mai celebru, deci identitatea ar fi data de faima. Candidatii
# (generati de tools/fetch_portraits.py) se dau judecatorului IMPREUNA cu
# contextul articolului; el alege persoana sau renunta.

_SYSTEM_PICK = (
    "You are a careful fact-checker for a Romanian news site. Several DIFFERENT real "
    "entities (people or organisations) share the same name. Decide which candidate "
    "the ARTICLE is actually about, using the article context (who appears alongside, "
    "the roles and actions described, dates, living vs deceased) and each candidate's "
    "label and description. If two candidates are equally plausible or you are unsure, "
    "choose none. Respond with ONLY a JSON object of the form "
    '{"pick": <0-based index>, "reason": "<=12 words"} or, when no candidate clearly '
    'matches, {"pick": -1, "reason": "<=12 words"}.'
)


def build_pick_user(title: str, summary: str, candidates: list) -> str:
    lines = [f"ARTICLE TITLE: {title}",
             f"ARTICLE SUMMARY: {(summary or '')[:600]}", "",
             "CANDIDATES (same name, different real entities):"]
    for i, c in enumerate(candidates):
        lines.append(f"[{i}] {c}")
    lines.append("")
    lines.append("Which candidate is the article about? Index only, or -1 if none clearly matches.")
    return "\n".join(lines)


def parse_pick(raw: str) -> int:
    """Index valid (>=0) sau -1. Orice altceva -> -1 (fail-safe: nimeni)."""
    try:
        cleaned = re.sub(r"^```(?:json)?|```$", "", (raw or "").strip(), flags=re.MULTILINE).strip()
        v = json.loads(cleaned).get("pick")
        if isinstance(v, bool):
            return -1
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            v = int(v.strip())
        if isinstance(v, int) and v >= -1:
            return v
    except (ValueError, AttributeError, TypeError):
        pass
    return -1


def pick_candidate(provider, title: str, summary: str, candidates: list) -> int:
    """Indexul candidatului despre care e articolul, sau -1 (niciunul/neclar).
    Acelasi fail-safe ca photo_fits: provider None -> -1 (offline: omonimele raman
    fara portret), apel esuat sau raspuns ambiguu -> -1, index invalid -> -1."""
    if provider is None or not candidates:
        return -1
    try:
        raw = provider.complete(_SYSTEM_PICK, build_pick_user(title, summary, candidates))
    except Exception:
        return -1
    idx = parse_pick(raw)
    return idx if 0 <= idx < len(candidates) else -1
