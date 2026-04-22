"""
Global Logging Configuration for Dubify.

Features:
- Centralized logging setup with file rotation
- Automatic masking of sensitive data (API keys, model paths, secrets)
- Structured log format with timestamps
- Console + File output
"""

import logging
import logging.handlers
import re
import os
from pathlib import Path
from typing import List, Pattern


# Patterns to mask in log output
SENSITIVE_PATTERNS: List[Pattern] = [
    # API keys (common formats: sk-xxx, gsk_xxx, AIza, etc.)
    re.compile(r'(sk-[a-zA-Z0-9]{20,})', re.IGNORECASE),
    re.compile(r'(gsk_[a-zA-Z0-9]{20,})', re.IGNORECASE),
    re.compile(r'(AIza[a-zA-Z0-9_-]{30,})', re.IGNORECASE),
    # Generic key=value patterns for Authorization headers
    re.compile(r'(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}', re.IGNORECASE),
    # Environment variable values that look like keys
    re.compile(r'(api[_-]?key["\s:=]+)["\']?([a-zA-Z0-9_\-\.]{10,})["\']?', re.IGNORECASE),
]

# Keywords that indicate sensitive context
SENSITIVE_KEYWORDS = [
    'api_key', 'api-key', 'apikey', 'secret', 'password', 'token',
    'authorization', 'bearer', 'credential',
]


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._mask_sensitive(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._mask_sensitive(str(v)) if isinstance(v, str) else v
                               for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._mask_sensitive(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True

    def _mask_sensitive(self, text: str) -> str:
        """Replace sensitive data with masked version."""
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(self._replacer, text)
        return text

    @staticmethod
    def _replacer(match: re.Match) -> str:
        """Replace matched sensitive data, keeping first/last few chars."""
        full = match.group(0)
        # For Bearer tokens, keep the "Bearer " prefix
        if full.lower().startswith('bearer'):
            return 'Bearer ***MASKED***'
        # For other patterns, show first 4 and last 2 chars
        if len(full) > 8:
            return f"{full[:4]}***{full[-2:]}"
        return "***MASKED***"


class DubifyLogger:
    """Global logging configuration for Dubify."""

    _initialized = False
    LOG_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "logs"
    LOG_FILE = "dubify.log"
    MAX_BYTES = 5 * 1024 * 1024  # 5MB per file
    BACKUP_COUNT = 5  # Keep 5 rotated files

    @classmethod
    def setup(cls, level: str = "INFO"):
        """Initialize global logging. Call once at app startup."""
        if cls._initialized:
            return

        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

        log_level = getattr(logging, level.upper(), logging.INFO)

        # Root logger config
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Format
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(cls.LOG_DIR / cls.LOG_FILE),
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        root_logger.addHandler(file_handler)

        # Suppress noisy third-party loggers
        for noisy in ["urllib3", "httpcore", "httpx", "watchfiles", "multipart"]:
            logging.getLogger(noisy).setLevel(logging.WARNING)

        cls._initialized = True
        logging.getLogger(__name__).info("Dubify logging initialized (level=%s)", level)

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance. Ensures setup has been called."""
        if not cls._initialized:
            cls.setup()
        return logging.getLogger(name)


def mask_api_key(key: str) -> str:
    """Utility to mask an API key for display purposes (e.g., in API responses)."""
    if not key or len(key) < 8:
        return "***" if key else ""
    return f"{key[:4]}{'*' * (len(key) - 6)}{key[-2:]}"
