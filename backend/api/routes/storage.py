"""
Storage API — manage workflow files (results, icons, docs, etc.).

Endpoints:
  GET  /storage/workflows/{workflow_id}/files   — List all files
  GET  /storage/files/{path:path}               — Download/serve a file
  POST /storage/workflows/{workflow_id}/init     — Initialize folder structure
  GET  /storage/stats                            — Overall storage statistics
"""

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from services.storage_service import get_storage_service
from services.workflow_service import WorkflowService
from sqlalchemy.ext.asyncio import AsyncSession

import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["storage"])


@router.get("/workflows/{workflow_id}/files")
async def list_workflow_files(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all files in a workflow's storage folder."""
    # Verify workflow belongs to user's org
    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    storage = get_storage_service()
    files = storage.list_workflow_files(workflow_id)

    # If no folder exists yet, init it
    if not files:
        storage.init_workflow_folder(workflow_id, wf.name, wf.description or "")
        files = storage.list_workflow_files(workflow_id)

    return {
        "workflow_id": workflow_id,
        "workflow_name": wf.name,
        "folder": storage.find_workflow_dir(workflow_id).name if storage.find_workflow_dir(workflow_id) else None,
        "files": files,
    }


@router.get("/files/{file_path:path}")
async def serve_file(
    file_path: str,
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Serve/download a file from storage by its relative path."""
    storage = get_storage_service()
    resolved = storage.get_file_path(file_path)
    if not resolved:
        raise HTTPException(status_code=404, detail="File not found")

    content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
    return FileResponse(
        path=str(resolved),
        media_type=content_type,
        filename=resolved.name,
    )


@router.post("/workflows/{workflow_id}/upload/{subfolder}")
async def upload_file(
    workflow_id: str,
    subfolder: str,
    file: UploadFile = File(...),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to a workflow's subfolder (icons, docs, etc.)."""
    allowed_subfolders = {"icons", "docs", "config", "screenshots"}
    if subfolder not in allowed_subfolders:
        raise HTTPException(status_code=400, detail=f"Invalid subfolder. Allowed: {', '.join(allowed_subfolders)}")

    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    storage = get_storage_service()
    wf_dir = storage.find_workflow_dir(workflow_id)
    if not wf_dir:
        wf_dir = storage.init_workflow_folder(workflow_id, wf.name, wf.description or "")

    target_dir = wf_dir / subfolder
    target_dir.mkdir(exist_ok=True)

    # Sanitize filename
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    target_path = target_dir / safe_name

    # Write file
    content = await file.read()
    target_path.write_bytes(content)

    logger.info(f"Uploaded {safe_name} to {subfolder}/ for workflow {workflow_id}")
    return {
        "filename": safe_name,
        "subfolder": subfolder,
        "size": len(content),
        "path": str(target_path.relative_to(storage.base_path)),
    }


@router.post("/workflows/{workflow_id}/init")
async def init_workflow_folder(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly initialize the folder structure for a workflow."""
    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    storage = get_storage_service()
    wf_dir = storage.init_workflow_folder(workflow_id, wf.name, wf.description or "")

    return {
        "workflow_id": workflow_id,
        "folder": wf_dir.name,
        "subfolders": [s.name for s in wf_dir.iterdir() if s.is_dir()],
        "message": f"Folder structure initialized at {wf_dir.name}/",
    }


@router.get("/workflows/{workflow_id}/latest-results")
async def get_latest_results(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest execution results for a workflow from DB."""
    import json as _json
    from sqlalchemy import text as sa_text

    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Fetch from DB execution_states (authoritative source)
    row = (await db.execute(sa_text(
        "SELECT e.id, e.status, e.started_at, e.completed_at, e.duration_ms, "
        "       es.state_data "
        "FROM executions e "
        "LEFT JOIN execution_states es ON es.execution_id = e.id "
        "WHERE e.workflow_id = :wid "
        "ORDER BY e.created_at DESC LIMIT 1"
    ), {"wid": workflow_id})).fetchone()

    if not row or not row[5]:
        raise HTTPException(status_code=404, detail="No results available yet. Run the workflow first.")

    state_data = row[5] if isinstance(row[5], dict) else _json.loads(row[5])

    return {
        "execution_id": str(row[0]),
        "status": row[1],
        "started_at": row[2].isoformat() if row[2] else None,
        "completed_at": row[3].isoformat() if row[3] else None,
        "data": state_data,
    }


@router.get("/workflows/{workflow_id}/latest-results/download")
async def download_latest_results(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download the latest execution results as a clean JSON file.
    Fetches full state_data from execution_states DB table,
    extracts actual product/output data from step outputs.
    """
    import json as _json
    import tempfile
    from datetime import datetime
    from sqlalchemy import text as sa_text

    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Get latest execution + its full state_data from DB
    row = (await db.execute(sa_text(
        "SELECT e.id, e.status, e.started_at, e.completed_at, e.duration_ms, "
        "       es.state_data "
        "FROM executions e "
        "LEFT JOIN execution_states es ON es.execution_id = e.id "
        "WHERE e.workflow_id = :wid "
        "ORDER BY e.created_at DESC LIMIT 1"
    ), {"wid": workflow_id})).fetchone()

    if not row or not row[5]:
        raise HTTPException(status_code=404, detail="No results available yet. Run the workflow first.")

    exec_id = str(row[0])
    exec_status = row[1]
    started_at = row[2].isoformat() if row[2] else None
    completed_at = row[3].isoformat() if row[3] else None
    duration_ms = row[4]
    state_data = row[5] if isinstance(row[5], dict) else _json.loads(row[5])

    # Extract actual output data from steps
    all_items = []
    steps_info = state_data.get("steps", {})
    for step_id, step_info in steps_info.items():
        if not isinstance(step_info, dict):
            continue
        output = step_info.get("output")
        if isinstance(output, list):
            all_items.extend(output)
        elif isinstance(output, dict):
            # Check for nested data array
            if "data" in output and isinstance(output["data"], list):
                all_items.extend(output["data"])
            elif output:  # Single dict output
                all_items.append(output)

    # Build a clean download file
    download_data = {
        "workflow": wf.name,
        "execution_id": exec_id,
        "status": exec_status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "total_records": len(all_items),
        "exported_at": datetime.now().isoformat(),
        "results": all_items,
    }

    # Write to temp file and serve
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    _json.dump(download_data, tmp, ensure_ascii=False, indent=2, default=str)
    tmp.close()

    safe_name = wf.name.replace(" ", "_")
    return FileResponse(
        path=tmp.name,
        media_type="application/json",
        filename=f"{safe_name}_results.json",
    )


@router.get("/workflows/{workflow_id}/detail")
async def get_workflow_detail(
    workflow_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full workflow detail for the dashboard page:
    workflow info, latest execution, results summary, schedules.
    """
    from sqlalchemy import text as sa_text

    svc = WorkflowService(db)
    wf = await svc.get_by_id_and_org(workflow_id, current_user.org_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Latest execution
    row = (await db.execute(sa_text(
        "SELECT id, status, trigger_type, started_at, completed_at, duration_ms, error_message "
        "FROM executions WHERE workflow_id = :wid ORDER BY created_at DESC LIMIT 1"
    ), {"wid": workflow_id})).fetchone()

    latest_execution = None
    if row:
        latest_execution = {
            "id": str(row[0]),
            "status": row[1],
            "trigger_type": row[2],
            "started_at": row[3].isoformat() if row[3] else None,
            "completed_at": row[4].isoformat() if row[4] else None,
            "duration_ms": row[5],
            "error_message": row[6],
        }

    # Total execution count
    count_row = (await db.execute(sa_text(
        "SELECT COUNT(*) FROM executions WHERE workflow_id = :wid"
    ), {"wid": workflow_id})).fetchone()
    total_executions = count_row[0] if count_row else 0

    # Schedules for this workflow
    schedule_rows = (await db.execute(sa_text(
        "SELECT id, name, cron_expression, timezone, is_enabled, next_run_at "
        "FROM schedules WHERE workflow_id = :wid AND is_deleted = false ORDER BY created_at"
    ), {"wid": workflow_id})).fetchall()

    schedules = [{
        "id": str(r[0]),
        "name": r[1],
        "cron_expression": r[2],
        "timezone": r[3],
        "is_enabled": r[4],
        "next_run_at": r[5].isoformat() if r[5] else None,
    } for r in schedule_rows]

    # Latest results summary — from DB execution_states (authoritative)
    results_summary = None
    if row:  # row from latest execution query above
        state_row = (await db.execute(sa_text(
            "SELECT state_data FROM execution_states WHERE execution_id = :eid LIMIT 1"
        ), {"eid": str(row[0])})).fetchone()

        if state_row and state_row[0]:
            import json as _json
            sd = state_row[0] if isinstance(state_row[0], dict) else _json.loads(state_row[0])
            total_items = 0
            steps = sd.get("steps", {})
            if isinstance(steps, dict):
                for step_id, step_info in steps.items():
                    if not isinstance(step_info, dict):
                        continue
                    output = step_info.get("output")
                    if isinstance(output, list):
                        total_items += len(output)
                    elif isinstance(output, dict) and "data" in output and isinstance(output["data"], list):
                        total_items += len(output["data"])

            results_summary = {
                "saved_at": row[4].isoformat() if row[4] else (row[3].isoformat() if row[3] else None),
                "execution_id": str(row[0]),
                "total_items": total_items,
                "file_size": 0,  # Size will be calculated on download
            }

    return {
        "workflow": {
            "id": str(wf.id),
            "name": wf.name,
            "description": wf.description,
            "status": wf.status,
            "version": wf.version,
            "is_enabled": wf.is_enabled,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
            "step_count": len(wf.definition.get("steps", [])) if wf.definition else 0,
        },
        "latest_execution": latest_execution,
        "total_executions": total_executions,
        "schedules": schedules,
        "results_summary": results_summary,
    }


@router.get("/stats")
async def storage_stats(
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Get overall storage statistics."""
    storage = get_storage_service()
    return storage.get_storage_stats()
