"""Observed text stability counts only real, comparable repeated readings."""
import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from generator import config, fetch_deep


T0 = "2026-10-25T10:00:00+00:00"
T1 = "2026-10-25T11:00:00+00:00"
T2 = "2026-10-25T12:00:00+00:00"


def _entry(stamp=T0, text="first", anchors=None, mode="FULL_TEXT"):
    return {"sha256": fetch_deep.compute_sha256(text), "mode": mode,
            "anchors": ["NUM:10", "ENT:Timis"] if anchors is None else anchors,
            "published": T0, "fetched_at": stamp}


def _advance(previous, current):
    result = copy.deepcopy(current)
    result["text_observations"] = fetch_deep._advance_text_observations(previous, result)
    return result


def test_legacy_record_is_one_baseline_not_invented_history():
    assert fetch_deep.text_observation_counts(_entry()) is None
    first = _advance({}, _entry())
    assert first["text_observations"]["comparisons"] == 0
    assert first["text_observations"]["first_at"] is None
    second = _advance(first, _entry(T1))
    assert second["text_observations"] == {
        "v": 1, "comparisons": 1, "changed": 0, "first_at": T0, "last_at": T1,
    }


def test_material_change_and_normal_completion_are_counted_without_truth_judgment():
    changed = _advance(_entry(), _entry(T1, text="completed", anchors=["NUM:20", "ENT:Cluj"]))
    assert changed["text_observations"]["changed"] == 1
    same_facts = _advance(changed, _entry(T2, text="wording changed", anchors=["NUM:20", "ENT:Cluj"]))
    assert same_facts["text_observations"]["comparisons"] == 2
    assert same_facts["text_observations"]["changed"] == 1


@pytest.mark.parametrize("stamp", [T0, "2026-10-25T10:00:00Z", "2026-10-25T09:00:00+00:00",
                                   "2026-10-25T11:00:00", "bad", None])
def test_same_or_invalid_or_backwards_timestamp_does_not_count(stamp):
    assert _advance(_entry(), _entry(stamp))["text_observations"]["comparisons"] == 0


@pytest.mark.parametrize("old_mode,new_mode", [
    ("RSS_FALLBACK", "RSS_FALLBACK"), ("FULL_TEXT", "RSS_FALLBACK"), ("RSS_FALLBACK", "FULL_TEXT"),
])
def test_fallback_and_mode_switch_are_not_text_comparisons(old_mode, new_mode):
    assert _advance(_entry(mode=old_mode), _entry(T1, mode=new_mode))["text_observations"]["comparisons"] == 0


def test_fallback_retains_prior_counts_but_breaks_comparison_chain():
    measured = _advance(_entry(), _entry(T1))
    fallback = _advance(measured, _entry(T2, mode="RSS_FALLBACK"))
    resumed = _advance(fallback, _entry("2026-10-25T13:00:00+00:00"))
    assert resumed["text_observations"] == measured["text_observations"]


def test_changed_text_without_comparable_anchors_remains_unknown():
    assert _advance(_entry(anchors=[]), _entry(T1, text="new"))["text_observations"]["comparisons"] == 0
    assert _advance(_entry(anchors=[]), _entry(T1, anchors=[]))["text_observations"]["comparisons"] == 1


@pytest.mark.parametrize("anchors", [None, 7, {"bad": "schema"}, [None], ["bad"], [""], ["NUM:"]])
def test_changed_hash_with_corrupt_anchor_sample_is_not_comparable(anchors):
    previous = _entry()
    previous["anchors"] = anchors
    assert _advance(previous, _entry(T1, text="changed"))["text_observations"]["comparisons"] == 0


def test_exact_twenty_percent_anchor_drift_counts_as_material_change():
    previous = _entry(anchors=["NUM:1", "NUM:2", "NUM:3", "NUM:4", "NUM:5"])
    current = _entry(T1, text="changed", anchors=["NUM:1", "NUM:2", "NUM:3", "NUM:4"])
    assert _advance(previous, current)["text_observations"]["changed"] == 1


def test_matching_invalid_hashes_are_not_comparable():
    previous, current = _entry(), _entry(T1)
    previous["sha256"] = current["sha256"] = "broken"
    assert _advance(previous, current)["text_observations"]["comparisons"] == 0


def test_counters_do_not_mutate_or_share_previous_metadata():
    previous = _advance(_entry(), _entry(T1))
    snapshot = copy.deepcopy(previous)
    current = _advance(previous, _entry(T2))
    current["text_observations"]["changed"] = 2
    assert previous == snapshot


@pytest.mark.parametrize("anchors", [None, 7, {"bad": "schema"}, [None]])
def test_identical_valid_hash_can_compare_without_usable_anchors(anchors):
    previous, current = _entry(), _entry(T1)
    previous["anchors"] = current["anchors"] = anchors
    assert _advance(previous, current)["text_observations"]["comparisons"] == 1


@pytest.mark.parametrize("entry", [None, [], "bad", 7])
def test_non_object_metadata_is_unknown(entry):
    assert fetch_deep.text_observation_counts(entry) is None


def test_boolean_schema_version_is_unknown():
    counts = _advance(_entry(), _entry(T1))["text_observations"]
    counts["v"] = True
    assert fetch_deep.text_observation_counts({"text_observations": counts}) is None


def test_invalid_hash_breaks_comparison_chain():
    measured = _advance(_entry(), _entry(T1))
    broken = _entry(T2)
    broken["sha256"] = "bad"
    invalid = _advance(measured, broken)
    resumed = _advance(invalid, _entry("2026-10-25T13:00:00+00:00"))
    assert resumed["text_observations"] == measured["text_observations"]


@pytest.mark.parametrize("metadata", [None, [], "bad", {"bad": None, "also-bad": []}])
def test_corrupt_metadata_store_prunes_safely(metadata):
    assert fetch_deep._prune(metadata) == {}


@pytest.mark.parametrize("counts", [
    {"v": 2, "comparisons": 4, "changed": 0},
    {"v": 1, "comparisons": 2, "changed": 3, "first_at": T0, "last_at": T1},
    {"v": 1, "comparisons": True, "changed": 0, "first_at": T0, "last_at": T1},
    {"v": 1, "comparisons": 1, "changed": 0, "first_at": T1, "last_at": T0},
])
def test_invalid_counter_schema_is_unknown(counts):
    assert fetch_deep.text_observation_counts({"text_observations": counts}) is None


@pytest.mark.parametrize("normalized", [False, True])
def test_fetch_pipeline_persists_counters_without_raw_text_and_dry_run_leaves_file(tmp_path, monkeypatch, normalized):
    path = tmp_path / "deep_meta.json"
    now = datetime.now(timezone.utc)
    url = "https://example.org/news"
    previous = _entry((now - timedelta(hours=1)).isoformat())
    path.write_text(json.dumps({url: previous}), encoding="utf-8")
    article = {"url": "https://example.org/normalized" if normalized else url,
               "original_link": url, "title": "Buget pentru Timiș", "published": now.isoformat()}

    def fetched(item, prev, sems, lock):
        return fetch_deep.DeepResult(
            url=url, domain="example.org", published=now.isoformat(), extraction_mode="FULL_TEXT",
            fallback_reason=None, raw_text="Private full text retained only in memory.",
            content_sha256=previous["sha256"], anchors=set(previous["anchors"]),
        )

    monkeypatch.setattr(fetch_deep, "_fetch_single", fetched)
    fetch_deep.fetch_deep([[article]], meta_path=str(path))
    persisted = path.read_bytes()
    record = json.loads(persisted)[url]
    assert record["text_observations"]["comparisons"] == 1
    assert b"Private full text" not in persisted
    fetch_deep.fetch_deep([[dict(article)]], meta_path=str(path), persist=False)
    assert path.read_bytes() == persisted
    expired = copy.deepcopy(record)
    expired["published"] = (now - timedelta(days=config.ARTICLE_TTL_DAYS + 1)).isoformat()
    assert fetch_deep._prune({url: expired}) == {}
