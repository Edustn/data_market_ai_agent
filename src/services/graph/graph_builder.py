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
        # Após inserir dados, cria conexões de similaridade básicas
        self._create_similarity_by_product()
        self._create_similarity_by_sector()

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

        # Relations/correlações extra em meta (ex.: companies correlacionadas, marcas irmãs)
        self._upsert_relations_from_meta(company)

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

    def _upsert_relations_from_meta(self, company: Company) -> None:
        relations = company.meta.get("relations") if company.meta else None
        if not relations:
            return
        for rel in relations:
            # Aceita string simples ou dict; string vira RELATED_TO Company
            if isinstance(rel, str):
                target_name = rel
                rel_type = "RELATED_TO"
                label = "Company"
            elif isinstance(rel, dict):
                target_name = rel.get("target")
                rel_type = (rel.get("type") or "RELATED_TO").upper()
                label = rel.get("label", "Company")
            else:
                continue
            if not target_name:
                continue
            self._merge_relation(company.name, target_name, rel_type, label)

    def _merge_relation(self, source_name: str, target_name: str, rel_type: str, target_label: str) -> None:
        query = f"""
        MERGE (src:Company {{name: $src_name}})
        MERGE (t:{target_label} {{name: $tgt_name}})
        MERGE (src)-[:{rel_type}]->(t)
        """
        self.client.run(query, {"src_name": source_name, "tgt_name": target_name})

    def _create_similarity_by_product(self) -> None:
        """Cria relações SIMILAR_TO entre empresas que compartilham categorias de produto."""
        query = """
        MATCH (c1:Company)-[:OFFERS]->(p:ProductCategory)<-[:OFFERS]-(c2:Company)
        WHERE id(c1) < id(c2)
        WITH c1, c2, collect(DISTINCT p.name) AS categories
        MERGE (c1)-[r:SIMILAR_TO {basis: 'product_category'}]->(c2)
        SET r.shared_categories = categories
        """
        self.client.run(query)

    def _create_similarity_by_sector(self) -> None:
        """Cria relações SIMILAR_TO entre empresas do mesmo setor."""
        query = """
        MATCH (c1:Company),(c2:Company)
        WHERE c1.sector = c2.sector AND c1.sector IS NOT NULL AND id(c1) < id(c2)
        MERGE (c1)-[:SIMILAR_TO {basis: 'sector'}]->(c2)
        """
        self.client.run(query)
