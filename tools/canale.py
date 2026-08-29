#!/usr/bin/env python3
"""Cele patru canale prin care o sesiune poate ajunge la ceva — CLAUDE.md sect. 12a.

Capacitatea nu e un canal, e REUNIUNEA lor. Fiecare are alta retea si alta
autorizare, deci un canal testat nu e o masuratoare: pana pe 2026-08-29 aceeasi
greseala a picat de trei ori (`gh`, GA4, Cloudflare), de fiecare data verificand
un singur canal si tragand concluzia pe toate.

Scriptul umple mecanic canalul 2 (HTTP prin proxy) si le lasa pe celelalte trei
tiparite ca `?`. Asta e tot rostul lui: un tabel cu `?` in el se vede ca
incomplet, iar o limitare declarata peste un `?` se vede ca presupunere.

  python tools/canale.py api.cloudflare.com searchconsole.googleapis.com
"""
import subprocess
import sys

CANALE = (
    ("1 binar local", "which <binar> — lipsa binarului NU inseamna lipsa accesului"),
    ("2 HTTP prin proxy", None),  # singurul pe care il masoara scriptul
    ("3 conector MCP", "cale SEPARATA de proxy: apeleaza o unealta ieftina din conector"),
    ("4 runner Actions", "alta retea: un workflow poate ajunge unde sesiunea nu ajunge"),
)


def sonda(host: str) -> tuple[str, str]:
    """Canalul 2, masurat. Intoarce (stare, dovada) — dovada e ce a spus curl."""
    url = host if host.startswith("http") else f"https://{host}/"
    try:
        p = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "20", url],
            capture_output=True, text=True, timeout=40,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return "EROARE", f"{type(exc).__name__}: {exc}"
    cod = (p.stdout or "").strip()
    eroare = (p.stderr or "").strip().splitlines()
    if cod and cod != "000":
        # 401/403 de la APLICATIE inseamna host ACCESIBIL, lipseste doar credentiala.
        return "TRECE", f"HTTP {cod}"
    return "BLOCAT", eroare[-1] if eroare else "fara raspuns"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for host in sys.argv[1:]:
        stare, dovada = sonda(host)
        print(f"\n=== {host} ===")
        for nume, nota in CANALE:
            if nota is None:
                print(f"  {nume:<20} {stare:<12} {dovada}")
            else:
                print(f"  {nume:<20} {'?':<12} {nota}")
        print("  --> O limitare se declara doar cand niciun rand nu mai e '?' (sect. 12a, 16.4).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
