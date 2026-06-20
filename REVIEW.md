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
3. Salvează fișierul pe GitHub. Build-ul următor (sau **Actions → Run workflow**) aplică schimbarea în câteva minute.

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

## Lansare soft (primele 7 zile)
Urmărește erorile din **Actions** și calitatea rezumatelor. Dacă AI derivează, ajustează prompturile din `generator/process.py`. Abia apoi pornește distribuția (newsletter + social).
