"""Garda de publicare (`render._fara_date_viitoare`): un `published` din viitor nu ajunge
niciodata in pagini, feed, sitemap sau pe 404.

Cazul real (Voiteg/Retim, raportat 3 oct 2026): selectorul de data al sursei prindea titlul
cardului, iar titlul continea data de EVENIMENT („colectare deseuri 01.01.2027") — recordul
a intrat in stare cu `published` in 2027 si a stat primul in feed si in sitemap-ul de stiri.
`_clamp_future` prinde doar itemele NOI la ingest; `state.merge()` nu reia URL-urile deja
stocate, deci garda trebuie sa existe la PUBLICARE, nu doar la intrare.
"""
from datetime import datetime, timedelta, timezone

from generator.render import _fara_date_viitoare

ACUM = datetime.now(timezone.utc)


def test_articolul_din_viitor_nu_se_publica():
    rau = {"url": "https://ex.ro/a", "published": "2027-01-01T00:00:00+00:00"}
    ok = {"url": "https://ex.ro/b",
          "published": (ACUM - timedelta(days=1)).isoformat()}
    out = _fara_date_viitoare([ok, rau])
    assert [a["url"] for a in out] == [ok["url"]]


def test_marja_de_48h_mentine_articolul_legitim():
    """Data-fara-ora de „mâine" e legitimă pentru o știre publicată diseară (ca la
    `_clamp_future`): sub 48 h rămâne, peste 48 h cade."""
    in_marja = {"url": "https://ex.ro/m",
                "published": (ACUM + timedelta(hours=47)).isoformat()}
    peste_marja = {"url": "https://ex.ro/p",
                   "published": (ACUM + timedelta(hours=49)).isoformat()}
    out = _fara_date_viitoare([in_marja, peste_marja])
    assert [a["url"] for a in out] == [in_marja["url"]]


def test_fara_published_ramane_in_lista():
    out = _fara_date_viitoare([{"url": "https://ex.ro/x", "published": ""}])
    assert len(out) == 1


def test_data_naiva_se_trateaza_ca_utc():
    rau = {"url": "https://ex.ro/n", "published": "2027-01-01T00:00:00"}  # fara offset
    out = _fara_date_viitoare([rau])
    assert out == []


def test_ordinea_relative_se_pastreaza():
    vechi = {"url": "https://ex.ro/1", "published": "2026-09-01T00:00:00+00:00"}
    nou = {"url": "https://ex.ro/2", "published": "2026-09-30T00:00:00+00:00"}
    out = _fara_date_viitoare([nou, vechi])
    assert [a["url"] for a in out] == [nou["url"], vechi["url"]]
