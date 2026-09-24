// The page's logic. It only talks to the API (fetch); every rule is decided there.
// TOKEN is written into index.html by the server at each start and goes with every API call.
const STATUS ={pending: 'por responder', draft: 'rascunho', error: 'erro no envio', sending: 'a enviar', uncertain: 'envio incerto'};
const AUX_KINDS = ['reminder', 'consent_request', 'visits_closed'];
const FIELDS = ['reference', 'sender', 'listing_id', 'listing_url', 'advertiser', 'advertised_rent_eur', 'description'];
const $ = id => document.getElementById(id);
let state = {properties: []}, settings = null, preview = null;

// Only the visual preference is stored locally; never account or email content.
const THEMES = ['night', 'day', 'indigo', 'amber', 'racing'];
function applyTheme(theme) {
  const chosen = THEMES.includes(theme) ? theme : 'night';
  document.documentElement.dataset.theme = chosen;
  $('theme-select').value = chosen;
}
try { applyTheme(localStorage.getItem('bot-mail-theme')); }
catch { applyTheme('night'); }
$('theme-select').addEventListener('change', event => {
  applyTheme(event.target.value);
  try { localStorage.setItem('bot-mail-theme', event.target.value); } catch { /* Storage may be unavailable. */ }
  applySkin();
  // A skin brings its own instruments: the property panel on screen is redrawn with them.
  if (settings && !$('tab-properties').hidden) renderPropertySlider();
});
let activeTab = 'dashboard', skinSelector = null;
const TAB_NAMES = {dashboard: 'Painel', replies: 'Respostas', properties: 'Imóveis', contacts: 'Contactos', agenda: 'Agenda',
  voice: 'Voz e estilo'};

// Skins: a rich theme goes beyond colours. It may bring the words on the page headings, the instruments on
// each property's panel (from the same signals: see panelSignals), a tab selector of its own and an analog
// clock; its stylesheet is in frontend/themes/. The plain themes use none of it. 90's RacingCar (id racing) is the first; a
// yacht or a grand-luxury skin fills the same four slots with its own words, dials, selector and clock.
const SKINS = {
  racing: {
    words: {
      'dashboard.eyebrow': 'COCKPIT', 'dashboard.title': 'O teu dia, a todo o gás.',
      'dashboard.step': 'Contactos, respostas e imóveis: todos os instrumentos à vista.',
      'activity.eyebrow': 'TELEMETRIA', 'activity.title': 'Pedidos e respostas, volta a volta',
      'setup.eyebrow': 'CHECK-LIST DE PARTIDA', 'setup.title': 'Pronto para arrancar',
      'portfolio.eyebrow': 'GARAGEM', 'portfolio.title': 'Os teus imóveis, na garagem',
      'replies.eyebrow': 'BOX', 'replies.title': 'Paragem na box: rápida, mas sem erros.',
      'properties.eyebrow': 'GARAGEM', 'properties.title': 'Cada imóvel, o seu motor.',
      'properties.step': 'Um quadro de instrumentos por imóvel: temperatura, rotação, velocidade e combustível.',
      'contacts.eyebrow': 'PADDOCK', 'contacts.title': 'Quem já passou pela box, num só registo.',
      'agenda.eyebrow': 'GRELHA DA SEMANA', 'agenda.title': 'A semana, prova a prova.',
      'voice.eyebrow': 'AFINAÇÃO', 'voice.title': 'Afinação: as tuas palavras, o teu estilo.',
      'cluster.eyebrow': 'QUADRO DE INSTRUMENTOS', 'cluster.chart': 'TELEMETRIA DESTE IMÓVEL',
      'lamp.heat': 'Sobreaquecido', 'heat.limit': 'H =', 'trip.title': 'Computador de bordo',
    },
    instruments: carInstruments,
    selector: gearbox,
  },
};
function skin() { return SKINS[document.documentElement.dataset.theme] || null; }
function word(key, plain) { return skin()?.words?.[key] ?? plain; }
// The headings marked data-word keep their plain text in data-plain, to come back to in a plain theme.
function applySkin() {
  const current = skin();
  for (const node of document.querySelectorAll('[data-word]')) {
    node.dataset.plain ??= node.textContent;
    node.textContent = current?.words?.[node.dataset.word] ?? node.dataset.plain;
  }
  $('skin-selector').replaceChildren();
  skinSelector = current?.selector ? current.selector($('skin-selector')) : null;
  skinSelector?.update(activeTab);
}

// 90's RacingCar's tab selector: the open gated gearbox of a GT of the time. Gears 1 to 6 are the six tabs (reverse is
// only there for the look); the lever goes through neutral like a real one, and a click on a gear changes
// tab. It repeats the nav for the mouse: the nav itself stays the accessible way (aria-hidden here).
const GEARS = {dashboard: [71, 29], replies: [71, 103], properties: [106, 29], contacts: [106, 103], agenda: [141, 29],
  voice: [141, 103]};
function gearbox(box) {
  const neutral = 66, gate = 'M36 66H141M36 66V29M71 29V103M106 29V103M141 29V103';
  const gradient = (id, attrs, colours) => svg(attrs.r ? 'radialGradient' : 'linearGradient', {id, ...attrs},
    colours.map(([offset, colour]) => svg('stop', {offset, 'stop-color': colour})));
  const channel = (colour, width, extra = {}) => svg('path', {d: gate, fill: 'none', stroke: colour, 'stroke-width': width,
    'stroke-linecap': 'round', ...extra});
  const tabs = Object.keys(GEARS);
  const labels = [svg('text', {x: 36, y: 14, class: 'gate-label'}, 'R'), ...tabs.map((tab, i) => svg('text', {x: GEARS[tab][0],
    y: GEARS[tab][1] < neutral ? 14 : 120, class: 'gate-label', 'data-tab': tab}, String(i + 1)))];
  const hits = tabs.map(tab => svg('circle', {cx: GEARS[tab][0], cy: GEARS[tab][1], r: 13, fill: 'transparent', class: 'gate-hit',
    'data-tab': tab}, svg('title', {}, TAB_NAMES[tab])));
  for (const node of [...labels, ...hits]) if (node.dataset.tab) node.addEventListener('click', () => showTab(node.dataset.tab));
  const knob = svg('g', {class: 'gate-knob'},
    svg('circle', {cx: 0.8, cy: 3.2, r: 13, fill: '#000', opacity: 0.45}),
    svg('circle', {r: 13, fill: 'url(#gate-collar)'}), svg('circle', {r: 10.8, fill: 'url(#gate-wood)'}),
    svg('path', {d: 'M-4 -4.5v9M4 -4.5v9M-4 0h8', stroke: '#f3e6d0', 'stroke-width': 1.3, 'stroke-linecap': 'round', opacity: 0.9}),
    svg('ellipse', {cx: -3.2, cy: -5, rx: 5, ry: 2.8, fill: '#fff', opacity: 0.18}));
  box.append(svg('svg', {viewBox: '0 0 176 132', class: 'gearbox'},
    svg('defs', {},
      gradient('gate-alu', {x1: 0, y1: 0, x2: 0, y2: 1}, [[0, '#f1f3f5'], [0.45, '#c3c7cc'], [0.55, '#dadde0'], [1, '#9aa0a7']]),
      gradient('gate-collar', {x1: 0, y1: 0, x2: 0, y2: 1}, [[0, '#fdfdfd'], [0.5, '#8d9299'], [1, '#e3e5e8']]),
      gradient('gate-wood', {cx: 0.38, cy: 0.32, r: 0.75}, [[0, '#b0652f'], [0.45, '#6e3414'], [1, '#2c1206']]),
      svg('pattern', {id: 'gate-brush', width: 176, height: 3, patternUnits: 'userSpaceOnUse'},
        svg('rect', {width: 176, height: 1, fill: '#fff', opacity: 0.14}),
        svg('rect', {y: 2, width: 176, height: 0.6, fill: '#000', opacity: 0.07}))),
    svg('rect', {x: 2, y: 2, width: 172, height: 128, rx: 16, fill: 'url(#gate-alu)', stroke: '#5d6268'}),
    svg('rect', {x: 2, y: 2, width: 172, height: 128, rx: 16, fill: 'url(#gate-brush)'}),
    svg('rect', {x: 6, y: 6, width: 164, height: 120, rx: 13, fill: 'none', stroke: '#ffffff8c'}),
    [[15, 15, 30], [161, 15, 110], [15, 117, 70], [161, 117, 150]].map(([x, y, turn]) =>
      svg('g', {transform: `translate(${x} ${y}) rotate(${turn})`},
        svg('circle', {r: 4, fill: 'url(#gate-collar)', stroke: '#4a4e54', 'stroke-width': 0.6}),
        svg('path', {d: 'M-2.6 0h5.2', stroke: '#3a3d42', 'stroke-width': 1.2}))),
    channel('#ffffffa6', 14, {transform: 'translate(0 1.3)'}), channel('#0b0b0c', 12.5), channel('#1d1d20', 6),
    labels, hits, knob));
  let at = null, timers = [];
  const place = ([x, y]) => { knob.style.transform = `translate(${x}px, ${y}px)`; };
  return {update(tab) {
    const target = GEARS[tab];
    if (!target) return;
    for (const label of labels) label.classList.toggle('active', label.dataset.tab === tab);
    timers.forEach(clearTimeout);
    timers = [];
    if (!at || matchMedia('(prefers-reduced-motion: reduce)').matches) {  // first draw: straight into gear
      knob.style.transition = 'none'; place(target); knob.getBoundingClientRect(); knob.style.transition = '';
    } else if (target !== at) {  // through neutral: along the slot, across, into the gear
      timers = [[at[0], neutral], [target[0], neutral], target].map((point, i) => setTimeout(() => place(point), i * 140));
    }
    at = target;
  }};
}

// Emails are untrusted: every value goes in as text, never as HTML.
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value !== false && value != null) node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat(Infinity)) if (child != null && child !== false && child !== '') node.append(child);
  return node;
}

async function call(path, body) {
  $('busy').hidden = false;
  try {
    const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST',
      headers: {'Content-Type': 'application/json', 'X-Bot-Mail-Token': TOKEN},
      body: body === undefined ? undefined : JSON.stringify(body)});
    const data = await response.json().catch(() => ({error: response.statusText}));
    if (!response.ok) throw new Error(data.error || 'Erro inesperado.');
    return data;
  } finally { $('busy').hidden = true; }
}

function toast(text, kind = 'ok') {
  const box = $('toast');
  box.textContent = text; box.className = kind; box.hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { box.hidden = true; }, 7000);
}

// button, when given, shows the click was received and is still running: disabled and relabelled
// until the action settles, whether it succeeds or fails (the error itself goes to the toast).
async function run(action, button) {
  const original = button?.textContent;
  if (button) { button.disabled = true; button.textContent = 'A trabalhar…'; }
  try { await action(); }
  catch (error) { toast(error.message, 'bad'); }
  // data-hold: something else keeps it off (an empty API tank): finishing a click must not switch it back on.
  finally { if (button) { button.disabled = button.dataset.hold === '1'; button.textContent = original; } }
}

async function copyText(text, done, fallbackBox) {
  try { await navigator.clipboard.writeText(text); toast(done); }
  catch { fallbackBox.open = true; toast('Não consegui copiar sozinho: seleciona o texto do prompt e copia-o.', 'warn'); }
}

function showTab(name) {
  activeTab = name;
  skinSelector?.update(name);
  document.querySelectorAll('nav [data-tab]').forEach(button => {
    button.classList.toggle('active', button.dataset.tab === name);
    if (button.dataset.tab === name) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  $('page-label').textContent = TAB_NAMES[name];
  for (const tab of Object.keys(TAB_NAMES)) $('tab-' + tab).hidden = tab !== name;
  window.scrollTo({top: 0, behavior: 'instant'});
  if (name === 'dashboard') { run(loadMetrics); run(loadDigest); }
  if (name === 'contacts') run(loadContacts);
  if (name === 'agenda') renderAgenda();
  // Sends, refills and reads elsewhere change its numbers: the cluster is never shown out of date.
  if (name === 'properties' && settings) renderPropertySlider();
}

// The chart is drawn by hand: the page may not load anything from outside.
function svg(tag, attrs = {}, ...children) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  node.append(...children.flat(Infinity).filter(child => child != null));
  return node;
}

// What each field is: RAG facts, a prompt, the voice, or text carried to and from ChatGPT.
const KINDS = {rag: ['RAG', 'Factos que o assistente consulta para responder'], prompt: ['Prompt', 'Instruções de como responder'],
  voice: ['Voz', 'Estilo comum a todos os imóveis'], copy: ['Copiar/colar', 'Texto que levas e trazes do ChatGPT']};
function kind(type) { const [label, title] = KINDS[type]; return el('span', {class: 'kind kind-' + type, title}, label); }
const VISIT_STATES = {nao_quer: 'não quer visitar', outra_data: 'só pode noutra data'};
function dayLabel(day) {
  return new Date(day + 'T12:00:00').toLocaleDateString('pt-PT', {weekday: 'long', day: '2-digit', month: '2-digit'});
}
function slotLabel(value) { const [day, time] = String(value).split(' '); return `${dayLabel(day)}, ${time}`; }

function when(value) { return value ? new Date(value).toLocaleString('pt-PT', {dateStyle: 'short', timeStyle: 'short'}) : ''; }
function currentQueue() {
  return state.properties.find(queue => String(queue.property_ref ?? '') === $('queue').value) || state.properties[0];
}
function queueRef() { return currentQueue()?.property_ref ?? null; }
function selectedIds() { return [...document.querySelectorAll('.pick:checked')].map(box => box.dataset.id); }
function nameOf(id) {
  const email = (currentQueue()?.emails || []).find(item => item.id === id) || {};
  return (email.customer || {}).name || id;
}

// Workflow steps 01-04: a step only ever looks "done" through this call, never by coincidence (e.g. an
// empty textarea after saving looks exactly like one nobody has touched yet, unless something marks it).
function markStep(id, done) {
  const li = document.querySelector(`.workflow li[data-step="${id}"]`);
  if (li) li.classList.toggle('done', done);
}
// Saving drafts or sending redraws the queue, which resets the steps; the earlier steps of the same
// batch were still done, so they keep their mark.
function keepSteps(redraw) {
  const done = [...document.querySelectorAll('.workflow li.done')].map(li => li.dataset.step);
  redraw();
  done.forEach(step => markStep(step, true));
}

function renderState() {
  $('account').textContent = state.account || '';
  $('nav-count').textContent = state.properties.reduce((n, q) => n + q.emails.length, 0);
  $('error').hidden = !state.error; $('error').textContent = state.error || '';
  const select = $('queue'), chosen = select.value;
  select.replaceChildren(...state.properties.map(queue => el('option', {value: queue.property_ref ?? ''}, queue.property_ref ?? 'Todos')));
  if ([...select.options].some(option => option.value === chosen)) select.value = chosen;
  const queue = currentQueue();
  $('last-read').textContent = queue?.last_read_at ? 'Última leitura: ' + when(queue.last_read_at) : '';
  const emails = queue?.emails || [];
  $('emails').replaceChildren(...(emails.length ? emails.map(card)
    : [el('div', {class: 'empty-state'}, el('strong', {}, state.error ? 'Configuração pendente' : 'Tudo em dia.'), state.error ? 'Verifica o aviso acima para continuar.' : 'Não há emails pendentes. Faz uma nova leitura quando quiseres.')]));
  $('instructions').textContent = queue?.instructions || '';
  preview = null; $('preview-box').replaceChildren();
  // A fresh batch of emails makes any earlier "done" (import, send) stale: back to work, not finished.
  $('import-status').hidden = true; markStep('import-step', false); markStep('send-step', false);
  updateSelection();
  holdFuelButtons();  // the email cards were just rebuilt (or the queue changed), their API buttons with them
}

function updateSelection() {
  const count = selectedIds().length;
  $('selection-count').textContent = `${count} selecionado(s)`;
  $('build-prompt').disabled = !count;
  $('preview').disabled = !count;
  markStep('inbox-step', count > 0);
  // A prompt already created stops matching once the selection (or the extra instructions) changes.
  $('copy-prompt').disabled = true;
  $('prompt').textContent = ''; $('prompt-box').open = false;
  markStep('prepare-step', false);
}

// The whole exchange with this customer, oldest first, ending in the current message: what the
// assistant also gets in the prompt, so the page never shows less context than it hands over.
function historyBlock(email) {
  if (email.visit_window || AUX_KINDS.includes(email.kind) || email.closing) return false;
  const history = email.history || [];
  const turns = [...history, {who: 'cliente', text: email.body_text || '', at: (email.date || '').slice(0, 10)}];
  return el('details', {},
    el('summary', {class: 'muted small'}, 'Email completo' + (history.length ? ` (${history.length + 1} trocas)` : '')),
    turns.map(turn => el('div', {class: 'history-turn'},
      el('p', {class: 'muted small'}, turn.who === 'cliente' ? 'Cliente' : 'Nós', turn.at ? ' · ' + turn.at : ''),
      el('pre', {}, turn.text))));
}

function card(email) {
  const customer = email.customer || {}, sender = (email.from || [])[0] || {};
  const saved = email.reply_text || '';
  const draft = el('textarea', {'aria-label': 'Rascunho da resposta', rows: 7, placeholder: 'Rascunho: cola a resposta do ChatGPT no passo 3 ou escreve aqui.'}, saved);
  const contact = [customer.email || (email.recipient || {}).email, customer.phone].filter(Boolean).join(' · ');
  const ignoreEmail = customer.email || (email.recipient || {}).email;
  const ignoreTarget = ignoreEmail && {email: ignoreEmail, name: customer.name};
  // Whether the textarea still matches what api/drafts last saved: nothing else marks that on the page,
  // so after pasting 40 answers or editing one by hand, it is easy to lose track of what still needs a click.
  const saveButton = el('button', {}, 'Guardar rascunho');
  const saveStatus = el('span', {class: 'muted small save-status'});
  const refreshSaveStatus = () => {
    if (!draft.value.trim()) { saveStatus.textContent = ''; saveButton.classList.remove('primary'); return; }
    const dirty = draft.value !== saved;
    saveStatus.textContent = dirty ? 'Por guardar' : 'Guardado';
    saveButton.classList.toggle('primary', dirty);
    saveStatus.classList.toggle('warn', dirty);
  };
  draft.addEventListener('input', refreshSaveStatus);
  refreshSaveStatus();
  saveButton.addEventListener('click', event => run(async () => {
    state = await call('api/drafts', {property_ref: queueRef(), replies: [{id: email.id, reply_text: draft.value}]});
    renderState(); toast('Rascunho guardado.');
  }, event.currentTarget));
  // Just this one, as it is in the box now: the same save → preview → send as the batch in step 04 (the
  // preview token is tied to this exact text), with the recipient and subject confirmed before it goes.
  const sendOne = !email.blocked && el('button', {class: 'send-action', onclick: event => run(async () => {
    if (!draft.value.trim()) throw new Error('Escreve o texto antes de enviar.');
    state = await call('api/drafts', {property_ref: queueRef(), replies: [{id: email.id, reply_text: draft.value}]});
    const check = await call('api/preview', {property_ref: queueRef(), ids: [email.id]});
    const [reply] = check.replies;
    const warnings = (reply.warnings || []).length ? `\n\nAvisos: ${reply.warnings.join(' ')}` : '';
    if (!confirm(`Enviar agora só este email, tal como está?\n\nPara: ${reply.to}\nAssunto: ${reply.subject}${warnings}`)) {
      renderState(); return;
    }
    const result = await call('api/send', {property_ref: queueRef(), preview_token: check.preview_token, confirmed: true});
    const sent = result.results[0]?.status === 'sent';
    state = await call('api/state'); renderState();
    toast(sent ? `Enviado para ${reply.to}. Saiu da lista.` : 'Não saiu: vê o aviso no próprio email antes de repetir.',
      sent ? 'ok' : 'warn');
  }, event.currentTarget)}, 'Enviar só este');
  return el('article', {class: 'card email-card' + (email.blocked ? ' blocked' : '')},
    el('div', {class: 'card-head'},
      el('label', {class: 'who'}, el('input', {type: 'checkbox', class: 'pick', 'data-id': email.id, checked: !email.blocked, disabled: !!email.blocked}),
        el('strong', {}, customer.name || sender.name || sender.email || 'Sem nome')),
      email.interaction && el('span', {class: 'tag'}, email.interaction + '.ª interação'),
      el('span', {class: 'tag' + (email.reply_status === 'draft' ? ' draft' : '')}, STATUS[email.reply_status] || email.reply_status || ''),
      email.kind === 'visit_proposal' && el('span', {class: 'tag visit'}, 'proposta de visita'),
      email.kind === 'reminder' && el('span', {class: 'tag visit'}, email.reminder === '4d' ? 'lembrete aos 4 dias' : 'lembrete aos 2 dias'),
      email.kind === 'consent_request' && el('span', {class: 'tag visit'}, 'pedido de consentimento'),
      email.closing && el('span', {class: 'tag visit'}, 'visitas fechadas'),
      email.consent_confirmed && el('span', {class: 'tag visit'}, 'consentimento: sim'),
      email.visit_slot && el('span', {class: 'tag visit'}, 'visita ' + slotLabel(email.visit_slot)),
      email.visit_status && el('span', {class: 'tag warn'}, VISIT_STATES[email.visit_status] || email.visit_status),
      el('span', {class: 'muted small'}, when(email.date))),
    contact && el('div', {class: 'muted small'}, contact),
    email.blocked && el('p', {class: 'alert bad'}, email.blocked),
    (email.warnings || []).map(warning => el('p', {class: 'alert warn'}, warning)),
    email.reply_error && el('p', {class: 'alert bad'}, email.reply_error),
    email.consent_suggested && el('p', {class: 'alert warn'}, 'O cliente parece ter dito que sim: confirma para gravar em contactos.csv.'),
    el('blockquote', {}, email.visit_window
      ? `Proposta de visita: ${dayLabel(email.visit_window.day)}, das ${email.visit_window.start} às ${email.visit_window.end}.`
      : AUX_KINDS.includes(email.kind) || email.closing ? '(sem mensagem nova do cliente: email preparado automaticamente, ver o rascunho abaixo)'
      : customer.message || email.body_text || ''),
    historyBlock(email),
    draft,
    el('div', {class: 'actions'},
      saveButton, saveStatus, sendOne,
      email.consent_suggested && el('button', {class: 'primary', onclick: event => run(async () => {
        state = await call('api/consent/confirm', {property_ref: queueRef(), id: email.id});
        renderState(); toast('Consentimento confirmado e registado em contactos.csv.');
      }, event.currentTarget)}, 'Confirmar consentimento (RGPD)'),
      el('button', {class: 'link danger', onclick: event => run(async () => {
        if (!confirm('Retirar este email da fila sem responder? O Gmail não é alterado e o email não volta a entrar.')) return;
        state = await call('api/dismiss', {property_ref: queueRef(), ids: [email.id]});
        renderState(); toast('Email retirado da fila.');
      }, event.currentTarget)}, 'Retirar da fila'),
      ignoreTarget && el('button', {class: 'link danger', onclick: event => run(async () => {
        if (!confirm(`${ignoreTarget.name || ignoreTarget.email} disse que não tem interesse: ignorar sempre, `
            + 'neste imóvel? Sai da fila e nunca mais volta a entrar, mesmo que escreva de novo — e não recebe '
            + 'propostas de visita nem outros envios automáticos. Podes reverter mais tarde em Imóveis.')) return;
        const result = await call('api/contacts/ignore', {property_ref: queueRef(), email: ignoreTarget.email,
          ignored: true, kind: 'grey', reason: 'Cliente disse que não tem interesse.'});
        state = result.state; renderState();
        toast(`${ignoreTarget.name || ignoreTarget.email} passou a ser ignorado(a) neste imóvel.`);
      }, event.currentTarget)}, 'Não tem interesse'),
      ignoreTarget && el('button', {class: 'link danger', onclick: event => run(async () => {
        if (!confirm(`Ignorar ${ignoreTarget.name || ignoreTarget.email} sempre, neste imóvel? Este email sai da `
            + 'fila e nunca mais volta a entrar, mesmo que escreva de novo — e não recebe propostas de visita '
            + 'nem outros envios automáticos. Podes reverter mais tarde em Imóveis.')) return;
        const result = await call('api/contacts/ignore', {property_ref: queueRef(), email: ignoreTarget.email,
          ignored: true, kind: 'black'});
        state = result.state; renderState();
        toast(`${ignoreTarget.name || ignoreTarget.email} passou a ser ignorado(a) neste imóvel.`);
      }, event.currentTarget)}, 'Ignorar sempre')),
    noteBox(queueRef(), null, email.id));
}

// What the assistant knows about a property, exactly as it gets it: the property's base and the agency's.
function knowledgeView(ref) {
  const box = el('div', {class: 'knowledge-view'}, el('p', {class: 'muted small'}, 'A carregar…'));
  run(async () => {
    const data = await call('api/knowledge', {property_ref: ref});
    const block = (title, parts) => el('div', {class: 'knowledge-block'}, el('p', {class: 'eyebrow'}, title),
      parts.length ? parts.map(part => el('pre', {}, part.text)) : el('p', {class: 'muted small'}, 'Ainda vazio.'));
    box.replaceChildren(block('Deste imóvel', data.property), block('Da agência, para todos os imóveis', data.agency));
  });
  return box;
}

// One more fact while reviewing a reply: it goes to notas.md and the next prompt already carries it.
// emailId, only from a reply card: offers a second button that also redrafts that one email via the
// OpenAI API (same call as "Gerar respostas via API"), so the new fact is used right away, not just
// remembered for next time.
function noteBox(ref, onSaved, emailId) {
  const text = el('textarea', {rows: 2, 'aria-label': 'Informação a acrescentar ao conhecimento',
    placeholder: 'Ex.: Não tem arrecadação, mas pode guardar algumas coisas no lugar de garagem.'});
  const scope = el('select', {'aria-label': 'Onde guardar'},
    el('option', {value: 'property'}, 'Só este imóvel'), el('option', {value: 'agency'}, 'Todos os imóveis (agência)'));
  const saveNote = async () => {
    const result = await call('api/knowledge/note', {property_ref: ref, scope: scope.value, text: text.value});
    text.value = '';
    state = result.state; renderState();
    if (onSaved) onSaved();
    else await loadSettings();  // the Imóveis tab lists the knowledge files: keep it current
    return result;
  };
  const buttons = [el('button', {class: 'primary', onclick: event => run(async () => {
    const result = await saveNote();
    toast((result.scope === 'agency' ? 'Guardado no know-how da agência.' : 'Guardado no conhecimento do imóvel.')
      + ' O próximo prompt já o leva.');
  }, event.currentTarget)}, 'Guardar no conhecimento')];
  if (emailId) {
    buttons.push(el('button', {class: 'needs-fuel', title: settings?.openai_configured ? '' : 'Sem chave OpenAI configurada: o clique explica como.',
      onclick: event => run(async () => {
        if (!text.value.trim()) throw new Error('Escreve a informação antes de refazer a resposta.');
        await saveNote();
        const generated = await call('api/prompt/generate', {property_ref: ref, ids: [emailId], extra: ''});
        state = generated.state; renderState(); applyFuel(generated.fuel, ref);
        toast(generated.saved ? 'Conhecimento guardado e resposta refeita com a nova informação.'
          : 'Conhecimento guardado, mas a API não devolveu um rascunho novo para este email.');
      }, event.currentTarget)}, 'Guardar e refazer esta resposta (API)'));
  }
  return el('details', {class: 'note-box'}, el('summary', {class: 'muted small'}, '+ Acrescentar ao conhecimento'),
    text, el('div', {class: 'actions'}, scope, ...buttons));
}

function renderPreview() {
  const box = $('preview-box'), count = preview.replies.length;
  box.replaceChildren(
    el('p', {class: 'alert warn'}, `Vais enviar ${count} email(s) reais. Confere destinatários e textos; esta pré-visualização vale 15 minutos.`),
    ...preview.replies.map(reply => el('article', {class: 'card'},
      el('div', {}, el('strong', {}, 'Para: '), reply.to), el('div', {}, el('strong', {}, 'Assunto: '), reply.subject),
      (reply.warnings || []).map(warning => el('p', {class: 'alert warn'}, warning)), el('pre', {}, reply.reply_text))),
    el('div', {class: 'actions'},
      el('button', {class: 'primary send-action', onclick: event => run(async () => {
        if (!confirm(`Enviar agora ${count} email(s) reais?`)) return;
        const result = await call('api/send', {property_ref: queueRef(), preview_token: preview.preview_token, confirmed: true});
        const sent = result.results.filter(item => item.status === 'sent').length;
        state = await call('api/state'); keepSteps(renderState);  // renderState clears preview-box first
        $('preview-box').replaceChildren(el('p', {class: 'alert ' + (sent === result.results.length ? 'ok' : 'warn')},
          `✓ Enviados ${sent} de ${result.results.length} email(s).`
          + (sent < result.results.length ? ' Vê os avisos nos que ficaram.' : ' Passa ao próximo lote no passo 01.')));
        markStep('send-step', true);
        toast(`Enviados: ${sent} de ${result.results.length}.` + (sent < result.results.length ? ' Vê os avisos nos que ficaram.' : ''),
          sent === result.results.length ? 'ok' : 'warn');
      }, event.currentTarget)}, `Enviar ${count} email(s)`),
      el('button', {class: 'link', onclick: () => { preview = null; box.replaceChildren(); }}, 'Cancelar')));
}

function ago(value) {
  if (!value) return 'ainda não houve leitura';
  const hours = (Date.now() - new Date(value).getTime()) / 3600000;
  if (hours < 1) return `há ${Math.max(1, Math.round(hours * 60))} min`;
  if (hours < 24) return `há ${Math.round(hours)} h`;
  return `há ${Math.round(hours / 24)} dia(s)`;
}

// open: what a click does (the number leads to the emails behind it); title: the per-property split on hover.
function metricCard(value, label, kind, {open, title} = {}) {
  const go = open && (event => { if (event.type === 'click' || event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); } });
  return el('article', {class: 'metric' + (kind && value ? ' ' + kind : '') + (open ? ' clickable' : ''), title,
      role: open ? 'button' : null, tabindex: open ? '0' : null, onclick: go || null, onkeydown: go || null},
    el('div', {class: 'value'}, String(value)), el('div', {class: 'label'}, label));
}

// Short, readable labels however many bars there are: every bar up to 14, fewer after that.
function chart(days, bucketDays) {
  const width = 640, height = 150, base = height - 22, top = 12;
  const most = Math.max(1, ...days.map(day => Math.max(day.requests, day.sent)));
  const slot = width / days.length, bar = Math.max(2, slot / 2 - 3);
  const every = Math.ceil(days.length / 14);
  const column = (value, x, cls, day, what) => value
    ? svg('rect', {x, y: base - Math.max(3, (base - top) * value / most), width: bar,
                   height: Math.max(3, (base - top) * value / most), rx: 2, class: cls},
          svg('title', {}, `${bucketDays > 1 ? 'Semana de ' : ''}${day.day.slice(8)}/${day.day.slice(5, 7)}: ${value} ${what}`))
    : null;
  return svg('svg', {viewBox: `0 0 ${width} ${height}`, class: 'chart', role: 'img',
                     'aria-label': 'Pedidos recebidos e respostas enviadas por ' + (bucketDays > 1 ? 'semana' : 'dia')},
    svg('line', {x1: 0, y1: base, x2: width, y2: base, class: 'grid-line'}),
    days.map((day, i) => [
      column(day.requests, i * slot + 2, 'bar-requests', day, 'pedido(s) recebido(s)'),
      column(day.sent, i * slot + slot / 2 + 1, 'bar-sent', day, 'resposta(s) enviada(s)'),
      // null, not false: svg() only skips null children, and false would be drawn as the text "false".
      i % every === 0 || i === days.length - 1
        ? svg('text', {x: i * slot + slot / 2, y: height - 6, class: 'bar-label'}, day.day.slice(8) + '/' + day.day.slice(5, 7))
        : null]));
}

// A retro desk clock + calendar in the dashboard header. The calendar marks days with a visit booked,
// from settings.properties[].visits.slots — already loaded for Imóveis, so no call of its own.
const WEEKDAY_NARROW = [...Array(7)].map((_, i) => new Date(2024, 0, 1 + i).toLocaleDateString('pt-PT', {weekday: 'narrow'}));

// The analog face beside it, drawn once in every theme and shown only by a skin that has one (90's RacingCar's
// is a 90s dash clock). Quartz: the second hand ticks, it does not sweep.
const clockHands = (() => {
  const c = 50, at = (degrees, radius) => [c + radius * Math.sin(degrees * Math.PI / 180), c - radius * Math.cos(degrees * Math.PI / 180)];
  const hand = (cls, length, width, tail = 0) => svg('g', {class: 'clock-hand'},
    svg('line', {x1: c, y1: c + tail, x2: c, y2: c - length, class: cls, 'stroke-width': width}));
  const ticks = [...Array(60)].map((_, i) => {
    const [x1, y1] = at(i * 6, i % 5 ? 39.5 : 35.5), [x2, y2] = at(i * 6, 42.5);
    return svg('line', {x1, y1, x2, y2, class: 'clock-tick' + (i % 5 ? '' : ' major')});
  });
  const numerals = [12, 3, 6, 9].map((n, i) => { const [x, y] = at(i * 90, 28); return svg('text', {x, y, class: 'clock-numeral'}, String(n)); });
  const hands = {hours: hand('hour', 21, 3.6), minutes: hand('minute', 32, 2.4), seconds: hand('second', 37, 1.1, 9)};
  $('clock-analog').append(svg('svg', {viewBox: '0 0 100 100'},
    svg('circle', {cx: c, cy: c, r: 49, class: 'clock-bezel'}), svg('circle', {cx: c, cy: c, r: 45.5, class: 'clock-face'}),
    ticks, numerals, hands.hours, hands.minutes, hands.seconds, svg('circle', {cx: c, cy: c, r: 3.2, class: 'clock-cap'})));
  return hands;
})();

function tickClock() {
  const now = new Date();
  $('clock-time').textContent = now.toLocaleTimeString('pt-PT', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
  $('clock-date').textContent = now.toLocaleDateString('pt-PT', {weekday: 'short', day: '2-digit', month: 'short'}).replace('.', '');
  const minutes = now.getMinutes() + now.getSeconds() / 60;
  clockHands.hours.style.transform = `rotate(${(now.getHours() % 12) * 30 + minutes / 2}deg)`;
  clockHands.minutes.style.transform = `rotate(${minutes * 6}deg)`;
  clockHands.seconds.style.transform = `rotate(${now.getSeconds() * 6}deg)`;
}

function visitDays() {
  const days = {};
  for (const property of settings?.properties || []) {
    for (const slot of property.visits?.slots || []) {
      (days[slot.at.slice(0, 10)] ??= []).push(slot.name || slot.customer || 'visita');
    }
  }
  return days;
}

function renderCalendar() {
  const today = new Date();
  const year = today.getFullYear(), month = today.getMonth();
  const startWeekday = (new Date(year, month, 1).getDay() + 6) % 7;  // Monday-first
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const marks = visitDays();
  $('calendar-month').textContent = today.toLocaleDateString('pt-PT', {month: 'long', year: 'numeric'});
  $('calendar-dow').replaceChildren(...WEEKDAY_NARROW.map(letter => el('span', {class: 'cal-dow'}, letter)));
  const cells = [...Array(startWeekday)].map(() => el('span', {class: 'cal-cell empty'}));
  for (let day = 1; day <= daysInMonth; day++) {
    const iso = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const visits = marks[iso];
    cells.push(el('span', {class: 'cal-cell' + (day === today.getDate() ? ' today' : '') + (visits ? ' has-visit' : ''),
      title: visits ? `Visita(s): ${visits.join(', ')}` : ''}, String(day)));
  }
  $('calendar-grid').replaceChildren(...cells);
}

tickClock(); setInterval(tickClock, 1000);

function renderDashboard(data) {
  const totals = data.totals;
  // The dashboard carries no customer data, only counts: a click opens the property's queue, where they are.
  const openQueue = field => {
    const target = data.properties.find(item => item[field] > 0);
    if (!target) return undefined;
    return () => {
      $('queue').value = target.property_ref || ''; renderState(); showTab('replies');
      $('inbox-step').scrollIntoView({behavior: 'smooth', block: 'start'});
    };
  };
  const split = field => data.properties.length > 1
    ? data.properties.map(item => `${item.property_ref || 'Fila única'}: ${item[field]}`).join('\n') : undefined;
  const dm = day => day ? day.slice(8, 10) + '/' + day.slice(5, 7) : '?';
  // Who was answered: first name, the day they first wrote (when known), our last reply and how many.
  const answeredList = () => {
    const lines = [`${totals.customers} cliente(s) · ${totals.answered} resposta(s)`];
    for (const item of data.properties) {
      const people = item.answered_customers || [];
      if (!people.length) continue;
      if (data.properties.length > 1) lines.push('', item.property_ref || 'Fila única');
      for (const person of people) {
        lines.push(`${person.name} · ${person.first_contact ? 'pedido ' + dm(person.first_contact) + ' · ' : ''}`
          + `respondido ${dm(person.last_reply)} · ${person.interactions} interaç${person.interactions === 1 ? 'ão' : 'ões'}`);
      }
    }
    return lines.join('\n');
  };
  $('metric-cards').replaceChildren(
    metricCard(totals.pending, 'Pedidos por responder', null, {open: openQueue('pending'), title: split('pending')}),
    metricCard(totals.drafts, 'Rascunhos prontos', 'ok', {open: openQueue('drafts'), title: split('drafts')}),
    metricCard(totals.blocked, 'Bloqueados', 'warn', {open: openQueue('blocked'), title: split('blocked')}),
    metricCard(totals.attention, 'A precisar de atenção', 'bad', {open: totals.attention ? openQueue('pending') : undefined}),
    metricCard(totals.answered, 'Respostas enviadas', null, {title: answeredList()}),
    metricCard(data.reply_hours == null ? '—' : data.reply_hours + ' h', 'Tempo médio até resposta'));
  $('dashboard-read').textContent = `Última leitura ${ago(data.last_read_at)}`
    + (data.last_read_at ? ` (${when(data.last_read_at)})` : '') + ` · conta ${data.account}`;
  $('dashboard-chart').replaceChildren(chart(data.by_day, data.bucket_days || 1));
  $('chart-note').textContent = data.bucket_days > 1 ? 'Cada barra soma uma semana.' : '';
  $('dashboard-properties').replaceChildren(...(data.properties.length ? data.properties.map(item =>
    el('article', {class: 'card property-tile'},
      propertyCover(item.property_ref, item.photo),
      el('div', {class: 'property-body'},
        el('span', {class: 'property-ref'}, item.property_ref || 'Fila única'),
        el('h3', {class: 'property-title'}, item.description || 'Mensagens da conta'),
        el('div', {class: 'property-stats'},
          ...[[item.pending, 'Pendentes'], [item.drafts, 'Rascunhos'], [item.blocked, 'Bloqueados'], [item.answered, 'Respondidos']]
            .map(([value, label]) => el('div', {}, el('strong', {}, String(value)), el('span', {}, label)))),
        el('div', {class: 'property-footer'},
          el('span', {class: 'muted small'}, item.advertised_rent_eur != null ? new Intl.NumberFormat('pt-PT', {style: 'currency', currency: 'EUR', maximumFractionDigits: 0}).format(item.advertised_rent_eur) : 'Renda não definida'),
          el('div', {class: 'property-links'},
            item.property_ref && el('button', {class: 'link', onclick: () => {
              selectProperty(item.property_ref, 0, false); showPropertiesView('list'); showTab('properties');
            }}, 'Painel do imóvel →'),
            el('button', {class: 'link', onclick: () => {
              $('queue').value = item.property_ref || ''; renderState(); showTab('replies');
            }}, 'Ver respostas →')))))) : [el('div', {class: 'empty-state'}, 'Ainda não há imóveis configurados. Adiciona o primeiro em Imóveis.')]));
  const check = (ok, label, hint) => el('li', {},
    el('span', {class: 'dot' + (ok ? '' : ' missing')}), el('span', {}, label,
      !ok && hint ? el('span', {class: 'muted small'}, ' — ' + hint) : ''));
  $('dashboard-setup').replaceChildren(
    check(data.setup.account, 'Conta de email configurada', 'corre mac/setup.command'),
    check(data.setup.app_password, 'App Password guardada no Keychain', 'corre mac/password.command'),
    check(data.setup.voice, 'Voz completa', 'preenche o separador Voz e estilo'),
    check(data.setup.properties > 0, `Imóveis configurados: ${data.setup.properties}`, 'cria um no separador Imóveis'));
  const usageText = usage => usage.calls ? `${costFormat.format(usage.cost_usd)} · ${usage.calls} pedido(s) · ${usage.prompt_tokens + usage.completion_tokens} tokens`
    : 'Sem pedidos ainda';
  $('usage-period').textContent = usageText(data.openai_usage.period);
  $('usage-all-time').textContent = usageText(data.openai_usage.all_time);
  renderFuelOverview(data);
}

async function loadMetrics() { renderDashboard(await call('api/metrics', {days: Number($('chart-period').value) || 14})); }
try { $('chart-period').value = localStorage.getItem('bot-mail-period') || '14'; } catch { /* Storage may be unavailable. */ }
$('chart-period').addEventListener('change', event => {
  try { localStorage.setItem('bot-mail-period', event.target.value); } catch { /* Storage may be unavailable. */ }
  run(loadMetrics);
});

const DIGEST_STATUS = {draft: 'rascunho', sending: 'a enviar', sent: 'enviado',
  error: 'erro no envio', uncertain: 'envio incerto'};

// The daily status digest: prepared by itself at each READ, for the owner's own inbox. Never sent
// without this "Enviar" click, however many days it has been sitting there as a draft.
function renderDigest(digest) {
  const box = $('digest-panel');
  if (!digest) {
    const reason = 'Aparece depois da próxima leitura de emails (é aí que o rascunho é preparado) — e só '
      + 'com um destinatário definido em Voz e estilo.';
    box.replaceChildren(el('article', {class: 'card'},
      el('div', {class: 'section-heading'},
        el('div', {}, el('p', {class: 'eyebrow'}, 'PONTO DE SITUAÇÃO DIÁRIO'), el('h2', {}, 'Ainda sem rascunho')),
        el('span', {class: 'tag'}, 'por criar')),
      el('div', {class: 'actions'},
        el('button', {disabled: true, title: reason}, 'Guardar'),
        el('button', {class: 'primary send-action', disabled: true, title: reason}, 'Enviar'))));
    return;
  }
  const sent = digest.reply_status === 'sent';
  const text = el('textarea', {rows: 10, 'aria-label': 'Ponto de situação diário', readonly: sent}, digest.reply_text);
  box.replaceChildren(el('article', {class: 'card'},
    el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, 'PONTO DE SITUAÇÃO DIÁRIO'), el('h2', {}, `Rascunho de ${digest.date}`)),
      el('span', {class: 'tag' + (digest.reply_status === 'draft' ? ' draft' : '')},
        DIGEST_STATUS[digest.reply_status] || digest.reply_status)),
    digest.reply_error && el('p', {class: 'alert bad'}, digest.reply_error),
    sent && digest.sent_at && el('p', {class: 'muted small'}, 'Enviado em ' + when(digest.sent_at)),
    text,
    !sent && el('div', {class: 'actions'},
      el('button', {onclick: event => run(async () => {
        renderDigest(await call('api/digest/save', {text: text.value})); toast('Ponto de situação guardado.');
      }, event.currentTarget)}, 'Guardar'),
      el('button', {class: 'primary send-action', onclick: event => run(async () => {
        if (!confirm('Enviar agora o ponto de situação de hoje?')) return;
        await call('api/digest/save', {text: text.value});
        const result = await call('api/digest/send', {confirmed: true});
        renderDigest(await call('api/digest'));
        toast(result.status === 'sent' ? 'Ponto de situação enviado.'
          : 'Envio incerto: verifica Enviados no Gmail antes de repetir.', result.status === 'sent' ? 'ok' : 'warn');
      }, event.currentTarget)}, 'Enviar'))));
}

async function loadDigest() { renderDigest(await call('api/digest')); }

// What a past round looked like: who it went to, and where each one stands now (booked and when, declined,
// still an unsent draft, or sent and awaiting a reply) — otherwise a sent round leaves no trace to check.
function roundSummaryContent(data) {
  if (!data.window) return [el('p', {class: 'muted small'}, 'Ainda sem nenhuma ronda para este imóvel.')];
  const stateLabel = {...CLIENT_STATE_LABEL, nao_quer: 'não quer visitar', outra_data: 'só pode noutra data'};
  const note = person => person.state === 'ok' ? 'enviado, a aguardar resposta'
    : person.state === 'pending' ? 'ainda não foi enviado' : person.reason || '';
  return [
    el('p', {class: 'muted small'},
      `Última ronda: ${dayLabel(data.window.day)}, das ${data.window.start} às ${data.window.end}`),
    el('div', {class: 'client-list'}, data.recipients.map(person => el('div', {class: 'client-row'},
      el('span', {}, person.name || person.email),
      el('span', {class: 'tag' + (person.state === 'booked' ? ' visit' : person.state === 'pending' ? ' draft' : '')},
        person.visit_at ? slotLabel(person.visit_at) : (stateLabel[person.state] || person.state)),
      el('span', {class: 'muted small'}, note(person)))))];
}

// One click, all of a property's active clients: skips the per-client picking in Imóveis → Visitas for
// the common case (everyone eligible gets the same day and window). Fine control still lives there.
let roundPanelProperty = null;
function renderVisitsRound() {
  const box = $('visits-round-panel');
  const properties = (settings?.properties || []).filter(property => !property.visits?.closed_at);
  const card = (...body) => box.replaceChildren(el('article', {class: 'card'},
    el('p', {class: 'eyebrow'}, 'RONDA DE VISITAS'), el('h2', {}, 'Avisa os clientes ativos'), ...body));
  if (!properties.length) {
    card(el('p', {class: 'muted small'}, 'Sem imóveis com visitas em aberto.'));
    return;
  }
  if (!properties.some(property => property.reference === roundPanelProperty)) roundPanelProperty = properties[0].reference;
  const propertySelect = el('select', {'aria-label': 'Imóvel'}, properties.map(property =>
    el('option', {value: property.reference}, property.reference || property.description || 'Imóvel')));
  propertySelect.value = roundPanelProperty;
  const slot = settings.voice.visits?.slot_minutes || 30;
  const day = el('input', {type: 'date', 'aria-label': 'Dia das visitas'});
  const start = el('input', {type: 'time', value: '17:00', step: slot * 60, 'aria-label': 'Hora de início'});
  const end = el('input', {type: 'time', value: '19:00', step: slot * 60, 'aria-label': 'Hora de fim'});
  const summaryBox = el('div', {class: 'round-summary'});
  const loadSummary = () => run(async () => {
    const data = await call('api/visits/round-summary', {property_ref: propertySelect.value});
    summaryBox.replaceChildren(...roundSummaryContent(data));
  });
  propertySelect.addEventListener('change', () => { roundPanelProperty = propertySelect.value; loadSummary(); });
  card(
    el('p', {class: 'step'},
      'Um email a cada cliente ativo deste imóvel, a propor o dia e o intervalo e a perguntar a hora que '
      + 'lhe dá mais jeito dentro dele — fica na fila de Respostas, por rever antes de enviar, como qualquer outra.'),
    el('div', {class: 'row'}, propertySelect, day, start, end),
    el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
      if (!day.value) throw new Error('Escolhe o dia das visitas.');
      const ref = propertySelect.value;
      const data = await call('api/visits/candidates', {property_ref: ref});
      const emails = data.customers.filter(customer => customer.state === 'ok').map(customer => customer.email);
      if (!emails.length) throw new Error('Não há clientes elegíveis agora (por responder, já convidados ou recusaram).');
      if (!confirm(`Vais avisar ${emails.length} cliente(s) de ${ref}: ${dayLabel(day.value)}, das ${start.value} `
          + `às ${end.value}. Continuar?`)) return;
      const result = await call('api/visits/propose', {property_ref: ref, day: day.value, start: start.value, end: end.value, emails});
      state = result.state; settings = result.settings; renderState(); renderSettings();
      toast(`${result.created} proposta(s) de visita na fila de Respostas: prepara-as no ChatGPT ou via API, como as outras.`);
    }, event.currentTarget)}, 'Iniciar ronda')),
    summaryBox);
  loadSummary();
}

// Contactos: contactos.csv as a table. The filters run here (it is one small file); every change goes to the API.
let contactsData = {contacts: [], properties: [], rgpd_states: {}};
const fullDay = day => day ? day.split('-').reverse().join('/') : '—';

function fillSelect(select, options, first) {
  const chosen = select.value;
  select.replaceChildren(...(first ? [el('option', {value: ''}, first)] : []),
    ...Object.entries(options).map(([value, label]) => el('option', {value}, label)));
  if ([...select.options].some(option => option.value === chosen)) select.value = chosen;
}

function contactRow(contact) {
  const nome = el('input', {value: contact.nome, 'aria-label': 'Nome'});
  const telefone = el('input', {value: contact.telefone, 'aria-label': 'Telefone'});
  const rgpd = el('select', {'aria-label': 'Estado RGPD'},
    Object.entries(contactsData.rgpd_states).map(([value, label]) => el('option', {value}, label)));
  rgpd.value = contact.rgpd;
  // The proof of a «sim» confirmed from an email is its Message-ID; one changed here says so itself.
  const proof = contact.rgpd_data && el('div', {class: 'muted small'},
    fullDay(contact.rgpd_data) + ' · ' + (contact.rgpd_prova.startsWith('<') ? 'por email' : contact.rgpd_prova || '—'));
  return el('tr', {},
    el('td', {}, nome), el('td', {class: 'email'}, contact.email), el('td', {}, telefone),
    el('td', {class: 'mono small'}, contact.imovel), el('td', {class: 'nowrap'}, fullDay(contact.primeiro_contacto)),
    el('td', {}, String(contact.interactions)), el('td', {}, rgpd, proof),
    el('td', {class: 'actions-cell'},
      el('button', {onclick: event => run(async () => {
        contactsData = await call('api/contacts/save', {contact: {...contact, nome: nome.value, telefone: telefone.value,
          rgpd: rgpd.value}});
        renderContacts(); toast('Contacto guardado no CSV.');
      }, event.currentTarget)}, 'Guardar'),
      el('button', {class: 'link danger', onclick: event => run(async () => {
        if (!confirm(`Apagar ${contact.nome || contact.email} (${contact.imovel})? Sai do registo de contactos e também da `
          + 'conversa, dos emails por responder e das visitas marcadas deste imóvel. Não se pode desfazer.')) return;
        const result = await call('api/contacts/delete', {email: contact.email, imovel: contact.imovel});
        contactsData = result; state = result.state; renderState(); renderContacts();
        toast('Contacto apagado' + (result.pending_removed ? `, e ${result.pending_removed} email(s) retirado(s) da fila` : '') + '.');
      }, event.currentTarget)}, 'Apagar')));
}

function renderContacts() {
  const properties = Object.fromEntries(contactsData.properties.map(ref => [ref, ref]));
  fillSelect($('contacts-property'), properties, 'Todos');
  fillSelect($('contacts-rgpd'), contactsData.rgpd_states, 'Todos');
  fillSelect($('c-imovel'), properties);
  fillSelect($('c-rgpd'), contactsData.rgpd_states);
  if (!$('c-primeiro').value) $('c-primeiro').value = new Date().toLocaleDateString('sv-SE');  // AAAA-MM-DD, local day
  const ref = $('contacts-property').value, rgpd = $('contacts-rgpd').value;
  const text = $('contacts-search').value.trim().toLowerCase();
  const shown = contactsData.contacts.filter(contact => (!ref || contact.imovel === ref) && (!rgpd || contact.rgpd === rgpd)
    && (!text || [contact.nome, contact.email, contact.telefone].some(value => (value || '').toLowerCase().includes(text))));
  $('contacts-count').textContent = `${shown.length} de ${contactsData.contacts.length}`;
  $('contacts-body').replaceChildren(...(shown.length ? shown.map(contactRow)
    : [el('tr', {}, el('td', {colspan: 8, class: 'muted'}, contactsData.contacts.length
      ? 'Nenhum contacto com estes filtros.' : 'Ainda não há contactos: entram aqui a cada leitura.'))]));
}

async function loadContacts() { contactsData = await call('api/contacts'); renderContacts(); }
$('contacts-property').addEventListener('change', renderContacts);
$('contacts-rgpd').addEventListener('change', renderContacts);
$('contacts-search').addEventListener('input', renderContacts);
$('contact-add').addEventListener('click', event => run(async () => {
  const contact = Object.fromEntries(['email', 'nome', 'telefone', 'imovel', 'fonte', 'rgpd'].map(key => [key, $('c-' + key).value]));
  contact.primeiro_contacto = $('c-primeiro').value;
  contactsData = await call('api/contacts/save', {contact});
  for (const key of ['email', 'nome', 'telefone', 'fonte']) $('c-' + key).value = '';
  renderContacts();
  toast(contactsData.created ? 'Contacto acrescentado ao CSV.' : 'Esse contacto já existia neste imóvel: foi atualizado.');
}, event.currentTarget));

async function refreshState() { state = await call('api/state'); renderState(); }
async function loadSettings() { settings = await call('api/settings'); renderSettings(); }

function renderSettings() {
  renderVoice();
  $('agency-knowledge').replaceChildren(el('p', {class: 'eyebrow'}, 'KNOW-HOW DA AGÊNCIA ', kind('rag')),
    el('h2', {}, 'Conhecimento comum a todos os imóveis'), knowledgeEditor('agency', null));
  if (!$('days').value) $('days').value = settings.lookback_days || 7;
  renderPropertySlider();
  if (!$('f-sender').value) $('f-sender').value = settings.properties[0]?.sender || 'reply@idealista.pt';
  $('generate-api').title = settings.openai_configured ? '' : 'Sem chave OpenAI configurada: o clique explica como.';
  $('api-hint').hidden = !!settings.openai_configured;
  $('api-hint').textContent = 'Sem chave OpenAI configurada ainda: corre mac/openai_key.command no terminal.';
  renderCalendar();
  renderVisitsRound();
  holdFuelButtons();
}

// No photo is the normal case here (nothing is fetched from the Idealista listing): skip the cover
// entirely instead of a placeholder that would show on almost every card. Only a real photo gets one.
function propertyCover(ref, hasPhoto) {
  if (!hasPhoto || !ref) return false;
  const cover = el('div', {class: 'property-cover'});
  cover.append(el('img', {src: 'photo/' + encodeURIComponent(ref), alt: 'Fotografia do imóvel ' + ref,
    loading: 'lazy', onerror: () => cover.remove()}));
  return cover;
}

function propertyCard(property) {
  const areas = {};
  const area = (name, label, rows) => {
    areas[name] = el('textarea', {rows}, property.prompts[name] || '');
    return el('label', {class: 'field'}, el('span', {}, label, kind('prompt')), areas[name]);
  };
  const link = /^https:\/\//.test(property.listing_url || '')
    && el('a', {href: property.listing_url, target: '_blank', rel: 'noopener noreferrer'}, property.listing_url);
  // Two columns on a wide screen: what the property is on the left, what is happening with it on the right.
  return el('article', {class: 'card property-slide'}, el('div', {class: 'property-identity'},
    propertyCover(property.reference, property.photo),
    el('div', {class: 'card-head'}, el('strong', {}, property.reference), el('span', {}, property.description || ''),
      property.advertised_rent_eur != null && el('span', {class: 'tag'}, property.advertised_rent_eur + ' €')),
    el('div', {class: 'muted small'}, [property.sender, property.listing_id && 'anúncio ' + property.listing_id,
      property.knowledge_files.length ? 'conhecimento: ' + property.knowledge_files.join(', ') : 'base de conhecimento vazia']
      .filter(Boolean).join(' · ')),
    link,
    knowledgeDetails(property.reference),
    el('details', {}, el('summary', {class: 'muted small'}, 'Prompts deste imóvel ', kind('prompt')),
      area('general', 'Prompt base: contexto do imóvel', 4),
      area('first', '1.ª interação: primeira resposta', 4), area('first_template', 'Texto base da 1.ª resposta (opcional)', 4),
      area('second', '2.ª interação: confirmar e pedir o que falta', 3),
      area('third', '3.ª interação: proposta de visita', 3),
      area('fourth', '4.ª interação: marcar a visita', 3),
      area('knowledge', 'Como usar a base de conhecimento', 3),
      el('button', {class: 'primary', onclick: event => run(async () => {
        const prompts = Object.fromEntries(Object.entries(areas).map(([name, box]) => [name, box.value]));
        settings = await call('api/property/prompts', {reference: property.reference, prompts});
        renderSettings(); await refreshState(); toast('Prompts guardados.');
      }, event.currentTarget)}, 'Guardar prompts')),
    el('button', {class: 'link', onclick: () => openPropertyEditor(property, property.reference)}, 'Editar dados do anúncio')),
    el('div', {class: 'property-operations'},
      activeClientsList(property),
      analysisPanel(property),
      visitsPanel(property)));
}

function knowledgeDetails(ref) {
  const view = el('div', {});
  const show = () => view.replaceChildren(knowledgeEditor('property', ref));
  return el('details', {ontoggle: event => { if (event.target.open) show(); }},
    el('summary', {class: 'muted small'}, 'Conhecimento deste imóvel ', kind('rag')),
    view, noteBox(ref, show));
}

// The knowledge files as the owner wrote them: each one editable whole, and new ones can be added.
function knowledgeEditor(scope, ref) {
  const box = el('div', {class: 'knowledge-editor'}, el('p', {class: 'muted small'}, 'A carregar…'));
  const load = () => run(async () => {
    const data = await call('api/knowledge', {property_ref: ref});
    const save = (file, area, button) => run(async () => {
      const result = await call('api/knowledge/save', {scope, property_ref: ref, file, text: area.value});
      state = result.state; renderState(); load();
      toast(`${result.file} guardado. O próximo prompt já o leva.`);
    }, button);
    const block = file => {
      const area = el('textarea', {rows: Math.min(18, Math.max(4, file.text.split('\n').length + 1)), 'aria-label': file.file}, file.text);
      return el('div', {class: 'knowledge-file'}, el('p', {class: 'eyebrow'}, file.file), area,
        el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => save(file.file, area, event.currentTarget)}, 'Guardar ' + file.file)));
    };
    const name = el('input', {placeholder: 'novo-ficheiro.md', 'aria-label': 'Nome do ficheiro novo'});
    const text = el('textarea', {rows: 3, placeholder: '# Título\n- Um facto por linha.', 'aria-label': 'Texto do ficheiro novo'});
    const files = data.files[scope] || [];
    box.replaceChildren(
      el('p', {class: 'step'}, scope === 'agency'
        ? 'Vale para todos os imóveis; se o conhecimento de um imóvel disser outra coisa, prevalece o do imóvel.'
        : 'Só para este imóvel. O texto entre <!-- e --> fica para ti: não chega ao assistente.'),
      ...(files.length ? files.map(block) : [el('p', {class: 'muted small'}, 'Ainda não há ficheiros.')]),
      el('details', {}, el('summary', {class: 'muted small'}, '+ Novo ficheiro'), name, text,
        el('div', {class: 'actions'}, el('button', {onclick: event => save(name.value.trim(), text, event.currentTarget)}, 'Criar ficheiro'))));
  });
  load();
  return box;
}

const CLIENT_STATE_LABEL = {ok: 'ativo', pending: 'por responder', booked: 'visita marcada'};

// Persistent, not behind a click: everyone this property has written to, and where they stand — until
// the property closes (sold/rented/withdrawn is the same "Fechar visitas" event, not a separate state).
function activeClientsList(property) {
  const box = el('div', {class: 'client-list'}, el('p', {class: 'muted small'}, 'A carregar…'));
  if (property.visits?.closed_at) {
    box.replaceChildren(el('p', {class: 'muted small'}, 'Imóvel fechado: já não há clientes ativos.'));
  } else {
    run(async () => {
      const data = await call('api/visits/candidates', {property_ref: property.reference});
      box.replaceChildren(...(data.customers.length ? data.customers.map(customer => el('div', {class: 'client-row'},
        el('span', {}, customer.name || customer.email),
        el('span', {class: 'tag' + (customer.state === 'booked' ? ' visit' : customer.state === 'ok' ? ' draft' : '')},
          CLIENT_STATE_LABEL[customer.state] || customer.state),
        el('span', {class: 'muted small'}, customer.reason || `${customer.stage} interaç${customer.stage === 1 ? 'ão' : 'ões'}`)))
        : [el('p', {class: 'muted small'}, 'Ainda não escrevemos a nenhum cliente deste imóvel.')]));
    });
  }
  return el('details', {class: 'visits-panel', open: true},
    el('summary', {class: 'muted small'}, 'Clientes ativos'), box);
}

// Read-only: a summary of what active clients have said, to help pick a day and a window — by copy/paste
// with ChatGPT (no key needed) or straight from the OpenAI API (same key as "Gerar respostas via API").
function analysisPanel(property) {
  if (property.visits?.closed_at) return false;
  const promptText = el('pre', {}, '');
  const promptBox = el('details', {}, el('summary', {class: 'muted small'}, 'Prompt de análise'), promptText);
  const copyBtn = el('button', {disabled: true, onclick: event => run(async () => {
    await copyText(promptText.textContent, 'Prompt copiado. Cola-o numa conversa do ChatGPT e lê a resposta lá — não é preciso trazê-la de volta.', promptBox);
  }, event.currentTarget)}, 'Copiar');
  const summaryBox = el('div', {});
  return el('details', {class: 'visits-panel'}, el('summary', {class: 'muted small'}, 'Analisar antes de propor'),
    el('p', {class: 'step'}, 'Resume o que os clientes ativos já disseram (disponibilidade, urgência, preferências), para te ajudar a escolher o dia e o intervalo abaixo.'),
    el('div', {class: 'actions'},
      el('button', {onclick: event => run(async () => {
        const result = await call('api/visits/analysis-prompt', {property_ref: property.reference});
        promptText.textContent = result.prompt; promptBox.open = true; copyBtn.disabled = false;
        toast('Prompt de análise criado: revê abaixo e depois copia.');
      }, event.currentTarget)}, 'Criar prompt de análise'),
      copyBtn,
      el('button', {class: 'primary needs-fuel', 'data-ref': property.reference,
        title: settings.openai_configured ? '' : 'Sem chave OpenAI configurada: o clique explica como.',
        onclick: event => run(async () => {
          const result = await call('api/visits/analyze', {property_ref: property.reference});
          summaryBox.replaceChildren(el('p', {class: 'alert ok'}, result.summary));
          applyFuel(result.fuel, property.reference);
          toast('Análise pronta.');
        }, event.currentTarget)}, 'Analisar via API')),
    promptBox, summaryBox);
}

function visitsPanel(property) {
  const visits = property.visits || {windows: [], slots: [], closed_at: null};
  const closed = !!visits.closed_at;
  const slot = settings.voice.visits?.slot_minutes || 30;
  const day = el('input', {type: 'date', 'aria-label': 'Dia das visitas'});
  const start = el('input', {type: 'time', value: '17:00', step: slot * 60, 'aria-label': 'Hora de início'});
  const end = el('input', {type: 'time', value: '19:00', step: slot * 60, 'aria-label': 'Hora de fim'});
  const list = el('div', {class: 'visit-candidates'});
  const choose = event => run(async () => {
    const data = await call('api/visits/candidates', {property_ref: property.reference});
    const rows = data.customers.map(customer => el('label', {class: 'candidate'},
      el('input', {type: 'checkbox', 'data-email': customer.email, checked: customer.state === 'ok',
        disabled: customer.state === 'pending' || customer.state === 'booked'}),
      el('span', {}, customer.name || customer.email),
      customer.reason && el('span', {class: 'muted small'}, '— ' + customer.reason)));
    list.replaceChildren(...(rows.length ? rows : [el('p', {class: 'muted small'}, 'Ainda não escrevemos a nenhum cliente deste imóvel.')]),
      rows.length && el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
        const emails = [...list.querySelectorAll('input[type=checkbox]:checked')].map(box => box.dataset.email);
        const result = await call('api/visits/propose', {property_ref: property.reference, day: day.value,
          start: start.value, end: end.value, emails});
        state = result.state; settings = result.settings; renderState(); renderSettings();
        toast(`${result.created} proposta(s) de visita na fila de Respostas: prepara-as no ChatGPT como as outras.`);
      }, event.currentTarget)}, 'Criar propostas')));
    toast(`${data.customers.length} cliente(s) encontrados.`);
  }, event.currentTarget);
  const closeVisits = el('button', {class: 'link danger', onclick: event => run(async () => {
    if (!confirm(`Fechar as visitas de ${property.reference}? Prepara um email de agradecimento para cada cliente (pendentes e já respondidos) e os pedidos novos deste imóvel passam a ser respondidos automaticamente.`)) return;
    const result = await call('api/visits/close', {property_ref: property.reference});
    state = result.state; settings = result.settings; renderState(); renderSettings();
    toast(`Visitas fechadas: ${result.drafted} rascunho(s) na fila de Respostas, prontos a rever e enviar.`);
  }, event.currentTarget)}, 'Fechar visitas e agradecer a todos');
  const requestConsent = el('button', {onclick: event => run(async () => {
    const result = await call('api/consent/request', {property_ref: property.reference});
    state = result.state; renderState();
    toast(result.drafted ? `${result.drafted} pedido(s) de consentimento na fila de Respostas.` : 'Ninguém por pedir: já foi pedido a todos os que responderam.');
  }, event.currentTarget)}, 'Pedir consentimento RGPD a quem respondeu');
  return el('details', {class: 'visits-panel'}, el('summary', {class: 'muted small'}, 'Visitas: propor e marcar' + (closed ? ' (fechadas)' : '')),
    closed && el('p', {class: 'alert warn'}, `Visitas fechadas em ${when(visits.closed_at)}. Novos pedidos deste imóvel recebem a resposta automática.`),
    !closed && (visits.windows.length
      ? visits.windows.map(window => el('p', {class: 'small'}, `Proposta: ${dayLabel(window.day)}, das ${window.start} às ${window.end}`))
      : [el('p', {class: 'muted small'}, 'Sem visitas propostas.')]),
    !closed && visits.slots.map(booked => el('p', {class: 'small'}, el('strong', {}, slotLabel(booked.at)), ' · ', booked.name || booked.customer)),
    !closed && el('p', {class: 'step'}, `Escolhe o dia e o intervalo. Marcam-se de ${slot} em ${slot} minutos (em Voz e estilo).`),
    !closed && el('div', {class: 'row'}, day, start, end, el('button', {onclick: choose}, 'Escolher clientes')), !closed && list,
    el('div', {class: 'actions'}, !closed && closeVisits, requestConsent));
}

// Agenda: a weekly planner, filofax-style — one paper page per day, day pages laid side by side, not a
// Google-Calendar grid. Reads only settings.properties[].visits (already loaded for Imóveis): no request
// of its own. Export to a real calendar is deliberately not built yet — for now this page is the agenda.
let agendaWeekOffset = 0;

function startOfWeek(date) {
  const start = new Date(date);
  start.setDate(date.getDate() - ((date.getDay() + 6) % 7));  // Monday-first, matching the retro calendar
  start.setHours(0, 0, 0, 0);
  return start;
}

function isoDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function agendaEntries(iso, propertyFilter) {
  const properties = settings?.properties || [];
  const entries = [];
  for (const property of properties) {
    if (propertyFilter && property.reference !== propertyFilter) continue;
    const label = property.reference || property.description || 'Imóvel';
    for (const window of property.visits?.windows || []) {
      if (window.day === iso) entries.push({time: window.start, kind: 'window', label, text: `Proposta: ${window.start}–${window.end}`});
    }
    for (const slot of property.visits?.slots || []) {
      const [day, time] = String(slot.at).split(' ');
      if (day === iso) entries.push({time, kind: 'slot', label, text: `Marcada: ${time} · ${slot.name || slot.customer || 'visita'}`});
    }
  }
  entries.sort((a, b) => a.time.localeCompare(b.time));
  return {entries, showLabel: properties.length > 1};
}

function renderAgenda() {
  const properties = Object.fromEntries((settings?.properties || []).map(property =>
    [property.reference, property.reference || property.description || 'Imóvel']));
  fillSelect($('agenda-property'), properties, 'Todos');
  const monday = startOfWeek(new Date());
  monday.setDate(monday.getDate() + agendaWeekOffset * 7);
  const days = [...Array(7)].map((_, i) => { const d = new Date(monday); d.setDate(monday.getDate() + i); return d; });
  $('agenda-range').textContent = agendaWeekOffset === 0 ? 'Esta semana'
    : `${days[0].toLocaleDateString('pt-PT', {day: '2-digit', month: '2-digit'})} – `
      + days[6].toLocaleDateString('pt-PT', {day: '2-digit', month: '2-digit'});
  const todayIso = isoDate(new Date());
  const filter = $('agenda-property').value;
  $('agenda-week').replaceChildren(...days.map(date => {
    const iso = isoDate(date);
    const {entries, showLabel} = agendaEntries(iso, filter);
    return el('div', {class: 'filofax-page' + (iso === todayIso ? ' today' : '')},
      el('div', {class: 'filofax-head'},
        el('span', {class: 'filofax-weekday'}, date.toLocaleDateString('pt-PT', {weekday: 'long'})),
        el('span', {class: 'filofax-date'}, date.toLocaleDateString('pt-PT', {day: '2-digit', month: '2-digit'}))),
      el('div', {class: 'filofax-lines'},
        entries.length ? entries.map(entry => el('div', {class: 'filofax-entry ' + entry.kind},
          el('strong', {}, entry.text), showLabel && el('span', {class: 'muted small'}, entry.label)))
          : el('p', {class: 'muted small filofax-empty'}, 'Sem visitas previstas.')));
  }));
}

$('agenda-prev').addEventListener('click', () => { agendaWeekOffset--; renderAgenda(); });
$('agenda-next').addEventListener('click', () => { agendaWeekOffset++; renderAgenda(); });
$('agenda-today').addEventListener('click', () => { agendaWeekOffset = 0; renderAgenda(); });
$('agenda-property').addEventListener('change', renderAgenda);

// Imóveis: one property at a time (a slider, not side by side), each with its own instrument cluster;
// creating or editing a property's ad data is a view of its own. The property shown is remembered in
// this browser only, like the theme.
let propertyRef = null, slideDirection = 0, editorRef = null;
try { propertyRef = localStorage.getItem('bot-mail-property'); } catch { /* Storage may be unavailable. */ }

function selectProperty(ref, direction = 0, render = true) {
  propertyRef = ref; slideDirection = direction;
  try { localStorage.setItem('bot-mail-property', ref || ''); } catch { /* Storage may be unavailable. */ }
  if (render && settings) renderPropertySlider();
}

function stepProperty(step) {
  const properties = settings?.properties || [];
  if (properties.length < 2) return;
  const index = Math.max(0, properties.findIndex(property => property.reference === propertyRef));
  selectProperty(properties[(index + step + properties.length) % properties.length].reference, step);
}

function showPropertiesView(view) {
  const editing = view === 'editor';
  $('properties-view').hidden = editing;
  $('new-property-view').hidden = !editing;
  for (const [id, on] of [['view-properties', !editing], ['view-new-property', editing]]) {
    $(id).classList.toggle('active', on); $(id).setAttribute('aria-pressed', String(on));
  }
  window.scrollTo({top: 0, behavior: 'instant'});
}

// ref: the property being edited (its data fills the form); null for a new one.
function openPropertyEditor(fields, ref = null) {
  editorRef = ref;
  for (const name of FIELDS) if (name !== 'sender' || fields.sender) $('f-' + name).value = fields[name] ?? '';
  $('f-facts').value = (fields.facts || []).join('\n');
  $('editor-title').textContent = ref ? `Editar ${ref}` : 'Novo imóvel';
  showPropertiesView('editor');
}

function renderPropertySlider() {
  const properties = settings.properties;
  if (!properties.length) {
    $('property-slider').replaceChildren();
    $('property-dashboard').replaceChildren();
    $('property-list').replaceChildren(el('div', {class: 'empty-state'}, el('strong', {}, 'Ainda não há imóveis.'),
      el('button', {class: 'link', onclick: () => openPropertyEditor({}, null)}, 'Criar o primeiro →')));
    return;
  }
  let index = properties.findIndex(property => property.reference === propertyRef);
  if (index < 0) { index = 0; propertyRef = properties[0].reference; }
  const property = properties[index], many = properties.length > 1;
  // Through el(), which drops a false child: replaceChildren itself would print it as the text "false".
  $('property-slider').replaceChildren(...el('div', {},
    many && el('button', {class: 'slider-arrow prev', 'aria-label': 'Imóvel anterior', onclick: () => stepProperty(-1)}, '‹'),
    el('div', {class: 'slider-title'},
      el('span', {class: 'property-ref'}, property.reference),
      el('strong', {}, property.description || ''),
      many && el('div', {class: 'slider-dots'}, properties.map((other, i) => el('button', {
        class: 'slider-dot' + (i === index ? ' active' : ''), 'aria-label': other.reference, title: other.reference,
        'aria-current': i === index ? 'true' : false,
        onclick: () => selectProperty(other.reference, Math.sign(i - index))})),
        el('span', {class: 'muted small'}, `${index + 1} / ${properties.length}`))),
    many && el('button', {class: 'slider-arrow next', 'aria-label': 'Imóvel seguinte', onclick: () => stepProperty(1)}, '›')).childNodes);
  const slide = slideDirection > 0 ? 'slide-next' : slideDirection < 0 ? 'slide-prev' : '';
  const card = propertyCard(property);
  if (slide) card.classList.add(slide);
  $('property-list').replaceChildren(card);
  renderPropertyDashboard(property, slide);
  slideDirection = 0;
}

$('view-properties').addEventListener('click', () => showPropertiesView('list'));
// A form left half-filled for a new property stays as it was; one showing another property starts blank.
$('view-new-property').addEventListener('click', () => editorRef ? openPropertyEditor({}, null) : showPropertiesView('editor'));
$('property-slider').addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft') stepProperty(-1);
  if (event.key === 'ArrowRight') stepProperty(1);
});
(() => {  // a horizontal swipe on a phone moves to the next or previous property
  let startX = null, startY = 0;
  $('properties-view').addEventListener('touchstart', event => {
    [startX, startY] = [event.touches[0].clientX, event.touches[0].clientY];
  }, {passive: true});
  $('properties-view').addEventListener('touchend', event => {
    if (startX == null) return;
    const dx = event.changedTouches[0].clientX - startX, dy = event.changedTouches[0].clientY - startY;
    startX = null;
    if (Math.abs(dx) >= 60 && Math.abs(dx) > Math.abs(dy) * 1.5 && !event.target.closest('input, textarea, select, pre')) {
      stepProperty(dx < 0 ? 1 : -1);
    }
  }, {passive: true});
})();

// The instrument cluster: dials, odometers and warning lamps, drawn by hand like the chart (nothing is
// loaded from outside). Each dial remembers where its needle was, so a redraw sweeps from there.
const needles = {};
let gaugeCount = 0;

function niceMax(value) {
  const power = 10 ** Math.floor(Math.log10(value));
  return [1, 2, 2.5, 5, 10].map(step => step * power).find(step => step >= value - 1e-9);
}

// Car-dial symbols in a 24-unit box, as on a real dashboard: engine temperature and fuel. Only a skin shows them.
const GAUGE_ICONS = {
  heat: [['M12 3v10M12 6h3M12 9h3', 'M3 20.6c1.5-1.2 3-1.2 4.5 0s3 1.2 4.5 0 3-1.2 4.5 0 3 1.2 4.5 0'], ['circle', {cx: 12, cy: 15.6, r: 2.6}]],
  fuel: [['M5 20V5a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v15M3.5 20h12', 'M14 9h1.5l2.5 2.5V17a1.4 1.4 0 0 1-2.8 0v-3H14'],
         ['rect', {x: 7, y: 6.5, width: 5, height: 4}]],
};
function gaugeIcon(name, x, y) {
  const [paths, [shape, attrs]] = GAUGE_ICONS[name];
  return svg('g', {class: 'gauge-icon', transform: `translate(${x - 8.4} ${y - 8.4}) scale(.7)`},
    paths.map(d => svg('path', {d})), svg(shape, {...attrs, class: 'fill'}));
}

// red: [from, to] in the dial's units (a fuel gauge's is at the empty end); labels: the major ticks' text.
// role: what the dial measures (heat, tach, speedo, fuel), for the layout; alert: the readout turns red.
function gauge({key, value, max, red = null, unit, caption, readout, size = 'small', face = 'dark', labels = null,
                divisions = 4, minor = 4, icon = null, role = '', alert = false,
                format = n => n.toLocaleString('pt-PT', {maximumFractionDigits: 3})}) {
  const id = 'gauge' + (++gaugeCount), c = 100, r = 84, start = -135, sweep = 270;
  const angle = v => start + sweep * Math.max(0, Math.min(1, v / max));
  const point = (a, radius) => [c + radius * Math.sin(a * Math.PI / 180), c - radius * Math.cos(a * Math.PI / 180)];
  const arc = (a1, a2, radius) => {
    const [x1, y1] = point(a1, radius), [x2, y2] = point(a2, radius);
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${a2 - a1 > 180 ? 1 : 0} 1 ${x2} ${y2}`;
  };
  const marks = [];
  for (let i = 0, steps = divisions * minor; i <= steps; i++) {
    const a = start + sweep * i / steps, major = i % minor === 0;
    const [x1, y1] = point(a, r - (major ? 14 : 7)), [x2, y2] = point(a, r - 1);
    marks.push(svg('line', {x1, y1, x2, y2, class: 'gauge-tick' + (major ? ' major' : '')}));
    if (major) {
      const [x, y] = point(a, r - 27), end = i === 0 || i === steps;  // simple themes show only the ends
      marks.push(svg('text', {x, y, class: 'gauge-number' + (end ? ' end' : '')},
        labels ? labels[i / minor] : format(max * i / steps)));
    }
  }
  const needle = svg('g', {class: 'gauge-needle'},
    svg('path', {d: `M ${c - 4} ${c + 18} L ${c - 1.3} ${c - r + 14} L ${c + 1.3} ${c - r + 14} L ${c + 4} ${c + 18} Z`}));
  const target = angle(value || 0);
  needle.style.transform = `rotate(${needles[key] ?? start}deg)`;
  needles[key] = target;
  requestAnimationFrame(() => requestAnimationFrame(() => { needle.style.transform = `rotate(${target}deg)`; }));
  return el('figure', {class: `gauge gauge-${size} gauge-${face}` + (role ? ' gauge-' + role : '') + (alert ? ' gauge-alert' : '')},
    svg('svg', {viewBox: '0 0 200 200', role: 'img', 'aria-label': `${caption}: ${readout}`},
      svg('defs', {}, svg('linearGradient', {id: id + '-bezel', x1: 0, y1: 0, x2: 0, y2: 1},
        svg('stop', {offset: '0%', 'stop-color': '#f6f6f6'}), svg('stop', {offset: '50%', 'stop-color': '#7d8186'}),
        svg('stop', {offset: '100%', 'stop-color': '#dcdde0'}))),
      svg('circle', {cx: c, cy: c, r: 99, fill: `url(#${id}-bezel)`, class: 'gauge-bezel'}),
      svg('circle', {cx: c, cy: c, r: 93, class: 'gauge-face'}),
      red && red[0] < red[1] ? svg('path', {d: arc(angle(red[0]), angle(red[1]), r - 4), class: 'gauge-red'}) : null,
      marks,
      svg('text', {x: c, y: c - 32, class: 'gauge-unit'}, unit.toUpperCase()),
      icon ? gaugeIcon(icon, c, c + 31) : null,  // between the needle's cap and the readout
      // Below the first and last numbers (at ±135°, y ≈ c + 40): in the dial's open bottom, never over them.
      svg('rect', {x: c - 42, y: c + 52, width: 84, height: 22, rx: 3, class: 'gauge-readout-box'}),
      svg('text', {x: c, y: c + 63.5, class: 'gauge-readout'}, readout),
      needle,
      svg('circle', {cx: c, cy: c, r: 9, class: 'gauge-cap'})),
    el('figcaption', {}, caption));
}

function odometer(value, label, digits = 4) {
  return el('div', {class: 'odometer'},
    el('div', {class: 'odometer-digits', role: 'img', 'aria-label': `${label}: ${value}`},
      // The padding zeros are marked, so the simple themes can hide them and show a plain number.
      [...String(Math.max(0, value)).padStart(digits, '0')].map((digit, i, all) =>
        el('span', i < all.length - String(Math.max(0, value)).length ? {class: 'lead'} : {}, digit))),
    el('span', {class: 'odometer-label'}, label));
}

// A warning lamp: dark when the count is zero, lit (in its colour) otherwise. icon: the car symbol a skin
// shows instead of the plain bulb (heat, fuel, engine, blocked).
function lamp(label, count, tone, shown = String(count), icon = null) {
  return el('div', {class: 'lamp' + (count ? ` on lamp-${tone}` : '') + (icon ? ` lamp-icon-${icon}` : ''),
      title: `${label}: ${shown || (count ? 'sim' : 'não')}`},
    el('span', {class: 'lamp-bulb', 'aria-hidden': 'true'}), el('span', {}, label), shown ? el('strong', {}, shown) : null);
}

// 1 € = 1 US$ for this assistant, by the owner's choice: OpenAI's cost reads in euros, with no conversion.
const eurFormat = new Intl.NumberFormat('pt-PT', {style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2});
const costFormat = new Intl.NumberFormat('pt-PT', {style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 4});
const litresText = litres => litres == null ? '— L' : litres.toLocaleString('pt-PT', {maximumFractionDigits: 1}) + ' L';

// A property's API tank as a fuel gauge: E to F, the red at the empty end (the reserve), needle on what is left.
function fuelGauge(fuel, key, caption, size = 'small') {
  const capacity = fuel.capacity_eur, left = fuel.configured ? Math.max(0, fuel.remaining_eur) : capacity;
  return gauge({key, value: left, max: capacity, red: [0, capacity * 0.15], unit: 'combustível', labels: ['E', '½', 'F'],
    divisions: 2, minor: 4, icon: 'fuel', role: 'fuel', alert: fuel.empty, size,
    readout: fuel.configured ? eurFormat.format(left) : 'sem limite', caption});
}

// Each property has its own tank (settings.properties[].api_fuel); settings.api_fuel is only for a folder
// without properties.
function fuelOf(ref) {
  return (ref ? settings?.properties.find(property => property.reference === ref)?.api_fuel : null) ?? settings?.api_fuel;
}

// An empty tank switches off that property's API buttons (data-ref, else the queue open in Respostas):
// data-hold stops run() from switching them back on, and the title says why. Copy/paste is untouched, and
// the server refuses the call too — this is only the signal.
function holdFuelButtons() {
  if (!settings) return;
  for (const button of document.querySelectorAll('.needs-fuel')) {
    const ref = button.dataset.ref || queueRef(), fuel = fuelOf(ref);
    button.dataset.hold = fuel?.empty ? '1' : '';
    button.disabled = !!fuel?.empty;
    if (fuel?.empty) button.title = `Depósito da API${ref ? ' de ' + ref : ''} vazio: enche-o no painel do imóvel `
      + '(Imóveis). O copiar/colar com o ChatGPT continua a funcionar.';
    else if (button.title.startsWith('Depósito da API')) {
      button.title = settings.openai_configured ? '' : 'Sem chave OpenAI configurada: o clique explica como.';
    }
  }
}

// What an API call left in its property's tank: kept in settings, and that property's buttons follow it.
function applyFuel(fuel, ref) {
  if (!fuel || !settings) return;
  const property = ref && settings.properties.find(item => item.reference === ref);
  if (property) property.api_fuel = fuel;
  else settings.api_fuel = fuel;
  holdFuelButtons();
}

// The Painel's view of the tanks: one per property, each filled on its own property's panel (Imóveis).
function renderFuelOverview(metrics) {
  const rows = metrics.properties.filter(item => item.property_ref && item.api_fuel).map(item => {
    const fuel = item.api_fuel, left = eurFormat.format(Math.max(0, fuel.remaining_eur ?? 0));
    const size = eurFormat.format(fuel.capacity_eur);
    const status = !fuel.configured ? 'Sem depósito: a via API não tem limite neste imóvel.'
      : fuel.empty ? 'Vazio: a via API está desligada neste imóvel. O copiar/colar continua.'
      : fuel.reserve ? `Na reserva: restam ${left} de ${size}.` : `Restam ${left} de ${size}.`;
    return el('div', {class: 'fuel-row'},
      fuelGauge(fuel, 'painel:fuel:' + item.property_ref, item.property_ref, 'mini'),
      el('div', {class: 'fuel-side'},
        el('p', {class: 'fuel-status' + (fuel.empty ? ' bad' : fuel.reserve ? ' warn' : '')}, status),
        el('button', {class: 'link', onclick: () => {
          selectProperty(item.property_ref, 0, false); showPropertiesView('list'); showTab('properties');
        }}, 'Encher no painel do imóvel →')));
  });
  $('fuel-panel').replaceChildren(...(rows.length ? rows : [fuelGauge(metrics.api_fuel, 'painel:fuel', 'Depósito da API')]));
}

// What a property's panel measures, whatever a skin draws it as: emails waiting, the average reply time
// against this property's own limit, requests per day in the chosen period, its API tank and the petrol
// its visits took.
function panelSignals(data, metrics) {
  const hoursMax = data.reply_hours_max || 24;
  return {pending: data.pending, pendingMax: data.pending <= 20 ? 20 : niceMax(data.pending),
    hours: data.reply_hours, hoursMax, hot: data.reply_hours != null && data.reply_hours >= hoursMax,
    perDay: data.by_day.reduce((sum, day) => sum + day.requests, 0) / (metrics.period_days || 14),
    fuel: data.api_fuel || metrics.api_fuel, spent: data.openai_usage.all_time.cost_usd,
    petrol: data.petrol || {distance_km: null, l_per_100km: 7, trips: 0, planned_trips: 0, km: null, litres: null}};
}
const hoursText = hours => hours == null ? '—' : hours.toLocaleString('pt-PT') + ' h';

// Petrol for the visits, beside the API tank: a gauge like the fuel one, but it only ever adds up — one round
// trip to the property per day of visits already begun, at the car's consumption (see tripComputer).
function petrolGauge(ref, petrol, caption) {
  const litres = petrol.litres || 0;
  return gauge({key: ref + ':petrol', role: 'petrol', value: litres, max: niceMax(Math.max(20, litres * 1.1)),
    unit: 'litros', icon: 'fuel', size: 'mini', divisions: 2, minor: 4, readout: litresText(petrol.litres), caption});
}

// The plain themes: flat dials — reply time, emails waiting, the API tank and the petrol of the visits.
function plainInstruments(ref, s) {
  return [
    gauge({key: ref + ':hours', role: 'heat', value: s.hours || 0, max: s.hoursMax, red: [s.hoursMax * 0.75, s.hoursMax],
      unit: 'horas', divisions: 4, minor: 3, readout: hoursText(s.hours), caption: 'Tempo médio de resposta', alert: s.hot}),
    gauge({key: ref + ':pending', role: 'tach', value: s.pending, max: s.pendingMax, red: [s.pendingMax / 2, s.pendingMax],
      unit: 'emails', size: 'big', face: 'yellow', divisions: 10, minor: 2, readout: String(s.pending), caption: 'Por responder'}),
    fuelGauge(s.fuel, 'cluster:fuel', `Depósito da API deste imóvel · gastou ${costFormat.format(s.spent)}`),
    petrolGauge(ref, s.petrol, 'Gasolina das visitas')];
}

// 90's RacingCar: a GT's binnacle. Water temperature is the average reply time, with this property's own limit
// as its H; the yellow tachometer, the emails waiting; the speedometer, requests per day; fuel, the property's
// token tank; and, smaller beside it, the petrol its visits took.
function carInstruments(ref, s) {
  const speedMax = Math.max(10, niceMax(Math.max(1, s.perDay)));
  return [
    gauge({key: ref + ':hours', role: 'heat', value: s.hours || 0, max: s.hoursMax, red: [s.hoursMax * 0.75, s.hoursMax],
      unit: '', icon: 'heat', labels: ['C', '', 'H'], divisions: 2, minor: 4, readout: hoursText(s.hours),
      caption: 'Temperatura · tempo médio de resposta', alert: s.hot}),
    gauge({key: ref + ':pending', role: 'tach', value: s.pending, max: s.pendingMax, red: [s.pendingMax / 2, s.pendingMax],
      unit: 'emails', size: 'big', face: 'yellow', divisions: 10, minor: 2, readout: String(s.pending),
      caption: 'Conta-rotações · por responder'}),
    gauge({key: ref + ':speed', role: 'speedo', value: s.perDay, max: speedMax, unit: 'pedidos / dia', size: 'big',
      divisions: 5, minor: 4, readout: s.perDay.toLocaleString('pt-PT', {maximumFractionDigits: 1}) + ' /dia',
      caption: 'Velocímetro · pedidos por dia'}),
    fuelGauge(s.fuel, 'cluster:fuel', `Combustível · tokens · gastou ${costFormat.format(s.spent)}`),
    petrolGauge(ref, s.petrol, 'Gasolina · visitas')];
}

// This property's reply-time limit: the top (H) of its temperature dial, saved per property, like the
// size of its tank. Past it, the dial is overheated and its lamp lights up.
function heatLimit(property, hoursMax) {
  const input = el('input', {type: 'number', min: 1, max: 720, step: 1, value: hoursMax,
    'aria-label': `Tempo máximo de resposta de ${property.reference}, em horas`});
  const save = button => run(async () => {
    const {panel} = await call('api/property/panel', {property_ref: property.reference, reply_hours_max: input.value});
    toast(`${property.reference}: o máximo do tempo de resposta passa a ${hoursText(panel.reply_hours_max)}.`);
    renderPropertyDashboard(property);
  }, button);
  input.addEventListener('keydown', event => { if (event.key === 'Enter') save(); });
  return el('div', {class: 'gauge-setting'}, el('label', {}, word('heat.limit', 'Máximo'), input, 'h'),
    el('button', {class: 'link', onclick: event => save(event.currentTarget)}, 'Guardar'));
}

// Filling this property's tank, under its fuel gauge: from now on the API may spend up to that here.
function fuelFill(property, fuel) {
  const ref = property.reference;
  const input = el('input', {type: 'number', min: 0.5, max: 1000, step: 0.5, value: fuel.capacity_eur,
    'aria-label': `Valor do depósito de ${ref}, em euros`});
  const fill = button => run(async () => {
    const amount = eurFormat.format(Number(input.value) || 0);
    if (!confirm(`Encher o depósito de ${ref} com ${amount}? A partir de agora, a via API pode gastar até ${amount} `
        + 'neste imóvel (estimativa a partir dos tokens), e o gasto volta a contar do zero.')) return;
    const result = await call('api/fuel/fill', {property_ref: ref, capacity_eur: input.value});
    applyFuel(result.fuel, ref);
    toast(`Depósito de ${ref} cheio: ${eurFormat.format(result.fuel.capacity_eur)}.`);
    renderPropertyDashboard(property);
  }, button);
  return el('div', {class: 'gauge-setting'}, el('label', {}, input, '€'),
    el('button', {class: 'link', onclick: event => fill(event.currentTarget)}, 'Encher'));
}

// The trip computer: the distance from the agency to this property and the car's consumption (saved per
// property), and what the visits took so far — days, km, litres — with the days booked ahead apart.
function tripComputer(property, petrol) {
  const ref = property.reference;
  const km = el('input', {type: 'number', min: 0, max: 1000, step: 1, value: petrol.distance_km ?? '', placeholder: '—',
    'aria-label': `Distância da agência a ${ref}, só ida, em km`});
  const rate = el('input', {type: 'number', min: 1, max: 40, step: 0.1, value: petrol.l_per_100km,
    'aria-label': 'Consumo do carro, em litros aos 100 km'});
  const save = button => run(async () => {
    await call('api/property/panel', {property_ref: ref, distance_km: km.value, l_per_100km: rate.value});
    toast(`${ref}: distância e consumo guardados.`);
    renderPropertyDashboard(property);
  }, button);
  for (const input of [km, rate]) input.addEventListener('keydown', event => { if (event.key === 'Enter') save(); });
  const days = count => count === 1 ? '1 dia' : `${count} dias`;
  const reading = petrol.distance_km == null ? 'Indica a distância (só ida) para contar a gasolina das visitas.'
    : `${days(petrol.trips)} de visitas · ${petrol.km.toLocaleString('pt-PT')} km · ${litresText(petrol.litres)}`
      + (petrol.planned_trips ? ` · ${days(petrol.planned_trips)} marcado${petrol.planned_trips === 1 ? '' : 's'}, `
        + `mais ${litresText(petrol.planned_litres)}` : '');
  return el('div', {class: 'trip-computer'},
    el('span', {class: 'trip-title'}, word('trip.title', 'Gasolina das visitas')),
    el('label', {}, 'Ida', km, 'km'), el('label', {}, 'Consumo', rate, 'L/100 km'),
    el('button', {class: 'link', onclick: event => save(event.currentTarget)}, 'Guardar'),
    el('span', {class: 'trip-reading'}, reading));
}

function propertyCluster(property, data, metrics) {
  const ref = property.reference, signals = panelSignals(data, metrics);
  const unattributed = metrics.openai_usage.unattributed;
  const dials = (skin()?.instruments || plainInstruments)(ref, signals);
  dials.find(dial => dial.classList.contains('gauge-heat'))?.append(heatLimit(property, signals.hoursMax));
  dials.find(dial => dial.classList.contains('gauge-fuel'))?.append(fuelFill(property, signals.fuel));
  const period = el('select', {class: 'period-select', 'aria-label': 'Período do gráfico'},
    [...$('chart-period').options].map(option => el('option', {value: option.value}, option.textContent)));
  period.value = $('chart-period').value;
  period.addEventListener('change', () => {  // the same period as the Painel's chart, in both places
    $('chart-period').value = period.value;
    try { localStorage.setItem('bot-mail-period', period.value); } catch { /* Storage may be unavailable. */ }
    renderPropertyDashboard(property);
  });
  return el('article', {class: 'card cluster'},
    el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, word('cluster.eyebrow', 'PAINEL DO IMÓVEL')), el('h2', {}, ref)),
      el('span', {class: 'muted small'}, `Última leitura ${ago(data.last_read_at)}`)),
    el('div', {class: 'cluster-gauges'}, dials),
    tripComputer(property, signals.petrol),
    el('div', {class: 'cluster-odometers'},
      odometer(data.answered, 'Respostas enviadas'),
      odometer(data.clients.ok + data.clients.pending + data.clients.booked, 'Clientes ativos'),
      odometer(data.customers, 'Contactos'),
      odometer(data.visits_booked, 'Visitas marcadas', 3)),
    el('div', {class: 'cluster-lamps'},
      lamp('Rascunhos', data.drafts, 'green'),
      lamp('Bloqueados', data.blocked, 'red', undefined, 'blocked'),
      lamp('Atenção', data.attention, 'red', undefined, 'engine'),
      lamp(word('lamp.heat', 'Resposta lenta'), signals.hot ? 1 : 0, 'red', signals.hot ? hoursText(signals.hours) : '', 'heat'),
      lamp('Só noutra data', data.clients.outra_data, 'amber'),
      lamp('Blacklist', data.ignored.black, 'red'),
      lamp('Greylist', data.ignored.grey, 'grey'),
      lamp('Reserva', signals.fuel.reserve || signals.fuel.empty ? 1 : 0, 'amber', signals.fuel.empty ? 'vazio' : '', 'fuel')),
    el('div', {class: 'cluster-chart'},
      el('div', {class: 'section-heading'}, el('p', {class: 'eyebrow'}, word('cluster.chart', 'O RITMO DESTE IMÓVEL')), period),
      chart(data.by_day, metrics.bucket_days || 1),
      el('div', {class: 'legend'}, el('span', {class: 'requests'}, 'Pedidos recebidos'),
        el('span', {class: 'sent'}, 'Respostas enviadas'))),
    unattributed.calls ? el('p', {class: 'cluster-note'},
      `${unattributed.calls} pedido(s) à API anteriores a 24/09 (${costFormat.format(unattributed.cost_usd)}) não guardaram `
      + 'o imóvel: contam no custo total do Painel, mas não aqui.') : null);
}

// Black list (the owner decided) and grey list (the customer opted out): the same effect — never queued
// again, never sent anything automatic — kept apart so it is clear, later, whose choice it was.
function ignoreListCard(property, kind, customers) {
  const grey = kind === 'grey';
  const input = el('input', {type: 'email', placeholder: 'email@exemplo.com', 'aria-label': `Email para a ${grey ? 'greylist' : 'blacklist'}`});
  const done = result => { state = result.state; renderState(); renderPropertySlider(); };
  return el('article', {class: `card ignore-list ${kind}`},
    el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, grey ? 'GREYLIST' : 'BLACKLIST'),
        el('h2', {}, grey ? 'Pediram para parar' : 'Decidiste parar')),
      el('span', {class: 'tag'}, String(customers.length))),
    el('p', {class: 'step'}, grey
      ? 'Disseram que não têm interesse: não voltam a receber nada deste imóvel.'
      : 'Por decisão tua: nunca mais entram em Respostas, mesmo que escrevam, nem recebem envios automáticos.'),
    el('div', {class: 'client-list'}, customers.length ? customers.map(customer => el('div', {class: 'client-row'},
      el('span', {}, customer.name || customer.email,
        customer.reason ? el('span', {class: 'muted small ignore-reason'}, customer.reason) : null),
      el('button', {class: 'link', onclick: event => run(async () => {
        done(await call('api/contacts/ignore', {property_ref: property.reference, email: customer.email, ignored: false}));
        toast(`${customer.name || customer.email} deixou de ser ignorado(a).`);
      }, event.currentTarget)}, 'Deixar de ignorar')))
      : el('p', {class: 'muted small'}, 'Ninguém.')),
    el('div', {class: 'row'}, input, el('button', {onclick: event => run(async () => {
      if (!input.value.trim()) throw new Error('Escreve o email.');
      done(await call('api/contacts/ignore', {property_ref: property.reference, email: input.value.trim(), ignored: true,
        kind, reason: grey ? 'Cliente disse que não tem interesse.' : ''}));
      toast(`Acrescentado à ${grey ? 'greylist' : 'blacklist'}.`);
    }, event.currentTarget)}, 'Acrescentar')));
}

async function renderPropertyDashboard(property, slide = '') {
  // Only the latest request draws: switching property mid-load must not be overwritten by the older one.
  const token = renderPropertyDashboard.token = (renderPropertyDashboard.token || 0) + 1;
  await run(async () => {
    const ref = property.reference;
    const metrics = await call('api/metrics', {days: Number($('chart-period').value) || 14});
    const ignored = await call('api/contacts/ignored', {property_ref: ref});
    const round = property.visits?.closed_at ? null : await call('api/visits/round-summary', {property_ref: ref});
    const data = metrics.properties.find(item => item.property_ref === ref);
    if (token !== renderPropertyDashboard.token || !data) return;
    const wrap = el('div', {class: slide}, propertyCluster(property, data, metrics),
      el('div', {class: 'dashboard-lists'},
        ignoreListCard(property, 'black', ignored.customers.filter(customer => customer.kind === 'black')),
        ignoreListCard(property, 'grey', ignored.customers.filter(customer => customer.kind === 'grey')),
        el('article', {class: 'card'}, el('p', {class: 'eyebrow'}, 'ÚLTIMA RONDA DE VISITAS'),
          round ? roundSummaryContent(round) : el('p', {class: 'muted small'}, 'Visitas fechadas neste imóvel.'))));
    $('property-dashboard').replaceChildren(wrap);
  });
}

function renderVoice() {
  const selects = {};
  const choice = (key, label) => {
    const voice = settings.voice[key];
    const labels = {normal: 'Habitual', formal: 'Formal', cordial: 'Cordial', multilingual: 'Idioma do cliente',
      pt_en_fr: 'Português, inglês ou francês', multilingual_en_backup: 'Idioma do cliente + tradução em inglês'};
    const hint = el('span', {class: 'choice-hint', id: 'hint-' + key});
    selects[key] = el('select', {'aria-describedby': 'hint-' + key}, el('option', {value: ''}, '— escolhe —'),
      Object.entries(voice.options).map(([name, text]) => el('option', {value: name, title: text}, labels[name] || name)));
    selects[key].value = voice.selected || '';
    const updateHint = () => { hint.textContent = voice.options[selects[key].value] || ''; };
    selects[key].addEventListener('change', updateHint); updateHint();
    return el('label', {class: 'field'}, label, selects[key], hint);
  };
  const signature = el('input', {value: settings.voice.signature || ''});
  const senderName = el('input', {value: settings.voice.sender_name || '', placeholder: 'vazio: só o endereço de email'});
  const replySubject = el('input', {value: settings.voice.reply_subject || ''});
  const visits = settings.voice.visits || {};
  const slot = el('input', {type: 'number', min: 10, max: 180, step: 5, value: visits.slot_minutes || 30});
  const rental = el('input', {value: visits.rental || '', placeholder: 'ex.: 15 a 20 minutos'});
  const sale = el('input', {value: visits.sale || '', placeholder: 'ex.: 30 a 40 minutos'});
  const behaviour = el('textarea', {rows: 4}, settings.voice.application_instructions || '');
  const reminders = settings.voice.reminders || {day2: '', day4: ''};
  const reminderDay2 = el('textarea', {rows: 2, placeholder: 'ex.: Ainda precisa de alguma informação sobre o imóvel?'}, reminders.day2 || '');
  const reminderDay4 = el('textarea', {rows: 2, placeholder: 'ex.: Ficamos à disposição se ainda tiver interesse em visitar.'}, reminders.day4 || '');
  const visitsClosed = el('textarea', {rows: 4, placeholder: 'ex.: Agradecemos o interesse. As visitas a este imóvel já estão fechadas.'}, settings.voice.visits_closed || '');
  const consentRequest = el('textarea', {rows: 4, placeholder: 'ex.: Podemos guardar o seu contacto para futuras oportunidades semelhantes? Responda "sim" se concordar.'}, settings.voice.consent_request || '');
  const digestRecipient = el('input', {type: 'email', value: settings.voice.digest_recipient || '', placeholder: 'vazio: sem ponto de situação diário'});
  $('voice-form').replaceChildren(el('p', {class: 'eyebrow'}, 'VOZ ', kind('voice')),
    choice('greeting', 'Saudação'), choice('languages', 'Idiomas'), choice('closing', 'Fecho'),
    el('label', {class: 'field'}, 'Assinatura (sempre igual, sem tradução)', signature),
    el('label', {class: 'field'}, 'Nome do remetente, ao lado do endereço', senderName),
    el('label', {class: 'field'},
      'Assunto das respostas a pedidos do portal ({imovel} e {referencia}). Nas respostas do próprio cliente mantém-se o assunto dele.',
      replySubject),
    el('label', {class: 'field'}, el('span', {}, 'Comportamento geral: como aplicar a voz em todas as respostas', kind('prompt')), behaviour),
    el('div', {class: 'grid'},
      el('label', {class: 'field'}, 'Marcar visitas de quantos em quantos minutos', slot),
      el('label', {class: 'field'}, 'Uma visita de arrendamento dura', rental),
      el('label', {class: 'field'}, 'Uma visita de compra dura', sale)),
    el('p', {class: 'eyebrow voice-section'}, 'LEMBRETES, VISITAS FECHADAS E CONSENTIMENTO ', kind('voice')),
    el('p', {class: 'step voice-section'},
      'Preparados pelo programa (sem ChatGPT) e enviados só depois de reveres e confirmares, como qualquer outro rascunho.'),
    el('label', {class: 'field'}, 'Lembrete aos 2 dias sem resposta (fica por cima do último texto enviado)', reminderDay2),
    el('label', {class: 'field'}, 'Lembrete aos 4 dias sem resposta (o segundo e último)', reminderDay4),
    el('label', {class: 'field'}, 'Email de «visitas fechadas», para todos os clientes do imóvel', visitsClosed),
    el('label', {class: 'field'}, 'Pedido de consentimento RGPD, para quem já respondeu', consentRequest),
    el('p', {class: 'eyebrow voice-section'}, 'PONTO DE SITUAÇÃO DIÁRIO ', kind('voice')),
    el('p', {class: 'step voice-section'},
      'Um rascunho é preparado a cada leitura de emails, para este endereço; só sai depois de reveres e '
      + 'clicares «Enviar» no Painel, tal como o resto. Vazio: a funcionalidade fica desligada.'),
    el('label', {class: 'field'}, 'Enviar o ponto de situação diário para', digestRecipient),
    el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
      const choices = Object.fromEntries(Object.entries(selects).map(([key, select]) => [key, select.value]));
      settings = await call('api/voice', {...choices, signature: signature.value,
        sender_name: senderName.value, reply_subject: replySubject.value, application_instructions: behaviour.value,
        visits: {slot_minutes: Number(slot.value), rental: rental.value, sale: sale.value},
        reminders: {day2: reminderDay2.value, day4: reminderDay4.value},
        visits_closed: visitsClosed.value, consent_request: consentRequest.value, digest_recipient: digestRecipient.value});
      renderSettings(); await refreshState(); toast('Voz guardada.');
    }, event.currentTarget)}, 'Guardar voz')));
}

document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
$('queue').addEventListener('change', renderState);
$('emails').addEventListener('change', updateSelection);
$('read').addEventListener('click', event => run(async () => {
  state = await call('api/read', {days: Number($('days').value) || undefined}); renderState();
  toast(state.added ? `${state.added} email(s) novo(s).` : 'Leitura concluída: nada de novo.');
}, event.currentTarget));
$('build-prompt').addEventListener('click', event => run(async () => {
  const ids = selectedIds();
  if (!ids.length) throw new Error('Seleciona pelo menos um email.');
  const {prompt} = await call('api/prompt', {property_ref: queueRef(), ids, extra: $('extra').value});
  $('prompt').textContent = prompt;
  $('prompt-box').open = true;
  $('copy-prompt').disabled = false;
  markStep('prepare-step', true);
  toast(`Prompt criado (${ids.length} email(s)): revê abaixo e depois copia.`);
}, event.currentTarget));
$('copy-prompt').addEventListener('click', event => run(async () => {
  const text = $('prompt').textContent;
  if (!text) throw new Error('Cria o prompt primeiro.');
  await copyText(text, 'Prompt copiado. Cola-o numa conversa do ChatGPT.', $('prompt-box'));
}, event.currentTarget));
$('extra').addEventListener('input', () => { $('copy-prompt').disabled = true; });
$('generate-api').addEventListener('click', event => run(async () => {
  const ids = selectedIds();
  if (!ids.length) throw new Error('Seleciona pelo menos um email.');
  const result = await call('api/prompt/generate', {property_ref: queueRef(), ids, extra: $('extra').value});
  state = result.state; keepSteps(renderState); applyFuel(result.fuel, queueRef());
  $('notes').replaceChildren(...result.notes.map(note => el('p', {class: 'alert warn'}, `Nota sobre ${nameOf(note.id)}: ${note.nota}`)));
  markStep('prepare-step', true); markStep('import-step', true);  // this one button does the work of both
  const tokens = (result.tokens?.prompt_tokens || 0) + (result.tokens?.completion_tokens || 0);
  const summary = `${result.saved} rascunho(s) gerado(s) via API` + (result.visits ? ` e ${result.visits} marcação(ões) de visita` : '')
    + (tokens ? ` (${tokens} tokens)` : '') + '.';
  toast(summary + ' Revê-os no passo 01 antes de enviar.');
}, event.currentTarget));
$('paste').addEventListener('click', event => run(async () => {
  const text = $('answer').value;
  if (!text.trim()) throw new Error('Cola primeiro a resposta do ChatGPT.');
  const result = await call('api/paste', {property_ref: queueRef(), text});
  state = result.state; keepSteps(renderState);
  $('notes').replaceChildren(...result.notes.map(note => el('p', {class: 'alert warn'}, `Nota do ChatGPT sobre ${nameOf(note.id)}: ${note.nota}`)));
  $('answer').value = '';
  const summary = `${result.saved} rascunho(s) guardado(s)` + (result.visits ? ` e ${result.visits} marcação(ões) de visita` : '') + '.';
  $('import-status').hidden = false;
  $('import-status').textContent = `✓ ${summary} Revê-os no passo 01, ou cola outra resposta aqui para acrescentar mais.`;
  markStep('import-step', true);
  toast(summary + ' Revê-os no passo 01 antes de enviar.');
}, event.currentTarget));
$('answer').addEventListener('input', () => { $('import-status').hidden = true; markStep('import-step', false); });
$('preview').addEventListener('click', event => run(async () => {
  const ids = selectedIds();
  if (!ids.length) throw new Error('Seleciona pelo menos um email.');
  if ($('answer').value.trim()) {
    // Only the page knows this: the server never sees a paste until "Guardar rascunhos".
    $('import-step').scrollIntoView({behavior: 'smooth', block: 'center'});
    throw new Error('Tens uma resposta colada no passo 03 que ainda não foi guardada. Carrega em «Guardar rascunhos» '
      + '(ou apaga-a) antes de pré-visualizar.');
  }
  preview = await call('api/preview', {property_ref: queueRef(), ids});
  renderPreview();
  toast(`Pré-visualização pronta: ${preview.replies.length} email(s) por rever antes de enviar.`);
}, event.currentTarget));
$('listing-prompt').addEventListener('click', event => run(async () => {
  const {prompt} = await call('api/property/prompt', {listing_url: $('listing-url').value});
  $('listing-prompt-text').textContent = prompt;
  await copyText(prompt, 'Prompt copiado. Cola-o no ChatGPT e traz a resposta.', $('listing-prompt-box'));
}, event.currentTarget));
$('listing-parse').addEventListener('click', event => run(async () => {
  const {fields} = await call('api/property/parse', {text: $('listing-answer').value});
  const existing = settings.properties.some(property => property.reference === fields.reference);
  openPropertyEditor({...fields, sender: null}, existing ? fields.reference : null);
  toast('Campos preenchidos: revê-os antes de guardar.', 'warn');
}, event.currentTarget));
$('property-save').addEventListener('click', event => run(async () => {
  const fields = Object.fromEntries(FIELDS.map(name => [name, $('f-' + name).value.trim() || null]));
  fields.facts = $('f-facts').value;
  const result = await call('api/property/save', {fields});
  settings = result.settings; editorRef = result.reference;
  selectProperty(result.reference, 0, false); renderSettings(); showPropertiesView('list'); await refreshState();
  toast(`Imóvel ${result.reference} ${result.created ? 'criado' : 'atualizado'}. Revê a base de conhecimento na pasta do imóvel.`);
}, event.currentTarget));

applySkin();  // here, once everything it draws with is defined
run(async () => { await loadMetrics(); await loadDigest(); await refreshState(); await loadSettings(); });
