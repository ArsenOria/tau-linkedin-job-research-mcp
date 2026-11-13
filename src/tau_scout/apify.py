"""One explicit Apify actor adapter. Never follows provider-supplied URLs."""
from dataclasses import dataclass
import re

import httpx

from .errors import ProviderError
from .models import SearchBrief

API_BASE = "https://api.apify.com/v2"
ACTOR = "bebity/linkedin-jobs-scraper"
RUN_STATES = {"READY", "RUNNING", "SUCCEEDED", "FAILED", "TIMING-OUT", "TIMED-OUT", "ABORTING", "ABORTED"}
TERMINAL = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


@dataclass
class Run:
    id: str
    status: str
    dataset_id: str | None


def actor_input(brief: SearchBrief) -> dict:
    result = {
        "titles": brief.target_titles,
        "locations": brief.locations,
        "rows": brief.max_results,
        "companyProfile": False,
        "enrichCompany": False,
    }
    if brief.posted_within != "any":
        result["publishedAt"] = {"day": "r86400", "week": "r604800", "month": "r2592000"}[brief.posted_within]
    if brief.workplace != "any":
        result["workTypes"] = [{"onsite": "1", "remote": "2", "hybrid": "3"}[brief.workplace]]
    if brief.easy_apply_only:
        result["easyApply"] = True
    return result


class ApifyClient:
    def __init__(self, token: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self._token = token
        self._transport = transport

    async def _request(self, method: str, path: str, *, params=None, body=None, starting=False):
        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=httpx.Timeout(30, connect=10),
                follow_redirects=False, trust_env=False,
            ) as client:
                response = await client.request(
                    method, API_BASE + path,
                    headers={"Authorization": f"Bearer {self._token}"},
                    params=params, json=body,
                )
        except (httpx.HTTPError, OSError, ValueError):
            raise ProviderError("apify_network", "Apify could not be reached. No automatic paid retry was made.",
                                uncertain=starting) from None
        status = response.status_code
        if status in {401, 403}:
            raise ProviderError("apify_auth", "Apify rejected the configured token or its permissions.")
        if status == 402:
            raise ProviderError("apify_credit", "Apify requires available credit for this operation.")
        if status == 429:
            raise ProviderError("apify_rate_limit", "Apify rate-limited this operation. Wait before checking again.")
        if status >= 300:
            raise ProviderError("apify_response", "Apify returned an unsuccessful response.",
                                uncertain=starting and status not in {400, 404, 405, 422})
        if len(response.content) > 8 * 1024 * 1024:
            raise ProviderError("apify_response", "Apify returned an oversized response.", uncertain=starting)
        try:
            return response.json()
        except (ValueError, TypeError):
            raise ProviderError("apify_response", "Apify returned an unreadable response.", uncertain=starting) from None

    @staticmethod
    def _run(payload, *, starting=False) -> Run:
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise ProviderError("apify_response", "Apify did not return run details.", uncertain=starting)
        run_id = data.get("id")
        status = data.get("status")
        dataset = data.get("defaultDatasetId")
        if (not isinstance(run_id, str) or not ID_PATTERN.fullmatch(run_id)
                or not isinstance(status, str) or status not in RUN_STATES):
            raise ProviderError("apify_response", "Apify returned incomplete run details.", uncertain=starting)
        if dataset is not None and (not isinstance(dataset, str) or not ID_PATTERN.fullmatch(dataset)):
            raise ProviderError("apify_response", "Apify returned an invalid dataset reference.", uncertain=starting)
        return Run(run_id, status, dataset)

    async def start(self, brief: SearchBrief) -> Run:
        payload = await self._request(
            "POST", f"/acts/{ACTOR.replace('/', '~')}/runs",
            params={"maxItems": brief.max_results, "maxTotalChargeUsd": brief.max_charge_usd, "timeout": 300},
            body=actor_input(brief), starting=True,
        )
        return self._run(payload, starting=True)

    async def status(self, run_id: str) -> Run:
        if not ID_PATTERN.fullmatch(run_id):
            raise ProviderError("invalid_run", "The saved Apify run reference is invalid.")
        payload = await self._request("GET", f"/actor-runs/{run_id}")
        result = self._run(payload)
        if result.id != run_id:
            raise ProviderError("apify_response", "Apify returned a different run reference.")
        return result

    async def items(self, dataset_id: str, limit: int) -> list[dict]:
        if not ID_PATTERN.fullmatch(dataset_id):
            raise ProviderError("invalid_dataset", "The saved dataset reference is invalid.")
        collected = []
        while len(collected) < limit:
            size = min(25, limit - len(collected))
            page = await self._request("GET", f"/datasets/{dataset_id}/items",
                                       params={"format": "json", "clean": "true", "offset": len(collected), "limit": size})
            if not isinstance(page, list):
                raise ProviderError("apify_response", "Apify returned an unreadable dataset page.")
            collected.extend(page[:size])
            if len(page) < size:
                break
        return collected
