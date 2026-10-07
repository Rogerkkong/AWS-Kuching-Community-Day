# Lambda triage

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

Read the REPORT line for the failing request first:

```text
REPORT RequestId: <id> Duration: <ms> Billed Duration: <ms> Memory Size: <MB> Max Memory Used: <MB> Init Duration: <ms>
```

`Init Duration` appears only on cold starts. `Max Memory Used` close to `Memory Size` points to memory pressure.

```bash
aws logs tail /aws/lambda/<fn> --since 30m
aws logs tail /aws/lambda/<fn> --since 30m --filter-pattern '"<request-id>"'
# Prints env var NAMES only, never values
aws lambda get-function-configuration --function-name <fn> \
  --query '{Runtime:Runtime,Handler:Handler,Timeout:Timeout,Memory:MemorySize,EnvKeys:keys(Environment.Variables || `{}`)}'
```

| Symptom | Likely cause | Fix |
|---|---|---|
| `Task timed out after N seconds` | The timeout is too low for real work (the default is 3 seconds), or the function waits on something that never answers: a Lambda in a VPC with no NAT gateway or VPC endpoint, the wrong endpoint or region, a promise that never resolves, a slow Bedrock call | Find what it waits on first (log timings around each external call). Raise the timeout in IaC only when the work is legitimately slow. Behind API Gateway, the API's integration timeout still applies |
| `Runtime exited with error: signal: killed`, or memory used near the limit | Out of memory | Raise memory in IaC (this also raises CPU). Stream large files instead of loading them whole |
| `Runtime.ImportModuleError` (`Cannot find module`, `No module named`) | A dependency was not bundled or packaged, a path is wrong, or a native module was built for the wrong OS or architecture | Fix the bundling or packaging config. Build for the function's architecture (x86_64 or arm64) |
| `Runtime.HandlerNotFound` | The handler setting does not match `<file>.<export>` | Fix the handler string in IaC |
| `Cannot use import statement outside a module` (Node) | ESM syntax in a CommonJS package | Use `.mjs`, set `"type": "module"`, or bundle to CommonJS, whichever `tech.md` implies |
| Works locally, `undefined` config when deployed | An env var is missing from the deployed function, or was set in the console but not in IaC | Add it in IaC. Read env vars once at init and fail fast with a clear message when one is missing |
| A write sometimes does not happen (Node) | A promise was not awaited, so the handler returned first | `await` every AWS SDK call |
| First request is slow (high `Init Duration`) | Cold start: heavy imports, a large bundle, SDK clients created per request | Create SDK clients outside the handler, trim the bundle, and call the endpoint once before the demo to warm it. Provisioned concurrency costs money; check pricing first |
| The same event is processed twice | Async invocations and event sources retry on error, and many event sources deliver at least once even without an error | Make the handler idempotent (DynamoDB condition expression or an idempotency key) |
| `Rate exceeded`, `TooManyRequestsException`, throttles metric rising | The concurrency limit was reached. New or sandbox accounts can have a much lower quota than the documented default | Check current quotas in Service Quotas. Reduce fan-out. Do not count on a quota increase arriving on demo day |
| Invocation count explodes | A recursive loop, such as an S3-triggered function writing back to the same bucket and prefix | Stop it first: set the function's reserved concurrency to 0 (ask the user; it is a write). Then write output to a separate prefix or bucket. Lambda detects some loops, but do not rely on it |

Do not: raise the timeout to the maximum to "fix" a hang, log whole events that contain tokens or personal data, or edit code in the Lambda console when IaC will overwrite it.
