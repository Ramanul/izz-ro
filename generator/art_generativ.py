"""Motor de Artă Generativă 3D Procedurală (SVG) pentru izz.ro.

Generează matematic compoziții editoriale 3D abstracte și geometrie editorială caldă,
inspirate din grafica publicațiilor contemporane (The Verge, Wired, The New Stack,
The Economist, FT Weekend, Monocle).

Reguli stricte de clasificare și domeniu tematic:
- Circuitele PCB (circuit_matrix), terenul topografic (wireframe_mesh) și valurile de date (parametric_waves)
  sunt STRICT REZERVATE știrilor unde Tehnologia, IT, AI, Cyber sau Telecom este subiectul real și central.
- Știrile non-tech nu primesc NICIODATĂ aceste trei motive tech, indiferent de secțiune.
- Toate celelalte domenii au motive semantice dedicate:
  * Sănătate: forme luminoase/organice (organic_flow, cellular_harmony)
  * Auto/Trafic: drumuri, marcaje și perspectivă (road_perspective, perspective_lines)
  * Carieră/Educație: documente, pași de progres, diplome (progress_steps, document_lines)
  * Energie/Economic: prisme izometrice arhitecturale, bare financiare (isometric_prism, financial_bars)
  * Cultură/Turism: portaluri și arcade arhitecturale, repere de patrimoniu (architectural_arch, heritage_shapes)
  * Politică/Instituții: compoziții civice/instituționale, coloane (civic_columns, editorial_block)
  * Sport: teren, velodrom, arce sportive (field_curves, sport_geometry)
  * Fallback general: exclusiv grafică editorială neutră (geometrie caldă nobilă).
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata

# Dimensiuni cadru compozițional SVG (raport standard card ~1.9:1)
W, H = 480, 252


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


def _seed(a: dict | None) -> bytes:
    if not a:
        return b"\x00" * 8
    val = (a.get("slug") or a.get("url") or a.get("title") or "default").encode("utf-8")
    return hashlib.sha256(val).digest()


def _normalize_text(text: str) -> str:
    """Normalizează textul la Unicode NFC și casefold."""
    if not text or not isinstance(text, str):
        return ""
    return unicodedata.normalize("NFC", text).casefold()


class DomeniuClasificat(str):
    """Clasă string inspectabilă ce reține domeniul tematic, scorul și motivul alegerii."""
    def __new__(cls, val: str, scor: float = 0.0, motiv: str = ""):
        obj = super().__new__(cls, val)
        obj.scor = scor
        obj.motiv = motiv
        return obj

    def __eq__(self, other):
        s = str(self)
        if s == "tech_ai" and other == "tech":
            return True
        if s == "tech" and other == "tech_ai":
            return True
        return super().__eq__(other)

    def __hash__(self):
        s = str(self)
        if s in ("tech_ai", "tech"):
            return hash("tech_ai")
        return super().__hash__()


# Expresii compuse cu greutate mare (+8 în titlu, +4 în rezumat)
_EXPRESII_DOMENII = {
    "sanatate": (
        "sănătate publică", "sanatate publica", "tratament medical", "spitalul clinic",
        "pacienți internați", "pacienti internati", "medici specialiști", "medici specialisti",
        "secția de chirurgie", "sectia de chirurgie", "chirurgie cardiovasculară", "chirurgie cardiovasculara",
        "tratament oncologic", "infecție respiratorie", "infectie respiratorie", "asistență medicală",
        "asistenta medicala", "ministerul sănătății", "ministerul sanatatii", "serviciul de ambulanță",
        "serviciul de ambulanta", "gardă de mediu", "garda de mediu", "sistemul sanitar",
        "boli cardiovasculare", "cancer pulmonar", "studiu clinic", "produse farmaceutice"
    ),
    "auto_trafic": (
        "poliția rutieră", "politia rutiera", "siguranță rutieră", "siguranta rutiera",
        "accident rutier", "accidente rutiere", "circulație rutieră", "circulatie rutiera",
        "codul rutier", "trafic rutier", "autostrada a1", "autostrada a2", "autostrada a3",
        "autostrada a7", "autostrada a8", "drumul național", "drumul national", "drumuri naționale",
        "permis de conducere", "inspecția tehnică", "inspectia tehnica", "registrul auto român",
        "registrul auto roman", "vehicul electric", "vehicule electrice", "mașini electrice",
        "masini electrice", "stații de încărcare", "statii de incarcare", "transport public",
        "infrastructură rutieră", "infrastructura rutiera", "rețeaua de drumuri", "reteaua de drumuri"
    ),
    "cariera_educatie": (
        "cv și recrutare", "cv si recrutare", "piața muncii", "piata muncii", "locuri de muncă",
        "locuri de munca", "evaluare națională", "evaluare nationala", "bacalaureat 2026",
        "inspectoratul școlar", "inspectoratul scolar", "titularizare profesori", "angajare tineri",
        "burse studențești", "burse studentesti", "învățământ superior", "invatamant superior",
        "an școlar", "an scolar", "salariul minim", "forță de muncă", "forta de munca",
        "codul muncii", "contract de muncă", "contract de munca", "angajatori români"
    ),
    "energie_economic": (
        "energie verde", "gaze naturale", "rețele electrice", "retele electrice",
        "bursa de valori", "fondul monetar", "banca centrală", "banca centrala",
        "rata inflației", "rata inflatiei", "politica monetară", "politica monetara",
        "prețul energiei", "pretul energiei", "panouri solare", "parcuri eoliene",
        "deficit bugetar", "impozit pe profit", "taxa pe valoarea adăugată",
        "banca transilvania", "omv petrom", "neptun deep", "banca națională",
        "banca nationala", "creștere economică", "crestere economica", "piața financiară",
        "piata financiara", "politici fiscale", "titluri de stat"
    ),
    "cultura_turism": (
        "patrimoniu cultural", "festivalul internațional", "festivalul international",
        "muzeul național", "muzeul national", "teatrul național", "teatrul national",
        "monument istoric", "monumente istorice", "obiective turistice", "destinație turistică",
        "destinatie turistica", "lansare de carte", "expoziție de artă", "expozitie de arta",
        "stagiune teatrală", "stagiune teatrala", "hoteluri și pensiuni", "hoteluri si pensiuni",
        "turism montan", "turism balnear", "turism cultural"
    ),
    "tech_ai": (
        "atac cibernetic", "atacuri cibernetice", "securitate cibernetică", "securitate cibernetica",
        "inteligență artificială", "inteligenta artificiala", "centre de date", "sisteme cloud",
        "modele lingvistice", "semiconductori avansați", "semiconductori avansati", "rețea 5g",
        "retea 5g", "tehnologie cuantică", "tehnologie cuantica", "baze de date",
        "inginerie software", "deep learning", "machine learning", "amenințare cibernetică",
        "amenintare cibernetica", "hacker etic", "ransomware masiv", "breșă de securitate",
        "bresa de securitate", "vulnerabilitate zero-day"
    ),
    "politica_institutii": (
        "curtea constituțională", "curtea constitutionala", "alegeri prezidențiale",
        "alegeri prezidentiale", "alegeri parlamentare", "ședință de guvern", "sedinta de guvern",
        "proiect de lege", "ordonanță de urgență", "ordonanta de urgenta", "partid politic",
        "moțiune de cenzură", "motiune de cenzura", "reuniune la vârf", "reuniune la varf",
        "relații diplomatice", "relatii diplomatice", "ministerul de externe", "adunarea generală",
        "adunarea generala", "politica externă", "politica externa", "scena politică", "scena politica"
    ),
    "sport": (
        "meci de fotbal", "liga campionilor", "echipa națională", "echipa nationala",
        "campionatul european", "campionatul mondial", "jocurile olimpice", "cupa româniei",
        "cupa romaniei", "turneu de tenis", "mare șlem", "mare slem", "etapa a",
        "meciul decisiv", "faza grupelor", "finala campionatului"
    )
}

# Cuvinte-cheie unice per domeniu (+3 în titlu, +1 în rezumat)
_KEYWORDS_DOMENII = {
    "sanatate": {
        "spital", "spitale", "spitalul", "spitalele", "medic", "medici", "medicul", "doctor", "doctori",
        "pacient", "pacienți", "pacienti", "pacientul", "tratament", "tratamente", "sănătate", "sanatate",
        "boală", "boala", "boli", "vaccin", "vaccinare", "epidemie", "pandemie", "virus", "gripă", "gripa",
        "farmacie", "farmacii", "medicament", "medicamente", "chirurg", "chirurgie", "cardiologie", "oncologie",
        "dsp", "oms", "sanitar", "sanitară", "sanitara", "urgență", "urgenta", "ambulanță", "ambulanta",
        "smurd", "terapie", "diagnostic", "clinic", "clinică", "clinica", "medical", "medicală", "medicala",
        "transplant", "infectie", "infecție", "anestezie", "recuperare"
    },
    "auto_trafic": {
        "auto", "trafic", "mașină", "masina", "mașini", "masini", "șosea", "sosea", "autostradă", "autostrada",
        "autostrăzi", "autostrazi", "drum", "drumul", "drumuri", "dn1", "dn2", "dn7", "a1", "a2", "a3", "a7",
        "circulație", "circulatie", "vehicul", "vehicule", "pod", "pasaj", "accident", "accidente", "rutier",
        "rutieră", "rutiera", "rutiere", "șofer", "sofer", "șoferi", "soferi", "conducător", "conducator",
        "viteză", "viteza", "radar", "parcare", "parcări", "parcari", "pieton", "pietoni", "permis", "dacia",
        "renault", "volkswagen", "bmw", "audi", "mercedes", "ford", "toyota", "cnair", "rar", "itp", "carosabil",
        "ambuteiaj", "motocicletă", "motocicleta", "camion", "tir"
    },
    "cariera_educatie": {
        "educație", "educatie", "școală", "scoala", "școli", "scoli", "liceu", "licee", "elev", "elevi",
        "elevul", "profesor", "profesori", "profesorul", "universitate", "universități", "universitati",
        "facultate", "facultăți", "facultati", "student", "studenți", "studenti", "bacalaureat", "titularizare",
        "bursă", "burse", "carieră", "cariera", "angajare", "angajări", "angajari", "angajator", "angajatori",
        "salariu", "salarii", "recalificare", "învățământ", "invatamant", "cursuri", "studii", "diplomă",
        "diploma", "șomaj", "somaj", "cv", "recrutare", "job", "joburi", "muncă", "munca", "profesie"
    },
    "energie_economic": {
        "energie", "energetic", "gaz", "gaze", "curent", "electric", "electricitate", "nuclear", "hidro",
        "termocentrală", "termocentrala", "eolian", "eoliene", "solar", "fotovoltaic", "fotovoltaice", "petrol",
        "combustibil", "combustibili", "carburant", "carburanți", "carburanti", "bancar", "bancă", "banca",
        "bănci", "banci", "dobândă", "dobanda", "dobânzi", "dobanzi", "inflație", "inflatie", "buget",
        "bugetul", "fiscal", "fiscală", "fiscala", "impozit", "impozite", "tva", "anaf", "bnr", "economie",
        "economic", "economică", "economica", "pib", "investiții", "investitii", "euro", "lei", "miliarde",
        "milioane", "acțiuni", "actiuni", "bursă", "bursa", "bvb", "finanțe", "finante", "profit", "venituri"
    },
    "cultura_turism": {
        "cultură", "cultura", "cultural", "culturală", "turism", "turistic", "turistică", "turiști", "turisti",
        "turist", "teatru", "muzeu", "muzee", "film", "filme", "cinema", "festival", "festivalul", "carte",
        "cărți", "carti", "autor", "autori", "scriitor", "scriitori", "patrimoniu", "monument", "monumente",
        "istoric", "istorie", "concert", "concerte", "spectacol", "spectacole", "expoziție", "expozitie",
        "hotel", "hoteluri", "cazare", "destinație", "destinatie", "vacanță", "vacanta", "sejur", "stațiune",
        "statiune", "pensiune", "pensiuni", "horeca"
    },
    "tech_ai": {
        "tech", "tehnologie", "it", "cyber", "cibernetic", "cibernetică", "cibernetica", "hacker", "malware",
        "ransomware", "phishing", "vulnerabilitate", "software", "hardware", "cip", "cipuri", "chip", "chips",
        "procesor", "procesoare", "algoritm", "algoritmi", "robot", "roboți", "roboti", "robotică", "robotica",
        "cloud", "server", "servere", "datacenter", "smartphone", "semiconductori", "microcip", "openai",
        "nvidia", "codex", "github", "telecom", "telecomunicații", "telecomunicatii", "router", "firmware"
    },
    "politica_institutii": {
        "guvern", "guvernul", "parlament", "parlamentul", "senat", "senatul", "deputați", "deputati",
        "ministru", "miniștri", "ministri", "premier", "președinte", "presedinte", "președinție", "presedintie",
        "partid", "partide", "psd", "pnl", "usr", "aur", "ccr", "cna", "alegeri", "vot", "voturi", "primar",
        "primărie", "primarie", "prefect", "consiliu", "lege", "legi", "ordonanță", "ordonanta", "justiție",
        "justitie", "judecător", "judecator", "tribunal", "procuror", "dosar", "anchetă", "ancheta",
        "ambasador", "diplomație", "diplomatie"
    },
    "sport": {
        "sport", "fotbal", "meci", "meciul", "meciuri", "scor", "gol", "goluri", "victorie", "înfrângere",
        "infrangere", "campionat", "cupă", "cupa", "liga", "ligii", "clasament", "stadion", "antrenor",
        "arbitru", "jucător", "jucători", "jucator", "jucatori", "fcsb", "dinamo", "rapid", "cfr cluj",
        "tenis", "handbal", "baschet", "natație", "natatie", "atletism", "olimpic"
    }
}

# Cuvinte generice/incidentale care au pondere minimă (nu pot impune categoria tech sau economic)
_INCIDENTAL_KEYWORDS = frozenset({
    "google", "meta", "apple", "microsoft", "telefon", "telefoane", "server", "ai", "energie", "economic"
})

# Mapare categorii de secțiuni către domeniul primar
_CATEGORY_TO_DOMAIN = {
    "tech": "tech_ai",
    "ai": "tech_ai",
    "it": "tech_ai",
    "economic": "energie_economic",
    "energie": "energie_economic",
    "financiar": "energie_economic",
    "auto": "auto_trafic",
    "sanatate": "sanatate",
    "educatie": "cariera_educatie",
    "cariera": "cariera_educatie",
    "cultura": "cultura_turism",
    "turism": "cultura_turism",
    "politic": "politica_institutii",
    "sport": "sport",
}


def clasifica_domeniu(title: str = "", summary: str = "", category: str = "") -> DomeniuClasificat:
    """Clasificator tematic determinist bazat pe dicționare, expresii și ponderi.

    Ponderea semantică a titlului este dominantă (4x). Rezumatul clarifică (1x).
    Categoria servește exclusiv ca indiciu de departajare (tie-break).
    Motivele tech sunt atribuite EXCLUSIV când Tehnologia/IT/AI/Cyber este subiectul central.
    """
    t_norm = _normalize_text(title)
    s_norm = _normalize_text(summary)
    cat_norm = (category or "").strip().lower()

    words_t = set(re.findall(r"[\w-]+", t_norm))
    words_s = set(re.findall(r"[\w-]+", s_norm))

    scoruri: dict[str, float] = {k: 0.0 for k in _KEYWORDS_DOMENII}
    motive: dict[str, list[str]] = {k: [] for k in _KEYWORDS_DOMENII}

    for dom, expresii in _EXPRESII_DOMENII.items():
        for exp in expresii:
            if exp in t_norm:
                scoruri[dom] += 8.0
                motive[dom].append(f"expresie_titlu('{exp}')")
            elif exp in s_norm:
                scoruri[dom] += 4.0
                motive[dom].append(f"expresie_sumar('{exp}')")

    for dom, kws in _KEYWORDS_DOMENII.items():
        for w in (words_t & kws):
            pts = 1.0 if w in _INCIDENTAL_KEYWORDS else 3.5
            scoruri[dom] += pts
            motive[dom].append(f"titlu('{w}')")
        for w in (words_s & kws):
            pts = 0.5 if w in _INCIDENTAL_KEYWORDS else 1.0
            scoruri[dom] += pts
            motive[dom].append(f"sumar('{w}')")

    # Departajare auxiliară din categorie
    domeniu_cat = _CATEGORY_TO_DOMAIN.get(cat_norm)
    if domeniu_cat and domeniu_cat in scoruri:
        scoruri[domeniu_cat] += 2.0
        motive[domeniu_cat].append(f"categorie('{cat_norm}')")

    sorted_scoruri = sorted(scoruri.items(), key=lambda item: item[1], reverse=True)
    top_dom, top_scor = sorted_scoruri[0]

    # Regula de siguranță Tech: tech poate fi ales doar dacă scorul este substanțial
    # și nu doar din cauza unui cuvânt generic (ex. "Google" pe o știre politică/economică)
    if top_dom == "tech_ai":
        # Dacă categoria originală NU este tech/ai, solicităm scor clar (>= 6)
        if cat_norm not in ("tech", "ai", "it") and top_scor < 6.0:
            second_dom, second_scor = sorted_scoruri[1]
            if second_scor >= 2.0:
                top_dom, top_scor = second_dom, second_scor
            else:
                top_dom, top_scor = "general", 0.0

    if top_scor < 2.0:
        if domeniu_cat:
            top_dom = domeniu_cat
            top_scor = 2.0
            motiv_text = f"fallback categorie {cat_norm}"
        else:
            top_dom = "general"
            top_scor = 0.0
            motiv_text = "fallback neutru"
    else:
        motiv_text = "; ".join(motive[top_dom][:4])

    return DomeniuClasificat(top_dom, scor=top_scor, motiv=motiv_text)


# Mapare domenii -> palete permise
_PALETE_DOMENIU = {
    "tech": (4, 1, 0, 5),                  # ardezie, cerneală, albastru, prun
    "tech_ai": (4, 1, 0, 5),               # ardezie, cerneală, albastru, prun
    "energie_economic": (0, 3, 4, 1),      # auriu cald, pământ ars, ardezie, cerneală
    "sanatate": (0, 2, 1, 3),              # auriu cald, măsliniu, cerneală, pământ ars
    "auto_trafic": (4, 1, 0, 2),           # ardezie, cerneală, albastru, măsliniu
    "cariera_educatie": (0, 1, 4, 3),      # auriu cald, cerneală, ardezie, pământ ars
    "cultura_turism": (3, 5, 2, 0),        # pământ ars, prun, măsliniu, auriu cald
    "politica_institutii": (0, 1, 4, 3),   # cerneală pe aur, cerneală pe hârtie, ardezie, pământ ars
    "sport": (2, 4, 0, 1),                 # măsliniu, ardezie, albastru, cerneală
    "general": (0, 1, 2, 3, 4, 5),         # toate
}

# Mapare domenii -> motive permise (TECH motivele sunt STRICT INTERZISE pe restul domeniilor)
_MOTIVE_DOMENIU = {
    "tech": ("circuit_matrix", "wireframe_mesh", "parametric_waves"),
    "tech_ai": ("circuit_matrix", "wireframe_mesh", "parametric_waves"),
    "energie_economic": ("isometric_prism", "financial_bars", "warm_geometry"),
    "sanatate": ("organic_flow", "cellular_harmony", "warm_geometry"),
    "auto_trafic": ("road_perspective", "perspective_lines", "warm_geometry"),
    "cariera_educatie": ("progress_steps", "document_lines", "warm_geometry"),
    "cultura_turism": ("architectural_arch", "heritage_shapes", "warm_geometry"),
    "politica_institutii": ("civic_columns", "editorial_block", "warm_geometry"),
    "sport": ("field_curves", "sport_geometry", "warm_geometry"),
    "general": ("warm_geometry",),
}

TECH_MOTIFS = frozenset({"circuit_matrix", "wireframe_mesh", "parametric_waves"})


# ==============================================================================
# Generatoare Procedurale SVG
# ==============================================================================

def _gen_warm_geometry(seed: bytes, gid: str) -> str:
    """Grafică editorială neutră (geometrie caldă nobilă bazată pe secțiunea de aur)."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 125 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 16) - 8
    r_mic, r_mediu, r_mare = 42, 75, 120

    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r_mare}" fill="{fill_ref}" fill-opacity="0.12" '
        f'stroke="{glow_ref}" stroke-width="0.8" stroke-dasharray="3,5" stroke-opacity="0.35"/>'
    )
    elements.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{r_mediu}" ry="{r_mic + 8}" fill="none" '
        f'stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.75"/>'
    )
    elements.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{r_mic + 12}" ry="{r_mediu}" fill="none" '
        f'stroke="{glow_ref}" stroke-width="1.1" stroke-opacity="0.55"/>'
    )
    elements.append(
        f'<line x1="{cx - 150}" y1="{cy}" x2="{cx + 100}" y2="{cy}" stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="0.45"/>'
    )
    elements.append(
        f'<line x1="{cx - 100}" y1="{cy + 4}" x2="{cx + 60}" y2="{cy + 4}" stroke="{glow_ref}" stroke-width="0.5" stroke-opacity="0.3"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="14" fill="{fill_ref}" fill-opacity="0.3" stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.85"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{glow_ref}" fill-opacity="0.95"/>'
    )

    for ang in (0, 90, 180, 270):
        rad = math.radians(ang)
        x1 = cx + (r_mediu - 6) * math.cos(rad)
        y1 = cy + (r_mediu - 6) * math.sin(rad)
        x2 = cx + (r_mediu + 6) * math.cos(rad)
        y2 = cy + (r_mediu + 6) * math.sin(rad)
        elements.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.75"/>'
        )
    return "".join(elements)


def _gen_organic_flow(seed: bytes, gid: str) -> str:
    """Forme organice luminoase și arce vitale armonioase pentru Sănătate."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"
    cx = W - 120 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 16) - 8

    # Unde vitale fluide suprapuse
    for i in range(4):
        rx = 60 + i * 22
        ry = 45 + i * 18
        rot = (seed[3] * 7 + i * 35) % 180
        op = 0.15 + i * 0.12
        elements.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill_ref}" fill-opacity="{op * 0.4:.2f}" '
            f'stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="{op:.2f}" transform="rotate({rot} {cx} {cy})"/>'
        )

    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="16" fill="{fill_ref}" fill-opacity="0.45" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.9"/>'
    )
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{glow_ref}" fill-opacity="0.95"/>')
    # Ramură fluidă orizontală
    elements.append(
        f'<path d="M {cx - 140} {cy + 20} Q {cx - 60} {cy - 30} {cx} {cy} T {cx + 90} {cy - 10}" '
        f'fill="none" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.75"/>'
    )
    return "".join(elements)


def _gen_cellular_harmony(seed: bytes, gid: str) -> str:
    """Structură celulară armonioasă și inele vitale pentru Sănătate."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"
    cx = W - 115 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 16) - 8

    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="78" fill="{fill_ref}" fill-opacity="0.12" stroke="{glow_ref}" stroke-width="0.9" stroke-dasharray="4,4" stroke-opacity="0.5"/>'
    )
    for ang in (30, 90, 150, 210, 270, 330):
        rad = math.radians(ang)
        x = cx + 46 * math.cos(rad)
        y = cy + 46 * math.sin(rad)
        elements.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="18" fill="{fill_ref}" fill-opacity="0.22" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.7"/>'
        )
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{glow_ref}" fill-opacity="0.85"/>')

    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="22" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.95"/>'
    )
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_road_perspective(seed: bytes, gid: str) -> str:
    """Linii de perspectivă și marcaje rutiere pentru Auto & Trafic."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    vx = W - 110 + (seed[1] % 20) - 10
    vy = 65 + (seed[2] % 12) - 6

    # Orizont și nod radiant
    elements.append(
        f'<line x1="{W * 0.4}" y1="{vy}" x2="{W}" y2="{vy}" stroke="{glow_ref}" stroke-width="0.9" stroke-opacity="0.4"/>'
    )
    elements.append(
        f'<circle cx="{vx}" cy="{vy}" r="7" fill="{fill_ref}" fill-opacity="0.4" stroke="{glow_ref}" stroke-width="1.5" stroke-opacity="0.9"/>'
    )

    # Liniile carosabilului în perspectivă
    y_bot = H - 15
    for offset in (-140, -85, -30, 30, 85, 140):
        x_bot = vx + offset * 1.5
        op = 0.75 if abs(offset) in (30, 85) else 0.4
        sw = 1.6 if abs(offset) in (30, 85) else 1.0
        dash = ' stroke-dasharray="6,5"' if abs(offset) == 30 else ""
        elements.append(
            f'<line x1="{vx}" y1="{vy}" x2="{x_bot:.1f}" y2="{y_bot}" stroke="{glow_ref}" stroke-width="{sw}" stroke-opacity="{op}"{dash}/>'
        )

    # Arcuri dinamice transversale de flux
    for dy in (40, 85, 135):
        y = vy + dy
        span = dy * 1.4
        elements.append(
            f'<path d="M {vx - span} {y} Q {vx} {y - 12} {vx + span} {y}" fill="none" stroke="{glow_ref}" stroke-width="1.1" stroke-opacity="0.55"/>'
        )
    return "".join(elements)


def _gen_perspective_lines(seed: bytes, gid: str) -> str:
    """Linii cinetice de viteză și marcaje direcționale pentru Auto & Mobilitate."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 115
    cy = H // 2

    for i in range(6):
        y = 45 + i * 30
        x_start = W * 0.45 + i * 15
        x_end = W - 25
        elements.append(
            f'<line x1="{x_start}" y1="{y}" x2="{x_end}" y2="{y}" stroke="{glow_ref}" stroke-width="1.2" stroke-dasharray="12,8" stroke-opacity="0.6"/>'
        )

    # Arc parabolic de viteză
    elements.append(
        f'<path d="M {cx - 100} {cy + 70} Q {cx + 30} {cy + 30} {cx + 70} {cy - 60}" fill="none" stroke="{glow_ref}" stroke-width="2.2" stroke-opacity="0.85"/>'
    )
    elements.append(
        f'<circle cx="{cx + 70}" cy="{cy - 60}" r="8" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.95"/>'
    )
    return "".join(elements)


def _gen_progress_steps(seed: bytes, gid: str) -> str:
    """Pași de progres ascendenți și geometrie de carieră/educație."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    ox = W - 170
    oy = H - 45
    step_w = 28
    step_h = 24

    for i in range(5):
        x = ox + i * step_w
        h_box = (i + 1) * step_h
        y = oy - h_box
        op = 0.2 + i * 0.14
        elements.append(
            f'<rect x="{x}" y="{y}" width="{step_w - 4}" height="{h_box}" rx="3" '
            f'fill="{fill_ref}" fill-opacity="{op:.2f}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.8"/>'
        )

    # Linie ascendentă de progres
    elements.append(
        f'<line x1="{ox - 10}" y1="{oy - 15}" x2="{ox + 4 * step_w + 24}" y2="{oy - 5 * step_h - 15}" '
        f'stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.9"/>'
    )
    elements.append(
        f'<circle cx="{ox + 4 * step_w + 24}" cy="{oy - 5 * step_h - 15}" r="6" fill="{glow_ref}" fill-opacity="0.95"/>'
    )
    return "".join(elements)


def _gen_document_lines(seed: bytes, gid: str) -> str:
    """Structură de document, CV și diplomă pentru Carieră & Educație."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    dx = W - 145
    dy = 42
    dw = 100
    dh = 160

    # Fila de document
    elements.append(
        f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="6" fill="{fill_ref}" fill-opacity="0.2" '
        f'stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.85"/>'
    )
    # Filet antet
    elements.append(
        f'<line x1="{dx + 16}" y1="{dy + 24}" x2="{dx + dw - 16}" y2="{dy + 24}" stroke="{glow_ref}" stroke-width="2.4" stroke-opacity="0.9"/>'
    )
    # Linii de conținut
    for i in range(5):
        y = dy + 48 + i * 18
        w_line = (dw - 32) * (0.85 if i % 2 == 1 else 1.0)
        elements.append(
            f'<line x1="{dx + 16}" y1="{y}" x2="{dx + 16 + w_line}" y2="{y}" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.55"/>'
        )

    # Sigiliu / distincție rotundă în colțul inferior
    elements.append(
        f'<circle cx="{dx + dw - 24}" cy="{dy + dh - 24}" r="14" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="1.5" stroke-opacity="0.9"/>'
    )
    elements.append(
        f'<circle cx="{dx + dw - 24}" cy="{dy + dh - 24}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>'
    )
    return "".join(elements)


def _gen_isometric_prism(seed: bytes, gid: str) -> str:
    """Structură geometrică izometrică 3D (prisme și blocuri arhitecturale flotante)."""
    elements = []
    cx = W * 0.74 + (seed[1] % 20) - 10
    cy = H * 0.52 + (seed[2] % 20) - 10
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cos30 = 0.866
    sin30 = 0.5

    def iso_box(ox: float, oy: float, w_box: float, d_box: float, h_box: float,
                op_top: float, op_left: float, op_right: float) -> str:
        p_top = (ox, oy - h_box)
        p_top_r = (ox + w_box * cos30, oy - h_box - w_box * sin30)
        p_top_l = (ox - d_box * cos30, oy - h_box - d_box * sin30)
        p_top_back = (ox + (w_box - d_box) * cos30, oy - h_box - (w_box + d_box) * sin30)
        p_bot = (ox, oy)
        p_bot_r = (ox + w_box * cos30, oy - w_box * sin30)
        p_bot_l = (ox - d_box * cos30, oy - d_box * sin30)

        d_top_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_r[0]:.1f} {p_top_r[1]:.1f} L {p_top_back[0]:.1f} {p_top_back[1]:.1f} L {p_top_l[0]:.1f} {p_top_l[1]:.1f} Z"
        d_left_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_l[0]:.1f} {p_top_l[1]:.1f} L {p_bot_l[0]:.1f} {p_bot_l[1]:.1f} L {p_bot[0]:.1f} {p_bot[1]:.1f} Z"
        d_right_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_r[0]:.1f} {p_top_r[1]:.1f} L {p_bot_r[0]:.1f} {p_bot_r[1]:.1f} L {p_bot[0]:.1f} {p_bot[1]:.1f} Z"

        return (
            f'<path d="{d_top_face}" fill="{fill_ref}" fill-opacity="{op_top}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.85"/>'
            f'<path d="{d_left_face}" fill="{fill_ref}" fill-opacity="{op_left}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.7"/>'
            f'<path d="{d_right_face}" fill="{fill_ref}" fill-opacity="{op_right}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.9"/>'
        )

    elements.append(iso_box(cx, cy + 25, 48, 65, 42, 0.4, 0.25, 0.5))
    elements.append(iso_box(cx - 45, cy - 10, 28, 40, 24, 0.25, 0.15, 0.35))
    elements.append(
        f'<line x1="{cx - 120}" y1="{cy + 40}" x2="{cx + 60}" y2="{cy - 50}" stroke="{glow_ref}" stroke-width="0.9" stroke-dasharray="4,4" stroke-opacity="0.4"/>'
    )
    elements.append(
        f'<line x1="{cx - 80}" y1="{cy - 60}" x2="{cx + 80}" y2="{cy + 25}" stroke="{glow_ref}" stroke-width="0.9" stroke-dasharray="4,4" stroke-opacity="0.4"/>'
    )
    return "".join(elements)


def _gen_financial_bars(seed: bytes, gid: str) -> str:
    """Diagrame volumetrice și registre financiare pentru Energie & Economic."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    bx = W - 170
    by = H - 45
    bar_w = 22
    heights = (35, 60, 48, 95, 125, 110)

    for i, h_val in enumerate(heights):
        x = bx + i * (bar_w + 6)
        y = by - h_val
        op = 0.25 + (h_val / 130) * 0.35
        elements.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h_val}" rx="3" fill="{fill_ref}" fill-opacity="{op:.2f}" '
            f'stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.85"/>'
        )

    # Linie curbă de trend bursier
    pts = [(bx + i * (bar_w + 6) + bar_w // 2, by - heights[i] - 10) for i in range(len(heights))]
    d_line = f"M {pts[0][0]} {pts[0][1]}"
    for p in pts[1:]:
        d_line += f" L {p[0]} {p[1]}"
    elements.append(f'<path d="{d_line}" fill="none" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.95"/>')
    for p in pts:
        elements.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="3.5" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_architectural_arch(seed: bytes, gid: str) -> str:
    """Arcade arhitecturale clasice și portaluri culturale pentru Cultură & Turism."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 110
    base_y = H - 35
    w_arch = 90
    h_col = 80
    r_arch = w_arch / 2

    for layer in (1.0, 0.72, 0.46):
        w_cur = w_arch * layer
        h_cur = h_col * layer
        r_cur = w_cur / 2
        d_portal = (
            f"M {cx - r_cur} {base_y} L {cx - r_cur} {base_y - h_cur} "
            f"A {r_cur} {r_cur} 0 0 1 {cx + r_cur} {base_y - h_cur} "
            f"L {cx + r_cur} {base_y}"
        )
        op = 0.2 + (1.0 - layer) * 0.4
        elements.append(
            f'<path d="{d_portal}" fill="none" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="{op:.2f}"/>'
        )

    # Filet soclu
    elements.append(
        f'<line x1="{cx - 80}" y1="{base_y}" x2="{cx + 80}" y2="{base_y}" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.85"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{base_y - h_col - r_arch}" r="7" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="1.5" stroke-opacity="0.9"/>'
    )
    return "".join(elements)


def _gen_heritage_shapes(seed: bytes, gid: str) -> str:
    """Emblemă de patrimoniu și trandafir al vânturilor pentru Turism & Tradiție."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 115
    cy = H // 2
    r_ring = 65

    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r_ring}" fill="{fill_ref}" fill-opacity="0.15" '
        f'stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.75"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r_ring - 14}" fill="none" '
        f'stroke="{glow_ref}" stroke-width="0.8" stroke-dasharray="4,4" stroke-opacity="0.5"/>'
    )

    # Raze romboidale
    for ang in (0, 45, 90, 135, 180, 225, 270, 315):
        rad = math.radians(ang)
        rad_perp = rad + math.pi / 2
        d_ray = 52 if ang % 90 == 0 else 36
        tip_x = cx + d_ray * math.cos(rad)
        tip_y = cy + d_ray * math.sin(rad)
        w_side = 6 if ang % 90 == 0 else 4
        s1_x = cx + w_side * math.cos(rad_perp)
        s1_y = cy + w_side * math.sin(rad_perp)
        s2_x = cx - w_side * math.cos(rad_perp)
        s2_y = cy - w_side * math.sin(rad_perp)
        elements.append(
            f'<polygon points="{cx},{cy} {s1_x:.1f},{s1_y:.1f} {tip_x:.1f},{tip_y:.1f} {s2_x:.1f},{s2_y:.1f}" '
            f'fill="{fill_ref}" fill-opacity="0.3" stroke="{glow_ref}" stroke-width="1.0" stroke-opacity="0.85"/>'
        )
    return "".join(elements)


def _gen_civic_columns(seed: bytes, gid: str) -> str:
    """Coloane civice și ritm instituțional nobil pentru Politică & Instituții."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 120
    top_y = 55
    bot_y = H - 50
    w_architrave = 140

    # Arhitravă orizontală superioară și soclu
    elements.append(
        f'<line x1="{cx - w_architrave // 2}" y1="{top_y}" x2="{cx + w_architrave // 2}" y2="{top_y}" stroke="{glow_ref}" stroke-width="2.5" stroke-opacity="0.85"/>'
    )
    elements.append(
        f'<line x1="{cx - w_architrave // 2 - 8}" y1="{bot_y}" x2="{cx + w_architrave // 2 + 8}" y2="{bot_y}" stroke="{glow_ref}" stroke-width="2.5" stroke-opacity="0.85"/>'
    )

    # 4 coloane clasice
    cols = (-48, -16, 16, 48)
    for col_x in cols:
        x = cx + col_x
        elements.append(
            f'<line x1="{x - 4}" y1="{top_y}" x2="{x - 4}" y2="{bot_y}" stroke="{glow_ref}" stroke-width="1.0" stroke-opacity="0.6"/>'
        )
        elements.append(
            f'<line x1="{x + 4}" y1="{top_y}" x2="{x + 4}" y2="{bot_y}" stroke="{glow_ref}" stroke-width="1.0" stroke-opacity="0.6"/>'
        )

    # Fronton triunghiular discret deasupra
    elements.append(
        f'<polygon points="{cx - w_architrave // 2},{top_y} {cx},{top_y - 20} {cx + w_architrave // 2},{top_y}" '
        f'fill="{fill_ref}" fill-opacity="0.2" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.8"/>'
    )
    return "".join(elements)


def _gen_editorial_block(seed: bytes, gid: str) -> str:
    """Bloc compozițional civic și scut instituțional pentru Politică."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 110
    cy = H // 2

    # Scut civic rafinat
    elements.append(
        f'<path d="M {cx - 50} {cy - 55} L {cx + 50} {cy - 55} L {cx + 50} {cy + 10} Q {cx} {cy + 70} {cx} {cy + 70} Q {cx} {cy + 70} {cx - 50} {cy + 10} Z" '
        f'fill="{fill_ref}" fill-opacity="0.25" stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.85"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{cy - 10}" r="16" fill="{fill_ref}" fill-opacity="0.4" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.9"/>'
    )
    elements.append(f'<circle cx="{cx}" cy="{cy - 10}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_field_curves(seed: bytes, gid: str) -> str:
    """Piste de stadion, ovaluri dinamice și forme atletice pentru Sport."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 110
    cy = H // 2

    for i in range(4):
        rx = 40 + i * 22
        ry = 65 + i * 16
        rot = -30
        op = 0.2 + i * 0.18
        elements.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{glow_ref}" '
            f'stroke-width="1.3" stroke-opacity="{op:.2f}" transform="rotate({rot} {cx} {cy})"/>'
        )

    # Linie mediană de sprint
    elements.append(
        f'<line x1="{cx - 80}" y1="{cy + 60}" x2="{cx + 70}" y2="{cy - 60}" stroke="{glow_ref}" stroke-width="2.0" stroke-opacity="0.9"/>'
    )
    elements.append(
        f'<circle cx="{cx + 70}" cy="{cy - 60}" r="7" fill="{fill_ref}" fill-opacity="0.6" stroke="{glow_ref}" stroke-width="1.5" stroke-opacity="0.95"/>'
    )
    return "".join(elements)


def _gen_sport_geometry(seed: bytes, gid: str) -> str:
    """Geometrie de teren sportiv și vectori cinetici pentru Sport."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 115
    cy = H // 2
    r_center = 42

    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r_center}" fill="{fill_ref}" fill-opacity="0.2" stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.85"/>'
    )
    elements.append(
        f'<line x1="{cx - 80}" y1="{cy}" x2="{cx + 80}" y2="{cy}" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.9"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="{glow_ref}" fill-opacity="0.95"/>'
    )
    elements.append(
        f'<path d="M {cx - 70} {cy - 50} Q {cx} {cy - 75} {cx + 70} {cy - 50}" fill="none" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.6"/>'
    )
    elements.append(
        f'<path d="M {cx - 70} {cy + 50} Q {cx} {cy + 75} {cx + 70} {cy + 50}" fill="none" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.6"/>'
    )
    return "".join(elements)


# Generatoare Tech & AI
def _gen_wireframe_mesh(seed: bytes, gid: str) -> str:
    """Teren topografic 3D wireframe. EXCLUSIV pentru Tech & AI."""
    elements = []
    rows = 11
    cols = 16
    y_start, y_end = 60, 240

    freq_x = 0.035 + (seed[1] % 20) * 0.001
    freq_z = 0.05 + (seed[2] % 15) * 0.002
    phase = (seed[3] % 100) * 0.05
    amp_base = 22.0 + (seed[5] % 12)

    grid = []
    for r in range(rows):
        row_pts = []
        t = r / (rows - 1)
        y_base = y_start + t * (y_end - y_start)
        span_x = 220 + t * 240
        x_min = (W - span_x) / 2
        amp = amp_base * (0.35 + 0.65 * t)

        for c in range(cols):
            s = c / (cols - 1)
            x = x_min + s * span_x
            wave = (
                math.sin(c * freq_x * 8 + phase) * 0.6 +
                math.cos(r * freq_z * 5 + phase * 0.8) * 0.4
            )
            elevation = wave * amp * math.sin(s * math.pi)
            y = y_base - elevation
            row_pts.append((round(x, 1), round(y, 1)))
        grid.append(row_pts)

    glow_ref = f"url(#art-3d-glow-{gid})"

    for r in range(rows):
        row_pts = grid[r]
        t = r / (rows - 1)
        opacity = 0.25 + 0.65 * (t ** 1.3)
        sw = 1.0 + 0.8 * t
        d_parts = [f"M {row_pts[0][0]} {row_pts[0][1]}"]
        for c in range(1, cols):
            p0 = row_pts[c - 1]
            p1 = row_pts[c]
            d_parts.append(f"Q {p0[0]} {p0[1]} {(p0[0] + p1[0]) / 2} {(p0[1] + p1[1]) / 2}")
        d_parts.append(f"L {row_pts[-1][0]} {row_pts[-1][1]}")
        elements.append(
            f'<path d="{" ".join(d_parts)}" fill="none" stroke="{glow_ref}" stroke-width="{sw:.2f}" stroke-opacity="{opacity:.2f}"/>'
        )

    for c in range(0, cols, 2):
        d_parts = [f"M {grid[0][c][0]} {grid[0][c][1]}"]
        for r in range(1, rows):
            d_parts.append(f"L {grid[r][c][0]} {grid[r][c][1]}")
        s = c / (cols - 1)
        op = 0.15 + 0.3 * math.sin(s * math.pi)
        elements.append(
            f'<path d="{" ".join(d_parts)}" fill="none" stroke="{glow_ref}" stroke-width="0.85" stroke-opacity="{op:.2f}" stroke-dasharray="3,3"/>'
        )
    return "".join(elements)


def _gen_circuit_matrix(seed: bytes, gid: str) -> str:
    """Matrice de circuite imprimate (PCB bus traces). EXCLUSIV pentru Tech & AI."""
    elements = []
    cx = W - 110 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 20) - 10
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    chip_size = 54
    elements.append(
        f'<rect x="{cx - chip_size // 2}" y="{cy - chip_size // 2}" width="{chip_size}" height="{chip_size}" rx="8" '
        f'fill="{fill_ref}" fill-opacity="0.25" stroke="{glow_ref}" stroke-width="2.2" stroke-opacity="0.9"/>'
    )
    core_size = 32
    elements.append(
        f'<rect x="{cx - core_size // 2}" y="{cy - core_size // 2}" width="{core_size}" height="{core_size}" rx="4" '
        f'fill="none" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.6"/>'
    )
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>')

    num_traces = 9
    for i in range(num_traces):
        slot = i - (num_traces - 1) / 2
        y_start = cy + slot * 10
        x0 = cx - chip_size // 2
        len1 = 20 + (i * 7 + seed[3]) % 35
        x1 = x0 - len1
        diag_len = 14 + (i * 5 + seed[4]) % 22
        x2 = x1 - diag_len
        y2 = y_start + (diag_len if slot >= 0 else -diag_len)
        len3 = 30 + (i * 11 + seed[5]) % 50
        x3 = x2 - len3
        d_trace = f"M {x0} {y_start} L {x1} {y_start} L {x2} {y2} L {x3} {y2}"
        op = 0.4 + (1.0 - abs(slot) / 5) * 0.5
        elements.append(f'<path d="{d_trace}" fill="none" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="{op:.2f}"/>')
        elements.append(f'<circle cx="{x3}" cy="{y2}" r="2.8" fill="{glow_ref}" fill-opacity="{op:.2f}"/>')
    return "".join(elements)


def _gen_parametric_waves(seed: bytes, gid: str) -> str:
    """Valuri parametrice / benzi oscilante de date. EXCLUSIV pentru Tech & AI."""
    elements = []
    num_ribbons = 5
    base_y = H * 0.52 + (seed[0] % 16) - 8
    freq1 = 0.016 + (seed[1] % 10) * 0.0008
    freq2 = 0.024 + (seed[2] % 10) * 0.001
    phase_step = 0.42 + (seed[3] % 8) * 0.03
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    for r in range(num_ribbons):
        p = (seed[4] % 50) * 0.1 + r * phase_step
        thickness = 14 + r * 3
        y_offset = (r - (num_ribbons - 1) / 2) * 16

        pts_top, pts_bot = [], []
        steps = 14
        dx = W / steps
        for s in range(steps + 1):
            x = s * dx
            wave = (
                math.sin(x * freq1 + p) * 38.0 +
                math.cos(x * freq2 - p * 0.7) * 18.0
            )
            persp = 0.65 + 0.55 * (x / W)
            y_mid = base_y + wave * persp + y_offset
            pts_top.append((x, y_mid - thickness * persp / 2))
            pts_bot.append((x, y_mid + thickness * persp / 2))

        d_top = [f"M {pts_top[0][0]:.1f} {pts_top[0][1]:.1f}"]
        for i in range(1, len(pts_top)):
            p0, p1 = pts_top[i - 1], pts_top[i]
            d_top.append(f"Q {p0[0]:.1f} {p0[1]:.1f} {(p0[0] + p1[0]) / 2:.1f} {(p0[1] + p1[1]) / 2:.1f}")
        d_top.append(f"L {pts_top[-1][0]:.1f} {pts_top[-1][1]:.1f}")

        d_bot = []
        for i in range(len(pts_bot) - 1, -1, -1):
            d_bot.append(f"L {pts_bot[i][0]:.1f} {pts_bot[i][1]:.1f}")

        d_ribbon = " ".join(d_top) + " " + " ".join(d_bot) + " Z"
        op_fill = 0.12 + r * 0.04
        op_stroke = 0.55 + r * 0.08
        elements.append(
            f'<path d="{d_ribbon}" fill="{fill_ref}" fill-opacity="{op_fill:.2f}" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="{op_stroke:.2f}"/>'
        )
    return "".join(elements)


# Dictionar dispecerat generatoare
_GENERATOARE_MOTIVE = {
    "warm_geometry": _gen_warm_geometry,
    "circuit_matrix": _gen_circuit_matrix,
    "wireframe_mesh": _gen_wireframe_mesh,
    "parametric_waves": _gen_parametric_waves,
    "isometric_prism": _gen_isometric_prism,
    "financial_bars": _gen_financial_bars,
    "organic_flow": _gen_organic_flow,
    "cellular_harmony": _gen_cellular_harmony,
    "road_perspective": _gen_road_perspective,
    "perspective_lines": _gen_perspective_lines,
    "progress_steps": _gen_progress_steps,
    "document_lines": _gen_document_lines,
    "architectural_arch": _gen_architectural_arch,
    "heritage_shapes": _gen_heritage_shapes,
    "civic_columns": _gen_civic_columns,
    "editorial_block": _gen_editorial_block,
    "field_curves": _gen_field_curves,
    "sport_geometry": _gen_sport_geometry,
}


def genereaza_scena_generativa(
    a: dict | None = None,
    seed: bytes | None = None,
    *,
    title: str = "",
    category: str = "",
    summary: str = "",
    stil_impus: str | None = None,
) -> dict:
    """Generează reprezentarea grafică SVG procedurală pentru articol.

    Garantează respectarea strictă a domeniilor:
    - Tech & AI: circuite PCB, wireframe mesh sau valuri de date.
    - Non-tech: motive semantice dedicate sau geometrie caldă nobilă.
    """
    if a:
        if not title:
            title = (a.get("title") or "").strip()
        if not category:
            category = (a.get("category") or "").strip()
        if not summary:
            # Preluare rezumat conform modelului
            model = (a.get("model") or "").upper()
            if model == "C":
                summary = (a.get("synthesis") or a.get("description") or a.get("teaser") or "").strip()
            else:
                summary = (a.get("teaser") or a.get("description") or a.get("synthesis") or "").strip()

    if seed is None:
        seed = _seed(a) if a else b"\x00" * 8

    gid = seed[:4].hex()
    domeniu_clasif = clasifica_domeniu(title=title, summary=summary, category=category)
    domeniu = domeniu_clasif

    # Determinare stil
    if stil_impus and stil_impus in _GENERATOARE_MOTIVE:
        # Verificare suplimentară de siguranță: motivele tech nu pot fi impuse pe non-tech
        if stil_impus in TECH_MOTIFS and domeniu != "tech_ai":
            motive_permise = _MOTIVE_DOMENIU.get(domeniu, ("warm_geometry",))
            stil = motive_permise[seed[4] % len(motive_permise)]
        else:
            stil = stil_impus
    else:
        motive_permise = _MOTIVE_DOMENIU.get(domeniu, ("warm_geometry",))
        stil = motive_permise[seed[4] % len(motive_permise)]

    # Culori de glow și fill calibrate pentru paleta editorială
    if stil in TECH_MOTIFS:
        if stil == "circuit_matrix":
            c_glow = ("#6ee7b7", "#10b981", "#047857")
            c_fill = ("#10b981", "#022c22")
        else:
            c_glow = ("#67e8f9", "#06b6d4", "#0369a1")
            c_fill = ("#06b6d4", "#082f49")
    elif domeniu in ("energie_economic", "sanatate"):
        c_glow = ("#fae8a2", "#dcb84e", "#8a6512")
        c_fill = ("#dcb84e", "#1c1917")
    elif domeniu in ("auto_trafic", "cariera_educatie"):
        c_glow = ("#cbd5e1", "#94a3b8", "#475569")
        c_fill = ("#94a3b8", "#0f172a")
    elif domeniu == "cultura_turism":
        c_glow = ("#fbcfe8", "#f472b6", "#be185d")
        c_fill = ("#f472b6", "#3f1a2e")
    elif domeniu == "sport":
        c_glow = ("#a7f3d0", "#34d399", "#059669")
        c_fill = ("#34d399", "#064e3b")
    else:
        c_glow = ("#fae8a2", "#dcb84e", "#8a6512")
        c_fill = ("#dcb84e", "#1d1f24")

    gen_func = _GENERATOARE_MOTIVE.get(stil, _gen_warm_geometry)
    markup = gen_func(seed, gid)

    return {
        "id": gid,
        "stil": stil,
        "domeniu": domeniu,
        "markup": markup,
        "vb": f"0 0 {W} {H}",
        "c_glow": c_glow,
        "c_fill": c_fill,
        "motiv_clasificare": domeniu_clasif.motiv,
    }
