#!/usr/bin/env python3
"""
MessageGateway — Multi-Platform Message Gateway for Harnessing

支援多平台訊息發送，遵循零外部依賴優先原則。

平台優先級：
| 平台 | 優先級 | 整合方式 |
|------|--------|---------|
| 本地 CLI | P0 | 零外部依賴 |
| Web UI | P0 | FastAPI + WebSocket |
| 微信/企業微信 | P1 | HermesAgent 風格 |
| Slack/Discord | P1 | Webhook API |
| 飛書/釘釘 | P2 | 企業 API |

遵循零外部依賴原則，P0 功能使用標準庫實現
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import threading
import queue
import time
from abc import ABC, abstractmethod


class Platform(Enum):
    CLI = "cli"
    WEB_UI = "web_ui"
    WECHAT = "wechat"
    ENTERPRISE_WECHAT = "enterprise_wechat"
    SLACK = "slack"
    DISCORD = "discord"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"


class MessagePriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class PlatformPriority(Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"


@dataclass
class Message:
    content: str
    title: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    platform: Optional[Platform] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    message_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "title": self.title,
            "priority": self.priority.value,
            "platform": self.platform.value if self.platform else None,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "message_id": self.message_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            content=data["content"],
            title=data.get("title"),
            priority=MessagePriority(data.get("priority", "normal")),
            platform=Platform(data["platform"]) if data.get("platform") else None,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            message_id=data.get("message_id"),
        )


@dataclass
class SendResult:
    success: bool
    platform: Platform
    message_id: Optional[str] = None
    error: Optional[str] = None
    response_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform.value,
            "message_id": self.message_id,
            "error": self.error,
            "response_data": self.response_data,
            "timestamp": self.timestamp,
        }


class PlatformAdapter(ABC):
    @abstractmethod
    def send(self, message: Message) -> SendResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_platform(self) -> Platform:
        pass

    @abstractmethod
    def get_priority(self) -> PlatformPriority:
        pass


class MessageFormatter:
    PLATFORM_LIMITS = {
        Platform.CLI: None,
        Platform.WEB_UI: None,
        Platform.WECHAT: 4096,
        Platform.ENTERPRISE_WECHAT: 4096,
        Platform.SLACK: 40000,
        Platform.DISCORD: 2000,
        Platform.FEISHU: 30000,
        Platform.DINGTALK: 20000,
    }

    PLATFORM_MARKDOWN_SUPPORT = {
        Platform.CLI: False,
        Platform.WEB_UI: True,
        Platform.WECHAT: False,
        Platform.ENTERPRISE_WECHAT: True,
        Platform.SLACK: True,
        Platform.DISCORD: True,
        Platform.FEISHU: True,
        Platform.DINGTALK: True,
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def format(self, message: Message, platform: Platform) -> Message:
        formatted = Message(
            content=message.content,
            title=message.title,
            priority=message.priority,
            platform=platform,
            metadata=message.metadata.copy(),
            created_at=message.created_at,
            message_id=message.message_id,
        )
        formatted.content = self._truncate(formatted.content, platform)
        formatted.content = self._convert_markdown(formatted.content, platform)
        return formatted

    def _truncate(self, content: str, platform: Platform) -> str:
        limit = self.PLATFORM_LIMITS.get(platform)
        if limit and len(content) > limit:
            return content[: limit - 3] + "..."
        return content

    def _convert_markdown(self, content: str, platform: Platform) -> str:
        if self.PLATFORM_MARKDOWN_SUPPORT.get(platform, False):
            return content
        return self._strip_markdown(content)

    def _strip_markdown(self, content: str) -> str:
        import re
        content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)
        content = re.sub(r"\*(.+?)\*", r"\1", content)
        content = re.sub(r"`(.+?)`", r"\1", content)
        content = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```", ""), content)
        content = re.sub(r"#+\s*", "", content)
        content = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", content)
        return content

    def format_for_broadcast(self, message: Message, platforms: List[Platform]) -> Dict[Platform, Message]:
        return {platform: self.format(message, platform) for platform in platforms}


class CLIAdapter(PlatformAdapter):
    def __init__(self, output_handler: Optional[Callable[[str], None]] = None):
        self.logger = logging.getLogger(__name__)
        self.output_handler = output_handler or self._default_output
        self._available = True

    def _default_output(self, text: str) -> None:
        print(text)

    def send(self, message: Message) -> SendResult:
        try:
            output = self._format_output(message)
            self.output_handler(output)
            return SendResult(
                success=True,
                platform=self.get_platform(),
                message_id=f"cli_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            )
        except Exception as e:
            self.logger.error(f"CLI send failed: {e}")
            return SendResult(
                success=False,
                platform=self.get_platform(),
                error=str(e),
            )

    def _format_output(self, message: Message) -> str:
        parts = []
        if message.title:
            parts.append(f"[{message.title}]")
        parts.append(message.content)
        if message.priority == MessagePriority.HIGH:
            parts.insert(0, "⚠️ HIGH PRIORITY")
        elif message.priority == MessagePriority.CRITICAL:
            parts.insert(0, "🚨 CRITICAL")
        return "\n".join(parts)

    def is_available(self) -> bool:
        return self._available

    def get_platform(self) -> Platform:
        return Platform.CLI

    def get_priority(self) -> PlatformPriority:
        return PlatformPriority.P0


class WebUIAdapter(PlatformAdapter):
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self._available = True
        self._connected_clients: List[Any] = []
        self._message_queue: queue.Queue = queue.Queue()
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        self._app: Optional[Any] = None

    def start_server(self) -> bool:
        try:
            import uvicorn
            from fastapi import FastAPI, WebSocket, WebSocketDisconnect
            from fastapi.responses import HTMLResponse

            app = FastAPI(title="MessageGateway Web UI")

            @app.get("/")
            async def root():
                return HTMLResponse(self._get_html_page())

            @app.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket):
                await websocket.accept()
                self._connected_clients.append(websocket)
                try:
                    while True:
                        data = await websocket.receive_text()
                        if data == "ping":
                            await websocket.send_json({"type": "pong"})
                except WebSocketDisconnect:
                    self._connected_clients.remove(websocket)

            @app.get("/messages")
            async def get_messages():
                messages = []
                while not self._message_queue.empty():
                    messages.append(self._message_queue.get())
                return {"messages": messages}

            self._app = app
            self._running = True
            self._server_thread = threading.Thread(
                target=lambda: uvicorn.run(app, host=self.host, port=self.port, log_level="warning"),
                daemon=True,
            )
            self._server_thread.start()
            self.logger.info(f"Web UI server started on http://{self.host}:{self.port}")
            return True
        except ImportError:
            self.logger.warning("FastAPI/uvicorn not installed, Web UI unavailable")
            self._available = False
            return False

    def stop_server(self) -> None:
        self._running = False
        self._available = False

    def _get_html_page(self) -> str:
        return """<!DOCTYPE html>
<html>
<head>
    <title>MessageGateway</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        #messages { border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: auto; }
        .message { margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee; }
        .high { background: #fff3cd; }
        .critical { background: #f8d7da; }
    </style>
</head>
<body>
    <h1>MessageGateway</h1>
    <div id="messages"></div>
    <script>
        const ws = new WebSocket(`ws://${location.host}/ws`);
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                const div = document.createElement('div');
                div.className = 'message ' + (data.priority || 'normal');
                div.textContent = data.content;
                document.getElementById('messages').appendChild(div);
            }
        };
    </script>
</body>
</html>"""

    async def _broadcast(self, message: Message) -> None:
        import asyncio
        data = json.dumps({"type": "message", **message.to_dict()})
        for client in self._connected_clients[:]:
            try:
                await client.send_text(data)
            except Exception:
                self._connected_clients.remove(client)

    def send(self, message: Message) -> SendResult:
        if not self._available:
            return SendResult(
                success=False,
                platform=self.get_platform(),
                error="Web UI not available (FastAPI/uvicorn not installed)",
            )
        try:
            self._message_queue.put(message.to_dict())
            return SendResult(
                success=True,
                platform=self.get_platform(),
                message_id=f"web_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            )
        except Exception as e:
            self.logger.error(f"Web UI send failed: {e}")
            return SendResult(
                success=False,
                platform=self.get_platform(),
                error=str(e),
            )

    def is_available(self) -> bool:
        return self._available

    def get_platform(self) -> Platform:
        return Platform.WEB_UI

    def get_priority(self) -> PlatformPriority:
        return PlatformPriority.P0


class StubPlatformAdapter(PlatformAdapter):
    """降級適配器 - 記錄請求但不發送，用於未配置平台"""
    
    def __init__(self, platform: Platform, priority: PlatformPriority = PlatformPriority.P1):
        self.logger = logging.getLogger(__name__)
        self._platform = platform
        self._priority = priority
        self._available = True
        self._message_log: List[Dict[str, Any]] = []
    
    def send(self, message: Message) -> SendResult:
        self._message_log.append({
            "timestamp": datetime.now().isoformat(),
            "message": message.to_dict()
        })
        self.logger.info(f"[STUB] Would send to {self._platform.value}: {message.title or message.content[:50]}")
        return SendResult(
            success=True,
            platform=self._platform,
            message_id=f"stub_{self._platform.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            response_data={"stub": True, "platform": self._platform.value, "logged": True}
        )
    
    def is_available(self) -> bool:
        return self._available
    
    def get_platform(self) -> Platform:
        return self._platform
    
    def get_priority(self) -> PlatformPriority:
        return self._priority
    
    def get_logged_messages(self) -> List[Dict[str, Any]]:
        return self._message_log.copy()


class WeChatAdapter(PlatformAdapter):
    def __init__(self, webhook_url: Optional[str] = None, corp_id: Optional[str] = None, secret: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.webhook_url = webhook_url
        self.corp_id = corp_id
        self.secret = secret
        self._available = bool(webhook_url or (corp_id and secret))

    def send(self, message: Message) -> SendResult:
        if not self._available:
            return SendResult(
                success=False,
                platform=self.get_platform(),
                error="WeChat not configured (webhook_url or corp_id+secret required)",
            )
        self.logger.info(f"WeChat send (stub): {message.title or 'No title'}")
        return SendResult(
            success=True,
            platform=self.get_platform(),
            message_id=f"wechat_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            response_data={"stub": True, "message": "WeChat integration not implemented"},
        )

    def is_available(self) -> bool:
        return self._available

    def get_platform(self) -> Platform:
        return Platform.WECHAT

    def get_priority(self) -> PlatformPriority:
        return PlatformPriority.P1


class SlackAdapter(PlatformAdapter):
    def __init__(self, webhook_url: Optional[str] = None, bot_token: Optional[str] = None, channel: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.webhook_url = webhook_url
        self.bot_token = bot_token
        self.channel = channel
        self._available = bool(webhook_url or bot_token)

    def send(self, message: Message) -> SendResult:
        if not self._available:
            return SendResult(
                success=False,
                platform=self.get_platform(),
                error="Slack not configured (webhook_url or bot_token required)",
            )
        self.logger.info(f"Slack send (stub): {message.title or 'No title'}")
        return SendResult(
            success=True,
            platform=self.get_platform(),
            message_id=f"slack_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            response_data={"stub": True, "message": "Slack integration not implemented"},
        )

    def is_available(self) -> bool:
        return self._available

    def get_platform(self) -> Platform:
        return Platform.SLACK

    def get_priority(self) -> PlatformPriority:
        return PlatformPriority.P1


class FeishuAdapter(PlatformAdapter):
    def __init__(self, webhook_url: Optional[str] = None, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.webhook_url = webhook_url
        self.app_id = app_id
        self.app_secret = app_secret
        self._available = bool(webhook_url or (app_id and app_secret))

    def send(self, message: Message) -> SendResult:
        if not self._available:
            return SendResult(
                success=False,
                platform=self.get_platform(),
                error="Feishu not configured (webhook_url or app_id+app_secret required)",
            )
        self.logger.info(f"Feishu send (stub): {message.title or 'No title'}")
        return SendResult(
            success=True,
            platform=self.get_platform(),
            message_id=f"feishu_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            response_data={"stub": True, "message": "Feishu integration not implemented"},
        )

    def is_available(self) -> bool:
        return self._available

    def get_platform(self) -> Platform:
        return Platform.FEISHU

    def get_priority(self) -> PlatformPriority:
        return PlatformPriority.P2


class MessageGateway:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.formatter = MessageFormatter()
        self._adapters: Dict[Platform, PlatformAdapter] = {}
        self._rate_limits: Dict[Platform, Dict[str, Any]] = {}
        self._retry_config = {
            "max_retries": 3,
            "backoff_base": 2,
            "initial_delay": 1,
        }
        self._lock = threading.Lock()
        self._init_adapters()

    def _init_adapters(self) -> None:
        self._adapters[Platform.CLI] = CLIAdapter()
        web_config = self.config.get("web_ui", {})
        self._adapters[Platform.WEB_UI] = WebUIAdapter(
            host=web_config.get("host", "127.0.0.1"),
            port=web_config.get("port", 8080),
        )
        wechat_config = self.config.get("wechat", {})
        wechat_adapter = WeChatAdapter(
            webhook_url=wechat_config.get("webhook_url"),
            corp_id=wechat_config.get("corp_id"),
            secret=wechat_config.get("secret"),
        )
        if not wechat_adapter.is_available():
            wechat_adapter = StubPlatformAdapter(Platform.WECHAT, PlatformPriority.P1)
        self._adapters[Platform.WECHAT] = wechat_adapter
        
        slack_config = self.config.get("slack", {})
        slack_adapter = SlackAdapter(
            webhook_url=slack_config.get("webhook_url"),
            bot_token=slack_config.get("bot_token"),
            channel=slack_config.get("channel"),
        )
        if not slack_adapter.is_available():
            slack_adapter = StubPlatformAdapter(Platform.SLACK, PlatformPriority.P1)
        self._adapters[Platform.SLACK] = slack_adapter
        
        feishu_config = self.config.get("feishu", {})
        feishu_adapter = FeishuAdapter(
            webhook_url=feishu_config.get("webhook_url"),
            app_id=feishu_config.get("app_id"),
            app_secret=feishu_config.get("app_secret"),
        )
        if not feishu_adapter.is_available():
            feishu_adapter = StubPlatformAdapter(Platform.FEISHU, PlatformPriority.P2)
        self._adapters[Platform.FEISHU] = feishu_adapter
        self._init_rate_limits()

    def _init_rate_limits(self) -> None:
        self._rate_limits = {
            Platform.CLI: {"limit": None, "window": None},
            Platform.WEB_UI: {"limit": None, "window": None},
            Platform.WECHAT: {"limit": 20, "window": 60},
            Platform.ENTERPRISE_WECHAT: {"limit": 20, "window": 60},
            Platform.SLACK: {"limit": 1, "window": 1},
            Platform.DISCORD: {"limit": 5, "window": 2},
            Platform.FEISHU: {"limit": 20, "window": 60},
            Platform.DINGTALK: {"limit": 20, "window": 60},
        }

    def register_adapter(self, adapter: PlatformAdapter) -> None:
        with self._lock:
            self._adapters[adapter.get_platform()] = adapter

    def get_adapter(self, platform: Platform) -> Optional[PlatformAdapter]:
        return self._adapters.get(platform)

    def get_available_platforms(self) -> List[Platform]:
        return [p for p, a in self._adapters.items() if a.is_available()]

    def get_platforms_by_priority(self, priority: PlatformPriority) -> List[Platform]:
        return [p for p, a in self._adapters.items() if a.get_priority() == priority and a.is_available()]

    def send(self, message: Message, platform: Platform) -> SendResult:
        adapter = self._adapters.get(platform)
        if not adapter:
            return SendResult(
                success=False,
                platform=platform,
                error=f"No adapter registered for {platform.value}",
            )
        if not adapter.is_available():
            return SendResult(
                success=False,
                platform=platform,
                error=f"Adapter for {platform.value} is not available",
            )
        formatted = self.formatter.format(message, platform)
        return self._send_with_retry(adapter, formatted)

    def _send_with_retry(self, adapter: PlatformAdapter, message: Message) -> SendResult:
        max_retries = self._retry_config["max_retries"]
        backoff_base = self._retry_config["backoff_base"]
        initial_delay = self._retry_config["initial_delay"]
        last_result = None
        for attempt in range(max_retries + 1):
            result = adapter.send(message)
            if result.success:
                return result
            last_result = result
            if attempt < max_retries:
                delay = initial_delay * (backoff_base**attempt)
                self.logger.warning(
                    f"Send failed (attempt {attempt + 1}/{max_retries}), retrying in {delay}s: {result.error}"
                )
                time.sleep(delay)
        return SendResult(
            success=False,
            platform=last_result.platform if last_result else adapter.get_platform(),
            error=f"Max retries ({max_retries}) exceeded: {last_result.error if last_result else 'Unknown error'}",
        )

    def broadcast(self, message: Message, platforms: Optional[List[Platform]] = None) -> Dict[Platform, SendResult]:
        if platforms is None:
            platforms = self.get_available_platforms()
        results = {}
        for platform in platforms:
            results[platform] = self.send(message, platform)
        return results

    def broadcast_p0(self, message: Message) -> Dict[Platform, SendResult]:
        platforms = self.get_platforms_by_priority(PlatformPriority.P0)
        return self.broadcast(message, platforms)

    def broadcast_all(self, message: Message) -> Dict[Platform, SendResult]:
        return self.broadcast(message)

    def start_web_server(self) -> bool:
        adapter = self._adapters.get(Platform.WEB_UI)
        if isinstance(adapter, WebUIAdapter):
            return adapter.start_server()
        return False

    def stop_web_server(self) -> None:
        adapter = self._adapters.get(Platform.WEB_UI)
        if isinstance(adapter, WebUIAdapter):
            adapter.stop_server()

    def create_message(
        self,
        content: str,
        title: Optional[str] = None,
        priority: Union[str, MessagePriority] = MessagePriority.NORMAL,
        **metadata: Any,
    ) -> Message:
        if isinstance(priority, str):
            priority = MessagePriority(priority)
        return Message(
            content=content,
            title=title,
            priority=priority,
            metadata=metadata,
        )

    def notify(self, content: str, title: Optional[str] = None, priority: Union[str, MessagePriority] = MessagePriority.NORMAL) -> Dict[Platform, SendResult]:
        message = self.create_message(content, title, priority)
        return self.broadcast_p0(message)

    def alert(self, content: str, title: Optional[str] = None) -> Dict[Platform, SendResult]:
        return self.notify(content, title, MessagePriority.HIGH)

    def critical(self, content: str, title: Optional[str] = None) -> Dict[Platform, SendResult]:
        return self.notify(content, title, MessagePriority.CRITICAL)


def create_gateway(config: Optional[Dict[str, Any]] = None) -> MessageGateway:
    return MessageGateway(config)
