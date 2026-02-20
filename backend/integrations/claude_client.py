"""
Claude AI Client — Production-grade integration for Anthropic Claude API.

Features (v2):
- HTTP/2 connection pooling with auto-reconnect
- **Tool Use (Function Calling)** — Claude can invoke registered tools
- **Redis-backed ConversationMemory** with 24h TTL (persistent across restarts)
- **Streaming** for long-running analysis tasks
- **Smart JSON parsing** — extracts clean JSON from mixed text/markdown responses
- Token usage tracking with cost estimation
- Health monitoring and graceful degradation
"""

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


# ─── Smart JSON Extractor ──────────────────────────────────────
#
# Claude sometimes wraps JSON in explanation text or markdown fences.
# This module extracts clean JSON regardless of wrapper format.

def extract_json(text: str) -> Any:
    """Extract clean JSON from a Claude response that may contain markdown or prose.

    Tries multiple strategies in order:
    1. Direct JSON parse (fastest path)
    2. Strip markdown code fences (```json ... ```)
    3. Find first { ... } or [ ... ] block via bracket balancing
    4. Regex fallback for simple objects

    Returns parsed JSON object or raises ValueError.
    """
    if not text or not text.strip():
        raise ValueError("Empty response")

    clean = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown code fences
    fence_pattern = re.compile(r'```(?:json|JSON)?\s*\n?(.*?)```', re.DOTALL)
    match = fence_pattern.search(clean)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Bracket-balanced extraction
    for opener, closer in [('{', '}'), ('[', ']')]:
        start = clean.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape_next = False
        for i in range(start, len(clean)):
            c = clean[i]
            if escape_next:
                escape_next = False
                continue
            if c == '\\':
                escape_next = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    candidate = clean[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # Strategy 4: Regex for simple key-value object
    simple_obj = re.search(r'\{[^{}]+\}', clean)
    if simple_obj:
        try:
            return json.loads(simple_obj.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response: {clean[:200]}")


def safe_extract_json(text: str, fallback: Any = None) -> Any:
    """Extract JSON with a safe fallback (no exceptions)."""
    try:
        return extract_json(text)
    except (ValueError, json.JSONDecodeError):
        return fallback if fallback is not None else {"raw": text, "error": "JSON parse failed"}


# ─── Redis-backed Conversation Memory ─────────────────────────

class ConversationMemory:
    """Manages conversation history with Redis persistence and 24h TTL.

    Falls back to in-memory storage if Redis is unavailable.
    Each conversation is stored as a Redis list with key: rpa:conv:{conversation_id}
    """

    REDIS_PREFIX = "rpa:conv:"
    DEFAULT_TTL = 86400  # 24 hours

    def __init__(self, max_messages: int = 50, ttl: int = DEFAULT_TTL):
        self._max_messages = max_messages
        self._ttl = ttl
        self._redis = None
        self._fallback: Dict[str, List[Dict[str, str]]] = {}  # In-memory fallback

    async def _get_redis(self):
        """Lazy-init Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                settings = get_settings()
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=3,
                )
                await self._redis.ping()
            except Exception as e:
                logger.debug(f"Redis unavailable for conversation memory, using in-memory: {e}")
                self._redis = None
        return self._redis

    def _key(self, conversation_id: str) -> str:
        return f"{self.REDIS_PREFIX}{conversation_id}"

    async def add_message(self, conversation_id: str, role: str, content: str):
        """Add a message to the conversation."""
        msg = json.dumps({"role": role, "content": content})
        r = await self._get_redis()
        if r:
            try:
                key = self._key(conversation_id)
                await r.rpush(key, msg)
                await r.ltrim(key, -self._max_messages, -1)
                await r.expire(key, self._ttl)
                return
            except Exception as e:
                logger.warning(f"Redis conversation write failed: {e}")

        # Fallback
        if conversation_id not in self._fallback:
            self._fallback[conversation_id] = []
        self._fallback[conversation_id].append({"role": role, "content": content})
        if len(self._fallback[conversation_id]) > self._max_messages:
            self._fallback[conversation_id] = self._fallback[conversation_id][-self._max_messages:]

    async def get_messages(self, conversation_id: str) -> List[Dict[str, str]]:
        """Get all messages for a conversation."""
        r = await self._get_redis()
        if r:
            try:
                key = self._key(conversation_id)
                raw = await r.lrange(key, 0, -1)
                return [json.loads(m) for m in raw]
            except Exception as e:
                logger.warning(f"Redis conversation read failed: {e}")

        return list(self._fallback.get(conversation_id, []))

    async def clear(self, conversation_id: str):
        """Clear a conversation thread."""
        r = await self._get_redis()
        if r:
            try:
                await r.delete(self._key(conversation_id))
            except Exception:
                pass
        self._fallback.pop(conversation_id, None)

    async def clear_all(self):
        """Clear all conversations."""
        r = await self._get_redis()
        if r:
            try:
                keys = []
                async for key in r.scan_iter(f"{self.REDIS_PREFIX}*"):
                    keys.append(key)
                if keys:
                    await r.delete(*keys)
            except Exception:
                pass
        self._fallback.clear()

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None


# ─── Tool Registry ─────────────────────────────────────────────

class ToolRegistry:
    """Registry of tools that Claude can invoke via function calling.

    Each tool has:
    - name: unique identifier
    - description: what the tool does (for Claude's context)
    - input_schema: JSON Schema describing parameters
    - handler: async callable that executes the tool
    """

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
    ):
        """Register a tool for Claude to use."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
        }
        self._handlers[name] = handler
        logger.info(f"Tool registered: {name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions in Claude API format."""
        return list(self._tools.values())

    async def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a registered tool."""
        handler = self._handlers.get(tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {tool_name}")

        try:
            result = await handler(tool_input)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}", error=str(e))
            return {"error": str(e)}

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


# ─── Token Usage Tracker ───────────────────────────────────────

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


# ─── Main Claude Client ───────────────────────────────────────

class ClaudeClient:
    """
    Production-grade Claude AI client with tool use, streaming, and Redis memory.

    Features:
    - HTTP/2 connection pooling via httpx
    - Automatic retry with exponential backoff
    - Tool Use / Function Calling — Claude can invoke registered tools
    - Streaming responses for long-running analysis
    - Redis-backed conversation memory (24h TTL)
    - Smart JSON extraction from mixed responses
    - Token usage tracking and cost estimation
    """

    API_BASE = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._is_connected: bool = False
        self._last_health_check: Optional[datetime] = None
        self._health_check_interval: int = 60

        self.memory = ConversationMemory()
        self.tools = ToolRegistry()
        self.usage = TokenUsageTracker()

        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 10
        self._cached_api_key: str = ""

    @property
    def api_key(self) -> str:
        """Get API key from env vars or cached Redis value."""
        return self.settings.ANTHROPIC_API_KEY or self.settings.CHAT_API_KEY or self._cached_api_key or ""

    async def _resolve_api_key(self) -> str:
        """Resolve API key from env vars or Redis system config."""
        key = self.settings.ANTHROPIC_API_KEY or self.settings.CHAT_API_KEY
        if key:
            return key
        try:
            from core.system_config import get_config
            key = await get_config("ANTHROPIC_API_KEY") or ""
            if key:
                self._cached_api_key = key
                return key
        except Exception as e:
            logger.debug(f"Could not read API key from system config: {e}")
        return ""

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._client is not None

    async def connect(self) -> bool:
        """Establish connection to Claude API with HTTP/2 pooling."""
        resolved_key = await self._resolve_api_key()
        if not resolved_key:
            logger.warning("Claude API key not configured. AI features disabled.")
            return False

        try:
            self._client = httpx.AsyncClient(
                base_url=self.API_BASE,
                headers={
                    "x-api-key": resolved_key,
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

            self._is_connected = await self._health_check()
            if self._is_connected:
                self._reconnect_attempts = 0
                logger.info("Claude AI client connected",
                           model=self.settings.CLAUDE_MODEL,
                           tools=self.tools.tool_names)
            return self._is_connected

        except Exception as e:
            logger.error("Failed to connect to Claude API", error=str(e))
            self._is_connected = False
            return False

    async def disconnect(self):
        """Gracefully close connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._is_connected = False
        await self.memory.close()
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
                f"Max reconnect attempts ({self._max_reconnect_attempts}) exceeded."
            )
        self._reconnect_attempts += 1
        delay = min(2 ** self._reconnect_attempts * self.settings.CLAUDE_RETRY_DELAY, 60)
        logger.info("Reconnecting to Claude API", attempt=self._reconnect_attempts, delay=delay)
        await asyncio.sleep(delay)
        if not await self.connect():
            raise ConnectionError("Failed to reconnect to Claude API")

    # ─── Core API Request ──────────────────────────────────────────

    async def _make_request(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make a request to Claude API with retry logic."""
        await self._ensure_connected()

        settings = self.settings
        payload: Dict[str, Any] = {
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
                    )
                    return data

                elif response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", 5))
                    logger.warning("Claude rate limited", retry_after=retry_after)
                    await asyncio.sleep(retry_after)

                elif response.status_code == 529:
                    delay = min(2 ** (attempt + 1), 30)
                    logger.warning("Claude API overloaded", delay=delay)
                    await asyncio.sleep(delay)

                else:
                    error_body = response.text
                    logger.error("Claude API error", status=response.status_code, body=error_body[:500])
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

            if attempt < settings.CLAUDE_MAX_RETRIES - 1:
                delay = min(2 ** attempt * settings.CLAUDE_RETRY_DELAY, 30)
                await asyncio.sleep(delay)

        raise RuntimeError(f"Claude API failed after {settings.CLAUDE_MAX_RETRIES} retries: {last_error}")

    # ─── Streaming ─────────────────────────────────────────────────

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response from Claude — ideal for long analyses.

        Yields text chunks as they arrive via Server-Sent Events.
        """
        await self._ensure_connected()

        settings = self.settings
        payload = {
            "model": model or settings.CLAUDE_MODEL,
            "max_tokens": max_tokens or settings.CLAUDE_MAX_TOKENS,
            "temperature": settings.CLAUDE_TEMPERATURE,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        if system:
            payload["system"] = system

        try:
            async with self._client.stream("POST", "/messages", json=payload) as response:
                if response.status_code != 200:
                    error = await response.aread()
                    raise RuntimeError(f"Stream error {response.status_code}: {error[:200]}")

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        event = json.loads(data_str)
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.error("Streaming failed", error=str(e))
            yield f"\n[Streaming error: {str(e)}]"

    # ─── Tool Use (Function Calling) ───────────────────────────────

    async def ask_with_tools(
        self,
        prompt: str,
        system: Optional[str] = None,
        conversation_id: Optional[str] = None,
        max_tool_rounds: int = 5,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a message to Claude with tool use capabilities.

        Claude can invoke registered tools and use their results.
        Automatically handles multi-round tool use loops.

        Args:
            prompt: User message
            system: Optional system prompt
            conversation_id: For multi-turn conversations
            max_tool_rounds: Max tool invocations before stopping
            model: Optional model override
            max_tokens: Optional max tokens

        Returns:
            Final text response after all tool invocations
        """
        tool_defs = self.tools.get_tool_definitions()
        if not tool_defs:
            # No tools registered — fall back to regular ask
            return await self.ask(prompt, system=system, conversation_id=conversation_id,
                                 model=model, max_tokens=max_tokens)

        # Build messages
        if conversation_id:
            await self.memory.add_message(conversation_id, "user", prompt)
            messages = await self.memory.get_messages(conversation_id)
        else:
            messages = [{"role": "user", "content": prompt}]

        for _round in range(max_tool_rounds):
            response = await self._make_request(
                messages=messages,
                system=system or self.settings.CLAUDE_SYSTEM_PROMPT,
                tools=tool_defs,
                model=model,
                max_tokens=max_tokens,
            )

            content_blocks = response.get("content", [])
            stop_reason = response.get("stop_reason", "")

            # Check if Claude wants to use a tool
            if stop_reason == "tool_use":
                # Add assistant's response (with tool_use blocks) to messages
                messages.append({"role": "assistant", "content": content_blocks})

                # Process all tool_use blocks
                tool_results = []
                for block in content_blocks:
                    if block.get("type") == "tool_use":
                        tool_name = block["name"]
                        tool_input = block["input"]
                        tool_use_id = block["id"]

                        logger.info(f"Tool invoked: {tool_name}", input_keys=list(tool_input.keys()))

                        result = await self.tools.execute(tool_name, tool_input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result) if not isinstance(result, str) else result,
                        })

                # Add tool results to messages
                messages.append({"role": "user", "content": tool_results})
                continue  # Let Claude process tool results

            else:
                # Claude finished — extract text response
                text = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        text += block.get("text", "")

                if conversation_id:
                    await self.memory.add_message(conversation_id, "assistant", text)

                return text

        # Max rounds reached — return whatever we have
        return "[Tool use limit reached]"

    # ─── High-Level API Methods ────────────────────────────────────

    async def ask(
        self,
        prompt: str,
        system: Optional[str] = None,
        conversation_id: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a message and get a text response."""
        if conversation_id:
            await self.memory.add_message(conversation_id, "user", prompt)
            messages = await self.memory.get_messages(conversation_id)
        else:
            messages = [{"role": "user", "content": prompt}]

        response = await self._make_request(
            messages=messages,
            system=system or self.settings.CLAUDE_SYSTEM_PROMPT,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content_blocks = response.get("content", [])
        text = ""
        for block in content_blocks:
            if block.get("type") == "text":
                text += block.get("text", "")

        if conversation_id:
            await self.memory.add_message(conversation_id, "assistant", text)

        return text


    async def ask_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        tool_name: str = "structured_output",
        tool_description: str = "Return the result as structured JSON",
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send a message and get a guaranteed JSON response via tool use.

        Uses Anthropic tool_choice to force Claude to respond with
        structured output matching the provided JSON schema.
        """
        tools = [{
            "name": tool_name,
            "description": tool_description,
            "input_schema": schema,
        }]
        tool_choice = {"type": "tool", "name": tool_name}

        messages = [{"role": "user", "content": prompt}]

        response = await self._make_request(
            messages=messages,
            system=system,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
        )

        # Extract tool_use block from response
        content_blocks = response.get("content", [])
        for block in content_blocks:
            if block.get("type") == "tool_use" and block.get("name") == tool_name:
                return block.get("input", {})

        # Fallback: try to extract JSON from text blocks
        for block in content_blocks:
            if block.get("type") == "text":
                try:
                    return extract_json(block["text"])
                except (ValueError, json.JSONDecodeError):
                    pass

        raise ValueError(
            f"Claude did not return structured output. "
            f"Response blocks: {[b.get('type') for b in content_blocks]}"
        )

    async def analyze(
        self,
        data: str,
        instruction: str,
        output_format: str = "text",
        system: Optional[str] = None,
    ) -> str:
        """Analyze data with Claude (documents, CSV, JSON, etc.)."""
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

    async def analyze_streaming(
        self,
        data: str,
        instruction: str,
    ) -> AsyncGenerator[str, None]:
        """Stream an analysis — ideal for large order datasets like Galaxus."""
        prompt = f"""## Instruction
{instruction}

## Data
{data}"""

        async for chunk in self.stream(
            prompt=prompt,
            system="You are a data analysis expert. Be precise, thorough, and structured.",
        ):
            yield chunk

    async def decide(
        self,
        context: str,
        options: List[str],
        criteria: Optional[str] = None,
    ) -> Dict[str, Any]:
        """AI decision making for workflow branching — returns structured JSON."""
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

        return safe_extract_json(response, {
            "choice": 1,
            "option": options[0] if options else "unknown",
            "confidence": 0.0,
            "reasoning": f"Failed to parse AI response: {response[:200]}",
        })

    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[str] = None,
    ) -> str:
        """Generate code for custom script tasks."""
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
        """Summarize text for report generation."""
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
        """Classify text into categories with confidence scores."""
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
        return safe_extract_json(response, {
            "category" if not multi_label else "categories": categories[0] if categories else "unknown",
            "confidence": 0.0,
            "reasoning": f"Parse error: {response[:200]}",
        })

    async def extract_structured(
        self,
        text: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract structured data from text using a JSON schema."""
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

        return safe_extract_json(response, {"error": "Failed to parse", "raw": response})

    # ─── Status ────────────────────────────────────────────────────

    async def get_status(self) -> Dict[str, Any]:
        """Get current client status and usage statistics."""
        return {
            "configured": self.is_configured,
            "connected": self.is_connected,
            "model": self.settings.CLAUDE_MODEL,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "reconnect_attempts": self._reconnect_attempts,
            "registered_tools": self.tools.tool_names,
            "usage": self.usage.get_stats(),
        }


# ─── Singleton ─────────────────────────────────────────────────

_claude_client: Optional[ClaudeClient] = None


async def get_claude_client() -> ClaudeClient:
    """Get or create the singleton Claude client."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
        await _claude_client.connect()
    elif not _claude_client.is_connected:
        await _claude_client.connect()
    return _claude_client
