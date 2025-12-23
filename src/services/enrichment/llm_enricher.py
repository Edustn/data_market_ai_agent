"""Agent LLM para interpretar e normalizar dados de empresas."""

from typing import Any


class LlmEnricher:
    def __init__(self, llm_client: Any, view=None) -> None:
        self.llm = llm_client
        self.view = view

    def enrich(self, company: dict) -> dict:
        if not self.llm:
            # Sem cliente configurado, retorna dados originais.
            return company

        system_prompt, user_prompt = self._build_prompt(company)
        try:
            response = self.llm.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=600,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or ""
            if self.view:
                self.view.info(f"LLM output bruto para {company.get('name')}: {content[:200]}")
            return self._safe_parse(content, fallback=company)
        except Exception as exc:
            if self.view:
                self.view.warn(f"LLM falhou para {company.get('name')}: {exc}")
            # Falha no LLM: devolve dados originais para manter robustez.
            return company

    def _build_prompt(self, company: dict) -> tuple[str, str]:
        hints = company.get("hints") or []
        hints_text = "\n".join(
            f"- {h.get('title','')} {h.get('url','')} {h.get('content','')}"
            for h in hints
        )
        system_prompt = (
            "Você é um agente de enriquecimento corporativo. "
            "Retorne apenas JSON válido com os campos solicitados."
        )
        user_prompt = (
            "Use a entrada abaixo (nome, receita, setor) e as pistas de busca em `hints` (urls/snippets). "
            "Retorne apenas JSON com as chaves: "
            "website, linkedin, other_socials[], cnpjs[], addresses[], description, "
            "brands[{name, cnpjs?, products?}], products[], group, investors[], relations[], meta{confidence, sources[]}.\n"
            "- website: url oficial. Prefira domínio próprio da empresa.\n"
            "- linkedin: perfil da empresa.\n"
            "- other_socials: outras redes (instagram, twitter etc.).\n"
            "- cnpjs: extraia se aparecerem nos hints (use regex para padrões de CNPJ).\n"
            "- addresses: endereços físicos citados.\n"
            "- description: resumo curto e factual.\n"
            "- brands: marcas/subempresas citadas (ex.: StoneCo -> PagarMe, Ton, Linx), com CNPJs/produtos se possível.\n"
            "- products: categorias/produtos-chave normalizados (ex.: adquirência, gateway, orquestração).\n"
            "- group: holding/grupo econômico se existir.\n"
            "- investors: lista de investidores ou relações de capital mencionadas.\n"
            "- relations: correlações relevantes (ex.: pertence ao grupo X, parceria com Y).\n"
            "- meta.confidence: nota de confiança 0-1; meta.sources: lista de urls usadas.\n"
            "Priorize sites oficiais e perfis da empresa; não invente dados. "
            "Responda apenas com JSON no formato citado.\n\n"
            f"Entrada: {company}\n\n"
            f"Hints:\n{hints_text}"
        )
        return system_prompt, user_prompt

    def _safe_parse(self, content: str, fallback: dict) -> dict:
        import json

        try:
            return json.loads(content)
        except Exception:
            return fallback
