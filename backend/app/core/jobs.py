"""
Job Manager with persistence, history, and cancel/pause support.

Features:
- JSON file persistence (survives restarts)
- Full job history with pagination
- Cancel and pause/resume support via threading events
- Automatic cleanup of old jobs
"""

import uuid
import json
import threading
import logging
import time
import queue
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Persistence file location
JOBS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "storage" / "jobs.json"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobType(str, Enum):
    DUBBING = "dubbing"
    STUDIO = "studio"
    SHORTS = "shorts"


class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        # Cancel/pause signals per job
        self._cancel_events: Dict[str, threading.Event] = {}
        self._pause_events: Dict[str, threading.Event] = {}
        self._subscribers: List[queue.Queue] = []
        self._load()

    # ─── Persistence ────────────────────────────────────────────────────

    def _load(self):
        """Load jobs from disk on startup."""
        try:
            if JOBS_FILE.exists():
                with open(JOBS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.jobs = data if isinstance(data, dict) else {}
                # Mark any previously "processing" jobs as failed (unclean shutdown)
                for job_id, job in self.jobs.items():
                    if job.get("status") in (JobStatus.PROCESSING, JobStatus.PENDING):
                        job["status"] = JobStatus.FAILED
                        job["error"] = "Server restarted while job was in progress"
                        job["updated_at"] = datetime.now().isoformat()
                logger.info(f"Loaded {len(self.jobs)} jobs from history.")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load job history: {e}. Starting fresh.")
            self.jobs = {}

    def _save(self):
        """Persist jobs to disk atomically (write to temp, then rename)."""
        try:
            JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = JOBS_FILE.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.jobs, f, indent=2, ensure_ascii=False, default=str)
            # Atomic rename (safe on most OS)
            tmp_path.replace(JOBS_FILE)
        except IOError as e:
            logger.error(f"Failed to persist jobs: {e}")

    def _emit_event(self, event_type: str, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return
        payload = {
            "type": event_type,
            "job_id": job_id,
            "job": dict(job),
        }
        stale_subscribers: List[queue.Queue] = []
        for subscriber in self._subscribers:
            try:
                subscriber.put_nowait(payload)
            except Exception:
                stale_subscribers.append(subscriber)
        if stale_subscribers:
            self._subscribers = [subscriber for subscriber in self._subscribers if subscriber not in stale_subscribers]

    def subscribe(self) -> queue.Queue:
        subscriber: queue.Queue = queue.Queue()
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue):
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    # ─── Job Creation ───────────────────────────────────────────────────

    def create_job(self, filename: str, job_type: str = JobType.DUBBING) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self.jobs[job_id] = {
                "id": job_id,
                "filename": filename,
                "type": job_type,
                "status": JobStatus.PENDING,
                "progress": 0,
                "message": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "output_path": None,
                "error": None,
            }
            self._cancel_events[job_id] = threading.Event()
            self._pause_events[job_id] = threading.Event()
            self._save()
            self._emit_event("created", job_id)
        return job_id

    def register_job(self, job_id: str, filename: str = "untitled", **extra: Any) -> str:
        """Register a job with a pre-generated external ID."""
        with self._lock:
            self.jobs[job_id] = {
                "id": job_id,
                "filename": filename,
                "type": extra.pop("job_type", JobType.DUBBING),
                "status": JobStatus.PENDING,
                "progress": 0,
                "message": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "output_path": None,
                "error": None,
                **extra,
            }
            self._cancel_events[job_id] = threading.Event()
            self._pause_events[job_id] = threading.Event()
            self._save()
            self._emit_event("created", job_id)
        return job_id

    # ─── Job Updates ────────────────────────────────────────────────────

    def update_job(
        self,
        job_id: str,
        status: JobStatus,
        output_path: Optional[str] = None,
        error: Optional[str] = None,
        message: Optional[str] = None,
        progress: Optional[int] = None,
    ):
        with self._lock:
            if job_id not in self.jobs:
                return
            job = self.jobs[job_id]
            job["status"] = status
            job["updated_at"] = datetime.now().isoformat()

            if status == JobStatus.PROCESSING and not job.get("started_at"):
                job["started_at"] = datetime.now().isoformat()
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                job["completed_at"] = datetime.now().isoformat()
            if status == JobStatus.COMPLETED:
                job["progress"] = 100

            if output_path:
                job["output_path"] = output_path
            if error:
                job["error"] = error
            if message is not None:
                job["message"] = message
            if progress is not None:
                job["progress"] = progress
            self._save()
            self._emit_event("updated", job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    # ─── Job History ────────────────────────────────────────────────────

    def get_history(
        self,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None,
        job_type_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated job history, newest first."""
        jobs_list = list(self.jobs.values())

        # Filter
        if status_filter:
            jobs_list = [j for j in jobs_list if j.get("status") == status_filter]
        if job_type_filter:
            jobs_list = [j for j in jobs_list if j.get("type") == job_type_filter]

        # Sort by created_at descending
        jobs_list.sort(key=lambda j: j.get("created_at", ""), reverse=True)

        total = len(jobs_list)
        paginated = jobs_list[offset: offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "jobs": paginated,
        }

    # ─── Cancel / Pause / Resume ────────────────────────────────────────

    def cancel_job(self, job_id: str) -> bool:
        """Signal a job to cancel. Returns True if signal was sent."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return False
            if job["status"] not in (JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.PAUSED):
                return False  # Already finished

            # If pending (still in queue), mark cancelled immediately
            if job["status"] == JobStatus.PENDING:
                if job_id in self._cancel_events:
                    self._cancel_events[job_id].set()
                job["status"] = JobStatus.CANCELLED
                job["updated_at"] = datetime.now().isoformat()
                job["completed_at"] = datetime.now().isoformat()
                job["message"] = "Cancelled by user"
                self._save()
                self._emit_event("updated", job_id)
                return True

            # If processing/paused, signal the worker
            if job_id in self._cancel_events:
                self._cancel_events[job_id].set()
            job["status"] = JobStatus.CANCELLED
            job["updated_at"] = datetime.now().isoformat()
            job["completed_at"] = datetime.now().isoformat()
            job["message"] = "Cancelled by user"
            self._save()
            self._emit_event("updated", job_id)
            return True

    def pause_job(self, job_id: str) -> bool:
        """Signal a job to pause."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job["status"] != JobStatus.PROCESSING:
                return False
            if job_id in self._pause_events:
                self._pause_events[job_id].set()
            job["status"] = JobStatus.PAUSED
            job["updated_at"] = datetime.now().isoformat()
            job["message"] = "Paused by user"
            self._save()
            self._emit_event("updated", job_id)
            return True

    def resume_job(self, job_id: str) -> bool:
        """Signal a job to resume."""
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job["status"] != JobStatus.PAUSED:
                return False
            if job_id in self._pause_events:
                self._pause_events[job_id].clear()
            job["status"] = JobStatus.PROCESSING
            job["updated_at"] = datetime.now().isoformat()
            job["message"] = "Resumed"
            self._save()
            self._emit_event("updated", job_id)
            return True

    def is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled. Call this in pipeline steps."""
        event = self._cancel_events.get(job_id)
        return event.is_set() if event else False

    def wait_if_paused(self, job_id: str, timeout: float = 1.0) -> bool:
        """
        Block if job is paused. Returns True if cancelled during pause.
        Call this between pipeline steps.
        """
        event = self._pause_events.get(job_id)
        if not event:
            return self.is_cancelled(job_id)
        while event.is_set():
            if self.is_cancelled(job_id):
                return True
            time.sleep(timeout)
        return self.is_cancelled(job_id)

    def cleanup_old_jobs(self, max_age_days: int = 30):
        """Remove jobs older than max_age_days."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        with self._lock:
            to_remove = [
                jid for jid, job in self.jobs.items()
                if job.get("created_at", "") < cutoff
                and job.get("status") in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            ]
            for jid in to_remove:
                del self.jobs[jid]
                self._cancel_events.pop(jid, None)
                self._pause_events.pop(jid, None)
            if to_remove:
                self._save()
                logger.info(f"Cleaned up {len(to_remove)} old jobs.")


# Global singleton
job_manager = JobManager()
