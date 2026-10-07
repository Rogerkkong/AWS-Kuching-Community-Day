---
name: architecture-selection
description: Guides a small, time-boxed team through choosing the architecture, AWS services and frontend/backend stack for a new project or major component, then records the decision so Kiro follows it. Gathers constraints in one batched round (problem, demo, time left, skills, budget, data, region), proposes 2-3 candidates (serverless API Gateway + Lambda + DynamoDB, Amplify Gen 2 full-stack, containers on ECS Fargate, plus optional Amazon Bedrock for GenAI), scores them in a weighted decision matrix, and writes .kiro/steering/tech.md, .kiro/steering/structure.md and an ADR in docs/decisions/. Use when the user asks which AWS services or stack to use, or says "choose our architecture", "what should we build this with", "Lambda or containers", "should we use Amplify", "React or Next.js", "Node or Python backend", "add Bedrock or AI to the stack", "pick a region", "set up tech.md", "write an ADR", or starts a project with no tech.md yet. Not for writing feature specs (use quick-spec) or fixing bugs (use bug-fix).
metadata:
  version: "1.0"
---

# Architecture Selection

Choose a stack that a 3-person team can take to a working, demo-ready AWS deployment in the time they have. Then write the choice into always-on steering so every later Kiro session follows it.

## When to use

- A new project or repo, with no `.kiro/steering/tech.md` yet, or a placeholder or generated one.
- A major new component: adding GenAI, auth, file uploads, real-time updates, a mobile client or a second service.
- The current stack has hit a hard blocker: a service or model is unavailable in the region, a cost alarm fired, or a teammate left and their skills went with them.
- A hand-off from **quick-spec** (a feature needs a service, library or data store not in `tech.md`) or from **bug-fix** (a fix needs a new service or a change to a core choice, with the root cause already found). Do not send these back; use "Revisiting a decision" below.

Do not use it for:

- Designing a feature inside a stack that is already chosen. Hand off to **quick-spec**.
- Errors, failing deploys, AccessDenied or wrong behaviour. Hand off to **bug-fix**.
- Brainstorming the product idea. Ask only enough about the product to choose the architecture.

## Operating rules

1. **Three-turn target.** Turn 1: ask the batched questions. Turn 2: give the recommendation with the matrix. Turn 3: write the files. If the user already gave the answers, skip turn 1. The team is on Kiro Free (50 credits a month per account, no top-ups; chat, spec and hook runs all draw on them), so every extra round trip costs.
2. **Timebox.** Aim for 30-45 minutes of team time. If the team is still torn after the matrix, take the familiarity winner and move on.
3. **Never invent requirements.** Use only what the user said. Mark everything else `(assumed)` and list it where the user will see it.
4. **Prefer proven technology.** Prefer managed, serverless, well-documented services the team already knows. The team gets one "innovation token": at most one tool or service on the critical path that nobody on the team has used before.
5. **Record, don't just chat.** Chat is lost when the session ends; the ADR, `tech.md` and `structure.md` are not.
6. **Decide only.** Do not scaffold code, write infrastructure, or run commands that create or change AWS resources. The one exception is the read-only spike in Phase 4, and only when the user approves it.
7. **Stay accurate.** Do not quote prices, quotas, limits or regional availability from memory as facts. Write "check current pricing" or "verify in the console", and name the page or command to check.

**Credit savers to tell the team** (once, in turn 1 or 2):

- Answer all the questions in one reply; "defaults ok" is a valid answer.
- No need to run "Generate Steering Docs" first on an empty repo; this skill writes the steering files.
- Leave the model on Auto unless there is a reason not to; other models can use more credits per request (the model picker shows this).
- Start a fresh chat for `/quick-spec` afterwards, so the long architecture discussion is not carried into every later turn.

## Outputs

| File | Purpose | Create or update |
|---|---|---|
| `docs/decisions/NNNN-<slug>.md` | ADR: context, options, matrix, decision, diagram, guardrails | Always new. Supersede old ADRs; never rewrite them. |
| `.kiro/steering/tech.md` | Always-on stack rules for the agent | Edit sections in place if the file exists |
| `.kiro/steering/structure.md` | Folder layout, naming, ownership | Edit sections in place if the file exists |
| `.kiro/steering/product.md` | Only if missing: 3-6 lines of facts the user stated | Optional |

Steering files with no frontmatter (`inclusion: always`, the default) are included in every interaction. If an existing file has frontmatter, keep it. Because `tech.md` and `structure.md` are sent with every request, keep each to about 80 lines.

## Phase 0: Read the current state (cheap)

1. List `.kiro/steering/` and `docs/decisions/`. Read only those files. Do not scan the codebase.
2. If the team already used Kiro's "Generate Steering Docs", the three files exist with generated text. Treat them as drafts: keep correct facts, replace the stack sections.
3. If an accepted ADR already covers this scope, this is a revision. Note its number; the new ADR will supersede it.
4. Note facts already present, such as team skills in `product.md` or an existing region. Do not ask for them again.

## Phase 1: Gather constraints in ONE message

Send this once, removing any question that is already answered. Defaults in brackets let the user reply "defaults ok".

```text
To pick the stack I need a few facts. Answer in one reply; anything you skip uses the [default].

1. Problem and user: what does it do, and for whom? One sentence.  [required]
2. Demo: which 1-3 actions must work live in front of judges?      [the core flow from Q1]
3. Time: hours until code freeze, and hours each of the 3 of you can give?  [24 h to freeze, ~8 h each]
4. Skills: strongest language/framework per person; has anyone deployed to AWS before?
   [2x React/JavaScript, 1x Python; little AWS experience]
5. AWS account: one shared account, individual accounts, or event-provided? Credits or a hard budget?
   [one shared account; spend nothing beyond Free Tier or credits]
6. Must-haves: login, file/photo upload, real-time updates, GenAI/chat, maps, notifications, mobile app?
   [only what Q1-Q2 need]
7. Data: any personal data? Must data stay in Malaysia?             [emails only; no residency rule]
8. Event rules: required services, judging criteria, anything banned?  [none known]
```

If Q1 is missing and cannot be inferred, stop and ask for it alone. For every other gap, proceed with the defaults and label them `(assumed)`. If Q4 was skipped, say in the recommendation that the familiarity scores rest on assumed skills. Do not start a second round of questions unless an answer is blocking.

## Phase 2: Shortlist 2-3 candidates

Start from this catalogue. Adapt it; do not present all of it. Read [references/aws-service-cheatsheet.md](references/aws-service-cheatsheet.md) only when Q6 lists must-haves or a service choice is unclear, and only the section you need.

| ID | Candidate | Typical shape | Fits when |
|---|---|---|---|
| A | Serverless API | SPA on Amplify Hosting or S3 + CloudFront; API Gateway HTTP API + Lambda; DynamoDB; Cognito; IaC with AWS SAM or CDK | Mixed skills (Lambda runs Node.js or Python); clear REST endpoints; scale to zero |
| A-lite | Minimal serverless | Static frontend + one Lambda function URL + DynamoDB or S3 | Under ~8 hours left, or a single core action |
| B | Amplify Gen 2 full-stack | React/Next.js (or another supported frontend) + `amplify/` backend defined in TypeScript: Auth (Cognito), Data (AppSync + DynamoDB), Storage (S3), Functions (Lambda) | Team is comfortable in TypeScript; wants auth, CRUD and a sandbox per developer fast |
| C | Container | One containerised web app (FastAPI, Express, Next.js SSR) on ECS Fargate behind a load balancer; DynamoDB or RDS/Aurora; IaC with CDK | Team already has a containerised app or depends on a server framework; has credits for always-on cost |
| +G | GenAI layer (add-on, not a candidate) | Amazon Bedrock called from the backend (Converse API); Knowledge Bases only if RAG is essential | Any candidate whose demo needs generation, summarising, chat or extraction |

App Runner is a simpler container host. Before you shortlist it, confirm that it is still open to new accounts and available in the chosen region.

**Knock-outs and penalties.** Apply these before scoring, and list what each one removed.

- Nobody is comfortable in TypeScript: penalise B, because its backend definitions are TypeScript. Prefer A.
- Hard budget of zero and no credits: drop C. Load balancers and running tasks cost money while idle.
- Under ~8 hours left, or nobody has deployed to AWS: shortlist A-lite or B. Drop C.
- Work that runs longer than Lambda's 15-minute maximum (video processing, long batch jobs): Lambda alone is out for that part; add Step Functions, or a Fargate task for the long step.
- A required service or Bedrock model is not available in the chosen region: change the region, or change the service or model. Record which.
- Data must stay in Malaysia: use `ap-southeast-5` and check every service there first. Bedrock cross-region inference profiles can process requests in other regions, so confirm the model runs in-region, or send it no data covered by the rule.
- Event-provided account: these are often time-limited or restricted to certain regions and services. Check the restrictions before building, and plan how to redeploy if it expires before judging.
- Event rules require or ban a service: obey them, and record it in the ADR context.

**Stack picks inside each candidate.**

- **Frontend:** default to React + Vite as a static SPA (it hosts anywhere and works with every candidate). Choose Next.js only if the frontend owner already uses it; SSR needs Amplify Hosting or C, while a static export works anywhere. For A-lite, plain HTML/JS is fine. For "mobile app", build a responsive web app or PWA; a native app is only worth it if a teammate has already shipped one.
- **Backend language:** the language the backend owner is strongest in. Node.js (JS/TS) and Python are both first-class Lambda runtimes with Powertools libraries. Use one backend language, not two. B means TypeScript. Heavy Python libraries (pandas, ML) can exceed the Lambda package size limit; prefer a Lambda container image or a managed AI service.
- **Login UI:** in B, use the Amplify Authenticator component. In A, the Amplify JS library can also point at an existing Cognito user pool, which saves building login screens.

**Must-haves (Q6).** Map each must-have to a service with the "Quick picks by need" table at the top of the cheatsheet, and add only those services to the candidates.

**GenAI (+G).** One direct Converse call per feature (agents only if the agent is the demo). Smallest model that passes the spike, model ID read from config, max tokens set, route throttled. Answers that can outlast API Gateway's ~30-second integration timeout need streaming or an async job-and-poll pattern (cheatsheet sections 3 and 6).

For each surviving candidate, write a card of up to 5 lines: services, languages, IaC tool, what is new to the team, and the biggest risk.

## Phase 3: Score with a weighted matrix

Score each criterion from 1 to 5. The weighted value is weight x score. Each weight column sums to 100, so the maximum total is 500. Use the "continues after event" weights only if the user says the project will keep going.

| Criterion | Weight (hackathon) | Weight (continues after event) | 5 means | 1 means |
|---|---|---|---|---|
| Time to working demo | 30 | 15 | Hello-world deployed end to end within 1 h | More than a day of setup before the first feature |
| Team familiarity | 20 | 15 | Everyone has used every core piece | Nobody has used the core pieces |
| Cost / Free Tier fit | 15 | 15 | Scales to zero; idle cost about nil | Meaningful hourly cost while idle |
| Judging appeal | 15 | 5 | Clear AWS-native story, live demo, clean diagram | Hard to explain, or mostly non-AWS |
| Ops burden | 10 | 20 | Fully managed; few things to break | Servers, networking or patching to babysit |
| Scalability / path to production | 5 | 20 | Scales without redesign | Needs a rewrite to grow |
| Delivery risk | 5 | 10 | No unknowns, region verified | Several unverified pieces |

Present the scores as a table like the one in the worked example: one column per candidate, `score = weighted` cells, and a total row.

Scoring rules:

- Give a one-phrase reason for any score of 1 or 5.
- If the event publishes judging criteria, map the weights to them and say so.
- If the top two totals are within 25 points, treat it as a tie. Break it by team familiarity first, then by fewer AWS services.
- The user may change the weights. Recompute once; do not argue.

## Phase 4: Recommend and get approval (single message)

```text
Recommendation: <Option> (<score>/500). Runner-up: <Option> (<score>/500).
Why:
- <reason tied to the user's constraints>
- <reason>
- <reason>
Main risk: <risk>. Mitigation: <spike, fallback, or owner>.
Region: <code> (<why>). To verify: <services/models not yet confirmed there>.
Dropped: <option - knock-out rule>
Assumed: <bullets of (assumed) items>
<candidate cards>
<matrix table>
Reply "approve", or tell me what to change. On approval I will write the ADR, tech.md and structure.md in one pass.
```

If the riskiest unknown could sink the demo, propose a spike of at most 30 minutes, run by a teammate (or by Kiro if the user approves the commands). Mark the ADR `Proposed (pending spike)` until it passes; if it fails, switch to the runner-up. If the user says "just decide", treat that as approval and move to Phase 5.

For a Bedrock spike, copy the commands and pass/fail rules from the "Bedrock spike" section of the cheatsheet into the message.

## Phase 5: Record the decision (one pass, small diffs)

Now read [references/templates.md](references/templates.md) (ADR, diagrams, steering templates) and [references/repo-layouts.md](references/repo-layouts.md) (layouts, naming, ownership). Do not read them earlier.

1. **ADR.** Take the highest number in `docs/decisions/` and add one; the first ADR is `0001`. Make the slug kebab-case, five words or fewer, e.g. `0001-serverless-api-on-aws.md`. Use the ADR template and the diagram for the chosen option, edited to match. If this supersedes an older ADR, change only that ADR's Status line to `Superseded by NNNN`.
2. **tech.md.** If the file exists, replace or append only the template's sections and keep teammates' content. Otherwise create it from the template.
3. **structure.md.** Use the layout for the chosen option and the ownership table, with the teammates' real names if known. Keep the `## Ownership` heading: quick-spec reads it to assign task owners, and bug-fix to assign each bug's owner and reviewer.
4. **product.md.** Create it only if missing, with the facts the user stated: problem, users, demo flow. Nothing invented.
5. **Optional scoped steering.** If the infrastructure rules would push `tech.md` past about 80 lines, put them in `.kiro/steering/aws-infra.md` with `inclusion: fileMatch` (template section 6).

Finish the turn with a list of the files written and one line on what each contains. Do not paste the files back into chat.

## Phase 6: Guardrails checklist (give to the user)

Human tasks: present them as a checklist with an owner per line (default: the infra owner, who can start while Kiro writes the files). Do not perform them unless asked.

- [ ] **Region.** One region for everything, every service and model confirmed there (cheatsheet "Region check"). Usually `ap-southeast-1` (Singapore), or `ap-southeast-5` (Asia Pacific (Malaysia)) if data residency matters; newer regions can lack some services or models. Exceptions go in `tech.md`.
- [ ] **Root account.** MFA on; root not used for daily work.
- [ ] **People access.** Each teammate signs in as themselves (IAM Identity Center, or their own IAM user). No shared passwords. Short-lived credentials (`aws configure sso`) over long-lived access keys.
- [ ] **App permissions.** Each Lambda or task role is scoped to specific actions and resources (CDK grant helpers, SAM policy templates, or explicit ARNs). No wildcard actions, and never widen a policy to "*" to get past an error.
- [ ] **Secrets.** Add `.env*` to `.gitignore`. Keep secrets in Parameter Store, Secrets Manager or Amplify secrets. Never paste keys into Kiro chat, steering or specs.
- [ ] **Budget alert.** An AWS Budgets alert, emailed to all 3 teammates, at a low threshold (Budgets has a zero-spend template). Check your account's current Free Tier or credit terms in the Billing console.
- [ ] **Tags.** Default tag `project=<name>` on all IaC resources, so teardown can find everything.
- [ ] **Logs.** CloudWatch Logs retention set in IaC; by default, log groups never expire.
- [ ] **Public endpoints.** Auth on write endpoints. If the ADR skips login for the demo, the API is public to anyone with the URL whatever the stage is called: fake data only, throttling on the stage, and teardown after the event. CORS restricted to the frontend origin once known. Throttling on any route that calls Bedrock.
- [ ] **Demo fallback.** Seeded demo data and a short screen recording of the flow, in case of venue Wi-Fi, throttling or a broken deploy.
- [ ] **Teardown.** Command, date and owner recorded in `tech.md`. Delete anything with idle cost after judging.

## Phase 7: Hand off to quick-spec

End with a short ordered list of the first specs, and stop. Do not write the specs here.

1. **Walking skeleton:** deploy hello-world across every layer (frontend, API, data, and auth if needed) in the chosen region. Done means a URL a teammate can open.
2. **Core demo flow:** the 1-3 actions from Q2.
3. **GenAI feature** (if any): one prompt path with error handling and a fallback message.

Then say: start a new chat and run `/quick-spec` for item 1. The new `tech.md` and `structure.md` are always-on steering, so quick-spec picks them up without being told.

## Worked example (hypothetical, not this team's project)

Input: "~20 h left. Two of us know React/JS, one knows Python. Users upload a photo and get an AI description. Free Tier only, no personal data."

- Knock-outs: Free Tier only drops C (load balancer and tasks bill while idle). B is viable but penalised: TypeScript backend definitions are new to the Python member. 20 h is more than enough for A rather than A-lite.
- Candidates: A = React (Vite) on Amplify Hosting, HTTP API + Python Lambda, S3 upload by presigned URL, DynamoDB, Bedrock image-capable model, SAM. B = Amplify Gen 2 (Auth, Storage, Data, TypeScript function calling Bedrock).

| Criterion (weight) | A | B |
|---|---|---|
| Time to working demo (30) | 4 = 120 | 4 = 120 |
| Team familiarity (20) | 4 = 80 | 3 = 60 |
| Cost / Free Tier fit (15) | 5 = 75 (scales to zero) | 5 = 75 (scales to zero) |
| Judging appeal (15) | 4 = 60 | 4 = 60 |
| Ops burden (10) | 4 = 40 | 5 = 50 (one managed toolchain) |
| Scalability (5) | 5 = 25 (all serverless) | 4 = 20 |
| Delivery risk (5) | 4 = 20 | 3 = 15 |
| **Total (max 500)** | **420** | **400** |

A and B are within 25 points, so the tie-break applies; familiarity favours A. Decision: A, with login skipped (no personal data; demo user stated in the ADR). Bedrock tokens are billed even when the rest fits the Free Tier, so the ADR flags "small Bedrock spend or credits (assumed)". Spike: 20 minutes to confirm an image-capable Bedrock model answers in the chosen region. Files written: `docs/decisions/0001-serverless-photo-api.md`, `tech.md`, `structure.md`, `product.md`. Hand-off: new chat, `/quick-spec` walking skeleton.

## Exit criteria

- [ ] The ADR exists with Status, context (assumptions labelled), options (including knock-outs), matrix, decision, mermaid diagram, guardrails and revisit triggers.
- [ ] `tech.md` names the region, services, languages and versions, test runner, IaC tool, where CORS is set, sandbox/deploy/teardown commands and agent rules, in about 80 lines or fewer.
- [ ] `structure.md` has the layout, naming and an `## Ownership` table covering all 3 teammates.
- [ ] Every service and model has been checked in the region, or is flagged "to verify" with an owner.
- [ ] The user has the guardrail checklist (budget alert, IAM, secrets, demo fallback, teardown).
- [ ] The user approved, or said "just decide".
- [ ] The quick-spec hand-off list is given, with the walking skeleton first.

## Anti-patterns

- **Resume-driven architecture.** Microservices, Kubernetes/EKS, multi-region or event sourcing for a one-day demo.
- **Too much new technology.** More than one tool on the critical path that is new to the whole team.
- **Open-ended design prompts.** "Design the whole system" that produces long documents and burns credits.
- **Full rewrites.** Regenerating `tech.md` or `structure.md`, or rewriting an accepted ADR instead of superseding it.
- **Region last.** Choosing the region after the services, then finding a service or model is missing.
- **RAG by reflex.** A vector store and Knowledge Base when a few documents in the prompt would do.
- **Wildcard IAM as a fix.** `"Action": "*"` or `"Resource": "*"` added to make an AccessDenied go away.
- **Idle-cost surprises.** NAT gateways, load balancers, databases or vector stores left running after the event.
- **Secrets in the wrong place.** Credentials in code, `.env` committed, or keys in chat or steering.

## Revisiting a decision

Re-run the full flow only for a real reversal, such as a late knock-out, a failed spike, a cost alarm, a change in team skills, or a bug-fix hand-off that changes a core choice (region, compute, database, auth, IaC tool, backend language). Write a new ADR that supersedes the old one and update `tech.md` in place.

For a small addition that fits the decision (a library, or a supporting service such as SES or SQS that a quick-spec feature needs), take the short path in one turn: check the cheatsheet's quick picks, region and cost shape, edit `tech.md`, add a line to the current ADR's Follow-ups, and tell the teammate to return to `/quick-spec` or `/bug-fix`.

## Related skills

- `quick-spec` owns feature specs inside the chosen stack (`.kiro/specs/<feature-name>/`), including the walking skeleton. It reads `tech.md` and the `## Ownership` table, and hands back here when a feature needs something not in `tech.md`.
- `bug-fix` owns defects in existing behavior. It hands back here when a fix needs a new service or a core-choice change, and may propose one-line rule additions to `tech.md` or `structure.md`.

## Reference files (load only when a phase says so)

- [references/aws-service-cheatsheet.md](references/aws-service-cheatsheet.md): quick picks by need, per-service gotchas and cost shape, idle-cost list, Bedrock spike, region check, teardown. Phases 2, 4 and 6.
- [references/templates.md](references/templates.md): ADR, mermaid diagrams for A/B/C, and steering templates. Phase 5.
- [references/repo-layouts.md](references/repo-layouts.md): folder layouts, naming and ownership per option. Phase 5.
