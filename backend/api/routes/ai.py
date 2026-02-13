"""
AI Integration API Routes.

Endpoints for interacting with Claude AI directly and managing AI configuration.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
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

    try:
        response = await client.ask(
            prompt=request.prompt,
            system=request.system_prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            conversation_id=request.conversation_id,
        )
        return AIResponse(
            success=True,
            result=response,
            metadata={"conversation_id": request.conversation_id},
        )
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
