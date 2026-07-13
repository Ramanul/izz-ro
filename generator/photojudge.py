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
