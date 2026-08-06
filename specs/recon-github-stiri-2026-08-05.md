# Recon GitHub — tehnici pentru site-uri de știri pe care izz.ro nu le are

**Rulat:** 2026-08-05 · workflow `wf_65b243ce-847` · 872k tokeni, 259 tool calls, 8m56s
**Stare:** 6/6 sweep-uri de recon REUȘITE (49 findings). Cele 6 gap-check-uri și verificarea
adversarială au murit pe plafon de sesiune — **findings-urile de mai jos NU sunt verificate**
împotriva a ce avem deja și NU au trecut proba adversarială. Recuperate din journal, nu re-rulate.

> ⚠️ **Citește ca ipoteze, nu ca fapte.** Fiecare agent a citit fișierul cu `gh api` și a
> întors fragment verbatim, dar nimeni n-a verificat independent (a) că repo-ul/fișierul chiar
> există, (b) că noi chiar NU avem tehnica. Ambele se pot verifica ieftin, per rând.

## Cuprins
- **Arhitectură de agregator** (dedup, clustering, stare între rulări) — 8 tehnici
- **Generatoare statice / SSG** (build incremental, pipeline, templating) — 8 tehnici
- **SEO tehnic de știri** (structured data, sitemaps, indexare) — 8 tehnici
- **Performanță / Core Web Vitals** (imagini, CSS critic, payload) — 8 tehnici
- **Testare & QA** (determinism, snapshot, CI) — 8 tehnici
- **Procesare de conținut** (NER, extragere articol, imagini) — 9 tehnici

---

# Arhitectură de agregator
*dedup, clustering, stare între rulări*

## 1. Deduplicare prin Jaccard ponderat pe n-grame, cu prag variabil după lungime

- **Repo:** https://github.com/lemon24/reader · ⭐ 548
- **Fișier-dovadă:** `src/reader/plugins/entry_dedupe.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

Plugin-ul găsește articole duplicate în doi pași. Întâi „groupers" ieftini (titlu exact, titlu fără prefix comun, link normalizat, timestamp published) produc grupuri candidate; grupurile mai mari de 4 sunt aruncate ca prea riscante. Abia apoi se compară conținutul: text tokenizat (HTML scos, accente scoase, lowercase), n-grame, și similaritate Jaccard PONDERATĂ (Counter, nu set — o frază repetată scade scorul). Pragul nu e fix: tabelul `_IS_DUPLICATE_THRESHOLDS` alege între n-grame pe caractere (texte scurte, mai iertătoare la typo) și pe cuvinte (texte lungi, mai rapid), cu prag de la 0.6 la 0.9 crescător cu lungimea. Reguli anti-fals-pozitiv explicite: minim 48 de tokeni de conținut, iar dacă un text e de peste 1.5x mai lung decât celălalt, cel lung e TĂIAT la lungimea celui scurt (cazul „un feed dă doar primul paragraf, altul articolul întreg").

**De ce ne-ar folosi:**

Nu avem deduplicare de conținut între surse — avem cluster.py, 126 de linii, iar felia duplicatelor tocmai a fost livrată (#142). Aici e o implementare matură, în Python pur, fără dependențe noi (Counter, re, unicodedata, itertools) — exact profilul nostru de requirements.txt sărac. Trimming-ul la lungimea textului scurt rezolvă direct cazul agregatorului: aceeași știre apare la o sursă ca lead de 3 rânduri și la alta ca articol întreg. Pragurile sunt calibrate empiric și documentate cu link la issue-ul unde au fost testate, deci nu ghicim constante (L2).

<details><summary>Fragment verbatim</summary>

```
    if tokens_are_chars:
        one = ' '.join(one)
        two = ' '.join(two)

    pad = min(len(one), len(two)) < 100

    # using weighted Jaccard (repeat occurrences are counted separately),
    # which decreases similarity if two has a sentence from one twice
    similarity = jaccard_similarity(ngrams(one, n, pad), ngrams(two, n, pad))

    return similarity >= threshold


def jaccard_similarity(one, two):
    """Calculate (weighted) Jaccard similarity."""
    one = Counter(one)
    two = Counter(two)
    try:
        return (one & two).total() / (one | two).total()
    except ZeroDivisionError:  # pragma: no cover
        return 0
```

</details>

## 2. Clusterizare cross-sursă cu union-find și coeficient de suprapunere

- **Repo:** https://github.com/samuelclay/NewsBlur · ⭐ 7573
- **Fișier-dovadă:** `apps/clustering/models.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

1422 de linii care grupează știrile despre același eveniment venite din feed-uri diferite. Tier 1: potrivire pe titlu normalizat exact (lowercase, `-` și `/` devin spații ÎNAINTE de scoaterea punctuației, ca „Anthropic-backed" să dea două tokeni). Tier 2: suprapunere de cuvinte semnificative — stopwords scoase, stemming naiv (taie „s" final doar la cuvinte >3 litere și nu la „ss"), tokenii pur numerici FILTRAȚI pentru că anii provoacă potriviri false. Perechile candidate nu se caută O(n²): se construiește un index inversat cuvânt→articole, iar cuvintele care apar în peste 50 de articole sunt sărite. Fuziunea grupurilor se face cu union-find cu path-halving. Cheia: folosesc coeficient de suprapunere (intersecție / mulțimea mai mică), NU Jaccard, pentru că titlurile de agregator sunt de 2-3x mai lungi și Jaccard le penalizează. În plus, cuvintele din titlul FEED-ului se scad din titlul articolului, ca prefixele constante de sursă să nu domine scorul. Un cluster e valid doar cu 2+ articole din 2+ feed-uri distincte.

**De ce ne-ar folosi:**

cluster.py are 126 de linii; asta e problema noastră centrală (aceeași știre la Digi, Hotnews, G4Media). Trei mecanisme sunt direct aplicabile și nu cred că le avem: (a) scăderea cuvintelor din numele sursei — la noi multe titluri RSS vin cu prefix de secțiune; (b) filtrarea tokenilor numerici, care la știri românești ar lipi „2026" peste subiecte fără legătură; (c) indexul inversat cu plafon de 50, care ține costul liniar la mii de articole pe rulare. Constantele lor sunt documentate cu MOTIVUL calibrării (au ridicat pragul de la 3 la 4 după fals-pozitive pe jargon), deci sunt un punct de plecare, nu o intuiție.

<details><summary>Fragment verbatim</summary>

```
                intersection = len(words_a & words_b)
                if intersection < FUZZY_MIN_INTERSECTION:
                    continue
                # clustering/models.py: Use overlap coefficient (intersection / min set size)
                # instead of Jaccard to handle asymmetric title lengths.
                # Aggregator titles (Techmeme, Google News) include source attribution
                # and extra detail, making them 2-3x longer than the original title.
                # Jaccard penalizes these because the union is dominated by the
                # longer title's unique words. Overlap coefficient normalizes by the
                # smaller set, so a short title sharing most words with a long title
                # scores high.
                smaller = min(len(words_a), len(words_b))
                if smaller == 0:
                    continue
                similarity = intersection / smaller
                if similarity >= FUZZY_SIMILARITY_THRESHOLD:
                    union(h_a, h_b)
```

</details>

## 3. Backoff geometric pe surse care eșuează, cu jitter

- **Repo:** https://github.com/samuelclay/NewsBlur · ⭐ 7573
- **Fișier-dovadă:** `apps/rss_feeds/models.py`
- **Cost de transfer:** reimplementare

**Ce face:**

`set_next_scheduled_update` calculează când se reia o sursă. Intervalul de bază vine din activitatea sursei, apoi se multiplică GEOMETRIC cu numărul de erori consecutive (`interval * error_count`), plafonat la 7 zile. 429 e tratat separat: minim 60 de minute, indiferent de calcul. Peste rezultat se adaugă un factor aleator (un sfert din interval, sau intervalul întreg dacă e sub 5 minute) ca sursele să nu se sincronizeze toate pe același minut. Contorul de erori e suma dintre `errors_since_good` (persistat) și un contor în Redis, iar dacă antetele HTTP dau Cache-Control/Retry-After, tot calculul e ocolit și se folosește valoarea serverului. Când sursa răspunde bine, contorul se resetează la zero.

**De ce ne-ar folosi:**

Avem monitor la 10 minute și feedcheck, dar din inventar nu reiese niciun backoff per-sursă: o sursă moartă e lovită la fel de des ca una vie, la fiecare build. Formula e trivial de portat în state.py (un dict `{url: {errors_since_good, next_check_at}}`) și rezolvă două lucruri deodată — nu mai ardem timp de build pe surse moarte, și nu mai luăm 429 de la sursele care ne limitează. Jitter-ul e detaliul pe care l-am fi ratat: fără el, toate sursele reintră simultan după un build eșuat.

<details><summary>Fragment verbatim</summary>

```
            # Handle 429 rate limiting - enforce minimum 60 minute backoff
            if self.exception_code == 429:
                minutes_until_next_fetch = max(minutes_until_next_fetch, 60)
                if verbose:
                    logging.debug(
                        "   ---> [%-30s] ~FY429 Rate Limited - enforcing minimum 60 min backoff"
                        % (self.log_title[:30])
                    )
            elif error_count:
                original_total = minutes_until_next_fetch
                minutes_until_next_fetch = minutes_until_next_fetch * error_count
                minutes_until_next_fetch = min(minutes_until_next_fetch, 60 * 24 * 7)
```

</details>

## 4. Detectarea challenge-ului Cloudflare din antet, fără a citi body-ul

- **Repo:** https://github.com/miniflux/v2 · ⭐ 9548
- **Fișier-dovadă:** `internal/reader/fetcher/response_handler.go`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

`isCloudflareChallenge()` distinge un interstițiu de bot Cloudflare de un 403 real al originii, folosind DOAR antetele: status 403 + antetul `cf-mitigated: challenge` + Content-Type text/html. Verificarea rulează înaintea citirii body-ului, deci e ieftină, iar rezultatul devine o clasă de eroare separată (`error.http_cloudflare_challenge`), nu „sursă moartă". În același fișier, aceeași logică de clasificare desparte erorile TLS, erorile de rețea, timeout-urile, `io.EOF` (răspuns gol) și fiecare cod HTTP relevant — 401, 403, 429, 404, 410, 500, 502, 503, 504 — în mesaje distincte. Tot aici `ParseRetryDelay()` citește Retry-After atât ca număr de secunde cât și ca dată RFC1123, iar `CacheControlMaxAge()` extrage max-age; ambele alimentează programarea următoarei verificări.

**De ce ne-ar folosi:**

Asta atacă direct una dintre problemele cunoscute: „Cloudflare bot-challenge blochează unelte headless", plus episodul în care feedcheck raporta o sursă VIE ca moartă pentru că citeam refuzul infrastructurii ca defect. Un `if status == 403 and headers.get('cf-mitigated') == 'challenge'` în tools/feed_check.py transformă un fals pozitiv într-o categorie proprie — „blocat, nu mort" — și oprește ștergerea unei surse bune. Trei linii de cod, și e exact tiparul pe care l-am plătit deja o dată.

<details><summary>Fragment verbatim</summary>

```
// isCloudflareChallenge reports whether the response looks like a Cloudflare
// bot/captcha interstitial rather than a genuine error from the origin. It
// relies on response headers only (no body read) to keep the check cheap and
// to run before ReadBody is called.
func (r *ResponseHandler) isCloudflareChallenge() bool {
	if r.httpResponse == nil {
		return false
	}

	return r.httpResponse.StatusCode == http.StatusForbidden &&
		strings.EqualFold(r.httpResponse.Header.Get("cf-mitigated"), "challenge") &&
		strings.HasPrefix(strings.ToLower(r.ContentType()), "text/html")
}
```

</details>

## 5. Normalizare de date stricate: ~200 de formate plus înlocuiri localizate

- **Repo:** https://github.com/miniflux/v2 · ⭐ 9548
- **Fișier-dovadă:** `internal/reader/date/parser.go`
- **Cost de transfer:** reimplementare

**Ce face:**

Parserul încearcă în ordine aproximativ 200 de șabloane de dată observate în feed-uri reale, de la RFC3339 până la aberații gen "Mon, 2th Jan 2006 15:05:05 MST", "02.01.06" sau "Jan. 2, 2006, 3:04 a.m.". Două detalii nu-s evidente. Primul: `dateFormatsLocalTimesOnly` separă RFC822/RFC850/RFC1123 — formatele fără offset numeric — pentru că ele se aplică DOAR ca ore locale, altfel obții o oră greșită cu tăcere. Al doilea: un `strings.NewReplacer` normalizează șirul înainte de parsare, mapând nume de zile și luni localizate (germană „Mi," → „Wed,", „Okt " → „Oct "; franceză „jeu," → „Thu,") și nume IANA de fus („Europe/Brussels" → „CET", „GMT-" → „GMT -").

**De ce ne-ar folosi:**

Avem test `published_is_utc`, deci știm că timezone-ul e o zonă de risc, dar nu văd nimic care să trateze date localizate. Sursele românești publică frecvent zile/luni în română („Lun,", „Mar,", „Mai", „Iun", „Noi") — feedparser eșuează pe ele și cade pe `now()`, ceea ce sparge ordinea cronologică și „stale_new_items". Tabelul lor de formate e un inventar empiric de ce apare efectiv în feed-uri, iar mecanismul replacer-ului e vreo 20 de linii de portat cu numele românești. Observația despre formatele fără offset e cea mai valoroasă: e o clasă de bug care nu aruncă excepție, doar produce ore greșite.

<details><summary>Fragment verbatim</summary>

```
var replacer = strings.NewReplacer(
	// Timezones
	"Europe/Brussels", "CET",
	"America/Los_Angeles", "PDT",
	"GMT+0000 (Coordinated Universal Time)", "GMT",
	"GMT-", "GMT -",

	// Localized dates
	"Mo,", "Mon,",
	"Di,", "Tue,",
	"Mi,", "Wed,",
	"Do,", "Thu,",
	"Fr,", "Fri,",
	"Sa,", "Sat,",
	"So,", "Sun,",
	"Mär ", "Mar ",
	"Mai ", "May ",
	"Okt ", "Oct ",
	"Dez ", "Dec ",
	"lun,", "Mon,",
	"mar,", "Tue,",
	"mer,", "Wed,",
	"jeu,", "Thu,",
	"ven,", "Fri,",
```

</details>

## 6. Decodor XML tolerant: filtrarea caracterelor ilegale înainte de parsare

- **Repo:** https://github.com/miniflux/v2 · ⭐ 9548
- **Fișier-dovadă:** `internal/reader/xml/decoder.go`
- **Cost de transfer:** reimplementare

**Ce face:**

Feed-urile reale conțin octeți care sunt ilegali în XML (caractere de control sub 0x20, surrogate) și care fac orice parser strict să pice pe tot documentul. Miniflux nu repară XML-ul, îl filtrează: `filterValidXMLChars` rescrie buffer-ul IN-PLACE, păstrând doar rune-le permise de spec (0x09, 0x0A, 0x0D, 0x20-0xD7FF, 0xE000-0xFFFD, 0x10000-0x10FFFF) și aruncând tăcut restul, inclusiv `utf8.RuneError`. Cheia arhitecturală e ramificarea: dacă declarația XML spune UTF-8 (sau lipsește), filtrarea se face pe octeți înainte de decodor, pentru că `CharsetReader` NU e chemat pentru utf-8; altfel filtrarea se agață de CharsetReader după conversie. Peste asta, decodorul rulează cu `Strict = false` și `Entity = xml.HTMLEntity`, ca entitățile HTML nedeclarate (`&nbsp;`) să nu omoare parsarea.

**De ce ne-ar folosi:**

fetch.py are 623 de linii și teste pentru content_encoded și silent_empty, deci deja ne-am lovit de feed-uri stricate. Mecanismul ăsta e la un nivel mai jos decât orice avem: un pre-filtru de octeți aplicat înainte de feedparser, care transformă „feed-ul ăsta nu se parsează deloc" în „feed-ul se parsează, minus câțiva octeți invizibili". În Python e o funcție de vreo 10 linii cu un regex peste `str`. Detaliul cu ramificarea pe declarația de encoding e cel pe care l-am fi ratat: dacă filtrezi doar după conversia de charset, feed-urile UTF-8 rămân nefiltrate.

<details><summary>Fragment verbatim</summary>

```
// This function is copied from encoding/xml package,
// and is used to check if all the characters are legal.
func filterValidXMLChar(r rune) rune {
	if r == 0x09 ||
		r == 0x0A ||
		r == 0x0D ||
		r >= 0x20 && r <= 0xD7FF ||
		r >= 0xE000 && r <= 0xFFFD ||
		r >= 0x10000 && r <= 0x10FFFF {
		return r
	}
	return -1
}
```

</details>

## 7. Hash stabil peste rulări, cu câmpuri excluse explicit

- **Repo:** https://github.com/lemon24/reader · ⭐ 548
- **Fișier-dovadă:** `src/reader/_hash_utils.py`
- **Cost de transfer:** copy-paste

**Ce face:**

Un modul de ~100 de linii, fără business logic, care produce un hash stabil pentru obiecte de date (dataclass-uri, datetime, JSON). Trei decizii contează. Prima: câmpurile GOALE (None, '', (), [], {}) sunt ignorate la hashing, ca adăugarea unui câmp nou în model să NU invalideze hash-urile existente. A doua: primul octet al hash-ului e un număr de versiune, ca implementarea să poată fi schimbată fără să rescrii datele vechi. A treia: serializarea forțează explicit toate opțiunile de formatare (`sort_keys=True`, `ensure_ascii=False`, `separators=(',',':')`), ca hash-ul să fie stabil între versiuni de interpretor. Consumatorul îl folosește prin `_hash_exclude_ = frozenset({'feed_url', 'id', 'updated'})` pe fiecare dataclass, iar starea persistată ține un contor `hash_changed` — de câte ori s-a schimbat conținutul de la ultima schimbare a lui `updated` — ca să prindă feed-urile care rescriu articole fără să actualizeze data.

**De ce ne-ar folosi:**

state.py are 107 linii și avem test `state_resync`, ceea ce sugerează că starea „ce a fost deja publicat" ne-a dat deja bătăi de cap. Asta e exact bucata lipsă: un hash de conținut care spune „articolul ăsta s-a SCHIMBAT", nu doar „există". Excluderea câmpurilor goale e detaliul care ne salvează la următorul refactor — altfel, prima dată când adăugăm un câmp în modelul de articol, tot arhivul se marchează ca modificat și rescriem site-ul întreg. Modulul e stdlib pur (hashlib, json, dataclasses), deci intră direct în generator/ fără dependență nouă.

<details><summary>Fragment verbatim</summary>

```
_VERSION = 0
_EXCLUDE = '_hash_exclude_'


def get_hash(thing: object) -> bytes:
    prefix = _VERSION.to_bytes(1, 'big')
    digest = hashlib.md5(_json_dumps(thing).encode('utf-8')).digest()
    return prefix + digest[:-1]


def _json_dumps(thing: object) -> str:
    return json.dumps(
        thing,
        default=_json_default,
        # force formatting-related options to known values
        ensure_ascii=False,
        sort_keys=True,
        indent=None,
        separators=(',', ':'),
    )
```

</details>

## 8. GUID sintetic determinist pentru articole fără identificator

- **Repo:** https://github.com/nkanaev/yarr · ⭐ 3917
- **Fișier-dovadă:** `src/parser/feed.go`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

Pipeline-ul de parsare are un pas de normalizare obligatoriu după parsare (`ParseAndFix`): rezolvă URL-urile relative față de base URL, umple datele lipsă cu `time.Now()`, și — partea interesantă — sintetizează un GUID pentru articolele care nu au unul, ca sha256 peste `title + ";;" + data RFC3339 + ";;" + URL`. Fiind determinist, același articol produce același GUID la fiecare rulare, deci nu reapare ca „nou". Înainte de asta, formatul feed-ului nu se ghicește din Content-Type, ci se adulmecă din primii 2048 de octeți: se taie spațiile, apoi se taie din STÂNGA octeții de gunoi și BOM-urile (`\x00\xEF\xBB\xBF\xFE\xFF`), și abia apoi se decide după primul caracter — `<` duce la tokenizare XML până la primul element rss/RDF/feed, `{` duce la JSON Feed.

**De ce ne-ar folosi:**

Avem teste pentru slug stabil, deci identitatea articolelor e deja o preocupare. GUID-ul sintetic determinist e o plasă de siguranță pentru sursele care nu dau `<guid>` — fără el, orice mică schimbare de URL sau titlu creează un articol nou și îl republicăm. Sniffing-ul cu TrimLeft pe BOM-uri e un fix de 2 linii pentru o clasă de feed-uri care „nu se parsează" fără motiv aparent: gunoi înainte de declarația XML. Ambele sunt sub 10 linii în Python și se pun în fetch.py fără să atingem nimic altceva.

<details><summary>Fragment verbatim</summary>

```
func (feed *Feed) SetMissingGUIDs() {
	for i, item := range feed.Items {
		if item.GUID == "" {
			id := strings.Join([]string{item.Title, item.Date.Format(time.RFC3339), item.URL}, ";;")
			feed.Items[i].GUID = fmt.Sprintf("%x", sha256.Sum256([]byte(id)))
		}
	}
}
```

</details>

---

# Generatoare statice / SSG
*build incremental, pipeline, templating*

## 9. Build incremental cu graf artefact→surse în SQLite

- **Repo:** https://github.com/lektor/lektor · ⭐ 3947
- **Fișier-dovadă:** `lektor/builder.py`
- **Cost de transfer:** reimplementare

**Ce face:**

Lektor ține o bază SQLite locală cu tabelul `artifacts (artifact, source, source_mtime, source_size, source_checksum, is_dir, is_virtual, is_primary_source)` plus `artifact_config_hashes` și `dirty_sources`. Înainte să regenereze un fișier de ieșire, întreabă baza: s-a schimbat hash-ul de configurație? e vreo sursă marcată explicit murdară? s-a schimbat mtime/size/checksum al vreunei surse de care depinde artefactul? Dacă nu, artefactul e sărit complet. Cheia primară e (artifact, source), deci un artefact poate depinde de N surse, iar indexul pe `source` permite drumul invers: ce trebuie rebuild-uit când s-a schimbat fișierul X.

**De ce ne-ar folosi:**

izz regenerează TOT la fiecare build. Cu 8545 de linii de SSG și un site de știri care primește câteva articole noi pe ciclu, asta e muncă aruncată la fiecare rulare de CI. Modelul e direct aplicabil: fiecare pagină HTML din output/ e un artefact, sursele sunt itemul de feed + template-urile + config-ul. Bonus: aceeași bază răspunde la „ce pagini trebuie reconstruite dacă am editat templates/_card.html", ceea ce acum nu se poate ști.

<details><summary>Fragment verbatim</summary>

```
    def check_artifact_is_current(self, artifact_name, sources, config_hash):
        con = self.connect_to_database()
        cur = con.cursor()
        try:
            # The artifact config changed
            if config_hash != self._get_artifact_config_hash(cur, artifact_name):
                return False

            # If one of our source files is explicitly marked as dirty in the
            # build state, we are not current.
            if self._any_sources_are_dirty(cur, sources):
                return False

            # If we do have an already existing artifact, we need to check if
            # any of the source files we depend on changed.
            for _, info in self._iter_artifact_dependency_infos(
                cur, artifact_name, sources
            ):
                # if we get a missing source info it means that we never
                # saw this before.  This means we need to build it.
                if info is None:
                    return False

                if info.is_changed(self):
                    return False
```

</details>

## 10. Jinja2 care își înregistrează singur dependențele de template

- **Repo:** https://github.com/lektor/lektor · ⭐ 3947
- **Fișier-dovadă:** `lektor/environment/__init__.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

O subclasă de ~25 de linii peste `jinja2.Environment` care suprascrie `_load_template`. De fiecare dată când Jinja încarcă un template — inclusiv prin `{% extends %}`, `{% include %}`, `{% import %}` — filename-ul real e raportat în contextul de build prin `ctx.record_dependency(filename)`. Tratează și cele două cazuri de eroare: la `TemplateSyntaxError` înregistrează fișierul stricat, iar la `TemplateNotFound` înregistrează TOATE căile candidate din searchpath, ca un watcher să prindă template-ul când va apărea. Colectarea se face cu context manager `gather_dependencies(func)` din `lektor/context.py`.

**De ce ne-ar folosi:**

Asta e piesa care face fezabil build-ul incremental fără să întreținem manual o listă „ce template afectează ce pagină". Cu moștenirea din base.html + _card.html, orice hardcodare de dependențe ar fi greșită în două săptămâni. E cel mai ieftin transfer din tot lotul: izz folosește deja Jinja2, deci subclasa se lipește direct peste environment-ul existent din render.py.

<details><summary>Fragment verbatim</summary>

```
class CustomJinjaEnvironment(jinja2.Environment):
    def _load_template(self, name, globals):
        ctx = get_ctx()

        try:
            rv = jinja2.Environment._load_template(self, name, globals)
            if ctx is not None:
                filename = rv.filename
                ctx.record_dependency(filename)
            return rv
        except jinja2.TemplateSyntaxError as e:
            if ctx is not None:
                ctx.record_dependency(e.filename)
            raise
        except jinja2.TemplateNotFound as e:
            if ctx is not None:
                # If we can't find the template we want to record at what
                # possible locations the template could exist.  This will help
                # out watcher to pick up templates that will appear in the
                # future.  This assumes the loader is a file system loader.
                for template_name in e.templates:
                    pieces = split_template_path(template_name)
                    for base in self.loader.searchpath:
                        ctx.record_dependency(os.path.join(base, *pieces))
            raise
```

</details>

## 11. Cache de build invalidat prin amprentă de fișier

- **Repo:** https://github.com/getpelican/pelican · ⭐ 13330
- **Fișier-dovadă:** `pelican/cache.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

139 de linii, două clase. `FileDataCacher` ține un dict picklat pe disc (opțional gzip), tolerant la corupție: dacă unpickle eșuează pornește cu cache gol și doar avertizează. `FileStampDataCacher` adaugă o „amprentă" per fișier, iar metoda de amprentare e configurabilă: `mtime` (ieftin) sau orice funcție din `hashlib` (corect, dar citește fișierul). Trucul e în `get_cached_data`: stochează tuplul (stamp, data) și returnează default-ul dacă amprenta curentă diferă de cea salvată — invalidarea e implicită, nu există pas separat de „curăță cache-ul".

**De ce ne-ar folosi:**

E varianta ieftină, fără SQLite, a build-ului incremental: aplicabilă imediat pe partea scumpă și idempotentă din pipeline — parsarea feed-urilor, clusterizarea, geo.py, photojudge, deciziile de moderare. Nu schimbă arhitectura de render, se pune ca un strat între fetch și process. Opțiunea mtime-vs-hash contează pentru izz: în CI checkout-ul rescrie mtime-urile, deci acolo doar hash-ul e o amprentă validă — exact motivul pentru care Pelican a făcut-o configurabilă.

<details><summary>Fragment verbatim</summary>

```
        method = self.settings["CHECK_MODIFIED_METHOD"]
        if method == "mtime":
            self._filestamp_func = os.path.getmtime
        else:
            try:
                hash_func = getattr(hashlib, method)

                def filestamp_func(filename):
                    """return hash of file contents"""
                    with open(filename, "rb") as fhandle:
                        return hash_func(fhandle.read()).digest()

                self._filestamp_func = filestamp_func

#   ... (aceeasi clasa, mai jos)

    def get_cached_data(self, filename, default=None):
        """Get the cached data for the given filename
        if the file has not been modified.

        If no record exists or file has been modified, return default.
        Modification is checked by comparing the cached
        and current file stamp.
        """

        stamp, data = super().get_cached_data(filename, (None, default))
        if stamp != self._get_file_stamp(filename):
            return default
        return data
```

</details>

## 12. Arhive pe an/lună/zi generate dintr-un singur groupby

- **Repo:** https://github.com/getpelican/pelican · ⭐ 13330
- **Fișier-dovadă:** `pelican/generators.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

`_build_period_archives` construiește toate cele trei niveluri de arhivă dintr-o listă deja sortată, folosind `itertools.groupby` cu chei din `operator.attrgetter`: `date.year`, apoi `(date.year, date.month)`, apoi `(date.year, date.month, date.day)`. Fiecare nivel are propriile șabloane de URL și de cale-de-scriere (`YEAR_ARCHIVE_URL` / `SAVE_AS`), formatate cu `.format(date=d)`, iar un nivel cu `save_as` gol e sărit complet — deci activarea/dezactivarea arhivei zilnice e o singură setare, nu cod. Fiecare grup primește `period` (cu numele lunii localizat prin `calendar.month_name`) și `period_num` (numeric), ca template-ul să aibă și afișare, și sortare.

**De ce ne-ar folosi:**

izz are template `calendar` dar nu are structura asta de arhivă ierarhică pe date. Pentru un agregator de știri, /2026/08/05/ e exact felia care aduce trafic long-tail și pe care Google o indexează ca hub temporal. Mecanismul e ~60 de linii de Python pur, fără dependențe noi, și se alimentează din lista de articole pe care select.py o produce oricum.

<details><summary>Fragment verbatim</summary>

```
        granularity_key_func = {
            "year": attrgetter("date.year"),
            "month": attrgetter("date.year", "date.month"),
            "day": attrgetter("date.year", "date.month", "date.day"),
        }

        for granularity in "year", "month", "day":
            save_as_fmt = period_archives_settings[granularity]["save_as"]
            url_fmt = period_archives_settings[granularity]["url"]
            key_func = granularity_key_func[granularity]

            if not save_as_fmt:
                # the archives for this period granularity are not needed
                continue

            for period, group in groupby(sorted_articles, key=key_func):
                archive = {}

                dates = list(group)
                archive["dates"] = dates
                archive["articles"] = [a for a in articles if a in dates]

                d = dates[0].date
                archive["save_as"] = save_as_fmt.format(date=d)
                archive["url"] = url_fmt.format(date=d)
```

</details>

## 13. Corectitudinea unui item de feed: id stabil, summary ≠ content

- **Repo:** https://github.com/getpelican/pelican · ⭐ 13330
- **Fișier-dovadă:** `pelican/writers.py`
- **Cost de transfer:** reimplementare

**Ce face:**

`_add_item_to_the_feed` conține deciziile subtile pe care le ratează orice feed scris de mână. (1) Titlul e trecut prin `Markup(item.title).striptags()` — fără HTML în titlu. (2) RSS are un singur `description`, Atom are `content` + `summary`; dacă summary-ul ar ieși identic cu content-ul, îl șterge, ca cititoarele să nu afișeze textul de două ori. (3) `unique_id=get_tag_uri(link, item.date)` — id-ul e un tag URI derivat din URL + dată, nu URL-ul brut, deci rămâne stabil chiar dacă domeniul se schimbă. (4) `pubdate` și `updateddate` sunt trecute explicit prin `set_date_tzinfo`, deci nu ies date naive. Categoriile combină categoria și tagurile.

**De ce ne-ar folosi:**

izz nu expune NICIUN feed, deși e agregator de știri — pierdem sindicalizarea, cititoarele RSS și semnalul de prospețime. Când îl scriem, astea sunt exact capcanele: id instabil (duplicate în cititoare la fiecare rebuild) și summary identic cu content (afișare dublă). izz are deja `published_is_utc` testat, deci partea de fus e rezolvată; restul e template Jinja2, fără dependență nouă — Pelican folosește feedgenerator, dar tehnica se transferă fără el.

<details><summary>Fragment verbatim</summary>

```
        else:
            # Atom feeds have two different tags for full content (called
            # 'content' by feedgenerator) and summary (called 'description' by
            # feedgenerator).
            #
            # It does not make sense to have the summary be the
            # exact same thing as the full content. If we detect that
            # they are we just remove the summary.
            content = item.get_content(self.site_url)
            description = item.summary
            if description == content:
                description = None

        categories = []
        if hasattr(item, "category"):
            categories.append(item.category)
        if hasattr(item, "tags"):
            categories.extend(item.tags)

        feed.add_item(
            title=title,
            link=link,
            unique_id=get_tag_uri(link, item.date),
            description=description,
            content=content,
```

</details>

## 14. JSON Feed generat din template, ~25 de linii

- **Repo:** https://github.com/google/eleventy-high-performance-blog · ⭐ 4039
- **Fișier-dovadă:** `feed/json.njk`
- **Cost de transfer:** copy-paste

**Ce face:**

Un JSON Feed 1.0 complet, scris ca template Nunjucks (portul JS al lui Jinja2, sintaxă aproape identică: `{%- for %}`, `loop.last`, `{% set %}`). Punctele care contează: URL-ul absolut e calculat o singură dată într-un `{% set %}` și refolosit ca `id` ȘI ca `url`; conținutul HTML e scăpat corect prin filtrul `dump` (echivalentul lui `tojson` din Jinja2), nu prin escape manual; virgula dintre elemente e pusă cu `{%- if not loop.last -%}` ca să nu iasă JSON invalid la ultimul item. Repo-ul are în paralel și `feed/feed.njk` (Atom) și `feed/htaccess.njk`.

**De ce ne-ar folosi:**

Transferul cel mai ieftin de pe listă: Nunjucks → Jinja2 e practic copy-paste, `dump` devine `tojson`. Rezolvă golul „nu expunem niciun feed" fără să atingem deloc render.py — se adaugă un template nou și o linie în main.py. JSON Feed e mai ușor de consumat de agregatoare moderne decât Atom, iar pentru izz e și un canal de distribuție către alte site-uri.

<details><summary>Fragment verbatim</summary>

```
{
  "version": "https://jsonfeed.org/version/1",
  "title": "{{ metadata.title }}",
  "home_page_url": "{{ metadata.url }}",
  "feed_url": "{{ metadata.jsonfeed.url }}",
  "description": "{{ metadata.description }}",
  "author": {
    "name": "{{ metadata.author.name }}",
    "url": "{{ metadata.author.url }}"
  },
  "items": [
    {%- for post in collections.posts | reverse %}
    {%- set absolutePostUrl %}{{ post.url | url | absoluteUrl(metadata.url) }}{% endset -%}
    {
      "id": "{{ absolutePostUrl }}",
      "url": "{{ absolutePostUrl }}",
      "title": "{{ post.data.title }}",
      "content_html": {% if post.templateContent %}{{ post.templateContent | dump | safe }}{% else %}""{% endif %},
      "date_published": "{{ post.date | rssDate }}"
    }
    {%- if not loop.last -%}
    ,
    {%- endif -%}
    {%- endfor %}
  ]
}
```

</details>

## 15. Post-procesare a HTML-ului: dimensiuni, lazy, picture, LQIP

- **Repo:** https://github.com/google/eleventy-high-performance-blog · ⭐ 4039
- **Fișier-dovadă:** `_11ty/img-dim.js`
- **Cost de transfer:** reimplementare

**Ce face:**

În loc să ceară autorului să scrie markup corect, repo-ul rulează o transformare peste HTML-ul deja randat: parsează DOM-ul, ia fiecare `<img>` și îl completează automat. Citește dimensiunile reale de pe disc și setează `width`/`height` (elimină CLS), pune `decoding="async"` și `loading="lazy"`, apoi înfășoară imaginea într-un `<picture>` cu trei `<source>` în ordinea avif → webp → jpeg/png, fiecare cu propriul srcset. Placeholder-ul de încărcare (LQIP) e pus ca `background-image` inline pe `<img>`, generat de `_11ty/blurry-placeholder.js`: un bitmap de ~60 de pixeli, împachetat într-un SVG cu `feGaussianBlur` ca blur-ul să nu se rasterizeze la fiecare layout, serializat ca data-URI și cachat pe disc. PNG-urile rămân PNG ca fallback, ca să nu se piardă transparența.

**De ce ne-ar folosi:**

izz are covers.py (426 linii) și pillow, dar tehnica de aici e ortogonală: se aplică pe HTML-ul de ieșire, nu în generator, deci nu atinge render.py-ul de 1090 de linii. Pentru un site de știri cu multe imagini de lead, `<picture>` cu AVIF plus width/height plus LQIP e diferența măsurabilă pe Core Web Vitals — și e exact ce Google indexează pentru Discover. Nota de cost: JS + jsdom + sharp; în Python echivalentul ar fi un pas separat cu lxml + pillow, deci reimplementare, nu import.

<details><summary>Fragment verbatim</summary>

```
  const fallbackType = inputType == "png" ? "png" : "jpeg";
  if (img.tagName == "IMG") {
    img.setAttribute("decoding", "async");
    img.setAttribute("loading", "lazy");
    img.setAttribute(
      "style",
      `background-size:cover;` +
        `background-image:url("${await blurryPlaceholder(src)}")`
    );
    const doc = img.ownerDocument;
    const picture = doc.createElement("picture");
    const avif = doc.createElement("source");
    const webp = doc.createElement("source");
    const jpeg = doc.createElement("source");
    await setSrcset(avif, src, "avif");
    avif.setAttribute("type", "image/avif");
    await setSrcset(webp, src, "webp");
    webp.setAttribute("type", "image/webp");
    const fallback = await setSrcset(jpeg, src, fallbackType);
    jpeg.setAttribute("type", `image/${fallbackType}`);
    picture.appendChild(avif);
    picture.appendChild(webp);
    picture.appendChild(jpeg);
    img.parentElement.replaceChild(picture, img);
    picture.appendChild(img);
```

</details>

## 16. Scara de lățimi cu cache pe disc, invalidat prin nume

- **Repo:** https://github.com/google/eleventy-high-performance-blog · ⭐ 4039
- **Fișier-dovadă:** `_11ty/srcset.js`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

58 de linii care generează întreg srcset-ul. Scara de lățimi e o constantă simplă `[1920, 1280, 640, 320]`, calitatea e per format (AVIF la 40, restul la 60 — AVIF suportă compresie mai agresivă la aceeași percepție). Cache-ul e cel mai curat detaliu: nu există bază de date și nici manifest, cheia e chiar numele fișierului de ieșire — `sizedName` transformă `foo.jpg` în `foo-640w.webp`, iar `resize` verifică `if (await exists(...)) return out;` și sare peste redimensionare. Se apelează și `.rotate()` fără argumente, ca orientarea EXIF să fie aplicată efectiv (altfel pozele de pe telefon ies întoarse).

**De ce ne-ar folosi:**

Cache-ul prin nume-de-fișier e exact mecanismul de care are nevoie covers.py ca să nu reproceseze aceleași imagini la fiecare build — costă o singură verificare `os.path.exists`, zero infrastructură, și se combină natural cu build-ul incremental. Detaliul cu `.rotate()` pe EXIF e o capcană concretă: pillow nu aplică orientarea implicit, deci dacă izz preia poze din surse externe fără `ImageOps.exif_transpose`, o parte ies rotite pe site.

<details><summary>Fragment verbatim</summary>

```
const widths = [1920, 1280, 640, 320];

const quality = {
  avif: 40,
  default: 60,
};

module.exports = async function srcset(filename, format) {
  const names = await Promise.all(
    widths.map((w) => resize(filename, w, format))
  );
  return {
    srcset: names.map((n, i) => `${n} ${widths[i]}w`).join(", "),
    fallback: names[0],
  };
};

async function resize(filename, width, format) {
  const out = sizedName(filename, width, format);
  if (await exists("_site" + out)) {
    return out;
  }
  await sharp("_site" + filename)
    .rotate() // Manifest rotation from metadata
    .resize(width)
```

</details>

---

# SEO tehnic de știri
*structured data, sitemaps, indexare*

## 17. Un singur @graph JSON-LD cu validator de referințe orfane

- **Repo:** https://github.com/jdevalk/seo-graph · ⭐ 44
- **Fișier-dovadă:** `packages/seo-graph-core/src/assemble.ts`
- **Cost de transfer:** reimplementare

**Ce face:**

În loc de mai multe blocuri <script type="application/ld+json"> independente, toate entitățile sunt puse într-un singur `{"@context":"https://schema.org","@graph":[...]}`, deduplicate după @id (prima apariție câștigă). Entitățile se referă între ele prin `{"@id": "..."}` fără @type. `collectReferences` umblă recursiv prin graf, adună toate referințele de forma asta și avertizează pentru fiecare @id care nu se rezolvă la nicio entitate din graf. Distincția e mecanică: obiect cu @id ȘI fără @type = referință; cu @type = entitate.

**De ce ne-ar folosi:**

Noi emitem NewsArticle, BreadcrumbList, ItemList, FAQPage, Organization, ImageObject — foarte probabil ca blocuri separate, fără @id și fără legături între ele. Google tratează un graf legat (Article -> isPartOf WebSite, -> publisher Organization, -> image ImageObject) ca o singură descriere coerentă a entității, nu ca șase fragmente. Validatorul de referințe orfane e un test pytest natural în tests/ — dacă un template scoate `image: {@id: ...#primaryimage}` dar covers.py n-a găsit poză, testul prinde legătura ruptă la build, nu în Search Console peste 3 săptămâni. Zero dependențe noi: e recursie peste dict-uri Python.

<details><summary>Fragment verbatim</summary>

```
// An object with @id but no @type is a reference, not an entity.
    if (typeof obj['@id'] === 'string' && obj['@type'] === undefined) {
        refs.add(obj['@id']);
        return;
    }

[...]

        for (const [ref, sourceType] of refs) {
            if (!entityIds.has(ref)) {
                console.warn(
                    `[seo-graph] Dangling reference in ${sourceType}: { "@id": "${ref}" } does not match any entity in the graph.`,
                );
            }
        }

    return {
        '@context': 'https://schema.org',
        '@graph': graph,
    };
```

</details>

## 18. Convenție de @id stabile: singleton de site vs. per-pagină

- **Repo:** https://github.com/jdevalk/seo-graph · ⭐ 44
- **Fișier-dovadă:** `packages/seo-graph-core/src/ids.ts`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

O fabrică fără stare care generează URI-uri de @id după două reguli: entitățile unice pe tot site-ul stau la `${siteUrl}/#/schema.org/<Type>` (WebSite, Person, Organization/<slug>, Country/<cod>), iar entitățile legate de o pagină stau la `${pageUrl}#<sufix>` (`#article`, `#breadcrumb`, `#primaryimage`, `#video`). @id-ul unui WebPage este chiar URL-ul canonic, fără fragment. Include normalizare de slash-uri ca ID-urile să nu varieze între rulări.

**De ce ne-ar folosi:**

Fără @id-uri stabile nu poți construi graful din finding-ul anterior — și mai ales nu poți lega două pagini de aceeași entitate. Pentru un agregator cu pagini de subiect, categorie și localitate, un `#/schema.org/Organization/<slug-sursa>` per sursă de știri și un `#/schema.org/Place/<slug-localitate>` per localitate (avem localities.py și geo.py, deci slug-urile există deja) înseamnă că 40 de articole despre aceeași primărie trimit toate spre același nod. Asta e exact ce înțelege Google prin "entitate". Costul e mic: o funcție în generator/util.py plus câteva variabile în templates.

<details><summary>Fragment verbatim</summary>

```
return {
        person: `${person}#/schema.org/Person`,
        personImage: `${site}/#personlogo`,
        website: `${site}/#/schema.org/WebSite`,
        navigation: `${site}/#site-navigation`,
        organization: (slug: string) => `${site}/#/schema.org/Organization/${slug}`,
        country: (code: string) => `${site}/#/schema.org/Country/${code.toLowerCase()}`,
        webPage: (url: string) => url,
        breadcrumb: (url: string) => `${url}#breadcrumb`,
        article: (url: string) => `${url}#article`,
        videoObject: (url: string) => `${url}#video`,
        primaryImage: (url: string) => `${url}#primaryimage`,
    };
```

</details>

## 19. WebSite + SearchAction (sitelinks searchbox) pe homepage

- **Repo:** https://github.com/Yoast/wordpress-seo · ⭐ 1980
- **Fișier-dovadă:** `src/generators/schema/website.php`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

Emite un nod WebSite cu @id, url, name, description, opțional alternateName și publisher (referință spre Organization). Peste el adaugă un `potentialAction` de tip SearchAction, cu target EntryPoint care conține un urlTemplate cu placeholder-ul literal `{search_term_string}` și un `query-input` de tip PropertyValueSpecification cu `valueRequired: true` și `valueName: "search_term_string"`. Codul e generat doar pe homepage și e dezactivabil prin filtru.

**De ce ne-ar folosi:**

Este un tip schema.org pe care nu îl avem deloc (inventarul listează Organization, dar nu WebSite). WebSite e nodul-rădăcină la care se agață tot restul prin `isPartOf` — fără el graful n-are ancoră. În plus avem deja templates/search, deci SearchAction e implementabil imediat: `https://izz.ro/cautare/?q={search_term_string}`. Atenție la o capcană reală: Google cere ca URL-ul de căutare să întoarcă rezultate la o navigare normală. Dacă search-ul nostru e 100% client-side pe JS, searchbox-ul poate fi ignorat — asta trebuie verificat înainte, nu presupus. Nodul WebSite merită oricum, independent de searchbox.

<details><summary>Fragment verbatim</summary>

```
$data['potentialAction'][] = [
			'@type'       => 'SearchAction',
			'target'      => [
				'@type'       => 'EntryPoint',
				'urlTemplate' => $search_url,
			],
			'query-input' => [
				'@type'          => 'PropertyValueSpecification',
				'valueRequired'  => true,
				'valueName'      => 'search_term_string',
			],
		];
```

</details>

## 20. Nodul WebPage care leagă articolul de site și de breadcrumb

- **Repo:** https://github.com/Yoast/wordpress-seo · ⭐ 1980
- **Fișier-dovadă:** `src/generators/schema/webpage.php`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

Construiește un nod WebPage (sau CollectionPage / ItemPage / ProfilePage, tipul e configurabil) cu @id = URL-ul canonic, `isPartOf` -> WebSite, `breadcrumb` -> BreadcrumbList prin referință @id, `primaryImageOfPage` + `image` -> ImageObject prin referință, `thumbnailUrl` ca URL brut, plus datePublished / dateModified (dateModified doar dacă e strict mai mare decât datePublished) și un `potentialAction` de tip ReadAction. Pe CollectionPage sare peste ReadAction.

**De ce ne-ar folosi:**

Avem NewsArticle, BreadcrumbList și ImageObject, dar probabil ca obiecte paralele. WebPage e liantul: articolul devine `mainEntityOfPage` al paginii, breadcrumb-ul devine proprietate a paginii, iar poza devine `primaryImageOfPage` în loc de un ImageObject care plutește. Două detalii de furat direct: (a) `dateModified` se emite doar dacă e efectiv mai mare decât `datePublished` — noi avem test published_is_utc, deci datele există; a pune dateModified = datePublished pe fiecare articol e zgomot; (b) tipurile de pagină din PAGE_TYPES (CollectionPage pentru /categorie/ și /subiect/, SearchResultsPage pentru căutare) sunt un câștig gratuit pe paginile de listă, unde acum probabil emitem doar ItemList.

<details><summary>Fragment verbatim</summary>

```
$data = [
			'@type'      => $this->context->schema_page_type,
			'@id'        => $this->context->main_schema_id,
			'url'        => $this->context->canonical,
			'name'       => $this->helpers->schema->html->smart_strip_tags( $this->context->title ),
			'isPartOf'   => [
				'@id' => $this->context->site_url . Schema_IDs::WEBSITE_HASH,
			],
		];
[...]
		if ( $this->context->has_image ) {
			$data['primaryImageOfPage'] = [ '@id' => $this->context->canonical . Schema_IDs::PRIMARY_IMAGE_HASH ];
			$data['image']              = [ '@id' => $this->context->canonical . Schema_IDs::PRIMARY_IMAGE_HASH ];
			$data['thumbnailUrl']       = $this->context->main_image_url;
		}
[...]
		$data['potentialAction'][] = [
			'@type'  => 'ReadAction',
			'target' => $targets,
		];
```

</details>

## 21. ClaimReview — marcaj de fact-checking pentru știri

- **Repo:** https://github.com/garmeeh/next-seo · ⭐ 8503
- **Fișier-dovadă:** `src/components/ClaimReviewJsonLd.tsx`
- **Cost de transfer:** reimplementare

**Ce face:**

Emite un obiect ClaimReview cu `claimReviewed` (afirmația verificată, ca text), `reviewRating` (un Rating cu ratingValue, bestRating, worstRating și alternateName — eticheta textuală gen "Fals"), `url`, `author` (organizația care face verificarea) și `itemReviewed` (un Claim cu autorul afirmației, data și locul unde a apărut). Câmpurile opționale sunt adăugate condiționat prin spread, deci nu apar chei goale în JSON.

**De ce ne-ar folosi:**

E singurul tip schema.org din listă care are un slot dedicat în Google News (Fact Check) și nu îl avem. Structura e minusculă — trei câmpuri obligatorii — dar cere date editoriale pe care noi nu le producem azi. Concret: dacă o sursă agregată e un fact-check (există astfel de surse românești), câmpurile pot fi mapate din feed. Punctul slab, spus direct: Google acceptă ClaimReview doar de la publisheri înregistrați ca fact-checkeri, deci marcajul singur nu aduce rich result — dar tipul Claim/ClaimReview rămâne util ca semnal de calitate și e ieftin. Nu îl recomand ca prima felie; îl recomand ca opțiune cunoscută, nu descoperită la nevoie.

<details><summary>Fragment verbatim</summary>

```
const data = {
    "@context": "https://schema.org",
    "@type": "ClaimReview",
    claimReviewed,
    reviewRating: processClaimReviewRating(reviewRating),
    url,
    ...(author && { author: processAuthor(author) }),
    ...(itemReviewed && { itemReviewed: processClaim(itemReviewed) }),
  };
```

</details>

## 22. IndexNow incremental prin manifest de hash-uri de conținut

- **Repo:** https://github.com/jdevalk/seo-graph · ⭐ 44
- **Fișier-dovadă:** `packages/astro-seo-graph/src/indexnow-manifest.ts`
- **Cost de transfer:** reimplementare

**Ce face:**

Rezolvă exact problema "trimit tot site-ul la fiecare build", pe care autorul o numește în comentariu ca fiind descurajată de specificația IndexNow și care declanșează rate-limit pe host. Construiește un manifest `{url: hash}` cu SHA-256 trunchiat la 16 caractere hex, îl compară cu manifestul publicat la build-ul anterior și scoate trei mulțimi: added, updated, deleted. Trimite reuniunea lor (inclusiv URL-urile șterse — motoarele recrawlează și le scot). Manifestul se serializează cu chei sortate ca să facă diff curat între deploy-uri, și are `version` + `algorithm` în payload. Funcția de hash e injectabilă, ca să normalizezi markup volatil (nonce-uri, timestamp-uri de build) înainte de hashing, altfel conținutul neschimbat apare ca "updated".

**De ce ne-ar folosi:**

Avem tools/indexnow_submit.py; asta e stratul care lipsește peste el. La un agregator care rebuildează des, marea majoritate a paginilor sunt identice între build-uri — trimiterea lor repetată e exact tiparul pe care Bing îl penalizează prin rate-limit, iar URL-urile chiar noi se pierd în zgomot. Detaliul de hash injectabil e important pentru noi în mod specific: dacă template-ul pune un timestamp de generare sau un "actualizat acum X minute", fiecare pagină se schimbă la fiecare build și diff-ul devine inutil — deci normalizarea nu e opțională, e condiția ca mecanismul să funcționeze. Toate funcțiile sunt pure și fără IO, deci se portează în ~60 de linii Python cu hashlib, testabile în pytest fără rețea.

<details><summary>Fragment verbatim</summary>

```
export function hashContent(content: string): string {
    return createHash('sha256').update(content, 'utf8').digest('hex').slice(0, 16);
}

[...]

export function diffManifests(prev: UrlManifest, curr: UrlManifest): ManifestDiff {
    const added: string[] = [];
    const updated: string[] = [];
    const deleted: string[] = [];

    for (const url of Object.keys(curr)) {
        if (!(url in prev)) added.push(url);
        else if (prev[url] !== curr[url]) updated.push(url);
    }
    for (const url of Object.keys(prev)) {
        if (!(url in curr)) deleted.push(url);
    }

    added.sort();
    updated.sort();
    deleted.sort();
    return { added, updated, deleted };
}
```

</details>

## 23. llms.txt generat la build, plus alternate .md pe articol

- **Repo:** https://github.com/jdevalk/seo-graph · ⭐ 44
- **Fișier-dovadă:** `packages/astro-seo-graph/src/llms-txt.ts`
- **Cost de transfer:** reimplementare

**Ce face:**

Randează un fișier llms.txt după specificația llmstxt.org: `# Titlu`, un blockquote de sumar, paragrafe de detaliu, apoi secțiuni `## Nume` cu linii `- [titlu](url): descriere`. Secțiunile goale se omit, parantezele drepte din titluri se escapează, se termină cu newline. Funcția e pură — primește o structură și scoate un string. În același pachet, markdown-alternate.ts randează fiecare articol ca markdown cu frontmatter YAML (title, canonical, pubDate, updatedDate, author, description, tags, categories), servit la un URL `.md`, descoperibil printr-un `<link rel="alternate" type="text/markdown">` și marcat cu header `Link: <...>; rel="canonical"` ca să nu fie indexat separat.

**De ce ne-ar folosi:**

Nu avem nici llms.txt, nici alternate markdown. Amândouă sunt aproape gratis într-un SSG: avem deja titlul, descrierea și URL-ul fiecărei pagini în context la render, deci llms.txt e o iterație peste aceleași date din care iese sitemap-ul editorial. Secțiunile se mapează direct pe categoriile noastre. Partea care mi se pare mai valoroasă decât llms.txt în sine e detaliul de canonicalizare din markdown-alternate: alternativa .md primește header `Link: rel="canonical"` spre HTML — fără el creezi conținut duplicat cu propriile mâini. Rezerva mea, spusă pe față: nu am dovadă că vreun crawler major consumă efectiv llms.txt astăzi; costul e mic, dar beneficiul e speculativ, nu măsurat.

<details><summary>Fragment verbatim</summary>

```
export function renderLlmsTxt(input: LlmsTxtInput): string {
    const parts: string[] = [`# ${input.title.trim()}`];

    if (input.summary?.trim()) {
        parts.push(`> ${input.summary.trim()}`);
    }

    if (input.details?.trim()) {
        parts.push(input.details.trim());
    }

    for (const section of input.sections) {
        if (section.links.length === 0) continue;
        parts.push(`## ${section.name.trim()}`);
        const lines = section.links.map((link) => {
            const label = escapeLinkTitle(link.title.trim() || link.url);
            const base = `- [${label}](${link.url})`;
            const desc = link.description?.trim();
            return desc ? `${base}: ${desc}` : base;
        });
        parts.push(lines.join('\n'));
    }

    return parts.join('\n\n') + '\n';
}
```

</details>

## 24. Articole conexe prin scor de tag-uri comune, fără dependențe

- **Repo:** https://github.com/pelican-plugins/related-posts · ⭐ 9
- **Fișier-dovadă:** `pelican/plugins/related_posts/related_posts.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

Linking intern automat într-un SSG Python, cu stdlib curat. Scorul de înrudire e literalmente `Counter` peste articolele care împart tag-uri: se lipesc listele de articole ale fiecărui tag al articolului curent, se numără aparițiile, se scoate articolul însuși din numărătoare, se iau primele N cu `most_common`. Are două comutatoare utile: `RELATED_POSTS_SKIP_SAME_CATEGORY`, care filtrează articolele din aceeași categorie ca să nu recomande mereu din același sertar, și un override manual — dacă articolul are `related_posts` scris explicit ca listă de slug-uri, ăla câștigă în fața scorului automat.

**De ce ne-ar folosi:**

Linking-ul intern automat e singura pârghie de SEO din listă care nu ține de markup, ci de structura sitului: articolele orfane nu primesc PageRank intern și se indexează prost. Avem deja cluster.py și pagini de subiect, deci semnalul de înrudire există — probabil mai bun decât tag overlap. Ce merită furat nu e formula, ci cele două comutatoare: filtrul de categorie (altfel toate recomandările dintr-un articol Politică sunt tot Politică, ceea ce nu redistribuie nimic) și override-ul manual, care îți lasă o portiță editorială fără să atingi codul. Notă onestă: e cel mai mic repo din listă (9 stele) și mecanismul e trivial — îl raportez pentru cele două decizii de design, nu pentru cod.

<details><summary>Fragment verbatim</summary>

```
# score = number of common tags
            related = chain(*(generator.tags[tag] for tag in article.tags))
            if skipcategory:
                related = (
                    other for other in related if other.category != article.category
                )
            scores = Counter(related)

            # remove itself
            scores.pop(article, None)

            article.related_posts = [
                other for other, count in scores.most_common(numentries)
            ]
```

</details>

---

# Performanță / Core Web Vitals
*imagini, CSS critic, payload*

## 25. Prag care sparge build-ul prin aserțiuni Lighthouse CI

- **Repo:** https://github.com/GoogleChrome/lighthouse-ci · ⭐ 7037
- **Fișier-dovadă:** `docs/configuration.md`
- **Cost de transfer:** dependenta-noua

**Ce face:**

Lighthouse CI are trei niveluri de aserțiune: `off`, `warn` (scrie pe stderr, exit 0) și `error` (exit non-zero, deci pică jobul). Fiecare audit Lighthouse poate fi verificat pe trei proprietăți — `minScore`, `maxNumericValue` (milisecunde sau bytes) și `maxLength`. Bugetele de resurse se scriu ca aserțiuni de forma `resource-summary:<tip>:(size|count)`, deci pragul de mărime al documentului HTML sau numărul de fonturi devin condiții de build. Există și `aggregationMethod` (median / optimistic / pessimistic / median-run) pentru a decide cum se agregă mai multe rulări înainte de comparație — asta e antidotul la variabilitatea rulărilor în CI.

**De ce ne-ar folosi:**

Este exact lucrul care lipsește: 13 workflow-uri și niciunul nu are prag de performanță. Cu `error` + `maxNumericValue` pe `resource-summary:document:size` se prinde regresia de mărime a paginii de articol înainte să ajungă pe izz.ro, iar `aggregationMethod: median` ține în frâu zgomotul dintre rulări — problemă pe care o aveți deja demonstrat la suita de teste nedeterministă.

<details><summary>Fragment verbatim</summary>

```
##### Levels

There are three Lighthouse CI assertion levels.

- `off` - The audit result will not be checked. If an audit is not found in the `assertions` object, it is assumed to be `off`.
- `warn` - The audit result will be checked, and the result will be printed to stderr, but failure will not result in a non-zero exit code.
- `error` - The audit result will be checked, the result will be printed to stderr, and failure will result in a non-zero exit code.

##### Properties

The `score`, `details.items.length`, and `numericValue` properties of audit results can all be checked against configurable thresholds. Use `minScore`, `maxLength`, and `maxNumericValue` properties, respectively, in the options object to control the assertion.

{
  "ci": {
    "assert": {
      "assertions": {
        "first-contentful-paint": ["warn", {"maxNumericValue": 4000}],
        "viewport": "error",
        "resource-summary:document:size": ["error", {"maxNumericValue": 14000}],
        "resource-summary:font:count": ["warn", {"maxNumericValue": 1}],
        "resource-summary:third-party:count": ["warn", {"maxNumericValue": 5}]
      }
    }
  }
}
```

</details>

## 26. Măsurare pe output/ local, nu pe site-ul live

- **Repo:** https://github.com/GoogleChrome/lighthouse-ci · ⭐ 7037
- **Fișier-dovadă:** `docs/configuration.md`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

`collect.staticDistDir` primește directorul cu build-ul static; Lighthouse CI pornește singur un server local peste el și rulează auditurile acolo. Descoperă automat URL-urile din fișierele HTML de pe disc, cu `maxAutodiscoverUrls` (implicit 5, 0 = fără limită) și `staticDirFileDiscoveryDepth` (implicit 2) ca limite de explorare. Când dai și `url` explicit, portul din URL e rescris cu portul serverului temporar, deci poți scrie `http://localhost/pagina.html` fără să știi portul.

**De ce ne-ar folosi:**

Rezolvă direct blocajul cunoscut „Cloudflare bot-challenge blochează unelte headless pe izz.ro" — nu mai testezi produsul livrat, testezi `output/` înainte de deploy, unde niciun challenge nu se interpune. În plus descoperirea automată a URL-urilor se potrivește cu un SSG care generează articole, categorii și subiecte fără listă manuală.

<details><summary>Fragment verbatim</summary>

```
#### `staticDistDir`

The path to the directory where the project's productionized static assets are kept. Lighthouse CI uses this to spin up a static server on your behalf that will be used to load your site.

Use this option when the project is a static website to be hosted locally that does not require a separate server. **DO NOT** use this option if `url` will point to an origin that isn't `localhost` or the project uses `startServerCommand` to start a separate server.

  --maxAutodiscoverUrls      The maximum number of pages to collect when using the staticDistDir
                             option with no specified URL. Disable this limit by setting to 0.
                                                                               [number] [default: 5]
  --staticDirFileDiscoveryDepth The maximum depth of nested folders Lighthouse will look into to discover 
                                URLs on a static file folder.
                                                                               [number] [default: 2]

**When used with `staticDistDir`:**

- Automatic detection of URLs based on HTML files on disk will be disabled.
- URLs will have their port replaced with the port of the local server that Lighthouse CI starts for you. This allows you to write URLs as `http://localhost/my-static-page.html` without worrying about the chosen temporary port.
```

</details>

## 27. budget.json în kB, cablat în GitHub Actions

- **Repo:** https://github.com/treosh/lighthouse-ci-action · ⭐ 1286
- **Fișier-dovadă:** `README.md`
- **Cost de transfer:** copy-paste

**Ce face:**

Action-ul rulează Lighthouse pe o listă de URL-uri și primește `budgetPath`, calea către un `budget.json` conform specificației Google. Fișierul e o listă de obiecte cu `path` (glob) și `resourceSizes`, unde bugetul se exprimă în kilobytes — spre deosebire de aserțiunile LHCI, unde aceeași valoare se scrie în bytes. Documentația action-ului spune explicit că build-ul pică dacă vreun URL depășește bugetul. Are și `uploadArtifacts` pentru a salva rapoartele ca artefacte de job.

**De ce ne-ar folosi:**

E cea mai ieftină formă a pragului care lipsește: un fișier de 8 linii plus 12 linii de workflow, fără server LHCI, fără infrastructură. `uploadArtifacts: true` se potrivește cu reflexul „dovada înaintea raționamentului" — când pică, ai raportul salvat, nu doar un exit code.

<details><summary>Fragment verbatim</summary>

```
      - name: Audit URLs using Lighthouse
        uses: treosh/lighthouse-ci-action@v12
        with:
          urls: |
            https://example.com/
            https://example.com/blog
          budgetPath: ./budget.json # test performance budgets
          uploadArtifacts: true # save results as an action artifacts
          temporaryPublicStorage: true # upload lighthouse report to the temporary storage

Describe your performance budget using a [`budget.json`](https://web.dev/use-lighthouse-for-performance-budgets/).

[
  {
    "path": "/*",
    "resourceSizes": [
      { "resourceType": "document", "budget": 18 },
      { "resourceType": "total", "budget": 200 }
    ]
  }
]

#### `budgetPath`

Use a performance budget to keep your page size in check. `Lighthouse CI Action` will fail the build if one of the URLs exceeds the budget.
```

</details>

## 28. Un singur prag peste tot site-ul, cu crawl automat

- **Repo:** https://github.com/harlan-zw/unlighthouse · ⭐ 4751
- **Fișier-dovadă:** `docs/2.integrations/1.ci.md`
- **Cost de transfer:** dependenta-noua

**Ce face:**

`unlighthouse-ci --site <url> --budget 80` descoperă singur toate paginile site-ului, rulează Lighthouse pe fiecare în paralel și iese cu cod 1 dacă vreo categorie de pe vreo pagină scade sub prag. Bugetul poate fi și pe categorii, într-un `unlighthouse.config.ts` cu `ci.budget` ca obiect (performance / accessibility / best-practices / seo separat). Documentația își asumă contrastul cu LHCI: acolo listezi URL-urile manual, aici se descoperă.

**De ce ne-ar folosi:**

Un agregator de știri are sute de pagini generate (articole, categorii, subiecte, calendar, localități) — o listă manuală de URL-uri în lighthouserc devine caducă la fiecare build. Aici o singură comandă acoperă tot. Bugetele pe categorii permit prag sever pe SEO și accesibilitate, unde deja aveți investiție (JSON-LD complet), și prag mai relaxat pe performance cât timp e în lucru.

<details><summary>Fragment verbatim</summary>

```
The `unlighthouse-ci` binary runs Lighthouse on every page of your site and fails your CI build if any score drops below a budget:

npm install -g @unlighthouse/cli puppeteer
unlighthouse-ci --site https://staging.example.com --budget 80

Exit code 1 = budget failed. Exit code 0 = all pages passed. That's the entire contract.

// unlighthouse.config.ts
export default defineUnlighthouseConfig({
  site: 'https://example.com',
  ci: {
    budget: {
      'performance': 70, // Performance can be lower
      'accessibility': 95, // Accessibility must be high
      'best-practices': 80,
      'seo': 90,
    },
  },
})
```

</details>

## 29. Fallback de font cu metrici potrivite, ca să nu sară textul

- **Repo:** https://github.com/unjs/fontaine · ⭐ 1975
- **Fișier-dovadă:** `packages/fontaine/src/css.ts`
- **Cost de transfer:** reimplementare

**Ce face:**

Generează un `@font-face` fals, cu `src: local("Arial")`, care imită metricile fontului tău real prin patru descriptori CSS: `size-adjust`, `ascent-override`, `descent-override` și `line-gap-override`. Formula: `sizeAdjust = (xWidthAvg/unitsPerEm al fontului dorit) / (același raport la fontul de sistem)`, apoi ascent/descent/lineGap se împart la `unitsPerEm * sizeAdjust`. Rezultatul e că textul randat cu fallback-ul ocupă exact aceleași linii ca fontul final, deci swap-ul nu mai produce deplasare de layout.

**De ce ne-ar folosi:**

Aveți `fetch_fonts.py` și `fonts.yml`, deci fonturi self-hosted — dar descărcarea fontului nu spune nimic despre CLS. Asta e piesa care lipsește între `font-display: swap` și zero deplasare. Se poate genera la build cu `fontTools` (citește ascent/descent/unitsPerEm din tabelele hhea/head) și emite CSS-ul în template, fără Node. E și consistent cu bugetul `resource-summary:font:count` din primul finding.

<details><summary>Fragment verbatim</summary>

```
export function generateFontFace(metrics: FontFaceMetrics, fallback: FallbackOptions) {
  const { name: fallbackName, font: fallbackFontName, metrics: fallbackMetrics, ...properties } = fallback

  // Calculate size adjust
  const preferredFontXAvgRatio = metrics.xWidthAvg / metrics.unitsPerEm
  const fallbackFontXAvgRatio = fallbackMetrics
    ? fallbackMetrics.xWidthAvg / fallbackMetrics.unitsPerEm
    : 1

  const sizeAdjust = fallbackMetrics && preferredFontXAvgRatio && fallbackFontXAvgRatio
    ? preferredFontXAvgRatio / fallbackFontXAvgRatio
    : 1

  const adjustedEmSquare = metrics.unitsPerEm * sizeAdjust

  // Calculate metric overrides for preferred font
  const ascentOverride = metrics.ascent / adjustedEmSquare
  const descentOverride = Math.abs(metrics.descent) / adjustedEmSquare
  const lineGapOverride = metrics.lineGap / adjustedEmSquare

  const declaration = {
    'font-family': JSON.stringify(fallbackName),
    'src': `local(${JSON.stringify(fallbackFontName)})`,
    'size-adjust': toPercentage(sizeAdjust),
    'ascent-override': toPercentage(ascentOverride),
    'descent-override': toPercentage(descentOverride),
    'line-gap-override': toPercentage(lineGapOverride),
  }
```

</details>

## 30. Diacriticele românești cad în subsetul latin-ext, nu latin

- **Repo:** https://github.com/fontsource/fontsource · ⭐ 6055
- **Fișier-dovadă:** `packages/core/tests/__snapshots__/subsets/latin-ext-nam-subset.json`
- **Cost de transfer:** copy-paste

**Ce face:**

Registrul de subseturi definește pentru fiecare subset intervalul exact de `unicode-range`. Subsetul `latin` acoperă `U+A0-FF`, deci conține â (U+00E2) și î (U+00EE), dar NU conține ă (U+0102/0103), ș (U+0218/0219) și ț (U+021A/021B). Acelea intră în `latin-ext`, care declară `U+100-130` și `U+154-2BA`. Mecanismul e descriptorul `unicode-range` pe `@font-face`: browserul descarcă fișierul doar dacă pagina chiar folosește caractere din interval.

**De ce ne-ar folosi:**

Un site de știri românesc are ș și ț în aproape fiecare titlu. Dacă `fetch_fonts.py` aduce doar subsetul latin (implicitul multor pipeline-uri Google Fonts), jumătate din diacritice se randează cu fontul de sistem — două fonturi în aceeași propoziție, plus deplasare la swap. Verificarea e de cinci minute: uită-te ce interval `unicode-range` e emis în CSS și dacă fișierul descărcat acoperă U+0218-021B. Invers, dacă aduceți tot, `unicode-range` corect vă lasă să separați latin de latin-ext și să scădeți transferul.

<details><summary>Fragment verbatim</summary>

```
{
  "name": "latin-ext",
  "type": "range",
  "unicodeRange": "U+0, U+D, U+20, U+A0, U+100-130, U+132-151, U+154-2BA, U+2BC-2C5, U+2C7-2CC, U+2CE-2D7, U+2DD-301, U+303-304, U+308-309, U+323, U+329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A

{
  "name": "latin",
  "type": "range",
  "unicodeRange": "U+0, U+D, U+20-7E, U+A0-FF, U+131, U+152-153, U+2BB-2BC, U+2C6, U+2DA, U+2DC, U+300-301, U+303-304, U+308-309, U+323, U+329, U+2002, U+2009, U+200B, U+2013-2014, U+2018-201A, U+201C-201E, U+2022, U+2026, U+2032-2033, U+2039-203A, U+2044, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD",
```

</details>

## 31. CSS critic inline ca pas post-build peste HTML-ul generat

- **Repo:** https://github.com/danielroe/beasties · ⭐ 682
- **Fișier-dovadă:** `packages/beasties/README.md`
- **Cost de transfer:** dependenta-noua

**Ce face:**

API-ul central e `await beasties.process(html)` — primește un string HTML și întoarce HTML-ul cu regulile CSS efectiv folosite de document inline într-un `<style>`, restul foii fiind încărcat asincron. Nu depinde de un bundler: `path` spune de unde să citească fișierele CSS de pe disc, `publicPath` scoate prefixul din `href`, `pruneSource` elimină din foaia externă regulile deja inline, iar `allowRules` forțează includerea unor selectoare care nu apar în DOM-ul static (stări de hover, clase adăugate de JS). Strategiile de `preload` includ `swap`, care transformă link-ul în preload și îl comută în stylesheet după încărcare.

**De ce ne-ar folosi:**

Fiind SSG, `output/` e o grămadă de fișiere HTML gata făcute — exact intrarea pe care o vrea `process()`. Un script Node de 20 de linii care iterează `output/**/*.html` merge fără să atingă generatorul Python. Atenție la un detaliu al vostru: aveți testul `no_inline_js`, iar strategiile `swap`/`swap-high`/`swap-low` introduc JS; `preload` implicit (mută link-urile și pune meta preload) nu introduce JS, deci alegeți-l pe acela ca să nu spargeți testul.

<details><summary>Fragment verbatim</summary>

```
import Beasties from 'beasties'

const beasties = new Beasties({
  // optional configuration (see below)
})

const inlined = await beasties.process(html)

// "<style>.blue{color:blue}</style><div class=\"blue\">I'm Blue</div>"

- `path` **String** Base path location of the CSS files _(default: `''`)_
- `publicPath` **String** Public path of the CSS resources. This prefix is removed from the href _(default: `''`)_
- `pruneSource` **Boolean** Remove inlined rules from the external stylesheet _(default: `false`)_
- `allowRules` **Array<String | RegExp>** Always include rules matching these selectors or patterns in the critical CSS, regardless of whether they match elements in the document. _(default: `[]`)_
- `preload` **String** Which preload strategy to use

- **default:** Move stylesheet links to the end of the document and insert preload meta tags in their place.
- **"swap":** Convert stylesheet links to preloads that swap to `rel="stylesheet"` once loaded. <kbd>JS</kbd>
```

</details>

## 32. Reguli de generat picture/srcset fără CLS la imagini

- **Repo:** https://github.com/11ty/image · ⭐ 465
- **Fișier-dovadă:** `src/generate-html.js`
- **Cost de transfer:** reimplementare

**Ce face:**

Algoritmul de emitere a marcajului responsive, cu trei decizii care contează. Unu: `width`/`height` pe `<img>` se iau din candidatul cel mai MARE (`lowsrc[lowsrc.length - 1]`), nu din cel mic — raportul de aspect e identic, iar browserul rezervă spațiul corect. Doi: un `srcset` cu un singur candidat nu primește descriptor `w`, deci nu are nevoie de `sizes` — evită markup invalid. Trei: dacă sunt mai mulți candidați și lipsește `sizes`, se aruncă eroare, exceptând cazul `loading="lazy"` unde se pune `sizes="auto"`. Formatul de fallback se alege dintr-o listă de preferință (jpeg, png, gif, svg, webp, avif), iar `alt` lipsă e eroare, nu avertisment.

**De ce ne-ar folosi:**

Regulile astea sunt independente de sharp — se pot porta pe Pillow într-o funcție care întoarce dict-ul de atribute, plus o macro Jinja care îl randează. Aveți deja `covers.py` (426 linii) și `htmlart.py`, deci pipeline-ul de imagini există; ce lipsește e contractul de markup. Cel mai important e punctul unu: fără `width`/`height` corecte pe imaginea de lead, CLS-ul pe pagina de articol e garantat, indiferent cât optimizați bytes. Iar „alt lipsă = eroare de build" e o gardă gratuită care se leagă de tema pragurilor din CI.

<details><summary>Fragment verbatim</summary>

```
const LOWSRC_FORMAT_PREFERENCE = ["jpeg", "png", "gif", "svg", "webp", "avif"];

function generateSrcset(metadataFormatEntry) {
  // A single candidate needs no `w` descriptor (a bare URL defaults to 1x density),
  // which also means it doesn’t require a `sizes` attribute to be valid HTML. See #298.
  if(metadataFormatEntry.length === 1) {
    return metadataFormatEntry[0].url;
  }
  return metadataFormatEntry.map(entry => entry.srcset).join(", ");
}

  if(imgAttributes.alt === undefined) {
    // You bet we throw an error on missing alt (alt="" works okay)
    throw new Error(`Missing \`alt\` attribute on \`@11ty/eleventy-img\` image optimization from: ${originalSrc}`);
  }

  imgAttributes.src = lowsrc[0].url;

  if(htmlOptions.fallback === "largest" || htmlOptions.fallback === undefined) {
    imgAttributes.width = lowsrc[lowsrc.length - 1].width;
    imgAttributes.height = lowsrc[lowsrc.length - 1].height;
  } else if(htmlOptions.fallback === "smallest") {
    imgAttributes.width = lowsrc[0].width;
    imgAttributes.height = lowsrc[0].height;
  }

  if(lowsrc.length > 1 && !imgAttributes.sizes && imgAttributes.loading === "lazy") {
    imgAttributes.sizes = "auto";
  }
```

</details>

---

# Testare & QA
*determinism, snapshot, CI*

## 33. Verificare HTML construit: alt lipsă, imagini interne moarte, ancore #frag inexistente

- **Repo:** https://github.com/gjtorikian/html-proofer · ⭐ 1648
- **Fișier-dovadă:** `lib/html_proofer/check/images.rb`
- **Cost de transfer:** reimplementare

**Ce face:**

Rulează pe DIRECTORUL de HTML deja generat (nu pe sursă) și, per fișier, verifică: img fără src/srcset, imagine internă care nu există pe disc, URL protocol-relative, schema http în loc de https, alt lipsă sau gol. Separat, în lib/html_proofer/url_validator/internal.rb, validează link-urile interne inclusiv fragmentul: „internally linking to #{url}; the file exists, but the hash '#{href_hash}' does not" — deci prinde ancorele #sectiune care nu au țintă în pagina destinație. Are cache pe disc (lib/html_proofer/cache.rb, DEFAULT_STORAGE_DIR = tmp/.htmlproofer) cu timeframe separat pentru intern și extern („2d", „1w", „1M").

**De ce ne-ar folosi:**

Categoria de bug pe care cele 46 de teste pytest nu o pot prinde: ele testează generatorul, nu produsul. O imagine de cover generată cu cale greșită, un href intern spre un articol care a picat din selecție, o ancoră spre #sursa care nu mai există — toate trec de unit teste și ajung live. La 3.5% hit rate pe Wikimedia, verificarea „internal image does not exist" pe output/ e exact garda care lipsește. Validarea fragmentelor e utilă și pentru FAQPage/BreadcrumbList unde legați secțiuni în pagină.

<details><summary>Fragment verbatim</summary>

```
@html.css("img, source").each do |node|
  @img = create_element(node)
  next if @img.ignore?
  if missing_src?
    add_failure("image has no src or srcset attribute", element: @img)
  elsif @img.url.protocol_relative?
    add_failure(
      "image link #{@img.url} is a protocol-relative URL, use explicit https:// instead",
      element: @img,
    )
  elsif @img.url.remote?
    add_to_external_urls(@img.url, @img)
  elsif !@img.url.exists? && !@img.multiple_srcsets? && !@img.multiple_sizes?
    add_failure(
      "internal image #{@img.url.raw_attribute} does not exist",
      element: @img,
    )
  end
  if @img.img_tag? && !ignore_element?
    if missing_alt_tag? && !ignore_missing_alt?
      add_failure(
        "image #{@img.url.raw_attribute} does not have an alt attribute",
        element: @img,
      )
```

</details>

## 34. Link rot cu cache, UA custom și status-uri acceptate

- **Repo:** https://github.com/lycheeverse/lychee · ⭐ 3807
- **Fișier-dovadă:** `lychee.example.toml`
- **Cost de transfer:** dependenta-noua

**Ce face:**

Extrage link-urile din HTML/Markdown și le verifică în paralel. Trei mecanisme relevante: (a) cache pe disc cu vârstă maximă și excludere din cache a claselor de status volatile (5xx nu se memorează, ca să nu îngheți un fals-negativ); (b) `accept` ca listă de status-uri considerate VALIDE — 429 e acceptat explicit, adică rate-limit nu e tratat ca link mort; (c) `user_agent`, `header` și `remap`, care permit rescrierea unui URL de producție într-unul local. Workflow-ul propriu (.github/workflows/links.yml) rulează pe cron zilnic și deschide automat un issue din raport: `uses: peter-evans/create-issue-from-file@v6` cu `if: env.lychee_exit_code != 0`.

**De ce ne-ar folosi:**

Un agregator de știri e un câmp minat de link rot: sursele externe mor sau se mută constant, iar voi nu aveți NIMIC care să verifice asta. Mai important pentru problema voastră cunoscută cu Cloudflare: `accept` și `user_agent` sunt exact butoanele care fac diferența între „sursa e moartă" și „infrastructura refuză automatele" — aceeași confuzie care era să vă coste o sursă vie la feedcheck. Iar `remap` rezolvă verificarea link-urilor absolute izz.ro pe build-ul local, fără să atingi site-ul live.

<details><summary>Fragment verbatim</summary>

```
# Enable link caching. This can be helpful to avoid checking the same links on
# multiple runs.
cache = true

# Discard all cached requests older than this duration.
max_cache_age = "2d"

# A list of status codes that will be ignored from the cache
cache_exclude_status = "500.."

# User agent to send with each request.
user_agent = "curl/7.83. 1"

# Maximum number of allowed retries before a link is declared dead.
max_retries = 2

# Comma-separated list of accepted status codes for valid links.
accept = ["200", "429"]

# Custom request headers
header = { "accept" = "text/html", "x-custom-header" = "value" }

# Remap URI matching pattern to different URI.
remap = ["https://example.com http://example.invalid"]
```

</details>

## 35. Test de build hermetic: mkdtemp pentru output ȘI cache, apoi git diff

- **Repo:** https://github.com/getpelican/pelican · ⭐ 13330
- **Fișier-dovadă:** `pelican/tests/test_pelican.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

Fiecare test de integrare primește DOUĂ directoare temporare proaspete — unul pentru output, unul pentru cache — injectate prin override de settings, și amândouă șterse în tearDown. Build-ul rulează complet acolo, apoi rezultatul se compară cu un arbore de referință versionat în repo. Comparația nu e făcută cu filecmp, ci delegată la git: în pelican/tests/support.py, `diff_subproc` rulează `["git", "--no-pager", "diff", "--no-ext-diff", "--exit-code", "-w", first, second]` — `-w` ignoră whitespace-ul, iar `--exit-code` face din diff un assert. Mesajul de eroare conține diff-ul complet, deci vezi exact ce s-a schimbat în HTML.

**De ce ne-ar folosi:**

Ăsta e răspunsul direct la problema voastră #1. Nedeterminismul nu vine din teste, vine din faptul că `output/` e o variabilă globală partajată între rulări: fixture-ul citește ce a lăsat build-ul precedent. Leacul e structural — calea de output devine PARAMETRU, nu constantă, iar testul primește un mkdtemp. Punctul cheie pe care l-aș sublinia: Pelican izolează și CACHE_PATH, nu doar output-ul; voi aveți generator/state.py, deci există o a doua sursă de stare persistentă care trebuie izolată la fel, altfel mutați problema, n-o rezolvați. Bonus: `git diff -w` ca assert vă dă snapshot testing pe HTML fără nicio dependență nouă.

<details><summary>Fragment verbatim</summary>

```
def setUp(self):
    super().setUp()
    self.temp_path = mkdtemp(prefix="pelicantests.")
    self.temp_cache = mkdtemp(prefix="pelican_cache.")
    self.maxDiff = None

def tearDown(self):
    read_settings()  # cleanup PYGMENTS_RST_OPTIONS
    rmtree(self.temp_path)
    rmtree(self.temp_cache)

def assertDirsEqual(self, left_path, right_path, msg=None):
    """
    Check if the files are the same (ignoring whitespace) below both paths.
    """
    proc = diff_subproc(left_path, right_path)
    out, err = proc.communicate()
    if proc.returncode != 0:
        raise self.failureException(msg)

def test_basic_generation_works(self):
    settings = read_settings(path=None, override={
        "PATH": INPUT_PATH, "OUTPUT_PATH": self.temp_path,
        "CACHE_PATH": self.temp_cache, "LOCALE": locale.normalize("en_US")})
    pelican = Pelican(settings=settings)
```

</details>

## 36. Amestecă ordinea testelor ca să expună dependențele ascunse

- **Repo:** https://github.com/pytest-dev/pytest-randomly · ⭐ 717
- **Fișier-dovadă:** `README.rst`
- **Cost de transfer:** dependenta-noua

**Ce face:**

Plugin pytest care (a) amestecă ordinea modulelor, claselor și funcțiilor la fiecare rulare, (b) tipărește seed-ul folosit ca să poți reproduce exact eșecul cu `--randomly-seed=N`, și (c) resetează `random.seed()` la o valoare derivată determinist din seed + ID-ul testului, înainte de setup, run și teardown separat. Deci ordinea e aleatoare, dar rulările sunt reproductibile.

**De ce ne-ar folosi:**

Nu vă repară nedeterminismul, dar îl face VIZIBIL și reproductibil — iar asta lipsește acum. În momentul ăsta un test care depinde de artefactele lăsate de alt test trece sau pică după noroc, fără să știți care e vinovatul. Cu ordinea amestecată, dependența devine un eșec pe care îl poți fixa cu un seed și îl poți debuga. Costul e o linie în requirements și niciun cod modificat. Atenție la calibrare: plugin-ul prinde dependențe ÎNTRE teste, nu dependența de un `output/` rămas de la un build anterior rulării — pentru aia e nevoie de izolarea din finding-ul Pelican. Se folosesc împreună, nu unul în locul celuilalt.

<details><summary>Fragment verbatim</summary>

```
* Randomly shuffles the order of test items. This is done first at the level of
  modules, then at the level of test classes (if you have them), then at the
  order of functions. This also works with things like doctests.

* Generates a base random seed or accepts one for reproduction with ``--randomly-seed``.
  The base random seed is printed at the start of the test run, and can be passed in to repeat a failure caused by test ordering or random data.

* At the start of the test run, and before each test setup, run, and teardown, it resets Python's global random seed to a fixed value, using |random.seed()|__.
  The fixed value is derived from the base random seed, the pytest test ID, and an offset for setup or teardown.

By randomly ordering the tests, the risk of surprising inter-test dependencies
is reduced - a technique used in many places, for example Google's C++ test
runner `googletest`.
Research suggests that "dependent tests do exist in practice" and a random
order of test executions can effectively detect such dependencies [1]_.
Alternatively, a reverse order of test executions, as provided by `pytest-reverse`,
may find less dependent tests but can achieve a better benefit/cost ratio.
```

</details>

## 37. Validare HTML pe tot directorul generat, din Python

- **Repo:** https://github.com/svenkreiss/html5validator · ⭐ 338
- **Fișier-dovadă:** `html5validator/validator.py`
- **Cost de transfer:** dependenta-noua

**Ce face:**

Ambalaj Python peste Nu Html Checker (vnu.jar, de la validator/validator — validatorul oficial W3C), livrat împreună cu jar-ul în pachetul pip `vnujar`. Parcurge recursiv un director, filtrează după pattern și blacklist, apoi rulează vnu pe toate fișierele într-un singur proces Java. Suportă `--format json` pentru ieșire parsabilă, `--errors-only`, `--no-langdetect` și liste de ignorare, atât literale cât și regex — mecanismul cu care faci validarea utilizabilă în CI fără să te înece în warning-uri irelevante.

**De ce ne-ar folosi:**

E singura rută de validare HTML care se lipește natural de un proiect Python fără framework: pip install, plus Java (deja prezent pe runner-ele GitHub Actions). Categoriile pe care le prinde și pe care voi n-aveți cum să le prindeți acum: id-uri duplicate (probabil în cardurile de articol generate în buclă), tag-uri neînchise dintr-un branch Jinja rar atins, atribute invalide, imbricare ilegală, entități HTML nescăpate din titlurile RSS — și exact aici e riscul mare, pentru că titlurile vin din surse externe pe care nu le controlați. `--no-langdetect` e obligatoriu la voi: conținut românesc, detectorul de limbă dă fals-pozitive.

<details><summary>Fragment verbatim</summary>

```
DEFAULT_IGNORE_RE: List[str] = [
    r'\APicked up _JAVA_OPTIONS:.*',
    r'\ADocument checking completed. No errors found.*',
]

DEFAULT_IGNORE: List[str] = [
    '{"messages":[]}'
]

def all_files(
        directory: str = '.',
        match: str = '*.html',
        blacklist: Optional[List[str]] = None,
        skip_invisible: bool = True) -> List:
    files = []
    for root, dirnames, filenames in os.walk(directory):
        # filter out blacklisted directory names
        for b in blacklist:
            if b in dirnames:
                dirnames.remove(b)
        for pattern in match:
            for filename in fnmatch.filter(filenames, pattern):
                files.append(os.path.join(root, filename))
    return files
```

</details>

## 38. Accesibilitate fără browser, pe fișierele din output/

- **Repo:** https://github.com/dequelabs/axe-core · ⭐ 7369
- **Fișier-dovadă:** `doc/examples/jsdom/test/a11y.js`
- **Cost de transfer:** dependenta-noua

**Ce face:**

axe-core rulează peste un DOM construit de jsdom, din string sau fișier — fără Chrome, fără Playwright, fără rețea. Regula `color-contrast` e dezactivată explicit în exemplu, pentru că jsdom nu face layout și nu calculează culori efective; restul regulilor merg. Catalogul din doc/rule-descriptions.md conține, verbatim: „Ensure each HTML document contains a non-empty <title> element" (document-title), „Ensure <img> elements have alternative text or a role of none or presentation" (image-alt), „Ensure every HTML document has a lang attribute" (html-has-lang), „Ensure every id attribute value used in ARIA and in labels is unique" (duplicate-id-aria), „Ensure links have discernible text" (link-name), „Ensure each page has at least one mechanism for a user to bypass navigation" (bypass).

**De ce ne-ar folosi:**

Ruta jsdom ocolește fix problema voastră: Cloudflare blochează uneltele headless pe izz.ro, deci orice audit de accesibilitate pe site-ul live e mort din start. Aici verifici fișierele din output/ ÎNAINTE de deploy, unde Cloudflare nu are cuvânt. Pe un agregator, regulile care contează sunt exact cele generate în buclă din date externe: link-name (card cu titlu gol dintr-un feed prost), image-alt (cover fără alt), document-title (pagină de categorie fără titlu), duplicate-id-aria (id repetat în template-ul de card). Reține limita, ca să nu o vindeți greșit: contrastul NU e verificabil pe ruta asta, deci partea vizuală de accesibilitate rămâne descoperită.

<details><summary>Fragment verbatim</summary>

```
const axe = require('axe-core');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

describe('axe', () => {
  const { document } = new JSDOM(`<!DOCTYPE html>
  <html lang="en">
    ...
  </html>`).window;
  const config = {
    rules: {
      'color-contrast': { enabled: false }
    }
  };

  it('reports that good HTML is good', async () => {
    const node = document.getElementById('working');
    const result = await axe.run(node, config);
    assert.equal(result.violations.length, 0, 'Violations is not empty');
  });

  it('reports that bad HTML is bad', async () => {
    const node = document.getElementById('broken');
    const results = await axe.run(node, config);
    assert.equal(results.violations.length, 1, 'Violations.length is not 1');
  });
});
```

</details>

## 39. Diff de imagini care ignoră antialiasing și măsoară pe fereastră

- **Repo:** https://github.com/mapbox/pixelmatch · ⭐ 6906
- **Fișier-dovadă:** `index.js`
- **Cost de transfer:** reimplementare

**Ce face:**

Compară două imagini pixel cu pixel și returnează numărul de pixeli diferiți, cu trei mecanisme care fac diferența față de un diff naiv: (a) distanța de culoare e perceptuală (OKLab HyAB), nu euclidiană pe RGB, deci pragul are înțeles constant pe toată gama de culori; (b) pixelii care sunt doar antialiasing sunt DETECTAȚI și excluși din numărătoare — sursa numărul unu de fals-pozitive la regresie vizuală, pentru că fonturile se rasterizează ușor diferit între rulări; (c) `windowSize` finit schimbă metrica din „total pixeli diferiți" în „maximul de pixeli diferiți din orice fereastră N×N", deci o schimbare mică dar concentrată pică testul, în timp ce zgomotul împrăștiat pe toată pagina nu.

**De ce ne-ar folosi:**

Aveți visual_check.py și o gardă vizuală, dar (după inventar) fără diff real de imagini — adică nu prindeți regresiile de layout: card care se rupe la un titlu lung, cover care împinge grid-ul, header suprapus pe mobil. Algoritmul e portabil în Python peste Pillow, pe care îl aveți deja în requirements, fără nicio dependență nouă. Cele două idei care merită copiate chiar dacă nu portați tot: excluderea antialiasing-ului (altfel garda va fi zgomotoasă și o veți dezactiva în două săptămâni) și metrica pe fereastră glisantă, care e mult mai potrivită pentru o pagină de știri unde conținutul se schimbă legitim la fiecare build — un prag global pe „procent de pixeli diferiți" e inutilizabil acolo.

<details><summary>Fragment verbatim</summary>

```
 * @param {number} [options.threshold=0.1] Matching threshold (0 to 1); smaller is more sensitive.
 * @param {boolean} [options.includeAA=false] Whether to skip anti-aliasing detection.
 * @param {number} [options.windowSize=Infinity] If finite, return the maximum number of diff pixels found in any N×N sliding window instead of the total diff count.

// maximum acceptable OKLab HyAB distance between two colors;
// 1.0 is the HyAB distance between black and white
const maxDelta = threshold;

// compare each pixel of one image against the other one
for (let i = 0, pos = 0; i < len; i++, pos += 4) {
    const delta = a32[i] === b32[i] ? 0 : colorDelta(img1, img2, pos, pos, checkerboard, maxDelta);
    if (delta) {
        const x = i % width;
        const y = (i / width) | 0;
        // check it's a real rendering difference or just anti-aliasing
        const isExcludedAA = !includeAA && (antialiased(img1, x, y, width, height, a32, b32) || antialiased(img2, x, y, width, height, b32, a32));
        if (isExcludedAA) {
            // one of the pixels is anti-aliasing; draw as yellow and do not count as difference
            if (mask) mask[i] = 2;
        } else {
            diff++;
        }
    }
}
```

</details>

## 40. Aserțiuni declarative pe JSON-LD cu JMESPath

- **Repo:** https://github.com/iaincollins/structured-data-testing-tool · ⭐ 82
- **Fișier-dovadă:** `lib/tests.js`
- **Cost de transfer:** reimplementare

**Ce face:**

Extrage datele structurate dintr-o pagină (JSON-LD, microdata, RDFa, meta tags) într-un obiect unic, apoi rulează teste scrise ca expresii JMESPath peste el — ex. `NewsArticle[0].headline`. Testele se grupează în preset-uri legate de o schemă (lib/helpers/presets.js): dacă preset-ul are `schema`, testele se multiplică automat peste FIECARE instanță găsită din acea schemă, cu `test.test.replace(/(.*)?\[\*\]/, ...)`, deci scrii regula o dată și se aplică la toate. Când un test nu are tip explicit, caută proprietatea pe rând în jsonld, microdata, rdfa, meta — util când migrezi între formate.

**De ce ne-ar folosi:**

Aveți JSON-LD bogat — NewsArticle, BreadcrumbList, ItemList, FAQPage, Organization, ImageObject — și zero teste care să verifice că e corect după generare. Modul tipic de eșec la un agregator nu e „lipsește blocul", ci „câmpul e prezent dar gol": headline gol când titlul din feed e prost, datePublished null când sursa n-a dat dată, ImageObject fără url când photojudge a respins poza. Un unit test pe generator nu prinde asta pentru că datele reale intră abia la build. Tiparul e transferabil ieftin: `jmespath` există pe PyPI, extragerea JSON-LD din HTML e o expresie regex peste script[type=application/ld+json], iar regulile stau într-un YAML pe care îl poți extinde fără să atingi cod. Repo-ul are doar 82 de stele — recomand tiparul, nu dependența.

<details><summary>Fragment verbatim</summary>

```
const jmespath = require('jmespath')

// Wrapper for the _test() function that tries to work out how
// best to run the test, with a series of fallbacks, so that the
// most specific type of test can be run as possible.
function runTest(test, structuredData) {
  if (test.type == 'metatag') {
    return _test(test, structuredData.metatags)
  } else if (test.type == 'jsonld') {
    return _test(test, structuredData.jsonld)
  } else if (test.type == 'microdata') {
    return _test(test, structuredData.microdata)
  } else if (test.type == 'any' || !Object(test).hasOwnProperty('type')) {
    let result = {}
    result = _test(test, structuredData.jsonld)
    if (result.testPassed) {
      test.type = 'jsonld'
      return result
    }
    // ... microdata, rdfa, metatags
    return {
      testPassed: false,
      testError: {
        type: 'NOT_FOUND',
        message: `The property "${test.test}" was not found`,
      }
    }
```

</details>

---

# Procesare de conținut
*NER, extragere articol, imagini*

## 41. Alegerea imaginii principale prin distanța în DOM

- **Repo:** https://github.com/AndyTheFactory/newspaper4k · ⭐ 1135
- **Fișier-dovadă:** `newspaper/extractors/image_extractor.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

După ce identifică nodul corpului articolului (top_node), calculează pentru fiecare <img> din pagină o distanță structurală în arborele DOM: transformă calea XPath a fiecărui nod în listă de pași, găsește primul pas divergent și adună lungimile rămase (funcția locală node_distance). Sortează candidații crescător după distanță și returnează prima imagine care trece validarea de dimensiune. Înaintea acestui pas există un cascade de meta-taguri cu scoruri explicite (og:image=10, link rel=image_src|img_src=8, meta name=og:image=8, favicon=5, în newspaper/extractors/defines.py, META_IMAGE_TAGS) — deci meta câștigă dacă e validă, altfel se cade pe proximitatea față de text. Validarea (_check_image_size) respinge sub 300x200 px sau sub 10000 px arie și are o regulă separată pentru URL-uri care conțin 'logo' sau 'sprite'.

**De ce ne-ar folosi:**

Noi luăm lead photo prin tools/fetch_leadphotos.py, dar nu am văzut în inventar un criteriu de proximitate față de corpul articolului — asta e exact ce separă imaginea reală a știrii de bannerele, logourile și thumbnail-urile de 'citește și'. Repo-ul e MIT, iar tehnica e ~40 de linii cu lxml, care oricum e folosit indirect. Nu rezolvă cei 3.5% de pe Wikimedia, dar reduce nevoia de a căuta extern: multe surse RSS românești au deja o poză bună în pagină, doar că e greu de distins de decor.

<details><summary>Fragment verbatim</summary>

```
        img_cand = []
        for img in parsers.get_tags(doc, tag="img"):
            if not img.get("src"):
                continue
            if img.get("src").startswith("data:"):
                continue

            if top_node is not None:
                distance = node_distance(top_node, img)
                img_cand.append((img, distance))
            else:
                if self._check_image_size(img.get("src"), article_url):
                    return img.get("src")

        img_cand.sort(key=lambda x: x[1])

        for img in img_cand:
            if self._check_image_size(img[0].get("src"), article_url):
                return img[0].get("src")

        return ""
```

</details>

## 42. Validare dimensiune imagine fără a descărca fișierul

- **Repo:** https://github.com/AndyTheFactory/newspaper4k · ⭐ 1135
- **Fișier-dovadă:** `newspaper/extractors/image_extractor.py`
- **Cost de transfer:** copy-paste

**Ce face:**

_fetch_image deschide conexiunea cu stream=True, verifică întâi Content-Type (abandonează dacă nu conține 'image'), apoi alimentează un PIL ImageFile.Parser cu bucăți de 1024 de octeți (self._chunksize) într-o buclă care se oprește imediat ce parserul a reconstruit obiectul Image. Pentru un JPEG/PNG, dimensiunile sunt în antet, deci de obicei se citește un singur chunk. Setează și headerul Referer din requests_params, ceea ce trece de hotlink protection pe multe site-uri.

**De ce ne-ar folosi:**

Avem deja Pillow în requirements.txt, deci e zero dependențe noi. Dacă validăm candidații de imagine descărcând fișierul întreg, un build care evaluează câteva sute de candidați plătește zeci de MB și secunde bune; aici plătim ~1 KB per candidat. Asta face fezabil un pas de 'încearcă 5 surse de imagine și alege prima validă' în loc de o singură căutare Wikimedia. Headerul Referer e detaliul care ne-ar lipsi și pe care l-am fi găsit greu singuri.

<details><summary>Fragment verbatim</summary>

```
        response = None
        while True:
            try:
                response = session.get(
                    url,
                    stream=True,
                    **requests_params,
                )

                content_type = response.headers.get("Content-Type")

                if not content_type or "image" not in content_type.lower():
                    return None

                p = ImageFile.Parser()
                new_data = response.raw.read(self._chunksize)
                while not p.image and new_data:
                    try:
                        p.feed(new_data)
```

</details>

## 43. Vot între mai mulți extractori de corp de articol

- **Repo:** https://github.com/fhamborg/news-please · ⭐ 2478
- **Fișier-dovadă:** `newsplease/pipeline/extractor/comparer/comparer_text.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

Rulează mai mulți extractori independenți pe aceeași pagină (newspaper, readability, date_extractor, lang_detect — vezi newsplease/pipeline/extractor/extractors/) și apoi compară rezultatele două câte două. Scorul este 1 - (|A Δ B| / (2·|A ∩ B|)) pe seturile de cuvinte, adică penalizează cuvintele care apar doar într-una din variante, normalizat la cele comune. Perechea cu scorul maxim câștigă; dacă unul dintre cei doi e 'newspaper' se ia acela (tiebreak fixat de autor), altfel se ia textul mai lung. Există comparatoare separate pentru titlu, dată, autor, limbă și top image (comparer_topimage.py). Există și un filtru înainte: variantele sub 15 cuvinte sunt eliminate.

**De ce ne-ar folosi:**

Noi avem un singur drum de extragere în generator/fetch.py + process.py. Când un site își schimbă template-ul, extractorul unic dă text trunchiat sau plin de meniuri și nu avem cum să detectăm asta automat — nu există al doilea semnal. Mecanismul ăsta oferă exact un detector: dacă două extrageri independente diverg puternic, articolul e suspect și poate merge la moderare în loc să iasă stricat pe site. Nu trebuie neapărat să adoptăm extractorii lor, doar schema de comparare, care e ~40 de linii de Python pur, fără dependențe.

<details><summary>Fragment verbatim</summary>

```
            # Compare every text with all other texts at least once
            for a, b, in itertools.combinations(list_text, 2):

                # Create sets from the texts
                set_a = set(a[0].split())
                set_b = set(b[0].split())
                symmetric_difference_a_b = set_a ^ set_b
                intersection_a_b = set_a & set_b

                # Replace 0 with -1 in order to elude division by zero
                if intersection_a_b == 0:
                    intersection_a_b = -1

                # Create the score. It divides the number of words which are not in both texts by the number of words which
                # are in both texts and subtracts the result from 1. The closer to 1 the more similiar they are.
                score = 1 - ((len(symmetric_difference_a_b)) / (2 * len(intersection_a_b)))
                list_score.append((score, a[1], b[1]))
```

</details>

## 44. Simhash Charikar pentru duplicate, zero dependențe noi

- **Repo:** https://github.com/adbar/trafilatura · ⭐ 6410
- **Fișier-dovadă:** `trafilatura/deduplication.py`
- **Cost de transfer:** copy-paste

**Ce face:**

Implementare compactă de Simhash: tokenizează textul (sample_tokens taie punctuația și păstrează doar alfanumerice, cu un fallback pentru limbi fără punctuație latină), hashuiește fiecare token cu blake2b pe 8 octeți, îl transformă într-un vector de +1/-1 pe 64 de biți (cu lru_cache la nivel de token, partajat între instanțe), însumează vectorii și ia semnul fiecărei poziții. Similaritatea se calculează cu hamming_distance, care e literalmente int.bit_count(self.hash ^ other_hash.hash) — un XOR și un popcount. Fișierul mai conține generate_bow_hash (hash de bag-of-words pentru duplicate exacte) și is_similar_domain pe SequenceMatcher.

**De ce ne-ar folosi:**

Avem clustering lexical în generator/cluster.py (126 de linii) și 46 de teste, dar un Simhash pe 64 de biți e un semnal complet diferit: rezistă la reordonări de cuvinte și la mici rescrieri, iar comparația e o instrucțiune de procesor, nu o intersecție de seturi. Se poate persista un întreg per articol în generator/state.py și verifica duplicatele față de tot arhivul, nu doar față de fereastra curentă. Importă doar hashlib, functools, string, unicodedata, operator — deci nu atinge requirements.txt. Apache-2.0, copy-paste legal cu atribuire.

<details><summary>Fragment verbatim</summary>

```
    def create_hash(self, inputstring: str) -> int:
        """Calculates a Charikar simhash. References used:
        https://github.com/vilda/shash/
        https://github.com/sean-public/python-hashes/blob/master/hashes/simhash.py
        Optimized for Python by @adbar.
        """
        vector = [0] * self.length

        for token in sample_tokens(inputstring, self.length):
            vector = list(map(add, vector, _vector_to_add(token, self.length)))

        return sum(1 << i for i in range(self.length) if vector[i] >= 0)
```

</details>

## 45. Community detection pentru grupare semantică de știri

- **Repo:** https://github.com/huggingface/sentence-transformers · ⭐ 18972
- **Fișier-dovadă:** `sentence_transformers/util/retrieval.py`
- **Cost de transfer:** dependenta-noua

**Ce face:**

community_detection primește o matrice de embeddings normalizate și găsește 'comunități' — grupuri în care fiecare element are cel puțin min_community_size vecini peste threshold cosinus. Lucrează pe batch-uri (batch_size=1024) calculând cos_scores = embeddings[batch] @ embeddings.T, filtrează rândurile cu prea puțini vecini apropiați, apoi extrage comunitățile în ordine descrescătoare, primul element fiind centrul. Exemplul din examples/sentence_transformer/applications/clustering/fast_clustering.py rulează pe 50k propoziții și declară ~5 secunde pentru clustering (excluzând calculul embeddings-urilor), cu apelul community_detection(corpus_embeddings, min_community_size=25, threshold=0.75).

**De ce ne-ar folosi:**

Asta e varianta 'corectă' pentru gruparea a N relatări ale aceleiași știri, spre deosebire de suprapunerea lexicală: două agenții care scriu despre același eveniment cu vocabular diferit ajung în același cluster. Costul e onest și mare: torch + un model (all-MiniLM-L6-v2 e multilingv slab pe română, ar trebui paraphrase-multilingual-MiniLM-L12-v2), adică sute de MB peste cele 7 dependențe actuale. Nu recomand adoptarea directă în build; recomand ca prag intermediar Simhash-ul din findings-ul anterior și, dacă vrem semantic, un pas offline care produce embeddings și le cache-uiește, nu un import în generator.

<details><summary>Fragment verbatim</summary>

```
def community_detection(
    embeddings: torch.Tensor | np.ndarray,
    threshold: float = 0.75,
    min_community_size: int = 10,
    batch_size: int = 1024,
    show_progress_bar: bool = False,
) -> list[list[int]]:
    """
    Function for Fast Community Detection.

    Finds in the embeddings all communities, i.e. embeddings that are close (closer than threshold).
    Returns only communities that are larger than min_community_size. The communities are returned
    in decreasing order. The first element in each list is the central point in the community.
    """
    if not isinstance(embeddings, torch.Tensor):
        embeddings = torch.tensor(embeddings)

    threshold = torch.tensor(threshold, device=embeddings.device)
    embeddings = normalize_embeddings(embeddings)
```

</details>

## 46. Openverse — un singur API peste 25 de surse cu licență liberă

- **Repo:** https://github.com/WordPress/openverse · ⭐ 359
- **Fișier-dovadă:** `api/api/serializers/media_serializers.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

MediaSearchRequestSerializer definește parametrii de căutare acceptați de API-ul public: q, source, excluded_source, license, license_type, creator, tags, title, filter_dead, extension, plus sortare. Catalogul din spate (catalog/dags/providers/provider_api_scripts/) are ingestori separați pentru flickr, wikimedia_commons, europeana, smithsonian, rawpixel, stocksnap, nappy, nypl, science_museum, cleveland_museum, metropolitan_museum, brooklyn_museum, museum_victoria, auckland_museum, finnish_museums, smk, phylopic, justtakeitfree, wordpress, inaturalist. Flickr singur e ingerat cu mapare completă de licențe CC (by, by-sa, by-nc, cc0, pdm). Endpoint-ul public e https://api.openverse.org/v1/images/ (văzut literal ca OPENVERSE_API_BASE = 'https://api.openverse.org/v1' în neno-is-ooo/mcp-openverse, src/index.ts, care mai expune și /images/{id}/related/).

**De ce ne-ar folosi:**

Ăsta e răspunsul direct la 3.5% pe 4024 de căutări: căutăm într-un singur depozit (Wikimedia Commons), care e o bibliotecă de fișiere, nu o bancă de fotografii de presă. Openverse indexează Flickr CC, Wikimedia și încă ~20 de surse sub aceeași interogare, cu filtru pe licență și pe extensie, fără cheie de API pentru volume mici. Parametrul filter_dead scutește un HEAD de validare. Bonus concret: endpoint-ul /related/ dă alternative când prima potrivire e proastă. Migrarea e o rescriere a interogării, nu a pipeline-ului — noi avem deja tot ce urmează (descărcare, judecată, atribuire).

<details><summary>Fragment verbatim</summary>

```
    field_names = [
        "q",
        "source",
        "excluded_source",
        "license",
        "license_type",
        "creator",
        "tags",
        COLLECTION,
        TAG,
        "title",
        "filter_dead",
        "extension",
        "mature",
        "unstable__sort_by",
        "unstable__sort_dir",
        "unstable__authority",
        "unstable__authority_boost",
        "unstable__include_sensitive_results",
    ]
```

</details>

## 47. Cascadă de imagini Wikipedia: pageimages, thumbnail, Wikidata P18

- **Repo:** https://github.com/siznax/wptools · ⭐ 593
- **Fișier-dovadă:** `wptools/page.py`
- **Cost de transfer:** adaptare-usoara

**Ce face:**

În loc să caute în Commons după text, wptools rezolvă entitatea la o pagină Wikipedia și colectează imaginile din mai multe locuri, etichetate cu un câmp 'kind': query-pageimage și query-thumbnail (din action=query&prop=pageimages&pithumbsize=240&redirects, vezi șablonul QUERY din wptools/query.py), wikidata-image (proprietatea P18 a itemului, în wptools/wikidata.py: wd_images = self.data['claims'].get('P18')), plus parse-image și parse-cover extrase din infobox. Parametrul &redirects rezolvă automat variantele de nume, iar &ppprop=disambiguation semnalează paginile de dezambiguizare care ar da o potrivire greșită.

**De ce ne-ar folosi:**

Diferența față de ce facem noi e conceptuală, nu de volum: căutarea full-text în Commons returnează fișiere, iar o entitate românească are rareori un fișier al cărui titlu se potrivește. În schimb, 'Klaus Iohannis' -> pagina ro.wikipedia -> pageimages -> thumbnail e o rezoluție deterministă, cu redirect handling gratuit. Pentru primari, instituții, localități (avem deja generator/localities.py și build_gazetteer.py) rata ar trebui să fie de ordinul zecilor de procente, nu 3.5%. Structura cu 'kind' e și ea de furat: ne spune din ce sursă a venit poza, deci putem măsura rata pe sursă în loc să avem un singur număr agregat. MIT.

<details><summary>Fragment verbatim</summary>

```
    def _set_query_image(self, page):
        """
        set image data from action=query response
        """
        pageimage = page.get('pageimage')
        thumbnail = page.get('thumbnail')

        if pageimage or thumbnail:
            if 'image' not in self.data:
                self.data['image'] = []

        if pageimage:
            self.data['image'].append({
                'kind': 'query-pageimage',
                'file': pageimage})

        if thumbnail:
            qthumb = {'kind': 'query-thumbnail'}
            qthumb.update(thumbnail)
            qthumb['url'] = thumbnail.get('source')
            del qthumb['source']
            qthumb['file'] = qthumb['url'].split('/')[-2]
            self.data['image'].append(qthumb)
```

</details>

## 48. RoNER — NER de producție pentru limba română

- **Repo:** https://github.com/dumitrescustefan/roner · ⭐ 13
- **Fișier-dovadă:** `README.md`
- **Cost de transfer:** dependenta-noua

**Ce face:**

Pachet pip (pip install roner) peste modelul dumitrescustefan/bert-base-romanian-ner, antrenat pe RONECv2. Rezolvă singur împărțirea textelor lungi în ferestre suprapuse (suprapune ultimul sfert al ferestrei de 512 tokeni) și alinierea word-to-subword. Ieșirea per cuvânt conține tag, part-of-speech, start_char, end_char și un flag multi_word_entity care leagă cuvântul de precedentul, ca să poți distinge două entități multi-cuvânt consecutive. Are opțiunea named_persons_only, care folosește POS-ul de la Stanza ca să eticheteze PERSON doar substantivele proprii — necesară pentru că RONECv2 marchează ca PERSON și pronume sau substantive comune ('ea', 'fratele', 'doctorul').

**De ce ne-ar folosi:**

E singura piesă de NER românesc pe care am găsit-o împachetată ca bibliotecă, nu ca notebook de cercetare, și e făcută de autorul corpusului standard. Ne-ar da două lucruri deodată: entități pentru paginile de subiect (avem deja templates/subject.html și tests/test_entity_sections) și, mai important, interogări bune pentru căutarea de imagini — un nume propriu extras corect e exact intrarea pentru cascada Wikipedia din findings-ul anterior. Costul e real: transformers + torch + pachetul de date Stanza pentru română, descărcat la prima rulare. Atenție la capcana PERSON: dacă o adoptăm fără named_persons_only=True, vom 'extrage' pronume ca entități. Doar 13 stele — puțin, dar codul e mic și verificabil, iar modelul e pe HuggingFace.

<details><summary>Fragment verbatim</summary>

```
import roner
ner = roner.NER()

input_texts = ["George merge cu trenul Cluj - Timișoara de ora 6:20.", 
               "Grecia are capitala la Atena."]

output_texts = ner(input_texts)

for output_text in output_texts:
  print(f"Original text: {output_text['text']}")
  for word in output_text['words']:
    print(f"{word['text']:>20} = {word['tag']}")
```

</details>

## 49. YAKE — cuvinte-cheie fără corpus, cu stopwords românești

- **Repo:** https://github.com/INESCTEC/yake · ⭐ 1876
- **Fișier-dovadă:** `yake/core/yake.py`
- **Cost de transfer:** dependenta-noua

**Ce face:**

Extractor nesupervizat de cuvinte-cheie care nu are nevoie de corpus de antrenare, dicționar sau model: calculează trăsături statistice pe un singur document (poziție, frecvență, dispersie în context, apartenență la propoziții diferite) și scorează n-grame până la lungimea n. Constructorul primește lan (limba pentru stopwords), n (mărimea maximă a n-gramei), dedup_lim și dedup_func — deduplicarea între cuvinte-cheie similare se face cu SequenceMatcher, Jaro sau Levenshtein, ca să nu returneze 'ministrul finanțelor' și 'ministrul de finanțe' ca două rezultate. Există yake/core/StopwordsList/stopwords_ro.txt, cu diacritice, inclusiv formele vechi cu sedilă ('aceşti').

**De ce ne-ar folosi:**

Ne dă termeni de căutare pentru imagini și etichete de subiect fără niciun model neuronal — deci fără torch, spre deosebire de RoNER. Concret: din corpul articolului scoatem 3-5 n-grame, le dăm ca 'q' la Openverse și avem brusc mai multe încercări per articol în loc de una singură bazată pe titlu. ATENȚIE LICENȚĂ, verificat în fișierul LICENSE: e AGPL-3.0, nu MIT cum ar sugera 1876 de stele și PyPI. Pentru izz.ro, care e SSG (rulăm la build, publicăm HTML static, nu servim software prin rețea), interpretarea uzuală e că AGPL nu se declanșează, dar nu sunt jurist și asta trebuie decis explicit înainte, nu după. Dependența adăugată e jellyfish, mică.

<details><summary>Fragment verbatim</summary>

```
    def __init__(
        self,
        lan: str = "en",
        n: int = 3,
        dedup_lim: float = 0.9,
        dedup_func: str = "seqm",
        window_size: int = 1,
        top: int = 20,
        features: Optional[List[str]] = None,
        stopwords: Optional[Set[str]] = None,
        lemmatize: bool = False,
        lemma_aggregation: str = "min",
        lemmatizer: str = "spacy",
        **kwargs
    ):
```

</details>
