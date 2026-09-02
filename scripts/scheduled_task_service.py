"""Authenticated request-based host for the scheduled FPL tasks.

Cloud Run Jobs bill a one-minute minimum per execution.  This service reuses
the same task functions behind Cloud Run IAM so Cloud Scheduler pays for the
actual request duration instead.  It has no FPL write capability.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from scripts.run_scheduled_task import (
    task_capture_journal,
    task_decision_refresh,
    task_finalize_gameweek,
    task_fixtures,
    task_live_refresh,
    task_monitor,
)

app = FastAPI(title="FPL scheduled task service", version="1.0.0")


@app.get("/healthz")
def healthz() -> dict[str, object]:
    return {"ok": True, "execution_authority": "manual_fpl", "writes_enabled": False}


@app.post("/tasks/{task}")
def run_task(task: str, gw: int | None = Query(default=None, ge=1, le=38)) -> dict[str, object]:
    if task == "fixtures":
        task_fixtures()
    elif task == "capture-journal":
        task_capture_journal(gw)
    elif task == "decision-refresh":
        task_decision_refresh(gameweek=gw)
    elif task == "decision-final-window":
        task_decision_refresh(final_window=True, gameweek=gw)
    elif task == "finalize-gameweek":
        task_finalize_gameweek(gw)
    elif task == "monitor":
        task_monitor()
    elif task == "live-refresh":
        task_live_refresh()
    else:
        raise HTTPException(status_code=404, detail="unknown_task")
    return {"task": task, "status": "completed", "execution_authority": "manual_fpl", "writes_enabled": False}
