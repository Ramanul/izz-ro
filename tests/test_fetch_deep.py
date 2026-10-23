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


# ---------------------------------------------------------------------------
# 6. E1-core: ancore extinse, atribuire derivată, fereastră 15 min, roluri epistemice
# ---------------------------------------------------------------------------

def test_ancore_acronime_citate_si_entitati_la_inceput_de_propozitie():
    text = (
        "Parlamentul a adoptat legea fiscală. BNR și ANAF vor aplica noile reguli "
        "la Timișoara din 15 noiembrie, deoarece „deficitul trebuie redus rapid”."
    )
    anchors = fetch_deep.extract_quick_anchors(text)
    assert any(a.startswith("ENT:parlamen") for a in anchors)
    assert any(a.startswith("ENT:timisoar") for a in anchors)
    assert "ACR:bnr" in anchors
    assert "ACR:anaf" in anchors
    assert "NUM:15" in anchors
    # citatul e prezent ca ancoră, dar DOAR ca hash: deep_meta.json e comis în repo public
    q = [a for a in anchors if a.startswith("Q:")]
    assert len(q) == 1 and "deficit" not in q[0] and len(q[0]) == 2 + 12


def test_glosarul_nu_prinde_cuvinte_de_inceput_de_fraza():
    """„Potrivit…”, „Poate…”, „Mai mult…”, „Sensul…” nu sunt entități: o rădăcină scurtă
    potrivită pe prefix le transforma în ancore comune tuturor articolelor."""
    text = ("Potrivit sursei, ședința s-a amânat. Poate fi reluată. Mai mult, se amână. "
            "Sensul giratoriu rămâne închis. Pot apărea întârzieri.")
    anchors = fetch_deep.extract_quick_anchors(text)
    assert not any(a.startswith(("ENT:pot", "ENT:mai", "ENT:sens")) for a in anchors), anchors


def test_glosarul_prinde_acronimele_exacte_si_flexiunea():
    anchors = fetch_deep.extract_quick_anchors(
        "PSD a anunțat. Guvernului i s-a cerut avizul. Ministrul a semnat. Cluj e gazdă.")
    assert "ACR:psd" in anchors
    assert "ENT:guvern" in anchors
    assert any(a.startswith("ENT:ministr") for a in anchors)
    assert "ENT:cluj" in anchors


def test_clona_fara_atribuire_nu_e_confirmare():
    """Trei publicații care preiau același comunicat sunt o singură origine."""
    comunicat = ("Consiliul Județean Bihor a aprobat bugetul de 820 de milioane de lei pentru "
                 "anul viitor, cu investiții în drumuri, spitale și școli din tot județul.")
    group = [
        {"url": "https://a.ro/1", "source_name": "A", "published": "2026-10-20T10:00:00+00:00",
         "title": "Buget aprobat", "description": comunicat},
        {"url": "https://b.ro/1", "source_name": "B", "published": "2026-10-20T10:20:00+00:00",
         "title": "Bihor: buget", "description": "Azi. " + comunicat},
        {"url": "https://c.ro/1", "source_name": "C", "published": "2026-10-20T10:40:00+00:00",
         "title": "Bugetul Bihorului",
         "description": ("Consilierii județeni din Bihor au votat 820 de milioane de lei; "
                         "opoziția PNL a criticat lipsa fondurilor pentru transportul "
                         "public din Oradea și a cerut o rectificare în martie.")},
    ]
    roles = fetch_deep.classify_cluster_epistemic_roles(group)
    assert roles["https://a.ro/1"] == "ROOT"
    assert roles["https://b.ro/1"] == "CLONE"
    assert roles["https://c.ro/1"] in ("INDEPENDENT_CONTRIBUTOR", "ECHO")
    confirmate = fetch_deep.cross_confirmed_domains(group, roles)
    assert "b.ro" not in confirmate
    assert "a.ro" in confirmate


def test_detectie_atribuire_derivata_si_excludere_proprie():
    assert fetch_deep.is_derived_attribution(
        "Potrivit Agerpres, ședința a început la ora 10.",
        own_domain="digi24.ro",
        own_source_name="Digi24",
    )
    assert fetch_deep.is_derived_attribution(
        "Conform G4Media.ro, documentul a fost semnat azi.",
        own_domain="libertatea.ro",
        own_source_name="Libertatea",
    )
    # auto-referința NU este preluare derivată
    assert not fetch_deep.is_derived_attribution(
        "Potrivit Digi24, ședința a început la ora 10.",
        own_domain="digi24.ro",
        own_source_name="Digi24",
    )


def test_fereastra_densitate_15_min_promoveaza_investigatia_ca_root():
    from generator import process

    t0 = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
    alerta = {
        "url": "https://alerta.ro/stire",
        "original_link": "https://alerta.ro/stire",
        "source": "alerta",
        "source_name": "AlertaRapida",
        "title": "Guvernul adoptă bugetul pe 2027",
        "original_title": "Guvernul adoptă bugetul pe 2027",
        "description": "Ministerul Finanțelor a prezentat bugetul pe 2027.",
        "published": t0.isoformat(),
    }
    investigatie = {
        "url": "https://investigatie.ro/analiza",
        "original_link": "https://investigatie.ro/analiza",
        "source": "inv",
        "source_name": "InvestigatieCompleta",
        "title": "Guvernul adoptă bugetul pe 2027 cu 14,5 miliarde lei pentru autostrăzi",
        "original_title": "Guvernul adoptă bugetul pe 2027 cu 14,5 miliarde lei pentru autostrăzi",
        "description": (
            "Ministerul Finanțelor, BNR și CNAIR au alocat 14,5 miliarde lei pentru "
            "Timișoara, Cluj-Napoca și Iași în 3 tranșe trimestriale, conform „planului "
            "multianual de investiții”."
        ),
        "published": (t0 + timedelta(minutes=8)).isoformat(),
    }

    roles = fetch_deep.classify_cluster_epistemic_roles([alerta, investigatie])
    assert roles[investigatie["url"]] == "ROOT"
    assert roles[alerta["url"]] == "ECHO"

    _, rep = process._prep_cluster_rep([alerta, investigatie])
    # URL-ul rep-ului rămâne stabil pe primul membru, dar first_source recompensează ROOT-ul dens
    assert rep["url"] == alerta["url"]
    assert rep["first_source"] == "InvestigatieCompleta"
    assert rep["epistemic_roles"]["investigatie.ro"] == "ROOT"
    assert rep["epistemic_roles"]["alerta.ro"] == "ECHO"
    assert rep["cross_confirmations"] == 2


def test_graf_noutate_epistemica_si_confirmari_incrucisate():
    t0 = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
    s_root = {
        "url": "https://s1.ro/a",
        "original_link": "https://s1.ro/a",
        "source_name": "Sursa1",
        "title": "Guvernul alocă 100 milioane lei pentru Timișoara",
        "description": "BNR și Ministerul Finanțelor au confirmat suma de 100 milioane lei la Timișoara.",
        "published": t0.isoformat(),
    }
    s_contrib = {
        "url": "https://s2.ro/b",
        "original_link": "https://s2.ro/b",
        "source_name": "Sursa2",
        "title": "Guvernul alocă 100 milioane lei: Cluj-Napoca și Oradea primesc 45 milioane",
        "description": "Primăria Cluj-Napoca și CNAIR primesc încă 45 milioane euro prin PNRR în 2027.",
        "published": (t0 + timedelta(minutes=25)).isoformat(),
    }
    s_echo = {
        "url": "https://s3.ro/c",
        "original_link": "https://s3.ro/c",
        "source_name": "Sursa3",
        # aceleași fapte, cu alte cuvinte — ECHO; titlul identic cu al ROOT ar fi fost
        # CLONE (text comun, posibil comunicat), iar asta e alt caz, testat separat
        "title": "Timișoara primește de la Guvern o alocare de 100 de milioane",
        "description": "Suma, confirmată de Ministerul Finanțelor, ajunge la 100 milioane lei.",
        "published": (t0 + timedelta(minutes=30)).isoformat(),
    }
    s_derived = {
        "url": "https://s4.ro/d",
        "original_link": "https://s4.ro/d",
        "source_name": "Sursa4",
        "title": "Guvernul alocă 100 milioane lei pentru Timișoara",
        "description": "Potrivit Agerpres, Guvernul a alocat 100 milioane lei pentru Timișoara și Arad.",
        "published": (t0 + timedelta(minutes=35)).isoformat(),
    }

    group = [s_root, s_contrib, s_echo, s_derived]
    roles = fetch_deep.classify_cluster_epistemic_roles(group)
    assert roles[s_root["url"]] == "ROOT"
    assert roles[s_contrib["url"]] == "INDEPENDENT_CONTRIBUTOR"
    assert roles[s_echo["url"]] == "ECHO"
    assert roles[s_derived["url"]] == "DERIVED"
    # DERIVED nu numără drept confirmare încrucișată independentă
    assert fetch_deep.cluster_cross_confirmations(group, roles) == 3


def test_silent_edit_ignorat_pe_echo_dar_activ_pe_root(tmp_path, monkeypatch):
    meta_path = str(tmp_path / "deep_meta.json")
    t0 = datetime(2026, 10, 22, 9, 0, tzinfo=timezone.utc)
    root_it = {
        "url": "https://root.ro/a",
        "original_link": "https://root.ro/a",
        "source_name": "Root",
        "title": ARTICLE_TITLE,
        "original_title": ARTICLE_TITLE,
        "description": "Guvernul și BNR au aprobat 100 miliarde pentru Timișoara și Cluj-Napoca.",
        "published": t0.isoformat(),
    }
    echo_it = {
        "url": "https://echo.ro/b",
        "original_link": "https://echo.ro/b",
        "source_name": "Echo",
        "title": ARTICLE_TITLE,
        "original_title": ARTICLE_TITLE,
        "description": "Guvernul a aprobat 100 miliarde pentru Timișoara.",
        "published": (t0 + timedelta(minutes=30)).isoformat(),
    }
    html_root = ("<html><body>" + "<p>Guvernul și BNR au aprobat bugetul cu 100 miliarde de lei "
                 "pentru Timișoara și Cluj-Napoca în ședința de azi.</p>" * 6 + "</body></html>").encode("utf-8")
    html_echo_v1 = ("<html><body>" + "<p>Guvernul a aprobat bugetul cu 100 miliarde de lei "
                    "pentru Timișoara în ședința de azi.</p>" * 6 + "</body></html>").encode("utf-8")
    html_echo_v2 = ("<html><body>" + "<p>Guvernul a aprobat bugetul cu 250 miliarde de lei "
                    "pentru București și Iași în ședința de azi.</p>" * 6 + "</body></html>").encode("utf-8")

    raspunsuri = {
        root_it["url"]: html_root,
        echo_it["url"]: html_echo_v1,
    }

    def fake_deschide(req, timeout=None):
        u = getattr(req, "full_url", str(req))
        return _Raspuns(raspunsuri[u])

    monkeypatch.setattr(fetch, "_deschide", fake_deschide)
    fetch_deep.fetch_deep([[root_it, echo_it]], meta_path=meta_path)
    assert fetch_deep.stats().get("SILENT_EDIT_DIRTY", 0) == 0

    # Modificăm DOAR articolul ECHO -> nu trebuie să declanșeze SILENT_EDIT_DIRTY
    raspunsuri[echo_it["url"]] = html_echo_v2
    fetch_deep.fetch_deep([[root_it, echo_it]], meta_path=meta_path)
    assert fetch_deep.stats().get("SILENT_EDIT_DIRTY", 0) == 0


def test_scrub_processed_curata_cheile_tranzitorii_deep():
    from generator import state

    art = {
        "url": "https://s1.ro/a",
        "title": "Titlu",
        "processed_by": "gemini",
        "original_title": "Orig",
        "description": "Desc",
        "_deep_sentences": {"S1.1": "Propoziție."},
        "_deep_mode": "FULL_TEXT",
        "_deep_anchors": ["NUM:10"],
        "_epistemic_role": "ROOT",
        "_caused_dirty": False,
    }
    state._scrub_processed([art])
    for k in ("_deep_sentences", "_deep_mode", "_deep_anchors", "_epistemic_role", "_caused_dirty"):
        assert k not in art



def test_drift_compara_esantion_cu_esantion_nu_trunchiat_cu_intreg():
    """Un articol lung (peste plafonul de 80 de ancore), cu SHA schimbat dar aceleași fapte,
    NU e „modificare tăcută”: înainte, setul stocat (trunchiat alfabetic) era comparat cu
    setul proaspăt întreg și orice widget schimbat murdărea clusterul."""
    anchors = {f"NUM:{i}" for i in range(150)} | {f"ENT:e{i}" for i in range(60)}
    stocat = set(fetch_deep.anchor_sample(anchors))
    assert len(stocat) == fetch_deep.MAX_ANCHORS_STORED
    assert set(fetch_deep.anchor_sample(set(anchors))) == stocat      # stabil
    assert not fetch_deep.check_if_silent_edit_causes_dirty(
        "ROOT", "sha-vechi", "sha-nou", stocat, set(fetch_deep.anchor_sample(anchors)))
    # o schimbare reală de fapte (jumătate din cifre înlocuite) rămâne detectată
    schimbat = {f"NUM:{i}" for i in range(75, 225)} | {f"ENT:e{i}" for i in range(60)}
    assert fetch_deep.check_if_silent_edit_causes_dirty(
        "ROOT", "sha-vechi", "sha-nou", stocat, set(fetch_deep.anchor_sample(schimbat)))
