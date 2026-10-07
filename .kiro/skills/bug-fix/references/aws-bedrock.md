# Amazon Bedrock triage

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

```bash
aws bedrock list-foundation-models --region <region> --query 'modelSummaries[].modelId'
aws bedrock list-inference-profiles --region <region> --query 'inferenceProfileSummaries[].inferenceProfileId'
```

A single small Converse call confirms access end to end; it is billed like any other model call:

```bash
aws bedrock-runtime converse --region <region> --model-id <model-or-inference-profile-id> \
  --messages '[{"role":"user","content":[{"text":"Reply with OK"}]}]' \
  --inference-config '{"maxTokens":10}'
```

| Error or symptom | Cause | Fix |
|---|---|---|
| `AccessDeniedException: You don't have access to the model with the specified model ID.` | Model access is not enabled for this account and region, a provider agreement (use-case form or Marketplace subscription) is incomplete, or an organization policy blocks Bedrock | Open the Bedrock console in the same region and follow its current model access or model catalog flow; this process has changed over time. On an event-provided account, ask the organizers |
| `AccessDeniedException ... is not authorized to perform: bedrock:InvokeModel` | IAM | Allow `bedrock:InvokeModel` (also used by Converse) or `bedrock:InvokeModelWithResponseStream` (streaming) on the model ARN. With an inference profile, allow the profile ARN and the foundation-model ARNs in each region it routes to |
| `Invocation of model ID ... with on-demand throughput isn't supported. Retry your request with the ID or ARN of an inference profile` | The model must be called through an inference profile | Use an inference profile ID from `list-inference-profiles` (it starts with a geography prefix such as `apac.`, or with `global.`) instead of the bare model ID. Cross-region inference may process requests in any region the profile covers, worldwide for a `global.` profile; check the team's data-residency expectations |
| `The provided model identifier is invalid`, `ResourceNotFoundException` | A model ID typo, the wrong version suffix, a model not offered in this region, or a retired model | List the models in the region. Do not assume a model exists in the region in `tech.md` |
| `ValidationException: Malformed input request` | The InvokeModel body does not match that provider's schema | Prefer the Converse API, which uses one request shape across models |
| `Input is too long for requested model` | The prompt and context exceed the model's context window | Trim, summarize or chunk the input |
| `ThrottlingException`, `ServiceQuotaExceededException` | Per-model request or token quotas, which can be low on new accounts | Retry with exponential backoff and jitter, lower `maxTokens`, cache answers to repeated demo prompts, and check Service Quotas. Do not plan on a quota increase on demo day |
| `ModelTimeoutException`, Lambda timeout, API 504 | Generation takes longer than the Lambda timeout (raise it in IaC) or the API Gateway integration timeout (a Lambda change cannot fix this) | Shorter output, streaming, or an async pattern. The last two are architecture changes: hand off to `architecture-selection` |
| Unexpected cost | Retry loops or unbounded output | Log the `usage` token counts that Converse returns, set `maxTokens`, and cap retries |

Do not: hardcode model IDs in several files (keep one config value), log full prompts that contain personal data, or retry in a tight loop.
