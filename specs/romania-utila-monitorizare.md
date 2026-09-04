# România Utilă — monitorizarea surselor oficiale

## Scop
Introducem un contract simplu prin care fiecare entitate volatilă din `data/entities/` declară sursele primare, frecvența dorită de verificare și ce se întâmplă când o sursă nu mai este accesibilă. Prima etapă este declarativă; automatizarea fetch/alertare vine după validarea contractului.

## Intrări / ieșiri
- Intrare: fișierele YAML ale entităților, în special `verificat`, `ultima_verificare` și `monitorizare.surse`.
- Ieșire: un registru ușor de analizat care poate identifica entități neverificate, surse lipsă și date expirate.

## Contract propus
- `sursa_url` din `valoare_curenta` rămâne sursa primară afișată cititorului.
- `monitorizare.surse[]` conține sursa primară și, când există, una sau mai multe surse instituționale de rezervă.
- `verificat: true` este permis numai după confruntarea cu cel puțin o sursă instituțională.
- `ultima_verificare` este data ultimei confruntări reale, nu data publicării paginii.
- O entitate volatilă fără verificare recentă trebuie marcată pentru reverificare înainte de a fi prezentată ca valoare curentă.

## Priorități pentru România Utilă
1. Salarii, pensii, taxe, contribuții și beneficii monetare: verificare frecventă.
2. Termene fiscale și administrative: verificare frecventă în perioadele cu schimbări legislative.
3. Acte, proceduri și costuri administrative: reverificare când instituția publică schimbă procedura sau tariful.

## Criterii de acceptare pentru următoarea felie
- Există un câmp de stare care poate separa `verificat`, `expirat` și `neverificat` fără a modifica rendererul.
- Un test poate detecta o entitate cu `verificat: true` dar cu `ultima_verificare` lipsă sau fără sursă de monitorizare.
- O viitoare automatizare poate consuma același contract fără migrarea tuturor entităților.

## Notă
Nu pornim încă fetch-uri automate din CI. CI trebuie să rămână hermetic, iar verificarea externă să fie un proces separat, explicit, până când avem un mecanism de cache, backoff și audit al modificărilor.