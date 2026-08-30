# Rutina zilnică (~15 minute)

Acuratețea rămâne umană — AI poate greși, iar la știri o greșeală e risc de defăimare. Aceste 15 minute sunt și controlul de calitate, și „moat"-ul (selecția).

## Pași
1. Deschide site-ul și citește titlurile/rezumatele de azi.
2. Dacă ceva e **greșit, manipulator sau prea „complet"** (înlocuiește articolul), deschide **`moderation.yaml`** pe GitHub (în browser) și:
   - **ascunde** o știre → adaugă linkul ei la `blocklist_urls`;
   - **corectează** un titlu/teaser → adaugă o intrare la `corrections`;
   - **scoate o sursă** temporar → adaug-o la `suppress_sources`;
   - **promovează** o știre în hero → adaug-o la `featured`;
   - **filtru pe cuvinte** → `blocklist_keywords`.
3. Salvează fișierul pe GitHub. Când se vede schimbarea depinde de calea aleasă — **nu sunt „câteva minute" în ambele cazuri**:
   - **acum** → **Actions → Run workflow**. Rularea manuală ocolește poarta de cadență (`build.yml`, jobul `pipeline`), deci publică în ~12 minute, indiferent cât de proaspăt e ultimul conținut;
   - **de la sine** → următorul build automat, la până la ~2h. Cron-ul încearcă orar, dar poarta taie rularea dacă ultimul conținut e mai proaspăt de 105 minute. Deliberat: vezi `CLAUDE.md` §17.

## Exemple
```yaml
blocklist_urls:
  - "https://sursa.ro/articol-gresit"
corrections:
  "https://sursa.ro/articol": { title: "Titlu corect", teaser: "Rezumat corect." }
featured:
  - "https://sursa.ro/stire-importanta"
suppress_sources:
  - "gsp"
```

## Verificare înainte de publicare (opțional)
Pentru ca știrile importante (clusterele C) să **aștepte aprobarea** ta înainte să apară, pune în `moderation.yaml`:
```yaml
hold_important: true
```

## Lansare soft — etapă încheiată

Cele 7 zile au trecut demult; secțiunea rămâne pentru partea care e valabilă permanent, nu pentru fază. Urmărește erorile din **Actions** și calitatea rezumatelor; dacă AI derivează, ajustează prompturile din `generator/process.py` — după `REGULI-SINTEZA.md`, care e normativul.

Distribuția (newsletter + social) **nu mai e condiționată de faza asta**. Dacă n-a pornit, e o decizie separată, nu o condiție de lansare rămasă neîndeplinită.
