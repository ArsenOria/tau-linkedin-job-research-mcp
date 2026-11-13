"""Exercise derived facts and constraints through the public service boundary."""
from tau_scout.config import Settings
from tau_scout.models import Candidate, JobInput, RefineFilters
from tau_scout.service import Scout


def test_legacy_snapshot_enriched_at_read_time_and_constraints_rank_conflicts_last(tmp_path):
    scout = Scout(Settings(tmp_path))
    imported = scout.import_jobs([
        JobInput(external_id="9999800001", title="Manager Data Analytics",
                 company="Example Office", description=(
                     "Requirements: At least 5 years of experience in data analytics. "
                     "SQL, Excel and Power BI. Location: Berlin, hybrid.")),
        JobInput(external_id="9999800002", title="Product Analyst",
                 company="Example Remote", description=(
                     "Requirements: At least 3 years of product analytics experience and SQL. "
                     "You will design A/B tests. Remote work within Germany.")),
    ])
    sid = imported["search_id"]
    before = scout.store.jobs(sid)
    saved = scout.get_saved_results(sid)
    remote = next(job for job in saved["jobs"] if job["external_id"] == "9999800002")
    assert remote["workplace"] == "remote"
    assert remote["research"]["workplace"]["evidence"]
    # Enrichment cannot rewrite the persisted source or change observation time.
    assert scout.store.jobs(sid) == before
    assert all(job["workplace"] == "unknown" for job in before)
    candidate = Candidate(skills=["SQL", "Excel", "Power BI", "A/B testing"],
                          target_titles=["Product Analyst"], workplace="remote",
                          experience_years=4, target_seniority="mid",
                          remote_from_country="DE", domains=["product analytics"])
    matches = scout.rank_jobs(sid, candidate)["matches"]
    assert matches[0]["job"]["external_id"] == "9999800002"
    blocked = next(row for row in matches if row["job"]["external_id"] == "9999800001")
    assert blocked["constraint_status"] == "conflict"
    assert blocked["recommendation"] == "deprioritize"
    assert blocked["conflicts"] and blocked["evidence"]
    refined = scout.refine_shortlist(sid, RefineFilters(workplace="remote"))
    assert [job["external_id"] for job in refined["jobs"]] == ["9999800002"]

    junior = Candidate(skills=["Excel", "Power BI"], target_titles=["Junior Data Analyst"],
                       experience_years=0.5, target_seniority="junior", requires_sponsorship=True)
    result = scout.rank_jobs(sid, junior, limit=1)
    assert result["no_supported_priority"] is True
    assert result["decision_counts"] == {"prioritize": 0, "investigate": 0, "deprioritize": 2}
    assert len(result["matches"]) == 1  # Counts describe the whole set, not just the page.


def test_employer_filter_does_not_match_job_board_publisher(tmp_path):
    scout = Scout(Settings(tmp_path))
    imported = scout.import_jobs([JobInput(
        external_id="9999800003", title="UX &amp; Usability Analyst",
        company="Jobs-Example.de",
        description="Example Research GmbH – We are hiring! Apply directly at Example Research GmbH.",
    )])
    sid = imported["search_id"]
    saved = scout.get_saved_results(sid)["jobs"][0]
    assert saved["title"] == "UX & Usability Analyst"
    assert saved["employer"] == "Example Research GmbH"
    assert saved["publisher"] == "Jobs-Example.de"
    assert saved["source_company"] == "Jobs-Example.de"
    assert scout.refine_shortlist(sid, RefineFilters(companies=["Example Research GmbH"]))["total"] == 1
    assert scout.refine_shortlist(sid, RefineFilters(companies=["Jobs-Example.de"]))["total"] == 0
