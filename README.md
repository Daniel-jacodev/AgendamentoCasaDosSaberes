# Backend — Agendamento Casa de Saberes

API para consultar a programação da Casa de Saberes, apresentar horários disponíveis e receber solicitações de **visita mediada** ou **uso de espaço**. A equipe administrativa consulta os pedidos e decide manualmente pela aprovação ou recusa. A referência funcional é o [documento de requisitos](Documentação/Requisitos%20-%20Sistema%20de%20Agendamento%20Casa%20de%20Saberes.pdf).

Este repositório é dedicado ao **backend em Python, FastAPI e Pydantic**. A autenticação é feita pelo **Keycloak**. O frontend será um **WordPress separado**, responsável pelas páginas, formulários, calendários e acessibilidade.

## Estado atual

A API possui rotas de eventos e autenticação com Keycloak: `POST /usuarios` (cadastro), `POST /usuarios/login` (tokens) e `GET /usuarios/me` (perfil autenticado). Consulte o [guia de execução e exemplos](Documentação/Keycloak.md).

## Contrato de eventos do MVP

`GET /eventos/` retorna `{"eventos": [...]}`. `POST /eventos/` é público: sem sessão, retorna o evento com status `pendente`; com token válido, identifica o administrador e cria o evento já como `aceito`. O status no JSON de entrada não altera essa regra. O campo `celular` é opcional (até 30 caracteres). Enviar `status="aceito"` no cadastro público mantém o evento pendente; a aprovação exige autenticação.

A aprovação de uma solicitação pública envia o evento completo para `PUT /eventos/{id}` com `status="aceito"`. A resposta e a listagem retornam o status persistido. No painel administrativo, eventos criados por uma pessoa autenticada já são aceitos; solicitações públicas continuam sujeitas a aprovação ou exclusão. Os únicos status são `pendente` e `aceito`. A recusa usa `DELETE /eventos/{id}`, com `204` sem corpo. GET e POST são públicos; PUT e DELETE exigem token do Keycloak. A confirmação por pop-up acontece no frontend antes da chamada; a API não mantém estados de confirmação ou histórico de recusas.

Espaços: `1 = Auditório`, `2 = Quintal`, `3 = Salas Expositivas`, `4 = Varanda`; o espaço é obrigatório. Consulte os [comandos de inicialização](scripts/README.md).

## Horários dos eventos

Criação e alteração recusam períodos que se sobrepõem a outro evento no mesmo espaço, retornando `409` com `detail` explicando o conflito. Eventos em espaços diferentes podem ocorrer simultaneamente. Por exemplo, se existe um evento das 14h às 16h, outro no mesmo espaço das 15h às 17h é recusado; um evento a partir das 16h é permitido. Na alteração, o próprio evento é desconsiderado na verificação.

O fim deve ser posterior ao início; períodos inválidos retornam `422`. Datas sem fuso representam o horário de Fortaleza; datas com offset são convertidas para esse horário antes de salvar e comparar. A API usa um [lock transacional do PostgreSQL](https://www.postgresql.org/docs/17/explicit-locking.html) para serializar a verificação e a gravação e impedir reservas simultâneas conflitantes. Eventos que já estavam cadastrados são preservados.

## Iniciar os serviços

Consulte os [scripts de inicialização](scripts/README.md) para iniciar o backend, o PostgreSQL e o Keycloak separadamente.

## Estrutura

```text
projsocial/
├── Documentação/             # Requisitos originais
├── README.md
├── app/                      # Pacote Python do backend
│   ├── __init__.py
│   ├── config/               # Ambiente, configuração do banco, Keycloak e CORS
│   ├── controllers/          # APIRouter e operações HTTP públicas/administrativas
│   ├── dependencies/         # Depends: usuário autenticado, permissões e conexão com banco
│   ├── models/               # Representação dos dados e acesso à persistência
│   ├── schemas/              # Pydantic: validação de entrada e contratos JSON de saída
│   └── services/             # Regras de disponibilidade, conflitos e decisão manual
└── storage/
    └── private/              # Portfólios PDF opcionais; arquivos não versionados
```

Cada pasta de `app/` é um pacote Python. `app/main.py` cria a instância FastAPI e registra os routers. Os eventos são persistidos com SQLAlchemy e Psycopg 3 no PostgreSQL do serviço Docker `db`, com volume `app-db-data`. O Keycloak usa um banco separado (`keycloak-db`). As variáveis `DB_*` do `.env` configuram a conexão da API; consulte os [scripts de inicialização](scripts/README.md).

## Camadas e fluxo

A organização preserva as responsabilidades do MVC, adaptadas a uma API com frontend externo:

| Responsabilidade | Local e função |
| --- | --- |
| Model | `models/` representa e persiste solicitações e atividades. `services/` concentra as regras que operam sobre esses dados. |
| Controller | `controllers/` declara as rotas com `APIRouter`, recebe dados validados e chama os serviços ou modelos. |
| View | As telas ficam no WordPress. Na API, `schemas/` define as representações JSON de saída usando Pydantic e `response_model`. |
| Validação | `schemas/` define tipos e restrições dos dados recebidos; as regras de negócio ficam em `services/`. |
| Autorização e recursos | `dependencies/` verifica identidade e permissões e fornece recursos por requisição através de `Depends`. |
| Configuração | `config/` centraliza parâmetros de ambiente e conexões. |

Os próprios controllers agrupam as rotas em routers. Os schemas de entrada e saída devem ser distintos quando necessário, para que respostas públicas exponham apenas os campos previstos.

Fluxo: **WordPress → controller + schema de entrada + dependências → serviço/modelo → schema de saída → JSON para o WordPress**. Controllers coordenam HTTP; serviços aplicam as regras; modelos concentram a persistência. Uma transação deverá proteger a aprovação contra decisões simultâneas sobre horários conflitantes, conforme as regras de ocupação que forem definidas.

## Autenticação e integração

Para iniciar o Keycloak em Docker e configurar o realm e o cliente OIDC, consulte o [guia de Keycloak](Documentação/Keycloak.md).

O Keycloak gerencia usuários, credenciais, login, logout e expiração de sessões/tokens. A integração do WordPress com o Keycloak obterá o **access token** do usuário administrativo por OpenID Connect. As chamadas administrativas à API enviarão `Authorization: Bearer <access_token>`.

O backend deverá validar assinatura, expiração, emissor e audiência do token com as chaves públicas do Keycloak, além de exigir a permissão administrativa configurada. Essas verificações ficam em `dependencies/`. Token ausente ou inválido resulta em `401`; identidade válida sem a permissão necessária resulta em `403`. A sessão do WordPress, por si só, não autoriza acesso à API.

As decisões deverão registrar a referência `sub` do usuário do Keycloak para identificar quem aprovou ou recusou o pedido. Credenciais e hashes de senha ficam sob responsabilidade do Keycloak. Consultas públicas e envio de solicitações são acessíveis ao usuário externo sem login, conforme o fluxo dos requisitos.

Realm, clients, audiência da API e permissões serão definidos na integração. As origens do WordPress devem ser explicitamente permitidas em CORS quando o navegador acessar a API diretamente. CORS configura o acesso entre origens; a autorização administrativa continua sendo verificada pela API.

## Domínio e requisitos

| Dados | Finalidade |
| --- | --- |
| Solicitação | Tipo de pedido, intervalo solicitado, contato, proposta e referência ao espaço quando aplicável; status `pendente`, `aprovada` ou `recusada`, com registro da decisão e de seu autor. |
| Atividade publicada | Informações confirmadas e divulgadas na programação pública. Aprovação de um pedido e publicação precisam de regras próprias. |
| Identidade administrativa | Usuário e permissões no Keycloak; o backend registra a referência do autor das decisões. |

O espaço é uma referência a um catálogo mantido fora do sistema, conforme a definição do documento. Imagens e cores podem ser fornecidas por metadados estáticos ou por uma fonte externa, conforme o catálogo que for levantado.

| Requisitos | Responsabilidade prevista |
| --- | --- |
| RF01–RF03 | Consultas distintas de programação pública e disponibilidade; os dois calendários são apresentados no WordPress. |
| RF04–RF09 | Recebimento de pedidos, validação de contato e dados da proposta, incluindo características e classificação indicativa conforme a prioridade de cada requisito. |
| RF10 | Portfólio PDF opcional, com acesso protegido em `storage/private/`; a descrição textual permanece disponível. |
| RF12 | Login pelo Keycloak e proteção das operações administrativas pela API. |
| RF13–RF17 | Listagem, detalhes, calendário interno, identificação de conflitos e decisão manual. |
| RF18–RF19 | Registro da situação após a atividade e retorno ao solicitante, conforme prioridade e definição do canal de notificação. |
| RF21–RF22 | Metadados dos espaços para imagens e cores consistentes nas telas do WordPress. |

Dados de contato e anexos devem ter acesso restrito e não devem aparecer nas respostas públicas ou nos logs. O backend deverá validar PDFs e limitar seu tamanho quando esse recurso for implementado. A proteção dos dados de contato atende ao RNF08; o RNF07 será atendido pela configuração segura do Keycloak e pela validação dos tokens na API. A interface e os requisitos de acessibilidade pertencem ao WordPress.

## Decisões pendentes do produto

- **Disponibilidade:** horários de funcionamento, duração de visitas e conflitos entre visita, espaço e uso total da Casa.
- **Espaços:** catálogo, imagens e fonte dos metadados, preservando o escopo sem cadastro administrativo próprio de espaços.
- **Publicação:** como atividades confirmadas entram na programação pública.
- **Notificação:** retorno manual ou e-mail automático (RF19).
- **Visitas sem agendamento:** aplicação da exceção para grupos pequenos (RNG02).

A confirmação é sempre manual (RNG01), não há cobrança (RNG03), e 48 horas é um prazo de referência para retorno (RNG04). Dashboards quantitativos (RF20) estão fora do escopo. Essas definições pendentes não impedem a organização das pastas, mas devem orientar a implementação das respectivas funcionalidades.

Referências técnicas: [organização com APIRouter e dependências](https://fastapi.tiangolo.com/tutorial/bigger-applications/), [schemas de resposta no FastAPI](https://fastapi.tiangolo.com/tutorial/response-model/) e [OpenID Connect no Keycloak](https://www.keycloak.org/securing-apps/oidc-layers).
