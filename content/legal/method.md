# Cum devin ideile funcții

Pagina [Principii](/principii/) explică de ce există IZZ.ro. Aceasta arată **cum**: ce problemă am văzut, ce regulă am adoptat, ce face efectiv site-ul, unde verifici asta în câteva clicuri și unde se oprește implementarea. Fiecare mecanism de mai jos funcționează azi; nimic de aici nu este plan sau promisiune.

## 1. Titlul spune ce s-a întâmplat

**Problemă:** titlurile construite pentru retenție ascund informația după întrebări retorice, suspans și adjective, ca să forțeze clicul.

**Regulă adoptată:** informația grea la început. Fără momeală de anticipare, fără adjective evaluative, fără titluri care nu se înțeleg singure.

**Ce face site-ul:** promptul de sinteză rescrie titlul și rezumatul de la zero, mută subiectul și acțiunea în față, elimină adjectivele de opinie și păstrează verbele de rezervă din textul-sursă („ar fi declarat", „conform documentului"). Pagina [/azi/](/azi/) afișează ziua curentă exclusiv ca listă de titluri și surse.

**Unde verifici:** deschide [/azi/](/azi/) și caută un titlu-întrebare sau un „Șocant!".

**Limită:** comprimarea pierde contextul secundar, iar modelul poate prelua ocazional tonul sau un epitet din sursă; în plus, dacă publicația originală greșește un fapt, îl preluăm ca atare.

## 2. Nimic fără sursă

**Problemă:** agregatoarele refac titluri și îngroapă originea; cititorul nu poate verifica ce a citit.

**Regulă adoptată:** orice știre trimite vizibil la publicația originală, iar afirmațiile disputate sunt atribuite nominal în text.

**Ce face site-ul:** fiecare card și fiecare articol are linkul direct spre sursă; sintezele multi-sursă listează toate publicațiile implicate.

**Unde verifici:** deschide orice știre de pe prima pagină și caută linkul către publicația originală.

**Limită:** dacă pagina sursei dispare sau stă în spatele unui paywall, linkul rămâne și nu servim copie a textului lor.

## 3. Contradicțiile se arată, nu se netezesc

**Problemă:** preluarea în masă creează iluzia consensului, iar citirea a cinci articole despre același subiect consumă timpul cititorului.

**Regulă adoptată:** la un eveniment relatat de mai multe publicații generăm o singură sinteză care separă faptele confirmate din mai multe surse de afirmațiile divergente și reține ordinea apariției în flux.

**Ce face site-ul:** sintezele marchează explicit unde sursele se contrazic (cifre diferite, versiuni opuse). Pagina [/surse/](/surse/) publică, pe o fereastră de 12 zile, cine a publicat prima fiecare subiect devenit sinteză.

**Unde verifici:** deschide o sinteză multi-sursă pentru marcarea diferențelor, apoi tabelul de inițiativă de pe [/surse/](/surse/).

**Limită:** două publicații care preiau același comunicat sunt tratate tehnic drept două confirmări, iar o sursă aflată în afara fluxurilor RSS pe care le urmărim nu intră în calculul primei apariții — de aceea pagina poartă avertismentul că ordinea observată nu dovedește autorul informației.

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

## Transparență scurtă: drepturi și conținut

- Modele utilizate: Google Gemini și Anthropic Claude. Răspunderea editorială pentru ce rămâne publicat aparține IZZ.ro.
- Corecțiile materiale sunt publicate cu ce s-a schimbat, când și de ce, pe [/legal/corrections/](/legal/corrections/). Retragerea materialelor la cerere temeinică: [/legal/takedown/](/legal/takedown/).
- Imaginile **nu** sunt extrase din surse: coperțile sunt, de regulă, grafică proprie generată programatic; o fotografie de terț apare numai cu temei de licență documentat și credit vizibil. Detalii: [/legal/images/](/legal/images/).
- Nu folosim conținut de agenții de presă și nu republicăm articolele integrale.

## Notă de arhitectură

Cele șase mecanisme de mai sus sunt traducerea în reguli, filtre și interfețe a unor idei din _Contactul Ra_ (volumele 1 și 2) și _AlienMind_: atenția ca resursă finită, verificabilitatea în locul autorității, limita asumată a oricărui sistem, corecția admisă. Fundamentul, pasajele și tensiunile acestei adaptări sunt documentate pe [/principii/](/principii/).

## Dacă ceva nu se confirmă

Fiecare afirmație de pe această pagină poate fi testată prin linkurile de mai sus. Dacă una nu se confirmă în funcționarea reală, scrie la **contact@izz.ro** sau folosește raportarea de eroare de pe articol: pagina se corectează prin același mecanism ca restul site-ului, vizibil pe [/legal/corrections/](/legal/corrections/).
