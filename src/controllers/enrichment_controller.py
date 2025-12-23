"""Controller que orquestra enriquecimento via agentes."""

from agents.orchestrator_agent import OrchestratorAgent


class EnrichmentController:
    def __init__(self, view) -> None:
        self.view = view
        self.agent = OrchestratorAgent(view=view)

    def enrich_companies(self, companies):
        self.view.info("Iniciando enriquecimento por agentes")
        enriched = self.agent.enrich_batch(companies)
        self.view.info("Enriquecimento concluído")
        return enriched
