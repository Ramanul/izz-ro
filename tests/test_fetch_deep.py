"""E0 fetch_deep — materia primă pe clusterele selectate (plan-paradigma-izz.md §3).

Rețeaua e înlocuită prin patch pe granita `fetch._deschide` (idiomul din
test_fetch_redirect_ssrf): testele nu ies pe internet, dar exercită integral
validatorul, fallback-ul, meta-ul cu SHA-256/ancore și driftul.
"""
import json
from datetime import datetime, timedelta, timezone
from urllib.error import URLError

from generator import config, fetch, fetch_deep


def _item(url, title, description=""):
    return {
        "url": url,
        "original_link": url,
        "title": title,
        "original_title": title,
        "description": description,
        "published": datetime.now(timezone.utc).isoformat(),
        "source": "test",
    }


ARTICLE_TITLE = "Guvernul a aprobat bugetul pentru Timiș"
_ARTICLE_PARAS = "".join(
    f"<p>Guvernul a aprobat bugetul cu {i} miliarde de lei pentru jud. Timiș în ședința de azi.</p>"
    for i in range(2, 12)
)
ARTICLE_HTML = f"<html><body><script>var x=1;</script>{_ARTICLE_PARAS}</body></html>"


class _Raspuns:
    def __init__(self, body):
        self._body = body

    def read(self, n=None):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _instaleaza_deschide(monkeypatch, body, fail=None):
    def fake(req, timeout=None):
        if fail is not None:
            raise fail
        return _Raspuns(body)
    monkeypatch.setattr(fetch, "_deschide", fake)


# ---------------------------------------------------------------------------
# 1. Splitter românesc: abrevieri, numere, acronime, inițiale, domenii
# ---------------------------------------------------------------------------

def test_splitter_protejeaza_abrevierile_si_numerotarea():
    text = ("Conform art. 5 alin. 2 din O.U.G. nr. 114/2026, M.Ap.N. și B.N.R. au alocat "
            "1.500.000 de lei (aprox. 300.000 euro) pentru jud. Timiș și mun. Cluj-Napoca. "
            "Dr. I. L. Popescu a declarat pentru izz.ro că măsura intră în vigoare la "
            "1 nov. 2026! „Nu există niciun risc bugetar major”, a precizat oficialul.")
    chunks = fetch_deep.split_romanian_sentences(text, source_id="S1")
    assert "S1.1" in chunks and len(chunks) >= 2
    # punctele protejate NU devin granițe de propoziție
    for sent in chunks.values():
        assert not sent.strip().endswith(("art.", "alin.", "nr.", "jud.", "Dr.", "izz.ro"))
    # numărul cu punct și domeniul rămân întregi în interiorul unei propoziții
    joined = " ".join(chunks.values())
    assert "1.500.000" in joined
    assert "izz.ro" in joined
    assert "M.Ap.N." in joined


def test_splitter_text_gol_si_cap_de_propozitii():
    assert fetch_deep.split_romanian_sentences("", "S1") == {}
    many = "Acesta este un test simplu de spargere corecta a propozitiilor. " * 30
    chunks = fetch_deep.split_romanian_sentences(many, source_id="S1", max_sentences=5)
    assert set(chunks) == {"S1.1", "S1.2", "S1.3", "S1.4", "S1.5"}


def test_splitter_lipste_fragments_scurte():
    chunks = fetch_deep.split_romanian_sentences(
        "UPDATE 14:30. Guvernul a aprobat azi bugetul pentru Timiș.", source_id="S1")
    assert len(chunks) >= 1
    # ciotul „UPDATE 14:30.” nu rămâne propoziție proprie: se lipește de următoarea
    assert "Guvernul" in chunks["S1.1"]


# ---------------------------------------------------------------------------
# 2. Validatorul anti-parazit
# ---------------------------------------------------------------------------

def test_validator_respinge_ciotul():
    ok, reason = fetch_deep.validate_extracted_body("Prea scurt.", ARTICLE_TITLE)
    assert not ok and "SHORT_BODY" in reason


def test_validator_respinge_cookie_wall():
    wall = ("Acceptă toate modulele cookie pentru a continua navigarea pe site-ul nostru. "
            "Partenerii noștri prelucrează date. " * 10)
    ok, reason = fetch_deep.validate_extracted_body(wall, ARTICLE_TITLE)
    assert not ok and reason == "COOKIE_OR_PAYWALL_DETECTED"


def test_validator_respinge_titlu_nepotrivit():
    alt_subiect = "Echipa locală a câștigat derby-ul de campionat cu o replăcnet reușită. " * 5
    ok, reason = fetch_deep.validate_extracted_body(alt_subiect, ARTICLE_TITLE)
    assert not ok and "TITLE_MISMATCH" in reason


def test_validator_accepta_articolul_real():
    ok, reason = fetch_deep.validate_extracted_body(
        "Guvernul a aprobat bugetul. " + "Sumele pentru Timiș au fost confirmate. " * 10,
        ARTICLE_TITLE)
    assert ok and reason is None


# ---------------------------------------------------------------------------
# 3. SHA-256, ancore și drift (baza E1)
# ---------------------------------------------------------------------------

def test_sha_ignora_whitespace():
    assert fetch_deep.compute_sha256("Guvernul   a aprobat\nbugetul") == \
           fetch_deep.compute_sha256("guvernul a aprobat bugetul")


def test_ancore_extrag_cifre_si_entitati():
    anchors = fetch_deep.extract_quick_anchors(
        "Bugetul de 3,5 miliarde a fost aprobat de Guvernul pentru 12 județe.")
    assert "NUM:3.5" in anchors
    assert "NUM:12" in anchors
    assert any(a.startswith("ENT:guvern") for a in anchors)


def test_drift_doar_pe_roluri_grele_si_doar_la_schimbare():
    old = {"NUM:100", "ENT:guvern"}
    same = {"NUM:100", "ENT:guvern"}
    changed = {"NUM:100", "ENT:guvern", "NUM:250", "ENT:cluj", "ENT:banat", "ENT:oradea"}
    assert not fetch_deep.check_if_silent_edit_causes_dirty("ROOT", None, "x", old, same)
    assert not fetch_deep.check_if_silent_edit_causes_dirty("ROOT", "a", "a", old, same)
    assert not fetch_deep.check_if_silent_edit_causes_dirty("ECHO", "a", "b", old, changed)
    assert fetch_deep.check_if_silent_edit_causes_dirty("ROOT", "a", "b", old, changed)


# ---------------------------------------------------------------------------
# 4. Extragerea nativă HTML (calea din CI, fără trafilatura)
# ---------------------------------------------------------------------------

def test_extragere_nativa_html(monkeypatch):
    monkeypatch.setattr(fetch_deep, "HAS_TRAFILATURA", False)
    text = fetch_deep._extract_body_sync(ARTICLE_HTML.encode("utf-8"), "https://exemplu.ro/a")
    assert "miliarde de lei" in text
    assert "var x=1" not in text
    assert len(text) >= fetch_deep.MIN_FULL_TEXT_CHARS


# ---------------------------------------------------------------------------
# 5. fetch_deep: full text, fallback, meta, drift, prune, dry-run
# ---------------------------------------------------------------------------

def test_fetch_deep_full_text_si_numerotare_per_cluster(tmp_path, monkeypatch):
    _instaleaza_deschide(monkeypatch, ARTICLE_HTML.encode("utf-8"))
    meta_path = str(tmp_path / "deep_meta.json")
    it1 = _item("https://exemplu1.ro/a", ARTICLE_TITLE, "descriere scurtă")
    it2 = _item("https://exemplu2.ro/b", "Alt titlu despre buget", "altă descriere")
    rezultate = fetch_deep.fetch_deep([[it1, it2]], meta_path=meta_path)

    assert rezultate[it1["url"]].extraction_mode == "FULL_TEXT"
    # numerotarea S1..Sn e PER CLUSTER, după poziția în grup
    assert "S1.1" in rezultate[it1["url"]].sentences
    assert "S2.1" in rezultate[it2["url"]].sentences
    assert fetch_deep.stats()["FULL_TEXT"] == 2

    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    assert it1["url"] in meta
    assert len(meta[it1["url"]]["sha256"]) == 64
    assert meta[it1["url"]]["anchors"]


def test_fetch_deep_fallback_pe_eroare_retea(tmp_path, monkeypatch):
    _instaleaza_deschide(monkeypatch, b"", fail=URLError("refuzat"))
    meta_path = str(tmp_path / "deep_meta.json")
    it = _item("https://exemplu1.ro/a", ARTICLE_TITLE, "descrierea din RSS")
    rezultate = fetch_deep.fetch_deep([[it]], meta_path=meta_path)
    r = rezultate[it["url"]]
    assert r.extraction_mode == "RSS_FALLBACK"
    assert r.fallback_reason == "URLError"
    assert r.raw_text == f"{ARTICLE_TITLE}. descrierea din RSS"
    assert fetch_deep.stats()["RSS_FALLBACK"] == 1


def test_fetch_deep_respinge_interstitialul_cu_200(tmp_path, monkeypatch):
    challenge = b"One moment, please" + ARTICLE_HTML.encode("utf-8")
    _instaleaza_deschide(monkeypatch, challenge)
    meta_path = str(tmp_path / "deep_meta.json")
    it = _item("https://exemplu1.ro/a", ARTICLE_TITLE, "desc")
    rezultate = fetch_deep.fetch_deep([[it]], meta_path=meta_path)
    assert rezultate[it["url"]].extraction_mode == "RSS_FALLBACK"
    assert rezultate[it["url"]].fallback_reason == "CHALLENGE_INTERSTITIAL"


def test_fetch_deep_dry_run_nu_persisteaza(tmp_path, monkeypatch):
    _instaleaza_deschide(monkeypatch, b"")   # orice răspuns — contează doar persist=False
    meta_path = str(tmp_path / "deep_meta.json")
    it = _item("https://exemplu1.ro/a", ARTICLE_TITLE, "d")
    fetch_deep.fetch_deep([[it]], meta_path=meta_path, persist=False)
    assert not (tmp_path / "deep_meta.json").exists()


def test_fetch_deep_marcheaza_silent_edit(tmp_path, monkeypatch):
    meta_path = str(tmp_path / "deep_meta.json")
    it = _item("https://exemplu1.ro/a", ARTICLE_TITLE)
    v1 = ("<html><body>" + "<p>Guvernul a aprobat bugetul cu 100 miliarde de lei pentru "
          "Timiș în ședința de azi.</p>" * 8 + "</body></html>").encode("utf-8")
    v2 = ("<html><body>" + "<p>Guvernul a aprobat bugetul cu 250 miliarde de lei pentru "
          "București și Clujul-Napoca după amânare.</p>" * 8 + "</body></html>").encode("utf-8")

    _instaleaza_deschide(monkeypatch, v1)
    fetch_deep.fetch_deep([[it]], meta_path=meta_path)
    assert fetch_deep.stats().get("SILENT_EDIT_DIRTY", 0) == 0

    _instaleaza_deschide(monkeypatch, v2)
    fetch_deep.fetch_deep([[it]], meta_path=meta_path)
    assert fetch_deep.stats()["SILENT_EDIT_DIRTY"] == 1


def test_fetch_deep_prune_la_ttl(tmp_path, monkeypatch):
    _instaleaza_deschide(monkeypatch, ARTICLE_HTML.encode("utf-8"))
    meta_path = str(tmp_path / "deep_meta.json")
    publicat_vechi = (datetime.now(timezone.utc)
                      - timedelta(days=config.ARTICLE_TTL_DAYS + 5)).isoformat()
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"https://vechi.ro/x": {
            "sha256": "abc", "anchors": ["NUM:1"], "mode": "FULL_TEXT",
            "published": publicat_vechi, "fetched_at": "x"}}, fh)

    it = _item("https://exemplu1.ro/a", ARTICLE_TITLE)
    fetch_deep.fetch_deep([[it]], meta_path=meta_path)
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    assert "https://vechi.ro/x" not in meta
    assert it["url"] in meta


def test_fetch_deep_fara_clustere_curata_contorii(tmp_path):
    fetch_deep._STATISTICI["FULL_TEXT"] = 99   # eventual rest dintr-un apel anterior
    assert fetch_deep.fetch_deep([], meta_path=str(tmp_path / "m.json"), persist=False) == {}
    assert fetch_deep.stats() == {}
