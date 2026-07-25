# -*- coding: utf-8 -*-
"""
Módulo: src/app/app.py
Descrição: Interface Gráfica de Usuário (UI) desenvolvida em Streamlit utilizando o padrão OOP.
           Gerencia os layouts da Interface A (painel lateral para upload e carga de dados)
           e da Interface B (chat centralizado para consultas e exibição de tabelas/gráficos),
           consumindo as saídas do Grafo de Estados.
"""


import os
import streamlit as st
from tabulate import tabulate
from config import UPLOADS_DIR
from src.utils.utils import reset_application_storage
from src.services.ingestion_service import DataIngestionService
from src.graph.orchestrator import run_orchestrator_graph
from src.memory.conversation import ConversationMemory


class StreamlitApp:
    def __init__(self):
        st.set_page_config(page_title="Analista IA Corporativo", layout="wide")
        self._init_session_state()

    def _init_session_state(self):
        if "db_ready" not in st.session_state:
            st.session_state.db_ready = False
        # Garante que o data_dict seja sempre inicializado como um dicionário Python vazio
        if "data_dict" not in st.session_state or not isinstance(st.session_state.data_dict, dict):
            st.session_state.data_dict = {}
        # Armazena um conjunto (set) com os nomes de todos os ZIPs já mesclados no banco
        if "loaded_zip_names" not in st.session_state:
            st.session_state.loaded_zip_names = set()
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

    def render_header(self):
        st.title(
            "Interface Inteligente de Consulta e Visualização")

    def render_sidebar(self):
        st.sidebar.header("Interface A - Carga de Arquivos")
        # O uploader funciona como uma zona temporária de drop de arquivos
        uploaded_zip = st.sidebar.file_uploader(
            "Arraste um ZIP para adicionar dados à análise",
            type=["zip"],
            max_upload_size=500,
            key=f"zip_uploader_{st.session_state.uploader_key}"
        )

        if uploaded_zip is not None:
            # Se o arquivo ZIP ainda não tiver sido processado
            if uploaded_zip.name not in st.session_state.loaded_zip_names:
                with st.sidebar.status(f"Adicionando dados de {uploaded_zip.name}...") as status:
                    try:
                        # Arquivo temporário ZIP enviado pelo usuário no painel de carga.
                        temp_zip_path = os.path.join(
                            UPLOADS_DIR, "payload.zip")
                        with open(temp_zip_path, "wb") as f:
                            f.write(uploaded_zip.getbuffer())
                        # Executa a ingestão (Carrega as novas tabelas no DuckDB sem apagar as antigas)
                        res = DataIngestionService.process_zip_payload(
                            temp_zip_path)
                        # Funde o novo dicionário de dados com o dicionário existente
                        new_dict = res["data_dict"]
                        if isinstance(new_dict, dict) and "mensagem" not in new_dict and "erro" not in new_dict:
                            # Se a base continha apenas a mensagem de aviso anterior, limpa antes de mesclar dados reais
                            if "mensagem" in st.session_state.data_dict:
                                st.session_state.data_dict = {}
                            st.session_state.data_dict.update(new_dict)
                        elif not st.session_state.data_dict or "mensagem" in st.session_state.data_dict:
                            # Se o dicionário ativo estiver vazio, armazena o aviso/erro temporário
                            st.session_state.data_dict = new_dict
                        # Atualiza os estados de controle (Sem limpar o histórico de chat anterior)
                        st.session_state.db_ready = True
                        st.session_state.loaded_zip_names.add(
                            uploaded_zip.name)  # Adiciona à lista de carregados
                        status.update(
                            label=f"Dados de '{uploaded_zip.name}' integrados!", state="complete")
                        # Incrementa a chave para forçar o uploader
                        # a se esvaziar imediatamente na tela após o processamento bem-sucedido
                        st.session_state.uploader_key += 1
                        # Atualiza a tela de exibição para atualizar o dicionário de dados na UI
                        st.rerun()
                    except Exception as e:
                        status.update(
                            label="Falha na carga do dataset", state="error")
                        st.sidebar.error(f"Erro: {e}")

        # Botão recomeçar
        if st.session_state.db_ready:
            st.sidebar.markdown("---")
            st.sidebar.subheader("📦 Bases Ativas na Análise")

            # Lista estática dos arquivos indexados (Sem a opção de remoção individual confusa)
            for name in st.session_state.loaded_zip_names:
                st.sidebar.caption(f"✅ {name}")

            st.sidebar.markdown("---")

            # Label amigável com um balão explicativo (help) para evitar confusão técnica
            restart = st.sidebar.button(
                "🧹 Iniciar Nova Análise",
                use_container_width=True,
                help="Clique aqui para apagar os arquivos carregados atualmente, limpar o histórico de conversas e começar do zero."
            )

            if restart:

                reset_application_storage()

                # Reseta todas as variáveis de controle da sessão
                st.session_state.db_ready = False
                st.session_state.data_dict = {}
                st.session_state.loaded_zip_names = set()
                st.session_state.messages = []
                st.session_state.temp_charts = []
                st.session_state.last_dataframe = None
                st.session_state.uploader_key += 1

                # Reinicia a aplicação de forma limpa
                st.rerun()

    def render_chat_interface(self):
        if not st.session_state.db_ready:
            st.info(
                "Aguardando envio do pacote de dados (.ZIP) para carregar o console analítico.")
            return

        st.subheader("Interface B - Análises e Consultas")

        with st.expander("Metadados e Dicionário de Dados"):

            data_dict = st.session_state.data_dict

            # Se o dicionário foi carregado com sucesso e possui chaves de tabelas válidas
            if isinstance(data_dict, dict) and len(data_dict) > 0 and "mensagem" not in data_dict and "erro" not in data_dict:
                try:
                    table_rows = []
                    for table_name, columns in data_dict.items():
                        for col_name, description in columns.items():
                            # Se for o formato dinâmico (dict de N variáveis)
                            if isinstance(description, dict):
                                desc_text = description.get(
                                    "Descrição funcional", str(description))
                            else:
                                desc_text = str(description)
                            table_rows.append(
                                [table_name, col_name, desc_text])

                    # Gera e plota a tabela markdown estável
                    table_markdown = tabulate(
                        table_rows, headers="keys", tablefmt="pipe", showindex=False)
                    st.markdown(table_markdown)
                except Exception as e:
                    st.text(str(data_dict))
            else:
                # Se for apenas a mensagem de aviso (Sem Dicionário no ZIP)
                if isinstance(data_dict, dict) and "mensagem" in data_dict:
                    st.warning(f"⚠️ {data_dict['mensagem']}")
                # Se for uma mensagem de erro físico de leitura
                elif isinstance(data_dict, dict) and "erro" in data_dict:
                    st.error(f"❌ {data_dict['erro']}")
                # Fallback genérico caso seja uma string pura
                else:
                    # Caso de inicialização padrão do sistema(Dicionário {} sem dados)
                    st.warning(
                        "⚠️ Nenhum dicionário de dados CSV foi localizado no arquivo ZIP. O assistente utilizará as colunas físicas.")

        chat_history = ConversationMemory.get_history()

        # Renderização do histórico
        for msg in chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                # Renderiza o gráfico primeiro
                if msg.get("chart") is not None:
                    st.plotly_chart(msg["chart"], width="stretch")

                # Se houver gráfico, renderiza a tabela recolhida em um expander
                if msg.get("table") is not None:
                    df_result = msg["table"]
                    if msg.get("chart") is not None:
                        with st.expander("📊 Visualizar Dados Brutos (Tabela)"):
                            st.dataframe(df_result, width="stretch")
                    else:
                        st.dataframe(df_result, width="stretch")

        # Entrada de novos inputs do usuário
        if user_query := st.chat_input("Insira sua pergunta:"):

            # Salva imediatamente a pergunta do usuário e atualiza a tela
            ConversationMemory.add_message("user", user_query)

            # Força a renderização imediata do balão do usuário na tela
            with st.chat_message("user"):
                st.markdown(user_query)

            # Processamento em background
            with st.spinner("O Grafo de Agentes está processando..."):
                try:
                    # Executa o grafo unificado do LangGraph
                    final_state = run_orchestrator_graph(
                        user_query, st.session_state.data_dict)

                    # Extrai os resultados gerados pelos nós especializados
                    explanation = final_state.get(
                        "explanation", "Não foi possível obter resposta.")
                    df_result = final_state.get("dataframe")
                    plotly_fig = final_state.get("chart_fig")

                    # SALVA DIRETAMENTE NO HISTÓRICO (O segredo da sincronização)
                    ConversationMemory.add_message(
                        role="assistant",
                        content=explanation,
                        table=df_result,
                        chart=plotly_fig
                    )

                except Exception as e:
                    st.error(f"Erro ao processar requisição: {e}")
                    return

            st.rerun()

    def run(self):
        self.render_header()
        self.render_sidebar()
        self.render_chat_interface()
