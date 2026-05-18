"""Bounded streaming uploads for large media files."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


async def save_upload_limited(upload: UploadFile, dest: Path, max_bytes: int) -> int:
    """Stream upload to disk; abort and remove partial file if over max_bytes."""
    written = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with dest.open("wb") as buffer:
            while True:
                chunk = await upload.read(_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
                    )
                buffer.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    if written == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return written
