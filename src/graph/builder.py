# -*- coding: utf-8 -*-
"""Módulo construtor da topologia do Grafo de Estados (LangGraph)."""

from src.models.state_model import AgentState
from langgraph.graph import StateGraph, END
from src.agents.agents_nodes import GraphNodes


class WorkflowGraphBuilder:
    """Implementa o padrão de design Builder para compilação do grafo."""

    def __init__(self):
        """Inicializa as instâncias de dependência dos nós e a estrutura do grafo."""
        self.nodes = GraphNodes()
        self.workflow = StateGraph(AgentState)

    def _register_nodes(self):
        """Registra os nós físicos de agentes na topologia do grafo."""
        self.workflow.add_node("supervisor", self.nodes.supervisor_node)
        self.workflow.add_node("analyst", self.nodes.analyst_node)
        self.workflow.add_node("chart_generator", self.nodes.chart_node)
        self.workflow.add_node("synthesizer", self.nodes.synthesis_node)
        self.workflow.set_entry_point("supervisor")

    def _setup_routing(self):
        """Configura os roteadores lógicos e as arestas direcionadas do grafo."""

        def router_after_supervisor(state: AgentState) -> str:
            """Roteia o fluxo a partir do planejamento do supervisor."""
            return state["next_step"]

        def router_after_analyst(state: AgentState) -> str:
            """Determina se o fluxo deve passar pelo gerador de gráficos antes da síntese."""
            query = state["user_query"].lower()
            if any(kw in query for kw in ["gráfico", "grafico", "plot", "desenhe"]):
                return "chart"
            return "synthesize"

        self.workflow.add_conditional_edges(
            "supervisor",
            router_after_supervisor,
            {
                "analyze": "analyst",
                "synthesize": "synthesizer"
            }
        )

        self.workflow.add_conditional_edges(
            "analyst",
            router_after_analyst,
            {
                "chart": "chart_generator",
                "synthesize": "synthesizer"
            }
        )

        self.workflow.add_edge("chart_generator", "synthesizer")
        self.workflow.add_edge("synthesizer", END)

    def build(self) -> StateGraph:
        """Executa a montagem lógica e compila o fluxo do StateGraph.

        Returns:
            StateGraph: O grafo de estados compilado e pronto para execução.
        """
        self._register_nodes()
        self._setup_routing()
        return self.workflow.compile()
