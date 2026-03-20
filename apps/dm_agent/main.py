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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single-turn GM agent graph.")
    parser.add_argument(
        "--world",
        default="demo",
        help="World identifier stored under workspace_data/worlds/<world_id>.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Player action to resolve for one turn.",
    )
    parser.add_argument(
        "--dump-state",
        action="store_true",
        help="Print the full LangGraph output state as JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    graph = build_graph()
    result = graph.invoke(
        {
            "world_id": args.world,
            "workspace_root": str(REPO_ROOT),
            "player_input": args.input,
        }
    )

    if args.dump_state:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["final_response"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
