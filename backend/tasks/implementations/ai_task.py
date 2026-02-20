"""
AI-Powered Task Implementations using Claude.

Provides multiple AI task types for workflows:
- ai_ask: Free-form question/prompt to Claude
- ai_analyze: Data analysis and document processing
- ai_decide: Decision-making for workflow branching
- ai_classify: Text classification for routing
- ai_extract: Structured data extraction from text
- ai_summarize: Text summarization for reports
- ai_generate_code: Code generation for custom scripts
- ai_conversation: Multi-turn conversation with memory
"""

from typing import Any, Dict, Optional

from tasks.base_task import BaseTask, TaskResult
from integrations.claude_client import get_claude_client


class AIAskTask(BaseTask):
    """Send a prompt to Claude and get a response."""

    task_type = "ai_ask"
    display_name = "AI Ask"
    description = "Send a question or prompt to Claude AI and get a response"
    icon = "🤖"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        prompt = config.get("prompt", "")
        if not prompt:
            return TaskResult(success=False, error="Prompt is required")

        # Replace variables from context
        prompt = self._resolve_variables(prompt, context or {})

        response = await client.ask(
            prompt=prompt,
            system=config.get("system_prompt"),
            model=config.get("model"),
            max_tokens=config.get("max_tokens"),
            temperature=config.get("temperature"),
            conversation_id=config.get("conversation_id"),
        )

        return TaskResult(
            success=True,
            output=response,
            metadata={"model": config.get("model", client.settings.CLAUDE_MODEL)},
        )

    def _resolve_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Replace {{variable}} placeholders with context values."""
        for key, value in context.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt to send to Claude"},
                "system_prompt": {"type": "string", "description": "Optional system prompt override"},
                "model": {"type": "string", "description": "Model override (e.g., claude-opus-4-5-20251101)"},
                "max_tokens": {"type": "integer", "description": "Max response tokens"},
                "temperature": {"type": "number", "description": "Temperature (0-1)"},
                "conversation_id": {"type": "string", "description": "ID for multi-turn conversation"},
            },
            "required": ["prompt"],
        }


class AIAnalyzeTask(BaseTask):
    """Analyze data with Claude — documents, CSV, JSON, etc."""

    task_type = "ai_analyze"
    display_name = "AI Analyze"
    description = "Analyze data, documents, or text with Claude AI"
    icon = "🔍"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        data = config.get("data", "")
        instruction = config.get("instruction", "Analyze this data")
        output_format = config.get("output_format", "text")

        # Data can come from previous step output
        if not data and context:
            data = str(context.get("previous_output", ""))

        if not data:
            return TaskResult(success=False, error="No data to analyze")

        response = await client.analyze(
            data=data,
            instruction=instruction,
            output_format=output_format,
            system=config.get("system_prompt"),
        )

        return TaskResult(success=True, output=response, metadata={"output_format": output_format})

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data to analyze (or uses previous step output)"},
                "instruction": {"type": "string", "description": "Analysis instructions"},
                "output_format": {
                    "type": "string",
                    "enum": ["text", "json", "csv", "markdown"],
                    "description": "Expected output format",
                },
                "system_prompt": {"type": "string"},
            },
            "required": ["instruction"],
        }


class AIDecideTask(BaseTask):
    """AI-powered decision making for workflow branching."""

    task_type = "ai_decide"
    display_name = "AI Decision"
    description = "Let Claude AI make a decision for workflow branching"
    icon = "🧠"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        context_text = config.get("context", "")
        options = config.get("options", [])
        criteria = config.get("criteria")

        if not options:
            return TaskResult(success=False, error="Options are required for decision")

        # Enrich context with previous step data
        if context and context.get("previous_output"):
            context_text += f"\n\nAdditional data from previous step:\n{context['previous_output']}"

        result = await client.decide(
            context=context_text,
            options=options,
            criteria=criteria,
        )

        return TaskResult(
            success=True,
            output=result,
            metadata={
                "chosen_option": result.get("option"),
                "confidence": result.get("confidence", 0),
                "choice_index": result.get("choice", 1) - 1,
            },
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "context": {"type": "string", "description": "Decision context/situation"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of possible options",
                },
                "criteria": {"type": "string", "description": "Decision criteria"},
            },
            "required": ["context", "options"],
        }


class AIClassifyTask(BaseTask):
    """Classify text into categories for routing."""

    task_type = "ai_classify"
    display_name = "AI Classify"
    description = "Classify text into predefined categories for routing"
    icon = "🏷️"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        text = config.get("text", "")
        categories = config.get("categories", [])
        multi_label = config.get("multi_label", False)

        if not text and context:
            text = str(context.get("previous_output", ""))

        if not text or not categories:
            return TaskResult(success=False, error="Text and categories are required")

        result = await client.classify(
            text=text,
            categories=categories,
            multi_label=multi_label,
        )

        return TaskResult(
            success=True,
            output=result,
            metadata={"categories_available": categories},
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to classify"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Possible categories",
                },
                "multi_label": {"type": "boolean", "description": "Allow multiple categories"},
            },
            "required": ["categories"],
        }


class AIExtractTask(BaseTask):
    """Extract structured data from unstructured text."""

    task_type = "ai_extract"
    display_name = "AI Extract"
    description = "Extract structured data from text using a JSON schema"
    icon = "📋"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        text = config.get("text", "")
        schema = config.get("schema", {})

        if not text and context:
            text = str(context.get("previous_output", ""))

        if not text or not schema:
            return TaskResult(success=False, error="Text and schema are required")

        result = await client.extract_structured(text=text, schema=schema)

        return TaskResult(
            success=True,
            output=result,
            metadata={"schema_fields": list(schema.get("properties", {}).keys())},
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to extract from"},
                "schema": {"type": "object", "description": "JSON schema for expected output"},
            },
            "required": ["schema"],
        }


class AISummarizeTask(BaseTask):
    """Summarize text for reports and digests."""

    task_type = "ai_summarize"
    display_name = "AI Summarize"
    description = "Summarize text with configurable length and style"
    icon = "📝"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        text = config.get("text", "")
        if not text and context:
            text = str(context.get("previous_output", ""))

        if not text:
            return TaskResult(success=False, error="Text is required")

        response = await client.summarize(
            text=text,
            max_length=config.get("max_length"),
            style=config.get("style", "concise"),
        )

        return TaskResult(
            success=True,
            output=response,
            metadata={"style": config.get("style", "concise")},
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"},
                "max_length": {"type": "integer", "description": "Max word count"},
                "style": {
                    "type": "string",
                    "enum": ["concise", "detailed", "bullet_points", "executive"],
                    "description": "Summary style",
                },
            },
        }


class AIGenerateCodeTask(BaseTask):
    """Generate code for custom script tasks."""

    task_type = "ai_generate_code"
    display_name = "AI Code Generator"
    description = "Generate code from natural language description"
    icon = "💻"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        description = config.get("description", "")
        language = config.get("language", "python")

        if not description:
            return TaskResult(success=False, error="Code description is required")

        code = await client.generate_code(
            description=description,
            language=language,
            context=config.get("context"),
        )

        return TaskResult(
            success=True,
            output=code,
            metadata={"language": language},
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "What the code should do"},
                "language": {"type": "string", "description": "Programming language"},
                "context": {"type": "string", "description": "Additional context (existing code, APIs)"},
            },
            "required": ["description"],
        }


class AIConversationTask(BaseTask):
    """Multi-turn conversation with persistent memory."""

    task_type = "ai_conversation"
    display_name = "AI Conversation"
    description = "Multi-turn conversation with Claude, maintaining context across steps"
    icon = "💬"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        client = await get_claude_client()
        if not client.is_configured:
            return TaskResult(success=False, error="Claude API key not configured")

        message = config.get("message", "")
        conversation_id = config.get("conversation_id", "default")
        action = config.get("action", "message")  # message, clear, status

        if action == "clear":
            client.memory.clear(conversation_id)
            return TaskResult(success=True, output="Conversation cleared")

        if action == "status":
            messages = client.memory.get_messages(conversation_id)
            return TaskResult(
                success=True,
                output={"message_count": len(messages), "conversation_id": conversation_id},
            )

        if not message:
            return TaskResult(success=False, error="Message is required")

        # Replace variables
        if context:
            for key, value in context.items():
                message = message.replace(f"{{{{{key}}}}}", str(value))

        response = await client.ask(
            prompt=message,
            conversation_id=conversation_id,
            system=config.get("system_prompt"),
        )

        return TaskResult(
            success=True,
            output=response,
            metadata={
                "conversation_id": conversation_id,
                "message_count": len(client.memory.get_messages(conversation_id)),
            },
        )

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to send"},
                "conversation_id": {"type": "string", "description": "Conversation thread ID"},
                "action": {
                    "type": "string",
                    "enum": ["message", "clear", "status"],
                    "description": "Action type",
                },
                "system_prompt": {"type": "string", "description": "System prompt for this conversation"},
            },
            "required": ["message"],
        }


# ─── Registry of all AI task types ───────────────────────────────────

AI_TASK_TYPES = {
    "ai_ask": AIAskTask,
    "ai_analyze": AIAnalyzeTask,
    "ai_decide": AIDecideTask,
    "ai_classify": AIClassifyTask,
    "ai_extract": AIExtractTask,
    "ai_summarize": AISummarizeTask,
    "ai_generate_code": AIGenerateCodeTask,
    "ai_conversation": AIConversationTask,
}
