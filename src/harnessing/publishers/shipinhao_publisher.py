from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

_BASE_URL = "https://channels.weixin.qq.com"
_DASHBOARD_URL = f"{_BASE_URL}/platform/dashboard"
_UPLOAD_URL = f"{_BASE_URL}/platform/post/create"
_MAX_TITLE_LENGTH = 30

_LOGIN_INDICATOR_SELECTORS = [
    "[data-testid='header-user-avatar']",
    ".header-user-info",
    ".user-avatar",
    ".account-info",
    "[class*='user-avatar']",
    "[class*='header-user']",
]

_UPLOAD_AREA_SELECTORS = [
    "[data-testid='upload-area']",
    ".upload-area",
    ".video-upload",
    "[class*='upload'] input[type='file']",
    "input[type='file']",
]

_TITLE_SELECTORS = [
    "[data-testid='title-input']",
    "input[placeholder*='标题']",
    "input[placeholder*='title']",
    ".title-input input",
    "[class*='title'] input",
]

_DESCRIPTION_SELECTORS = [
    "[data-testid='description-input']",
    "textarea[placeholder*='描述']",
    "textarea[placeholder*='description']",
    ".description-input textarea",
    "[class*='desc'] textarea",
]

_PUBLISH_BUTTON_SELECTORS = [
    "[data-testid='publish-button']",
    "button:has-text('发布')",
    "button:has-text('发表')",
    "button:has-text('Publish')",
    "[class*='publish'] button",
]

_SUCCESS_INDICATOR_SELECTORS = [
    "[data-testid='publish-success']",
    ".success-icon",
    "[class*='success']",
    "text=发布成功",
    "text=已发布",
]

_PROGRESS_SELECTORS = [
    "[data-testid='upload-progress']",
    ".upload-progress",
    ".progress-bar",
    "[class*='progress']",
    "[class*='uploading']",
]


class ShipinhaoPublisher:
    def __init__(self) -> None:
        self._cookie = os.getenv("SHIPINHAO_COOKIE", "")
        self.headless = True
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def _ensure_playwright(self) -> None:
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("playwright is not installed. Run: pip install playwright && playwright install chromium")

    def _parse_cookie_string(self, cookie_str: str) -> list[dict]:
        cookies = []
        if not cookie_str:
            return cookies
        domain = urlparse(_BASE_URL).netloc
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/",
            })
        return cookies

    def _find_element(self, selectors: list[str], timeout: int = 10000):
        for selector in selectors:
            try:
                el = self._page.wait_for_selector(selector, timeout=timeout)
                if el:
                    return el
            except Exception:
                continue
        return None

    def login(self, cookie: str | None = None) -> bool:
        self._ensure_playwright()

        cookie_value = cookie or self._cookie
        if not cookie_value:
            logger.error("no_cookie_provided")
            return False

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            )

            parsed_cookies = self._parse_cookie_string(cookie_value)
            self._context.add_cookies(parsed_cookies)

            self._page = self._context.new_page()
            self._page.goto(_DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_timeout(3000)

            login_element = self._find_element(_LOGIN_INDICATOR_SELECTORS, timeout=10000)
            if login_element:
                logger.info("login_successful")
                return True

            logger.error("login_failed_no_indicator")
            return False

        except PlaywrightTimeoutError:
            logger.error("login_timeout")
            return False
        except Exception as e:
            logger.error("login_error", error=str(e))
            return False

    def publish_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> dict:
        self._ensure_playwright()

        if not self._page:
            return {"success": False, "url": "", "error": "not_logged_in"}

        video_file = Path(video_path)
        if not video_file.exists():
            return {"success": False, "url": "", "error": f"video_file_not_found: {video_path}"}

        try:
            self._page.goto(_UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_timeout(2000)

            upload_input = self._find_element(_UPLOAD_AREA_SELECTORS, timeout=10000)
            if not upload_input:
                file_inputs = self._page.query_selector_all("input[type='file']")
                upload_input = file_inputs[0] if file_inputs else None

            if not upload_input:
                return {"success": False, "url": "", "error": "upload_area_not_found"}

            upload_input.set_input_files(str(video_file.resolve()))
            logger.info("video_upload_started", path=str(video_path))

            upload_complete = False
            max_wait = 300
            for _ in range(max_wait):
                progress_el = self._find_element(_PROGRESS_SELECTORS, timeout=2000)
                if not progress_el:
                    upload_complete = True
                    break
                try:
                    is_visible = progress_el.is_visible()
                    if not is_visible:
                        upload_complete = True
                        break
                except Exception:
                    upload_complete = True
                    break
                self._page.wait_for_timeout(1000)

            if not upload_complete:
                return {"success": False, "url": "", "error": "upload_timeout"}

            logger.info("video_upload_complete")
            self._page.wait_for_timeout(2000)

            truncated_title = title[:_MAX_TITLE_LENGTH]
            title_input = self._find_element(_TITLE_SELECTORS, timeout=10000)
            if not title_input:
                return {"success": False, "url": "", "error": "title_input_not_found"}

            title_input.fill(truncated_title)
            logger.info("title_filled", title=truncated_title)

            if description:
                desc_input = self._find_element(_DESCRIPTION_SELECTORS, timeout=5000)
                if desc_input:
                    desc_input.fill(description)
                    logger.info("description_filled")

            if tags:
                self._add_tags(tags)

            publish_btn = self._find_element(_PUBLISH_BUTTON_SELECTORS, timeout=10000)
            if not publish_btn:
                return {"success": False, "url": "", "error": "publish_button_not_found"}

            publish_btn.click()
            logger.info("publish_button_clicked")

            success_el = self._find_element(_SUCCESS_INDICATOR_SELECTORS, timeout=30000)
            if not success_el:
                return {"success": False, "url": "", "error": "publish_success_not_confirmed"}

            current_url = self._page.url
            logger.info("video_published", url=current_url)
            return {"success": True, "url": current_url, "error": ""}

        except PlaywrightTimeoutError:
            logger.error("publish_timeout")
            return {"success": False, "url": "", "error": "playwright_timeout"}
        except FileNotFoundError as e:
            logger.error("file_error", error=str(e))
            return {"success": False, "url": "", "error": str(e)}
        except Exception as e:
            logger.error("publish_error", error=str(e))
            return {"success": False, "url": "", "error": str(e)}

    def _add_tags(self, tags: list[str]) -> None:
        tag_input_selectors = [
            "[data-testid='tag-input']",
            "input[placeholder*='标签']",
            "input[placeholder*='tag']",
            "[class*='tag'] input",
        ]
        tag_input = self._find_element(tag_input_selectors, timeout=3000)
        if not tag_input:
            logger.warning("tag_input_not_found")
            return

        for tag in tags:
            try:
                tag_input.fill(tag)
                tag_input.press("Enter")
                self._page.wait_for_timeout(500)
            except Exception:
                logger.warning("tag_add_failed", tag=tag)

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
        except Exception as e:
            logger.error("close_error", error=str(e))
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
