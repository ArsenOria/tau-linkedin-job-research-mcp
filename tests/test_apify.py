import asyncio
import json
from pathlib import Path

import httpx
import pytest

from tau_scout.apify import ApifyClient, actor_input
from tau_scout.config import Settings
from tau_scout.models import SearchBrief
from tau_scout.service import Scout

TOKEN = "unit-secret-do-not-expose"


def brief(**overrides):
    return SearchBrief(target_titles=["Product Analyst"], locations=["Berlin"], **overrides)


def make_scout(tmp_path, handler):
    return Scout(Settings(tmp_path, TOKEN), provider=ApifyClient(TOKEN, transport=httpx.MockTransport(handler)))


def test_actor_filter_mapping_has_no_cv_or_forced_easy_apply():
    data = actor_input(brief(workplace="remote"))
    assert data["workTypes"] == ["2"]
    assert data["rows"] == 25
    assert data["publishedAt"] == "r604800"
    assert "easyApply" not in data
    assert data["enrichCompany"] is False
    assert "publishedAt" not in actor_input(brief(posted_within="any"))
    assert actor_input(brief(easy_apply_only=True))["easyApply"] is True


async def test_capped_run_dataset_pagination_and_dedupe(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.host == "api.apify.com"
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert TOKEN not in str(request.url)
        if request.method == "POST":
            assert request.url.params["maxItems"] == "27"
            assert request.url.params["maxTotalChargeUsd"] == "0.5"
            payload = json.loads(request.content)
            assert payload["rows"] == 27 and payload["locations"] == ["Berlin"]
            return httpx.Response(201, json={"data": {"id": "runA", "status": "RUNNING", "defaultDatasetId": "dataA"}})
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "runA", "status": "SUCCEEDED", "defaultDatasetId": "dataA"}})
        start, size = int(request.url.params["offset"]), int(request.url.params["limit"])
        assert size <= 25
        rows = [{"id": str(9999901000 + i), "title": "Product Analyst", "workType": "Remote",
                 "description": "SQL and Python", "applyType": "EXTERNAL", "publishedAt": "2026-11-01",
                 "posterName": "Should not persist", "descriptionHtml": "<html>not retained</html>"}
                for i in range(start, start + size)]
        if start == 25:
            rows[0]["id"] = "9999901000"
        return httpx.Response(200, json=rows)

    scout = make_scout(tmp_path, handler)
    plan = scout.prepare_search(brief(max_results=27))
    started = await scout.search_jobs(plan["plan_id"])
    done = await scout.get_search_status(started["search_id"])
    assert done["status"] == "ready" and done["count"] == 26
    assert len([r for r in requests if r.method == "POST"]) == 1
    assert len([r for r in requests if "/datasets/" in r.url.path]) == 2
    saved = scout.get_saved_results(started["search_id"], limit=100)
    assert saved["jobs"][0]["easy_apply"] is False
    assert "Should not persist" not in str(saved)
    assert "descriptionHtml" not in str(saved)
    assert "company" in saved["jobs"][0] and saved["jobs"][0]["company"] is None


@pytest.mark.parametrize("failure", ["lost_response", "missing_id", "malformed_status", "server_error", "redirect"])
async def test_uncertain_paid_start_never_repeats_for_same_plan(tmp_path, failure):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if failure == "lost_response":
            raise httpx.ReadTimeout(f"secret in raw exception {TOKEN}", request=request)
        if failure == "server_error":
            return httpx.Response(500, text=TOKEN)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://evil.example/" + TOKEN})
        data = {"status": "RUNNING"} if failure == "missing_id" else {"id": "runA", "status": {"bad": TOKEN}}
        return httpx.Response(201, json={"data": data})

    scout = make_scout(tmp_path, handler)
    plan = scout.prepare_search(brief())
    first = await scout.search_jobs(plan["plan_id"])
    again = await scout.search_jobs(plan["plan_id"])
    polled = await scout.get_search_status(first["search_id"])
    assert first["status"] == again["status"] == polled["status"] == "start_uncertain"
    assert calls == 1 and again["reused"]
    assert TOKEN not in str([first, again, polled])


async def test_concurrent_requests_and_processes_share_one_paid_reservation(tmp_path):
    starts = 0

    async def handler(request):
        nonlocal starts
        starts += 1
        await asyncio.sleep(0.03)
        return httpx.Response(201, json={"data": {"id": "runA", "status": "RUNNING", "defaultDatasetId": "dataA"}})

    first = make_scout(tmp_path, handler)
    second = make_scout(tmp_path, handler)
    plan = first.prepare_search(brief())
    rows = await asyncio.gather(first.search_jobs(plan["plan_id"]), second.search_jobs(plan["plan_id"]))
    assert starts == 1
    assert rows[0]["search_id"] == rows[1]["search_id"]


async def test_crash_reservation_stays_uncertain_without_a_post(tmp_path):
    def forbidden(request):
        pytest.fail("A reserved plan must not be restarted")

    scout = make_scout(tmp_path, forbidden)
    plan = scout.prepare_search(brief())
    row, _ = scout.store.reserve(scout.store.get_plan(plan["plan_id"]))
    restart = make_scout(tmp_path, forbidden)
    result = await restart.get_search_status(row["id"])
    assert result["status"] == "start_uncertain"
    reused = await restart.search_jobs(plan["plan_id"])
    assert reused["reused"] and reused["status"] == "start_uncertain"


async def test_dataset_failure_retries_reading_without_new_run(tmp_path):
    starts, reads = 0, 0

    def handler(request):
        nonlocal starts, reads
        if request.method == "POST":
            starts += 1
            return httpx.Response(201, json={"data": {"id": "runA", "status": "RUNNING", "defaultDatasetId": "dataA"}})
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "runA", "status": "SUCCEEDED", "defaultDatasetId": "dataA"}})
        reads += 1
        if reads == 1:
            raise httpx.ConnectError(TOKEN, request=request)
        return httpx.Response(200, json=[{"id": "9999900001", "title": "Product Analyst"}])

    scout = make_scout(tmp_path, handler)
    start = await scout.search_jobs(scout.prepare_search(brief())["plan_id"])
    unavailable = await scout.get_search_status(start["search_id"])
    assert unavailable["status"] == "results_unavailable"
    assert TOKEN not in str(unavailable)
    ready = await scout.get_search_status(start["search_id"])
    assert ready["status"] == "ready" and ready["count"] == 1
    assert starts == 1 and reads == 2


async def test_explicit_refresh_reloads_existing_dataset_without_starting_another_run(tmp_path):
    starts, reads = 0, 0

    def handler(request):
        nonlocal starts, reads
        if request.method == "POST":
            starts += 1
            return httpx.Response(201, json={"data": {"id": "runA", "status": "RUNNING", "defaultDatasetId": "dataA"}})
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "runA", "status": "SUCCEEDED", "defaultDatasetId": "dataA"}})
        reads += 1
        rows = [{"id": "9999900001", "title": "Product Analyst"}]
        if reads > 1:
            rows.append({"id": "9999900002", "title": "Product Analyst",
                         "jobUrl": "https://de.linkedin.com/jobs/view/analyst-9999900002"})
        return httpx.Response(200, json=rows)

    scout = make_scout(tmp_path, handler)
    plan = scout.prepare_search(brief())
    start = await scout.search_jobs(plan["plan_id"])
    sid = start["search_id"]
    assert (await scout.get_search_status(sid))["count"] == 1
    assert (await scout.get_search_status(sid))["count"] == 1
    assert reads == 1
    refreshed = await scout.get_search_status(sid, refresh_results=True)
    assert refreshed["status"] == "ready" and refreshed["count"] == 2
    assert refreshed["run_id"] == start["run_id"]
    assert (await scout.search_jobs(plan["plan_id"]))["reused"]
    assert starts == 1 and reads == 2


async def test_refresh_replaces_bounded_snapshot_and_preserves_it_on_read_failure(tmp_path):
    starts, reads = 0, 0

    def handler(request):
        nonlocal starts, reads
        if request.method == "POST":
            starts += 1
            return httpx.Response(201, json={"data": {"id": "runA", "status": "RUNNING", "defaultDatasetId": "dataA"}})
        if "/actor-runs/" in request.url.path:
            return httpx.Response(200, json={"data": {"id": "runA", "status": "SUCCEEDED", "defaultDatasetId": "dataA"}})
        reads += 1
        if reads == 3:
            raise httpx.ReadTimeout("temporary read failure", request=request)
        if reads == 4:
            return httpx.Response(200, json=[{"title": "Missing job identity"}])
        if reads == 5:
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=[{"id": "9999900001" if reads == 1 else "9999900002", "title": "Analyst"}])

    scout = make_scout(tmp_path, handler)
    start = await scout.search_jobs(scout.prepare_search(brief(max_results=1))["plan_id"])
    sid = start["search_id"]
    assert (await scout.get_search_status(sid))["count"] == 1
    refreshed = await scout.get_search_status(sid, refresh_results=True)
    assert refreshed["count"] == 1
    assert scout.get_saved_results(sid)["jobs"][0]["external_id"] == "9999900002"
    failed = await scout.get_search_status(sid, refresh_results=True)
    assert failed["status"] == "results_unavailable"
    assert scout.get_saved_results(sid)["jobs"][0]["external_id"] == "9999900002"
    malformed = await scout.get_search_status(sid)
    assert malformed["status"] == "results_unavailable"
    assert scout.get_saved_results(sid)["jobs"][0]["external_id"] == "9999900002"
    empty = await scout.get_search_status(sid)
    assert empty["status"] == "ready" and empty["count"] == 0
    assert scout.get_saved_results(sid)["jobs"] == []
    assert starts == 1 and reads == 5


async def test_stale_poll_cannot_regress_ready_state(tmp_path):
    delayed = asyncio.Event()
    release = asyncio.Event()
    polls = 0

    async def handler(request):
        nonlocal polls
        if request.method == "POST":
            return httpx.Response(201, json={"data": {"id": "runA", "status": "RUNNING", "defaultDatasetId": "dataA"}})
        if "/actor-runs/" in request.url.path:
            polls += 1
            if polls == 1:
                delayed.set()
                await release.wait()
                status = "RUNNING"
            else:
                status = "SUCCEEDED"
            return httpx.Response(200, json={"data": {"id": "runA", "status": status, "defaultDatasetId": "dataA"}})
        return httpx.Response(200, json=[{"id": "9999900001", "title": "Product Analyst"}])

    first, second = make_scout(tmp_path, handler), make_scout(tmp_path, handler)
    started = await first.search_jobs(first.prepare_search(brief())["plan_id"])
    stale = asyncio.create_task(first.get_search_status(started["search_id"]))
    await delayed.wait()
    complete = await second.get_search_status(started["search_id"])
    assert complete["status"] == "ready"
    release.set()
    result = await stale
    assert result["status"] == "ready"
    saved = first.get_saved_results(started["search_id"])
    assert saved["status"] == "ready" and saved["total"] == 1


@pytest.mark.parametrize("status", [401, 402, 403, 429])
async def test_definite_start_failure_is_sanitized_and_not_retried(tmp_path, status):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(status, text=f"provider raw secret {TOKEN}")

    scout = make_scout(tmp_path, handler)
    plan = scout.prepare_search(brief())
    first = await scout.search_jobs(plan["plan_id"])
    again = await scout.search_jobs(plan["plan_id"])
    assert first["status"] == again["status"] == "failed"
    assert calls == 1 and TOKEN not in str(first)
