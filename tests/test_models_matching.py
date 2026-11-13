import os
import stat

import pytest
from pydantic import ValidationError

from tau_scout.config import Settings
from tau_scout.errors import ScoutError
from tau_scout.matching import filtered, match
from tau_scout.models import Candidate, JobInput, RefineFilters, SearchBrief
from tau_scout.normalize import actor_job
from tau_scout.service import Scout


def test_import_identity_and_unknowns(tmp_path):
    scout = Scout(Settings(tmp_path))
    job = JobInput(title="Analyst", url="https://www.linkedin.com/jobs/view/analyst-9999900001/?tracking=ignore")
    result = scout.import_jobs([job, job])
    assert result["count"] == 1
    saved = scout.get_saved_results(result["search_id"])["jobs"][0]
    assert saved["url"] == "https://www.linkedin.com/jobs/view/9999900001/"
    assert saved["easy_apply"] is None and saved["posted_at"] is None
    assert saved["observed_at"]
    assert stat.S_IMODE(tmp_path.stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "scout.sqlite3").stat().st_mode) == 0o600


@pytest.mark.parametrize("fields", [
    {"external_id": "9999900001", "url": "https://evil.example/jobs/view/9999900001/"},
    {"external_id": "9999900001", "url": "https://www.linkedin.com/jobs/view/9999900002/"},
    {"url": "file:///private/secret"},
    {"url": "https://token@www.linkedin.com/jobs/view/9999900001/"},
    {"url": "https://de.linkedin.com.evil.example/jobs/view/9999900001/"},
    {"url": "https://evil-linkedin.com/jobs/view/9999900001/"},
    {"url": "https://token@de.linkedin.com/jobs/view/9999900001/"},
])
def test_import_disallows_non_job_or_conflicting_identity(fields):
    with pytest.raises(ValidationError):
        JobInput(title="Analyst", **fields)


@pytest.mark.parametrize("host", ["de.linkedin.com", "uk.linkedin.com", "fr.linkedin.com", "www.linkedin.com"])
def test_regional_actor_job_urls_are_canonicalized_without_losing_jobs(host):
    job = actor_job({"id": "9999900001", "title": "Product Analyst",
                     "jobUrl": f"https://{host}/jobs/view/product-analyst-at-example-9999900001?trk=public_jobs",
                     "companyName": "Example", "applyType": "EXTERNAL"})
    assert job is not None
    assert job.external_id == "9999900001"
    assert job.url == "https://www.linkedin.com/jobs/view/9999900001/"
    assert job.easy_apply is False


@pytest.mark.parametrize("field,value", [("max_results", 0), ("max_results", 101), ("max_charge_usd", 0),
                                         ("max_charge_usd", 5.01), ("max_charge_usd", float("nan")),
                                         ("max_results", True)])
def test_search_caps_cannot_be_bypassed(field, value):
    with pytest.raises(ValidationError):
        SearchBrief(target_titles=["Analyst"], locations=["Berlin"], **{field: value})


def test_normalization_malformed_fields_and_no_forced_easy_apply():
    job = actor_job({"id": "9999900001", "title": "Analyst", "salaryMin": "NaN", "salaryMax": -1,
                     "postedAtTimestamp": 10**100, "publishedAt": "yesterday", "workType": "unknown"})
    assert job.salary_min is None and job.salary_max is None
    assert job.posted_at is None and job.easy_apply is None
    assert actor_job({"id": "not-an-id", "title": "Analyst"}) is None


def test_ranking_is_lexical_and_does_not_infer_eligibility():
    job = actor_job({"id": "9999900001", "title": "Product Analyst", "description": "NoSQL and Tableau", "workType": "Remote"})
    result = match(job.model_dump(), Candidate(skills=["SQL", "Tableau"], target_titles=["Product Analyst"], requires_sponsorship=True))
    assert result["matched_candidate_skills"] == ["Tableau"]
    assert result["unmatched_candidate_skills"] == ["SQL"]
    assert result["heuristic_score"] == 80
    assert any("Sponsorship" in item for item in result["unknowns"])
    assert any("countries" in item for item in result["unknowns"])


def test_unknown_fields_do_not_pass_explicit_filters():
    job = actor_job({"id": "9999900001", "title": "Analyst", "companyName": "Example"}).model_dump()
    assert filtered([job], RefineFilters(workplace="remote")) == []
    assert filtered([job], RefineFilters(easy_apply_only=True)) == []
    selected = filtered([job], RefineFilters(companies=["example"]))
    assert [row["external_id"] for row in selected] == [job["external_id"]]
    assert selected[0]["employer"] == "Example"
    assert filtered([job], RefineFilters(exclude_companies=["example"])) == []


def test_existing_shared_directory_is_not_chmodded(tmp_path):
    directory = tmp_path / "shared"
    directory.mkdir(mode=0o755)
    with pytest.raises(ScoutError, match="permissions were not changed"):
        Scout(Settings(directory))
    assert stat.S_IMODE(directory.stat().st_mode) == 0o755
    assert not (directory / "scout.sqlite3").exists()
