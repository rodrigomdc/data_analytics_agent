# -*- coding: utf-8 -*-
"""Ponto de entrada para a execução unificada do Grafo de Estados (LangGraph)."""

import json
from src.db_manager.duckdb_manager import DuckDBManager
from src.graph.builder import WorkflowGraphBuilder
from src.utils.utils import validate_user_query


def run_orchestrator_graph(user_query: str, data_dict: dict) -> dict:
    """Instancia, compila e executa o fluxo do Grafo síncrono.

    Este método inicializa o estado de entrada mapeando o esquema do banco,
    normalizando o dicionário de dados em uma string JSON descritiva e
    invocando a execução do motor de estados do LangGraph.

    Args:
        user_query (str): A pergunta em linguagem natural feita pelo usuário.
        data_dict (dict): Dicionário contendo os metadados do dataset carregado.

    Returns:
        dict: O estado final compartilhado (AgentState) após a conclusão de todos os nós.
    """
    db = DuckDBManager()
    schema = db.get_schema_info()

    # Validação de entrada do usuário
    is_valid, error_msg = validate_user_query(user_query, schema)
    if not is_valid:
        return {
            "explanation": error_msg,
            "dataframe": None,
            "chart_fig": None,
            "execution_logs": ["Validação local: Pergunta fora de contexto. Fluxo abortado."]
        }

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
        "chart_fig": None,
        "explanation": None,
        "execution_logs": []
    }

    # Execução do Grafo síncrona
    final_state = app_graph.invoke(initial_state)
    return final_state
