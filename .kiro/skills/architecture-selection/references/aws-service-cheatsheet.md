# AWS Service Cheat Sheet (hackathon edition)

Read this file during architecture-selection when a service choice is unclear (Phase 2) or when you prepare the guardrails (Phase 6). It helps you get oriented. It does not set prices or limits.

- This sheet deliberately contains no prices and few numbers. Before committing, check the service's pricing page, the Free Tier page in the Billing console, and regional availability.
- AWS changed its Free Tier for new accounts in 2025 to a credit-based model, while older accounts keep the earlier offers. Check what your own account has.
- Events and student programs sometimes provide AWS credits. Ask the organisers.

**Cost shape legend:**

| Shape | What it means |
|---|---|
| per-request | You pay per use, so cost is near zero when idle. Good for demos. |
| per-hour | Billed while the resource exists or runs, even with no traffic. Delete it after the event. |
| per-GB | Storage or data transfer. Usually small at demo scale. |

## 1. Frontend hosting

| Service | Use it for | Gotchas | Cost shape |
|---|---|---|---|
| Amplify Hosting | Git-connected deploys of a SPA or SSR app (e.g. Next.js), with a preview per branch | Build settings live in `amplify.yml`. Environment variables are set per branch in the console. | per build minute + per-GB |
| S3 + CloudFront | Static SPA build output (Vite/React) | Keep the bucket private and use Origin Access Control. SPA deep links need the error response mapped to `index.html`. A custom-domain certificate for CloudFront must be in `us-east-1`. Invalidate the cache after a deploy. | per-GB + per-request |

## 2. Compute

| Service | Use it for | Gotchas | Cost shape |
|---|---|---|---|
| AWS Lambda | API handlers, background jobs, Bedrock calls, S3 event processing | 15-minute maximum run time. Set memory and timeout explicitly. Python native dependencies must match the Lambda architecture: build in a container (`sam build --use-container`) or pick pure-Python libraries. Pick arm64 or x86_64 once and keep it. | per-request + duration; check for an always-free allowance |
| ECS on Fargate | Containerised web apps without managing servers | Needs a VPC, subnets, security groups and usually a load balancer. Private subnets need a NAT gateway (per-hour) or VPC endpoints. Public subnets avoid NAT, but public IPv4 addresses are charged. | per-hour while tasks run, plus the load balancer |
| AWS App Runner | Simplest container or web-service hosting | Before choosing it, confirm it is still open to new accounts and available in your region | per-hour of active and provisioned capacity; check pricing |
| Amazon Lightsail | A traditional server app, fixed-price VPS, simple containers | Separate console, so a weaker "AWS-native" story | monthly plans; check pricing |
| Amazon EC2 | Full VMs | Avoid for a hackathon unless something specifically needs a VM: you take on patching, SSH keys, security groups and idle cost | per-hour |

## 3. APIs and real-time

| Service | Use it for | Gotchas | Cost shape |
|---|---|---|---|
| API Gateway HTTP API | Default JSON API in front of Lambda | Has a built-in JWT authorizer (works with Cognito) and CORS settings. The integration timeout is about 30 seconds, so long LLM calls need streaming or an async pattern. | per-request |
| API Gateway REST API | When you need API keys and usage plans, request validation, or other REST-API-only features | More configuration than an HTTP API | per-request |
| Lambda function URL | The simplest HTTPS endpoint for a single function; supports response streaming | Auth is either IAM or NONE. With NONE the endpoint is public, so add your own checks. Check streaming support for your runtime (native for Node.js). | Lambda cost only |
| AWS AppSync (GraphQL) | Real-time subscriptions; it is the backend of Amplify Data | GraphQL has a learning curve if you are not using Amplify | per-request + real-time connection time |
| API Gateway WebSocket API | Real-time without GraphQL | You manage connection IDs yourself (store them in DynamoDB) | per-message + connection time |

## 4. Data and files

| Service | Use it for | Gotchas | Cost shape |
|---|---|---|---|
| Amazon DynamoDB | The default database for serverless | List your access patterns first; choose keys to match them. Use on-demand capacity. Use Query by key, not Scan. One table per entity is fine at hackathon scale. | per-request (on-demand) + per-GB; check for an always-free allowance |
| Amazon RDS / Aurora (PostgreSQL, MySQL) | Relational data, joins, or a team that only knows SQL | Brings VPC networking. Lambda opening many connections needs RDS Proxy or the Aurora Data API. Instances bill hourly. Whether Aurora Serverless can pause to zero depends on version and configuration, so check the docs. | per-hour + storage |
| Amazon S3 | Uploads, images, documents, static assets, exports | Keep Block Public Access on. Browser uploads go through presigned URLs, which need a bucket CORS rule. Use S3 events to trigger Lambda processing. | per-GB + per-request |
| Vector store (for RAG) | Knowledge Bases or semantic search | Some options (e.g. OpenSearch Serverless) have a minimum capacity cost for as long as they exist. Compare the options the Bedrock console offers, check pricing, and delete after the event. | varies; can be per-hour |

## 5. Authentication

| Service | Use it for | Gotchas | Cost shape |
|---|---|---|---|
| Amazon Cognito user pools | Sign-up and sign-in; JWTs for API Gateway authorizers; managed login pages | Some settings, such as required attributes and sign-in identifiers, cannot be changed after creation, so decide them before the first deploy. The built-in email sender has a low daily quota: fine for a demo, so check the quotas. Pricing has tiers; check them. | per monthly active user; check the free allowance |
| Amplify Auth | Cognito wrapped by Amplify Gen 2 (`defineAuth`), plus a prebuilt Authenticator UI component | Inherits the Cognito rules above | as Cognito |
| Social login (Google etc.) | Only if the demo requires it | Needs OAuth app registration with the provider. Budget at least 30 minutes. | as Cognito |

## 6. AI and ML

| Service | Use it for | Gotchas | Cost shape |
|---|---|---|---|
| Amazon Bedrock | Foundation models (Anthropic, Amazon, Meta and others) behind one API. Use the Converse API (ConverseStream for streaming) for chat-style calls. | Model availability varies by region. Some models are reached through cross-region inference profiles, which can process requests in other regions of the same geography. Confirm model access in the Bedrock console for your region. Always set max tokens. Retry throttling errors with backoff. The IAM permissions needed are `bedrock:InvokeModel`, plus `bedrock:InvokeModelWithResponseStream` for streaming. | per input/output token, varying by model. Start with the smallest model that works. |
| Bedrock Knowledge Bases | Managed RAG over documents in S3 | Needs a vector store; see the cost note in section 4 | ingestion + queries + vector store |
| Bedrock Guardrails | Content filters and PII redaction; a good "responsible AI" story for judges | Adds latency, and a policy to tune | per text unit; check pricing |
| Bedrock agent features (Agents, AgentCore) | When tool-using agent behaviour is itself the demo | Many moving parts. Prefer one direct Converse call unless the agent is the point. | varies |
| Amazon Rekognition | Image labels, text in images, moderation, faces | Face features carry privacy duties: get consent and avoid storing faces | per image |
| Amazon Textract | OCR plus forms and tables from documents | Async APIs for multi-page PDFs | per page |
| Amazon Transcribe / Translate / Polly | Speech-to-text, translation, text-to-speech | Check the supported-language list for each service before promising Malay, Chinese or Sarawak languages (e.g. Iban). Test with real samples during the spike. | per second / per character |
| Amazon Comprehend | Sentiment, entities, PII detection | Language support varies; check it | per unit |

## 7. Messaging, events and workflows

| Service | Use it for | Gotchas |
|---|---|---|
| Amazon SQS | Decoupling slow work (e.g. AI processing after an upload) | Add a dead-letter queue. Make the Lambda consumer idempotent. |
| Amazon SNS | Fan-out notifications | SMS has country-specific registration rules. Avoid SMS in a demo unless it is required. |
| Amazon EventBridge (+ Scheduler) | Event routing and cron-style schedules | Keep event schemas simple |
| AWS Step Functions | Multi-step workflows with retries | Produces a visual workflow that judges can see. Choose Standard or Express according to duration and volume. |
| Amazon SES | Sending email | New accounts start in the SES sandbox and can send only to verified addresses until production access is granted. Verify the demo addresses, or skip email. |

## 8. Observability

- **CloudWatch Logs.** Lambda logs go here automatically. Set a retention period in IaC; the default is never expire.
- **CloudWatch alarms.** Add an alarm on Lambda errors and throttles for the demo stack.
- **AWS X-Ray.** Optional tracing. Useful when a request crosses several services.
- **Powertools for AWS Lambda** (Python, TypeScript and others). A library for structured logging, tracing, idempotency and validation. Cheap to add early.

## 9. Infrastructure as code and tooling

| Tool | Best for | Notes |
|---|---|---|
| Amplify Gen 2 | TypeScript full-stack (option B) | `npx ampx sandbox` gives each developer a personal cloud sandbox. It is built on CDK, and `amplify/backend.ts` can add other AWS resources. |
| AWS SAM | Lambda-centric apps (option A) | YAML template. `sam local` needs Docker. `sam sync --watch` iterates quickly. `sam deploy --guided` writes `samconfig.toml`. |
| AWS CDK | Code-defined infra (TypeScript or Python); options A and C | Grant helpers (e.g. `table.grantReadWriteData(fn)`) make least privilege easy. Run `cdk bootstrap` once per account and region. |
| Terraform | Only if the team already knows it | Three people need a shared state backend |
| Console clicking | A spike of at most 30 minutes | Recreate it in IaC before it becomes load-bearing, or teardown and teammate setup get painful |
| AWS CloudShell | A browser terminal with the AWS CLI, for when a laptop setup is broken | Not available in every region; check |
| GitHub Actions + OIDC | CI deploys without long-lived keys | Optional. Set up only if time allows. |

## 10. Security and cost tools

- **IAM Identity Center:** one sign-in per teammate, with short-lived CLI credentials (`aws configure sso`).
- **AWS Budgets:** email alerts at a low threshold. Templates include a zero-spend budget.
- **Cost Explorer:** shows cost by service. Cost by your own tags works only after those tags are activated as cost allocation tags in Billing.
- **Systems Manager Parameter Store:** config values and SecureString secrets. The standard tier is low-cost or free; check.
- **Secrets Manager:** managed secrets with rotation. Charged per secret per month plus API calls.
- **Resource Groups and Tag Editor:** find every resource tagged `project=<name>` before teardown.

## Things that cost money while idle (delete after the event)

- NAT gateways
- Load balancers (ALB/NLB)
- Running EC2 instances, Fargate tasks, and RDS/Aurora capacity that is not paused
- Public IPv4 addresses, including Elastic IPs
- OpenSearch domains and OpenSearch Serverless collections, including those created for Knowledge Bases
- EKS clusters (control plane)
- SageMaker endpoints and notebook instances
- Secrets Manager secrets (small, but monthly)
- Large S3 or CloudWatch Logs data with no retention or lifecycle rules

## Region check (Phase 6)

1. Pick the home region. Usual candidates for a team in Kuching:
   - `ap-southeast-1` (Singapore): broad service catalogue, close by.
   - `ap-southeast-5` (Asia Pacific (Malaysia)): data stays in Malaysia and latency is local. Newer regions can lack some services or models.
   - `us-east-1` (N. Virginia): often the widest catalogue and the first region for new models. It is far away, and data leaves the region.
2. For every chosen service, switch the console to the home region and confirm the service opens, or check the AWS services-by-region list.
3. Bedrock: in the home region, open the Bedrock console and confirm the exact model ID. Check whether it runs in-region or only through a cross-region inference profile.
4. Write any exception into `tech.md` under "Exceptions", with the reason.

## Teardown (after judging)

| Tool | Command |
|---|---|
| SAM | `sam delete --stack-name <stack>` |
| CDK | `npx cdk destroy --all` |
| Amplify Gen 2 sandbox | `npx ampx sandbox delete`. Delete branch deployments or the app in the Amplify console. |
| Terraform | `terraform destroy` |

Then check what IaC deliberately leaves behind. Retained S3 buckets and DynamoDB tables are common (CDK, for example, retains some stateful resources by default). Also check CloudWatch log groups, Cognito user pools, ECR images and Knowledge Base vector stores. Search Tag Editor for `project=<name>` to confirm nothing is left.
