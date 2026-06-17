#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

exec docker compose --env-file "$SCRIPT_DIR/.env.docker" "$@"
