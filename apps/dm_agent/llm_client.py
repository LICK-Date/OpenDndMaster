from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from urllib import error, request


@dataclass
class LLMConfig:
    model: str
    base_url: str
    api_key: str
    timeout_seconds: float = 30.0
    temperature: float = 0.7
    force_json_output: bool = True


class LLMClientError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient | None":
        model = os.getenv("DM_LLM_MODEL") or os.getenv("OPENAI_MODEL") or ""
        base_url = os.getenv("DM_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or ""
        api_key = os.getenv("DM_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        timeout_value = os.getenv("DM_LLM_TIMEOUT") or "30"
        temperature_value = os.getenv("DM_LLM_TEMPERATURE") or "0.7"
        json_mode_value = (os.getenv("DM_LLM_JSON_MODE") or "on").strip().lower()

        if not model or not base_url:
            return None

        config = LLMConfig(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=float(timeout_value),
            temperature=float(temperature_value),
            force_json_output=json_mode_value not in {"off", "false", "0"},
        )
        return cls(config)

    def generate(self, messages: list[dict[str, str]]) -> str:
        endpoint = self._resolve_endpoint(self.config.base_url)
        payload: dict[str, object] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if self.config.force_json_output:
            payload["response_format"] = {"type": "json_object"}
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"HTTP {exc.code}: {detail}") from exc
        except (error.URLError, TimeoutError, socket.timeout) as exc:
            reason = getattr(exc, "reason", str(exc))
            raise LLMClientError(f"Network error: {reason}") from exc

        try:
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError("Invalid response shape from LLM provider") from exc

    @staticmethod
    def _resolve_endpoint(base_url: str) -> str:
        cleaned = base_url.rstrip("/")
        if cleaned.endswith("/chat/completions"):
            return cleaned
        return cleaned + "/chat/completions"
