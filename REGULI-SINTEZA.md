# Reguli de sinteză — titluri și rezumate izz.ro

> Versiunea 1, 17 august 2026. Normează regulile împrăștiate azi în prompturile din
> `generator/process.py`. Document normativ: prompturile din cod trebuie să implementeze
> ce scrie aici, nu invers. **Nu s-a modificat niciun fișier de cod.**

## 0. Poziția editorială asumată

izz.ro **nu redă titlurile surselor**, ci le rescrie. Consecința, asumată explicit:
**răspunderea editorială pentru fiecare titlu și rezumat publicat pe izz.ro aparține izz.ro**,
nu publicației-sursă.

Verificarea făcută de sursă acoperă textul *ei*. Nu acoperă textul *nostru*: propoziția
comprimată de model n-a fost scrisă de sursă și n-a fost citită de un om la noi. Moștenim
verificarea intrării, niciodată pe cea a ieșirii. Toate regulile de mai jos derivă din asta.

**Baza normativă:** Codul Deontologic Unic al jurnalistului (Convenția Organizațiilor de
Media, 2009) · Regulamentul (UE) 2024/1689 (AI Act), art. 50 alin. (4) · lucrările din §8 ·
incidentele proprii IZZ-0168 și IZZ-0142 din registru.

---

## 1. Reguli pentru TITLU

### 1.1 Fidelitate față de esență
Titlul redă **punctul principal al articolului**, nu detaliul cel mai spectaculos din el.
Dacă articolul are un fapt central și unul secundar mai atrăgător, titlul îl ia pe cel central.

*De ce:* Ecker et al. (2014) au măsurat că un titlu care accentuează secundarul strică memoria
și raționamentul cititorului — iar efectul persistă chiar dacă textul de dedesubt e corect.
Articolul corect nu repară titlul deviat.

### 1.2 Informația grea la început
Primele **2-3 cuvinte** conțin subiectul real: cine sau ce. Nu se începe cu circumstanțial,
cu adverb, sau cu instituția care anunță dacă subiectul e altcineva.
- DA: „Primăria Cluj suspendă autorizațiile pentru…"
- NU: „După mai multe luni de dezbateri, Primăria Cluj suspendă…"

*De ce:* Nielsen Norman Group, pe urmărirea privirii — scanare în formă de F, primele unul-două
cuvinte duc aproape toată greutatea. **Regula asta înlocuiește orice plafon de caractere:
problema reală nu e lungimea, e ordinea.**

Se împacă cu principiul deja decis la IZZ-0158: *sursa spune de UNDE se scrie, titlul spune
DESPRE ce* — deci subiectul din titlu, nu proveniența.

### 1.3 Se înțelege singur, rupt de context
Titlul apare în card, în feed, în rezultatul de căutare — fără articol lângă el. Trebuie să
transmită faptul complet fără nimic altceva.

### 1.4 Interzis: momeala de anticipare
Fără construcții care promit o informație în loc s-o dea. Interzise explicit: „iată ce",
„ce a pățit", „motivul e", „nu o să-ți vină să crezi", „asta s-a întâmplat apoi", pronume
demonstrative fără referent („aceasta e decizia care…"), titlu-întrebare fără răspuns.

*De ce, cu partea incomodă spusă:* Blom & Hansen (2015) numesc tiparul „forward-reference" și
l-au găsit în 17% din 100.000 de titluri daneze. Kuiken et al. (2017), pe date reale de la
Blendle, au măsurat că **funcționează — crește clicurile**. Rămâne interzis oricum. E o alegere
asumată în cunoștință de cauză, nu o presupunere că n-ar merge.

### 1.5 Formă
Verb activ, prezent, un singur fapt. Se aruncă articolele unde nu strică înțelesul.
**6-16 cuvinte** țintă. `TITLE_MAX_WORDS` din `config.py` e plasa de siguranță, nu a doua țintă —
vezi §6.

### 1.6 Fără opinie, fără adjectiv evaluativ
„Scandalos", „incredibil", „dezastruos" nu apar în titlu decât în citat atribuit.

### 1.7 Anunțul fără corp: titlul nu se cosmetizează
Când sursa e un anunț oficial fără text (doar titlu, uneori un URL brut sau un nume de fișier),
modelul **nu are voie să compenseze** inventând un titlu care sună a știre. Fără material,
ieșirea e „titlu insuficient" și articolul nu se publică.

*De ce, și cum e rezolvat deja:* IZZ-0142 — 79 de anunțuri oficiale fără corp (69 cu text
substituent, 10 cu descrierea repetând titlul), măsurate pe `data/articles.json` la 4 august 2026.
Soluția e **implementată și livrată** (PR #131, varianta (b) aleasă de proprietar): predicatul
`anunt_oficial_fara_corp()` e folosit de **aceeași funcție** și în poarta de calitate și în
randare, ca să nu poată devia una de alta. Anunțul se publică drept **titlu + link**, cu insigna
`· Anunț oficial`, fără timp de citire și **fără teaser inventat**. Poarta e slăbită punctual
doar pe `processed_by == "official"` — adică exact pe articolele care nu ating deloc modelul.

Regula de față codifică **de ce** e așa, ca să nu fie desfăcută: la un anunț fără corp, modelul
nu are din ce să sintetizeze, deci orice text produs ar fi inventat. Cele 12 teste din
`tests/test_anunt_oficial_fara_teaser.py` pin-uiesc comportamentul, inclusiv regresia inversă —
un articol **ne**-oficial fără substanță trebuie să rămână nepublicat.

**De curățat (nu blochează nimic):** rândul IZZ-0142 din registru a rămas pe `blocat` deși
munca e livrată. Rândul stătut m-a trimis pe pistă greșită la 17 august 2026.

---

## 2. Reguli pentru REZUMAT / SINTEZĂ

### 2.1 Doar fapte din textul primit
Niciun fapt care nu apare în sursă. Dacă cine / unde / când lipsește din sursă, **lipsește și
din rezumat** — nu se inventează și nu se înlocuiește cu o formulare vagă care să pară completă.

### 2.2 Reformulare integrală
Zero propoziții copiate din original. *(Preexistent în cod, se păstrează.)*

### 2.3 Citatele: exact sau deloc
Un citat se reproduce **cuvânt cu cuvânt, între ghilimele, cu atribuire**, sau nu se reproduce
deloc. **Este interzisă parafrazarea unei declarații ca și cum ar fi citat.**

*De ce:* Codul deontologic cere citate exacte și, la citare parțială, obligația de a nu
distorsiona mesajul textului citat. Atenție: regula asta creează o excepție reală de la §2.2 —
un citat corect atribuit **nu** încalcă interdicția de a copia.

### 2.4 Interzis: declarația scoasă din context
Nu se publică o declarație ruptă de condiția care o califică. Dacă sursa scrie „X a spus că va
demisiona **dacă** ancheta confirmă acuzațiile", rezumatul nu poate spune „X a anunțat că
demisionează". *(Codul deontologic interzice explicit publicarea declarațiilor scoase din context.)*

### 2.5 Rezerva se păstrează — regula cu cel mai mare risc din document
Marcatorii de incertitudine din sursă **se transportă în rezumat**: „ar fi", „presupus",
„acuzat de", „potrivit unor surse", „neconfirmat oficial", „urmează să".

Comprimarea are o tendință mecanică să-i șteargă, fiindcă par cuvinte de umplutură. Nu sunt.
**„X este acuzat că ar fi delapidat" nu devine niciodată „X a delapidat".**

[INTERPRETARE — regulă derivată, nu citată dintr-o prevedere anume] Ștergerea rezervei
transformă o relatare corectă într-o afirmație de fapt pentru care izz.ro răspunde, cu
prezumția de nevinovăție în joc.

### 2.6 Atribuirea afirmațiilor contestate
Orice afirmație care nu e fapt stabilit se atribuie: „potrivit Primăriei", „susține partidul",
„afirmă reclamanții". *(Codul deontologic: separarea clară a opiniilor de informații; citarea
surselor oficiale.)*

### 2.7 Cifrele
Se transportă exact, cu unitatea și perioada lor. Nu se rotunjesc, nu se convertesc, nu devin
„aproape", „peste", „record". Dacă sursa dă un interval, rezumatul dă intervalul.

### 2.8 Sursele care se contrazic
La sinteza din mai multe surse: dacă sursele se contrazic pe un fapt, **contradicția se scrie**,
nu se alege una dintre variante. *(Preexistent pentru fluxul C, se extinde la tot.)*

### 2.9 Lungime
25-40 de cuvinte pentru rezumatul dintr-o sursă; 40-80 pentru sinteza din mai multe.
*(Preexistent, se păstrează.)*

---

## 3. Regula de siguranță: garda nu se uită niciodată la textul rescris

**Verificarea de conținut ostil se face pe textul SURSĂ, înainte de model. Niciodată pe ieșirea
modelului, și niciodată doar pe ea.**

*De ce, cu dovadă din proiect:* la incidentul IZZ-0168 (feed de primărie compromis care a
publicat warez pe izz.ro), **al 8-lea articol a avut titlul rescris curat de Gemini, a trecut
de garda de conținut și a fost prins abia de suprimarea sursei.** Modelul nu a detectat
conținutul ostil — l-a *spălat*, producând un titlu curat pentru un articol otrăvit.

Consecința pentru regulile de sinteză: rescrierea e o operațiune care **elimină semnalele de
alarmă**, deci nu poate sta niciodată în fața filtrului. Ordinea e obligatoriu: fetch → gardă
pe conținut brut → model → publicare.

---

## 4. Marcajul de conținut generat de AI

### 4.1 Temeiul
Regulamentul (UE) 2024/1689 (AI Act), **art. 50 alin. (4)**: cine folosește un sistem AI care
generează sau manipulează text **publicat în scopul informării publicului asupra unor chestiuni
de interes public** are obligația să dezvăluie că textul a fost generat sau manipulat artificial.

**Se aplică de la 2 august 2026. Este deja în vigoare.**

### 4.2 De ce izz.ro nu beneficiază de excepție
Art. 50(4) scutește de obligație textul care **a trecut printr-un proces de verificare umană
sau control editorial** ȘI pentru care **o persoană fizică sau juridică deține răspunderea
editorială**.

[INTERPRETARE] izz.ro îndeplinește a doua condiție (§0), **nu și pe prima**: pipeline-ul
generează și publică fără ca un om să citească fiecare titlu. Excepția cere ambele condiții.
**Deci marcarea nu e opțională pentru noi — e obligatorie.**

Ce ar schimba concluzia: verificare umană efectivă, articol cu articol, înainte de publicare.
La ~2.000 de titluri nu e realist.

### 4.3 Cum se marchează
- **Pictograma oficială UE.** Comisia Europeană, prin AI Office, a publicat pe 10 iunie 2026
  un set de **trei pictograme**, în Codul de Bune Practici privind transparența conținutului
  generat de AI. Fiecare în patru variante (negru, alb, ambele la 50% transparență), SVG și PNG.
  Libere de folosit, **fără atribuire** către Comisie.
  Descărcare: <https://digital-strategy.ec.europa.eu/en/policies/eu-icons-labelling-ai-generated-content>
  **Care din cele trei ni se potrivește nu e stabilit** — alegerea depinde de cât din conținut
  e responsabilitatea AI-ului, iar pagina cu pictogramele n-a fost deschisă încă. De făcut.
- **Pictograma singură nu ajunge.** Testarea cu utilizatori a arătat că funcționează doar
  însoțită de etichetă text. La noi: **„Titlu și rezumat generate automat"**.
- **Accesibilitate:** `alt` sau `aria-label` care spune că textul e generat automat. Nu se pune
  ca imagine decorativă.
- **Unde:** informarea trebuie făcută „în mod clar și distinct, cel târziu la momentul primei
  interacțiuni sau expuneri". Practic: **pe fiecare card, lângă titlu — nu o singură dată în
  subsol sau într-o pagină „Despre".** Cardul e prima expunere.

### 4.4 Ce NU marcăm, și de ce contează formularea
Faptele preluate **nu** sunt generate de AI: vin din surse verificate editorial de publicațiile
respective. Marcajul acoperă **formularea noastră**, nu conținutul factual. Eticheta trebuie să
spună exact asta — altfel sugerează că știrea însăși e fabricată, ceea ce ar fi neadevărat și
ne-ar strica singurul lucru care ne ține: credibilitatea.

### 4.5 Sursele care publică ele însele conținut generat de AI
Aceeași obligație li se aplică lor. Dacă o sursă marchează un articol ca generat automat,
marcajul **se propagă** la noi, distinct de al nostru: al lor acoperă faptele, al nostru
formularea. De verificat dacă vreo sursă din listă face deja asta.

---

## 5. Corectarea erorilor

Codul deontologic impune corectarea promptă a erorilor semnificative. În lipsa unui om care
citește totul înainte de publicare, procesul de după:
1. Orice sesizare pe un titlu sau rezumat se tratează în maximum 24 de ore.
2. Corectura se face **vizibil**, nu prin înlocuire tăcută: rămâne mențiunea că textul a fost
   corectat și când.
3. Dacă eroarea vine din compresie (nu din sursă), se identifică regula din §1-§2 care a cedat
   și se completează — altfel se repetă pe alte 2.000 de titluri.

---

## 6. Raportul dintre 6-16 și `TITLE_MAX_WORDS` — DECIS 2026-08-29

Cele două numere nu se contrazic; sunt straturi diferite, și de-acum scrise ca atare:

- **6-16 cuvinte = ținta cerută modelului** în prompturile din `generator/process.py`. E regula
  editorială din §1.5 și rămâne singura cifră pe care o urmărește un om când judecă un titlu.
- **`TITLE_MAX_WORDS = 22` (`generator/config.py`) = plasa de siguranță**, nu o a doua țintă.
  Nu cere modelului nimic; taie doar titlurile care scapă mult peste țintă, ca să nu ajungă în
  output ceva nelizibil pe mobil. Un titlu de 18 cuvinte trece de plasă, dar rămâne în afara
  țintei — și asta e intenționat, fiindcă alternativa e să respingi conținut bun pentru un cuvânt.

Ridicarea sau coborârea plasei se face în `config.py`, nu aici; textul ăsta nu repetă valoarea,
tocmai ca să nu rămână în urmă cum a rămas trimiterea veche la `config.py:230` (linia reală era
`:306` când a fost verificată pe 2026-08-29).

---

## 7. Ce NU rezolvă documentul ăsta

- **Nu înlocuiește verificarea umană.** Regulile fac compresia mai puțin riscantă; nu o fac sigură.
- **Nu acoperă selecția.** Ce știre intră și ce știre nu intră e decizie editorială separată.
- **Nu acoperă imaginile.** Codul deontologic pune fotografiile în aceeași frază cu titlurile
  („nu trebuie să inducă în eroare"), iar `covers.py` generează vizualuri. Zonă neacoperită.
- **Nu schimbă nimic la anunțurile oficiale.** §1.7 doar scrie motivul unei soluții deja livrate
  (PR #131). Singura acțiune rămasă acolo e igienă de registru.

---

## 8. Surse

| Sursă | Ce susține | Cum a fost citită |
|---|---|---|
| Ecker, Lewandowsky, Chang & Pillai (2014), *J. Exp. Psychol. Appl.* 20, 323-335 | §1.1 | rezumat de căutare |
| Blom & Hansen (2015), *J. of Pragmatics* 76, 87-100 | §1.4 | rezumat de căutare |
| Kuiken, Schuth, Spitters & Marx (2017), *Digital Journalism* 5(10), 1300-1314 | §1.4 | rezumat de căutare |
| Nielsen Norman Group — microcontent, „First 2 Words" | §1.2 | rezumat de căutare |
| Center for Media Engagement — *The Current State of News Headlines* | §1 (absența unei reguli de lungime) | **citit integral** |
| Codul Deontologic Unic (COM, 2009) | §1.1, §2.3, §2.4, §2.6, §5 | rezumat de căutare |
| Regulament (UE) 2024/1689 art. 50(4) + Cod de Bune Practici / pictograme | §4 | rezumat de căutare + pagina CE citită parțial |
| Registru intern: IZZ-0142, IZZ-0158, IZZ-0168 | §1.2, §1.7, §3 | **citit integral, sursă primară** |

**Avertisment de fiabilitate:** în afara registrului intern și a unei singure pagini, sursele
au fost citite prin rezumat automat, nu în original. Bibliografia e coroborată din rezultate
independente; redarea concluziilor trece printr-un strat de parafrază necontrolat.
**Înainte ca documentul să devină norma permanentă a redacției, textele primare — în special
Codul Deontologic Unic și art. 50 din AI Act — trebuie citite direct.**
