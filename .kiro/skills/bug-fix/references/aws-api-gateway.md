# API Gateway and CORS triage

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

First find out which API type it is: **REST API** (`AWS::ApiGateway::RestApi`, CDK `RestApi`/`LambdaRestApi`) or **HTTP API** (`AWS::ApiGatewayV2::Api`, CDK `HttpApi`). Errors, logging and CORS work differently in each.

| Status | Meaning and usual cause |
|---|---|
| 400 | Request validation failed (REST request validators or models), or your Lambda returned 400. Read the response body |
| 401 | An authorizer rejected the request: missing, expired or wrong token, the wrong header, or a token from another user pool or app client. See `aws-amplify-cognito.md` |
| 403 `Missing Authentication Token` (REST) | Usually the path or method does not exist on that stage: a typo, the stage missing from the URL, the method never created, or the API not redeployed after a change. Also returned when an IAM-authorized method is called without SigV4 signing |
| 403, other messages | A Lambda authorizer denied it, a cached authorizer policy built for one method was reused for another (authorizer caching), a required API key is missing (`x-api-key`, REST usage plans), a resource policy, WAF, or IAM auth |
| 404 `Not Found` (HTTP API) | No route matches the method and path |
| 413 | The payload is over the API Gateway or Lambda request size limit (check current quotas). Upload files straight to S3 with a presigned URL instead (see `aws-s3.md`) |
| 429 | Throttling at the stage, route, usage plan or account level. Check the throttling settings in IaC |
| 500 | REST: often a configuration error, such as API Gateway lacking permission to invoke the Lambda (execution log: `Invalid permissions on Lambda function`). HTTP API: integration failures, including Lambda errors, usually show as 500; check `$context.integrationErrorMessage` in the access log |
| 502 | REST with Lambda proxy: the Lambda threw an unhandled error or returned a malformed response (execution log: `Malformed Lambda proxy response`). The response must be `{ "statusCode": <number>, "headers": {...}, "body": "<string>" }`, with `body` as a string (`JSON.stringify`) |
| 504 `Endpoint request timed out` | The integration took longer than API Gateway's integration timeout (about 29 to 30 seconds by default; check current quotas). Raising the Lambda timeout does not help. Make the call faster, or move to streaming or an async pattern (hand off to `architecture-selection`) |

Logs:

- REST: enable CloudWatch execution logging on the stage. This needs a CloudWatch Logs role ARN set once in the API Gateway account settings. Logs land in `API-Gateway-Execution-Logs_<api-id>/<stage>`. Enable access logs too. The console's method **Test** feature shows a full execution log but skips the authorizer and CORS, so it cannot reproduce browser-only problems.
- HTTP API: enable access logging and include `$context.status`, `$context.integrationErrorMessage` and `$context.authorizer.error`.
- REST API changes take effect only after **Deploy API** to the stage. An HTTP API stage with auto-deploy enabled deploys by itself.

## CORS playbook

1. Open the failing request in the browser DevTools Network tab. If the actual request has a 4xx or 5xx status, fix that error first; the CORS message is a side effect of an error response without CORS headers.
2. Test the preflight directly:

   ```bash
   curl -i -X OPTIONS "$API_URL/<path>" \
     -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type,authorization"
   ```

   Expect a 2xx with `Access-Control-Allow-Origin` matching your origin, `Access-Control-Allow-Methods` including the method, and `Access-Control-Allow-Headers` including every header the browser sends.
3. Match the cause:
   - **REST with Lambda proxy:** the Lambda must return CORS headers on every response, including errors. Use one shared response helper.
   - **REST, gateway-generated errors** (401, 403, 502, 504) have no CORS headers unless you add them to the API's Gateway Responses (`DEFAULT_4XX`, `DEFAULT_5XX`).
   - **REST with no OPTIONS method:** each resource needs an OPTIONS method to answer preflight (console Enable CORS, CDK `defaultCorsPreflightOptions`, or SAM `Cors`), and the API must be redeployed to the stage.
   - **REST with an authorizer on OPTIONS:** browsers do not send `Authorization` on preflight, so OPTIONS must not use an authorizer.
   - **HTTP API:** configure CORS on the API itself. API Gateway then answers preflight and ignores CORS headers returned by the integration, so fix the API's CORS settings, not the Lambda.
   - **Origin mismatch:** `http://localhost:5173` and `http://127.0.0.1:5173` are different origins; the deployed Amplify or CloudFront domain is missing; an origin was written with a trailing slash.
   - **Credentials:** requests using cookies or `credentials: "include"` cannot use `Access-Control-Allow-Origin: *`. Return the exact origin and `Access-Control-Allow-Credentials: true`. Apps that send a token in a header usually do not need credentials mode.
   - **Custom headers** (for example `x-api-key`) missing from `Access-Control-Allow-Headers`.

Do not: use public CORS proxy services, disable browser security, or combine `*` with credentials.
