"""Agent grafic (HTML/CSS) — preanalizeaza articolul si compune o imagine UNICA:
paleta cu nuanta continua din continut, pictograme tematice extrase din titlu,
layout ales din mai multe scheme. Randata ulterior cu headless Chromium
(tools/gen_images.py). Aici doar construim HTML-ul (pur, testabil, fara Chromium).

De ce HTML/CSS si nu Pillow: gradienturi netede, umbre/glow, blend-modes,
tipografie web -> calitate de design peste ce poate desena Pillow. Chromium nu
exista in build-ul Cloudflare, deci randarea se face in GitHub Actions.
"""
import base64
import hashlib
import os
import re

from . import covers as _C   # reutilizam _KW_ICON, _CAT_ICONS, _norm

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ART_W, ART_H = 960, 504
COVER_W, COVER_H = 1200, 630

_FONT_B64 = None
_ICON_B64: dict = {}


def _font() -> str:
    global _FONT_B64
    if _FONT_B64 is None:
        p = os.path.join(_ASSETS, "PlayfairDisplay_800ExtraBold.ttf")
        _FONT_B64 = base64.b64encode(open(p, "rb").read()).decode() if os.path.exists(p) else ""
    return _FONT_B64


def _icon_uri(name: str) -> str:
    if name not in _ICON_B64:
        p = os.path.join(_ASSETS, "icons", f"{name}.png")
        _ICON_B64[name] = ("data:image/png;base64," + base64.b64encode(open(p, "rb").read()).decode()
                           if os.path.exists(p) else "")
    return _ICON_B64[name]


def _elements(a: dict) -> list:
    text = _C._norm(a.get("title", "")) + " " + " ".join(_C._norm(e) for e in a.get("entities") or [])
    out = []
    for pat, ic in _C._KW_ICON:
        if re.search(pat, text) and _icon_uri(ic) and ic not in out:
            out.append(ic)
        if len(out) >= 5:
            break
    if a.get("icon") and a["icon"] not in out and _icon_uri(a["icon"]):
        out.insert(0, a["icon"])
    for ic in _C._CAT_ICONS.get(a.get("category", ""), []):
        if len(out) < 3 and ic not in out and _icon_uri(ic):
            out.append(ic)
    return [e for e in out if _icon_uri(e)][:5] or ["building-community"]


def _mask(name: str, color: str, extra: str = "") -> str:
    u = _icon_uri(name)
    return (f'background:{color};-webkit-mask:url({u}) center/contain no-repeat;'
            f'mask:url({u}) center/contain no-repeat;{extra}')


_GRAIN = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E"
          "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E"
          "%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")")


def _base_css(w: int, h: int) -> str:
    return (
        "*{margin:0;padding:0;box-sizing:border-box}"
        f"@font-face{{font-family:PF;src:url(data:font/ttf;base64,{_font()})}}"
        f"html,body{{width:{w}px;height:{h}px;overflow:hidden}}"
        f".stage{{position:relative;width:{w}px;height:{h}px;overflow:hidden}}"
        f".grain{{position:absolute;inset:0;background-image:{_GRAIN};opacity:.06;mix-blend-mode:overlay}}"
        ".frame{position:absolute;inset:14px;border:2px solid rgba(201,162,39,.9)}"
        ".chip{position:absolute;top:32px;left:34px;font-family:PF;font-weight:800;font-size:26px;letter-spacing:2px;"
        "text-transform:uppercase;color:#8b6918;background:rgba(255,255,255,.55);padding:6px 16px;border-radius:4px;backdrop-filter:blur(4px)}"
        ".blob{position:absolute;border-radius:50%;filter:blur(60px);mix-blend-mode:soft-light}"
    )


def _t_aurora(a, hue, els):
    small = "".join(
        f'<div style="position:absolute;width:120px;height:120px;opacity:.55;{_mask(e, f"hsl({hue},40%,58%)")}'
        f'{"left:90px;bottom:120px" if i == 0 else "left:230px;top:150px"}"></div>'
        for i, e in enumerate(els[1:3]))
    return (
        f'<div class="stage" style="background:linear-gradient(135deg,hsl({hue},70%,92%),hsl({(hue+45)%360},62%,82%))">'
        f'<div class="blob" style="width:640px;height:640px;left:-120px;top:-160px;background:hsl({hue},85%,68%);opacity:.7"></div>'
        f'<div class="blob" style="width:560px;height:560px;right:-120px;bottom:-160px;background:hsl({(hue+180)%360},75%,72%);opacity:.6"></div>'
        f'<div style="position:absolute;right:70px;bottom:40px;width:360px;height:360px;transform:rotate(-6deg);'
        f'filter:drop-shadow(0 22px 30px rgba(30,20,50,.35));{_mask(els[0], f"hsl({hue},46%,42%)")}"></div>'
        f'{small}<div class="chip">{a.get("category","stiri")}</div><div class="frame"></div><div class="grain"></div></div>'
    )


def _t_spotlight(a, hue, els):
    return (
        f'<div class="stage" style="background:radial-gradient(circle at 60% 42%,hsl({hue},55%,90%),hsl({hue},48%,70%))">'
        f'<div style="position:absolute;left:50%;top:44%;width:520px;height:520px;transform:translate(-50%,-50%);border-radius:50%;'
        f'box-shadow:0 0 0 2px rgba(201,162,39,.25),0 0 0 60px rgba(201,162,39,.06),0 0 0 120px rgba(201,162,39,.05)"></div>'
        f'<div style="position:absolute;left:50%;top:44%;transform:translate(-50%,-50%);width:300px;height:300px;'
        f'filter:drop-shadow(0 0 34px hsla({hue},70%,55%,.7));{_mask(els[0], f"hsl({hue},52%,40%)")}"></div>'
        f'<div class="chip">{a.get("category","stiri")}</div><div class="frame"></div><div class="grain"></div></div>'
    )


def _t_split(a, hue, els):
    small = "".join(
        f'<div style="width:110px;height:110px;opacity:.8;{_mask(e, f"hsl({hue},42%,44%)")}"></div>' for e in els[1:4])
    return (
        f'<div class="stage" style="display:grid;grid-template-columns:38% 62%">'
        f'<div style="background:hsl({hue},52%,46%);display:flex;align-items:center;justify-content:center">'
        f'<div style="width:230px;height:230px;filter:drop-shadow(0 14px 20px rgba(0,0,0,.25));{_mask(els[0], f"hsl({hue},40%,90%)")}"></div></div>'
        f'<div style="background:linear-gradient(120deg,hsl({hue},55%,92%),#fff);display:flex;gap:26px;align-items:center;padding-left:60px">{small}</div>'
        f'<div class="chip" style="left:calc(38% + 34px)">{a.get("category","stiri")}</div><div class="frame"></div><div class="grain"></div></div>'
    )


def _t_poster(a, hue, els):
    row = "".join(f'<div style="width:130px;height:130px;{_mask(e, "#fff", "opacity:.95")}"></div>' for e in els[:3])
    return (
        f'<div class="stage" style="background:linear-gradient(120deg,hsl({hue},60%,52%),hsl({(hue+35)%360},62%,44%))">'
        f'<div style="position:absolute;right:-60px;top:50%;transform:translateY(-50%) rotate(-10deg);width:620px;height:620px;'
        f'opacity:.12;{_mask(els[0], "#fff")}"></div>'
        f'<div style="position:absolute;top:40px;left:40px;font-family:PF;font-weight:800;color:#fff;font-size:64px;'
        f'letter-spacing:1px;text-transform:uppercase;text-shadow:0 6px 20px rgba(0,0,0,.25)">{a.get("category","stiri")}</div>'
        f'<div style="position:absolute;bottom:56px;left:44px;display:flex;gap:28px">{row}</div>'
        f'<div class="frame" style="border-color:rgba(255,255,255,.85)"></div><div class="grain"></div></div>'
    )


_TEMPLATES = [_t_aurora, _t_spotlight, _t_split, _t_poster]


def build_html(a: dict, cover: bool = False) -> str:
    """HTML pentru imaginea articolului. cover=True -> 1200x630 (og); altfel 960x504 (banner)."""
    seed = hashlib.sha1((a.get("title") or "x").encode()).digest()
    hue = seed[0] * 360 // 256
    els = _elements(a)
    w, h = (COVER_W, COVER_H) if cover else (ART_W, ART_H)
    body = _TEMPLATES[seed[4] % len(_TEMPLATES)](a, hue, els)
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{_base_css(w, h)}</style></head>"
            f"<body>{body}</body></html>")


def art_id(a: dict) -> str:
    """ID stabil (din URL/titlu) — numele imaginii comise, independent de slug-ul de render."""
    key = a.get("url") or a.get("original_link") or a.get("title") or ""
    return hashlib.sha1(key.encode()).hexdigest()[:16]
