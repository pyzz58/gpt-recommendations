#!/bin/sh
set -eu

: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD must be set}"

psql \
  --set=ON_ERROR_STOP=1 \
  --set=app_password="${POSTGRES_APP_PASSWORD}" \
  --username "${POSTGRES_USER}" \
  --dbname "${POSTGRES_DB}" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'medical_one_app') THEN
    CREATE ROLE medical_one_app LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS;
  END IF;
END
$$;

ALTER ROLE medical_one_app PASSWORD :'app_password';
SQL
