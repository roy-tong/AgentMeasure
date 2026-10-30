# Repeat a review for each billing period

For local-only data handling, run `verovo recount --export FILE --vendor ID`
on your own machine. This does not fetch vendor data or prove the final invoice.

The optional **Monthly bill reconcile** workflow runs on GitHub-hosted runners.
It uploads the export, report and artifacts to GitHub; repository access controls
apply. It is not the local-only mode. Do not commit customer exports to a public
fork. [Public forks remain public](https://docs.github.com/en/pull-requests/reference/forks).

## Optional hosted setup

1. Create a **separate private repository**, with a reviewed copy of this source
   tree. Do not use a public fork for billing data. The workflow skips public repos.
   Enable Actions in that private repository; enable Issues only if you want tracking.
2. Copy `examples/reconcile.example.json` to `.verovo/reconcile.json`.
   Set the vendor and `billing_period` (`YYYY-MM`).
3. Prepare and review that period's export. Required fields are
   `conversation_id,human_agent_participated,issue_addressed,customer_recontacted_within_window,vendor_billed`.
   Optional `customer_recontacted_at,closed_at` support the separate contract lane.
   `verovo prepare` can map supported native exports; it leaves judgement
   fields empty for review. Missing evidence remains unknown.
4. Save the reviewed file at the configured path. Compute its SHA256 locally
   with `python -c "import hashlib; print(hashlib.sha256(open('.verovo/recount-export.csv','rb').read()).hexdigest())"`
   and set `reviewed_export_sha256`. This records the reviewed file, not proof
   that its rows truly belong to that period; you must check that yourself.
5. These runtime files are gitignored. Only in the independent private repository,
   explicitly add the two reviewed files with `git add -f .verovo/reconcile.json .verovo/recount-export.csv`,
   commit, and push. This step uploads the data to GitHub.
6. Run **Monthly bill reconcile** manually. It installs the checked-out source
   revision, writes a run summary, and retains artifacts for seven days.
   Set `open_tracking_issue` to `true` only if you want a GitHub issue containing
   the report. Issues have their own retention and are not deleted with artifacts.

## Each new month

Replace the export, review it, update the billing period and hash, then commit the
new input. The workflow does **not** fetch new exports. The scheduled run on the
3rd at 09:00 UTC requires the previous calendar month and stops on stale config.
A manual run may review an older period.

Tracking is per vendor and billing period. Offsetting findings and unresolved
rows still require review even if net variance is zero. Re-running updates that
period's open issue instead of creating duplicate comments. No report is sent to
a vendor, and no refund is promised. Credits, negotiated prices, contract terms
and the actual invoice still require separate checks.

GitHub Actions and storage usage depend on your plan; this is not a guarantee of
zero cost or a fixed runtime. Use local CLI handling if you do not want hosting.
