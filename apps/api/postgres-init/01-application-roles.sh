#!/bin/sh
set -eu

psql \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set ON_ERROR_STOP=1 \
  --set app_password="$APP_DB_PASSWORD" \
  --set migrator_password="$MIGRATOR_DB_PASSWORD" <<'SQL'
CREATE ROLE cgs_migrator LOGIN PASSWORD :'migrator_password';
CREATE ROLE cgs_app LOGIN PASSWORD :'app_password';
GRANT CONNECT ON DATABASE cgs_shield TO cgs_migrator, cgs_app;
ALTER SCHEMA public OWNER TO cgs_migrator;
GRANT USAGE ON SCHEMA public TO cgs_app;
GRANT CREATE ON SCHEMA public TO cgs_migrator;
ALTER DEFAULT PRIVILEGES FOR ROLE cgs_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cgs_app;
SQL
