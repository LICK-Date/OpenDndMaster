from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
LANGGRAPH_SRC = REPO_ROOT / "libs" / "langgraph"
WEB_ROOT = Path(__file__).resolve().parent / "web"
INVALID_WORLD_ID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
RESERVED_WORLD_IDS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(LANGGRAPH_SRC) not in sys.path:
    sys.path.insert(0, str(LANGGRAPH_SRC))

from apps.dm_agent.graph import build_graph
from apps.dm_agent.memory_store import append_session_transcript, get_world_paths, load_session_transcript, load_world_memory
from apps.dm_agent.settings_store import (
    activate_llm_profile,
    delete_llm_profile,
    get_active_llm_profile,
    load_llm_settings,
    upsert_llm_profile,
)


def validate_world_id(world_id: str) -> str:
    candidate = (world_id or "").strip()
    if not candidate:
        raise ValueError("世界编号不能为空")
    if len(candidate) > 64:
        raise ValueError("世界编号长度不能超过 64 个字符")
    if candidate != candidate.rstrip(" ."):
        raise ValueError("世界编号不能以空格或句点结尾")
    if INVALID_WORLD_ID_CHARS_RE.search(candidate):
        raise ValueError("世界编号不能包含 < > : \" / \\ | ? * 或控制字符")
    if candidate.upper() in RESERVED_WORLD_IDS:
        raise ValueError("世界编号不能使用 Windows 保留名称")
    return candidate


def run_turn(graph, world_id: str, player_input: str) -> dict:
    active_llm_profile = get_active_llm_profile(str(REPO_ROOT))
    return graph.invoke(
        {
            "world_id": world_id,
            "workspace_root": str(REPO_ROOT),
            "player_input": player_input,
            "llm_config": active_llm_profile or {},
        }
    )


def list_worlds() -> list[str]:
    worlds_dir = REPO_ROOT / "workspace_data" / "worlds"
    worlds_dir.mkdir(parents=True, exist_ok=True)
    return sorted([item.name for item in worlds_dir.iterdir() if item.is_dir()])


def delete_world(world_id: str) -> dict:
    world_id = validate_world_id(world_id)
    worlds = list_worlds()
    if world_id not in worlds:
        raise ValueError(f"世界“{world_id}”不存在")
    if len(worlds) <= 1:
        raise ValueError("至少要保留一个世界")

    paths = get_world_paths(str(REPO_ROOT), world_id)
    if not paths["world_dir"].exists():
        raise ValueError(f"世界“{world_id}”不存在")

    shutil.rmtree(paths["world_dir"])
    remaining = list_worlds()
    return {
        "deleted_world_id": world_id,
        "worlds": remaining,
        "fallback_world_id": remaining[0] if remaining else "",
    }


def build_world_summary(world_id: str) -> dict:
    memory = load_world_memory(str(REPO_ROOT), world_id)
    world = memory["world"]
    player = memory["player_profile"]
    npc_records = memory["npc_records"]
    paths = get_world_paths(str(REPO_ROOT), world_id)
    return {
        "world_id": world_id,
        "world": {
            "name": world.get("world_name", world_id),
            "city": world.get("current_city", "未知地点"),
            "tone": world.get("tone", "未知基调"),
            "factions": world.get("factions", []),
            "recent_events": world.get("recent_events", [])[-8:],
            "path": str(paths["world_dir"]),
        },
        "player": {
            "name": player.get("name", "未命名"),
            "background": player.get("background", ""),
            "location": player.get("status", {}).get("location", "未知地点"),
            "injury": player.get("status", {}).get("injury", "无"),
            "wanted": player.get("status", {}).get("wanted", False),
            "attributes": player.get("attributes", {}),
            "reputation": player.get("hidden_reputation", {}),
            "equipment": player.get("equipment", []),
        },
        "transcript": load_session_transcript(str(REPO_ROOT), world_id),
        "npcs": [
            {
                "id": npc_id,
                "name": payload.get("name", npc_id),
                "profession": payload.get("profession", ""),
                "status": payload.get("current_status", "未知"),
                "city": payload.get("current_city", "未知地点"),
                "favorability": payload.get("favorability", 0),
                "relationship": payload.get("relationship_to_player", ""),
                "appearance": payload.get("appearance", ""),
            }
            for npc_id, payload in npc_records.items()
        ],
    }


class DMRequestHandler(BaseHTTPRequestHandler):
    graph = build_graph()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/worlds":
                self._send_json({"worlds": list_worlds()})
                return
            if parsed.path == "/api/world":
                world_id = validate_world_id(parse_qs(parsed.query).get("world_id", ["demo"])[0])
                self._send_json(build_world_summary(world_id))
                return
            if parsed.path == "/api/settings/llm":
                self._send_json(load_llm_settings(str(REPO_ROOT)))
                return
            self._serve_static(parsed.path)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - defensive path for manual UI use
            self._send_json({"error": f"服务器错误：{exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        body = self._read_json_body()
        try:
            if parsed.path == "/api/turn":
                world_id = validate_world_id(body.get("world_id") or "demo")
                player_input = (body.get("input") or "").strip()
                if not player_input:
                    self._send_json({"error": "行动内容不能为空"}, status=HTTPStatus.BAD_REQUEST)
                    return
                result = run_turn(self.graph, world_id, player_input)
                memory = load_world_memory(str(REPO_ROOT), world_id)
                append_session_transcript(
                    str(REPO_ROOT),
                    world_id,
                    [
                        {
                            "kind": "player",
                            "speaker": memory["player_profile"].get("name", "未命名"),
                            "content": player_input,
                        },
                        {
                            "kind": "gm",
                            "speaker": "Dungeon Master",
                            "content": result.get("final_response", ""),
                        },
                    ],
                )
                summary = build_world_summary(world_id)
                self._send_json({"result": result, "summary": summary})
                return
            if parsed.path == "/api/worlds/create":
                world_id = validate_world_id(body.get("world_id") or "")
                summary = build_world_summary(world_id)
                self._send_json(summary, status=HTTPStatus.CREATED)
                return
            if parsed.path == "/api/worlds/delete":
                payload = delete_world(body.get("world_id") or "")
                self._send_json(payload)
                return
            if parsed.path == "/api/settings/llm/save":
                payload = upsert_llm_profile(str(REPO_ROOT), body.get("profile") or {})
                self._send_json(payload)
                return
            if parsed.path == "/api/settings/llm/delete":
                payload = delete_llm_profile(str(REPO_ROOT), body.get("profile_id") or "")
                self._send_json(payload)
                return
            if parsed.path == "/api/settings/llm/activate":
                payload = activate_llm_profile(str(REPO_ROOT), body.get("profile_id") or "")
                self._send_json(payload)
                return
            self._send_json({"error": "未找到接口"}, status=HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - defensive path for manual UI use
            self._send_json({"error": f"服务器错误：{exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self, path: str) -> None:
        relative = "/index.html" if path in {"/", ""} else path
        safe_name = relative.lstrip("/")
        file_path = (WEB_ROOT / safe_name).resolve()
        if not str(file_path).startswith(str(WEB_ROOT.resolve())) or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        content_type = self._guess_content_type(file_path.suffix)
        payload = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(encoded)

    def _guess_content_type(self, suffix: str) -> str:
        return {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }.get(suffix, "text/plain; charset=utf-8")

    def log_message(self, format: str, *args) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DM Agent web UI server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), DMRequestHandler)
    print(f"DM Agent UI available at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

