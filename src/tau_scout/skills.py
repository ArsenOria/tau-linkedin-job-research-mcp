"""Small, explicit skill vocabulary. Related products are not interchangeable skills."""
from html import unescape
import re
import unicodedata


def clean(value: str) -> str:
    return unicodedata.normalize("NFKC", unescape(value)).replace("’", "'").replace("–", "-").replace("—", "-")


ALIASES = {
    "A/B testing": r"a\s*[/\-]\s*b[\s\-]+test(?:s|ing)?(?:\s+design)?|ab\s+tests?|split\s+testing",
    "SQL": r"sql|structured\s+query\s+language",
    "Python": r"python(?:\s*3)?",
    "R": r"(?-i:R)(?!\s*&\s*[Dd])",
    "Power BI": r"(?:(?:microsoft|ms)\s+)?power\s*bi",
    "Excel": r"(?:(?:microsoft|ms)\s+)?excel",
    "PostgreSQL": r"postgres(?:ql)?",
    "Tableau": r"tableau",
    "dbt": r"dbt|data\s+build\s+tool",
    "Snowflake": r"snowflake",
    "Databricks": r"databricks",
    "Amplitude": r"amplitude",
    "Adobe Analytics": r"adobe\s+analytics",
    "GA4": r"ga\s*4|google\s+analytics\s*4",
    "dashboards": r"dashboards?|dashboarding",
    "data modeling": r"data\s+modell?ing",
    "monetization": r"moneti[sz]ation",
    "player behavior": r"player\s+behaviou?rs?",
}
PATTERNS = {name: re.compile(r"(?<!\w)(?:" + pattern + r")(?!\w)", re.I)
            for name, pattern in ALIASES.items()}


def canonical_skill(value: str) -> str:
    value = " ".join(clean(value).strip().split())
    for name, pattern in PATTERNS.items():
        if pattern.fullmatch(value):
            return name
    return value.casefold()


def unique_skills(values: list[str]) -> list[tuple[str, str]]:
    """(first supplied spelling, canonical spelling); aliases count once."""
    unique = {}
    for value in values:
        canonical = canonical_skill(value)
        unique.setdefault(canonical, value)
    return [(value, canonical) for canonical, value in unique.items()]


def _negated(text: str, start: int, end: int) -> bool:
    # Restrict context to this clause, not unrelated previous requirements.
    left = re.split(r"[.;\n]", text[max(0, start - 90):start])[-1]
    right = re.split(r"[.;\n]", text[end:end + 90])[0]
    left = re.sub(r"\bnot\s+(?:only|just|merely)\b", "", left, flags=re.I)
    left = re.split(r"\b(?:but|however|whereas|sondern|aber)\b", left, flags=re.I)[-1]
    if re.search(r"\b(?:no|without|not|kein\w*|ohne)\s+(?:\w+\s+){0,4}$", left, re.I):
        return True
    if re.match(r"\s*(?:(?:experience|knowledge|skills?|kenntnisse|erfahrung)\s+)?(?:is\s+|are\s+|ist\s+)?(?:not\s+(?:required|necessary|needed)|nicht\s+(?:erforderlich|notwendig))\b", right, re.I):
        return True
    # A trailing qualifier can apply to an entire explicit skill list. Do not
    # count SQL positively in "SQL and Python are not required". Keeping only
    # recognized skill names in this pattern prevents it crossing arbitrary
    # prose or a separate positive requirement.
    list_right = right
    for pattern in PATTERNS.values():
        list_right = pattern.sub("__skill__", list_right)
    if re.match(r"\s*(?:(?:,|/|\b(?:and|or|und|oder)\b)\s*__skill__\s*)+"
                r"(?:(?:experience|knowledge|skills?)\s+)?(?:is\s+|are\s+)?"
                r"not\s+(?:required|necessary|needed)\b", list_right, re.I):
        return True
    return False


def mentions(text: str, skill: str, source: str = "description") -> list[dict]:
    text = clean(text)
    canonical = canonical_skill(skill)
    pattern = PATTERNS.get(canonical)
    if pattern is None:
        pattern = re.compile(r"(?<!\w)" + re.escape(canonical).replace(r"\ ", r"\s+") + r"(?!\w)", re.I)
    output = []
    for found in pattern.finditer(text):
        if _negated(text, found.start(), found.end()):
            continue
        start = max(text.rfind("\n", 0, found.start()) + 1, found.start() - 100)
        end = text.find("\n", found.end())
        end = min(end if end >= 0 else len(text), found.end() + 160)
        output.append({"skill": canonical, "source": source, "quote": text[start:end].strip(),
                       "start": found.start(), "end": found.end()})
    return output


REQUIREMENT_HEADINGS = re.compile(
    r"(?im)^\s*(?:#+\s*)?(?:requirements|qualifications|your profile|profile|"
    r"what (?:we're|we are) looking for|what you bring|your qualifications|"
    r"skills(?: and experience)?|what you'll need|you'll be great for this role if[^\n]*|"
    r"qualifikation(?:en)?|dein profil|das bringst du mit)(?:\s*[-:–—].*)?\s*[:.…]*\s*$")
END_HEADINGS = re.compile(r"(?im)^\s*(?:benefits|what we offer|why (?:you should )?join[^\n]*|"
                          r"nice to have|von vorteil|das erwartet dich|what happens next|"
                          r"what does the recruitment[^\n]*)\s*[:.…]*\s*$")
OPTIONAL = re.compile(r"\b(?:preferred|preferably|ideally|nice.to.have|optional|advantage|a plus|"
                      r"wünschenswert|von vorteil|idealerweise|vorzugsweise)\b", re.I)


def required_skills(description: str) -> list[dict]:
    """Recognized, positively required skill groups; `or` alternatives stay groups.

    This is intentionally a bounded vocabulary, not a claim to extract every
    requirement. Unknown requirements remain for the host's description review.
    """
    description = clean(description)
    heading = REQUIREMENT_HEADINGS.search(description)
    if heading:
        end = END_HEADINGS.search(description, heading.end())
        section = description[heading.end():end.start() if end else len(description)]
    else:
        section = "\n".join(line for line in description.splitlines()
                            if re.search(r"\b(?:required|must have|essential|erforderlich)\b", line, re.I))
    result = []
    clauses = []
    for line in re.split(r"[\n;]+", section):
        if OPTIONAL.search(line):
            if not re.search(r"\b(?:required|must|essential|erforderlich)\b", line, re.I):
                continue
            clauses.extend(re.split(r",|\bbut\b|\bwhereas\b|\band\b(?=.{0,60}\brequired\b)", line, flags=re.I))
        else:
            clauses.append(line)
    for clause in clauses:
        if not clause.strip() or OPTIONAL.search(clause):
            continue
        found = []
        for skill in PATTERNS:
            for item in mentions(clause, skill):
                found.append(item)
        found.sort(key=lambda item: item["start"])
        groups = []
        for item in found:
            if groups and re.search(r"\b(?:or|oder)\b|/", clause[groups[-1][-1]["end"]:item["start"]], re.I):
                groups[-1].append(item)
            else:
                groups.append([item])
        for group in groups:
            names = list(dict.fromkeys(item["skill"] for item in group))
            key = tuple(names)
            if not any(tuple(item["skills"]) == key for item in result):
                result.append({"skills": names, "source": "description", "quote": clause.strip()[:400]})
    return result


def canonical_domain(value: str) -> str:
    value = " ".join(clean(value).casefold().replace("_", " ").replace("-", " ").split())
    if re.search(r"\bgam(?:e|es|ing)\b", value):
        return "gaming"
    if "product" in value and "analytic" in value:
        return "product analytics"
    if ("mobile" in value or "app" in value) and "analytic" in value:
        return "mobile analytics"
    return value
