"""Motor de Artă Generativă 3D Procedurală (SVG) pentru izz.ro.

Generează matematic compoziții editoriale 3D abstracte (wireframe mesh, circuite PCB,
panglici parametrice, vortex optic și prisme izometrice), inspirate din grafica
publicațiilor tehnologice contemporane (The Verge, Wired, The New Stack, Unsplash 3D).

Fiecare compoziție este 100% matematică (curbe Bézier, proiecții izometrice, ecuații de undă),
fără fișiere raster externe, fără costuri de API și consumând ZERO fișiere din plafonul
Cloudflare Workers.
"""
from __future__ import annotations

import math


# Dimensiuni cadru compozițional SVG (raport standard card ~1.9:1)
W, H = 480, 252


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(val, hi))


def _gen_wireframe_mesh(seed: bytes, gid: str) -> str:
    """Teren topografic 3D wireframe (perspectivă + linii de relief + unde sinusoidale).
    Inspirat din grafica de telemetrie și topologie de date (stil Unsplash 3D telemetry).
    """
    elements = []
    rows = 11
    cols = 16
    y_start = 60
    y_end = 240
    
    # Parametri deterministi din seed
    freq_x = 0.035 + (seed[1] % 20) * 0.001
    freq_z = 0.05 + (seed[2] % 15) * 0.002
    phase = (seed[3] % 100) * 0.05
    amp_base = 22.0 + (seed[5] % 12)

    # Coordonate 3D proiectate
    grid = []
    for r in range(rows):
        row_pts = []
        t = r / (rows - 1)  # 0 (orizont) -> 1 (prim plan)
        y_base = y_start + t * (y_end - y_start)
        span_x = 220 + t * 240  # perspectivă unghiulară conică
        x_min = (W - span_x) / 2
        
        # Amplitudinea crește spre prim-plan
        amp = amp_base * (0.35 + 0.65 * t)
        
        for c in range(cols):
            s = c / (cols - 1)
            x = x_min + s * span_x
            # Undă compusă cu două armonice
            wave = (
                math.sin(c * freq_x * 8 + phase) * 0.6 +
                math.cos(r * freq_z * 5 + phase * 0.8) * 0.4
            )
            # Dips la margini pentru curbură organică
            edge_falloff = math.sin(s * math.pi)
            elevation = wave * amp * edge_falloff
            y = y_base - elevation
            row_pts.append((round(x, 1), round(y, 1)))
        grid.append(row_pts)

    glow_ref = f"url(#art-3d-glow-{gid})"

    # 1. Linii orizontale de contur (curbe Bézier line-to-line)
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

    # 2. Linii verticale de adâncime (perspective ribs)
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
    """
    elements = []
    # Centrul procesorului poziționat în dreapta
    cx = W - 110 + (seed[1] % 20) - 10
    cy = H // 2 + (seed[2] % 20) - 10
    
    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    # Corpul central al cipului (pătrat rotunjit sau romb rotit la 45°)
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
    # Nodul luminos central
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="{glow_ref}" fill-opacity="0.95"/>'
    )

    # Trasee de magistrale (PCB traces) cu unghiuri canonice de 45°
    num_traces = 9
    for i in range(num_traces):
        slot = i - (num_traces - 1) / 2
        y_start = cy + slot * 10
        # Punct de plecare de la marginea cipului
        x0 = cx - chip_size // 2
        # Lungimea primei porțiuni orizontale
        len1 = 20 + (i * 7 + seed[3]) % 35
        x1 = x0 - len1
        y1 = y_start
        # Bending la 45°
        dy = slot * 16
        dx = abs(dy)
        x2 = x1 - dx
        y2 = y1 + dy
        # Punct terminus pe stânga
        x3 = _clamp(x2 - 40 - ((i * 13 + seed[4]) % 50), 30, x2 - 10)
        y3 = y2

        d = f"M {x0:.1f} {y1:.1f} L {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f} L {x3:.1f} {y3:.1f}"
        op = 0.45 + (i % 3) * 0.18
        elements.append(
            f'<path d="{d}" fill="none" stroke="{glow_ref}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="{op:.2f}"/>'
        )
        # Pad circular la capătul traseului
        elements.append(
            f'<circle cx="{x3:.1f}" cy="{y3:.1f}" r="3.2" fill="{glow_ref}" fill-opacity="0.85"/>'
        )
        elements.append(
            f'<circle cx="{x3:.1f}" cy="{y3:.1f}" r="1.3" fill="#15171c"/>'
        )

    # Linii secundare paralele în fundal
    for j in range(4):
        bx = cx + 38 + j * 12
        by = 25 + j * 48
        elements.append(
            f'<path d="M {bx} {by} L {bx + 20} {by + 20} L {bx + 50} {by + 20}" fill="none" stroke="{glow_ref}" stroke-width="1.0" stroke-opacity="0.3"/>'
        )

    return "".join(elements)


def _gen_parametric_waves(seed: bytes, gid: str) -> str:
    """Panglici tridimensionale mătăsoase / valuri parametrice ondulate.
    Inspirat din estetica Verge / Wired de fluxuri de date fluide și fibre optice.
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

        # Construim o panglică închisă formată din curba superioară și cea inferioară
        pts_top = []
        pts_bot = []
        steps = 14
        dx = W / steps
        for s in range(steps + 1):
            x = s * dx
            # Ecuație de undă parametrică tridimensională
            wave = (
                math.sin(x * freq1 + p) * 38.0 +
                math.cos(x * freq2 - p * 0.7) * 18.0
            )
            # Perspectivă: unda devine mai mare spre dreapta
            persp = 0.65 + 0.55 * (x / W)
            y_mid = base_y + wave * persp + y_offset
            pts_top.append((x, y_mid - thickness * persp / 2))
            pts_bot.append((x, y_mid + thickness * persp / 2))

        # Construim path-ul SVG
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


def _gen_light_vortex(seed: bytes, gid: str) -> str:
    """Vortex de lumină / fascicul radial hipnotic cu punct de fugă central.
    Inspirat din ilustrațiile de viteză a datelor și spațiu dimensional.
    """
    elements = []
    cx = W * 0.72 + (seed[1] % 20) - 10
    cy = H * 0.48 + (seed[2] % 20) - 10
    
    num_rays = 28
    rot_offset = (seed[3] % 360)

    glow_ref = f"url(#art-3d-glow-{gid})"

    # Inele de adâncime concentrice
    for rad, op in ((18, 0.7), (38, 0.45), (68, 0.3), (110, 0.18), (170, 0.08)):
        elements.append(
            f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{glow_ref}" stroke-width="1.2" stroke-opacity="{op}"/>'
        )

    # Raze spiralate divergente spre exterior
    for i in range(num_rays):
        angle_deg = rot_offset + (i / num_rays) * 360
        angle_rad = math.radians(angle_deg)
        r_inner = 18
        r_outer = 190 + (i % 3) * 35

        # Punct pe cercul interior
        x0 = cx + r_inner * math.cos(angle_rad)
        y0 = cy + r_inner * math.sin(angle_rad)
        
        # Punct de control curbat (efect de rotație vortex)
        ctrl_angle = angle_rad + 0.35
        r_ctrl = (r_inner + r_outer) * 0.55
        xc = cx + r_ctrl * math.cos(ctrl_angle)
        yc = cy + r_ctrl * math.sin(ctrl_angle)

        # Punct final exterior
        x1 = cx + r_outer * math.cos(angle_rad + 0.65)
        y1 = cy + r_outer * math.sin(angle_rad + 0.65)

        d = f"M {x0:.1f} {y0:.1f} Q {xc:.1f} {yc:.1f} {x1:.1f} {y1:.1f}"
        op = 0.25 + (i % 4) * 0.18
        sw = 1.0 + (i % 3) * 0.5
        elements.append(
            f'<path d="{d}" fill="none" stroke="{glow_ref}" stroke-width="{sw}" stroke-opacity="{op:.2f}"/>'
        )

    # Punct focal orbitor
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="6" fill="{glow_ref}" fill-opacity="0.95"/>'
    )
    return "".join(elements)


def _gen_isometric_prism(seed: bytes, gid: str) -> str:
    """Structură geometrică izometrică 3D (prisme și blocuri arhitecturale flotante).
    Inspirat din ilustrațiile abstracte de arhitectură de sistem și baze de date (The New Stack).
    """
    elements = []
    cx = W * 0.74 + (seed[1] % 20) - 10
    cy = H * 0.52 + (seed[2] % 20) - 10

    glow_ref = f"url(#art-3d-glow-{gid})"
    fill_ref = f"url(#art-3d-fill-{gid})"

    # Funcție internă de proiecție cutie izometrică
    # Unghi izometric standard: cos(30°) ≈ 0.866, sin(30°) = 0.5
    cos30 = 0.866
    sin30 = 0.5

    def iso_box(ox: float, oy: float, w_box: float, d_box: float, h_box: float,
                op_top: float, op_left: float, op_right: float) -> str:
        # Vârfurile cutiei
        # Punct superior central
        p_top = (ox, oy - h_box)
        p_top_r = (ox + w_box * cos30, oy - h_box - w_box * sin30)
        p_top_l = (ox - d_box * cos30, oy - h_box - d_box * sin30)
        p_top_back = (ox + (w_box - d_box) * cos30, oy - h_box - (w_box + d_box) * sin30)

        p_bot = (ox, oy)
        p_bot_r = (ox + w_box * cos30, oy - w_box * sin30)
        p_bot_l = (ox - d_box * cos30, oy - d_box * sin30)

        # 1. Fața superioară
        d_top_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_r[0]:.1f} {p_top_r[1]:.1f} L {p_top_back[0]:.1f} {p_top_back[1]:.1f} L {p_top_l[0]:.1f} {p_top_l[1]:.1f} Z"
        # 2. Fața stângă
        d_left_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_l[0]:.1f} {p_top_l[1]:.1f} L {p_bot_l[0]:.1f} {p_bot_l[1]:.1f} L {p_bot[0]:.1f} {p_bot[0]:.1f} Z"
        # 3. Fața dreaptă
        d_right_face = f"M {p_top[0]:.1f} {p_top[1]:.1f} L {p_top_r[0]:.1f} {p_top_r[1]:.1f} L {p_bot_r[0]:.1f} {p_bot_r[1]:.1f} L {p_bot[0]:.1f} {p_bot[0]:.1f} Z"

        return (
            f'<path d="{d_top_face}" fill="{fill_ref}" fill-opacity="{op_top}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.85"/>'
            f'<path d="{d_left_face}" fill="{fill_ref}" fill-opacity="{op_left}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.7"/>'
            f'<path d="{d_right_face}" fill="{fill_ref}" fill-opacity="{op_right}" stroke="{glow_ref}" stroke-width="1.3" stroke-opacity="0.9"/>'
        )

    # Prisma principală
    elements.append(iso_box(cx, cy + 25, 48, 65, 42, 0.4, 0.25, 0.5))
    # O prismă secundară flotantă decroșată
    elements.append(iso_box(cx - 45, cy - 10, 28, 40, 24, 0.25, 0.15, 0.35))
    # Un plan translucid de fundal (grid structural)
    elements.append(
        f'<line x1="{cx - 120}" y1="{cy + 40}" x2="{cx + 60}" y2="{cy - 50}" stroke="{glow_ref}" stroke-width="0.9" stroke-dasharray="4,4" stroke-opacity="0.4"/>'
    )
    elements.append(
        f'<line x1="{cx - 80}" y1="{cy - 60}" x2="{cx + 80}" y2="{cy + 25}" stroke="{glow_ref}" stroke-width="0.9" stroke-dasharray="4,4" stroke-opacity="0.4"/>'
    )

    return "".join(elements)


# Catalogul celor 5 familii de compoziții generative
_STILURI_GENERATIVE = (
    "wireframe_mesh",
    "circuit_matrix",
    "parametric_waves",
    "light_vortex",
    "isometric_prism",
)


def genereaza_scena_generativa(a: dict, seed: bytes) -> dict:
    """Generează reprezentarea grafică 3D procedurală pentru articolul `a` pe baza `seed`-ului determinist.
    
    Alege stilul cel mai armonios în funcție de categorie și context semantic:
    - tech / ai -> circuite PCB (verde smarald/cyan) sau wireframe mesh
    - auto / stiinta -> valuri parametrice sau vortex de lumină (safir electric)
    - economic / finante -> prisme izometrice sau valuri structurale (aur lingou)
    - restul -> rotație deterministă prin seed
    """
    cat = (a.get("category") or "").strip().lower()
    gid = seed[:4].hex()
    
    if cat in ("tech", "ai", "it"):
        alegeri = ("circuit_matrix", "wireframe_mesh", "parametric_waves")
        stil = alegeri[seed[4] % len(alegeri)]
        if stil == "circuit_matrix":
            c_glow = ("#6ee7b7", "#10b981", "#047857")
            c_fill = ("#10b981", "#022c22")
        else:
            c_glow = ("#67e8f9", "#06b6d4", "#0369a1")
            c_fill = ("#06b6d4", "#082f49")
    elif cat in ("auto", "stiinta", "spatiu"):
        alegeri = ("parametric_waves", "wireframe_mesh", "light_vortex")
        stil = alegeri[seed[4] % len(alegeri)]
        c_glow = ("#93c5fd", "#3b82f6", "#1d4ed8")
        c_fill = ("#3b82f6", "#0f172a")
    elif cat in ("economic", "financiar"):
        alegeri = ("isometric_prism", "parametric_waves", "wireframe_mesh")
        stil = alegeri[seed[4] % len(alegeri)]
        c_glow = ("#fae8a2", "#dcb84e", "#8a6512")
        c_fill = ("#dcb84e", "#1c1917")
    else:
        stil = _STILURI_GENERATIVE[seed[4] % len(_STILURI_GENERATIVE)]
        c_glow = ("#fae8a2", "#dcb84e", "#8a6512")
        c_fill = ("#dcb84e", "#1d1f24")

    if stil == "wireframe_mesh":
        markup = _gen_wireframe_mesh(seed, gid)
    elif stil == "circuit_matrix":
        markup = _gen_circuit_matrix(seed, gid)
    elif stil == "parametric_waves":
        markup = _gen_parametric_waves(seed, gid)
    elif stil == "light_vortex":
        markup = _gen_light_vortex(seed, gid)
    else:
        markup = _gen_isometric_prism(seed, gid)

    return {
        "id": gid,
        "stil": stil,
        "markup": markup,
        "vb": f"0 0 {W} {H}",
        "c_glow": c_glow,
        "c_fill": c_fill,
    }
