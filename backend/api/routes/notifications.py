"""Notification API routes.

Manage notification channels, send test notifications, view status.
Provides in-app notification feed from execution events + AI diagnosis + fix history.
"""

import json as _json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.dependencies import get_current_active_user, get_db, TokenPayload
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.channels import NotificationChannel, NotificationPriority
from notifications.manager import get_notification_manager

router = APIRouter()
logger = logging.getLogger(__name__)


# -- Schemas --

class NotificationSendRequest(BaseModel):
    """Schema for sending a notification."""
    title: str
    message: str
    channel: str  # email, slack, webhook, websocket
    recipient: str = ""
    priority: str = "normal"
    metadata: dict = Field(default_factory=dict)


class ChannelConfigRequest(BaseModel):
    """Schema for configuring a notification channel."""
    channel: str
    config: dict


# ─── In-memory read tracking (per-org, per-notification-id) ─────
# In production you'd persist to DB, but this works for the running instance.
_read_ids: dict[str, set] = {}


# ─── GET /notifications/ — Main feed ────────────────────────────

@router.get("/", summary="List in-app notifications")
async def list_notifications(
    per_page: int = Query(default=30, ge=1, le=100),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return recent notification feed for the current user/org.

    Sources:
      1. Failed executions  → type='error'  (with AI diagnosis + fix info)
      2. Completed executions with results → type='success'
      3. AI auto-fixes → type='warning' (shows what was fixed)
    """
    from sqlalchemy import text as sa_text

    org_id = current_user.org_id
    read_set = _read_ids.get(org_id, set())

    # ── 1. Recent executions (last 48h, both failed + completed) ──
    rows = (await db.execute(sa_text("""
        SELECT
            e.id,
            e.workflow_id,
            e.status,
            e.error_message,
            e.started_at,
            e.completed_at,
            e.duration_ms,
            e.trigger_type,
            w.name AS workflow_name
        FROM executions e
        LEFT JOIN workflows w ON w.id = e.workflow_id
        WHERE w.organization_id = :org_id
          AND e.status IN ('failed', 'completed')
          AND e.completed_at > (NOW() - INTERVAL '48 hours')
        ORDER BY e.completed_at DESC
        LIMIT :limit
    """), {"org_id": org_id, "limit": per_page})).fetchall()

    notifications = []
    for r in rows:
        exec_id = str(r[0])
        wf_name = r[8] or str(r[1])[:8]
        exec_status = r[2]
        error_msg = r[3]
        completed_at = r[5]
        duration_ms = r[6]
        trigger_type = r[7]

        duration_str = ""
        if duration_ms:
            secs = duration_ms / 1000
            if secs < 60:
                duration_str = f"{secs:.0f}s"
            else:
                duration_str = f"{secs/60:.1f}m"

        nid = f"exec-{exec_id}"

        if exec_status == "failed":
            # ── Check for AI diagnosis ──
            ai_diagnosis = None
            try:
                diag_row = (await db.execute(sa_text("""
                    SELECT details FROM execution_journal
                    WHERE execution_id = :eid AND event_type = 'ai_diagnosis'
                    ORDER BY created_at DESC LIMIT 1
                """), {"eid": exec_id})).fetchone()
                if diag_row and diag_row[0]:
                    ai_diagnosis = diag_row[0] if isinstance(diag_row[0], dict) else _json.loads(diag_row[0])
            except Exception:
                pass

            # ── Check for AI auto-fix applied ──
            ai_fix = None
            try:
                fix_row = (await db.execute(sa_text("""
                    SELECT details, message FROM execution_journal
                    WHERE execution_id = :eid AND event_type = 'ai_auto_fix'
                    ORDER BY created_at DESC LIMIT 1
                """), {"eid": exec_id})).fetchone()
                if fix_row and fix_row[0]:
                    ai_fix = fix_row[0] if isinstance(fix_row[0], dict) else _json.loads(fix_row[0])
            except Exception:
                pass

            # Build notification based on whether fix was applied
            if ai_fix and ai_fix.get("action") == "fix_definition":
                # ── Auto-fix was applied (definition was modified) ──
                title = f"🔧 {wf_name} — Auto-Fixed"
                changes = ai_fix.get("changes_summary", "Definition updated")
                message = f"AI diagnosed & fixed: {changes[:200]}"
                new_exec = ai_fix.get("new_execution_id") or ""
                if new_exec:
                    # Check if the re-run succeeded
                    rerun_row = None
                    try:
                        rerun_row = (await db.execute(sa_text(
                            "SELECT status FROM executions WHERE id = :eid"
                        ), {"eid": new_exec})).fetchone()
                    except Exception:
                        pass
                    if rerun_row:
                        if rerun_row[0] == "completed":
                            title = f"✅🔧 {wf_name} — Auto-Fixed & Succeeded"
                            message += " → Re-run succeeded!"
                        elif rerun_row[0] == "failed":
                            title = f"⚠️ {wf_name} — Auto-Fix Applied, Re-run Failed"
                            message += " → Re-run also failed."
                        elif rerun_row[0] == "running":
                            title = f"🔧⏳ {wf_name} — Auto-Fixed, Re-running..."
                            message += " → Re-running now..."
                    old_ver = ai_fix.get("old_version", "?")
                    new_ver = ai_fix.get("new_version", "?")
                    message += f" (v{old_ver} → v{new_ver})"

                notifications.append({
                    "id": nid,
                    "type": "warning",
                    "title": title,
                    "message": message,
                    "resource_type": "execution",
                    "resource_id": exec_id,
                    "read": nid in read_set,
                    "created_at": completed_at.isoformat() if completed_at else datetime.utcnow().isoformat(),
                    "metadata": {
                        "workflow_id": str(r[1]),
                        "workflow_name": wf_name,
                        "trigger_type": trigger_type,
                        "ai_diagnosis": ai_diagnosis,
                        "ai_fix": ai_fix,
                    },
                })

            elif ai_fix and ai_fix.get("action") == "retry":
                # ── Simple retry was triggered ──
                title = f"🔄 {wf_name} — Auto-Retried"
                diag_text = ai_diagnosis.get("diagnosis", "") if ai_diagnosis else ""
                message = f"Error: {error_msg[:100]}" if error_msg else "Failed"
                if diag_text:
                    message += f"\n💡 AI: {diag_text[:150]}"
                message += "\n🔄 Auto-retry in progress..."

                notifications.append({
                    "id": nid,
                    "type": "warning",
                    "title": title,
                    "message": message,
                    "resource_type": "execution",
                    "resource_id": exec_id,
                    "read": nid in read_set,
                    "created_at": completed_at.isoformat() if completed_at else datetime.utcnow().isoformat(),
                    "metadata": {
                        "workflow_id": str(r[1]),
                        "workflow_name": wf_name,
                        "trigger_type": trigger_type,
                        "ai_diagnosis": ai_diagnosis,
                        "ai_fix": ai_fix,
                    },
                })
            else:
                # ── Plain failure, no auto-fix ──
                title = f"❌ {wf_name} — Failed"
                message = f"Error: {error_msg[:200]}" if error_msg else "Execution failed"
                if duration_str:
                    message += f" (after {duration_str})"

                if ai_diagnosis:
                    diagnosis_text = ai_diagnosis.get("diagnosis", "")
                    fix_suggestion = ai_diagnosis.get("fix_suggestion", "")
                    if diagnosis_text:
                        message += f"\n💡 AI: {diagnosis_text[:150]}"
                        if fix_suggestion:
                            message += f"\n🔧 Fix: {fix_suggestion[:100]}"

                notifications.append({
                    "id": nid,
                    "type": "error",
                    "title": title,
                    "message": message,
                    "resource_type": "execution",
                    "resource_id": exec_id,
                    "read": nid in read_set,
                    "created_at": completed_at.isoformat() if completed_at else datetime.utcnow().isoformat(),
                    "metadata": {
                        "workflow_id": str(r[1]),
                        "workflow_name": wf_name,
                        "trigger_type": trigger_type,
                        "ai_diagnosis": ai_diagnosis,
                    },
                })

        elif exec_status == "completed":
            # Get result count from execution_states
            total_items = 0
            try:
                state_row = (await db.execute(sa_text("""
                    SELECT state_data FROM execution_states
                    WHERE execution_id = :eid LIMIT 1
                """), {"eid": exec_id})).fetchone()
                if state_row and state_row[0]:
                    sd = state_row[0] if isinstance(state_row[0], dict) else _json.loads(state_row[0])
                    steps = sd.get("steps", {})
                    if isinstance(steps, dict):
                        for sid in sorted(steps.keys(), reverse=True):
                            si = steps[sid]
                            if not isinstance(si, dict):
                                continue
                            out = si.get("output")
                            if isinstance(out, dict) and "data" in out and isinstance(out["data"], list):
                                total_items = len(out["data"])
                                break
                            elif isinstance(out, list) and out and isinstance(out[0], dict):
                                total_items = len(out)
                                break
            except Exception:
                pass

            title = f"✅ {wf_name} — Completed"
            message = f"{total_items} records collected" if total_items > 0 else "Completed successfully"
            if duration_str:
                message += f" in {duration_str}"
            if trigger_type:
                message += f" ({trigger_type})"

            notifications.append({
                "id": nid,
                "type": "success",
                "title": title,
                "message": message,
                "resource_type": "execution",
                "resource_id": exec_id,
                "read": nid in read_set,
                "created_at": completed_at.isoformat() if completed_at else datetime.utcnow().isoformat(),
                "metadata": {
                    "workflow_id": str(r[1]),
                    "workflow_name": wf_name,
                    "total_items": total_items,
                    "trigger_type": trigger_type,
                },
            })

    return {"notifications": notifications, "total": len(notifications)}


# ─── Fix History endpoint ─────────────────────────────────────

@router.get("/fix-history", summary="AI auto-fix history")
async def get_fix_history(
    per_page: int = Query(default=20, ge=1, le=50),
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return history of all AI auto-fixes applied to workflows.
    Shows: problem → diagnosis → fix applied → result.
    """
    from sqlalchemy import text as sa_text

    org_id = current_user.org_id

    rows = (await db.execute(sa_text("""
        SELECT
            ej.execution_id,
            ej.message,
            ej.details,
            ej.created_at,
            e.workflow_id,
            w.name AS workflow_name,
            e.error_message
        FROM execution_journal ej
        JOIN executions e ON e.id = ej.execution_id
        JOIN workflows w ON w.id = e.workflow_id
        WHERE w.organization_id = :org_id
          AND ej.event_type = 'ai_auto_fix'
        ORDER BY ej.created_at DESC
        LIMIT :limit
    """), {"org_id": org_id, "limit": per_page})).fetchall()

    fixes = []
    for r in rows:
        details = r[2] if isinstance(r[2], dict) else (_json.loads(r[2]) if r[2] else {})

        # Check if re-run execution succeeded
        rerun_status = None
        new_exec_id = details.get("new_execution_id")
        if new_exec_id:
            try:
                status_row = (await db.execute(sa_text(
                    "SELECT status FROM executions WHERE id = :eid"
                ), {"eid": new_exec_id})).fetchone()
                if status_row:
                    rerun_status = status_row[0]
            except Exception:
                pass

        fixes.append({
            "execution_id": str(r[0]),
            "workflow_id": str(r[4]),
            "workflow_name": r[5] or str(r[4])[:8],
            "original_error": (r[6] or "")[:300],
            "fix_action": details.get("action", "unknown"),
            "changes_summary": details.get("changes_summary", r[1]),
            "changes_detail": details.get("changes_detail", []),
            "old_version": details.get("old_version"),
            "new_version": details.get("new_version"),
            "root_cause": details.get("root_cause", "unknown"),
            "diagnosis": details.get("diagnosis", ""),
            "rerun_execution_id": new_exec_id,
            "rerun_status": rerun_status,
            "fixed_at": r[3].isoformat() if r[3] else None,
        })

    return {"fixes": fixes, "total": len(fixes)}


# ─── Mark read endpoints ────────────────────────────────────────

@router.put("/{notification_id}/read", summary="Mark notification as read")
async def mark_notification_read(
    notification_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
):
    org_id = current_user.org_id
    if org_id not in _read_ids:
        _read_ids[org_id] = set()
    _read_ids[org_id].add(notification_id)
    return {"success": True}


@router.put("/read-all", summary="Mark all notifications as read")
async def mark_all_read(
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import text as sa_text
    org_id = current_user.org_id
    if org_id not in _read_ids:
        _read_ids[org_id] = set()

    # Mark all recent execution notifications as read
    rows = (await db.execute(sa_text("""
        SELECT e.id FROM executions e
        LEFT JOIN workflows w ON w.id = e.workflow_id
        WHERE w.organization_id = :org_id
          AND e.status IN ('failed', 'completed')
          AND e.completed_at > (NOW() - INTERVAL '48 hours')
    """), {"org_id": org_id})).fetchall()

    for r in rows:
        _read_ids[org_id].add(f"exec-{r[0]}")

    return {"success": True, "marked": len(rows)}


# ─── AI Diagnosis ─────────────────────────────────────────────

@router.post("/{execution_id}/ai-diagnose", summary="Trigger AI diagnosis + auto-fix for failed execution")
async def ai_diagnose_execution(
    execution_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger AI analysis of a failed execution.
    ClaudeClient analyzes the error, workflow config, and execution context,
    then stores diagnosis in execution_journal.
    If fixable, generates a corrected definition, applies it, and re-runs.
    """
    from sqlalchemy import text as sa_text

    # Get execution + workflow info
    row = (await db.execute(sa_text("""
        SELECT e.id, e.status, e.error_message, e.workflow_id,
               w.name, w.definition, w.version, w.organization_id,
               es.state_data
        FROM executions e
        LEFT JOIN workflows w ON w.id = e.workflow_id
        LEFT JOIN execution_states es ON es.execution_id = e.id
        WHERE e.id = :eid
    """), {"eid": execution_id})).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Execution not found")
    if row[1] != "failed":
        raise HTTPException(status_code=400, detail="Only failed executions can be diagnosed")

    error_message = row[2] or "Unknown error"
    workflow_id = str(row[3])
    workflow_name = row[4] or "Unknown"
    definition = row[5] if isinstance(row[5], dict) else (_json.loads(row[5]) if row[5] else {})
    wf_version = row[6] or 1
    org_id = str(row[7])
    state_data = row[8] if isinstance(row[8], dict) else (_json.loads(row[8]) if row[8] else {})

    # Extract step error details
    step_errors = []
    steps = state_data.get("steps", {}) if state_data else {}
    for sid, si in (steps.items() if isinstance(steps, dict) else []):
        if isinstance(si, dict) and si.get("error"):
            step_errors.append({"step": sid, "error": str(si["error"])[:300], "status": si.get("status", "unknown")})

    # ── Step 1: Diagnose ──
    prompt = f"""Analyze this RPA workflow execution failure and provide diagnosis.

WORKFLOW: {workflow_name}
EXECUTION ID: {execution_id}
ERROR: {error_message}

STEP ERRORS:
{_json.dumps(step_errors, indent=2) if step_errors else "No step-level errors captured."}

FULL WORKFLOW DEFINITION:
{_json.dumps(definition, indent=2, default=str)[:3000]}

Respond in this JSON format:
{{
  "diagnosis": "Brief explanation of what went wrong and why",
  "root_cause": "connection_error|auth_error|data_error|config_error|rate_limit|site_changed|timeout|unknown",
  "severity": "low|medium|high|critical",
  "fix_suggestion": "Specific actionable fix",
  "auto_fixable": true/false,
  "auto_fix_action": "retry|fix_definition|null",
  "confidence": 0.0-1.0,
  "needs_definition_change": true/false,
  "affected_steps": ["step-id-1"]
}}

Set "auto_fix_action": "fix_definition" when the issue is a bad selector, wrong URL,
timeout too low, or any config that can be programmatically corrected.
Set "auto_fix_action": "retry" ONLY for transient errors."""

    # Call ClaudeClient
    diagnosis = None
    ai_available = False
    try:
        from integrations.claude_client import get_claude_client
        ai = get_claude_client()
        raw = await ai.analyze(prompt, output_format="json")
        if isinstance(raw, str):
            diagnosis = ai.safe_extract_json(raw)
        elif isinstance(raw, dict):
            diagnosis = raw
        ai_available = True
    except Exception as ai_err:
        logger.warning(f"AI diagnosis failed for {execution_id}: {ai_err}")
        diagnosis = {
            "diagnosis": f"AI analysis unavailable: {str(ai_err)[:100]}",
            "root_cause": "unknown",
            "severity": "medium",
            "fix_suggestion": "Check execution logs manually",
            "auto_fixable": False,
            "auto_fix_action": None,
            "confidence": 0.0,
        }

    # Store diagnosis
    try:
        await db.execute(sa_text("""
            INSERT INTO execution_journal
            (id, execution_id, event_type, message, severity, details, created_at)
            VALUES (gen_random_uuid(), :eid, 'ai_diagnosis', :msg, :severity,
                    CAST(:details AS jsonb), NOW())
        """), {
            "eid": execution_id,
            "msg": diagnosis.get("diagnosis", "AI diagnosis")[:500],
            "severity": diagnosis.get("severity", "medium"),
            "details": _json.dumps(diagnosis),
        })
        await db.commit()
    except Exception as db_err:
        logger.warning(f"Could not store AI diagnosis: {db_err}")

    # ── Step 2: Auto-fix if possible ──
    auto_fixed = False
    fix_result = None
    fix_action = diagnosis.get("auto_fix_action")

    if diagnosis.get("auto_fixable") and fix_action == "fix_definition" and ai_available:
        # ── REAL AUTO-FIX: Ask Claude for corrected definition ──
        fix_prompt = f"""You are an RPA workflow repair AI. Fix this workflow definition.

WORKFLOW: {workflow_name}
ERROR: {error_message[:500]}
DIAGNOSIS: {diagnosis.get('diagnosis', 'Unknown')}
ROOT CAUSE: {diagnosis.get('root_cause', 'unknown')}
AFFECTED STEPS: {_json.dumps(diagnosis.get('affected_steps', []))}

STEP ERRORS:
{_json.dumps(step_errors, indent=2) if step_errors else "None."}

CURRENT DEFINITION (the one that failed):
{_json.dumps(definition, indent=2, default=str)[:4000]}

Return JSON:
{{
  "fixed_definition": {{ ... COMPLETE corrected workflow definition ... }},
  "changes_summary": "Brief description of changes",
  "changes_detail": [
    {{"step_id": "step-1", "field": "config.timeout", "old_value": "30", "new_value": "60", "reason": "Timeout was too low"}}
  ]
}}

Rules: Return FULL definition. Only change what's needed. For selectors: use more robust selectors. For timeouts: increase 2x."""

        try:
            from integrations.claude_client import get_claude_client
            ai = get_claude_client()
            raw = await ai.analyze(fix_prompt, output_format="json")
            if isinstance(raw, str):
                fix_result = ai.safe_extract_json(raw)
            elif isinstance(raw, dict):
                fix_result = raw
        except Exception as fix_err:
            logger.warning(f"AI fix generation failed: {fix_err}")

        if fix_result and "fixed_definition" in fix_result:
            new_definition = fix_result["fixed_definition"]
            changes_summary = fix_result.get("changes_summary", "AI auto-fix applied")
            changes_detail = fix_result.get("changes_detail", [])

            if isinstance(new_definition, dict) and "steps" in new_definition:
                # Apply fix to DB
                try:
                    new_ver = wf_version + 1
                    await db.execute(sa_text("""
                        UPDATE workflows
                        SET definition = CAST(:def AS jsonb),
                            version = :new_ver,
                            updated_at = NOW()
                        WHERE id = :wid
                    """), {
                        "wid": workflow_id,
                        "def": _json.dumps(new_definition),
                        "new_ver": new_ver,
                    })
                    await db.commit()

                    # Log fix history
                    fix_history = {
                        "action": "fix_definition",
                        "changes_summary": changes_summary,
                        "changes_detail": changes_detail,
                        "old_version": wf_version,
                        "new_version": new_ver,
                        "old_definition_snapshot": _json.dumps(definition, default=str)[:5000],
                        "diagnosis": diagnosis.get("diagnosis", ""),
                        "root_cause": diagnosis.get("root_cause", "unknown"),
                        "error_message": error_message[:500],
                    }

                    # Create new execution
                    from uuid import uuid4
                    new_exec_id = str(uuid4())
                    await db.execute(sa_text("""
                        INSERT INTO executions
                        (id, workflow_id, status, trigger_type, created_at)
                        VALUES (:eid, :wid, 'pending', 'ai_auto_fix', NOW())
                    """), {"eid": new_exec_id, "wid": workflow_id})

                    fix_history["new_execution_id"] = new_exec_id

                    await db.execute(sa_text("""
                        INSERT INTO execution_journal
                        (id, execution_id, event_type, message, severity, details, created_at)
                        VALUES (gen_random_uuid(), :eid, 'ai_auto_fix', :msg, 'info',
                                CAST(:details AS jsonb), NOW())
                    """), {
                        "eid": execution_id,
                        "msg": f"AI auto-fix applied: {changes_summary[:300]}",
                        "details": _json.dumps(fix_history),
                    })
                    await db.commit()

                    # Dispatch re-run
                    from worker.tasks.workflow import execute_workflow
                    execute_workflow.delay(
                        execution_id=new_exec_id,
                        workflow_id=workflow_id,
                        organization_id=org_id,
                        definition=new_definition,
                    )

                    auto_fixed = True
                    diagnosis["auto_fixed"] = True
                    diagnosis["fix_applied"] = changes_summary
                    diagnosis["changes_detail"] = changes_detail
                    diagnosis["retry_execution_id"] = new_exec_id
                    diagnosis["old_version"] = wf_version
                    diagnosis["new_version"] = new_ver
                    logger.info(f"AI auto-fix applied to workflow {workflow_id}: v{wf_version} → v{new_ver}, re-running as {new_exec_id}")

                except Exception as apply_err:
                    logger.warning(f"Failed to apply AI fix: {apply_err}")

    elif diagnosis.get("auto_fixable") and fix_action == "retry":
        # ── Simple retry ──
        try:
            from worker.tasks.workflow import execute_workflow
            from uuid import uuid4
            new_exec_id = str(uuid4())
            await db.execute(sa_text("""
                INSERT INTO executions
                (id, workflow_id, status, trigger_type, created_at)
                VALUES (:eid, :wid, 'pending', 'ai_retry', NOW())
            """), {"eid": new_exec_id, "wid": workflow_id})
            await db.commit()

            execute_workflow.delay(
                execution_id=new_exec_id,
                workflow_id=workflow_id,
                organization_id=org_id,
                definition=definition,
            )
            auto_fixed = True
            diagnosis["auto_fixed"] = True
            diagnosis["retry_execution_id"] = new_exec_id

            await db.execute(sa_text("""
                INSERT INTO execution_journal
                (id, execution_id, event_type, message, severity, details, created_at)
                VALUES (gen_random_uuid(), :eid, 'ai_auto_fix', :msg, 'info',
                        CAST(:details AS jsonb), NOW())
            """), {
                "eid": execution_id,
                "msg": f"AI auto-retry triggered: {new_exec_id}",
                "details": _json.dumps({"action": "retry", "new_execution_id": new_exec_id}),
            })
            await db.commit()
            logger.info(f"AI auto-retry triggered: {new_exec_id} (from failed {execution_id})")
        except Exception as retry_err:
            logger.warning(f"Auto-fix retry failed: {retry_err}")

    return {
        "success": True,
        "execution_id": execution_id,
        "diagnosis": diagnosis,
        "auto_fixed": auto_fixed,
    }


# ─── Existing endpoints (unchanged) ─────────────────────────────

@router.get("/status", summary="Get notification manager status")
async def get_notification_status():
    """Get the current status of the notification system."""
    manager = get_notification_manager()
    return manager.get_status()


@router.post("/send", summary="Send a notification")
async def send_notification(request: NotificationSendRequest):
    """Send a notification through the specified channel."""
    from notifications.channels import Notification

    manager = get_notification_manager()

    try:
        channel = NotificationChannel(request.channel)
        priority = NotificationPriority(request.priority)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    notification = Notification(
        title=request.title,
        message=request.message,
        channel=channel,
        priority=priority,
        recipient=request.recipient,
        metadata=request.metadata,
    )

    result = await manager.send(notification)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error or "Delivery failed",
        )

    return {
        "success": True,
        "channel": result.channel.value,
        "recipient": result.recipient,
        "delivered_at": result.delivered_at,
    }


@router.post("/channels/configure", summary="Configure a notification channel")
async def configure_channel(request: ChannelConfigRequest):
    """Configure a notification channel (email, slack, webhook)."""
    manager = get_notification_manager()
    manager.configure_channels({request.channel: request.config})
    return {"message": f"Channel '{request.channel}' configured", "success": True}


@router.post("/test", summary="Send a test notification")
async def send_test_notification(channel: str = "websocket"):
    """Send a test notification to verify channel configuration."""
    manager = get_notification_manager()

    from notifications.channels import Notification
    try:
        ch = NotificationChannel(channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown channel: {channel}",
        )

    notification = Notification(
        title="Test Notification",
        message="This is a test notification from the RPA Automation Engine.",
        channel=ch,
        priority=NotificationPriority.NORMAL,
        metadata={"test": True},
    )

    result = await manager.send(notification)
    return {
        "success": result.success,
        "channel": channel,
        "error": result.error,
    }


# ─── FCM Device Token Management ────────────────────────────

class FCMTokenRequest(BaseModel):
    """Register a device token for push notifications."""
    token: str
    device_name: str = "Unknown"
    platform: str = "web"  # web, android, ios


# In-memory token store (per-org). In production, persist to DB.
_device_tokens: dict[str, list[dict]] = {}


@router.post("/fcm/register", summary="Register FCM device token")
async def register_fcm_token(
    request: FCMTokenRequest,
    current_user=Depends(get_current_active_user),
):
    """Register a device token for push notifications."""
    org_id = current_user.org_id
    user_id = current_user.sub

    if org_id not in _device_tokens:
        _device_tokens[org_id] = []

    # Remove existing entry for same token
    _device_tokens[org_id] = [
        t for t in _device_tokens[org_id] if t["token"] != request.token
    ]

    _device_tokens[org_id].append({
        "token": request.token,
        "user_id": user_id,
        "device_name": request.device_name,
        "platform": request.platform,
    })

    return {"success": True, "message": "Device registered for push notifications"}


@router.delete("/fcm/unregister", summary="Unregister FCM device token")
async def unregister_fcm_token(
    token: str,
    current_user=Depends(get_current_active_user),
):
    """Remove a device token."""
    org_id = current_user.org_id
    if org_id in _device_tokens:
        _device_tokens[org_id] = [
            t for t in _device_tokens[org_id] if t["token"] != token
        ]
    return {"success": True}


@router.get("/fcm/tokens", summary="List registered FCM tokens")
async def list_fcm_tokens(
    current_user=Depends(get_current_active_user),
):
    """List registered device tokens for the current organization."""
    org_id = current_user.org_id
    tokens = _device_tokens.get(org_id, [])
    return {
        "tokens": [
            {"device_name": t["device_name"], "platform": t["platform"]}
            for t in tokens
        ],
        "count": len(tokens),
    }
