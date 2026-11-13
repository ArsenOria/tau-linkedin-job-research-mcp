# Public repository review — 2026-11-12

Scope: the standalone Tau Scout and Tau Skills source repositories, their reachable Git history, public fixtures, licenses, workflows and publication documentation. No private account configuration, real candidate store or credentials were read for this review.

## Source and history

- Reviewed 100 Scout and 54 Skills historical blobs across the seven and six commits present at the start of review. Checks covered token/private-key patterns, credential-bearing URLs, private machine paths, the real account address and accidentally committed runtime artifacts. No matching secret or real-profile content was found in those blobs. Pattern checks are bounded evidence, not a proof that any possible secret is absent.
- Public candidate examples and comparison reports identify their profiles as synthetic. They contain concise sourced observations rather than complete live job descriptions or raw Actor datasets. The private forty-job replay and real candidate inputs are outside these repositories.
- Existing history contains a local-machine author/committer identity. Publish with the intended Tau team Git identity; a clean publication snapshot can preserve the original local development history separately. An email in commit metadata does not establish which GitHub account owns a repository.
- The implementation is standalone: no private Tau modules, production prompt files, browser profiles, account/billing services, worker queues or application/outreach engine are included. The documented open/closed boundary matches the inspected imports and tools.

## Runtime and CI

- Both repositories carry an MIT license. The Scout package declares MIT and includes its source license.
- CI uses `push`/`pull_request` with `contents: read`, not privileged `pull_request_target`. Scout tests use synthetic fixtures and fake HTTP transports; CI explicitly empties the Apify token and isolates data. No CI step launches a paid search or uses account secrets. Skills CI validates and packages the six instruction folders.
- Ignore rules exclude environment secrets, virtual environments and generated packages. Scout additionally excludes database files and caches. The tracked `.env.example` contains empty placeholders.
- Fixed a documentation overstatement: dedicated poster/recruiter profile fields are omitted, but saved description text can contain contact details from its source. The data-flow and tool-contract pages now state that accurately.
- No business logic changed during publication review, so the earlier 193-test result is not presented as a newly repeated test run. Header/link/package checks are assessed separately.

## Publication checks

Independently spot-checked the [positioning research](SEARCH_POSITIONING.md) against anonymous GitHub API responses: the two recommended exact phrase queries and the leading adjacent projects supported the recorded comparison. Star counts can change even within the review; this does not make them search-ranking evidence.

Both original Tau banner SVGs parse correctly, include accessible titles/descriptions and contain no scripts, foreign-object content or external asset references. Rendered previews were visually checked for clipping and legibility. Each README has one H1, image alt text, working section navigation and factual static badges; all 37 local file references and seven same-page anchors checked across the two READMEs resolved. Runtime package/tool names remain stable while the public slugs describe the job-research workflow.

No source-level publication blocker remains in the reviewed snapshot. After the new Tau account could not be accessed, the user explicitly authorized publication through their existing Oria account. The final owner is `ArsenOria`; this change was checked against the authenticated account's existing Tau project. The clean publication snapshot excludes `.git`, preserving local development history separately, and its initial commit is intended to use `Tau Team <team@get-tau.com>`. Companion links use the final repository names; repository About/homepage/topics should be checked after creation. This review does not authorize publishing under a different account merely because it is currently logged in.

Search observations do not guarantee search-engine ranking, traffic or the absence of competitors. Public project language should describe supported research workflows without claiming official LinkedIn affiliation, universal chat support, verified hiring eligibility or automatic applications.
