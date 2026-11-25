# Backend — Agendamento Casa de Saberes

API para consultar a programação da Casa de Saberes, apresentar horários disponíveis e receber solicitações de **visita mediada** ou **uso de espaço**. A equipe administrativa consulta os pedidos e decide manualmente pela aprovação ou recusa. A referência funcional é o [documento de requisitos](Documentação/Requisitos%20-%20Sistema%20de%20Agendamento%20Casa%20de%20Saberes.pdf).

Este repositório é dedicado ao **backend em Python, FastAPI e Pydantic**. A autenticação é feita pelo **Keycloak**. O frontend será um **WordPress separado**, responsável pelas páginas, formulários, calendários e acessibilidade.

## Estado atual

A API possui rotas de eventos e autenticação com Keycloak: `POST /usuarios` (cadastro), `POST /usuarios/login` (tokens) e `GET /usuarios/me` (perfil autenticado). Consulte o [guia de execução e exemplos](Documentação/Keycloak.md).

## Contrato de eventos do MVP

As consultas retornam `{"eventos": [...]}`.

| Rota | Resultado | Acesso |
| --- | --- | --- |
| `GET /eventos/` | Programação confirmada para o público ou todos os eventos com sessão | Bearer do Keycloak opcional |
| `GET /eventos/pendentes` | Solicitações com status `pendente` | Bearer do Keycloak |
| `GET /eventos/aceitos` | Programação confirmada, com os campos públicos do evento | Público |
| `GET /eventos/ordenados` | Todos os eventos por data de início crescente, com desempate pelo ID | Bearer do Keycloak |

O frontend público deve usar `GET /eventos/aceitos` para carregar a programação. A resposta inclui ID, status, título, descrição, classificação indicativa, datas e ID do espaço.

`POST /eventos/` é público: sem sessão, retorna o evento com status `pendente`; com token válido, identifica o administrador e cria o evento já como `aceito`. O status no JSON de entrada não altera essa regra. O campo `celular` é opcional (até 30 caracteres). Enviar `status="aceito"` no cadastro público mantém o evento pendente; a aprovação exige autenticação.

`POST /eventos/` aceita JSON ou `multipart/form-data`. No formulário multipart, envie o JSON como texto no campo `dados` e, opcionalmente, um PDF de até 30 MB no campo `arquivo`. O anexo é salvo em `storage/private/`, e a resposta autenticada de consulta inclui `arquivo_pdf_id`.

`PATCH /eventos/{id}/status` recebe `{"status": "aceito"}`, `{"status": "negado"}` ou `{"status": "cancelado"}`. A edição completa via `PUT /eventos/{id}` também pode atualizar o status. Eventos negados e cancelados liberam o horário e ficam fora dos totais de confirmados e pendentes do relatório. `DELETE /eventos/{id}` exclui o evento e retorna `204`. PATCH, PUT e DELETE exigem token do Keycloak.

O espaço é obrigatório. Os IDs são `1 = Auditório`, `2 = Quintal`, `3 = Salas Expositivas`, `4 = Varanda` e `5 = Área Externa`. Consulte os [comandos de inicialização](scripts/README.md).

## Consultas de visitas mediadas

As consultas retornam `{"visitas": [...]}`.

| Rota | Resultado | Acesso |
| --- | --- | --- |
| `GET /visitas/` | Todas as visitas mediadas | Bearer do Keycloak |
| `GET /visitas/pendentes` | Somente visitas com status `pendente` | Bearer do Keycloak |
| `GET /visitas/aceitas` | Somente visitas com status `aprovada`, com ID e horários | Público |
| `GET /visitas/ordenadas` | Todas as visitas por data de início crescente, com desempate pelo ID | Bearer do Keycloak |
| `POST /visitas/` | Retorna `201` com status `pendente` para pedidos públicos ou `aprovada` para cadastros autenticados | Público, com Bearer do Keycloak opcional |
| `DELETE /visitas/{id}` | Exclui uma visita e retorna `204` | Bearer do Keycloak |

## Exposições e formulário de visita

| Rota | Contrato | Acesso |
| --- | --- | --- |
| `GET /exposicoes/` | Retorna `{"exposicoes": [...]}` com as exposições ativas em ordem de sala | Público |
| `GET /exposicoes/administracao` | Retorna `salas` (cada uma com `id` e `nome`) e `exposicoes` (ativas e pausadas) | Administrador |
| `PUT /exposicoes/{sala_id}` | Publica ou edita a exposição da sala e retorna o registro salvo | Administrador |
| `PUT /exposicoes/{sala_id}/status` | Recebe `{"pausada": true}` para pausar ou `{"pausada": false}` para reativar | Administrador |
| `GET /visitas/formulario` | Retorna a configuração publicada em `{"campos": [...]}` | Público |
| `PUT /visitas/formulario` | Substitui a lista de perguntas e retorna a configuração salva | Administrador |

Os IDs do editor são `1 = Sala expositiva 1`, `2 = Sala expositiva 2`, `3 = Corredor` e `4 = Varanda`. Cada sala tem uma exposição. O primeiro PUT publica o conteúdo por padrão. O JSON recebe `nome` (até 120 caracteres), `descricao` (até 500, opcional) e `classificacao` (até 40, opcional). A resposta inclui também `sala_id` e `pausada`. Se `pausada` for omitido em uma edição, o status atual é preservado. É possível enviar `pausada` junto com os demais dados para salvar conteúdo e status em uma única operação. Uma sala desconhecida ou uma alteração de status em sala vazia retorna `404`.

O formulário preserva a ordem de `campos` e de `opcoes`. Cada campo tem `id` único e `titulo`. Os demais atributos são `dica`, `opcoes` e as flags `opcional`, `complementar`, `multipla`, `outro` e `email`. Com `opcoes`, o campo é de seleção, com ou sem múltipla escolha. Sem `opcoes`, é de texto. Antes do primeiro salvamento, a API fornece as perguntas padrão do editor. Enviar `{"campos": []}` publica um formulário vazio. A configuração descreve as perguntas exibidas, e o envio das solicitações continua usando o contrato de `POST /visitas/`.

As tabelas são criadas na inicialização da API. Os dados de protótipo já salvos no navegador podem ser enviados pelos PUTs correspondentes. As novas rotas administrativas exigem token Bearer com o papel de realm `administrador` no claim `realm_access.roles`. O arquivo de importação do Keycloak inclui o papel e seu vínculo com o client da API. Em um realm existente, crie o papel, adicione-o ao escopo do client e atribua-o aos usuários responsáveis. Esses usuários devem entrar novamente para obter um token com o papel.

## Relatório administrativo em PDF

`GET /relatorios/agendamentos?tipo=ambos&data_inicio=2026-11-01&data_fim=2026-11-30`

Envie `Authorization: Bearer <access_token>` com o papel `administrador`. O parâmetro `tipo` aceita `eventos`, `visitas` ou `ambos`. O período inclui os dois dias informados e usa a data de início de cada agendamento, no horário de Fortaleza. Datas inválidas, campos obrigatórios ausentes ou a data final anterior à inicial retornam `422`.

A resposta contém `application/pdf` e o nome sugerido para download em `Content-Disposition`. Períodos sem agendamentos também retornam um PDF. O relatório informa os totais de confirmados e de pendentes. Os gráficos mostram o percentual de confirmados por dia da semana, hora de início e, nos eventos, por pauta. O ranking apresenta até cinco eventos com maior público estimado, pois o sistema registra previsões de público. Para visitas, o PDF mostra pessoas previstas, grupos com pessoas com deficiência e a distribuição por natureza da instituição.

## Disponibilidade

| Rota pública | Agenda consultada |
| --- | --- |
| `GET /disponibilidade?espaco_id=1&data=2026-11-20` | Eventos do espaço escolhido |
| `GET /visitas/disponibilidade?data=2026-11-20` | Visitas mediadas |

As consultas retornam `horarios_reservaveis` e `bloqueios`, ambos com intervalos no formato `{"data_inicio": "...", "data_fim": "..."}`, em horário local de Fortaleza. Os bloqueios incluem solicitações pendentes e agendamentos confirmados. A API recorta os bloqueios à data consultada, consolida intervalos sobrepostos ou contíguos e retorna apenas seus horários.

As janelas públicas vão das 8h às 12h e das 13h30 às 18h. Para a Área Externa (`espaco_id=5`), o turno é das 18h às 21h. Cada janela indica um intervalo livre dentro do qual o usuário pode escolher início e fim. Para espaços, a consulta omite janelas com menos de duas horas e informa os limites de duração de duas a três horas para a seleção no calendário.

## Conflitos na gravação

Criação e alteração recusam períodos que se sobrepõem a outro evento no mesmo espaço, retornando `409` com `detail` explicando o conflito. Eventos em espaços diferentes podem ocorrer simultaneamente. Por exemplo, se existe um evento das 14h às 16h, outro no mesmo espaço das 15h às 17h é recusado; um evento a partir das 16h é permitido. Na alteração, o próprio evento é desconsiderado na verificação.

O fim deve ser posterior ao início; períodos inválidos retornam `422`. Datas sem fuso representam o horário de Fortaleza; datas com offset são convertidas para esse horário antes de salvar e comparar. A API usa um [lock transacional do PostgreSQL](https://www.postgresql.org/docs/17/explicit-locking.html) para serializar a verificação e a gravação e impedir reservas simultâneas conflitantes. Eventos que já estavam cadastrados são preservados.

O cadastro de uma visita retorna `409` se o horário se sobrepuser a outra visita pendente ou aprovada. Horários consecutivos são permitidos e visitas podem ocorrer durante eventos. A gravação de visitas usa a mesma proteção transacional na sua própria agenda.

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

- **Disponibilidade:** duração de visitas e regras para reservas que ocupem toda a Casa.
- **Espaços:** catálogo, imagens e fonte dos metadados, preservando o escopo sem cadastro administrativo próprio de espaços.
- **Publicação:** como atividades confirmadas entram na programação pública.
- **Notificação:** retorno manual ou e-mail automático (RF19).
- **Visitas sem agendamento:** aplicação da exceção para grupos pequenos (RNG02).

A confirmação é sempre manual (RNG01), não há cobrança (RNG03), e 48 horas é um prazo de referência para retorno (RNG04). O RF20 é atendido pela rota de relatório administrativo em PDF. Essas definições pendentes não impedem a organização das pastas, mas devem orientar a implementação das respectivas funcionalidades.

Referências técnicas: [organização com APIRouter e dependências](https://fastapi.tiangolo.com/tutorial/bigger-applications/), [schemas de resposta no FastAPI](https://fastapi.tiangolo.com/tutorial/response-model/) e [OpenID Connect no Keycloak](https://www.keycloak.org/securing-apps/oidc-layers).


## Frontend e CORS

O frontend chama esta API diretamente, sem proxy. As origens locais padrão são
`http://127.0.0.1:3000` e `http://localhost:3000`. Para outra porta, Live Server ou
WordPress, configure `CORS_ORIGINS` no `.env` e reinicie a API:

```dotenv
CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000,https://seusite.com.br
```

Use apenas origens (protocolo, domínio e porta, sem caminho). O middleware permite
`GET`, `POST`, `PUT`, `PATCH` e `DELETE`, com os cabeçalhos `Authorization` e `Content-Type`,
e responde ao preflight OPTIONS. A autenticação por Bearer continua obrigatória
nas rotas protegidas; cookies do WordPress não são utilizados.
