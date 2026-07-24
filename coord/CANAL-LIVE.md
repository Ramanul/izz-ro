# Canal LIVE A ↔ B

Acest PR **nu se merge niciodată**. Există ca să țină deschis un fir de comentarii.

**De ce:** `TASKS-A.md`/`TASKS-B.md` sunt asincrone — latența = cât de des face fiecare
`git pull`. Comentariile pe acest PR ajung **instantaneu** în sesiunea contului B, prin
webhook. Nu mai e nevoie de owner ca releu pe direcția A → B.
