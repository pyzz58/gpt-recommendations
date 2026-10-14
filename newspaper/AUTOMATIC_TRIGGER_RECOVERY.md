# Newspaper automatic trigger recovery — Issue #53

## Status (not yet deployed)
This branch adds an authenticated `repository_dispatch` entrypoint. It is **not** a functioning independent timer until a separate scheduler is configured and this PR is merged to `main`. Do not infer success from PR CI or manual runs. Never dispatch production events as a test without explicit user approval.

## Canonical timing
Beijing local date is the edition. Target delivery is 01:00 Asia/Shanghai; attempts are allowed only from 01:00 inclusive to 02:00 exclusive. Existing native prepare crons are 00:05 and 00:20; native send crons are 01:03, 01:16, 01:29, 01:42 and 01:55. The fallback should call the dispatch endpoint near 00:20 (prepare) and 01:10/01:30/01:50 (send retries). These are *suggested* fallback schedules, not yet deployed. No automatic sends after 02:00.

## External service configuration (requires separate authorization)
Use a reliable scheduler independent of GitHub Actions. Configure authenticated HTTPS POST:

`https://api.github.com/repos/pyzz58/gpt-recommendations/dispatches`

Headers:
- `Authorization: Bearer <FINE_GRAINED_GITHUB_TOKEN>`
- `Accept: application/vnd.github+json`
- `X-GitHub-Api-Version: 2022-11-28`
- `Content-Type: application/json`

JSON body: `{"event_type":"newspaper-daily-tick"}`

Use a fine-grained GitHub token scoped to this repository with Contents write permission required for repository_dispatch. Store the token only in the external scheduler's secret store. Do not paste it into chat, workflow YAML, issues, or logs. The dispatch endpoint normally returns HTTP 204 if accepted; 204 means **event accepted**, not workflow started or mail delivered.

## Acceptance evidence
For three consecutive real edition days, collect (1) GitHub run with `event=repository_dispatch` or `schedule`, (2) run creation time and job start time, (3) prepared bundle result, (4) send step outcome and SMTP acceptance Message-ID, (5) receipt state. If no run is created by 01:10, report trigger failure independently of GitHub Actions; the scheduler's own request logs must be preserved.

## Known limitations
- GitHub's native `schedule` can be delayed or dropped. `repository_dispatch` is a second entrypoint but still depends on GitHub Actions execution.
- Current `actions/cache` receipt is not a transactional lock. Do not enable overlapping external ticks until duplicate/unknown SMTP outcomes are handled safely.
- `workflow_dispatch` is not the same as `repository_dispatch`. Do not use the green Run workflow button for production testing.
- This recovery does not establish QQ inbox delivery; SMTP acceptance and actual mailbox receipt are separate.
