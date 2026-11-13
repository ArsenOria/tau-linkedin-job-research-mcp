"""Conservative, quoted research facts from saved source claims.

This module does not establish employment eligibility, resolve organizations on the
web or execute posting text. Unrecognized and conflicting claims stay unknown.
"""
from copy import deepcopy
from html import unescape
import re

from .publication import enrich_publication
from .programs import enrich_program


COUNTRIES = {
    "DE": r"Germany|Deutschland", "GB": r"United Kingdom|Great Britain|UK",
    "US": r"United States(?: of America)?|USA|(?-i:US)|U\.S\.A?\.?", "CA": r"Canada",
    "FR": r"France|Frankreich", "NL": r"Netherlands|Niederlande", "IE": r"Ireland|Irland",
    "ES": r"Spain|Spanien", "IT": r"Italy|Italien", "PT": r"Portugal",
    "PL": r"Poland|Polen", "AT": r"Austria|Österreich", "CH": r"Switzerland|Schweiz",
    "SE": r"Sweden|Schweden", "NO": r"Norway|Norwegen", "DK": r"Denmark|Dänemark",
    "FI": r"Finland|Finnland", "BE": r"Belgium|Belgien", "AU": r"Australia|Australien",
    "IN": r"India|Indien", "SG": r"Singapore|Singapur",
    "CZ": r"Czechia|Czech Republic|Tschechien", "RO": r"Romania|Rumänien",
    "HU": r"Hungary|Ungarn", "BG": r"Bulgaria|Bulgarien", "GR": r"Greece|Griechenland",
    "HR": r"Croatia|Kroatien", "SI": r"Slovenia|Slowenien", "SK": r"Slovakia|Slowakei",
    "EE": r"Estonia|Estland", "LV": r"Latvia|Lettland", "LT": r"Lithuania|Litauen",
    "LU": r"Luxembourg|Luxemburg", "MT": r"Malta", "CY": r"Cyprus|Zypern",
    "IS": r"Iceland",
}
LEGAL_SUFFIX = r"(?:GmbH|Limited|Ltd\.?|LLC|Inc\.?|SAS|AG|B\.?V\.?|Oy)"
YEAR_RX = re.compile(r"(?P<min>\d{1,2}(?:[.,]\d+)?)\s*(?:\+|(?:[-–—]|\bto\b|\band\b|\ba\b|\bà\b)\s*(?P<max>\d{1,2}(?:[.,]\d+)?))?\s*(?:years?|Jahre[n]?|ans?|años?)\b", re.I)


def evidence(source, quote):
    return {"source": source, "quote": quote.strip()[:600]}


def chunks(description):
    return [part.strip() for part in re.split(r"\n+|(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9])", description) if part.strip()]


def _conditional(value):
    return bool(re.search(r"\b(?:depending|depends|subject to|may be|might|je nach|abhängig|nach absprache|only after|after (?:the )?probation|nach (?:der )?probezeit)\b|\bafter\b[^.!?]{0,55}\b(?:months?|weeks?|days?|years?|training|office)\b", value, re.I))


def workplace_facts(description, structured):
    policies = []
    for part in chunks(description):
        if re.search(r"remote[- ](?:interviews?|sensing|monitoring|control|experience)", part, re.I):
            continue
        if re.search(r"\bno remote(?: work)? (?:restrictions|limitations|constraints|requirements)\b",part,re.I):
            continue
        denied_partial = bool(re.search(r"\bnot (?:a )?(?:fully|full|100\s*%) remote\b",part,re.I))
        denied = denied_partial or bool(re.search(r"\b(?:no remote(?: work)?|not (?:a )?remote(?: role)?|(?:cannot|can't|do not|don't) work remotely|remote(?: work)? (?:is )?not (?:available|possible|allowed|offered)|kein(?:e|en)? remote|remote(?:[- ]arbeit)? (?:ist )?nicht (?:möglich|erlaubt))\b", part, re.I))
        remote = bool(re.search(r"\b(?:fully remote|full remote|100\s*%\s*remote|remote[- ]first|remote (?:work|role|position|within|from|in|across|anywhere)|work(?:ing)? remotely|work(?:ing)? remote|remotely \(within|remote[- ]arbeit|mobiles arbeiten|homeoffice)\b", part, re.I))
        hybrid = bool(re.search(r"\bhybrid (?:work|working|role|position|setup|model|arrangement|schedule|office|in|from)\b|\blocation\s*:[^.\n]{0,100}\bhybrid\b|^\W*hybrid\W*$", part, re.I)) and not bool(re.search(r"\bnot (?:a )?hybrid\b",part,re.I))
        onsite = bool(re.search(r"\b(?:office[- ]first|office[- ]based|on[- ]?site|in[- ]office|vor ort|büropflicht)\b", part, re.I)) and not bool(re.search(r"\bnot (?:an? )?(?:on[- ]?site|office[- ]based|in[- ]office)\b",part,re.I))
        attendance = bool(re.search(r"\b(?:require|required|expected|must|mandatory)\b[^.!?]{0,45}\b(?:days?|Tage?)\b[^.!?]{0,25}\b(?:in (?:the )?office|on[- ]?site|vor ort)\b",part,re.I))
        if denied:
            policies.append(("hybrid" if denied_partial or attendance else "onsite", part, _conditional(part), True))
        elif remote:
            # An explicit choice of full remote OR an office is not mandatory hybrid.
            alternative = bool(re.search(r"\b(?:or|oder|choose between)\b", part, re.I))
            if (hybrid or onsite) and not alternative:
                policies.append(("conflict", part, _conditional(part), False))
            else:
                policies.append(("remote", part, _conditional(part), False))
        elif hybrid or attendance:
            policies.append(("hybrid", part, _conditional(part), False))
        elif onsite:
            policies.append(("onsite", part, _conditional(part), False))
    modes = {item[0] for item in policies}
    descriptions_mode = next(iter(modes)) if len(modes) == 1 else "unknown"
    conflicting = "conflict" in modes or len(modes) > 1
    if descriptions_mode == "conflict":
        descriptions_mode = "unknown"
    structured = structured if structured in {"remote", "hybrid", "onsite"} else "unknown"
    if structured != "unknown" and descriptions_mode != "unknown" and structured != descriptions_mode:
        conflicting = True
    mode = "unknown" if conflicting else descriptions_mode if descriptions_mode != "unknown" else structured
    quotes = [evidence("description", item[1]) for item in policies]
    if structured != "unknown":
        quotes.insert(0, evidence("structured", structured))
    conditional = any(item[2] for item in policies)
    countries, regions, excluded_countries, timezone_policy = set(), set(), set(), None
    remote_quotes = []
    exclusions = False
    for policy, part, condition, denied in policies:
        if policy != "remote" or denied:
            continue
        remote_quotes.append(evidence("description", part))
        # Geographic restrictions must be attached to remote work, not office locations.
        segment = re.split(r"\b(?:remote|remotely|homeoffice)\b", part, maxsplit=1, flags=re.I)[-1]
        segment = re.split(r"\bor (?:from|in|at) (?:one of )?(?:our |the )?(?:offices?|locations?)\b", segment, flags=re.I)[0]
        scope = re.match(r"\s*(?:work(?:ing)?\s+)?(?:\(?\s*(?:within|from|in|across|anywhere in)\b|(?:is\s+)?(?:available|offered|possible|permitted|allowed)\s+(?:only\s+)?(?:within|from|in|across)\b|(?:only\s+)?for\s+residents\s+(?:of|in)\b)(.*)",segment,re.I)
        geography = scope.group(1) if scope else ""
        geography = re.split(r";|\b(?:headquarters|annual team meetings|our offices|our office|but our|while our)\b",geography,maxsplit=1,flags=re.I)[0]
        for code, names in COUNTRIES.items():
            if re.search(r"(?<!\w)(?:" + names + r")(?!\w)", geography, re.I):
                countries.add(code)
        if re.search(r"\b(?:European Union|EU)\b", geography, re.I): regions.add("eu")
        if re.search(r"\b(?:Europe|Europa)\b", geography, re.I): regions.add("europe")
        if re.search(r"\b(?:worldwide|anywhere in the world|from anywhere)\b", part, re.I): regions.add("worldwide")
        tz = re.search(r"\b(?:CET|CEST|UTC|GMT)\b[^.!?\n]{0,65}(?:[±+\-]|hours?|hrs?|Stunden)[^.!?\n]{0,30}", part, re.I)
        if tz: timezone_policy = tz.group(0).strip()
        elif re.search(r"\b(?:CET|CEST|UTC|GMT)\b",part,re.I) and re.search(r"\b(?:hours?|hrs?|Stunden)\b",part,re.I):
            timezone_policy = part[:450]
        if re.search(r"\b(?:except|excluding|not (?:from|in)|outside|must (?:live|reside)|residency required)\b", part, re.I):
            exclusions = True
        excluded = re.search(r"\b(?:except|excluding|not (?:from|in))\s+(.+)",part,re.I)
        if excluded:
            for code,names in COUNTRIES.items():
                if re.search(r"(?<!\w)(?:"+names+r")(?!\w)",excluded.group(1),re.I): excluded_countries.add(code)
    if remote_quotes:
        for part in chunks(description):
            if not re.search(r"\b(?:must (?:live|reside|be based)|residency (?:is )?required|Wohnsitz.*erforderlich)\b",part,re.I):
                continue
            if evidence("description",part) not in remote_quotes:
                remote_quotes.append(evidence("description",part))
            for code,names in COUNTRIES.items():
                if re.search(r"(?<!\w)(?:"+names+r")(?!\w)",part,re.I): countries.add(code)
            exclusions = True
    # Do not reduce compound exceptions, inconsistent global/national rules or
    # conflicting sentences to a confident allowlist.
    geographic_conflict = exclusions or ("worldwide" in regions and bool(countries))
    remote = {"allowed_countries": sorted(countries) if not geographic_conflict else [],
              "allowed_regions": sorted(regions) if not geographic_conflict else [],
              "timezone_policy": timezone_policy, "conditional": conditional or geographic_conflict,
              "conflict": geographic_conflict or conflicting, "excluded_countries":sorted(excluded_countries), "evidence": remote_quotes}
    return {"mode": mode, "source": "conflicting" if conflicting else "description" if policies else "structured" if structured != "unknown" else "unknown",
            "evidence": quotes, "conditional": conditional, "conflict": conflicting}, remote


def experience_facts(description):
    claims = []
    for part in chunks(description):
        for match in YEAR_RX.finditer(part):
            before, after = part[max(0, match.start()-180):match.start()], part[match.end():match.end()+170]
            context = before + match.group(0) + after
            if re.search(r"\b(?:founded|existence|anniversary|sabbatical|years of service|after|nach|(?:our |the )?(?:team|company|organization|organisation|business|firm) has|we have|we've)\b", before[-55:] + after[:35], re.I):
                continue
            if re.search(r"(?:do not|don't|does not|not)\s+(?:need|require)|without|no\s+(?:prior\s+)?experience|keine?\s+(?:berufs)?erfahrung|nicht\s+(?:erforderlich|notwendig)|aucune?\s+expérience|sans\s+expérience|pas\s+d[’']expérience|sin\s+experiencia|no\s+(?:se\s+)?requiere\s+experiencia|experiencia[^.;]{0,45}no\s+(?:es\s+)?(?:necesaria|requerida)|expérience[^.;]{0,45}(?:non requise|pas requise)", context, re.I):
                continue
            direct = bool(re.match(r"\s*[’']?\s*(?:(?:of|de|d[’'])\s*)?(?:(?:relevant|professional|hands-on)\s+)*(?:experience|Erfahrung|Berufserfahrung|expérience|experiencia)\b", after, re.I)
                          or re.match(r"\s+of\s+(?:(?!service\b|existence\b)[\w/-]+\s+){0,7}(?:experience|Erfahrung|Berufserfahrung)\b",after,re.I)
                          or re.match(r"\s+in\s+(?:data|analytics|analytical|statistics|gaming|product|marketing|a similar|similar)\b", after, re.I)
                          or re.search(r"\b(?:experience|Erfahrung|Berufserfahrung|expérience|experiencia)\b", before[-160:], re.I)
                          or re.search(r"\b(?:Data|Product|Business|Marketing|Quantitative)\s+Analyst\b",before[-160:],re.I) and after.startswith(")"))
            if not direct:
                continue
            lo = float(match.group("min").replace(",", "."))
            hi = float(match.group("max").replace(",", ".")) if match.group("max") else None
            if not 0 <= lo <= 70 or hi is not None and (hi < lo or hi > 70):
                continue
            preferred = bool(re.search(r"\b(?:preferred|ideally|desirable|nice to have|von vorteil|wünschenswert|idealerweise|around|about|approximately|environ|idéalement|souhaitée?|appréciée?|deseable|preferible|idealmente)\b[^.;]{0,70}$", before, re.I)
                             or re.match(r"\s*(?:(?:of\s+)?(?:[\w/-]+\s+){0,7}experience\s*)?(?:is\s+|are\s+|would be\s+)?(?:preferred|desirable|nice to have|von vorteil|wünschenswert|souhaitée?|appréciée?|deseable|preferible)\b", after,re.I)
                             or re.match(r"\s*(?:(?:d[’']expérience|de experiencia|expérience|experiencia)\s*)?(?:(?:est|serait|es)\s+)?(?:souhaitée?|appréciée?|deseable|preferible)\b", after, re.I))
            alternative = bool(re.search(r"\b(?:degree|bachelor|master|abschluss|studium)\b[^.;]{0,80}\b(?:or|oder)\s+(?:(?:at least|minimum|equivalent)\s+)?\d|\byears?\b[^.;]{0,60}\b(?:or|oder)\s+(?:a\s+)?(?:degree|bachelor|master)", context, re.I))
            strength = "unknown" if alternative else "preferred" if preferred else "required"
            if not re.search(r"\bno less than\s*$",before,re.I) and re.search(r"\b(?:up to|less than|no more than|not more than|at most|bis zu|maximal|jusqu[’']à|moins de|hasta)\s*$",before,re.I):
                hi,lo,strength=lo,None,"unknown"
            domain = []
            for name, pattern in {"gaming":r"\b(?:gaming|game analytics|mobile games?)\b", "mobile analytics":r"\b(?:mobile[- ]app(?: analytics| setting)?|working with an app|app analytics)\b", "product analytics":r"\b(?:product analyst|product analytics|produktanalytik)\b", "marketing analytics":r"\bmarketing analytics\b", "product management":r"\b(?:Product Owner|Product Manager|Produktmanagement)\b"}.items():
                if re.search(pattern, context, re.I): domain.append(name)
            quote=part[max(0,match.start()-200):min(len(part),match.end()+200)]
            claims.append({"min_years":lo,"max_years":hi,"strength":strength,"domains":domain,"evidence":evidence("description",quote)})
    primary = [c for c in claims if c["strength"]=="required"] or [c for c in claims if c["strength"]=="preferred"] or claims
    unique = {(c["min_years"],c["max_years"],c["strength"]) for c in primary}
    conflict = len(unique) > 1
    if not claims or conflict:
        return {"min_years":None,"max_years":None,"strength":"unknown","domains":sorted({d for c in claims for d in c["domains"]}),"evidence":[c["evidence"] for c in claims],"conflict":conflict}
    first = primary[0]
    return {"min_years":first["min_years"],"max_years":first["max_years"],"strength":first["strength"],"domains":sorted({d for c in claims for d in c["domains"]}),"evidence":[c["evidence"] for c in claims],"conflict":False}


def seniority_facts(title):
    # Explicit labels only; no universal mapping from years to a career level.
    for level, pattern in [("executive",r"\b(?:chief|vice president|vp|director)\b"),
                           ("manager",r"^Manager\b|\b(?:Engineering|People|Team) Manager\b"),("lead",r"\b(?:lead|principal|staff)\b"),
                           ("senior",r"\b(?:senior|sr\.?)\b"),("junior",r"\b(?:junior|jr\.?)\b"),
                           ("intern",r"\b(?:intern|internship|trainee|praktikant)\b"),
                           ("mid",r"\bmid[- ]?(?:level)?\b")]:
        if re.search(pattern,title,re.I):
            return {"level":level,"evidence":[evidence("title",title)]}
    return {"level":None,"evidence":[]}


# Organization extraction requires an identity-bearing context. A capitalized
# customer, technology vendor or benefit provider alone is not employer evidence.
_ORG_NAME = r"[A-ZÄÖÜÉ][\w&’'().-]*(?:\s+(?:(?:of|the|and|for|de|des|&|&amp;)\s+)?[A-ZÄÖÜÉ][\w&’'().-]*){0,8}"


def _identity_name(value):
    value = unescape(value).strip(" \t,;:–—-")
    value = re.sub(r"^(?:the|The)\s+", "", value)
    if not 2 <= len(value) <= 130 or re.match(r"(?i)^(?:our|a|an|your|their|this|partners?|clients?|customers?|company|organisation|organization|team|department|requirements|responsibilities)\b", value):
        return None
    return value


def employer_facts(job, description, previous):
    company = job.get("source_company") if job.get("source_company") is not None else job.get("company")
    company_display = unescape(company) if isinstance(company, str) else None
    claims = previous.get("employer", {}) if isinstance(previous, dict) else {}
    explicit_employer = claims.get("input_employer") if claims else job.get("employer")
    explicit_publisher = claims.get("input_publisher") if claims else job.get("publisher")
    parts = chunks(description)
    first_line = next(iter(parts), "")
    heading = re.match(r"^([^\n!?]{1,110}?\b" + LEGAL_SUFFIX + r")(?=\s*(?:[–—\-:!]|$))", first_line, re.I)
    publisher_signal = bool(company_display and re.search(r"(?:jobs?|stellen|career|vacanc|emploi|recruit)[^\s]*\.(?:de|com|net|org|io)\b", company_display, re.I))
    publisher_quotes, recruiter_quotes = [], []
    for part in parts:
        if re.search(r"\b(?:advertis(?:e|es|ing)|publish(?:es|ing)?)\s+(?:jobs?|roles?|vacancies|positions?|job advertisements?)\s+(?:on behalf of|for)\b", part, re.I):
            publisher_quotes.append(part)
        # Explicit recruitment/client relationships, not generic mentions of
        # clients in a consulting firm's job responsibilities.
        if re.search(r"\b(?:recruiting|hiring)\s+(?:on behalf of|for\s+(?:our\s+(?:[\w-]+\s+){0,3}(?:client|customer|partner)|(?:a|an|the)\s+(?:[\w-]+\s+){0,3}(?:client|customer|partner|company|organisation|organization)))\b|\bon behalf of (?:our|a) client\b|\b(?:our client|notre client)\s+(?:is|are|est|recherche)\b|\bfür unseren Kunden\b|\bim Auftrag (?:unseres|eines) Kunden\b|\bper (?:un|il|un nostro) cliente\b|\bdla naszego klienta\b", part, re.I):
            recruiter_quotes.append(part)
        elif re.search(r"\b(?:partnering|working) with (?:a|an|the|our)\b", part, re.I) and re.search(r"\b(?:look(?:ing)?|appoint|recruit|hire|hiring|role|position)\b", part, re.I):
            recruiter_quotes.append(part)
    publisher = explicit_publisher or company_display if publisher_signal or publisher_quotes or recruiter_quotes or explicit_publisher else None
    source_role = "recruiter" if recruiter_quotes else "publisher" if publisher else "employer" if company_display else "unknown"
    candidates, client_names = [], []
    def add_candidate(name, quote):
        name = _identity_name(name)
        if name and name.casefold() != (company_display or "").casefold():
            candidates.append((name, quote))
    if heading:
        add_candidate(heading.group(1), first_line)
    for part in parts:
        # Explicit labels and an employer speaking in the first person are
        # stronger than merely mentioning a business in programme copy.
        for match in re.finditer(r"(?i:Employer|Hiring company|Arbeitgeber)\s*:\s*(" + _ORG_NAME + r")(?=\s*[,;:!–—-]|$)", part):
            add_candidate(match.group(1), part)
        for match in re.finditer(r"(?:^|(?<=[.!?])\s+)(?i:At)\s+(?:(?i:the)\s+)?(" + _ORG_NAME + r"),\s*(?i:we)\b", part):
            add_candidate(match.group(1), part)
        for match in re.finditer(r"(?i:on behalf of)\s+(" + _ORG_NAME + r")(?=\s*[,;:!–—-]|$)", part):
            add_candidate(match.group(1), part)
        for match in re.finditer(r"(?i:for our client|für unseren Kunden)\s+(" + _ORG_NAME + r")(?=\s+(?i:in|we|seeking|suchen)|\s*[,;:!–—-]|$)", part):
            name = _identity_name(match.group(1))
            if name:
                client_names.append((name, part))
    unique = {}
    for name, quote in candidates:
        unique.setdefault(name.casefold(), (name, quote))
    candidate = next(iter(unique.values()))[0] if len(unique) == 1 else None
    # For a recruitment agency, a named client is not necessarily the legal
    # employer. Return that distinction without inventing an employment contract.
    employer = explicit_employer or (candidate if publisher else company_display)
    quotes = [evidence("structured", company)] if company else []
    quotes.extend(evidence("description", part) for part in publisher_quotes + recruiter_quotes)
    quotes.extend(evidence("description", quote) for _, quote in unique.values())
    quotes.extend(evidence("description", quote) for _, quote in client_names)
    if explicit_employer:
        quotes.append(evidence("structured", explicit_employer))
    deduped = list({(item["source"], item["quote"]): item for item in quotes}.values())
    conflict = bool(len(unique) > 1 or explicit_employer and unique and any(name.casefold() != str(explicit_employer).casefold() for name, _ in unique.values()))
    status = "description_claim" if publisher and candidate and not explicit_employer else "source_claim" if employer else "unresolved"
    return employer, publisher, company, {"status": status, "source_role": source_role,
        "evidence": deduped, "description_candidate": candidate,
        "candidate_employers": [name for name, _ in unique.values()],
        "client_organizations": list(dict.fromkeys(name for name, _ in client_names)),
        "employment_relationship": "unverified_client_relationship" if client_names and not employer else "advertised_employer" if employer else "unresolved",
        "conflict": conflict, "input_employer": explicit_employer,
        "input_publisher": explicit_publisher, "verified": False}


def enrich_job(job):
    """Return a new research view of a legacy/current saved row, never mutate it."""
    result=deepcopy(job)
    description=str(job.get("description") or "")
    original_mode=job.get("source_workplace") or job.get("workplace","unknown")
    workplace,remote=workplace_facts(description,original_mode)
    employer,publisher,source_company,employer_info=employer_facts(job,description,job.get("research",{}))
    result.update(title=unescape(str(job.get("title") or "")),source_workplace=original_mode,
                  workplace=workplace["mode"],source_company=source_company,employer=employer,publisher=publisher)
    result["research"]={"version":"0.3","workplace":workplace,"remote":remote,
        "experience":experience_facts(description),"seniority":seniority_facts(result["title"]),"employer":employer_info,
        "publication":enrich_publication(job),"program":enrich_program(job)}
    return result
