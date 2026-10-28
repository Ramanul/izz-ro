"""Motor de Artă Generativă 3D Procedurală (SVG) pentru izz.ro.

Generează matematic compoziții editoriale 3D abstracte și geometrie editorială caldă,
inspirate din grafica publicațiilor contemporane (The Verge, Wired, The New Stack,
The Economist, FT Weekend, Monocle).

Reguli stricte de clasificare și domeniu tematic:
- Circuitele PCB și valurile/rețelele sci-fi sunt STRICT REZERVATE știrilor Tech & AI.
- Știrile de Energie & Economic folosesc prisme izometrice arhitecturale sau geometrie caldă.
- Știrile de Sănătate, Auto/Trafic, Carieră/Educație, Cultură/Turism și toate celelalte știri non-tech
  folosesc EXCLUSIV grafică editorială neutră (geometrie caldă nobilă bazată pe secțiunea de aur).
"""
from __future__ import annotations

import hashlib
import math
import re


# Dimensiuni cadru compozițional SVG (raport standard card ~1.9:1)
W, H = 480, 252


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


def _seed(a: dict) -> bytes:
    val = (a.get("slug") or a.get("url") or a.get("title") or "default").encode("utf-8")
    return hashlib.sha256(val).digest()


# Dicționare de cuvinte-cheie pentru clasificarea domeniilor tematice
_KEYWORDS_DOMENII = {
    "sanatate": {
        "spital", "spitalul", "spitale", "spitalele", "medic", "medici", "medicul", "doctor", "doctori",
        "pacient", "pacienți", "pacienti", "pacientul", "pacienții", "tratament", "tratamente",
        "sănătate", "sanatate", "boală", "boala", "boli", "bolnavi", "vaccin", "vaccinare",
        "epidemie", "pandemie", "virus", "gripă", "gripa", "farmacie", "farmacii", "medicament",
        "medicamente", "chirurg", "chirurgie", "cardiologie", "oncologie", "dsp", "oms",
        "sanitar", "sanitară", "sanitara", "urgență", "urgenta", "ambulanță", "ambulanta", "smurd",
        "terapie", "diagnostic", "clinic", "clinică", "clinica"
    },
    "auto_trafic": {
        "auto", "trafic", "mașină", "masina", "mașini", "masini", "șosea", "sosea", "autostradă",
        "autostrada", "autostrăzi", "autostrazi", "drum", "drumul", "drumuri", "dn1", "dn2", "dn7",
        "a1", "a2", "a3", "a7", "circulație", "circulatie", "vehicul", "vehicule", "pod", "podul",
        "pasaj", "pasajul", "accident", "accidente", "rutier", "rutieră", "rutiera", "șofer", "sofer",
        "șoferi", "soferi", "conducător", "conducator", "viteză", "viteza", "radar", "parcare",
        "parcări", "parcari", "pieton", "pietoni", "permis", "dacia", "renault", "volkswagen",
        "bmw", "audi", "mercedes", "ford", "toyota", "cnair", "rar"
    },
    "cariera_educatie": {
        "educație", "educatie", "școală", "scoala", "școli", "scoli", "liceu", "licee", "elev",
        "elevi", "elevul", "profesor", "profesori", "profesorul", "universitate", "universități",
        "universitati", "facultate", "facultăți", "facultati", "studenți", "studenti", "student",
        "bacalaureat", "evaluare națională", "evaluare nationala", "titularizare", "bursă", "burse",
        "carieră", "cariera", "angajare", "angajări", "angajari", "angajatori", "angajator",
        "locuri de muncă", "locuri de munca", "salariu", "salarii", "recalificare", "învățământ",
        "invatamant", "inspectoratul școlar", "inspectoratul scolar", "cursuri", "studii",
        "diplomă", "diploma", "șomaj", "somaj"
    },
    "energie_economic": {
        "energie", "energetic", "gaz", "gaze", "curent", "electric", "electricitate", "nuclear",
        "hidro", "termocentrală", "termocentrala", "eolian", "eoliene", "solar", "fotovoltaic",
        "fotovoltaice", "petrol", "combustibil", "combustibili", "carburant", "carburanți",
        "carburanti", "bancar", "bancă", "banca", "bănci", "banci", "dobândă", "dobanda",
        "dobânzi", "dobanzi", "inflație", "inflatie", "buget", "bugetul", "fiscal", "fiscală",
        "fiscala", "impozit", "impozite", "tva", "anaf", "bnr", "economie", "economic",
        "economică", "economica", "pib", "investiții", "investitii", "euro", "lei", "miliarde",
        "milioane", "acțiuni", "actiuni", "bursă", "bursa", "bvb", "finanțe", "finante"
    },
    "cultura_turism": {
        "cultură", "cultura", "cultural", "turism", "turistic", "turiști", "turisti", "turist",
        "teatru", "muzeu", "muzee", "film", "filme", "cinema", "festival", "festivalul",
        "carte", "cărți", "carti", "autor", "autori", "scriitor", "scriitori", "patrimoniu",
        "monument", "monumente", "istoric", "istorie", "concert", "concerte", "spectacol",
        "spectacole", "expoziție", "expozitie", "expoziții", "expozitii", "hotel", "hoteluri",
        "cazare", "destinație", "destinatie", "vacanță", "vacanta", "sejur", "stațiune",
        "statiune", "pensiune", "pensiuni", "horeca"
    },
    "tech_ai": {
        "tech", "tehnologie", "ai", "it", "software", "hardware", "cip", "cipuri", "chip",
        "chips", "procesor", "procesoare", "inteligență artificială", "inteligenta artificiala",
        "algoritm", "algoritmi", "robot", "roboți", "roboti", "robotică", "robotica", "cyber",
        "securitate cibernetică", "cloud", "server", "servere", "gadget", "smartphone",
        "telefon", "telefoane", "apple", "google", "microsoft", "nvidia", "amd", "starlink",
        "spacex", "meta", "openai", "semiconductori", "microcip", "codex", "github"
    }
}


def clasifica_domeniu(title: str = "", summary: str = "", category: str = "") -> str:
    """Clasifică articolul într-un domeniu tematic pe baza categoriei și a dicționarelor de cuvinte-cheie.
    Domenii returnate: 'tech_ai', 'energie_economic', 'sanatate', 'auto_trafic', 'cariera_educatie', 'cultura_turism', 'general'.
    """
    cat_lower = (category or "").strip().lower()

    if cat_lower in ("tech", "ai", "it"):
        return "tech_ai"
    if cat_lower in ("economic", "financiar", "energie"):
        return "energie_economic"
    if cat_lower in ("auto",):
        return "auto_trafic"
    if cat_lower in ("sanatate",):
        return "sanatate"
    if cat_lower in ("educatie", "cariera"):
        return "cariera_educatie"
    if cat_lower in ("cultura", "turism"):
        return "cultura_turism"

    text = f"{title} {summary}".lower()
    words = set(re.findall(r"[a-zăâîșț0-9_-]+", text))

    scoruri = {}
    for domeniu, kw_set in _KEYWORDS_DOMENII.items():
        scor = len(words & kw_set)
        for kw in kw_set:
            if " " in kw and kw in text:
                scor += 2
        scoruri[domeniu] = scor

    top_domeniu, top_scor = max(scoruri.items(), key=lambda item: item[1])
    if top_scor >= 1:
        return top_domeniu

    return "general"


def _gen_warm_geometry(seed: bytes, gid: str) -> str:
    """Grafică editorială neutră (geometrie caldă nobilă bazată pe secțiunea de aur).
    Folosită ca stil exclusiv pe toate știrile non-tech (sănătate, auto, educație, cultură, politic, general).
    Inspirată din tipografia și grafica revistelor de înaltă ținută (The Economist, FT Weekend, Monocle).
    """
    elements = []
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    cx = W - 125 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 16) - 8

    r_mic = 42
    r_mediu = 75
    r_mare = 120

    # 1. Câmp circular translucid de profunzime
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r_mare}" fill="{fill_ref}" fill-opacity="0.12" '
        f'stroke="{glow_ref}" stroke-width="0.8" stroke-dasharray="3,5" stroke-opacity="0.35"/>'
    )

    # 2. Arcuri eliptice orbitale în aur
    elements.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{r_mediu}" ry="{r_mic + 8}" fill="none" '
        f'stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.75"/>'
    )
    elements.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{r_mic + 12}" ry="{r_mediu}" fill="none" '
        f'stroke="{glow_ref}" stroke-width="1.1" stroke-opacity="0.55"/>'
    )

    # 3. Filet dublu structural fin orizontal de aliniere
    elements.append(
        f'<line x1="{cx - 150}" y1="{cy}" x2="{cx + 100}" y2="{cy}" '
        f'stroke="{glow_ref}" stroke-width="0.8" stroke-opacity="0.45"/>'
    )
    elements.append(
        f'<line x1="{cx - 100}" y1="{cy + 4}" x2="{cx + 60}" y2="{cy + 4}" '
        f'stroke="{glow_ref}" stroke-width="0.5" stroke-opacity="0.3"/>'
    )

    # 4. Nod compozițional central rafinat (disc auriu + inel fin)
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="14" fill="{fill_ref}" fill-opacity="0.3" '
        f'stroke="{glow_ref}" stroke-width="1.6" stroke-opacity="0.85"/>'
    )
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{glow_ref}" fill-opacity="0.95"/>'
    )

    # 5. Marcaje fine de cadran (4 repere de aliniere)
    for ang in (0, 90, 180, 270):
        rad = math.radians(ang)
        x1 = cx + (r_mediu - 6) * math.cos(rad)
        y1 = cy + (r_mediu - 6) * math.sin(rad)
        x2 = cx + (r_mediu + 6) * math.cos(rad)
        y2 = cy + (r_mediu + 6) * math.sin(rad)
        elements.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="0.75"/>'
        )

    return "".join(elements)


def _gen_wireframe_mesh(seed: bytes, gid: str) -> str:
    """Teren topografic 3D wireframe (perspectivă + linii de relief + unde sinusoidale).
    Inspirat din grafica de telemetrie și topologie de date (stil Unsplash 3D telemetry).
    EXCLUSIV pentru Tech & AI.
    """
    elements = []
    rows = 11
    cols = 16
    y_start = 60
    y_end = 240

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
            edge_falloff = math.sin(s * math.pi)
            elevation = wave * amp * edge_falloff
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
            mid_x = (p0[0] + p1[0]) / 2
            d_parts.append(f"Q {p0[0]} {p0[1]} {mid_x} {(p0[1] + p1[1]) / 2}")
        d_parts.append(f"L {row_pts[-1][0]} {row_pts[-1][1]}")
        d = " ".join(d_parts)
        elements.append(
            f'<path d="{d}" fill="none" stroke="{glow_ref}" stroke-width="{sw:.2f}" stroke-opacity="{opacity:.2f}"/>'
        )

    for c in range(0, cols, 2):
        d_parts = [f"M {grid[0][c][0]} {grid[0][c][1]}"]
        for r in range(1, rows):
            d_parts.append(f"L {grid[r][c][0]} {grid[r][c][1]}")
        d = " ".join(d_parts)
        s = c / (cols - 1)
        op = 0.15 + 0.3 * math.sin(s * math.pi)
        elements.append(
            f'<path d="{d}" fill="none" stroke="{glow_ref}" stroke-width="0.85" stroke-opacity="{op:.2f}" stroke-dasharray="3,3"/>'
        )

    return "".join(elements)


def _gen_circuit_matrix(seed: bytes, gid: str) -> str:
    """Matrice de circuite imprimate (PCB bus traces) cu noduri și pastilă centrală.
    Inspirat din grafica cipurilor de calcul avansat și infrastructurii AI.
    EXCLUSIV pentru Tech & AI.
    """
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
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>'
    )

    num_traces = 9
    for i in range(num_traces):
        slot = i - (num_traces - 1) / 2
        y_start = cy + slot * 10
        x0 = cx - chip_size // 2
        len1 = 20 + (i * 7 + seed[3]) % 35
        x1 = x0 - len1
        y1 = y_start
        dy = slot * 16
        dx = abs(dy)
        x2 = x1 - dx
        y2 = y1 + dy
        x3 = _clamp(x2 - 40 - ((i * 13 + seed[4]) % 50), 30, x2 - 10)
        y3 = y2

        d = f"M {x0:.1f} {y1:.1f} L {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f} L {x3:.1f} {y3:.1f}"
        op = 0.45 + (i % 3) * 0.18
        elements.append(
            f'<path d="{d}" fill="none" stroke="{glow_ref}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="{op:.2f}"/>'
        )
        elements.append(
            f'<circle cx="{x3:.1f}" cy="{y3:.1f}" r="3.2" fill="{glow_ref}" fill-opacity="0.85"/>'
        )
        elements.append(
            f'<circle cx="{x3:.1f}" cy="{y3:.1f}" r="1.3" fill="#15171c"/>'
        )

    for j in range(4):
        bx = cx + 38 + j * 12
        by = 25 + j * 48
        elements.append(
            f'<path d="M {bx} {by} L {bx + 20} {by + 20} L {bx + 50} {by + 20}" fill="none" stroke="{glow_ref}" stroke-width="1.0" stroke-opacity="0.3"/>'
        )

    return "".join(elements)


def _gen_parametric_waves(seed: bytes, gid: str) -> str:
    """Panglici tridimensionale mătăsoase / valuri parametrice ondulate.
    EXCLUSIV pentru Tech & AI.
    """
    elements = []
    num_ribbons = 5
    base_y = H * 0.52

    freq1 = 0.012 + (seed[1] % 10) * 0.001
    freq2 = 0.024 + (seed[2] % 10) * 0.001
    phase_step = 0.42 + (seed[3] % 8) * 0.03

    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    for r in range(num_ribbons):
        p = (seed[4] % 50) * 0.1 + r * phase_step
        thickness = 14 + r * 3
        y_offset = (r - (num_ribbons - 1) / 2) * 16

        pts_top = []
        pts_bot = []
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
            p0 = pts_top[i - 1]
            p1 = pts_top[i]
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


def _gen_isometric_prism(seed: bytes, gid: str) -> str:
    """Structură geometrică izometrică 3D (prisme și blocuri arhitecturale flotante).
    Folosită pentru știri de Energie și Economie / Finanțe.
    """
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
        d_left_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_l[0]:.1f} {p_top_l[1]:.1f} L {p_bot_l[0]:.1f} {p_bot_l[1]:.1f} L {p_bot[0]:.1f} {p_bot[0]:.1f} Z"
        d_right_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_r[0]:.1f} {p_top_r[1]:.1f} L {p_bot_r[0]:.1f} {p_bot_r[1]:.1f} L {p_bot[0]:.1f} {p_bot[0]:.1f} Z"

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


def genereaza_scena_generativa(
    a: dict | None = None,
    seed: bytes | None = None,
    *,
    title: str = "",
    category: str = "",
    summary: str = "",
) -> dict:
    """Generează reprezentarea grafică 3D/geometrică pentru articol.

    Pasează obligatoriu parametrul 'summary' alături de 'title' și 'category'.
    Clasifică tematic articolul și impune:
    - Tech & AI: circuite PCB (verde smarald/cyan), wireframe mesh sau valuri de date.
    - Energie & Economic: prisme izometrice arhitecturale sau geometrie caldă.
    - Toate celelalte știri non-tech: EXCLUSIV grafică editorială neutră (geometrie caldă nobilă).
    Circuitele PCB și valurile sci-fi sunt STRICT INTERZISE pe știri non-tech.
    """
    if a:
        if not title:
            title = (a.get("title") or "").strip()
        if not category:
            category = (a.get("category") or "").strip()
        if not summary:
            summary = (a.get("summary") or a.get("lead") or a.get("teaser") or a.get("synthesis") or "").strip()

    if seed is None:
        seed = _seed(a) if a else b"\x00" * 8

    gid = seed[:4].hex()
    domeniu = clasifica_domeniu(title=title, summary=summary, category=category)

    if domeniu == "tech_ai":
        alegeri = ("circuit_matrix", "wireframe_mesh", "parametric_waves")
        stil = alegeri[seed[4] % len(alegeri)]
        if stil == "circuit_matrix":
            c_glow = ("#6ee7b7", "#10b981", "#047857")
            c_fill = ("#10b981", "#022c22")
        else:
            c_glow = ("#67e8f9", "#06b6d4", "#0369a1")
            c_fill = ("#06b6d4", "#082f49")
    elif domeniu == "energie_economic":
        alegeri = ("isometric_prism", "warm_geometry")
        stil = alegeri[seed[4] % len(alegeri)]
        c_glow = ("#fae8a2", "#dcb84e", "#8a6512")
        c_fill = ("#dcb84e", "#1c1917")
    else:
        # Sănătate, Auto/Trafic, Carieră/Educație, Cultură/Turism, Politică, Sport, General:
        # EXCLUSIV grafică editorială neutră (geometrie caldă)
        stil = "warm_geometry"
        c_glow = ("#fae8a2", "#dcb84e", "#8a6512")
        c_fill = ("#dcb84e", "#1d1f24")

    if stil == "wireframe_mesh":
        markup = _gen_wireframe_mesh(seed, gid)
    elif stil == "circuit_matrix":
        markup = _gen_circuit_matrix(seed, gid)
    elif stil == "parametric_waves":
        markup = _gen_parametric_waves(seed, gid)
    elif stil == "isometric_prism":
        markup = _gen_isometric_prism(seed, gid)
    else:
        markup = _gen_warm_geometry(seed, gid)

    return {
        "id": gid,
        "stil": stil,
        "domeniu": domeniu,
        "markup": markup,
        "vb": f"0 0 {W} {H}",
        "c_glow": c_glow,
        "c_fill": c_fill,
    }
