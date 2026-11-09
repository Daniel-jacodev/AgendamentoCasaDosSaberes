# Keycloak e autenticação local

O Compose inicia Keycloak 26.8.1 e PostgreSQL persistente. Usa `start-dev` e HTTP local para desenvolvimento. A importação de realm segue a [documentação oficial](https://www.keycloak.org/server/importExport).

## Iniciar

```bash
cp .env.example .env
# Edite .env e substitua as tres senhas/segredos.
docker compose up -d
docker compose logs -f keycloak
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Aguarde a inicialização do Keycloak antes de chamar as rotas. A API fica em http://localhost:8000/docs e o console administrativo em http://localhost:8080/admin, com as credenciais `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD`.

O arquivo `docker/keycloak/proj-social-ufc-realm.json` importa automaticamente:

- Realm `proj-social-ufc`, com e-mails únicos e proteção contra tentativas repetidas.
- Cliente confidencial `proj-social-backend`, com Direct Access Grants para o login JSON e service account com `realm-management/manage-users` para cadastrar e consultar usuários.
- Audiência do backend nos access tokens, validada pela API junto de assinatura, emissor e expiração.
- Perfil em que sobrenome é opcional, permitindo entrar imediatamente após cadastrar `nome`, `email` e `senha`.

Os nomes e o segredo vêm do `.env`. Se mudar `KEYCLOAK_REALM`, renomeie também o arquivo de importação para `<nome-do-realm>-realm.json`, como exigido pelo Keycloak. O segredo pertence apenas ao backend. As contas criadas pela rota não recebem permissões administrativas. A senha fica no Keycloak.

**Realms existentes não são sobrescritos pela importação na inicialização.** Se já criou esse realm, ajuste o cliente, o segredo, os fluxos, o mapper de audiência, o perfil e a role da service account pelo console, ou importe o arquivo em um ambiente novo. Alterar o `.env` não atualiza clientes já persistidos. Não apague o volume de um ambiente com dados que deseja preservar.

Ao alterar `KEYCLOAK_PORT`, ajuste também `KEYCLOAK_HOSTNAME` e `KEYCLOAK_SERVER_URL`. A API é executada no host; se movê-la para um container, configure a URL interna em `KEYCLOAK_SERVER_URL` e o emissor público em `KEYCLOAK_ISSUER_URL`.

## Cadastro e login

```bash
curl -i http://localhost:8000/usuarios \
  -H 'Content-Type: application/json' \
  -d '{"nome":"Maria Silva","email":"maria@example.com","senha":"UmaSenha123!"}'

curl -i http://localhost:8000/usuarios/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"maria@example.com","senha":"UmaSenha123!"}'
```

Cadastro retorna `201` com `id`, `nome` e `email`. E-mail repetido retorna `409`; entrada inválida retorna `422`. Login retorna `200` com `access_token`, `refresh_token`, tempos de validade e `token_type`. Credenciais inválidas retornam `401`; falhas do provedor retornam `502`.

Para conferir a sessão, copie o `access_token` retornado:

```bash
curl http://localhost:8000/usuarios/me -H 'Authorization: Bearer SEU_ACCESS_TOKEN'
```

Sem token, com token adulterado, expirado ou de outra audiência/emissor, retorna `401`.

`docker compose down` para os serviços mantendo os dados. O fluxo de senha atende às rotas solicitadas; uma futura integração OIDC do WordPress pode usar Authorization Code com PKCE em um cliente separado. Para produção, configure HTTPS, modo `start`, segredos externos e política de recuperação/verificação de e-mail.
