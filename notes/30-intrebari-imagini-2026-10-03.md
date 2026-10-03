# Cele mai inteligente 30 de întrebări despre imagini (sau lipsa lor) pe izz.ro

> **Ce e fișierul ăsta:** un instrument de interogare, nu un plan. 30 de întrebări pe care
> le-ar pune cineva care construiește site-uri *și* se îndoiește de ele. Fiecare întrebare
> atacă o presupunere, cere o dovadă sau scoate la iveală un cost ascuns. Nu toate au răspuns
> azi — exact asta le face utile.
>
> **De ce imaginile:** `REGULI-SINTEZA.md §7` scrie chiar el că documentul „nu acoperă
> imaginile" și că e „zonă neacoperită". Codul deontologic pune fotografiile în aceeași frază
> cu titlurile („să nu inducă în eroare"), deci întrebările de mai jos nu sunt cosmetice.

## Cum e construită lista

Șase lentile, fiecare cu câte o întrebare care nu se poate rezolva prin intuiție:

| Lentilă | Ce verifică |
|---|---|
| A. Rolul imaginii | De ce există un pixel pe pagină — și cui promite ce |
| B. Absența | Ce face site-ul când nu are ce arăta (cazul cel mai des uitat) |
| C. Drepturi & etică | Cine răspunde, cu ce dovadă, peste cât timp |
| D. Tehnic & performanță | Costul real în octeți, secunde și CLS |
| E. SEO & distribuție | Ce văd roboții și previzualizările sociale |
| F. Sistem & măsurare | Cine deține problema și cum se observă că s-a stricat |

---

## A. Rolul imaginii — de ce există

**1.** Ce promite imaginea cititorului în primele 200 ms, înainte să citească titlul — și se
ține promisiunea la fel pe *sinteză*, *rezumat* și *anunț oficial*?
*Răspuns bun:* o propoziție, nu un slogan. Dacă promisiunea diferă pe cele trei tipuri, atunci
avem nevoie de trei tratamente vizuale, nu de una singură.

**2.** Dacă o copertă generată e „ilustrativă, nu fotografie a evenimentului", din ce moment
exact o află cititorul — fără să deschidă politica imaginilor, unde nimeni nu ajunge?
*Răspuns bun:* disclosure la prima expunere, nu în subsol. „Ilustrație" e o informație despre
imagine, la fel cum „generat automat" e o informație despre text.

**3.** Care e testul care prinde o imagine *în sine* corectă, dar care, lângă titlu, sugerează un
fapt pe care articolul nu îl susține?
*Răspuns bun:* un test corespondent regulii de titluri — poza nu are voie să afirme singură un
rezultat, o vină sau o identitate. `photojudge.py` e precedenta: aceeași gândire, extinsă.

**4.** Am măsurat vreodată ce câștigă un articol cu fotografie reală față de o copertă generată —
pe cohorte, nu pe impresii — în CTR, timp pe pagină și reveniri?
*Răspuns bun:* un număr, cu interval de încredere. Fără el, decizia „merită o poză reală aici?"
e luată de gust, iar gustul nu se poate apăra în fața unui avocat.

**5.** Care e ipoteza noastră explicită despre rolul imaginii — ilustrare, ancoră de memorie sau
promisiune de subiect?
*Răspuns bun:* alegerea e scrisă, fiindcă din ea decurg toate celelalte 29 de răspunsuri.
O ipoteză nescrisă se contrazice singură pe la întrebarea 11.

---

## B. Absența imaginii — cazul cel mai des ignorat

**6.** Care e varianta corectă când nu există imagine adevărată: copertă tipografică, spațiu gol
sau alt tip de artefact (hartă, cronologie, cifre)? Ce *criteriu*, nu ce preferință, decide?
*Răspuns bun:* criteriul e tipul de informație, nu bugetul. O știre despre bani cere cifre, una
de proximitate cere hartă; restul primesc tipografie.

**7.** Câte pagini ajung fără un `og:image` funcțional — și știm ce vede atunci WhatsApp, LinkedIn,
un cititor de ecran sau un crawler: nimic, o imagine de site sau un pătrat gol?
*Răspuns bun:* procentul e măsurat, iar fallback-ul e testat explicit, nu presupus din valoarea
implicită din `base.html`.

**8.** Când randarea unei coperte cade (Chromium dispărut din CI, font lipsă, timeout, cotă),
degradarea e onestă sau tăcută — și cine vede primul?
*Răspuns bun:* un fallback determinist (Pillow → generic de categorie → nimic) *și* un semnal.
O degradare fără semnal e un bug care așteaptă să fie descoperit de cititor.

**9.** `alt=""` pe card e o decizie semantică luată de cineva sau un default moștenit? Cine
răspunde de diferența dintre „decorativ" și „nedescris"?
*Răspuns bun:* fiecare `alt=""` are un motiv scris (ex. link-ul are deja text accesibil), iar
`alt`-ul de pe pagina de articol spune ce e imaginea, nu doar al cui e creditul.

**10.** Dacă un articol nu are voie legal la fotografie, dar subiectul e important, ce formă
vizuală alternativă îi dai fără să fabrice un fapt — și cine aprobă ruta?
*Răspuns bun:* formele alternative sunt enumerate în §18 lângă interdicție. Interdicția fără
alternativă produce articole importante deliberate fără niciun vizual.

---

## C. Drepturi & etică — cine răspunde și cu ce dovadă

**11.** Care e regula într-o singură propoziție: ce licență are voie pe card / hero / `og:image`
față de pagina de articol — și e implementată ca *poartă în cod*, nu ca obicei de redacție?
*Răspuns bun:* da (PD/CC0 în zonele fără legendă; CC BY doar cu credit complet lângă imagine),
iar garda are test negativ — nu doar că trece ce e permis, ci că pică ce nu e.

**12.** Cine aprobă o fotografie cu persoană identificabilă în context sensibil (minor, victimă,
situație medicală) — și cum arată dovada peste doi ani, când persoana care a aprobat nu mai e
în echipă?
*Răspuns bun:* un dosar de decizie (cine, când, pe ce temei), nu aprobarea din firul de
discuție. Regula „om în buclă" fără dovada buclei e o intenție, nu un control.

**13.** Când „licență liberă" e incertă, autorul e probabil greșit sau lipsește data verificării,
ce prevalează: viteza sau poarta? Există criteriul scris, sau fiecare sesiune îl reinventează?
*Răspuns bun:* scris și aplicat automat. Incertitudinea pe un drept nu se rotunjește niciodată
în favoarea publicării — la fel ca la `photojudge`, unde dubiul ⇒ respinge.

**14.** Cum dovedim că fotografia unei localități e chiar localitatea din județul cerut, nu un
omonim — și ce se întâmplă dacă poza e frumoasă dar greșită?
*Răspuns bun:* potrivirea pe județ e obligatorie și testată (fără fallback pe alt județ), iar
legenda spune că e ilustrație de localitate, nu document al evenimentului.

**15.** Takedown-ul pe o imagine: cine răspunde în 24h și se propagă ștergerea în `cover`, `webp`,
cache CDN, sitemap, `og:image` și feed — sau rămâne o copie orfană pe undeva?
*Răspuns bun:* un singur lanț de ștergere, verificat cap-coadă. O imagine „ștearsă" care
supraviețuiește în cache e cea mai proastă formă a răspunsului „da".

---

## D. Tehnic & performanță — costul în octeți, secunde și CLS

**16.** Care e bugetul de octeți pentru imagini per pagină, cine îl apără în CI — și ce se
întâmplă concret când un articol îl sparge?
*Răspuns bun:* cifra e în bugetul de greutate (dimensiunea 5), iar depășirea produce un
avertisment măsurabil, nu o discuție. Alternativ: o excepție documentată, cu motiv.

**17.** Imaginea principală e LCP sau nu — și `fetchpriority`/`loading` fac exact ce credem pe 4G
real, nu pe simulare de birou?
*Răspuns bun:* măsurat pe teren (CrUX / WebPageTest mobile), cu ipoteza „hero-ul e LCP" fie
confirmată, fie infirmată. `fetchpriority="high"` pe o poză greșită doar înrăutățește.

**18.** WebP e răspunsul sau doar reflexul? În ce caz JPEG (sau AVIF) câștigă — și alegerea se
face la build sau la request?
*Răspuns bun:* dovadă pe corpusul propriu de coperți, nu pe benchmark-uri generale. Formatul e
un cost de mentenanță: fiecare variantă în plus trebuie justificată.

**19.** Toate zonele (card, hero, portret, hartă, og) au dimensiuni intrinseci declarate, astfel
încât CLS să fie zero — inclusiv pe breakpoint-urile neacoperite azi de `sizes`?
*Răspuns bun:* verificat cu măsurători, nu prin simpla prezență a atributelor. Atribute
greșite sunt mai rele decât absente.

**20.** Cache-ul: hash de conținut, TTL, invalidare la re-render — cum arată un cold start pe un
articol abia publicat și cât de des plătim regenerarea a 11.000 de coperți?
*Răspuns bun:* invalidarea e legată de conținut, costul regenerării e cunoscut în minute, iar
articolul proaspăt nu are niciodată un al doilea `og:image` diferit de cel din pagină.

**21.** Care e cea mai fragilă verigă din lanțul sursă → build → CDN → browser, și ce am tăia
conștient dacă ar trebui să supraviețuim șase luni fără ea?
*Răspuns bun:* un nume, nu o categorie. Fragilitatea neidentificată e cea care alege singură
momentul să se manifeste.

---

## E. SEO & distribuție — ce văd roboții și previzualizările

**22.** `og:image` e per articol sau cade pe imaginea generică mai des decât ne imaginăm — și cum
arată cardul social în fiecare caz?
*Răspuns bun:* procentul de fallback e cunoscut și e mic pentru articolele proaspete; cardul
social e verificat vizual pe cel puțin un canal care refolosește imaginea (WhatsApp).

**23.** Ce imagini intră în `sitemap-images.xml` și în schema.org — toate, doar cele reale, doar
cele marcate — și e o decizie sau un efect secundar al codului?
*Răspuns bun:* decizie scrisă. Marcaj, nu deducere din URL; ce nu e în sitemap nu trebuie să
fie o scăpare, ci o alegere.

**24.** `alt`-ul e pentru om sau pentru robot? Cum formulezi `alt`-ul unei coperți tipografice
generate, încât să fie util unui nevăzător fără să pretindă că e fotografie?
*Răspuns bun:* o formulă consistentă, testată pe câteva exemple („Ilustrație tipografică pentru
articolul X"), nu un text gol repetat pe mii de pagini.

**25.** Cât de des două articole primesc aceeași imagine (hash, seed, fallback de categorie) — și
cine măsoară coliziunile pe arhivă?
*Răspuns bun:* o măsurătoare pe arhivă, nu o presupunere că hash-ul rezolvă totul. Coperțile
identice pe subiecte diferite erodează exact încrederea pe care imaginea ar trebui să o construiască.

**26.** Feed-ul RSS și agregatele terțe au nevoie de imagini? Ce pierdem fără ele și ce riscăm cu
ele (hotlink, licență, control al afișării)?
*Răspuns bun:* decizie explicită pe categorii de imagini, nu „ce iese din template". O poză
reală scursă într-un agregat fără legendă e un incident de licență, nu o problemă de design.

---

## F. Sistem & măsurare — cine deține problema

**27.** Care e metrica de sănătate a imaginilor: % articole cu imagine, reală vs generată,
greutate mediană, 404, timp de randare, CTR social — și care prag declanșează o decizie?
*Răspuns bun:* un tablou mic de indicatori, cu praguri care chiar provoacă o acțiune. Un
dashboard pe care nimeni nu acționează e decor.

**28.** Cine e proprietarul imaginii ca sistem: o persoană, un test, un tool? Ce se întâmplă dacă
nimeni nu mai atinge `covers.py` un an?
*Răspuns bun:* un test care pică atunci când contractul se rupe (font lipsă, dimensiune greșită,
poartă de licență ocolită). Codul fără proprietar moare tăcut; testul e forma cea mai ieftină
de proprietar.

**29.** Ce imagini din arhivă au îmbătrânit prost (licență re-evaluată, entitate redenumită, poză
retrasă de autor) — ai proces de *re*-verificare, nu doar de verificare la intrare?
*Răspuns bun:* o re-verificare periodică pe eșantion sau pe evenimente (takedown, schimbare de
licență). Poarta de la intrare nu apără de ce se schimbă după.

**30.** Care e întrebarea pe care ne-o punem greșit despre imagini — și dacă am răspunde corect
la ea, ce am schimba săptămâna viitoare?
*Răspuns bun:* o schimbare concretă, mică, cu termen. Lista asta nu valorează nimic dacă
răspunsul rămâne o listă.

---

## Notă de ancorare (măsurat azi, 2026-10-03)

- `content/legal/images.md` — poarta PD/CC0 pentru suprafețele fără legendă (card/hero/og) și
  creditul complet doar lângă imagine; `tests/test_image_policy.py` apără regula, inclusiv pe
  cazurile negative.
- `generator/htmlart.py` — coperțile se compun din tipografie și geometrie, randate cu Chromium
  în CI; `generator/covers.py` e fallback-ul Pillow. Ambele explică în docstring *de ce* arată
  așa — precedentele bune pentru „răspuns bun" de la întrebările 8, 18 și 28.
- `generator/photojudge.py` — judecătorul AI al potrivirii poză↔articol, cu fail-safe: dubiul
  înseamnă „fără poză". Modelul de urmat pentru întrebarea 3.
- `data/leadphotos.json` — 11.653 de înregistrări, 275 utilizabile; `data/articles.json` — 11.792
  articole. Raportul ăsta e întrebarea 27 în formă brută.
- `generator/render.py` — `og_image` per articol, `sitemap-images.xml`, `digitalSourceType`,
  credit de licență pe pagina de articol; `specs/locality-lead-photos.md` fixează regulile P18.
- `.claude/reguli/18-imagini.md` — fotografiile instituțiilor nu sunt libere fiindcă sunt
  publice; trei căi verificate și consemnate, altfel articolul își păstrează coperta generată.
