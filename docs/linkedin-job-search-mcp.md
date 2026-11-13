# LinkedIn job search MCP server: connect Scout to AI chat

Tau Scout gives a local MCP-capable AI chat tools to search LinkedIn job listings through Apify and review a saved shortlist. You describe the job search and follow up in ordinary language. The chat client starts Scout as a local stdio process; there is no Tau-hosted MCP URL.

## What runs where

| Component | Responsibility |
|---|---|
| Your AI chat | Reads the CV you choose to share, proposes search criteria, explains evidence and uncertainty. |
| Local Scout MCP server | Validates a bounded plan, calls the supported Apify Actor, saves results and applies explicit fit checks. |
| Your Apify account | Supplies the API token and pays for live Actor runs from your balance. |
| Tau Skills, optional | Adds six job-research instructions to the assistant; it does not install or host Scout. |

Scout needs no LinkedIn login or LinkedIn session cookie. It does require your own Apify account for live searches. Apify is a third-party scraping platform; using its API is not official LinkedIn authorization. Scout supports only `bebity/linkedin-jobs-scraper`, and source availability and prices can change. See [the Apify adapter notes](apify-setup.md) and [data flow](data-flow.md).

## Connect once, then work in chat

1. Follow [First connection in the README](../README.md#first-connection) to clone and install the Python package. Python 3.11+ and local stdio MCP support are required.
2. Add `tau-job-scout` to your AI client's MCP settings, pointing at the absolute path to the installed `.venv/bin/tau-job-scout` executable. The README includes Codex TOML and a JSON example for other local clients.
3. Create or find a token in [Apify Console → Settings → API & Integrations](https://console.apify.com/settings/integrations). Add it as `APIFY_TOKEN` in the MCP server's private environment settings. Never paste it into the conversation or commit it. Scout does not automatically load `.env` files.
4. Reconnect the server. Optionally install [Tau Skills](https://github.com/ArsenOria/tau-job-research-skills#skills) separately to guide the assistant's brief, search and fit-review workflow.

An environment variable exported in an unrelated terminal is not automatically available to an already-running desktop chat. Use the client's server environment settings or its documented environment forwarding. Clients that support only remote connectors cannot launch this local stdio preview.

## Check the connection without paying

Say in chat:

> Check Scout's connection and token presence without revealing the token. Do not start a search or make paid requests.

The assistant uses `get_scout_status`. `apify_configured: true` means a token is present locally; it does not prove that Apify accepts it or that your account has credit.

Then try the synthetic workflow:

> Use Scout's synthetic demo to show Product Analyst roles in Berlin and compare SQL and Python relevance. Do not make paid requests.

The assistant prepares a demo plan, reads the synthetic results and reviews them in chat. These are not real openings or application links. No Apify token is needed for demo or imported data.

## Start a small live search

After setup, say:

> Find up to five Product Analyst roles in Berlin from the past week, with a $0.10 search cap. Show the proposed source and limits before starting. Compare the results with my attached CV and flag remote-location restrictions.

The assistant uses `prepare_search` to show a bounded plan, then `search_jobs` to start that plan and `get_search_status` to check the same run. Live searches charge your Apify account. A cap limits a run; it is not a price quote or a promise of five relevant results. Token and credit errors can only be confirmed when Apify is contacted.

Scout reserves the paid operation before sending it and will not start another run for the same plan. If a start is uncertain, inspect Apify Console before creating a fresh plan. There is no automatic paid retry or background scheduler.

## Refine the same shortlist in chat

> Keep roles that allow remote work from Germany. Explain which location restrictions are confirmed and which need checking. Do not search again.

> Prioritize student placements that fit my degree and graduation year. Keep uncertain eligibility visible.

> Explain the first three matches using evidence from my CV and the saved job descriptions.

The assistant reuses saved results with `get_saved_results`, `rank_jobs` and `refine_shortlist`. Scout normalizes common skill aliases and checks supplied experience, education and remote constraints. Its deterministic scores are not interview probabilities. An unknown remote country, publication date or employer remains uncertain; a recently collected listing does not prove a new posting or a still-open role.

The CV stays with the host assistant unless you choose to share it elsewhere. Scout accepts a minimal structured candidate profile for ranking and does not send the CV to Apify. See [matching and uncertainty](../README.md#matching-and-uncertainty) for the supported evidence fields.

## Common questions

**Is this a general LinkedIn MCP server?** It is focused on job search and shortlist review. It cannot log into LinkedIn, scrape personal profiles, apply for jobs or send outreach messages.

**Do I need another model API key?** No. Your existing AI chat provides the reasoning; Scout provides local tools and the Apify connection.

**Can I use it without Apify?** Yes, with the synthetic demo or jobs supplied in chat through `import_jobs`. Live LinkedIn searches use the supported Apify Actor.

**Are Skills and Scout the same installation?** No. [Tau Skills](https://github.com/ArsenOria/tau-job-research-skills) contains assistant instructions; Scout is the executable MCP server. Install both if you want the guided research workflow plus live search tools.

For exact inputs and outputs, see the [tool contract](tool-contract.md). For the dated search-positioning evidence behind this documentation, see [the positioning study](SEARCH_POSITIONING.md).
