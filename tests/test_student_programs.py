"""Student eligibility and programme relevance from synthetic source evidence."""
from copy import deepcopy

import pytest

from tau_scout.facts import enrich_job
from tau_scout.matching import match, ranked
from tau_scout.models import Candidate
from tau_scout.programs import enrich_program


def job(title="Data Analyst", description="SQL and Python analysis.", **extra):
    return {"title": title, "description": description, "company": "Example Research",
            "external_id": "9999908801", "workplace": "hybrid", "location": "London",
            "source": "import", "observed_at": "2026-11-11T12:00:00+00:00", **extra}


def student(**extra):
    values = {"skills": ["SQL", "Python"], "target_titles": ["Junior Data Analyst", "Data Analyst Intern"],
              "target_seniority": "junior", "experience_years": 0, "workplace": "hybrid",
              "is_student": True, "degree_completed": False, "graduation_year": 2028,
              "fields_of_study": ["Economics"]}
    values.update(extra)
    return Candidate(**values)


@pytest.mark.parametrize("description", [
    "A bachelor's degree is not required.",
    "A bachelor’s degree isn't necessary.",
    "No university degree is needed.",
    "You do not need a bachelor’s degree.",
    "You don't need to have a university degree.",
    "You need not hold a master's degree.",
    "Ein abgeschlossenes Studium ist nicht erforderlich.",
])
def test_negated_degree_does_not_exclude_an_undergraduate(description):
    result = match(job(description=description), student())
    assert not result["conflicts"]
    assert not any(c["field"] == "degree_completed" for c in result["program_fit"]["eligibility_checks"])


@pytest.mark.parametrize("description", [
    "You do not need to be currently enrolled.",
    "You are not required to be currently enrolled.",
    "It is not necessary to be currently studying.",
    "Student status is not required.",
])
def test_negated_enrollment_does_not_exclude_a_nonstudent(description):
    result = match(job(title="Data Analyst Internship", description=description), student(is_student=False))
    assert not any(c["field"] == "student" for c in result["program_fit"]["eligibility_checks"])
    assert not result["conflicts"]


@pytest.mark.parametrize("description", [
    "Previous internships are a plus.",
    "Prior internship experience is preferred.",
    "Previous internships in data analytics are required.",
])
def test_incidental_prior_internships_do_not_turn_an_ordinary_role_into_a_programme(description):
    result = match(job(description=description), student())
    assert result["job"]["research"]["program"]["kind"] is None
    assert not result["program_fit"]["role_affinity"]
    assert result["program_fit"]["affinity_adjustment"] == 0


def test_relevant_placement_is_ranked_above_generic_role_without_claiming_eligibility():
    programme = job(title="Statistical Data Student Placement", external_id="9999908802", description=(
        "We are recruiting placement students for a 12 month industry placement.\n"
        "Successful completion of the first two years of a degree course.\n"
        "A minimum of a 2:1 achieved in the first year.\nPython analysis."))
    ordinary = job(description="SQL and Python analysis. A bachelor's degree is required.")
    results = ranked([ordinary, programme], student(requires_sponsorship=True))
    first = results[0]
    assert first["job"]["external_id"] == "9999908802"
    assert first["program_fit"]["role_affinity"]
    assert first["ranking_score"] > first["heuristic_score"]
    assert first["recommendation"] == "investigate"
    unknown_fields = {c["field"] for c in first["program_fit"]["eligibility_checks"] if c["assessment"] == "unknown"}
    assert {"completed_study_years", "grade_classification"} <= unknown_fields
    assert any("compatibility with studies" in s for s in first["critical_unknowns"])
    assert not any("while the supplied target is junior" in s for s in first["critical_unknowns"])


def test_explicit_intern_target_accepts_intern_level_without_junior_penalty():
    result = match(job(title="Data Analyst Intern"), student())
    assert result["program_fit"]["role_affinity"]
    assert not any(p["reason"] == "role_level_review" for p in result["penalties"])


def test_programme_bonus_requires_role_relevance_and_explicit_student_search():
    irrelevant = match(job(title="Marketing Intern"), student())
    professional = match(job(title="Data Analyst Intern"), student(target_titles=["Data Analyst"], target_seniority="mid"))
    assert irrelevant["program_fit"]["affinity_adjustment"] == 0
    assert professional["program_fit"]["affinity_adjustment"] == 0


@pytest.mark.parametrize("description", [
    "Requirements\nA bachelor's or master's degree, preferably in an IT-related field.",
    "Requirements\nEin abgeschlossenes Studium.",
    "Personas que hayan finalizado recientemente un grado o máster.",
])
def test_completed_degree_requirement_conflicts_with_explicitly_incomplete_degree(description):
    result = match(job(description=description), student())
    assert result["constraint_status"] == "conflict"
    assert result["ranking_score"] == 0
    assert any("completed degree" in item for item in result["conflicts"])


def test_degree_preference_or_alternative_remains_investigation_not_hard_rejection():
    preferred = match(job(description="A bachelor's degree is preferred."), student())
    alternative = match(job(description="A bachelor's degree or equivalent practical experience."), student())
    assert not preferred["conflicts"] and not alternative["conflicts"]
    assert preferred["program_fit"]["eligibility_status"] == "needs_verification"
    assert alternative["program_fit"]["eligibility_status"] == "needs_verification"


def test_compound_grade_and_no_degree_requirements_are_both_checked():
    source = job(title="Data Placement", description="Expecting a 2.1 degree classification. You must not already have a degree.")
    result = match(source, student())
    checks = {c["field"]: c for c in result["program_fit"]["eligibility_checks"]}
    assert checks["degree_completed"]["expected"] is False
    assert checks["degree_completed"]["assessment"] == "supported_by_supplied_facts"
    assert checks["grade_classification"]["expected"] == "2:1"
    assert checks["grade_classification"]["assessment"] == "unknown"
    graduated = match(source, student(degree_completed=True))
    assert graduated["constraint_status"] == "conflict"


def test_preferred_enrollment_is_not_a_hard_requirement():
    result = match(job(title="Data Internship", description="Currently enrolled university students preferred."), student(is_student=False))
    check = next(c for c in result["program_fit"]["eligibility_checks"] if c["field"] == "student")
    assert check["strength"] == "preferred" and check["assessment"] == "unknown"
    assert not result["conflicts"]


@pytest.mark.parametrize("description", [
    "Applicants must be enrolled in university.",
    "You must be pursuing a bachelor’s degree.",
])
def test_required_university_enrollment_is_not_missed_without_currently_word(description):
    result = match(job(title="Data Internship", description=description), student(is_student=False))
    checks = result["program_fit"]["eligibility_checks"]
    assert any(c["field"] == "student" and c["assessment"] == "conflict" for c in checks)
    assert result["constraint_status"] == "conflict"


def test_explicit_placement_permission_is_distinct_from_unverified_study_years_and_grades():
    source = job(title="Data Placement", description=(
        "Designed for undergraduates with a placement year built into their course.\n"
        "Successful completion of the first two years of a degree course.\nExpected a 2:1 degree classification."))
    unknown = match(source, student())
    assert unknown["program_fit"]["eligibility_status"] == "needs_verification"
    assert not unknown["conflicts"]
    denied = match(source, student(placement_year_available=False))
    assert denied["constraint_status"] == "conflict"
    supported = match(source, student(placement_year_available=True, completed_study_years=2, grade_classification="First"))
    assert supported["program_fit"]["eligibility_status"] == "supported_by_supplied_facts"


def test_grad_cohort_is_checked_but_programme_start_year_is_not_a_cohort():
    cohort = job(title="Data Internship", description="Applicants graduating between 2027 and 2028 are eligible.")
    assert not match(cohort, student())["conflicts"]
    assert match(cohort, student(graduation_year=2029))["conflicts"]
    start = enrich_program(job(title="2027 Data Placement", description="The placement starts July 2027."))
    assert not any(r["kind"] == "graduation_year" for r in start["requirements"])


def test_grades_can_be_supported_conflicting_or_incomparable():
    source = job(title="Data Placement", description="A minimum 2:1 degree classification is required.")
    assert match(source, student(grade_classification="2:1"))["program_fit"]["eligibility_status"] == "supported_by_supplied_facts"
    assert match(source, student(grade_classification="2:2"))["conflicts"]
    incomparable = match(source, student(grade_classification="3.8 GPA"))
    assert not incomparable["conflicts"]
    assert incomparable["program_fit"]["eligibility_status"] == "needs_verification"


def test_programme_enrichment_preserves_source_and_is_idempotent():
    source = job(title="Data Internship", description="We are recruiting interns for a data analysis internship programme.")
    before = deepcopy(source)
    result = enrich_job(source)
    assert source == before
    assert enrich_job(result) == result
    assert result["description"] == before["description"]
    assert result["observed_at"] == before["observed_at"]
