# Cum devin ideile funcții

Pagina [Principii](/principii/) explică de ce există IZZ.ro. Aceasta arată **cum**: ce problemă am văzut, ce regulă am adoptat, ce face efectiv site-ul, unde verifici asta în câteva clicuri și unde se oprește implementarea. Fiecare mecanism de mai jos funcționează azi; nimic de aici nu este plan sau promisiune.

## 1. Titlul spune ce s-a întâmplat

**Problemă:** titlurile construite pentru retenție ascund informația după întrebări retorice, suspans și adjective, ca să forțeze clicul.

**Regulă adoptată:** informația grea la început. Fără momeală de anticipare, fără adjective evaluative, fără titluri care nu se înțeleg singure.

**Ce face site-ul:** promptul de sinteză rescrie titlul de la zero, mută subiectul și acțiunea în față, elimină adjectivele de opinie și păstrează verbele de rezervă din textul-sursă („ar fi declarat", „conform documentului"); o afirmație care pierde rezerva pe care sursa o avea nu intră în textul scurt de pe card. Pagina [/azi/](/azi/) afișează ziua curentă exclusiv ca listă de titluri și surse.

**Unde verifici:** deschide [/azi/](/azi/) și caută un titlu-întrebare sau un „Șocant!".

**Limită:** comprimarea pierde contextul secundar, iar modelul poate prelua ocazional tonul sau un epitet din sursă; în plus, dacă publicația originală greșește un fapt, îl preluăm ca atare.

## 2. Nimic fără sursă

**Problemă:** agregatoarele refac titluri și îngroapă originea; cititorul nu poate verifica ce a citit.

**Regulă adoptată:** orice știre trimite vizibil la publicația originală, iar afirmațiile disputate sunt atribuite nominal în text.

**Ce face site-ul:** fiecare card și fiecare articol are linkul direct spre sursă; sintezele multi-sursă listează toate publicațiile implicate.

**Unde verifici:** deschide orice știre de pe prima pagină și caută linkul către publicația originală.

**Limită:** dacă pagina sursei dispare sau stă în spatele unui paywall, linkul rămâne și nu servim copie a textului lor.

## 3. Ce confirmă publicațiile, unde diferă, ce vine dintr-o singură origine

**Problemă:** preluarea în masă creează iluzia consensului: trei redacții care publică același comunicat par trei confirmări, iar citirea a cinci articole despre același subiect consumă timpul cititorului.

**Regulă adoptată:** o sinteză nu redactează un text liber peste surse. Separă ce confirmă cel puțin două publicații care nu preiau același text, ce versiuni diferă (atribuite fiecărei publicații) și ce apare la o singură origine. Când relatările se exclud, nu scriem o versiune comună.

**Ce face site-ul:** pentru fiecare eveniment relatat de mai multe publicații, sistemul citește textul integral al articolelor și îl împarte în propoziții numerotate. Modelul de limbaj propune faptele comune, diferențele și afirmațiile izolate, fiecare cu propozițiile din care provine; apoi un program le verifică pe rând: propoziția citată trebuie să existe și să aparțină acelui eveniment, fiecare cifră trebuie să fie în propozițiile citate, iar „confirmat" înseamnă cel puțin două origini distincte. Ce nu trece verificarea nu se publică; dacă prea multe afirmații pică, sinteza se amână. Rolul fiecărei publicații e calculat mecanic, fără model de limbaj: prima relatare observată (o relatare densă publicată în aceleași 15 minute bate o alertă de două rânduri), detalii suplimentare, aceleași fapte cu alte cuvinte, text comun cu altă publicație (posibil comunicat) sau preluare declarată. Cardul arată câte confirmări încrucișate are subiectul, iar [/surse/](/surse/) publică, pe 12 zile, cine a relatat primul. Când o sinteză se actualizează, pagina spune câte fapte sunt noi și care nu mai apar; când o sursă își schimbă ulterior faptele (amprenta textului diferă cu peste 20%), mențiunea apare lângă numele ei.

**Unde verifici:** deschide o sinteză cu eticheta „Sinteză din N publicații": fiecare fapt poartă numele publicațiilor, iar lângă fiecare sursă stă rolul ei. Deschide sursele și caută faptul.

**Limită:** o preluare rescrisă integral, fără atribuire, nu poate fi deosebită de o relatare independentă; textul comun e recunoscut doar când secvențele de cuvinte coincid. Când textul integral nu poate fi citit (paywall, pagină de consimțământ), se folosește doar descrierea din fluxul RSS, deci diferențele fine se pot pierde. Modelul poate clasa greșit un fapt, iar verificarea prinde citarea și cifra greșită, nu sensul greșit al unei propoziții corect citate. Prima relatare e prima observată în fluxurile pe care le urmărim, nu dovada autorului informației. Sintezele publicate înainte de 23 octombrie 2026 păstrează forma veche, narativă, până la actualizare sau expirare.

## 4. Proporție geografică și proveniența relatării

**Problemă:** fluxurile naționale suprareprezintă capitala și marile orașe; restul țării pare fie gol, fie distorsionat de evenimente izolate mediatizate intens.

**Regulă adoptată:** localizare la nivel de județ și localitate, raportare la populație și proveniența relatărilor arătată explicit.

**Ce face site-ul:** [/harta/](/harta/) extrage județele și localitățile din text, permite comutarea vizualizării din volum brut în știri la 100.000 de locuitori și afișează panoul de proveniență: presă cu sediu în județ, din alte județe sau fără sediu în județ.

**Unde verifici:** deschide [/harta/](/harta/), apasă „Pe locuitor" și alege un județ pentru structura surselor.

**Limită:** localizarea depinde de toponimele prezente în text; evenimentele reale, dar formulate generic, nu ajung pe hartă.

## 5. Generarea automată e declarată

**Problemă:** textul generat automat, prezentat ca text scris de om, e o formă structurală de dezinformare.

**Regulă adoptată:** tot ce e generat automat se marchează; nimic generat nu se prezintă ca „verificat de om" dacă nu este.

**Ce face site-ul:** articolele poartă marcaj explicit de generare automată în pagină și în metadate. Înainte de publicare, un filtru automat blochează textele în care modelul introduce citate sau cifre absente din sursă, iar un set de verificări automate respinge titlurile corupte sau trunchiate.

**Unde verifici:** marcajul de sub orice sinteză, apoi istoricul intervențiilor pe [/legal/corrections/](/legal/corrections/).

**Limită:** nu există aprobare umană înainte de publicare și nici verificare umană zilnică a întregului flux. Filtrul validează prezența cifrei sau a citatului în sursă, nu asociația semantică corectă — o cifră reală poate ajunge într-un context greșit. Astfel de erori sunt corectate reactiv, prin verificări ulterioare.

## 6. Acces fără captivitate

**Problemă:** conturile obligatorii, profilarea și arhitecturile închise transformă cititorul în utilizator reținut.

**Regulă adoptată:** accesul e liber, fără cont și fără paywall; canalele sunt deschise și standard.

**Ce face site-ul:** flux RSS complet ([/feed.xml](/feed.xml)), abonare la notificări web push prin protocol standard (VAPID), fără cont și fără colectare de email, căutare liberă pe site, setări de consimțământ pe categorii ([/legal/privacy/#consimtamant](/legal/privacy/)) și acces la știrile expirate printr-o arhivă oglindă.

**Unde verifici:** deschide direct [/feed.xml](/feed.xml) sau panoul de consimțământ din [/legal/privacy/#consimtamant](/legal/privacy/#consimtamant).

**Limită:** fără profilare, zero personalizare: toți cititorii văd același flux.

## 7. Atenția are un capăt

**Problemă:** fluxurile fără sfârșit, contoarele de noutăți și notificările repetate transformă informarea în reținere.

**Regulă adoptată:** ziua are o listă finită, care își spune capătul; sistemul arată ce a eliminat, nu doar ce a adunat.

**Ce face site-ul:** antetul primei pagini arată câte relatări ale surselor stau în spatele subiectelor publicate în ultimele 24 de ore (relatările despre același eveniment devin un singur subiect). Lista de pe [/azi/](/azi/) se încheie cu un rând care spune că ai parcurs toate subiectele zilei. Nu există derulare infinită și nici notificări repetate: alertele sunt opționale, cel mult una pe zi.

**Unde verifici:** prima pagină, rândul de sub dată (pe ecran lat); capătul listei de pe [/azi/](/azi/); registrul [Ce nu ajunge pe site](/sub-prag/), cu câte relatări a oprit fiecare filtru la ultima publicare.

**Limită:** cifra relatărilor numără doar sursele din fluxurile urmărite și doar relatările unite într-o sinteză; duplicatele eliminate înainte de publicare nu sunt încă numărate public.

## Transparență scurtă: drepturi și conținut

- Modele utilizate: Google Gemini și Anthropic Claude. Răspunderea editorială pentru ce rămâne publicat aparține IZZ.ro.
- Corecțiile materiale sunt publicate cu ce s-a schimbat, când și de ce, pe [/legal/corrections/](/legal/corrections/). Retragerea materialelor la cerere temeinică: [/legal/takedown/](/legal/takedown/).
- Imaginile **nu** sunt extrase din surse: coperțile sunt, de regulă, grafică proprie generată programatic; o fotografie de terț apare numai cu temei de licență documentat și credit vizibil. Detalii: [/legal/images/](/legal/images/).
- Memoria subiectelor: deciziile încheiate pe care le-au confirmat cel puțin două origini (o lege promulgată, un buget aprobat, o hotărâre a unei instituții) rămân 12 luni într-un registru separat de fereastra de 12 zile — data, faptul și publicațiile, fără text de presă — și apar pe pagina unei știri noi despre aceleași entități. Nu intră acolo nicio anchetă, acuzație sau altă stare judiciară, iar o corecție ori o retragere scoate rândul și din registru.
- Nu folosim conținut de agenții de presă și nu republicăm articolele integrale. Textul integral al surselor e citit doar în timpul generării și nu se păstrează nicăieri; în starea publică rămân doar amprentele lui (cifre, nume, hash-uri), pentru a observa modificările ulterioare.

## Codul e public

Regulile, filtrele și verificările descrise aici sunt cod, nu declarații: [depozitul public al site-ului](https://github.com/Ramanul/izz-ro) conține programul care le aplică, testele care le fixează și specificațiile de proiectare. Mecanismele trebuie să rămână utile și pentru un cititor care nu împărtășește nicio convingere a celor care le-au construit.

## Dacă ceva nu se confirmă

Fiecare afirmație de pe această pagină poate fi testată prin linkurile de mai sus. Dacă una nu se confirmă în funcționarea reală, scrie la **contact@izz.ro** sau folosește raportarea de eroare de pe articol: pagina se corectează prin același mecanism ca restul site-ului, vizibil pe [/legal/corrections/](/legal/corrections/).
