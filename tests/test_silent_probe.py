"""Logica de citire/decomprimare din tools/silent_probe.py.

Nu testeaza fetch-ul (proba are nevoie de retea; tocmai asta o face unealta de teren).
Testeaza ce se poate strica tacut si ar produce un DIAGNOSTIC FALS — ceea ce pentru unealta
asta e mai rau decat sa nu ruleze deloc:
  - un corp taiat la mijloc ridica IncompleteRead, care nu e URLError; fara ramura dedicata
    o singura sursa trunchiata ar opri toata proba, fix pe cazul pe care il diagnosticheaza;
  - un corp comprimat afisat brut arata ca gunoi binar, iar gunoiul s-ar citi drept "raspuns
    corupt" in loc de "raspuns normal, doar gzip".
"""
import gzip
import http.client
import importlib.util
import os
import zlib

_SPEC = importlib.util.spec_from_file_location(
    "silent_probe",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "silent_probe.py"),
)
silent_probe = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(silent_probe)


class _Resp:
    """Raspuns minimal: `read(n)` intoarce corpul sau ridica exceptia data."""

    def __init__(self, body=b"", headers=None, raises=None):
        self._body = body
        self.headers = headers or {}
        self._raises = raises

    def read(self, n=None):
        if self._raises is not None:
            raise self._raises
        return self._body if n is None else self._body[:n]


# --- _printable ---------------------------------------------------------------

def test_printable_collapses_whitespace_to_one_line():
    assert silent_probe._printable(b"<?xml\n  version\t=\"1.0\"?>") == '<?xml version ="1.0"?>'


def test_printable_reports_empty_body_explicitly():
    # "(corp gol)" trebuie sa fie distinct de un corp cu spatii: ambele arata la fel altfel.
    assert silent_probe._printable(b"") == "(corp gol)"
    assert silent_probe._printable(b"   \n\t ") == "(corp gol)"


def test_printable_truncates_to_limit():
    assert silent_probe._printable(b"x" * 1000, limit=10) == "x" * 10


def test_printable_survives_invalid_utf8():
    # Un corp binar nu are voie sa arunce; altfel proba moare pe sursa care intereseaza.
    assert silent_probe._printable(b"\xff\xfe\x00abc")


# --- _read_body ---------------------------------------------------------------

def test_read_body_clean_response_has_no_note():
    raw, note = silent_probe._read_body(_Resp(b"<rss/>", {"Content-Length": "6"}))
    assert raw == b"<rss/>"
    assert note is None


def test_read_body_keeps_partial_bytes_on_incomplete_read():
    exc = http.client.IncompleteRead(partial=b"<rss><chan", expected=500)
    raw, note = silent_probe._read_body(_Resp(raises=exc))
    assert raw == b"<rss><chan"          # octetii primiti sunt exact dovada cautata
    assert "TRUNCHIAT de sursa" in note
    assert "500" in note


def test_read_body_flags_short_read_against_content_length():
    raw, note = silent_probe._read_body(_Resp(b"abc", {"Content-Length": "99"}))
    assert raw == b"abc"
    assert "citire scurta" in note and "99" in note


def test_read_body_marks_its_own_truncation_distinctly():
    big = b"y" * (silent_probe.MAX_READ + 50)
    raw, note = silent_probe._read_body(_Resp(big))
    assert len(raw) == silent_probe.MAX_READ
    # "DE PROBA" separa taierea noastra de una a sursei — altfel s-ar raporta un fals pozitiv.
    assert "DE PROBA" in note


def test_read_body_does_not_flag_longer_than_declared():
    # Content-Length mai mic decat corpul nu e o citire scurta; sa nu inventeze anomalii.
    raw, note = silent_probe._read_body(_Resp(b"abcdef", {"Content-Length": "3"}))
    assert raw == b"abcdef"
    assert note is None


def test_read_body_ignores_non_numeric_content_length():
    raw, note = silent_probe._read_body(_Resp(b"abc", {"Content-Length": "gunoi"}))
    assert raw == b"abc" and note is None


def test_read_body_survives_generic_http_exception():
    raw, note = silent_probe._read_body(_Resp(raises=http.client.LineTooLong("status line")))
    assert raw == b""
    assert "raspuns invalid la nivel HTTP" in note


# --- _decode_body -------------------------------------------------------------

def test_decode_body_passes_through_when_not_encoded():
    for enc in ("", "-", "identity", "IDENTITY"):
        body, note = silent_probe._decode_body(b"<rss/>", enc)
        assert body == b"<rss/>" and note is None


def test_decode_body_unpacks_gzip():
    body, note = silent_probe._decode_body(gzip.compress(b"<rss/>"), "gzip")
    assert body == b"<rss/>"
    assert note == "decomprimat gzip"


def test_decode_body_unpacks_raw_deflate():
    comp = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    body, note = silent_probe._decode_body(comp.compress(b"<rss/>") + comp.flush(), "deflate")
    assert body == b"<rss/>"
    assert note == "decomprimat deflate"


def test_decode_body_reports_failure_instead_of_raising():
    # Antet gzip mincinos: intoarce None + nota, nu exceptie, ca proba sa treaca mai departe.
    body, note = silent_probe._decode_body(b"nu e gzip", "gzip")
    assert body is None
    assert "esuata" in note


def test_decode_body_names_unsupported_encoding():
    body, note = silent_probe._decode_body(b"\x00\x01", "br")
    assert body is None
    assert "'br'" in note and "nesuportat" in note


def test_decode_body_is_case_and_space_insensitive():
    body, _ = silent_probe._decode_body(gzip.compress(b"ok"), "  GZip ")
    assert body == b"ok"
