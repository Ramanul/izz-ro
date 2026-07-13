"""Teste offline pentru judecatorul AI de potrivire foto<->articol (partile pure +
comportamentul fail-safe cu provideri fake -- fara retea)."""
from generator import photojudge as pj


class _Provider:
    """Provider fals: intoarce raspunsul dat sau ridica exceptie."""
    name = "fake"

    def __init__(self, reply=None, boom=False):
        self.reply, self.boom = reply, boom
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        if self.boom:
            raise RuntimeError("api down")
        return self.reply


def test_build_user_includes_all_fields():
    u = pj.build_user("Craiova a batut U Cluj", "Universitatea Craiova a invins...",
                      "U Cluj", "Echipa U Cluj sarbatorind promovarea")
    for needle in ("Craiova a batut U Cluj", "U Cluj", "sarbatorind promovarea"):
        assert needle in u


def test_parse_verdict_true_only_on_explicit_ok():
    assert pj.parse_verdict('{"ok": true, "reason": "subject"}')
    assert pj.parse_verdict('```json\n{"ok": true}\n```')          # tolerant la fences
    for bad in ('{"ok": false}', '{"ok": "true"}', '{}', 'not json', '', None):
        assert not pj.parse_verdict(bad), bad


def test_photo_fits_none_provider_defers_to_deterministic():
    # fara provider -> True (regulile deterministe raman singurele in vigoare)
    assert pj.photo_fits(None, "t", "s", "e", "c") is True


def test_photo_fits_uses_ai_verdict():
    assert pj.photo_fits(_Provider(reply='{"ok": true}'), "t", "s", "e", "c") is True
    assert pj.photo_fits(_Provider(reply='{"ok": false}'), "t", "s", "e", "c") is False


def test_photo_fits_failsafe_rejects_on_error():
    # apel AI care crapa -> False (mai bine fara poza decat una inselatoare)
    assert pj.photo_fits(_Provider(boom=True), "t", "s", "e", "c") is False
    # raspuns ambiguu/negol -> False
    assert pj.photo_fits(_Provider(reply="maybe?"), "t", "s", "e", "c") is False
