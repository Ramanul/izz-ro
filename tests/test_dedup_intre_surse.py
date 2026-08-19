"""Aceeasi stire citita din doua feeduri nu trebuie publicata de doua ori.

Masurat pe starea din 2026-08-07 (2766 articole): 57 de perechi aveau acelasi `url`,
toate 57 din aceeasi combinatie — `digi24` (RSS general) si `extern`
(`digi24.ro/rss/stiri/externe`, submultime a aceluiasi site). 56 din 57 aveau slug-uri
diferite, deci erau doua pagini distincte pe site, cu doua titluri scrise separat de AI.
Pe un site al carui brand e „Zero Zgomot", asta se vede.

Mecanismul: `main.run` filtra itemele noi DOAR fata de starea existenta
(`i["url"] not in known`), niciodata intre ele. Doua iteme cu acelasi url in acelasi
`raw` treceau amandoua, primeau fiecare cate un apel AI si intrau amandoua in `combined`,
care e o concatenare de liste, nu un dict.

`state.merge()` — pe dict, deci imuna prin constructie — promite in docstring exact
dedup-ul asta, dar nu e chemata nicaieri in productie: singurul ei apelant e
`tests/test_state.py`. De aceea testul de acolo trecea in timp ce calea reala nu deduplica.
"""
from datetime import datetime, timedelta, timezone

import pytest

from generator import main, moderation, state

URL = "https://www.digi24.ro/stiri/externe/o-stire-oarecare-3896871"


def _item(sursa: str, nume: str, titlu: str, url: str = URL) -> dict:
    """Forma minima a unui item asa cum il intoarce fetch."""
    return {
        "url": url,
        "source": sursa,
        "source_name": nume,
        "title": titlu,
        "original_title": titlu,
        "description": "",
        "category": "extern",
        "model": None,
        "published": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    }


@pytest.fixture
def ruleaza(tmp_path, monkeypatch):
    """Ruleaza main.run pe un set de iteme date, fara retea si fara AI."""
    def _run(items, stare_initiala="[]"):
        p = tmp_path / "articles.json"
        p.write_text(stare_initiala, encoding="utf-8")
        monkeypatch.setattr(state, "STATE_PATH", str(p))
        monkeypatch.setattr(main.fetch, "fetch_all", lambda: (items, []))
        monkeypatch.setattr(main, "get_provider", lambda: None)
        return main.run(dry_run=True)
    return _run


def test_acelasi_url_din_doua_surse_intra_o_singura_data(ruleaza):
    """Regresia care a produs 57 de pagini duplicate pe site."""
    stats = ruleaza([
        _item("extern", "Digi24 Extern", "Nord-coreenii indemnati sa manance supa de caine"),
        _item("digi24", "Digi24", "Coreea de Nord recomanda supa de caine"),
    ])
    assert stats["new"] == 1, "al doilea exemplar consuma un apel AI si devine a doua pagina"
    assert stats["total_known"] == 1


def test_castiga_primul_din_ordinea_de_fetch(ruleaza):
    """Care exemplar supravietuieste NU e indiferent.

    `fetch_all` intoarce itemele in ordinea din `config.SOURCES` (invariant documentat
    acolo, fiindca bugetul AI se consuma in aceeasi ordine). Deci „primul castiga"
    inseamna „sursa asezata mai sus in config castiga" — o regula pe care proprietarul
    o poate controla mutand sursa, nu un accident de dictionar.
    """
    stats = ruleaza([
        _item("extern", "Digi24 Extern", "varianta de la extern"),
        _item("digi24", "Digi24", "varianta de la digi24"),
    ])
    assert stats["new"] == 1
    assert stats["exemplare_duplicate"] == 1


def test_urluri_diferite_nu_sunt_atinse(ruleaza):
    """Contraexemplul: garda nu are voie sa uneasca stiri distincte."""
    stats = ruleaza([
        _item("extern", "Digi24 Extern", "prima", url=URL),
        _item("digi24", "Digi24", "a doua", url=URL + "-alta"),
    ])
    assert stats["new"] == 2
    assert stats["exemplare_duplicate"] == 0


def test_moderation_indexed_dedup_preserves_exact_event_rule():
    a = _item("extern", "Digi24", "Guvernul aprobă bugetul apărării pentru 2027", URL + "-a")
    b = _item("digi24", "Digi24", "Bugetul apărării pentru 2027 a fost aprobat de guvern", URL + "-b")
    c = _item("extern", "Digi24", "Echipa națională începe pregătirea pentru turneu", URL + "-c")
    out = moderation._dedup_visible([a, b, c])
    urls = {item["url"] for item in out}
    assert len(out) == 2
    assert URL + "-c" in urls
    assert urls & {URL + "-a", URL + "-b"}


def test_duplicatul_fata_de_starea_existenta_ramane_prins(ruleaza):
    """Vechea garda (fata de `existing`) nu trebuie slabita de cea noua."""
    stare = f'[{{"url": "{URL}", "title": "publicat ieri", "processed_by": "gemini"}}]'
    stats = ruleaza([_item("extern", "Digi24 Extern", "acelasi lucru, azi")], stare)
    assert stats["new"] == 0
    assert stats["exemplare_duplicate"] == 0, "ce e deja in stare nu se numara ca duplicat de fetch"
