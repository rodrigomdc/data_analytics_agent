# -*- coding: utf-8 -*-
"""Módulo de gerenciamento da infraestrutura do banco de dados DuckDB."""

import duckdb
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

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Estabelece e retorna uma conexão ativa com o arquivo do DuckDB.

        Returns:
            duckdb.DuckDBPyConnection: Objeto de conexão ativa com o banco.
        """
        return duckdb.connect(database=self.db_path, read_only=False)

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
