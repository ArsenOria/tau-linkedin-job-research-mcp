"""Actor-specific mapping; unknown values stay unknown and raw content is discarded."""
from html import unescape
import re

from pydantic import ValidationError

from .models import Job, JobInput, now_iso
from .publication import actor_publication


def text(value, cap=300):
    if not isinstance(value, str):
        return None
    result = value.strip()[:cap]
    return result or None


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            pass
    return None


def workplace_of(value):
    value = str(value or "").lower()
    if "hybrid" in value:
        return "hybrid"
    if "remote" in value:
        return "remote"
    if value in {"onsite", "on-site", "on site", "office"}:
        return "onsite"
    return "unknown"


def actor_job(raw: dict) -> Job | None:
    if not isinstance(raw, dict):
        return None
    job_id = str(raw.get("id") or raw.get("jobId") or "")
    url = raw.get("jobUrl") or raw.get("link") or raw.get("linkedinUrl")
    if not re.fullmatch(r"\d{5,30}", job_id):
        job_id = None
    observed_at = now_iso()
    published, publication_source = actor_publication(raw, observed_at)
    easy_apply = raw.get("easyApply")
    if not isinstance(easy_apply, bool):
        apply_type = str(raw.get("applyType") or "").upper()
        easy_apply = True if "EASY" in apply_type else False if apply_type == "EXTERNAL" else None
    currency = str(raw.get("salaryCurrency") or "").upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        currency = None
    period = str(raw.get("salaryPeriod") or "").lower()
    period = {"yearly": "year", "annually": "year", "annual": "year", "hourly": "hour",
              "monthly": "month", "weekly": "week", "daily": "day"}.get(period, period)
    if period not in {"year", "month", "week", "day", "hour"}:
        period = None
    fields = dict(
        title=unescape(text(raw.get("title")) or ""), external_id=job_id, url=url,
        company=unescape(text(raw.get("companyName")) or "") or None,
        source_company=text(raw.get("companyName")), location=text(raw.get("location")),
        workplace=workplace_of(raw.get("workType") or raw.get("workplaceType")),
        description=text(raw.get("description") or raw.get("descriptionText"), 20000),
        posted_at=published, easy_apply=easy_apply,
        salary_min=number(raw.get("salaryMin")), salary_max=number(raw.get("salaryMax")),
        salary_currency=currency, salary_period=period,
    )
    # Provider data can be inconsistent; salary anomalies must not discard a real job.
    lo, hi = fields["salary_min"], fields["salary_max"]
    if lo is not None and (lo < 0 or not (float("-inf") < lo < float("inf"))):
        fields["salary_min"] = None
    if hi is not None and (hi < 0 or not (float("-inf") < hi < float("inf"))):
        fields["salary_max"] = None
    if fields["salary_min"] is not None and fields["salary_max"] is not None and fields["salary_min"] > fields["salary_max"]:
        fields["salary_min"] = fields["salary_max"] = None
    try:
        return Job(**fields, source="apify", observed_at=observed_at, publication_source=publication_source)
    except (ValidationError, ValueError, TypeError):
        return None


def imported_job(job: JobInput, source="import") -> Job:
    return Job(**job.model_dump(), source=source, observed_at=now_iso())
