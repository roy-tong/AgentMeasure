# Free triage baseline — synthetic, not a paid-value demonstration

Scope: explain the retry finding in the bundled Verovo demo summary.
Input: synthetic-demo; 1 session; 10 command executions; 7 failed executions;
1 retry chain containing 3 executions. These counts come from the bundled demo.

## Finding
The summary reports repeated attempts under a retry chain. It does not identify
the command, error, environment or root cause. Seven failed executions do not
prove seven separate bugs or seven billable operations.

## Next check
Open the local HTML report and inspect the first error in the longest failure
run. Check the command's path, dependency and authentication only as hypotheses.
If a specific diagnosis is needed, optionally send a manually redacted excerpt
of that error and the relevant tool/version; do not send credentials or prompts.

## Re-check
After a justified change, run another local check with the same runtime and
comparable task/window. A lower failure count alone does not establish causality.

## Limits
No invoice, root cause or savings claim. The aggregate summary supports triage,
not a confirmed fix. This generic explanation belongs in free triage; it does not by itself justify a $10 charge.

## When a paid review could add something
Only after agreeing on a specific remaining decision and additional evidence review. The scope reply must name what the free baseline cannot answer, what will be checked, and what result would help your decision. No root cause or savings are promised. If only this generic guidance is possible, no paid review is proposed.
