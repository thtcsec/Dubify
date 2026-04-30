import os
import re
import yt_dlp
import logging
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from urllib.parse import quote
from typing import Dict, Any, Optional, Iterable, List, Tuple
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


class URLServiceError(Exception):
    """User-facing error for URL metadata/download failures."""

    def __init__(self, message: str, hints: Optional[List[str]] = None):
        super().__init__(message)
        self.hints = hints or []

class URLService:
    def __init__(self):
        self.download_path = settings.INPUT_DIR
        self.session = requests.Session()
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8,vi;q=0.6",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    def _resolve_redirect_url(self, url: str) -> str:
        """Resolve short links to final URL when possible."""
        headers = dict(self.default_headers)
        if "douyin.com" in url or "tiktok.com" in url or "b23.tv" in url:
            headers["User-Agent"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"
            headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
            headers["Referer"] = "https://www.bilibili.com/" if "b23.tv" in url else "https://www.douyin.com/"
        
        try:
            # We use a custom redirect handler to catch the video ID if it gets lost
            response = self.session.get(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=10,
            )
            
            final_url = response.url
            
            # Check redirect history for a video ID if final_url doesn't have it
            if "/video/" not in final_url and "modal_id=" not in final_url:
                for resp in response.history:
                    if "/video/" in resp.url:
                        return resp.url
                    # Sometimes the ID is in a Location header even if final one is home
                    location = resp.headers.get("Location", "")
                    if "/video/" in location:
                        return location
            
            # Last ditch effort: search the text for a video ID
            if "/video/" not in final_url:
                match = re.search(r'video/(\d+)', response.text)
                if match:
                    return f"https://www.douyin.com/video/{match.group(1)}"
            
            return final_url or url
        except Exception:
            return url

    def _normalize_url(self, url: str) -> str:
        """Normalize complex share links into standalone paths supported by yt-dlp."""
        url = url.strip()
        
        # Remove any sharing text prefix
        if "http" in url:
            url = url[url.find("http"):]
        # Split on whitespace/newline in case user pasted metadata
        url = url.split()[0]

        # Resolve short links often used by TikTok/Douyin sharing.
        if "v.douyin.com" in url or "vm.tiktok.com" in url or "vt.tiktok.com" in url or "b23.tv" in url:
            url = self._resolve_redirect_url(url)

        if "bilibili.com" in url:
            match = re.search(r"(https?://(?:www\.)?bilibili\.com/video/[A-Za-z0-9]+)", url)
            if match:
                return match.group(1)

        # Handle Douyin modal_id share links
        if "douyin.com" in url and "modal_id=" in url:
            match = re.search(r"modal_id=(\d+)", url)
            if match:
                return f"https://www.douyin.com/video/{match.group(1)}"

        # Normalize generic Douyin URLs to canonical video URL when possible.
        if "douyin.com" in url:
            match = re.search(r"/video/(\d+)", url)
            if match:
                return f"https://www.douyin.com/video/{match.group(1)}"

        return url

    def _douyin_video_id(self, url: str) -> Optional[str]:
        match = re.search(r"douyin\.com/video/(\d+)", url)
        return match.group(1) if match else None

    def _build_common_ydl_opts(self, download: bool) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": settings.YTDLP_SOCKET_TIMEOUT,
            "http_headers": dict(self.default_headers),
        }
        if settings.YTDLP_PROXY:
            opts["proxy"] = settings.YTDLP_PROXY

        if download:
            opts.update({
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": os.path.join(str(self.download_path), "%(title)s.%(ext)s"),
            })
        else:
            opts["format"] = "best"

        return opts

    def _build_douyin_bootstrap_cookiefile(self, url: str) -> Optional[str]:
        video_id = self._douyin_video_id(url)
        if not video_id:
            return None

        session = requests.Session()
        session.headers.update(self.default_headers)

        try:
            session.head("https://www.douyin.com/", allow_redirects=False, timeout=8)
            session.get(f"https://www.douyin.com/video/{video_id}", allow_redirects=True, timeout=8)
        except Exception as exc:
            logger.warning("Douyin cookie bootstrap request failed: %s", exc)

        if not session.cookies:
            return None

        cookie_names = {cookie.name for cookie in session.cookies}
        if "ttwid" not in cookie_names and "__ac_nonce" not in cookie_names:
            return None

        cookie_path = settings.TEMP_DIR / f"douyin_bootstrap_{video_id}.cookies.txt"
        try:
            jar = MozillaCookieJar(str(cookie_path))
            for cookie in session.cookies:
                jar.set_cookie(cookie)
            jar.save(ignore_discard=True, ignore_expires=True)
            return str(cookie_path)
        except Exception as exc:
            logger.warning("Could not persist Douyin bootstrap cookies: %s", exc)
            return None

    def _iter_ydl_profiles(self, url: str, download: bool) -> Iterable[Tuple[str, Dict[str, Any]]]:
        base = self._build_common_ydl_opts(download=download)
        yield ("default", base)

        if "douyin.com" in url:
            cookiefile = self._build_douyin_bootstrap_cookiefile(url)
            if cookiefile:
                opts = dict(base)
                opts["cookiefile"] = cookiefile
                yield ("cookie-bootstrap:douyin", opts)

        browsers = [b.strip().lower() for b in settings.YTDLP_COOKIES_FROM_BROWSERS.split(",") if b.strip()]
        for browser in browsers:
            opts = dict(base)
            opts["cookiesfrombrowser"] = (browser,)
            yield (f"cookiesfrombrowser:{browser}", opts)

        if settings.YTDLP_COOKIE_FILE:
            cookie_path = Path(settings.YTDLP_COOKIE_FILE).expanduser()
            if cookie_path.exists():
                opts = dict(base)
                opts["cookiefile"] = str(cookie_path)
                yield (f"cookiefile:{cookie_path}", opts)

        # Last fallback: allow Android client extraction for TikTok family sites.
        if "douyin.com" in url or "tiktok.com" in url:
            mobile = dict(base)
            mobile["extractor_args"] = {"tiktok": {"app_info": ["musical_ly/35.1.3/2023501030"]}}
            yield ("tiktok-mobile-client", mobile)

    def _run_ydl(self, url: str, download: bool) -> Dict[str, Any]:
        errors: List[str] = []
        for profile_name, opts in self._iter_ydl_profiles(url, download=download):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=download)
                    if download:
                        if info and "entries" in info and info["entries"]:
                            return {
                                "info": info["entries"][0],
                                "path": ydl.prepare_filename(info["entries"][0]),
                            }
                        return {"info": info, "path": ydl.prepare_filename(info)}
                    return {"info": info}
            except Exception as exc:
                message = str(exc)
                errors.append(f"[{profile_name}] {message}")
                logger.warning("yt-dlp profile %s failed: %s", profile_name, message)

        raise URLServiceError(
            "Could not access this video with current extraction profiles.",
            hints=self._build_cookie_hints(url, errors),
        )

    def _build_cookie_hints(self, url: str, errors: List[str]) -> List[str]:
        hints: List[str] = []
        if "douyin.com" in url or "tiktok.com" in url:
            hints.append("Open the video once in your browser, then retry in Dubify immediately.")
            hints.append("Set YTDLP_COOKIES_FROM_BROWSERS in .env (example: chrome,edge).")
            hints.append("Or export cookies.txt and set YTDLP_COOKIE_FILE in .env.")
        if errors:
            hints.append(f"Last extractor error: {errors[-1][:300]}")
        if "douyin.com" in url:
            hints.append("Optional: configure DOUYIN_FALLBACK_API_BASE and DOUYIN_FALLBACK_API_KEY in .env for a stable external parser fallback.")
        return hints

    def _provider_headers(self) -> Dict[str, str]:
        headers = dict(self.default_headers)
        api_key = settings.DOUYIN_FALLBACK_API_KEY.strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key
        return headers

    def _search_field(self, payload: Any, candidate_keys: List[str]) -> Optional[Any]:
        target = {key.lower() for key in candidate_keys}
        queue: List[Any] = [payload]

        while queue:
            current = queue.pop(0)
            if isinstance(current, dict):
                for key, value in current.items():
                    if key.lower() in target and value not in (None, ""):
                        return value
                    queue.append(value)
            elif isinstance(current, list):
                queue.extend(current)

        return None

    def _collect_candidate_urls(self, payload: Any) -> List[str]:
        result: List[str] = []

        def walk(node: Any, parent_key: str = "") -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(value, key)
                return
            if isinstance(node, list):
                for item in node:
                    walk(item, parent_key)
                return
            if not isinstance(node, str) or not node.startswith("http"):
                return

            key = parent_key.lower()
            if any(tag in key for tag in ("play", "download", "video", "url", "src", "wm")):
                result.append(node)

        walk(payload)

        # Deduplicate while preserving order.
        unique: List[str] = []
        seen = set()
        for item in result:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    def _douyin_external_provider_data(self, url: str) -> Optional[Dict[str, Any]]:
        base = settings.DOUYIN_FALLBACK_API_BASE.strip().rstrip("/")
        if not base:
            return None

        endpoints = [
            (f"{base}/api/hybrid/video_data", {"url": url, "minimal": "false"}),
            (f"{base}/api/download", {"url": url, "prefix": "true", "with_watermark": "false"}),
        ]

        for endpoint, params in endpoints:
            try:
                response = self.session.get(
                    endpoint,
                    params=params,
                    headers=self._provider_headers(),
                    timeout=12,
                )
                if response.status_code >= 400:
                    logger.warning(
                        "Douyin external provider returned status %s for %s",
                        response.status_code,
                        endpoint,
                    )
                    continue

                payload = response.json()
                if not isinstance(payload, dict):
                    continue

                detail = payload.get("detail")
                if isinstance(detail, dict) and detail.get("code", 0) >= 400:
                    continue

                title = self._search_field(payload, ["title", "desc", "description", "aweme_desc"])
                duration_raw = self._search_field(payload, ["duration", "duration_ms"])
                thumbnail = self._search_field(payload, ["thumbnail", "cover", "cover_url", "thumbnail_url"])
                candidate_urls = self._collect_candidate_urls(payload)

                duration = 0
                try:
                    if duration_raw is not None:
                        duration = int(float(duration_raw))
                        if duration > 10000:
                            duration = int(duration / 1000)
                except Exception:
                    duration = 0

                return {
                    "title": str(title) if title else f"Douyin video {self._douyin_video_id(url) or ''}".strip(),
                    "duration": duration,
                    "thumbnail": str(thumbnail) if thumbnail else None,
                    "candidate_urls": candidate_urls,
                    "source": "douyin-external-provider",
                }
            except Exception as exc:
                logger.warning("Douyin external provider call failed (%s): %s", endpoint, exc)

        return None

    def _download_from_candidates(self, candidates: List[str], output_prefix: str) -> Optional[str]:
        if not candidates:
            return None

        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", output_prefix)
        destination = self.download_path / f"{safe_name}.mp4"

        for candidate in candidates:
            try:
                with self.session.get(candidate, headers=self.default_headers, stream=True, timeout=20) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if "video" not in content_type and "octet-stream" not in content_type:
                        continue

                    with open(destination, "wb") as file_obj:
                        for chunk in response.iter_content(chunk_size=1024 * 512):
                            if chunk:
                                file_obj.write(chunk)
                    if destination.exists() and destination.stat().st_size > 0:
                        return str(destination)
            except Exception as exc:
                logger.warning("Candidate media URL failed: %s", exc)

        return None

    def _douyin_item_info(self, url: str) -> Optional[Dict[str, Any]]:
        video_id = self._douyin_video_id(url)
        if not video_id:
            return None

        api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}"
        try:
            response = self.session.get(api_url, headers=self.default_headers, timeout=12)
            response.raise_for_status()
            payload = response.json()
            items = payload.get("item_list") or []
            return items[0] if items else None
        except Exception as exc:
            logger.warning("Douyin item API fallback failed for %s: %s", video_id, exc)
            return None

    def _fallback_info(self, url: str) -> Optional[Dict[str, Any]]:
        if "douyin.com" in url:
            external = self._douyin_external_provider_data(url)
            if external:
                return {
                    "title": external.get("title") or f"Douyin video {self._douyin_video_id(url) or ''}".strip(),
                    "duration": external.get("duration") or 0,
                    "thumbnail": external.get("thumbnail"),
                    "source": external.get("source") or "douyin-external-provider",
                    "url": url,
                }

        # Douyin item API fallback
        if "douyin.com" in url:
            item = self._douyin_item_info(url)
            if item:
                duration_ms = item.get("duration") or 0
                cover = (((item.get("video") or {}).get("cover") or {}).get("url_list") or [None])[0]
                return {
                    "title": item.get("desc") or f"Douyin video {self._douyin_video_id(url) or ''}".strip(),
                    "duration": int(duration_ms / 1000) if duration_ms else 0,
                    "thumbnail": cover,
                    "source": "douyin-fallback",
                    "url": url,
                }

        # TikTok oEmbed fallback
        if "tiktok.com" in url:
            try:
                oembed = self.session.get(
                    f"https://www.tiktok.com/oembed?url={quote(url, safe='')}",
                    headers=self.default_headers,
                    timeout=12,
                )
                oembed.raise_for_status()
                data = oembed.json()
                return {
                    "title": data.get("title") or "TikTok video",
                    "duration": 0,
                    "thumbnail": data.get("thumbnail_url"),
                    "source": "tiktok-oembed-fallback",
                    "url": url,
                }
            except Exception as exc:
                logger.warning("TikTok oEmbed fallback failed: %s", exc)

        return None

    def _download_douyin_fallback(self, url: str) -> Optional[str]:
        external = self._douyin_external_provider_data(url)
        if external:
            external_result = self._download_from_candidates(
                external.get("candidate_urls") or [],
                f"douyin_provider_{self._douyin_video_id(url) or os.urandom(4).hex()}",
            )
            if external_result:
                return external_result

        item = self._douyin_item_info(url)
        if not item:
            return None

        video = item.get("video") or {}
        candidates = []
        for key in ("play_addr", "play_addr_h264", "download_addr", "play_addr_lowbr"):
            addr = video.get(key) or {}
            url_list = addr.get("url_list") or []
            for u in url_list:
                # Typically, replacing 'playwm' with 'play' removes the watermark.
                candidates.append(u.replace("playwm", "play"))
            candidates.extend(url_list)

        if not candidates:
            return None
        return self._download_from_candidates(candidates, f"douyin_{self._douyin_video_id(url) or os.urandom(4).hex()}")

    def get_info(self, url: str) -> Dict[str, Any]:
        """Fetch video metadata without downloading."""
        try:
            url = self._normalize_url(url)
            if not settings.allow_network_downloads():
                raise URLServiceError(
                    "Offline mode does not allow fetching video metadata from remote URLs.",
                    hints=["Switch to Hybrid or Online mode to import video URLs."],
                )
            
            # Handle Google Drive separately if needed
            if "drive.google.com" in url:
                file_id = self._extract_gdrive_id(url)
                if not file_id:
                    raise Exception("Invalid Google Drive URL")
                return {
                    "title": f"Google Drive File ({file_id})",
                    "duration": 0,
                    "thumbnail": "https://p7.hiclipart.com/preview/452/63/873/google-drive-logo-google-docs-google-google-cloud-storage.jpg",
                    "source": "gdrive",
                    "url": url
                }
            result = self._run_ydl(url, download=False)
            info = result["info"]
            return {
                "title": info.get("title", "Unknown Title"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail"),
                "source": info.get("extractor"),
                "url": info.get("webpage_url") or url,
            }
        except URLServiceError:
            fallback = self._fallback_info(url)
            if fallback:
                return fallback
            raise
        except Exception as e:
            raise URLServiceError(f"Failed to fetch video info: {str(e)}")

    def download_video(self, url: str) -> str:
        """Download video and return local path."""
        try:
            url = self._normalize_url(url)
            if not settings.allow_network_downloads():
                raise URLServiceError(
                    "Offline mode does not allow downloading remote videos.",
                    hints=["Switch to Hybrid or Online mode to import from URL."],
                )
            
            if "drive.google.com" in url:
                return self._download_from_gdrive(url)

            result = self._run_ydl(url, download=True)
            return result["path"]
        except URLServiceError:
            if "douyin.com" in url:
                fallback_path = self._download_douyin_fallback(url)
                if fallback_path:
                    return fallback_path
            raise
        except Exception as e:
            raise URLServiceError(f"Download failed: {str(e)}")

    def _extract_gdrive_id(self, url: str) -> Optional[str]:
        match = re.search(r"/d/([^/]+)", url)
        return match.group(1) if match else None

    def _download_from_gdrive(self, url: str) -> str:
        file_id = self._extract_gdrive_id(url)
        if not file_id:
            raise URLServiceError("Could not extract GDrive ID")
        
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        dest_path = os.path.join(str(self.download_path), f"gdrive_{file_id}.mp4")
        
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()
        
        max_size = 5 * 1024 * 1024 * 1024  # 5 GB
        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if chunk:
                    downloaded += len(chunk)
                    if downloaded > max_size:
                        response.close()
                        os.remove(dest_path)
                        raise URLServiceError("File too large (max 5 GB).")
                    f.write(chunk)
        response.close()
        
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            raise URLServiceError("Downloaded file is empty.")
        return dest_path
