# -*- coding: utf-8 -*-
"""Serviço para geração de análises preliminares de dados via Pandas."""

import pandas as pd
from src.db_manager.duckdb_manager import DuckDBManager


class ColumnProfiler:
    """Classifica colunas semanticamente para evitar estatísticas sem sentido."""

    ID_KEYWORDS = ["chave", "cpf", "cnpj", "inscri", "codigo", "código", "id_", "_id"]

    # Palavras-chave de tempo: termos curtos (dia, mes, ano, hora) exigem
    # separador de palavra para reduzir falsos positivos (ex.: "Diagnóstico")
    TIME_KEYWORDS_LONGAS = ["data", "periodo", "período", "timestamp", "emissao", "emissão"]
    TIME_KEYWORDS_CURTAS = ["ano", "mes", "mês", "dia", "hora", "minuto"]

    MONEY_KEYWORDS = ["valor", "custo", "despesa", "invoice", "entrada", "saida", "saída",
                      "preco", "preço", "total", "montante", "receita"]

    @staticmethod
    def _nome_sugere_tempo(name_lower: str) -> bool:
        """Verifica palavras-chave de tempo, exigindo separador para termos curtos."""
        if any(kw in name_lower for kw in ColumnProfiler.TIME_KEYWORDS_LONGAS):
            return True
        # Para termos curtos, exige que apareçam como palavra isolada
        # (separada por espaço, underscore, barra ou hífen), não como substring solta
        tokens = name_lower.replace("_", " ").replace("/", " ").replace("-", " ").split()
        return any(kw in tokens for kw in ColumnProfiler.TIME_KEYWORDS_CURTAS)

    @staticmethod
    def _tentar_converter_data(series: pd.Series):
        """Tenta converter a série para datetime, independente do dtype de entrada.

        Retorna a série convertida e a taxa de sucesso do parse (ignorando nulos originais).
        """
        try:
            parsed = pd.to_datetime(series, errors="coerce")
            nao_nulos_original = series.notna().sum()
            if nao_nulos_original == 0:
                return parsed, 0.0
            taxa_sucesso = parsed.notna().sum() / nao_nulos_original
            return parsed, taxa_sucesso
        except Exception:
            return series, 0.0

    @staticmethod
    def _tentar_converter_numero(series: pd.Series):
        """Tenta converter a série para float, tratando formatos BR (vírgula decimal,
        ponto de milhar) e formatos já numéricos, independente do dtype de entrada.
        """
        if pd.api.types.is_numeric_dtype(series):
            return series.astype(float), 1.0

        try:
            limpo = (
                series.astype(str)
                .str.strip()
                .str.replace(r"[R\$\s]", "", regex=True)
                .str.replace(".", "", regex=False)   # remove separador de milhar (padrão BR)
                .str.replace(",", ".", regex=False)   # troca vírgula decimal por ponto
            )
            parsed = pd.to_numeric(limpo, errors="coerce")
            nao_nulos_original = series.notna().sum()
            if nao_nulos_original == 0:
                return parsed, 0.0
            taxa_sucesso = parsed.notna().sum() / nao_nulos_original
            return parsed, taxa_sucesso
        except Exception:
            return series, 0.0

    @staticmethod
    def classify_column(series: pd.Series, col_name: str, n_rows: int):
        """Classifica a coluna e retorna também a série já convertida quando aplicável.

        Returns:
            tuple: (tipo_detectado: str, series_convertida: pd.Series)
        """
        name_lower = col_name.lower()
        n_unique = series.nunique(dropna=True)
        cardinality_ratio = n_unique / n_rows if n_rows > 0 else 0

        if any(kw in name_lower for kw in ColumnProfiler.ID_KEYWORDS):
            return "identificador", series

        # Já é datetime nativo (ex.: veio do DuckDB como DATE/TIMESTAMP)
        if pd.api.types.is_datetime64_any_dtype(series):
            return "data", series

        nome_sugere_tempo = ColumnProfiler._nome_sugere_tempo(name_lower)
        if nome_sugere_tempo:
            parsed, taxa = ColumnProfiler._tentar_converter_data(series)
            if taxa > 0.9:
                return "data", parsed

        nome_sugere_valor = any(kw in name_lower for kw in ColumnProfiler.MONEY_KEYWORDS)
        if nome_sugere_valor:
            parsed, taxa = ColumnProfiler._tentar_converter_numero(series)
            if taxa > 0.9:
                return "monetaria", parsed

        if pd.api.types.is_numeric_dtype(series):
            if cardinality_ratio > 0.9:
                return "identificador", series
            return "numerica", series

        if cardinality_ratio > 0.5 or n_unique > 50:
            return "texto_livre", series
        return "categorica", series
    
    @staticmethod
    def _evolucao_trimestral(df: pd.DataFrame, col_data: str, col_valor: str = None):
        """Gera a evolução trimestral de contagem (e soma, se houver coluna monetária)."""
        parsed = pd.to_datetime(df[col_data], errors="coerce")
        validos = parsed.notna()

        if validos.sum() == 0:
            return None

        trimestre = parsed[validos].dt.to_period("Q").astype(str)

        if col_valor:
            valores = df.loc[validos, col_valor]
            agrupado = pd.DataFrame({"Trimestre": trimestre.values, "Valor": valores.values})
            resultado = agrupado.groupby("Trimestre").agg(
                Quantidade_de_Registros=("Valor", "count"),
                Soma_dos_Valores=("Valor", "sum")
            ).reset_index()
        else:
            resultado = trimestre.value_counts().sort_index().reset_index()
            resultado.columns = ["Trimestre", "Quantidade_de_Registros"]

        return resultado.to_dict("records")

    @staticmethod
    def build_profile(df: pd.DataFrame) -> dict:
        n_rows = len(df)
        profile = {}
        colunas_data = []
        colunas_valor = []
        series_convertidas = {}

        for col in df.columns:
            series_original = df[col]
            tipo, serie_convertida = ColumnProfiler.classify_column(series_original, col, n_rows)
            series_convertidas[col] = serie_convertida

            n_nulos = series_original.isna().sum()
            pct_nulos = round(100 * n_nulos / n_rows, 2) if n_rows else 0

            entry = {
                "tipo_detectado": tipo,
                "nulos": int(n_nulos),
                "pct_nulos": pct_nulos,
                "valores_unicos": int(series_original.nunique(dropna=True)),
            }

            if tipo == "numerica":
                try:
                    entry["estatisticas"] = serie_convertida.describe().to_dict()
                except Exception:
                    entry["estatisticas"] = None

            elif tipo == "monetaria":
                # Cada métrica é calculada isoladamente: uma falha pontual
                # não derruba as demais métricas já calculadas com sucesso
                for chave, func in [
                    ("soma_total", lambda s: float(s.sum())),
                    ("media", lambda s: float(s.mean())),
                    ("mediana", lambda s: float(s.median())),
                    ("maior_valor", lambda s: float(s.max())),
                    ("menor_valor", lambda s: float(s.min())),
                ]:
                    try:
                        entry[chave] = func(serie_convertida.dropna())
                    except Exception:
                        entry[chave] = None
                colunas_valor.append(col)

            elif tipo == "categorica":
                try:
                    top = series_original.value_counts(dropna=True).head(10)
                    entry["top_valores"] = (100 * top / n_rows).round(2).to_dict()
                except Exception:
                    entry["top_valores"] = {}

            elif tipo == "data":
                validos = serie_convertida.dropna()
                entry["data_min"] = str(validos.min()) if not validos.empty else None
                entry["data_max"] = str(validos.max()) if not validos.empty else None
                try:
                    entry["intervalo_dias"] = int((validos.max() - validos.min()).days) if not validos.empty else None
                except Exception:
                    entry["intervalo_dias"] = None
                colunas_data.append(col)

            elif tipo == "identificador":
                try:
                    entry["exemplos"] = series_original.dropna().unique()[:3].tolist()
                except Exception:
                    entry["exemplos"] = []

            elif tipo == "texto_livre":
                try:
                    entry["comprimento_medio"] = round(series_original.dropna().astype(str).str.len().mean(), 1)
                except Exception:
                    entry["comprimento_medio"] = None
                try:
                    normalizado = series_original.dropna().astype(str).str.strip().str.upper()
                    top_normalizado = normalizado.value_counts().head(10)
                    entry["top_valores_normalizados"] = (100 * top_normalizado / n_rows).round(2).to_dict()
                except Exception:
                    entry["top_valores_normalizados"] = {}

            profile[col] = entry

        col_valor_principal = colunas_valor[0] if colunas_valor else None
        for col_data in colunas_data:
            try:
                df_temp = df.copy()
                df_temp[col_data] = series_convertidas[col_data]
                if col_valor_principal:
                    df_temp[col_valor_principal] = series_convertidas[col_valor_principal]
                profile[col_data]["evolucao_trimestral"] = ColumnProfiler._evolucao_trimestral(
                    df_temp, col_data, col_valor_principal
                )
            except Exception:
                profile[col_data]["evolucao_trimestral"] = None

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
        df = db.execute_query(f'SELECT * FROM "{table_name}" LIMIT 50000')

        return {
            "head": df.head(5),
            "profile": ColumnProfiler.build_profile(df)
        }