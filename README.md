# Interface Inteligente para Consulta de Arquivos CSV 

Bem-vindo ao repositório do projeto da equipe GenAI Lab! Este projeto faz parte da Atividade Obrigatória 4 do curso InsurMinds (I2A2).

**Equipe:**

| Nome | E-mail |
|------|--------|
| Bruno Corrêa | correabruno321@gmail.com |
| Jhiovana Silva Ribeiro | jhiovanasilva11@gmail.com |
| Luis R G Pereira | luisrgpereira@gmail.com |
| Rodrigo Medeiros Costa | eng.rodrigomdc@gmail.com |
| Rodrigo Souza Aguiar | rodrigo_souza_aguiar@hotmail.com |

### Objetivo:

Construir uma plataforma inteligente e modular baseada em agentes cognitivos capazes de interpretar perguntas em linguagem natural, realizar consultas analíticas e gerar representações gráficas interativas a partir de bases de dados armazenadas em arquivos CSV.

A solução foi projetada sob os conceitos de **Clean Architecture (Arquitetura Limpa)** e **Orientação a Objetos (OOP)**, utilizando o **LangGraph** como motor de orquestração de estados, o **DuckDB** como banco de dados analítico de alta performance, e o **Google Gemini** como cérebro cognitivo dos agentes especialistas.

---

## 🛠️ Stack Tecnológica e Justificativa Analítica

Abaixo está a especificação técnica dos componentes principais do projeto:

| Componente | Tecnologia / Versão | Justificativa Analítica |
|---|---|---|
| **Framework de Agentes** | **LangGraph** `>= 0.2.0` | Permite construir workflows baseados em grafos de estados dirigidos cíclicos/acíclicos. Garante controle de estado rígido e previne loops infinitos de chamadas à LLM comuns em orquestradores tradicionais. |
| **Ecossistema de LLM** | **LangChain** `>= 0.1.0` | Proporciona integrações robustas para chamadas de modelos via `langchain-google-genai` e suporte comunitário (`langchain-community`). |
| **Modelo de Linguagem (LLM)** | **Google Gemini 3.5 Flash** (via `gemini-3-flash-preview`) | Cérebro analítico configurado globalmente no projeto. Modelo otimizado para baixíssima latência, excelente raciocínio lógico-matemático e suporte nativo a respostas em formato JSON estruturado estável. |
| **Interface de Usuário** | **Streamlit** `>= 1.30.0` | Viabiliza a renderização dinâmica de componentes visuais do dashboard e do chat interativo de forma rápida e orientada a objetos no Python. |
| **Banco de Dados Analítico** | **DuckDB** `>= 0.10.0` | Adotado como banco persistente OLAP (orientado a colunas) em vez de bancos tradicionais de linha. Processa agregações, ordenações e consultas analíticas de grande porte em milissegundos. |
| **Visualização de Dados** | **Plotly** `>= 5.18.0` | Utilizada pelo assistente para gerar gráficos vetoriais interativos e dinâmicos (Plotly Express) diretamente no navegador do usuário. |
| **Manipulação de Dados** | **Pandas** `>= 2.0.0` | Funciona como uma ponte de memória de alta velocidade entre arquivos descompactados e a importação no DuckDB, permitindo pré-processamentos e formatações locais eficientes. |
| **Observabilidade** | **LangSmith** | Permite o rastreio (tracing) completo de execuções de nós, consumo de tokens e comportamento detalhado dos prompts e do LLM. |

---

## 🏗️ Arquitetura e Fluxo do Grafo de Estados

O sistema adota o padrão de arquitetura **Supervisor-Worker (Hierárquico)** operando em um grafo de estados direcionado e cíclico gerenciado pelo LangGraph.

```text
                     [ Usuário (Chat Input) ]
                               │
                               ▼
               ┌───────────────────────────────┐
               │    Validador Determinístico   │ (Local/Zero Tokens)
               └───────────────┬───────────────┘
                               │
                Se Inválido    │    Se Válido
         ┌─────────────────────┴─────────────────────┐
         ▼                                           ▼
┌──────────────────┐                       ┌──────────────────┐
│   Synthesizer    │◄──────────────────────│    Supervisor    │ (Orquestrador)
│  (Orientação)    │                       └────────┬─────────┘
└────────┬─────────┘                                │
         │                                          ▼
         │                                 ┌──────────────────┐
         │                                 │  Analyst Node    │ (Gera SQL)
         │                                 └────────┬─────────┘
         │                                          │
         │                            Com Gráfico   │   Sem Gráfico
         │                         ┌────────────────┴────────────────┐
         │                         ▼                                 ▼
         │               ┌──────────────────┐              ┌──────────────────┐
         │               │    Chart Node    │─────────────►│   Synthesizer    │
         │               └──────────────────┘              │  (Análise Real)  │
         │                                                 └────────┬─────────┘
         │                                                          │
         └─────────────────────────┬────────────────────────────────┘
                                   ▼
                        [ Resposta ao Usuário ]
```

### Detalhamento do Fluxo de Execução

*   **Validação Local de Entrada (Filtro de Segurança):** Antes de iniciar o grafo ou gastar tokens com chamadas ao modelo, o sistema roda uma validação determinística na query (tamanho menor que 3 caracteres, ausência de palavras legíveis ou falta de palavras do vocabulário físico do esquema). Em caso de falha, responde imediatamente orientando o usuário.
*   **Roteamento por Cache Local:** Se a mesma pergunta exata em linguagem natural for feita novamente na sessão, o sistema recupera a query SQL e a explicação salvas no cache interno. O banco é reconsultado e o gráfico Plotly é remontado sem fazer chamadas à API do Gemini (0 tokens gastos e latência quase nula).
*   **Supervisor Node (Orquestrador):** Se houver um cache miss, o Supervisor avalia o pedido e o dicionário de dados para decidir a rota: análise quantitativa (`analyze`) ou síntese direta (`synthesize`) para mensagens conceituais ou informais.
*   **Analyst Node (Consultas Analíticas):** Escreve queries SQL DuckDB limpas (sem blocos markdown). Uma ferramenta de execução executa a query e valida previamente os comandos contra manipulações destrutivas de dados (bloqueio de `DROP`, `DELETE`, `UPDATE`, etc.). Para evitar erros de limites de chamadas (Rate Limit / Erro 429), este nó adota um delay preventivo automático de `1.2` segundos.
*   **Roteador Secundário de Gráficos (Chart Node):** Após a execução da consulta SQL pelo Analista, o sistema verifica a presença de palavras-chave associadas a gráficos (`"gráfico"`, `"plot"`, `"barras"`, etc.). Se detectado, aciona de forma autônoma o **Chart Node**, que define o melhor tipo de gráfico e parâmetros, executando a ferramenta `create_chart_tool` para construir a figura interativa Plotly.
*   **Synthesizer Node (Análise de Negócios):** Consome a tabela em formato Markdown com os dados obtidos e o dicionário de dados associado para construir uma narrativa analítica em português sob medida para usuários corporativos, ocultando jargões de programação ou de infraestrutura de banco de dados.

---

## 📁 Estrutura de Pastas e Arquivos do Projeto

```text
data_analytics_agent/
│
├── database/                  # Armazena o banco físico persistente do DuckDB (data.duckdb)
├── extracted/                 # Rascunho físico para descompactação dos CSVs do ZIP
├── uploads/                   # Armazenamento temporário do arquivo payload.zip enviado
├── config.py                  # Configurações globais (diretórios, chaves de API e modelo LLM)
├── main.py                    # Inicializador (Bootstrapper) da aplicação Streamlit
│
└── src/                       # Pacote principal de código-fonte
    ├── agents/
    │   └── agents_nodes.py    # Métodos de instância dos nós dos agentes (GraphNodes)
    │
    ├── app/
    │   └── app.py             # Interface Gráfica Orientada a Objetos (StreamlitApp)
    │
    ├── db_manager/
    │   └── duckdb_manager.py  # Gerenciador de conexões e transações do DuckDB
    │
    ├── graph/
    │   ├── builder.py         # Compilador e estruturador do StateGraph do LangGraph
    │   └── orchestrator.py    # Ponto de entrada de inicialização e execução do grafo
    │
    ├── memory/
    │   └── conversation.py    # Gerenciador estruturado de histórico de chat na sessão
    │
    ├── models/
    │   └── state_model.py     # Schema rígido do estado compartilhado (AgentState)
    │
    ├── prompts/
    │   └── prompts.py         # Armazena todos os System Prompts dos nós especialistas
    │
    ├── services/
    │   ├── analysis_service.py   # Análise preliminar das tabelas e geração de estatísticas por coluna
    │   ├── csv_service.py        # Validador de cabeçalhos e carregador físico do DuckDB via Pandas
    │   ├── data_dict_service.py  # Parser dinâmico de dicionário de dados CSV em dicionário Python
    │   ├── ingestion_service.py  # Orquestrador lógico do pipeline de dados (ETL)
    │   ├── query_service.py      # Serviço de validação local, controle de cache e execução de perguntas
    │   └── zip_service.py        # Serviço utilitário de extração física de arquivos ZIP
    │
    ├── tools/
    │   └── tools.py           # Ferramentas técnicas de uso do grafo (consultas e gráficos)
    │
    └── utils/
        └── utils.py           # Funções utilitárias de logging, sanitização e limpeza de arquivos
```

### 📁 Guia de Diretórios, Arquivos e Funcionamento Técnico

Este tópico descreve detalhadamente o papel de cada pasta e arquivo do repositório, demonstrando como eles se integram de forma complementar para construir o fluxo de análise inteligente:

1\. **Diretórios de Armazenamento e Estado (Raiz do Projeto)**

Estas pastas residem na raiz do projeto e gerenciam a persistência e o isolamento físico de arquivos durante a execução:

*   **`database/`**: Armazena o arquivo de banco de dados físico ativo do DuckDB (`data.duckdb`). Como o banco é persistido localmente e não apenas em memória, essa pasta permite a carga cumulativa de múltiplos uploads ao longo de uma sessão.
*   **`uploads/`**: Funciona como diretório de retenção temporária do arquivo compactado `payload.zip` enviado ativamente pelo usuário.
*   **`extracted/`**: Diretório de rascunho de disco. É o local físico onde os arquivos CSV e dicionários de dados são descompactados pelo sistema para sofrerem os processos de validação e leitura estruturada antes de serem inseridos no banco de dados.

2\. **Pacote Principal do Código-Fonte (`src/`)**

👤 **`src/agents/`** **(Camada Cognitiva)**

Responsável pelas decisões lógicas baseadas em IA que dependem das chamadas de API do Gemini.

* **`agents_nodes.py`**: Contém a classe `GraphNodes`. Centraliza os métodos de instância dos nós do grafo (`supervisor_node`, `analyst_node`, `chart_node`, `synthesis_node`). Cada nó possui uma persona própria de IA e regras específicas de processamento que lêem o estado do grafo e o atualizam.

🖥️ **`src/app/`** **(Camada de Apresentação / View)**

Gerencia a interface gráfica interativa do usuário.

* **`app.py`**: Contém a classe principal `StreamlitApp`. Ela renderiza o cabeçalho, a barra lateral de uploads cumulativos e redefinições (Interface A) e a interface de abas para chat analítico, visualização de dicionários e estatísticas descritivas (Interface B). É o único arquivo que interage com o Streamlit.

🗄️ **`src/db_manager/`** **(Infraestrutura de Banco de Dados)**

Camada isolada responsável por gerenciar a comunicação de leitura/escrita física.

* **`duckdb_manager.py`**: Contém a classe `DuckDBManager`. Estabelece conexões com o arquivo do DuckDB, executa queries SQL analíticas e lê os metadados do banco (`PRAGMA table_info`) para fornecer a estrutura exata do banco de dados (schema) para os agentes.

🕸️ **`src/graph/`** **(Orquestração e Topologia)**

Responsável por montar o grafo e definir o fluxo lógico da informação.

* **`builder.py`**: Contém a classe `WorkflowGraphBuilder`. Define os nós do grafo utilizando os métodos de instância de `GraphNodes`, conecta as arestas lógicas sequenciais e define as arestas condicionais (routers), compilando a topologia final do grafo de estados de forma robusta.
* **`orchestrator.py`**: Ponto de inicialização e execução do grafo de estados a partir do LangGraph.

💾 **`src/memory/`** **(Gerenciador de Estado do Chat)**

* **`conversation.py`**: Classe `ConversationMemory`. Gerencia e persiste a lista de mensagens trocadas no chat do Streamlit. Salva de forma estruturada as explicações do assistente associando-as às suas tabelas e gráficos específicos correspondentes para que o histórico seja redesenhado corretamente na tela.

📊 **`src/models/`** **(Modelos e Contratos de Dados)**

* **`state_model.py`**: Define a classe `AgentState` baseada em `TypedDict`. Esse modelo é o contrato de dados oficial do sistema. Ele define de forma rígida quais variáveis (query do usuário, schema do banco, queries SQL, DataFrames Pandas, figuras do Plotly, explicações de negócios e logs de execução) trafegam ao longo do grafo.

📝 **`src/prompts/`** **(Central de Instruções de IA)**

* **`prompts.py`**: Isola todos os templates de instruções textuais dos agentes de IA do código Python lógico do sistema. Armazena as diretrizes e regras rígidas aplicadas ao Supervisor, Analista SQL, Criador de Gráficos e Síntese analítica.

⚙️ **`src/services/`** **(Serviços Determinísticos)**

Camada de serviços clássicos de programação que **não** necessitam de IA cognitiva para operar.

* **`analysis_service.py`**: Contém o `PreliminaryAnalysisService` que gera amostras de dados e perfis descritivos inteligentes por coluna baseados em regras e tipos de dados estatísticos (numéricas, monetárias, categóricas, etc.).
* **`csv_service.py`**: Contém a lógica de tratamento de dados analíticos. Descobre estatisticamente o separador e o encoding corretos de arquivos usando o `csv.Sniffer` nativo. Lê arquivos via Pandas corrigindo decodificações e formatos decimais (vírgula brasileira para ponto) e os insere no DuckDB.
* **`data_dict_service.py`**: Mapeia e traduz o dicionário de dados CSV enviado no ZIP de forma totalmente dinâmica, gerando o suporte conceitual às colunas para os prompts das LLMs.
* **`ingestion_service.py`**: Orquestrador lógico do pipeline de ETL de dados (extração de arquivos ZIP, parsing do dicionário e carga física das tabelas no DuckDB).
* **`query_service.py`**: Coordena o recebimento das perguntas, faz validações de entrada preventivas locais, gerencia o cache e dispara a execução do grafo de agentes do LangGraph, retornando os estados atualizados.
* **`zip_service.py`**: Descompacta fisicamente os arquivos ZIP na pasta temporária.

🧰 **`src/tools/`** **(Ações Práticas dos Agentes)**

* **`tools.py`**: Contém as ferramentas executáveis pelo LangGraph: consulta segura ao DuckDB (`query_duckdb_tool`) e plotador interativo de gráficos (`create_chart_tool`).

🛠️ **`src/utils/`** **(Utilitários Globais do Sistema)**

* **`utils.py`**: Centraliza funções utilitárias do sistema como inicializador de logger, normalizador de strings unicode NFC/NFD, higienizadores de nomes de tabelas/colunas para `snake_case` ASCII e o reset físico de armazenamento do disco.

---

## ⚙️ Diferenciais de Engenharia de Dados Aplicados no Projeto

### 1. Ingestão Cumulativa com "Absorção" na UI
O componente de upload de arquivos (`file_uploader`) funciona como uma "zona de drop" temporária. Ao arrastar um novo ZIP, o sistema executa a carga, funde o dicionário de dados de forma cumulativa com o existente (usando `.update()`), registra o nome do arquivo em um conjunto de bases ativas e limpa o uploader imediatamente da tela utilizando o padrão de **Chaves Dinâmicas** do Streamlit. Isso evita o bug clássico de inconsistência ao tentar remover arquivos manualmente.

### 2. Tratamento de Encodings e Delimitadores Nacionais
Para contornar as limitações do leitor padrão de CSV do DuckDB (que falha ao ler arquivos não-UTF-8 ou com delimitadores `;`), a ingestão foi reescrita utilizando o **Pandas como ponte de memória**. O sistema executa uma varredura utilizando o **csv.Sniffer nativo do Python** para descobrir estatisticamente o separador e o encoding corretos. Em seguida, o Pandas lê o arquivo físico e o registra na memória do DuckDB utilizando o mecanismo **Zero-Copy (`conn.register`)**, o que garante uma carga instantânea e 100% imune a falhas de decodificação.

### 3. Sanitização Radical de Cabeçalhos contra Espaços Ocultos e Unicode Normalization (NFC/NFD)
Os arquivos CSV frequentemente contêm caracteres invisíveis (*Non-Breaking Space* - `\xa0`) ou acentuações salvas em formato decomposto (NFD). O sistema trata isso aplicando normalização unicode **NFC** e limpando todos os espaçamentos especiais nos nomes das colunas e das tabelas físicas salvos no DuckDB. Isso garante compatibilidade total com as queries geradas pelo Gemini.

### 4. Análise Preliminar Dinâmica por Tipo de Dados (ColumnProfiler)
O sistema analisa dinamicamente cada tabela carregada classificando colunas em tipos analíticos específicos (`numerica`, `monetaria`, `categorica`, `data`, `identificador`, `texto_livre`). Com base na classificação, estatísticas descritivas estruturadas são apresentadas automaticamente na interface Streamlit (médias/mediana de valores, evolução temporal agregada por trimestre, ocorrência percentual de dados categóricos e identificadores protegidos contra agregações), gerando insights instantâneos sem consumo de tokens da API de IA.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos

*  Python 3.9 ou superior.
*  Variável de ambiente com a chave de API do Gemini configurada: `GOOGLE_API_KEY`.

### Instalação

1.  **Clone o repositório:**

```bash
git clone https://github.com/rodrigomdc/data_analytics_agent.git
cd data_analytics_agent
```

2. **Crie e ative um ambiente virtual:**

```bash
python -m venv .venv
# No Linux/macOS:
source .venv/bin/activate  
# No Windows:
.venv\Scripts\activate
```

3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

4. **Configure sua Chave de API:**
Crie um arquivo `.env` na raiz do projeto ou configure nas variáveis de ambiente do seu sistema operacional:
```bash
GOOGLE_API_KEY="sua_chave_api_gemini_aqui"
```

5. **Inicie a aplicação:**

```bash
streamlit run main.py
```

---

## 💡 Como Usar

*   **Interface A (Carga e Perfil):** Faça o upload de um arquivo ZIP contendo um ou mais arquivos CSV e o seu dicionário de dados de formato CSV. O sistema fará a leitura e listará na barra lateral as bases que estão ativas na memória. Você pode adicionar mais arquivos de forma cumulativa. Além disso, as abas centrais de **Metadados** e **Perfil dos Dados** mostram o dicionário decodificado e a análise estatística preliminar gerada pelo sistema.
*   **Interface B (Consulta / Chat):** No console da aba principal de **Chat com Agente**, digite sua dúvida comercial em linguagem natural. O orquestrador gerenciará as chamadas dos subagentes e retornará a resposta explicativa acompanhada do gráfico e das tabelas brutas correspondentes.
*   **Iniciar Nova Análise:** Clique no botão "🧹 Iniciar Nova Análise" na barra lateral para apagar fisicamente todos os arquivos temporários, destruir as instâncias do banco DuckDB locais do disco, limpar o histórico de conversas do chat e retornar a interface ao estado inicial de carregamento limpo.