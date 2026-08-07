# -*- coding: utf-8 -*-
"""Módulo de gerenciamento da infraestrutura do banco de dados DuckDB."""

import duckdb
import json
import pandas as pd
from config import DB_PATH
from src.utils.utils import setup_logger

logger = setup_logger("DuckDBManager")


class DuckDBManager:
    """Classe responsável pelo ciclo de conexões e execução física de queries no DuckDB."""

    def __init__(self, db_path: str = DB_PATH):
        """Inicializa o gerenciador definindo o caminho físico do banco.

        Args:
            db_path (str): Caminho absoluto ou relativo do banco local do DuckDB.
        """
        self.db_path = db_path
        self._init_cache_table()

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Estabelece e retorna uma conexão ativa com o arquivo do DuckDB.

        Returns:
            duckdb.DuckDBPyConnection: Objeto de conexão ativa com o banco.
        """
        return duckdb.connect(database=self.db_path, read_only=False)

    def _init_cache_table(self):
        """Cria fisicamente a tabela de cache de controle se ela não existir no banco."""
        conn = self.get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _system_query_cache (
                    query_hash VARCHAR PRIMARY KEY,
                    sql_query VARCHAR,
                    explanation VARCHAR,
                    chart_config VARCHAR -- Armazena a string JSON dos parâmetros de eixos do gráfico
                );
            """)
            conn.close()
        except Exception as e:
            conn.close()
            logger.error(f"Erro ao inicializar tabela de cache interna: {e}")

    def lookup_cache(self, query_hash: str) -> dict:
        """Busca se a pergunta higienizada já possui resposta analítica em cache.

        Args:
            query_hash (str): Chave identificadora única higienizada da pergunta.

        Returns:
            dict: Resultados estruturados mapeados em caso de sucesso, ou None se não houver.
        """
        conn = self.get_connection()
        try:
            res = conn.execute(
                "SELECT sql_query, explanation, chart_config FROM _system_query_cache WHERE query_hash = ?;",
                (query_hash,)
            ).fetchone()
            conn.close()
            if res:
                return {
                    "sql_query": res[0],
                    "explanation": res[1],
                    "chart_config": json.loads(res[2]) if res[2] else None
                }
            return None
        except Exception as e:
            conn.close()
            logger.error(f"Erro ao buscar na tabela de cache: {e}")
            return None

    def save_cache(self, query_hash: str, sql_query: str, explanation: str, chart_config: dict = None):
        """Grava ou atualiza os resultados de uma consulta na tabela de cache física.

        Args:
            query_hash (str): Chave identificadora única higienizada da pergunta.
            sql_query (str): Instrução SQL de extração do banco.
            explanation (str): Explicação em texto de negócios gerada pela IA.
            chart_config (dict, optional): Parâmetros JSON estruturados do gráfico Plotly.
        """
        conn = self.get_connection()
        try:
            chart_config_str = json.dumps(
                chart_config) if chart_config else None
            conn.execute("""
                INSERT OR REPLACE INTO _system_query_cache (query_hash, sql_query, explanation, chart_config)
                VALUES (?, ?, ?, ?);
            """, (query_hash, sql_query, explanation, chart_config_str))
            conn.close()
        except Exception as e:
            conn.close()
            logger.error(f"Erro ao gravar dados na tabela de cache: {e}")

    def execute_query(self, query: str) -> pd.DataFrame:
        """Executa uma instrução SQL de leitura e retorna o resultado em DataFrame.

        Args:
            query (str): A instrução SQL de leitura a ser executada no banco.

        Returns:
            pd.DataFrame: DataFrame contendo as linhas resultantes da consulta.

        Raises:
            Exception: Se ocorrer qualquer erro de execução ou parser de SQL.
        """
        conn = self.get_connection()
        try:
            df = conn.execute(query).fetchdf()
            conn.close()
            return df
        except Exception as e:
            conn.close()
            logger.error(f"Erro ao executar a query SQL: {e}")
            raise e

    def get_schema_info(self) -> str:
        """Varre o banco e retorna uma string descrevendo o esquema físico das tabelas.

        Busca todas as tabelas ativas e mapeia suas respectivas colunas e tipos
        de dados para fornecer o contexto de esquema estruturado aos agentes.

        Returns:
            str: Uma string formatada descrevendo as tabelas e colunas físicas do banco.
        """
        try:
            conn = self.get_connection()
            tables = conn.execute("SHOW TABLES;").fetchall()
            schema_info = ""
            for t in tables:
                t_name = t[0]
                cols = conn.execute(
                    f"PRAGMA table_info('{t_name}');").fetchall()
                cols_desc = ", ".join([f"{c[1]} ({c[2]})" for c in cols])
                schema_info += f"Tabela '{t_name}': [{cols_desc}]\n"
            conn.close()
            return schema_info if schema_info else "Nenhuma tabela carregada."
        except Exception as e:
            logger.error(f"Erro ao obter esquema: {e}")
            return "Erro ao ler o esquema de dados."
