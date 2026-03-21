const chatLog = document.querySelector('#chat-log');
const turnForm = document.querySelector('#turn-form');
const turnInput = document.querySelector('#turn-input');
const worldInput = document.querySelector('#world-id');
const worldSuggestions = document.querySelector('#world-suggestions');
const worldTitle = document.querySelector('#world-title');
const navWorldName = document.querySelector('#nav-world-name');
const sourcePill = document.querySelector('#source-pill');
const rollPill = document.querySelector('#roll-pill');
const statusLine = document.querySelector('#status-line');
const createWorldButton = document.querySelector('#create-world');
const createWorldForm = document.querySelector('#create-world-form');
const createWorldInput = document.querySelector('#create-world-input');
const cancelCreateWorldButton = document.querySelector('#cancel-create-world');
const sendTurnButton = document.querySelector('#send-turn');
const sessionList = document.querySelector('#session-list');
const worldArchivePanel = document.querySelector('#world-archive-panel');
const worldArchiveBody = document.querySelector('#world-archive-body');
const toggleWorldArchiveButton = document.querySelector('#toggle-world-archive');
const recentEventsPanel = document.querySelector('#recent-events-panel');
const recentEventsWrap = document.querySelector('#recent-events-wrap');
const toggleRecentEventsButton = document.querySelector('#toggle-recent-events');
const npcPanel = document.querySelector('#npc-panel');
const npcPanelBody = document.querySelector('#npc-panel-body');
const toggleNpcPanelButton = document.querySelector('#toggle-npc-panel');
const template = document.querySelector('#message-template');

const playerName = document.querySelector('#player-name');
const playerLocation = document.querySelector('#player-location');
const playerBackground = document.querySelector('#player-background');
const attributeGrid = document.querySelector('#attribute-grid');
const worldCity = document.querySelector('#world-city');
const worldTone = document.querySelector('#world-tone');
const factionRow = document.querySelector('#faction-row');
const npcList = document.querySelector('#npc-list');
const recentEvents = document.querySelector('#recent-events');

const openSettingsButton = document.querySelector('#open-settings-btn');
const importWorldButton = document.querySelector('#import-world-btn');
const exportWorldButton = document.querySelector('#export-world-btn');
const settingsModal = document.querySelector('#settings-modal');
const closeSettingsButton = document.querySelector('#close-settings-btn');
const settingsBackdrop = document.querySelector('[data-close-settings]');
const newLlmProfileButton = document.querySelector('#new-llm-profile-btn');
const llmProfileList = document.querySelector('#llm-profile-list');
const llmSettingsForm = document.querySelector('#llm-settings-form');
const llmProfileIdInput = document.querySelector('#llm-profile-id');
const llmProfileLabelInput = document.querySelector('#llm-profile-label');
const llmProfileModelInput = document.querySelector('#llm-profile-model');
const llmProfileBaseUrlInput = document.querySelector('#llm-profile-base-url');
const llmProfileApiKeyInput = document.querySelector('#llm-profile-api-key');
const llmProfileTimeoutInput = document.querySelector('#llm-profile-timeout');
const llmProfileTemperatureInput = document.querySelector('#llm-profile-temperature');
const llmProfileJsonInput = document.querySelector('#llm-profile-json');
const activateLlmProfileButton = document.querySelector('#activate-llm-profile-btn');
const deleteLlmProfileButton = document.querySelector('#delete-llm-profile-btn');
const settingsStatus = document.querySelector('#settings-status');

let latestState = null;
let worlds = [];
let activeWorldId = '';
let recentEventsExpanded = false;
let npcPanelExpanded = false;
let worldArchiveExpanded = true;
let llmSettings = { active_profile_id: '', profiles: [] };
let selectedLlmProfileId = '';

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function slugifyProfileId(value) {
  const normalized = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return normalized || `profile_${Date.now()}`;
}

function setCollapsibleState(panel, body, button, expanded) {
  if (!panel || !body || !button) {
    return;
  }
  panel.classList.toggle('collapsed', !expanded);
  panel.classList.toggle('expanded', expanded);
  body.hidden = !expanded;
  button.textContent = expanded ? '▾' : '▸';
  button.setAttribute('aria-expanded', expanded ? 'true' : 'false');
}

function setWorldArchiveExpanded(expanded) {
  worldArchiveExpanded = expanded;
  setCollapsibleState(worldArchivePanel, worldArchiveBody, toggleWorldArchiveButton, expanded);
}

function setRecentEventsExpanded(expanded) {
  recentEventsExpanded = expanded;
  setCollapsibleState(recentEventsPanel, recentEventsWrap, toggleRecentEventsButton, expanded);
}

function setNpcPanelExpanded(expanded) {
  npcPanelExpanded = expanded;
  setCollapsibleState(npcPanel, npcPanelBody, toggleNpcPanelButton, expanded);
}

function setAccordionPanel(panelKey) {
  setWorldArchiveExpanded(panelKey === 'archive');
  setNpcPanelExpanded(panelKey === 'npc');
  setRecentEventsExpanded(panelKey === 'recent');
}

function appendMessage(kind, speaker, content) {
  if (!template || !chatLog) {
    return;
  }
  const node = template.content.firstElementChild.cloneNode(true);
  node.classList.add(kind);
  node.querySelector('.speaker').textContent = speaker;
  node.querySelector('.content').textContent = content;
  chatLog.appendChild(node);
  requestAnimationFrame(() => {
    chatLog.scrollTop = chatLog.scrollHeight;

  });
}

function clearMessages() {
  if (!chatLog) {
    return;
  }
  chatLog.innerHTML = '';
  appendMessage('system', 'System', '壁炉重新被拨旺了一些。你可以从这里继续推进这段冒险。');
}

function renderTranscript(transcript = []) {
  if (!template || !chatLog) {
    return;
  }
  chatLog.innerHTML = '';
  if (!transcript.length) {
    appendMessage('system', 'System', '壁炉重新被拨旺了一些。你可以从这里继续推进这段冒险。');
    return;
  }
  for (const item of transcript) {
    const kind = item.kind || 'system';
    const speaker = item.speaker || 'System';
    const content = item.content || '';
    if (!content) {
      continue;
    }
    const node = template.content.firstElementChild.cloneNode(true);
    node.classList.add(kind);
    node.querySelector('.speaker').textContent = speaker;
    node.querySelector('.content').textContent = content;
    chatLog.appendChild(node);
  }
  requestAnimationFrame(() => {
    chatLog.scrollTop = chatLog.scrollHeight;
  });
}

function setBusy(isBusy, message) {
  if (createWorldButton) {
    createWorldButton.disabled = isBusy;
  }
  if (sendTurnButton) {
    sendTurnButton.disabled = isBusy;
  }
  if (statusLine) {
    statusLine.textContent = message;
  }
}


function renderAttributes(attributes = {}) {
  if (!attributeGrid) {
    return;
  }
  attributeGrid.innerHTML = '';
  const entries = [
    ['Strength', attributes.strength],
    ['Dexterity', attributes.dexterity],
    ['Intelligence', attributes.intelligence],
    ['Charisma', attributes.charisma],
    ['Constitution', attributes.constitution],
    ['Talent', attributes.talent],
  ];
  for (const [label, value] of entries) {
    const card = document.createElement('div');
    card.className = 'stat';
    card.innerHTML = `<span class="label">${escapeHtml(label)}</span><strong>${value ?? '-'}</strong>`;
    attributeGrid.appendChild(card);
  }
}

function renderFactions(factions = []) {
  if (!factionRow) {
    return;
  }
  factionRow.innerHTML = '';
  const items = factions.length ? factions : ['No factions yet'];
  for (const faction of items) {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.textContent = faction;
    factionRow.appendChild(chip);
  }
}

function renderNpcs(npcs = []) {
  if (!npcList) {
    return;
  }
  npcList.innerHTML = '';
  if (npcs.length === 0) {
    npcList.innerHTML = '<div class="npc-entry"><p>No known NPCs in this world yet.</p></div>';
    return;
  }
  for (const npc of npcs.slice(0, 6)) {
    const card = document.createElement('article');
    card.className = 'npc-entry';
    card.innerHTML = `
      <h4>${escapeHtml(npc.name)}</h4>
      <p>${escapeHtml(npc.profession || 'Unknown role')} · 好感 ${npc.favorability ?? 0}</p>
      <p>${escapeHtml(npc.relationship || 'No clear relationship yet.')}</p>
    `;
    npcList.appendChild(card);
  }
}

function renderRecent(events = []) {
  if (!recentEvents) {
    return;
  }
  recentEvents.innerHTML = '';
  if (events.length === 0) {
    recentEvents.innerHTML = '<li>No turns have been recorded yet.</li>';
    return;
  }
  for (const item of events.slice().reverse()) {
    const li = document.createElement('li');
    li.textContent = item;
    recentEvents.appendChild(li);
  }
}

function renderSessionList() {
  if (!sessionList) {
    return;
  }
  sessionList.innerHTML = '';
  if (!worlds.length) {
    sessionList.innerHTML = '<div class="session-card muted">No saved worlds yet.</div>';
    return;
  }

  for (const worldId of worlds) {
    const card = document.createElement('div');
    card.className = 'session-card-shell';

    const button = document.createElement('button');
    button.type = 'button';
    button.className = `session-card${worldId === activeWorldId ? ' active' : ''}`;
    button.innerHTML = `
      <span class="session-badge">World</span>
      <strong>${escapeHtml(worldId)}</strong>
      <span class="session-meta">继续这条冒险分支</span>
    `;
    button.addEventListener('click', async () => {
      if (worldInput) {
        worldInput.value = worldId;
      }
      try {
        await loadWorld(worldId, 'load', { resetMessages: true });
      } catch (error) {
        if (statusLine) {
          statusLine.textContent = `Failed to load world: ${error.message}`;
        }
      }
    });

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'session-card-delete';
    deleteButton.title = '删除世界';
    deleteButton.setAttribute('aria-label', `删除世界 ${worldId}`);
    deleteButton.innerHTML = `
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 7h2v7h-2v-7Zm4 0h2v7h-2v-7ZM7 10h2v7H7v-7Zm-1 10V8h12v12H6Z" />
      </svg>
    `;
    deleteButton.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      event.stopPropagation();
    });
    deleteButton.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();
      try {
        await deleteWorld(worldId);
      } catch (error) {
        if (statusLine) {
          statusLine.textContent = `Failed to delete world: ${error.message}`;
        }
      }
    });
    card.appendChild(button);
    card.appendChild(deleteButton);
    sessionList.appendChild(card);
  }
}
function applySummary(summary, options = {}) {
  const { resetMessages = false } = options;
  activeWorldId = summary.world_id;
  if (worldInput) {
    worldInput.value = summary.world_id;
  }
  if (navWorldName) {
    navWorldName.textContent = summary.world.name;
  }
  if (worldTitle) {
    worldTitle.textContent = summary.world.name;
  }
  if (worldCity) {
    worldCity.textContent = summary.world.city;
  }
  if (worldTone) {
    worldTone.textContent = summary.world.tone;
  }
  if (playerName) {
    playerName.textContent = summary.player.name;
  }
  if (playerLocation) {
    playerLocation.textContent = summary.player.location;
  }
  if (playerBackground) {
    playerBackground.textContent = summary.player.background || 'No background yet.';
  }
  renderAttributes(summary.player.attributes);
  renderFactions(summary.world.factions);
  renderNpcs(summary.npcs);
  renderRecent(summary.world.recent_events);
  renderSessionList();
  if (resetMessages) {
    if (Array.isArray(summary.transcript)) {
      renderTranscript(summary.transcript);
    } else {
      clearMessages();
    }
  }

}

function updateMeta(result) {
  if (sourcePill) {
    sourcePill.textContent = result.narrative_source || 'template';
  }
  if (rollPill) {
    rollPill.textContent = result.roll?.result || 'unknown';
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `HTTP ${response.status}`;
    try {
      const payload = JSON.parse(text);
      message = payload.error || message;
    } catch {
      // keep original text
    }
    throw new Error(message);
  }
  return response.json();
}

async function refreshWorlds() {
  const payload = await api('/api/worlds');
  worlds = payload.worlds || [];
  if (worldSuggestions) {
    worldSuggestions.innerHTML = '';
    for (const world of worlds) {
      const option = document.createElement('option');
      option.value = world;
      worldSuggestions.appendChild(option);
    }
  }
  renderSessionList();
}

async function loadWorld(worldId, mode = 'load', options = {}) {
  const normalizedWorldId = (worldId || '').trim() || 'campaign_01';
  setBusy(true, mode === 'create' ? 'Creating world...' : 'Loading world...');
  try {
    const path = mode === 'create' ? '/api/worlds/create' : `/api/world?world_id=${encodeURIComponent(normalizedWorldId)}`;
    const payload = mode === 'create'
      ? await api(path, { method: 'POST', body: JSON.stringify({ world_id: normalizedWorldId }) })
      : await api(path);
    await refreshWorlds();
    applySummary(payload, options);
    if (statusLine) {
      statusLine.textContent = `World '${normalizedWorldId}' ready.`;
    }
    return payload;
  } finally {
    setBusy(false, statusLine?.textContent || 'Ready.');
  }
}

async function deleteWorld(worldId) {
  const normalizedWorldId = (worldId || '').trim();
  if (!normalizedWorldId) {
    return;
  }
  const confirmed = window.confirm(`确定要删除世界“${normalizedWorldId}”吗？此操作不可撤销。`);
  if (!confirmed) {
    return;
  }

  setBusy(true, `Deleting world '${normalizedWorldId}'...`);
  try {
    const payload = await api('/api/worlds/delete', {
      method: 'POST',
      body: JSON.stringify({ world_id: normalizedWorldId }),
    });
    await refreshWorlds();

    if (normalizedWorldId === activeWorldId) {
      const fallbackWorldId = payload.fallback_world_id || worlds[0] || '';
      if (fallbackWorldId) {
        await loadWorld(fallbackWorldId, 'load', { resetMessages: true });
        if (statusLine) {
          statusLine.textContent = `World '${normalizedWorldId}' deleted. Switched to '${fallbackWorldId}'.`;
        }
      }
    } else if (statusLine) {
      statusLine.textContent = `World '${normalizedWorldId}' deleted.`;
    }
  } finally {
    setBusy(false, statusLine?.textContent || 'Ready.');
  }
}
function setSettingsStatus(message) {
  if (settingsStatus) {
    settingsStatus.textContent = message;
  }
}

function fillLlmSettingsForm(profile = null) {
  if (!llmProfileIdInput) {
    return;
  }
  llmProfileIdInput.value = profile?.id || '';
  llmProfileLabelInput.value = profile?.label || '';
  llmProfileModelInput.value = profile?.model || '';
  llmProfileBaseUrlInput.value = profile?.base_url || '';
  llmProfileApiKeyInput.value = profile?.api_key || '';
  llmProfileTimeoutInput.value = String(profile?.timeout_seconds ?? 60);
  llmProfileTemperatureInput.value = String(profile?.temperature ?? 0.7);
  llmProfileJsonInput.checked = profile?.force_json_output ?? true;
}

function currentLlmProfile() {
  return llmSettings.profiles.find((item) => item.id === selectedLlmProfileId) || null;
}

function renderLlmProfileList() {
  if (!llmProfileList) {
    return;
  }
  llmProfileList.innerHTML = '';
  if (!llmSettings.profiles.length) {
    llmProfileList.innerHTML = '<div class="session-card muted">还没有模型配置，先新建一条接入信息。</div>';
    return;
  }

  for (const profile of llmSettings.profiles) {
    const button = document.createElement('button');
    button.type = 'button';
    const activeClass = profile.id === llmSettings.active_profile_id ? ' active' : '';
    const currentClass = profile.id === selectedLlmProfileId ? ' current' : '';
    button.className = `llm-profile-card${activeClass}${currentClass}`;
    button.innerHTML = `
      <strong>${escapeHtml(profile.label)}</strong>
      <span class="session-badge">${profile.id === llmSettings.active_profile_id ? 'Current' : 'Profile'}</span>
      <span class="llm-profile-meta">${escapeHtml(profile.model)}</span>
      <span class="llm-profile-meta">${escapeHtml(profile.base_url)}</span>
    `;
    button.addEventListener('click', () => {
      selectedLlmProfileId = profile.id;
      fillLlmSettingsForm(profile);
      renderLlmProfileList();
      setSettingsStatus(`正在编辑 ${profile.label}`);
    });
    llmProfileList.appendChild(button);
  }
}

function resetLlmProfileForm() {
  selectedLlmProfileId = '';
  fillLlmSettingsForm(null);
  renderLlmProfileList();
  setSettingsStatus('正在创建一条新的模型配置。');
}

function collectLlmProfileForm() {
  const label = llmProfileLabelInput?.value.trim() || '';
  const model = llmProfileModelInput?.value.trim() || '';
  const baseUrl = llmProfileBaseUrlInput?.value.trim() || '';
  const apiKey = llmProfileApiKeyInput?.value.trim() || '';
  const profileId = llmProfileIdInput?.value.trim() || slugifyProfileId(label || model);

  return {
    id: profileId,
    label,
    model,
    base_url: baseUrl,
    api_key: apiKey,
    timeout_seconds: Number(llmProfileTimeoutInput?.value || 60),
    temperature: Number(llmProfileTemperatureInput?.value || 0.7),
    force_json_output: Boolean(llmProfileJsonInput?.checked),
  };
}

async function refreshLlmSettings(preferredProfileId = '') {
  llmSettings = await api('/api/settings/llm');
  selectedLlmProfileId = preferredProfileId
    || selectedLlmProfileId
    || llmSettings.active_profile_id
    || llmSettings.profiles[0]?.id
    || '';
  const profile = currentLlmProfile();
  fillLlmSettingsForm(profile);
  renderLlmProfileList();
  if (!profile) {
    fillLlmSettingsForm(null);
  }
}

async function openSettingsModal() {
  if (!settingsModal) {
    return;
  }
  settingsModal.hidden = false;
  document.body.classList.add('modal-open');
  setSettingsStatus('正在读取模型配置...');
  try {
    await refreshLlmSettings();
    if (!currentLlmProfile()) {
      resetLlmProfileForm();
    } else {
      setSettingsStatus('你可以在这里新增、编辑或切换当前模型。');
    }
  } catch (error) {
    setSettingsStatus(`加载设置失败：${error.message}`);
  }
}

function closeSettingsModal() {
  if (!settingsModal) {
    return;
  }
  settingsModal.hidden = true;
  document.body.classList.remove('modal-open');
}

function openCreateWorldForm() {
  if (!createWorldForm || !createWorldInput) {
    return;
  }
  setAccordionPanel('archive');
  createWorldForm.hidden = false;
  createWorldInput.value = createWorldInput.value.trim() || `world_${Date.now()}`;
  if (statusLine) {
    statusLine.textContent = '输入一个新的 world id，然后点击创建。';
  }
  requestAnimationFrame(() => {
    createWorldInput.focus();
    createWorldInput.select();
  });
}

function closeCreateWorldForm() {
  if (!createWorldForm || !createWorldInput) {
    return;
  }
  createWorldForm.hidden = true;
  createWorldInput.value = '';
}

if (turnForm) {
  turnForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = turnInput?.value.trim() || '';
    const worldId = worldInput?.value.trim() || 'campaign_01';
    if (!input) {
      if (statusLine) {
        statusLine.textContent = 'Write an action first.';
      }
      return;
    }

    const intro = chatLog?.querySelector('.message.system');
    if (intro && chatLog.children.length === 1) {
      intro.remove();
    }

    appendMessage('player', 'Traveler', input);
    if (turnInput) {
      turnInput.value = '';
      turnInput.focus();
    }
    setBusy(true, 'Resolving turn...');

    try {
      const payload = await api('/api/turn', {
        method: 'POST',
        body: JSON.stringify({ world_id: worldId, input }),
      });
      latestState = payload.result;
      updateMeta(payload.result);
      if (Array.isArray(payload.summary?.transcript)) {
        applySummary(payload.summary, { resetMessages: true });
      } else {
        appendMessage('gm', 'Dungeon Master', payload.result.final_response);
        applySummary(payload.summary);
      }
      if (statusLine) {
        statusLine.textContent = payload.result.narrative_error
          ? `Fallback used: ${payload.result.narrative_error}`
          : 'Turn resolved.';
      }
    } catch (error) {
      appendMessage('system', 'System', `The turn failed: ${error.message}`);
      if (statusLine) {
        statusLine.textContent = 'Turn failed.';
      }
    } finally {
      setBusy(false, statusLine?.textContent || 'Ready.');
    }
  });
}

if (turnInput) {
  turnInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      turnForm?.requestSubmit();
    }
  });
}



if (toggleWorldArchiveButton) {
  toggleWorldArchiveButton.addEventListener('click', () => {
    setAccordionPanel(worldArchiveExpanded ? '' : 'archive');
  });
}

if (createWorldButton) {
  createWorldButton.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    openCreateWorldForm();
  });
}

if (createWorldForm) {
  createWorldForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const suggested = createWorldInput?.value.trim() || '';
    if (!suggested) {
      if (statusLine) {
        statusLine.textContent = '请先输入新的 world id。';
      }
      createWorldInput?.focus();
      return;
    }

    try {
      await loadWorld(suggested, 'create', { resetMessages: true });
      closeCreateWorldForm();
    } catch (error) {
      if (statusLine) {
        statusLine.textContent = `Failed to create world: ${error.message}`;
      }
    }
  });
}

if (cancelCreateWorldButton) {
  cancelCreateWorldButton.addEventListener('click', () => {
    closeCreateWorldForm();
  });
}

if (toggleRecentEventsButton) {
  toggleRecentEventsButton.addEventListener('click', () => {
    setAccordionPanel(recentEventsExpanded ? '' : 'recent');
  });
}

if (toggleNpcPanelButton) {
  toggleNpcPanelButton.addEventListener('click', () => {
    setAccordionPanel(npcPanelExpanded ? '' : 'npc');
  });
}

if (openSettingsButton) {
  openSettingsButton.addEventListener('click', () => {
    openSettingsModal();
  });
}

if (closeSettingsButton) {
  closeSettingsButton.addEventListener('click', closeSettingsModal);
}

if (settingsBackdrop) {
  settingsBackdrop.addEventListener('click', closeSettingsModal);
}

if (newLlmProfileButton) {
  newLlmProfileButton.addEventListener('click', () => {
    resetLlmProfileForm();
  });
}

if (llmSettingsForm) {
  llmSettingsForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const profile = collectLlmProfileForm();
    setSettingsStatus('正在保存配置...');
    try {
      await api('/api/settings/llm/save', {
        method: 'POST',
        body: JSON.stringify({ profile }),
      });
      await refreshLlmSettings(profile.id);
      setSettingsStatus(`已保存 ${profile.label || profile.id}`);
    } catch (error) {
      setSettingsStatus(`保存失败：${error.message}`);
    }
  });
}

if (activateLlmProfileButton) {
  activateLlmProfileButton.addEventListener('click', async () => {
    const profile = currentLlmProfile();
    if (!profile) {
      setSettingsStatus('先选择一条要激活的模型配置。');
      return;
    }
    try {
      await api('/api/settings/llm/activate', {
        method: 'POST',
        body: JSON.stringify({ profile_id: profile.id }),
      });
      await refreshLlmSettings(profile.id);
      setSettingsStatus(`当前会话已切换到 ${profile.label}`);
    } catch (error) {
      setSettingsStatus(`切换失败：${error.message}`);
    }
  });
}

if (deleteLlmProfileButton) {
  deleteLlmProfileButton.addEventListener('click', async () => {
    const profile = currentLlmProfile();
    if (!profile) {
      setSettingsStatus('没有可删除的模型配置。');
      return;
    }
    const confirmed = window.confirm(`确认删除配置“${profile.label}”吗？`);
    if (!confirmed) {
      return;
    }
    try {
      await api('/api/settings/llm/delete', {
        method: 'POST',
        body: JSON.stringify({ profile_id: profile.id }),
      });
      selectedLlmProfileId = '';
      await refreshLlmSettings();
      if (!currentLlmProfile()) {
        resetLlmProfileForm();
      }
      setSettingsStatus(`已删除 ${profile.label}`);
    } catch (error) {
      setSettingsStatus(`删除失败：${error.message}`);
    }
  });
}

if (importWorldButton) {
  importWorldButton.addEventListener('click', () => {
    setBusy(false, '导入世界功能稍后接入。');
  });
}

if (exportWorldButton) {
  exportWorldButton.addEventListener('click', () => {
    setBusy(false, '导出世界功能稍后接入。');
  });
}

window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    if (settingsModal && !settingsModal.hidden) {
      closeSettingsModal();
      return;
    }
    if (createWorldForm && !createWorldForm.hidden) {
      closeCreateWorldForm();
      createWorldButton?.focus();
    }
  }
});

window.addEventListener('load', async () => {
  try {
    setAccordionPanel('archive');
    await refreshWorlds();
    await loadWorld(worldInput?.value.trim() || 'campaign_01', 'load', { resetMessages: true });

  } catch (error) {
    if (statusLine) {
      statusLine.textContent = `Failed to load world: ${error.message}`;
    }
  }
});








