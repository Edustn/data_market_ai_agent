"""Constrói/upserta nodes e relações no grafo."""

from typing import Iterable

from models.company import Company
from services.graph.neo4j_client import Neo4jClient


class GraphBuilder:
    def __init__(self, view) -> None:
        self.view = view
        self.client = Neo4jClient()

    def upsert(self, companies: Iterable[Company]) -> None:
        for company in companies:
            self._upsert_company(company)

    def _upsert_company(self, company: Company) -> None:
        query = """
        MERGE (c:Company {name: $name})
        SET c.revenue = $revenue,
            c.sector = $sector,
            c.website = $website,
            c.linkedin = $linkedin,
            c.cnpjs = $cnpjs,
            c.addresses = $addresses,
            c.description = $description
        """
        params = {
            "name": company.name,
            "revenue": company.revenue,
            "sector": company.sector,
            "website": company.website,
            "linkedin": company.linkedin,
            "cnpjs": company.cnpjs,
            "addresses": company.addresses,
            "description": company.description,
        }
        self.client.run(query, params)

        if company.group:
            self._upsert_holding(company.name, company.group)

        for brand in company.brands:
            self._upsert_brand(company.name, brand.name, brand.cnpjs)

        if company.products:
            self._upsert_products(company.name, company.products)

    def _upsert_brand(self, company_name: str, brand_name: str, cnpjs=None) -> None:
        query = """
        MERGE (c:Company {name: $company_name})
        MERGE (b:Brand {name: $brand_name})
        SET b.cnpjs = $cnpjs
        MERGE (c)-[:OPERATES_AS]->(b)
        """
        self.client.run(
            query,
            {"company_name": company_name, "brand_name": brand_name, "cnpjs": cnpjs or []},
        )

    def _upsert_holding(self, company_name: str, holding_name: str) -> None:
        query = """
        MERGE (c:Company {name: $company_name})
        MERGE (h:Holding {name: $holding_name})
        MERGE (c)-[:BELONGS_TO]->(h)
        """
        self.client.run(query, {"company_name": company_name, "holding_name": holding_name})

    def _upsert_products(self, company_name: str, products: list[str]) -> None:
        for product in products:
            query = """
            MERGE (c:Company {name: $company_name})
            MERGE (p:ProductCategory {name: $product})
            MERGE (c)-[:OFFERS]->(p)
            """
            self.client.run(query, {"company_name": company_name, "product": product})
