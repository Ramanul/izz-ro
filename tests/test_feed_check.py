"""Regresie: `tools/feed_check.py` nu are voie sa aiba propriul lui fetch/retry/parsare.

Pana la 2026-07-25, feed_check isi reimplementa citirea RSS (urllib.request + feedparser
proprii), in loc sa cheme `generator.fetch._fetch_one_guarded` -- exact functia pe care
`fetch_all()` o foloseste in productie, pentru orice sursa (RSS, sitemap_news, html_list).

Masurat: doua rulari `feedcheck` la ~15 minute distanta, pe cod aproape identic, au raportat
1 sursa moarta si respectiv 74 -- desi verificare independenta a 4 din cele 74 (contributors,
bookhub, pl_ialomita_bucu, stirilemoldovei) a aratat ca sunt vii. Testele de mai jos nu pot
reproduce acel puseu (e o limitare tranzitorie de retea, nu de cod), dar verifica invariantul
pe care fix-ul il stabileste: rezultatul afisat de feed_check trebuie sa fie EXACT ce intoarce
fetch.py, fara nicio logica de fetch/retry in plus, ascunsa in feed_check insusi. Daca cineva
reintroduce un fetch propriu in feed_check, patch-ul de mai jos nu mai are efect si testele pica.
"""
import contextlib
import io
import sys

import tools.feed_check as feed_check
from generator import config


def _run(monkeypatch, sources, results, argv=()):
    """`results`: {key: (arts, err)} -- ce ar intoarce _fetch_one_guarded pentru fiecare sursa."""
    monkeypatch.setattr(config, "SOURCES", sources)
    monkeypatch.setattr(sys, "argv", ["feed_check.py", *argv])
    monkeypatch.setattr(feed_check, "RETRY_PAUZA_S", 0.0)  # suita nu doarme intre incercari

    def fake_guarded(key, source, cache=None):
        return results[key]

    # Patch DOAR simbolul pe care feed_check il cheama. Daca feed_check ar mai avea un
    # fetch propriu (bug-ul dinainte de fix), acest patch n-ar avea niciun efect vizibil.
    monkeypatch.setattr(feed_check, "_fetch_one_guarded", fake_guarded)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = feed_check.main()
    return code, buf.getvalue()


_SOURCES = {
    "alive":   {"name": "Alive",   "url": "https://example.invalid/alive",   "category": "general"},
    "empty":   {"name": "Empty",   "url": "https://example.invalid/empty",   "category": "general"},
    "limited": {"name": "Limited", "url": "https://example.invalid/limited", "category": "general"},
    "dead":    {"name": "Dead",    "url": "https://example.invalid/dead",    "category": "general"},
}


def test_feed_check_reflects_exactly_what_fetch_one_guarded_returns(monkeypatch):
    results = {
        "alive":   ([{"published": "2026-07-20T00:00:00+00:00"}], None),
        "empty":   ([], None),
        "limited": ([], "limited: HTTP Error 429: Too Many Requests"),
        "dead":    ([], "dead: HTTP Error 404: Not Found"),
    }

    code, out = _run(monkeypatch, _SOURCES, results)

    assert code == 1  # empty + dead -> FAIL
    assert "ok   alive" in out
    assert "GOL  empty" in out
    assert "LIMIT limited" in out and "nu inseamna sursa moarta" in out
    assert "DEAD dead" in out and "https://example.invalid/dead" in out
    assert "FAIL: 2 surse" in out
    assert "ATENTIE: 1 surse rate-limitate" in out


def test_429_dupa_retry_reusit_e_raportat_ok(monkeypatch):
    """Cazul central al bug-ului: o sursa care raspunde 429 o data si reuseste la retry-ul
    din fetch.py TREBUIE sa fie raportata 'ok', pentru ca asta e exact ce vede si productia
    (fetch_all cheama acelasi _fetch_one_guarded, cu acelasi retry). Un verificator cu fetch
    propriu, fara acelasi retry, ar fi raportat-o gresit DEAD sau LIMIT."""
    sources = {"alive": _SOURCES["alive"]}
    results = {"alive": ([{"published": "2026-07-20T00:00:00+00:00"}] * 3, None)}

    code, out = _run(monkeypatch, sources, results)

    assert code == 0
    assert "ok   alive" in out and "3 articole" in out


def test_type_sources_folosesc_acelasi_apel(monkeypatch):
    """sitemap_news / html_list treceau deja prin _fetch_one; testul confirma ca acum si
    RSS-ul simplu trece prin ACELASI apel unic, nu printr-o ramura separata."""
    sources = {
        "sitemap": {"name": "Sitemap", "url": "https://example.invalid/sitemap.xml",
                    "category": "auto", "type": "sitemap_news"},
        "rss":     _SOURCES["alive"],
    }
    results = {
        "sitemap": ([{"published": "2026-07-24T00:00:00+00:00"}], None),
        "rss":     ([{"published": "2026-07-20T00:00:00+00:00"}], None),
    }

    code, out = _run(monkeypatch, sources, results)

    assert code == 0
    assert "ok   sitemap" in out and "sitemap_news," in out
    assert "ok   rss" in out


def test_category_filter_still_works(monkeypatch):
    results = {
        "alive": ([{"published": "2026-07-20T00:00:00+00:00"}], None),
        "empty": ([], None),
    }
    code, out = _run(monkeypatch, {"alive": _SOURCES["alive"], "empty": _SOURCES["empty"]},
                      results, argv=("general",))

    assert code == 1
    assert "alive" in out and "empty" in out


def test_challenge_servit_cu_200_nu_e_sursa_moarta(monkeypatch):
    """Textul „challenge anti-bot servit cu 200 (sursa NU e moarta)" venea din fetch.py, dar
    feed_check il numara DEAD — verificatorul contrazicea sursa de adevar pe care o cheama.
    Efectul masurat: feedcheck rosu la fiecare rulare programata (46 din 46, 25 iul - 10 oct).
    """
    sources = {"challenged": _SOURCES["alive"]}
    results = {"challenged": ([], "challenged: challenge anti-bot servit cu 200 (sursa NU e moarta)")}

    code, out = _run(monkeypatch, sources, results)

    assert code == 0, "un challenge de pe IP de datacenter nu e un esec de sursa"
    assert "BLOCAT challenged" in out
    assert "NEVERIFICABIL de aici" in out
    assert "DEAD" not in out


def test_a_doua_incercare_scapa_de_o_pana_tranzitorie(monkeypatch):
    """Prima incercare poate cadea pe o pana de moment; a doua, pe acelasi cod, raspunde."""
    sources = {"puls": _SOURCES["alive"]}
    apeluri = {"n": 0}

    def fake_guarded(key, source, cache=None):
        apeluri["n"] += 1
        if apeluri["n"] == 1:
            # Pana de ROUTING (nu rate-limit — ala nu se reincearca imediat, gazda limiteaza
            # dupa frecventa si o a doua cerere o incalca din nou).
            return [], f"{key}: <urlopen error timed out>"
        return [{"published": "2026-10-11T00:00:00+00:00"}], None

    monkeypatch.setattr(config, "SOURCES", sources)
    monkeypatch.setattr(sys, "argv", ["feed_check.py"])
    monkeypatch.setattr(feed_check, "_fetch_one_guarded", fake_guarded)
    monkeypatch.setattr(feed_check, "RETRY_PAUZA_S", 0.0)

    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = feed_check.main()

    assert apeluri["n"] == 2, "sursa a fost reincercata o data"
    assert code == 0
    assert "ok   puls" in buf.getvalue()


def test_esecul_este_adnotat_cu_numele_surselor(monkeypatch, capsys):
    """Jurnalele binare nu sunt accesibile din sandbox; adnotarea da verdictul in UI/API."""
    sources = {"moarta": _SOURCES["dead"], "goala": _SOURCES["empty"]}
    results = {"moarta": ([], "moarta: HTTP Error 404: Not Found"), "goala": ([], None)}

    code, out = _run(monkeypatch, sources, results)

    assert code == 1
    assert "::error title=feed check::" in out
    assert "moarta" in out.split("::error title=feed check::")[1]
