# Tau Scout search positioning: Google demand and competition

Research date: **13 November 2026**. This is a dated, bounded discovery study. Monthly search volume and numeric Google keyword difficulty are **unknown**. The recommended wording is a testable positioning choice, not a promise of traffic or rankings.

## Decision

Use **Tau Scout — LinkedIn Job Search MCP Server** as the display title. Use **LinkedIn jobs MCP server** as a natural secondary variant and explain **Apify setup with your own token** in the connection guide. Keep the published repository URL, Python package, executable and MCP tool names stable.

The `job search` phrase family has relevant Google Autocomplete suggestions and matches Scout's actual job-search workflow. Actual Google results also show a meaningful incumbent: `stickerdaniel/linkedin-mcp-server`, with **4,205 GitHub stars** at the check. This is **moderate competition**, not an empty or easy niche. No GitHub project with tens of thousands of stars appeared in the two sampled LinkedIn job-search result sets, but that observation does not establish a complete competitor census or a measurable ranking advantage.

**Correction to the 12 November study:** sparse exact GitHub metadata matches for `LinkedIn job research MCP` did not establish Google demand or low Google competition. The actual Google query returns existing job-search products and directories. `job research` remains an accurate description of the broader workflow, but is no longer Scout's primary discovery phrase.

## Demand signals, kept separate from volume

We checked ten English query seeds through [Google's public Autocomplete endpoint](https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q=linkedin+job+search+mcp), requesting `hl=en&gl=us`. Effective localization was not independently established. Only relevant suggestions are shown below; unrelated suggestions were excluded.

| Query seed | Relevant suggestions observed | Interpretation |
|---|---|---|
| `linkedin jobs mcp` | `linkedin jobs mcp server`, `linkedin mcp job search`, `linkedin job search mcp server`, `linkedin job scraper mcp` | Supports the natural task/integration phrase family. |
| `linkedin job search mcp` | `linkedin job search mcp server`, `linkedin job search mcp` | Best match for Scout's primary wording. |
| `job search mcp server` | The seed itself; `linkedin job search mcp server` | Broad demand proxy; weaker source specificity. |
| `claude linkedin job search` | `claude linkedin job search skill`, `claude code linkedin job search`, `claude cowork linkedin job search`, `connect claude to linkedin job search` | Adjacent client/setup interest; not proof Scout has been tested in each client. |
| `apify mcp linkedin` | The seed itself; `apify linkedin mcp server` | Integration interest, but provider-heavy Google intent below. |
| `linkedin job research mcp` | `linkedin job search mcp`, `linkedin job search mcp server` | Suggestions favor the `search` family rather than a distinct `research` phrase. |
| `apify linkedin jobs mcp` | None | No suggestion signal in this sample; not proof of zero demand. |
| `resume matching mcp` | None | Demand not established here; a large adjacent incumbent also exists. |
| `cv matching mcp` | None | Demand not established here. |
| `linkedin mcp without login` | None | Useful factual feature, not a demand-established primary query. |

Autocomplete is a **qualitative proxy**, not a search-volume estimate. A Google Trends comparison for four related queries returned HTTP 429; we stopped and obtained no usable trend series. No paid SEO volume/KD account or Google Keyword Planner data was available. We therefore do not assign monthly searches, numeric difficulty, or traffic forecasts to these phrases.

## Actual Google results

These observations came from direct browser inspection of Google on the research date, separately from a general web-search tool. Search URLs requested `hl=en`, `gl=us` and `pws=0`; Google displayed “Results are not personalized”. Actual location was not verified, so these are **not universal US rankings**. AI Overview references were kept separate from ordinary organic results. The table records the visible result sample, not a fabricated complete ranked top ten.

| Actual Google query | Visible organic results | Assessment |
|---|---|---|
| [linkedin job search mcp server](https://www.google.com/search?q=linkedin+job+search+mcp+server&hl=en&gl=us&pws=0) | #1 MCPMarket job-search listing; #2 `stickerdaniel/linkedin-mcp-server`. Other observed results included Reddit, MCPServers, PulseMCP, Docker Hub, a LinkedIn video, Apify and MCP.so. | Recommended precise primary. Directories and a 4.2k-star incumbent make competition moderate. |
| [linkedin jobs mcp server](https://www.google.com/search?q=linkedin+jobs+mcp+server&hl=en&gl=us&pws=0) | #1 `stickerdaniel/linkedin-mcp-server`. Other observed results included MCPMarket, MCPServers, Reddit, `Rom7699/linkedin-jobs-mcp-server`, MCP.so, LinkupAPI, Docker Hub and Apify. | Natural secondary variant; the established competitor remains prominent. |
| [apify linkedin mcp server](https://www.google.com/search?q=apify+linkedin+mcp+server&hl=en&gl=us&pws=0) | Approximately seven of nine visible results were Apify-owned platform/Actor pages, including the official LinkedIn MCP page first and curious_coder/shahidirfan pages. | Reject as primary. Few direct GitHub results do not make the provider-dominated query easy. Use for a useful integration guide. |
| [linkedin job research mcp](https://www.google.com/search?q=linkedin+job+research+mcp&hl=en&gl=us&pws=0) | #1 MCPMarket job-search listing; #2 `saisudhir14/linkedin-mcp-search`. Other observed results included Reddit, MCPServers, LinkedIn, FirstTouch, PulseMCP, Docker Hub and Apify. | The old phrase is not an empty niche and overlaps the search family. |

The displayed ranking belongs to this dated sample. The linked queries can change. General web-search results were used only to discover additional projects and primary documentation; they were not recorded as Google ranks.

## GitHub popularity and product overlap

Stars were checked using GitHub's public repository REST API on 13 November. They screen for established adjacent projects; they are **not Google keyword difficulty**. A small direct competitor can still rank, and a provider domain can dominate without a GitHub result.

| Project | Stars at check | Overlap and consequence |
|---|---:|---|
| [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server) | 4,205 | Prominent in actual Google. Broader LinkedIn browser/session workflows, including profiles, companies, jobs and messages. Meaningful incumbent; Scout's narrower local Apify job-search workflow needs a clear explanation. |
| [Rom7699/linkedin-jobs-mcp-server](https://github.com/Rom7699/linkedin-jobs-mcp-server) | 1 | Direct jobs MCP using RapidAPI; observed in the Google sample. |
| [administrativetrick/linkedin-mcp](https://github.com/administrativetrick/linkedin-mcp) | 2 | Direct LinkedIn jobs MCP. Low stars do not imply low Google competition. |
| [johnisanerd/Apify-LinkedIn-Jobs-API](https://github.com/johnisanerd/Apify-LinkedIn-Jobs-API) | 0 | Direct Apify LinkedIn jobs project with MCP installation material; the Apify approach is not unique. |
| [borgius/jobspy-mcp-server](https://github.com/borgius/jobspy-mcp-server) | 128 | Multi-source job-search MCP wrapper; adjacent to broader job-search queries. |
| [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy) | 4,717 | Multi-board Python scraping library; adjacent infrastructure, not the same MCP/chat product. |
| [apify/apify-mcp-server](https://github.com/apify/apify-mcp-server) | 16,076 | Official platform-wide MCP. Avoid generic Apify MCP as primary; Scout is a bounded jobs-specific adapter. |
| [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher) | 29,274 | Large resume/matching product with [its own MCP documentation](https://resumematcher.fyi/docs/mcp-server/). Reject resume-matching MCP as primary: strong adjacent product and no suggestion signal in this sample. |
| [FarzamHejaziK/claude-linkedin-assistant](https://github.com/FarzamHejaziK/claude-linkedin-assistant) | 237 | Adjacent Claude job-search/outreach workflow. Scout cannot apply or send messages. |

Reproduce the popularity check using, for example, [GitHub's API record for the prominent LinkedIn MCP incumbent](https://api.github.com/repos/stickerdaniel/linkedin-mcp-server). Counts can change. The `felipfr/linkedin-mcpserver` API request returned 403; its star count remains unknown and is not treated as zero.

## Documentation and metadata application

- Put the primary phrase in the H1, first explanation, banner alt/semantic text, package description and GitHub About. Use natural variants where they describe a real feature.
- Link the practical [LinkedIn job search MCP guide](linkedin-job-search-mcp.md) from the README. Explain local stdio setup, an owned Apify token, free status/demo checks, disclosed paid limits, and follow-up in chat.
- Describe the distinct workflow accurately: no LinkedIn login, no Tau backend, locally saved results, explicit experience/student/remote checks and visible uncertainty. Live search still requires an Apify account and can incur charges.
- Keep the stable repository slug and technical identifiers. Do not rename tools or repeat phrases in historical output, source data or unrelated documentation.
- Suggested relevant topics: `linkedin-job-search`, `linkedin-jobs`, `job-search-mcp`, `mcp-server`, `model-context-protocol`, `apify`, `job-research`, `job-matching`, `ai-chat`, `python`, `local-first`.

After publication, review actual discovery/referral data and useful user feedback before expanding the phrase family. This study establishes a reasonable query to test and documents remaining competition; it does not establish enough demand to guarantee an acquisition channel.
