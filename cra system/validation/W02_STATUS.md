# CRA-W02 completion record

Status: verified. Date: 2026-10-31.

This record covers the engineering API and browser shell only. It is not
clinical-use validation, and it does not implement later document, rule,
subject, laboratory or report workflows.

## Delivered

- FastAPI app, uniform error contract, request IDs, Postgres readiness, truthful
  capability reporting and OpenAPI at `backend/cra_app/main.py` and
  `backend/cra_app/platform/api.py`.
- Authlib OIDC adapter and server-side signed HttpOnly sessions at
  `backend/cra_app/governance/identity.py`; synthetic login is limited to
  synthetic/test and production ignores client-supplied actor/tenant headers.
- `GET /api/v1/me/scopes` at `backend/cra_app/governance/api.py`, backed by the
  W01 authorization service and returning only the actor's studies and centers.
- React/TypeScript/Vite login and workspace shell under `web/`; browser refresh
  restores the selected authorized project/center, with a stale/revoked choice
  falling back to the first currently authorized center.
- Generated `contracts/openapi.json` and `web/src/api/generated.ts`, plus a
  drift check. OutputEnvelope is a shared OpenAPI component and runtime model.
- Pinned Python/frontend dependencies, truthful W02 dependency ledger, separate
  Codespaces database initialization, migration and synthetic seed.

No additional database migration was required: signed sessions are stateless,
and the study/site/membership source remains migration `0001_governance`.

## Authoritative execution

- Tested commit: `2db8475906b57a1689ca0f6fcc19b02880c67c4f`.
- GitHub Actions run:
  https://github.com/pyzz58/gpt-recommendations/actions/runs/41178355227
- Task job: `cra-w02`.
- API: 6 PostgreSQL synthetic tests passed.
- Frontend: 3 workspace persistence tests passed; typecheck and production build
  passed; npm audit reported 0 vulnerabilities.
- Contracts: generated OpenAPI/frontend types were current.
- Runtime smoke: FastAPI, synthetic login, authorized scopes and Vite shell
  started together successfully.
- Devcontainer smoke: the exact `.devcontainer/cra-system/devcontainer.json`
  was built and launched on GitHub Actions; PostgreSQL migration/seed and the
  same API/Vite smoke passed inside remote workspace
  `/workspaces/gpt-recommendations/cra system`.
- Baseline: synchronization and 40 existing tests passed; W01 independently
  revalidated.
- Subject digest:
  `71579fb04f3122541840437ca1f5e6b956a6e3fca51d2d7206ff2ed1bd879377`.

The web UI was also opened against a local PostgreSQL 18.6 instance; login,
unavailable capability messaging, project/center selection and refresh
retention were visually checked.

## Remaining limits

- The logged-in GitHub account lacks the `codespace` scope, so an external
  GitHub Codespaces instance was not provisioned. The exact devcontainer was
  actually launched in GitHub Actions, but the hosted Codespaces service itself
  remains an environment-level validation item.
- Authlib OIDC authorization is wired, but no approved external identity provider
  or credentials were supplied. Only synthetic auth and claim mapping are
  validated; formal OIDC end-to-end login is not yet verified.
- The workspace stores only the selected IDs in browser localStorage. Server
  authorization remains authoritative on every API call.
- W02 has no subject monitoring, documents, rules, laboratory OCR/comparison,
  reports or real clinical trial data. Those remain W03 onward.

Next task by dependency: CRA-W03.
