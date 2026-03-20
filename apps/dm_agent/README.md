# DM Agent v0

This directory contains a minimal single-turn Game Master agent built on top of
LangGraph without modifying the LangGraph library itself.

## What this version does

- Loads or bootstraps a world under `workspace_data/worlds/<world_id>/world_Info`
- Reads `world_Info/npcs/*.json` and keeps NPC files in sync with turn results
- Classifies one player action into a soul-style action type
- Decides whether the turn needs a roll based on the three-condition rule
- Resolves a `d20 < threshold` check when required
- Applies lightweight target-aware NPC resistance and attitude updates
- Applies hidden reputation updates with goodwill / notoriety tier linkage
- Writes the result back to `world.json`, `player_profile.json`, `player.md`,
  NPC files, and `session_log.txt`
- Produces a five-part narrative response

## Layout

```text
apps/dm_agent/
  state.py
  dice.py
  memory_store.py
  rules.py
  nodes.py
  graph.py
  main.py
```

## Run

You need a Python environment. If full LangGraph dependencies are not installed,
`graph.py` will automatically fall back to the local lightweight runtime in
`runtime_graph.py`.

```bash
python apps/dm_agent/main.py --world demo --input "我尝试说服旅店老板给我一个安静的房间"
```

To inspect the full graph state:

```bash
python apps/dm_agent/main.py --world demo --input "我偷偷调查楼上的脚印" --dump-state
```

## Current limitations

- NPC resistance is target-aware but still uses a lightweight local model
- Narrative output is template-based and not yet LLM-rendered
- World consequences are still lightweight summaries, not deep faction simulation

## Next recommended step

Replace the remaining lightweight pieces with:

- richer NPC stat models and explicit resistance fields for all important NPCs
- LLM-backed narrative rendering
- deeper world and faction updates
- player creation flow and world import compatible with your Soul documents
