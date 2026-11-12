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


def test_model_legend_matches_catalog_order(monkeypatch, capsys):
    monkeypatch.setattr(check, "MODELS", ("model-b", "model-a"))
    monkeypatch.setattr(check, "check_key", lambda key: ("ok", {"model-a"}))
    check.main()
    output = capsys.readouterr().out
    assert "modele 1=nu, 2=da" in output
    assert "1=model-b; 2=model-a" in output


def test_new_models_listed_and_only_matching_ones_probed(monkeypatch, capsys):
    catalog = {
        "gemini-3.8-flash": {}, "gemini-4-hydrogen": {"inputTokenLimit": 1000},
        "gemini-exp-1": {}, "text-embedding-9": {},
    }
    probed = []

    def opener(request, timeout):
        probed.append(request.full_url)
        assert request.get_header("X-goog-api-key") == "secret-value"
        assert "secret-value" not in request.full_url
        return Response({"candidates": [{"finishReason": "STOP",
                                         "content": {"parts": [{"text": '{"ok": true}'}]}}],
                         "usageMetadata": {"thoughtsTokenCount": 7, "candidatesTokenCount": 4}})

    assert check.new_models(catalog) == ["gemini-4-hydrogen", "gemini-exp-1"]
    check.report_new("secret-value", catalog, opener)
    output = capsys.readouterr().out
    assert len(probed) == 1 and "gemini-4-hydrogen:generateContent" in probed[0]
    assert "2: gemini-4-hydrogen(in=1000" in output
    assert "http=200" in output and "json_ok=True" in output and "thoughts=7" in output
    assert "secret-value" not in output


def test_probe_reports_only_status_on_http_error():
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 429, "secret-value", {}, io.BytesIO(b"secret-value"))

    result = check.probe("secret-value", "gemini-4-hydrogen", opener)
    assert result["http"] == 429 and "secret-value" not in str(result)


def test_probe_ignores_thought_parts():
    def opener(request, timeout):
        assert json.loads(request.data)["generationConfig"]["maxOutputTokens"] >= 1024
        return Response({"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": "ma gandesc", "thought": True}, {"text": '{"ok": true}'}]}}]})

    assert check.probe("k", "gemini-4-x", opener)["json_ok"] is True
