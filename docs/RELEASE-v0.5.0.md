# v0.5.0 — the buyer-side verification pipeline, complete

Three release-notes-worthy arcs land together. Nothing here changes a verdict
on existing fixtures; everything is additive, and 375 tests hold the line
(248 at v0.4.1).

## The pipeline (BP r28 pages 8/10, closed)

`prepare` maps a native Intercom/Zendesk export onto the canonical columns —
judgement columns stay empty for human review, native signals travel as
`hint_*` leads, every value carries `prov_*` provenance, and `--inspect`
aligns before any number exists. `recount` applies the vendor's own published
rules line by line (findings both ways, UNPROVABLE never guessed), with an
optional `--contract` overlay whose outcome-standard findings are a separate
lane, never netted into the claim. `dispute` builds the negotiable pack;
`recovery` records what the vendor actually conceded, counted separately;
`crosscheck` puts the buyer's billing ledger beside the export and names
every disagreement without resolving it; `crm-join` fills empty judgement
cells from the buyer's own business records and names conflicts. `verify`
composes all lanes into one Verified Ledger; `dashboard` renders it as an
offline single-file HTML page.

## The vocabulary

PASS / FAIL / UNPROVABLE rides on every line and summary, in the CLI and the
browser-local recount, guarded by a cross-language parity test. The three
kinds of money are labelled wherever they appear: claim / leverage / realized.

## Outcome units and what comes after (BP r28 pages 14/15)

`outcomes` verifies outcome-unit JSONL fail-closed (counted + criteria_unproven
is an inconsistency, refused), the schema covers qualified_lead,
completed_case, action (allowance-aware), and usage_aggregate — one evidence
plane across the BP's three billing stages. `period-compare` gives the
monthly ritual an honest delta; `template` turns appendix-E reuse into a
portable method artifact; `certify` grades an artifact on the AMS-1 adoption
ladder (Stage 0..3) and emits a deterministic digest for signing outside the
package; `incrementality` produces treatment-vs-holdout statistics with the
claim boundary printed — evidence about a difference, never a verdict.

## Discipline unchanged

Zero runtime dependencies; no network code (an import guard covers every new
module); judgement stays 100% rule-based; no message text is read. PyPI
publishing of this tag is gated on the account-recovery step the project
owner is completing; the GitHub Release ships regardless.
