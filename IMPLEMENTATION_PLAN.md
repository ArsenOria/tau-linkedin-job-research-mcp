# Tau open-source v0.1 plan

## Product decisions

- Two independent, MIT-licensed repositories: `tau-job-search-skills` (assistant instructions) and `tau-job-scout` (local MCP tools).
- Everyday interaction is a conversation with an AI assistant. No user-facing search CLI, separate dashboard, manual report transfer, or Tau account is required.
- Scout is a local stdio MCP server for a compatible desktop/agent client. The client launches it. Initial package installation and MCP/secret configuration are setup steps, not a claim of a completed one-click installer.
- The user supplies their own Apify token through the MCP process environment/host secret settings. Never ask for a token in chat or expose a token argument in an MCP tool.
- There is no Tau backend, shared Tau API key, LinkedIn login, browser automation, submission or outreach in these repositories.
- The host assistant reads an attached CV and proposes a minimal structured candidate profile; the user can correct it in chat. Scout does not need to read arbitrary files or send a CV to Apify.
- The host model performs nuanced reasoning. Scout supplies transparent deterministic matching and evidence fields. No second LLM API key is required in v0.1.

## Chat workflow

1. The assistant creates a search brief from the CV and stated preferences, asking only for missing constraints.
2. `prepare_search` validates queries and returns a stored plan, source, result and spending caps, without a paid call.
3. Within the user's requested search and disclosed caps, `search_jobs` starts one Apify run and returns a local search ID/run status. It must not silently restart a paid run after an ambiguous response.
4. `get_search_status` polls the same run and saves bounded normalized results. Incomplete/failed/unknown outcomes stay explicit.
5. `get_saved_results`, `rank_jobs`, and `refine_shortlist` let the assistant show and refine results directly in chat.
6. `import_jobs` and demo data support offline use, development and unavailable providers.
7. The user opens a vacancy and applies themselves. A listing returned by a scraper is an observed listing, not proof it remains open.

## Shared data and tools

Contract version: `0.1`. The server publishes JSON Schemas generated from its Pydantic argument models through MCP `tools/list`; `docs/tool-contract.md` documents their semantics.

- Search brief: `target_titles`, `locations`, `workplace` (`any`, `remote`, `hybrid`, `onsite`), `posted_within` (`day`, `week`, `month`, `any`), `easy_apply_only` (default false), `max_results` (default 25, cap 100), `max_charge_usd` (default 0.50, cap 5.00).
- Candidate: `skills`, `target_titles`, optional explicit location/remote/work-authorization preferences. Do not infer legal eligibility from nationality or CV location.
- Job: `source`, `external_id`, canonical `url`, `title`, `company`, `location`, `workplace`, `description`, `posted_at` (nullable), `observed_at`, optional salary and `easy_apply` (nullable). Unknown stays unknown.
- Matches: transparent heuristic relevance, matched/missing stated skills, concerns and unknown conditions. No interview probabilities. The assistant must distinguish this baseline from its own deeper evaluation.
- Tool names: `get_scout_status`, `prepare_search`, `search_jobs`, `get_search_status`, `get_saved_results`, `rank_jobs`, `refine_shortlist`, `import_jobs`. Authors may refine argument details but must update the tool contract and coordinate with the other repository.

## Skills v0.1

Six self-contained, individually installable skills: `job-search-brief`, `linkedin-search-plan`, `job-research`, `fit-review`, `company-brief`, `shortlist-review`. Each includes only necessary instructions/references; the package documents installation, MCP connection, demo conversations and limitations.

Use the existing Tau job-search/application resource skills selectively as editorial input. Remove duplicated promises, unsupported availability claims and live-account automation. The company brief uses the host's available public-web tools; it does not pretend Scout has an implemented company enrichment tool.

## Scout v0.1

Python package, official MCP SDK, local SQLite, one supported Apify actor adapter (`bebity/linkedin-jobs-scraper`), file-free structured import and packaged synthetic demo jobs. The Apify adapter starts asynchronously, polls existing runs, reads bounded datasets and normalizes actor-specific output. Easy Apply is optional; omit the filter when not requested. Credentials travel only in authorization headers to the fixed Apify API host.

Record a reservation before a paid start; use stored plan/search identity to prevent duplicate starts, including concurrent calls and lost responses. Set the actor run charge/result/timeout caps. Keep state in a private user data directory, not inside the installed source package. Output errors must not reveal headers, token values, CVs, raw provider exceptions or database paths.

No scheduler, auto-apply, outreach, arbitrary URL fetching, remote MCP hosting, PDF rendering, second model API, OCR or product billing is in v0.1.

## Porting boundary

Adapt only focused job normalization, source error handling, search-filter concepts and safe CV-to-search instructions from Tau. Rewrite database-bound logic for a standalone local tool. Keep Tau auth, production prompts, matching orchestration, worker queue, browser/session code, application engine, account data and infrastructure private. Use fresh Git history and synthetic fixtures; never copy environment files or read live credentials for this implementation.

## Verification and release

- Validate skill frontmatter and local reference portability. Exercise realistic conversations using a reviewer who did not author the skills.
- Test MCP initialize/list/call via the actual SDK transport; exercise prepare -> demo/import -> saved -> rank -> refine.
- Mock Apify HTTP to cover success, actor field mapping, missing values, failure, uncertain paid starts, caps and token redaction. No paid runs or live LinkedIn calls during implementation.
- Obtain independent reviewer passes for Scout and Skills/integration, address findings and rerun affected checks.
- Create local Git repositories first. Publication, package-index uploads and service deployment are separate from this local implementation.

## Primary references checked 2026-11-11

- https://github.com/modelcontextprotocol/python-sdk
- https://apify.com/bebity/linkedin-jobs-scraper
- https://apify.com/bebity/linkedin-jobs-scraper/input-schema
- https://docs.apify.com/api/v2/actors-runs-post
- https://docs.apify.com/actors/running/runs-and-builds
- https://www.linkedin.com/legal/user-agreement (section 8.2; an Apify actor is not official LinkedIn authorization)
