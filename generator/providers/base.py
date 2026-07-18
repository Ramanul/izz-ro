"""Interfata comuna pentru furnizorii AI. process.py nu stie ce provider e dedesubt."""


class Provider:
    name = "base"

    # Contoare pentru detectarea unei caderi AI SISTEMICE (model retras, cheie/quota
    # moarta). process.py inghite erorile per-apel intentionat (regula 'No mangled
    # output': un articol care nu se poate procesa se amana, nu se publica brut), asa
    # ca fara aceste contoare o cadere TOTALA e indistinctibila de "n-a fost nimic nou".
    # run() le citeste ca sa semnaleze zgomotos si sa iasa non-zero (CI rosu, deploy sarit).
    calls = 0
    failures = 0
    last_error = None

    def available(self) -> bool:
        """True daca providerul are cheia/SDK-ul necesar si poate fi apelat."""
        raise NotImplementedError

    def complete(self, system: str, user: str) -> str:
        """Wrapper instrumentat: numara apelurile + esecurile totale, apoi deleaga la
        `_complete` al providerului concret. Nu inghite exceptia (o re-arunca, ca
        process.py sa amane articolul ca inainte) -- doar o CONTABILIZEAZA."""
        self.calls += 1
        try:
            return self._complete(system, user)
        except Exception as exc:
            self.failures += 1
            self.last_error = f"{type(exc).__name__}: {exc}"
            raise

    def _complete(self, system: str, user: str) -> str:
        """Implementarea reala a providerului. Returneaza textul raspunsului (de obicei JSON)."""
        raise NotImplementedError
