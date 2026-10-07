# DynamoDB triage

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

```bash
aws dynamodb describe-table --table-name <table> \
  --query 'Table.{Keys:KeySchema,Attrs:AttributeDefinitions,GSIs:GlobalSecondaryIndexes[].{Name:IndexName,Keys:KeySchema},Status:TableStatus}'
aws dynamodb get-item --table-name <table> --key '{"pk":{"S":"<pk>"},"sk":{"S":"<sk>"}}'
```

Confirm the function reads the table you are looking at: table names usually come from an env var with a stage suffix.

| Error or symptom | Cause | Fix |
|---|---|---|
| `ValidationException: The provided key element does not match the schema` | Wrong key attribute names (`id` vs `pk`), a missing sort key, or the wrong type | Match `describe-table` exactly. `Type mismatch for key ... expected: S actual: N` means a string vs number mix-up |
| `ResourceNotFoundException: Requested resource not found` | Wrong table name, region or stage, or the table is still being created | Check the env var, the region and the table status |
| `ConditionalCheckFailedException` | The condition expression was false. Often this is correct behavior: a duplicate check-in, an existing item, a version mismatch | Map it to 409 Conflict or to idempotent success; do not retry blindly. Set `ReturnValuesOnConditionCheckFailure: ALL_OLD` to see the existing item. In transactions it arrives as `TransactionCanceledException` with `CancellationReasons` |
| `Attribute name is a reserved keyword` | Expressions use words such as `name`, `status`, `date` or `count` | Use `ExpressionAttributeNames` (`#s` for `status`) |
| Key attribute value is an empty string | Key attributes cannot be empty strings | Validate input before writing |
| `ProvisionedThroughputExceededException`, `ThrottlingException` | Provisioned capacity too low, a hot partition key, or a sudden spike | SDKs retry with backoff. Spread keys, batch writes, and check the billing mode and current pricing before switching modes |
| Items missing from results | Query and Scan return at most 1 MB per call; `Limit` applies before `FilterExpression`; GSI reads are eventually consistent; the wrong stage table | Loop on `LastEvaluatedKey` until it is absent. Do not expect a just-written item on a GSI immediately; strongly consistent reads exist only on the base table and local secondary indexes |
| Scan is slow or expensive | Scan reads the whole table | Fine for a demo-sized table. For a real access pattern, Query a key or GSI. Adding a GSI or changing keys is a data-model change: apply the stop rule |
| `Float types are not supported. Use Decimal types instead.` (Python boto3) | boto3 needs `Decimal` for numbers | Convert with `Decimal(str(x))`. On the way out, convert `Decimal` before JSON serialization (`Object of type Decimal is not JSON serializable`) |
| `Pass options.removeUndefinedValues=true to remove undefined values` (JS SDK v3) | An `undefined` value in the item | Drop undefined fields, or set `marshallOptions: { removeUndefinedValues: true }` on the document client |
| Values come back as `{ "S": "..." }` | The low-level client was used | Use `DynamoDBDocumentClient` from `@aws-sdk/lib-dynamodb`, or unmarshall |
| `Item size has exceeded the maximum allowed size` | The item is over the 400 KB item limit | Store large content in S3 and keep a pointer in the item |

Do not: switch a Query to a Scan to make it "work", ignore `ConditionalCheckFailedException` silently, or delete and recreate a table that holds data without asking.
