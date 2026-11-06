# Scripts de inicialização

Os scripts Bash podem ser executados de qualquer diretório e usam o `.env` da raiz. Antes do primeiro uso, configure esse arquivo a partir de `.env.example`.

Na raiz do projeto:

```bash
./scripts/start-db.sh
./scripts/start-keycloak.sh
./scripts/start-back.sh
```

- `start-db.sh`: inicia o PostgreSQL do Keycloak em segundo plano e aguarda o banco ficar saudável.
- `start-keycloak.sh`: inicia o Keycloak em segundo plano, incluindo o PostgreSQL caso ainda não esteja em execução. Aguarde o término da inicialização antes de fazer login.
- `start-back.sh`: inicia a API em `http://127.0.0.1:8000`, com recarga automática, usando a `.venv`. O terminal permanece ocupado; `Ctrl+C` encerra a API. A documentação fica em `/docs`.

O banco do backend é SQLite (`storage/agendamento.db`), inicializado automaticamente pela API. O PostgreSQL do Docker armazena os dados do Keycloak.

Se ainda não instalou as dependências do backend:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Para escolher outra porta da API:

```bash
./scripts/start-back.sh --port 8001
```

Os scripts do Docker tentam usar `sudo` quando não conseguem acessar o daemon diretamente. A senha, quando necessária, é solicitada no próprio terminal.

Para acompanhar os logs ou parar os containers, execute na raiz (com `sudo` se necessário):

```bash
docker compose logs -f keycloak
docker compose down
```

Parar os containers dessa forma preserva os dados do PostgreSQL.
