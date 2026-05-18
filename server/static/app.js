// Stream Deck PWA — cliente WebSocket + renderizado del grid.
(() => {
  const grid = document.getElementById('grid');
  const connDot = document.getElementById('conn-dot');
  const connText = document.getElementById('conn-text');
  const editBtn = document.getElementById('edit-btn');
  const toast = document.getElementById('toast');
  const dialog = document.getElementById('edit-dialog');

  let ws = null;
  let config = { grid: { cols: 4, rows: 4 }, buttons: [] };
  let sounds = [];
  let editMode = false;
  let editingId = null;
  let toastTimer = null;

  // --- WebSocket ----------------------------------------------------------

  function wsUrl() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${location.host}/ws`;
  }

  function connectWs() {
    setConn(false, 'conectando…');
    try {
      ws = new WebSocket(wsUrl());
    } catch (e) {
      scheduleReconnect();
      return;
    }
    ws.onopen = () => setConn(true, 'conectado');
    ws.onclose = () => {
      setConn(false, 'desconectado');
      scheduleReconnect();
    };
    ws.onerror = () => { /* close handler se encarga */ };
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      handleWsMessage(msg);
    };
  }

  let reconnectTimer = null;
  function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectWs();
    }, 1500);
  }

  function handleWsMessage(msg) {
    switch (msg.type) {
      case 'hello':
        setConn(true, msg.soundpad_connected ? 'conectado' : 'sin Soundpad');
        break;
      case 'press_result':
        if (msg.ok === false) showToast(`Error: ${msg.error || 'acción falló'}`);
        break;
      case 'action_result':
        if (msg.ok === false) showToast(`Error: ${msg.error || 'acción falló'}`);
        break;
      case 'config_updated':
        config = msg.config;
        renderGrid();
        break;
    }
  }

  function setConn(ok, label) {
    connDot.className = `dot ${ok ? 'dot-on' : 'dot-off'}`;
    connText.textContent = label;
  }

  // --- Data loading -------------------------------------------------------

  async function loadConfig() {
    const r = await fetch('/api/config');
    config = await r.json();
    if (!config.buttons || config.buttons.length === 0) {
      // Primer arranque: ofrecer auto-generar desde Soundpad
      const auto = await fetch('/api/config/autogen', { method: 'POST' });
      if (auto.ok) config = await auto.json();
    }
  }

  async function loadSounds() {
    try {
      const r = await fetch('/api/sounds');
      if (!r.ok) { sounds = []; return; }
      const data = await r.json();
      sounds = data.sounds || [];
    } catch { sounds = []; }
  }

  async function saveConfig() {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
  }

  // --- Grid rendering -----------------------------------------------------

  function renderGrid() {
    const { cols, rows } = config.grid || { cols: 4, rows: 4 };
    grid.style.setProperty('--cols', cols);
    grid.style.setProperty('--rows', rows);
    grid.innerHTML = '';

    const total = cols * rows;
    const byId = new Map((config.buttons || []).map(b => [b.id, b]));

    for (let i = 0; i < total; i++) {
      const id = `b${i + 1}`;
      const btn = byId.get(id);
      const tile = document.createElement('button');
      tile.className = 'tile' + (btn ? '' : ' empty');
      tile.dataset.id = id;
      if (btn) {
        tile.style.setProperty('--tile', btn.color || '#334155');
        tile.textContent = btn.label || `Botón ${i + 1}`;
      } else {
        tile.textContent = '+';
      }
      tile.addEventListener('click', () => onTileClick(id));
      grid.appendChild(tile);
    }
  }

  function onTileClick(id) {
    if (editMode) {
      openEditor(id);
      return;
    }
    const tile = grid.querySelector(`[data-id="${id}"]`);
    if (tile) {
      tile.classList.remove('flash');
      void tile.offsetWidth;
      tile.classList.add('flash');
    }
    if (navigator.vibrate) navigator.vibrate(10);
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      showToast('Sin conexión con el servidor');
      return;
    }
    ws.send(JSON.stringify({ type: 'press', button_id: id }));
  }

  // --- Editor -------------------------------------------------------------

  const edLabel = document.getElementById('ed-label');
  const edColor = document.getElementById('ed-color');
  const edActionType = document.getElementById('ed-action-type');
  const edParams = document.getElementById('ed-params');
  const edSave = document.getElementById('ed-save');

  edActionType.addEventListener('change', renderParamsForm);

  function openEditor(id) {
    editingId = id;
    const button = (config.buttons || []).find(b => b.id === id) || {
      id, label: '', color: '#3b82f6', action: { type: '', params: {} }
    };
    edLabel.value = button.label || '';
    edColor.value = button.color || '#3b82f6';
    edActionType.value = button.action?.type || '';
    renderParamsForm();
    fillParams(button.action?.params || {});
    dialog.showModal();
  }

  function renderParamsForm() {
    const t = edActionType.value;
    edParams.innerHTML = '';
    if (t === 'soundpad_play') {
      const select = document.createElement('select');
      select.id = 'ed-p-sound';
      sounds.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.index;
        opt.textContent = `[${s.index}] ${s.title}`;
        select.appendChild(opt);
      });
      const label = document.createElement('label');
      label.textContent = 'Sonido';
      label.appendChild(select);
      edParams.appendChild(label);
    } else if (t === 'hotkey') {
      addInput('ed-p-keys', 'Teclas (separadas por +, ej: ctrl+shift+f1)', 'text');
    } else if (t === 'launch_app') {
      addInput('ed-p-path', 'Ruta al ejecutable', 'text');
      addInput('ed-p-args', 'Argumentos (opcional)', 'text');
    } else if (t === 'run_script') {
      addInput('ed-p-path', 'Ruta al script (.bat/.ps1/.cmd)', 'text');
    } else if (t === 'open_url') {
      addInput('ed-p-url', 'URL', 'text');
    }
  }

  function addInput(id, labelText, type) {
    const label = document.createElement('label');
    label.textContent = labelText;
    const input = document.createElement('input');
    input.id = id; input.type = type;
    label.appendChild(input);
    edParams.appendChild(label);
  }

  function fillParams(params) {
    const t = edActionType.value;
    if (t === 'soundpad_play' && params.index) {
      const sel = document.getElementById('ed-p-sound');
      if (sel) sel.value = params.index;
    } else if (t === 'hotkey' && params.keys) {
      document.getElementById('ed-p-keys').value = params.keys.join('+');
    } else if (t === 'launch_app') {
      document.getElementById('ed-p-path').value = params.path || '';
      const args = params.args;
      document.getElementById('ed-p-args').value =
        Array.isArray(args) ? args.join(' ') : (args || '');
    } else if (t === 'run_script') {
      document.getElementById('ed-p-path').value = params.path || '';
    } else if (t === 'open_url') {
      document.getElementById('ed-p-url').value = params.url || '';
    }
  }

  function collectParams() {
    const t = edActionType.value;
    if (!t) return null;
    if (t === 'soundpad_play') {
      const sel = document.getElementById('ed-p-sound');
      return { index: parseInt(sel.value, 10) };
    }
    if (t === 'soundpad_stop' || t === 'soundpad_next' || t === 'soundpad_previous') {
      return {};
    }
    if (t === 'hotkey') {
      const raw = document.getElementById('ed-p-keys').value;
      return { keys: raw.split('+').map(s => s.trim()).filter(Boolean) };
    }
    if (t === 'launch_app') {
      const args = document.getElementById('ed-p-args').value.trim();
      return {
        path: document.getElementById('ed-p-path').value.trim(),
        args: args ? args.split(/\s+/) : [],
      };
    }
    if (t === 'run_script') {
      return { path: document.getElementById('ed-p-path').value.trim() };
    }
    if (t === 'open_url') {
      return { url: document.getElementById('ed-p-url').value.trim() };
    }
    return {};
  }

  edSave.addEventListener('click', (e) => {
    e.preventDefault();
    const id = editingId;
    const label = edLabel.value.trim();
    const color = edColor.value;
    const type = edActionType.value;
    const buttons = config.buttons || (config.buttons = []);
    let btn = buttons.find(b => b.id === id);

    if (!type && !label) {
      // Vacío → borrar
      config.buttons = buttons.filter(b => b.id !== id);
    } else {
      const action = type ? { type, params: collectParams() || {} } : null;
      if (!btn) { btn = { id }; buttons.push(btn); }
      btn.label = label;
      btn.color = color;
      if (action) btn.action = action; else delete btn.action;
    }
    dialog.close();
    saveConfig().then(renderGrid);
  });

  editBtn.addEventListener('click', () => {
    editMode = !editMode;
    document.body.classList.toggle('editing', editMode);
    editBtn.textContent = editMode ? '✓' : '✎';
    showToast(editMode ? 'Modo edición: toca un botón' : 'Modo normal');
  });

  // --- UI helpers ---------------------------------------------------------

  function showToast(msg) {
    toast.textContent = msg;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.hidden = true, 2200);
  }

  // --- Init ---------------------------------------------------------------

  (async function init() {
    try {
      await loadSounds();
      await loadConfig();
      renderGrid();
    } catch (e) {
      console.error(e);
      showToast('Error cargando configuración');
    }
    connectWs();

    // Mantener WS vivo
    setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25000);

    // Registrar service worker (sólo si HTTPS o localhost)
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
  })();
})();
