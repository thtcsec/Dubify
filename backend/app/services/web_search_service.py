"""Web Search Service — real-time news and web search for Research Video.

Supports multiple backends:
1. Tavily (recommended — built for AI research, includes news)
2. Brave Search API
3. Google Custom Search (Programmable Search Engine)
4. DuckDuckGo (free, no API key needed — fallback)

Configure SEARCH_API_KEY + SEARCH_PROVIDER in .env.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    published_date: str = ""  # ISO date or empty
    source: str = ""  # domain name
    score: float = 0.0  # relevance score (0-1)


class WebSearchService:
    """Multi-backend web search for real-time research."""

    def __init__(self):
        self.provider = (getattr(settings, "SEARCH_PROVIDER", "") or "auto").strip().lower()
        self.api_key = getattr(settings, "SEARCH_API_KEY", "") or ""

    def is_available(self) -> bool:
        """Check if any search backend is available."""
        if self.provider == "duckduckgo" or self.provider == "auto":
            return True  # DDG always available (no key needed)
        return bool(self.api_key)

    def search(
        self,
        query: str,
        *,
        max_results: int = 8,
        search_type: str = "news",  # "news", "web", "all"
        days_back: int = 7,
    ) -> List[SearchResult]:
        """Search the web for a topic.

        Args:
            query: Search query
            max_results: Maximum results to return
            search_type: "news" for recent news, "web" for general, "all" for both
            days_back: Only return results from the last N days (for news)
        """
        if not query.strip():
            return []

        # Try configured provider first
        if self.provider == "tavily" and self.api_key:
            results = self._search_tavily(query, max_results, search_type, days_back)
            if results:
                return results

        if self.provider == "brave" and self.api_key:
            results = self._search_brave(query, max_results, search_type, days_back)
            if results:
                return results

        if self.provider == "google" and self.api_key:
            results = self._search_google(query, max_results)
            if results:
                return results

        # Fallback: DuckDuckGo (no API key needed)
        return self._search_duckduckgo(query, max_results)

    def search_news(self, topic: str, max_results: int = 6, days_back: int = 3) -> List[SearchResult]:
        """Search specifically for recent news about a topic."""
        news_query = f"{topic} news {datetime.now().year}"
        return self.search(news_query, max_results=max_results, search_type="news", days_back=days_back)

    def _search_tavily(self, query: str, max_results: int, search_type: str, days_back: int) -> List[SearchResult]:
        """Tavily Search API — built for AI research, includes news mode."""
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": False,
                "include_raw_content": False,
            }
            if search_type == "news":
                payload["topic"] = "news"
                payload["days"] = days_back

            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:300],
                    published_date=item.get("published_date", ""),
                    source=self._extract_domain(item.get("url", "")),
                    score=item.get("score", 0.0),
                ))
            logger.info("Tavily search: %d results for '%s'", len(results), query[:50])
            return results

        except Exception as e:
            logger.warning("Tavily search failed: %s", e)
            return []

    def _search_brave(self, query: str, max_results: int, search_type: str, days_back: int) -> List[SearchResult]:
        """Brave Search API."""
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            if search_type == "news":
                url = "https://api.search.brave.com/res/v1/news/search"

            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            }
            params = {"q": query, "count": max_results}
            if search_type == "news" and days_back:
                freshness = f"pd{days_back}"  # past N days
                params["freshness"] = freshness

            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results_key = "news" if search_type == "news" else "web"
            items = data.get(results_key, {}).get("results", [])

            results = []
            for item in items[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", "")[:300],
                    published_date=item.get("age", ""),
                    source=self._extract_domain(item.get("url", "")),
                ))
            logger.info("Brave search: %d results for '%s'", len(results), query[:50])
            return results

        except Exception as e:
            logger.warning("Brave search failed: %s", e)
            return []

    def _search_google(self, query: str, max_results: int) -> List[SearchResult]:
        """Google Custom Search (Programmable Search Engine)."""
        try:
            cx = getattr(settings, "GOOGLE_SEARCH_CX", "") or ""
            if not cx:
                return []

            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": cx,
                "q": query,
                "num": min(max_results, 10),
                "sort": "date",  # Sort by date for freshness
            }
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("items", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", "")[:300],
                    source=self._extract_domain(item.get("link", "")),
                ))
            logger.info("Google search: %d results for '%s'", len(results), query[:50])
            return results

        except Exception as e:
            logger.warning("Google search failed: %s", e)
            return []

    def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        """DuckDuckGo Instant Answer API (free, no key needed)."""
        try:
            # Use DuckDuckGo HTML search (lite version)
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.post(url, data={"q": query}, headers=headers, timeout=10)
            resp.raise_for_status()

            # Parse results from HTML (simple regex extraction)
            results = []
            # Find result links and snippets
            links = re.findall(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.+?)</a>',
                resp.text,
            )
            snippets = re.findall(
                r'<a[^>]+class="result__snippet"[^>]*>(.+?)</a>',
                resp.text,
            )

            for i, (link_url, title) in enumerate(links[:max_results]):
                # Clean HTML tags from title
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""

                # DDG wraps URLs — extract actual URL
                actual_url = link_url
                uddg_match = re.search(r"uddg=([^&]+)", link_url)
                if uddg_match:
                    from urllib.parse import unquote
                    actual_url = unquote(uddg_match.group(1))

                results.append(SearchResult(
                    title=clean_title,
                    url=actual_url,
                    snippet=snippet[:300],
                    source=self._extract_domain(actual_url),
                ))

            logger.info("DuckDuckGo search: %d results for '%s'", len(results), query[:50])
            return results

        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
            return []

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else ""
