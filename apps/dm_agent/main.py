from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LANGGRAPH_SRC = REPO_ROOT / "libs" / "langgraph"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(LANGGRAPH_SRC) not in sys.path:
    sys.path.insert(0, str(LANGGRAPH_SRC))

from apps.dm_agent.graph import build_graph
from apps.dm_agent.memory_store import get_world_paths, load_world_memory


HELP_TEXT = """Available commands:
/help   Show this help text
/state  Show a short summary of the current world and player state
/dump   Print the latest full state as JSON
/exit   End the current session
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single-turn GM agent graph.")
    parser.add_argument(
        "--world",
        default="demo",
        help="World identifier stored under workspace_data/worlds/<world_id>.",
    )
    parser.add_argument(
        "--input",
        help="Player action to resolve for one turn.",
    )
    parser.add_argument(
        "--dump-state",
        action="store_true",
        help="Print the full LangGraph output state as JSON.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start an interactive multi-turn CLI session.",
    )
    return parser.parse_args()


def run_turn(graph, world_id: str, player_input: str) -> dict:
    return graph.invoke(
        {
            "world_id": world_id,
            "workspace_root": str(REPO_ROOT),
            "player_input": player_input,
        }
    )


def print_state_summary(world_id: str) -> None:
    memory = load_world_memory(str(REPO_ROOT), world_id)
    world = memory["world"]
    player = memory["player_profile"]
    npc_records = memory["npc_records"]
    recent_events = world.get("recent_events", [])

    print(f"[world] {world.get('world_name', 'Unknown')} @ {world.get('current_city', 'Unknown')}")
    print(f"[player] {player.get('name', 'Unknown')} at {player.get('status', {}).get('location', 'Unknown')}")
    print(
        "[reputation] "
        f"notoriety={player.get('hidden_reputation', {}).get('notoriety', 0)} "
        f"goodwill={player.get('hidden_reputation', {}).get('goodwill', 0)} "
        f"heroic={player.get('hidden_reputation', {}).get('heroic', 0)}"
    )
    if npc_records:
        print("[npc]")
        for npc_id, payload in npc_records.items():
            print(
                f"  - {payload.get('name', npc_id)}: "
                f"status={payload.get('current_status', 'unknown')}, "
                f"favorability={payload.get('favorability', 0)}, "
                f"relation={payload.get('relationship_to_player', 'unknown')}"
            )
    if recent_events:
        print("[recent]")
        for item in recent_events[-3:]:
            print(f"  - {item}")


def run_interactive_session(world_id: str) -> int:
    graph = build_graph()
    latest_result: dict | None = None
    paths = get_world_paths(str(REPO_ROOT), world_id)

    print(f"Starting DM interactive session for world '{world_id}'.")
    print(f"World files live under: {paths['world_dir']}")
    print("Type your action and press Enter.")
    print(HELP_TEXT.rstrip())

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession closed.")
            return 0

        if not raw:
            continue
        if raw == "/help":
            print(HELP_TEXT.rstrip())
            continue
        if raw == "/exit":
            print("Session closed.")
            return 0
        if raw == "/state":
            print_state_summary(world_id)
            continue
        if raw == "/dump":
            if latest_result is None:
                print("No turn has been executed yet.")
            else:
                print(json.dumps(latest_result, ensure_ascii=False, indent=2))
            continue

        latest_result = run_turn(graph, world_id, raw)
        print()
        print(latest_result["final_response"])
        print()
        print(
            f"[meta] source={latest_result.get('narrative_source', 'unknown')} "
            f"action_type={latest_result.get('action_type', 'unknown')} "
            f"roll={latest_result.get('roll', {}).get('result', 'unknown')}"
        )
        if latest_result.get("narrative_error"):
            print(f"[meta] narrative_error={latest_result['narrative_error']}")


def main() -> int:
    args = parse_args()
    if args.interactive:
        return run_interactive_session(args.world)

    if not args.input:
        raise SystemExit("--input is required unless --interactive is used.")

    graph = build_graph()
    result = run_turn(graph, args.world, args.input)

    if args.dump_state:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["final_response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
