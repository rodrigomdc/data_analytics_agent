# -*- coding: utf-8 -*-
"""Módulo de definição do schema de estado do Grafo de Estados (LangGraph)."""

from typing import TypedDict, List, Optional
import pandas as pd


class AgentState(TypedDict):
    """Representa o estado compartilhado que trafega ao longo do fluxo do Grafo.

    Este modelo baseado em TypedDict define rigidamente a estrutura das variáveis de
    fluxo (scratchpad) lidas, modificadas e persistidas por cada um dos nós especialistas
    do sistema.

    Attributes:
        user_query (str): A pergunta em linguagem natural feita pelo usuário.
        data_dict (str): String formatada em JSON contendo o dicionário de dados (metadados).
        schema (str): String descritiva gerada pelo DuckDB contendo as tabelas e colunas físicas.
        next_step (str): O destino lógico planejado pelo supervisor ("analyze" ou "synthesize").
        sql_query (Optional[str]): A instrução de consulta SQL gerada pelo nó analista.
        dataframe (Optional[pd.DataFrame]): Os dados tabulares resultantes da execução do SQL.
        chart_fig (Optional[object]): Objeto de figura do Plotly representando o gráfico gerado.
        chart_config (Optional[dict]): Dicionário JSON contendo os parâmetros de plotagem do gráfico.
        explanation (Optional[str]): A resposta descritiva final voltada para negócios.
        execution_logs (List[str]): Histórico sequencial das ações tomadas pelos agentes.
    """
    user_query: str
    data_dict: str
    schema: str
    next_step: str
    sql_query: Optional[str]
    dataframe: Optional[pd.DataFrame]
    chart_fig: Optional[object]
    chart_config: Optional[dict]
    explanation: Optional[str]
    execution_logs: List[str]
