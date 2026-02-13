"""Workflow Templates API routes.

Provides a library of pre-built workflow templates that users can browse,
preview, and instantiate as new workflows.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_active_user
from core.security import TokenPayload
from db.models.workflow import Workflow

router = APIRouter()


# ─── Built-in template library ─────────────────────────────────────────────

BUILTIN_TEMPLATES = [
    {
        "id": "tpl-web-scraper",
        "name": "Web Scraper",
        "description": "Scrape data from a website using CSS selectors, then save results to a file.",
        "category": "data-extraction",
        "icon": "🕷️",
        "tags": ["web", "scraping", "data"],
        "difficulty": "beginner",
        "estimated_duration": "2-5 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Scrape Page",
                "type": "web_scrape",
                "config": {
                    "url": "https://example.com",
                    "selectors": [
                        {"name": "title", "selector": "h1", "extract": "text"},
                        {"name": "links", "selector": "a", "extract": "attribute", "attribute": "href", "multiple": True},
                    ],
                },
            },
            {
                "id": "step-2",
                "name": "Transform Data",
                "type": "data_transform",
                "config": {
                    "script": "output = {'title': steps.step_1.title, 'link_count': len(steps.step_1.links)}",
                },
                "depends_on": ["step-1"],
            },
        ],
    },
    {
        "id": "tpl-api-monitor",
        "name": "API Health Monitor",
        "description": "Periodically check an API endpoint and send alerts on failure.",
        "category": "monitoring",
        "icon": "🔍",
        "tags": ["api", "monitoring", "health", "alerts"],
        "difficulty": "beginner",
        "estimated_duration": "1-2 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Check API",
                "type": "http_request",
                "config": {
                    "url": "https://api.example.com/health",
                    "method": "GET",
                    "timeout": 10,
                    "validate": {"status_code": [200]},
                },
            },
            {
                "id": "step-2",
                "name": "Alert on Failure",
                "type": "condition",
                "config": {
                    "condition": "{{ steps.step_1.success == false }}",
                    "on_true": "step-3",
                },
                "depends_on": ["step-1"],
            },
            {
                "id": "step-3",
                "name": "Send Alert Email",
                "type": "http_request",
                "config": {
                    "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
                    "method": "POST",
                    "body": {"text": "🚨 API health check failed!"},
                },
                "depends_on": ["step-2"],
            },
        ],
    },
    {
        "id": "tpl-form-automation",
        "name": "Form Submission Bot",
        "description": "Navigate to a page, fill a form with data, submit it, and capture the result.",
        "category": "browser-automation",
        "icon": "📝",
        "tags": ["form", "automation", "browser", "submit"],
        "difficulty": "intermediate",
        "estimated_duration": "3-8 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Fill Form",
                "type": "form_fill",
                "config": {
                    "url": "https://example.com/contact",
                    "fields": [
                        {"selector": "#name", "value": "John Doe", "action": "fill"},
                        {"selector": "#email", "value": "john@example.com", "action": "fill"},
                        {"selector": "#message", "value": "Automated message", "action": "fill"},
                    ],
                    "submit": "button[type=submit]",
                    "screenshot_after": True,
                },
            },
        ],
    },
    {
        "id": "tpl-data-pipeline",
        "name": "Data Pipeline",
        "description": "Fetch data from an API, transform it, and send results to another API.",
        "category": "data-extraction",
        "icon": "🔄",
        "tags": ["etl", "pipeline", "api", "data"],
        "difficulty": "intermediate",
        "estimated_duration": "2-5 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Fetch Source Data",
                "type": "http_request",
                "config": {
                    "url": "https://jsonplaceholder.typicode.com/posts",
                    "method": "GET",
                    "extract": {"json_path": "$.data"},
                },
            },
            {
                "id": "step-2",
                "name": "Transform",
                "type": "data_transform",
                "config": {
                    "script": "output = [{'id': p['id'], 'title': p['title']} for p in input_data[:10]]",
                },
                "depends_on": ["step-1"],
            },
            {
                "id": "step-3",
                "name": "Send to Destination",
                "type": "http_request",
                "config": {
                    "url": "https://httpbin.org/post",
                    "method": "POST",
                    "body_type": "json",
                },
                "depends_on": ["step-2"],
            },
        ],
    },
    {
        "id": "tpl-report-generator",
        "name": "PDF Report Generator",
        "description": "Generate a PDF report from a web dashboard page.",
        "category": "reporting",
        "icon": "📄",
        "tags": ["pdf", "report", "dashboard", "export"],
        "difficulty": "beginner",
        "estimated_duration": "1-3 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Generate PDF",
                "type": "pdf_generate",
                "config": {
                    "url": "https://example.com/dashboard",
                    "format": "A4",
                    "print_background": True,
                    "wait_for": ".chart-loaded",
                },
            },
        ],
    },
    {
        "id": "tpl-screenshot-monitor",
        "name": "Visual Regression Monitor",
        "description": "Take periodic screenshots of a page for visual change detection.",
        "category": "monitoring",
        "icon": "📸",
        "tags": ["screenshot", "monitoring", "visual", "regression"],
        "difficulty": "beginner",
        "estimated_duration": "1-2 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Capture Screenshot",
                "type": "screenshot",
                "config": {
                    "url": "https://example.com",
                    "full_page": True,
                    "format": "png",
                },
            },
        ],
    },
    {
        "id": "tpl-multi-step-scraper",
        "name": "Multi-Page Scraper",
        "description": "Navigate through multiple pages, interact with elements, and collect data.",
        "category": "data-extraction",
        "icon": "🌐",
        "tags": ["scraping", "multi-page", "browser", "navigation"],
        "difficulty": "advanced",
        "estimated_duration": "5-15 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Navigate & Interact",
                "type": "page_interaction",
                "config": {
                    "url": "https://example.com/search",
                    "steps": [
                        {"action": "fill", "selector": "#search", "value": "RPA automation"},
                        {"action": "press", "key": "Enter"},
                        {"action": "wait", "selector": ".results"},
                        {"action": "screenshot", "name": "search_results"},
                    ],
                },
            },
            {
                "id": "step-2",
                "name": "Extract Results",
                "type": "web_scrape",
                "config": {
                    "url": "{{ steps.step_1.final_url }}",
                    "selectors": [
                        {"name": "results", "selector": ".result-item h3", "extract": "text", "multiple": True},
                    ],
                },
                "depends_on": ["step-1"],
            },
        ],
    },
    {
        "id": "tpl-ai-classifier",
        "name": "AI Content Classifier",
        "description": "Fetch content, classify it using Claude AI, and route based on the result.",
        "category": "ai-powered",
        "icon": "🤖",
        "tags": ["ai", "classification", "routing", "claude"],
        "difficulty": "intermediate",
        "estimated_duration": "3-8 min",
        "steps": [
            {
                "id": "step-1",
                "name": "Fetch Content",
                "type": "http_request",
                "config": {
                    "url": "https://api.example.com/tickets/latest",
                    "method": "GET",
                },
            },
            {
                "id": "step-2",
                "name": "Classify with AI",
                "type": "ai_classify",
                "config": {
                    "input": "{{ steps.step_1.data }}",
                    "categories": ["bug", "feature_request", "question", "complaint"],
                },
                "depends_on": ["step-1"],
            },
            {
                "id": "step-3",
                "name": "Route by Category",
                "type": "condition",
                "config": {
                    "condition": "{{ steps.step_2.category == 'bug' }}",
                    "on_true": "step-4-bug",
                    "on_false": "step-4-other",
                },
                "depends_on": ["step-2"],
            },
        ],
    },
]


# ─── Endpoints ──────────────────────────────────────────────────────────────

class TemplateInstantiateRequest(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None


@router.get("")
async def list_templates(
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """List all available workflow templates."""
    templates = BUILTIN_TEMPLATES

    if category:
        templates = [t for t in templates if t["category"] == category]
    if difficulty:
        templates = [t for t in templates if t["difficulty"] == difficulty]
    if search:
        q = search.lower()
        templates = [
            t for t in templates
            if q in t["name"].lower()
            or q in t["description"].lower()
            or any(q in tag for tag in t.get("tags", []))
        ]

    # Return without step details for list view
    result = []
    for t in templates:
        result.append({
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "icon": t["icon"],
            "tags": t["tags"],
            "difficulty": t["difficulty"],
            "estimated_duration": t["estimated_duration"],
            "step_count": len(t["steps"]),
        })

    return {"templates": result, "total": len(result)}


@router.get("/categories")
async def list_categories(
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Get distinct template categories."""
    cats = sorted(set(t["category"] for t in BUILTIN_TEMPLATES))
    return {"categories": cats}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: TokenPayload = Depends(get_current_active_user),
):
    """Get a single template with full step details."""
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/{template_id}/instantiate")
async def instantiate_template(
    template_id: str,
    body: TemplateInstantiateRequest,
    current_user: TokenPayload = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow from a template."""
    template = None
    for t in BUILTIN_TEMPLATES:
        if t["id"] == template_id:
            template = t
            break

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    import uuid

    workflow = Workflow(
        id=str(uuid.uuid4()),
        organization_id=current_user.org,
        created_by=current_user.sub,
        name=body.name,
        description=body.description or template["description"],
        definition={
            "steps": template["steps"],
            "source_template": template_id,
        },
        version=1,
        status="draft",
    )

    db.add(workflow)
    await db.flush()

    return {
        "workflow_id": workflow.id,
        "name": workflow.name,
        "template_id": template_id,
        "template_name": template["name"],
        "status": "draft",
        "message": f"Workflow created from template '{template['name']}'",
    }
