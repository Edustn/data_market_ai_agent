"""
CLI para orquestrar scraping, enriquecimento e escrita no Graph DB.
Este módulo delega a controllers especializados para cada etapa.
"""

import argparse
import os

from controllers.scrape_controller import ScrapeController
from controllers.enrichment_controller import EnrichmentController
from controllers.graph_controller import GraphController
from views.cli import CliView


class App:
    def __init__(self) -> None:
        self.view = CliView()
        self.scrape_controller = ScrapeController(self.view)
        self.enrichment_controller = EnrichmentController(self.view)
        self.graph_controller = GraphController(self.view)

    def run(self, limit: int | None = None, use_cache: bool = True) -> None:
        """Pipeline principal: scrape -> enriquecimento -> persistência."""
        self.view.info("Iniciando pipeline")
        companies = self.scrape_controller.fetch_companies(limit=limit, use_cache=use_cache)
        enriched = self.enrichment_controller.enrich_companies(companies)
        self.graph_controller.persist(enriched)
        self.view.info("Pipeline concluída")


def main():
    parser = argparse.ArgumentParser(description="Pipeline de scraping, enriquecimento e grafos.")
    parser.add_argument("--limit", type=int, default=None, help="Limita quantidade de empresas processadas.")
    parser.add_argument("--no-cache", action="store_true", help="Desabilita cache local do HTML.")
    parser.add_argument("--neo4j-uri", type=str, default=None, help="URI do Neo4j (ex.: bolt://localhost:7687).")
    parser.add_argument("--neo4j-user", type=str, default=None, help="Usuário do Neo4j.")
    parser.add_argument("--neo4j-password", type=str, default=None, help="Senha do Neo4j.")
    args = parser.parse_args()

    # Override de configs via CLI (prioridade acima do .env)
    if args.neo4j_uri:
        os.environ["NEO4J_URI"] = args.neo4j_uri
    if args.neo4j_user:
        os.environ["NEO4J_USER"] = args.neo4j_user
    if args.neo4j_password:
        os.environ["NEO4J_PASSWORD"] = args.neo4j_password

    app = App()
    app.run(limit=args.limit, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
