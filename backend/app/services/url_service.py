import os
import re
import yt_dlp
from typing import Dict, Any, Optional
from app.core.config import settings

class URLService:
    def __init__(self):
        self.download_path = settings.INPUT_DIR

    def get_info(self, url: str) -> Dict[str, Any]:
        """Fetch video metadata without downloading."""
        try:
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

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "Unknown Title"),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail"),
                    "source": info.get("extractor"),
                    "url": url
                }
        except Exception as e:
            raise Exception(f"Failed to fetch video info: {str(e)}")

    def download_video(self, url: str) -> str:
        """Download video and return local path."""
        try:
            if "drive.google.com" in url:
                return self._download_from_gdrive(url)

            output_template = os.path.join(self.download_path, "%(title)s.%(ext)s")
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': output_template,
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

    def _extract_gdrive_id(self, url: str) -> Optional[str]:
        match = re.search(r"/d/([^/]+)", url)
        return match.group(1) if match else None

    def _download_from_gdrive(self, url: str) -> str:
        # Implementation for public gdrive files using direct download link
        file_id = self._extract_gdrive_id(url)
        if not file_id:
            raise Exception("Could not extract GDrive ID")
        
        # This is a common way to download public GDrive files
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        dest_path = os.path.join(self.download_path, f"gdrive_{file_id}.mp4")
        
        # Note: Large files might need a confirmation token handling, but start simple
        import requests
        response = requests.get(download_url, stream=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
        
        return dest_path
