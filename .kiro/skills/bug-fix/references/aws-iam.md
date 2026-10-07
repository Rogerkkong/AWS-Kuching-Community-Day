# IAM AccessDenied triage

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

The error message names everything you need:

```text
User: arn:aws:sts::111122223333:assumed-role/checkin-fn-role/checkin-fn
is not authorized to perform: dynamodb:PutItem
on resource: arn:aws:dynamodb:<region>:111122223333:table/Checkins
because no identity-based policy allows the dynamodb:PutItem action
```

1. **Principal:** the role after `assumed-role/`. Is it the role you expected (the Lambda execution role, a Cognito identity pool role, the CI role, your own)?
2. **Action:** the exact action to allow.
3. **Resource:** the exact ARN to allow it on.
4. **Reason** (the `because ...` clause):
   - `no identity-based policy allows`: add the permission to that principal's role (below).
   - `no resource-based policy allows`: the resource's own policy (for example a bucket policy or KMS key policy) must also allow it; this usually means cross-account access or a KMS key.
   - `no permissions boundary allows`, `no session policy allows` or `no service control policy allows`: a guardrail set by the account owner limits the role, so adding to the role's policy alone will not help. Ask the account owner.
   - `with an explicit deny in ...`: explicit deny always wins, so an allow will not help. Find the deny; if it is an organization or event-account restriction, ask the account owner or organizers.

Least-privilege fix, scoped to the one action and resource:

```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:PutItem"],
  "Resource": "arn:aws:dynamodb:<region>:<account-id>:table/Checkins"
}
```

Prefer the IaC tool's grant helpers, which scope to the resource: CDK `table.grantReadWriteData(fn)` or `bucket.grantPut(fn)`, SAM policy templates such as `DynamoDBCrudPolicy` or `S3ReadPolicy`, or the Amplify backend's resource access rules.

Common ARN mistakes:

- A Query on a GSI also needs the index ARN: `arn:aws:dynamodb:<region>:<account-id>:table/Checkins/index/*`.
- S3: `s3:ListBucket` goes on `arn:aws:s3:::<bucket>`; object actions (`s3:GetObject`, `s3:PutObject`) go on `arn:aws:s3:::<bucket>/*`.
- Resources encrypted with a customer-managed KMS key also need `kms:Decrypt` or `kms:GenerateDataKey` on that key.
- Deploys or services that hand a role to another service need `iam:PassRole` on that role.
- Bedrock inference profiles need both the profile ARN and the foundation-model ARNs it routes to (see `aws-bedrock.md`).
- The policy went onto the wrong role or the wrong stage's role. IAM changes can take a short time to propagate; retry once before digging further.

Check a fix before deploying:

```bash
aws iam simulate-principal-policy --policy-source-arn <role-arn> \
  --action-names dynamodb:PutItem --resource-arns <table-arn>
```

Treat the simulator result as a strong hint, not proof; reproduce the real call afterwards.

Never: `"Action": "*"`; `"Resource": "*"` (unless the service documentation says that action does not support resource-level permissions, and then only for that action); `AdministratorAccess` or `*FullAccess` managed policies on application roles; access keys in code or committed `.env` files.
