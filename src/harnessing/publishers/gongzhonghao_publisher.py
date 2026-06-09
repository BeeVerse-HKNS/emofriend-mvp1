#!/usr/bin/env python3
"""
GongzhonghaoPublisher — WeChat Official Account (公眾號) Article Publisher

Cookie-based authentication via Playwright browser automation.
Markdown-to-WeChat-HTML conversion with inline styles.
"""

from __future__ import annotations

import os
import re
import time
import logging
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout
except ImportError:
    sync_playwright = None
    Page = None
    Browser = None
    BrowserContext = None
    PlaywrightTimeout = Exception

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

_WECHAT_MP_URL = "https://mp.weixin.qq.com"
_ARTICLE_CREATE_URL = f"{_WECHAT_MP_URL}/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77"

_LOGIN_INDICATOR_SELECTORS = [
    "[data-testid='account_setting_item']",
    ".weui-desktop-account",
    "//div[contains(@class,'account_setting_item')]",
]

_ARTICLE_TITLE_SELECTORS = [
    "[data-testid='title']",
    "#title",
    ".article-title input",
    "//input[@id='title']",
]

_ARTICLE_CONTENT_SELECTORS = [
    "[data-testid='edui_body']",
    "#edui_body",
    ".edui-body-container",
    "//div[@id='edui_body']",
]

_COVER_UPLOAD_SELECTORS = [
    "[data-testid='cover-upload']",
    ".cover-upload input[type='file']",
    "//input[@type='file' and contains(@class,'cover')]",
]

_PUBLISH_BUTTON_SELECTORS = [
    "[data-testid='publish-btn']",
    ".weui-desktop-btn_primary",
    "//button[contains(@class,'weui-desktop-btn_primary')]",
]


class GongzhonghaoPublisher:

    def __init__(self) -> None:
        if load_dotenv is not None:
            load_dotenv(_ENV_PATH)
        self._cookie: str = os.getenv("WECHAT_OFFICIAL_ACCOUNT_COOKIE", "")
        self._headless: bool = True
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def login(self, cookie: Optional[str] = None) -> bool:
        if sync_playwright is None:
            logger.error("playwright is not installed")
            return False

        target_cookie = cookie or self._cookie
        if not target_cookie:
            logger.error("no cookie provided and WECHAT_OFFICIAL_ACCOUNT_COOKIE not set in .env")
            return False

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            self._context = self._browser.new_context()
            self._page = self._context.new_page()

            cookies = self._parse_cookie_string(target_cookie)
            self._context.add_cookies(cookies)

            self._page.goto(_WECHAT_MP_URL, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_load_state("networkidle", timeout=15000)

            for selector in _LOGIN_INDICATOR_SELECTORS:
                try:
                    self._page.wait_for_selector(selector, timeout=5000)
                    logger.info("login successful, indicator found: %s", selector)
                    return True
                except Exception:
                    continue

            self._take_screenshot("login_failure")
            logger.error("login failed: no logged-in indicator found")
            return False

        except PlaywrightTimeout as exc:
            self._take_screenshot("login_timeout")
            logger.error("login timeout: %s", exc)
            return False
        except Exception as exc:
            self._take_screenshot("login_error")
            logger.error("login error: %s", exc)
            return False

    def convert_markdown_to_wechat_html(self, md_content: str) -> str:
        html = md_content

        html = re.sub(
            r"^### (.+)$",
            r'<h3 style="font-size:16px;font-weight:bold;color:#333;margin:20px 0 10px 0;border-left:4px solid #1a73e8;padding-left:10px;">\1</h3>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^## (.+)$",
            r'<h2 style="font-size:18px;font-weight:bold;color:#222;margin:24px 0 12px 0;border-left:4px solid #1a73e8;padding-left:10px;">\1</h2>',
            html,
            flags=re.MULTILINE,
        )
        html = re.sub(
            r"^# (.+)$",
            r'<h1 style="font-size:22px;font-weight:bold;color:#111;margin:28px 0 14px 0;border-left:4px solid #1a73e8;padding-left:10px;">\1</h1>',
            html,
            flags=re.MULTILINE,
        )

        html = re.sub(
            r"```(\w*)\n([\s\S]*?)```",
            r'<pre style="background:#f6f8fa;border-radius:4px;padding:12px;overflow-x:auto;font-size:13px;line-height:1.6;"><code style="font-family:Consolas,Monaco,monospace;">\2</code></pre>',
            html,
        )

        html = re.sub(
            r"`([^`]+)`",
            r'<code style="background:#f0f0f0;padding:2px 4px;border-radius:3px;font-size:13px;font-family:Consolas,Monaco,monospace;">\1</code>',
            html,
        )

        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

        html = re.sub(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            r'<img src="\2" alt="\1" style="max-width:100%;height:auto;display:block;margin:10px 0;" />',
            html,
        )

        html = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" style="color:#1a73e8;text-decoration:none;">\1</a>',
            html,
        )

        lines = html.split("\n")
        processed: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                processed.append("")
                continue
            if stripped.startswith("<h") or stripped.startswith("<pre") or stripped.startswith("<img"):
                processed.append(stripped)
                continue
            if stripped.startswith("<"):
                processed.append(stripped)
                continue
            processed.append(
                f'<p style="font-size:15px;line-height:1.8;color:#333;margin:8px 0;">{stripped}</p>'
            )

        html = "\n".join(processed)

        html = re.sub(r"\n{3,}", "\n\n", html)

        ai_label = (
            '<p style="font-size:12px;color:#999;margin-top:30px;padding-top:10px;'
            'border-top:1px solid #eee;text-align:center;">'
            "此內容由 AI 輔助生成</p>"
        )
        html = html.rstrip() + "\n" + ai_label

        return html

    def publish_article(
        self,
        title: str,
        content_html: str,
        cover_image: Optional[str] = None,
    ) -> dict:
        if self._page is None:
            return {"success": False, "url": None, "error": "not logged in, call login() first"}

        try:
            self._page.goto(_ARTICLE_CREATE_URL, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_load_state("networkidle", timeout=15000)

            title_filled = False
            for selector in _ARTICLE_TITLE_SELECTORS:
                try:
                    el = self._page.wait_for_selector(selector, timeout=5000)
                    if el is not None:
                        el.fill(title)
                        title_filled = True
                        break
                except Exception:
                    continue

            if not title_filled:
                self._take_screenshot("title_not_found")
                return {"success": False, "url": None, "error": "could not locate title input"}

            content_filled = False
            for selector in _ARTICLE_CONTENT_SELECTORS:
                try:
                    el = self._page.wait_for_selector(selector, timeout=5000)
                    if el is not None:
                        el.evaluate("(node, html) => { node.innerHTML = html; }", content_html)
                        content_filled = True
                        break
                except Exception:
                    continue

            if not content_filled:
                self._take_screenshot("content_not_found")
                return {"success": False, "url": None, "error": "could not locate content editor"}

            if cover_image:
                uploaded = False
                for selector in _COVER_UPLOAD_SELECTORS:
                    try:
                        el = self._page.wait_for_selector(selector, timeout=5000)
                        if el is not None:
                            el.set_input_files(cover_image)
                            self._page.wait_for_load_state("networkidle", timeout=15000)
                            uploaded = True
                            break
                    except Exception:
                        continue
                if not uploaded:
                    logger.warning("cover image upload element not found, skipping cover")

            published = False
            for selector in _PUBLISH_BUTTON_SELECTORS:
                try:
                    el = self._page.wait_for_selector(selector, timeout=5000)
                    if el is not None:
                        el.click()
                        published = True
                        break
                except Exception:
                    continue

            if not published:
                self._take_screenshot("publish_button_not_found")
                return {"success": False, "url": None, "error": "could not locate publish button"}

            self._page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)

            current_url = self._page.url

            return {"success": True, "url": current_url, "error": None}

        except PlaywrightTimeout as exc:
            self._take_screenshot("publish_timeout")
            return {"success": False, "url": None, "error": f"timeout: {exc}"}
        except Exception as exc:
            self._take_screenshot("publish_error")
            return {"success": False, "url": None, "error": str(exc)}

    def close(self) -> None:
        try:
            if self._page is not None:
                self._page.close()
        except Exception:
            pass
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright is not None:
                self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def _take_screenshot(self, label: str) -> None:
        if self._page is None:
            return
        try:
            screenshot_dir = _PROJECT_ROOT / "data" / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            ts = int(time.time())
            path = screenshot_dir / f"gzh_{label}_{ts}.png"
            self._page.screenshot(path=str(path))
            logger.info("screenshot saved: %s", path)
        except Exception as exc:
            logger.warning("failed to take screenshot: %s", exc)

    @staticmethod
    def _parse_cookie_string(cookie_str: str) -> list[dict]:
        cookies: list[dict] = []
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            name, _, value = pair.partition("=")
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".qq.com",
                "path": "/",
            })
        return cookies
