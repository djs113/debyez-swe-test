import uuid
from datetime import datetime
from typing import Optional, Dict

JOB_STORE = {}

def create_job() -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {
        "id": job_id,
        "status": "PENDING",
        "created_at": datetime.now(),
        "result": None,
        "filename": None,
        "error": None
    }
    return job_id

def get_job(job_id: str) -> Optional[Dict]:
    """Get job details by ID."""
    return JOB_STORE.get(job_id)

def set_processing(job_id: str) -> None:
    """Mark job as processing."""
    if job_id in JOB_STORE:
        JOB_STORE[job_id]["status"] = "PROCESSING"

def set_complete(job_id: str, result: str, filename: str) -> None:
    """Mark job as complete with result path."""
    if job_id in JOB_STORE:
        JOB_STORE[job_id].update({
            "status": "COMPLETE",
            "result": result,
            "filename": filename,
            "completed_at": datetime.now()
        })

def set_failed(job_id: str, error: str) -> None:
    """Mark job as failed with error message."""
    if job_id in JOB_STORE:
        JOB_STORE[job_id].update({
            "status": "FAILED",
            "error": error,
            "completed_at": datetime.now()
        })

def cleanup_job(job_id: str) -> None:
    """Remove job from store."""
    if job_id in JOB_STORE:
        del JOB_STORE[job_id]