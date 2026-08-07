# -*- coding: utf-8 -*-
"""Ponto de entrada para a execução e compilação do Grafo de Estados (LangGraph)."""

import json
from src.graph.builder import WorkflowGraphBuilder


def run_orchestrator_graph(user_query: str, data_dict: dict, schema: str) -> dict:
    """Compila e executa o fluxo unificado do Grafo síncrono.

    Args:
        user_query (str): A pergunta em linguagem natural feita pelo usuário.
        data_dict (dict): Dicionário contendo os metadados do dataset carregado.
        schema (str): Esquema de banco de dados gerado dinamicamente pelo DuckDB.

    Returns:
        dict: O estado final compartilhado (AgentState) após a conclusão do grafo.
    """
    app_graph = WorkflowGraphBuilder().build()

    # Se o data_dict for um dicionário de erro/mensagem, converte para aviso amigável à LLM
    if "mensagem" in data_dict or "erro" in data_dict:
        data_dict_prompt = "Nenhum dicionário fornecido. Baseie-se estritamente nos nomes das colunas físicas no Schema."
    else:
        data_dict_prompt = json.dumps(data_dict, ensure_ascii=False, indent=2)

    # Define o Estado Inicial que alimentará o fluxo
    initial_state = {
        "user_query": user_query,
        "data_dict": data_dict_prompt,
        "schema": schema,
        "next_step": "",
        "sql_query": None,
        "dataframe": None,
        "chart_config": None,  # Inicia nulo para o cache
        "chart_fig": None,
        "explanation": None,
        "execution_logs": []
    }

    # Execução do Grafo síncrona
    final_state = app_graph.invoke(initial_state)
    return final_state
