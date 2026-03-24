from __future__ import annotations

from apps.dm_agent.llm_client import LLMClientError
from apps.dm_agent.memory_store import load_world_memory
from apps.dm_agent.nodes import render_narrative_node


class _BrokenClient:
    def generate(self, messages):
        raise LLMClientError('Network error: unavailable')


def test_render_narrative_returns_service_unavailable_when_llm_fails(tmp_path, monkeypatch):
    memory = load_world_memory(str(tmp_path), 'service_down_world')

    monkeypatch.setattr(
        'apps.dm_agent.nodes.OpenAICompatibleClient.from_mapping',
        lambda payload: _BrokenClient(),
    )
    monkeypatch.setattr(
        'apps.dm_agent.nodes.OpenAICompatibleClient.from_env',
        lambda: None,
    )

    result = render_narrative_node(
        {
            'world_id': 'service_down_world',
            'workspace_root': str(tmp_path),
            'player_input': '我尝试推开大门。',
            'memory': memory,
            'intent_summary': '测试意图',
            'target_npc_name': '',
            'roll': {
                'result': 'not_required',
                'summary': '测试摘要',
            },
            'consequences': ['测试后果'],
            'llm_config': {
                'model': 'demo-model',
                'base_url': 'http://demo.invalid/v1',
            },
        }
    )

    assert result['narrative_source'] == 'service_unavailable'
    assert result['narrative_error'] == '当前模型服务不可用'
    assert result['final_response'] == '当前模型服务不可用'
    assert result['narrative_sections'] == ['当前模型服务不可用']
