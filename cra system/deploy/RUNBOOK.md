# CRA runtime runbook

This runbook prepares an approved deployment. Running it against a synthetic
test environment does not establish authorization for real clinical data.

## 1. Preconditions

Obtain and record:

- approved use, accountable owner and data processing/storage terms;
- OIDC issuer, client, actor claim, tenant claim and a tested logout/revocation;
- private PostgreSQL and private object storage;
- externally managed secret injection;
- TLS reverse proxy with a private route to the web container;
- immutable API/web image digests;
- backup destination, retention and isolated restore environment;
- approved OCR/model runtime or an explicit disabled capability;
- physical device and weak-network support scope.

Do not commit `.env`, credentials, certificates, private logs or clinical
materials.

## 2. Configure and validate

Use `deploy/runtime.env.example` only as a key template. Inject production values
through the approved secret manager. Then run:

```bash
uv run --frozen python tools/check_deployment.py \
  --check \
  --env-file /approved/private/runtime.env
docker compose --env-file /approved/private/runtime.env \
  -f deploy/compose.runtime.yml config --quiet
```

The check requires:

- `CRA_ENV=production`;
- HTTPS public and OIDC URLs;
- secure session cookie and a non-template secret;
- PostgreSQL via `postgresql+psycopg`;
- private S3-compatible storage;
- digest-pinned API and web images;
- unapproved model/analysis providers disabled.

## 3. Build and pin images

The Dockerfiles are candidates for the approved registry, not production
approval:

```bash
docker build -f deploy/api.Dockerfile -t cra-api:candidate .
docker build -f deploy/web.Dockerfile -t cra-web:candidate .
```

The approved registry must scan, sign and record both image digests. Production
must reference `repository/image@sha256:...`; never deploy `latest`.

## 4. Deploy

```bash
docker compose --env-file /approved/private/runtime.env \
  -f deploy/compose.runtime.yml pull
docker compose --env-file /approved/private/runtime.env \
  -f deploy/compose.runtime.yml up -d postgres
docker compose --env-file /approved/private/runtime.env \
  -f deploy/compose.runtime.yml run --rm migrate
docker compose --env-file /approved/private/runtime.env \
  -f deploy/compose.runtime.yml up -d api worker web
docker compose --env-file /approved/private/runtime.env \
  -f deploy/compose.runtime.yml ps
```

Verify:

1. `https://<approved-host>/health/live` returns service OK.
2. `/health/ready` returns PostgreSQL ready.
3. OIDC login succeeds and logs out/revokes as approved.
4. The logged-in actor sees only authorized studies and centers.
5. A synthetic upload writes to the approved private store and its document
   reference can be read only through an authorized API request.
6. Audit timestamps, CSRF and secure cookies are present.
7. The approved reverse proxy sets HTTPS forwarding headers and blocks direct
   public access to API/PostgreSQL/object storage.

## 5. Backup

Use the approved database and object-storage backup tooling. At minimum:

- record database backup ID, timestamp, encryption/key reference and checksum;
- snapshot or version the object store and record manifest/checksum;
- confirm issue, rule, audit, outbox and issued-report tables are included;
- verify retention and deletion policy with the owner.

Do not use this command as the only production backup strategy:

```bash
pg_dump --format=custom --no-owner --file=/private/backup/cra.dump "$DATABASE_URL"
```

## 6. Restore drill

Restore into a separate approved network with no connection to the live trial:

1. Provision a fresh private PostgreSQL and object-store target.
2. Restore the database and file objects from the same backup set.
3. Run migrations only to their already-recorded version; do not silently
   upgrade during the integrity check.
4. Verify study/site isolation, issue numbers, rule activation dates, audit,
   outbox state, EDC/source references, report snapshots and file hashes.
5. Perform authorized OIDC login and confirm revoked membership remains denied.
6. Record restore duration, failures, manual repair and final decision.
7. Destroy the isolated synthetic/approved restore copy according to policy.

Application-level acceptance is in [restore-check.md](restore-check.md).

## 7. Trial operation

Proceed only after `validation/AUTHORIZED_TRIAL.md` is updated by the authorized
owner. Keep raw measurements in the approved private environment and commit only
deidentified summaries. Record:

- actual task start/end, interruptions, corrections and rework;
- identity/date/value/unit/instance errors and missed/extra findings;
- automatically usable fields versus manual corrections/backfill;
- physical desktop/iPad, browser, network and offline behavior;
- report total time for the same task and matched existing workflow.

Feedback is classified in `validation/FEEDBACK_REGISTER.md` and linked to a CRA
requirement, module and task. Do not rebuild the whole system for one localized
issue.

## 8. Upgrade

1. Review source-bound CI, provider/model hashes and migration compatibility.
2. Back up database and object store.
3. Deploy the new image by digest to a staging environment.
4. Run migration, health, login, scoped read, synthetic upload, restore and
   affected clinical regressions.
5. Record approved release and switch production.
6. Re-run smoke checks and monitor errors/review burden.

## 9. Rollback

Keep the previous image digests and prior application version. For a
non-compatible migration, stop new writes, restore the tested backup or execute
the reviewed down migration only when lossless rollback is proven. Re-running
old code against a newer incompatible schema is not an acceptable rollback.

Verify authorization, immutable snapshots and file references after rollback.
Keep source files, facts/lists/issues and signed snapshots available throughout.

## 10. Pause and recovery

If a critical automatic-use failure occurs, pause only that provider/use while
preserving manual review and existing records. Investigate, add a regression,
rerun provider and business checks, record the release, then resume the affected
scope. Do not add a CRA approval for every monitoring visit.
