# -*- coding: utf-8 -*-
"""Módulo gerenciador da memória histórica de conversação do Chat."""

import streamlit as st


class ConversationMemory:
    """Encapsula a leitura e a gravação de mensagens na sessão ativa do Streamlit."""

    @staticmethod
    def get_history() -> list:
        """Recupera a lista de mensagens históricas da sessão do Streamlit.

        Garante a inicialização segura do histórico caso o estado esteja vazio.

        Returns:
            list: Lista contendo dicionários de mensagens estruturadas no formato chat.
        """
        if "messages" not in st.session_state:
            st.session_state.messages = []
        return st.session_state.messages

    @staticmethod
    def add_message(role: str, content: str, table: object = None, chart: object = None):
        """Grava uma nova mensagem estruturada na memória de sessão do Streamlit.

        Args:
            role (str): O remetente da mensagem ('user' ou 'assistant').
            content (str): O conteúdo textual (explicação) da resposta.
            table (pd.DataFrame, optional): Tabela do Pandas associada à mensagem.
            chart (plotly.graph_objs.Figure, optional): Gráfico do Plotly associado.
        """
        st.session_state.messages.append({
            "role": role,
            "content": content,
            "table": table,
            "chart": chart
        })
