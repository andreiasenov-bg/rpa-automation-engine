"""Chat assistant API routes.

Provides AI-powered chat assistance for the RPA platform.
Uses configurable AI backend (Claude, OpenAI, etc.) or falls back to
predefined knowledge base responses.
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

# Platform knowledge base for fallback responses
KNOWLEDGE_BASE: dict[str, str] = {
    "workflow": "Workflows are automated processes made of connected steps. Create one in the Workflows page, add steps in the visual editor, then Publish to make it executable. Steps include: Web Scraping, API Request, Form Fill, Email, Database, File Ops, Custom Script, Conditional, Loop, and Delay.",
    "publish": "To publish a workflow: 1) Open it in the visual editor, 2) Click the 'Publish' button in the toolbar. Published workflows can be executed manually, via triggers, or on schedules. Draft workflows cannot run.",
    "execution": "Executions are instances of running workflows. Monitor them in the Executions page. You can filter by status (Pending, Running, Completed, Failed, Cancelled), expand rows for logs, retry failed ones, or export data to CSV.",
    "trigger": "Triggers automatically start workflows on events. Types: Cron (scheduled), Webhook (HTTP callback), File Watcher, Email, Database, API Poll, Manual, Event. Create them in the Triggers page.",
    "schedule": "Schedules run workflows at specific times using cron expressions. Format: minute hour day month weekday. Examples: '*/5 * * * *' = every 5 min, '0 9 * * 1-5' = weekdays at 9 AM.",
    "credential": "The Credentials vault stores API keys, passwords, and tokens encrypted with AES-256. Types: API Key, OAuth 2.0, Basic Auth, Database, Private Key, Custom. Values are never exposed in logs.",
    "agent": "Agents are distributed workers that execute tasks. Register them in the Agents page. After registration, save the token immediately — it's shown only once! Green pulsing dot = online.",
    "cron": "Cron expression format: [minute] [hour] [day] [month] [weekday]. Examples: '*/5 * * * *' = every 5 min, '0 */2 * * *' = every 2 hours, '0 9 * * 1-5' = weekdays at 9:00, '0 0 1 * *' = 1st of each month.",
    "template": "Templates are pre-built workflow patterns for common tasks. Browse by category (Data Extraction, Monitoring, Browser Automation, Reporting, AI Powered) and difficulty. Click 'Use' to create a workflow from a template.",
    "dashboard": "The Dashboard shows statistics, system health, quick actions, success rate, and recent executions. Customize visible widgets with the gear icon. Click stat cards to navigate to detailed views.",
    "audit": "The Audit Log records all system actions: create, read, update, delete, execute, login, logout, export, decrypt. Expand rows to see exact changes (old vs new values). Filter by action type or resource.",
    "plugin": "Plugins extend the platform with new task types. Sources: Builtin (included), Entrypoint (from packages), Local (custom). Toggle on/off with the power icon. Reload all with the refresh button.",
    "role": "Roles define what users can do. Manage them in Admin > Roles. Each role has a set of permissions. The admin role cannot be deleted. Assign roles to users in Admin > Users.",
    "settings": "Settings has 5 tabs: Profile (name), Organization, Security, Notifications, and Appearance (theme + language). Switch between light/dark theme in Appearance.",
    "editor": "The Workflow Editor is a visual drag-and-drop canvas. Drag tasks from the palette on the right. Connect steps by dragging handles. Keyboard: Ctrl+S save, Ctrl+Z undo, Delete remove, ? help.",
    "error": "If an execution fails: 1) Check the error message by expanding the execution row, 2) Fix the issue (wrong credentials, API down, etc.), 3) Click 'Retry' to re-run with same parameters.",
    "default": "I'm the RPA Platform AI Assistant. I can help you with: creating workflows, understanding features, configuring triggers and schedules, managing credentials, troubleshooting errors, and more. What would you like to know?",
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


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    page_context: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversationId: str


class ClearRequest(BaseModel):
    conversation_id: str


def find_best_answer(question: str) -> str:
    """Find the most relevant answer from the knowledge base."""
    q = question.lower()

    # Check each topic keyword
    keyword_map = {
        "workflow": ["workflow", "процес", "автоматизац"],
        "publish": ["publish", "публик"],
        "execution": ["execution", "изпълнен", "run", "стартир"],
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
        "error": ["error", "грешк", "fail", "неуспеш", "retry", "повтор"],
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
Admin (roles, permissions, RBAC), Audit Log, Plugins, Analytics Dashboard."""

            messages = [{"role": "system", "content": system_prompt}]
            # Add conversation history (last 10 messages)
            for msg in conversations[conv_id][-10:]:
                messages.append(msg)

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    chat_api_url,
                    json={"model": os.environ.get("CHAT_MODEL", "claude-sonnet-4-20250514"), "messages": messages, "max_tokens": 500},
                    headers={"Authorization": f"Bearer {chat_api_key}", "Content-Type": "application/json"},
                )
                data = resp.json()

                # Support both OpenAI and Anthropic response formats
                if "choices" in data:
                    answer = data["choices"][0]["message"]["content"]
                elif "content" in data:
                    answer = data["content"][0]["text"]
                else:
                    answer = find_best_answer(req.message)
        except Exception:
            answer = find_best_answer(req.message)
    else:
        # Fallback to knowledge base
        answer = find_best_answer(req.message)

    conversations[conv_id].append({"role": "assistant", "content": answer})

    # Keep conversation history manageable
    if len(conversations[conv_id]) > 20:
        conversations[conv_id] = conversations[conv_id][-20:]

    return ChatResponse(response=answer, conversationId=conv_id)


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
