from __future__ import annotations

import os
import urllib.request
from enum import Enum
from typing import Any

import structlog
from litellm import completion

logger = structlog.get_logger()


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    ZHIPUAI = "zhipuai"
    SILICONFLOW = "siliconflow"
    BAIDU = "baidu"
    VOLCENGINE = "volcengine"
    GEMINI = "gemini"
    GROQ = "groq"


_PROVIDER_CONFIG: dict[LLMProvider, dict[str, Any]] = {
    LLMProvider.OLLAMA: {
        "model": "ollama/qwen3:8b",
        "api_base": "http://localhost:11434",
        "api_key_env": "",
        "priority": 0,
        "dual_region": False,
        "local_models": {
            "fast": "ollama/qwen3:4b",
            "standard": "ollama/qwen3:8b",
        },
    },
    LLMProvider.ZHIPUAI: {
        "model": "openai/glm-4-flash",
        "api_base": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPUAI_API_KEY",
        "priority": 1,
        "dual_region": True,
    },
    LLMProvider.SILICONFLOW: {
        "model": "openai/deepseek-ai/DeepSeek-V3",
        "api_base": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "priority": 2,
        "dual_region": True,
    },
    LLMProvider.VOLCENGINE: {
        "model": "openai/doubao-seed-1-6-lite-32k",
        "api_base": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_env": "VOLCENGINE_API_KEY",
        "priority": 3,
        "dual_region": True,
    },
    LLMProvider.BAIDU: {
        "model": "openai/ernie-speed-128k",
        "api_base": "https://qianfan.baidubce.com/v2",
        "api_key_env": "BAIDU_QIANFAN_API_KEY",
        "priority": 4,
        "dual_region": True,
    },
    LLMProvider.GEMINI: {
        "model": "gemini/gemini-2.0-flash",
        "api_base": "",
        "api_key_env": "GEMINI_API_KEY",
        "priority": 5,
        "dual_region": False,
    },
    LLMProvider.GROQ: {
        "model": "groq/llama-3.3-70b-versatile",
        "api_base": "",
        "api_key_env": "GROQ_API_KEY",
        "priority": 6,
        "dual_region": False,
    },
}


class LLMRouter:
    def __init__(self) -> None:
        self._available: list[LLMProvider] = []
        self._detect_providers()

    def _detect_providers(self) -> None:
        ollama_config = _PROVIDER_CONFIG[LLMProvider.OLLAMA]
        try:
            req = urllib.request.Request(
                f"{ollama_config['api_base']}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    self._available.append(LLMProvider.OLLAMA)
                    logger.info(
                        "llm_provider_detected",
                        provider=LLMProvider.OLLAMA.value,
                        model=ollama_config["model"],
                    )
        except Exception:
            logger.debug("ollama_not_available")

        for provider, config in _PROVIDER_CONFIG.items():
            if provider == LLMProvider.OLLAMA:
                continue
            api_key_env = config["api_key_env"]
            if not api_key_env:
                continue
            api_key = os.environ.get(api_key_env, "")
            if api_key:
                self._available.append(provider)
                logger.info(
                    "llm_provider_detected",
                    provider=provider.value,
                    model=config["model"],
                )

        override_model = os.environ.get("HARNESSING_LLM_MODEL", "")
        override_key = os.environ.get("HARNESSING_LLM_API_KEY", "")
        override_base = os.environ.get("HARNESSING_LLM_API_BASE", "")
        if override_model and override_key:
            logger.info(
                "llm_override_detected",
                model=override_model,
                api_base=override_base,
            )

        if not self._available and not override_model:
            logger.warning("no_llm_provider_available")

    @property
    def available_providers(self) -> list[LLMProvider]:
        return list(self._available)

    @property
    def is_ollama_available(self) -> bool:
        return LLMProvider.OLLAMA in self._available

    def _build_kwargs(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        provider: LLMProvider | None = None,
        temperature: float = 0.8,
        max_tokens: int = 4000,
        **extra: Any,
    ) -> dict[str, Any]:
        override_model = os.environ.get("HARNESSING_LLM_MODEL", "")
        override_key = os.environ.get("HARNESSING_LLM_API_KEY", "")
        override_base = os.environ.get("HARNESSING_LLM_API_BASE", "")

        if override_model and override_key:
            kwargs: dict[str, Any] = {
                "model": override_model,
                "messages": messages,
                "api_key": override_key,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if override_base and "openai/" in override_model:
                kwargs["api_base"] = override_base
            kwargs.update(extra)
            return kwargs

        if model:
            resolved_model = model
            api_key = None
            api_base = None
        elif provider and provider in _PROVIDER_CONFIG:
            config = _PROVIDER_CONFIG[provider]
            resolved_model = config["model"]
            api_key_env = config.get("api_key_env", "")
            api_key = os.environ.get(api_key_env, "") if api_key_env else ""
            api_base = config.get("api_base", "")
        elif self._available:
            best = self._available[0]
            config = _PROVIDER_CONFIG[best]
            resolved_model = config["model"]
            api_key_env = config.get("api_key_env", "")
            api_key = os.environ.get(api_key_env, "") if api_key_env else ""
            api_base = config.get("api_base", "")
        else:
            raise ValueError("No LLM provider available. Set an API key in .env")

        kwargs = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if api_base and ("openai/" in resolved_model or "ollama/" in resolved_model):
            kwargs["api_base"] = api_base
        kwargs.update(extra)
        return kwargs

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        provider: LLMProvider | None = None,
        temperature: float = 0.8,
        max_tokens: int = 4000,
        **extra: Any,
    ) -> str:
        kwargs = self._build_kwargs(
            messages, model, provider, temperature, max_tokens, **extra
        )
        model_name = kwargs["model"]

        try:
            response = completion(**kwargs)
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty content")
            logger.info(
                "llm_call_success",
                model=model_name,
                tokens=response.usage.total_tokens if response.usage else 0,
            )
            return content.strip()
        except Exception as e:
            logger.error("llm_call_failed", model=model_name, error=str(e))
            if self._available and len(self._available) > 1:
                return self._fallback_chat(
                    messages, model_name, temperature, max_tokens, **extra
                )
            raise

    def chat_local(
        self,
        messages: list[dict[str, str]],
        model_size: str = "standard",
        temperature: float = 0.8,
        max_tokens: int = 4000,
        **extra: Any,
    ) -> str:
        if not self.is_ollama_available:
            raise RuntimeError("Ollama is not available. Start Ollama service first.")
        config = _PROVIDER_CONFIG[LLMProvider.OLLAMA]
        local_models = config.get("local_models", {})
        model_name = local_models.get(model_size, config["model"])
        return self.chat(
            messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )

    def chat_with_model(
        self,
        messages: list[dict[str, str]],
        model_name: str,
        temperature: float = 0.8,
        max_tokens: int = 4000,
        **extra: Any,
    ) -> str:
        return self.chat(
            messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **extra,
        )

    def _fallback_chat(
        self,
        messages: list[dict[str, str]],
        failed_model: str,
        temperature: float,
        max_tokens: int,
        **extra: Any,
    ) -> str:
        for provider in self._available:
            config = _PROVIDER_CONFIG[provider]
            if config["model"] == failed_model:
                continue
            kwargs: dict[str, Any] = {
                "model": config["model"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            api_key_env = config.get("api_key_env", "")
            api_key = os.environ.get(api_key_env, "") if api_key_env else ""
            api_base = config.get("api_base", "")
            if api_key:
                kwargs["api_key"] = api_key
            if api_base and ("openai/" in config["model"] or "ollama/" in config["model"]):
                kwargs["api_base"] = api_base
            kwargs.update(extra)

            try:
                logger.info(
                    "llm_fallback_attempt",
                    from_model=failed_model,
                    to_model=config["model"],
                )
                response = completion(**kwargs)
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("LLM returned empty content")
                logger.info("llm_fallback_success", model=config["model"])
                return content.strip()
            except Exception as e:
                logger.warning("llm_fallback_failed", model=config["model"], error=str(e))
                continue

        raise RuntimeError("All LLM providers failed")

    def generate(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        provider: LLMProvider | None = None,
        temperature: float = 0.8,
        max_tokens: int = 4000,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(
            messages, model=model, provider=provider,
            temperature=temperature, max_tokens=max_tokens,
        )
