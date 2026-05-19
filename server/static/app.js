// Stream Deck PWA — cliente WebSocket + grid + páginas + drag&drop.
(() => {
  // --- DOM refs -----------------------------------------------------------
  const grid = document.getElementById('grid');
  const tabsEl = document.getElementById('tabs');
  const connDot = document.getElementById('conn-dot');
  const connText = document.getElementById('conn-text');
  const editBtn = document.getElementById('edit-btn');
  const toast = document.getElementById('toast');
  const dialog = document.getElementById('edit-dialog');
  const pageDialog = document.getElementById('page-dialog');
  const tmplBtn = document.getElementById('tmpl-btn');
  const tmplDialog = document.getElementById('tmpl-dialog');
  const tmplList = document.getElementById('tmpl-list');
  const obsBtn = document.getElementById('obs-btn');
  const regenDialog = document.getElementById('regen-dialog');
  const regenFlat = document.getElementById('regen-flat');
  const regenCats = document.getElementById('regen-cats');
  const tmplRegenBtn = document.getElementById('tmpl-regen-btn');
  const obsDialog = document.getElementById('obs-dialog');
  const obsHost = document.getElementById('obs-host');
  const obsPort = document.getElementById('obs-port');
  const obsPassword = document.getElementById('obs-password');
  const obsState = document.getElementById('obs-state');
  const obsSave = document.getElementById('obs-save');

  // --- State --------------------------------------------------------------
  let ws = null;
  let config = { grid: { cols: 4, rows: 4 }, pages: [] };
  let sounds = [];
  let obsScenes = [];
  let obsInputs = [];
  let currentPageIdx = 0;
  let editMode = false;
  let editingId = null;
  let editingPageIdx = -1;
  let toastTimer = null;

  const AUTO_SOUNDS_ID = 'p_sounds';
  const TILE_PALETTE = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
  ];

  // Bloquear el menú contextual del navegador (compartir / guardar /
  // imprimir al mantener pulsado en Android).
  document.addEventListener('contextmenu', (e) => e.preventDefault());

  // --- Vibration patterns -------------------------------------------------
  const VIB = {
    tap: 10,
    longPress: 18,
    error: [25, 60, 25],
  };
  function vibrate(pattern) {
    if (navigator.vibrate) navigator.vibrate(pattern);
  }

  // --- WebSocket ----------------------------------------------------------

  function wsUrl() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${location.host}/ws`;
  }

  function connectWs() {
    setConn(false, 'conectando…');
    try { ws = new WebSocket(wsUrl()); }
    catch { scheduleReconnect(); return; }
    ws.onopen = () => setConn(true, 'conectado');
    ws.onclose = () => { setConn(false, 'desconectado'); scheduleReconnect(); };
    ws.onerror = () => {};
    ws.onmessage = (ev) => {
      let msg; try { msg = JSON.parse(ev.data); } catch { return; }
      handleWsMessage(msg);
    };
  }

  let reconnectTimer = null;
  function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(() => { reconnectTimer = null; connectWs(); }, 1500);
  }

  function handleWsMessage(msg) {
    switch (msg.type) {
      case 'hello':
        setConn(true, msg.soundpad_connected ? 'conectado' : 'sin Soundpad');
        break;
      case 'press_result':
      case 'action_result':
        if (msg.ok === false) {
          showToast(`Error: ${msg.error || 'acción falló'}`);
          vibrate(VIB.error);
        }
        break;
      case 'soundpad_status':
        setConn(true, msg.connected ? 'conectado' : 'sin Soundpad');
        if (msg.connected) loadSounds();
        break;
      case 'config_updated':
        // No sobrescribir si el cambio viene de esta misma sesión (evita re-render molesto)
        // Aquí lo aceptamos directamente porque es schema completo
        config = msg.config;
        clampCurrentPage();
        render();
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
    clampCurrentPage();
  }

  async function loadSounds() {
    try {
      const r = await fetch('/api/sounds');
      if (!r.ok) { sounds = []; return; }
      const data = await r.json();
      sounds = data.sounds || [];
    } catch { sounds = []; }
    // Si estamos viendo la página automática, repinta.
    if (currentPage()?.auto === 'soundpad') renderGrid();
  }

  async function saveConfig() {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
  }

  // --- Page helpers -------------------------------------------------------

  function pages() { return config.pages || []; }
  function currentPage() { return pages()[currentPageIdx] || null; }

  function clampCurrentPage() {
    const n = pages().length;
    if (n === 0) {
      config.pages = [{ id: AUTO_SOUNDS_ID, name: 'Soundpad', auto: 'soundpad', buttons: [] }];
      currentPageIdx = 0;
      return;
    }
    if (currentPageIdx < 0) currentPageIdx = 0;
    if (currentPageIdx >= n) currentPageIdx = n - 1;
  }

  function setPage(idx) {
    if (idx < 0 || idx >= pages().length) return;
    if (idx === currentPageIdx) { render(); return; }
    const direction = idx > currentPageIdx ? 1 : -1;
    currentPageIdx = idx;
    grid.style.setProperty('--slide-from', `${direction * 36}px`);
    grid.classList.remove('page-enter');
    render();
    void grid.offsetWidth;
    grid.classList.add('page-enter');
  }

  function newPageId() {
    const taken = new Set(pages().map(p => p.id));
    let i = 1;
    while (taken.has(`p${i}`)) i++;
    return `p${i}`;
  }

  function addPage() {
    const id = newPageId();
    pages().push({ id, name: `Página ${pages().length + 1}`, buttons: [] });
    currentPageIdx = pages().length - 1;
    saveConfig().then(render);
  }

  // --- Rendering ----------------------------------------------------------

  function render() {
    renderTabs();
    renderGrid();
  }

  function renderTabs() {
    tabsEl.innerHTML = '';
    pages().forEach((p, i) => {
      const tab = document.createElement('button');
      tab.className = 'tab' + (i === currentPageIdx ? ' active' : '');
      tab.textContent = p.name || `Página ${i + 1}`;
      tab.addEventListener('click', () => {
        const isAuto = p.auto === 'soundpad';
        if (editMode && i === currentPageIdx && !isAuto) {
          openPageEditor(i);
        } else {
          setPage(i);
        }
      });
      tabsEl.appendChild(tab);
    });
    if (editMode) {
      const plus = document.createElement('button');
      plus.className = 'tab tab-add';
      plus.textContent = '+';
      plus.title = 'Añadir página';
      plus.addEventListener('click', addPage);
      tabsEl.appendChild(plus);
    }
  }

  function renderGrid() {
    const { cols, rows } = config.grid || { cols: 4, rows: 4 };
    grid.style.setProperty('--cols', cols);
    grid.style.setProperty('--rows', rows);
    grid.innerHTML = '';

    const page = currentPage();
    const total = cols * rows;

    // Página automática: refleja los primeros 'total' sonidos de Soundpad
    // en su orden actual. No editable.
    if (page?.auto === 'soundpad') {
      for (let i = 0; i < total; i++) {
        const sound = sounds[i];
        const tile = document.createElement('div');
        if (sound) {
          tile.className = 'tile';
          tile.dataset.soundIndex = sound.index;
          tile.style.setProperty('--tile', TILE_PALETTE[i % TILE_PALETTE.length]);
          tile.textContent = sound.title;
        } else {
          tile.className = 'tile empty';
          tile.textContent = '';
        }
        attachTileHandlers(tile, `auto_${i}`, /* editable */ false);
        grid.appendChild(tile);
      }
      return;
    }

    const byId = new Map((page?.buttons || []).map(b => [b.id, b]));
    for (let i = 0; i < total; i++) {
      const id = `b${i + 1}`;
      const btn = byId.get(id);
      const tile = document.createElement('div');
      tile.className = 'tile' + (btn ? '' : ' empty');
      tile.dataset.id = id;
      if (btn) {
        tile.style.setProperty('--tile', btn.color || '#334155');
        const label = btn.label || `Botón ${i + 1}`;
        if (btn.icon) {
          tile.classList.add('with-icon');
          const ic = document.createElement('div');
          ic.className = 'tile-icon';
          ic.textContent = btn.icon;
          const lb = document.createElement('div');
          lb.className = 'tile-label';
          lb.textContent = label;
          tile.appendChild(ic);
          tile.appendChild(lb);
        } else {
          tile.textContent = label;
        }
      } else {
        tile.textContent = '+';
      }
      attachTileHandlers(tile, id, /* editable */ true);
      grid.appendChild(tile);
    }
  }

  // --- Tile interaction (tap + drag) --------------------------------------

  const DRAG_THRESHOLD_PX = 10;

  function attachTileHandlers(tile, id, editable = true) {
    let startX = 0, startY = 0;
    let dragging = false;
    let ghost = null;
    let lastTarget = null;
    let pointerActive = false;
    let pressTimer = null;

    function cleanup() {
      pointerActive = false;
      dragging = false;
      if (ghost) { ghost.remove(); ghost = null; }
      if (lastTarget) { lastTarget.classList.remove('drop-target'); lastTarget = null; }
      if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
    }

    tile.addEventListener('pointerdown', (e) => {
      if (e.button !== 0 && e.pointerType === 'mouse') return;
      pointerActive = true;
      startX = e.clientX;
      startY = e.clientY;
      // En modo edición y si la página lo permite, después de 250ms
      // sin movimiento, iniciamos drag.
      if (editable && editMode) {
        pressTimer = setTimeout(() => {
          if (pointerActive && !dragging) startDrag(e.clientX, e.clientY);
        }, 250);
      }
    });

    tile.addEventListener('pointermove', (e) => {
      if (!pointerActive) return;
      const dx = e.clientX - startX, dy = e.clientY - startY;
      if (!dragging && editable && editMode && Math.hypot(dx, dy) > DRAG_THRESHOLD_PX) {
        startDrag(e.clientX, e.clientY);
      }
      if (dragging) moveDrag(e.clientX, e.clientY);
    });

    tile.addEventListener('pointerup', (e) => {
      if (!pointerActive) return;
      const moved = Math.hypot(e.clientX - startX, e.clientY - startY);
      if (dragging) {
        finishDrag(e.clientX, e.clientY);
      } else if (moved < DRAG_THRESHOLD_PX) {
        // Tap
        onTileTap(id);
      }
      cleanup();
    });

    tile.addEventListener('pointercancel', cleanup);
    tile.addEventListener('lostpointercapture', cleanup);

    function startDrag(x, y) {
      dragging = true;
      tile.setPointerCapture?.(0);
      tile.classList.add('dragging-source');
      ghost = tile.cloneNode(true);
      ghost.classList.add('drag-ghost');
      ghost.style.width = tile.offsetWidth + 'px';
      ghost.style.height = tile.offsetHeight + 'px';
      document.body.appendChild(ghost);
      moveDrag(x, y);
      vibrate(VIB.longPress);
    }

    function moveDrag(x, y) {
      if (!ghost) return;
      ghost.style.left = (x - ghost.offsetWidth / 2) + 'px';
      ghost.style.top = (y - ghost.offsetHeight / 2) + 'px';
      // Highlight tile bajo el cursor
      ghost.style.pointerEvents = 'none';
      const under = document.elementFromPoint(x, y);
      const target = under?.closest?.('.tile');
      if (target !== lastTarget) {
        lastTarget?.classList.remove('drop-target');
        if (target && target !== tile) target.classList.add('drop-target');
        lastTarget = target && target !== tile ? target : null;
      }
    }

    function finishDrag(x, y) {
      const under = document.elementFromPoint(x, y);
      const target = under?.closest?.('.tile');
      tile.classList.remove('dragging-source');
      if (target && target !== tile && target.dataset.id) {
        swapButtons(id, target.dataset.id);
      }
    }
  }

  function onTileTap(id) {
    if (swipeJustHappened) return;
    const page = currentPage();
    if (!page) return;

    // Página automática Soundpad: id = 'auto_<i>' y disparamos
    // soundpad_play con el índice real del sonido.
    if (page.auto === 'soundpad') {
      const i = parseInt(id.replace('auto_', ''), 10);
      const sound = sounds[i];
      if (!sound) return;
      flashTile(id);
      vibrate(VIB.tap);
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('Sin conexión con el servidor');
        return;
      }
      ws.send(JSON.stringify({
        type: 'action',
        action: { type: 'soundpad_play', params: { index: sound.index } },
      }));
      return;
    }

    if (editMode) {
      openEditor(id);
      return;
    }
    const tile = grid.querySelector(`[data-id="${id}"]`);
    if (tile && !tile.classList.contains('empty')) {
      flashTile(id);
    }
    vibrate(VIB.tap);
    const hasButton = (page.buttons || []).some(b => b.id === id);
    if (!hasButton) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      showToast('Sin conexión con el servidor');
      return;
    }
    ws.send(JSON.stringify({ type: 'press', button_id: id, page_id: page.id }));
  }

  function flashTile(id) {
    const sel = id.startsWith('auto_')
      ? `[data-sound-index]`
      : `[data-id="${id}"]`;
    // Para auto, buscamos el tile por posición en el grid.
    let tile;
    if (id.startsWith('auto_')) {
      const i = parseInt(id.replace('auto_', ''), 10);
      tile = grid.children[i];
    } else {
      tile = grid.querySelector(`[data-id="${id}"]`);
    }
    if (!tile) return;
    tile.classList.remove('flash');
    void tile.offsetWidth;
    tile.classList.add('flash');
  }

  function swapButtons(idA, idB) {
    const page = currentPage();
    if (!page) return;
    const buttons = page.buttons || (page.buttons = []);
    const a = buttons.find(b => b.id === idA);
    const b = buttons.find(b => b.id === idB);
    if (a) a.id = idB;
    if (b) b.id = idA;
    saveConfig().then(render);
  }

  // --- Editor de botón ----------------------------------------------------

  const edLabel = document.getElementById('ed-label');
  const edColor = document.getElementById('ed-color');
  const edIcon = document.getElementById('ed-icon');
  const edActionType = document.getElementById('ed-action-type');
  const edParams = document.getElementById('ed-params');
  const edSave = document.getElementById('ed-save');
  const edDelete = document.getElementById('ed-delete');

  edActionType.addEventListener('change', renderParamsForm);

  function openEditor(id) {
    editingId = id;
    const page = currentPage();
    if (!page) return;
    const button = (page.buttons || []).find(b => b.id === id) || {
      id, label: '', color: '#3b82f6', action: { type: '', params: {} }
    };
    edLabel.value = button.label || '';
    edColor.value = button.color || '#3b82f6';
    edIcon.value = button.icon || '';
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
    } else if (t === 'text_input') {
      addTextarea('ed-p-text', 'Texto a escribir', 3);
    } else if (t === 'delay') {
      addInput('ed-p-ms', 'Pausa (milisegundos)', 'number');
    } else if (t === 'sequence') {
      addTextarea('ed-p-steps', 'Pasos en JSON (lista de acciones)', 8,
        '[\n  { "type": "hotkey", "params": { "keys": ["ctrl","shift","m"] } },\n  { "type": "delay", "params": { "ms": 200 } },\n  { "type": "text_input", "params": { "text": "Hola" } }\n]');
    } else if (t === 'obs_scene') {
      const select = document.createElement('select');
      select.id = 'ed-p-scene';
      if (obsScenes.length === 0) {
        const opt = document.createElement('option');
        opt.value = ''; opt.textContent = '(OBS no conectado o sin escenas)';
        select.appendChild(opt);
      }
      obsScenes.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.name; opt.textContent = s.name;
        select.appendChild(opt);
      });
      const label = document.createElement('label');
      label.textContent = 'Escena';
      label.appendChild(select);
      edParams.appendChild(label);
    } else if (t === 'obs_toggle_mute') {
      const select = document.createElement('select');
      select.id = 'ed-p-input';
      if (obsInputs.length === 0) {
        const opt = document.createElement('option');
        opt.value = ''; opt.textContent = '(OBS no conectado o sin fuentes de audio)';
        select.appendChild(opt);
      }
      obsInputs.forEach(i => {
        const opt = document.createElement('option');
        opt.value = i.name; opt.textContent = i.name;
        select.appendChild(opt);
      });
      const label = document.createElement('label');
      label.textContent = 'Fuente de audio';
      label.appendChild(select);
      edParams.appendChild(label);
    }
  }

  function addTextarea(id, labelText, rows, placeholder = '') {
    const label = document.createElement('label');
    label.textContent = labelText;
    const ta = document.createElement('textarea');
    ta.id = id;
    ta.rows = rows;
    if (placeholder) ta.placeholder = placeholder;
    label.appendChild(ta);
    edParams.appendChild(label);
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
    } else if (t === 'text_input') {
      document.getElementById('ed-p-text').value = params.text || '';
    } else if (t === 'delay') {
      document.getElementById('ed-p-ms').value = params.ms ?? 200;
    } else if (t === 'sequence') {
      const steps = params.steps;
      if (Array.isArray(steps) && steps.length > 0) {
        document.getElementById('ed-p-steps').value = JSON.stringify(steps, null, 2);
      }
    } else if (t === 'obs_scene' && params.scene) {
      const sel = document.getElementById('ed-p-scene');
      if (sel) sel.value = params.scene;
    } else if (t === 'obs_toggle_mute' && params.input) {
      const sel = document.getElementById('ed-p-input');
      if (sel) sel.value = params.input;
    }
  }

  function collectParams() {
    const t = edActionType.value;
    if (!t) return null;
    if (t === 'soundpad_play') {
      const sel = document.getElementById('ed-p-sound');
      return { index: parseInt(sel.value, 10) };
    }
    if (['soundpad_stop', 'soundpad_next', 'soundpad_previous'].includes(t)) {
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
    if (t === 'text_input') {
      return { text: document.getElementById('ed-p-text').value };
    }
    if (t === 'delay') {
      const ms = parseInt(document.getElementById('ed-p-ms').value, 10);
      return { ms: Number.isFinite(ms) ? ms : 200 };
    }
    if (t === 'sequence') {
      const raw = document.getElementById('ed-p-steps').value.trim();
      if (!raw) return { steps: [] };
      try {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) throw new Error('debe ser un array');
        return { steps: parsed };
      } catch (e) {
        showToast('JSON inválido en la secuencia: ' + e.message);
        throw e;
      }
    }
    if (t === 'obs_scene') {
      return { scene: document.getElementById('ed-p-scene').value };
    }
    if (t === 'obs_toggle_mute') {
      return { input: document.getElementById('ed-p-input').value };
    }
    if (['obs_toggle_stream', 'obs_toggle_record', 'obs_transition'].includes(t)) {
      return {};
    }
    return {};
  }

  edSave.addEventListener('click', (e) => {
    e.preventDefault();
    const id = editingId;
    const page = currentPage();
    if (!page) { dialog.close(); return; }
    const buttons = page.buttons || (page.buttons = []);
    const label = edLabel.value.trim();
    const color = edColor.value;
    const icon = edIcon.value.trim();
    const type = edActionType.value;

    if (!type && !label && !icon) {
      page.buttons = buttons.filter(b => b.id !== id);
    } else {
      let btn = buttons.find(b => b.id === id);
      if (!btn) { btn = { id }; buttons.push(btn); }
      btn.label = label || `Botón ${id.slice(1)}`;
      btn.color = color;
      if (icon) btn.icon = icon; else delete btn.icon;
      if (type) btn.action = { type, params: collectParams() || {} };
      else delete btn.action;
    }
    dialog.close();
    saveConfig().then(render);
  });

  edDelete.addEventListener('click', (e) => {
    e.preventDefault();
    const id = editingId;
    const page = currentPage();
    if (page) {
      page.buttons = (page.buttons || []).filter(b => b.id !== id);
    }
    dialog.close();
    saveConfig().then(render);
  });

  // --- Editor de página ---------------------------------------------------

  const pgName = document.getElementById('pg-name');
  const pgSave = document.getElementById('pg-save');
  const pgDelete = document.getElementById('pg-delete');
  const pgTitle = document.getElementById('pg-title');

  function openPageEditor(idx) {
    editingPageIdx = idx;
    const p = pages()[idx];
    pgTitle.textContent = `Editar página ${idx + 1}`;
    pgName.value = p?.name || '';
    pgDelete.disabled = pages().length <= 1;
    pageDialog.showModal();
  }

  pgSave.addEventListener('click', (e) => {
    e.preventDefault();
    const p = pages()[editingPageIdx];
    if (p) p.name = pgName.value.trim() || `Página ${editingPageIdx + 1}`;
    pageDialog.close();
    saveConfig().then(render);
  });

  pgDelete.addEventListener('click', (e) => {
    e.preventDefault();
    if (pages().length <= 1) return;
    if (!confirm(`¿Borrar la página "${pages()[editingPageIdx]?.name}" y todos sus botones?`)) {
      e.stopPropagation();
      return;
    }
    pages().splice(editingPageIdx, 1);
    clampCurrentPage();
    pageDialog.close();
    saveConfig().then(render);
  });

  // --- Modo edición -------------------------------------------------------

  editBtn.addEventListener('click', () => {
    editMode = !editMode;
    document.body.classList.toggle('editing', editMode);
    editBtn.textContent = editMode ? '✓' : '✎';
    tmplBtn.classList.toggle('hidden', !editMode);
    obsBtn.classList.toggle('hidden', !editMode);
    if (editMode) {
      showToast('Edición: toca botón para editar, mantén pulsado para mover, toca pestaña activa para renombrar');
    }
    render();
  });

  // --- Plantillas ---------------------------------------------------------

  tmplBtn.addEventListener('click', openTemplates);

  async function openTemplates() {
    tmplList.innerHTML = '<p class="muted">Cargando…</p>';
    tmplDialog.showModal();
    try {
      const r = await fetch('/api/templates');
      const data = await r.json();
      renderTemplateList(data.templates || []);
    } catch (e) {
      tmplList.innerHTML = '<p class="muted">Error al cargar plantillas</p>';
    }
  }

  function renderTemplateList(items) {
    tmplList.innerHTML = '';
    if (items.length === 0) {
      tmplList.innerHTML = '<p class="muted">No hay plantillas disponibles</p>';
      return;
    }
    for (const t of items) {
      const el = document.createElement('div');
      el.className = 'tmpl-item';
      el.innerHTML = `
        <h3>${escapeHtml(t.name)}<span class="tmpl-count">${t.button_count} botones</span></h3>
        <p>${escapeHtml(t.description || '')}</p>
        <div class="tmpl-actions">
          <button type="button" data-id="${escapeHtml(t.id)}">Aplicar como página</button>
        </div>
      `;
      el.querySelector('button').addEventListener('click', () => applyTemplate(t.id, t.name));
      tmplList.appendChild(el);
    }
  }

  async function applyTemplate(id, name) {
    try {
      const r = await fetch(`/api/templates/${encodeURIComponent(id)}/apply?mode=new_page`, {
        method: 'POST',
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        showToast(`Error: ${err.detail || 'no se pudo aplicar'}`);
        return;
      }
      config = await r.json();
      currentPageIdx = pages().length - 1;
      tmplDialog.close();
      render();
      showToast(`Plantilla "${name}" aplicada`);
    } catch (e) {
      showToast('Error de red al aplicar la plantilla');
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // --- OBS settings -------------------------------------------------------

  obsBtn.addEventListener('click', openObsDialog);

  // --- Regenerar páginas desde Soundpad ----------------------------------

  tmplRegenBtn?.addEventListener('click', () => {
    tmplDialog.close();
    regenDialog.showModal();
  });

  async function applyRegen(mode) {
    try {
      const r = await fetch(`/api/config/autogen?mode=${encodeURIComponent(mode)}`, {
        method: 'POST',
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        showToast(`Error: ${err.detail || 'no se pudo regenerar'}`);
        return;
      }
      config = await r.json();
      currentPageIdx = 0;
      regenDialog.close();
      await loadSounds();
      render();
      showToast('Páginas regeneradas');
    } catch {
      showToast('Error de red');
    }
  }

  regenFlat.addEventListener('click', (e) => {
    e.preventDefault();
    if (!confirm('Esto reemplaza las páginas actuales. ¿Seguir?')) return;
    applyRegen('flat');
  });
  regenCats.addEventListener('click', (e) => {
    e.preventDefault();
    if (!confirm('Esto reemplaza las páginas actuales. ¿Seguir?')) return;
    applyRegen('categories');
  });


  async function loadObsData() {
    try {
      const r = await fetch('/api/obs/scenes');
      obsScenes = r.ok ? ((await r.json()).scenes || []) : [];
    } catch { obsScenes = []; }
    try {
      const r = await fetch('/api/obs/inputs');
      obsInputs = r.ok ? ((await r.json()).inputs || []) : [];
    } catch { obsInputs = []; }
  }

  async function refreshObsStatus() {
    try {
      const r = await fetch('/api/obs/status');
      const data = await r.json();
      if (data.connected) {
        const v = data.version || {};
        obsState.textContent =
          `Conectado a OBS ${v.obs_version || ''} (ws ${v.ws_version || ''}). ` +
          `Stream: ${data.streaming ? 'on' : 'off'}, Rec: ${data.recording ? 'on' : 'off'}`;
        obsState.style.color = 'var(--ok)';
      } else {
        obsState.textContent = 'No conectado. Revisa host, puerto y contraseña.';
        obsState.style.color = 'var(--danger)';
      }
    } catch {
      obsState.textContent = 'No se pudo consultar el estado.';
      obsState.style.color = 'var(--danger)';
    }
  }

  async function openObsDialog() {
    const obsCfg = config.obs || {};
    obsHost.value = obsCfg.host || 'localhost';
    obsPort.value = obsCfg.port || 4455;
    obsPassword.value = obsCfg.password || '';
    obsState.textContent = 'Comprobando…';
    obsDialog.showModal();
    await refreshObsStatus();
  }

  obsSave.addEventListener('click', async (e) => {
    e.preventDefault();
    obsSave.disabled = true;
    obsState.textContent = 'Conectando…';
    try {
      const r = await fetch('/api/obs/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: obsHost.value.trim() || 'localhost',
          port: parseInt(obsPort.value, 10) || 4455,
          password: obsPassword.value,
        }),
      });
      const data = await r.json();
      if (data.connected) {
        await loadObsData();
        await refreshObsStatus();
        showToast('OBS conectado');
        // Recargar config local para tener los datos OBS
        const cr = await fetch('/api/config');
        config = await cr.json();
      } else {
        obsState.textContent = 'No se pudo conectar. Comprueba OBS y la contraseña.';
        obsState.style.color = 'var(--danger)';
      }
    } catch {
      obsState.textContent = 'Error de red.';
      obsState.style.color = 'var(--danger)';
    } finally {
      obsSave.disabled = false;
    }
  });

  // --- Swipe horizontal entre páginas -------------------------------------
  // Funciona aunque el toque empiece sobre un tile. Si detectamos un
  // desplazamiento horizontal significativo, cambiamos de página y
  // marcamos un flag para que el tap del tile no se dispare.

  let swipeStart = null;
  let swipeJustHappened = false;
  const SWIPE_MIN_X = 60, SWIPE_MAX_Y = 40;

  document.addEventListener('pointerdown', (e) => {
    if (editMode) return;
    if (!grid.contains(e.target) && e.target !== grid) return;
    swipeStart = { x: e.clientX, y: e.clientY };
  }, true);

  document.addEventListener('pointerup', (e) => {
    if (!swipeStart) return;
    const dx = e.clientX - swipeStart.x;
    const dy = e.clientY - swipeStart.y;
    swipeStart = null;
    if (Math.abs(dx) >= SWIPE_MIN_X && Math.abs(dy) <= SWIPE_MAX_Y) {
      if (dx < 0) setPage(currentPageIdx + 1);
      else setPage(currentPageIdx - 1);
      swipeJustHappened = true;
      setTimeout(() => { swipeJustHappened = false; }, 150);
    }
  }, true);

  // --- UI helpers ---------------------------------------------------------

  function showToast(msg) {
    toast.textContent = msg;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.hidden = true, 2500);
  }

  // --- Init ---------------------------------------------------------------

  (async function init() {
    try {
      await loadSounds();
      await loadConfig();
      await loadObsData();
      render();
    } catch (e) {
      console.error(e);
      showToast('Error cargando configuración');
    }
    connectWs();
    setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25000);
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
  })();
})();
