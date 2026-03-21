from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any


PROFILE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
DEFAULT_TIMEOUT = 60.0
DEFAULT_TEMPERATURE = 0.7


def _settings_path(workspace_root: str) -> Path:
    root = Path(workspace_root)
    settings_dir = root / "workspace_data" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "llm_profiles.json"


def _default_payload() -> dict[str, Any]:
    return {
        "active_profile_id": "",
        "profiles": [],
    }


def _normalize_profile_id(value: str) -> str:
    candidate = (value or "").strip()
    if candidate and PROFILE_ID_RE.fullmatch(candidate):
        return candidate
    generated = re.sub(r"[^a-zA-Z0-9_-]+", "-", candidate).strip("-").lower()
    if generated and PROFILE_ID_RE.fullmatch(generated):
        return generated
    return f"profile_{uuid.uuid4().hex[:8]}"


def _validate_profile(raw: dict[str, Any]) -> dict[str, Any]:
    label = str(raw.get("label") or raw.get("name") or "").strip()
    model = str(raw.get("model") or "").strip()
    base_url = str(raw.get("base_url") or "").strip()
    api_key = str(raw.get("api_key") or "").strip()
    profile_id = _normalize_profile_id(str(raw.get("id") or label or model or ""))
    timeout_seconds = float(raw.get("timeout_seconds") or DEFAULT_TIMEOUT)
    temperature = float(raw.get("temperature") or DEFAULT_TEMPERATURE)
    force_json_output = bool(raw.get("force_json_output", True))

    if not label:
        raise ValueError("配置名称不能为空")
    if not model:
        raise ValueError("模型名不能为空")
    if not base_url:
        raise ValueError("接入地址不能为空")

    return {
        "id": profile_id,
        "label": label,
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "timeout_seconds": timeout_seconds,
        "temperature": temperature,
        "force_json_output": force_json_output,
    }


def load_llm_settings(workspace_root: str) -> dict[str, Any]:
    path = _settings_path(workspace_root)
    if not path.exists():
        payload = _default_payload()
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        payload = _default_payload()
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    profiles: list[dict[str, Any]] = []
    for item in raw.get("profiles", []):
        if isinstance(item, dict):
            try:
                profiles.append(_validate_profile(item))
            except ValueError:
                continue

    active_profile_id = str(raw.get("active_profile_id") or "").strip()
    if active_profile_id and not any(profile["id"] == active_profile_id for profile in profiles):
        active_profile_id = ""

    payload = {
        "active_profile_id": active_profile_id,
        "profiles": profiles,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def save_llm_settings(workspace_root: str, payload: dict[str, Any]) -> dict[str, Any]:
    path = _settings_path(workspace_root)
    normalized = {
        "active_profile_id": str(payload.get("active_profile_id") or "").strip(),
        "profiles": [_validate_profile(profile) for profile in payload.get("profiles", [])],
    }
    if normalized["active_profile_id"] and not any(
        profile["id"] == normalized["active_profile_id"] for profile in normalized["profiles"]
    ):
        normalized["active_profile_id"] = ""
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def upsert_llm_profile(workspace_root: str, profile: dict[str, Any]) -> dict[str, Any]:
    payload = load_llm_settings(workspace_root)
    normalized = _validate_profile(profile)
    existing = [item for item in payload["profiles"] if item["id"] != normalized["id"]]
    existing.append(normalized)
    existing.sort(key=lambda item: item["label"].lower())
    payload["profiles"] = existing
    if not payload["active_profile_id"]:
        payload["active_profile_id"] = normalized["id"]
    return save_llm_settings(workspace_root, payload)


def delete_llm_profile(workspace_root: str, profile_id: str) -> dict[str, Any]:
    target_id = str(profile_id or "").strip()
    payload = load_llm_settings(workspace_root)
    payload["profiles"] = [item for item in payload["profiles"] if item["id"] != target_id]
    if payload["active_profile_id"] == target_id:
        payload["active_profile_id"] = payload["profiles"][0]["id"] if payload["profiles"] else ""
    return save_llm_settings(workspace_root, payload)


def activate_llm_profile(workspace_root: str, profile_id: str) -> dict[str, Any]:
    target_id = str(profile_id or "").strip()
    payload = load_llm_settings(workspace_root)
    if target_id and not any(item["id"] == target_id for item in payload["profiles"]):
        raise ValueError("找不到要激活的模型配置")
    payload["active_profile_id"] = target_id
    return save_llm_settings(workspace_root, payload)


def get_active_llm_profile(workspace_root: str) -> dict[str, Any] | None:
    payload = load_llm_settings(workspace_root)
    active_profile_id = payload.get("active_profile_id") or ""
    if not active_profile_id:
        return None
    for profile in payload["profiles"]:
        if profile["id"] == active_profile_id:
            return profile
    return None
