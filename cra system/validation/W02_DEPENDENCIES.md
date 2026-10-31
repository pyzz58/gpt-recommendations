# CRA-W02 dependency and environment lock

Date: 2026-10-31. This is an engineering dependency record, not a clinical
validation.

## Backend

| Component | Locked version | Licence | Role |
| --- | --- | --- | --- |
| FastAPI | 0.162.0 | MIT | HTTP API and OpenAPI |
| Uvicorn | 0.54.0 | BSD-3-Clause | ASGI server |
| Authlib | 1.9.1 | BSD-3-Clause | OIDC authorization-code adapter |
| itsdangerous | 2.2.0 | BSD-3-Clause | Signed session codec |
| httpx2 | 2.16.0 | BSD-3-Clause | FastAPI/Starlette test transport |
| SQLAlchemy | 2.0.55 | MIT | W01 persistence and authorization queries |
| Pydantic | 2.14.2 | MIT | API, identity and OutputEnvelope contracts |

Installed versions are resolved from `uv.lock` under CPython 3.13.15.

## Frontend

| Component | Locked version | Licence |
| --- | --- | --- |
| React / React DOM | 19.3.1 | MIT |
| Vite | 8.3.5 | MIT |
| TypeScript | 5.9.3 | Apache-2.0 |
| @vitejs/plugin-react | 6.1.2 | MIT |
| openapi-typescript | 7.13.0 | MIT |
| Vitest | 5.0.5 | MIT |
| @types/node | 24.19.2 | MIT |
| @types/react / @types/react-dom | 19.3.0 | MIT |

`web/package-lock.json` is the frontend exact lock. W02 verification uses Node
24.22.2 and npm 11.19.1. Vite/plugin peer requirements accept Node 24.

PostgreSQL remains pinned to the PostgreSQL 18.6 image digest recorded in
W01_DEPENDENCIES.md. Codespaces pins the Node and Docker devcontainer features;
the base Python image remains the project's existing tag rather than a claimed
production image pin.

Official package metadata:

- https://pypi.org/project/fastapi/0.162.0/
- https://pypi.org/project/uvicorn/0.54.0/
- https://pypi.org/project/Authlib/1.9.1/
- https://pypi.org/project/itsdangerous/2.2.0/
- https://pypi.org/project/httpx2/2.16.0/
- https://www.npmjs.com/package/react/v/19.3.1
- https://www.npmjs.com/package/vite/v/8.3.5
- https://www.npmjs.com/package/typescript/v/5.9.3
