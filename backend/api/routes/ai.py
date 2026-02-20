"""
AI Integration API Routes.

Endpoints for interacting with Claude AI directly and managing AI configuration.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from integrations.claude_client import get_claude_client
from tasks.registry import get_task_registry


router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────

class AIAskRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    conversation_id: Optional[str] = None


class AIAnalyzeRequest(BaseModel):
    data: str
    instruction: str
    output_format: str = "text"


class AIDecideRequest(BaseModel):
    context: str
    options: List[str]
    criteria: Optional[str] = None


class AIClassifyRequest(BaseModel):
    text: str
    categories: List[str]
    multi_label: bool = False


class AIExtractRequest(BaseModel):
    text: str
    schema_def: Dict[str, Any]


class AISummarizeRequest(BaseModel):
    text: str
    max_length: Optional[int] = None
    style: str = "concise"


class AIResponse(BaseModel):
    success: bool
    result: Any
    metadata: Optional[Dict[str, Any]] = None


# ─── Endpoints ───────────────────────────────────────────────────────

@router.get("/status")
async def get_ai_status():
    """Get Claude AI connection status and usage statistics."""
    client = await get_claude_client()
    return await client.get_status()


@router.get("/task-types")
async def list_ai_task_types():
    """List all available AI task types for workflow builder."""
    registry = get_task_registry()
    return [t for t in registry.list_all() if t["task_type"].startswith("ai_")]


@router.post("/ask", response_model=AIResponse)
async def ai_ask(request: AIAskRequest):
    """Send a prompt to Claude and get a response."""
    client = await get_claude_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Claude AI not configured. Set ANTHROPIC_API_KEY.")

    # JSON Schema for workflow structured output
    workflow_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "A descriptive name for the workflow"
            },
            "description": {
                "type": "string",
                "description": "What this workflow does"
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Unique step ID like step-1, step-2"},
                        "name": {"type": "string", "description": "Human-readable step name"},
                        "type": {
                            "type": "string",
                            "enum": ["web_scrape", "http_request", "custom_script",
                                     "data_transform", "email_send", "file_write",
                                     "database_query", "condition", "loop", "ai_ask"],
                            "description": "Task type from the available types"
                        },
                        "config": {"type": "object", "description": "Type-specific configuration"},
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of steps this depends on"
                        }
                    },
                    "required": ["id", "name", "type", "config", "depends_on"]
                },
                "description": "Ordered list of workflow steps"
            }
        },
        "required": ["name", "description", "steps"]
    }

    try:
        workflow_def = await client.ask_json(
            prompt=prompt,
            schema=workflow_schema,
            tool_name="generate_workflow",
            tool_description="Generate a complete RPA workflow definition with steps",
            system=system_prompt,
            model=None,
            max_tokens=4096,
            temperature=0.3,
        )

        return {
            "success": True,
            "workflow": {
                "name": workflow_def.get("name", "AI Generated Workflow"),
                "description": workflow_def.get("description", request.description),
                "steps": workflow_def.get("steps", []),
            }
        }

    except ValueError:
        try:
            response = await client.ask(
                prompt=prompt,
                system=system_prompt,
                temperature=0.3,
                max_tokens=4096,
            )
            from integrations.claude_client import extract_json
            workflow_def = extract_json(response)
            return {
                "success": True,
                "workflow": {
                    "name": workflow_def.get("name", "AI Generated Workflow"),
                    "description": workflow_def.get("description", request.description),
                    "steps": workflow_def.get("steps", []),
                }
            }
        except Exception as fallback_err:
            return {
                "success": False,
                "error": f"AI could not generate valid workflow: {str(fallback_err)}",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AIResponse)
async def ai_analyze(request: AIAnalyzeRequest):
    """Analyze data with Claude."""
    client = await get_claude_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Claude AI not configured")

    try:
        response = await client.analyze(
            data=request.data,
            instruction=request.instruction,
            output_format=request.output_format,
        )
        return AIResponse(success=True, result=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decide", response_model=AIResponse)
async def ai_decide(request: AIDecideRequest):
    """Let Claude make a decision based on context and options."""
    client = await get_claude_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Claude AI not configured")

    try:
        result = await client.decide(
            context=request.context,
            options=request.options,
            criteria=request.criteria,
        )
        return AIResponse(success=True, result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify", response_model=AIResponse)
async def ai_classify(request: AIClassifyRequest):
    """Classify text into categories."""
    client = await get_claude_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Claude AI not configured")

    try:
        result = await client.classify(
            text=request.text,
            categories=request.categories,
            multi_label=request.multi_label,
        )
        return AIResponse(success=True, result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract", response_model=AIResponse)
async def ai_extract(request: AIExtractRequest):
    """Extract structured data from text."""
    client = await get_claude_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Claude AI not configured")

    try:
        result = await client.extract_structured(
            text=request.text,
            schema=request.schema_def,
        )
        return AIResponse(success=True, result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize", response_model=AIResponse)
async def ai_summarize(request: AISummarizeRequest):
    """Summarize text."""
    client = await get_claude_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Claude AI not configured")

    try:
        result = await client.summarize(
            text=request.text,
            max_length=request.max_length,
            style=request.style,
        )
        return AIResponse(success=True, result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/{conversation_id}/clear")
async def clear_conversation(conversation_id: str):
    """Clear a conversation thread."""
    client = await get_claude_client()
    client.memory.clear(conversation_id)
    return {"message": f"Conversation '{conversation_id}' cleared"}


@router.get("/usage")
async def get_usage_stats():
    """Get AI token usage statistics."""
    client = await get_claude_client()
    return client.usage.get_stats()


# ─── AI Workflow Generator ──────────────────────────────────────────

class GenerateWorkflowRequest(BaseModel):
    description: str
    language: str = "en"  # "en" or "bg"


@router.post("/generate-workflow")
async def generate_workflow(request: GenerateWorkflowRequest):
    """
    Use Claude AI to generate a complete workflow definition from a natural
    language description. Returns a workflow name, description, and steps array
    ready for creating a workflow.
    """
    client = await get_claude_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Claude AI not configured. Set ANTHROPIC_API_KEY.")

    # Build the available task types list for Claude's context
    registry = get_task_registry()
    task_types = registry.available_types

    # Get template examples for Claude's context
    try:
        from api.routes.template_library import BUILTIN_TEMPLATES
        example_templates = BUILTIN_TEMPLATES[:3]
        example_steps = []
        for tpl in example_templates:
            for step in tpl.get("steps", [])[:2]:
                example_steps.append(step)
    except Exception:
        example_steps = []

    import json

    system_prompt = f"""You are an expert RPA workflow designer. Generate workflow definitions as JSON.

AVAILABLE TASK TYPES (use ONLY these):
- web_scrape: Scrape data from websites using CSS selectors
- http_request: Make HTTP requests (GET, POST, PUT, DELETE)
- custom_script: Execute Python code inline
- data_transform: Transform data with Python script
- email_send: Send emails
- file_write: Write data to files (CSV, JSON, etc.)
- database_query: Execute SQL queries
- condition: If/else branching
- loop: Iterate over collections
- delay: Wait for specified seconds
- ai_ask: Send prompt to Claude AI
- ai_analyze: Analyze data with AI
- ai_summarize: Summarize text with AI
- form_fill: Fill web forms with Playwright
- browser_navigate: Navigate to URLs
- browser_click: Click elements on page
- browser_extract: Extract data from page elements

STEP FORMAT:
Each step must have: id, name, type, config, depends_on (array of step ids)
- id: "step-1", "step-2", etc.
- name: Human-readable name
- type: One of the task types above
- config: Type-specific configuration
- depends_on: Array of step IDs this step depends on (first step has empty array)

For web_scrape config: url, selectors (array of {{name, selector, extract, multiple}})
For http_request config: url, method, headers, body, timeout
For custom_script config: language ("python"), script (Python code as string)
For condition config: condition (expression), on_true (step id), on_false (step id)
For loop config: items (expression), step (inline step definition)
For ai_ask config: prompt (string)

EXAMPLE STEPS:
{json.dumps(example_steps[:3], indent=2, default=str)[:2000]}

RESPONSE FORMAT (JSON only, no markdown):
{{
  "name": "Workflow name",
  "description": "What this workflow does",
  "steps": [
    {{
      "id": "step-1",
      "name": "Step Name",
      "type": "task_type",
      "config": {{}},
      "depends_on": []
    }}
  ]
}}

Generate realistic, production-ready workflows with proper error handling.
Respond ONLY with valid JSON, no explanation or markdown."""

    lang_hint = ""
    if request.language == "bg":
        lang_hint = " The user's description is in Bulgarian but generate the workflow with English step names and configs."

    prompt = f"Generate a complete RPA workflow for the following requirement:{lang_hint}\n\n{request.description}"

    try:
        response = await client.ask(
            prompt=prompt,
            system=system_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        # Parse JSON from response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        workflow_def = json.loads(clean)

        return {
            "success": True,
            "workflow": {
                "name": workflow_def.get("name", "AI Generated Workflow"),
                "description": workflow_def.get("description", request.description),
                "steps": workflow_def.get("steps", []),
            }
        }

    except json.JSONDecodeError as e:
        # Return what Claude gave us even if it's not perfect JSON
        return {
            "success": False,
            "error": f"AI generated invalid JSON: {str(e)}",
            "raw_response": response[:2000] if response else "",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
