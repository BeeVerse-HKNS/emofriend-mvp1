from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any


_OLLAMA_BASE_URL = "http://localhost:11434"
_RAG_SERVER_URL = "http://localhost:11435"
_HEALTH_CHECK_TIMEOUT = 5
_BEEVERSE_MODEL_NAME = "beeverse"
_QWEN3_MODEL_PATTERN = re.compile(r"^qwen3", re.IGNORECASE)
_DEFAULT_PROJECT_ROOT = Path(r"d:\My_Code_Projects\Harnessing")
_KB_SEARCH_DIRS = [
    "docs/knowledge-base",
    "data",
]


class ModelHealthCheck:

    def check_ollama_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{_OLLAMA_BASE_URL}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=_HEALTH_CHECK_TIMEOUT) as resp:
                return resp.status == 200
        except Exception:
            return False

    def check_rag_server_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{_RAG_SERVER_URL}/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=_HEALTH_CHECK_TIMEOUT) as resp:
                return resp.status == 200
        except Exception:
            return False

    def check_model_exists(self, model_name: str) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return False
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if parts and parts[0] == model_name:
                    return True
            return False
        except Exception:
            return False

    def get_vram_usage(self) -> float:
        try:
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=utilization.memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return 0.0
            lines = result.stdout.strip().split("\n")
            if not lines:
                return 0.0
            usages = []
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        usages.append(float(line))
                    except ValueError:
                        continue
            if not usages:
                return 0.0
            return max(usages) / 100.0
        except Exception:
            return 0.0

    def get_response_time(self, url: str) -> float:
        try:
            start = time.monotonic()
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=_HEALTH_CHECK_TIMEOUT) as _:
                pass
            return time.monotonic() - start
        except Exception:
            return -1.0

    def full_health_check(self) -> dict[str, Any]:
        ollama_available = self.check_ollama_available()
        rag_available = self.check_rag_server_available()
        beeverse_available = self.check_model_exists(_BEEVERSE_MODEL_NAME)
        vram_usage = self.get_vram_usage()
        ollama_response_time = (
            self.get_response_time(f"{_OLLAMA_BASE_URL}/api/tags")
            if ollama_available
            else -1.0
        )
        return {
            "ollama_available": ollama_available,
            "rag_available": rag_available,
            "beeverse_available": beeverse_available,
            "vram_usage": vram_usage,
            "ollama_response_time": ollama_response_time,
        }


class GracefulDegradation:

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or _DEFAULT_PROJECT_ROOT
        self._health = ModelHealthCheck()

    def select_model_tier(self, task_type: str) -> str:
        ollama_available = self._health.check_ollama_available()
        if ollama_available:
            if self._health.check_model_exists(_BEEVERSE_MODEL_NAME):
                return "LOCAL_BEEVERSE"
            if self._check_qwen3_exists():
                return "LOCAL_QWEN3"
        return "KB_DRIVEN"

    def should_use_cloud(self) -> bool:
        return os.environ.get("OLLAMA_CLOUD_ENABLED", "").lower() == "true"

    def get_kb_driven_response(self, query: str) -> str:
        results: list[str] = []
        query_lower = query.lower()
        query_terms = set(re.findall(r"\w+", query_lower))

        for rel_dir in _KB_SEARCH_DIRS:
            search_dir = self._project_root / rel_dir
            if not search_dir.exists():
                continue
            for file_path in sorted(glob.glob(str(search_dir / "**" / "*.md"), recursive=True)):
                try:
                    content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                content_lower = content.lower()
                content_terms = set(re.findall(r"\w+", content_lower))
                overlap = query_terms & content_terms
                if overlap:
                    best_paragraph = self._extract_best_paragraph(content, query_terms)
                    if best_paragraph:
                        results.append(
                            f"[{Path(file_path).relative_to(self._project_root)}] {best_paragraph}"
                        )

        if not results:
            return f"[KB_DRIVEN] No knowledge base match found for: {query}"

        results.sort(key=lambda r: len(set(re.findall(r"\w+", r.lower())) & query_terms), reverse=True)
        return "\n---\n".join(results[:5])

    def _check_qwen3_exists(self) -> bool:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return False
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if parts and _QWEN3_MODEL_PATTERN.match(parts[0]):
                    return True
            return False
        except Exception:
            return False

    def _extract_best_paragraph(self, content: str, query_terms: set[str]) -> str:
        paragraphs = content.split("\n\n")
        best_para = ""
        best_score = 0
        for para in paragraphs:
            para_stripped = para.strip()
            if not para_stripped or len(para_stripped) < 20:
                continue
            para_terms = set(re.findall(r"\w+", para_stripped.lower()))
            score = len(para_terms & query_terms)
            if score > best_score:
                best_score = score
                best_para = para_stripped
        return best_para


class LocalFirstModelStrategy:

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or _DEFAULT_PROJECT_ROOT
        self._health = ModelHealthCheck()
        self._degradation = GracefulDegradation(self._project_root)

    def resolve_model(self, task_type: str) -> dict[str, Any]:
        tier = self._degradation.select_model_tier(task_type)
        ollama_available = self._health.check_ollama_available()
        vram_usage = self._health.get_vram_usage()

        if tier == "LOCAL_BEEVERSE":
            return {
                "model_tier": "LOCAL_BEEVERSE",
                "model_name": _BEEVERSE_MODEL_NAME,
                "base_url": _OLLAMA_BASE_URL,
                "available": ollama_available,
                "vram_usage": vram_usage,
            }

        if tier == "LOCAL_QWEN3":
            qwen3_model = self._find_qwen3_model()
            return {
                "model_tier": "LOCAL_QWEN3",
                "model_name": qwen3_model,
                "base_url": _OLLAMA_BASE_URL,
                "available": ollama_available,
                "vram_usage": vram_usage,
            }

        if tier == "KB_DRIVEN" and not self._degradation.should_use_cloud():
            return {
                "model_tier": "KB_DRIVEN",
                "model_name": "knowledge_base",
                "base_url": "",
                "available": True,
                "vram_usage": vram_usage,
            }

        if self._degradation.should_use_cloud():
            return {
                "model_tier": "CLOUD_FALLBACK",
                "model_name": os.environ.get("HARNESSING_LLM_MODEL", ""),
                "base_url": os.environ.get("HARNESSING_LLM_API_BASE", ""),
                "available": bool(os.environ.get("HARNESSING_LLM_API_KEY", "")),
                "vram_usage": vram_usage,
            }

        return {
            "model_tier": "KB_DRIVEN",
            "model_name": "knowledge_base",
            "base_url": "",
            "available": True,
            "vram_usage": vram_usage,
        }

    def execute_with_fallback(self, task_type: str, prompt: str) -> dict[str, Any]:
        resolved = self.resolve_model(task_type)
        tier = resolved["model_tier"]

        if tier == "LOCAL_BEEVERSE":
            result = self._try_local_model(_BEEVERSE_MODEL_NAME, prompt)
            if result["success"]:
                return {**resolved, "response": result["content"], "fallback_used": False}
            degraded_tier = self._degradation.select_model_tier(task_type + "_fallback")
            if degraded_tier == "LOCAL_QWEN3":
                qwen3_model = self._find_qwen3_model()
                fallback_result = self._try_local_model(qwen3_model, prompt)
                if fallback_result["success"]:
                    return {
                        **resolved,
                        "model_tier": "LOCAL_QWEN3",
                        "model_name": qwen3_model,
                        "response": fallback_result["content"],
                        "fallback_used": True,
                    }
            kb_response = self._degradation.get_kb_driven_response(prompt)
            return {
                **resolved,
                "model_tier": "KB_DRIVEN",
                "model_name": "knowledge_base",
                "response": kb_response,
                "fallback_used": True,
            }

        if tier == "LOCAL_QWEN3":
            result = self._try_local_model(resolved["model_name"], prompt)
            if result["success"]:
                return {**resolved, "response": result["content"], "fallback_used": False}
            kb_response = self._degradation.get_kb_driven_response(prompt)
            return {
                **resolved,
                "model_tier": "KB_DRIVEN",
                "model_name": "knowledge_base",
                "response": kb_response,
                "fallback_used": True,
            }

        if tier == "KB_DRIVEN":
            kb_response = self._degradation.get_kb_driven_response(prompt)
            return {**resolved, "response": kb_response, "fallback_used": False}

        if tier == "CLOUD_FALLBACK":
            return {**resolved, "response": "[CLOUD_FALLBACK] Cloud execution not implemented in local-first mode", "fallback_used": False}

        return {**resolved, "response": "", "fallback_used": False}

    def get_status(self) -> dict[str, Any]:
        health = self._health.full_health_check()
        cloud_enabled = self._degradation.should_use_cloud()
        return {
            "ollama_available": health["ollama_available"],
            "rag_available": health["rag_available"],
            "beeverse_available": health["beeverse_available"],
            "vram_usage": health["vram_usage"],
            "ollama_response_time": health["ollama_response_time"],
            "cloud_enabled": cloud_enabled,
            "default_tier": self._degradation.select_model_tier("general"),
        }

    def _try_local_model(self, model_name: str, prompt: str) -> dict[str, Any]:
        try:
            payload = json.dumps({
                "model": model_name,
                "prompt": prompt,
                "stream": False,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{_OLLAMA_BASE_URL}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "content": body.get("response", "")}
        except Exception:
            return {"success": False, "content": ""}

    def _find_qwen3_model(self) -> str:
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    parts = line.split()
                    if parts and _QWEN3_MODEL_PATTERN.match(parts[0]):
                        return parts[0]
        except Exception:
            pass
        return "qwen3:8b"
