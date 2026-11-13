"""Evidence-aware research ordering, never a hiring or interview probability.

Lexical relevance retains its independent 60-title/40-skill scale. Ranking deducts
bounded uncertainty penalties, assigns known conflicts zero, and always sorts
conflicts below non-conflicts. Missing facts never confirm legal eligibility.
"""
import re

from .facts import enrich_job
from .models import Candidate, RefineFilters
from .programs import enrich_program, grade_rank, program_affinity, seeks_student_program
from .skills import canonical_domain, clean, mentions, required_skills, unique_skills

EU = set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())
CORE_EUROPE = EU | set("AL AD BA BY GB CH IS LI MC MD ME MK NO RS SM UA VA".split())
NON_EUROPE = set("US CA MX BR AR CL CO AU NZ JP CN IN SG HK ZA AE IL KR ID MY PH VN TH".split())


def contains(haystack: str, term: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(clean(term).casefold()) + r"(?!\w)", clean(haystack).casefold()))


def _region_membership(country: str, region: str) -> bool | None:
    if region == "worldwide":
        return True
    if region == "europe":
        return True if country in CORE_EUROPE else False if country in NON_EUROPE else None
    if region == "eu":
        return True if country in EU else False if country in (CORE_EUROPE | NON_EUROPE) else None
    return None


def _remote_geography(country: str, policy: dict) -> bool | None:
    if country in {str(item).upper() for item in policy.get("excluded_countries", [])}:
        return False
    countries = {str(item).upper() for item in policy.get("allowed_countries", [])}
    regions = policy.get("allowed_regions", [])
    if country in countries:
        return True
    membership = [_region_membership(country, str(region).lower()) for region in regions]
    if True in membership:
        return True
    if regions and any(item is None for item in membership):
        return None
    if countries or regions:
        return False if country in (CORE_EUROPE | NON_EUROPE) else None
    return None


def _target_seniority(candidate: Candidate) -> str | None:
    supplied = getattr(candidate, "target_seniority", None)
    if supplied:
        return supplied
    levels = set()
    for title in candidate.target_titles:
        for level in ("intern", "junior", "mid", "senior", "lead", "manager", "executive"):
            if contains(title, level):
                levels.add(level)
    return next(iter(levels)) if len(levels) == 1 else None


def _dedupe(values):
    return list(dict.fromkeys(values))


def match(job: dict, candidate: Candidate) -> dict:
    job = enrich_job(job)
    research = job.get("research", {})
    program = research.get("program") or enrich_program(job)
    student_path = program_affinity(program, candidate)
    description = str(job.get("description") or "")
    supplied = unique_skills(candidate.skills)
    evidence_by_skill = {canonical: mentions(job["title"], canonical, source="title") + mentions(description, canonical)
                         for _, canonical in supplied}
    matched = [original for original, canonical in supplied if evidence_by_skill[canonical]]
    unmatched = [original for original, canonical in supplied if not evidence_by_skill[canonical]]
    matched_canonical = {canonical for _, canonical in supplied if evidence_by_skill[canonical]}
    candidate_canonical = {canonical for _, canonical in supplied}
    matched_titles = [title for title in candidate.target_titles if contains(job["title"], title)]
    title_score = 0.0
    if candidate.target_titles:
        actual = set(re.findall(r"\w+", job["title"].casefold()))
        title_score = max(len(actual & set(re.findall(r"\w+", title.casefold()))) /
                          max(1, len(set(re.findall(r"\w+", title.casefold())))) for title in candidate.target_titles)
    factors = []
    if candidate.target_titles:
        factors.append((title_score, 60))
    if supplied:
        factors.append((len(matched_canonical) / len(supplied), 40))
    lexical = round(sum(value * weight for value, weight in factors) / sum(weight for _, weight in factors) * 100) if factors else None
    conflicts, reasons, critical, evidence = [], [], [], []
    penalties = []
    unknowns = ["Listing availability has not been independently verified.",
                "Candidate work authorization has not been verified."]

    def add_evidence(field):
        for item in research.get(field, {}).get("evidence", []):
            if item.get("quote"):
                value = {"field": field, "source": item.get("source", "description"), "quote": item["quote"]}
                if value not in evidence:
                    evidence.append(value)

    experience = research.get("experience", {})
    years = getattr(candidate, "experience_years", None)
    minimum = experience.get("min_years")
    strength = experience.get("strength", "unknown")
    if experience.get("conflict"):
        critical.append("The posting's experience requirements are ambiguous or conflicting; verify their scope.")
        penalties.append(("ambiguous_experience", 8))
        add_evidence("experience")
    elif minimum is not None:
        add_evidence("experience")
        if years is None:
            critical.append("Candidate experience years were not supplied; the stated experience expectation cannot be checked.")
            penalties.append(("experience_unknown", 6))
        elif years < minimum:
            message = f"Posting states {minimum:g}+ years; candidate explicitly supplies {years:g} years."
            if strength == "required":
                conflicts.append(message)
            else:
                critical.append(message + " This is preferred/uncertain experience, not a hard rejection.")
                penalties.append(("experience_expectation_gap", 8))
        else:
            reasons.append(f"Supplied {years:g} experience years meet the stated {minimum:g}-year minimum; this does not verify every domain requirement.")

    target_level = _target_seniority(candidate)
    job_level = research.get("seniority", {}).get("level")
    if target_level and job_level:
        add_evidence("seniority")
        if target_level in {"intern", "junior"} and job_level in {"senior", "lead", "manager", "executive"}:
            conflicts.append(f"Explicit {target_level} target conflicts with the posting's {job_level} role level.")
        elif target_level != job_level and not (job_level == "intern" and seeks_student_program(candidate)):
            critical.append(f"Posting level is {job_level}, while the supplied target is {target_level}; review role scope.")
            penalties.append(("role_level_review", 6))

    program_checks = []
    program_critical, program_conflicts = [], []
    degree_requirements = {item["value"] for item in program.get("requirements", [])
                           if item["kind"] == "degree_completed" and item["strength"] == "required"}
    for requirement in program.get("requirements", []):
        field, expected = requirement["kind"], requirement["value"]
        cohort = f"{expected[0]}–{expected[1]}" if field == "graduation_year" else ""
        supplied_value = getattr(candidate, field, None)
        assessment = "not_assessed"
        message = None
        if field == "student":
            supplied_value = candidate.is_student
        if field == "degree_completed" and len(degree_requirements) > 1:
            assessment = "unknown"
            message = "Degree-completion requirements conflict within the posting; verify the applicable route."
        elif supplied_value is None:
            assessment = "unknown"
            message = {
                "student": "The programme requires current student status; enrollment was not supplied.",
                "degree_completed": "The posting's degree-completion requirement cannot be checked from the supplied facts.",
                "placement_year_available": "The programme requires a placement year permitted by the degree; this has not been established.",
                "completed_study_years": f"The programme requires {expected} completed study years; completed years were not supplied and are not inferred from graduation year.",
                "grade_classification": f"The programme states a {expected} degree/grade expectation; equivalent attainment has not been established.",
                "graduation_year": f"The programme's graduation cohort is {cohort}; the candidate's graduation year was not supplied.",
            }.get(field, "Programme eligibility requires verification.")
        else:
            if field == "completed_study_years":
                meets = supplied_value >= expected
            elif field == "graduation_year":
                meets = expected[0] <= supplied_value <= expected[1]
            elif field == "grade_classification":
                actual_grade, expected_grade = grade_rank(supplied_value), grade_rank(expected)
                meets = actual_grade >= expected_grade if actual_grade is not None and expected_grade is not None else None
            else:
                meets = supplied_value == expected
            if meets is True:
                assessment = "supported_by_supplied_facts"
            elif meets is None or requirement.get("alternative"):
                assessment = "unknown"
                message = "The posting permits an alternative qualification or uses an incomparable grade; that route is not established by the supplied facts."
            else:
                assessment = "conflict" if requirement["strength"] == "required" else "unknown"
                message = {
                    "student": "The programme requires a current student; the candidate explicitly says they are not enrolled.",
                    "degree_completed": "The posting requires a completed degree; the candidate explicitly supplies an incomplete degree." if expected else "The programme requires not already holding a degree; the candidate explicitly supplies a completed degree.",
                    "placement_year_available": "The programme requires a placement year; the candidate explicitly says that a placement year is unavailable.",
                    "completed_study_years": f"The programme requires {expected} completed study years; the candidate supplies {supplied_value}.",
                    "grade_classification": f"The stated {expected} grade expectation is not met by the supplied {supplied_value} classification.",
                    "graduation_year": f"The required graduation cohort is {cohort}; the candidate supplies {supplied_value}.",
                }.get(field, "The supplied facts conflict with a programme requirement.")
                if requirement["strength"] != "required":
                    message += " This is a preference, not a hard exclusion."
        program_checks.append({"field":field, "expected":expected, "strength":requirement["strength"],
                               "candidate_value":supplied_value, "assessment":assessment,
                               "evidence":requirement["evidence"]})
        if message:
            (program_conflicts if assessment == "conflict" else program_critical).append(message)
        proof = requirement["evidence"]
        evidence.append({"field":"program." + field, "source":proof["source"], "quote":proof["quote"]})
    if (program.get("kind") == "placement" and (program.get("duration_months") or 0) >= 6
            and not any(check["field"] == "placement_year_available" for check in program_checks)):
        # A long industry placement is a material commitment, but does not
        # automatically imply that a university mandates a sandwich year.
        if candidate.placement_year_available is None:
            program_critical.append(f"Availability for the stated {program['duration_months']}-month placement and compatibility with studies have not been established.")
        elif candidate.placement_year_available is False:
            program_conflicts.append("The posting is a long placement; the candidate explicitly says a placement year is unavailable.")
    conflicts.extend(program_conflicts)
    critical.extend(program_critical)
    if program_critical:
        penalties.append(("education_program_eligibility_unknown", min(12, 4 * len(_dedupe(program_critical)))))
    program_bonus = 40 if student_path else 0
    if student_path:
        reasons.append("The candidate explicitly seeks internships and the posting is a student programme in a matching role area; this supports research relevance, not programme eligibility.")
        for proof in program.get("evidence", []):
            evidence.append({"field":"program.affinity", "source":proof["source"], "quote":proof["quote"]})

    wanted_domains = {canonical_domain(value) for value in getattr(candidate, "domains", [])}
    required_domains = {canonical_domain(value) for value in experience.get("domains", [])}
    missing_domains = sorted(required_domains - wanted_domains)
    if missing_domains:
        critical.append("Required/expected experience domains are not evidenced by the supplied profile: " + ", ".join(missing_domains) + ".")
        penalties.append(("domain_not_evidenced", min(12, 6 * len(missing_domains))))
        add_evidence("experience")
    elif required_domains:
        reasons.append("Supplied experience domains overlap the posting's stated domain expectations: " + ", ".join(sorted(required_domains)) + ".")

    missing_requirements = []
    for requirement in required_skills(description):
        alternatives = requirement["skills"]
        if not candidate_canonical.intersection(alternatives):
            missing_requirements.append(" or ".join(alternatives))
            value = {"field": "required_skills", "source": "description", "quote": requirement["quote"]}
            if value not in evidence:
                evidence.append(value)
    if missing_requirements:
        critical.append("Recognized required skills are not evidenced in the supplied profile: " + ", ".join(missing_requirements) + ". Missing evidence is not proof of missing ability.")
        penalties.append(("required_skills_not_evidenced", min(18, 6 * len(missing_requirements))))

    workplace = research.get("workplace", {})
    mode = job.get("workplace", "unknown")
    policy = research.get("remote", {})
    remote_geography = "not_assessed"
    if workplace.get("conflict"):
        critical.append("Source workplace statements conflict; no definitive workplace compatibility is asserted.")
        penalties.append(("ambiguous_workplace", 12))
        add_evidence("workplace")
    elif candidate.workplace != "any":
        if mode == "unknown":
            critical.append("Workplace arrangement is unknown for the requested " + candidate.workplace + " condition.")
            penalties.append(("workplace_unknown", 12))
        elif mode != candidate.workplace:
            conflicts.append(f"Posting states {mode}; the candidate explicitly requests {candidate.workplace}.")
            add_evidence("workplace")
        else:
            reasons.append("Posting has explicit " + mode + " workplace evidence matching the requested arrangement.")
            add_evidence("workplace")
    if mode == "unknown":
        unknowns.append("Workplace arrangement is unknown.")
    if candidate.workplace == "remote" and mode == "remote" and not workplace.get("conflict"):
        country = getattr(candidate, "remote_from_country", None)
        if country and country in {str(item).upper() for item in policy.get("excluded_countries", [])}:
            remote_geography = "conflict"
            conflicts.append(f"The posting explicitly excludes the supplied remote residence country {country}.")
            add_evidence("remote")
        elif policy.get("conflict"):
            critical.append("The posting's remote geography statements conflict; verify their applicability.")
            remote_geography = "unverified"
            penalties.append(("ambiguous_remote_geography", 10))
            add_evidence("remote")
        elif country:
            fit = _remote_geography(country, policy)
            add_evidence("remote")
            if fit is False:
                remote_geography = "conflict"
                conflicts.append(f"The stated remote geography does not include the supplied residence country {country}.")
            elif fit is True:
                remote_geography = "supported_by_posting"
                reasons.append(f"The posting's stated remote geography includes {country}; this does not confirm employment or work authorization.")
            else:
                remote_geography = "unverified"
                critical.append(f"Remote employment from {country} is not established by the saved policy; a timezone rule alone is insufficient.")
                penalties.append(("remote_country_unverified", 10))
        elif policy.get("allowed_countries") or policy.get("allowed_regions") or policy.get("timezone_policy"):
            remote_geography = "candidate_country_unknown"
            critical.append("Candidate remote residence country was not supplied; the posting's geographic policy cannot be checked.")
            penalties.append(("candidate_remote_country_unknown", 6))
        if policy.get("conditional") or workplace.get("conditional"):
            critical.append("The remote arrangement is conditional on role/team or approval; verify that it applies to this vacancy.")
            penalties.append(("conditional_remote", 8))
    if mode == "remote":
        unknowns.append("Remote work does not independently establish permitted countries of employment or legal work authorization.")

    if candidate.requires_sponsorship:
        denied = re.search(r"\b(?:cannot|can't|unable to)\s+(?:sponsor\b|provide\s+(?:visa\s+)?sponsorship\b)|"
                           r"\bno\s+(?:visa\s+)?sponsorship\s+(?:is\s+)?(?:available|offered|provided)\b|"
                           r"\bno visa sponsorship\s*(?=[.!?\n]|$)|"
                           r"\bvisa sponsorship\s+(?:is\s+)?not\s+(?:available|offered|provided)", description, re.I)
        if denied:
            conflicts.append("Candidate requires sponsorship, while the posting explicitly says sponsorship is unavailable.")
            evidence.append({"field": "sponsorship", "source": "description", "quote": description[max(0, denied.start() - 50):denied.end() + 80]})
        else:
            critical.append("Sponsorship availability is unverified; do not infer from silence.")

    if research.get("employer", {}).get("status") == "unresolved":
        critical.append("Employer identity is unresolved; a publisher must not be treated as the employer.")
        penalties.append(("employer_unresolved", 8))
        add_evidence("employer")
    if candidate.target_titles and title_score < 0.5 and not student_path:
        critical.append("The title is only loosely related to the supplied target; review the role's actual scope.")
        penalties.append(("role_affinity_review", 12))

    if job.get("salary_min") is None and job.get("salary_max") is None:
        unknowns.append("Salary is not stated in the saved data.")
    if not job.get("posted_at"):
        unknowns.append("Publication date is unknown; observation time is separate.")
    if candidate.locations and not any(contains(str(job.get("location") or ""), loc) for loc in candidate.locations):
        unknowns.append("The saved location does not explicitly establish the candidate's preferred geography; check it rather than inferring a mismatch.")

    conflicts, critical, reasons = _dedupe(conflicts), _dedupe(critical), _dedupe(reasons)
    adjusted = max(0, min(100, lexical + program_bonus) - sum(value for _, value in penalties)) if lexical is not None else None
    if conflicts and adjusted is not None:
        adjusted = 0
    constraint_status = "conflict" if conflicts else "needs_verification" if critical else "no_known_conflict"
    recommendation = "deprioritize" if conflicts else "prioritize" if adjusted is not None and adjusted >= 65 and not critical else "investigate"
    return {
        "job": job, "heuristic_score": lexical, "ranking_score": adjusted,
        "score_kind": "lexical_relevance_not_interview_probability",
        "ranking_method": "Lexical relevance plus a bounded matching student-program affinity adjustment, minus evidence-gap penalties; known conflicts score zero and sort last. Research priority only, not verified eligibility.",
        "recommendation": recommendation, "constraint_status": constraint_status,
        "conflicts": conflicts, "critical_unknowns": critical, "reasons": reasons,
        "evidence": evidence, "penalties": [{"reason": name, "points": value} for name, value in penalties],
        "remote_geography": remote_geography,
        "program_fit": {"kind":program.get("kind"), "role_affinity":student_path,
                        "affinity_adjustment":program_bonus, "eligibility_checks":program_checks,
                        "eligibility_status":"conflict" if program_conflicts else "needs_verification" if program_critical else "supported_by_supplied_facts" if program_checks else "not_assessed"},
        "matched_candidate_skills": matched, "unmatched_candidate_skills": unmatched,
        "normalized_candidate_skills": [canonical for _, canonical in supplied],
        "matched_skill_evidence": [{"supplied_skill": original, "canonical_skill": canonical,
                                  "evidence": evidence_by_skill[canonical]} for original, canonical in supplied if evidence_by_skill[canonical]],
        "missing_required_skills": missing_requirements,
        "matched_target_titles": matched_titles,
        "concerns": conflicts + critical, "unknowns": _dedupe(unknowns + critical),
        "interpretation": "Unmatched supplied skills are not evidence of missing candidate qualifications. Missing required-skill evidence is not proof of missing ability. Research priority is not an interview probability.",
    }


def ranked(jobs: list[dict], candidate: Candidate) -> list[dict]:
    output = [match(job, candidate) for job in jobs]
    return sorted(output, key=lambda row: (
        row["constraint_status"] == "conflict",
        -(row["ranking_score"] if row["ranking_score"] is not None else -1),
        -(row["heuristic_score"] if row["heuristic_score"] is not None else -1),
    ))


def filtered(jobs: list[dict], filters: RefineFilters) -> list[dict]:
    selected = []
    for original in jobs:
        job = enrich_job(original)
        content = " ".join(str(job.get(k) or "") for k in ("title", "description", "employer", "location"))
        if not all(mentions(content, term) for term in filters.include_terms):
            continue
        if any(mentions(content, term) for term in filters.exclude_terms):
            continue
        employer = str(job.get("employer") or "").casefold()
        if filters.companies and employer not in {clean(s).casefold() for s in filters.companies}:
            continue
        if employer in {clean(s).casefold() for s in filters.exclude_companies}:
            continue
        if filters.locations and not any(contains(str(job.get("location") or ""), loc) for loc in filters.locations):
            continue
        if filters.workplace != "any" and job.get("workplace") != filters.workplace:
            continue
        if filters.easy_apply_only and job.get("easy_apply") is not True:
            continue
        selected.append(job)
    return selected
