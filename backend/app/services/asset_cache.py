"""Asset Cache — SQLite-backed cache for models, rendered frames, and intermediate files.

Requirement 5: Centralized cache with LRU eviction, concurrent access, checksum validation.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class AssetCache:
    """SQLite-backed asset cache with LRU eviction and concurrent access (WAL mode)."""

    def __init__(self, max_size_gb: float = 10.0):
        self.cache_dir = settings.STORAGE_DIR / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "cache.db"
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database with WAL mode for concurrent access."""
        with self._conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    checksum TEXT,
                    created_at REAL NOT NULL,
                    last_access REAL NOT NULL,
                    ttl_seconds REAL DEFAULT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_access ON cache_entries(last_access)
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path), timeout=10)

    def get(self, key: str) -> Optional[Path]:
        """Get cached file path by key. Returns None if not found or expired."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT path, ttl_seconds, created_at FROM cache_entries WHERE key = ?",
                (key,),
            ).fetchone()

            if not row:
                return None

            path, ttl, created_at = Path(row[0]), row[1], row[2]

            # Check TTL expiration
            if ttl and (time.time() - created_at) > ttl:
                self.evict(key)
                return None

            # Check file exists
            if not path.exists():
                self.evict(key)
                return None

            # Update last access time
            conn.execute(
                "UPDATE cache_entries SET last_access = ? WHERE key = ?",
                (time.time(), key),
            )
            return path

    def put(self, key: str, source_path: Path, ttl: Optional[float] = None) -> Path:
        """Store a file in cache. Returns the cached file path."""
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Determine cache path
        ext = source_path.suffix
        cache_path = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}{ext}"

        # Copy file to cache
        import shutil
        shutil.copy2(source_path, cache_path)

        size = cache_path.stat().st_size
        checksum = self._file_checksum(cache_path)
        now = time.time()

        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries (key, path, size_bytes, checksum, created_at, last_access, ttl_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, str(cache_path), size, checksum, now, now, ttl))

        # Enforce size limit
        self._enforce_size_limit()
        return cache_path

    def evict(self, key: str) -> None:
        """Remove a cache entry and its file."""
        with self._conn() as conn:
            row = conn.execute("SELECT path FROM cache_entries WHERE key = ?", (key,)).fetchone()
            if row:
                path = Path(row[0])
                path.unlink(missing_ok=True)
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        now = time.time()
        removed = 0
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT key, path FROM cache_entries
                WHERE ttl_seconds IS NOT NULL AND (? - created_at) > ttl_seconds
            """, (now,)).fetchall()

            for key, path_str in rows:
                Path(path_str).unlink(missing_ok=True)
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                removed += 1

        if removed:
            logger.info("Cache cleanup: removed %d expired entries.", removed)
        return removed

    def validate(self) -> int:
        """Validate cached entries against checksums. Remove corrupted entries."""
        removed = 0
        with self._conn() as conn:
            rows = conn.execute("SELECT key, path, checksum FROM cache_entries").fetchall()
            for key, path_str, expected_checksum in rows:
                path = Path(path_str)
                if not path.exists():
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    removed += 1
                elif expected_checksum and self._file_checksum(path) != expected_checksum:
                    logger.warning("Cache corruption detected for key: %s", key)
                    path.unlink(missing_ok=True)
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    removed += 1

        if removed:
            logger.info("Cache validation: removed %d corrupted/missing entries.", removed)
        return removed

    def total_size(self) -> int:
        """Total size of cached files in bytes."""
        with self._conn() as conn:
            row = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM cache_entries").fetchone()
            return row[0] if row else 0

    def entry_count(self) -> int:
        """Number of cache entries."""
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()
            return row[0] if row else 0

    def _enforce_size_limit(self) -> None:
        """Evict LRU entries until total size is under limit."""
        total = self.total_size()
        if total <= self.max_size_bytes:
            return

        with self._conn() as conn:
            # Get entries ordered by last access (oldest first)
            rows = conn.execute(
                "SELECT key, path, size_bytes FROM cache_entries ORDER BY last_access ASC"
            ).fetchall()

            freed = 0
            for key, path_str, size in rows:
                if total - freed <= self.max_size_bytes:
                    break
                Path(path_str).unlink(missing_ok=True)
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                freed += size

            if freed:
                logger.info("Cache LRU eviction: freed %.1f MB.", freed / (1024 * 1024))

    @staticmethod
    def _file_checksum(path: Path) -> str:
        """Compute MD5 checksum of a file."""
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
