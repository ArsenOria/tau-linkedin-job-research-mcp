from copy import deepcopy

from tau_scout.facts import enrich_job
from tau_scout.matching import filtered
from tau_scout.models import RefineFilters


def row(description, company="Careers Community"):
    return {"title": "Data Placement", "description": description, "company": company,
            "source_company": company, "workplace": "unknown", "source": "import",
            "external_id": "123456789", "url": "https://www.linkedin.com/jobs/view/123456789/",
            "observed_at": "2026-06-01T12:00:00+00:00"}


def test_named_employer_speaker_resolves_publisher_without_claiming_verification():
    source = row("About the programme\nThis is a data placement.\nAt the Central Research Bank, we support students.\nCareers Community advertise roles on behalf of our partners, alliances, and members.")
    original = deepcopy(source)
    result = enrich_job(source)
    assert result["employer"] == "Central Research Bank"
    assert result["publisher"] == "Careers Community"
    assert result["source_company"] == "Careers Community"
    assert result["company"] == "Careers Community"
    facts = result["research"]["employer"]
    assert facts["status"] == "description_claim"
    assert facts["source_role"] == "publisher"
    assert facts["verified"] is False
    assert any("At the Central Research Bank" in item["quote"] for item in facts["evidence"])
    assert source == original
    assert enrich_job(result) == result


def test_partnering_recruiter_for_unnamed_client_is_not_employer():
    result = enrich_job(row("Horizon is partnering with a well-established media business, as they look for a Data Analyst to sit inside their growth team.", "Horizon Talent"))
    assert result["employer"] is None
    assert result["publisher"] == "Horizon Talent"
    assert result["research"]["employer"]["source_role"] == "recruiter"
    assert result["research"]["employer"]["status"] == "unresolved"
    assert enrich_job(result) == result


def test_working_with_an_unnamed_hiring_organization_is_unresolved():
    result = enrich_job(row("We're working with a leading organisation within insurance who are looking to appoint a Data Analyst.", "Career Partners"))
    assert result["employer"] is None
    assert result["publisher"] == "Career Partners"


def test_named_client_is_not_invented_as_legal_employer():
    result = enrich_job(row("Für unseren Kunden Example Pharma in Berlin suchen wir einen Data Analyst.", "Staffing Partner"))
    assert result["employer"] is None
    assert result["publisher"] == "Staffing Partner"
    assert result["research"]["employer"]["client_organizations"] == ["Example Pharma"]
    assert result["research"]["employer"]["employment_relationship"] == "unverified_client_relationship"


def test_multiple_distinct_named_employer_claims_stay_unresolved():
    result = enrich_job(row("We advertise roles on behalf of our partners.\nAt Aurora Research, we build models.\nAt Northern Analytics, we develop software."))
    assert result["employer"] is None
    assert result["research"]["employer"]["conflict"] is True
    assert set(result["research"]["employer"]["candidate_employers"]) == {"Aurora Research", "Northern Analytics"}


def test_explicit_input_employer_roundtrips_despite_unresolved_recruitment_copy():
    source = row("We are hiring for our client.", "Hiring Hub")
    source.update(employer="Explicit Employer Ltd", publisher="Hiring Hub")
    result = enrich_job(source)
    assert result["employer"] == "Explicit Employer Ltd"
    assert enrich_job(result) == result
    assert result["research"]["employer"]["verified"] is False


def test_consulting_client_work_does_not_imply_recruiter():
    result = enrich_job(row("We help our clients analyse data. You will work directly with customers to improve reporting. We are recruiting a Data Analyst for our team.", "Technical Consulting"))
    assert result["employer"] == "Technical Consulting"
    assert result["publisher"] is None


def test_internal_hiring_for_a_team_or_role_keeps_source_employer():
    for description in ["We are hiring for our internal analytics team.",
                        "We are recruiting for a Data Analyst role in our own organisation.",
                        "We are hiring for our company.",
                        "We are recruiting for our organisation.",
                        "Our team is hiring for an internship."]:
        result = enrich_job(row(description, "Example Employer"))
        assert result["employer"] == "Example Employer"
        assert result["publisher"] is None
        assert result["research"]["employer"]["source_role"] == "employer"


def test_hiring_for_an_explicit_external_organization_remains_unresolved():
    for description in ["We are hiring on behalf of our client.",
                        "We are recruiting for a leading media company.",
                        "We are hiring for our insurance client."]:
        result = enrich_job(row(description, "Talent Source"))
        assert result["employer"] is None
        assert result["publisher"] == "Talent Source"
        assert result["research"]["employer"]["source_role"] == "recruiter"


def test_company_filter_uses_resolved_employer_not_publisher():
    source = row("We publish jobs on behalf of our partners.\nAt Aurora Analytics, we work on data.")
    assert len(filtered([source], RefineFilters(companies=["Aurora Analytics"]))) == 1
    assert filtered([source], RefineFilters(companies=["Careers Community"])) == []


def test_international_unnamed_client_signals_are_not_company_identity():
    for description in ["Notre client est une entreprise qui recherche un analyste.",
                        "Per un cliente in ambito IT cerchiamo un analista.",
                        "Szukamy pracownika dla naszego klienta z branży technologicznej."]:
        result = enrich_job(row(description, "Talent Source"))
        assert result["employer"] is None
        assert result["publisher"] == "Talent Source"


# Adjacent confirmed source-language issue found during the same forty-row
# replay: explicit experience must not disappear because punctuation/language
# differs from the initial English/German subset.
def test_spanish_experience_range_is_required_minimum_not_maximum():
    result = enrich_job(row("Experiencia de 1 a 3 años en análisis de datos, mejora de procesos, sistemas o transformación digital."))
    facts = result["research"]["experience"]
    assert facts["min_years"] == 1
    assert facts["max_years"] == 3
    assert facts["strength"] == "required"


def test_french_experience_bounds_and_optional_requirements():
    cases = [("Vous justifiez d'au moins 5 ans d'expérience en analyse de données.", 5, None, "required"),
             ("Expérience de 3 à 5 ans en analyse de données.", 3, 5, "required"),
             ("3 ans d’expérience souhaitée.", 3, None, "preferred"),
             ("Experiencia de 2 años deseable.", 2, None, "preferred")]
    for description, minimum, maximum, strength in cases:
        facts = enrich_job(row(description))["research"]["experience"]
        assert (facts["min_years"],facts["max_years"],facts["strength"]) == (minimum,maximum,strength)


def test_approximate_possessive_english_experience_is_not_hard_requirement():
    for apostrophe in ["'", "’"]:
        facts = enrich_job(row(f"Around 1-2 years{apostrophe} experience and ready for the next step up."))["research"]["experience"]
        assert (facts["min_years"],facts["max_years"],facts["strength"]) == (1,2,"preferred")


def test_company_age_and_nonrequired_foreign_experience_are_not_minimums():
    for description in ["Notre entreprise a 5 ans d'existence.",
                        "La empresa fue fundada hace 5 años.",
                        "Experiencia de 3 años no requerida.",
                        "3 ans d'expérience non requise."]:
        facts = enrich_job(row(description))["research"]["experience"]
        assert facts["min_years"] is None
