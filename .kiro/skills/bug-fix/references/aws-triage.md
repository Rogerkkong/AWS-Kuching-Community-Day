# AWS triage: start here

Part of the `bug-fix` skill. Read this before any service playbook. Then open only the one playbook that matches the error (the index is in `SKILL.md`, Phase 3): `aws-lambda.md`, `aws-api-gateway.md`, `aws-dynamodb.md`, `aws-iam.md`, `aws-s3.md`, `aws-amplify-cognito.md`, `aws-bedrock.md` or `aws-deployments.md`.

Run read-only commands (`get`, `describe`, `list`, `logs tail`) freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders such as `<fn>`, `<table>`, `<bucket>`, `<region>` and `<account-id>` come from `.kiro/steering/tech.md`, the IaC source or the error message. Never guess a region; use the one in `tech.md`. AWS quotas and defaults change: where a playbook says "check current quotas", look them up in the Service Quotas console or the service documentation. If the AWS CLI is not set up where Kiro runs, ask the teammate to run the command (or read the same data in the console) and paste only the 10 to 30 relevant lines.

## Start here (every AWS bug)

1. **Who and where am I?** Many "not found" and "it's empty" bugs are the wrong account, region or stage.

   ```bash
   aws sts get-caller-identity   # account and role/user actually in use
   aws configure list            # profile and region, and where each value comes from
   ```

   Compare with the region in `tech.md` and the region selector in the console.
2. **Which deployment is the client calling?** Check the API URL and stage in the frontend config (`.env`, `amplify_outputs.json` or similar) and when that stage was last deployed.
3. **Get a request ID.** API Gateway returns its own request ID in a response header (for example `x-amzn-RequestId` on REST APIs or `apigw-requestid` on HTTP APIs) and in its access logs. Lambda logs print a different ID, the Lambda `RequestId`, on the START, END and REPORT lines, so the header ID will not match them. To join the two, log `event.requestContext.requestId` (the API Gateway ID, present in REST and HTTP API proxy events) once at the start of each handler. Then search logs by ID instead of scrolling.
4. **Read logs in the right region and group.** Lambda logs go to `/aws/lambda/<function-name>` by default.
5. **Find the first error, not the last.** Later errors are usually consequences.
6. **Ask who changed what.** Ask the team about console changes. The CloudTrail Event history page shows recent management events (for example `UpdateFunctionConfiguration` or `PutBucketPolicy`). Data events such as S3 object reads or DynamoDB item writes are not there unless a trail with data events was set up.
7. **Credential errors are not permission errors.** `ExpiredToken`, `The security token included in the request is invalid` and `Unable to locate credentials` mean the caller's credentials are stale or missing. Re-login (`aws sso login --profile <profile>` if the team uses IAM Identity Center), check `AWS_PROFILE`, and remove stale `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` environment variables, which take precedence over the profile.
8. **Outages are rare.** Check the AWS Health Dashboard last, not first.

## Then

Write down what steps 1 to 5 found (account, region, stage, request ID, first error) in the bug card's Evidence line, and open the matching playbook.
