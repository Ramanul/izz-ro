# Sinteza produce clickbait fluent când sursa nu trimite fapte

**Raportat de Alexandru, 2026-08-04**, cu un exemplu de pe live: titlul „Gestul neobișnuit al unui
portar în minutul 90+3 a uimit asistența" și teaserul „Finalul meciului disputat la scorul de 2-2 a
fost marcat de un moment neobișnuit și spectaculos al portarului…". Nu spun **cine**, **ce meci**,
**ce gest**. E exact contrariul lui „Zero Zgomot".

## Diagnostic — e în DATE *și* în COD, iar cele două se compun

### 1. DATE: sursa nu trimite nimic de sintetizat

Itemul, luat prin `fetch._fetch_one_guarded('digisport', …)`:

```
title       = ”Sigur nu ai mai văzut așa ceva!” Toată lumea a rămas ”mască”, după gestul
              portarului la 2-2, în minutul 90+3
description = ”Sigur nu ai mai văzut așa ceva!” Toată lumea a rămas ”mască”, după gestul
              portarului la 2-2, în minutul 90+3
```

`description` e **identic** cu titlul. Nu există corp de text. Modelul nu avea de unde ști numele
portarului sau meciul — deci nu a halucinat, a parafrazat. Comportamentul e corect **pentru intrarea
primită**; greșeala e că itemul a fost publicat.

**Amploarea, măsurată** (`fetch_all()`, 256 de iteme, 32 de surse, 2026-08-04):

| cuvinte pe care descrierea le ADAUGĂ față de titlu | iteme |
|---|---:|
| 0 (descriere goală sau identică) | 56 |
| 1–4 | 2 |
| 5–9 | 17 |
| **10+ (are substanță)** | **181** |

**58 din 256 (23%) sosesc cu 0–4 cuvinte noi — imposibil de sintetizat.**

Șase surse sunt **100%** așa: `digisport`, `monitorulsv`, `piataauto`,
`pl_arad_oras_pancota`, `pl_caras_severin_oras_oravita`, `pl_vrancea_municipiul_focsani`.
Pe corpusul publicat: **62 de articole din 2130** vin de la astfel de surse (digisport 52,
piataauto 10).

> Prima măsurătoare a dat 44%, cu o regulă greșită („descrierea e conținută în titlu"), care marca
> drept goale și rezumatele care *încep* cu titlul și apoi adaugă fapte. Cifra bună e 23%.
> Avertisment de metodă: a doua rulare a prins cache-ul cald, deci a văzut 32 de surse, nu 59 —
> procentele sunt reprezentative, dar eșantioanele diferă.

**`monitorulsv` merită numit separat: nu poate fi reparat.** Intră prin `type: sitemap_news`, iar un
sitemap de știri poartă titluri și date, nu descrieri. Sursa a fost adăugată de mine ieri (#129)
după ce am verificat că *întoarce iteme* — nu că itemele *conțin ceva*. **„Feedul răspunde" nu e
același lucru cu „feedul are conținut", și lotul de ieri n-a fost verificat pe a doua condiție.**

### 2. COD, prompt: `generator/process.py:27` cere explicit fabricarea

Regula finală din `USER_B`:

> „…**dacă descrierea e săracă, extrage esența din titlul original** (tot reformulat)."

Iar linia 22, în același prompt, cere „*fără clickbait, fără formulări vagi precum 'iată ce'*".
Când singura intrare e un titlu clickbait, cele două instrucțiuni **se exclud reciproc** și modelul
nu are ieșire: i se cere să producă, și i se interzice singurul lucru pe care l-ar putea produce.
Nu există nicio portiță de refuz — promptul nu-i permite să întoarcă „insuficient".

### 3. COD, poartă: `generator/select.py::_quality_gate` verifică forma, nu substanța

Poarta cere: titlu nevid · corp nevid · corp ≠ placeholder · **corp ≠ titlu** · sursă · nu
`fallback` · titlu netrunchiat. **Toate se uită la IEȘIRE.** Aici `description == title` la
*intrare*, dar AI-ul a scris un teaser *diferit* de titlu — deci `body == title` trece, și toate
celelalte la fel.

Asta explică întrebarea „cum e posibil după atâtea iterații": **ieșirea e fluentă și bine formată,
deci nicio verificare existentă n-are cum s-o distingă de un articol real.** Defectul nu e vizibil
în cod, ci doar citind textul publicat — și niciun test nu citește textul publicat.

§7 spune deja ce trebuia să se întâmple: *„If a fallback path cannot meet the «Zero Zgomot» quality
bar, SKIP the item — do not publish it broken."* Regula există; nu e implementată pentru cazul ăsta.

## Spec propus (de confirmat înainte de cod)

**Scop:** un articol nu se publică dacă intrarea din care a fost sintetizat nu conținea fapte peste
titlu.

**Intrări/ieșiri:** `fetch` marchează pe fiecare item cât adaugă descrierea față de titlu; poarta
respinge sub prag; itemul rămâne în state (nu se pierde), doar nu se publică.

**Criterii de acceptare:**
1. Un item cu 0–4 cuvinte noi față de titlu **nu ajunge la AI** (nu-i mai ardem buget) și nu se
   publică.
2. Cele 62 de articole deja publicate din surse fără substanță ies din feed la următoarea rulare.
3. Sursele 100% fără substanță sunt semnalate ca atare, nu tăcut golite — inclusiv `monitorulsv`,
   pe care l-am adăugat eu ieri și care nu poate trece niciodată pragul.
4. Regula din prompt care cere „extrage esența din titlul original" **dispare** — e instrucțiunea
   care legitima fabricarea.
5. Test care pornește de la itemul real din raportul ăsta și afirmă că NU se publică.

**Ce NU intră în felia asta:** aducerea textului integral de pe pagina sursă (schimbă profilul
legal și de trafic — decizie separată, a proprietarului).

## Întrebarea care rămâne a proprietarului

Pragul taie și presa locală utilă: multe primării trimit „ANUNȚ PUBLIC" cu descriere goală, iar
alea sunt exact anunțurile pentru care există rubrica `local`. Trei variante, cost crescător:
**(a)** nu se publică deloc; **(b)** se publică fără teaser, ca simplă listă de anunțuri cu link;
**(c)** se citește pagina sursă pentru primării (decizie legală + de infrastructură).
Nu aleg eu între ele — schimbă ce vede cititorul.
