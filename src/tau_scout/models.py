from datetime import datetime, timezone
from typing import Annotated, Literal
import re
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Workplace = Literal["any", "remote", "hybrid", "onsite"]
Text = Annotated[str, Field(min_length=1, max_length=200)]
Terms = Annotated[list[Text], Field(max_length=50)]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, hide_input_in_errors=True)


class SearchBrief(StrictModel):
    target_titles: Annotated[list[Text], Field(min_length=1, max_length=5)]
    locations: Annotated[list[Text], Field(min_length=1, max_length=5)]
    workplace: Workplace = "any"
    posted_within: Literal["day", "week", "month", "any"] = "week"
    easy_apply_only: bool = False
    max_results: Annotated[int, Field(ge=1, le=100, strict=True)] = 25
    max_charge_usd: Annotated[float, Field(gt=0, le=5, allow_inf_nan=False)] = 0.50


class Candidate(StrictModel):
    skills: Terms = Field(default_factory=list)
    target_titles: Terms = Field(default_factory=list)
    locations: Terms = Field(default_factory=list)
    workplace: Workplace = "any"
    requires_sponsorship: bool | None = None
    experience_years: Annotated[float, Field(ge=0, le=70, allow_inf_nan=False, strict=True)] | None = None
    target_seniority: Literal["intern", "junior", "mid", "senior", "lead", "manager", "executive"] | None = None
    remote_from_country: Annotated[str, Field(pattern=r"^[A-Za-z]{2}$")] | None = None
    domains: Terms = Field(default_factory=list)
    is_student: bool | None = None
    degree_completed: bool | None = None
    graduation_year: Annotated[int, Field(ge=1900, le=2200, strict=True)] | None = None
    fields_of_study: Terms = Field(default_factory=list)
    placement_year_available: bool | None = None
    completed_study_years: Annotated[int, Field(ge=0, le=20, strict=True)] | None = None
    grade_classification: Annotated[str, Field(min_length=1, max_length=80)] | None = None

    @field_validator("remote_from_country")
    @classmethod
    def canonical_country(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class RefineFilters(StrictModel):
    include_terms: Terms = Field(default_factory=list)
    exclude_terms: Terms = Field(default_factory=list)
    companies: Terms = Field(default_factory=list)
    exclude_companies: Terms = Field(default_factory=list)
    locations: Terms = Field(default_factory=list)
    workplace: Workplace = "any"
    easy_apply_only: bool = False


class JobInput(StrictModel):
    title: Annotated[str, Field(min_length=1, max_length=300)]
    external_id: Annotated[str, Field(pattern=r"^\d{5,30}$")] | None = None
    url: Annotated[str, Field(max_length=2000)] | None = None
    company: Annotated[str, Field(max_length=300)] | None = None
    source_company: Annotated[str, Field(max_length=300)] | None = None
    employer: Annotated[str, Field(max_length=300)] | None = None
    publisher: Annotated[str, Field(max_length=300)] | None = None
    source_workplace: Literal["unknown", "remote", "hybrid", "onsite"] | None = None
    location: Annotated[str, Field(max_length=300)] | None = None
    workplace: Literal["unknown", "remote", "hybrid", "onsite"] = "unknown"
    description: Annotated[str, Field(max_length=20000)] | None = None
    posted_at: Annotated[str, Field(max_length=100)] | None = None
    easy_apply: bool | None = None
    salary_min: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    salary_max: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    salary_currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None = None
    salary_period: Literal["hour", "day", "week", "month", "year"] | None = None

    @field_validator("posted_at")
    @classmethod
    def valid_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()

    @model_validator(mode="after")
    def identity(self) -> "JobInput":
        url_id = None
        if self.url:
            parsed = urlsplit(self.url)
            host = parsed.hostname or ""
            linkedin_host = host in {"www.linkedin.com", "linkedin.com"} or bool(
                re.fullmatch(r"[a-z]{2}\.linkedin\.com", host)
            )
            if (parsed.scheme != "https" or not linkedin_host
                    or parsed.username or parsed.password or parsed.port not in {None, 443}):
                raise ValueError("Expected a LinkedIn job URL.")
            match = re.fullmatch(r"/jobs/view/(?:[^/]*?-)?(\d{5,30})/?", parsed.path)
            if not match:
                raise ValueError("Expected a LinkedIn job URL with a numeric ID.")
            url_id = match.group(1)
        if not self.external_id and not url_id:
            raise ValueError("A numeric external_id or LinkedIn job URL is required.")
        if self.external_id and url_id and self.external_id != url_id:
            raise ValueError("Job ID and URL disagree.")
        self.external_id = self.external_id or url_id
        self.url = f"https://www.linkedin.com/jobs/view/{self.external_id}/"
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("Salary minimum exceeds maximum.")
        return self


class Job(JobInput):
    source: Literal["apify", "import", "demo"]
    observed_at: str
    publication_source: dict | None = None
