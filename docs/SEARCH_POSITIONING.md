# Search positioning for Tau Skills and Tau Scout

Research date: **12 November 2026**. This is a dated discovery snapshot, not a search-volume study or a guarantee of search-engine placement.

## Recommended names and phrase families

| Repository | Display title / primary phrase | Suggested public slug | Short description |
|---|---|---|---|
| Skills | **Tau Skills — Job Research Skills for AI Chat** | `tau-job-research-skills` | Job research skills for AI chat: turn a CV and preferences into an evidence-based shortlist, fit review and company brief. |
| Scout | **Tau Scout — LinkedIn Job Research MCP** | `tau-linkedin-job-research-mcp` | Local LinkedIn job research MCP server with your own Apify token, CV-to-job fit checks and evidence-based shortlists. |

The Python package and installed executable can remain `tau-job-scout`; a descriptive public repository slug does not require renaming the runtime. Keep clone-directory instructions consistent with whichever slug is published. Brand + task + format gives each repository a distinct purpose while the companion links connect them.

## Competition sample

The counts below are the live GitHub repository-search `total_count` returned for the **exact query shown**, sorted by stars, with the highest-star results inspected. They are not Google result counts, full-text/code occurrence counts, traffic estimates, or measures of how hard it will be to rank. A zero means this bounded query returned no repositories; related projects still exist.

| Phrase | Reproducible GitHub query | Returned repositories | Highest observed competitor(s), stars | Decision |
|---|---|---:|---|---|
| AI job search | [`"ai job search"`](https://github.com/search?q=%22ai%20job%20search%22&type=repositories&s=stars&o=desc) | 1,761 | [career-ops-hq/career-ops](https://github.com/career-ops-hq/career-ops) — 82,111; [ai-job-search-dev/ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) — 71,364 | High overlap with large application frameworks; secondary context only. |
| LinkedIn scraper | [`"linkedin scraper"`](https://github.com/search?q=%22linkedin%20scraper%22&type=repositories&s=stars&o=desc) | 1,296 | [joeyism/linkedin_scraper](https://github.com/joeyism/linkedin_scraper) — 4,675 | Broad scraping intent includes profiles, not just job research; secondary source explanation only. |
| LinkedIn MCP | [`"linkedin" mcp`](https://github.com/search?q=%22linkedin%22%20mcp&type=repositories&s=stars&o=desc) | 1,480 | [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server) — 4,191 | Large adjacent profile/message/browser MCP; retain as secondary category. |
| Job research skills | [`"job research skills"`](https://github.com/search?q=%22job%20research%20skills%22&type=repositories&s=stars&o=desc) | 1 | [rumihut/job-researcher-landing](https://github.com/rumihut/job-researcher-landing) — 0 | Best Skills phrase family; accurate and comparatively sparse exact metadata match. |
| Job research for AI chat | [`"job research" "AI chat"`](https://github.com/search?q=%22job%20research%22%20%22AI%20chat%22&type=repositories&s=stars&o=desc) | 0 | No returned repository for this query | Use to explain the chat workflow; demand was not measured. |
| LinkedIn job research MCP | [`"linkedin job research" mcp`](https://github.com/search?q=%22linkedin%20job%20research%22%20mcp&type=repositories&s=stars&o=desc) | 0 | No returned repository for this query | Best Scout primary phrase: source + user task + integration. |
| Apify job research MCP | [`"apify" "job research" mcp`](https://github.com/search?q=%22apify%22%20%22job%20research%22%20mcp&type=repositories&s=stars&o=desc) | 0 | No returned repository for this query | Scout integration/bring-your-own-token secondary phrase. |
| Local job research MCP | [`"local" "job research" mcp`](https://github.com/search?q=%22local%22%20%22job%20research%22%20mcp&type=repositories&s=stars&o=desc) | 0 | No returned repository for this query | Scout architecture secondary phrase; accurately reflects local stdio. |
| Job search brief skill | [`"job search brief" skill`](https://github.com/search?q=%22job%20search%20brief%22%20skill&type=repositories&s=stars&o=desc) | 0 | No returned repository for this query | Skill-level documentation phrase; narrower than whole-repo positioning. |
| Student job matching MCP | [`"student" "job matching" mcp`](https://github.com/search?q=%22student%22%20%22job%20matching%22%20mcp&type=repositories&s=stars&o=desc) | 0 | No returned repository for this query | Feature documentation only; Tau also serves non-student candidates. |
| Evidence-based job matching | [`"evidence based" "job matching"`](https://github.com/search?q=%22evidence%20based%22%20%22job%20matching%22&type=repositories&s=stars&o=desc) | 31 | [5JjiaLin/JobHuntBot](https://github.com/5JjiaLin/JobHuntBot) — 2 | Useful feature language; hyphenation/variants affect search results. |
| Codex job research skills | [`"codex" "job research" skills`](https://github.com/search?q=%22codex%22%20%22job%20research%22%20skills&type=repositories&s=stars&o=desc) | 7 | [qiusuo0226/job-research-analyst-skill](https://github.com/qiusuo0226/job-research-analyst-skill) — 2 | Skills client-specific secondary phrase; avoid implying universal client support. |

A broader query, `"job research" skills`, returned **26 repositories**, led by [TheQuantPy/quant-jobs-research](https://github.com/TheQuantPy/quant-jobs-research) at **13 stars**. The narrower exact phrase `"job research skills"` returned one zero-star landing-page repository. These differing counts illustrate how query formulation changes the sample.

## Search-engine cross-check

The web search tool was also queried with `job research skills AI chat github`, `LinkedIn job research MCP github`, `LinkedIn job shortlist MCP github`, `Apify job research MCP github`, and quoted versions of the recommended phrases. The sampled results did not establish an incumbent with tens of thousands of stars for either complete recommended primary phrase. Broader variants did surface adjacent MCP projects, including [TSS99/linkedin-mcp](https://github.com/TSS99/linkedin-mcp), [raaaaaif/linkedin-research-agent-mcp](https://github.com/raaaaaif/linkedin-research-agent-mcp), and [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server). The first two had **0 stars** and the latter **4,191** in the live public GitHub API snapshot.

These are useful comparisons because Tau Scout is narrower: local job research via a configured Apify Actor, rather than a signed-in LinkedIn browser/profile/outreach system. Describe the implemented source and workflow accurately. Exact quoted searches returning few results can also indicate low demand; this research did not measure query volume, click-through rate, conversions, or Google-specific personalized rankings.

## Where the phrases belong

- Put each primary phrase in the repository display title/H1, first explanatory paragraph, About description and banner alt text.
- Use its natural variants in installation and workflow headings, usage examples, package description and relevant supporting documentation.
- Use shared terms where the described feature is present: **AI chat job research**, **CV-to-job fit review**, **evidence-based job shortlist**, **student-program matching**, and **remote eligibility checks**.
- Scout-specific terms: **local MCP server**, **LinkedIn job shortlist**, **bring your own Apify token**. Skills-specific terms: **Codex job research skills**, **job search brief skill**, **company research brief**.
- Keep source code identifiers, tool names, skill names, licenses, factual evidence and historical reports precise. Keyword placement should help a reader identify the feature and follow setup, rather than change technical contracts or make unsupported claims.

Suggested About topics (select only relevant ones and check GitHub's current topic limits): `job-research`, `job-search`, `agent-skills`, `codex`, `cv-analysis`, `job-matching`, `linkedin-jobs`, `mcp-server`, `model-context-protocol`, `apify`, `python`, `local-first`. The Skills repository does not itself implement an MCP server; keep its topics focused on skills and link the Scout companion.

## Primary evidence and method

Repository counts and exact stars were read anonymously from GitHub's public REST API (`GET /search/repositories?q=...&sort=stars&per_page=3` and `GET /repos/{owner}/{repo}`), without account tokens or mutations. Search-engine examples were opened on GitHub to inspect actual scope; no competitor implementation was copied.

- [career-ops](https://github.com/career-ops-hq/career-ops) — **82,111 stars**, broad AI job search/application workflow.
- [ai-job-search](https://github.com/ai-job-search-dev/ai-job-search) — **71,364 stars**, CV/application/interview framework.
- [linkedin_scraper](https://github.com/joeyism/linkedin_scraper) — **4,675 stars**, LinkedIn user-data scraping library.
- [linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server) — **4,191 stars**, profiles, companies, jobs and messages.
- [job-research-analyst-skill](https://github.com/qiusuo0226/job-research-analyst-skill) — **2 stars**, adjacent career research skill.

All figures can change after the research date. GitHub stars show project visibility in this comparison; they do not determine web search ranking. Revisit positioning using actual repository discovery/referral data after publication rather than promising that Tau will outrank a competitor.
