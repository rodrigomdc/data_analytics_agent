# -*- coding: utf-8 -*-
"""Módulo de implementação dos nós de processamento cognitivo (Agentes)."""

import json
import time
import re
from src.models.state_model import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from src.tools.tools import query_duckdb_tool, create_chart_tool
from src.prompts.prompts import SUPERVISOR_PROMPT, SYNTHESIZE_RESPONSE_PROMPT, CHART_PROMPT, ANALYST_PROMPT
from src.utils.utils import setup_logger

logger = setup_logger("AgentsNodes")


def _clean_llm_output(response, fence_type: str = "") -> str:
    """Extrai texto do retorno da LLM de forma segura (trata str e list) e limpa blocos markdown.

    Args:
        response: Resposta retornada pela chamada .invoke() da LLM (AIMessage ou str).
        fence_type (str): Tipo de bloco markdown a ser removido (ex: 'json', 'sql').

    Returns:
        str: Conteúdo textual limpo e sem marcações markdown.
    """
    content = getattr(response, "content", response)
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and "text" in p:
                parts.append(p["text"])
        text = "".join(parts)
    else:
        text = str(content)

    text = text.strip()
    # Remove abertura de bloco ```json, ```sql, ```
    pattern = rf"^```(?:{fence_type})?\s*" if fence_type else r"^```(?:[a-zA-Z]+)?\s*"
    text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Remove fechamento de bloco ```
    if text.endswith("```"):
        text = text[:-3].strip()

    return text.strip()


class GraphNodes:
    """Classe que agrupa os nós de processamento executados pelo LangGraph."""

    def __init__(self):
        """Inicializa as instâncias centrais dos LLMs para os nós de decisão."""
        from config import LLM_MODEL

        self.llm_deterministic = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            temperature=0,
            max_retries=6
        )

        self.llm_creative = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            temperature=0.3,
            max_retries=6
        )

    def supervisor_node(self, state: AgentState) -> dict:
        """Analisa a intenção da pergunta do usuário e planeja a rota do grafo.

        Args:
            state (AgentState): O estado atual compartilhado do grafo.

        Returns:
            dict: Atualizações para as chaves 'next_step' e 'execution_logs'.
        """
        prompt = SUPERVISOR_PROMPT.format(
            data_dict=state['data_dict'],
            schema=state['schema'],
            user_query=state['user_query']
        )
        try:
            response = self.llm_deterministic.invoke(prompt)
            clean_content = _clean_llm_output(response, "json")
            res_json = json.loads(clean_content)
            next_step = res_json["next_step"]
        except Exception as e:
            logger.error(f"Erro ao executar o nó supervisor: {e}")
            next_step = "analyze"

        logs = state["execution_logs"] + \
            [f"Supervisor decidiu ir para: {next_step}"]
        return {"next_step": next_step, "execution_logs": logs}

    def analyst_node(self, state: AgentState) -> dict:
        """Gera e executa queries SQL no DuckDB para responder perguntas quantitativas.

        Args:
            state (AgentState): O estado atual compartilhado do grafo.

        Returns:
            dict: Atualizações para 'sql_query', 'dataframe' e 'execution_logs'.
        """
        time.sleep(1.2)  # Delay preventivo contra Rate Limit (Erro 429)

        prompt = ANALYST_PROMPT.format(
            user_query=state['user_query'],
            schema=state['schema'],
            data_dict=state['data_dict']
        )
        response = self.llm_deterministic.invoke(prompt)
        sql_query = _clean_llm_output(response, "sql")
        logs = state["execution_logs"] + [f"Analyst gerou SQL: {sql_query}"]
        try:
            df = query_duckdb_tool(sql_query)
            return {
                "sql_query": sql_query,
                "dataframe": df,
                "execution_logs": logs + ["Dados extraídos do DuckDB com sucesso."]
            }
        except Exception as e:
            logger.error(f"Erro ao executar SQL: {e}")
            return {
                "execution_logs": logs + [f"Erro ao executar SQL: {e}"],
                "dataframe": None
            }

    def chart_node(self, state: AgentState) -> dict:
        """Determina o melhor tipo de representação gráfica e desenha a figura Plotly.

        Args:
            state (AgentState): O estado atual compartilhado do grafo.

        Returns:
            dict: Atualizações para 'chart_fig' e 'execution_logs'.
        """
        if state["dataframe"] is None or state["dataframe"].empty:
            return {"execution_logs": state["execution_logs"] + ["Sem dados para gerar gráficos."]}

        time.sleep(1.2)  # Delay preventivo contra Rate Limit (Erro 429)

        columns_desc = ", ".join(list(state["dataframe"].columns))
        prompt = CHART_PROMPT.format(
            columns_desc=columns_desc,
            user_query=state['user_query']
        )
        try:
            response = self.llm_deterministic.invoke(prompt)
            clean_content = _clean_llm_output(response, "json")
            res_json = json.loads(clean_content)

            fig = create_chart_tool(
                df=state["dataframe"],
                chart_type=res_json["chart_type"],
                x_col=res_json["x_col"],
                y_col=res_json["y_col"],
                title=res_json["title"]
            )
            logs = state["execution_logs"] + \
                [f"Gráfico gerado: {res_json['title']}"]
            return {"chart_fig": fig, "execution_logs": logs}
        except Exception as e:
            logger.error(f"Falha ao plotar gráfico: {e}")
            return {"execution_logs": state["execution_logs"] + [f"Falha ao plotar gráfico: {e}"]}

    def synthesis_node(self, state: AgentState) -> dict:
        """Redige a narrativa explicativa final de negócios baseado nas tabelas e logs.

        Args:
            state (AgentState): O estado atual compartilhado do grafo.

        Returns:
            dict: Atualização para a chave 'explanation'.
        """
        time.sleep(1.2)  # Delay preventivo contra Rate Limit (Erro 429)

        table_md = state["dataframe"].to_markdown(
            index=False) if state["dataframe"] is not None else "Nenhum dado tabular."
        prompt = SYNTHESIZE_RESPONSE_PROMPT.format(
            user_query=state['user_query'],
            table_md=table_md,
            data_dict=state['data_dict']
        )
        response = self.llm_creative.invoke(prompt)
        explanation = _clean_llm_output(response)
        return {"explanation": explanation}
