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
    """Sferă armilară celestă, orbită armonică și spirală Fibonacci (Secțiunea de Aur)."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 120 + (seed[1] % 24) - 12
    cy = H // 2 + (seed[2] % 16) - 8

    # 1. Halo difuz de adâncime
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="130" fill="{fill_ref}" fill-opacity="0.08" '
        f'stroke="{glow_ref}" stroke-width="0.6" stroke-dasharray="2,6" stroke-opacity="0.25"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="95" fill="{fill_ref}" fill-opacity="0.14" '
        f'stroke="{glow_ref}" stroke-width="0.9" stroke-opacity="0.4"/>'
    )

    # 2. Inele eliptice înclinate în spațiu 3D (sferă armilară)
    inclinations = [
        (85, 34, (seed[3] * 5) % 180, 1.4, 0.85, "none"),
        (48, 88, (seed[4] * 7 + 45) % 180, 1.2, 0.7, "none"),
        (72, 55, (seed[5] * 11 + 110) % 180, 1.1, 0.6, "none"),
        (60, 26, (seed[0] * 3 + 15) % 180, 0.9, 0.5, "3,4"),
    ]
    for rx, ry, rot, sw, op, dash in inclinations:
        dash_attr = f' stroke-dasharray="{dash}"' if dash != "none" else ""
        elements.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="{glow_ref}" '
            f'stroke-width="{sw}" stroke-opacity="{op}"{dash_attr} transform="rotate({rot} {cx} {cy})"/>'
        )

    # 3. Spirală Fibonacci parametrică (Golden Spiral)
    spiral_pts = []
    a_sp = 2.2 + (seed[6] % 5) * 0.2
    b_sp = 0.165
    rot_sp = (seed[7] % 60) * 0.1
    for step in range(32):
        theta = step * 0.22 + rot_sp
        r_sp = a_sp * math.exp(b_sp * theta)
        if r_sp > 115:
            break
        sx = cx + r_sp * math.cos(theta)
        sy = cy + r_sp * math.sin(theta)
        spiral_pts.append((sx, sy))

    if len(spiral_pts) >= 2:
        d_spiral = [f"M {spiral_pts[0][0]:.1f} {spiral_pts[0][1]:.1f}"]
        for i in range(1, len(spiral_pts)):
            p0 = spiral_pts[i - 1]
            p1 = spiral_pts[i]
            d_spiral.append(f"Q {p0[0]:.1f} {p0[1]:.1f} {(p0[0] + p1[0]) / 2:.1f} {(p0[1] + p1[1]) / 2:.1f}")
        d_spiral.append(f"L {spiral_pts[-1][0]:.1f} {spiral_pts[-1][1]:.1f}")
        elements.append(
            f'<path d="{" ".join(d_spiral)}" fill="none" stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.8"/>'
        )

    # 4. Axe coordonate de calibrare editorială
    elements.append(
        f'<line x1="{cx - 145}" y1="{cy}" x2="{cx + 105}" y2="{cy}" stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="0.45"/>'
    )
    elements.append(
        f'<line x1="{cx}" y1="{cy - 105}" x2="{cx}" y2="{cy + 105}" stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="0.45"/>'
    )

    # 5. Marcaje radiale de precizie (ore / cadrane)
    for ang in range(0, 360, 30):
        rad = math.radians(ang)
        r1 = 92 if ang % 90 == 0 else 94
        r2 = 98 if ang % 90 == 0 else 96
        x1 = cx + r1 * math.cos(rad)
        y1 = cy + r1 * math.sin(rad)
        x2 = cx + r2 * math.cos(rad)
        y2 = cy + r2 * math.sin(rad)
        sw = 1.4 if ang % 90 == 0 else 0.8
        op = 0.85 if ang % 90 == 0 else 0.5
        elements.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{glow_ref}" stroke-width="{sw}" stroke-opacity="{op}"/>')

    # 6. Nucleu luminos și noduri satelit
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="18" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="2.0" stroke-opacity="0.95"/>'
    )
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{glow_ref}" fill-opacity="0.95"/>')

    for i in range(4):
        ang_sat = (seed[i] * 37 + i * 90) % 360
        r_dist = 45 + (seed[i + 2] % 40)
        sat_x = cx + r_dist * math.cos(math.radians(ang_sat))
        sat_y = cy + r_dist * math.sin(math.radians(ang_sat))
        elements.append(f'<circle cx="{sat_x:.1f}" cy="{sat_y:.1f}" r="3" fill="{glow_ref}" fill-opacity="0.9"/>')
        elements.append(f'<circle cx="{sat_x:.1f}" cy="{sat_y:.1f}" r="6.5" fill="none" stroke="{glow_ref}" stroke-width="0.7" stroke-opacity="0.6"/>')

    return "".join(elements)


def _gen_organic_flow(seed: bytes, gid: str) -> str:
    """Fluxuri organice luminoase și pânze celulare dense pentru Sănătate."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    base_y = H * 0.52 + (seed[1] % 20) - 10
    num_ribbons = 14
    freq1 = 0.014 + (seed[2] % 12) * 0.0006
    freq2 = 0.022 + (seed[3] % 10) * 0.0008

    # 1. Benzi fluide suprapuse
    for r in range(num_ribbons):
        p = (seed[4] % 50) * 0.12 + r * 0.38
        y_shift = (r - (num_ribbons - 1) / 2) * 9.5
        thick = 10 + (seed[r % 8] % 8)

        pts_top, pts_bot = [], []
        steps = 18
        dx = W / steps
        for s in range(steps + 1):
            x = s * dx
            wave = (
                math.sin(x * freq1 + p) * 32.0 +
                math.cos(x * freq2 - p * 0.6) * 16.0
            )
            persp = 0.75 + 0.45 * (x / W)
            ym = base_y + wave * persp + y_shift
            pts_top.append((x, ym - thick * persp / 2))
            pts_bot.append((x, ym + thick * persp / 2))

        d_top = [f"M {pts_top[0][0]:.1f} {pts_top[0][1]:.1f}"]
        for i in range(1, len(pts_top)):
            p0, p1 = pts_top[i - 1], pts_top[i]
            d_top.append(f"Q {p0[0]:.1f} {p0[1]:.1f} {(p0[0] + p1[0]) / 2:.1f} {(p0[1] + p1[1]) / 2:.1f}")
        d_top.append(f"L {pts_top[-1][0]:.1f} {pts_top[-1][1]:.1f}")

        d_bot = []
        for i in range(len(pts_bot) - 1, -1, -1):
            d_bot.append(f"L {pts_bot[i][0]:.1f} {pts_bot[i][1]:.1f}")

        d_path = " ".join(d_top) + " " + " ".join(d_bot) + " Z"
        op_fill = 0.08 + (r / num_ribbons) * 0.14
        op_stroke = 0.35 + (r / num_ribbons) * 0.55
        sw = 1.0 if r < num_ribbons - 2 else 1.8
        elements.append(
            f'<path d="{d_path}" fill="{fill_ref}" fill-opacity="{op_fill:.2f}" '
            f'stroke="{glow_ref}" stroke-width="{sw}" stroke-opacity="{op_stroke:.2f}"/>'
        )

    # 2. Noduri bio-celulare flotante cu halouri
    for k in range(6):
        kx = W * 0.45 + (seed[k] * 23) % int(W * 0.5)
        ky = 40 + (seed[k + 1] * 31) % (H - 80)
        kr = 4 + (seed[k + 2] % 6)
        elements.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="{kr + 8}" fill="{fill_ref}" fill-opacity="0.12" stroke="{glow_ref}" stroke-width="0.8" stroke-dasharray="2,3" stroke-opacity="0.4"/>')
        elements.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="{kr}" fill="{glow_ref}" fill-opacity="0.85"/>')

    return "".join(elements)


def _gen_cellular_harmony(seed: bytes, gid: str) -> str:
    """Rețea bio-moleculară celulară și inele de armonie geodesic pentru Sănătate."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"
    cx = W - 120 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 16) - 8

    # 1. Concentrice armonice
    for r_ring in (110, 85, 60):
        elements.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r_ring}" fill="{fill_ref}" fill-opacity="0.08" '
            f'stroke="{glow_ref}" stroke-width="0.8" stroke-dasharray="3,4" stroke-opacity="0.45"/>'
        )

    # 2. Noduri celulare și filamente de legătură
    nodes = []
    for tier, r_dist, count in ((1, 38, 6), (2, 70, 8), (3, 102, 10)):
        for i in range(count):
            ang = (i * (360 / count) + (seed[tier] * 17)) % 360
            rad = math.radians(ang)
            nx = cx + r_dist * math.cos(rad)
            ny = cy + r_dist * math.sin(rad)
            nodes.append((nx, ny, tier))

    # Filamente de rețea între noduri adiacente
    for i in range(len(nodes) - 1):
        x1, y1, t1 = nodes[i]
        x2, y2, t2 = nodes[i + 1]
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist < 65:
            elements.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{glow_ref}" stroke-width="0.9" stroke-opacity="0.5"/>')

    # Desenează corpurile celulare
    for nx, ny, tier in nodes:
        rad_cell = 7.5 - tier * 1.5
        elements.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{rad_cell * 1.8}" fill="{fill_ref}" fill-opacity="0.2" stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="0.6"/>')
        elements.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{rad_cell}" fill="{glow_ref}" fill-opacity="0.9"/>')

    # 3. Nucleu central radiant
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="22" fill="{fill_ref}" fill-opacity="0.4" stroke="{glow_ref}" stroke-width="2.0" stroke-opacity="0.95"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_road_perspective(seed: bytes, gid: str) -> str:
    """Autostradă nocturnă în perspectivă 3D infinită și flux cinetic pentru Auto & Trafic."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    vx = W - 110 + (seed[1] % 24) - 12
    vy = 52 + (seed[2] % 12) - 6
    y_bot = H + 10

    # 1. Orizont luminos cu difuzie
    elements.append(f'<line x1="{W * 0.35}" y1="{vy}" x2="{W + 20}" y2="{vy}" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.6"/>')
    elements.append(f'<circle cx="{vx}" cy="{vy}" r="12" fill="{fill_ref}" fill-opacity="0.3" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.95"/>')
    elements.append(f'<circle cx="{vx}" cy="{vy}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>')

    # 2. Liniile benzilor în perspectivă forțată
    offsets = (-220, -150, -95, -45, -15, 15, 45, 95, 150, 220)
    for off in offsets:
        x_bot = vx + off * 1.85
        sw = 2.2 if abs(off) in (15, 95) else 1.1
        op = 0.85 if abs(off) in (15, 95) else 0.45
        dash = ' stroke-dasharray="8,6"' if abs(off) in (45, 150) else ""
        elements.append(f'<line x1="{vx}" y1="{vy}" x2="{x_bot:.1f}" y2="{y_bot}" stroke="{glow_ref}" stroke-width="{sw}" stroke-opacity="{op}"{dash}/>')

    # 3. Marcaje luminoase transversale (linii de adâncime cu spacing logaritmic)
    for step in range(1, 9):
        t = (step / 8.0) ** 1.8
        y_tier = vy + t * (y_bot - vy)
        span = t * 380
        elements.append(
            f'<line x1="{vx - span:.1f}" y1="{y_tier:.1f}" x2="{vx + span:.1f}" y2="{y_tier:.1f}" '
            f'stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="{0.2 + t * 0.5:.2f}"/>'
        )

    # 4. Arce aerodinamice de tunel suspendat deasupra carosabilului
    for step in range(1, 5):
        t = (step / 4.0) ** 1.3
        y_top = vy - t * 45
        y_base_t = vy + t * 120
        span = t * 240
        elements.append(
            f'<path d="M {vx - span:.1f} {y_base_t:.1f} Q {vx} {y_top:.1f} {vx + span:.1f} {y_base_t:.1f}" '
            f'fill="none" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="{0.35 + t * 0.45:.2f}"/>'
        )

    return "".join(elements)


def _gen_perspective_lines(seed: bytes, gid: str) -> str:
    """Linii cinetice de tunel aerodinamic și vectori de viteză pentru Auto & Mobilitate."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 115
    cy = H // 2
    num_lines = 18

    for i in range(num_lines):
        t = i / (num_lines - 1)
        y = 35 + t * (H - 70)
        x_start = W * 0.4 + t * 35
        x_end = W - 15
        curve_drop = (math.sin(t * math.pi) * 28) - 14
        elements.append(
            f'<path d="M {x_start:.1f} {y:.1f} Q {cx - 40} {y + curve_drop:.1f} {x_end} {y:.1f}" '
            f'fill="none" stroke="{glow_ref}" stroke-width="{1.0 + t * 0.8:.2f}" stroke-dasharray="10,6" stroke-opacity="{0.35 + t * 0.45:.2f}"/>'
        )

    # Arc de contur aerodinamic prim-plan
    elements.append(
        f'<path d="M {cx - 130} {cy + 85} Q {cx + 40} {cy + 40} {cx + 90} {cy - 75}" '
        f'fill="none" stroke="{glow_ref}" stroke-width="2.8" stroke-opacity="0.95"/>'
    )
    elements.append(
        f'<path d="M {cx - 130} {cy + 75} Q {cx + 35} {cy + 30} {cx + 85} {cy - 85}" '
        f'fill="none" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.5"/>'
    )
    elements.append(f'<circle cx="{cx + 90}" cy="{cy - 75}" r="8" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="2.0" stroke-opacity="0.95"/>')
    elements.append(f'<circle cx="{cx + 90}" cy="{cy - 75}" r="3.5" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_progress_steps(seed: bytes, gid: str) -> str:
    """Trepte monumentale de ascensiune izometrică 3D pentru Carieră & Educație."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    ox = W - 185
    oy = H - 35
    step_w = 26
    step_d = 20
    step_h = 24
    num_steps = 6

    cos30 = 0.866
    sin30 = 0.5

    for i in range(num_steps):
        # Fațetă superioară, frontală și laterală pentru fiecare treaptă
        h_total = (i + 1) * step_h
        bx = ox + i * step_w
        by = oy - i * 14

        # Fațetă frontală
        elements.append(
            f'<polygon points="{bx},{by} {bx + step_w},{by - 7} {bx + step_w},{by - h_total - 7} {bx},{by - h_total}" '
            f'fill="{fill_ref}" fill-opacity="{0.25 + i * 0.1:.2f}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.85"/>'
        )
        # Fațetă superioară
        elements.append(
            f'<polygon points="{bx},{by - h_total} {bx + step_w},{by - h_total - 7} {bx + step_w + step_d * cos30:.1f},{by - h_total - 7 - step_d * sin30:.1f} {bx + step_d * cos30:.1f},{by - h_total - step_d * sin30:.1f}" '
            f'fill="{fill_ref}" fill-opacity="{0.45 + i * 0.08:.2f}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.95"/>'
        )
        # Punct nodal pe colțul superior
        elements.append(f'<circle cx="{bx + step_w / 2:.1f}" cy="{by - h_total - 4:.1f}" r="3" fill="{glow_ref}" fill-opacity="0.9"/>')

    # Fascicul ascendent de traiectorie
    p_start = (ox - 10, oy - 15)
    p_end = (ox + num_steps * step_w + 15, oy - num_steps * step_h - 35)
    elements.append(
        f'<line x1="{p_start[0]}" y1="{p_start[1]}" x2="{p_end[0]}" y2="{p_end[1]}" '
        f'stroke="{glow_ref}" stroke-width="2.2" stroke-opacity="0.95"/>'
    )
    elements.append(f'<circle cx="{p_end[0]}" cy="{p_end[1]}" r="6.5" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_document_lines(seed: bytes, gid: str) -> str:
    """Dosare editoriale plutitoare în spațiu 3D și sigiliu monumental pentru Carieră/Educație."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    # 3 documente înclinate izometric suprapuse
    docs = [
        (W - 170, 65, 85, 135, -8, 0.15, 0.5),
        (W - 150, 48, 92, 145, 4, 0.25, 0.75),
        (W - 130, 32, 98, 155, 0, 0.4, 0.95),
    ]

    for dx, dy, dw, dh, rot, op_f, op_s in docs:
        elements.append(
            f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="6" fill="{fill_ref}" fill-opacity="{op_f:.2f}" '
            f'stroke="{glow_ref}" stroke-width="1.5" stroke-opacity="{op_s:.2f}" transform="rotate({rot} {dx + dw / 2} {dy + dh / 2})"/>'
        )
        # Linii textuale hașurate
        for li in range(6):
            ly = dy + 32 + li * 18
            elements.append(
                f'<line x1="{dx + 16}" y1="{ly}" x2="{dx + dw - 18}" y2="{ly}" stroke="{glow_ref}" '
                f'stroke-width="1.2" stroke-opacity="{op_s * 0.7:.2f}" transform="rotate({rot} {dx + dw / 2} {dy + dh / 2})"/>'
            )

    # Sigiliu de absolvire / distincție cu lauri
    sx, sy = W - 80, H - 65
    elements.append(f'<circle cx="{sx}" cy="{sy}" r="22" fill="{fill_ref}" fill-opacity="0.55" stroke="{glow_ref}" stroke-width="2.0" stroke-opacity="0.95"/>')
    elements.append(f'<circle cx="{sx}" cy="{sy}" r="15" fill="none" stroke="{glow_ref}" stroke-width="1.0" stroke-dasharray="3,3" stroke-opacity="0.8"/>')
    elements.append(f'<circle cx="{sx}" cy="{sy}" r="5" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_isometric_prism(seed: bytes, gid: str) -> str:
    """Grup de prisme de cristal izometrice 3D cu refracție pentru Energie & Economic."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W * 0.74 + (seed[1] % 20) - 10
    cy = H * 0.52 + (seed[2] % 20) - 10

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

        d_top = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_r[0]:.1f} {p_top_r[1]:.1f} L {p_top_back[0]:.1f} {p_top_back[1]:.1f} L {p_top_l[0]:.1f} {p_top_l[1]:.1f} Z"
        d_left = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_l[0]:.1f} {p_top_l[1]:.1f} L {p_bot_l[0]:.1f} {p_bot_l[1]:.1f} L {p_bot[0]:.1f} {p_bot[1]:.1f} Z"
        d_right = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_r[0]:.1f} {p_top_r[1]:.1f} L {p_bot_r[0]:.1f} {p_bot_r[1]:.1f} L {p_bot[0]:.1f} {p_bot[1]:.1f} Z"

        return (
            f'<path d="{d_top}" fill="{fill_ref}" fill-opacity="{op_top:.2f}" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.95"/>'
            f'<path d="{d_left}" fill="{fill_ref}" fill-opacity="{op_left:.2f}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.75"/>'
            f'<path d="{d_right}" fill="{fill_ref}" fill-opacity="{op_right:.2f}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.9"/>'
        )

    # 4 prisme izometrice interconectate
    elements.append(iso_box(cx, cy + 35, 52, 68, 55, 0.45, 0.28, 0.55))
    elements.append(iso_box(cx - 55, cy - 12, 32, 45, 34, 0.35, 0.20, 0.45))
    elements.append(iso_box(cx + 42, cy - 25, 38, 30, 48, 0.40, 0.24, 0.50))
    elements.append(iso_box(cx - 15, cy - 65, 26, 36, 28, 0.30, 0.18, 0.40))

    # Conexiuni de rețea energetică între prisme
    elements.append(f'<line x1="{cx - 135}" y1="{cy + 45}" x2="{cx + 75}" y2="{cy - 55}" stroke="{glow_ref}" stroke-width="1.1" stroke-dasharray="4,4" stroke-opacity="0.5"/>')
    elements.append(f'<line x1="{cx - 95}" y1="{cy - 70}" x2="{cx + 95}" y2="{cy + 30}" stroke="{glow_ref}" stroke-width="1.1" stroke-dasharray="4,4" stroke-opacity="0.5"/>')
    return "".join(elements)


def _gen_financial_bars(seed: bytes, gid: str) -> str:
    """Histogramă izometrică 3D și spline bursier de trend pentru Energie & Finanțe."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    bx = W - 185
    by = H - 35
    bar_w = 22
    bar_d = 16
    cos30 = 0.866
    sin30 = 0.5

    heights = (45, 78, 62, 115, 148, 132, 165)
    pts_trend = []

    for i, h_val in enumerate(heights):
        x = bx + i * 24
        y = by - i * 4

        # Fațetă frontală
        elements.append(
            f'<polygon points="{x},{y} {x + bar_w},{y} {x + bar_w},{y - h_val} {x},{y - h_val}" '
            f'fill="{fill_ref}" fill-opacity="{0.25 + (h_val / 180) * 0.3:.2f}" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.8"/>'
        )
        # Fațetă laterală dreaptă
        elements.append(
            f'<polygon points="{x + bar_w},{y} {x + bar_w + bar_d * cos30:.1f},{y - bar_d * sin30:.1f} {x + bar_w + bar_d * cos30:.1f},{y - h_val - bar_d * sin30:.1f} {x + bar_w},{y - h_val}" '
            f'fill="{fill_ref}" fill-opacity="{0.4 + (h_val / 180) * 0.25:.2f}" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.85"/>'
        )
        # Fațetă superioară iluminată
        elements.append(
            f'<polygon points="{x},{y - h_val} {x + bar_w},{y - h_val} {x + bar_w + bar_d * cos30:.1f},{y - h_val - bar_d * sin30:.1f} {x + bar_d * cos30:.1f},{y - h_val - bar_d * sin30:.1f}" '
            f'fill="{fill_ref}" fill-opacity="0.65" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.95"/>'
        )
        pts_trend.append((x + bar_w / 2, y - h_val - 12))

    # Linie curbă de trend bursier spline
    d_trend = [f"M {pts_trend[0][0]:.1f} {pts_trend[0][1]:.1f}"]
    for i in range(1, len(pts_trend)):
        p0, p1 = pts_trend[i - 1], pts_trend[i]
        d_trend.append(f"Q {p0[0]:.1f} {p0[1]:.1f} {(p0[0] + p1[0]) / 2:.1f} {(p0[1] + p1[1]) / 2:.1f}")
    d_trend.append(f"L {pts_trend[-1][0]:.1f} {pts_trend[-1][1]:.1f}")
    elements.append(f'<path d="{" ".join(d_trend)}" fill="none" stroke="{glow_ref}" stroke-width="2.4" stroke-opacity="0.95"/>')

    for px, py in pts_trend:
        elements.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_architectural_arch(seed: bytes, gid: str) -> str:
    """Arcadă arhitecturală monumentală în perspectivă forțată pentru Cultură & Turism."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 110
    base_y = H - 30
    w_arch = 110
    h_col = 95

    # 5 arcade de adâncime
    for tier in (1.0, 0.82, 0.65, 0.50, 0.36):
        w_cur = w_arch * tier
        h_cur = h_col * tier
        r_cur = w_cur / 2
        d_arch = (
            f"M {cx - r_cur:.1f} {base_y} L {cx - r_cur:.1f} {base_y - h_cur:.1f} "
            f"A {r_cur:.1f} {r_cur:.1f} 0 0 1 {cx + r_cur:.1f} {base_y - h_cur:.1f} "
            f"L {cx + r_cur:.1f} {base_y}"
        )
        op = 0.25 + (1.0 - tier) * 0.55
        sw = 1.0 + (1.0 - tier) * 1.0
        elements.append(f'<path d="{d_arch}" fill="none" stroke="{glow_ref}" stroke-width="{sw:.2f}" stroke-opacity="{op:.2f}"/>')
        # Cheie de boltă (keystone)
        elements.append(f'<polygon points="{cx - 5},{base_y - h_cur - r_cur - 4} {cx + 5},{base_y - h_cur - r_cur - 4} {cx + 3.5},{base_y - h_cur - r_cur + 8} {cx - 3.5},{base_y - h_cur - r_cur + 8}" fill="{fill_ref}" fill-opacity="0.6" stroke="{glow_ref}" stroke-width="1.0" stroke-opacity="0.9"/>')

    # Pilastri și soclu
    elements.append(f'<line x1="{cx - 95}" y1="{base_y}" x2="{cx + 95}" y2="{base_y}" stroke="{glow_ref}" stroke-width="2.2" stroke-opacity="0.9"/>')
    elements.append(f'<line x1="{cx - 110}" y1="{base_y + 8}" x2="{cx + 110}" y2="{base_y + 8}" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.7"/>')
    return "".join(elements)


def _gen_heritage_shapes(seed: bytes, gid: str) -> str:
    """Rozetă de patrimoniu sacru și roză a vânturilor pentru Turism & Tradiție."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 115
    cy = H // 2
    r_outer = 85

    # 1. Inele concentrice de cadrane
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="{fill_ref}" fill-opacity="0.1" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.85"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer - 12}" fill="none" stroke="{glow_ref}" stroke-width="0.8" stroke-dasharray="3,3" stroke-opacity="0.55"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r_outer - 28}" fill="{fill_ref}" fill-opacity="0.18" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.75"/>')

    # 2. Stea cu 16 fațete (compass rose)
    for ang in range(0, 360, 22):
        rad = math.radians(ang)
        rad_perp = rad + math.pi / 2
        d_len = 68 if ang % 90 == 0 else (52 if ang % 45 == 0 else 38)
        w_base = 7 if ang % 90 == 0 else 4.5
        tip_x = cx + d_len * math.cos(rad)
        tip_y = cy + d_len * math.sin(rad)
        s1_x = cx + w_base * math.cos(rad_perp)
        s1_y = cy + w_base * math.sin(rad_perp)
        s2_x = cx - w_base * math.cos(rad_perp)
        s2_y = cy - w_base * math.sin(rad_perp)

        op = 0.55 if ang % 90 == 0 else 0.35
        elements.append(f'<polygon points="{cx},{cy} {s1_x:.1f},{s1_y:.1f} {tip_x:.1f},{tip_y:.1f}" fill="{fill_ref}" fill-opacity="{op}" stroke="{glow_ref}" stroke-width="0.9" stroke-opacity="0.85"/>')
        elements.append(f'<polygon points="{cx},{cy} {s2_x:.1f},{s2_y:.1f} {tip_x:.1f},{tip_y:.1f}" fill="{fill_ref}" fill-opacity="{op * 0.5:.2f}" stroke="{glow_ref}" stroke-width="0.9" stroke-opacity="0.85"/>')

    elements.append(f'<circle cx="{cx}" cy="{cy}" r="14" fill="{fill_ref}" fill-opacity="0.6" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.95"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_civic_columns(seed: bytes, gid: str) -> str:
    """Colonadă neoclasică monumentală și fronton civic pentru Politică & Instituții."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 120
    top_architrave = 62
    bot_base = H - 42
    w_span = 150

    # 1. Fronton triunghiular
    ped_apex = 28
    elements.append(f'<polygon points="{cx},{ped_apex} {cx - w_span / 2},{top_architrave - 8} {cx + w_span / 2},{top_architrave - 8}" fill="{fill_ref}" fill-opacity="0.22" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.9"/>')
    elements.append(f'<circle cx="{cx}" cy="{ped_apex + 18}" r="8" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="1.4" stroke-opacity="0.95"/>')

    # 2. Arhitravă dublă și soclu
    elements.append(f'<rect x="{cx - w_span / 2}" y="{top_architrave - 8}" width="{w_span}" height="10" rx="2" fill="{fill_ref}" fill-opacity="0.35" stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.9"/>')
    elements.append(f'<rect x="{cx - w_span / 2 - 8}" y="{bot_base}" width="{w_span + 16}" height="12" rx="2" fill="{fill_ref}" fill-opacity="0.35" stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.9"/>')

    # 3. 5 coloane canelate
    col_offsets = (-54, -27, 0, 27, 54)
    for off in col_offsets:
        x_c = cx + off
        elements.append(f'<rect x="{x_c - 7}" y="{top_architrave + 2}" width="14" height="{bot_base - top_architrave - 2}" rx="1" fill="{fill_ref}" fill-opacity="0.28" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.85"/>')
        elements.append(f'<line x1="{x_c}" y1="{top_architrave + 2}" x2="{x_c}" y2="{bot_base}" stroke="{glow_ref}" stroke-width="1.0" stroke-opacity="0.55"/>')

    return "".join(elements)


def _gen_editorial_block(seed: bytes, gid: str) -> str:
    """Compoziție constructivistă De Stijl / Golden Ratio pentru Politică & Editorial."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 125
    cy = H // 2

    # Blocuri geometrice proporționale
    blocks = [
        (cx - 75, cy - 85, 120, 80, 0.22, 0.7),
        (cx - 35, cy - 45, 95, 110, 0.35, 0.85),
        (cx - 85, cy + 15, 75, 65, 0.18, 0.6),
        (cx + 25, cy + 25, 60, 50, 0.45, 0.95),
    ]

    for bx, by, bw, bh, op_f, op_s in blocks:
        elements.append(
            f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="4" fill="{fill_ref}" fill-opacity="{op_f:.2f}" '
            f'stroke="{glow_ref}" stroke-width="1.5" stroke-opacity="{op_s:.2f}"/>'
        )

    # Axe de calibrare
    elements.append(f'<line x1="{cx - 110}" y1="{cy}" x2="{cx + 100}" y2="{cy}" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.9"/>')
    elements.append(f'<line x1="{cx}" y1="{cy - 95}" x2="{cx}" y2="{cy + 95}" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.9"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_field_curves(seed: bytes, gid: str) -> str:
    """Velodrom dinamic și arce parabolice de stadion pentru Sport."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 115
    cy = H // 2

    # Piste eliptice suprapuse în rotație
    for i in range(7):
        rx = 45 + i * 16
        ry = 28 + i * 12
        rot = -25 + i * 6
        elements.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill_ref}" fill-opacity="{0.06 + i * 0.04:.2f}" '
            f'stroke="{glow_ref}" stroke-width="{1.0 + i * 0.15:.2f}" stroke-opacity="{0.35 + i * 0.09:.2f}" transform="rotate({rot} {cx} {cy})"/>'
        )

    # Axe transversale de poartă
    elements.append(f'<line x1="{cx - 105}" y1="{cy - 45}" x2="{cx + 105}" y2="{cy + 45}" stroke="{glow_ref}" stroke-width="1.5" stroke-opacity="0.8"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="12" fill="{fill_ref}" fill-opacity="0.5" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.95"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_sport_geometry(seed: bytes, gid: str) -> str:
    """Traiectorii cinetice parabolice și telemetrie sportivă de precizie."""
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 115
    cy = H // 2

    # Cadrane de telemetrie
    for r_t in (75, 52, 30):
        elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r_t}" fill="{fill_ref}" fill-opacity="0.12" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.7"/>')

    # Traiectorii parabolice cinetice
    elements.append(f'<path d="M {cx - 130} {H - 35} Q {cx - 40} 35 {cx + 60} {cy - 30}" fill="none" stroke="{glow_ref}" stroke-width="2.5" stroke-opacity="0.95"/>')
    elements.append(f'<path d="M {cx - 110} {H - 25} Q {cx - 20} 55 {cx + 75} {cy - 15}" fill="none" stroke="{glow_ref}" stroke-width="1.3" stroke-dasharray="4,4" stroke-opacity="0.6"/>')

    elements.append(f'<circle cx="{cx + 60}" cy="{cy - 30}" r="7" fill="{fill_ref}" fill-opacity="0.6" stroke="{glow_ref}" stroke-width="1.8" stroke-opacity="0.95"/>')
    elements.append(f'<circle cx="{cx + 60}" cy="{cy - 30}" r="3" fill="{glow_ref}" fill-opacity="0.95"/>')
    return "".join(elements)


def _gen_wireframe_mesh(seed: bytes, gid: str) -> str:
    """Plasă topografică 3D densă (relief montan / grid sci-fi) — The Verge / Unsplash style. EXCLUSIV Tech & AI."""
    elements = []
    rows = 20
    cols = 28
    y_start, y_end = 45, 245

    freq_x = 0.038 + (seed[1] % 20) * 0.001
    freq_z = 0.055 + (seed[2] % 15) * 0.002
    phase = (seed[3] % 100) * 0.06
    amp_base = 28.0 + (seed[5] % 14)

    grid = []
    for r in range(rows):
        row_pts = []
        t = r / (rows - 1)
        y_base = y_start + t * (y_end - y_start)
        span_x = 240 + t * 230
        x_min = (W - span_x) / 2
        amp = amp_base * (0.35 + 0.65 * t)

        for c in range(cols):
            s = c / (cols - 1)
            x = x_min + s * span_x
            wave = (
                math.sin(c * freq_x * 8 + phase) * 0.55 +
                math.cos(r * freq_z * 6 + phase * 0.7) * 0.45
            )
            elevation = wave * amp * math.sin(s * math.pi)
            y = y_base - elevation
            row_pts.append((round(x, 1), round(y, 1)))
        grid.append(row_pts)

    glow_ref = f"url(#art-3d-glow-{gid})"

    # 1. Curbe transversale de relief
    for r in range(rows):
        row_pts = grid[r]
        t = r / (rows - 1)
        opacity = 0.2 + 0.75 * (t ** 1.3)
        sw = 0.9 + 0.9 * t
        d_parts = [f"M {row_pts[0][0]} {row_pts[0][1]}"]
        for c in range(1, cols):
            p0 = row_pts[c - 1]
            p1 = row_pts[c]
            d_parts.append(f"Q {p0[0]} {p0[1]} {(p0[0] + p1[0]) / 2} {(p0[1] + p1[1]) / 2}")
        d_parts.append(f"L {row_pts[-1][0]} {row_pts[-1][1]}")
        elements.append(f'<path d="{" ".join(d_parts)}" fill="none" stroke="{glow_ref}" stroke-width="{sw:.2f}" stroke-opacity="{opacity:.2f}"/>')

    # 2. Linii longitudinale de adâncime
    for c in range(0, cols, 2):
        d_parts = [f"M {grid[0][c][0]} {grid[0][c][1]}"]
        for r in range(1, rows):
            d_parts.append(f"L {grid[r][c][0]} {grid[r][c][1]}")
        s = c / (cols - 1)
        op = 0.15 + 0.35 * math.sin(s * math.pi)
        elements.append(f'<path d="{" ".join(d_parts)}" fill="none" stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="{op:.2f}" stroke-dasharray="2,3"/>')

    # 3. Noduri strălucitoare pe crestele cele mai înalte
    for r in range(2, rows, 3):
        for c in range(3, cols - 3, 4):
            pt = grid[r][c]
            elements.append(f'<circle cx="{pt[0]}" cy="{pt[1]}" r="1.8" fill="{glow_ref}" fill-opacity="0.95"/>')

    return "".join(elements)


def _gen_circuit_matrix(seed: bytes, gid: str) -> str:
    """Matrice densă de circuite imprimate (PCB bus architecture) — EXCLUSIV Tech & AI."""
    elements = []
    cx = W - 110 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 20) - 10
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    # 1. Pătrat micro-grid fundal
    for gx in range(cx - 160, cx + 80, 24):
        for gy in range(cy - 90, cy + 90, 24):
            elements.append(f'<circle cx="{gx}" cy="{gy}" r="0.8" fill="{glow_ref}" fill-opacity="0.3"/>')

    # 2. Microcip central multistrat
    chip_size = 58
    elements.append(f'<rect x="{cx - chip_size // 2}" y="{cy - chip_size // 2}" width="{chip_size}" height="{chip_size}" rx="8" fill="{fill_ref}" fill-opacity="0.3" stroke="{glow_ref}" stroke-width="2.4" stroke-opacity="0.95"/>')
    elements.append(f'<rect x="{cx - 18}" y="{cy - 18}" width="36" height="36" rx="4" fill="none" stroke="{glow_ref}" stroke-width="1.2" stroke-dasharray="3,3" stroke-opacity="0.7"/>')
    elements.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="{glow_ref}" fill-opacity="0.95"/>')

    # 3. 24 de piste de date la 45° cu via-pads
    num_traces = 18
    for i in range(num_traces):
        slot = i - (num_traces - 1) / 2
        y_start = cy + slot * 6.5
        x0 = cx - chip_size // 2
        len1 = 18 + (i * 7 + seed[3]) % 35
        x1 = x0 - len1
        diag_len = 16 + (i * 5 + seed[4]) % 24
        x2 = x1 - diag_len
        y2 = y_start + (diag_len if slot >= 0 else -diag_len)
        len3 = 35 + (i * 11 + seed[5]) % 65
        x3 = x2 - len3
        d_trace = f"M {x0} {y_start} L {x1} {y_start} L {x2} {y2} L {x3} {y2}"
        op = 0.4 + (1.0 - abs(slot) / 10) * 0.55
        elements.append(f'<path d="{d_trace}" fill="none" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="{op:.2f}"/>')
        elements.append(f'<circle cx="{x3}" cy="{y2}" r="2.8" fill="{glow_ref}" fill-opacity="{op:.2f}"/>')
        elements.append(f'<circle cx="{x3}" cy="{y2}" r="5.5" fill="none" stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="{op * 0.7:.2f}"/>')

    return "".join(elements)


def _gen_parametric_waves(seed: bytes, gid: str) -> str:
    """Panglici fluide 3D ondulate (The Verge / The New Stack style) — EXCLUSIV Tech & AI."""
    elements = []
    num_ribbons = 16
    base_y = H * 0.52 + (seed[0] % 16) - 8
    freq1 = 0.015 + (seed[1] % 10) * 0.0008
    freq2 = 0.026 + (seed[2] % 10) * 0.001
    phase_step = 0.32 + (seed[3] % 8) * 0.025
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    for r in range(num_ribbons):
        p = (seed[4] % 50) * 0.1 + r * phase_step
        thickness = 12 + r * 2.2
        y_offset = (r - (num_ribbons - 1) / 2) * 11

        pts_top, pts_bot = [], []
        steps = 20
        dx = W / steps
        for s in range(steps + 1):
            x = s * dx
            wave = (
                math.sin(x * freq1 + p) * 36.0 +
                math.cos(x * freq2 - p * 0.7) * 18.0
            )
            persp = 0.7 + 0.5 * (x / W)
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
        op_fill = 0.08 + (r / num_ribbons) * 0.16
        op_stroke = 0.45 + (r / num_ribbons) * 0.5
        sw = 1.2 if r < num_ribbons - 3 else 2.2
        elements.append(
            f'<path d="{d_ribbon}" fill="{fill_ref}" fill-opacity="{op_fill:.2f}" stroke="{glow_ref}" stroke-width="{sw}" stroke-opacity="{op_stroke:.2f}"/>'
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
