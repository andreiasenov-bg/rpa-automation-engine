"""Enhanced stealth configuration for anti-detection.

Centralized config for browser fingerprinting, proxy rotation,
and behavioral mimicry. Used by browser_task.py and other scrapers.
"""

import random
from typing import Dict, List, Optional

# Expanded realistic User-Agent pool (Chrome on Win/Mac/Linux)
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Viewport sizes matching real monitor resolutions
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 2560, "height": 1440},
]

# Accept-Language headers per marketplace
LOCALE_HEADERS: Dict[str, str] = {
    "amazon.de": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "amazon.fr": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "amazon.it": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "amazon.es": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "amazon.nl": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
    "amazon.com": "en-US,en;q=0.9",
    "idealo.de": "de-DE,de;q=0.9,en;q=0.7",
    "geizhals.de": "de-DE,de;q=0.9,en;q=0.7",
    "bol.com": "nl-NL,nl;q=0.9,en;q=0.7",
    "default": "en-US,en;q=0.9",
}

# Stealth JS to inject into browser context
STEALTH_JS = """
// Hide webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Hide automation
delete navigator.__proto__.webdriver;

// Fake plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5].map(() => ({
        length: 1,
        item: () => null,
        namedItem: () => null,
    })),
});

// Fake languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en', 'de'],
});

// Chrome runtime
window.chrome = { runtime: {}, loadTimes: () => ({}) };

// Permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);
"""


def get_stealth_context_options(domain: str = "default") -> Dict:
    """Get randomized browser context options for stealth."""
    ua = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)
    locale = LOCALE_HEADERS.get(domain, LOCALE_HEADERS["default"])

    return {
        "user_agent": ua,
        "viewport": viewport,
        "locale": locale.split(",")[0].split("-")[0],
        "extra_http_headers": {
            "Accept-Language": locale,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        },
    }


def get_random_delay(min_s: float = 1.5, max_s: float = 5.0) -> float:
    """Get a random delay with slight gaussian distribution."""
    mean = (min_s + max_s) / 2
    std = (max_s - min_s) / 4
    delay = random.gauss(mean, std)
    return max(min_s, min(max_s, delay))
