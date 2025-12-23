"""Scraper da lista Valor 1000 (busca JSON da própria página)."""

from bs4 import BeautifulSoup
import requests
from html import unescape

from models.company import Company


class Valor1000Scraper:
    BASE_URL = "https://infograficos.valor.globo.com/valor1000/rankings/ranking-das-1000-maiores/2025"
    JSON_URL = "https://infovalorbucket.s3.amazonaws.com/arquivos/valor-1000/2025/ranking-das-1000-maiores/RankingValor10002025.json"

    def scrape(self, limit: int | None = None, use_cache: bool = True) -> list[Company]:
        # Tenta usar a fonte oficial em JSON consumida pelo front.
        data = self._fetch_json()
        if data:
            companies = self._parse_companies_from_json(data)
        else:
            html = self._fetch_html()
            companies = self._parse_companies(html)
        if limit:
            companies = companies[:limit]
        return companies

    def _fetch_html(self) -> str:
        response = requests.get(self.BASE_URL, timeout=30)
        response.raise_for_status()
        return response.text

    def _fetch_json(self):
        try:
            resp = requests.get(self.JSON_URL, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def _parse_companies(self, html: str) -> list[Company]:
        soup = BeautifulSoup(html, "html.parser")
        extracted = []
        for row in soup.select("tr.odd, tr.even"):
            tds = row.find_all("td")
            name_el = row.select_one("td.click-control")
            sector_idx = self._find_sector_idx(tds)
            sector_el = tds[sector_idx] if sector_idx is not None else None
            revenue_el = self._find_revenue_td(tds, start=sector_idx)

            if not name_el:
                continue
            extracted.append(
                Company(
                    name=name_el.get_text(strip=True),
                    revenue=self._safe_float(revenue_el),
                    sector=sector_el.get_text(strip=True) if sector_el else None,
                )
            )
        return extracted

    def _parse_companies_from_json(self, data: dict) -> list[Company]:
        raw_columns = data.get("columns") or []
        if not raw_columns:
            return []
        columns = [self._clean_text(part) for part in raw_columns[0].split(";")]
        try:
            name_idx = columns.index("Empresa")
            sector_idx = columns.index("Setor de atividade")
            revenue_idx = columns.index("Receita líquida<br>(em R$milhões)")
        except ValueError:
            name_idx, sector_idx, revenue_idx = 2, 4, 5

        extracted = []
        rows = data.get("data", {})
        for key in sorted(rows, key=lambda x: int(x)):
            row_text = rows[key][0]
            parts = [self._clean_text(p) for p in row_text.split(";")]
            if len(parts) <= max(name_idx, sector_idx, revenue_idx):
                continue
            extracted.append(
                Company(
                    name=parts[name_idx],
                    revenue=self._safe_float(parts[revenue_idx]),
                    sector=parts[sector_idx],
                )
            )
        return extracted

    def _safe_float(self, el):
        if el is None:
            return None
        try:
            if hasattr(el, "get_text"):
                text = el.get_text(strip=True)
            else:
                text = str(el).strip()
            return float(text.replace(".", "").replace(",", "."))
        except ValueError:
            return None

    def _find_sector_idx(self, tds):
        """Encontra índice do setor (td com style contendo text-align: left)."""
        for idx, td in enumerate(tds):
            style = (td.get("style") or "").lower()
            if "text-align" in style and "left" in style:
                return idx
        return None

    def _find_revenue_td(self, tds, start=None):
        """
        Retorna o primeiro <td> com conteúdo numérico visível após o índice informado.
        Usa o setor como referência para evitar pegar colunas de ranking/sorting.
        """
        start_pos = start if start is not None else -1
        for td in tds[start_pos + 1 :]:
            style = (td.get("style") or "").lower()
            if "display: none" in style:
                continue
            text = td.get_text(strip=True)
            if text and any(ch.isdigit() for ch in text):
                return td
        return None

    def _clean_text(self, text: str) -> str:
        soup = BeautifulSoup(text, "html.parser")
        return unescape(soup.get_text(strip=True))
