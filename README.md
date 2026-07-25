# Interface Inteligente para Consulta de Arquivos CSV 

Bem-vindo ao repositório do projeto da equipe GenAI Lab! Este projeto faz parte da Atividade Obrigatória 4  do curso InsurMinds (I2A2).

**Equipe:**

| Nome | E-mail |
|------|--------|
| Bruno Corrêa | correabruno321@gmail.com |
| Jhiovana Silva Ribeiro | jhiovanasilva11@gmail.com |
| Luis R G Pereira | luisrgpereira@gmail.com |
| Rodrigo Medeiros Costa | eng.rodrigomdc@gmail.com |
| Rodrigo Souza Aguiar | rodrigo_souza_aguiar@hotmail.com |

### Objetivo:

Contruir uma plataforma inteligente e modular baseada em agentes cognitivos capazes de interpretar perguntas em linguagem natural, realizar consultas analíticas e gerar representações gráficas interativas a partir de bases de dados armazenadas em arquivos CSV.

A solução foi projetada sob os conceitos de **Clean Architecture (Arquitetura Limpa)** e **Orientação a Objetos (OOP)**, utilizando o **LangGraph** como motor de orquestração de estados, o **DuckDB** como banco de dados analítico de alta performance, e o **Google Gemini** como cérebro cognitivo dos agentes especialistas.

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

*   **Validação Local de Entrada (Filtro de Segurança):** Antes de iniciar o grafo de estados ou consumir qualquer token da API do Gemini, o sistema executa uma validação determinística de segurança. Se a pergunta for considerada fora do contexto (como sequências de letras aleatórias), o sistema retorna de imediato um estado de orientação amigável impresso no balão de chat do assistente.
    
*   **Supervisor Node (Orquestrador):** Se o input for válido, o Supervisor avalia o pedido do usuário e o esquema do banco, decidindo se o fluxo deve passar para a análise de dados (`analyze`) ou ir direto para a síntese conversacional (`synthesize`).
    
*   **Analyst Node (Consultas Analíticas):** Formula e executa queries SQL otimizadas diretamente na base de dados do DuckDB, estruturando o resultado em um DataFrame do Pandas.
    
*   **Chart Node (Visualização Estética):** Caso o usuário tenha solicitado uma representação gráfica (detectado de forma autônoma pela aresta de saída do Analista), este nó é acionado. Ele escolhe os eixos e o tipo de gráfico ideal (barras, linhas, pizza, dispersão), gerando uma figura interativa do Plotly Express.
    
*   **Synthesizer Node (Análise de Negócios):** Conecta a tabela Markdown de resultados, a explicação técnica e o dicionário de dados para gerar uma resposta final de negócios polida, sem jargões ou termos técnicos.

---

## 📁 Estrutura de Pastas e Arquivos do Projeto
```text
data-analyst-agent/
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
    │   ├── csv_service.py     # Validador de cabeçalhos e carregador físico do DuckDB via Pandas
    │   ├── data_dict_service.py # Parser dinâmico de dicionário JSON via csv.DictReader
    │   ├── ingestion_service.py # Orquestrador lógico do pipeline de dados (ETL)
    │   └── zip_service.py     # Serviço utilitário de extração física de arquivos ZIP
    │
    ├── tools/
    │   └── tools.py           # Ferramentas técnicas de uso do grafo (consultas e gráficos)
    │
    └── utils/
        └── utils.py           # Funções utilitárias de logging, sanitização e limpeza de arquivos
```

### 📁 Guia de Diretórios, Arquivos e Funcionamento Técnico

Este tópico descreve detalhadamente o papel de cada pasta e arquivo do repositório, demonstrando como eles se integram de forma complementar para construir o fluxo de análise inteligente:

1. **Diretórios de Armazenamento e Estado (Raiz do Projeto)**

Estas pastas residem na raiz do projeto e gerenciam a persistência e o isolamento físico de arquivos durante a execução:

*   `database/`: Armazena o arquivo de banco de dados físico ativo do DuckDB (`data.duckdb`). Como o banco é persistido localmente e não apenas em memória, essa pasta permite a carga cumulativa de múltiplos uploads ao longo de uma sessão.

*   `uploads/`: Funciona como diretório de retenção temporária do arquivo compactado `payload.zip` enviado ativamente pelo usuário.

*   `extracted/`: Diretório de rascunho de disco. É o local físico onde os arquivos CSV e dicionários de dados são descompactados pelo sistema para sofrerem os processos de validação e leitura estruturada antes de serem inseridos no banco de dados.

2. **Pacote Principal do Código-Fonte (`src/`)**

👤 `src/agents/` **(Camada Cognitiva)**

Responsável pelas decisões lógicas baseadas em IA que dependem das chamadas de API do Gemini.

* `agents_nodes.py`: Contém a classe GraphNodes. Centraliza os métodos de instância dos nós do grafo (`supervisor_node`, `analyst_node`, `chart_node`, `synthesis_node`). Cada nó possui uma persona própria de IA e regras específicas de processamento que lêem o estado do grafo e o atualizam.

🖥️ `src/app/` **(Camada de Apresentação / View)**

Gerencia a interface gráfica interativa do usuário.

* `app.py`: Contém a classe principal StreamlitApp. Ela renderiza o cabeçalho, a barra lateral de uploads cumulativos (Interface A) e a interface de chat de consultas (Interface B). É o único arquivo que interage com o Streamlit, consumindo os dicionários de dados gerados pelos serviços e os estados finais entregues pelo Orquestrador do Grafo.

🗄️ `src/db_manager/` **(Infraestrutura de Banco de Dados)**

Camada isolada responsável por gerenciar a comunicação de leitura/escrita física.

* `duckdb_manager.py`: Contém a classe `DuckDBManager`. Estabelece conexões com o arquivo do DuckDB, executa queries SQL analíticas e lê os metadados do banco (`PRAGMA table_info`) para fornecer a estrutura exata do banco de dados (schema) para os agentes.

🕸️ `src/graph/` **(Orquestração e Topologia)**

Responsável por montar o grafo e definir o fluxo lógico da informação.

* `builder.py`: Contém a classe WorkflowGraphBuilder. Define os nós do grafo utilizando os métodos de instância de `GraphNodes`, conecta as arestas lógicas sequenciais e define as arestas condicionais (routers), compilando a topologia final do grafo de estados de forma robusta.

* `orchestrator.py`: É o ponto de entrada da lógica de inteligência artificial. Contém a função `run_orchestrator_graph()`, que recebe as perguntas do usuário, realiza a validação semântica de segurança, monta o estado inicial de dados (`AgentState`) e dispara a execução do grafo de forma síncrona, retornando os resultados finais.

💾 `src/memory/` **(Gerenciador de Estado do Chat)**

* `conversation.py`: Classe `ConversationMemory`. Gerencia e persiste a lista de mensagens trocadas no chat do Streamlit. Salva de forma estruturada as explicações do assistente associando-as às suas tabelas e gráficos específicos correspondentes para que o histórico seja redesenhado corretamente na tela.

📊 `src/models/` **(Modelos e Contratos de Dados)**

* `state_model.py`: Define a classe `AgentState` baseada em `TypedDict`. Esse modelo é o contrato de dados oficial do sistema. Ele define de forma rígida quais variáveis (query do usuário, schema do banco, queries SQL, DataFrames Pandas, figuras do Plotly, explicações de negócios e logs de auditoria) trafegam de nó em nó ao longo do processamento do grafo.

📝 `src/prompts/` **(Central de Instruções de IA)**

* `prompts.py`: Isola todos os templates de instruções textuais dos agentes de IA do código Python lógico do sistema. Armazena as diretrizes e regras rígidas aplicadas ao Supervisor (incluindo a proibição absoluta de fazer cálculos manuais), o prompt do analista SQL, o do criador de gráficos e a síntese final do analista de negócios.

⚙️ `src/services/` **(Serviços Determinísticos)**

Camada de serviços clássicos de programação que não necessitam de IA cognitiva para operar.

* `zip_service.py`: Descompacta o arquivo payload.zip extraindo fisicamente os arquivos de dados na pasta `extracted/`.

* `csv_service.py`: Contém a lógica de tratamento de dados analíticos. Utiliza a função de varredura `_detect_csv_properties` para descobrir estatisticamente o separador e o encoding corretos do arquivo usando o `csv.Sniffer` nativo. Em seguida, lê os arquivos com Pandas (corrigindo formatações decimais brasileiras de vírgulas para pontos com decimal=",") e os grava nas tabelas físicas do DuckDB em memória sem perdas de decodificação.

* `data_dict_service.py`: Processa de forma determinística dicionários de dados salvos no formato CSV utilizando o `csv.DictReader`. Higieniza espaços em branco e extrai as N colunas extras de metadados para construir o dicionário de suporte do sistema.

* `ingestion_service.py`: Classe coordenadora do pipeline de ETL (Extração, Transformação e Carga). Aciona em lote os serviços de descompactação, parser de dicionário e gravação das tabelas no DuckDB.

🧰 `src/tools/` **(Ações Práticas dos Agentes)**

* `tools.py`: Biblioteca de ferramentas acionadas pelos nós do LangGraph. Contém a ferramenta de execução de queries SQL no DuckDB e o montador de gráficos interativos em Plotly Express (`create_chart_tool`), que padroniza os títulos e eixos com base nas melhores práticas de Data Viz.

🛠️ `src/utils/` **(Utilitários Globais do Sistema)**

* `utils.py`: Arquivo unificado que centraliza de forma limpa as funções utilitárias que atendem a várias camadas do sistema:

    1. `setup_logger`: Configura e padroniza o monitoramento de logs do console do servidor.

    2. `sanitize_table_name`: Higieniza nomes físicos de arquivos para chaves de tabelas compatíveis com SQL.

    3. `sanitize_column_name`: Normaliza e converte nomes de colunas complexas de arquivos CSV em identificadores amigáveis no padrão snake_case em ASCII puro.

    4. `validate_user_query`: Executa o algoritmo de validação determinística de perguntas com base em vocabulário dinâmico.

    5. `reset_application_storage`: Realiza a exclusão e o expurgo físico de segurança de arquivos e bancos temporários do disco.

---

## 🛠️ Tecnologias Utilizadas e Justificativa Analítica

*   **DuckDB:** Adotado como motor de persistência analítica (OLAP) em substituição ao SQLite. Sendo columnar, processa agregações e agrupamentos de forma imensamente mais veloz.
    
*   **LangGraph:** Utilizado para compilar o workflow de agentes. Fornece controle de estado unificado (AgentState) e previne loops infinitos de chamadas à LLM comuns em orquestradores tradicionais.
    
*   **Google Gemini (gemini-2.5-flash):** Modelo de última geração otimizado para baixíssima latência, excelente raciocínio lógico-matemático e suporte nativo à geração de estruturas JSON estáveis.
    
*   **Streamlit:** Framework de interface web que permite construir interfaces interativas rapidamente em Python.
    
*   **Plotly Express:** Biblioteca de visualização que gera gráficos dinâmicos altamente responsivos e personalizáveis na tela

---

## ⚙️ Diferenciais de Engenharia de Dados Aplicados no Projeto

### 1\. Ingestão Cumulativa com "Absorção" na UI

O componente de upload de arquivos (`file\_uploader`) funciona como uma "zona de drop" temporária. Ao arrastar um novo ZIP, o sistema executa a carga, funde o dicionário de dados de forma cumulativa com o existente (usando `.update()`), registra o nome do arquivo em um conjunto de bases ativas e limpa o uploader imediatamente da tela utilizando o padrão de **Chaves Dinâmicas** do Streamlit. Isso evita o bug clássico de inconsistência ao tentar remover arquivos manualmente.

### 2\. Tratamento de Encodings e Delimitadores Nacionais

Para contornar as limitações do leitor padrão de CSV do DuckDB (que falha ao ler arquivos não-UTF-8 ou com delimitadores ;), a ingestão foi reescrita utilizando o **Pandas como ponte de memória**.O sistema executa uma varredura utilizando o **csv.Sniffer nativo do Python** para descobrir estatisticamente o separador e o encoding corretos. Em seguida, o Pandas lê o arquivo físico e o registra na memória do DuckDB utilizando o mecanismo **Zero-Copy (`conn.register`)**, o que garante uma carga instantânea e 100% imune a falhas de decodificação.

### 3\. Sanitização Radical de Cabeçalhos contra Espaços Ocultos e Unicode Normalization (NFC/NFD)

Os arquivos CSV frequentemente contêm caracteres invisíveis (_Non-Breaking Space_ - `\\xa0`) ou acentuações salvas em formato decomposto (NFD). O sistema trata isso aplicando normalização unicode **NFC** e limpando todos os espaçamentos especiais nos nomes das colunas e das tabelas físicas salvos no DuckDB. Isso garante compatibilidade total com as queries geradas pelo Gemini.

## 🚀 Como Executar o Projeto

### Pré-requisitos

*  Python 3.9 ou superior.
    
*  Variável de ambiente com a chave de API do Gemini configurada: `GOOGLE\_API\_KEY`.
    

### Instalação

1.  **Clone o repositório:**

```bash
git clone https://github.com/seu-usuario/data-analyst-agent.git

cd data-analyst-agent
```

2. **Crie e ative um ambiente virtual:**

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
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

*   **Interface A (Carga):** Faça o upload de um arquivo ZIP contendo um ou mais arquivos CSV e o seu dicionário de dados de formato CSV. O sistema fará a leitura e listará na barra lateral as bases que estão ativas na memória. Você pode adicionar mais arquivos de forma cumulativa.
    
*   **Interface B (Consulta):** No console do chat, digite sua dúvida comercial em linguagem natural. O orquestrador gerenciará as chamadas dos subagentes e retornará a resposta explicativa acompanhada do gráfico e das tabelas brutas correspondentes.
    
*   **Iniciar Nova Análise:** Clique no botão de redefinição na barra lateral para apagar fisicamente todos os arquivos temporários, destruir as instâncias do banco DuckDB locais do disco, limpar o histórico de conversas do chat e retornar a interface ao estado inicial de carregamento limpo.