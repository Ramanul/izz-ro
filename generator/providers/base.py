"""Interfata comuna pentru furnizorii AI. process.py nu stie ce provider e dedesubt."""


class Provider:
    name = "base"

    def available(self) -> bool:
        """True daca providerul are cheia/SDK-ul necesar si poate fi apelat."""
        raise NotImplementedError

    def complete(self, system: str, user: str) -> str:
        """Returneaza textul raspunsului (de obicei JSON)."""
        raise NotImplementedError
