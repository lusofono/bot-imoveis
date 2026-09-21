// The page's logic. It only talks to the API (fetch); every rule is decided there.
// TOKEN is written into index.html by the server at each start and goes with every API call.
const STATUS ={pending: 'por responder', draft: 'rascunho', error: 'erro no envio', sending: 'a enviar', uncertain: 'envio incerto'};
const FIELDS = ['reference', 'sender', 'listing_id', 'listing_url', 'advertiser', 'advertised_rent_eur', 'description'];
const $ = id => document.getElementById(id);
let state = {properties: []}, settings = null, preview = null;

// Only the visual preference is stored locally; never account or email content.
const THEMES = ['night', 'day', 'indigo', 'amber'];
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
});

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

async function run(action) { try { await action(); } catch (error) { toast(error.message, 'bad'); } }

async function copyText(text, done, fallbackBox) {
  try { await navigator.clipboard.writeText(text); toast(done); }
  catch { fallbackBox.open = true; toast('Não consegui copiar sozinho: seleciona o texto do prompt e copia-o.', 'warn'); }
}

function showTab(name) {
  document.querySelectorAll('nav [data-tab]').forEach(button => {
    button.classList.toggle('active', button.dataset.tab === name);
    if (button.dataset.tab === name) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  $('page-label').textContent = {dashboard: 'Painel', replies: 'Respostas', properties: 'Imóveis', voice: 'Voz e estilo'}[name];
  for (const tab of ['dashboard', 'replies', 'properties', 'voice']) $('tab-' + tab).hidden = tab !== name;
  window.scrollTo({top: 0, behavior: 'instant'});
  if (name === 'dashboard') run(loadMetrics);
}

// The chart is drawn by hand: the page may not load anything from outside.
function svg(tag, attrs = {}, ...children) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  node.append(...children.flat(Infinity).filter(child => child != null));
  return node;
}

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
  updateSelection();
}

function updateSelection() {
  const count = selectedIds().length;
  $('selection-count').textContent = `${count} selecionado(s)`;
  $('copy-prompt').disabled = !count;
  $('preview').disabled = !count;
}

function card(email) {
  const customer = email.customer || {}, sender = (email.from || [])[0] || {};
  const draft = el('textarea', {'aria-label': 'Rascunho da resposta', rows: 7, placeholder: 'Rascunho: cola a resposta do ChatGPT no passo 3 ou escreve aqui.'}, email.reply_text || '');
  const contact = [customer.email || (email.recipient || {}).email, customer.phone].filter(Boolean).join(' · ');
  return el('article', {class: 'card email-card' + (email.blocked ? ' blocked' : '')},
    el('div', {class: 'card-head'},
      el('label', {class: 'who'}, el('input', {type: 'checkbox', class: 'pick', 'data-id': email.id, checked: !email.blocked, disabled: !!email.blocked}),
        el('strong', {}, customer.name || sender.name || sender.email || 'Sem nome')),
      email.interaction && el('span', {class: 'tag'}, email.interaction + '.ª interação'),
      el('span', {class: 'tag' + (email.reply_status === 'draft' ? ' draft' : '')}, STATUS[email.reply_status] || email.reply_status || ''),
      el('span', {class: 'muted small'}, when(email.date))),
    contact && el('div', {class: 'muted small'}, contact),
    email.blocked && el('p', {class: 'alert bad'}, email.blocked),
    (email.warnings || []).map(warning => el('p', {class: 'alert warn'}, warning)),
    email.reply_error && el('p', {class: 'alert bad'}, email.reply_error),
    el('blockquote', {}, customer.message || email.body_text || ''),
    el('details', {}, el('summary', {class: 'muted small'}, 'Email completo'), el('pre', {}, email.body_text || '')),
    draft,
    el('div', {class: 'actions'},
      el('button', {onclick: () => run(async () => {
        state = await call('api/drafts', {property_ref: queueRef(), replies: [{id: email.id, reply_text: draft.value}]});
        renderState(); toast('Rascunho guardado.');
      })}, 'Guardar rascunho'),
      el('button', {class: 'link danger', onclick: () => run(async () => {
        if (!confirm('Retirar este email da fila sem responder? O Gmail não é alterado e o email não volta a entrar.')) return;
        state = await call('api/dismiss', {property_ref: queueRef(), ids: [email.id]});
        renderState(); toast('Email retirado da fila.');
      })}, 'Retirar da fila')));
}

function renderPreview() {
  const box = $('preview-box'), count = preview.replies.length;
  box.replaceChildren(
    el('p', {class: 'alert warn'}, `Vais enviar ${count} email(s) reais. Confere destinatários e textos; esta pré-visualização vale 15 minutos.`),
    ...preview.replies.map(reply => el('article', {class: 'card'},
      el('div', {}, el('strong', {}, 'Para: '), reply.to), el('div', {}, el('strong', {}, 'Assunto: '), reply.subject),
      (reply.warnings || []).map(warning => el('p', {class: 'alert warn'}, warning)), el('pre', {}, reply.reply_text))),
    el('div', {class: 'actions'},
      el('button', {class: 'primary', onclick: () => run(async () => {
        if (!confirm(`Enviar agora ${count} email(s) reais?`)) return;
        const result = await call('api/send', {property_ref: queueRef(), preview_token: preview.preview_token, confirmed: true});
        const sent = result.results.filter(item => item.status === 'sent').length;
        state = await call('api/state'); renderState();
        toast(`Enviados: ${sent} de ${result.results.length}.` + (sent < result.results.length ? ' Vê os avisos nos que ficaram.' : ''),
          sent === result.results.length ? 'ok' : 'warn');
      })}, `Enviar ${count} email(s)`),
      el('button', {class: 'link', onclick: () => { preview = null; box.replaceChildren(); }}, 'Cancelar')));
}

function ago(value) {
  if (!value) return 'ainda não houve leitura';
  const hours = (Date.now() - new Date(value).getTime()) / 3600000;
  if (hours < 1) return `há ${Math.max(1, Math.round(hours * 60))} min`;
  if (hours < 24) return `há ${Math.round(hours)} h`;
  return `há ${Math.round(hours / 24)} dia(s)`;
}

function metricCard(value, label, kind) {
  return el('article', {class: 'metric' + (kind && value ? ' ' + kind : '')},
    el('div', {class: 'value'}, String(value)), el('div', {class: 'label'}, label));
}

function chart(days) {
  const width = 640, height = 150, base = height - 22, top = 12;
  const most = Math.max(1, ...days.map(day => Math.max(day.requests, day.sent)));
  const slot = width / days.length, bar = slot / 2 - 3;
  const column = (value, x, cls) => value
    ? svg('rect', {x, y: base - Math.max(3, (base - top) * value / most), width: bar,
                   height: Math.max(3, (base - top) * value / most), rx: 2, class: cls})
    : null;
  return svg('svg', {viewBox: `0 0 ${width} ${height}`, class: 'chart', role: 'img',
                     'aria-label': 'Pedidos recebidos e respostas enviadas por dia'},
    svg('line', {x1: 0, y1: base, x2: width, y2: base, class: 'grid-line'}),
    days.map((day, i) => [
      column(day.requests, i * slot + 2, 'bar-requests'),
      column(day.sent, i * slot + slot / 2 + 1, 'bar-sent'),
      svg('text', {x: i * slot + slot / 2, y: height - 6, class: 'bar-label'}, day.day.slice(8) + '/' + day.day.slice(5, 7))]));
}

function renderDashboard(data) {
  const totals = data.totals;
  $('metric-cards').replaceChildren(
    metricCard(totals.pending, 'Pedidos por responder'),
    metricCard(totals.drafts, 'Rascunhos prontos', 'ok'),
    metricCard(totals.blocked, 'Bloqueados', 'warn'),
    metricCard(totals.attention, 'A precisar de atenção', 'bad'),
    metricCard(totals.answered, 'Respostas enviadas'),
    metricCard(data.reply_hours == null ? '—' : data.reply_hours + ' h', 'Tempo médio até resposta'));
  $('dashboard-read').textContent = `Última leitura ${ago(data.last_read_at)}`
    + (data.last_read_at ? ` (${when(data.last_read_at)})` : '') + ` · conta ${data.account}`;
  $('dashboard-chart').replaceChildren(chart(data.by_day));
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
          el('button', {class: 'link', onclick: () => {
            $('queue').value = item.property_ref || ''; renderState(); showTab('replies');
          }}, 'Ver respostas →'))))) : [el('div', {class: 'empty-state'}, 'Ainda não há imóveis configurados. Adiciona o primeiro em Imóveis.')]));
  const check = (ok, label, hint) => el('li', {},
    el('span', {class: 'dot' + (ok ? '' : ' missing')}), el('span', {}, label,
      !ok && hint ? el('span', {class: 'muted small'}, ' — ' + hint) : ''));
  $('dashboard-setup').replaceChildren(
    check(data.setup.account, 'Conta de email configurada', 'corre mac/setup.command'),
    check(data.setup.app_password, 'App Password guardada no Keychain', 'corre mac/password.command'),
    check(data.setup.voice, 'Voz completa', 'preenche o separador Voz e estilo'),
    check(data.setup.properties > 0, `Imóveis configurados: ${data.setup.properties}`, 'cria um no separador Imóveis'));
}

async function loadMetrics() { renderDashboard(await call('api/metrics')); }

async function refreshState() { state = await call('api/state'); renderState(); }
async function loadSettings() { settings = await call('api/settings'); renderSettings(); }

function renderSettings() {
  renderVoice();
  $('property-list').replaceChildren(...(settings.properties.length ? settings.properties.map(propertyCard)
    : [el('p', {class: 'muted'}, 'Ainda não há imóveis: cria o primeiro abaixo.')]));
  if (!$('f-sender').value) $('f-sender').value = settings.properties[0]?.sender || 'reply@idealista.pt';
}

function propertyCover(ref, hasPhoto) {
  const cover = el('div', {class: 'property-cover'});
  const fallback = () => cover.replaceChildren(el('span', {class: 'property-monogram', 'aria-hidden': 'true'}, '⌂'));
  if (hasPhoto && ref) cover.append(el('img', {src: 'photo/' + encodeURIComponent(ref), alt: 'Fotografia do imóvel ' + ref, loading: 'lazy', onerror: fallback}));
  else fallback();
  return cover;
}

function propertyCard(property) {
  const areas = {};
  const area = (name, label, rows) => {
    areas[name] = el('textarea', {rows}, property.prompts[name] || '');
    return el('label', {class: 'field'}, label, areas[name]);
  };
  const link = /^https:\/\//.test(property.listing_url || '')
    && el('a', {href: property.listing_url, target: '_blank', rel: 'noopener noreferrer'}, property.listing_url);
  return el('article', {class: 'card'},
    propertyCover(property.reference, property.photo),
    el('div', {class: 'card-head'}, el('strong', {}, property.reference), el('span', {}, property.description || ''),
      property.advertised_rent_eur != null && el('span', {class: 'tag'}, property.advertised_rent_eur + ' €')),
    el('div', {class: 'muted small'}, [property.sender, property.listing_id && 'anúncio ' + property.listing_id,
      property.knowledge_files.length ? 'conhecimento: ' + property.knowledge_files.join(', ') : 'base de conhecimento vazia']
      .filter(Boolean).join(' · ')),
    link,
    el('details', {}, el('summary', {class: 'muted small'}, 'Prompts deste imóvel'),
      area('general', 'Prompt base: contexto do imóvel', 4),
      area('first', '1.ª interação', 4), area('first_template', 'Texto base da 1.ª resposta (opcional)', 4),
      area('second', '2.ª interação (vazio: o ChatGPT avisa-te e aguarda)', 3),
      area('knowledge', 'Como usar a base de conhecimento (RAG)', 3),
      el('button', {class: 'primary', onclick: () => run(async () => {
        const prompts = Object.fromEntries(Object.entries(areas).map(([name, box]) => [name, box.value]));
        settings = await call('api/property/prompts', {reference: property.reference, prompts});
        renderSettings(); await refreshState(); toast('Prompts guardados.');
      })}, 'Guardar prompts')),
    el('button', {class: 'link', onclick: () => fillProperty(property)}, 'Editar dados do anúncio'));
}

function fillProperty(fields) {
  for (const name of FIELDS) if (name !== 'sender' || fields.sender) $('f-' + name).value = fields[name] ?? '';
  $('f-facts').value = (fields.facts || []).join('\n');
  $('f-reference').scrollIntoView({behavior: 'smooth', block: 'center'});
}

function renderVoice() {
  const selects = {};
  const choice = (key, label) => {
    const voice = settings.voice[key];
    const labels = {normal: 'Habitual', formal: 'Formal', cordial: 'Cordial', multilingual: 'Idioma do cliente', pt_en_fr: 'Português, inglês ou francês'};
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
  $('voice-form').replaceChildren(choice('greeting', 'Saudação'), choice('languages', 'Idiomas'), choice('closing', 'Fecho'),
    el('label', {class: 'field'}, 'Assinatura (sempre igual, sem tradução)', signature),
    el('label', {class: 'field'}, 'Nome do remetente, ao lado do endereço', senderName),
    el('label', {class: 'field'},
      'Assunto das respostas a pedidos do portal ({imovel} e {referencia}). Nas respostas do próprio cliente mantém-se o assunto dele.',
      replySubject),
    el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: () => run(async () => {
      const choices = Object.fromEntries(Object.entries(selects).map(([key, select]) => [key, select.value]));
      settings = await call('api/voice', {...choices, signature: signature.value,
        sender_name: senderName.value, reply_subject: replySubject.value});
      renderSettings(); await refreshState(); toast('Voz guardada.');
    })}, 'Guardar voz')));
}

document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
$('queue').addEventListener('change', renderState);
$('emails').addEventListener('change', updateSelection);
$('read').addEventListener('click', () => run(async () => {
  state = await call('api/read', {}); renderState();
  toast(state.added ? `${state.added} email(s) novo(s).` : 'Leitura concluída: nada de novo.');
}));
$('copy-prompt').addEventListener('click', () => run(async () => {
  const ids = selectedIds();
  if (!ids.length) throw new Error('Seleciona pelo menos um email.');
  const {prompt} = await call('api/prompt', {property_ref: queueRef(), ids, extra: $('extra').value});
  $('prompt').textContent = prompt;
  await copyText(prompt, `Prompt copiado (${ids.length} email(s)). Cola-o numa conversa do ChatGPT.`, $('prompt-box'));
}));
$('paste').addEventListener('click', () => run(async () => {
  const result = await call('api/paste', {property_ref: queueRef(), text: $('answer').value});
  state = result.state; renderState();
  $('notes').replaceChildren(...result.notes.map(note => el('p', {class: 'alert warn'}, `Nota do ChatGPT sobre ${nameOf(note.id)}: ${note.nota}`)));
  $('answer').value = '';
  toast(`${result.saved} rascunho(s) guardado(s). Revê-os no passo 1 antes de enviar.`);
}));
$('preview').addEventListener('click', () => run(async () => {
  const ids = selectedIds();
  if (!ids.length) throw new Error('Seleciona pelo menos um email.');
  preview = await call('api/preview', {property_ref: queueRef(), ids});
  renderPreview();
}));
$('listing-prompt').addEventListener('click', () => run(async () => {
  const {prompt} = await call('api/property/prompt', {listing_url: $('listing-url').value});
  $('listing-prompt-text').textContent = prompt;
  await copyText(prompt, 'Prompt copiado. Cola-o no ChatGPT e traz a resposta.', $('listing-prompt-box'));
}));
$('listing-parse').addEventListener('click', () => run(async () => {
  const {fields} = await call('api/property/parse', {text: $('listing-answer').value});
  fillProperty({...fields, sender: null});
  toast('Campos preenchidos: revê-os antes de guardar.', 'warn');
}));
$('property-save').addEventListener('click', () => run(async () => {
  const fields = Object.fromEntries(FIELDS.map(name => [name, $('f-' + name).value.trim() || null]));
  fields.facts = $('f-facts').value;
  const result = await call('api/property/save', {fields});
  settings = result.settings; renderSettings(); await refreshState();
  toast(`Imóvel ${result.reference} ${result.created ? 'criado' : 'atualizado'}. Revê a base de conhecimento na pasta do imóvel.`);
}));

run(async () => { await loadMetrics(); await refreshState(); await loadSettings(); });
