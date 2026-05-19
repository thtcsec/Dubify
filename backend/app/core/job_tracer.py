"""Job Tracer — structured logging and tracing for pipeline jobs.

Requirement 3: Unique trace IDs, structured JSON logs, render metrics.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class StepMetrics:
    """Metrics for a single pipeline step."""
    step_name: str
    status: str = "started"  # started, completed, failed
    duration_ms: float = 0.0
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobTrace:
    """Complete trace for a pipeline job."""
    trace_id: str
    job_id: str
    job_type: str = "unknown"
    steps: list = field(default_factory=list)
    total_duration_ms: float = 0.0
    # Render metrics
    frames_rendered: int = 0
    ffmpeg_encode_time_ms: float = 0.0
    tts_synthesis_time_ms: float = 0.0
    asr_transcription_time_ms: float = 0.0
    disk_usage_bytes: int = 0


class JobTracer:
    """Structured tracing for pipeline jobs."""

    def __init__(self, job_id: str, job_type: str = "unknown"):
        self.trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        self.job_id = job_id
        self.job_type = job_type
        self._trace = JobTrace(
            trace_id=self.trace_id,
            job_id=job_id,
            job_type=job_type,
        )
        self._start_time = time.time()
        self._emit("job_started", {"job_type": job_type})

    @contextmanager
    def step(self, step_name: str, **extra):
        """Context manager for tracing a pipeline step."""
        step_start = time.time()
        self._emit("step_started", {"step": step_name, **extra})

        metrics = StepMetrics(step_name=step_name, extra=extra)
        try:
            yield metrics
            metrics.status = "completed"
            metrics.duration_ms = (time.time() - step_start) * 1000
            self._emit("step_completed", {
                "step": step_name,
                "duration_ms": round(metrics.duration_ms, 1),
                **extra,
            })
        except Exception as e:
            metrics.status = "failed"
            metrics.error = str(e)
            metrics.duration_ms = (time.time() - step_start) * 1000
            self._emit("step_failed", {
                "step": step_name,
                "error": str(e),
                "duration_ms": round(metrics.duration_ms, 1),
            })
            raise
        finally:
            self._trace.steps.append(metrics)

    def record_metric(self, key: str, value: Any) -> None:
        """Record a render metric."""
        if hasattr(self._trace, key):
            setattr(self._trace, key, value)
        self._emit("metric", {"key": key, "value": value})

    def finalize(self, status: str = "completed", error: Optional[str] = None) -> JobTrace:
        """Finalize the trace and return metrics."""
        self._trace.total_duration_ms = (time.time() - self._start_time) * 1000
        self._emit("job_finished", {
            "status": status,
            "total_duration_ms": round(self._trace.total_duration_ms, 1),
            "steps_count": len(self._trace.steps),
            **({"error": error} if error else {}),
        })
        return self._trace

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit a structured log entry."""
        entry = {
            "event": event_type,
            "trace_id": self.trace_id,
            "job_id": self.job_id,
            **data,
        }
        logger.info("[TRACE] %s", json.dumps(entry, ensure_ascii=False, default=str))
