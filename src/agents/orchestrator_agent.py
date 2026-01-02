"""Agente que coordena ferramentas de busca, LLM e regras para enriquecer empresas.

Integração principal com OpenAI e, se disponível, com o framework Agno
para orquestração de agentes. Quando Agno não está instalado ou falha,
faz fallback para o enriquecimento simples via `LlmEnricher`.
"""

import os
from typing import Any, Optional

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

try:
    from agno.agent import Agent as AgnoAgent
except Exception:  # pragma: no cover - tolera ausência de Agno
    AgnoAgent = None

from models.company import Company
from models.brand import Brand
from services.enrichment.search_agent import SearchAgent
from services.enrichment.llm_enricher import LlmEnricher
from agno.models.openai import OpenAIChat



class OrchestratorAgent:
    def __init__(self, view) -> None:
        self.view = view
        self.search_agent = SearchAgent(view=view)
        self.openai_client = self._init_openai()
        self.llm_enricher = LlmEnricher(llm_client=self.openai_client, view=view)
        self.agno_agent = self._build_agno_agent()

    def _init_openai(self) -> Optional[OpenAI]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.view.warn(f'OPENAI_API_KEY não definido; LLM ficará inativo.{api_key}')
            return None
        masked = f"...{api_key[-4:]}" if len(api_key) >= 4 else "***"
        self.view.info(f"OPENAI_API_KEY detectada (mascarada): {masked}")
        return OpenAI(api_key=api_key)

    def _build_agno_agent(self) -> Any:
        """Constroi um agente Agno, se a lib estiver instalada."""
        if AgnoAgent is None:
            self.view.warn("Agno não instalado; usando fallback simples de enriquecimento.")
            return None
        if not self.openai_client:
            self.view.warn("Sem cliente OpenAI; Agno não será inicializado.")
            return None
        try:
            return AgnoAgent(
                model=OpenAIChat(id="gpt-5-mini"),
                instructions=(
                    "Enriquecer dados de empresas com website, linkedin, endereços, "
                    "CNPJs, marcas/subempresas, produtos e grupo econômico. "
                    "Responda em JSON com chaves: website, linkedin, cnpjs[], "
                    "addresses[], description, brands[{name}], products[], group, meta{}."
                ),
            )
        except Exception as exc:  # pragma: no cover
            self.view.warn(f"Falha ao iniciar Agno: {exc}. Usando fallback simples.")
            return None

    def enrich_batch(self, companies):
        enriched = []
        for company in companies:
            enriched.append(self.enrich_company(company))
        return enriched

    def enrich_company(self, company: Company) -> Company:
        self.view.info(f"Enriquecendo {company.name}")
        # Busca temática: tentar capturar marcas, grupo, CNPJ, produtos
        topics = ["site oficial", "linkedin", "marcas", "subsidiárias", "holding", "grupo econômico", "CNPJ", "produtos", "soluções"]
        hints = self.search_agent.search_multi(company.name, topics=topics, limit_per_topic=3)
        enriched_data = None

        if self.agno_agent:
            enriched_data = self._run_agno(company, hints)

        if not enriched_data:
            enriched_data = self.llm_enricher.enrich(
                {**company.__dict__, "hints": hints}
            )

        self._log_enrichment(company.name, enriched_data)
        return self._merge(company, enriched_data)

    def _run_agno(self, company: Company, hints) -> Optional[dict]:
        """Executa o agente Agno com prompt consolidado."""
        payload = {**company.__dict__, "hints": hints}
        try:
            # Nota: API pode variar conforme versão do Agno; ajuste se necessário.
            response = self.agno_agent.run(str(payload))
            if hasattr(response, "output") and isinstance(response.output, dict):
                return response.output
            if isinstance(response, dict):
                return response
        except Exception as exc:  # pragma: no cover
            self.view.warn(f"Falha ao rodar Agno: {exc}. Fallback para LLM simples.")
        return None

    def _merge(self, company: Company, enriched_data: dict) -> Company:
        company.website = enriched_data.get("website", company.website)
        company.linkedin = enriched_data.get("linkedin", company.linkedin)
        company.cnpjs = enriched_data.get("cnpjs", company.cnpjs)
        company.addresses = enriched_data.get("addresses", company.addresses)
        company.description = enriched_data.get("description", company.description)
        brands = enriched_data.get("brands") or []
        company.brands = [Brand(name=b["name"]) for b in brands if "name" in b]
        company.products = enriched_data.get("products", company.products)
        company.group = enriched_data.get("group", company.group)
        # Meta e campos extras ficam em company.meta para não perder informação
        extras = {}
        if enriched_data.get("meta"):
            extras.update(enriched_data["meta"])
        if enriched_data.get("investors"):
            extras["investors"] = enriched_data["investors"]
        if enriched_data.get("other_socials"):
            extras["other_socials"] = enriched_data["other_socials"]
        if enriched_data.get("relations"):
            extras["relations"] = enriched_data["relations"]
        company.meta.update(extras)
        return company

    def _log_enrichment(self, name: str, data: dict) -> None:
        if not data:
            self.view.warn(f"Enriquecimento retornou vazio para {name}")
            return
        filled = [
            key for key in ["website", "linkedin", "cnpjs", "addresses", "brands", "products", "group"]
            if data.get(key)
        ]
        self.view.info(f"Campos enriquecidos para {name}: {filled if filled else 'nenhum'}")
