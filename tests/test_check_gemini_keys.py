import io
import json
import urllib.error

from tools import check_gemini_keys as check


class Response:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, *_args):
        return self.data


def test_catalog_uses_header_and_reports_known_models():
    def opener(request, timeout):
        assert "secret-value" not in request.full_url
        assert request.get_header("X-goog-api-key") == "secret-value"
        assert timeout == 20
        return Response({"models": [{"name": "models/gemini-3.5-flash-lite",
                                     "supportedGenerationMethods": ["generateContent"]}]})

    assert check.check_key("secret-value", opener) == ("ok", {"gemini-3.5-flash-lite"})


def test_errors_do_not_disclose_key_or_response(capsys, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret-value")
    monkeypatch.setattr(check, "check_key", lambda key: ("http_403", set()) if key else ("missing", set()))
    check.main()
    output = capsys.readouterr().out
    assert "secret-value" not in output
    assert "catalog=http_403" in output
    assert "catalog=missing" in output


def test_http_error_details_not_returned():
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "secret-value", {}, io.BytesIO(b"secret-value"))

    assert check.check_key("secret-value", opener) == ("http_403", set())


def test_baseline_25_is_in_catalog_check():
    assert "gemini-2.5-flash" in check.MODELS
