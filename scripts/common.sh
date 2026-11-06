#!/usr/bin/env bash
# Funcoes compartilhadas pelos scripts de inicializacao.
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$PROJECT_ROOT"

require_env() {
    if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
        echo 'Arquivo .env ausente. Copie .env.example para .env e configure as senhas.' >&2
        exit 1
    fi
}

compose() {
    if ! command -v docker >/dev/null 2>&1; then
        echo 'Docker nao encontrado. Instale Docker Engine e Docker Compose.' >&2
        exit 1
    fi
    if docker info >/dev/null 2>&1; then
        docker compose --project-directory "$PROJECT_ROOT" -f "$PROJECT_ROOT/compose.yaml" "$@"
    elif command -v sudo >/dev/null 2>&1; then
        echo 'Docker indisponivel sem privilegios; tentando com sudo.' >&2
        sudo docker compose --project-directory "$PROJECT_ROOT" -f "$PROJECT_ROOT/compose.yaml" "$@"
    else
        echo 'Nao foi possivel acessar o Docker. Verifique as permissoes e se o servico esta ativo.' >&2
        exit 1
    fi
}
