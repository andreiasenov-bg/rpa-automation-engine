"""Chat assistant API routes.

Provides AI-powered chat assistance for the RPA platform.
Uses configurable AI backend (Claude, OpenAI, etc.) or falls back to
predefined knowledge base responses.

Stage 1+2: Action buttons in responses + execute actions from chat.
"""

import os
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.security import get_current_user

router = APIRouter()

# In-memory conversation storage (per-session, cleared on restart)
conversations: dict[str, list[dict]] = {}


# ── Action models ──────────────────────────────────────────────────────────

class ChatAction(BaseModel):
    """An action the user can execute from the chat."""
    type: str       # navigate, execute_workflow, retry_execution, cancel_execution, view_logs, create_workflow
    label: str      # Button text
    icon: str       # Lucide icon name: ArrowRight, Play, RotateCcw, XCircle, Eye, Plus
    params: dict    # Type-specific params (path, workflow_id, execution_id, etc.)
    confirm: bool = False   # Require confirmation before executing


# ── Request / Response models ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    page_context: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversationId: str
    actions: list[ChatAction] = []


class ExecuteActionRequest(BaseModel):
    conversation_id: Optional[str] = None
    action: ChatAction


class ExecuteActionResponse(BaseModel):
    success: bool
    message: str
    execution_id: Optional[str] = None
    redirect: Optional[str] = None


class ClearRequest(BaseModel):
    conversation_id: str


# ── Knowledge base with actions ────────────────────────────────────────────

KNOWLEDGE_BASE: dict[str, dict] = {
    "workflow": {
        "text": "Workflows are automated processes made of connected steps. Create one in the Workflows page, add steps in the visual editor, then Publish to make it executable. Steps include: Web Scraping, API Request, Form Fill, Email, Database, File Ops, Custom Script, Conditional, Loop, and Delay.",
        "actions": [
            {"type": "navigate", "label": "Go to Workflows", "icon": "ArrowRight", "params": {"path": "/workflows"}},
            {"type": "navigate", "label": "Create New Workflow", "icon": "Plus", "params": {"path": "/workflows?action=create"}},
        ],
    },
    "publish": {
        "text": "To publish a workflow: 1) Open it in the visual editor, 2) Click the 'Publish' button in the toolbar. Published workflows can be executed manually, via triggers, or on schedules. Draft workflows cannot run.",
        "actions": [
            {"type": "navigate", "label": "Go to Workflows", "icon": "ArrowRight", "params": {"path": "/workflows"}},
        ],
    },
    "execution": {
        "text": "Executions are instances of running workflows. Monitor them in the Executions page. You can filter by status (Pending, Running, Completed, Failed, Cancelled), expand rows for logs, retry failed ones, or export data to CSV.",
        "actions": [
            {"type": "navigate", "label": "View Executions", "icon": "Eye", "params": {"path": "/executions"}},
        ],
    },
    "trigger": {
        "text": "Triggers automatically start workflows on events. Types: Cron (scheduled), Webhook (HTTP callback), File Watcher, Email, Database, API Poll, Manual, Event. Create them in the Triggers page.",
        "actions": [
            {"type": "navigate", "label": "Go to Triggers", "icon": "ArrowRight", "params": {"path": "/triggers"}},
        ],
    },
    "schedule": {
        "text": "Schedules run workflows at specific times using cron expressions. Format: minute hour day month weekday. Examples: '*/5 * * * *' = every 5 min, '0 9 * * 1-5' = weekdays at 9 AM.",
        "actions": [
            {"type": "navigate", "label": "Go to Schedules", "icon": "ArrowRight", "params": {"path": "/schedules"}},
        ],
    },
    "credential": {
        "text": "The Credentials vault stores API keys, passwords, and tokens encrypted with AES-256. Types: API Key, OAuth 2.0, Basic Auth, Database, Private Key, Custom. Values are never exposed in logs.",
        "actions": [
            {"type": "navigate", "label": "Go to Credentials", "icon": "ArrowRight", "params": {"path": "/credentials"}},
        ],
    },
    "agent": {
        "text": "Agents are distributed workers that execute tasks. Register them in the Agents page. After registration, save the token immediately — it's shown only once! Green pulsing dot = online.",
        "actions": [
            {"type": "navigate", "label": "Go to Agents", "icon": "ArrowRight", "params": {"path": "/agents"}},
        ],
    },
    "cron": {
        "text": "Cron expression format: [minute] [hour] [day] [month] [weekday]. Examples: '*/5 * * * *' = every 5 min, '0 */2 * * *' = every 2 hours, '0 9 * * 1-5' = weekdays at 9:00, '0 0 1 * *' = 1st of each month.",
        "actions": [
            {"type": "navigate", "label": "Go to Schedules", "icon": "ArrowRight", "params": {"path": "/schedules"}},
        ],
    },
    "template": {
        "text": "Templates are pre-built workflow patterns for common tasks. Browse by category (Data Extraction, Monitoring, Browser Automation, Reporting, AI Powered) and difficulty. Click 'Use' to create a workflow from a template.",
        "actions": [
            {"type": "navigate", "label": "Browse Templates", "icon": "ArrowRight", "params": {"path": "/templates"}},
        ],
    },
    "dashboard": {
        "text": "The Dashboard shows statistics, system health, quick actions, success rate, and recent executions. Customize visible widgets with the gear icon. Click stat cards to navigate to detailed views.",
        "actions": [
            {"type": "navigate", "label": "Go to Dashboard", "icon": "ArrowRight", "params": {"path": "/"}},
        ],
    },
    "audit": {
        "text": "The Audit Log records all system actions: create, read, update, delete, execute, login, logout, export, decrypt. Expand rows to see exact changes (old vs new values). Filter by action type or resource.",
        "actions": [
            {"type": "navigate", "label": "View Audit Log", "icon": "Eye", "params": {"path": "/audit-log"}},
        ],
    },
    "plugin": {
        "text": "Plugins extend the platform with new task types. Sources: Builtin (included), Entrypoint (from packages), Local (custom). Toggle on/off with the power icon. Reload all with the refresh button.",
        "actions": [
            {"type": "navigate", "label": "Go to Plugins", "icon": "ArrowRight", "params": {"path": "/plugins"}},
        ],
    },
    "role": {
        "text": "Roles define what users can do. Manage them in Admin > Roles. Each role has a set of permissions. The admin role cannot be deleted. Assign roles to users in Admin > Users.",
        "actions": [
            {"type": "navigate", "label": "Go to Admin", "icon": "ArrowRight", "params": {"path": "/admin"}},
        ],
    },
    "settings": {
        "text": "Settings has 5 tabs: Profile (name), Organization, Security, Notifications, and Appearance (theme + language). Switch between light/dark theme in Appearance.",
        "actions": [
            {"type": "navigate", "label": "Open Settings", "icon": "ArrowRight", "params": {"path": "/settings"}},
        ],
    },
    "editor": {
        "text": "The Workflow Editor is a visual drag-and-drop canvas. Drag tasks from the palette on the right. Connect steps by dragging handles. Keyboard: Ctrl+S save, Ctrl+Z undo, Delete remove, ? help.",
        "actions": [
            {"type": "navigate", "label": "Go to Workflows", "icon": "ArrowRight", "params": {"path": "/workflows"}},
        ],
    },
    "error": {
        "text": "If an execution fails: 1) Check the error message by expanding the execution row, 2) Fix the issue (wrong credentials, API down, etc.), 3) Click 'Retry' to re-run with same parameters.",
        "actions": [
            {"type": "navigate", "label": "View Executions", "icon": "Eye", "params": {"path": "/executions"}},
        ],
    },
    "retry": {
        "text": "To retry a failed execution, go to the Executions page, find the failed execution, and click the Retry button. You can also retry directly from here if you provide the execution ID.",
        "actions": [
            {"type": "navigate", "label": "View Executions", "icon": "Eye", "params": {"path": "/executions"}},
        ],
    },
    "run": {
        "text": "To run a workflow, go to the Workflows page, find the workflow you want, and click the Play button. You can also run it from the workflow editor. Make sure it's published first!",
        "actions": [
            {"type": "navigate", "label": "Go to Workflows", "icon": "ArrowRight", "params": {"path": "/workflows"}},
        ],
    },
    "default": {
        "text": "I'm the RPA Platform AI Assistant. I can help you with: creating workflows, understanding features, configuring triggers and schedules, managing credentials, troubleshooting errors, and more. What would you like to know?",
        "actions": [
            {"type": "navigate", "label": "Go to Dashboard", "icon": "ArrowRight", "params": {"path": "/"}},
            {"type": "navigate", "label": "Browse Templates", "icon": "ArrowRight", "params": {"path": "/templates"}},
        ],
    },
}

# Page-specific context for better answers
PAGE_CONTEXT_HINTS: dict[str, str] = {
    "/": "The user is on the Dashboard page.",
    "/workflows": "The user is on the Workflows list page.",
    "/executions": "The user is on the Executions monitoring page.",
    "/credentials": "The user is on the Credentials vault page.",
    "/triggers": "The user is on the Triggers management page.",
    "/schedules": "The user is on the Schedules page.",
    "/agents": "The user is on the Agents management page.",
    "/templates": "The user is on the Templates library page.",
    "/settings": "The user is on the Settings page.",
    "/admin": "The user is on the Admin panel.",
    "/audit-log": "The user is on the Audit Log page.",
    "/plugins": "The user is on the Plugins page.",
}


def find_best_answer(question: str) -> dict:
    """Find the most relevant answer from the knowledge base."""
    q = question.lower()

    keyword_map = {
        "workflow": ["workflow", "процес", "автоматизац"],
        "publish": ["publish", "публик"],
        "execution": ["execution", "изпълнен", "стартир"],
        "trigger": ["trigger", "тригер"],
        "schedule": ["schedule", "график", "cron"],
        "credential": ["credential", "удостоверен", "парол", "password", "api key", "ключ", "token"],
        "agent": ["agent", "агент"],
        "cron": ["cron", "крон"],
        "template": ["template", "шаблон"],
        "dashboard": ["dashboard", "табло"],
        "audit": ["audit", "одит", "лог", "log"],
        "plugin": ["plugin", "плъгин"],
        "role": ["role", "рол", "permission", "разрешен", "rbac"],
        "settings": ["setting", "настройк", "тема", "theme"],
        "editor": ["editor", "редактор", "drag", "drop", "canvas", "стъпк", "step"],
        "error": ["error", "грешк", "fail", "неуспеш"],
        "retry": ["retry", "повтор", "re-run", "отново"],
        "run": ["run", "стартирай", "пусни", "execute", "изпълни"],
    }

    best_topic = "default"
    best_score = 0

    for topic, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > best_score:
            best_score = score
            best_topic = topic

    return KNOWLEDGE_BASE[best_topic]


@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    req: ChatRequest,
    current_user=Depends(get_current_user),
):
    """Send a message to the AI chat assistant."""
    conv_id = req.conversation_id or str(uuid.uuid4())[:8]

    # Store message in conversation history
    if conv_id not in conversations:
        conversations[conv_id] = []
    conversations[conv_id].append({"role": "user", "content": req.message})

    actions: list[dict] = []

    # Try external AI API first
    chat_api_url = os.environ.get("CHAT_API_URL")
    chat_api_key = os.environ.get("CHAT_API_KEY")

    if chat_api_url and chat_api_key:
        try:
            import httpx

            page_hint = PAGE_CONTEXT_HINTS.get(req.page_context or "/", "")
            system_prompt = f"""You are an intelligent assistant for the RPA Automation Engine platform.
You help users with creating workflows, managing executions, configuring triggers,
storing credentials, and understanding all platform features.
{page_hint}
Be concise, helpful, and provide actionable answers.
If the user writes in Bulgarian, respond in Bulgarian.
Platform features: Workflows (visual drag-and-drop editor with 10 task types),
Executions (real-time monitoring), Credentials (AES-256 encrypted vault),
Triggers (cron, webhook, file watcher, email, database, API poll, manual, event),
Schedules (cron-based), Agents (distributed workers), Templates (pre-built patterns),
Admin (roles, permissions, RBAC), Audit Log, Plugins, Analytics Dashboard.

IMPORTANT: After your text response, you may include a JSON actions block.
Format: ACTIONS_JSON:[{{"type":"navigate","label":"Go to X","icon":"ArrowRight","params":{{"path":"/x"}},"confirm":false}}]
Action types: navigate, execute_workflow, retry_execution, cancel_execution, view_logs, create_workflow
Icons: ArrowRight, Play, RotateCcw, XCircle, Eye, Plus
Only include actions that are directly relevant to the user's question."""

            messages = [{"role": "system", "content": system_prompt}]
            for msg in conversations[conv_id][-10:]:
                messages.append(msg)

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    chat_api_url,
                    json={"model": os.environ.get("CHAT_MODEL", "claude-sonnet-4-20250514"), "messages": messages, "max_tokens": 600},
                    headers={"Authorization": f"Bearer {chat_api_key}", "Content-Type": "application/json"},
                )
                data = resp.json()

                if "choices" in data:
                    answer = data["choices"][0]["message"]["content"]
                elif "content" in data:
                    answer = data["content"][0]["text"]
                else:
                    kb = find_best_answer(req.message)
                    answer = kb["text"]
                    actions = kb.get("actions", [])

                # Parse actions from AI response if present
                if "ACTIONS_JSON:" in answer:
                    import json
                    parts = answer.split("ACTIONS_JSON:")
                    answer = parts[0].strip()
                    try:
                        actions = json.loads(parts[1].strip())
                    except (json.JSONDecodeError, IndexError):
                        pass
                elif not actions:
                    # Fallback: add relevant actions from knowledge base
                    kb = find_best_answer(req.message)
                    actions = kb.get("actions", [])

        except Exception:
            kb = find_best_answer(req.message)
            answer = kb["text"]
            actions = kb.get("actions", [])
    else:
        kb = find_best_answer(req.message)
        answer = kb["text"]
        actions = kb.get("actions", [])

    conversations[conv_id].append({"role": "assistant", "content": answer})

    # Keep conversation history manageable
    if len(conversations[conv_id]) > 20:
        conversations[conv_id] = conversations[conv_id][-20:]

    return ChatResponse(
        response=answer,
        conversationId=conv_id,
        actions=[ChatAction(**a) for a in actions],
    )


@router.post("/execute-action", response_model=ExecuteActionResponse)
async def execute_action(
    req: ExecuteActionRequest,
    current_user=Depends(get_current_user),
):
    """Execute an action from the chat assistant.

    Supports: navigate, execute_workflow, retry_execution,
    cancel_execution, view_logs, create_workflow.
    """
    action = req.action
    action_type = action.type
    params = action.params

    try:
        if action_type == "navigate":
            return ExecuteActionResponse(
                success=True,
                message=f"Navigating to {params.get('path', '/')}",
                redirect=params.get("path", "/"),
            )

        elif action_type == "execute_workflow":
            workflow_id = params.get("workflow_id")
            if not workflow_id:
                return ExecuteActionResponse(success=False, message="No workflow ID provided.")
            # Import and call workflow execution service
            try:
                from db.database import get_db
                from sqlalchemy.orm import Session
                db: Session = next(get_db())
                from db.models.execution import Execution
                from db.models.workflow import Workflow
                wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
                if not wf:
                    return ExecuteActionResponse(success=False, message=f"Workflow {workflow_id} not found.")
                new_exec = Execution(
                    workflow_id=wf.id,
                    status="pending",
                    triggered_by=current_user.get("sub", "chat"),
                    trigger_type="manual",
                )
                db.add(new_exec)
                db.commit()
                db.refresh(new_exec)
                return ExecuteActionResponse(
                    success=True,
                    message=f"Workflow '{wf.name}' started successfully!",
                    execution_id=str(new_exec.id),
                    redirect=f"/executions",
                )
            except Exception as e:
                return ExecuteActionResponse(success=False, message=f"Could not start workflow: {str(e)}")

        elif action_type == "retry_execution":
            execution_id = params.get("execution_id")
            if not execution_id:
                return ExecuteActionResponse(success=False, message="No execution ID provided.")
            try:
                from db.database import get_db
                from sqlalchemy.orm import Session
                db: Session = next(get_db())
                from db.models.execution import Execution
                old_exec = db.query(Execution).filter(Execution.id == execution_id).first()
                if not old_exec:
                    return ExecuteActionResponse(success=False, message=f"Execution {execution_id} not found.")
                new_exec = Execution(
                    workflow_id=old_exec.workflow_id,
                    status="pending",
                    triggered_by=current_user.get("sub", "chat"),
                    trigger_type="retry",
                )
                db.add(new_exec)
                db.commit()
                db.refresh(new_exec)
                return ExecuteActionResponse(
                    success=True,
                    message=f"Execution retried! New execution ID: {new_exec.id}",
                    execution_id=str(new_exec.id),
                    redirect="/executions",
                )
            except Exception as e:
                return ExecuteActionResponse(success=False, message=f"Retry failed: {str(e)}")

        elif action_type == "cancel_execution":
            execution_id = params.get("execution_id")
            if not execution_id:
                return ExecuteActionResponse(success=False, message="No execution ID provided.")
            try:
                from db.database import get_db
                from sqlalchemy.orm import Session
                db: Session = next(get_db())
                from db.models.execution import Execution
                ex = db.query(Execution).filter(Execution.id == execution_id).first()
                if not ex:
                    return ExecuteActionResponse(success=False, message=f"Execution {execution_id} not found.")
                if ex.status not in ("pending", "running"):
                    return ExecuteActionResponse(success=False, message=f"Cannot cancel — status is '{ex.status}'.")
                ex.status = "cancelled"
                db.commit()
                return ExecuteActionResponse(
                    success=True,
                    message=f"Execution {execution_id} cancelled.",
                    redirect="/executions",
                )
            except Exception as e:
                return ExecuteActionResponse(success=False, message=f"Cancel failed: {str(e)}")

        elif action_type == "view_logs":
            execution_id = params.get("execution_id")
            if execution_id:
                return ExecuteActionResponse(
                    success=True,
                    message="Opening execution logs...",
                    redirect=f"/executions?expand={execution_id}",
                )
            return ExecuteActionResponse(success=True, message="Opening executions...", redirect="/executions")

        elif action_type == "create_workflow":
            return ExecuteActionResponse(
                success=True,
                message="Opening workflow creator...",
                redirect="/workflows?action=create",
            )

        else:
            return ExecuteActionResponse(success=False, message=f"Unknown action type: {action_type}")

    except Exception as e:
        return ExecuteActionResponse(success=False, message=f"Action failed: {str(e)}")


@router.post("/clear")
async def clear_conversation(
    req: ClearRequest,
    current_user=Depends(get_current_user),
):
    """Clear conversation history."""
    conversations.pop(req.conversation_id, None)
    return {"success": True}


@router.get("/suggestions")
async def get_suggestions(
    page_context: str = "/",
    current_user=Depends(get_current_user),
):
    """Get suggested questions for the current page context."""
    suggestions_map = {
        "/": ["How do I create my first workflow?", "What do the dashboard stats mean?"],
        "/workflows": ["How do I publish a workflow?", "What's the difference between Draft and Published?"],
        "/executions": ["Why did my execution fail?", "How do I retry a failed execution?"],
        "/credentials": ["How are credentials encrypted?", "What types can I store?"],
        "/triggers": ["What is a cron expression?", "How do webhooks work?"],
        "/schedules": ["Common cron expressions?", "How to schedule a daily task?"],
        "/agents": ["How to register a new agent?", "What do agent statuses mean?"],
    }
    return {"suggestions": suggestions_map.get(page_context, suggestions_map["/"])}
