"""Controller de persistência no grafo."""

from services.graph.graph_builder import GraphBuilder


class GraphController:
    def __init__(self, view) -> None:
        self.view = view
        self.builder = GraphBuilder(view=view)

    def persist(self, companies):
        self.view.info("Persistindo dados no Graph DB")
        self.builder.upsert(companies)
        self.view.info("Persistência finalizada")
