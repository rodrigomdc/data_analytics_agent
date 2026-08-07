# -*- coding: utf-8 -*-
"""Serviço de validação e carga física de arquivos CSV no DuckDB."""

import os
import pandas as pd
from pandas.errors import ParserError
from src.db_manager.duckdb_manager import DuckDBManager
from src.utils.utils import sanitize_table_name, sanitize_column_name
from src.utils.utils import setup_logger
logger = setup_logger("CSVService")

ENCODINGS_TO_TRY = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
DELIMITERS_TO_TRY = [";", ",", "\t"]


class CSVService:
    """Classe responsável pelo tratamento, validação e carregamento de arquivos CSV."""

    @staticmethod
    def _detect_csv_properties(file_path: str) -> tuple:
        """Detecta estatisticamente as propriedades físicas do arquivo CSV.

        Utiliza o sniffer nativo da biblioteca csv para identificar o delimitador
        e executa uma varredura para identificar o encoding correto.

        Args:
            file_path (str): Caminho físico do arquivo CSV.

        Returns:
            tuple: Uma tupla contendo (is_valid: bool, encoding: str, delimiter: str).
        """
        import csv

        detected_encoding = "utf-8"
        for encoding in ENCODINGS_TO_TRY:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.read(10)
                detected_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        try:
            with open(file_path, "r", encoding=detected_encoding) as f:
                sample = f.read(2048)
                dialect = csv.Sniffer().sniff(sample, delimiters=DELIMITERS_TO_TRY)
                sep = dialect.delimiter
        except Exception:
            sep = ";" if detected_encoding in [
                "latin-1", "iso-8859-1", "cp1252"] else ","

        return True, detected_encoding, sep

    @staticmethod
    def load_csvs_to_db(csv_paths: list) -> list:
        """Carrega os arquivos CSV validados para o DuckDB de forma robusta.

        Lê os arquivos via Pandas aplicando a codificação correta e higieniza
        os cabeçalhos das colunas antes de registrar a tabela em memória no DuckDB.

        Args:
            csv_paths (list): Lista de caminhos dos arquivos CSV extraídos.

        Returns:
            list: Lista contendo os nomes das tabelas que foram carregadas com sucesso.

        Raises:
            RuntimeError: Se ocorrer uma falha crítica na gravação física da tabela.
        """
        db = DuckDBManager()
        conn = db.get_connection()
        loaded_tables = []

        try:
            for path in csv_paths:
                if path.endswith(".csv"):
                    is_valid, encoding, sep = CSVService._detect_csv_properties(
                        path)

                    if is_valid:
                        table_name = sanitize_table_name(path)

                        try:
                            df_completo = pd.read_csv(
                                path, sep=sep, encoding=encoding, decimal=",", on_bad_lines="skip")

                            # Higienização de colunas
                            df_completo.columns = [sanitize_column_name(
                                col) for col in df_completo.columns]

                            conn.execute(f'DROP TABLE IF EXISTS "{table_name}";')
                            conn.register("temp_dataframe_ingestion", df_completo)
                            conn.execute(
                                f'CREATE TABLE "{table_name}" AS SELECT * FROM temp_dataframe_ingestion;')
                            conn.unregister("temp_dataframe_ingestion")

                            loaded_tables.append(table_name)
                        except Exception as e:
                            logger.error(
                                f"Erro ao carregar a tabela {table_name}: {e}")
                            raise RuntimeError(
                                f"Erro na carga física da tabela {table_name}: {e}")
        finally:
            conn.close()

        return loaded_tables
