#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

require_env
# PostgreSQL da aplicacao; aguarda o healthcheck do banco.
compose up -d --wait db
