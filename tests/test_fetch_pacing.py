"""Distantarea cererilor catre acelasi furnizor de gazduire.

De ce exista: masurat 2026-08-02 pe un runner GitHub, o matura de 189 de surse a primit
challenge anti-bot pe 66 din cele 68 servite de `openresty`, fata de 0/24 LiteSpeed si
0/19 nginx. Cele 66 de domenii rezolva la IP-uri DIFERITE, deci nu se poate distanta nici
per hostname nici per IP — cheia trebuie sa fie furnizorul, citit din antetul `Server`.

Testele nu ating reteaua si nu dorm: verifica planificarea (`_next_free`), nu ceasul.
"""
import threading

from generator import fetch


def _cache(**pairs):
    return {k: {"server": v} for k, v in pairs.items()}


# --- _server_sig --------------------------------------------------------------

def test_server_sig_strips_the_version():
    # Acelasi furnizor ruleaza build-uri diferite; cota e a lui, nu a build-ului.
    assert fetch._server_sig({"server": "openresty/1.31.1.1"}) == "openresty"
    assert fetch._server_sig({"server": "openresty/1.29.2.3"}) == "openresty"


def test_server_sig_is_case_insensitive_and_trimmed():
    assert fetch._server_sig({"server": "  OpenResty "}) == "openresty"


def test_server_sig_absent_or_empty_is_none():
    assert fetch._server_sig({}) is None
    assert fetch._server_sig({"server": None}) is None
    assert fetch._server_sig(None) is None


# --- gruparea -----------------------------------------------------------------

def test_only_groups_at_or_above_the_threshold_are_paced():
    cache = _cache(**{f"a{i}": "openresty/1.31.1.1" for i in range(10)})
    cache.update(_cache(**{f"b{i}": "nginx" for i in range(3)}))
    pacer = fetch._HostPacer(cache, interval=1.0, group_min=10)
    assert pacer._paced == {"openresty"}          # nginx are 3, sub prag -> liber


def test_an_empty_cache_paces_nothing():
    # Prima rulare de dupa deploy nu are semnaturi: nu incetineste nimic, invata si se
    # corecteaza de la a doua rulare. Fara asta, deploy-ul ar arata ca o regresie de viteza.
    pacer = fetch._HostPacer({}, interval=1.0, group_min=10)
    assert pacer._paced == set()


# --- planificarea -------------------------------------------------------------

def test_requests_in_a_paced_group_are_spaced_by_the_interval():
    cache = _cache(**{f"s{i}": "openresty/1.31.1.1" for i in range(12)})
    pacer = fetch._HostPacer(cache, interval=5.0, group_min=10)
    slots = []
    for i in range(4):
        with pacer._lock:
            now = 100.0
            due = max(now, pacer._next_free.get("openresty", 0.0))
            pacer._next_free["openresty"] = due + pacer._interval
            slots.append(due)
    assert slots == [100.0, 105.0, 110.0, 115.0]


def test_wait_is_a_noop_for_an_unpaced_group(monkeypatch):
    cache = _cache(**{f"s{i}": "openresty" for i in range(12)}, lonely="nginx")
    pacer = fetch._HostPacer(cache, interval=5.0, group_min=10)
    slept = []
    monkeypatch.setattr(fetch.time, "sleep", slept.append)
    pacer.wait("lonely", cache)
    assert slept == []                             # nginx nu e in grupul limitat


def test_wait_is_a_noop_for_a_source_with_no_cached_server(monkeypatch):
    cache = _cache(**{f"s{i}": "openresty" for i in range(12)})
    pacer = fetch._HostPacer(cache, interval=5.0, group_min=10)
    slept = []
    monkeypatch.setattr(fetch.time, "sleep", slept.append)
    pacer.wait("necunoscuta", cache)
    assert slept == []


def test_zero_interval_disables_pacing(monkeypatch):
    cache = _cache(**{f"s{i}": "openresty" for i in range(12)})
    pacer = fetch._HostPacer(cache, interval=0.0, group_min=10)
    slept = []
    monkeypatch.setattr(fetch.time, "sleep", slept.append)
    pacer.wait("s0", cache)
    assert slept == []                             # FETCH_PACE_S=0 ca supapa de urgenta


def test_concurrent_waits_never_hand_out_the_same_slot(monkeypatch):
    # Invariantul care conteaza sub ThreadPoolExecutor: 8 fire nu au voie sa primeasca
    # aceeasi rezervare, altfel distantarea e doar aparenta si rafala ramane.
    cache = _cache(**{f"s{i}": "openresty" for i in range(12)})
    pacer = fetch._HostPacer(cache, interval=1.0, group_min=10)
    monkeypatch.setattr(fetch.time, "sleep", lambda _s: None)
    monkeypatch.setattr(fetch.time, "monotonic", lambda: 0.0)
    threads = [threading.Thread(target=pacer.wait, args=(f"s{i}", cache)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert pacer._next_free["openresty"] == 12.0   # 12 rezervari distincte, nu suprapuse


# --- integrare cu _fetch_one_guarded ------------------------------------------

def test_guarded_fetch_paces_before_fetching(monkeypatch):
    cache = _cache(**{f"s{i}": "openresty" for i in range(12)})
    pacer = fetch._HostPacer(cache, interval=5.0, group_min=10)
    order = []
    monkeypatch.setattr(fetch.time, "sleep", lambda _s: order.append("sleep"))
    monkeypatch.setattr(fetch, "_fetch_one",
                        lambda k, s, c: (order.append("fetch"), ([], None))[1])
    fetch._fetch_one_guarded("s0", {"url": "https://ex.ro/feed/"}, cache, pacer)
    fetch._fetch_one_guarded("s1", {"url": "https://ex2.ro/feed/"}, cache, pacer)
    # A doua cerere din grup asteapta INAINTE de fetch, nu dupa.
    assert order == ["fetch", "sleep", "fetch"]


def test_guarded_fetch_without_a_pacer_behaves_as_before(monkeypatch):
    monkeypatch.setattr(fetch, "_fetch_one", lambda k, s, c: ([], None))
    assert fetch._fetch_one_guarded("x", {"url": "u"}, None) == ([], None)
