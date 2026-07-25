# -*- coding: utf-8 -*-
"""Orquestrador do fluxo determinístico de ETL (Ingestão de Dados)."""

from src.services.zip_service import ZipService
from src.services.data_dict_service import DataDictionaryService
from src.services.csv_service import CSVService


class DataIngestionService:
    """Classe que coordena sequencialmente as etapas físicas de ingestão de dados."""

    @staticmethod
    def process_zip_payload(zip_file_path: str) -> dict:
        """Executa sequencialmente a extração, o parse do dicionário e a carga física do ZIP.

        Args:
            zip_file_path (str): Caminho físico do arquivo ZIP enviado pelo usuário.

        Returns:
            dict: Um dicionário contendo as tabelas carregadas e o data_dict estruturado.
        """
        extracted_paths = ZipService.extract_zip(zip_file_path)
        data_dict = DataDictionaryService.extract_dictionary(extracted_paths)
        tables = CSVService.load_csvs_to_db(extracted_paths)

        return {
            "loaded_tables": tables,
            "data_dict": data_dict
        }
