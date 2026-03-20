# DM Agent v0

This directory contains a minimal Game Master agent built on top of LangGraph without modifying the LangGraph library itself.

## What this version does

- Loads or bootstraps a world under `workspace_data/worlds/<world_id>/world_Info`
- Reads `world_Info/npcs/*.json` and keeps NPC files in sync with turn results
- Classifies one player action into a soul-style action type
- Decides whether the turn needs a roll based on the three-condition rule
- Resolves a `d20 < threshold` check when required
- Applies lightweight target-aware NPC resistance and attitude updates
- Applies hidden reputation updates with goodwill / notoriety tier linkage
- Requests structured JSON narration from an OpenAI-compatible LLM when configured
- Validates the JSON response locally and falls back to deterministic template narration on failure
- Preserves an internal five-part narrative structure while showing players a more immersive heading-free response
- Supports single-turn CLI, interactive multi-turn CLI, and a browser-based chat UI
- Writes the result back to `world.json`, `player_profile.json`, `player.md`, NPC files, and `session_log.txt`

## Layout

```text
apps/dm_agent/
  state.py
  dice.py
  memory_store.py
  rules.py
  prompts.py
  llm_client.py
  nodes.py
  graph.py
  main.py
  web_server.py
  web/
    index.html
    style.css
    app.js
```

## Run one turn

```bash
python apps/dm_agent/main.py --world demo --input "我尝试说服旅店老板给我一个安静的房间"
```

To inspect the full graph state:

```bash
python apps/dm_agent/main.py --world demo --input "我偷偷调查楼上的脚印" --dump-state
```

## Run interactive session

```bash
python apps/dm_agent/main.py --world campaign_01 --interactive
```

Interactive commands:

- `/help` show help
- `/state` show a short summary of the current world and player state
- `/dump` print the most recent full state as JSON
- `/exit` end the session

## Run the Web UI

Start the local web server:

```bash
python apps/dm_agent/web_server.py --host 127.0.0.1 --port 8787
```

Then open [http://127.0.0.1:8787](http://127.0.0.1:8787) in your browser.

The UI currently includes:

- a tavern-style chat surface for turn-by-turn play
- world load / create controls with local world suggestions
- a live sidebar for player stats, reputation, factions, NPC state, and recent events
- local fallback behavior when the LLM is not configured or returns invalid JSON

## LLM configuration

This project uses an OpenAI-compatible chat completions API.

Required environment variables:

- `DM_LLM_BASE_URL` or `OPENAI_BASE_URL`
- `DM_LLM_MODEL` or `OPENAI_MODEL`

Optional environment variables:

- `DM_LLM_API_KEY` or `OPENAI_API_KEY`
- `DM_LLM_TIMEOUT` (default `30`)
- `DM_LLM_TEMPERATURE` (default `0.7`)
- `DM_LLM_JSON_MODE` (default `on`; set to `off` only if your provider rejects `response_format`)

Example in `cmd`:

```cmd
set DM_LLM_BASE_URL=https://api.siliconflow.cn/v1
set DM_LLM_MODEL=deepseek-ai/DeepSeek-V3.2
set DM_LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
set DM_LLM_JSON_MODE=on
set DM_LLM_TIMEOUT=60
python apps/dm_agent/web_server.py --host 127.0.0.1 --port 8787
```

Example in PowerShell:

```powershell
$env:DM_LLM_BASE_URL = "https://api.openai.com/v1"
$env:DM_LLM_MODEL = "gpt-4.1-mini"
$env:DM_LLM_API_KEY = "<your-key>"
python apps/dm_agent/web_server.py --host 127.0.0.1 --port 8787
```

## Current limitations

- NPC resistance is target-aware but still uses a lightweight local model
- The LLM must return a strict five-field JSON object; invalid JSON is rejected and falls back to the template
- World consequences are still lightweight summaries, not deep faction simulation
- The Web UI is a local single-user surface; it does not yet support multiplayer sessions or auth

## Next recommended step

Replace the remaining lightweight pieces with:

- richer NPC stat models and explicit resistance fields for all important NPCs
- deeper world and faction updates
- player creation flow and world import compatible with your Soul documents
- automated regression tests for social, threat, and no-roll narrative paths
- a persistent conversation history panel in the Web UI
