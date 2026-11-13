# v0.1 offline review — 2026-11-11

The implementation was built by one agent and reviewed by separate agents for Scout and the Skills integration. No live Apify credentials, paid Actor runs or LinkedIn requests were used.

## Verification

- 32 project tests passed on Python 3.14, including official MCP SDK stdio transport, model validation, mapping, filtering and mocked Apify operations.
- An independent reviewer connected with the official SDK, initialized the server, discovered all eight tools and exercised demo -> saved results -> ranking -> local refinement.
- Twenty concurrent same-plan starts produced exactly one provider start. Repeated uncertain starts did not issue another start. A failed dataset read recovered by retrieving the same run.
- An independently executed concurrency reproduction verified that delayed poll responses cannot regress a ready search to running.
- The Skills reviewer confirmed agreement with published MCP schemas and exercised a no-token demo and conversational refinements.
- Source and wheel distributions built successfully. The final wheel was installed outside the source checkout and launched from that installed package over MCP. Demo/refinement, same-plan reuse, explicit missing-token errors and persisted results after restarting the MCP process passed.
- Startup errors, argument validation and token handling were checked for sensitive error output. Existing nonprivate directory permissions are preserved and rejected rather than silently changed.

Original pre-live wheel used for installed-package verification (historical snapshot):

`tau_job_scout-0.1.0-py3-none-any.whl`

SHA256: `9e83da83ff5e0d3bb9c05d9800dd4caefefd12fb479a3ab55d68df87abc0fe33`

## Resolved findings

- A delayed concurrent status response could move `ready` back to `running`. Conditional state updates and guarded transactional result writes fixed the race; the original independent reproduction now passes.
- A malformed provider status could bypass sanitized provider errors. Type validation and a focused mocked test cover it.
- Opening an existing configured data directory could modify its permissions. Existing unsuitable directories are now rejected without changing their mode.
- Demo results are a canned synthetic catalog, not a reproduction of live provider filtering. This limitation is explicit in tool results and setup documentation.

The final targeted review covered startup sanitization, date length bounds and explicit uncertainty for unconfirmed geography. No unresolved actionable findings remained in the reviewed scope.

## Limits

This initial review used synthetic HTTP responses rather than a live paid collection. The subsequent [live check](LIVE_TEST.md) records the real run, regional-URL correction, refresh snapshot review and 41-test result. Neither check establishes source completeness or continuous freshness. Desktop client settings, automatic skill discovery and a one-click installer were not exercised. CI is provided for Python 3.11/3.13 but was not run on GitHub during local implementation.
