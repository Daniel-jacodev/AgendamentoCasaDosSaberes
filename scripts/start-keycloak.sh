#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

require_env
# O Compose inicia tambem o PostgreSQL e aguarda sua saude antes do Keycloak.
compose up -d keycloak
echo 'Keycloak iniciado. Aguarde a importacao do realm; acompanhe com docker compose logs -f keycloak.'
