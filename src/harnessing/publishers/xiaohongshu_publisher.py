from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

_BASE_URL = "https://creator.xiaohongshu.com"
_PUBLISH_URL = f"{_BASE_URL}/publish/publish"
_DASHBOARD_URL = f"{_BASE_URL}/creator/home"
_MAX_TITLE_LENGTH = 20
_MAX_CONTENT_LENGTH = 1000

_LOGIN_INDICATOR_SELECTORS = [
    "[class*='user-info']",
    "[class*='avatar']",
    "[class*='nickname']",
    "[data-testid='user-avatar']",
    ".user-name",
]

_UPLOAD_SELECTORS = [
    "[class*='upload'] input[type='file']",
    "input[type='file'][accept*='image']",
    "[class*='image-upload'] input[type='file']",
    "[class*='upload-btn'] input[type='file']",
]

_TITLE_SELECTORS = [
    "[class*='title'] input",
    "[class*='title'] textarea",
    "input[placeholder*='标题']",
    "input[placeholder*='title']",
    "#title-input",
]

_CONTENT_SELECTORS = [
    "[class*='content'] [contenteditable='true']",
    "[class*='editor'] [contenteditable='true']",
    "[class*='desc'] [contenteditable='true']",
    "[class*='content'] textarea",
    ".ql-editor",
]

_TAG_INPUT_SELECTORS = [
    "[class*='tag'] input",
    "[class*='topic'] input",
    "input[placeholder*='标签']",
    "input[placeholder*='话题']",
    "input[placeholder*='tag']",
    "input[placeholder*='topic']",
]

_PUBLISH_SELECTORS = [
    "button[class*='publish']",
    "button[class*='submit']",
    "[class*='publish-btn']",
    "[data-testid='publish-button']",
    "button:has-text('发布')",
    "button:has-text('Publish')",
]

_SUCCESS_INDICATORS = [
    "[class*='success']",
    "[class*='published']",
    "[class*='complete']",
    "text=发布成功",
    "text=已发布",
]


class XiaohongshuPublisher:
    def __init__(self) -> None:
        self.headless = True
        self.cookie = None
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        env_path = Path(__file__).resolve().parents[4] / ".env"
        if _DOTENV_AVAILABLE:
            load_dotenv(env_path)
        self.cookie = os.getenv("XIAOHONGSHU_COOKIE", "")

    def _ensure_playwright(self) -> None:
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("playwright is not installed. Install with: pip install playwright && playwright install chromium")

    def _start_browser(self) -> None:
        self._ensure_playwright()
        if self._playwright is not None:
            return
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        )
        self._page = self._context.new_page()

    def _inject_cookie(self, cookie_str: str) -> None:
        if not cookie_str or not self._context:
            return
        cookies = []
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".xiaohongshu.com",
                "path": "/",
            })
        if cookies:
            self._context.add_cookies(cookies)

    def _wait_for_selector(self, selectors: list[str], timeout: int = 10000):
        for selector in selectors:
            try:
                el = self._page.wait_for_selector(selector, timeout=timeout)
                if el:
                    return el
            except PlaywrightTimeoutError:
                continue
        return None

    def _click_selector(self, selectors: list[str], timeout: int = 10000) -> bool:
        for selector in selectors:
            try:
                el = self._page.wait_for_selector(selector, timeout=timeout)
                if el:
                    el.click()
                    return True
            except PlaywrightTimeoutError:
                continue
        return False

    def login(self, cookie: str | None = None) -> bool:
        self._ensure_playwright()
        try:
            self._start_browser()
            cookie_value = cookie or self.cookie
            if not cookie_value:
                return False

            self._inject_cookie(cookie_value)

            self._page.goto(_DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_timeout(3000)

            indicator = self._wait_for_selector(_LOGIN_INDICATOR_SELECTORS, timeout=10000)
            if indicator:
                return True

            current_url = self._page.url
            if "login" in current_url.lower():
                return False

            return False
        except PlaywrightTimeoutError:
            return False
        except Exception:
            return False

    def publish_note(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        images: list[str] | None = None,
    ) -> dict:
        self._ensure_playwright()
        result = {"success": False, "url": None, "error": None}

        try:
            self._start_browser()

            self._page.goto(_PUBLISH_URL, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_timeout(2000)

            if images:
                upload_input = self._wait_for_selector(_UPLOAD_SELECTORS, timeout=10000)
                if upload_input:
                    for image_path in images:
                        if not Path(image_path).exists():
                            result["error"] = f"Image not found: {image_path}"
                            return result
                    upload_input.set_input_files(images)
                    self._page.wait_for_timeout(3000)

            title_el = self._wait_for_selector(_TITLE_SELECTORS, timeout=10000)
            if not title_el:
                result["error"] = "Title input not found"
                return result
            truncated_title = title[:_MAX_TITLE_LENGTH]
            title_el.fill(truncated_title)
            self._page.wait_for_timeout(500)

            content_el = self._wait_for_selector(_CONTENT_SELECTORS, timeout=10000)
            if not content_el:
                result["error"] = "Content editor not found"
                return result
            truncated_content = content[:_MAX_CONTENT_LENGTH]
            content_el.fill(truncated_content)
            self._page.wait_for_timeout(500)

            if tags:
                tag_input = self._wait_for_selector(_TAG_INPUT_SELECTORS, timeout=5000)
                if tag_input:
                    for tag in tags:
                        tag_input.fill(tag)
                        self._page.keyboard.press("Enter")
                        self._page.wait_for_timeout(500)

            publish_clicked = self._click_selector(_PUBLISH_SELECTORS, timeout=10000)
            if not publish_clicked:
                result["error"] = "Publish button not found or not clickable"
                return result

            success_el = self._wait_for_selector(_SUCCESS_INDICATORS, timeout=15000)
            if success_el:
                result["success"] = True
                result["url"] = self._page.url
            else:
                result["error"] = "Publish success indicator not detected"

            return result
        except PlaywrightTimeoutError as e:
            result["error"] = f"Timeout: {e}"
            return result
        except FileNotFoundError as e:
            result["error"] = f"File not found: {e}"
            return result
        except Exception as e:
            result["error"] = f"Unexpected error: {e}"
            return result

    def close(self) -> None:
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
