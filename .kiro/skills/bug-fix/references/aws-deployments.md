# Deployment triage (CloudFormation, CDK, SAM, Amplify)

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

CDK, SAM and Amplify Gen 2 backends all deploy through CloudFormation, so the stack events hold the real error:

```bash
aws cloudformation describe-stack-events --stack-name <stack> \
  --query 'StackEvents[?contains(ResourceStatus, `FAILED`)].[Timestamp,LogicalResourceId,ResourceStatusReason]' \
  --output table
```

Events are listed newest first, so the root cause is the **earliest** failure (at the bottom). Later `Resource creation cancelled` entries are side effects. If the earliest failure is a nested stack (`Embedded stack ... was not successfully created`, common with Amplify Gen 2 and CDK nested stacks), run the same command on that nested stack's name or ARN to see the real error.

| Error or symptom | Cause | Fix |
|---|---|---|
| `... already exists` | A fixed physical name collides with another stack, stage or teammate. S3 bucket names are globally unique | Let the tool generate names, or include the stage and account in the name |
| `is not authorized to perform` during deploy | The deploying identity lacks a permission | See `aws-iam.md`. On an event-provided account, ask the organizers |
| `Has the environment been bootstrapped?` (CDK) | CDK bootstrap has not run in this account and region | `cdk bootstrap aws://<account-id>/<region>`, once per account and region. It creates resources, so ask first |
| Stack stuck in `ROLLBACK_COMPLETE` after a failed first create | A stack in this state cannot be updated | It must be deleted and recreated. Ask a teammate first |
| `UPDATE_ROLLBACK_FAILED` | A resource could not be rolled back, often because it was changed or deleted by hand | Ask a teammate before using continue-update-rollback or deleting anything; data resources can be lost |
| A deploy reverts a fix | The fix was made in the console only (drift) | Put the change in IaC |

Before deploying a fix: `cdk diff`, or `sam validate` and `sam build`, or watch the Amplify sandbox terminal output, whichever the project uses.
