"""Browser automation tasks using Playwright.

Provides headless browser capabilities for:
- Web scraping (CSS/XPath selectors, full page or element extraction)
- Form filling (input, select, checkbox, radio, submit)
- Screenshot capture (full page, element, viewport)
- PDF generation from web pages
- Page interaction (click, type, navigate, wait)

Features:
- BrowserSessionManager: shares a single browser session across all steps
  in one execution (navigate → click → extract all use the same page)
- Stealth mode: realistic user-agent, hidden webdriver flags, proper
  headers — bypasses basic bot detection (Amazon, Galaxus, etc.)

Requires: playwright (pip install playwright && playwright install chromium)
"""

import asyncio
import base64
import json
import os
import random
import tempfile
from typing import Any, Dict, List, Optional

import structlog

from tasks.base_task import BaseTask, TaskResult

logger = structlog.get_logger(__name__)

# Lazy import — Playwright is optional
_playwright_available: Optional[bool] = None


def _check_playwright() -> bool:
    global _playwright_available
    if _playwright_available is None:
        try:
            import playwright  # noqa: F401
            _playwright_available = True
        except ImportError:
            _playwright_available = False
    return _playwright_available


async def _get_browser(headless: bool = True, **launch_kwargs):
    """Create a Playwright browser instance (legacy — standalone tasks)."""
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless, **launch_kwargs)
    return pw, browser


# ─── Stealth & anti-detection ──────────────────────────────────────────────────

_STEALTH_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

_STEALTH_JS = """
// Hide webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => false });

// Fake plugins array
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Fake languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['de-DE', 'de', 'en-US', 'en'],
});

// Override permissions query
if (navigator.permissions) {
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);
}

// Fake chrome runtime
window.chrome = { runtime: {} };
"""


# ─── Shared browser session manager ───────────────────────────────────────────

class BrowserSessionManager:
    """Manages a shared Playwright browser session across workflow steps.

    Within a single execution, all browser_navigate / browser_click /
    browser_extract steps reuse the SAME browser context and page so that
    cookies, login state, and DOM are preserved between steps.

    Usage in task context:
        session = BrowserSessionManager.get_or_create(execution_id)
        page = await session.get_page(url)  # navigates only if URL changed
        ...
        # Session is cleaned up automatically after execution completes
    """

    _sessions: Dict[str, "BrowserSessionManager"] = {}  # execution_id -> session

    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._current_url: Optional[str] = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_or_create(cls, context: Optional[Dict[str, Any]] = None) -> "BrowserSessionManager":
        """Get existing session for this execution or create a new one."""
        exec_key = "default"
        if context and context.get("workflow_id"):
            exec_key = context.get("workflow_id", "default")
        if exec_key not in cls._sessions:
            cls._sessions[exec_key] = cls()
        return cls._sessions[exec_key]

    async def get_page(self, url: Optional[str] = None, wait_until: str = "domcontentloaded",
                       timeout: int = 30000) -> Any:
        """Get the shared page, navigating to URL if needed."""
        async with self._lock:
            if not self._pw:
                from playwright.async_api import async_playwright
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                )
                ua = random.choice(_STEALTH_USER_AGENTS)
                self._context = await self._browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent=ua,
                    locale="de-DE",
                    timezone_id="Europe/Berlin",
                    extra_http_headers={
                        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "DNT": "1",
                        "Sec-CH-UA": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                        "Sec-CH-UA-Mobile": "?0",
                        "Sec-CH-UA-Platform": '"Windows"',
                    },
                )
                self._page = await self._context.new_page()
                # Inject stealth JS on every new document
                await self._page.add_init_script(_STEALTH_JS)
                logger.info("Browser session created", user_agent=ua)

            if url and url != self._current_url:
                response = await self._page.goto(url, wait_until=wait_until, timeout=timeout)
                self._current_url = self._page.url
                # Brief pause for dynamic content
                await self._page.wait_for_timeout(1000)
                return self._page, response

            return self._page, None

    async def close(self):
        """Close the browser session."""
        try:
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception as e:
            logger.warning(f"Error closing browser session: {e}")
        finally:
            self._pw = None
            self._browser = None
            self._context = None
            self._page = None
            self._current_url = None

    @classmethod
    async def cleanup(cls, context: Optional[Dict[str, Any]] = None):
        """Close and remove session for the given execution context."""
        exec_key = "default"
        if context and context.get("workflow_id"):
            exec_key = context.get("workflow_id", "default")
        session = cls._sessions.pop(exec_key, None)
        if session:
            await session.close()

    @classmethod
    async def cleanup_all(cls):
        """Close all active sessions."""
        for key in list(cls._sessions.keys()):
            session = cls._sessions.pop(key, None)
            if session:
                await session.close()


class WebScrapeTask(BaseTask):
    """Scrape data from web pages using CSS/XPath selectors.

    Config:
        url: Target URL (required)
        selectors: List of extraction rules (required)
            [
                {
                    "name": "title",
                    "selector": "h1.page-title",
                    "type": "css",             # css | xpath (default: css)
                    "extract": "text",          # text | html | attribute (default: text)
                    "attribute": "href",        # required when extract=attribute
                    "multiple": false           # return list of all matches
                }
            ]
        wait_for: CSS selector to wait for before scraping
        wait_timeout: Max wait time in ms (default: 10000)
        javascript: JS to execute before scraping
        headers: Custom HTTP headers
        viewport: { "width": 1280, "height": 720 }
        user_agent: Custom user agent string
        cookies: List of { "name", "value", "domain" } dicts
        proxy: { "server": "...", "username": "...", "password": "..." }
    """

    task_type = "web_scrape"
    display_name = "Web Scrape"
    description = "Extract data from web pages using selectors"
    icon = "🕷️"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed. Run: pip install playwright && playwright install chromium")

        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        selectors = config.get("selectors", [])
        if not selectors:
            return TaskResult(success=False, error="Missing required config: selectors")

        wait_for = config.get("wait_for")
        wait_timeout = config.get("wait_timeout", 10000)
        javascript = config.get("javascript")
        headers = config.get("headers", {})
        viewport = config.get("viewport", {"width": 1280, "height": 720})
        user_agent = config.get("user_agent")
        cookies = config.get("cookies", [])
        proxy = config.get("proxy")

        pw = None
        browser = None
        try:
            launch_kwargs = {}
            if proxy:
                launch_kwargs["proxy"] = proxy

            pw, browser = await _get_browser(**launch_kwargs)
            ctx_kwargs: Dict[str, Any] = {"viewport": viewport}
            if user_agent:
                ctx_kwargs["user_agent"] = user_agent
            if headers:
                ctx_kwargs["extra_http_headers"] = headers

            browser_context = await browser.new_context(**ctx_kwargs)

            if cookies:
                await browser_context.add_cookies(cookies)

            page = await browser_context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=wait_timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=wait_timeout)

            if javascript:
                await page.evaluate(javascript)
                await page.wait_for_timeout(500)

            # Extract data for each selector
            results: Dict[str, Any] = {}
            for rule in selectors:
                name = rule.get("name", f"field_{len(results)}")
                selector = rule.get("selector", "")
                sel_type = rule.get("type", "css")
                extract = rule.get("extract", "text")
                attribute = rule.get("attribute", "")
                multiple = rule.get("multiple", False)

                try:
                    if sel_type == "xpath":
                        elements = await page.query_selector_all(f"xpath={selector}")
                    else:
                        elements = await page.query_selector_all(selector)

                    if not elements:
                        results[name] = [] if multiple else None
                        continue

                    targets = elements if multiple else elements[:1]
                    extracted: List[Any] = []

                    for el in targets:
                        if extract == "html":
                            val = await el.inner_html()
                        elif extract == "attribute" and attribute:
                            val = await el.get_attribute(attribute)
                        else:
                            val = (await el.inner_text()).strip()
                        extracted.append(val)

                    results[name] = extracted if multiple else extracted[0]

                except Exception as e:
                    logger.warning("Selector extraction failed", name=name, error=str(e))
                    results[name] = None

            page_title = await page.title()
            page_url = page.url

            return TaskResult(
                success=True,
                output={
                    "data": results,
                    "page_title": page_title,
                    "page_url": page_url,
                    "selectors_matched": sum(1 for v in results.values() if v is not None),
                    "selectors_total": len(selectors),
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"Web scrape failed: {str(e)}")
        finally:
            if browser:
                await browser.close()
            if pw:
                await pw.stop()

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url", "selectors"],
            "properties": {
                "url": {"type": "string", "description": "Target URL to scrape"},
                "selectors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "selector": {"type": "string"},
                            "type": {"type": "string", "enum": ["css", "xpath"]},
                            "extract": {"type": "string", "enum": ["text", "html", "attribute"]},
                            "attribute": {"type": "string"},
                            "multiple": {"type": "boolean"},
                        },
                    },
                },
                "wait_for": {"type": "string", "description": "CSS selector to wait for"},
                "wait_timeout": {"type": "integer", "default": 10000},
                "javascript": {"type": "string", "description": "JS to run before scraping"},
                "viewport": {"type": "object"},
                "user_agent": {"type": "string"},
                "cookies": {"type": "array"},
                "proxy": {"type": "object"},
            },
        }


class FormFillTask(BaseTask):
    """Fill and submit web forms automatically.

    Config:
        url: Form page URL (required)
        fields: List of form field actions (required)
            [
                {
                    "selector": "#username",
                    "value": "john@example.com",
                    "action": "fill"           # fill | select | check | uncheck | click
                },
                {
                    "selector": "#country",
                    "value": "Bulgaria",
                    "action": "select"
                },
                {
                    "selector": "#agree",
                    "action": "check"
                }
            ]
        submit: Selector for submit button (optional — auto-click if provided)
        wait_after_submit: CSS selector to wait for after submit
        wait_timeout: Max wait time in ms (default: 15000)
        screenshot_after: Take screenshot after submission (default: false)
        extract_after: Selectors to extract from result page
        credentials_id: UUID of stored credential to use for sensitive fields
    """

    task_type = "form_fill"
    display_name = "Form Fill"
    description = "Automatically fill and submit web forms"
    icon = "📝"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed")

        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        fields = config.get("fields", [])
        if not fields:
            return TaskResult(success=False, error="Missing required config: fields")

        submit_selector = config.get("submit")
        wait_after = config.get("wait_after_submit")
        wait_timeout = config.get("wait_timeout", 15000)
        screenshot_after = config.get("screenshot_after", False)
        extract_after = config.get("extract_after", [])

        pw = None
        browser = None
        try:
            pw, browser = await _get_browser()
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=wait_timeout)

            # Resolve credential values from context if needed
            cred_values = {}
            cred_id = config.get("credentials_id")
            if cred_id and context and "credentials" in context:
                cred_values = context["credentials"].get(cred_id, {})

            filled_count = 0
            for field in fields:
                selector = field.get("selector", "")
                action = field.get("action", "fill")
                value = field.get("value", "")

                # Substitute credential placeholders like {{credential.username}}
                if isinstance(value, str) and value.startswith("{{credential."):
                    key = value.strip("{} ").replace("credential.", "")
                    value = cred_values.get(key, value)

                try:
                    if action == "fill":
                        await page.fill(selector, str(value))
                    elif action == "select":
                        await page.select_option(selector, label=str(value))
                    elif action == "check":
                        await page.check(selector)
                    elif action == "uncheck":
                        await page.uncheck(selector)
                    elif action == "click":
                        await page.click(selector)
                    filled_count += 1
                except Exception as e:
                    logger.warning("Form field action failed", selector=selector, error=str(e))

            # Submit
            submitted = False
            if submit_selector:
                await page.click(submit_selector)
                submitted = True
                if wait_after:
                    await page.wait_for_selector(wait_after, timeout=wait_timeout)
                else:
                    await page.wait_for_load_state("networkidle", timeout=wait_timeout)

            # Extract post-submit data
            extracted = {}
            for rule in extract_after:
                name = rule.get("name", f"result_{len(extracted)}")
                sel = rule.get("selector", "")
                try:
                    el = await page.query_selector(sel)
                    if el:
                        extracted[name] = (await el.inner_text()).strip()
                except Exception:
                    extracted[name] = None

            # Optional screenshot
            screenshot_b64 = None
            if screenshot_after:
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

            return TaskResult(
                success=True,
                output={
                    "fields_filled": filled_count,
                    "fields_total": len(fields),
                    "submitted": submitted,
                    "result_url": page.url,
                    "extracted": extracted,
                    "screenshot_base64": screenshot_b64,
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"Form fill failed: {str(e)}")
        finally:
            if browser:
                await browser.close()
            if pw:
                await pw.stop()

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url", "fields"],
            "properties": {
                "url": {"type": "string"},
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string"},
                            "value": {"type": "string"},
                            "action": {"type": "string", "enum": ["fill", "select", "check", "uncheck", "click"]},
                        },
                    },
                },
                "submit": {"type": "string"},
                "wait_after_submit": {"type": "string"},
                "wait_timeout": {"type": "integer", "default": 15000},
                "screenshot_after": {"type": "boolean", "default": False},
                "extract_after": {"type": "array"},
                "credentials_id": {"type": "string", "format": "uuid"},
            },
        }


class ScreenshotTask(BaseTask):
    """Capture screenshots of web pages or elements.

    Config:
        url: Target URL (required)
        full_page: Capture full scrollable page (default: false)
        selector: CSS selector to screenshot specific element
        viewport: { "width": 1280, "height": 720 }
        wait_for: CSS selector to wait for before capture
        wait_timeout: Max wait time in ms (default: 10000)
        format: "png" | "jpeg" (default: png)
        quality: JPEG quality 0-100 (default: 80, only for jpeg)
        save_path: File path to save screenshot (optional)
        output_base64: Return base64-encoded image (default: true)
    """

    task_type = "screenshot"
    display_name = "Screenshot"
    description = "Capture screenshots of web pages"
    icon = "📸"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed")

        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        full_page = config.get("full_page", False)
        selector = config.get("selector")
        viewport = config.get("viewport", {"width": 1280, "height": 720})
        wait_for = config.get("wait_for")
        wait_timeout = config.get("wait_timeout", 10000)
        img_format = config.get("format", "png")
        quality = config.get("quality", 80)
        save_path = config.get("save_path")
        output_base64 = config.get("output_base64", True)

        pw = None
        browser = None
        try:
            pw, browser = await _get_browser()
            ctx = await browser.new_context(viewport=viewport)
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=wait_timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=wait_timeout)

            screenshot_kwargs: Dict[str, Any] = {"type": img_format}
            if img_format == "jpeg":
                screenshot_kwargs["quality"] = quality

            if selector:
                element = await page.query_selector(selector)
                if not element:
                    return TaskResult(success=False, error=f"Element not found: {selector}")
                screenshot_bytes = await element.screenshot(**screenshot_kwargs)
            else:
                screenshot_kwargs["full_page"] = full_page
                screenshot_bytes = await page.screenshot(**screenshot_kwargs)

            # Save to file if requested
            if save_path:
                os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(screenshot_bytes)

            output: Dict[str, Any] = {
                "size_bytes": len(screenshot_bytes),
                "format": img_format,
                "page_title": await page.title(),
                "page_url": page.url,
            }

            if save_path:
                output["file_path"] = save_path
            if output_base64:
                output["image_base64"] = base64.b64encode(screenshot_bytes).decode()

            return TaskResult(success=True, output=output)

        except Exception as e:
            return TaskResult(success=False, error=f"Screenshot failed: {str(e)}")
        finally:
            if browser:
                await browser.close()
            if pw:
                await pw.stop()

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string"},
                "full_page": {"type": "boolean", "default": False},
                "selector": {"type": "string"},
                "viewport": {"type": "object"},
                "wait_for": {"type": "string"},
                "wait_timeout": {"type": "integer"},
                "format": {"type": "string", "enum": ["png", "jpeg"]},
                "quality": {"type": "integer", "minimum": 0, "maximum": 100},
                "save_path": {"type": "string"},
                "output_base64": {"type": "boolean", "default": True},
            },
        }


class PdfGenerateTask(BaseTask):
    """Generate PDF from a web page.

    Config:
        url: Target URL (required)
        save_path: File path to save PDF (optional, auto-generated if not provided)
        format: Paper format — A4, Letter, Legal, etc. (default: A4)
        landscape: Landscape orientation (default: false)
        print_background: Include background graphics (default: true)
        margin: { "top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm" }
        header_template: HTML template for header
        footer_template: HTML template for footer
        wait_for: CSS selector to wait for before generating
        wait_timeout: Max wait time in ms (default: 10000)
        output_base64: Return base64-encoded PDF (default: false)
    """

    task_type = "pdf_generate"
    display_name = "PDF Generate"
    description = "Generate PDF documents from web pages"
    icon = "📄"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed")

        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        save_path = config.get("save_path")
        if not save_path:
            save_path = os.path.join(tempfile.gettempdir(), f"rpa_pdf_{os.urandom(4).hex()}.pdf")

        paper_format = config.get("format", "A4")
        landscape = config.get("landscape", False)
        print_bg = config.get("print_background", True)
        margin = config.get("margin", {"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"})
        header_template = config.get("header_template")
        footer_template = config.get("footer_template")
        wait_for = config.get("wait_for")
        wait_timeout = config.get("wait_timeout", 10000)
        output_base64 = config.get("output_base64", False)

        pw = None
        browser = None
        try:
            pw, browser = await _get_browser()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=wait_timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=wait_timeout)

            pdf_kwargs: Dict[str, Any] = {
                "path": save_path,
                "format": paper_format,
                "landscape": landscape,
                "print_background": print_bg,
                "margin": margin,
            }
            if header_template:
                pdf_kwargs["display_header_footer"] = True
                pdf_kwargs["header_template"] = header_template
            if footer_template:
                pdf_kwargs["display_header_footer"] = True
                pdf_kwargs["footer_template"] = footer_template

            pdf_bytes = await page.pdf(**pdf_kwargs)

            output: Dict[str, Any] = {
                "file_path": save_path,
                "size_bytes": len(pdf_bytes),
                "format": paper_format,
                "landscape": landscape,
                "page_title": await page.title(),
                "page_url": page.url,
            }

            if output_base64:
                output["pdf_base64"] = base64.b64encode(pdf_bytes).decode()

            return TaskResult(success=True, output=output)

        except Exception as e:
            return TaskResult(success=False, error=f"PDF generation failed: {str(e)}")
        finally:
            if browser:
                await browser.close()
            if pw:
                await pw.stop()

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string"},
                "save_path": {"type": "string"},
                "format": {"type": "string", "enum": ["A4", "Letter", "Legal", "Tabloid", "A3", "A5"]},
                "landscape": {"type": "boolean", "default": False},
                "print_background": {"type": "boolean", "default": True},
                "margin": {"type": "object"},
                "header_template": {"type": "string"},
                "footer_template": {"type": "string"},
                "wait_for": {"type": "string"},
                "wait_timeout": {"type": "integer"},
                "output_base64": {"type": "boolean", "default": False},
            },
        }


class PageInteractionTask(BaseTask):
    """Execute a sequence of browser interactions on a page.

    Config:
        url: Starting URL (required)
        steps: List of interaction steps (required)
            [
                { "action": "goto", "url": "https://..." },
                { "action": "click", "selector": "#btn" },
                { "action": "fill", "selector": "#search", "value": "RPA" },
                { "action": "press", "key": "Enter" },
                { "action": "wait", "selector": ".results" },
                { "action": "wait_ms", "duration": 2000 },
                { "action": "select", "selector": "#dropdown", "value": "opt1" },
                { "action": "scroll", "direction": "down", "amount": 500 },
                { "action": "evaluate", "script": "document.title" },
                { "action": "screenshot", "name": "step_result" }
            ]
        viewport: { "width": 1280, "height": 720 }
        timeout: Default timeout for each step in ms (default: 10000)
    """

    task_type = "page_interaction"
    display_name = "Page Interaction"
    description = "Execute browser interaction sequences"
    icon = "🖱️"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed")

        steps = config.get("steps", [])
        if not steps:
            return TaskResult(success=False, error="Missing required config: steps")

        # URL can come from config top-level or from first navigate/goto step
        url = config.get("url")
        viewport = config.get("viewport", {"width": 1280, "height": 720})
        default_timeout = config.get("timeout", 10000)
        headless = config.get("headless", True)

        pw = None
        browser = None
        try:
            pw, browser = await _get_browser(headless=headless)
            ctx = await browser.new_context(viewport=viewport)
            page = await ctx.new_page()

            # Only navigate to initial URL if provided (templates may use navigate action instead)
            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=default_timeout)

            step_results: List[Dict[str, Any]] = []
            screenshots: Dict[str, str] = {}

            for i, step in enumerate(steps):
                action = step.get("action", "")
                timeout = step.get("timeout", default_timeout)
                step_info: Dict[str, Any] = {"step": i + 1, "action": action, "success": True}

                try:
                    if action in ("goto", "navigate"):
                        target_url = step.get("url", url)
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout)
                    elif action == "click":
                        optional = step.get("optional", False)
                        try:
                            await page.click(step["selector"], timeout=timeout)
                        except Exception:
                            if not optional:
                                raise
                    elif action == "fill":
                        await page.fill(step["selector"], str(step.get("value", "")))
                    elif action == "press":
                        await page.keyboard.press(step["key"])
                    elif action == "wait":
                        if "selector" in step:
                            await page.wait_for_selector(step["selector"], timeout=timeout)
                        else:
                            wait_s = step.get("timeout", step.get("duration", 1))
                            wait_ms = int(wait_s * 1000) if isinstance(wait_s, (int, float)) and wait_s < 100 else int(wait_s)
                            await page.wait_for_timeout(wait_ms)
                    elif action == "wait_ms":
                        await page.wait_for_timeout(step.get("duration", 1000))
                    elif action == "select":
                        await page.select_option(step["selector"], value=step.get("value"))
                    elif action == "scroll":
                        direction = step.get("direction", "down")
                        amount = step.get("amount", 500)
                        delta = amount if direction == "down" else -amount
                        await page.evaluate(f"window.scrollBy(0, {delta})")
                    elif action == "evaluate":
                        result = await page.evaluate(step["script"])
                        step_info["result"] = result
                    elif action == "screenshot":
                        name = step.get("name", f"step_{i+1}")
                        shot = await page.screenshot(full_page=step.get("full_page", False))
                        screenshots[name] = base64.b64encode(shot).decode()
                    else:
                        step_info["success"] = False
                        step_info["error"] = f"Unknown action: {action}"

                except Exception as e:
                    step_info["success"] = False
                    step_info["error"] = str(e)
                    if step.get("required", False):
                        step_results.append(step_info)
                        return TaskResult(
                            success=False,
                            output={"steps": step_results, "screenshots": screenshots},
                            error=f"Required step {i+1} failed: {str(e)}",
                        )

                step_results.append(step_info)

            all_ok = all(s["success"] for s in step_results)
            return TaskResult(
                success=all_ok,
                output={
                    "steps": step_results,
                    "steps_succeeded": sum(1 for s in step_results if s["success"]),
                    "steps_total": len(step_results),
                    "final_url": page.url,
                    "final_title": await page.title(),
                    "screenshots": screenshots,
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"Page interaction failed: {str(e)}")
        finally:
            if browser:
                await browser.close()
            if pw:
                await pw.stop()

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url", "steps"],
            "properties": {
                "url": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": [
                                    "goto", "click", "fill", "press", "wait",
                                    "wait_ms", "select", "scroll", "evaluate", "screenshot",
                                ],
                            },
                            "selector": {"type": "string"},
                            "value": {"type": "string"},
                            "key": {"type": "string"},
                            "url": {"type": "string"},
                            "script": {"type": "string"},
                            "required": {"type": "boolean", "default": False},
                        },
                    },
                },
                "viewport": {"type": "object"},
                "timeout": {"type": "integer", "default": 10000},
            },
        }


class BrowserNavigateTask(BaseTask):
    """Navigate to a URL using a shared stealth browser session.

    Uses BrowserSessionManager to share browser state across steps.
    Includes anti-bot detection measures for sites like Amazon.

    Config:
        url: Target URL (required)
        wait_for: CSS selector to wait for after navigation
        wait_timeout: Max wait time in ms (default: 30000)
        wait_until: Load state — domcontentloaded | load | networkidle (default: load)
        javascript: JS to execute after page load
    """

    task_type = "browser_navigate"
    display_name = "Browser Navigate"
    description = "Navigate to a URL in a stealth browser session"
    icon = "🌐"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed. Run: pip install playwright && playwright install chromium")

        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        wait_for = config.get("wait_for")
        wait_timeout = config.get("wait_timeout", 30000)
        wait_until = config.get("wait_until", "load")
        javascript = config.get("javascript")

        try:
            session = BrowserSessionManager.get_or_create(context)
            page, response = await session.get_page(url, wait_until=wait_until, timeout=wait_timeout)

            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=wait_timeout)
                except Exception:
                    logger.info(f"wait_for selector '{wait_for}' not found, continuing")

            if javascript:
                await page.evaluate(javascript)

            status = response.status if response else None
            page_title = await page.title()
            final_url = page.url

            body_text = await page.evaluate("document.body ? document.body.innerText.substring(0, 5000) : ''")

            return TaskResult(
                success=True,
                output={
                    "url": final_url,
                    "page_title": page_title,
                    "status_code": status,
                    "body_preview": body_text[:2000] if body_text else "",
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"Browser navigate failed: {str(e)}")

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "Target URL to navigate to"},
                "wait_for": {"type": "string", "description": "CSS selector to wait for"},
                "wait_timeout": {"type": "integer", "default": 30000},
                "wait_until": {"type": "string", "enum": ["domcontentloaded", "load", "networkidle"]},
                "javascript": {"type": "string"},
            },
        }


class BrowserClickTask(BaseTask):
    """Click an element on the current page in the shared browser session.

    Reuses the browser session from BrowserNavigateTask — no need to
    re-navigate if already on the right page.

    Config:
        url: Page URL — navigates only if not already there (optional if preceded by navigate)
        selector: CSS selector of element to click (required)
        wait_for: CSS selector to wait for after click
        wait_timeout: Max wait time in ms (default: 10000)
        optional: If true, don't fail when element not found (default: true)
        javascript_before: JS to execute before clicking
        javascript_after: JS to execute after clicking
    """

    task_type = "browser_click"
    display_name = "Browser Click"
    description = "Click an element on a web page"
    icon = "👆"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed. Run: pip install playwright && playwright install chromium")

        selector = config.get("selector")
        if not selector:
            return TaskResult(success=False, error="Missing required config: selector")

        url = config.get("url")
        wait_for = config.get("wait_for")
        wait_timeout = config.get("wait_timeout", 10000)
        optional = config.get("optional", True)
        js_before = config.get("javascript_before")
        js_after = config.get("javascript_after")

        try:
            session = BrowserSessionManager.get_or_create(context)
            page, _ = await session.get_page(url, timeout=wait_timeout)

            if js_before:
                await page.evaluate(js_before)

            clicked = False
            try:
                await page.click(selector, timeout=wait_timeout)
                clicked = True
            except Exception as click_err:
                if not optional:
                    return TaskResult(success=False, error=f"Click failed on '{selector}': {str(click_err)}")
                logger.info("Optional click target not found, continuing", selector=selector)

            if clicked and js_after:
                await page.evaluate(js_after)

            if clicked and wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=wait_timeout)
                except Exception:
                    pass

            await page.wait_for_timeout(500)

            return TaskResult(
                success=True,
                output={
                    "clicked": clicked,
                    "selector": selector,
                    "url_after": page.url,
                    "page_title": await page.title(),
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"Browser click failed: {str(e)}")

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["selector"],
            "properties": {
                "url": {"type": "string", "description": "Page URL (optional if already navigated)"},
                "selector": {"type": "string", "description": "CSS selector of element to click"},
                "wait_for": {"type": "string", "description": "CSS selector to wait for after click"},
                "wait_timeout": {"type": "integer", "default": 10000},
                "optional": {"type": "boolean", "default": True, "description": "Skip if element not found"},
                "javascript_before": {"type": "string"},
                "javascript_after": {"type": "string"},
            },
        }


class BrowserExtractTask(BaseTask):
    """Extract text/data from the current page in the shared browser session.

    Supports three extraction modes:

    1) **javascript** mode (recommended for complex scraping):
       Run a custom JS function that returns structured data.
       Config: { "javascript": "Array.from(document.querySelectorAll('.item')).map(..." }

    2) **selectors** mode (multi-field extraction):
       Extract multiple named fields using CSS selectors.
       Config: { "selectors": [{"name": "titles", "selector": "h2", "extract": "text", "multiple": true}, ...] }

    3) **selector** mode (simple single-field):
       Extract from one CSS selector.
       Config: { "selector": "h2.title", "extract": "text", "multiple": true }

    Common config:
        url: Page URL — navigates only if needed (optional if preceded by navigate)
        wait_for: CSS selector to wait for before extraction
        wait_timeout: Max wait time in ms (default: 15000)
    """

    task_type = "browser_extract"
    display_name = "Browser Extract"
    description = "Extract text or data from a web page element"
    icon = "📋"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        if not _check_playwright():
            return TaskResult(success=False, error="Playwright not installed")

        url = config.get("url")
        wait_for = config.get("wait_for")
        wait_timeout = config.get("wait_timeout", 15000)
        javascript = config.get("javascript")
        selectors = config.get("selectors")
        selector = config.get("selector")

        # ── Mode 0: Loop extraction (navigate to multiple pages) ──────
        loop_config = config.get("loop")
        if loop_config:
            return await self._execute_loop(loop_config, config, context)

        if not javascript and not selectors and not selector:
            return TaskResult(success=False, error="Missing required config: provide 'javascript', 'selectors', or 'selector'")

        try:
            session = BrowserSessionManager.get_or_create(context)
            page, _ = await session.get_page(url, timeout=wait_timeout)

            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=wait_timeout)
                except Exception:
                    logger.info(f"wait_for selector '{wait_for}' not found, continuing")

            page_title = await page.title()
            page_url = page.url

            # ── Mode 1: JavaScript extraction ──────────────────────────────
            if javascript:
                # Inject previous step results into browser context for cross-step data sharing
                if context and "steps" in context:
                    try:
                        import json as _json
                        steps_json = _json.dumps(context["steps"], default=str)
                        await page.evaluate(f"window.__rpaSteps = {steps_json};")
                    except Exception as inj_err:
                        logger.warning(f"Failed to inject step data into browser: {inj_err}")

                try:
                    result = await page.evaluate(javascript)
                except Exception as js_err:
                    return TaskResult(success=False, error=f"JS extraction failed: {str(js_err)}")

                # Determine count
                count = len(result) if isinstance(result, list) else 1

                return TaskResult(
                    success=True,
                    output={
                        "data": result,
                        "count": count,
                        "page_title": page_title,
                        "page_url": page_url,
                    },
                )

            # ── Mode 2: Multiple selectors extraction ──────────────────────
            if selectors:
                results: Dict[str, Any] = {}
                for rule in selectors:
                    name = rule.get("name", f"field_{len(results)}")
                    sel = rule.get("selector", "")
                    extract_type = rule.get("extract", "text")
                    attr = rule.get("attribute", "")
                    multi = rule.get("multiple", False)

                    try:
                        # Wait briefly for selector
                        try:
                            await page.wait_for_selector(sel, timeout=min(wait_timeout, 5000))
                        except Exception:
                            pass

                        elements = await page.query_selector_all(sel)
                        if not elements:
                            results[name] = [] if multi else None
                            continue

                        targets = elements if multi else elements[:1]
                        extracted: List[Any] = []
                        for el in targets:
                            if extract_type == "html":
                                val = await el.inner_html()
                            elif extract_type == "attribute" and attr:
                                val = await el.get_attribute(attr)
                            else:
                                val = (await el.inner_text()).strip()
                            extracted.append(val)

                        results[name] = extracted if multi else extracted[0]
                    except Exception as e:
                        logger.warning("Selector extraction failed", name=name, error=str(e))
                        results[name] = [] if multi else None

                return TaskResult(
                    success=True,
                    output={
                        "data": results,
                        "page_title": page_title,
                        "page_url": page_url,
                        "selectors_matched": sum(1 for v in results.values() if v),
                        "selectors_total": len(selectors),
                    },
                )

            # ── Mode 3: Single selector extraction ─────────────────────────
            extract = config.get("extract", "text")
            attribute = config.get("attribute", "")
            multiple = config.get("multiple", False)

            try:
                await page.wait_for_selector(selector, timeout=min(wait_timeout, 10000))
            except Exception:
                logger.info(f"Extraction selector '{selector}' not found after wait")

            elements = await page.query_selector_all(selector)
            if not elements:
                return TaskResult(
                    success=True,
                    output={"data": [] if multiple else None, "count": 0},
                )

            targets = elements if multiple else elements[:1]
            extracted_vals = []
            for el in targets:
                if extract == "html":
                    val = await el.inner_html()
                elif extract == "attribute" and attribute:
                    val = await el.get_attribute(attribute)
                else:
                    val = (await el.inner_text()).strip()
                extracted_vals.append(val)

            return TaskResult(
                success=True,
                output={
                    "data": extracted_vals if multiple else extracted_vals[0],
                    "count": len(extracted_vals),
                    "page_title": page_title,
                    "page_url": page_url,
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"Browser extract failed: {str(e)}")

    async def _execute_loop(self, loop_config: Dict[str, Any], config: Dict[str, Any],
                            context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """Loop over items from a previous step, navigating to a URL per item and extracting data.

        loop config:
            source_step: Step ID to get items from (e.g. "step-3")
            url_template: URL with {field} placeholders (e.g. "https://galaxus.ch/en/search?q={title}")
            wait_for: CSS selector to wait for on each page
            wait_timeout: Max wait per page in ms (default: 15000)
            extract_js: JavaScript to run on each page; receives window.__currentItem
            delay_ms: Delay between navigations in ms (default: 1500)
            max_items: Max items to process (default: 20)
        """
        import urllib.parse as _urlparse

        source_step = loop_config.get("source_step", "")
        url_template = loop_config.get("url_template", "")
        lp_wait_for = loop_config.get("wait_for", "")
        lp_wait_timeout = loop_config.get("wait_timeout", 15000)
        extract_js = loop_config.get("extract_js", "")
        delay_ms = loop_config.get("delay_ms", 1500)
        max_items = loop_config.get("max_items", 20)

        if not source_step or not url_template or not extract_js:
            return TaskResult(success=False, error="Loop config requires: source_step, url_template, extract_js")

        # Get items from previous step
        items = []
        if context and "steps" in context:
            step_data = context["steps"].get(source_step) or context["steps"].get(source_step.replace("-", "_"))
            if step_data:
                output = step_data.get("output", step_data) if isinstance(step_data, dict) else {}
                if isinstance(output, dict):
                    items = output.get("data", [])
                    # Handle double-nesting: output.data might be {data: [...]} instead of [...]
                    if isinstance(items, dict) and "data" in items and isinstance(items["data"], list):
                        items = items["data"]
                elif isinstance(output, list):
                    items = output
        if isinstance(items, list):
            items = items[:max_items]
        else:
            items = []

        logger.info(f"Loop extract: {len(items)} items from {source_step}")

        try:
            session = BrowserSessionManager.get_or_create(context)
            results = []
            errors = []

            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    results.append(item)
                    continue

                # Build URL from template — replace {field} with URL-encoded item values
                try:
                    nav_url = url_template
                    # Fallback: if template uses {search_query} but item lacks it, use title
                    if "{search_query}" in nav_url and "search_query" not in item and "title" in item:
                        item["search_query"] = str(item["title"])[:60]
                    for key, val in item.items():
                        placeholder = "{" + key + "}"
                        if placeholder in nav_url:
                            nav_url = nav_url.replace(placeholder, _urlparse.quote(str(val)))
                except Exception as tmpl_err:
                    errors.append({"idx": idx, "error": f"URL template error: {tmpl_err}"})
                    results.append(item)
                    continue

                try:
                    # Get the shared page (don't pass URL — we'll navigate manually to force it)
                    page, _ = await session.get_page(timeout=lp_wait_timeout)
                    # Always navigate for loop items (each has different query params)
                    await page.goto(nav_url, wait_until="domcontentloaded", timeout=lp_wait_timeout)

                    # Wait for content to render
                    if lp_wait_for:
                        try:
                            await page.wait_for_selector(lp_wait_for, timeout=lp_wait_timeout)
                        except Exception:
                            pass
                    # Extra wait for client-side rendering (SPA pages)
                    await page.wait_for_timeout(4000)

                    # Inject current item data
                    import json as _json
                    item_json = _json.dumps(item, default=str)
                    await page.evaluate(f"window.__currentItem = {item_json};")

                    # Execute extraction JS
                    extracted = await page.evaluate(extract_js)

                    # Merge extracted data into item
                    merged = dict(item)
                    if isinstance(extracted, dict):
                        merged.update(extracted)
                    elif extracted is not None:
                        merged["_extracted"] = extracted
                    results.append(merged)

                    logger.info(f"Loop extract [{idx+1}/{len(items)}]: OK",
                                title=str(item.get("title", ""))[:50])

                except Exception as nav_err:
                    logger.warning(f"Loop extract [{idx+1}/{len(items)}] failed: {nav_err}")
                    errors.append({"idx": idx, "error": str(nav_err)})
                    results.append(item)

                # Delay between requests
                if idx < len(items) - 1 and delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000)

            return TaskResult(
                success=True,
                output={
                    "data": results,
                    "count": len(results),
                    "processed": len(results),
                    "errors": errors,
                    "error_count": len(errors),
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"Loop extract failed: {str(e)}")

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Page URL (optional if already navigated)"},
                "javascript": {"type": "string", "description": "JS code that returns extraction result"},
                "selectors": {
                    "type": "array",
                    "description": "Multiple named selectors for multi-field extraction",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "selector": {"type": "string"},
                            "extract": {"type": "string", "enum": ["text", "html", "attribute"]},
                            "attribute": {"type": "string"},
                            "multiple": {"type": "boolean"},
                        },
                    },
                },
                "selector": {"type": "string", "description": "Single CSS selector (simple mode)"},
                "extract": {"type": "string", "enum": ["text", "html", "attribute"]},
                "attribute": {"type": "string"},
                "multiple": {"type": "boolean", "default": False},
                "wait_for": {"type": "string"},
                "wait_timeout": {"type": "integer", "default": 15000},
            },
        }


class FileWriteTask(BaseTask):
    """Write data to a file on disk.

    Config:
        path: File path to write to (required)
        content: String content to write (required, unless data is provided)
        data: Structured data to write as JSON (alternative to content)
        mode: Write mode — write | append (default: write)
        encoding: File encoding (default: utf-8)
        create_dirs: Create parent directories if needed (default: true)
    """

    task_type = "file_write"
    display_name = "File Write"
    description = "Write data to a file"
    icon = "💾"

    async def execute(self, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> TaskResult:
        path = config.get("path")
        if not path:
            path = config.get("file_path") or config.get("filename")
        if not path:
            return TaskResult(success=False, error="Missing required config: path")

        content = config.get("content")
        data = config.get("data")
        mode = config.get("mode", "write")
        encoding = config.get("encoding", "utf-8")
        create_dirs = config.get("create_dirs", True)

        try:
            if create_dirs:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

            if data is not None and content is None:
                content = json.dumps(data, indent=2, ensure_ascii=False)

            if content is None:
                content = ""

            file_mode = "a" if mode == "append" else "w"
            with open(path, file_mode, encoding=encoding) as f:
                f.write(content)

            file_size = os.path.getsize(path)

            return TaskResult(
                success=True,
                output={
                    "path": path,
                    "size_bytes": file_size,
                    "mode": mode,
                },
            )

        except Exception as e:
            return TaskResult(success=False, error=f"File write failed: {str(e)}")

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "File path to write to"},
                "content": {"type": "string"},
                "data": {"description": "Structured data (written as JSON)"},
                "mode": {"type": "string", "enum": ["write", "append"]},
                "encoding": {"type": "string", "default": "utf-8"},
                "create_dirs": {"type": "boolean", "default": True},
            },
        }


# Export for task registry
BROWSER_TASK_TYPES = {
    "web_scrape": WebScrapeTask,
    "form_fill": FormFillTask,
    "screenshot": ScreenshotTask,
    "pdf_generate": PdfGenerateTask,
    "page_interaction": PageInteractionTask,
    "browser_navigate": BrowserNavigateTask,
    "browser_click": BrowserClickTask,
    "browser_extract": BrowserExtractTask,
    "file_write": FileWriteTask,
}
