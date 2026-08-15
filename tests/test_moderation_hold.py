"""Poarta `hold_important` — testeaza CABLAJUL, nu doar existenta steagului.

Context (2026-08-15): pana azi `hold_important` era un steag mincinos. `moderation.yaml` il
documenta ca „clusterele C/importante asteapta aprobare inainte de publicare", iar tot ce facea
era un `print` in `main.py:359`. Setat pe `true`, sintezele C se publicau exact ca inainte, in
timp ce operatorul credea ca sunt retinute. Conteaza dincolo de igiena: exceptarea de la AI Act
art. 50 se sprijina pe control editorial, iar steagul asta e singurul mecanism din repo care il
poate implementa.

Testele sunt scrise ca sa PICE daca poarta e scoasa din `moderation.apply` — nu ca sa confirme
ca exista o cheie in DEFAULTS. Un test care verifica doar `"approved" in DEFAULTS` ar fi trecut
si inainte de fix, cand steagul nu bloca nimic.
"""
import textwrap

from generator import moderation


def _mod(**over) -> dict:
    """Configurare de moderare completa; `apply` citeste unele chei cu indexare directa."""
    base = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
            for k, v in moderation.DEFAULTS.items()}
    base.update(over)
    return base


def _art(url: str, titlu: str, model: str = "C", **over) -> dict:
    """Articol minim care trece garda de continut (titluri romanesti, banale, distincte)."""
    a = {
        "url": url,
        "original_link": url,
        "title": titlu,
        "original_title": titlu,
        "teaser": "Consiliul local a aprobat bugetul pentru anul in curs.",
        "model": model,
        "source": "sursa_test",
        "source_lang": "ro",
        "published": "2026-08-15T10:00:00+00:00",
        "sources": [{"name": "Sursa Test", "url": url}],
    }
    a.update(over)
    return a


# --- comportamentul implicit nu se schimba -----------------------------------------------

def test_implicit_steagul_e_stins_si_sintezele_C_se_publica():
    """Fara `hold_important`, nimic nu se retine — regresia cea mai scumpa ar fi aici."""
    arts = [_art("https://ex.ro/a", "Primaria Cluj a aprobat bugetul pe 2026")]
    out = moderation.apply(arts, _mod())
    assert len(out) == 1


def test_approved_lipsa_din_config_nu_crapa():
    """`moderation.yaml` vechi, fara cheia `approved`, trebuie sa mearga mai departe."""
    mod = _mod(hold_important=True)
    del mod["approved"]
    out = moderation.apply([_art("https://ex.ro/a", "Spitalul judetean primeste aparatura noua")], mod)
    assert out == []


# --- poarta propriu-zisa -----------------------------------------------------------------

def test_hold_retine_sinteza_C():
    arts = [_art("https://ex.ro/a", "Primaria Cluj a aprobat bugetul pe 2026")]
    out = moderation.apply(arts, _mod(hold_important=True))
    assert out == [], "sinteza C s-a publicat desi hold_important=true"


def test_hold_nu_atinge_articolele_B():
    """Poarta e pe sintezele multi-sursa. Un articol B retinut ar goli site-ul."""
    arts = [_art("https://ex.ro/b", "Trenul de Timisoara circula cu intarziere", model="B")]
    out = moderation.apply(arts, _mod(hold_important=True))
    assert len(out) == 1


def test_aprobarea_pe_url_lasa_sa_treaca_doar_articolul_aprobat():
    arts = [
        _art("https://ex.ro/aprobat", "Primaria Cluj a aprobat bugetul pe 2026"),
        _art("https://ex.ro/retinut", "Spitalul judetean primeste aparatura medicala noua"),
    ]
    out = moderation.apply(arts, _mod(hold_important=True, approved=["https://ex.ro/aprobat"]))
    assert [a["url"] for a in out] == ["https://ex.ro/aprobat"]


def test_aprobarea_normalizeaza_url_ul():
    """`approved` trece prin `normalize_url`, ca `blocklist_urls` — altfel un slash in plus
    scris de om in yaml ar face aprobarea sa para ignorata."""
    arts = [_art("https://ex.ro/a", "Primaria Cluj a aprobat bugetul pe 2026")]
    out = moderation.apply(arts, _mod(hold_important=True, approved=["https://ex.ro/a/"]))
    assert len(out) == 1


# --- ordinea: retinerea vine dupa respingeri ---------------------------------------------

def test_articolul_blocat_nu_ajunge_in_coada_de_aprobare(capsys):
    """Un URL de pe blocklist e respins, nu „in asteptare" — altfel coada se umple cu gunoi."""
    arts = [_art("https://ex.ro/rau", "Primaria Cluj a aprobat bugetul pe 2026")]
    out = moderation.apply(arts, _mod(hold_important=True, blocklist_urls=["https://ex.ro/rau"]))
    assert out == []
    assert "RETINUTE" not in capsys.readouterr().out


def test_lista_retinutilor_e_tiparita_cu_titlu_si_link(capsys):
    """Fara lista tiparita, operatorul nu are de unde sti ce asteapta aprobare."""
    moderation.apply(
        [_art("https://ex.ro/a", "Primaria Cluj a aprobat bugetul pe 2026")],
        _mod(hold_important=True),
    )
    iesire = capsys.readouterr().out
    assert "RETINUTE" in iesire
    assert "https://ex.ro/a" in iesire
    assert "Primaria Cluj" in iesire


# --- configurarea de pe disc -------------------------------------------------------------

def test_load_citeste_approved_din_yaml(tmp_path, monkeypatch):
    cale = tmp_path / "moderation.yaml"
    cale.write_text(textwrap.dedent("""\
        hold_important: true
        approved:
          - https://ex.ro/a
        """), encoding="utf-8")
    monkeypatch.setattr(moderation, "MOD_PATH", str(cale))
    mod = moderation.load()
    assert mod["hold_important"] is True
    assert mod["approved"] == ["https://ex.ro/a"]


def test_moderation_yaml_real_documenteaza_poarta():
    """Fisierul livrat nu mai are voie sa promita ce codul nu face (motivul acestui slice)."""
    with open(moderation.MOD_PATH, "r", encoding="utf-8") as fh:
        text = fh.read()
    assert "approved:" in text, "lipseste lista de aprobare din moderation.yaml"
    assert "art. 50" in text, "lipseste avertismentul legal de langa hold_important"
