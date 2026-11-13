"""Publication claims are evidence, not proof of original posting or freshness.

Only bounded date-specific provider values survive normalization. Existing saved
rows are enriched without changing their posted_at or observation timestamp.
"""
from datetime import datetime, timedelta, timezone
import math
import re

UTC = timezone.utc
DATE_FIELDS = ("postedAtTimestamp", "publishedAt", "postedDate", "postedAt", "postedTime", "timePosted")


def _observation(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.year < 2000:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    except (TypeError, ValueError, OverflowError):
        return None


def _absolute(value, observed):
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and re.fullmatch(r"\d{10}|\d{13}", value):
        value = int(value)
    try:
        if isinstance(value, (int, float)):
            if not math.isfinite(value):
                return None
            parsed = datetime.fromtimestamp(value / 1000 if abs(value) >= 100_000_000_000 else value, UTC)
            precision = "timestamp"
        elif isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+(?:Z|[+-]\d{2}:?\d{2})?)?", value.strip()):
            value = value.strip()
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            precision = "day" if len(value) == 10 else "timestamp"
            parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        else:
            return None
        if parsed.year < 2000 or observed and parsed > observed + timedelta(minutes=5):
            return None
        # Keep day precision through subsequent read-time enrichment. Turning a
        # day into an ISO midnight value here would later make it look precise.
        value = parsed.date().isoformat() if precision == "day" else parsed.isoformat()
        return {"kind": "absolute", "value": value, "date": parsed.isoformat(), "precision": precision}
    except (ValueError, OverflowError, OSError):
        return None


def _relative(value, observed):
    if not isinstance(value, str) or len(value) > 100 or not observed:
        return None
    label = value.strip().lower()
    repost = bool(re.match(r"reposted\s+", label))
    label = re.sub(r"^(?:reposted|posted)\s+", "", label)
    if label in {"just now", "today", "yesterday"}:
        midnight = observed.replace(hour=0, minute=0, second=0, microsecond=0)
        if label == "just now":
            earliest, latest = observed - timedelta(minutes=1), observed
        elif label == "today":
            earliest, latest = midnight, observed
        else:
            earliest, latest = midnight - timedelta(days=1), midnight
    else:
        match = re.fullmatch(r"(\d{1,3})\s*(minute|hour|day|week|month|year)s?\s+ago", label)
        if not match:
            return None
        count, unit = int(match[1]), match[2]
        if unit in {"month", "year"}:
            # Provider labels do not specify their calendar/rounding policy.
            # Use conservative bounds rather than equating months with 30 days
            # or years with 365 days, which can contradict a valid exact date.
            minimum, maximum = (28, 31) if unit == "month" else (365, 366)
            earliest = observed - timedelta(days=maximum * (count + 1))
            latest = observed - timedelta(days=minimum * count)
        else:
            step = timedelta(seconds={"minute": 60, "hour": 3600, "day": 86400, "week": 604800}[unit])
            earliest, latest = observed - step * (count + 1), observed - step * count
    if earliest.year < 2000:
        return None
    return {"kind": "repost" if repost else "relative", "value": ("reposted " if repost else "") + label,
            "date": None, "precision": "approximate", "earliest": earliest.isoformat(), "latest": latest.isoformat()}


def _conflicting(claims):
    absolute = [c for c in claims if c["kind"] == "absolute"]
    # Conflicting calendar dates are material. Different same-day times can be
    # provider rounding, so they do not establish a precise original timestamp.
    if len({c["date"][:10] for c in absolute}) > 1:
        return True
    for absolute_claim in absolute:
        value = _observation(absolute_claim["date"])
        for relative in (c for c in claims if c["kind"] == "relative"):
            earliest, latest = _observation(relative["earliest"]), _observation(relative["latest"])
            # Date-only claims describe a calendar day rather than midnight.
            end = value + timedelta(days=1) if absolute_claim["precision"] == "day" else value
            if end < earliest or value > latest:
                return True
    return False


def actor_publication(raw, observed_at):
    """Return compatible provider posted_at and bounded provenance metadata."""
    observed = _observation(observed_at)
    claims, rejected = [], []
    for field in DATE_FIELDS:
        value = raw.get(field)
        if value is None:
            continue
        claim = _absolute(value, observed) or _relative(value, observed)
        if claim:
            claims.append({"field": field, **claim})
        else:
            rejected.append(field)
    conflict = _conflicting(claims)
    absolute = next((c["date"] for c in claims if c["kind"] == "absolute"), None)
    return (None if conflict else absolute), {"claims": claims, "rejected_fields": rejected, "conflict": conflict}


def enrich_publication(job):
    """Return honest research metadata from a normalized or legacy job dict.

    No source claim is promoted to independent verification. In particular,
    original_publication_at remains unknown even if an absolute provider date
    exists: an updated/reposted listing can carry a different date.
    """
    observed_at = job.get("observed_at")
    observed = _observation(observed_at)
    source = job.get("publication_source")
    if isinstance(source, dict) and isinstance(source.get("claims"), list):
        claims = []
        for claim in source["claims"][:len(DATE_FIELDS)]:
            if not isinstance(claim, dict) or claim.get("field") not in DATE_FIELDS:
                continue
            parsed = _absolute(claim.get("value"), observed) or _relative(claim.get("value"), observed)
            if parsed:
                claims.append({"field": claim["field"], **parsed})
        rejected_fields = source.get("rejected_fields")
        rejected = ([f for f in rejected_fields[:len(DATE_FIELDS)]
                     if isinstance(f, str) and f in DATE_FIELDS]
                    if isinstance(rejected_fields, list) else [])
    else:
        legacy = _absolute(job.get("posted_at"), observed)
        claims = [{"field": "posted_at", **legacy}] if legacy else []
        rejected = ["posted_at"] if job.get("posted_at") and not legacy else []
    conflict = _conflicting(claims)
    warnings = ["Provider/import publication claims are not independently verified; observation time is not publication time."]
    if conflict:
        warnings.append("Publication claims conflict; do not assert a publication date or recency eligibility.")
    if any(c["kind"] == "repost" for c in claims):
        warnings.append("A repost label does not establish the original publication date.")
    if any(c["kind"] == "relative" for c in claims):
        warnings.append("Relative labels are approximate ranges anchored to the saved observation, not the current clock.")
    if any(c["kind"] == "absolute" and c["date"][11:19] == "00:00:00" for c in claims):
        warnings.append("A midnight value may be date-only; precise publication time is not established.")
    if rejected:
        warnings.append("Unparseable, implausible or future date fields were not used.")
    return {"status": "ambiguous" if conflict else "unverified_source_claim" if claims else "unknown",
            "source_posted_at": job.get("posted_at"), "observed_at": observed_at,
            "original_publication_at": None, "independently_verified": False,
            "freshness_verified": False, "claims": claims, "rejected_fields": rejected, "warnings": warnings}
