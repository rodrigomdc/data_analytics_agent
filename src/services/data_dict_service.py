# -*- coding: utf-8 -*-
"""Serviço responsável pelo processamento dinâmico do dicionário de dados."""

import os
import csv
from src.utils.utils import sanitize_table_name, setup_logger, sanitize_column_name

logger = setup_logger("DataDictionaryService")


class DataDictionaryService:
    """Classe que encapsula a leitura e o parse do arquivo de dicionário de dados."""

    @staticmethod
    def extract_dictionary(extracted_files: list) -> dict:
        """Localiza e extrai os metadados do dicionário de dados contido nos arquivos.

        Args:
            extracted_files (list): Lista de caminhos de arquivos extraídos do ZIP.

        Returns:
            dict: Dicionário estruturado do Python com as tabelas e suas regras.
        """
        for file_path in extracted_files:
            file_name = os.path.basename(file_path).lower()
            if "dicionario" in file_name or "readme" in file_name or "dict" in file_name:
                try:
                    data_dict = DataDictionaryService._parse_csv_to_dict(
                        file_path)
                    return data_dict
                except Exception as e:
                    logger.error(
                        f"Erro ao processar dicionário {file_name}: {e}")
                    return {"erro": f"Falha no processamento do dicionário: {e}"}
        return {"mensagem": "Nenhum dicionário estruturado foi encontrado no ZIP."}

    @staticmethod
    def _parse_csv_to_dict(file_path: str) -> dict:
        """Processa qualquer CSV de dicionário de dados de forma 100% dinâmica.

        Mapeia dinamicamente os cabeçalhos de tabela e campo com base em
        sinônimos, agrupando as demais colunas como metadados associados.

        Args:
            file_path (str): Caminho físico do arquivo CSV de dicionário.

        Returns:
            dict: Um dicionário aninhado do Python no formato {tabela: {coluna: {metadados}}}.
        """
        parsed_dict = {}

        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [name.strip()
                                 for name in reader.fieldnames if name]

            headers = reader.fieldnames
            file_header = next((h for h in headers if any(k in h.lower() for k in [
                "arquivo", "tabela", "file", "table"])), headers[0])
            field_header = next((h for h in headers if any(k in h.lower() for k in [
                "campo", "coluna", "field", "column"])), headers[1] if len(headers) > 1 else headers[0])

            for row in reader:
                clean_row = {
                    k.strip(): v.strip()
                    for k, v in row.items()
                    if k is not None and v is not None
                }

                raw_file = clean_row.get(file_header, "")
                campo_bruto = clean_row.get(field_header, "")

                if raw_file and campo_bruto:
                    table_name = sanitize_table_name(raw_file)
                    campo = sanitize_column_name(campo_bruto)

                metadata_columnas = {
                    col_name: val
                    for col_name, val in clean_row.items()
                    if col_name not in [file_header, field_header] and val != ""
                }

                if table_name not in parsed_dict:
                    parsed_dict[table_name] = {}

                parsed_dict[table_name][campo] = metadata_columnas

        return parsed_dict
