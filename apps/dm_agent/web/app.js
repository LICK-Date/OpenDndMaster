const chatLog = document.querySelector('#chat-log');
const turnForm = document.querySelector('#turn-form');
const turnInput = document.querySelector('#turn-input');
const worldInput = document.querySelector('#world-id');
const worldSuggestions = document.querySelector('#world-suggestions');
const worldTitle = document.querySelector('#world-title');
const worldPath = document.querySelector('#world-path');
const sourcePill = document.querySelector('#source-pill');
const rollPill = document.querySelector('#roll-pill');
const statusLine = document.querySelector('#status-line');
const loadWorldButton = document.querySelector('#load-world');
const createWorldButton = document.querySelector('#create-world');
const sendTurnButton = document.querySelector('#send-turn');
const template = document.querySelector('#message-template');

const playerName = document.querySelector('#player-name');
const playerLocation = document.querySelector('#player-location');
const playerBackground = document.querySelector('#player-background');
const attributeGrid = document.querySelector('#attribute-grid');
const repNotoriety = document.querySelector('#rep-notoriety');
const repGoodwill = document.querySelector('#rep-goodwill');
const repHeroic = document.querySelector('#rep-heroic');
const worldCity = document.querySelector('#world-city');
const worldTone = document.querySelector('#world-tone');
const factionRow = document.querySelector('#faction-row');
const npcList = document.querySelector('#npc-list');
const recentEvents = document.querySelector('#recent-events');

let latestState = null;
let worlds = [];

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function appendMessage(kind, speaker, content) {
  const node = template.content.firstElementChild.cloneNode(true);
  node.classList.add(kind);
  node.querySelector('.speaker').textContent = speaker;
  node.querySelector('.content').textContent = content;
  chatLog.appendChild(node);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setBusy(isBusy, message) {
  loadWorldButton.disabled = isBusy;
  createWorldButton.disabled = isBusy;
  sendTurnButton.disabled = isBusy;
  statusLine.textContent = message;
}

function renderAttributes(attributes = {}) {
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
  npcList.innerHTML = '';
  if (npcs.length === 0) {
    npcList.innerHTML = '<div class="npc-entry"><p>No known NPCs in this world yet.</p></div>';
    return;
  }
  for (const npc of npcs) {
    const card = document.createElement('article');
    card.className = 'npc-entry';
    card.innerHTML = `
      <h4>${escapeHtml(npc.name)}</h4>
      <p>${escapeHtml(npc.profession || 'Unknown role')} · ${escapeHtml(npc.city || 'Unknown city')} · status=${escapeHtml(npc.status || 'unknown')}</p>
      <p>${escapeHtml(npc.relationship || 'No clear relationship yet.')}</p>
      <p>${escapeHtml(npc.appearance || 'No visible appearance details yet.')}</p>
      <p>Favorability: ${npc.favorability ?? 0}</p>
    `;
    npcList.appendChild(card);
  }
}

function renderRecent(events = []) {
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

function applySummary(summary) {
  worldInput.value = summary.world_id;
  worldTitle.textContent = `${summary.world.name} · ${summary.world.city}`;
  worldPath.textContent = summary.world.path;
  playerName.textContent = summary.player.name;
  playerLocation.textContent = summary.player.location;
  playerBackground.textContent = summary.player.background || 'No background yet.';
  worldCity.textContent = summary.world.city;
  worldTone.textContent = summary.world.tone;
  repNotoriety.textContent = summary.player.reputation?.notoriety ?? 0;
  repGoodwill.textContent = summary.player.reputation?.goodwill ?? 0;
  repHeroic.textContent = summary.player.reputation?.heroic ?? 0;
  renderAttributes(summary.player.attributes);
  renderFactions(summary.world.factions);
  renderNpcs(summary.npcs);
  renderRecent(summary.world.recent_events);
}

function updateMeta(result) {
  sourcePill.textContent = result.narrative_source || 'template';
  rollPill.textContent = result.roll?.result || 'unknown';
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
  worldSuggestions.innerHTML = '';
  for (const world of worlds) {
    const option = document.createElement('option');
    option.value = world;
    worldSuggestions.appendChild(option);
  }
}

async function loadWorld(worldId, mode = 'load') {
  const normalizedWorldId = worldId.trim() || 'campaign_01';
  setBusy(true, mode === 'create' ? 'Creating world...' : 'Loading world...');
  try {
    const path = mode === 'create' ? '/api/worlds/create' : `/api/world?world_id=${encodeURIComponent(normalizedWorldId)}`;
    const payload = mode === 'create'
      ? await api(path, { method: 'POST', body: JSON.stringify({ world_id: normalizedWorldId }) })
      : await api(path);
    applySummary(payload);
    await refreshWorlds();
    statusLine.textContent = `World '${normalizedWorldId}' ready.`;
    return payload;
  } finally {
    setBusy(false, statusLine.textContent);
  }
}

turnForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const input = turnInput.value.trim();
  const worldId = worldInput.value.trim() || 'campaign_01';
  if (!input) {
    statusLine.textContent = 'Write an action first.';
    return;
  }

  const intro = chatLog.querySelector('.message.system');
  if (intro && chatLog.children.length === 1) {
    intro.remove();
  }

  appendMessage('player', 'Traveler', input);
  turnInput.value = '';
  turnInput.focus();
  setBusy(true, 'Resolving turn...');

  try {
    const payload = await api('/api/turn', {
      method: 'POST',
      body: JSON.stringify({ world_id: worldId, input }),
    });
    latestState = payload.result;
    appendMessage('gm', 'Dungeon Master', payload.result.final_response);
    updateMeta(payload.result);
    applySummary(payload.summary);
    statusLine.textContent = payload.result.narrative_error
      ? `Fallback used: ${payload.result.narrative_error}`
      : 'Turn resolved.';
  } catch (error) {
    appendMessage('system', 'System', `The turn failed: ${error.message}`);
    statusLine.textContent = 'Turn failed.';
  } finally {
    setBusy(false, statusLine.textContent);
  }
});

turnInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    turnForm.requestSubmit();
  }
});

loadWorldButton.addEventListener('click', async () => {
  try {
    await loadWorld(worldInput.value, 'load');
  } catch (error) {
    statusLine.textContent = `Failed to load world: ${error.message}`;
  }
});

createWorldButton.addEventListener('click', async () => {
  const suggested = worldInput.value.trim() || `world_${Date.now()}`;
  try {
    const summary = await loadWorld(suggested, 'create');
    appendMessage('system', 'System', `A new world called '${summary.world_id}' is waiting for its first scene.`);
  } catch (error) {
    statusLine.textContent = `Failed to create world: ${error.message}`;
  }
});

window.addEventListener('load', async () => {
  try {
    await refreshWorlds();
    await loadWorld(worldInput.value.trim() || 'campaign_01', 'load');
  } catch (error) {
    statusLine.textContent = `Failed to load world: ${error.message}`;
  }
});
