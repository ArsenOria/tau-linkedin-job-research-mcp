from copy import deepcopy

import pytest
from pydantic import ValidationError

from tau_scout.facts import enrich_job, experience_facts, workplace_facts
from tau_scout.models import Candidate
from tau_scout.normalize import actor_job


def sample(description, **extra):
    return {"title":"Data Analyst","company":"Example Analytics","description":description,
            "workplace":"unknown",**extra}


def test_enrichment_is_pure_idempotent_and_keeps_source_claims():
    original=sample("You may work remotely within Germany.",title="UX &amp; Analytics Analyst")
    frozen=deepcopy(original)
    result=enrich_job(original)
    assert original==frozen
    assert result==enrich_job(result)
    assert result["title"]=="UX & Analytics Analyst"
    assert result["source_workplace"]=="unknown"
    assert result["workplace"]=="remote"
    assert result["description"]==original["description"]
    assert result["research"]["remote"]["allowed_countries"]==["DE"]
    assert result["research"]["remote"]["conditional"] is False


@pytest.mark.parametrize("description,mode",[
    ("Our role uses an office-first setup in Berlin.","onsite"),
    ("Location: Berlin or Zurich, Hybrid","hybrid"),
    ("This is a hybrid role.","hybrid"),
    ("You can work remotely within Germany.","remote"),
    ("This position can be onsite in Paris or full remote within CET ±3 hours.","remote"),
    ("Our gaming team builds hybrid-casual games as a hybrid publisher.","unknown"),
    ("We use hybrid cloud infrastructure and remote sensing systems.","unknown"),
    ("This role is not hybrid.","unknown"),
    ("Remote work is not available.","onsite"),
    ("No remote experience required.","unknown"),
    ("This is not a fully remote role; we require three days in the office.","hybrid"),
    ("We have no remote work restrictions.","unknown"),
])
def test_workplace_patterns_do_not_confuse_product_with_policy(description,mode):
    workplace,_=workplace_facts(description,"unknown")
    assert workplace["mode"]==mode


def test_full_remote_option_survives_unrelated_gaming_words():
    job=enrich_job(sample("Full remote within CET ±3 hours. Our team makes hybrid-casual games for a hybrid publisher."))
    assert job["workplace"]=="remote"
    assert job["research"]["remote"]["allowed_countries"]==[]
    assert job["research"]["remote"]["timezone_policy"]


@pytest.mark.parametrize("description",[
    "Remote work is offered; our headquarters are in Germany.",
    "Remote work includes annual team meetings in Germany.",
])
def test_countries_in_meetings_or_headquarters_are_not_remote_allowlists(description):
    assert enrich_job(sample(description))["research"]["remote"]["allowed_countries"]==[]


def test_country_tokens_do_not_confuse_pronouns_or_location_substrings():
    assert enrich_job(sample("Remote work within US."))["research"]["remote"]["allowed_countries"]==["US"]
    assert enrich_job(sample("Remote work from us."))["research"]["remote"]["allowed_countries"]==[]
    assert enrich_job(sample("Remote work from Long Island."))["research"]["remote"]["allowed_countries"]==[]


def test_conditional_remote_and_conflicting_source_claims_stay_unverified():
    data=enrich_job(sample("Depending on the team, you can work remotely within Europe."))
    assert data["research"]["remote"]["allowed_regions"]==["europe"]
    assert data["research"]["remote"]["conditional"] is True
    assert enrich_job(sample("Fully remote within Europe.",workplace="onsite"))["workplace"]=="unknown"
    assert enrich_job(sample("Fully remote work. This role is office-first."))["research"]["workplace"]["conflict"]


def test_remote_exceptions_and_conflicting_worldwide_residence_not_flat_allowlists():
    excluded=enrich_job(sample("Remote work worldwide except France."))["research"]["remote"]
    assert excluded["excluded_countries"]==["FR"]
    assert excluded["allowed_regions"]==[] and excluded["conditional"]
    contradictory=enrich_job(sample("Fully remote worldwide. You must reside in Germany."))["research"]["remote"]
    assert contradictory["conflict"] and contradictory["allowed_countries"]==[]
    assert len(contradictory["evidence"])==2
    probation=enrich_job(sample("You may work remotely only after probation."))["research"]["remote"]
    assert probation["conditional"]
    delayed=enrich_job(sample("Remote work is possible only after six months in the office."))["research"]["remote"]
    assert delayed["conditional"]


@pytest.mark.parametrize("description",[
    "We were founded 20 years ago. Benefits include a sabbatical after 3 years of service.",
    "You do not need 5 years of experience.",
    "Our team has 10 years of experience in analytics.",
    "No prior experience required.",
])
def test_nonrequirements_do_not_become_minimum_experience(description):
    assert experience_facts(description)["min_years"] is None


def test_required_years_are_not_contaminated_by_preferred_or_company_years():
    result=experience_facts("Our company was founded 20 years ago. At least 5 years of professional experience required. 2 years of SQL experience preferred.")
    assert result["min_years"]==5
    assert result["strength"]=="required"
    assert not result["conflict"]


def test_domain_qualified_experience_and_quoted_numeric_evidence():
    description="Requirements: At least 3 years of product analytics experience and SQL."
    result=experience_facts(description)
    assert result["min_years"]==3 and result["strength"]=="required"
    assert result["domains"]==["product analytics"]
    assert "3 years" in result["evidence"][0]["quote"]
    long="Relevant background "*40+"at least 4 years of analytics experience."
    result=experience_facts(long)
    assert "4 years" in result["evidence"][0]["quote"]


def test_preferred_years_degree_alternatives_and_upper_bounds_not_hard_minimums():
    preferred=experience_facts("Ideally 5 years of experience in analytics.")
    assert preferred["min_years"]==5 and preferred["strength"]=="preferred"
    alternative=experience_facts("A Bachelor degree or 3 years of equivalent experience.")
    assert alternative["strength"]=="unknown"
    upper=experience_facts("Up to 5 years of professional experience.")
    assert upper["min_years"] is None and upper["max_years"]==5
    paired=experience_facts("A degree in mathematics or a similar field, paired with 5+ years of professional experience (ideally in retail).")
    assert paired["min_years"]==5 and paired["strength"]=="required"
    lower=experience_facts("No less than 5 years of professional experience.")
    assert lower["min_years"]==5 and lower["max_years"] is None
    negative_upper=experience_facts("Not more than 5 years of experience.")
    assert negative_upper["min_years"] is None and negative_upper["max_years"]==5


@pytest.mark.parametrize("description",["3 to 5 years of experience.","Between 3 and 5 years of experience."])
def test_worded_year_ranges_do_not_become_wrong_lower_bounds(description):
    assert experience_facts(description)["min_years"]==3


def test_mobile_domain_is_from_explicit_experience_clause_not_company_name():
    facts=experience_facts("You have relevant experience of 2-3 years in Product Analytics, working with an app.")
    assert "mobile analytics" in facts["domains"]


def test_german_years_domain_and_contradictory_year_claims():
    german=experience_facts("3–5 Jahre Erfahrung als Product Owner – idealerweise im Handel.")
    assert german["min_years"]==3 and german["strength"]=="required"
    game=experience_facts("4+ years in analytical roles within gaming.")
    assert game["domains"]==["gaming"]
    conflict=experience_facts("Minimum 3 years of experience. At least 7 years of experience.")
    assert conflict["min_years"] is None and conflict["conflict"]


def test_publisher_is_not_the_employer_and_description_claim_is_not_verification():
    original=sample("Acme Research GmbH – Join our team!\nWe are hiring analysts.",company="Jobs-in-Example.de")
    result=enrich_job(original)
    assert result["company"]=="Jobs-in-Example.de"
    assert result["source_company"]=="Jobs-in-Example.de"
    assert result["publisher"]=="Jobs-in-Example.de"
    assert result["employer"]=="Acme Research GmbH"
    assert result["research"]["employer"]["status"]=="description_claim"
    assert result["research"]["employer"]["verified"] is False
    assert result==enrich_job(result)


def test_unnamed_client_and_nonpublisher_domains_remain_conservative():
    unnamed=enrich_job(sample("We are hiring for our client.",company="CareerJobs.example.com"))
    assert unnamed["employer"] is None
    assert unnamed["publisher"]=="CareerJobs.example.com"
    assert unnamed["research"]["employer"]["status"]=="unresolved"
    legitimate=enrich_job(sample("We build travel software.",company="Example.com"))
    assert legitimate["employer"]=="Example.com" and legitimate["publisher"] is None


def test_normalized_actor_display_decodes_title_but_preserves_description():
    job=actor_job({"id":"9999900123","title":"UX &amp; Data Analyst","companyName":"Example &amp; Partners",
                   "description":"Literal &amp; source content."})
    assert job.title=="UX & Data Analyst"
    assert job.company=="Example & Partners"
    assert job.source_company=="Example &amp; Partners"
    assert job.description=="Literal &amp; source content."


def test_explicit_candidate_context_is_optional_validated_and_not_inferred():
    plain=Candidate(skills=["SQL"])
    assert plain.experience_years is None and plain.remote_from_country is None
    candidate=Candidate(experience_years=0.5,target_seniority="junior",remote_from_country="de",domains=["gaming"])
    assert candidate.remote_from_country=="DE"
    for invalid in [True,-1,float("nan"),71]:
        with pytest.raises(ValidationError): Candidate(experience_years=invalid)


def test_manager_job_functions_do_not_automatically_become_management_seniority():
    for title in ["Product Manager","Account Manager","Customer Success Manager"]:
        assert enrich_job(sample("",title=title))["research"]["seniority"]["level"] is None
    assert enrich_job(sample("",title="Senior Product Manager"))["research"]["seniority"]["level"]=="senior"
    assert enrich_job(sample("",title="Engineering Manager"))["research"]["seniority"]["level"]=="manager"
