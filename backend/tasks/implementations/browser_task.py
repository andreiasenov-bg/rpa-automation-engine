"""Browser automation tasks using Playwright.

Provides headless browser capabilities for:
- Web scraping (CSS/XPath selectors, full page or element extraction)
- Form filling (input, select, checkbox, radio, submit)
- Screenshot capture (full page, element, viewport)
- PDF generation from web pages
- Page interaction (click, type, navigate, wait)

Requires: playwright (pip install playwright && playwright install chromium)
"""

import asyncio
import base64
import json
import os
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
    """Create a Playwright browser instance."""
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless, **launch_kwargs)
    return pw, browser


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

        url = config.get("url")
        if not url:
            return TaskResult(success=False, error="Missing required config: url")

        steps = config.get("steps", [])
        if not steps:
            return TaskResult(success=False, error="Missing required config: steps")

        viewport = config.get("viewport", {"width": 1280, "height": 720})
        default_timeout = config.get("timeout", 10000)

        pw = None
        browser = None
        try:
            pw, browser = await _get_browser()
            ctx = await browser.new_context(viewport=viewport)
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=default_timeout)

            step_results: List[Dict[str, Any]] = []
            screenshots: Dict[str, str] = {}

            for i, step in enumerate(steps):
                action = step.get("action", "")
                timeout = step.get("timeout", default_timeout)
                step_info: Dict[str, Any] = {"step": i + 1, "action": action, "success": True}

                try:
                    if action == "goto":
                        await page.goto(step["url"], wait_until="domcontentloaded", timeout=timeout)
                    elif action == "click":
                        await page.click(step["selector"], timeout=timeout)
                    elif action == "fill":
                        await page.fill(step["selector"], str(step.get("value", "")))
                    elif action == "press":
                        await page.keyboard.press(step["key"])
                    elif action == "wait":
                        await page.wait_for_selector(step["selector"], timeout=timeout)
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


# Export for task registry
BROWSER_TASK_TYPES = {
    "web_scrape": WebScrapeTask,
    "form_fill": FormFillTask,
    "screenshot": ScreenshotTask,
    "pdf_generate": PdfGenerateTask,
    "page_interaction": PageInteractionTask,
}
