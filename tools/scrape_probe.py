#!/usr/bin/env python
"""Descopera selectoarele pentru o sursa Monitor Local (scraper generic).

  python tools/scrape_probe.py https://primaria-x.ro/anunturi

Ruleaza in GitHub Actions (dispatch) — runnerii au internet, sandbox-ul de dev nu.
Descarca pagina publica si raporteaza containerele HTML REPETITIVE (tag.class care apar
de multe ori si contin o ancora + text) — candidatii pentru `item=` din config.SOURCES.
Nu scrie nimic; doar informeaza alegerea selectoarelor inainte de a adauga sursa.
"""
import collections
import socket
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from generator.fetch import USER_AGENT, TIMEOUT  # noqa: E402


class _Probe(HTMLParser):
    """Numara (tag.class) si cate ancore contine direct fiecare, ca sa gaseasca lista."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.count = collections.Counter()          # tag.class -> aparitii
        self.with_anchor = collections.Counter()    # tag.class -> aparitii ce contin <a>
        self._stack: list = []                       # (tag.class, are_ancora)

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if tag == "a":
            for i in range(len(self._stack)):
                self._stack[i] = (self._stack[i][0], True)
            return
        for cls in (ad.get("class") or "").split():
            key = f"{tag}.{cls}"
            self.count[key] += 1
            self._stack.append((key, False))
            break
        else:
            self._stack.append((f"{tag}", False))

    def handle_endtag(self, tag):
        if tag == "a" or not self._stack:
            return
        key, had = self._stack.pop()
        if had and "." in key:
            self.with_anchor[key] += 1


def main() -> int:
    if len(sys.argv) < 2:
        print("uz: python tools/scrape_probe.py <URL pagina de anunturi>")
        return 2
    url = sys.argv[1]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ValueError) as exc:
        print(f"DEAD {url} -> {exc}")
        return 1

    p = _Probe()
    p.feed(raw)
    print(f"=== probe {url} ===")
    print("Candidati pentru item= (tag.class repetitiv, care contine ancore):\n")
    ranked = sorted(p.with_anchor.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked:
        print("  (niciun container repetitiv cu ancore — probabil lista e randata via JS)")
        return 1
    for key, n_anchor in ranked[:15]:
        print(f"  item='{key}'  apare de {p.count[key]}x, cu ancora de {n_anchor}x")
    print("\nAlege un container care apare de N ori (N = numarul de anunturi din lista),")
    print("apoi ruleaza feedcheck cu sursa configurata ca sa confirmi extractia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
