"""Ferramenta de busca externa.

Fluxo: tenta Tavily se `TAVILY_API_KEY` estiver definido; caso contrário,
usa um fallback sem credenciais via DuckDuckGo HTML.
"""

import os
from typing import Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


class SearchAgent:
    def __init__(self, view=None) -> None:
        self.view = view
        self.api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_endpoint = "https://api.tavily.com/search"
        self._log_key_masked()

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        if self.api_key:
            results = self._search_tavily(query, limit)
            if results:
                return results
        return self._search_duckduckgo(query, limit)

    def _search_tavily(self, query: str, limit: int) -> list[dict[str, Any]]:
        try:
            resp = requests.post(
                self.tavily_endpoint,
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": limit,
                    "include_domains": [],
                    "search_depth": "basic",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or []
            return [
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": r.get("content"),
                }
                for r in results
                if r.get("url")
            ]
        except Exception:
            return []

    def _log_key_masked(self):
        if not self.view:
            return
        if not self.api_key:
            self.view.warn("TAVILY_API_KEY não definida; usando fallback DuckDuckGo.")
        else:
            masked = f"...{self.api_key[-4:]}" if len(self.api_key) >= 4 else "***"
            self.view.info(f"TAVILY_API_KEY detectada (mascarada): {masked}")

    def _search_duckduckgo(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Fallback sem credenciais usando DuckDuckGo HTML."""
        try:
            resp = requests.get(
                "https://duckduckgo.com/html",
                params={"q": query, "kl": "br-pt"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for a in soup.select("a.result__a")[:limit]:
                title = a.get_text(strip=True)
                url = a.get("href")
                snippet_el = a.find_parent("div", class_="result__body")
                snippet = ""
                if snippet_el:
                    snippet = snippet_el.get_text(" ", strip=True)
                if url:
                    results.append({"title": title, "url": url, "content": snippet})
            return results
        except Exception:
            return []
