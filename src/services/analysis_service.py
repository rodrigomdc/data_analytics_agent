# -*- coding: utf-8 -*-
"""Serviço para geração de análises preliminares de dados via Pandas."""

import pandas as pd
from src.db_manager.duckdb_manager import DuckDBManager


class ColumnProfiler:
    """Classifica colunas semanticamente para evitar estatísticas sem sentido.

    Diferencia identificadores, campos numéricos reais, categóricos, texto livre
    e datas, aplicando a métrica estatística adequada para cada tipo detectado.
    """

    ID_KEYWORDS = ["chave", "cpf", "cnpj", "inscri", "codigo", "código", "id_", "_id"]

    @staticmethod
    def classify_column(series: pd.Series, col_name: str, n_rows: int) -> str:
        """Determina o tipo semântico de uma coluna com base em nome e distribuição."""
        name_lower = col_name.lower()
        n_unique = series.nunique(dropna=True)
        cardinality_ratio = n_unique / n_rows if n_rows > 0 else 0

        # Heurística por nome: campos claramente identificadores
        if any(kw in name_lower for kw in ColumnProfiler.ID_KEYWORDS):
            return "identificador"

        # Tenta conversão para data antes de decidir se é numérico/categórico
        if series.dtype == object:
            parsed_dates = pd.to_datetime(series, errors="coerce")
            taxa_sucesso = parsed_dates.notna().mean()
            if taxa_sucesso > 0.9:
                return "data"

        if pd.api.types.is_numeric_dtype(series):
            # Alta cardinalidade em coluna numérica costuma ser identificador
            if cardinality_ratio > 0.9:
                return "identificador"
            return "numerica"

        # Colunas de texto: decide entre categórica e texto livre pela cardinalidade
        if cardinality_ratio > 0.5 or n_unique > 50:
            return "texto_livre"
        return "categorica"

    @staticmethod
    def build_profile(df: pd.DataFrame) -> dict:
        """Constrói o dicionário de perfil estatístico para cada coluna do DataFrame."""
        n_rows = len(df)
        profile = {}

        for col in df.columns:
            series = df[col]
            tipo = ColumnProfiler.classify_column(series, col, n_rows)
            n_nulos = series.isna().sum()
            pct_nulos = round(100 * n_nulos / n_rows, 2) if n_rows else 0

            entry = {
                "tipo_detectado": tipo,
                "nulos": int(n_nulos),
                "pct_nulos": pct_nulos,
                "valores_unicos": int(series.nunique(dropna=True)),
            }

            try:
                if tipo == "numerica":
                    entry["estatisticas"] = series.describe().to_dict()
                elif tipo == "categorica":
                    top = series.value_counts(dropna=True).head(10)
                    entry["top_valores"] = (100 * top / n_rows).round(2).to_dict()
                elif tipo == "data":
                    parsed = pd.to_datetime(series, errors="coerce")
                    entry["data_min"] = str(parsed.min())
                    entry["data_max"] = str(parsed.max())
                elif tipo == "identificador":
                    entry["exemplos"] = series.dropna().unique()[:3].tolist()
                elif tipo == "texto_livre":
                    entry["comprimento_medio"] = round(series.dropna().astype(str).str.len().mean(), 1)
            except Exception:
                # Garante que uma coluna problemática não derrube o perfil inteiro
                entry["erro_processamento"] = True

            profile[col] = entry

        return profile


class PreliminaryAnalysisService:
    """Classe responsável por extrair estatísticas básicas das tabelas."""

    @staticmethod
    def get_analysis(table_name: str) -> dict:
        """Busca a tabela no DuckDB e retorna a amostra e o perfil semântico das colunas.

        Args:
            table_name (str): Nome da tabela no banco de dados.

        Returns:
            dict: Dicionário contendo head (amostra) e profile (perfil por coluna).
        """
        db = DuckDBManager()
        df = db.execute_query(f'SELECT * FROM "{table_name}"')

        return {
            "head": df.head(5),
            "profile": ColumnProfiler.build_profile(df)
        }