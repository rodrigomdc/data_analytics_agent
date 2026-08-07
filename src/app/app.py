# -*- coding: utf-8 -*-
"""Módulo de interface gráfica de usuário (UI) da plataforma.

Gerencia e renderiza os componentes visuais utilizando o Streamlit, encapsulando
as lógicas lógicas de apresentação das Interfaces A (Carga) e B (Consulta),
comunicando-se diretamente com as camadas de serviços e do grafo de estados.
"""

import os
import pandas as pd
import streamlit as st
from config import UPLOADS_DIR
from src.utils.utils import reset_application_storage
from src.services.ingestion_service import DataIngestionService
from src.services.analysis_service import PreliminaryAnalysisService
from src.graph.orchestrator import run_orchestrator_graph
from src.memory.conversation import ConversationMemory


class StreamlitApp:
    """Classe responsável por construir e coordenar a interface Streamlit.

    Encapsula o ciclo de vida da interface gráfica, o gerenciamento de estados
    de sessão, a renderização de componentes de upload cumulativo e a área
    de conversação inteligente de dados.
    """

    def __init__(self):
        """Inicializa a interface gráfica definindo as configurações da página.

        Define o título da página do navegador, o layout expandido (wide)
        e chama o inicializador do estado de sessão.
        """
        st.set_page_config(page_title="Analista IA Corporativo", layout="wide")
        self._init_session_state()

    def _init_session_state(self):
        """Inicializa e padroniza as variáveis de controle do Streamlit Session State.

        Garante que as chaves de controle lógico da aplicação existam em memória
        e persistam de forma previsível entre os recarregamentos (reruns) de tela.
        """
        # Define se a base de dados DuckDB está pronta para ser consultada
        if "db_ready" not in st.session_state:
            st.session_state.db_ready = False
            
        # Dicionário unificado de metadados das tabelas (inicia sempre como dict vazio)
        if "data_dict" not in st.session_state or not isinstance(st.session_state.data_dict, dict):
            st.session_state.data_dict = {}
            
        # Conjunto (set) contendo os nomes dos arquivos ZIP já processados na sessão
        if "loaded_zip_names" not in st.session_state:
            st.session_state.loaded_zip_names = set()

        # Conjunto (set) com os nomes de todas as tabelas físicas já carregadas no DuckDB. 
        # Fica desacoplado do data_dict para que a análise preliminar não dependa da existência de um dicionário de dados descritivo dentro do ZIP.
        if "loaded_tables" not in st.session_state:
            st.session_state.loaded_tables = set()
        
        # Chave dinâmica incremental para limpar fisicamente o campo de upload no reset
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "temp_charts" not in st.session_state:
            st.session_state.temp_charts = []
        
        if "last_dataframe" not in st.session_state:
            st.session_state.last_dataframe = None

        if "cached_profiles" not in st.session_state:
            st.session_state.cached_profiles = {}

    def render_header(self):
        """Renderiza o cabeçalho principal da página do painel web."""
        st.title("Interface Inteligente de Consulta e Visualização")

    def render_sidebar(self):
        """Interface A: Renderiza o painel lateral de controle e upload.

        Gerencia a área de drop de novos pacotes ZIP de forma cumulativa
        e exibe a lista de bases indexadas, além do botão de redefinição de dados.
        """
        st.sidebar.header("Interface A - Carga de Arquivos")
        
        # O uploader usa a uploader_key para se auto-limpar e virar uma 'zona de drop' temporária
        uploaded_zip = st.sidebar.file_uploader(
            "Arraste um ZIP para adicionar dados à análise",
            type=["zip"],
            max_upload_size=500,
            key=f"zip_uploader_{st.session_state.uploader_key}"
        )

        # Bloco de execução disparado assim que um novo ZIP é depositado no uploader
        if uploaded_zip is not None:
            # Garante que só processará se o arquivo ZIP for inédito na sessão ativa
            if uploaded_zip.name not in st.session_state.loaded_zip_names:
                with st.sidebar.status(f"Adicionando dados de {uploaded_zip.name}...") as status:
                    try:
                        # Define o caminho temporário de gravação do buffer físico
                        temp_zip_path = os.path.join(UPLOADS_DIR, "payload.zip")
                        with open(temp_zip_path, "wb") as f:
                            f.write(uploaded_zip.getbuffer())
                            
                        # Aciona o serviço coordenador de ETL (Descompactação, dicionário e DuckDB)
                        res = DataIngestionService.process_zip_payload(temp_zip_path)
                        
                        # Bloco de mesclagem cumulativa de Dicionários de Dados (Metadados)
                        new_dict = res["data_dict"]
                        if isinstance(new_dict, dict) and "mensagem" not in new_dict and "erro" not in new_dict:
                            # Se a base continha apenas um aviso de "sem dicionário", limpa antes de mesclar
                            if "mensagem" in st.session_state.data_dict:
                                st.session_state.data_dict = {}
                            # Adiciona os novos campos ao dicionário global cumulativo
                            st.session_state.data_dict.update(new_dict)
                        elif not st.session_state.data_dict or "mensagem" in st.session_state.data_dict:
                            # Se a base de metadados estiver vazia, armazena o aviso/erro temporário
                            st.session_state.data_dict = new_dict

                        # Acumula as tabelas físicas carregadas nesta ingestão, independente de haver dict descritivo no ZIP.
                        new_tables = res.get("loaded_tables", [])
                        st.session_state.loaded_tables.update(new_tables)

                        # Atualiza os estados lógicos de persistência da sessão
                        if len(st.session_state.loaded_tables) > 0:
                            st.session_state.db_ready = True
                            
                        st.session_state.loaded_zip_names.add(uploaded_zip.name)
                        
                        # Atualiza o status visual do processo para o usuário
                        status.update(
                            label=f"Dados de '{uploaded_zip.name}' integrados!", 
                            state="complete"
                        )
                        
                        # Incrementa a chave para recriar o uploader vazio na tela
                        st.session_state.uploader_key += 1
                        
                        # Recarrega a aplicação para atualizar instantaneamente o dicionário na tela
                        st.rerun()
                        
                    except Exception as e:
                        status.update(label="Falha na carga do dataset", state="error")
                        st.sidebar.error(f"Erro: {e}")

        # Se houver bases carregadas, exibe a lista de arquivos ativos e o botão de recomeçar
        if st.session_state.db_ready:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📦 Bases Ativas na Análise")

            # Lista estática dos arquivos indexados para evitar remoções acidentais e desalinhamento de estados
            for name in st.session_state.loaded_zip_names:
                st.sidebar.caption(f"✅ {name}")

            st.sidebar.markdown("---")

            # Botão de redefinição voltado para o usuário final de negócios
            restart = st.sidebar.button(
                "🧹 Iniciar Nova Análise",
                width="stretch",
                help="Clique aqui para apagar os arquivos carregados atualmente, limpar o histórico de conversas e começar do zero."
            )

            if restart:
                # Expurgar fisicamente todos os arquivos do disco (ZIP, CSVs e DuckDB)
                reset_application_storage()

                # Reseta todas as variáveis lógicas de estado da sessão de UI
                st.session_state.db_ready = False
                st.session_state.data_dict = {}
                st.session_state.loaded_zip_names = set()
                st.session_state.loaded_tables = set()
                st.session_state.messages = []
                st.session_state.temp_charts = []
                st.session_state.last_dataframe = None
                st.session_state.cached_profiles = {}
                st.session_state.uploader_key += 1

                # Reinicia a aplicação retornando o usuário à Tela 1 de carregamento limpo
                st.rerun()

    def render_chat_interface(self):
        """Interface B: Renderiza a área de chat e visualizações.

        Lê o histórico de mensagens, exibe o dicionário de dados de forma tabular,
        desenha gráficos/tabelas e gerencia a entrada e execução de perguntas no Grafo.
        """
        # Se db_ready for False (Tela 1), exibe mensagem instrutiva e encerra a renderização
        if not st.session_state.db_ready:
            st.info("Aguardando envio do pacote de dados (.ZIP) para carregar o console analítico.")
            return

        # Se db_ready for True (Tela 2), renderiza a interface central
        st.subheader("Interface B - Análises e Consultas")

        # --- INÍCIO - METADADOS E DICIONÁRIO DE DADOS ---
        with st.expander("Metadados e Dicionário de Dados"):
            data_dict = st.session_state.data_dict

            # Se o dicionário cumulativo for válido e contiver metadados de tabelas reais
            if isinstance(data_dict, dict) and len(data_dict) > 0 and "mensagem" not in data_dict and "erro" not in data_dict:
                try:
                    table_rows = []
                    # Planifica o dicionário aninhado em uma lista bidimensional
                    for table_name, columns in data_dict.items():
                        for col_name, description in columns.items():
                            # Se for o formato dinâmico (dict de N variáveis), busca a descrição funcional
                            if isinstance(description, dict):
                                desc_text = description.get("Descrição funcional", str(description))
                            else:
                                desc_text = str(description)
                            table_rows.append([table_name, col_name, desc_text])

                    # Gera o DataFrame nativo e plota usando o Streamlit
                    df_metadata = pd.DataFrame(table_rows, columns=["Tabela", "Coluna", "Descrição"])
                    st.dataframe(df_metadata, width="stretch", hide_index=True)
                except Exception as e:
                    st.text(str(data_dict))

            else:
                # Tratamento de fallbacks e avisos amigáveis caso não haja dicionário válido
                if isinstance(data_dict, dict) and "mensagem" in data_dict:
                    st.warning(f"⚠️ {data_dict['mensagem']}")
                elif isinstance(data_dict, dict) and "erro" in data_dict:
                    st.error(f"❌ {data_dict['erro']}")
                else:
                    st.warning(
                        "⚠️ Nenhum dicionário de dados CSV foi localizado no arquivo ZIP. O assistente utilizará as colunas físicas.")
        # --- FIM - METADADOS E DICIONÁRIO DE DADOS ---

        # --- INÍCIO - ANÁLISE PRELIMINAR DOS DADOS ---
        with st.expander("📊 Análise Preliminar dos Dados"):
            # A lista de tabelas vem diretamente do que foi fisicamente carregado no DuckDB, não do dicionário descritivo.
            active_tables = sorted(st.session_state.get("loaded_tables", set()))

            if not active_tables:
                st.info("Nenhuma tabela disponível para análise no momento.")
            else:
                for table_name in active_tables:
                    st.markdown(f"### Tabela: `{table_name}`")
                    try:
                        # Busca a amostra e o perfil semântico usando cache de sessão para evitar recálculos em reruns
                        if table_name not in st.session_state.cached_profiles:
                            st.session_state.cached_profiles[table_name] = PreliminaryAnalysisService.get_analysis(table_name)
                        analysis = st.session_state.cached_profiles[table_name]

                        # Cria as abas: amostra bruta e perfil inteligente por coluna
                        tab1, tab2 = st.tabs(["Amostra (.head)", "Perfil Inteligente das Colunas"])

                        with tab1:
                            st.write("Primeiras 5 linhas da base de dados:")
                            st.dataframe(analysis["head"], width="stretch")

                        with tab2:
                            profile = analysis["profile"]

                            # Tabela-resumo com o essencial de cada coluna
                            summary_rows = []
                            for col_name, info in profile.items():
                                summary_rows.append({
                                    "Coluna": col_name,
                                    "Tipo Detectado": info["tipo_detectado"],
                                    "% Nulos": info["pct_nulos"],
                                    "Valores Únicos": info["valores_unicos"],
                                })
                            st.write("Resumo geral das colunas:")
                            st.dataframe(pd.DataFrame(summary_rows), width="stretch", hide_index=True)

                            # Detalhamento específico por coluna, de acordo com o tipo detectado
                            for col_name, info in profile.items():
                                with st.expander(f"🔍 Detalhes: {col_name}"):
                                    tipo = info["tipo_detectado"]

                                    if info.get("erro_processamento"):
                                        st.warning("Não foi possível processar esta coluna automaticamente.")

                                    elif tipo == "numerica":
                                        st.write("Estatísticas descritivas:")
                                        stats_df = pd.DataFrame(
                                            list(info["estatisticas"].items()),
                                            columns=["Métrica", "Valor"]
                                        )
                                        st.dataframe(stats_df, width="stretch", hide_index=True)

                                    elif tipo == "monetaria":
                                        st.write("Estatísticas de valor:")
                                        money_df = pd.DataFrame([
                                            {"Métrica": "Soma Total", "Valor": info.get("soma_total")},
                                            {"Métrica": "Média", "Valor": info.get("media")},
                                            {"Métrica": "Mediana", "Valor": info.get("mediana")},
                                            {"Métrica": "Maior Valor", "Valor": info.get("maior_valor")},
                                            {"Métrica": "Menor Valor", "Valor": info.get("menor_valor")},
                                        ])
                                        st.dataframe(money_df, width="stretch", hide_index=True)

                                    elif tipo == "categorica":
                                        st.write("Top 10 valores mais frequentes (% do total):")
                                        top_df = pd.DataFrame(
                                            list(info["top_valores"].items()),
                                            columns=["Valor", "% do Total"]
                                        )
                                        st.dataframe(top_df, width="stretch", hide_index=True)

                                    elif tipo == "data":
                                        data_min = info.get("data_min")
                                        data_max = info.get("data_max")
                                        intervalo = info.get("intervalo_dias")

                                        st.write(f"Data mais antiga: {data_min or 'não disponível'}")
                                        st.write(f"Data mais recente: {data_max or 'não disponível'}")
                                        if intervalo is not None:
                                            st.write(f"Intervalo total: {intervalo} dias")

                                        evolucao = info.get("evolucao_trimestral")
                                        if evolucao:
                                            st.write("Evolução por trimestre:")
                                            st.dataframe(
                                                pd.DataFrame(evolucao),
                                                width="stretch", hide_index=True
                                            )
                                        else:
                                            st.info("Não foi possível calcular a evolução trimestral para esta coluna.")

                                    elif tipo == "identificador":
                                        st.write("Coluna identificadora — não é submetida a estatísticas agregadas.")
                                        st.write(f"Exemplos de valores: {info['exemplos']}")

                                    elif tipo == "texto_livre":
                                        st.write("Campo de texto livre com alta variabilidade.")
                                        comprimento = info.get("comprimento_medio")
                                        if comprimento is not None:
                                            st.write(f"Comprimento médio do texto: {comprimento} caracteres")

                                        top_normalizado = info.get("top_valores_normalizados")
                                        if top_normalizado:
                                            st.write("Top 10 valores mais frequentes (normalizados — maiúsculas e sem espaços extras):")
                                            top_df = pd.DataFrame(
                                                list(top_normalizado.items()),
                                                columns=["Valor Normalizado", "% do Total"]
                                            )
                                            st.dataframe(top_df, width="stretch", hide_index=True)
                                        else:
                                            st.info("Não foi possível calcular a frequência de valores para esta coluna.")

                    except Exception as e:
                        st.error(f"Erro ao analisar a tabela {table_name}: {e}")

                    st.markdown("---")
        # --- FIM - ANÁLISE PRELIMINAR DOS DADOS ---


        # Recupera as conversas salvas na sessão
        chat_history = ConversationMemory.get_history()

        # Renderização do histórico estável do chat
        for msg in chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                # Renderiza o gráfico do Plotly Express primeiro (Boa Prática de UX)
                if msg.get("chart") is not None:
                    st.plotly_chart(msg["chart"], width="stretch")

                # Se houver gráfico, renderiza a tabela de apoio recolhida em um expansor
                if msg.get("table") is not None:
                    df_result = msg["table"]
                    if msg.get("chart") is not None:
                        with st.expander("📊 Visualizar Dados Brutos (Tabela)"):
                            st.dataframe(df_result, width="stretch")
                    else:
                        st.dataframe(df_result, width="stretch")

        # Entrada de novos inputs do usuário no console de chat
        if user_query := st.chat_input("Insira sua pergunta:"):
            # Salva imediatamente a pergunta do usuário no histórico para atualizar a tela
            ConversationMemory.add_message("user", user_query)

            # Força o balão de fala do usuário a aparecer na tela sem delays
            with st.chat_message("user"):
                st.markdown(user_query)

            # Processamento em background
            with st.spinner("O Grafo de Agentes está processando..."):
                try:
                    # Executa de forma síncrona o grafo compilado do LangGraph (valida e orquestra)
                    final_state = run_orchestrator_graph(user_query, st.session_state.data_dict)

                    # Extrai as variáveis geradas de forma nativa do AgentState retornado
                    explanation = final_state.get("explanation", "Não foi possível obter resposta.")
                    df_result = final_state.get("dataframe")
                    plotly_fig = final_state.get("chart_fig")

                    # Salva diretamente no histórico de mensagens (O segredo da sincronização da tela)
                    ConversationMemory.add_message(
                        role="assistant",
                        content=explanation,
                        table=df_result,
                        chart=plotly_fig
                    )

                except Exception as e:
                    st.error(f"Erro ao processar requisição: {e}")
                    return

            # Força o Streamlit a reiniciar o script. Na reexecução, a nova resposta do assistente
            # será renderizada imediatamente no bloco estável do histórico de chat (evita latência)
            st.rerun()

    def run(self):
        """Executa sequencialmente a montagem visual da aplicação.

        É o método principal invocado pelo arquivo de boot main.py.
        """
        self.render_header()
        self.render_sidebar()
        self.render_chat_interface()