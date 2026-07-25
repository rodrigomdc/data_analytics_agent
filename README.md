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
    
*   **Supervisor Node (Orquestrador):** Se o input for válido, o Supervisor avalia o pedido do usuário e o esquema do banco, decidindo se o fluxo deve passar para a análise de dados (analyze) ou ir direto para a síntese conversacional (synthesize).
    
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

O componente de upload de arquivos (file\_uploader) funciona como uma "zona de drop" temporária. Ao arrastar um novo ZIP, o sistema executa a carga, funde o dicionário de dados de forma cumulativa com o existente (usando .update()), registra o nome do arquivo em um conjunto de bases ativas e limpa o uploader imediatamente da tela utilizando o padrão de **Chaves Dinâmicas** do Streamlit. Isso evita o bug clássico de inconsistência ao tentar remover arquivos manualmente.

### 2\. Tratamento de Encodings e Delimitadores Nacionais

Para contornar as limitações do leitor padrão de CSV do DuckDB (que falha ao ler arquivos não-UTF-8 ou com delimitadores ;), a ingestão foi reescrita utilizando o **Pandas como ponte de memória**.O sistema executa uma varredura utilizando o **csv.Sniffer nativo do Python** para descobrir estatisticamente o separador e o encoding corretos. Em seguida, o Pandas lê o arquivo físico e o registra na memória do DuckDB utilizando o mecanismo **Zero-Copy (conn.register)**, o que garante uma carga instantânea e 100% imune a falhas de decodificação.

### 3\. Sanitização Radical de Cabeçalhos contra Espaços Ocultos e Unicode Normalization (NFC/NFD)

Os arquivos CSV frequentemente contêm caracteres invisíveis (_Non-Breaking Space_ - \\xa0) ou acentuações salvas em formato decomposto (NFD). O sistema trata isso aplicando normalização unicode **NFC** e limpando todos os espaçamentos especiais nos nomes das colunas e das tabelas físicas salvos no DuckDB. Isso garante compatibilidade total com as queries geradas pelo Gemini.

## 🚀 Como Executar o Projeto

### Pré-requisitos

*  Python 3.9 ou superior.
    
*  Variável de ambiente com a chave de API do Gemini configurada: GOOGLE\_API\_KEY.
    

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
Crie um arquivo .env na raiz do projeto ou configure nas variáveis de ambiente do seu sistema operacional:
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