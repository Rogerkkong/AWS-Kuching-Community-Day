# S3 triage

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

```bash
aws s3api head-object --bucket <bucket> --key "<key>"
aws s3api get-bucket-location --bucket <bucket>   # a null LocationConstraint means us-east-1
aws s3api get-public-access-block --bucket <bucket>
aws s3api get-bucket-policy --bucket <bucket>
aws s3api get-bucket-cors --bucket <bucket>
```

| Error or symptom | Cause | Fix |
|---|---|---|
| 403 `AccessDenied` on an object that "should exist" | The caller lacks `s3:GetObject` on `<bucket>/*`; or the object does not exist and the caller lacks `s3:ListBucket`, in which case S3 returns 403 instead of 404; or the key differs (case, leading slash, URL encoding of spaces and `+`) | `head-object` the exact key, then fix the key or the IAM policy (see `aws-iam.md`) |
| Public images or site return 403 | Block Public Access is on, or no bucket policy allows reads | Prefer serving through CloudFront with origin access control, or Amplify Hosting, over a public bucket. Ask the team before making anything public |
| `AccessControlListNotSupported: The bucket does not allow ACLs` | The code sets an ACL (for example `public-read`), but the bucket's Object Ownership setting disables ACLs | Remove the ACL from the request |
| Browser upload blocked by CORS | The bucket CORS rules are missing the origin, method (PUT or POST) or header (Content-Type) | Add a CORS rule (example below) in IaC |
| `Request has expired` | A presigned URL was used after it expired | Set the expiry explicitly (SDK defaults differ) and generate the URL right before use, not hours earlier at page load. A URL signed with temporary credentials (such as a Lambda role) stops working when those credentials expire, even if the requested expiry is longer. SigV4 presigned URLs are capped at 7 days |
| `SignatureDoesNotMatch` on a presigned PUT | The client sent different headers than were signed (commonly `Content-Type`), used another HTTP method, or the URL was re-encoded | Sign with the exact `Content-Type` the browser will send, and pass the URL through unchanged |
| `PermanentRedirect`, or `AuthorizationHeaderMalformed` mentioning a region | The S3 client is configured for a different region than the bucket | Create the client with the bucket's region |
| `RequestTimeTooSkewed` | The local clock is wrong | Sync the system clock |
| Files land in the wrong bucket | The bucket name came from another stage's env var | Check the env var and stage |

Example bucket CORS rules (console JSON format; restrict origins to the ones you use):

```json
[
  {
    "AllowedOrigins": ["http://localhost:5173", "https://<your-app-domain>"],
    "AllowedMethods": ["GET", "PUT"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

Do not: make a bucket public to fix a 403, allow `"Principal": "*"` with write actions, or write presigned URLs to logs or chat.
