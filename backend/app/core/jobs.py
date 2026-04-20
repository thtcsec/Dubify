import uuid
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobManager:
    def __init__(self):
        # In a real SaaS, this would be a Database (PostgreSQL/Redis)
        # For Dubify MVP, we use an in-memory dictionary.
        self.jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, filename: str) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "id": job_id,
            "filename": filename,
            "status": JobStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "output_path": None,
            "error": None
        }
        return job_id

    def update_job(self, job_id: str, status: JobStatus, output_path: Optional[str] = None, error: Optional[str] = None):
        if job_id in self.jobs:
            self.jobs[job_id]["status"] = status
            self.jobs[job_id]["updated_at"] = datetime.now().isoformat()
            if output_path:
                self.jobs[job_id]["output_path"] = output_path
            if error:
                self.jobs[job_id]["error"] = error

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

job_manager = JobManager()
