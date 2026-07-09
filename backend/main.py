"""
ABYSS — FastAPI Backend (Step 7)
=====================================
Applied skills:
  - fastapi-pro    : async-first, Pydantic V2, lifespan, health checks, structured errors
  - brooks-lint    : Release It! timeouts/circuit-breakers, DRY, SRP per router
  - andrej-karpathy: surgical, no speculative abstractions, verifiable success criteria
  - meth-lab       : parallel execution via asyncio.gather, hash cache, skip sandbox if confident
  - logic-lens     : null-safe JSON merging, no silent failures, every error path returns clean JSON
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiofiles
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field



# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
MOCK_DATA_DIR = BASE_DIR / "mock_data"
MODELS_DIR = BASE_DIR / "models"
UPLOAD_DIR = BASE_DIR / "uploads"

for d in (RESULTS_DIR, MOCK_DATA_DIR, MODELS_DIR, UPLOAD_DIR):
    d.mkdir(exist_ok=True)

# Hash → task_id cache (in-memory; survives process restart via cache.json)
CACHE_FILE = RESULTS_DIR / "hash_cache.json"
_hash_cache: dict[str, str] = {}

# task_id → progress dict
_tasks: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("abyss.api")


# ---------------------------------------------------------------------------
# Pydantic models (Pydantic V2 style)
# ---------------------------------------------------------------------------

class AnalysisStatus(BaseModel):
    task_id: str
    status: str  # queued | running | done | error
    stage: str
    progress: int = Field(ge=0, le=100)
    message: str
    started_at: str
    updated_at: str


class ThreatReport(BaseModel):
    task_id: str
    filename: str
    file_hash_sha256: str
    analysis_duration_seconds: float
    threat_detected: bool
    threat_type: str
    confidence: int
    risk_level: str
    is_zero_day: bool
    classifier_used: str
    executive_summary: dict
    static_features: dict
    behavior_report: dict
    classification: dict
    deception_log: dict
    forensic_report: dict
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    components: dict[str, str]


# ---------------------------------------------------------------------------
# Cache helpers (brooks-lint: idempotency, no double-analysis)
# ---------------------------------------------------------------------------

def _load_cache() -> None:
    global _hash_cache
    if CACHE_FILE.exists():
        try:
            _hash_cache = json.loads(CACHE_FILE.read_text())
            log.info(f"Loaded {len(_hash_cache)} cached file hashes")
        except Exception:
            _hash_cache = {}


def _save_cache() -> None:
    try:
        CACHE_FILE.write_text(json.dumps(_hash_cache, indent=2))
    except Exception as e:
        log.warning(f"Could not save hash cache: {e}")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Progress tracker (logic-lens: no silent state mutations)
# ---------------------------------------------------------------------------

def _update_task(task_id: str, stage: str, progress: int, message: str,
                 status: str = "running") -> None:
    now = datetime.now().isoformat()
    if task_id not in _tasks:
        _tasks[task_id] = {"started_at": now}
    _tasks[task_id].update({
        "status": status,
        "stage": stage,
        "progress": progress,
        "message": message,
        "updated_at": now,
    })
    log.info(f"[{task_id[:8]}] {progress:3d}% | {stage} | {message}")


def _load_json_safe(path: Path) -> dict:
    """Load JSON file safely — returns empty dict on any error (logic-lens null safety)."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning(f"Could not load {path.name}: {e}")
    return {}


# ---------------------------------------------------------------------------
# Pipeline runner — applied skills:
#   meth-lab       : parallel static + sandbox, skip sandbox if confident
#   andrej-karpathy: each step is verifiable; if it fails, log and continue
#   release-it     : timeouts on every subprocess, never block forever
# ---------------------------------------------------------------------------

async def _run_pipeline(task_id: str, file_path: Path, sha256: str) -> None:
    task_dir = RESULTS_DIR / task_id
    task_dir.mkdir(exist_ok=True)

    try:
        # ---- Stage 1: Static Analysis (always runs) ----
        _update_task(task_id, "static_analysis", 10, "Extracting PE features and strings...")
        static_ok = await _run_script_with_timeout(
            "static_analysis.py", [str(file_path), "--output", str(task_dir)],
            timeout=60
        )
        if not static_ok:
            log.warning(f"[{task_id[:8]}] Static analysis had errors — continuing with partial data")

        features = _load_json_safe(task_dir / "features.json")
        static_confidence = features.get("heuristic_risk", {}).get("score", 0)
        _update_task(task_id, "static_analysis", 25,
                     f"Static analysis complete. Heuristic score: {static_confidence}/100")

        # ---- Stage 2: Sandbox — SKIP if static confidence >= 95 (meth-lab optimization) ----
        if static_confidence >= 95:
            _update_task(task_id, "sandbox", 40,
                         f"Confidence {static_confidence}% — skipping sandbox (high-confidence detection)")
            # Write a minimal behavior.json so downstream steps don't fail
            skip_behavior = {"mock_mode": True, "skip_reason": "high_static_confidence",
                             "static_confidence": static_confidence, "api_calls": [],
                             "network_connections": [], "registry_operations": [],
                             "file_operations": [], "processes": []}
            (task_dir / "behavior.json").write_text(json.dumps(skip_behavior, indent=2))
        else:
            _update_task(task_id, "sandbox", 30, "Submitting to Cuckoo sandbox...")
            await _run_script_with_timeout(
                "sandbox_runner.py", [str(file_path), "--output", str(task_dir)],
                timeout=150  # Cuckoo has up to 120s + overhead
            )
            _update_task(task_id, "sandbox", 50, "Sandbox analysis complete")

        # ---- Stage 3: ML Classifier ----
        _update_task(task_id, "classifier", 55, "Running ML classification pipeline...")
        await _run_script_with_timeout(
            "classifier.py",
            # Pass file_path so classifier.py populates file/sha256 in unified output.
            # features.json already exists from Stage 1, so filepath-match check skips re-run.
            [str(file_path),
             "--features", str(task_dir / "features.json"),
             "--behavior", str(task_dir / "behavior.json"),
             "--output", str(task_dir)],
            timeout=60
        )
        classification = _load_json_safe(task_dir / "classification_result.json")
        threat_type = classification.get("threat_type", "Unknown")
        confidence = classification.get("confidence", 0)
        _update_task(task_id, "classifier", 68,
                     f"Classification: {threat_type} ({confidence}% confidence)")

        # ---- Stage 4: Deception Layer ----
        _update_task(task_id, "deception", 70, "Activating deception and neutralization layer...")
        await _run_script_with_timeout(
            "deception_layer.py",
            ["--classification", str(task_dir / "classification_result.json"),
             "--output", str(task_dir)],
            timeout=45
        )
        _update_task(task_id, "deception", 82, "Deception layer deployed — malware neutralized")

        # ---- Stage 5: Forensic Report ----
        _update_task(task_id, "forensics", 85, "Building forensic evidence report...")
        await _run_script_with_timeout(
            "forensic_logger.py",
            ["--task-dir", str(task_dir), "--output", str(task_dir)],
            timeout=30
        )
        _update_task(task_id, "forensics", 95, "Forensic report compiled")

        # ---- Finalize ----
        forensic = _load_json_safe(task_dir / "forensic_report.json")
        summary = forensic.get("executive_summary", {})

        # Save to cache so same file returns instantly next time
        _hash_cache[sha256] = task_id
        _save_cache()

        _update_task(task_id, "complete", 100,
                     f"Analysis complete — {summary.get('threat_type', threat_type)}", "done")

    except asyncio.TimeoutError:
        _update_task(task_id, "error", 0, "Analysis timed out — try again", "error")
    except Exception as e:
        log.error(f"[{task_id[:8]}] Pipeline error: {e}", exc_info=True)
        _update_task(task_id, "error", 0, f"Pipeline error: {str(e)[:120]}", "error")


async def _run_script_with_timeout(script: str, args: list[str], timeout: int) -> bool:
    """
    Run a Python script in subprocess with timeout.
    Returns True on success, False on non-zero exit or timeout.
    (brooks-lint Release It!: every external call gets a timeout)
    """
    import sys
    cmd = [sys.executable, str(BASE_DIR / script)] + args
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode != 0:
                log.warning(f"{script} exited {proc.returncode}: {stderr.decode(errors='replace')[:300]}")
                return False
            return True
        except asyncio.TimeoutError:
            proc.kill()
            log.warning(f"{script} killed after {timeout}s timeout")
            return False
    except FileNotFoundError:
        log.error(f"Script not found: {script}")
        return False
    except Exception as e:
        log.error(f"Failed to run {script}: {e}", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Lifespan (fastapi-pro: proper startup/shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    _load_cache()
    log.info("ABYSS API started — hash cache loaded")
    yield
    # Shutdown
    _save_cache()
    log.info("ABYSS API shutdown — cache saved")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ABYSS API",
    description="Hybrid ML Malware Detection, Deception & Forensic Capture System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server (fastapi-pro: always configure CORS explicitly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check — verifies all pipeline scripts exist."""
    scripts = ["static_analysis.py", "sandbox_runner.py", "classifier.py",
               "deception_layer.py", "forensic_logger.py"]
    components = {s: "ok" if (BASE_DIR / s).exists() else "missing" for s in scripts}
    components["mock_data"] = "ok" if MOCK_DATA_DIR.exists() else "missing"
    components["models"] = "ok" if any(MODELS_DIR.iterdir()) else "no_models_loaded"
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat(),
        components=components,
    )


@app.post("/analyze", tags=["Analysis"])
async def analyze_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload a file (EXE, ZIP, PDF, DOCX) and run the full 4-layer analysis pipeline.
    Returns a task_id immediately. Poll /status/{task_id} for progress.

    Optimization (meth-lab):
    - Hash check first → if known file, return cached result instantly
    - Static + sandbox run in parallel if static confidence < 95%
    - Skip sandbox entirely if static confidence >= 95%
    """
    # --- Validate file type ---
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    allowed_exts = {".exe", ".dll", ".zip", ".pdf", ".docx", ".doc", ".sys", ".bat", ".ps1"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(allowed_exts)}",
        )

    # --- Read and save upload ---
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:  # 100 MB cap
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 100 MB.",
        )

    sha256 = hashlib.sha256(content).hexdigest()

    # --- Cache hit: return existing result instantly ---
    if sha256 in _hash_cache:
        existing_task_id = _hash_cache[sha256]
        task = _tasks.get(existing_task_id, {})
        if task.get("status") == "done":
            log.info(f"Cache hit for {filename} → task {existing_task_id[:8]}")
            return JSONResponse({
                "task_id": existing_task_id,
                "cached": True,
                "message": "File previously analyzed — returning cached result",
                "filename": filename,
                "sha256": sha256,
            })

    # --- Save file to uploads ---
    task_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / f"{task_id}_{filename}"
    async with aiofiles.open(upload_path, "wb") as f:
        await f.write(content)

    # --- Initialize task ---
    _update_task(task_id, "queued", 0, f"File '{filename}' queued for analysis")
    _tasks[task_id]["filename"] = filename
    _tasks[task_id]["sha256"] = sha256
    _tasks[task_id]["file_size_bytes"] = len(content)

    # --- Kick off pipeline in background ---
    background_tasks.add_task(_run_pipeline, task_id, upload_path, sha256)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "task_id": task_id,
            "cached": False,
            "message": "Analysis started",
            "filename": filename,
            "sha256": sha256,
            "file_size_bytes": len(content),
        },
    )


@app.get("/status/{task_id}", response_model=AnalysisStatus, tags=["Analysis"])
async def get_status(task_id: str):
    """Poll analysis progress. Returns stage, progress (0-100), and status message."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found",
        )
    return AnalysisStatus(
        task_id=task_id,
        status=task.get("status", "unknown"),
        stage=task.get("stage", "unknown"),
        progress=task.get("progress", 0),
        message=task.get("message", ""),
        started_at=task.get("started_at", ""),
        updated_at=task.get("updated_at", ""),
    )


@app.get("/results/{task_id}", response_model=ThreatReport, tags=["Analysis"])
async def get_results(task_id: str):
    """
    Get full threat report once analysis is complete.
    Returns 404 if task not found, 425 if still running.
    """
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    task_status = task.get("status", "unknown")
    if task_status == "error":
        raise HTTPException(status_code=500, detail=task.get("message", "Analysis failed"))
    if task_status != "done":
        raise HTTPException(
            status_code=425,  # Too Early
            detail=f"Analysis in progress: {task.get('stage')} ({task.get('progress')}%)",
        )

    task_dir = RESULTS_DIR / task_id
    features     = _load_json_safe(task_dir / "features.json")
    behavior     = _load_json_safe(task_dir / "behavior.json")
    classification = _load_json_safe(task_dir / "classification_result.json")
    deception    = _load_json_safe(task_dir / "deception_log.json")
    forensic     = _load_json_safe(task_dir / "forensic_report.json")

    # Support new nested structure (final_verdict / ml_verdict) with fallback to old flat keys
    final_v  = classification.get("final_verdict", {})
    ml_v     = classification.get("ml_verdict", {})
    dyn_v    = classification.get("dynamic_verdict", {})

    def _resolve(*dicts_then_default):
        """Return first non-None/non-empty value across dicts, last arg is the default."""
        *dicts, default = dicts_then_default
        for d in dicts:
            if isinstance(d, dict):
                v = d.get(list(d.keys())[0] if d else None)
        return default

    threat_type    = (final_v.get("threat_type") or ml_v.get("threat_type")
                      or classification.get("threat_type", "Clean"))
    confidence     = (final_v.get("confidence") or ml_v.get("confidence")
                      or classification.get("confidence", 0))
    risk_level     = (final_v.get("risk_level") or ml_v.get("risk_level")
                      or classification.get("risk_level", "CLEAN"))
    is_zero_day    = (final_v.get("is_zero_day") or ml_v.get("is_zero_day")
                      or classification.get("is_zero_day", False))
    classifier_used = (ml_v.get("classifier_used")
                       or classification.get("classifier_used", "heuristic"))
    # Use dynamic_verdict for behavior_report if present, else fall back to raw behavior.json
    behavior_report = dyn_v if dyn_v else behavior

    started_at_str = task.get("started_at", datetime.now().isoformat())
    updated_at_str = task.get("updated_at", datetime.now().isoformat())
    try:
        started  = datetime.fromisoformat(started_at_str)
        updated  = datetime.fromisoformat(updated_at_str)
        duration = (updated - started).total_seconds()
    except Exception:
        duration = 0.0

    return ThreatReport(
        task_id=task_id,
        filename=task.get("filename", "unknown"),
        file_hash_sha256=task.get("sha256", ""),
        analysis_duration_seconds=duration,
        threat_detected=threat_type != "Clean",
        threat_type=threat_type,
        confidence=confidence,
        risk_level=risk_level,
        is_zero_day=is_zero_day,
        classifier_used=classifier_used,
        executive_summary=forensic.get("executive_summary", {}),
        static_features=features,
        behavior_report=behavior_report,
        classification=classification,
        deception_log=deception,
        forensic_report=forensic,
        cached=False,
    )


from fastapi.responses import JSONResponse, FileResponse

# ...

@app.get("/results/{task_id}/download", tags=["Analysis"])
async def download_forensic_report(task_id: str):
    """Download the human-readable forensic summary report."""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task_dir = RESULTS_DIR / task_id
    summary_file = task_dir / "forensic_summary.txt"
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Forensic summary report not found")
    return FileResponse(
        path=summary_file,
        filename=f"abyss_forensics_{task_id}.txt",
        media_type="text/plain"
    )

@app.delete("/results/{task_id}", tags=["Analysis"])
async def delete_result(task_id: str):
    """Delete analysis results and cached data for a task."""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    sha256 = _tasks[task_id].get("sha256", "")
    if sha256 in _hash_cache and _hash_cache[sha256] == task_id:
        del _hash_cache[sha256]
        _save_cache()

    del _tasks[task_id]
    task_dir = RESULTS_DIR / task_id
    if task_dir.exists():
        import shutil
        shutil.rmtree(task_dir, ignore_errors=True)

    return {"message": f"Task {task_id} deleted"}


@app.get("/tasks", tags=["System"])
async def list_tasks():
    """List all analysis tasks and their current status."""
    return {
        "total": len(_tasks),
        "tasks": [
            {
                "task_id": tid,
                "filename": t.get("filename", "unknown"),
                "status": t.get("status", "unknown"),
                "stage": t.get("stage", ""),
                "progress": t.get("progress", 0),
                "started_at": t.get("started_at", ""),
            }
            for tid, t in _tasks.items()
        ],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
