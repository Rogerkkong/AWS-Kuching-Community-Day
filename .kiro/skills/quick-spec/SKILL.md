---
name: quick-spec
description: Writes a lightweight, credit-efficient Kiro spec for a small or medium feature (about half a day of work for a 3-person team) in .kiro/specs/<feature-name>/. It produces requirements.md with user stories and numbered EARS acceptance criteria, a compact design.md (components, data model, API contract, error handling, testing) and tasks.md with Kiro checkboxes, owner tags, parallel work streams and requirement trace lines. Use when someone says 'quick spec', 'spec this', 'plan this feature', 'mini spec', 'write requirements for', 'break this into tasks', 'split this between the three of us', 'who does what', or wants to plan a hackathon feature on the AWS services already in tech.md (Lambda, API Gateway, DynamoDB, S3, Cognito, Amplify, Bedrock) without running the full Kiro spec flow. It escalates large features to a full spec, sends stack and AWS service choices to architecture-selection, and sends defects to bug-fix.
metadata:
  version: "1.0"
---

# Quick Spec

This skill writes a small spec in Kiro's native format (`requirements.md`, `design.md`, `tasks.md` in `.kiro/specs/<feature-name>/`) in one clarification round and one writing turn. It also splits the work so three people can build in parallel without merge conflicts. The layout copies Kiro's own generated specs, so Kiro should list the spec in the Specs section and offer "Start task" in `tasks.md`; this is untested for hand-written folders, so Phase 8 gives a fallback.

The skill is tuned for this team:

- Three students on a time-boxed delivery (AWS Community Day, hackathon style). Whatever can be demoed beats whatever is complete.
- An AWS-native stack. The chosen services, languages and folder layout live in `.kiro/steering/tech.md` and `.kiro/steering/structure.md`, which the `architecture-selection` skill owns.
- The Kiro Free plan: 50 credits a month per account, no top-ups. Prompts, spec refinements, task runs and agent hooks all draw on them, and a task run usually costs more than a simple prompt. Wasted turns are the main thing to avoid.

Kiro's built-in Spec flow and Quick Plan mode also produce these three files. If the teammate explicitly asks for one of them, let them use it, then offer Phase 7 below (the three-person split) on the `tasks.md` it generates.

## Phase 0. Ground rules (apply to every phase)

1. Write no application code. The skill outputs three spec files and a summary of 12 lines or fewer in chat.
2. Stay within the turn budget: one clarification turn (or none), one writing turn and at most one revision turn. If more seem necessary, the feature is too big or too vague; see Phase 1.
3. Write all three files in a single turn. In Supervised mode the teammate can then review and accept them together.
4. On feedback, edit only the lines affected. Never regenerate a whole file to change one requirement or task.
5. Never pick technology. Use what `tech.md` and `structure.md` say. If the feature needs a service, library or data store that is not recorded there, stop and hand off (Phase 1).
6. Do not invent facts. Leave AWS quotas, prices, latency numbers and region codes out of the spec unless they are already in steering or the teammate gave them. Write "check current pricing" or "check service quotas" instead.
7. Keep each file short. Aim for `requirements.md` of about 80 lines or fewer, `design.md` of about 120 or fewer and `tasks.md` of about 100 or fewer.
8. Use fake data only, in examples, seed scripts and mocks. Never copy real attendee names, emails, phone numbers or IC numbers into a spec.

## Phase 1. Route the request (sizing gate)

Input: the teammate's request, including any text typed after `/quick-spec`.
Output: one route decision. Do not write any files in this phase.

| Signal | Route |
|---|---|
| 30 minutes or less, one or two files, obvious behavior | **No spec.** Suggest doing it directly in chat. |
| Existing behavior is wrong: an error, a stack trace, "it used to work" | **Hand off to `bug-fix`.** Exception: `bug-fix` already sent it here because the fix changes an API contract, key schema or index, or the expected behavior is undefined. That is a quick spec; do not send it back, and name `BUG-<n>` in the Introduction. |
| Stack not decided: needs a service, framework or data store not in an existing `tech.md`, or a choice between options (DynamoDB vs RDS, REST vs WebSocket). If `tech.md` is missing, see Phase 2 | **Hand off to `architecture-selection`**, then return here. |
| 1 to 5 requirements, 12 leaf tasks or fewer, a critical path of about half a day (4 to 5 hours) with three people working in parallel, at most one new table, bucket or route group, one user role | **Quick spec. Continue.** |
| Between half a day and a day of critical path | **Split** into two quick specs that each demo on their own. |
| More than 5 requirements or 12 leaf tasks, more than a day of critical path, several roles, payments, sensitive personal data, or a cross-cutting refactor | **Escalate to the full Kiro spec flow** (Specs, +, Feature), or split into smaller quick specs. |

When you are unsure, prefer splitting into smaller quick specs over escalating. Small specs ship; big ones stall.

The **walking skeleton** that `architecture-selection` hands off first (hello-world through every layer, deployed) is a normal quick spec. Requirement 1 is "a teammate can open the deployed URL and see data from the API"; the contract in task 1.1 is a single health or hello route.

Exit criteria: you have chosen one route and stated it in one sentence. If the route is not "Quick spec", tell the teammate which skill or flow to use and stop.

## Phase 2. Gather context cheaply

Read only the following, and skip silently any that do not exist:

1. `.kiro/steering/tech.md`, `.kiro/steering/structure.md` and `.kiro/steering/product.md`. Steering without frontmatter is `inclusion: always`, so these are normally already in your context; do not open them again. Open one only if its content is missing from context (for example it uses `inclusion: manual` or `fileMatch`).
2. The folder names under `.kiro/specs/`, without opening them, to avoid a name collision and spot related specs. Open a related spec's `design.md` only if this feature extends it.
3. The entry file of an existing module the request names explicitly (for example "add export to the dashboard page"). Do not scan the codebase.

If `tech.md` is missing and no stack was stated, do not stall. Ask for the stack in one line among the Phase 3 questions (for example "React + API Gateway + Lambda (Node.js) + DynamoDB"), record the answer as an assumption in `design.md`, and recommend `/architecture-selection` afterwards.

For owner tags, use the `## Ownership` table in `structure.md` (written by `architecture-selection`) when it exists. Its Owner names become the tags (`@Mei`), its three areas become the FE, BE and INFRA streams, and each task goes to the owner whose `Covers` column contains the task's files. Otherwise use `@A`, `@B` and `@C`, with the default streams in Phase 7.

Exit criteria: you know the stack, the folder layout (or an assumed one) and the owner tags.

## Phase 3. Clarify once, or assume

1. Write down the answers the request already gives. Do not ask about them again.
2. From the question bank below, choose at most 5 questions whose answers would change the requirements or the task split. Skip any whose default is clearly fine.
3. Send all of the questions in one message, each with a default answer, so the teammate can reply "ok" or change just one or two.
4. If the teammate said "just assume", "go", or "no questions", or there is nothing material left to ask, skip asking. List the defaults as assumptions (`A1`, `A2`, and so on) in `requirements.md` instead.

Question bank (pick the ones that matter):

- **Actor:** attendee, staff, judge or admin? Only one role?
- **Trigger:** a page, a button, a scan, an upload, a schedule or an AWS event?
- **Demo moment:** what exactly must work live? (This becomes Requirement 1.)
- **Data:** what is stored, for how long, and is any of it personal data?
- **Failure that matters:** bad input, no network, a duplicate action or AWS throttling?
- **Out of scope:** login, admin UI, emails, analytics?
- **Connectivity:** venue Wi-Fi or mobile data? Is retry or offline behavior needed?
- **Deadline:** hours until it must work, and are all three teammates available?
- **Existing pieces:** a table, route, auth setup or page it must reuse?

Message template (copy, fill and trim):

```text
Quick spec for "<feature>". I'll write the 3 files after one answer from you.
Reply "ok" to accept all defaults, or change only what's wrong:
1. <question>? Default: <default>
2. <question>? Default: <default>
3. <question>? Default: <default>
Out of scope unless you say otherwise: <x>, <y>.
```

Exit criteria: every item in the question bank that matters is either answered or recorded as an assumption. Do not start a second round of questions.

## Phase 4. Name the spec folder

- Use kebab-case with 2 to 4 words, describing the user-visible capability: `attendee-checkin`, `session-feedback-form`, `photo-upload`, `ai-session-summary`.
- Use no dates, no ticket numbers and no words like "quick", "v2" or "spec".
- If the name already exists under `.kiro/specs/`, extend that spec (edit it) or choose a more specific name. Never overwrite another spec.
- Create only the three Markdown files. Do not hand-write Kiro's hidden `.config.kiro` file or invent a spec ID; Kiro manages those.

## Phase 5. Write requirements.md

Before writing, read [references/templates.md](references/templates.md). It holds the copy-paste skeletons for all three files, in Kiro's native layout, and the AWS design checklist. Fill in its requirements section:

- `## Introduction`: 3 to 5 lines on what is being built, for whom, and what success looks like at the demo.
- `## Glossary`: `- **Snake_Case_Name**: definition` for each actor and component. Use these names as the subject of every criterion (`Checkin_Api`, not "THE SYSTEM").
- `## Requirements`: 1 to 5 requirements ordered by demo value; Requirement 1 is the demo moment. Each has `### Requirement N: <Title>`, a `**User Story:** As a <role>, I want <capability>, so that <benefit>.` and `#### Acceptance Criteria` with 2 to 6 numbered EARS statements.
- `## Assumptions` (A1, A2, ...) and `## Out of Scope`: short bullets.

EARS patterns:

| Pattern | Form | Use for |
|---|---|---|
| Ubiquitous | `THE <Component> SHALL <response>.` | Rules that always hold |
| Event | `WHEN <trigger>, THE <Component> SHALL <response>.` | User actions, API calls, AWS events |
| State | `WHILE <state>, THE <Component> SHALL <response>.` | Modes such as loading, offline or signed-out |
| Unwanted | `IF <bad condition>, THEN THE <Component> SHALL <response>.` | Invalid input, duplicates, network and AWS failures |
| Optional | `WHERE <option is enabled>, THE <Component> SHALL <response>.` | Feature flags, stretch behavior |

Rules for acceptance criteria:

- Each criterion must have an observable outcome: UI text or state, an HTTP status and body field, a stored attribute, or an emitted event. If nobody could check it in two minutes, rewrite it.
- Describe one behavior per criterion: one SHALL, plus at most one `SHALL NOT` guard for a prohibition, for example "SHALL NOT overwrite the original check-in time".
- Avoid vague words such as fast, simple, user-friendly, robust, secure or scalable. Replace them with something checkable or delete them.
- Every requirement that touches the network or AWS needs at least one `IF ..., THEN` criterion.
- Criteria are referenced as `<requirement>.<criterion>`; `2.3` means Requirement 2, criterion 3. Once tasks reference them, never renumber. Add new criteria at the end instead.
- Put stretch goals in a separate, last requirement, so their tasks can be marked optional.

Exit criteria: between 1 and 5 requirements and between 4 and 20 criteria in total, every criterion in EARS form with a Glossary subject, and the assumptions listed.

## Phase 6. Write design.md (compact)

Fill in the design section of the templates file, and drop any section that would say nothing:

- `## Overview`: 3 to 6 lines, naming the steering decisions it relies on.
- `## Architecture`: one Mermaid flowchart or ASCII diagram of 15 lines or fewer, plus 2 to 6 `### Key Design Decisions`, each with a one-line reason.
- `## Components and Interfaces`: a table of Component, Responsibility, Location (from `structure.md`) and Stream.
- `## Data Models`: key schema, attributes, the access patterns served, and fake example records.
- `## API Contract`: method, path, request, responses by status code with example JSON, and auth. "None" is allowed for a demo, but say that the URL is then public, so the route holds fake data only.
- `## Correctness Properties` (only for pure logic worth property testing, such as "for any ticket, a second check-in never changes `checkedInAt`"; otherwise drop it): `### Property N`, a "*For any* ..." sentence and `**Validates: Requirements x.y**`.
- `## Error Handling`: Scenario, Detection, Response to user and Criterion, one row per `IF ..., THEN` criterion.
- `## AWS Notes`: one line per item of the AWS design checklist in the templates file (IAM, secrets, Lambda, CORS and auth, DynamoDB, S3, Bedrock, region, cost, personal data). Anything not in `tech.md` means handing off to `architecture-selection`.
- `## Testing Strategy`: the one or two required tests that protect the core rule; the rest are optional.

Exit criteria: every component has an owner stream and a path, every route has request and response examples, and every `IF ..., THEN` criterion appears in Error Handling.

## Phase 7. Write tasks.md (three-person split)

Use the tasks section of [references/templates.md](references/templates.md). Keep to the task syntax Kiro itself generates, so that Kiro can show and update task status:

```markdown
- [ ] 4. Backend stream
  - [ ] 4.1 Implement POST /checkins handler with conditional write
    - Owner: @B | Stream: BE | Est: 1.5h | Depends on: 1.1
    - Files: backend/src/checkin/postCheckin.ts, backend/src/checkin/repo.ts
    - Done when: unit test for 200/404/409 mapping passes
    - _Requirements: 1.1, 1.3, 1.4_
  - [ ]* 4.3 Extra unit tests for edge cases
    - Owner: @B | Stream: BE | Est: 45m | Depends on: 4.1
    - _Requirements: 1.3_
```

The syntax works like this:

- `- [ ]` marks a task not started, `- [-]` in progress and `- [x]` done. A `*` after the box (`- [ ]*`) marks an optional task. Put `*` on sub-tasks only; Kiro's own output never stars a top-level task.
- Top-level tasks are numbered `1.`, `2.`, and so on; sub-tasks are `1.1`, `1.2`, and so on, indented two spaces. Detail bullets are indented four spaces.
- The last detail bullet is the trace line: `_Requirements: 1.1, 2.3_`.
- A checkpoint is a top-level task named `Checkpoint - <name>`, whose body reads "Ensure all tests pass, ask the user if questions arise." plus what to demo.
- The file opens with `# Implementation Plan: <Feature Title>` and `## Overview` (including the stream table), then `## Tasks`, and ends with `## Notes`.

Splitting rules for three people:

1. **Contract first.** Task 1 is the shared contract: request and response types, example payloads, mocks and environment variable names. It has one owner and takes 45 minutes or less, followed by Checkpoint 2, a 10-minute review by all three. The frontend then builds against mocks while the backend and infrastructure are built.
2. **Three streams, one owner each.** Follow the Ownership table in `structure.md` if there is one. Otherwise @A owns FE (pages, components, client state), @B owns BE (Lambda handlers, business logic, unit tests) and @C owns INFRA/QA (infrastructure as code, tables, buckets, IAM, deployment, seed data, integration test, demo script). If any stream holds more than about 40% of the estimate, move tests, seed data or demo-script tasks to the lightest one.
3. **Leaf task size.** A leaf task takes 30 minutes to 2 hours of human time, fits one Kiro "Start task" run, touches about 5 files or fewer and has one "Done when" check. Split anything bigger by layer or by acceptance criterion, never into "part 1" and "part 2".
4. **Disjoint files.** Every leaf task lists `Files:`, and no two parallel tasks edit the same file. Give each hot file (package manifests and lockfiles, the stack entry, the route table, the app router, shared types) to one owner, or touch it only at integration.
5. **Explicit dependencies.** Write `Depends on:` with task numbers. Depend on the contract or on earlier tasks in the same stream. Cross-stream dependencies happen only at checkpoints.
6. **Demo path first.** In each stream, order tasks so that the demo moment (Requirement 1) works end to end first. Stretch tasks go last in their own stream, are marked `*` and depend on the integration checkpoint.
7. **Checkpoints.** Use three: after the contract, at integration (switch from mocks to the deployed API and run the demo path) and a final checkpoint.
8. **Traceability.** Every leaf task has a trace line, and every acceptance criterion appears in at least one non-optional task. Keep at least one required test for the core rule; other tests may be optional.
9. **Cap and time box.** Use 12 or fewer leaf tasks, not counting checkpoints; needing more means returning to Phase 1. If the critical path is longer than the time left, cut in this order: `*` tasks, the stretch requirement, then the lowest requirement. Keep the contract, the required core-rule test and the integration checkpoint.
10. **Branches.** Follow the branch convention in `structure.md`; otherwise use one branch per stream, `feature/<feature-name>-<stream>`. Merge the contract first and keep pull requests small enough to review in 10 minutes.
11. **Shared spec files.** Everyone's Kiro ticks boxes in the same `tasks.md`; each person ticks only their own tasks, so the edits sit on different lines and usually merge cleanly (in a conflict, keep the `[x]`). Requirement and design text is edited by one person and merged before the others pull.
12. **Credits.** Each owner starts their own tasks in their own Kiro, which spreads spending over three accounts. Mechanical tasks (seed data, demo script, a README line) are cheaper by hand or with one short chat prompt.

In `## Notes`, always include these lines (the first three are the ones Kiro's own specs use):

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation; cross-stream dependencies happen only at checkpoints.
- Start tasks one at a time in order of priority; on the Free plan avoid "Run all tasks" unless enough credits remain.
- A teammate may implement a task by hand and tick its box; that uses no credits.
- The branch names and the merge order.

Exit criteria: 12 or fewer leaf tasks, each with an owner, an estimate, files, a "Done when" check and a trace line; no parallel file overlap; the streams roughly balanced; and three checkpoints.

## Phase 8. Self-check, then hand back

Run this checklist silently and fix any failures before replying:

- [ ] The folder name is kebab-case and unique, and the file lengths fit Phase 0, rule 7.
- [ ] Every criterion is in EARS form, has a Glossary subject, is observable and is traced by a non-optional task.
- [ ] Every `IF ..., THEN` criterion has a row in Error Handling.
- [ ] No service, library or region appears that is not in `tech.md` or the stated assumptions.
- [ ] Each leaf task is 2 hours or less with an owner, files and dependencies; no parallel tasks share a file; no stream holds more than about 40% of the total estimate; and the critical path fits the deadline.
- [ ] No real personal data, secrets or account IDs appear anywhere. Any route without auth stores fake data only and is listed for teardown.

Reply in chat with this summary of 12 lines or fewer, and nothing longer:

```text
Quick spec ready: .kiro/specs/<feature-name>/
- <N> requirements, <M> criteria, <T> tasks (<K> optional), 3 checkpoints
- Assumptions: A1 <...>; A2 <...>  (reply to change; I'll edit only those lines)
- Streams: @A FE <h>h | @B BE <h>h | @C INFRA/QA <h>h  -> critical path about <h>h
- Start: task 1.1 (<owner>), then each owner starts their stream after Checkpoint 2
- In Kiro: Specs section -> <feature-name> -> tasks.md -> Start task on your next task
```

If the new spec does not appear in the Specs section, open `tasks.md` from the file explorer. If "Start task" still does not appear, tell the teammate to run a task from chat instead ("Implement task 3.1 in .kiro/specs/<feature-name>/tasks.md") and tick its box when done. Do not fabricate `.config.kiro` or other Kiro metadata files.

## Definition of done

A **task** is done when:

- [ ] Its code is committed on the stream branch (Conventional Commits, e.g. `feat(checkin): ...`, as in `structure.md`) and builds or deploys without errors.
- [ ] Its "Done when" check (a test, a curl request or a click-through) and any required tests for its criteria pass.
- [ ] No secrets, account IDs or real personal data are committed.
- [ ] Its box is `[x]` (Kiro ticks it after a task run; tick it yourself for work done by hand).

The **feature** is done when:

- [ ] All non-optional tasks are `[x]` and the final checkpoint has passed.
- [ ] The demo path works on the deployed environment, or the team has explicitly decided to demo locally.
- [ ] At least one `IF ..., THEN` path has been demonstrated or tested.
- [ ] The AWS resources the feature created are named or tagged according to `tech.md` and listed for clean-up after the event.
- [ ] The spec matches what was built: changed criteria are edited in place, and dropped work is listed under `## Notes` as `Deferred: <task> (<reason>)`.
- [ ] The README or demo notes say in 1 to 3 lines how to run or show the feature.

## Changing a quick spec during the build

- Edit the affected lines only. Add new criteria and tasks at the end of their list and never renumber.
- If a change adds more than 2 requirements or more than 4 tasks, run Phase 1 again. The feature may have outgrown a quick spec.
- When scope is cut, remove the task, add a `Deferred:` line in `## Notes`, and remove its criteria or move them to the stretch requirement.
- A bug found while building an unfinished task is part of that task. A defect in finished, merged behavior goes to `bug-fix`.

## Worked mini-example (condensed)

The full three files are in [references/example-attendee-checkin.md](references/example-attendee-checkin.md). Read that file when you need a complete model answer, or when a teammate asks "show me an example".

Request: `/quick-spec staff scan attendee QR codes at the door to check them in, show a live count`

The route is quick spec: one role, one table, two routes, about half a day, with React, API Gateway, Lambda and DynamoDB assumed in `tech.md`. The one clarification message asks whether the QR code holds only an opaque ticket ID, whether staff login is out of scope (so the API is public and holds fake data only), and whether manual entry is needed if the camera fails. The defaults are yes, yes and yes, and the teammate replies "ok".

Requirement 1 ("Check in an attendee by scanning a QR code") gets 6 criteria. A model criterion:

```markdown
4. IF the attendee is already checked in, THEN THE Checkin_Api SHALL return HTTP 409 with the original checkedInAt and SHALL NOT overwrite it.
```

Phase 7, the split:

```text
1.1 Contract + mocks ............ @B 45m
2.  Checkpoint - contract agreed  (all, 10m)
3.x FE: scanner page, result states, live count ......... @A ~3h
    3.4* stretch: recent check-ins on this device, after 6 ... @A 45m
4.x BE: POST /checkins (transaction with conditional write), GET count ... @B ~2h
5.x INFRA/QA: table + routes + IAM, seed fake attendees + printable QRs, demo script,
    optional property tests ............................ @C ~2.75h
6.  Checkpoint - integration (FE switches from mocks to the deployed API, run demo path)
7.  Checkpoint - final
```

## Anti-patterns (do not do this)

- Asking questions over several turns, or asking about what the request already says.
- Regenerating whole files after a one-line change, or renumbering criteria after tasks reference them.
- Choosing a new AWS service, database or framework in `design.md` instead of handing off to `architecture-selection`, or using a quick spec for a bug.
- Vague criteria ("THE system SHALL be fast and user-friendly"), requirements with no tasks, or tests that trace to no requirement.
- Tasks like "Build backend" or "Testing", "Part 1"/"Part 2" splits, or two people editing the route table, `package.json` or the IaC stack entry in parallel.
- An architecture essay, or a sequence diagram for every flow.
- Hand-writing `.config.kiro`, or starring a top-level task.
- Making every test mandatory on the Free plan, or having no required test for the core rule.
- "Run all tasks" on the last few credits, re-reading steering already in context, or scanning the codebase "for context".
- Treating a stage name ("dev", "demo") as protection. An API without auth is public to anyone with the URL.

## Related skills

- `architecture-selection` owns the stack and AWS service choices and records them in `.kiro/steering/tech.md`, `.kiro/steering/structure.md` and `docs/decisions/`. Hand off whenever the feature needs something not recorded there; a small addition comes back in one turn through its short path, then continue here.
- `bug-fix` owns reproducing, finding the root cause of, fixing and regression-testing defects in existing behavior. Hand off whenever the request describes something that is broken rather than something new. `bug-fix` hands back here when a fix needs a contract, key-schema or index change, or the correct behavior was never specified.
- The full Kiro spec flow (Specs, then +, then Feature) is for features beyond the Phase 1 limits.
