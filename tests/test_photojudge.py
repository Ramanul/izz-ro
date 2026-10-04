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


# === dezambiguizare omonime (pick_candidate) ====================================

def test_build_pick_user_lists_numbered_candidates():
    u = pj.build_pick_user("Senatorul John Kennedy l-a criticat pe Trump",
                           "Senatorul de Louisiana...", 
                           ["John F. Kennedy (presedinte SUA 1961-1963, 1917-1963)",
                            "John N. Kennedy (senator de Louisiana, n. 1951)"])
    for needle in ("Senatorul John Kennedy", "[0] John F. Kennedy",
                   "[1] John N. Kennedy", "senator de Louisiana"):
        assert needle in u, needle


def test_parse_pick_accepts_index_and_neg_one():
    assert pj.parse_pick('{"pick": 1, "reason": "senator"}') == 1
    assert pj.parse_pick('```json\n{"pick": 0}\n```') == 0     # tolerant la fences
    assert pj.parse_pick('{"pick": "-1"}') == -1               # cifre ca text
    for bad in ('{"pick": -1}', '{}', 'not json', '', None,
                '{"pick": true}', '{"pick": false}', '{"pick": 1.5}'):
        assert pj.parse_pick(bad) == -1, bad


def test_pick_candidate_none_provider_offline_fallback():
    # fara provider -> -1: omonimele raman fara portret, niciodata "cel mai celebru"
    assert pj.pick_candidate(None, "t", "s", ["a", "b"]) == -1


def test_pick_candidate_uses_ai_verdict():
    p = _Provider(reply='{"pick": 1, "reason": "senator in viata"}')
    assert pj.pick_candidate(p, "t", "s", ["a", "b"]) == 1
    assert pj.pick_candidate(_Provider(reply='{"pick": 0}'), "t", "s", ["a", "b"]) == 0


def test_pick_candidate_failsafe_rejects():
    # apel AI care crapa, raspuns ambiguu sau index in afara listei -> -1
    assert pj.pick_candidate(_Provider(boom=True), "t", "s", ["a", "b"]) == -1
    assert pj.pick_candidate(_Provider(reply="hmm"), "t", "s", ["a", "b"]) == -1
    assert pj.pick_candidate(_Provider(reply='{"pick": 7}'), "t", "s", ["a", "b"]) == -1
    # lista vida -> -1 fara sa cheme providerul
    p = _Provider(reply='{"pick": 0}')
    assert pj.pick_candidate(p, "t", "s", []) == -1
    assert p.calls == 0
