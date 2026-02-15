"""Custom script execution with optional browser context.

Executes inline Python code from workflow templates.
Scripts that reference `browser.*` get a Playwright-backed browser.
Scripts without browser calls run directly with exec().

Template scripts use SYNCHRONOUS browser calls like:
    browser.navigate(url)
    browser.wait_for(selector)
    elements = browser.query_selector_all(selector)
    text = el.text_content()
    attr = el.get_attribute("href")

This module wraps Playwright's async API in synchronous wrappers
so template scripts work without async/await.
"""

import asyncio
import json
import os
import re
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from tasks.base_task import BaseTask, TaskResult

logger = structlog.get_logger(__name__)

# Lazy Playwright check
_pw_available: Optional[bool] = None


def _check_playwright() -> bool:
    global _pw_available
    if _pw_available is None:
        try:
            import playwright  # noqa: F401
            _pw_available = True
        except ImportError:
            _pw_available = False
    return _pw_available


def _script_uses_browser(script: str) -> bool:
    """Detect if script code references browser API."""
    return bool(re.search(r'\bbrowser\.\w+', script))


# ─── Sync Browser API Wrapper ────────────────────────────────────

class ElementWrapper:
    """Wraps a Playwright ElementHandle for synchronous access."""

    def __init__(self, element, loop):
        self._el = element
        self._loop = loop

    def get_attribute(self, attr: str) -> Optional[str]:
        future = asyncio.run_coroutine_threadsafe(
            self._el.get_attribute(attr), self._loop
        )
        return future.result(timeout=10)

    def text_content(self) -> Optional[str]:
        future = asyncio.run_coroutine_threadsafe(
            self._el.text_content(), self._loop
        )
        return future.result(timeout=10)

    def inner_text(self) -> Optional[str]:
        future = asyncio.run_coroutine_threadsafe(
            self._el.inner_text(), self._loop
        )
        return future.result(timeout=10)

    def query_selector(self, selector: str) -> Optional["ElementWrapper"]:
        future = asyncio.run_coroutine_threadsafe(
            self._el.query_selector(selector), self._loop
        )
        el = future.result(timeout=10)
        return ElementWrapper(el, self._loop) if el else None

    def query_selector_all(self, selector: str) -> List["ElementWrapper"]:
        future = asyncio.run_coroutine_threadsafe(
            self._el.query_selector_all(selector), self._loop
        )
        elements = future.result(timeout=10)
        return [ElementWrapper(e, self._loop) for e in elements]


class SyncBrowserAPI:
    """Synchronous browser API for template scripts.

    Wraps Playwright's async page methods so scripts can call:
        browser.navigate(url)
        browser.wait_for(selector, timeout=5)
        el = browser.find_element(selector)
        elements = browser.query_selector_all(selector)
    """

    def __init__(self, page, loop):
        self._page = page
        self._loop = loop

    def _run(self, coro, timeout=30):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def navigate(self, url: str, timeout: int = 30000):
        self._run(
            self._page.goto(url, wait_until="domcontentloaded", timeout=timeout),
            timeout=timeout / 1000 + 5,
        )

    def wait_for(self, selector: str, timeout: int = 15000):
        self._run(
            self._page.wait_for_selector(selector, timeout=timeout),
            timeout=timeout / 1000 + 5,
        )

    def wait(self, seconds: float):
        time.sleep(seconds)

    def find_element(self, selector: str) -> Optional[ElementWrapper]:
        el = self._run(self._page.query_selector(selector))
        return ElementWrapper(el, self._loop) if el else None

    def find_elements(self, selector: str) -> List[ElementWrapper]:
        elements = self._run(self._page.query_selector_all(selector))
        return [ElementWrapper(e, self._loop) for e in elements]

    def query_selector_all(self, selector: str) -> List[ElementWrapper]:
        return self.find_elements(selector)

    def click(self, selector: str, optional: bool = False, timeout: int = 5000):
        try:
            self._run(self._page.click(selector, timeout=timeout))
        except Exception:
            if not optional:
                raise

    def fill(self, selector: str, value: str):
        self._run(self._page.fill(selector, str(value)))

    def select(self, selector: str, value: str):
        self._run(self._page.select_option(selector, value=value))

    def evaluate(self, script: str) -> Any:
        return self._run(self._page.evaluate(script))

    def screenshot(self, path: str = None, full_page: bool = False) -> bytes:
        return self._run(self._page.screenshot(path=path, full_page=full_page))

    @property
    def url(self) -> str:
        return self._page.url

    @property
    def title(self) -> str:
        return self._run(self._page.title())


# ─── Task Implementation ────────────────────────────────────────

class CustomScriptTask(BaseTask):
    """Execute Python scripts with optional browser context.

    Config:
        script: Python source code (required)
        language: "python" (default, only supported)
        headless: Run browser headless (default: true)
        viewport: Browser viewport (default: {"width": 1920, "height": 1080})
        timeout: Overall timeout in seconds (default: 300)
        user_agent_rotation: Enable random user agent (default: false)

    Script namespace receives:
        browser: SyncBrowserAPI instance (if script uses browser.*)
        steps: Dict of previous step results (from context)
        variables: Dict of workflow variables
        config: Dict of runtime config
        state: Shared state dict (mutable, persists)
        item: Current loop item (if inside a loop)
        output: Dict to set as step output (script should assign this)

    Standard library modules are available:
        json, re, os, time, datetime, random, math, urllib, csv, hashlib
    """

    task_type = "custom_script"
    display_name = "Custom Script"
    description = "Execute Python code with optional browser automation"
    icon = "🔧"

    async def execute(
        self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        script = config.get("script", "")
        if not script:
            return TaskResult(success=False, error="No script provided")

        language = config.get("language", "python")
        if language != "python":
            return TaskResult(success=False, error=f"Unsupported language: {language}")

        timeout = config.get("timeout", 300)
        needs_browser = _script_uses_browser(script)
        ctx = context or {}

        # Build script namespace with common imports and context
        namespace = self._build_namespace(ctx, config)

        if needs_browser and _check_playwright():
            return await self._execute_with_browser(script, namespace, config, timeout)
        else:
            return await self._execute_plain(script, namespace, timeout)

    def _build_namespace(self, context: Dict, config: Dict) -> Dict[str, Any]:
        """Build the execution namespace for the script."""
        import csv
        import hashlib
        import math
        import random
        import urllib.request

        # Extract step results from context and wrap in DotDict recursively
        steps_data = {}
        if "steps" in context:
            for sid, sresult in context["steps"].items():
                if isinstance(sresult, dict):
                    raw = sresult.get("output", sresult)
                else:
                    raw = sresult
                steps_data[sid] = _to_dotdict(raw) if isinstance(raw, dict) else raw

        # Create a dotdict-like access object for steps
        steps_proxy = DotDict(steps_data)

        return {
            # Context from workflow
            "steps": steps_proxy,
            "variables": context.get("variables", {}),
            "config": config,
            "state": context.get("variables", {}).get("_state", {}),
            "item": context.get("loop_item", None),
            # Output placeholder — script assigns to this
            "output": {},
            # Common imports available to scripts
            "json": json,
            "re": re,
            "os": os,
            "time": time,
            "datetime": datetime,
            "random": random,
            "math": math,
            "urllib": urllib,
            "csv": csv,
            "hashlib": hashlib,
            # Builtins
            "__builtins__": __builtins__,
            "print": lambda *a, **kw: logger.info("script_print", message=" ".join(str(x) for x in a)),
        }

    async def _execute_plain(
        self, script: str, namespace: Dict, timeout: int
    ) -> TaskResult:
        """Execute script without browser context."""
        try:
            # Run in thread to avoid blocking event loop
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, self._exec_script, script, namespace),
                timeout=timeout,
            )
            output = namespace.get("output", {})
            # Also capture state if script set it
            if namespace.get("state") and namespace["state"] != {}:
                output["_state"] = namespace["state"]
            return TaskResult(success=True, output=output)

        except asyncio.TimeoutError:
            return TaskResult(success=False, error=f"Script timed out after {timeout}s")
        except Exception as e:
            tb = traceback.format_exc()
            logger.error("custom_script_error", error=str(e), traceback=tb)
            return TaskResult(success=False, error=f"Script error: {str(e)}")

    async def _execute_with_browser(
        self, script: str, namespace: Dict, config: Dict, timeout: int
    ) -> TaskResult:
        """Execute script with Playwright browser context."""
        from playwright.async_api import async_playwright

        headless = config.get("headless", True)
        viewport = config.get("viewport", {"width": 1920, "height": 1080})

        pw = None
        browser_inst = None
        try:
            pw = await async_playwright().start()
            browser_inst = await pw.chromium.launch(headless=headless)
            ctx = await browser_inst.new_context(
                viewport=viewport,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await ctx.new_page()

            # Get the event loop to pass to SyncBrowserAPI
            loop = asyncio.get_event_loop()
            namespace["browser"] = SyncBrowserAPI(page, loop)

            # Run script in thread (so sync browser calls work via run_coroutine_threadsafe)
            await asyncio.wait_for(
                loop.run_in_executor(None, self._exec_script, script, namespace),
                timeout=timeout,
            )

            output = namespace.get("output", {})
            if namespace.get("state") and namespace["state"] != {}:
                output["_state"] = namespace["state"]
            return TaskResult(success=True, output=output)

        except asyncio.TimeoutError:
            return TaskResult(success=False, error=f"Script timed out after {timeout}s")
        except Exception as e:
            tb = traceback.format_exc()
            logger.error("custom_script_browser_error", error=str(e), traceback=tb)
            return TaskResult(success=False, error=f"Script error: {str(e)}")
        finally:
            if browser_inst:
                await browser_inst.close()
            if pw:
                await pw.stop()

    @staticmethod
    def _exec_script(script: str, namespace: dict):
        """Execute Python code in the given namespace."""
        exec(compile(script, "<custom_script>", "exec"), namespace)

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["script"],
            "properties": {
                "script": {"type": "string", "description": "Python source code"},
                "language": {"type": "string", "default": "python"},
                "headless": {"type": "boolean", "default": True},
                "viewport": {"type": "object"},
                "timeout": {"type": "integer", "default": 300},
            },
        }


def _to_dotdict(obj):
    """Recursively convert dicts to DotDict."""
    if isinstance(obj, dict) and not isinstance(obj, DotDict):
        return DotDict({k: _to_dotdict(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_to_dotdict(item) for item in obj]
    return obj


class DotDict(dict):
    """Dict subclass with dot notation access: steps.step_1.output_field.

    Supports len(), item assignment, iteration, and all standard dict ops.
    """

    def __init__(self, data=None):
        super().__init__(data or {})

    def __getattr__(self, key):
        if key.startswith("_"):
            return super().__getattribute__(key)
        try:
            val = self[key]
        except KeyError:
            # Try with underscore/dash swap
            alt = key.replace("_", "-") if "_" in key else key.replace("-", "_")
            try:
                val = self[alt]
            except KeyError:
                return DotDict({})  # Return empty DotDict instead of raising
        if isinstance(val, dict) and not isinstance(val, DotDict):
            return DotDict(val)
        return val

    def __setattr__(self, key, value):
        if key.startswith("_"):
            super().__setattr__(key, value)
        else:
            self[key] = value

    def __repr__(self):
        return f"DotDict({dict.__repr__(self)})"
