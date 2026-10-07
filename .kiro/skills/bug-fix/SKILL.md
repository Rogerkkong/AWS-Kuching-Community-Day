---
name: bug-fix
description: Runs a disciplined, credit-efficient debugging workflow for a 3-person hackathon team building on AWS. It triages by demo impact, captures the symptom, reproduces it with a failing test or one-command repro, isolates it (layer by layer, git log/diff/bisect), finds the root cause, applies the smallest fix, adds a regression test, verifies, and writes the commit message and bug log entry. Includes AWS triage playbooks for Lambda, API Gateway and CORS, DynamoDB, IAM AccessDenied, S3, Amplify/Cognito, Bedrock and deploys, and aligns with Kiro's Bugfix spec for larger bugs. Use when someone pastes an error, stack trace, failing test or failed deploy, or says "fix this bug", "debug this", "it's broken", "it used to work", "why is this failing", "getting a 403/500/502/504", "CORS error", "AccessDenied", "Lambda timed out", "ConditionalCheckFailedException", "Bedrock access denied", "works on my machine" or "the demo is broken". Not for new features (use quick-spec) or stack changes (use architecture-selection).
metadata:
  version: "1.0"
---

# Bug Fix

Find the real cause of a defect, fix it with the smallest safe change, prove the fix with a test, and leave a short record. Tuned for this team:

- Three students on a deadline (AWS Community Day, hackathon style). A working demo beats a perfect codebase, but a guessed fix that breaks something else on stage is worse than no fix.
- An AWS-native stack recorded in `.kiro/steering/tech.md` and `structure.md` (owned by `architecture-selection`): services, languages, test runner, IaC tool. Read them; never assume a stack.
- Kiro Free: 50 credits a month per account, no top-ups; chat, spec and hook runs all draw on them. A bug hunt that "tries things" can burn a week of credits in an hour.

Invoke it as `/bug-fix <what is broken>`, or let Kiro match it from the description. The cheapest first prompt already holds the bug card's key fields (severity, symptom, exact error, `file:line`, repro, last good), so Phase 1 needs no questions:

```text
/bug-fix P0: POST /checkins returns 502 on the demo stage since the ticketType merge (last good: a1b2c3d).
Error: TypeError: Cannot read properties of undefined (reading 'toUpperCase') at src/checkin.js:18
Repro: curl -i -X POST "$API_URL/checkins" -H "Content-Type: application/json" -d '{"eventId":"e1","ticketId":"t1"}'
```

## Inputs and outputs

Inputs: the bug report (anything from a pasted stack trace to "login is broken"), the repo, and the steering files if they exist.

Outputs: a bug card (Phase 1), a failing test or repro (2), a root-cause statement with evidence (4), a minimal diff plus a red-then-green regression test (5, 6), a verification checklist, commit message and, for important bugs, a `docs/BUGS.md` entry (7, 8), and a chat summary of 10 lines or fewer.

## Operating rules (apply to every phase)

1. **Evidence before edits.** Do not change code until the bug is reproduced or there is a log line that explains it. No speculative fixes.
2. **One hypothesis at a time.** State it, name the check that would disprove it, run the check. Record disproved hypotheses; they count toward the stop rule.
3. **Turn budget.** Aim for 4 Kiro turns: (1) triage and capture, (2) reproduce, isolate and root cause, (3) fix and test, (4) verify and document. Small bugs collapse into 1 or 2 turns. Batch all questions into one message.
4. **Small diffs.** Edit only the lines on the causal path. Never regenerate or rewrite a whole file, handler or component to fix a bug.
5. **Read-only AWS by default.** You may run read-only commands (`get`, `describe`, `list`, `logs tail`) when the user's permission settings allow it. Ask before any command that creates, updates or deletes AWS resources, data or permissions.
6. **Never widen permissions to fix an error.** No `"Action": "*"`, no `"Resource": "*"` added to make an AccessDenied go away, no `Access-Control-Allow-Origin: *` with credentials, no public buckets.
7. **Protect secrets.** Never paste or echo access keys, secret keys, session tokens, JWTs, passwords, `.env` contents or presigned URLs (they grant access until they expire). Redact as `<redacted>`. If a secret was committed or shared, tell the user to deactivate or rotate it first; deleting it from git is not enough.
8. **Stay accurate.** Do not quote AWS limits, prices or quotas from memory as facts; the few long-standing hard limits stated in the playbooks are the only exception. Otherwise write "check current quotas" and name the console page or command.

## Phase 0. Triage by demo impact

Input: the report. Output: a severity, a path (fix now, workaround now and fix later, or log and defer) and an owner. This takes one line in chat.

| Severity | Meaning | Default path |
|---|---|---|
| P0 demo-blocker | The demo path cannot complete: login fails, the core API errors, the deploy is broken | Fix now. If there is no confirmed root cause within the timebox (see stop rule), ship a workaround first |
| P1 demo-visible | The demo completes but something visibly wrong happens: wrong data, error toast, very slow step | Fix before the code freeze; otherwise work around or hide it |
| P2 off-path | Real bug, not on the demo path | Log it in `docs/BUGS.md`; fix after the demo |
| P3 cosmetic | Typo, spacing, colour | Batch with other P3s, or ignore |

**One owner per bug.** The owner is the area owner in the `## Ownership` table of `structure.md` (written by `architecture-selection`), or whoever found the bug if there is no table; that table's Reviewer is the second pair of eyes for Phase 7 and any redeploy. Post the bug title and owner in the team chat so two people do not edit the same files or fix the same bug in parallel.

Choose a **workaround** instead of a fix when any of these hold: the root cause is unknown, the fix touches shared code or infrastructure, the fix estimate is more than half the time left before the demo, or the team is inside the code freeze. Workaround options, best first:

1. `git revert <sha>` the commit that introduced it, if it is known and nothing depends on it.
2. Redeploy the last known-good build or commit.
3. Disable or hide the broken control, or put it behind a flag.
4. Use seeded or fixture data for the demo path.
5. A fallback response (for example a cached result when Bedrock is throttled). Label it honestly if judges will see it.
6. Last resort inside the demo window: skip the broken step and show the team's recorded demo or screenshots for it, and say so.

Every workaround gets a `WORKAROUND(BUG-<n>)` comment in code and an entry in `docs/BUGS.md`.

**Code freeze.** Agree a freeze time with the team (for example the last 1 to 2 hours before the demo). After it: P0 only, prefer revert or workaround, no dependency upgrades, no IaC refactors, and redeploy only with a teammate watching.

## Phase 1. Capture

Input: the report. Output: a bug card in chat. Do not write it to a file yet.

Fill in what the report already says. Then, if a field that changes the investigation is missing, ask **one** batched message of at most 5 questions, each with a default, and state your assumptions. If the report already has the error text and the file or endpoint, skip the questions and move to Phase 2 in the same turn.

```text
BUG-<n>: <one-line symptom>
Severity: <P0-P3> (<demo impact>)   Path: <fix now | workaround then fix | defer>   Owner: <name>
Where: <local | personal sandbox or stage | shared demo stage>, branch <name> @ <git rev-parse --short HEAD>, region/account <alias>, <browser/device>
Steps:
  1. <...>
Expected: <...>
Actual: <exact error text, HTTP status, request ID>
Last known good: <time, commit or deploy>
Recent changes: <merges, deploys, env var or console changes, dependency bumps>
Evidence: <file:line, 10-30 log lines around the FIRST error>
Assumptions: <A1 ...>

Current:   WHEN <condition> THEN the system <incorrect behavior>
Expected:  WHEN <condition> THEN the system SHALL <correct behavior>
Unchanged: WHEN <other condition> THEN the system SHALL CONTINUE TO <existing behavior>
```

The last three lines use the same categories as Kiro's Bugfix spec (`bugfix.md`), so the card can be pasted into one if the bug is escalated (see "Escalating to a Kiro Bugfix spec").

Question template:

```text
To reproduce BUG-<n> I need a few facts. Reply "ok" to accept the defaults:
1. Which stage or URL? Default: the one in your frontend config
2. Exact error text or status from the browser Network tab or terminal? Default: none, I'll reproduce it
3. Last time it worked? Default: before today's merges
Assuming: <A1>, <A2>.
```

Exit criteria: severity, path, owner, Expected and Actual are filled in; unknowns are recorded as assumptions.

## Phase 2. Reproduce

Input: the bug card. Output: a repro that fails for the **same reason** as the report (same error message or same wrong value), not merely a repro that fails.

Preference order:

1. **An automated failing test** in the project's test runner (from `tech.md`; otherwise the language default, such as pytest for Python or Vitest/Jest for Node). Call the smallest unit that shows the bug: a handler with a saved event, or a function with the bad input.
2. **A one-command repro**: `curl -i ...`, `aws lambda invoke ...`, or a script under `scripts/repro/`. For a browser bug, open DevTools > Network, right-click the failing request and choose Copy as cURL. Run it in your own terminal; before pasting it into chat, replace the `Authorization` and `Cookie` values with `<redacted>`.
3. **Exact manual steps**, only for UI-only bugs.

Useful repro commands:

```bash
# HTTP: shows status AND headers (CORS headers included)
curl -i -X POST "$API_URL/<path>" -H "Content-Type: application/json" -d '{"example":"value"}'
# Lambda directly, with a sanitized event saved from CloudWatch or a test
aws lambda invoke --function-name <fn> --payload fileb://tests/fixtures/<event>.json out.json && cat out.json
# Tail the function's logs while reproducing
aws logs tail /aws/lambda/<fn> --since 15m --follow
```

Save captured events as `tests/fixtures/<name>.json` with tokens, emails and names replaced by fake values.

If you cannot reproduce after two attempts, do not guess-fix. Check, in order:

1. Environment differences, using the "works on my machine" list in Phase 3.
2. Intermittent causes: eventual consistency (GSI reads), cold starts and timeouts, retries and duplicate events, caching (browser, CDN, service worker), token expiry, concurrent writes.
3. Add one targeted log line with a correlation ID on the suspected path, reproduce, read it, then remove it.

Exit criteria: a repro command or test that fails, and its exact failure output in the bug card.

## Phase 3. Isolate

Input: the repro. Output: one line, `Isolated to: <layer>, <file:line or resource>, introduced by <sha or change, if known>`.

1. **Follow the request through the layers** and find the first layer where the data or status is wrong: browser (Network tab: status, request headers, response body) -> hosting (Amplify Hosting, CloudFront, S3) -> API Gateway -> Lambda (logs by request ID) -> data store or service (DynamoDB, S3, Cognito, Bedrock).
2. **Check recent changes** (free; run these yourself or ask the user to):

   ```bash
   git log --oneline --since="1 day ago"
   git log -p -5 -- <suspect-path>
   git diff <last-good-sha>..HEAD --stat
   git diff <last-good-sha>..HEAD -- <suspect-file>
   ```

   Not everything is in git. Ask the team in one message whether anyone changed env vars, Lambda settings, Cognito, IAM or the API in the console, or redeployed from another branch.
3. **Bisect** when a last-known-good commit exists and the repro is a command (exit 0 = good, non-zero = bad):

   ```bash
   git bisect start
   git bisect bad HEAD
   git bisect good <last-good-sha>
   git bisect run <repro-command>
   git bisect reset
   ```

   Bisect needs a local repro (a unit test or local script), not one that needs a deploy at every step. Make the command exit 125 on commits that do not build, so bisect skips them instead of marking them bad.

4. **Binary-search the input or code**: halve the payload, comment out half the pipeline, or toggle the feature flag until the smallest failing case remains.
5. **"Works on my machine" diff**: branch and commit, uncommitted changes, lockfile and a clean install (`npm ci` or equivalent), runtime version, `.env` and env vars, AWS profile and region (`aws sts get-caller-identity`, `aws configure list`), stage and API URL in the frontend config, which Amplify sandbox or backend the frontend points to, and browser cache or service worker.
6. **AWS symptom?** First read [references/aws-triage.md](references/aws-triage.md) (account, region, stage, request ID; short). Then read only the one playbook that matches:

| Error text or symptom | Read |
|---|---|
| `Task timed out`, `Runtime.ImportModuleError`, `Runtime.HandlerNotFound`, `signal: killed`, slow first call, missing env var, duplicate processing | [aws-lambda.md](references/aws-lambda.md) |
| Browser "CORS error", 401, 403 `Missing Authentication Token`, 404, 413, 429, 500, 502, 504 | [aws-api-gateway.md](references/aws-api-gateway.md) |
| `key element does not match the schema`, `ConditionalCheckFailedException`, throttling, missing items, `reserved keyword`, `Float types are not supported` | [aws-dynamodb.md](references/aws-dynamodb.md) |
| `is not authorized to perform`, `AccessDenied`, `explicit deny` | [aws-iam.md](references/aws-iam.md) |
| S3 403, `SignatureDoesNotMatch`, `Request has expired`, `AccessControlListNotSupported`, upload blocked by CORS | [aws-s3.md](references/aws-s3.md) |
| `NotAuthorizedException`, `UserNotConfirmedException`, `Unable to verify secret hash`, `redirect_mismatch`, `Not Authorized to access`, 404 on page refresh, Amplify build failed | [aws-amplify-cognito.md](references/aws-amplify-cognito.md) |
| `You don't have access to the model`, `inference profile`, `model identifier is invalid`, `ThrottlingException`, `Input is too long` | [aws-bedrock.md](references/aws-bedrock.md) |
| `CREATE_FAILED`, `ROLLBACK_COMPLETE`, `UPDATE_ROLLBACK_FAILED`, `Has the environment been bootstrapped`, `already exists` | [aws-deployments.md](references/aws-deployments.md) |

`ExpiredToken` and `security token ... is invalid` are credential problems, not permissions; `aws-triage.md` step 7 covers them.

Exit criteria: the isolate line is written, and the next step is a specific root-cause hypothesis.

## Phase 4. Root cause

Input: the isolated location. Output: a root-cause statement backed by evidence.

Separate the symptom from the cause. The first error the user sees is rarely the cause:

| Symptom | Common real cause |
|---|---|
| Browser says "CORS error" | The API returned 4xx or 5xx without CORS headers, or preflight (OPTIONS) is not configured or is blocked by an authorizer |
| REST API 502 | The Lambda threw, or returned a malformed proxy response |
| Lambda `Task timed out` | Waiting on a network call: a Lambda in a VPC with no route to the service, a slow Bedrock call, an unresolved promise |
| `AccessDenied` | Missing action on the role, the wrong resource ARN (for example a table but not its index), the wrong role, or an explicit deny |
| Empty list or `undefined` in the UI | Wrong field or key name, pagination not followed, eventually consistent read, wrong stage or table |
| Works locally, fails when deployed | Env var missing in the deployed function, dependency not bundled, different region, table or user pool |

Ask "why?" until you reach something you can change in code or config that would prevent the whole class of failure, not just this one input (usually 3 to 5 whys). Stop at the team's own system; "AWS is slow" is not a root cause.

```text
Root cause: <one sentence in terms of code or config, not symptoms>
Evidence: <log line, failing test output, or diff hunk>
Bug condition: <which inputs or states trigger it; everything else must keep working>
Why it was not caught: <missing validation, test or review>
```

The bug condition is the line between "must change" (inputs that trigger the bug) and "must not change" (all other inputs). It defines the regression test and the preservation check in Phase 6, the same split Kiro's Bugfix spec uses.

Exit criteria: the statement is written, and the evidence directly supports it. If the evidence is only "it seems likely", go back to Phase 3.

## Phase 5. Minimal fix

Input: the root cause. Output: the smallest diff that removes it.

1. State the plan in 3 lines or fewer (files, change, test), then make targeted edits. For P0 fixes and anything inside the code freeze, use Supervised mode so a teammate accepts or rejects each hunk.
2. Change the fewest lines that remove the cause, only in files on the causal path. As a guide, a diff of more than about 30 lines or 3 files needs a one-line justification.
3. No drive-by changes: no renames, refactors, formatting passes, dependency upgrades or "while I'm here" improvements. List them as follow-ups in the summary.
4. Do not change public contracts (API request or response shape, table keys, event schemas, auth flow) in a bug fix. If the fix needs that, apply the stop rule.
5. Fix the cause, not the symptom. Not allowed: catching and ignoring exceptions, returning 200 on error, adding `sleep` or blind retries to hide a race, raising a timeout without knowing why the call is slow, or widening IAM or CORS.
6. Config fixes (timeout, memory, env var, IAM policy, CORS) go into the IaC source (CDK, SAM, Amplify backend, Terraform or whatever `tech.md` names). A console hot-fix is acceptable only for a P0 during the demo window, and it must be copied back into IaC and logged, because the next deploy can silently overwrite console changes. Announce edits to shared IaC files in team chat first.
7. Commit or stash before each attempt, so undoing it cannot throw away other work. If an attempt fails, undo it before the next one: `git restore <file>` (or `git checkout -- <file>`), or Restore the Kiro chat checkpoint for that attempt. Restore reverts only files changed by Kiro's own file tools and drops the later chat context; manual or formatter edits to those files can be lost, and commands Kiro ran (a deploy, an AWS change) are not undone. Do not stack a second fix on top of a failed one.

Exit criteria: the diff is applied, small, and on the causal path only.

## Phase 6. Regression test

Input: the fix and the Phase 2 repro. Output: a test that failed on the old code and passes on the new code.

1. Turn the Phase 2 repro into a permanent test, or keep it if it already is one. Name it after the behavior: `accepts a check-in without ticketType and defaults to GENERAL`, not `fix bug 3`.
2. Confirm red then green: the test failed before the fix (Phase 2 output) and passes after it. A test that never failed proves nothing.
3. Add one preservation test for the nearest "Unchanged" behavior from the bug card, unless an existing test already covers it.
4. Mock AWS at the SDK boundary with whatever the repo already uses (for example `aws-sdk-client-mock` for the AWS SDK for JavaScript v3, or `moto` or botocore's `Stubber` for Python). Unit tests must not call real AWS.
5. If the bug only reproduces against real AWS (IAM, CORS, Cognito settings), keep the repro command in `scripts/repro/` as the regression check and note it in the bug log.
6. Optional: if the project already uses a property-based testing library and the bug condition covers a range of inputs, add one property test. Never add a library during a P0.
7. Inside the code freeze a test may be deferred; record `TEST-DEBT` in `docs/BUGS.md`.

Exit criteria: the regression test and the existing related tests pass.

## Phase 7. Verify

Output: this checklist, ticked, in chat.

- [ ] The Phase 2 repro now passes (same command, same stage).
- [ ] The relevant test suite passes, not just the new test. Lint and type checks pass if configured.
- [ ] If the bug was seen on a deployed stage: deployed to that stage and the repro re-run there.
- [ ] The demo path was checked end to end by hand, ideally by the teammate who reported the bug.
- [ ] The logs show no new errors for the request (filter by request ID).
- [ ] A spot check of the "Unchanged" behavior still works.
- [ ] No debug logging, hardcoded IDs, test credentials, temporary IAM grants or console-only changes are left behind.
- [ ] Any workaround is either removed or logged.

Exit criteria: every box is ticked, or the unticked ones are listed as follow-ups with an owner.

## Phase 8. Document

Output: a commit message, and a bug log entry when it is worth one.

Commit message (Conventional Commits style):

```text
fix(<scope>): <imperative summary, 72 chars or fewer>

Symptom: <what users saw>
Root cause: <one sentence>
Fix: <what changed>
Test: <test name or repro command>
Refs: BUG-<n>
```

One bug per commit, so it can be reverted on its own. Follow the branch rule in `structure.md`; by default `main` stays demo-ready and the fix goes on a short `fix/bug-<n>-<short-name>` branch merged after Phase 7.

Add an entry to `docs/BUGS.md` (create it with a `# Bug log` heading if it is missing; number entries sequentially) only for P0 and P1 bugs, AWS gotchas, recurring bugs, workarounds and test debt. Append; do not rewrite earlier entries.

```markdown
### BUG-<n> (<YYYY-MM-DD>) <title> [fixed | workaround | open]
- Symptom: <...>
- Root cause: <...>
- Fix: <commit sha or PR>
- Prevention: <test added, validation, rule>
- Follow-ups: <owner: item>
```

Then:

1. If the lesson is a standing rule (for example "every Lambda response goes through the shared `respond()` helper"), propose a one-line addition to the relevant steering file and wait for approval. `tech.md` and `structure.md` belong to `architecture-selection`; do not restructure them.
2. Tell the user what teammates must do: pull, reinstall, redeploy, regenerate frontend config, or clear test data.

## Stop and ask

Stop investigating, post a handoff note, and ask a teammate (or the user) when any of these is true:

- Two fix attempts failed, three hypotheses were disproved, or about 30 minutes (P0) or 60 minutes (other bugs) have passed without a confirmed root cause.
- The fix needs a new AWS service or a change to a core choice recorded in `tech.md` (region, compute, database, auth approach, IaC tool, backend language), for example moving long Bedrock calls that cannot finish within the API timeout to an async or streaming pattern. Hand off to **`architecture-selection`**.
- The fix needs new or changed behavior inside the current stack (an API contract change, a key-schema change or new index), no spec or teammate can say what the correct behavior is, or the "bug" is a missing feature. Hand off to **`quick-spec`**, or ask the area owner.
- The fix needs destructive or shared actions: deleting tables, buckets, stacks or data, changing IAM in a shared or event-provided account, rotating keys, force-pushing or rewriting git history.
- The error is an explicit deny from an organization policy or account restriction. Ask the account owner or the event organizers; do not work around it.
- Kiro shows the low-credit warning (Free plan users get it at 80% used). Switch to human-driven debugging with the playbooks and use Kiro only for the final edit.

```text
Stuck on BUG-<n> (<severity>), <minutes> spent.
Tried: 1) <hypothesis> -> <result>  2) <hypothesis> -> <result>
Known (with evidence): <facts>
Unknown: <the one question that would unblock this>
Repro: <command>
Ask: <specific request, e.g. "check the Cognito app client settings in the console">
```

## Escalating to a Kiro Bugfix spec

The default is this lightweight chat flow, because generating and running a spec costs more credits. Escalate to Kiro's Bugfix spec when the bug spans two or more components or owners, the fix needs more than about 3 tasks, the same class of bug has come back, or the team wants a traceable record.

1. Create a new spec and pick Bugfix when Kiro asks for the type. At the time of writing this is the + in the Specs section of the Kiro panel, or Spec in chat; if the UI differs, look for the Bugfix option when creating a spec.
2. In the first prompt, paste the bug card (including the Current, Expected and Unchanged lines), the root-cause statement and the repro command, so Kiro does not spend turns rediscovering them.
3. Kiro writes `bugfix.md` in `.kiro/specs/<bug-name>/` in place of `requirements.md` (current, expected and unchanged behavior), then `design.md` (root cause, proposed fix, properties) and `tasks.md`. Review each once and edit specific lines; do not ask for regeneration.
4. In `tasks.md`, `- [ ]*` marks an optional task. Keep the tasks that reproduce the bug, check the fix and check preservation, even if they are marked optional; skip the rest. Start tasks one at a time instead of Run all tasks, and tick `[x]` by hand any task a teammate does without Kiro; that costs no credits.
5. If those tasks call for a property-based testing library the project does not have, decide as a team; never add one during a P0.

## Credit-saving checklist

- Give Kiro the exact error line, status code, request ID, `file:line`, the command you ran and 10 to 30 lines around the first error. Do not paste whole log files, HAR files, full `node_modules` stack frames or screenshots of text.
- Do the free work yourself: run the tests, run `git bisect`, read CloudWatch in the console, click through the UI. Use Kiro for reasoning and edits.
- Operating rules 2 to 4 (one hypothesis per turn, batched questions, targeted edits) save the most. Never ask Kiro to "try things until it works" or to rewrite a file.
- Undo failed attempts with git or checkpoint Restore, not with a chat turn.
- Keep the model on Auto; other models can use more credits per request (the model picker shows the multiplier). Being stuck is a reason to apply the stop rule, not to switch to a pricier model.
- Start a fresh chat session for an unrelated bug, so old context does not ride along.
- Do not add hooks with an `agent` action (one that prompts the model) on frequent triggers such as file save or Stop while debugging; agent hook runs draw from the same credits.

## Worked example (hypothetical, condensed)

A different hypothetical project from quick-spec's check-in example: this one uses a REST API, where CORS headers come from the Lambda.

Report: "Check-in page says 'Network error' since lunch. Browser console shows a CORS error on POST /checkins."

1. **Triage.** P0: check-in is the demo path. Path: fix now, revert as fallback.
2. **Capture.** Expected: 201 and the attendee is checked in. Actual: the browser shows a CORS error. `GET /events` works. Last good: before the "add ticketType" merge. Stack (from `tech.md`): React, API Gateway REST API with Lambda proxy integration (Node.js), DynamoDB.
3. **Reproduce.** `curl -i -X POST "$API_URL/checkins" -H "Content-Type: application/json" -d '{"eventId":"e1","ticketId":"t1"}'` returns `HTTP/2 502` with `{"message": "Internal server error"}` and no `Access-Control-Allow-Origin` header. So the CORS error is a symptom: the browser hides the 502.
4. **Isolate.** `aws logs tail /aws/lambda/checkin-fn --since 30m` shows `TypeError: Cannot read properties of undefined (reading 'toUpperCase') at handler (src/checkin.js:18)`. `git log -p -3 -- src/checkin.js` shows the merge added `body.ticketType.toUpperCase()`.
5. **Root cause.** Why the CORS error? The 502 has no CORS headers. Why the 502? The Lambda threw. Why did it throw? `ticketType` was undefined. Why? The deployed frontend does not send `ticketType`, and the handler treats an optional field (the spec says it defaults to `GENERAL`) as required. Root cause: the handler does not apply the default for an optional field. Not caught because no test sent a check-in without `ticketType`.
6. **Fix.** One line in `src/checkin.js`: `const ticketType = (body.ticketType ?? "GENERAL").toUpperCase();`. Not changed: gateway error responses also lack CORS headers, which disguised this bug. That is logged as a separate follow-up, not added to this commit.
7. **Regression test.** `accepts a check-in without ticketType and defaults to GENERAL` failed before the fix and passes after. The existing `VIP` test still passes (preservation).
8. **Verify.** Tests green, deployed to the shared demo stage with the Reviewer watching, curl returns 201, the teammate checks in a fake attendee in the browser, and the logs are clean.
9. **Document.** Commit `fix(checkin): default missing ticketType to GENERAL`, with Symptom, Root cause, Fix, Test and `Refs: BUG-4`. A `docs/BUGS.md` entry with a follow-up: "@C (infra owner): add CORS headers to API Gateway DEFAULT_4XX/5XX responses in IaC".

Kiro turns used: 3.

## Exit criteria (definition of done)

- [ ] Every phase's exit criteria are met (or the stop rule was applied and the handoff note posted).
- [ ] The diff is minimal and on the causal path: no drive-by changes, widened permissions, swallowed errors or console-only config.
- [ ] A regression test went red to green, and the "Unchanged" behavior still passes.
- [ ] Any workaround is labelled `WORKAROUND(BUG-<n>)` and logged; the commit follows the template.
- [ ] The chat summary is 10 lines or fewer and lists follow-ups (with owners) and what teammates must do.

## Anti-patterns (do not do this)

- **Shotgun debugging:** several changes at once, then not knowing which one mattered.
- **Fixing the symptom:** adding CORS headers when the real problem is a 502, raising a Lambda timeout when the call never had network access, or `catch {}` and "return 200" so the error vanishes from the UI.
- **Permission inflation:** `"Action": "*"`, `"Resource": "*"`, a public bucket, or `AdministratorAccess` on a Lambda role "just for the demo".
- **Debugging the wrong environment:** another region, stage, branch, AWS profile or a teammate's Amplify sandbox.
- **A test that would have passed before the fix**, which proves nothing.
- **Two people on one bug** without telling each other, or **pushing on alone past the stop rule** while the demo clock runs.
- Drive-by refactors, console-only fixes, pasted logs or secrets, and regenerated files (see the operating rules and Phase 5).

## Related skills

- `architecture-selection` owns the stack, AWS services, region and the other core choices in `tech.md`. Hand off when a fix needs any of these to change.
- `quick-spec` owns new or changed behavior, API contracts and data models inside the chosen stack. Hand off when the "bug" is a missing feature, the expected behavior is undefined, or the fix changes a contract or key schema.
- `bug-fix` (this skill) owns defects in existing, merged behavior: reproduce, root cause, minimal fix, regression test, verify, document. A failing test inside an unfinished quick-spec task belongs to that task; use this skill there only when its owner is stuck.

## Reference files (load only when needed)

All live in `references/`, one level below this file, and are linked from the Phase 3 index. For an AWS bug, read `aws-triage.md` plus the single matching playbook (CORS is in `aws-api-gateway.md`); never load them all.
