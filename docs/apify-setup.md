# Apify adapter and your account

1. Create or use your own Apify account.
2. Obtain an API token from your Apify account's integration/settings UI.
3. Put `APIFY_TOKEN` in the MCP client's server-process secret/environment settings. Never pass it to Scout tools or paste it into the conversation.
4. Reconnect the server. Ask the assistant to check local configuration and prepare a small search with explicit caps before running it.

Scout reads only environment configuration; it does not load source-project environment files or use a shared Tau token. Restrict token permissions in Apify to the capabilities you need where supported. The token is sent only as an authorization header to the fixed `https://api.apify.com/v2` API, with redirects disabled. No LinkedIn password or cookies are requested.

## Supported actor

v0.1 supports only [`bebity/linkedin-jobs-scraper`](https://apify.com/bebity/linkedin-jobs-scraper), whose author describes it as not requiring a LinkedIn account or cookies. This is an actor-author capability claim, not a guarantee of completeness, availability, or permission from LinkedIn.

The adapter maps `titles`, `locations`, bounded `rows`, `publishedAt`, and `workTypes` (`1` onsite, `2` remote, `3` hybrid). It sets `easyApply` only when explicitly requested and disables `enrichCompany`/`companyProfile`. It sends neither candidate data nor CV text. `rows` applies per title × location, so the API run additionally receives global `maxItems`, `maxTotalChargeUsd`, and a 300-second timeout. Only up to the local plan result cap is read into Scout.

The public actor build's input schema was checked read-only at `https://api.apify.com/v2/acts/bebity~linkedin-jobs-scraper/builds/default` (`data.actorDefinition.input`) on 2026-11-11. A [bounded live run](LIVE_TEST.md) on the same date returned five listings. Regional LinkedIn URLs are canonicalized; this sample does not establish completeness or ongoing compatibility. Future actor changes need explicit adapter changes and fixture updates; merely changing the actor name is unsupported.

## Lifecycle and ambiguous operations

Scout starts an asynchronous run once, persists the returned run reference, and polls the same run when asked by the chat client. Dataset reads are paginated and bounded. It never follows an arbitrary URL from a job or provider response.

| Local status | Meaning / next step |
|---|---|
| `starting` | A reservation exists; do not launch another search. |
| `running` | Check the same search later. |
| `start_uncertain` | A paid start may have succeeded without a usable response. Inspect Apify Console before intentionally creating another plan. |
| `results_unavailable` | Existing run results cannot currently be read/normalized. Check the same search again; this does not start another run. |
| `failed` | Provider rejected or failed this operation. No automatic paid retry. |
| `ready` | Saved results are available; heed warnings, including empty or synthetic results. |

The same plan cannot start again even after failure. A new plan is an intentional new operation and may incur another charge. Failed provider runs can incur charges; a zero-row result can reflect invalid queries, blocked access, budget limits or no matches, so do not interpret it as proof no opportunities exist. The preview does not import partial datasets from failed runs.

For a completed run, the assistant can request `get_search_status` with `refresh_results: true` to reread that same dataset without a new Actor run. Successful retrieval replaces the bounded snapshot atomically; failed retrieval or wholly invalid nonempty data retains prior jobs with an explicit unavailable status.

Exact prices and which operations count toward billing depend on Apify and the actor. The spending cap is disclosed before a run; see [Apify run API](https://docs.apify.com/api/v2/actors-runs-post) and [actor pricing models](https://docs.apify.com/actors/running/actors-in-store).
