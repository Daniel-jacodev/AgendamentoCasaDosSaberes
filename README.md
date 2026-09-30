# Backend — Agendamento Casa de Saberes

API para consultar a programação da Casa de Saberes, apresentar horários disponíveis e receber solicitações de **visita mediada** ou **uso de espaço**. A equipe administrativa consulta os pedidos e decide manualmente pela aprovação ou recusa. A referência funcional é o [documento de requisitos](Documentação/Requisitos%20-%20Sistema%20de%20Agendamento%20Casa%20de%20Saberes.pdf).

Este repositório é dedicado ao **backend em Python, FastAPI e Pydantic**. A autenticação será feita pelo **Keycloak**. O frontend será um **WordPress separado**, responsável pelas páginas, formulários, calendários e acessibilidade.

## Estado atual

Há apenas o esqueleto de pastas e esta documentação. Os arquivos `__init__.py` identificam os pacotes Python. Aplicação FastAPI, endpoints, integração com Keycloak, dependências e banco de dados ainda serão implementados.

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
├── database/
│   └── migrations/           # Evolução versionada do esquema do banco
└── storage/
    └── private/              # Portfólios PDF opcionais; arquivos não versionados
```

Cada pasta de `app/` é um pacote Python. Quando a aplicação for implementada, `app/main.py` deverá criar a instância FastAPI, registrar os routers e configurar CORS e o tratamento de erros. O banco e a biblioteca de persistência ainda precisam ser escolhidos; PostgreSQL é uma opção para os dados relacionais e as transações de agendamento.

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
