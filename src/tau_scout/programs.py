"""Conservative student-program and education evidence, independent of employers.

Descriptions are claims. Missing education/placement facts remain unknown; a
programme title, start year or subject preference cannot establish eligibility.
"""
from html import unescape
import re


PROGRAM = re.compile(r"\b(?:intern(?:ship)?s?|placement|working student|werkstudent\w*|praktik(?:um|ant\w*)|graduate (?:programme|program|scheme))\b", re.I)
STUDENT = re.compile(r"\b(?:university students?|undergraduates?|placement students?|currently (?:be )?(?:studying|enrolled)|be studying an undergraduate|"
                     r"enrolled\s+(?:at|in)\s+(?:(?:a|an|the)\s+)?(?:university|college)|"
                     r"pursuing\s+(?:(?:a|an)\s+)?(?:bachelor[’']?s?|master[’']?s?|university|undergraduate)\s+degree|"
                     r"immatrikuliert\w*|eingeschrieben\w*)\b", re.I)
OPTIONAL = re.compile(r"\b(?:preferred|preferable|ideally|desirable|is a plus|nice to have|von vorteil|wünschenswert|bevorzugt)\b", re.I)
DOMAINS = {
    "data": re.compile(r"\b(?:data|analytics?|statistical|statistics|daten|analytik)\b", re.I),
    "business": re.compile(r"\b(?:business|wirtschaft\w*)\b", re.I),
    "finance": re.compile(r"\b(?:financ\w*|investment|economics?|ökonom\w*)\b", re.I),
    "software": re.compile(r"\b(?:software|engineering|developer|computer science|informatik)\b", re.I),
    "marketing": re.compile(r"\bmarketing\b", re.I),
    "hr": re.compile(r"\b(?:human resources|HR|recruitment)\b", re.I),
}


def _clauses(description):
    # A degree sentence can contain abbreviations and ratios; avoid splitting at
    # every period or colon (e.g. 2.1, M.Sc., Bachelor's degree: required).
    return [line.strip(" \t*•-") for line in re.split(r"[\n;]+", description) if line.strip()]


def _proof(source, quote):
    return {"source": source, "quote": quote[:600]}


def _body_program(description):
    for line in _clauses(description):
        found = PROGRAM.search(line)
        if not found or OPTIONAL.search(line):
            continue
        if re.search(r"\b(?:previous|prior|past|completed)\s+(?:work\s+)?internships?\b|\binternship\s+experience\b", line, re.I):
            continue
        if (re.search(r"\b(?:recruiting|hiring|seeking)\s+(?:\w+\s+){0,4}(?:interns?|placement students?)\b|"
                      r"\b(?:position|role|opportunity|programme|program)\s+(?:\w+\s+){0,8}(?:internship|placement|students?)\b|"
                      r"\b(?:this|the)\s+(?:is\s+)?(?:a\s+)?(?:\d+[ -]month\s+)?(?:industrial |industry )?placement\b|"
                      r"\b(?:internship|placement)\s+(?:programme|program|for\s+(?:university\s+)?students)\b", line, re.I)
                or re.fullmatch(r"(?:Non[- ]LDP\s+)?Intern(?:ship)?(?:/Co-Op)?", line, re.I)):
            return found, line
    return None, ""


def _degree_negated(line):
    return bool(re.search(r"\b(?:degree|Studium|Bachelor|Master)\b\s+(?:(?:is\s+)?not|isn[’']t)\s+(?:required|necessary|needed|essential)|"
                          r"\b(?:Studium|Bachelor|Master)\b\s+(?:ist\s+)?nicht\s+erforderlich|"
                          r"\bno\s+(?:bachelor[’']?s?\s+|master[’']?s?\s+|university\s+)?degree\s+(?:is\s+)?(?:required|needed)|"
                          r"\b(?:do not|don[’']t)\s+(?:need|require)\s+(?:(?:to\s+)?(?:have|hold)\s+)?(?:a\s+)?(?:bachelor[’']?s?\s+|master[’']?s?\s+|university\s+)?degree\b|"
                          r"\bneed not\s+(?:have|hold)\s+(?:a\s+)?(?:bachelor[’']?s?\s+|master[’']?s?\s+)?degree\b", line, re.I))


def _enrollment_negated(line):
    return bool(re.search(r"\b(?:not|need not|do not need to|don[’']t need to)\s+(?:be\s+)?(?:currently\s+)?(?:a\s+)?(?:student|enrolled|pursuing|studying)\b|"
                          r"\b(?:not\s+(?:required|necessary|expected)|not\s+essential)\s+to\s+(?:be\s+)?(?:currently\s+)?(?:enrolled|studying|pursuing)\b|"
                          r"\b(?:enrollment|student status)\s+(?:is\s+)?not\s+(?:required|necessary)\b", line, re.I))


def role_domains(text):
    return [name for name, pattern in DOMAINS.items() if pattern.search(text)]


def enrich_program(job):
    """Return additive program/education metadata without mutating the job."""
    title = unescape(str(job.get("title") or ""))
    description = unescape(str(job.get("description") or ""))
    title_program = PROGRAM.search(title)
    body_program, body_quote = _body_program(description)
    found = title_program or body_program
    kind = None
    if found:
        token = found.group(0).lower()
        kind = ("graduate" if "graduate" in token else "working_student" if "werkstudent" in token or "working student" in token
                else "placement" if "placement" in token else "internship")
    evidence = [_proof("title" if title_program else "description", title if title_program else body_quote)] if found else []
    requirements = []

    def requirement(kind, value, line, strength="required", **extra):
        item = {"kind": kind, "value": value, "strength": strength, "evidence": _proof("description", line), **extra}
        if item not in requirements:
            requirements.append(item)

    for line in _clauses(description):
        lower = line.lower()
        # These are eligibility statements, not company age, tenure benefits,
        # or completion of a training module supplied by the employer.
        strength = "preferred" if OPTIONAL.search(line) else "required"
        if kind and STUDENT.search(line) and not _enrollment_negated(line):
            if re.search(r"\b(?:for (?:university )?students|for undergraduates|must|requires?|be studying|currently|seeking|recruiting|designed .{0,30}for undergraduates|position is for university students|immatrikuliert|eingeschrieben)\b", line, re.I):
                requirement("student", True, line, strength)
        if re.search(r"\b(?:placement year (?:built into|as part of)|degree (?:that |which )?allows .{0,35}placement year|degree includes (?:a |an )?(?:industrial )?placement|undergraduate degree .{0,30}allows .{0,30}placement year|sandwich (?:degree|course))\b", line, re.I):
            requirement("placement_year_available", True, line, strength)
        degree_forbidden = re.search(r"\b(?:must not|cannot|should not)\s+(?:already\s+)?(?:have|hold)\s+(?:a |an )?(?:university )?degree\b", line, re.I)
        if degree_forbidden:
            requirement("degree_completed", False, line, strength)
        degree = re.search(r"\b(?:bachelor[’']?s?|master[’']?s?|university|undergraduate)\s+(?:or master[’']?s?\s+)?degree\b|\babgeschlossen\w*\s+(?:Hochschulstudium|Studium|Bachelor|Master)\b|\bfinalizado\s+recientemente\s+un\s+grado\s+o\s+m[aá]ster\b", line, re.I)
        if degree:
            studying = re.search(r"\b(?:studying|pursuing|enrolled|working towards|completion of the first|first (?:two|three|\d+) years|undergraduates?|not .{0,15}degree|allows you|degree (?:that|which) allows|built into|currently|curso|estudiante)\b", line, re.I)
            # A bare degree bullet under requirements counts as a source claim;
            # a description of a degree funded by the employer does not.
            offered = re.search(r"\b(?:we (?:offer|provide)|you (?:will|can) (?:earn|obtain)|subvencionad|obtendr[aá]s|our (?:training|degree)|no .{0,12}degree (?:required|needed))\b", line, re.I)
            if not studying and not offered and not degree_forbidden and not _degree_negated(line):
                strength = "preferred" if OPTIONAL.search(line) and not re.search(r"\bdegree\s*[–—-]\s*preferably\s+in\b", line, re.I) else "required"
                alternative = bool(re.search(r"\b(?:or equivalent|or (?:relevant |equivalent )?(?:experience|qualification|training)|oder (?:vergleichbare|gleichwertige))\b", line, re.I))
                requirement("degree_completed", True, line, strength, alternative=alternative)
        study_years = re.search(r"\b(?:successful )?completion of (?:the )?first (one|two|three|four|[1-9]) years?\b|\b(?:completed|absolviert)\s+(?:at least )?(one|two|three|four|[1-9])\s+(?:years? of (?:university|degree|study)|Studienjahre)\b", line, re.I)
        if study_years:
            raw = study_years.group(1) or study_years.group(2)
            value = {"one":1,"two":2,"three":3,"four":4}.get(raw.lower(), int(raw) if raw.isdigit() else None)
            requirement("completed_study_years", value, line, strength)
        grade = re.search(r"\b(?:minimum (?:of )?(?:a )?|expect(?:ing|ed) (?:a )?|at least (?:a )?)(2\s*[:.]\s*1|2\s*[:.]\s*2|first(?:[- ]class)?)\b", line, re.I)
        if grade:
            requirement("grade_classification", re.sub(r"\s+", "", grade.group(1).lower()).replace(".", ":"), line, strength)
        if re.search(r"\b(?:graduat(?:e|ing|ion)|Abschluss)\b", line, re.I) and not OPTIONAL.search(line):
            cohort = re.search(r"\b(?:graduating|graduate|graduation|Abschluss)\s+(?:(?:date|year|between|in|by|expected|of|is)\s+)*(20\d{2})(?:\s*(?:and|to|through|[-–])\s*(20\d{2}))?", line, re.I)
            if cohort:
                lo = int(cohort.group(1)); hi = int(cohort.group(2) or lo)
                requirement("graduation_year", [min(lo,hi),max(lo,hi)], line)

    # Long placements imply a commitment to check, without inventing a course
    # rule if the posting never stated one.
    duration = None
    if kind == "placement":
        lengths = re.findall(r"\b(\d{1,2})\s*[- ]?months?\b", description, re.I)
        if lengths:
            duration = max(int(value) for value in lengths if 1 <= int(value) <= 36) if any(1 <= int(value) <=36 for value in lengths) else None
    return {"kind":kind, "role_domains":role_domains(title), "duration_months":duration,
            "requirements":requirements, "evidence":evidence, "verified":False}


def seeks_student_program(candidate):
    return candidate.target_seniority == "intern" or any(PROGRAM.search(title) for title in candidate.target_titles)


def program_affinity(program, candidate):
    if program.get("kind") not in {"internship", "placement", "working_student"} or not seeks_student_program(candidate):
        return False
    wanted = set(role_domains(" ".join(candidate.target_titles)))
    offered = set(program.get("role_domains", []))
    return bool(wanted & offered)


def grade_rank(value):
    text = re.sub(r"\s+", "", str(value).lower()).replace(".", ":")
    return {"first":3,"first-class":3,"1st":3,"1stclass":3,"2:1":2,"2:2":1,"third":0}.get(text)
