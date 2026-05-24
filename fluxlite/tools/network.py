"""Network tools — HTTP requests, file download, and web scraping."""

import json
import time as _time
from html.parser import HTMLParser
from pathlib import Path
import httpx


def http_request_handler(
    method: str = "GET",
    url: str = "",
    headers: str = "",
    body: str = "",
    timeout: int = 30,
) -> str:
    if not url:
        return "Error: url is required"

    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE", "HEAD", "PATCH"):
        return f"Error: unsupported method {method}"

    parsed_headers = _parse_headers(headers)
    if isinstance(parsed_headers, str):
        return parsed_headers
    timeout = min(max(timeout, 1), 120)

    try:
        start = _time.monotonic()
        with httpx.Client(timeout=httpx.Timeout(timeout), follow_redirects=True) as client:
            response = client.request(
                method=method,
                url=url,
                headers=parsed_headers or None,
                content=body if body else None,
            )
        elapsed = _time.monotonic() - start

        parts = [
            f"Status: {response.status_code}",
            f"Time: {elapsed:.2f}s",
            f"Size: {len(response.content)} bytes",
        ]

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = response.json()
                body_str = json.dumps(data, ensure_ascii=False, indent=2)
                if len(body_str) > 5000:
                    body_str = body_str[:5000] + "\n... (truncated)"
                parts.append(f"\nBody:\n{body_str}")
            except Exception:
                parts.append(f"\nBody:\n{response.text[:3000]}")
        else:
            text = response.text[:3000]
            if len(response.text) > 3000:
                text += "\n... (truncated)"
            if text:
                parts.append(f"\nBody:\n{text}")

        return "\n".join(parts)

    except httpx.TimeoutException:
        return f"Error: request timed out after {timeout}s"
    except httpx.ConnectError as e:
        return f"Error: connection failed: {e}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return f"Error: {e}"


def file_download_handler(url: str = "", path: str = "", timeout: int = 120) -> str:
    if not url:
        return "Error: url is required"

    timeout = min(max(timeout, 5), 600)

    try:
        with httpx.Client(timeout=httpx.Timeout(timeout), follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()

                disposition = resp.headers.get("content-disposition", "")
                suggested = ""
                if "filename=" in disposition:
                    suggested = disposition.split("filename=")[-1].strip(' "\'')

                if not path:
                    path = (
                        suggested
                        or Path(url.split("/")[-1].split("?")[0])
                        or "downloaded_file"
                    ).strip()

                dest = Path(path)
                dest.parent.mkdir(parents=True, exist_ok=True)

                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(8192):
                        f.write(chunk)
                        downloaded += len(chunk)

        size_str = (
            f"{downloaded / 1024:.1f} KB"
            if downloaded < 1024 * 1024
            else f"{downloaded / 1024 / 1024:.1f} MB"
        )
        return f"Downloaded {size_str} ({downloaded} bytes) to {dest.resolve()}"

    except httpx.TimeoutException:
        return f"Error: download timed out after {timeout}s"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} — {e}"
    except Exception as e:
        return f"Error: {e}"


class _TextExtractor(HTMLParser):

    def __init__(self):
        super().__init__()
        self._result = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._result.append(text)

    def get_text(self) -> str:
        return "\n".join(self._result)


class _LinkExtractor(HTMLParser):

    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = None
            text = ""
            for k, v in attrs:
                if k == "href":
                    href = v
            if href and href.strip() and not href.startswith(("#", "javascript:")):
                self.links.append((href, ""))


def _parse_headers(headers: str) -> dict | str:
    if not headers:
        return {}
    try:
        parsed = json.loads(headers)
        if not isinstance(parsed, dict):
            return "Error: headers must be a JSON object"
        return parsed
    except json.JSONDecodeError as e:
        return f"Error: invalid headers JSON: {e}"


def web_scrape_handler(
    url: str = "",
    extract: str = "text",
    selector: str = "",
    timeout: int = 30,
) -> str:
    if not url:
        return "Error: url is required"

    timeout = min(max(timeout, 5), 120)
    extract = extract.lower()

    try:
        start = _time.monotonic()
        with httpx.Client(timeout=httpx.Timeout(timeout), follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        elapsed = _time.monotonic() - start

        html = resp.text
        parts = [
            f"Status: {resp.status_code}",
            f"Time: {elapsed:.2f}s",
            f"Size: {len(html)} chars",
        ]

        if extract in ("raw", "all"):
            preview = html[:3000]
            if len(html) > 3000:
                preview += "\n... (truncated)"
            parts.append(f"\nHTML:\n{preview}")

        if extract in ("text", "all"):
            extractor = _TextExtractor()
            extractor.feed(html)
            text = extractor.get_text()
            if len(text) > 3000:
                text = text[:3000] + "\n... (truncated)"
            if text:
                parts.append(f"\nReadable text:\n{text}")
            else:
                parts.append("\n(no readable text extracted)")

        if extract in ("links", "all"):
            linker = _LinkExtractor()
            linker.feed(html)
            links = linker.links[:50]
            if links:
                parts.append(f"\nLinks ({len(links)} shown):")
                for href, label in links:
                    parts.append(f"  {href}")
            else:
                parts.append("\n(no links found)")

        return "\n".join(parts)

    except httpx.TimeoutException:
        return f"Error: request timed out after {timeout}s"
    except httpx.ConnectError as e:
        return f"Error: connection failed: {e}"
    except Exception as e:
        return f"Error: {e}"
