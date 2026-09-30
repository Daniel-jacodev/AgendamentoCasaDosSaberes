# Sistema de Agendamento — Casa de Saberes

Este projeto prevê uma API para consultar a programação da Casa de Saberes, mostrar a disponibilidade para agendamentos e receber pedidos de **visita mediada** ou **uso de espaço**. A equipe administrativa acessa uma área protegida para analisar cada pedido e decidir manualmente pela aprovação ou recusa. A referência funcional é o [documento de requisitos](Documentação/Requisitos%20-%20Sistema%20de%20Agendamento%20Casa%20de%20Saberes.pdf).

## Estado do projeto

Este repositório contém o documento de requisitos e o **esqueleto de pastas do backend**. Ainda não há aplicação, banco de dados, dependências ou endpoints implementados. A escolha de tecnologia abaixo é uma proposta para orientar a implementação, não uma dependência já instalada.

## Arquitetura proposta

Uma API REST em **Node.js + TypeScript + Express**, com **PostgreSQL** e consultas SQL parametrizadas pelo pacote `pg`, mantém poucas dependências e permite transações para proteger a decisão de agendamento. O frontend consome JSON; por isso, a camada *View* do MVC representa respostas JSON, sem páginas HTML no backend.

```text
projsocial/
├── Documentação/                         # Requisitos originais
├── README.md
└── backend/
    ├── src/
    │   ├── config/                       # Ambiente, conexão com banco e parâmetros operacionais
    │   ├── routes/                       # Rotas públicas e administrativas
    │   ├── controllers/                  # Entrada HTTP: parâmetros, chamada ao modelo/serviço, resposta
    │   ├── models/                       # Dados e acesso ao PostgreSQL
    │   ├── views/                        # Formatação das respostas JSON, inclusive erros
    │   ├── services/                     # Regras de disponibilidade e decisão manual
    │   └── middlewares/                  # Autenticação, validação e tratamento de erros
    ├── database/
    │   └── migrations/                   # Evolução versionada do esquema SQL
    └── storage/
        └── private/                      # PDFs opcionais; arquivos não versionados
```

### Responsabilidade de cada camada

`routes` associa URL e método ao controller. `controllers` recebe a requisição e coordena a resposta, sem conter SQL nem regras de conflito. `models` representa os dados e concentra as consultas parametrizadas. `views` define os campos públicos de saída e o formato de erro, evitando expor senhas ou dados internos. `services` só reúne operações que exigem regra de negócio ou transação, como calcular disponibilidade e aprovar solicitações. `middlewares` protege as rotas administrativas e valida entradas antes do controller. `config` centraliza parâmetros e conexão. As migrações mantêm a estrutura do banco reproduzível.

Fluxo principal: **rota → middleware → controller → model/service → view JSON**. Na aprovação, o serviço consulta conflitos de horário e espaço dentro de uma transação, mas a decisão continua sendo feita por uma pessoa da equipe (RF17, RNG01). Uma solicitação enviada permanece **pendente** até essa decisão; ela não ocupa automaticamente a programação pública.

### Domínio mínimo

| Entidade | Dados e finalidade |
| --- | --- |
| Administrador | Identidade, e-mail e hash da senha para acesso ao painel. |
| Solicitação | Tipo (`visita_mediada` ou `uso_espaco`), intervalo pedido, contato, proposta, referência ao espaço quando aplicável, status (`pendente`, `aprovada`, `recusada`) e registro da decisão. |
| Atividade publicada | Eventos confirmados que aparecem na programação pública; mantidos separadamente das solicitações e dos agendamentos internos. |

O espaço é uma **referência**, sem cadastro administrativo próprio neste escopo, conforme a definição do documento. Imagens e cores dos espaços (RF21/RF22) poderão vir de metadados estáticos ou de uma fonte externa; a escolha depende do catálogo ainda não levantado. A disponibilidade (RF03) deve ser calculada a partir das regras de funcionamento e das ocupações confirmadas, mantendo uma consulta distinta da programação pública (RF01/RF02).

| Requisitos | Lugar na arquitetura |
| --- | --- |
| RF01–RF03 | Consultas públicas de programação e disponibilidade, com respostas diferentes. |
| RF04–RF10 | Solicitações de visita ou espaço, contato e dados da proposta; portfólio em PDF opcional. |
| RF12–RF19 | Autenticação, análise, calendário interno, decisão manual e eventual notificação. |
| RF21–RF22 | Metadados dos espaços para imagens e cores na interface. |

### Superfície da API prevista

| Área | Operações previstas |
| --- | --- |
| Pública | Consultar programação; consultar disponibilidade e metadados dos espaços; criar solicitação de visita ou uso de espaço. |
| Administrativa | Iniciar/encerrar sessão; listar e detalhar solicitações; consultar agendamentos; aprovar ou recusar manualmente. |

Dados de contato (RF06) devem ser validados e acessíveis somente à equipe autorizada. Senhas devem usar hash adequado; sessões devem expirar (RNF07). O PDF de portfólio (RF10) é opcional: quando implementado, deve ficar em `storage/private`, com validação de tipo e tamanho e acesso autorizado. Não armazenar anexos nem dados pessoais no controle de versão. Não há cobrança (RNG03). Dashboard (RF20) está fora do escopo.

## Pontos a definir antes das respectivas funcionalidades

- **Disponibilidade:** horários de funcionamento, duração das visitas, antecedência e critérios de conflito entre visita, espaço e uso total da Casa ainda não estão especificados.
- **Espaços:** falta o catálogo e a fonte das imagens; a definição de espaço no documento exclui cadastro próprio no sistema. As cores consistentes são responsabilidade da interface, com identificadores estáveis fornecidos pela API.
- **Publicação:** o documento não define como atividades entram na programação pública. Aprovação de solicitação e publicação devem permanecer ações distintas até essa regra ser definida.
- **Notificação (RF19):** falta decidir se o retorno ao solicitante será manual ou por e-mail automático. O prazo de 48 horas é referência, não aprovação automática (RNG04).
- **Visitas sem agendamento (RNG02):** a exceção para grupos pequenos ainda depende de decisão operacional.

O próximo passo de implementação é definir essas regras com a Casa, criar o esquema SQL e implementar primeiro os requisitos essenciais. A interface, inclusive os dois calendários separados e a acessibilidade, pertence à camada de frontend.
# AgendamentoCasaDosSaberes
# AgendamentoCasaDosSaberes
# AgendamentoCasaDosSaberes
# AgendamentoCasaDosSaberes
