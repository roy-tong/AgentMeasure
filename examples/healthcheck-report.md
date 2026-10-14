# Example $10 report — synthetic, not customer evidence

Scope: explain the retry finding in the bundled AgentMeasure demo summary.
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
not a confirmed fix. One clarification round is included in the service scope.
