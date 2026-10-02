"""Detectie automata de selectori pentru clasa html_clasic (site-uri cu pagina de stiri
detectata). Pentru fiecare site:
  1) descarca pagina de stiri
  2) genereaza CANDIDATI de selectori-item: taguri cu class repetate >=3, jumatate+ cu data
  3) pentru fiecare candidat, genereaza selectori de DATA din interiorul blocului-item
     (parser HTML adevarat — regex-ul devoreaza elementele imbricate)
  4) valideaza cu parserul REAL al repo-ului (_GenericListParser): >=3 itemi, maxim itemi cu data
Versiune v3 rescrisa de la zero: v2 avea 3 backspace-uri corupte in regex-ul de bloc
(artefact de heredoc) si nu gasea niciodata blocul-item.
"""
import csv
import re
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

sys.path.insert(0, r"C:/Users/cw_26/izz-ro")
from generator.fetch import _GenericListParser

IN_PATH = r"C:/Users/cw_26/AppData/Local/Temp/clase_structuri.csv"
OUT_PATH = r"C:/Users/cw_26/AppData/Local/Temp/html_clasic_v3.csv"
WORKERS = 12
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

DATE_RE = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])[.\-/ ](0?[1-9]|1[0-2])[.\-/ ](20[12]\d)\b"
    r"|\b(20[12]\d)[.\-/](0?[1-9]|1[0-2])[.\-/](0?[1-9]|[12]\d|3[01])\b"
    r"|\b([1-9]|[12]\d|3[01]) (ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|"
    r"septembrie|octombrie|noiembrie|decembrie) (20[12]\d)\b", re.I)

VOID = {"br", "img", "meta", "input", "hr", "link", "source", "area", "col", "embed", "track", "wbr"}


class _BlocScan(HTMLParser):
    """Stat pe elemente cu prima clasa: de cate ori apar, de cate ori contin <a>, de cate ori contin data."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stiva = []
        self.stat = {}   # "tag.cls" -> [instante, cu_a, cu_data]

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        ad = dict(attrs)
        cls = (ad.get("class") or "").split()[0] if ad.get("class") else ""
        self.stiva.append([tag, cls, False, False])   # tag, cls, are_a, are_data
        if tag == "a":
            for fr in self.stiva:
                fr[2] = True

    def handle_data(self, data):
        if self.stiva and DATE_RE.search(data):
            for fr in self.stiva:
                fr[3] = True

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for idx in range(len(self.stiva) - 1, -1, -1):
            fr = self.stiva[idx]
            if fr[0] == tag:
                if fr[1] and fr[2]:
                    c = self.stat.setdefault(f"{fr[0]}.{fr[1]}", [0, 0, 0])
                    c[0] += 1
                    if fr[2]:
                        c[1] += 1
                    if fr[3]:
                        c[2] += 1
                del self.stiva[idx:]
                if self.stiva and fr[3]:
                    self.stiva[-1][3] = True
                return


class _DateScan(HTMLParser):
    """Pe un singur bloc-item: elementele cu clasa al caror subarbore contine data.
    Regex pe HTML imbricat devoreaza elementele interioare; parser adevarat aici."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stiva = []
        self.candidati = {}   # "tag.cls" -> [n, len_inner_min]

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        ad = dict(attrs)
        cls = (ad.get("class") or "").split()[0] if ad.get("class") else ""
        self.stiva.append([tag, cls, []])

    def handle_data(self, data):
        if self.stiva:
            for fr in self.stiva:
                fr[2].append(data)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for idx in range(len(self.stiva) - 1, -1, -1):
            fr = self.stiva[idx]
            if fr[0] == tag:
                inner = "".join(fr[2])
                if fr[1] and DATE_RE.search(inner):
                    c = self.candidati.setdefault(f"{fr[0]}.{fr[1]}", [0, 10**9])
                    c[0] += 1
                    c[1] = min(c[1], len(inner))
                del self.stiva[idx:]
                return


def detecteaza_item(body):
    p = _BlocScan()
    try:
        p.feed(body)
    except Exception:
        return []
    cand = []
    for cheie, (n, cu_a, cu_data) in p.stat.items():
        if n >= 3 and cu_data >= max(1, n // 2):
            cand.append((cheie, {"n": n, "cu_data": cu_data}))
    cand.sort(key=lambda kv: (-kv[1]["cu_data"], kv[0]))
    return cand[:6]


def selectori_data(bloc):
    ds = _DateScan()
    try:
        ds.feed(bloc)
    except Exception:
        return []
    return [s for s, c in sorted(ds.candidati.items(), key=lambda kv: kv[1][1])
            if c[0] >= 1][:4]


def extrage_bloc(body, tag, cls):
    """Primul bloc <tag ... class=...cls...> ... </tag> care contine o data."""
    pat = re.compile(
        r"<" + re.escape(tag) + r"\b[^>]*class=\"[^\"]*" + re.escape(cls) +
        r"[^\"]*\"[^>]*>(.*?)</" + re.escape(tag) + r">", re.S | re.I)
    for m in pat.finditer(body):
        if DATE_RE.search(m.group(1)):
            return m.group(1)
    return None


def valideaza(site, body):
    """Alege cel mai bun selector: maxim itemi cu data (scor=(cu_data, itemi))."""
    origin = "/".join(site.split("/")[:3])
    best = None
    for tag_cls, _stat in detecteaza_item(body):
        tag, cls = tag_cls.split(".", 1)
        bloc = extrage_bloc(body, tag, cls)
        date_cands = [""] + (selectori_data(bloc) if bloc else [])
        for title_sel in (None, "a"):
            for date_sel in date_cands:
                parser = _GenericListParser(origin, tag_cls, title_sel, date_sel or None)
                try:
                    parser.feed(body)
                except Exception:
                    continue
                items = [i for i in parser.items if i.get("href") and i.get("title")]
                cu_data = sum(1 for i in items if i.get("date_raw") and DATE_RE.search(i["date_raw"]))
                if len(items) >= 3:
                    scor = (cu_data, len(items))
                    if best is None or scor > best[0]:
                        best = (scor, tag_cls, title_sel or "", date_sel or "", len(items), cu_data)
        if best and best[0][0] >= 2:
            break
    return best


if __name__ == "__main__":
    rows = [r for r in csv.DictReader(open(IN_PATH, encoding="utf-8")) if r["clasa"] == "html_clasic"]
    print(f"analiz {len(rows)} site-uri html_clasic", flush=True)

    def proceseaza(r):
        try:
            req = urllib.request.Request(r["stiri_page"] or r["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=18, context=CTX) as resp:
                body = resp.read(400_000).decode("utf-8", "replace")
            best = valideaza(r["stiri_page"] or r["url"], body)
            if best and best[0][0] >= 2:
                _, item, title, date_sel, n, nd = best
                return {"judet": r["judet"], "localitate": r["localitate"],
                        "url": r["stiri_page"] or r["url"],
                        "base_url": "/".join((r["stiri_page"] or r["url"]).split("/")[:3]),
                        "item": item, "title": title or "", "date": date_sel or "",
                        "n_itemi": n, "cu_data": nd}
        except Exception as e:
            return {"judet": r["judet"], "localitate": r["localitate"], "url": r["url"],
                    "base_url": "", "item": f"err_{type(e).__name__}", "title": "", "date": "",
                    "n_itemi": 0, "cu_data": 0}
        return None

    rez = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(proceseaza, r): r for r in rows}
        for i, fut in enumerate(as_completed(futs), 1):
            h = fut.result()
            if h:
                rez.append(h)
            if i % 40 == 0:
                print(f"  {i}/{len(rows)} — {sum(1 for x in rez if x['cu_data'] >= 2)} cu date", flush=True)

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["judet", "localitate", "url", "base_url", "item", "title", "date", "n_itemi", "cu_data"])
        w.writeheader()
        w.writerows(rez)

    ok = [r for r in rez if r.get("cu_data", 0) and int(r["cu_data"]) >= 2]
    print(f"DONE: {len(ok)} din {len(rows)} surse validate cu itemi datati")
    from collections import Counter
    print("clasuri item:", dict(Counter(r["item"] for r in ok).most_common(10)))
