"""
Claude AI Client - Persistent connection manager for Anthropic Claude API.

Provides a resilient, auto-reconnecting client with:
- Connection pooling and keep-alive
- Automatic retry with exponential backoff
- Streaming support for long-running tasks
- Token usage tracking
- Conversation memory for multi-turn interactions
- Health monitoring and automatic recovery
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class ClaudeMessage:
    """Represents a message in a Claude conversation."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class ConversationMemory:
    """Manages conversation history for multi-turn Claude interactions."""

    def __init__(self, max_messages: int = 50, max_tokens_estimate: int = 100000):
        self.conversations: Dict[str, List[ClaudeMessage]] = {}
        self.max_messages = max_messages
        self.max_tokens_estimate = max_tokens_estimate

    def get_or_create(self, conversation_id: str) -> List[ClaudeMessage]:
        """Get or create a conversation thread."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        return self.conversations[conversation_id]

    def add_message(self, conversation_id: str, role: str, content: str):
        """Add a message to conversation history."""
        messages = self.get_or_create(conversation_id)
        messages.append(ClaudeMessage(role=role, content=content))

        # Trim old messages if exceeding limit
        if len(messages) > self.max_messages:
            # Keep system context + recent messages
            self.conversations[conversation_id] = messages[-self.max_messages:]

    def get_messages(self, conversation_id: str) -> List[Dict[str, str]]:
        """Get all messages for a conversation as dicts."""
        messages = self.get_or_create(conversation_id)
        return [m.to_dict() for m in messages]

    def clear(self, conversation_id: str):
        """Clear a conversation thread."""
        self.conversations.pop(conversation_id, None)

    def clear_all(self):
        """Clear all conversations."""
        self.conversations.clear()


class TokenUsageTracker:
    """Tracks Claude API token usage for analytics and cost management."""

    def __init__(self):
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_requests: int = 0
        self.failed_requests: int = 0
        self.history: List[Dict[str, Any]] = []

    def record(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        duration_ms: float,
        success: bool = True,
    ):
        """Record a single API call's usage."""
        self.total_requests += 1
        if success:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
        else:
            self.failed_requests += 1

        self.history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model,
            "duration_ms": duration_ms,
            "success": success,
        })

        # Keep only last 1000 records in memory
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                (self.total_requests - self.failed_requests) / max(self.total_requests, 1)
            ) * 100,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": self._estimate_cost(),
        }

    def _estimate_cost(self) -> float:
        """Rough cost estimate based on Claude Sonnet pricing."""
        input_cost = (self.total_input_tokens / 1_000_000) * 3.0
        output_cost = (self.total_output_tokens / 1_000_000) * 15.0
        return round(input_cost + output_cost, 4)


class ClaudeClient:
    """
    Persistent Claude AI client with auto-reconnect and resilience.

    Features:
    - HTTP/2 connection pooling via httpx
    - Automatic retry with exponential backoff
    - Streaming responses for long tasks
    - Multi-turn conversation support
    - Token usage tracking
    - Health monitoring
    - Graceful degradation on API issues
    """

    API_BASE = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._is_connected: bool = False
        self._last_health_check: Optional[datetime] = None
        self._health_check_interval: int = 60  # seconds

        self.memory = ConversationMemory()
        self.usage = TokenUsageTracker()

        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 10

    @property
    def api_key(self) -> str:
        """Get API key, checking both ANTHROPIC_API_KEY and CHAT_API_KEY."""
        return self.settings.ANTHROPIC_API_KEY or self.settings.CHAT_API_KEY or ""

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    @property
    def is_connected(self) -> bool:
        """Check if client is connected and healthy."""
        return self._is_connected and self._client is not None

    async def connect(self) -> bool:
        """
        Establish connection to Claude API.

        Creates an HTTP/2 client with connection pooling and keep-alive.
        Returns True if connection is successful.
        """
        if not self.is_configured:
            logger.warning("Claude API key not configured. AI features disabled.")
            return False

        try:
            self._client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": self.API_VERSION,
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=float(self.settings.CLAUDE_TIMEOUT),
                    write=30.0,
                    pool=10.0,
                ),
                http2=True,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=300,
                ),
            )

            # Verify connection with a minimal request
            self._is_connected = await self._health_check()
            if self._is_connected:
                self._reconnect_attempts = 0
                logger.info("Claude AI client connected successfully",
                           model=self.settings.CLAUDE_MODEL)
            return self._is_connected

        except Exception as e:
            logger.error("Failed to connect to Claude API", error=str(e))
            self._is_connected = False
            return False

    async def disconnect(self):
        """Gracefully close the client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._is_connected = False
        self.memory.clear_all()
        logger.info("Claude AI client disconnected")

    async def _health_check(self) -> bool:
        """Verify API connectivity with a minimal request."""
        try:
            response = await self._client.post(
                "/messages",
                json={
                    "model": self.settings.CLAUDE_MODEL,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "ping"}],
                },
            )
            self._last_health_check = datetime.now(timezone.utc)
            return response.status_code == 200
        except Exception as e:
            logger.warning("Claude health check failed", error=str(e))
            return False

    async def _ensure_connected(self):
        """Ensure client is connected, reconnect if necessary."""
        if self.is_connected:
            return

        if self._reconnect_attempts >= self._max_reconnect_attempts:
            raise ConnectionError(
                f"Max reconnect attempts ({self._max_reconnect_attempts}) exceeded. "
                "Claude AI is unavailable."
            )

        self._reconnect_attempts += 1
        delay = min(2 ** self._reconnect_attempts * self.settings.CLAUDE_RETRY_DELAY, 60)

        logger.info(
            "Reconnecting to Claude API",
            attempt=self._reconnect_attempts,
            delay=delay,
        )
        await asyncio.sleep(delay)

        if not await self.connect():
            raise ConnectionError("Failed to reconnect to Claude API")

    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make a request to Claude API with retry logic.

        Returns the full API response as a dict.
        """
        await self._ensure_connected()

        settings = self.settings
        payload = {
            "model": model or settings.CLAUDE_MODEL,
            "max_tokens": max_tokens or settings.CLAUDE_MAX_TOKENS,
            "temperature": temperature if temperature is not None else settings.CLAUDE_TEMPERATURE,
            "messages": messages,
        }

        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

        last_error = None
        for attempt in range(settings.CLAUDE_MAX_RETRIES):
            start_time = time.monotonic()
            try:
                response = await self._client.post("/messages", json=payload)
                duration_ms = (time.monotonic() - start_time) * 1000

                if response.status_code == 200:
                    data = response.json()
                    self.usage.record(
                        input_tokens=data.get("usage", {}).get("input_tokens", 0),
                        output_tokens=data.get("usage", {}).get("output_tokens", 0),
                        model=payload["model"],
                        duration_ms=duration_ms,
                        success=True,
                    )
                    return data

                elif response.status_code == 429:
                    # Rate limited — wait and retry
                    retry_after = float(response.headers.get("retry-after", 5))
                    logger.warning("Claude rate limited", retry_after=retry_after)
                    await asyncio.sleep(retry_after)

                elif response.status_code == 529:
                    # Overloaded — backoff
                    delay = min(2 ** (attempt + 1), 30)
                    logger.warning("Claude API overloaded", delay=delay)
                    await asyncio.sleep(delay)

                else:
                    error_body = response.text
                    logger.error(
                        "Claude API error",
                        status=response.status_code,
                        body=error_body[:500],
                    )
                    self.usage.record(0, 0, payload["model"], duration_ms, success=False)
                    last_error = f"API error {response.status_code}: {error_body[:200]}"

            except httpx.TimeoutException:
                duration_ms = (time.monotonic() - start_time) * 1000
                logger.warning("Claude request timeout", attempt=attempt)
                self.usage.record(0, 0, payload["model"], duration_ms, success=False)
                last_error = "Request timed out"

            except httpx.ConnectError:
                self._is_connected = False
                logger.warning("Claude connection lost, reconnecting...")
                await self._ensure_connected()
                last_error = "Connection lost"

            except Exception as e:
                duration_ms = (time.monotonic() - start_time) * 1000
                self.usage.record(0, 0, payload["model"], duration_ms, success=False)
                last_error = str(e)
                logger.error("Claude request failed", error=str(e), attempt=attempt)

            # Exponential backoff between retries
            if attempt < settings.CLAUDE_MAX_RETRIES - 1:
                delay = min(2 ** attempt * settings.CLAUDE_RETRY_DELAY, 30)
                await asyncio.sleep(delay)

        raise RuntimeError(f"Claude API request failed after {settings.CLAUDE_MAX_RETRIES} retries: {last_error}")

    # ─── High-Level API Methods ───────────────────────────────────────

    async def ask(
        self,
        prompt: str,
        system: Optional[str] = None,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a message to Claude and get a text response.

        Args:
            prompt: The user message
            system: Optional system prompt override
            conversation_id: Optional ID for multi-turn conversation
            model: Optional model override
            max_tokens: Optional max tokens override
            temperature: Optional temperature override

        Returns:
            Claude's text response
        """
        if conversation_id:
            self.memory.add_message(conversation_id, "user", prompt)
            messages = self.memory.get_messages(conversation_id)
        else:
            messages = [{"role": "user", "content": prompt}]

        response = await self._make_request(
            messages=messages,
            system=system or self.settings.CLAUDE_SYSTEM_PROMPT,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Extract text from response
        content_blocks = response.get("content", [])
        text = ""
        for block in content_blocks:
            if block.get("type") == "text":
                text += block.get("text", "")

        if conversation_id:
            self.memory.add_message(conversation_id, "assistant", text)

        return text

    async def analyze(
        self,
        data: str,
        instruction: str,
        output_format: str = "text",
        system: Optional[str] = None,
    ) -> str:
        """
        Analyze data with Claude — ideal for document processing, data extraction, etc.

        Args:
            data: The data to analyze (text, CSV, JSON, etc.)
            instruction: What to do with the data
            output_format: Expected output format (text, json, csv, markdown)

        Returns:
            Analysis result as text
        """
        format_instructions = {
            "json": "Respond with valid JSON only. No markdown, no explanation.",
            "csv": "Respond with CSV data only. Include header row.",
            "markdown": "Respond in well-formatted Markdown.",
            "text": "Respond in plain text.",
        }

        prompt = f"""## Instruction
{instruction}

## Output Format
{format_instructions.get(output_format, format_instructions['text'])}

## Data
{data}"""

        return await self.ask(
            prompt=prompt,
            system=system or "You are a data analysis expert. Be precise and thorough.",
            temperature=0.1,
        )

    async def decide(
        self,
        context: str,
        options: List[str],
        criteria: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Make a decision based on context — for workflow branching logic.

        Args:
            context: The situation description
            options: List of possible actions/choices
            criteria: Optional criteria for decision making

        Returns:
            Dict with 'choice' (index), 'option' (text), 'reasoning' (explanation)
        """
        options_text = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))

        prompt = f"""## Decision Required

### Context
{context}

### Available Options
{options_text}

{f'### Decision Criteria{chr(10)}{criteria}' if criteria else ''}

### Instructions
Analyze the context and choose the best option. Respond in this exact JSON format:
{{
    "choice": <option number (1-based)>,
    "option": "<chosen option text>",
    "confidence": <0.0 to 1.0>,
    "reasoning": "<brief explanation>"
}}

Respond with JSON only."""

        response = await self.ask(
            prompt=prompt,
            system="You are a decision-making AI. Analyze carefully and choose the best option.",
            temperature=0.1,
        )

        # Parse JSON response
        import json
        try:
            # Handle potential markdown code blocks
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(clean)
            return result
        except json.JSONDecodeError:
            return {
                "choice": 1,
                "option": options[0] if options else "unknown",
                "confidence": 0.0,
                "reasoning": f"Failed to parse AI response: {response[:200]}",
            }

    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[str] = None,
    ) -> str:
        """
        Generate code for custom script tasks.

        Args:
            description: What the code should do
            language: Programming language
            context: Optional additional context (existing code, API docs, etc.)

        Returns:
            Generated code as string
        """
        prompt = f"""Generate {language} code for the following task:

{description}

{f'Context:{chr(10)}{context}' if context else ''}

Requirements:
- Clean, production-ready code
- Include error handling
- Add brief comments
- Return ONLY the code, no explanations

```{language}"""

        response = await self.ask(
            prompt=prompt,
            system=f"You are an expert {language} developer. Write clean, efficient code.",
            temperature=0.2,
        )

        # Extract code block if wrapped
        if "```" in response:
            parts = response.split("```")
            for part in parts:
                if part.strip() and not part.strip().startswith(language):
                    continue
                code = part.strip()
                if code.startswith(language):
                    code = code[len(language):].strip()
                if code:
                    return code
        return response.strip()

    async def summarize(
        self,
        text: str,
        max_length: Optional[int] = None,
        style: str = "concise",
    ) -> str:
        """
        Summarize text — for report generation and document processing.

        Args:
            text: Text to summarize
            max_length: Optional max word count
            style: Summary style (concise, detailed, bullet_points, executive)

        Returns:
            Summary text
        """
        length_instruction = f"Keep the summary under {max_length} words." if max_length else ""

        style_map = {
            "concise": "Write a concise, to-the-point summary.",
            "detailed": "Write a comprehensive, detailed summary preserving key information.",
            "bullet_points": "Summarize as organized bullet points with key takeaways.",
            "executive": "Write an executive summary suitable for leadership briefing.",
        }

        prompt = f"""{style_map.get(style, style_map['concise'])}
{length_instruction}

Text to summarize:
{text}"""

        return await self.ask(
            prompt=prompt,
            system="You are an expert at distilling information into clear summaries.",
            temperature=0.2,
        )

    async def classify(
        self,
        text: str,
        categories: List[str],
        multi_label: bool = False,
    ) -> Dict[str, Any]:
        """
        Classify text into categories — for routing and automation decisions.

        Args:
            text: Text to classify
            categories: List of possible categories
            multi_label: Whether multiple categories can be assigned

        Returns:
            Dict with category/categories and confidence scores
        """
        categories_text = ", ".join(f'"{c}"' for c in categories)

        prompt = f"""Classify the following text into {'one or more of' if multi_label else 'exactly one of'} these categories: [{categories_text}]

Text: {text}

Respond in JSON format:
{{
    "{'categories' if multi_label else 'category'}": {'["cat1", "cat2"]' if multi_label else '"category"'},
    "confidence": 0.95,
    "reasoning": "brief explanation"
}}

JSON only:"""

        response = await self.ask(prompt=prompt, temperature=0.1)

        import json
        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            return {
                "category" if not multi_label else "categories": categories[0] if categories else "unknown",
                "confidence": 0.0,
                "reasoning": f"Parse error: {response[:200]}",
            }

    async def extract_structured(
        self,
        text: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract structured data from unstructured text using a JSON schema.

        Args:
            text: Unstructured text to extract from
            schema: JSON schema describing expected output structure

        Returns:
            Extracted data matching the schema
        """
        import json

        prompt = f"""Extract structured data from the following text according to this JSON schema:

Schema:
```json
{json.dumps(schema, indent=2)}
```

Text:
{text}

Respond with a JSON object matching the schema. Use null for missing values. JSON only:"""

        response = await self.ask(
            prompt=prompt,
            system="You are a data extraction expert. Extract information precisely.",
            temperature=0.1,
        )

        try:
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            return {"error": f"Failed to parse: {response[:200]}", "raw": response}

    # ─── Status & Management ──────────────────────────────────────────

    async def get_status(self) -> Dict[str, Any]:
        """Get current client status and usage statistics."""
        return {
            "configured": self.is_configured,
            "connected": self.is_connected,
            "model": self.settings.CLAUDE_MODEL,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "reconnect_attempts": self._reconnect_attempts,
            "active_conversations": len(self.memory.conversations),
            "usage": self.usage.get_stats(),
        }


# ─── Singleton Instance ──────────────────────────────────────────────

_claude_client: Optional[ClaudeClient] = None


async def get_claude_client() -> ClaudeClient:
    """Get or create the singleton Claude client."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
        await _claude_client.connect()
    return _claude_client
