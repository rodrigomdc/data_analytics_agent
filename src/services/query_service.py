# -*- coding: utf-8 -*-
"""Módulo de serviço encarregado da interceptação de cache e validação de consultas."""

import json
from src.db_manager.duckdb_manager import DuckDBManager
from src.utils.utils import validate_user_query, sanitize_column_name
from src.tools.tools import query_duckdb_tool, create_chart_tool
from src.graph.orchestrator import run_orchestrator_graph


class QueryService:
    """Classe responsável pelo ciclo de vida, validação e cache de consultas."""

    @staticmethod
    def process_query(user_query: str, data_dict: dict) -> dict:
        """Processa a requisição do usuário aplicando validação local e interceptação de cache.

        Args:
            user_query (str): A pergunta em linguagem natural feita pelo usuário.
            data_dict (dict): Dicionário contendo os metadados (dicionário de dados).

        Returns:
            dict: O dicionário de estado final contendo a resposta, tabela e gráfico.
        """
        db = DuckDBManager()
        schema = db.get_schema_info()

        # VALIDAÇÃO LOCAL DE ENTRADA (Zero Custo de API/Tokens)
        is_valid, error_msg = validate_user_query(user_query, schema)
        if not is_valid:
            # Retorna imediatamente uma resposta estruturada de orientação em caso de input inválido
            return {
                "explanation": error_msg,
                "dataframe": None,
                "chart_fig": None,
                "execution_logs": ["Validação local: Pergunta considerada inválida ou fora do contexto."]
            }

        # INTERCEPTAÇÃO DE CACHE (Lookup)
        # Normaliza a pergunta do usuário para usá-la como chave hash única de busca
        query_hash = sanitize_column_name(user_query)
        cached_result = db.lookup_cache(query_hash)

        if cached_result is not None:
            # === CACHE HIT (EXCELENTE DESEMPENHO) ===
            # Bypassa todo o Grafo e o Gemini, executando apenas o banco localmente (latência mínima)
            try:
                # Executa a query SQL salva para obter os dados em tempo real (dados atualizados)
                df = query_duckdb_tool(cached_result["sql_query"])
                fig = None

                # Se houver configuração gráfica salva, reconstrói o gráfico instantaneamente
                if cached_result["chart_config"]:
                    cfg = cached_result["chart_config"]
                    fig = create_chart_tool(
                        df, cfg["chart_type"], cfg["x_col"], cfg["y_col"], cfg["title"])

                return {
                    "explanation": cached_result["explanation"],
                    "dataframe": df,
                    "chart_fig": fig,
                    "execution_logs": ["Resultado recuperado diretamente do Cache Local do Sistema (0 Tokens)."]
                }
            except Exception:
                # Caso ocorra qualquer erro de estrutura de tabela no cache, prossegue para o fluxo normal de IA
                pass

        # CACHE MISS: Delega a inteligência cognitiva de IA ao Orquestrador do Grafo
        final_state = run_orchestrator_graph(user_query, data_dict, schema)

        # 4. GRAVAÇÃO EM CACHE: Registra o sucesso da consulta para as próximas requisições
        if final_state.get("explanation") and final_state.get("sql_query"):
            db.save_cache(
                query_hash=query_hash,
                sql_query=final_state["sql_query"],
                explanation=final_state["explanation"],
                chart_config=final_state.get("chart_config")
            )

        return final_state
