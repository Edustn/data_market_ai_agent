"""Controller responsável por obter a lista inicial de empresas."""

from services.scraping.valor1000_scraper import Valor1000Scraper


class ScrapeController:
    def __init__(self, view) -> None:
        self.view = view
        self.scraper = Valor1000Scraper()

    def fetch_companies(self, limit: int | None = None, use_cache: bool = True):
        companies = self.scraper.scrape(limit=limit, use_cache=use_cache)
        self.view.info(f"{len(companies)} empresas coletadas da fonte primária")
        return companies
