# Editorial operation - Principles pilot

## Scope and current state

Pagina `/principii/` explică identitatea și angajamentele proiectului. Cele trei surse
active sunt Contactul Ra, volumele 1 și 2, și AlienMind, în traducerile analizate.
Ele fundamentează o inspirație selectivă; probele unei știri vin din sursele evenimentului.
Un principiu filosofic nu aprobă automat o relatare și nu clasifică cititorii.

Colectarea, gruparea, redactarea inițială și publicarea pot fi automate. Această felie
adaugă conținut explicativ, nu certifică un flux universal de revizie umană. Contextul
suplimentar, dosarele, marcajele detaliate de revizie, propagarea istoricului corecțiilor
și cache-ul editorial sunt în implementare și se declară disponibile numai după
verificarea lor separată. Nu se promite o frecvență zilnică sau revizia tuturor știrilor.

## Ownership and bounded review

Alexandru Nicolae Stanciu, operatorul Redacției IZZ.ro, răspunde pentru regulile
editoriale și deciziile de aprobare, corecție ori retragere. Automatizarea poate pregăti
materialul, dar nu acordă singură aprobarea editorială. Capacitatea umană se constată
din munca efectuată, nu din numărul articolelor generate sau din buna intenție.

Înaintea pilotului, redacția delimitează lotul, intervalul, persoana care îl examinează
și timpul disponibil. În raport se păstrează separat numărul selectat, numărul examinat
și domeniul fiecărei revizii. Un bloc aprobat nu face întregul articol verificat.
Dacă lotul depășește capacitatea, se reduce ori se amână; nu se elimină verificarea
pentru a păstra o promisiune de volum. Ra II 99.9 (PDF380-381) este o ancoră a limitei
capacității, nu o durată optimă de lucru pentru redacție sau cititor.

## Manual review record

Pentru fiecare material efectiv examinat, se consemnează într-o fișă de lucru:

- adresa stabilă a articolului, momentul examinării și persoana care a examinat;
- afirmațiile sau blocurile examinate, sursele directe și pasajele relevante;
- diferențele dintre relatare, fapt documentat, estimare și interpretare;
- originea comună a preluărilor, contradicțiile, necunoscutele și resursele expirate;
- decizia motivată și ce a rămas neexaminat, inclusiv prezentările afectate de o corecție.

Acesta este un contract de proces pentru pilot, nu declarația că toate fișele există
deja într-un sistem public. În lipsa unei examinări, nu se afișează un marcaj de aprobare.
Datele sensibile nu se publică doar pentru a demonstra transparența. Se păstrează
distincția dintre fotografie documentară, imagine de context și ilustrație generată;
Ra II 88.10-88.12 (PDF280-281) inspiră documentarea sinceră, nu dovedește o știre.

## Objections and corrections

Calea existentă este `contact@izz.ro`, cu procedura publică la `/legal/corrections/`.
O sesizare utilă identifică pagina, afirmația contestată, documentul și locul precis
din el. Obiecția se examinează după probe; voturile, prestigiul și numărul preluărilor
nu o validează și nici nu o resping. Nu se promite confirmare automată ori timp garantat.

O corecție materială trebuie să numească schimbarea, data, motivul și conținutul afectat.
Operatorul verifică efectiv prezentările pe care le-a schimbat. Un mecanism viitor de
propagare sau cache nu este considerat funcțional pentru că această procedură îl cere.
Nu se editează manual starea colectării pentru a simula rezolvarea. O factualitate
corectată rămâne corectată și dacă o opțiune de prezentare este retrasă.

O obiecție privind filosofia se verifică în ediția citată. Pentru Ra se disting
întrebarea, răspunsul atribuit și nota editorului/traducătorului; pentru AlienMind,
mărturia și interpretarea autorului. Dacă ancora este defectă, se corectează atribuirea
înaintea păstrării interpretării. Nu se validează contacte, telepatie ori explicații
ale bolii prin simpla citire a cărților. Nu se distribuie automat fișierele furnizate.

## Delivery and stopping conditions

Conținutul folosește rendererul Markdown/Jinja existent. Integrarea navigației,
sitemapului, construirea întregului site, controlul în browser și verificarea live
aparțin integratorului. Trecerea testelor locale nu dovedește o publicare reușită.

Pilotul se revizuiește dacă cititorii confundă afirmațiile spirituale cu probele
știrilor, dacă o funcție ascunde informație incomodă sau dacă revizia depășește
capacitatea consemnată. Se păstrează critica, refuzul doctrinei și ieșirea reală.
Ra II 73.12 (PDF147) limitează serviciul impus; 97.9 (PDF366) limitează folosirea
arhetipurilor ca explicație totală. Nici pagina, nici pilotul nu promit vindecare,
protecție spirituală sau transformarea personală a cititorului.

La închiderea fiecărei felii se raportează separat: scris în cod, verificat local și
confirmat pe live. O funcție se trece din angajament în comportament disponibil doar
după verificarea ei efectivă și actualizarea explicației publice.

## Pilotul de context documentat

`content/editorial/annotations.json` este un catalog manual. Pentru fiecare bloc se
consemnează articolul, tipul real al reviziei, data, amprenta intrării, afirmațiile,
adresa și locul exact al probelor examinate, plus ce lipsește. `kind=documentary`
este documentare asistată de AI și nu se etichetează ca revizie umană. Identitatea
internă a revizorului nu se exportă în HTML sau în raportul public.

Înainte de randare: `python tools/validate_editorial.py`. Raport fără colectare sau
apeluri AI: `python tools/editorial_report.py`. Randarea emite și
`/editorial-report.json`, cu acoperire numărător/numitor din articolele publicabile.
O amprentă schimbată ascunde contextul și este numărată la `needs_review`; nu
modificăm aprobarea automat. Un catalog invalid oprește randarea înainte de golirea
rezultatului anterior. Articolele fără adnotări își păstrează prezentarea.

Pilotul inițial examinează numai pagina Primăriei Ineu și prezența legăturii spre
registrul trimestrului III 2026, fără a verifica valorile din PDF. Nu se promite
documentare continuă, confirmare independentă sau revizia umană a întregii știri.
