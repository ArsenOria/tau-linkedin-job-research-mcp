# Live MCP smoke test — 2026-11-11

## Scope and measured result

The user explicitly requested a live check after the initial offline implementation. A local MCP client using the official Python SDK exercised Scout with an existing user-owned Apify credential injected only into the server process environment. No token, account data, raw Actor dataset, full job description or personal CV is committed here.

| Property | Observed value |
|---|---|
| Actor | `bebity/linkedin-jobs-scraper` |
| Query | Product Analyst; Berlin, Germany; past week; any workplace; Easy Apply not required |
| Caps sent to Apify | 5 results; USD 0.10; 300 seconds |
| Actor result | SUCCEEDED; 5 dataset rows |
| Runtime reported by Apify | 23.71 seconds |
| Run `usageTotalUsd` reported by Apify | USD 0.0056 |
| Paid Actor runs started | 1 |
| Saved after correction | 5 unique canonical jobs; 0 invalid rows |
| Lexically ranked / containing SQL | 5 / 5 |
| Structured remote-only filter | 0; all five source workplace fields were unknown |
| Repeat start for original plan | Same run and search identity; `reused: true` |
| Structured import of one observed job | Succeeded; 1 saved job |

The reported run usage is not a universal price quote or a reconciliation of account-wide storage/API charges. Runtime excludes the assistant's setup and analysis time.

## Defect found and recovery

The first read retained only one of five rows. Four legitimate job links used the regional `de.linkedin.com` hostname, rejected by the initial URL validator. The identity validator now accepts apex, `www`, and two-letter regional LinkedIn hosts, still rejects lookalike/credential-bearing URLs, and returns canonical numeric-ID job URLs.

Added `get_search_status(search_id, refresh_results=true)` so the assistant can reread the original completed run through MCP after an adapter correction. This recovered all five rows without another paid Actor run. Refresh is explicit; ordinary status checks continue using cached completed results.

Independent review caught a snapshot bug in the first refresh implementation: disjoint refreshes could retain old rows and exceed the plan cap. Successful refreshes now replace the snapshot atomically. Retrieval failure or wholly invalid nonempty provider data preserves prior jobs with an unavailable status. Successful empty retrieval replaces the snapshot with an empty one. An independent reviewer reproduced and verified all four cases with one provider start.

The final offline suite passes **41 tests**. Seventeen affected Apify tests were also independently run during targeted review.

The rebuilt wheel was then installed outside the source checkout and used over real MCP to refresh the same live dataset, rank/filter all five jobs, repeat the original plan and import one observed job. All steps passed without another Actor start. Verified wheel SHA256: `ae4ddacb9df06941a20c9ad4540c288f5a991f0d81cef93550d50576e8db52cf`.

## Observed listings

These rows were returned by the Actor on this date, not independently certified as still accepting applications. Titles may be adjacent to the query; source matching is not exact.

| Employer | Role | Source publication date | Canonical link |
|---|---|---|---|
| SumUp | Senior Product Analyst | 2026-11-09 | [LinkedIn](https://www.linkedin.com/jobs/view/4487169531/) |
| Pennylane | Senior Product Analyst | 2026-11-08 | [LinkedIn](https://www.linkedin.com/jobs/view/4444702320/) |
| F. Schumacher & Co. | Senior Quantitative Analyst | 2026-11-07 | [LinkedIn](https://www.linkedin.com/jobs/view/4461901236/) |
| Voodoo | Senior Game Data Analyst — Paper.io 2 | 2026-11-05 | [LinkedIn](https://www.linkedin.com/jobs/view/4479537318/) |
| Kaufland e-commerce | Product Analyst — Mobile App | 2026-11-11 | [LinkedIn](https://www.linkedin.com/jobs/view/4488681762/) |

## Important source limitation

The Actor left every `workType` blank in this sample. Consequently the structured remote filter correctly returned zero *confirmed structured matches*, even though some descriptions contained remote policies. The host assistant must read those descriptions and distinguish evidence from unknowns; zero filtered rows must not be presented as proof that no remote positions exist. Job availability, remote-country eligibility, sponsorship and salary still require source-specific checks.

## What this does not establish

This is one bounded live query, not a coverage, reliability or quality benchmark. It does not test all geographies, automatic skill discovery in desktop UI, installation screens or a one-click installer. No LinkedIn login, browser session, application, outreach or Tau backend was used. Skills were applied by the chat agent from their files; the live MCP client was an operator test harness, not a claim that every chat host is already configured.
