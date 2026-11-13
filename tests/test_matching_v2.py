"""Constraint and terminology regressions independent of the live sample."""
from copy import deepcopy

import pytest

from tau_scout.matching import filtered, match, ranked
from tau_scout.models import Candidate, RefineFilters
from tau_scout.skills import canonical_skill, mentions, required_skills


def job(title="Product Analyst", description="SQL", **extra):
    return {"title": title, "description": description, "company": "Example",
            "external_id": "9999900701", "workplace": "unknown", "location": "Berlin",
            **extra}


@pytest.mark.parametrize("value,canonical", [
    ("A/B tests", "A/B testing"), ("A/B test design", "A/B testing"),
    ("A-B-Testing", "A/B testing"), ("PowerBI", "Power BI"),
    ("Microsoft Power BI", "Power BI"), ("Postgres", "PostgreSQL"),
    ("Data modelling", "data modeling"), ("Python 3", "Python"),
])
def test_aliases_have_a_stable_canonical_skill(value, canonical):
    assert canonical_skill(value) == canonical


def test_aliases_do_not_inflate_the_scoring_denominator():
    result = match(job(description="PowerBI"), Candidate(skills=[
        "Power BI", "Microsoft Power BI", "Postgres", "PostgreSQL"]))
    assert result["heuristic_score"] == 50
    assert result["normalized_candidate_skills"] == ["Power BI", "PostgreSQL"]
    assert result["matched_candidate_skills"] == ["Power BI"]
    assert result["unmatched_candidate_skills"] == ["Postgres"]


def test_skill_evidence_distinguishes_title_from_description():
    result = match(job(title="SQL Analyst", description="Power BI reporting."), Candidate(skills=["SQL", "Power BI"]))
    proofs = {item["canonical_skill"]: item["evidence"] for item in result["matched_skill_evidence"]}
    assert proofs["SQL"][0]["source"] == "title"
    assert proofs["Power BI"][0]["source"] == "description"


@pytest.mark.parametrize("description,skill,found", [
    ("NoSQL experience", "SQL", False), ("SQLAlchemy development", "SQL", False),
    ("No SQL experience required.", "SQL", False),
    ("SQL is not required.", "SQL", False),
    ("SQL and Python are not required.", "SQL", False),
    ("SQL and Python are not required.", "Python", False),
    ("SQL is required and Python is not required.", "SQL", True),
    ("SQL is not required, but Python is required.", "Python", True),
    ("Not SQL but Python is required.", "SQL", False),
    ("Not SQL but Python is required.", "Python", True),
    ("Not only SQL but also Python is required.", "SQL", True),
    ("Not only SQL but also Python is required.", "Python", True),
    ("R&D team", "R", False),
])
def test_negative_and_positive_skill_evidence_remain_distinct(description, skill, found):
    assert bool(mentions(description, skill)) is found


def test_optional_skill_does_not_erase_a_separate_required_skill():
    requirements = required_skills("Requirements\nPython preferred, SQL required.")
    assert [item["skills"] for item in requirements] == [["SQL"]]
    assert required_skills("Requirements\nSQL, Python or R preferred.") == []
    assert required_skills("Requirements\nSQL and Python are not required.") == []
    assert [item["skills"] for item in required_skills(
        "What You Bring\nPower BI, SQL and Excel; Python or R is an advantage.\nWhy join us\nTraining."
    )] == [["Power BI"], ["SQL"], ["Excel"]]


def test_alternative_skill_requirements_do_not_require_every_option():
    result = match(job(description="Requirements\nSQL and either R or Python.\nBenefits\nTraining."),
                   Candidate(skills=["SQL", "Python"], target_titles=["Product Analyst"]))
    assert result["missing_required_skills"] == []
    assert result["recommendation"] == "prioritize"


def test_known_experience_and_seniority_conflicts_cannot_lead_the_shortlist():
    candidate = Candidate(skills=["Excel", "Power BI"], target_titles=["Junior Data Analyst"],
                          experience_years=0.5, target_seniority="junior")
    senior = job(title="Manager Data Analyst", description="Requirements\nAt least 5 years of experience in analytics.\nExcel and Power BI.")
    weak = job(title="Junior Research Assistant", description="A training opportunity.", external_id="9999900702")
    result = ranked([senior, weak], candidate)
    assert result[0]["job"]["external_id"] == weak["external_id"]
    blocked = result[1]
    assert blocked["heuristic_score"] > result[0]["heuristic_score"]
    assert blocked["ranking_score"] == 0
    assert blocked["constraint_status"] == "conflict"
    assert blocked["recommendation"] == "deprioritize"
    assert any("5" in item for item in blocked["conflicts"])
    assert not any(item["recommendation"] == "prioritize" for item in result)


def test_experience_range_upper_is_not_a_maximum_and_preferred_is_not_required():
    experienced = Candidate(experience_years=8, skills=["SQL"], target_titles=["Product Analyst"])
    result = match(job(description="Requirements\n2-5 years of experience in analytics.\nSQL."), experienced)
    assert result["constraint_status"] != "conflict"
    preferred = match(job(description="Requirements\n5 years of experience preferred.\nSQL."),
                      Candidate(experience_years=1, skills=["SQL"], target_titles=["Product Analyst"]))
    assert preferred["conflicts"] == []
    assert preferred["recommendation"] == "investigate"


def test_undisclosed_years_are_unknown_not_a_failure():
    result = match(job(description="Requirements\nAt least 3 years of experience.\nSQL."),
                   Candidate(skills=["SQL"], target_titles=["Product Analyst"]))
    assert result["conflicts"] == []
    assert result["constraint_status"] == "needs_verification"
    assert any("not supplied" in item for item in result["critical_unknowns"])


@pytest.mark.parametrize("arrangement", ["Office-first in Berlin.", "Location: Berlin, Hybrid"])
def test_explicit_office_and_hybrid_conflict_with_required_remote(arrangement):
    result = match(job(description="SQL. " + arrangement),
                   Candidate(skills=["SQL"], target_titles=["Product Analyst"], workplace="remote", remote_from_country="DE"))
    assert result["recommendation"] == "deprioritize"
    assert result["constraint_status"] == "conflict"
    assert result["evidence"]


@pytest.mark.parametrize("policy", ["Fully remote within Germany.", "Fully remote within Europe.", "Fully remote worldwide."])
def test_explicit_remote_geography_supports_fit_but_not_legal_eligibility(policy):
    result = match(job(description=policy + "\nRequirements\nSQL."),
                   Candidate(skills=["SQL"], target_titles=["Product Analyst"], workplace="remote", remote_from_country="DE"))
    assert result["remote_geography"] == "supported_by_posting"
    assert result["constraint_status"] == "no_known_conflict"
    assert any("authorization" in item.lower() for item in result["unknowns"])


def test_explicit_country_mismatch_is_not_hidden_by_keyword_overlap():
    result = match(job(description="Fully remote within France. SQL and Python."),
                   Candidate(skills=["SQL", "Python"], target_titles=["Product Analyst"], workplace="remote", remote_from_country="DE"))
    assert result["heuristic_score"] == 100
    assert result["recommendation"] == "deprioritize"
    assert result["remote_geography"] == "conflict"


def test_explicit_excluded_country_is_a_conflict_even_when_remaining_geography_is_ambiguous():
    result = match(job(description="Fully remote worldwide except France. SQL."),
                   Candidate(skills=["SQL"], target_titles=["Product Analyst"], workplace="remote", remote_from_country="FR"))
    assert result["recommendation"] == "deprioritize"
    assert result["remote_geography"] == "conflict"


def test_timezone_and_missing_residence_country_do_not_confirm_employment_geography():
    posting = job(description="Full remote within CET time ±3h. SQL.")
    result = match(posting, Candidate(skills=["SQL"], target_titles=["Product Analyst"], workplace="remote", remote_from_country="DE"))
    assert result["remote_geography"] == "unverified"
    assert result["recommendation"] == "investigate"
    missing = match(job(description="Fully remote within Germany. SQL."),
                    Candidate(skills=["SQL"], target_titles=["Product Analyst"], locations=["Berlin"], workplace="remote"))
    assert missing["remote_geography"] == "candidate_country_unknown"
    assert missing["conflicts"] == []


def test_missing_required_domain_and_skill_evidence_are_not_claimed_absent_abilities():
    result = match(job(description="Requirements\n4+ years in analytical roles within gaming.\nSQL and Python."),
                   Candidate(skills=["SQL"], target_titles=["Product Analyst"], experience_years=4, domains=["product analytics"]))
    assert result["conflicts"] == []
    assert result["recommendation"] == "investigate"
    assert "Python" in result["missing_required_skills"]
    assert any("gaming" in item for item in result["critical_unknowns"])
    assert "not proof" in result["interpretation"]


def test_remote_filter_uses_evidence_and_company_filter_uses_employer_not_publisher():
    original = job(title="UX &amp; Research Analyst", company="careers.example.com",
                   description="Fictional Example GmbH – Join our team!\nFully remote within Germany.")
    before = deepcopy(original)
    result = filtered([original], RefineFilters(workplace="remote", companies=["Fictional Example GmbH"]))
    assert len(result) == 1
    assert result[0]["publisher"] == "careers.example.com"
    assert result[0]["employer"] == "Fictional Example GmbH"
    assert result[0]["title"] == "UX & Research Analyst"
    assert filtered([original], RefineFilters(companies=["careers.example.com"])) == []
    assert original == before


def test_no_new_facts_are_needed_for_old_candidate_and_saved_job_shapes():
    original = job(description="SQL")
    result = match(original, Candidate(skills=["SQL"]))
    assert result["heuristic_score"] == 100
    assert original.get("research") is None


@pytest.mark.parametrize("text", ["No sponsorship restrictions apply; we can sponsor visas.",
                                  "No sponsorship required for local applicants."])
def test_sponsorship_negation_does_not_invent_an_availability_denial(text):
    result = match(job(description=text + " SQL."), Candidate(skills=["SQL"], requires_sponsorship=True))
    assert result["conflicts"] == []


def test_explicit_sponsorship_unavailability_is_not_silenced():
    result = match(job(description="We cannot provide visa sponsorship. SQL."),
                   Candidate(skills=["SQL"], requires_sponsorship=True))
    assert result["recommendation"] == "deprioritize"
