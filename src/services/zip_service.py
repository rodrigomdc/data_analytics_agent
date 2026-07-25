# -*- coding: utf-8 -*-
"""Serviço utilitário responsável por extrair arquivos compactados (.ZIP)."""

import zipfile
import os
from config import EXTRACTED_DIR
from src.utils.utils import setup_logger

logger = setup_logger("ZipService")


class ZipService:
    """Classe responsável pelo tratamento físico de descompactação de arquivos."""

    @staticmethod
    def extract_zip(zip_file_path: str, extract_to: str = EXTRACTED_DIR) -> list:
        """Extrai todos os arquivos de um pacote ZIP no diretório de extração.

        Filtra e descarta arquivos ocultos gerados por sistemas operacionais (como __MACOSX).

        Args:
            zip_file_path (str): Caminho absoluto ou relativo do arquivo ZIP físico.
            extract_to (str, optional): Caminho do diretório de destino.

        Returns:
            list: Lista contendo os caminhos absolutos dos arquivos físicos extraídos.
        """
        extracted_paths = []
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            for root, _, files in os.walk(extract_to):
                for file in files:
                    if file.startswith('__MACOSX') or file.startswith('.'):
                        continue
                    extracted_paths.append(os.path.join(root, file))
            return extracted_paths
        except Exception as e:
            logger.error(f"Falha de extração do arquivo {zip_file_path}: {e}")
        return extracted_paths
