> Superseded for current ranking behavior by the 2026-11-11 Scout 0.2 replay. The original results below are historical evidence.

# Installed-module and output-quality check — 2026-11-11

## Verdict

The locally configured module works end to end. Its observed-listing data and transparent lexical scores are useful research inputs. **Raw Scout ordering is not sufficient as a final suitability shortlist.** Installed Skills substantially improve decisions by reading requirements and separating conflicts from unknowns. This is one ten-job exercise with three synthetic profiles, not a benchmark or a claim that the user fits these jobs.

## Actual installation and native client verification

- Installed the six companion skill folders at user scope, preserving each folder's references. All installed files matched their repository sources.
- Registered the local Scout executable in the actual Codex user-level MCP configuration and added the user-authorized Tau Apify token privately. Existing settings were preserved and the configuration remained mode 0600. No token is included in either repository.
- `codex mcp list` recognized Scout as enabled. An official SDK client launched the executable from that exact saved configuration and discovered all eight tools.
- A fresh ephemeral **Codex CLI** process, using the same user configuration, automatically discovered the native Scout MCP server and read the installed job-research, fit-review and shortlist-review skills. It completed seven native MCP calls and produced a Russian assessment. It did not launch another Python harness or a new paid search.
- Reloading the already-running desktop chat through its UI was not exercised: the Computer Use tool forbids controlling the Codex app. Native-client evidence above is from the fresh Codex CLI process; it must not be described as a hot reload of this desktop chat.

## Live run and data coverage

One new Actor run searched Product Analyst in Berlin, Germany, past week, any workplace, with Easy Apply optional. Limits: ten results, USD 0.10, 300 seconds. Apify returned SUCCEEDED in **15.022 seconds**, reporting run `usageTotalUsd` of **USD 0.0111**. This is run usage, not a reconciliation of account-wide API/storage charges.

| Measured property | Result |
|---|---|
| Saved jobs / unique IDs / canonical job URLs | 10 / 10 / 10 |
| Descriptions / source publication dates present | 10 / 10 |
| Structured workplace known | 0 / 10 |
| Structured salary bounds present | 0 / 10 |
| Titles literally containing Product Analyst | 3 / 10; the source also returned broader roles |
| Local SQL filter / Berlin filter | 8 / 10 |
| Local structured remote filter | 0, because every workplace field was unknown |
| Same-plan retry | Reused the original run; no second Actor start |

All dates reported by the source were November 5–11. Neither this nor an Actor-returned row independently establishes current availability. Full descriptions and raw provider/account artifacts are kept outside the repositories.

## Three synthetic profiles

| Profile | Raw Scout result | Description-based judgment |
|---|---|---|
| Four-year product analyst; Germany remote required | Voodoo, Pennylane, SumUp and Kaufland all score 80; tie order follows saved order | Investigate Kaufland's mobile-app fit, ablefy's remote/tooling conditions and Pennylane's senior scope. SumUp's office-first setup conflicts with required remote. No unconditional match is established. |
| Six-year senior mobile-game analyst; Germany remote | Voodoo first at 100 | Voodoo is a supported priority for investigation, subject to employment-country/sponsorship checks. Kaufland is an adjacent non-game option if that pivot is wanted. |
| Six-month Excel/Power BI reporting intern; sponsorship needed | Sonova Manager Data Analytics first at 60 | No supported junior-data recommendation. Sonova explicitly needs five-plus years and SQL. The UX role is only an optional pivot requiring employer/sponsorship checks. |

The fresh Codex result and independent evaluator broadly agreed on these decisions. Neither treated lexical scores as interview probabilities or fabricated sponsorship. Investigate and deprioritize are judgments about supplied evidence, not proof that a person lacks unstated experience.

## Concrete quality limitations

1. **Hard constraints are not assessed from descriptions inside the raw ranking.** Sonova's manager role leads the junior result; SumUp scores 80 for a remote-required product candidate. Empty `concerns` means no structured conflict was found, not that no concern exists. Keep host review mandatory and permit an empty final shortlist.
2. **Remote metadata is absent despite explicit text evidence.** Kaufland states Germany remote; other descriptions contain Europe/time-zone remote, hybrid or office-first policies. A structured filter alone cannot answer the user's remote question. Description evidence must remain separate from country/employment eligibility.
3. **Employer and publisher can differ.** Job `4487483431` lists Jobs-im-Allgäu.de as company while its description names June Fund GmbH. Resolve identity before treating publisher information as employer research; the discrepancy is not proof of fraud.
4. **Exact phrase matching loses variants.** A/B tests, A/B test design and A/B-Testing can remain unmatched for the supplied skill A/B testing. These are useful sorting improvements, not evidence that the candidate lacks a qualification.
5. **Presentation artifacts remain.** Job `4487483431` retains `&amp;` in its title. Decode display text without erasing source evidence.
6. **The native model answer still needs consistency review.** Its SumUp decision correctly says deprioritize, but one sentence reverses the precedence between skill overlap and a hard remote conflict. The captured answer is preserved for inspection; this wording issue is not silently edited away.

No scoring or semantic-extraction algorithm was redesigned during this assessment. Recommended next changes are evidence-backed workplace/employer/requirement fields, conflict-aware final decisions, terminology normalization and output consistency checks. These are improvements to make, not claims of implemented features.

## Evidence boundaries

An independent agent reviewed all thirty synthetic-profile/job pairs using only sanitized jobs, rankings, refinements and profile summaries. A separate fresh Codex invocation verified native discovery and generated a user-facing assessment from installed skills and the configured MCP server. The public companion Skills repository contains the captured response with only its local search identifier redacted. No LinkedIn login, account browser automation, application, outreach or Tau backend was used.
