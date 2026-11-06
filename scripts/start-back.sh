#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/common.sh"

require_env
if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
    echo 'Ambiente Python ausente. Execute na raiz do projeto:' >&2
    echo '  python -m venv .venv' >&2
    echo '  .venv/bin/pip install -r requirements.txt' >&2
    exit 1
fi

# Inicia o PostgreSQL antes da API; as tabelas sao criadas no lifespan.
"$PROJECT_ROOT/scripts/start-db.sh"
# Argumentos adicionais sao repassados ao Uvicorn (ex.: --port 8001).
exec "$PROJECT_ROOT/.venv/bin/python" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 "$@"
