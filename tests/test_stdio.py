"""Exercise the installed server over the real official SDK stdio transport."""
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_demo_chat_workflow_over_stdio(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-m", "tau_scout"], env={
        "TAU_SCOUT_DATA_DIR": str(tmp_path), "APIFY_TOKEN": "",
    })
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            listing = await session.list_tools()
            assert len(listing.tools) == 8
            assert all("token" not in tool.inputSchema.get("properties", {}) for tool in listing.tools)

            async def call(name, arguments=None):
                result = await session.call_tool(name, arguments or {})
                assert not result.isError, result.content
                return result.structuredContent

            status = await call("get_scout_status")
            assert status["apify_configured"] is False
            plan = await call("prepare_search", {"source": "demo", "brief": {
                "target_titles": ["Product Analyst"], "locations": ["Berlin"], "max_results": 3,
            }})
            assert plan["paid_call"] is False
            search = await call("search_jobs", {"plan_id": plan["plan_id"]})
            assert search["status"] == "ready"
            assert search["count"] == 3
            again = await call("search_jobs", {"plan_id": plan["plan_id"]})
            assert again["search_id"] == search["search_id"] and again["reused"]
            search_id = search["search_id"]
            saved = await call("get_saved_results", {"search_id": search_id})
            assert {job["source"] for job in saved["jobs"]} == {"demo"}
            assert "Synthetic" in saved["warnings"][0]
            candidate = {"skills": ["SQL", "Python"], "target_titles": ["Product Analyst"]}
            ranked = await call("rank_jobs", {"search_id": search_id, "candidate": candidate})
            assert ranked["matches"][0]["job"]["title"] == "Product Analyst"
            assert ranked["matches"][0]["heuristic_score"] == 100
            refined = await call("refine_shortlist", {"search_id": search_id, "filters": {"workplace": "remote"}})
            assert refined["total"] == 2
            assert refined["paid_call"] is False
            imported = await call("import_jobs", {"jobs": [{"title": "Research Analyst", "external_id": "9999900020"}]})
            missing = await call("get_saved_results", {"search_id": imported["search_id"]})
            assert missing["jobs"][0]["easy_apply"] is None
            assert missing["jobs"][0]["posted_at"] is None
            # Schema violations do not echo arbitrary sensitive user-supplied values.
            invalid = await session.call_tool("prepare_search", {"brief": {
                "target_titles": [], "locations": ["Berlin"], "token": "sensitive-sentinel"}})
            assert invalid.isError
            assert "sensitive-sentinel" not in str(invalid)
            assert invalid.structuredContent["error"]["code"] == "invalid_arguments"

    # A fresh MCP process uses the persisted local store, not a process-only cache.
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool("get_saved_results", {"search_id": search_id})
            assert result.structuredContent["total"] == 3


async def test_missing_token_is_explained_in_chat_without_paid_call(tmp_path):
    params = StdioServerParameters(command=sys.executable, args=["-m", "tau_scout"], env={
        "TAU_SCOUT_DATA_DIR": str(tmp_path), "APIFY_TOKEN": "",
    })
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            plan = (await session.call_tool("prepare_search", {"brief": {
                "target_titles": ["Analyst"], "locations": ["Berlin"]}})).structuredContent
            result = await session.call_tool("search_jobs", {"plan_id": plan["plan_id"]})
            assert result.isError
            assert result.structuredContent["error"]["code"] == "apify_token_missing"
            assert "Never paste" in result.structuredContent["error"]["message"]
