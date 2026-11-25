/* Colaboração por célula: revisão atômica, rascunho local e sincronização. */
(() => {
  'use strict';
  const editor = document.getElementById('plano-editor');
  if (!editor) return;
  const endpoint = editor.dataset.endpoint;
  let editable = editor.dataset.editavel === 'true';
  const canRead = editor.dataset.leitura === 'true';
  const tbody = document.getElementById('plano-linhas');
  const status = document.getElementById('plano-status');
  const retry = document.getElementById('plano-retry');
  const csrf = editor.querySelector('[name=csrfmiddlewaretoken]').value;
  const states = new Map();
  let polling = false;
  let adding = false;
  let permissionLost = false;
  let storageFailed = false;
  let syncPromise = null;
  const prefix = `plano:${editor.dataset.user}:${editor.dataset.sala}:`;
  const key = id => prefix + id;
  const storage = {
    get(id) { try { return JSON.parse(localStorage.getItem(key(id))); } catch { return null; } },
    set(s) { try { localStorage.setItem(key(s.id), JSON.stringify({ value: s.input.value, base: s.base, revisao: s.revisao })); } catch { storageFailed = true; } },
    remove(id) { try { localStorage.removeItem(key(id)); } catch { /* Salvamento no servidor continua disponível. */ } }
  };
  function dirtyStates() { return [...states.values()].filter(s => s.dirty || s.saving || s.conflict); }
  function updateStatus() {
    if (!canRead) return;
    const dirty = dirtyStates();
    if (permissionLost) status.textContent = 'Sua permissão mudou. O texto pendente foi preservado neste navegador.';
    else if (dirty.some(s => s.conflict)) status.textContent = 'Há alterações no mesmo campo. Escolha qual texto salvar abaixo.';
    else if (dirty.some(s => s.failed)) status.textContent = 'Não foi possível salvar. Tentaremos novamente; mantenha esta página aberta.';
    else if (dirty.length) status.textContent = 'Salvando alterações…';
    else status.textContent = editable ? 'Todas as alterações salvas' : 'Somente leitura';
    if (storageFailed && dirty.length) status.textContent += ' O rascunho local está indisponível.';
    if (retry) retry.hidden = permissionLost || !dirty.some(s => s.failed);
  }
  function resize(input) {
    input.style.height = 'auto';
    input.style.height = Math.max(100, Math.min(input.scrollHeight, 600)) + 'px';
  }
  function applyRemote(s, remote) {
    s.base = remote.texto;
    s.revisao = remote.revisao;
    s.input.value = remote.texto;
    s.dirty = false;
    s.failed = false;
    s.conflict = null;
    s.conflictBox.hidden = true;
    s.note.textContent = remote.autor ? `Salvo por ${remote.autor}` : '';
    storage.remove(s.id);
    resize(s.input);
  }
  function showConflict(s, remote) {
    s.conflict = remote;
    s.failed = false;
    s.conflictBox.replaceChildren();
    s.conflictBox.hidden = false;
    const title = document.createElement('strong');
    title.textContent = 'Outra pessoa alterou este campo. Seu texto continua acima.';
    const label = document.createElement('div');
    label.textContent = `Texto salvo${remote.autor ? ` por ${remote.autor}` : ''}:`;
    const text = document.createElement('p');
    text.textContent = remote.texto || '(campo vazio)';
    const useRemote = document.createElement('button');
    useRemote.type = 'button'; useRemote.className = 'btn btn-sm btn-outline-secondary';
    useRemote.textContent = 'Usar texto salvo';
    useRemote.addEventListener('click', () => { applyRemote(s, s.conflict); updateStatus(); });
    const keep = document.createElement('button');
    keep.type = 'button'; keep.className = 'btn btn-sm btn-outline-primary';
    keep.textContent = 'Salvar meu texto';
    keep.addEventListener('click', () => {
      s.revisao = s.conflict.revisao; s.base = s.conflict.texto;
      s.conflict = null; s.conflictBox.hidden = true;
      storage.set(s); save(s);
    });
    s.conflictBox.append(title, label, text, useRemote, keep);
    s.note.textContent = 'Aguardando sua escolha';
    storage.set(s); updateStatus();
  }
  function disableEditing() {
    permissionLost = true; editable = false;
    states.forEach(s => { s.input.readOnly = true; });
    editor.querySelectorAll('button').forEach(button => { button.disabled = true; });
    updateStatus();
  }
  function save(s) {
    if (s.pending) return s.pending;
    s.pending = saveOnce(s).finally(() => { s.pending = null; });
    return s.pending;
  }
  async function saveOnce(s) {
    clearTimeout(s.timer);
    if (!editable || !s.dirty || s.saving || s.conflict) return;
    s.saving = true; s.failed = false;
    const sent = s.input.value;
    const revisao = s.revisao;
    s.note.textContent = 'Salvando…'; updateStatus();
    try {
      const response = await fetch(endpoint, {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ id: s.id, texto: sent, revisao }), keepalive: true,
        signal: AbortSignal.timeout(20000)
      });
      if (response.status === 403 || response.redirected) { disableEditing(); return; }
      const data = await response.json();
      if (response.status === 409) { showConflict(s, data.linha); return; }
      if (!response.ok) throw new Error(data.erro || 'Falha ao salvar');
      s.base = data.linha.texto; s.revisao = data.linha.revisao;
      s.dirty = s.input.value !== sent;
      s.note.textContent = s.dirty ? 'Alteração pendente' : 'Salvo';
      if (s.dirty) storage.set(s); else storage.remove(s.id);
    } catch (error) {
      s.failed = true; s.dirty = true;
      s.note.textContent = 'Ainda não salvo. Seu texto permanece neste campo.';
      storage.set(s);
    } finally {
      s.saving = false; updateStatus();
      if (editable && s.dirty && !s.conflict) s.timer = setTimeout(() => save(s), s.failed ? 5000 : 400);
    }
  }
  function createRow(line) {
    const row = document.createElement('tr'); row.dataset.linha = line.id; row.dataset.tipo = line.tipo;
    if (line.tipo === 'objetivo') row.className = 'plano-objective';
    const th = document.createElement('th'); th.scope = 'row';
    const label = document.createElement('label'); label.htmlFor = `linha-${line.id}`; label.textContent = line.rotulo;
    th.append(label);
    if (editable && line.tipo === 'objetivo') {
      const button = document.createElement('button'); button.type = 'button';
      button.className = 'plano-add-meta'; button.dataset.objetivo = line.id;
      button.textContent = '+ Meta'; button.setAttribute('aria-label', `Adicionar meta ao ${line.rotulo}`); th.append(button);
    }
    const td = document.createElement('td');
    const input = document.createElement('textarea'); input.id = label.htmlFor;
    input.rows = 3; input.maxLength = 50000; input.readOnly = !editable;
    input.placeholder = {objetivo: 'Escreva o objetivo…', meta: 'Escreva o texto desta meta…',
      estrategia: 'Escreva o texto desta estratégia…', indicador: 'Escreva o texto deste indicador…'}[line.tipo];
    input.value = line.texto;
    const note = document.createElement('div'); note.className = 'plano-cell-status small text-muted'; note.setAttribute('role', 'status');
    const box = document.createElement('div'); box.className = 'plano-conflict'; box.hidden = true;
    td.append(input, note, box); row.append(th, td);
    return row;
  }
  function register(line, row) {
    const s = { ...line, base: line.texto, input: row.querySelector('textarea'), note: row.querySelector('.plano-cell-status'),
      conflictBox: row.querySelector('.plano-conflict'), dirty: false, saving: false, failed: false, conflict: null };
    states.set(line.id, s);
    if (editable) {
      const draft = storage.get(line.id);
      if (draft && typeof draft.value === 'string' && draft.value !== line.texto) {
        s.input.value = draft.value; s.dirty = true;
        if (draft.base !== line.texto) showConflict(s, line);
        else { s.note.textContent = 'Rascunho recuperado. Salvando…'; s.timer = setTimeout(() => save(s), 600); }
      } else if (draft) storage.remove(line.id);
      s.input.addEventListener('input', () => {
        s.dirty = s.input.value !== s.base;
        s.failed = false;
        if (s.dirty || s.saving) storage.set(s); else storage.remove(s.id);
        s.note.textContent = s.dirty ? 'Alteração pendente' : 'Salvo';
        resize(s.input); clearTimeout(s.timer);
        if (!s.conflict) s.timer = setTimeout(() => save(s), 650);
        updateStatus();
      });
      s.input.addEventListener('blur', () => save(s));
    }
    resize(s.input);
    return row;
  }
  function mergeLines(lines) {
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]; const s = states.get(line.id);
      if (!s) {
        const row = createRow(line);
        const next = lines.slice(i + 1).map(l => tbody.querySelector(`[data-linha="${l.id}"]`)).find(Boolean);
        tbody.insertBefore(row, next || null); register(line, row);
      } else if (!s.dirty && !s.saving && !s.conflict && line.revisao > s.revisao) applyRemote(s, line);
    }
    refreshActions(lines);
  }
  function refreshActions(lines) {
    if (!editable) return;
    lines.filter(line => line.fim_objetivo).forEach(line => {
      let actions = tbody.querySelector(`[data-grupo="${line.grupo_id}"]`);
      if (!actions) {
        actions = document.createElement('tr');
        actions.className = 'plano-row-actions'; actions.dataset.grupo = line.grupo_id;
        const cell = document.createElement('td'); cell.colSpan = 2;
        const buttons = document.createElement('div'); buttons.className = 'd-flex flex-wrap gap-2';
        for (const [tipo, rotulo] of [['estrategia', 'estratégia'], ['indicador', 'indicador']]) {
          const button = document.createElement('button'); button.type = 'button';
          button.className = 'btn btn-sm btn-outline-primary'; button.dataset.adicionar = tipo;
          button.dataset.grupoId = line.grupo_id; button.textContent = `+ Adicionar ${rotulo}`;
          button.setAttribute('aria-label', `Adicionar ${rotulo} ao ${line.grupo_rotulo}`);
          buttons.append(button);
        }
        cell.append(buttons); actions.append(cell);
      }
      const last = tbody.querySelector(`[data-linha="${line.id}"]`);
      if (last.nextElementSibling !== actions) last.after(actions);
    });
  }
  function sync() {
    if (syncPromise) return syncPromise;
    syncPromise = syncOnce().finally(() => { syncPromise = null; });
    return syncPromise;
  }
  async function syncOnce() {
    if (!canRead || polling || document.hidden) return;
    polling = true;
    try {
      const response = await fetch(endpoint, { credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(15000) });
      if (response.status === 403 || response.redirected) { disableEditing(); return; }
      if (!response.ok) return;
      const data = await response.json();
      if (!data.editavel && editable) disableEditing();
      mergeLines(data.linhas); updateStatus();
    } catch { /* Erros de rede na leitura não descartam rascunhos. */ }
    finally { polling = false; }
  }
  async function add(tipo, objetivoId) {
    if (!editable || adding) return;
    adding = true;
    try {
      const response = await fetch(endpoint, { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ acao: 'adicionar', tipo, objetivo_id: objetivoId }), signal: AbortSignal.timeout(20000) });
      if (response.status === 403 || response.redirected) { disableEditing(); return; }
      if (!response.ok) throw new Error();
      const data = await response.json();
      // Aguarde uma consulta já em andamento antes de buscar a nova linha.
      if (syncPromise) await syncPromise;
      await sync();
      states.get(data.linha.id)?.input.focus();
    } catch { status.textContent = 'Não foi possível adicionar a linha. Tente novamente.'; }
    finally { adding = false; }
  }
  JSON.parse(document.getElementById('plano-dados').textContent).forEach(line => register(line, tbody.querySelector(`[data-linha="${line.id}"]`)));
  tbody.addEventListener('click', event => {
    const action = event.target.closest('[data-adicionar]');
    if (action) { add(action.dataset.adicionar, Number(action.dataset.grupoId)); return; }
    const button = event.target.closest('[data-objetivo]');
    if (button) add('meta', Number(button.dataset.objetivo));
  });
  document.getElementById('plano-add-objective')?.addEventListener('click', () => add('objetivo'));
  retry?.addEventListener('click', () => states.forEach(s => save(s)));
  window.addEventListener('online', () => { states.forEach(s => save(s)); sync(); });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) states.forEach(s => { if (s.dirty) { storage.set(s); save(s); } });
    else sync();
  });
  window.addEventListener('beforeunload', event => {
    if (dirtyStates().length) { states.forEach(s => { if (s.dirty) storage.set(s); }); event.preventDefault(); event.returnValue = ''; }
  });
  // A aba de exportação só abre depois que os textos pendentes chegam ao servidor.
  document.querySelectorAll('.plano-tabs a').forEach(link => link.addEventListener('click', async event => {
    if (!dirtyStates().length) return;
    event.preventDefault();
    await Promise.all([...states.values()].map(async s => {
      if (s.pending) await s.pending;
      await save(s);
    }));
    if (dirtyStates().length) { updateStatus(); status.scrollIntoView({ block: 'center' }); }
    else window.location.assign(link.href);
  }));
  if (canRead) { setInterval(sync, 4000); sync(); }
  updateStatus();
})();
