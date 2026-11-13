"""Publication provenance regressions use synthetic evidence, never live access."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from tau_scout.publication import actor_publication, enrich_publication
from tau_scout.normalize import actor_job

OBSERVED = "2026-11-11T16:06:08+00:00"
DATE = "2026-10-20T12:00:00+00:00"


def test_seconds_and_milliseconds_are_equivalent_provider_claims():
    seconds = datetime.fromisoformat(DATE).timestamp()
    a, sa = actor_publication({"postedAtTimestamp": seconds}, OBSERVED)
    b, sb = actor_publication({"postedAtTimestamp": seconds * 1000}, OBSERVED)
    assert a == b == DATE
    for source in (sa, sb):
        view = enrich_publication({"publication_source": source, "posted_at": a, "observed_at": OBSERVED})
        assert view["status"] == "unverified_source_claim"
        assert view["original_publication_at"] is None
        assert not view["independently_verified"] and not view["freshness_verified"]


@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), 0, -100, 1234,
                                    "not-a-date SECRET", "2026-02-30", "2026-11-12", "2026-11-11T18:00:00Z"])
def test_invalid_implausible_and_future_dates_are_unknown_without_echoing_raw_values(value):
    date, source = actor_publication({"postedAtTimestamp": value}, OBSERVED)
    assert date is None and source["claims"] == []
    assert source["rejected_fields"] == ["postedAtTimestamp"]
    assert "SECRET" not in json.dumps(source)


def test_date_only_precision_is_distinct_from_observation_and_not_exact_time():
    date, source = actor_publication({"publishedAt": "2026-10-20"}, OBSERVED)
    assert date == "2026-10-20T00:00:00+00:00"
    assert source["claims"][0]["precision"] == "day"
    view = enrich_publication({"publication_source": source, "posted_at": date, "observed_at": OBSERVED})
    assert view["observed_at"] == OBSERVED
    assert view["claims"][0]["precision"] == "day"
    assert view["claims"][0]["value"] == "2026-10-20"
    assert any("midnight" in warning for warning in view["warnings"])


def test_conflicting_absolute_and_relative_claims_do_not_produce_a_single_date():
    date, source = actor_publication({"publishedAt": "2026-10-20", "postedTime": "2 days ago"}, OBSERVED)
    assert date is None and source["conflict"]
    view = enrich_publication({"publication_source": source, "posted_at": None, "observed_at": OBSERVED})
    assert view["status"] == "ambiguous"
    assert view["original_publication_at"] is None
    assert len(view["claims"]) == 2


def test_conflicting_absolute_dates_preserve_both_claims():
    date, source = actor_publication({"publishedAt": "2026-10-20", "postedDate": "2026-11-10"}, OBSERVED)
    assert date is None and source["conflict"]
    assert [claim["date"][:10] for claim in source["claims"]] == ["2026-10-20", "2026-11-10"]


def test_relative_labels_are_anchored_to_saved_observation_not_live_clock():
    date, source = actor_publication({"postedTime": "2 days ago"}, OBSERVED)
    assert date is None
    claim = source["claims"][0]
    assert claim["earliest"] == "2026-11-08T16:06:08+00:00"
    assert claim["latest"] == "2026-11-09T16:06:08+00:00"
    view = enrich_publication({"publication_source": source, "observed_at": OBSERVED, "posted_at": None})
    assert view["claims"][0] == claim
    assert view["original_publication_at"] is None


def test_repost_age_does_not_create_original_publication_or_conflict_with_old_original_claim():
    date, source = actor_publication({"publishedAt": "2026-10-20", "postedTime": "Reposted 2 days ago"}, OBSERVED)
    assert date and not source["conflict"]
    view = enrich_publication({"publication_source": source, "posted_at": date, "observed_at": OBSERVED})
    assert view["claims"][1]["kind"] == "repost"
    assert view["original_publication_at"] is None
    assert any("repost" in warning for warning in view["warnings"])


def test_missing_dates_do_not_fall_back_to_observation_time():
    view = enrich_publication({"posted_at": None, "observed_at": OBSERVED})
    assert view["status"] == "unknown" and view["claims"] == []
    assert view["original_publication_at"] is None


def test_legacy_claim_is_preserved_but_not_promoted_to_verified_freshness():
    job = {"posted_at": "2026-11-11T00:00:00+00:00", "observed_at": OBSERVED,
           "research": {"publication": {"independently_verified": True}}}
    original = deepcopy(job)
    view = enrich_publication(job)
    assert job == original
    assert view["source_posted_at"] == original["posted_at"]
    assert view["status"] == "unverified_source_claim"
    assert not view["independently_verified"]
    assert enrich_publication({**job, "research": {"publication": view}}) == view


def test_actor_mapping_retains_only_bounded_date_evidence():
    job = actor_job({"id": "9999901234", "title": "Analyst", "publishedAt": "2026-10-20",
                     "postedTime": "Reposted 2 days ago", "posterEmail": "private@example.org",
                     "rawHTML": "do not persist"})
    assert job and job.publication_source
    assert len(job.publication_source["claims"]) == 2
    assert "private@example" not in str(job.model_dump())
    assert "rawHTML" not in str(job.model_dump())


@pytest.mark.parametrize("malformed", [None, True, "postedAtTimestamp", {}, 1])
def test_malformed_rejected_fields_do_not_crash_or_echo_values(malformed):
    view = enrich_publication({"publication_source": {"claims": [], "rejected_fields": malformed},
                               "observed_at": OBSERVED})
    assert view["status"] == "unknown"
    assert view["rejected_fields"] == []


def test_publication_metadata_limits_repeated_untrusted_items():
    source = {"claims": [{"field": "publishedAt", "value": "2026-10-20"}] * 1000,
              "rejected_fields": ["postedAtTimestamp"] * 1000}
    view = enrich_publication({"publication_source": source, "observed_at": OBSERVED})
    assert len(view["claims"]) <= 6
    assert len(view["rejected_fields"]) <= 6


def test_calendar_month_variation_does_not_create_false_date_conflict():
    # January 31 to February 28 is one calendar month but fewer than 30 days.
    observed = "2026-02-28T12:00:00+00:00"
    date, source = actor_publication({"publishedAt": "2026-01-31T12:00:00+00:00",
                                      "postedTime": "1 month ago"}, observed)
    assert date and not source["conflict"]
    view = enrich_publication({"publication_source": source, "observed_at": observed})
    assert view["original_publication_at"] is None
    assert view["claims"][1]["precision"] == "approximate"


def test_calendar_year_bounds_include_leap_year_variation():
    observed = "2026-02-28T12:00:00+00:00"
    _, source = actor_publication({"postedTime": "1 year ago"}, observed)
    bounds = source["claims"][0]
    assert datetime.fromisoformat(bounds["earliest"]) == datetime(2024, 2, 27, 12, tzinfo=timezone.utc)
    assert datetime.fromisoformat(bounds["latest"]) == datetime(2025, 2, 28, 12, tzinfo=timezone.utc)


def test_implausible_observation_cannot_anchor_relative_publication_or_crash():
    view = enrich_publication({"observed_at": "0001-01-01T00:00:00Z",
                               "publication_source": {"claims": [{"field": "postedTime", "value": "1 year ago"}]}})
    assert view["status"] == "unknown"
    assert view["claims"] == []
    assert view["original_publication_at"] is None
