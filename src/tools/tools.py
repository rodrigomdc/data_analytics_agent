# -*- coding: utf-8 -*-
"""
Módulo: src/tools/tools.py
Descrição: Biblioteca unificada de ferramentas técnicas (Actions) consumidas pelos nós do Grafo.
           Contém as funções decoradas que executam queries SQL de leitura no banco analítico DuckDB
           e montam gráficos estatísticos interativos utilizando Plotly Express.
"""


import re
import unicodedata
import pandas as pd
import plotly.express as px
from src.db_manager.duckdb_manager import DuckDBManager


def query_duckdb_tool(sql_query: str) -> pd.DataFrame:
    """Executa consultas de leitura no DuckDB normalizando a query para o padrão NFC.

    Args:
        sql_query (str): A query SQL bruta gerada pela IA.

    Returns:
        pd.DataFrame: DataFrame contendo o resultado da consulta analítica.
    """
    normalized_query = unicodedata.normalize('NFC', sql_query)
    db = DuckDBManager()
    return db.execute_query(normalized_query)


def format_axis_label(label: str) -> str:
    """Formata esteticamente nomes de colunas do banco em rótulos limpos de eixos.

    Args:
        label (str): Nome técnico original da coluna.

    Returns:
        str: Rótulo formatado em Title Case e com siglas corrigidas.
    """
    if not label:
        return ""
    clean_label = str(label).replace("_", " ").strip().title()
    siglas = {
        r"\bUf\b": "UF", r"\bCnpj\b": "CNPJ", r"\bCpf\b": "CPF",
        r"\bNf\b": "NF", r"\bNfs\b": "NFs", r"\bIe\b": "IE",
        r"\bNcm\b": "NCM", r"\bCfop\b": "CFOP"
    }
    for padrao, substituicao in siglas.items():
        clean_label = re.sub(padrao, substituicao,
                             clean_label, flags=re.IGNORECASE)
    return clean_label


def create_chart_tool(df: pd.DataFrame, chart_type: str, x_col: str, y_col: str, title: str) -> px.bar:
    """Gera uma figura de visualização interativa do Plotly baseada em regras de Data Viz.

    Args:
        df (pd.DataFrame): O DataFrame de dados.
        chart_type (str): Tipo do gráfico ('bar', 'line', 'pie', 'scatter').
        x_col (str): Nome da coluna para o eixo X.
        y_col (str): Nome da coluna para o eixo Y.
        title (str): Título do gráfico.

    Returns:
        px.bar: Objeto de figura gráfica do Plotly gerado.

    Raises:
        ValueError: Se o DataFrame fornecido estiver vazio.
    """
    chart_type = chart_type.lower()
    template = "plotly_white"

    if df.empty:
        raise ValueError("DataFrame vazio. Impossível gerar gráfico.")

    fig = None

    if chart_type == "bar":
        is_temporal = any(df[x_col].astype(str).str.match(r'^\d{4}-\d{2}') |
                          df[x_col].isin(['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                                          'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']))
        if not is_temporal:
            df = df.sort_values(by=y_col, ascending=True)

        if len(df) > 8:
            fig = px.bar(df, x=y_col, y=x_col, orientation='h',
                         title=title, template=template)
            fig.update_layout(xaxis_title=format_axis_label(
                y_col), yaxis_title=format_axis_label(x_col))
        else:
            fig = px.bar(df, x=x_col, y=y_col, title=title, template=template)
            fig.update_layout(xaxis_title=format_axis_label(
                x_col), yaxis_title=format_axis_label(y_col))

    elif chart_type == "line":
        fig = px.line(df, x=x_col, y=y_col, title=title,
                      template=template, markers=True)
        fig.update_layout(xaxis_title=format_axis_label(
            x_col), yaxis_title=format_axis_label(y_col))

    elif chart_type == "pie":
        if len(df) > 5:
            df = df.sort_values(by=y_col, ascending=False)
            fig = px.bar(df, x=x_col, y=y_col,
                         title=f"{title} (Convertido para barras)", template=template)
            fig.update_layout(xaxis_title=format_axis_label(
                x_col), yaxis_title=format_axis_label(y_col))
        else:
            fig = px.pie(df, names=x_col, values=y_col,
                         title=title, template=template, hole=0.3)
            fig.update_layout(legend_title_text=format_axis_label(x_col))
    else:
        fig = px.scatter(df, x=x_col, y=y_col, title=title, template=template)
        fig.update_layout(xaxis_title=format_axis_label(
            x_col), yaxis_title=format_axis_label(y_col))

    return fig
