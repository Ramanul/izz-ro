# Sablon + proces: permisiuni multimedia de la institutii (sect. 18)

> Pasul 1 din procesul de permisiuni in masa. Ce faci cu fisierul asta: copiezi
> scrisoarea, completezi campurile dintre paranteze, o trimiti de pe adresa ta
> (contact@izz.ro) catre institutie. Nimic din ce cumva primesti NU intra in
> pipeline pana nu e trecut in `data/permisiuni.yaml` cu acordul tau explicit
> (regula sect. 18: om in bucla, inainte sa tragem vreo imagine).

## Scrisoare-tip (ISU, primarii, consilii judetene)

Subiect: Cerere de acord pentru reutilizarea fotografiilor publicate de [INSTITUȚIA]

Stimata [INSTITUȚIA],

izz.ro este un agregator de stiri romanesc care sintetizeaza stiri publice si indica
întotdeauna sursa originala, cu link direct catre comunicatul dumneavoastra.

Va rugam sa ne acordati acordul scris pentru reutilizarea fotografiilor publicate
de dumneavoastra pe site-ul propriu si in comunicatele de presa, cu urmatoarele
conditii, pe care le respectam implicit:

1. Fiecare imagine apare alaturi de sursa: „Foto: [INSTITUȚIA]", cu link catre
   comunicatul original;
2. Folosirea este exclusiv editoriala, informativa, necomerciala;
3. Nu alteram imaginile decat prin decupaj tehnic pentru formatul paginii;
4. Acordul poate fi retras oricand, cu efect pentru publicarile viitoare.

Raspunsul dumneavoastra pe acest e-mail are valoare de acord in aceasta intelegere.

Va multumim,
[NUME], izz.ro — contact@izz.ro

## data/permisiuni.yaml — schema (se completeaza DOAR cu acord explicit al proprietarului)

```yaml
# Un rand per institutie care a ACORDAT permisiunea. Fara acord scris -> fara rand.
# Comportamentul pipeline-ului: numai domeniile de aici intra in fluxul de poze
# institutionale; tot ce nu e aici e tratat ca interzis (fail-safe, sect. 18).
- institutie: "ISU VRANCEA"          # numele exact, ca in comunicate
  domenii: ["isuvrancea.ro"]         # site-urile de pe care se pot lua imagini
  termeni: "credit + link comunicat; uz editorial necomercial; decupaj tehnic admis"
  dovada: "email de la pr@isuvrancea.ro, 2026-09-10"   # unde e acordul scris
  aprobat_de: "Alexandru"            # cine a dat OK-ul (sect. 18: om in bucla)
  data: "2026-09-10"
```

## Ordinea pasilor (cine face ce)

1. Alexandru trimite scrisoarea (sablonul de mai sus) — la ISU-judet, primariile GOLD
   cu poze frecvente, Administratia Nationala de Meteorologie — sursele cu multimedia
   frecventa si relevanta;
2. La raspuns pozitiv scris, proprietarul aproba randul din `permisiuni.yaml`;
3. Dopul tehnic: o felie de cod care citeste whitelist-ul si trage pozele DOAR din
   domeniile listate, cu creditul obligatoriu — se construieste ABIA dupa primul acord.
