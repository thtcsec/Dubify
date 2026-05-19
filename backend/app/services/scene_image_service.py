"""Fetch topic-relevant stock/Wikipedia images per studio scene (no random placeholders)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Dubify/1.0 (research-video)"}
_GENERIC_SCENE = re.compile(
    r"^(hook|story|insight|close|cảnh\s*\d+|scene\s*\d+|mở đầu|kết)$",
    re.IGNORECASE,
)


def _download_image(url: str, dest: Path, timeout: int = 20) -> bool:
    try:
        response = requests.get(url, timeout=timeout, headers=_HEADERS, stream=True)
        if response.status_code != 200:
            return False
        content_type = (response.headers.get("content-type") or "").lower()
        if "image" not in content_type and not url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)
        return dest.exists() and dest.stat().st_size > 4_000
    except Exception as exc:
        logger.debug("Image download failed %s: %s", url[:80], exc)
        return False


def _pexels_image_url(query: str, page: int = 1) -> Optional[str]:
    api_key = (settings.PEXELS_API_KEY or "").strip()
    if not api_key or not query.strip():
        return None
    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": query.strip()[:120],
                "per_page": 1,
                "page": max(1, page),
                "orientation": "portrait",
            },
            headers={"Authorization": api_key},
            timeout=12,
        )
        if response.status_code != 200:
            return None
        photos = (response.json() or {}).get("photos") or []
        if not photos:
            return None
        src = (photos[0].get("src") or {}).get("large") or (photos[0].get("src") or {}).get("medium")
        return str(src) if src else None
    except Exception as exc:
        logger.debug("Pexels search failed: %s", exc)
        return None


def _wikimedia_commons_image(search: str) -> Optional[str]:
    """Search Wikimedia Commons for on-topic photos (tech events, logos, etc.)."""
    term = (search or "").strip()
    if len(term) < 3:
        return None
    try:
        response = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"{term} conference technology",
                "gsrnamespace": 6,
                "gsrlimit": 8,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 1400,
            },
            headers=_HEADERS,
            timeout=14,
        )
        if response.status_code != 200:
            return None
        pages = (response.json() or {}).get("query", {}).get("pages") or {}
        for page in sorted(pages.keys(), key=lambda k: int(k)):
            infos = (pages[page] or {}).get("imageinfo") or []
            if not infos:
                continue
            url = infos[0].get("thumburl") or infos[0].get("url")
            if url and isinstance(url, str):
                return url
    except Exception as exc:
        logger.debug("Commons image search failed: %s", exc)
    return None


def fetch_wikipedia_bundle(topic: str, lang: str = "vi") -> dict[str, str]:
    """Wikipedia summary + thumbnail for research context."""
    wiki_lang = "vi" if (lang or "").startswith("vi") else "en"
    title = topic.strip().replace(" ", "_")
    url = f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
    try:
        response = requests.get(url, timeout=10, headers=_HEADERS)
        if response.status_code != 200:
            return {}
        data = response.json()
        extract = (data.get("extract") or "").strip()
        page_url = (data.get("content_urls") or {}).get("desktop", {}).get("page", "")
        thumb = (data.get("thumbnail") or {}).get("source", "")
        return {
            "title": str(data.get("title") or topic),
            "extract": extract[:1400],
            "page_url": str(page_url or ""),
            "thumbnail_url": str(thumb or ""),
        }
    except Exception as exc:
        logger.debug("Wikipedia bundle skipped: %s", exc)
        return {}


def _scene_image_queries(topic: str, scene_title: str, scene_body: str, scene_index: int) -> list[str]:
    """Build stock-photo search queries biased toward tech / events — never random."""
    topic_clean = re.sub(r"\s+", " ", (topic or "").strip())
    title = "" if _GENERIC_SCENE.match((scene_title or "").strip()) else (scene_title or "").strip()
    body = re.sub(r"\[.*?\]", " ", scene_body or "")
    body = re.sub(r"\s+", " ", body).strip()[:80]

    queries: list[str] = []
    if topic_clean:
        queries.append(f"{topic_clean} developer conference keynote")
        queries.append(f"{topic_clean} technology presentation")
    if title:
        queries.append(f"{topic_clean} {title} technology".strip())
    if body:
        queries.append(f"{topic_clean} {body}".strip())

    low = topic_clean.lower()
    if "google" in low or "i/o" in low or "io" in low.split():
        queries.extend(
            [
                "Google I/O developer conference stage",
                "Google keynote presentation",
                "Android developer conference",
            ]
        )
    queries.extend(
        [
            "software developer conference audience",
            "tech keynote stage presentation",
            "silicon valley technology conference",
        ]
    )

    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        q = q.strip()
        if len(q) >= 4 and q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:8]


def resolve_scene_image(
    *,
    topic: str,
    scene_title: str,
    scene_body: str,
    output_path: Path,
    fallback_path: Path,
    scene_index: int = 0,
    wiki_thumbnail_url: str = "",
) -> Path:
    """Topic-relevant background; gradient fallback only if all sources fail."""
    queries = _scene_image_queries(topic, scene_title, scene_body, scene_index)

    if scene_index == 0 and wiki_thumbnail_url:
        if _download_image(wiki_thumbnail_url, output_path):
            logger.info("Scene %d image: Wikipedia thumbnail", scene_index)
            return output_path

    for qi, query in enumerate(queries):
        pexels_url = _pexels_image_url(query, page=scene_index + 1 + qi)
        if pexels_url and _download_image(pexels_url, output_path):
            logger.info("Scene %d image: Pexels (%s)", scene_index, query[:48])
            return output_path

        commons_url = _wikimedia_commons_image(query)
        if commons_url and _download_image(commons_url, output_path):
            logger.info("Scene %d image: Wikimedia Commons (%s)", scene_index, query[:48])
            return output_path

    logger.warning(
        "Scene %d: no stock image matched for topic=%r — using gradient (add PEXELS_API_KEY for better results)",
        scene_index,
        topic[:40],
    )
    return fallback_path
