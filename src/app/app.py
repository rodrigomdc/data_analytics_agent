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
from src.services.query_service import QueryService
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
        if "db_ready" not in st.session_state: st.session_state.db_ready = False

        # Dicionário unificado de metadados das tabelas (inicia sempre como dict vazio)
        if "data_dict" not in st.session_state or not isinstance(st.session_state.data_dict, dict): st.session_state.data_dict = {}

        # Conjunto (set) contendo os nomes dos arquivos ZIP já processados na sessão
        if "loaded_zip_names" not in st.session_state: st.session_state.loaded_zip_names = set()

        # Conjunto (set) com os nomes de todas as tabelas físicas já carregadas no DuckDB.
        # Fica desacoplado do data_dict para que a análise preliminar não dependa da existência de um dicionário de dados descritivo dentro do ZIP.
        if "loaded_tables" not in st.session_state: st.session_state.loaded_tables = set()

        # Chave dinâmica incremental para limpar fisicamente o campo de upload no reset
        if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0

        if "cached_profiles" not in st.session_state: st.session_state.cached_profiles = {}

    def render_header(self):
        """Renderiza o cabeçalho principal da página do painel web."""
        st.title("Interface Inteligente de Consulta e Visualização")

    def render_sidebar(self):
        """Renderiza controles laterais: Upload e Gestão de sessão."""
        with st.sidebar:
            st.header("⚙️ Configurações")
            uploaded_zip = st.file_uploader("Upload de ZIP", type=["zip"], key=f"up_{st.session_state.uploader_key}")

            # Lógica de processamento de ingestão
            if uploaded_zip and uploaded_zip.name not in st.session_state.loaded_zip_names:
                with st.status("Processando dados..."):
                    temp_path = os.path.join(UPLOADS_DIR, "payload.zip")
                    with open(temp_path, "wb") as f: f.write(uploaded_zip.getbuffer())
                    res = DataIngestionService.process_zip_payload(temp_path)
                    st.session_state.data_dict.update(res["data_dict"])
                    st.session_state.loaded_tables.update(res.get("loaded_tables", []))
                    st.session_state.db_ready = True
                    st.session_state.loaded_zip_names.add(uploaded_zip.name)
                    st.session_state.uploader_key += 1
                st.rerun()

            # Controle de reset de aplicação
            if st.session_state.db_ready:
                st.markdown("---")
                if st.button("🧹 Iniciar Nova Análise"):
                    reset_application_storage()
                    st.session_state.clear()
                    st.rerun()

    def _render_chat_logic(self):
        """Renderiza o container de chat e gerencia a interação do usuário."""
        st.subheader("Interação com o Analista Corporativo")
        chat_container = st.container(height=550)

        with chat_container:
            for msg in ConversationMemory.get_history():
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg.get("chart"): st.plotly_chart(msg["chart"], use_container_width=True)
                    if msg.get("table") is not None: st.dataframe(msg["table"], use_container_width=True)

        if user_query := st.chat_input("Digite sua pergunta..."):
            ConversationMemory.add_message("user", user_query)
            with st.spinner("Agente processando..."):
                final_state = QueryService.process_query(user_query, st.session_state.data_dict)
                ConversationMemory.add_message(
                    role="assistant",
                    content=final_state.get("explanation"),
                    table=final_state.get("dataframe"),
                    chart=final_state.get("chart_fig")
                )
            st.rerun()

    def _render_metadata_view(self):
        """Renderiza a visualização do dicionário de dados."""
        st.subheader("Dicionário de Dados")
        st.write("Metadados estruturados das tabelas carregadas.")
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
                                desc_text = description.get(
                                    "Descrição funcional", str(description))
                            else:
                                desc_text = str(description)
                            table_rows.append(
                                [table_name, col_name, desc_text])

                    # Gera o DataFrame nativo e plota usando o Streamlit
                    df_metadata = pd.DataFrame(
                        table_rows, columns=["Tabela", "Coluna", "Descrição"])
                    st.dataframe(df_metadata, use_container_width=True, hide_index=True)
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
        st.json(st.session_state.data_dict)

    def _render_preliminary_analysis(self):
        """Renderiza a análise preliminar das tabelas carregadas."""
        st.subheader("Análise Preliminar")
        active_tables = sorted(st.session_state.get("loaded_tables", set()))

        if not active_tables:
            st.info("Nenhuma tabela disponível para análise no momento.")
            return

        for table_name in active_tables:
            st.markdown(f"### Tabela: `{table_name}`")
            with st.expander(f"📊 Análise Preliminar — {table_name}"):
                try:
                    if table_name not in st.session_state.cached_profiles:
                        st.session_state.cached_profiles[table_name] = PreliminaryAnalysisService.get_analysis(
                            table_name)
                    analysis = st.session_state.cached_profiles[table_name]

                    tab1, tab2 = st.tabs(
                        ["Amostra (.head)", "Perfil Inteligente das Colunas"])

                    with tab1:
                        st.write("Primeiras 5 linhas da base de dados:")
                        st.dataframe(analysis["head"], use_container_width=True)

                    with tab2:
                        profile = analysis["profile"]

                        summary_rows = []
                        for col_name, info in profile.items():
                            summary_rows.append({
                                "Coluna": col_name,
                                "Tipo Detectado": info["tipo_detectado"],
                                "% Nulos": info["pct_nulos"],
                                "Valores Únicos": info["valores_unicos"],
                            })
                        st.write("Resumo geral das colunas:")
                        st.dataframe(pd.DataFrame(summary_rows),
                                    use_container_width=True, hide_index=True)

                        for col_name, info in profile.items():
                            with st.expander(f"🔍 Detalhes: {col_name}"):
                                tipo = info["tipo_detectado"]

                                if info.get("erro_processamento"):
                                    st.warning(
                                        "Não foi possível processar esta coluna automaticamente.")

                                elif tipo == "numerica":
                                    st.write("Estatísticas descritivas:")
                                    stats_df = pd.DataFrame(
                                        list(info["estatisticas"].items()),
                                        columns=["Métrica", "Valor"]
                                    )
                                    st.dataframe(
                                        stats_df, use_container_width=True, hide_index=True)

                                elif tipo == "monetaria":
                                    st.write("Estatísticas de valor:")
                                    money_df = pd.DataFrame([
                                        {"Métrica": "Soma Total",
                                            "Valor": info.get("soma_total")},
                                        {"Métrica": "Média",
                                            "Valor": info.get("media")},
                                        {"Métrica": "Mediana",
                                            "Valor": info.get("mediana")},
                                        {"Métrica": "Maior Valor",
                                            "Valor": info.get("maior_valor")},
                                        {"Métrica": "Menor Valor",
                                            "Valor": info.get("menor_valor")},
                                    ])
                                    st.dataframe(
                                        money_df, use_container_width=True, hide_index=True)

                                elif tipo == "categorica":
                                    st.write(
                                        "Top 10 valores mais frequentes (% do total):")
                                    top_df = pd.DataFrame(
                                        list(info["top_valores"].items()),
                                        columns=["Valor", "% do Total"]
                                    )
                                    st.dataframe(
                                        top_df, use_container_width=True, hide_index=True)

                                elif tipo == "data":
                                    data_min = info.get("data_min")
                                    data_max = info.get("data_max")
                                    intervalo = info.get("intervalo_dias")

                                    st.write(
                                        f"Data mais antiga: {data_min or 'não disponível'}")
                                    st.write(
                                        f"Data mais recente: {data_max or 'não disponível'}")
                                    if intervalo is not None:
                                        st.write(
                                            f"Intervalo total: {intervalo} dias")

                                    evolucao = info.get("evolucao_trimestral")
                                    if evolucao:
                                        st.write("Evolução por trimestre:")
                                        st.dataframe(
                                            pd.DataFrame(evolucao),
                                            use_container_width=True, hide_index=True
                                        )
                                    else:
                                        st.info(
                                            "Não foi possível calcular a evolução trimestral para esta coluna.")

                                elif tipo == "identificador":
                                    st.write(
                                        "Coluna identificadora — não é submetida a estatísticas agregadas.")
                                    st.write(
                                        f"Exemplos de valores: {info['exemplos']}")

                                elif tipo == "texto_livre":
                                    st.write(
                                        "Campo de texto livre com alta variabilidade.")
                                    comprimento = info.get("comprimento_medio")
                                    if comprimento is not None:
                                        st.write(
                                            f"Comprimento médio do texto: {comprimento} caracteres")

                                    top_normalizado = info.get(
                                        "top_valores_normalizados")
                                    if top_normalizado:
                                        st.write(
                                            "Top 10 valores mais frequentes (normalizados — maiúsculas e sem espaços extras):")
                                        top_df = pd.DataFrame(
                                            list(top_normalizado.items()),
                                            columns=[
                                                "Valor Normalizado", "% do Total"]
                                        )
                                        st.dataframe(
                                            top_df, use_container_width=True, hide_index=True)
                                    else:
                                        st.info(
                                            "Não foi possível calcular a frequência de valores para esta coluna.")

                except Exception as e:
                    st.error(
                        f"Erro ao analisar a tabela {table_name}: {e}")

            st.markdown("---")


    def render_chat_interface(self):
        """Gerencia abas e conteúdo principal."""
        if not st.session_state.db_ready:
            st.info("Aguardando upload do pacote ZIP para iniciar.")
            return

        tab1, tab2, tab3 = st.tabs(["💬 Chat com Agente", "ℹ️ Metadados", "📊 Perfil dos Dados"])
        with tab1: self._render_chat_logic()
        with tab2: self._render_metadata_view()
        with tab3: self._render_preliminary_analysis()

    def run(self):
        """Método principal de execução."""
        self.render_sidebar()
        self.render_chat_interface()

if __name__ == "__main__":
    StreamlitApp().run()