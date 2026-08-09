"""Garda de ingestie: respinge continut ostil venit prin feeduri terte.

De ce exista fisierul asta
--------------------------
izz.ro citeste automat feedurile a ~1274 de primarii. Un site de primarie e cel mai des
WordPress neactualizat, deci o parte din ele SUNT compromise in orice moment dat. Pe
2026-08-09 primariarovinari.ro (site real, CMS luat de atacator) a impins 8 pagini de warez
pe izz.ro, intercalate cu anunturi autentice. Modelul de amenintare nu e „o sursa a gresit",
e „o sursa din o mie e controlata de un atacator si nu stim care".

Consecinta de arhitectura: **niciun text venit dintr-un feed nu e de incredere**, nici macar
de la o institutie publica. Filtrarea per-sursa (`moderation.yaml`) e reactiva — trebuie sa
vezi problema ca s-o opresti. Fisierul asta e partea proactiva: reguli pe CONTINUT, care nu
au nevoie sa stie ce sursa e compromisa.

Cele cinci straturi si de ce fiecare
------------------------------------
1. **Markup care a supravietuit curatarii.** `util.clean_html` scotea tagurile si ABIA APOI
   decoda entitatile — deci `&lt;img onload=...&gt;` trecea de taiere si redevenea `<img ...>`
   dupa decodare. Evaziune clasica prin dubla codare. Ordinea e reparata in `util.py`, iar
   regula asta prinde ce mai scapa (inclusiv markup construit prin alte codari).
2. **Payload de script.** `onload=`, `data:...;base64,`, `String.fromCharCode`, `eval(`.
   Chiar escapat si afisat ca text, e semnatura unui atac, nu a unei stiri.
3. **Amestec de alfabete in acelasi cuvant (homoglife).** Atacul folosea „To𝚛rent" (U+1D69B,
   litera matematica) si „Frее" (е chirilic). Scopul lui e sa treaca de listele de cuvinte;
   scopul nostru e sa nu ne bazam pe liste de cuvinte. Ideea e din Unicode TR39
   („mixed-script confusables"), restransa la nivel de CUVANT: un text romanesc poate contine
   legitim un nume rusesc scris chirilic ca token separat, dar NU litere din doua alfabete
   in acelasi cuvant. Literele matematice (blocul U+1D400-U+1D7FF) se resping direct — nicio
   stire reala nu le foloseste.
4. **Markere de warez.** Lista de cuvinte, ultimul strat, nu primul: e cel mai usor de ocolit.
5. **Titlu-gunoi.** `ki0esb8vxpjuiwknjx` — pagina-canar prin care atacatorul isi verifica
   indexarea. Un titlu de stire nu e un singur token de 12+ caractere cu cifre in el.

Regula de proiectare: garda RESPINGE itemul, nu incearca sa-l repare. E §7 din CLAUDE.md
(„daca nu poate atinge bara Zero Zgomot, SARE itemul") aplicata la securitate. Un articol
pierdut e gratis; unul publicat gresit costa reputatia site-ului.

Cine pazeste paznicul (LECTII L5)
---------------------------------
Modul de esec al unei garzi e sa moara in tacere: cineva strica un regex, garda inceteaza sa
mai prinda ceva, iar site-ul republica warez fara ca nimic sa scarțaie. De-aia `autotest()`
ruleaza corpusul REAL de atac (titlurile de pe Rovinari, verbatim) la fiecare pornire de
pipeline si **arunca exceptie**, oprind build-ul, daca garda nu mai prinde. Corpusul contine
si exemple curate: o garda care respinge tot e la fel de moarta ca una care nu respinge nimic,
doar ca esueaza in cealalta directie.
"""
import re
import unicodedata

# --- 1. markup care a supravietuit curatarii --------------------------------------------
# `<a `, `</p>`, `<img/>` si varianta inca codata `&lt;img`. Deliberat NU prinde un `<`
# singuratic („temperaturi < 0 grade"): cere litera imediat dupa paranteza.
_MARKUP_RE = re.compile(r"<\s*/?\s*[a-z][a-z0-9]{0,9}[\s/>]|&lt;\s*/?\s*[a-z]", re.I)

# --- 2. semnaturi de payload executabil -------------------------------------------------
_PAYLOAD_RE = re.compile(
    r"\bon(?:load|error|click|mouseover|focus)\s*=|"
    r"javascript\s*:|"
    r"data\s*:\s*[a-z/]+\s*;\s*base64\s*,|"
    r"String\s*\.\s*fromCharCode|"
    r"\beval\s*\(|"
    r"\batob\s*\(|"
    r"document\s*\.\s*(?:getElementById|write|cookie)|"
    r"window\s*\.\s*(?:location|open)\b|"
    r"<\s*script",
    re.I,
)

# --- 4. markere de warez ----------------------------------------------------------------
# Cuvinte care nu apar intr-o stire romaneasca legitima decat ca SUBIECT al unui articol
# despre piraterie — caz in care pierdem un articol pe an. Compromis acceptat deliberat:
# vezi `specs/securitate-ingestie.md` §„Fals-pozitive asumate".
_WAREZ_RE = re.compile(
    r"\btorrent\b|\bcrack(?:ed|\s*fixed)?\b|\bkeygen\b|\bkmspico\b|\brepack\b|\bnulled\b|"
    r"\belamigos\b|\bskidrow\b|\bfitgirl\b|\bweb-?dl\b|\bwebrip\b|\bdvd-?rip\b|"
    r"\bbd-?rip\b|\bhd-?rip\b|\bx264\b|\bx265\b|\byify\b|\bgalaxyrg\b|\bsteam\s*[- ]?rip\b|"
    r"\bfull\s+version\b|\bserial\s+key\b|\bactivation\s+key\b|\bproduct\s+key\b|"
    r"\bfree\s+download\b|\bactivator\b|\blicense\s+key\b",
    re.I,
)

# blocul Unicode al literelor „matematice" (U+1D400-U+1D7FF): 𝐀 𝚊 etc. Se normalizeaza NFKC
# in litere ASCII, deci sunt exact unealta de evaziune — si au zero utilizare legitima aici.
_MATH_ALPHA = (0x1D400, 0x1D7FF)

_ALFABETE = ("LATIN", "CYRILLIC", "GREEK", "ARMENIAN", "HEBREW", "ARABIC")


def _alfabete_din_cuvant(cuvant: str) -> set:
    """Ce alfabete apar in cuvantul asta. `MATH` = litera din blocul matematic."""
    gasite = set()
    for ch in cuvant:
        if not ch.isalpha():
            continue
        if _MATH_ALPHA[0] <= ord(ch) <= _MATH_ALPHA[1]:
            gasite.add("MATH")
            continue
        nume = unicodedata.name(ch, "")
        for alfabet in _ALFABETE:
            if nume.startswith(alfabet):
                gasite.add(alfabet)
                break
    return gasite


def _are_homoglife(text: str) -> bool:
    """Litera matematica oriunde, sau doua alfabete in ACELASI cuvant."""
    for cuvant in text.split():
        alfabete = _alfabete_din_cuvant(cuvant)
        if "MATH" in alfabete or len(alfabete) > 1:
            return True
    return False


def _e_titlu_gunoi(titlu: str) -> bool:
    """Un singur token lung cu cifre in el — pagina-canar de indexare, nu titlu de stire.

    Cifrele sunt obligatorii in conditie tocmai ca sa NU respinga un cuvant romanesc lung
    folosit singur ca titlu („Responsabilitate", „Rectificare", „Convocator").
    """
    t = titlu.strip()
    if " " in t or len(t) < 12:
        return False
    return any(c.isdigit() for c in t) and any(c.isalpha() for c in t)


def verdict(titlu: str, corp: str = "") -> str | None:
    """`None` daca itemul e curat, altfel motivul respingerii (scurt, pentru log).

    Titlul si corpul se verifica impreuna pentru straturile 1, 2 si 4 (payloadul poate sta
    in oricare), dar homoglifele si titlul-gunoi se judeca DOAR pe titlu: corpul unui articol
    legitim poate cita un nume strain, titlul aproape niciodata.
    """
    tot = f"{titlu} {corp}"
    if _MARKUP_RE.search(tot):
        return "markup in text dupa curatare"
    if _PAYLOAD_RE.search(tot):
        return "semnatura de payload executabil"
    if _are_homoglife(titlu):
        return "homoglife in titlu (amestec de alfabete)"
    if _WAREZ_RE.search(tot):
        return "marker de warez"
    if _e_titlu_gunoi(titlu):
        return "titlu-gunoi (token unic alfanumeric)"
    return None


def e_curat(titlu: str, corp: str = "") -> bool:
    """Zahar pentru `verdict(...) is None`."""
    return verdict(titlu, corp) is None


# --- dead man's switch ------------------------------------------------------------------
# Titluri VERBATIM de pe primariarovinari.ro, 8-9 aug 2026, cu homoglifele intacte. Daca un
# regex se strica, astea nu mai sunt prinse si `autotest()` opreste build-ul.
_CORPUS_OSTIL = [
    ("Stellar Blade Crack Fixed ElAmigos Release Desktop Version 2026", ""),
    ("Office 2021 Standard Frее Download To\U0001d69brent", ""),
    ("The Brink of War 2026 \U0001d405\U0001d69e\U0001d5a5\U0001d5a5 \U0001d40c\U0001d698\U0001d69f\U0001d422\U0001d452", ""),
    ("ki0esb8vxpjuiwknjx", "hjrk4e7wz7iq6hhwq7bdcdej52 Ultima modificare: 08.08.26"),
    ("MS Office Optimized VL Final Torrent", ""),
    ("The First Berserker: Khazan Deluxe Edition Steam Rip MEGA", ""),
    ("Mariinka 2026 WEB-DL 4K Dual Audio Available Torrent", ""),
    ("Tempal: Item no Chikara 2026 Pre-DVDRip 2160p", ""),
    ("Anunt oarecare", 'HASH-SUM: 2fb2 <img src="data:image/gif;base64,R0lGODlh" onload=window.genC>'),
    ("Anunt oarecare", "&lt;script&gt;alert(1)&lt;/script&gt;"),
]

# Anunturi REALE de primarie, inclusiv cele trei legitime de pe Rovinari. O garda care le
# respinge e stricata in cealalta directie si trebuie sa opreasca build-ul la fel de tare.
_CORPUS_CURAT = [
    ("Anunț privind colectarea separată a deșeurilor", "Ultima modificare: 07.08.26"),
    ("REZULTAT selecție dosar – Concurs pentru ocuparea funcției contractuale de execuție,"
     " vacantă, de îngrijitor", "Ultima modificare: 04.08.26 de către Adriana S."),
    ("Licitații parcări reședință pentru data de 13-08-2026, ora 17:00",
     "Primăria organizează licitație pentru 24 de locuri de parcare."),
    ("Convocator", "Ședință ordinară a Consiliului Local, joi, ora 14:00."),
    ("Temperaturi de până la 39 de grade în Oltenia", "ANM a emis cod galben de caniculă."),
    ("Vladimir Putin a semnat decretul", "Președintele rus a semnat un decret privind..."),
]


class GardaStricata(RuntimeError):
    """Garda nu-si mai face treaba. Build-ul NU are voie sa continue."""


def autotest() -> int:
    """Ruleaza corpusul de atac si pe cel curat. Arunca `GardaStricata` la orice abatere.

    Returneaza numarul de cazuri verificate, ca sa apara o cifra in logul de build: o garda
    care ruleaza 0 cazuri e o garda dezactivata din greseala.
    """
    scapate = [t for t, c in _CORPUS_OSTIL if e_curat(t, c)]
    respinse_gresit = [(t, verdict(t, c)) for t, c in _CORPUS_CURAT if not e_curat(t, c)]

    if scapate or respinse_gresit:
        raport = []
        if scapate:
            raport.append("NU mai prinde continut ostil: " + " | ".join(scapate))
        if respinse_gresit:
            raport.append("respinge continut LEGITIM: "
                          + " | ".join(f"{t!r} -> {m}" for t, m in respinse_gresit))
        raise GardaStricata("; ".join(raport))

    return len(_CORPUS_OSTIL) + len(_CORPUS_CURAT)
