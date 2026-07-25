# -*- coding: utf-8 -*-
"""Biblioteca unificada de ferramentas de suporte e infraestrutura de arquivos."""

import sys
import re
import os
import logging
import shutil
import unicodedata
from config import DB_PATH, EXTRACTED_DIR, UPLOADS_DIR

# Conjunto estático de tokens conversacionais e analíticos válidos (ASCII plano/sem acentos)
VALID_BASE_TOKENS = {
    # Conversacionais / Saudações
    "ola", "bom", "dia", "tarde", "noite", "quem", "como", "qual", "quais", "quanto", "quantos",
    "ajuda", "obrigado", "obrigada", "valeu", "tchau", "oi", "blz", "tudo", "bem",
    # Termos Analíticos e de Ações de BI
    "soma", "media", "total", "grafico", "tabela", "mostrar", "exibir", "vendas", "quantidade", "valor",
    "maior", "menor", "minimo", "maximo", "contar", "contagem", "filtro", "filtrar", "listar", "lista",
    "grupo", "agrupar", "evolucao", "crescimento", "periodo", "mes", "ano", "data"
}


def setup_logger(name: str) -> logging.Logger:
    """Configura e retorna uma instância padronizada do Logger do Python.

    Adiciona formatadores para exibição de data, hora e severidade das mensagens
    no console de saída padrão (sys.stdout).

    Args:
        name (str): O nome da classe ou módulo associado aos registros.

    Returns:
        logging.Logger: Instância configurada do Logger.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


def validate_user_query(query: str, schema_info: str) -> tuple[bool, str]:
    """Valida deterministicamente se a pergunta do usuário é elegível para processamento.

    Verifica tamanho mínimo, presença de caracteres legíveis e se há cruzamento
    com o vocabulário analítico/conversacional padrão ou com as colunas físicas 
    do DuckDB ativo, poupando chamadas desnecessárias à API (Gemini).

    Args:
        query (str): A pergunta bruta digitada pelo usuário.
        schema_info (str): O esquema descritivo das tabelas ativas gerado pelo DuckDB.

    Returns:
        tuple[bool, str]: Uma tupla contendo (is_valid: bool, error_message: str).
    """
    clean_query = query.strip()

    # Validação 1: Tamanho mínimo absoluto
    if len(clean_query) < 3:
        return False, "Sua mensagem é muito curta. Por favor, formule uma pergunta ou instrução mais clara."

    # Validação 2: Presença de letras legíveis (evita mensagens apenas com símbolos como "???")
    if not re.search(r'[a-zA-Zá-úÁ-Ú]', clean_query):
        return False, "Sua mensagem não contém palavras legíveis. Por favor, digite uma pergunta estruturada."

    # Função auxiliar para limpar, remover acentos e quebrar o texto em conjunto de palavras
    def tokenize_text(text: str) -> set:
        normalized = unicodedata.normalize('NFD', text)
        no_accents = "".join(
            [c for c in normalized if unicodedata.category(c) != 'Mn'])
        words = re.findall(r'\b[a-z0-9_]+\b', no_accents.lower())
        return set(words)

    user_tokens = tokenize_text(clean_query)

    # Validação Dinâmica: Coleta as colunas e tabelas reais do DuckDB para somar ao vocabulário aceito
    db_tokens = tokenize_text(schema_info)

    # Vocabulário unificado aceito (Base + Banco de Dados do Usuário)
    accepted_vocabulary = VALID_BASE_TOKENS.union(db_tokens)

    # Validação 3: Verifica se há interseção de palavras (Overlap)
    # Se o usuário digitar lixo eletrônico (ex: "asdfasdf qwerqwer"), a interseção será vazia
    has_valid_terms = not user_tokens.isdisjoint(accepted_vocabulary)

    if not has_valid_terms:
        return False, (
            "Sua pergunta não parece conter termos analíticos conhecidos "
            "ou referências às tabelas e colunas carregadas. Por favor, reformule sua pergunta."
        )

    return True, ""


def sanitize_table_name(file_name: str) -> str:
    """Higieniza o nome físico de um arquivo para um identificador de tabela SQL válido.

    Remove caminhos, extensões de arquivos, caracteres especiais e trata
    prefixos numéricos comuns em arquivos de notas fiscais.

    Args:
        file_name (str): O caminho ou nome do arquivo original (ex: "202401_NFs_Cabecalho.csv").

    Returns:
        str: O nome da tabela higienizado e padronizado (ex: "_202401_nfs_cabecalho").
    """
    base_name = os.path.splitext(os.path.basename(file_name))[0].lower()
    sanitized = re.sub(r'[^a-z0-9_]', '_', base_name)
    sanitized = re.sub(r'_+', '_', sanitized)
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized


def sanitize_column_name(col_name: str) -> str:
    """Padroniza nomes de colunas do CSV para o formato snake_case em ASCII puro.

    Remove acentuações utilizando decomposição unicode (NFD), elimina caracteres
    especiais e substitui múltiplos espaços por sublinhados.

    Args:
        col_name (str): O nome original da coluna (ex: "CÓDIGO NCM/SH").

    Returns:
        str: O nome da coluna higienizado e padronizado (ex: "codigo_ncm_sh").
    """
    if not col_name:
        return ""

    # Decompõe caracteres acentuados para separar a letra do acento
    normalized = unicodedata.normalize('NFD', str(col_name))
    no_accents = "".join(
        [c for c in normalized if unicodedata.category(c) != 'Mn'])

    # Converte para minúsculas e limpa espaços nas pontas
    lowercased = no_accents.lower().strip()

    # Substitui caracteres não-alfanuméricos por sublinhado
    sanitized = re.sub(r'[^a-z0-9_]', '_', lowercased)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')

    return sanitized


def reset_application_storage():
    """Executa a exclusão de segurança de todos os arquivos físicos e temporários.

    Remove o arquivo 'data.duckdb' do banco DuckDB, exclui o arquivo ZIP em uploads
    e limpa recursivamente todos os diretórios de descompactação física.
    """
    # Deleta o banco de dados DuckDB físico do disco
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    # Deleta o arquivo compactado temporário em uploads/
    temp_zip_path = os.path.join(UPLOADS_DIR, "payload.zip")
    if os.path.exists(temp_zip_path):
        try:
            os.remove(temp_zip_path)
        except Exception:
            pass

    # Limpa recursivamente todos os CSVs e metadados extraídos em extracted/
    if os.path.exists(EXTRACTED_DIR):
        try:
            shutil.rmtree(EXTRACTED_DIR)
            # Reconstrói a pasta vazia
            os.makedirs(EXTRACTED_DIR, exist_ok=True)
        except Exception:
            pass
