// The page's logic. It only talks to the API (fetch); every rule is decided there.
// TOKEN is written into index.html by the server at each start and goes with every API call.
const STATUS ={pending: 'por responder', draft: 'rascunho', error: 'erro no envio', sending: 'a enviar', uncertain: 'envio incerto'};
const FIELDS = ['reference', 'sender', 'listing_id', 'listing_url', 'advertiser', 'advertised_rent_eur', 'description'];
const $ = id => document.getElementById(id);
let state = {properties: []}, settings = null, preview = null;

// Emails are untrusted: every value goes in as text, never as HTML.
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value !== false && value != null) node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat()) if (child != null && child !== false && child !== '') node.append(child);
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
  document.querySelectorAll('[data-tab]').forEach(button => button.classList.toggle('active', button.dataset.tab === name));
  for (const tab of ['replies', 'properties', 'voice']) $('tab-' + tab).hidden = tab !== name;
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
  $('error').hidden = !state.error; $('error').textContent = state.error || '';
  const select = $('queue'), chosen = select.value;
  select.replaceChildren(...state.properties.map(queue => el('option', {value: queue.property_ref ?? ''}, queue.property_ref ?? 'Todos')));
  if ([...select.options].some(option => option.value === chosen)) select.value = chosen;
  const queue = currentQueue();
  $('last-read').textContent = queue?.last_read_at ? 'Última leitura: ' + when(queue.last_read_at) : '';
  const emails = queue?.emails || [];
  $('emails').replaceChildren(...(emails.length ? emails.map(card)
    : [el('p', {class: 'muted'}, state.error ? '' : 'Não há emails pendentes. Usa «Ler emails do Gmail».')]));
  $('instructions').textContent = queue?.instructions || '';
  preview = null; $('preview-box').replaceChildren();
}

function card(email) {
  const customer = email.customer || {}, sender = (email.from || [])[0] || {};
  const draft = el('textarea', {rows: 7, placeholder: 'Rascunho: cola a resposta do ChatGPT no passo 3 ou escreve aqui.'}, email.reply_text || '');
  const contact = [customer.email || (email.recipient || {}).email, customer.phone].filter(Boolean).join(' · ');
  return el('article', {class: 'card' + (email.blocked ? ' blocked' : '')},
    el('div', {class: 'card-head'},
      el('label', {class: 'who'}, el('input', {type: 'checkbox', class: 'pick', 'data-id': email.id, checked: !email.blocked, disabled: !!email.blocked}),
        el('strong', {}, customer.name || sender.name || sender.email || 'Sem nome')),
      email.interaction && el('span', {class: 'tag'}, email.interaction + '.ª interação'),
      el('span', {class: 'tag'}, STATUS[email.reply_status] || email.reply_status || ''),
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

async function refreshState() { state = await call('api/state'); renderState(); }
async function loadSettings() { settings = await call('api/settings'); renderSettings(); }

function renderSettings() {
  renderVoice();
  $('property-list').replaceChildren(...(settings.properties.length ? settings.properties.map(propertyCard)
    : [el('p', {class: 'muted'}, 'Ainda não há imóveis: cria o primeiro abaixo.')]));
  if (!$('f-sender').value) $('f-sender').value = settings.properties[0]?.sender || 'reply@idealista.pt';
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
    selects[key] = el('select', {}, el('option', {value: ''}, '— escolhe —'),
      Object.entries(voice.options).map(([name, text]) => el('option', {value: name}, `${name}: ${text}`)));
    selects[key].value = voice.selected || '';
    return el('label', {class: 'field'}, label, selects[key]);
  };
  const signature = el('input', {value: settings.voice.signature || ''});
  $('voice-form').replaceChildren(choice('greeting', 'Saudação'), choice('languages', 'Idiomas'), choice('closing', 'Fecho'),
    el('label', {class: 'field'}, 'Assinatura (sempre igual, sem tradução)', signature),
    el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: () => run(async () => {
      const choices = Object.fromEntries(Object.entries(selects).map(([key, select]) => [key, select.value]));
      settings = await call('api/voice', {...choices, signature: signature.value});
      renderSettings(); await refreshState(); toast('Voz guardada.');
    })}, 'Guardar voz')));
}

document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
$('queue').addEventListener('change', renderState);
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

run(async () => { await refreshState(); await loadSettings(); });
