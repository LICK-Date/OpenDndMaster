from apps.dm_agent.graph import build_graph
from apps.dm_agent.memory_store import ensure_world_exists, load_session_transcript, load_world_memory


def test_new_world_starts_blank_and_with_opening_prompt(tmp_path):
    ensure_world_exists(str(tmp_path), 'fresh_world')

    memory = load_world_memory(str(tmp_path), 'fresh_world')
    transcript = load_session_transcript(str(tmp_path), 'fresh_world')

    assert memory['world']['world_name'] == 'fresh_world'
    assert memory['world']['current_city'] == '尚未设定'
    assert memory['world']['factions'] == []
    assert memory['npc_index'] == []
    assert memory['npc_records'] == {}
    assert memory['player_profile']['name'] == '未命名'
    assert '角色尚未创建' in memory['player_profile']['background']
    assert memory['player_profile']['attributes'] == {
        'strength': None,
        'dexterity': None,
        'intelligence': None,
        'charisma': None,
        'constitution': None,
        'talent': None,
    }
    assert transcript[0]['kind'] == 'gm'
    assert '希望在什么样的世界里冒险' in transcript[0]['content']


def test_new_world_uses_world_id_as_default_world_name(tmp_path):
    ensure_world_exists(str(tmp_path), '超级棒棒糖')

    memory = load_world_memory(str(tmp_path), '超级棒棒糖')

    assert memory['world']['world_name'] == '超级棒棒糖'


def test_player_setup_input_updates_name_and_attributes(tmp_path):
    result = build_graph().invoke(
        {
            'world_id': 'setup_world',
            'workspace_root': str(tmp_path),
            'player_input': '我叫星璃，力量16，敏捷15，智力14，魅力13，体质12，天赋11。',
        }
    )

    memory = load_world_memory(str(tmp_path), 'setup_world')

    assert result['roll']['result'] == 'not_required'
    assert memory['player_profile']['name'] == '星璃'
    assert memory['player_profile']['attributes'] == {
        'strength': 16,
        'dexterity': 15,
        'intelligence': 14,
        'charisma': 13,
        'constitution': 12,
        'talent': 11,
    }
    assert '基础建卡' in memory['player_profile']['background']
