"""Browser automation — control web pages via Playwright.

Requires: pip install playwright && playwright install chromium
"""

import json
from pathlib import Path

_HAS_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    pass

_INSTALL_HINT = (
    "Playwright is required.\n"
    "Install: pip install playwright && playwright install chromium"
)

_browser = None
_page = None
_playwright = None


def _get_page():
    global _browser, _page, _playwright
    if _page is not None:
        return _page

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=True)
    context = _browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
    )
    _page = context.new_page()
    return _page


def _cleanup():
    global _browser, _page, _playwright
    try:
        if _page:
            _page.close()
    except Exception:
        pass
    try:
        if _browser:
            _browser.close()
    except Exception:
        pass
    try:
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _page = None
    _browser = None
    _playwright = None


def browser_handler(
    action: str = "",
    url: str = "",
    selector: str = "",
    text: str = "",
    script: str = "",
    timeout: int = 30,
) -> str:
    if not _HAS_PLAYWRIGHT:
        return f"Error: {_INSTALL_HINT}"

    if action == "close":
        _cleanup()
        return "Browser closed"

    try:
        page = _get_page()
    except Exception as e:
        return f"Error: failed to launch browser: {e}\n{_INSTALL_HINT}"

    timeout_ms = min(max(timeout, 1), 120) * 1000

    try:
        if action == "open":
            if not url:
                return "Error: url is required"
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            return f"Navigated to {url}\nTitle: {page.title()}"

        elif action == "click":
            if not selector:
                return "Error: selector is required"
            page.click(selector, timeout=timeout_ms)
            return f"Clicked {selector}"

        elif action == "fill":
            if not selector or not text:
                return "Error: both selector and text are required"
            page.fill(selector, text, timeout=timeout_ms)
            return f"Filled {selector} with '{text[:100]}{'...' if len(text) > 100 else ''}'"

        elif action == "html":
            html = page.content()
            from html.parser import HTMLParser

            class _BodyExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._in_body = False
                    self._parts = []

                def handle_starttag(self, tag, attrs):
                    if tag == "body":
                        self._in_body = True

                def handle_endtag(self, tag):
                    if tag == "body":
                        self._in_body = False

                def handle_data(self, data):
                    if self._in_body:
                        self._parts.append(data)

            extractor = _BodyExtractor()
            extractor.feed(html)
            body_text = "".join(extractor._parts)

            raw = body_text if body_text else html[:5000]
            if len(raw) > 5000:
                raw = raw[:5000] + "\n... (truncated)"
            return f"Page HTML:\n{raw}"

        elif action == "text":
            text_content = page.inner_text("body")
            if len(text_content) > 5000:
                text_content = text_content[:5000] + "\n... (truncated)"
            return f"Page text:\n{text_content}"

        elif action == "title":
            return f"Title: {page.title()}\nURL: {page.url}"

        elif action == "evaluate":
            if not script:
                return "Error: script is required"
            result = page.evaluate(script)
            return f"Result:\n{json.dumps(result, ensure_ascii=False, indent=2)[:3000]}"

        elif action == "screenshot":
            dest = Path(text or "screenshot.png")
            dest.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(dest), full_page=False)
            return f"Screenshot saved to {dest.resolve()}"

        else:
            return (
                f"Unknown action: {action}. Supported: open, click, fill, html, "
                "text, title, evaluate, screenshot, close"
            )

    except Exception as e:
        err = str(e)[:500]
        return f"Browser error ({action}): {err}"
