"""Site-ul nu deduce cititorul din ce citește și nu rulează cod de măsurare în browserul lui.

DE CE EXISTA (2026-10-23, specs/plan-paradigma-izz.md §5 D6). Până atunci `personalize.js`
construia, după un singur buton de consimțământ, un profil din clicuri și timp de lectură,
reordona rubricile („talmeș-balmeș cu rubricile", raportat de proprietar pe 2026-09-09, chiar
de pe profilul lui), insera „Pentru tine" și pornea Google Analytics + Microsoft Clarity. Toate
au ieșit; rămâne alegerea EXPLICITĂ a județului.

Testele de mai jos apără proprietatea, nu implementarea: orice semnal comportamental nou
(click, derulare, timp pe pagină) sau orice gazdă de măsurare nouă trebuie să treacă prin
această gardă, adică printr-o decizie scrisă, nu printr-un import tăcut. Repo-ul n-are runner
de JS, deci garda e pe sursă; comportamentul real se verifică în Chromium (PR-ul care a
introdus-o: cereri externe 0, localStorage gol la încărcare, județul salvat doar la `change`).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator import render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAZDE_MASURARE = ("googletagmanager", "google-analytics", "analytics.google", "clarity.ms",
                  "cloudflareinsights", "gtag(", "dataLayer")


def _citeste(*parti) -> str:
    with open(os.path.join(ROOT, *parti), encoding="utf-8") as fh:
        return fh.read()


def _js() -> str:
    return _citeste("static", "judet.js")


def test_motorul_de_profilare_nu_mai_exista():
    assert not os.path.exists(os.path.join(ROOT, "static", "personalize.js"))
    js = _js()
    for semn in ("trackClick", "trackTime", "reorderNav", "renderForYou", "Pentru tine",
                 "izz_profile_v1'", "MIN_INTERACTIONS"):
        assert semn not in js, semn


def test_singurul_eveniment_ascultat_e_alegerea_cititorului():
    """Un listener de click, scroll sau vizibilitate e începutul unui profil."""
    evenimente = set(re.findall(r"addEventListener\(\s*['\"](\w+)['\"]", _js()))
    assert evenimente <= {"change", "DOMContentLoaded"}, evenimente


def test_judetul_se_scrie_doar_la_cerere():
    """La încărcare nu se scrie nimic: singurul `setItem` e în handlerul de `change`."""
    js = _js()
    assert js.count("setItem(") == 1
    assert js.index("addEventListener('change'") < js.index("setItem(")
    assert "localStorage.setItem(KEYJ, sel.value)" in js
    assert "localStorage.removeItem(KEYJ)" in js        # „Toată țara" nu lasă urme


def test_curatenia_atinge_doar_ce_a_pus_versiunea_veche():
    js = _js()
    assert r"/^izz_(profile|consent)/" in js
    assert r"/^(_ga|_gid|_gat|_clck|_clsk)/" in js
    assert "Max-Age=0" in js


def test_nicio_gazda_de_masurare_in_scripturi_si_sabloane():
    for folder in ("static", "templates"):
        for nume in os.listdir(os.path.join(ROOT, folder)):
            if not nume.endswith((".js", ".html")):
                continue
            text = _citeste(folder, nume)
            for gazda in GAZDE_MASURARE:
                assert gazda not in text, f"{folder}/{nume}: {gazda}"


def test_csp_nu_permite_masurare_externa(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_headers()
    hdr = (tmp_path / "_headers").read_text(encoding="utf-8")
    csp = re.search(r"Content-Security-Policy: (.+)", hdr).group(1)
    for gazda in ("google", "clarity", "cloudflareinsights"):
        assert gazda not in csp, gazda
    assert "connect-src 'self' https://tiles.openfreemap.org;" in csp


def test_sablonul_incarca_scriptul_versionat_fara_bara_de_consimtamant():
    base = _citeste("templates", "base.html")
    assert "static/judet.js?v={{ asset_ver['judet.js'] }}" in base
    assert "#consimtamant" not in base
    assert "judet.js" in render._asset_ver()


def test_textele_publice_descriu_ce_face_codul():
    """O promisiune pe care codul n-o mai ține e mai rea decât una lipsă."""
    privacy = _citeste("content", "legal", "privacy.md")
    # numele furnizorilor vechi rămân DOAR în paragraful istoric (cine a acceptat are dreptul
    # să afle ce s-a întâmplat cu datele lui); prezentul nu are voie să le descrie active
    for disparut in ("activăm Google Analytics", "activăm Microsoft Clarity", "◎",
                     "bara de consimțământ", "Folosim Cloudflare Web Analytics", "„Activează\""):
        assert disparut not in privacy, disparut
    assert "izz_judet" in privacy
    method = _citeste("content", "legal", "method.md")
    assert "setări de consimțământ" not in method
    assert "toți cititorii văd același flux" in method
