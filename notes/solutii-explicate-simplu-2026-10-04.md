# Soluțiile, explicate simplu

> Analiza tehnică e în `notes/analiza-audit-extern-2026-10-04.md` (ce e adevărat și ce e fals
> din auditul extern). Aici e partea pe care n-am explicat-o bine prima dată: **ce facem
> concret, la fiecare punct, și de ce**.
>
> Regula documentului: zero termeni tehnici neexplicați. Fiecare propunere are:
> ce problemă rezolvă în viața reală → ce schimbăm → înainte/după → cât durează → cum se vede că a mers.

---

## 1. Pe scurt, în patru propoziții

- Site-ul nu are nevoie de „mai multe poze" sau de „încă un banner" — are nevoie de **lucruri mărunte de încredere**, pe care le pot face eu singur.
- Una singură cere o acțiune de la tine (5 minute): **o comandă pe site-ul live**, fiindcă din sandboxul în care lucrez internetul e blocat.
- Ce e greu nu e codul: e ce se adaugă **peste** cod — **un e-mail pe zi (newsletter)** și **un text pe zi scris de om**. Doar ele transformă un „site de rezumate" în ceva ce oamenii urmăresc pe nume.
- Restul sunt decizii de bani, de buget de fișiere și de imagine editorială — ale tale, nu ale mele.

---

## 2. Grupa A — le pot face eu, fără nicio decizie de la tine

### A1. Garda de diacritice („romanesc" → „românesc")

**Problema, în viață reală.** Uneori robotul scrie așa, pe site:

> „Afacerile unui brand romanesc de cosmetice pe baza de apa termala au crescut semnificativ"

Informația e corectă, dar orice cititor român vede imediat text scris pe repede-înainte. Pe un
site de știri, asta costă încredere. Se întâmplă la ~13 articole pe zi (1,7%).

**Ce schimbăm.** Chiar în locul unde textul vine de la AI, punem o verificare simplă: dacă
titlul și rezumatul n-au **niciun** semn diacritic (ă â î ș ț) deși textul original le are,
pipeline-ul cere o dată reformularea. Dacă tot vin fără, articolul nu se publică. În plus,
raportul de calitate care rulează la fiecare build afișează câte astfel de texte au apărut.

**Înainte → după**

| | Text |
|---|---|
| Azi | Afacerile unui brand **romanesc** de cosmetice pe baza de **apa termala** au crescut semnificativ |
| După | Afacerile unui brand **românesc** de cosmetice pe **bază** de **apă termală** au crescut semnificativ |

**Cât durează:** 2–3 ore de lucru pentru mine. Nu depinde de nimeni.
**Cum știm că a mers:** raportul de calitate arată 0 în loc de 13/747.

### A2. „Cine răspunde pentru ce scrie site-ul?" — semnătura

**Problema, în viață reală.** Site-ul are nouă pagini publice de transparență care explică *cum* se produce textul, dar
nicăieri nu scrie **cine răspunde** pentru el. Pentru un cititor atent (și pentru Google), un
site care spune „generat automat" dar nu spune „răspunde redacția X, la adresa Y" e un site
anonim. Iar Google are reguli speciale exact pentru site-urile anonime care produc text în masă.

**Ce schimbăm — trei lucruri mărunte:**

1. **În „cartea de vizită" tehnică** pe care site-ul o livrează motoarelor de căutare, adăugăm
   două rânduri care trimit la regulile de publicare și la politica de corecții. (Astea se
   numesc, în limbajul lor, `publishingPrinciples` și `correctionsPolicy` — sunt doar două
   adrese.)
2. **Pe pagina `/despre/`**, un paragraf nou: „Cine răspunde editorial" + adresa de contact.
3. **Sub fiecare articol**, o linie vizibilă:

   > Răspunde editorial: Redacția IZZ.ro · Raportează o eroare

   Nu inventăm un autor-personalitate cu nume și față. „Redacția IZZ.ro" e cinstit, verificabil
   și exact ce recomandă bunul simț (nu marketingul).

**Cât durează:** 2 ore. **Cum știm că a mers:** oricine — cititor sau validator automat — poate
răspunde la întrebarea „cine răspunde de textul ăsta?" fără să caute prin zece pagini.

### A3. Documentele de stare să spună adevărul

**Problema.** Fișierul de stare al proiectului încă scrie „PWA — PR deschis, fără merge", dar
codul e pe `main` din 4 octombrie. Cine citește starea rămâne în urmă față de realitate.

**Ce schimbăm:** două rânduri corectate + o linie în registrul de decizii despre analiza asta.
**15 minute.**

### A4. Link static „Setări consimțământ" în subsol

**Problema.** Azi, cine vrea să-și retragă acceptul pentru statistici trebuie să știe că există
un buton „◎" (doar un simbol, fără text) și să apese pe el. Legal e în regulă — retragerea
există — dar e greu de găsit fără să știi unde să cauți.

**Ce schimbăm:** un link text în subsolul oricărei pagini: **„Setări consimțământ"** → pagina de
confidențialitate. Nimic de întreținut, nimic care să încarce pagina.
**20 de minute.**

---

## 3. Grupa B — o singură acțiune de la tine (5 minute)

### B1. Un test pe site-ul live (nu se poate din sandbox)

**De ce nu pot eu.** În mediul în care lucrez, internetul de ieșire e blocat: am încercat
`curl https://izz.ro/` și nu răspunde deloc. Nu e o problemă a site-ului, e a sandboxului —
de aceea tot raportul meu zice „verificat local", nu „confirmat pe live".

**Ce e de verificat și de ce contează.** Browserul decide dacă îți oferă butonul „Instalează
aplicația" pe baza unui fișier numit *manifest*. Serverul trebuie să spună browserului **ce fel
de fișier e**; dacă răspunde „fișier oarecare" în loc de „manifest", browserul îl ignoră — fără
nicio eroare vizibilă, instalarea pur și simplu nu merge. Un audit a spus că manifestul
lipsește; în cod el există, e complet și testat automat. Rămâne de văzut **cum îl servește
serverul live**.

**Ce faci tu** (sau orice sesiune care are internet) — o comandă, ne uităm împreună la răspuns:

```shell
curl -sI "https://izz.ro/static/site.webmanifest?cb=$(date +%s)" | grep -i content-type
```

- iese `application/manifest+json` → **gata, PWA e în regulă**, punctul din audit e închis;
- iese altceva → e o linie de configurat la gazdă, 5 minute pentru mine.

---

## 4. Grupa C — ce cere un obicei nou, nu cod

### C1. Un e-mail pe zi: newsletter-ul

**Ce e azi.** Un cititor nu are cum să te urmărească. Dacă nu nimerește din nou site-ul, te-a
pierdut. Peste o mie de știri pe zi pleacă spre nimeni. Și e mai rău: pagina de contact promite
„abonează-te din formularul de pe pagina principală", dar **formularul nu există** — locul lui e
pregătit în cod, lipsește doar codul furnizorului.

**Ce schimbăm.** Un formular simplu pe prima pagină:

> **Un e-mail pe zi.** Ce contează, pe scurt, cu linkuri. Te dezabonezi într-un click.

Furnizorul propus (Brevo) are plan gratuit, dă un cod de lipit în site și se ocupă el de
confirmarea dublei înscrieri (cerută de lege).

**De ce e important.** E singurul canal care rămâne **al tău**: nu depinde de Google, nu depinde
de Facebook. 300 de oameni care te citesc în fiecare dimineață valorează mai mult decât 30.000
de vizitatori din căutări, pentru că revin singuri — și pot deveni susținători sau public pentru
un sponsor.

**Ce am nevoie de la tine:** un cont Brevo (gratuit) și codul de embed — 5 minute.
La mine: o oră.

### C2. Un text pe zi scris de om („editorialul de dimineață")

**Ce e azi.** Practic tot ce e pe site e scris de robot. E corect, e onest — dar exact acesta
e tipul de conținut pe care Google l-a declarat riscant în 2024: text produs în masă, fără autor
și fără valoare adăugată umană.

**Ce propun.** Un singur text pe zi — 300–500 de cuvinte — scris sau măcar finalizat de tine,
marcat clar:

> **Editorial** · Scris de redacție · Spre deosebire de știrile de mai jos, care sunt sintetizate automat.

Ce poate conține: ce s-a întâmplat azi în trei fraze, de ce contează, ce urmărești mâine.
Nu trebuie să fie literatură — trebuie să fie al tău.

**De ce contează, concret:**
1. e exact lucrul pe care un concurent **nu** îl poate copia într-o oră (restul site-ului poate fi clonat în weekend);
2. Google tratează diferit un site unde se vede judecata unui om;
3. oamenii se abonează la o voce, nu la un flux.

**Cost:** 30–45 de minute din timpul tău, pe zi. Tehnic: ~1 oră de pregătit locul în pagină.

---

## 5. Grupa D — ce cere o decizie de la tine

### D1. Imaginea de share: mii de articole arată identic

**Problema, în viață reală.** Când cineva dă un articol pe WhatsApp sau Facebook, se vede o
imagine. Azi, ~87% din articole folosesc **aceeași** copertă de categorie — mii de articole
arată la fel în feed. Oamenii dau mai puțin click, deși textul e bun.

**De ce nu e simplu.** Site-ul are un plafon de fișiere al gazdei (20.000 pe versiune; noi
folosim 13.480 din bugetul intern de 17.000). Tocmai de aceea ilustrațiile se desenează în
pagină, nu ca fișiere. Dacă am face imagine pentru toate cele ~9.500 de articole, **spargem
deploy-ul**.

**Varianta care încape, cu margini:** imagine proprie doar pentru articolele zilei care merită
(titlul principal, cele promovate, sintezele multi-sursă) — ~30–60 pe zi, adică 400–700 de
fișiere în fereastra de 12 zile. Încape.

**Decizia ta:** doar pe acest subset, sau amânăm?

### D2. Mai multă sinteză din mai multe surse (azi 6%)

**Ce e azi:** din 747 de articole în ultimele 24 de ore, doar 45 combină mai multe publicații. Restul sunt
rezumate dintr-o singură sursă — deci promisiunea brandului („un subiect, toate sursele") se
vede rar.

**De ce nu e simplu:** înseamnă reglat gruparea articolelor care vorbesc despre același eveniment.
Prea agresiv = lipești știri diferite între ele, mai rău decât acum. De aceea zona e marcată
„protejată" în proiect: se schimbă numai cu probă pe date reale, înainte și după.

**Decizia ta:** vrei să pregătesc doar **proba** (nu schimbarea) și să-ți arăt: câte articole
s-ar putea uni, cu exemple — inclusiv exemple greșite?

### D3. Banii

**Ce e azi:** zero venituri, zero reclame. Costurile (AI + găzduire) există.

**Opțiuni, pe scurt:**
- **sponsorizări locale, marcate clar** („sponsorizat de X") — se potrivește cu nișa județeană;
- **abonați susținători** — mică sumă lunară, fără reclame (promisiunea „zero zgomot" rămâne intactă);
- **vânzarea de analiză/date** — discuția din issue #271 (IZZ Intelligence).

Fiecare cere o regulă clară de separare între editorial și comercial. Regula o stabilești tu —
de aceea e decizia ta, nu a mea.

### D4. Fotografii doar pe verticalele cu trafic

**Ce e azi:** imaginile sunt desene proprii (zero drepturi de autor de plătit). Fotografii reale
avem doar pentru câteva persoane publice, din arhive libere.

**Ce propun:** fotografii libere (domeniu public / licență deschisă) **doar** pentru rubricile
cu trafic (ex. Local, Sport) — nu pentru tot volumul. Fiecare imagine înseamnă și un fișier
consumat, și un risc de atribuire greșită.

### D5. O rubrică fără știri să nu mai apară

**Ce e azi:** rubrici ca „Inteligență artificială" pot fi listate (în navigare, pe pagina de
secțiuni) chiar dacă n-au nicio știre proaspătă. Cititorul intră și găsește puțin sau nimic.

**Ce propun:** pe prima pagină, o rubrică apare doar dacă are cel puțin **3 știri în ultimele
72 de ore**. Simplu de implementat, dar schimbă ce vede primul vizitator — deci întreb.

---

## 6. Ce NU facem (și de ce)

- **Nu punem a doua bară de cookie-uri.** Există una, e corectă și blochează statisticile până
  când accepți. A doua bară strică pagina fără să adauge nimic.
- **Nu creăm un fișier „manifest.json" doar ca să tacă un tool.** Întâi măsurăm (B1); dacă
  serverul livrează corect manifestul care există, n-avem ce repara.
- **Nu punem descrieri lungi la imaginile decorative.** Pentru cine folosește un cititor de
  ecran, ar însemna aceeași informație repetată de zeci de ori pe pagină.
- **Nu ascundem articolele de Google ca să scăpăm de risc.** Ascuns nu aduce niciun cititor;
  editorialele + newsletter-ul aduc.
- **Nu ne jucăm cu ora la care rulează pipeline-ul** și nu relaxăm gruparea fără probă — sunt
  deja documente în proiect care arată de ce nu ajută.

---

## 7. Întrebarea mea, pe scurt

Pot începe **chiar acum, fără nicio decizie de la tine**, cu **A1 + A2 + A3** (diacriticele,
semnătura editorială, starea reală din documente) — vreo 5 ore de lucru pe branch-ul acesta.
Le livrez una câte una, fiecare cu verificarea ei. A4 vine în aceeași tranșă (20 de minute).

Ce am nevoie de la tine, în ordinea importanței:

1. **„da, începe"** pentru A1–A4 — nu costă nimic și nu schimbă nimic vizibil în rău;
2. **comanda de la B1** (5 minute, oriunde ai internet) — închide întrebarea PWA din audit;
3. **un cont Brevo** (5 minute) — pornim newsletter-ul, singurul canal care rămâne al tău;
4. și abia apoi deciziile de la D (imagini, sinteză, bani, prag pe rubrici).
