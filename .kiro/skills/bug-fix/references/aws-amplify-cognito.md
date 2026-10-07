# Amplify and Cognito triage

Part of the `bug-fix` skill. Do the checks in `aws-triage.md` ("Start here") first. Run read-only commands freely when permissions allow; ask before anything that creates, changes or deletes resources, data or permissions. Placeholders (`<fn>`, `<table>`, `<bucket>`, `<region>`, `<account-id>`) come from `.kiro/steering/tech.md`, the IaC source or the error message.

First identify the setup: Amplify Gen 2 (an `amplify/` folder with `backend.ts`, frontend config in `amplify_outputs.json`), Amplify Gen 1 (`amplify/backend/` and `aws-exports.js`), or Cognito used directly without Amplify.

Configuration:

- **The frontend points at the wrong backend.** Each Gen 2 sandbox is a separate backend per developer. An `amplify_outputs.json` from a teammate's sandbox or a deleted sandbox makes users and data "disappear" and tokens fail. Regenerate the outputs for the backend you mean: `npx ampx sandbox` writes them for your own sandbox, and `npx ampx generate outputs --app-id <app-id> --branch <branch>` writes them for a deployed branch. For Gen 1, `amplify pull`.
- **`Amplify.configure(...)`** must run once at the app entry point, before any Auth or Data call.
- **Frontend env vars** reach the browser only with the framework's public prefix (for example `VITE_` or `NEXT_PUBLIC_`), and changing them needs a rebuild and redeploy.

| Error or symptom | Cause | Fix |
|---|---|---|
| `NotAuthorizedException: Incorrect username or password.` | Wrong credentials, or the user exists in a different pool or sandbox | Check which user pool the frontend config points to |
| `UserNotConfirmedException` | Sign-up was never confirmed | `aws cognito-idp admin-get-user --user-pool-id <id> --username <user> --query UserStatus`. For fake test users only, confirm them with `admin-confirm-sign-up` (a write; ask first) |
| `Unable to verify secret hash for client` | The app client has a client secret; browser apps, including Amplify JS, need an app client without one | Use or create a public app client (no secret) in IaC |
| `InvalidPasswordException`, `UsernameExistsException`, `CodeMismatchException`, `ExpiredCodeException` | Password policy, duplicate sign-up, or a wrong or old verification code | Show the message to the user; resend the code |
| Verification emails do not arrive | The default Cognito email sender has a low daily sending limit, or the mail went to spam | Check current quotas. For the demo, pre-create and confirm the test users |
| `redirect_mismatch` (hosted or managed login) | The callback or sign-out URL is not in the app client's allowed list exactly (scheme, host, port, path, trailing slash) | Add the exact URL in IaC |
| API returns 401 even with a token | Wrong token type for the authorizer (ID vs access token), a token from another user pool or app client, an expired token, or a header format the authorizer does not expect | Decode the JWT payload locally (never on a website or in chat) and check `iss`, `aud` or `client_id`, `token_use` and `exp`. Send the token type the authorizer is configured for, refreshing it when expired |
| `Not Authorized to access <field> on type <Type>` (Amplify Data or AppSync) | The model's authorization rules do not allow the auth mode the client used (for example an API key or guest call against an owner-only model) | Align the client's `authMode` with the model's `.authorization(...)` rules |
| Each user sees only their own data | Owner-based rules working as designed | Confirm the intended rule with the team before changing it |
| Amplify Hosting build failed | Read the failing phase in the build log: Node version, a lockfile mismatch with `npm ci`, missing env vars in the Amplify console, the wrong output folder (`dist` vs `build`) | Fix the build settings or env vars and redeploy |
| 404 or blank page when refreshing a client-side route | No single-page-app rewrite rule | Add the SPA rewrite rule from the Amplify Hosting docs (rewrite to `/index.html` with status 200) |
| The old version is still served | Caching, or the wrong branch deployed | Hard refresh, and confirm the deployed commit in the Amplify console |
