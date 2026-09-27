// The demo's backend, in the browser: the page (app.js, unchanged) calls fetch('api/...') as always, and this file
// answers from demo-data.js, which bot-mail webdemo recorded from the real backend with a fictitious agency.
// Nothing leaves the browser: no email is read or sent, no AI is called, and a reload starts the demo again.
(() => {
  'use strict';
  const D = window.DEMO_DATA;
  const DAY = 86400000;
  const clone = value => (value === undefined ? undefined : JSON.parse(JSON.stringify(value)));
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

  // The recordings' dates move to the viewer's week: the day the demo was built becomes today, so the agenda, the
  // «last 14 days» and the visits of tomorrow stay true whenever the demo is shown.
  const noon = value => { const d = new Date(value); d.setHours(12, 0, 0, 0); return d; };
  const delta = Math.round((noon(new Date()) - noon(D.build_day + 'T12:00:00')) / DAY);
  const pad = n => String(n).padStart(2, '0');
  const moved = (y, m, d) => new Date(Date.UTC(+y, +m - 1, +d) + delta * DAY);
  const iso = date => `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
  const LOCALES = {pt: 'pt-PT', en: 'en-GB', fr: 'fr-FR', es: 'es-ES', de: 'de-DE'};
  const WEEKDAYS = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
  function shiftText(text) {
    let out = text.replace(/\[\[D:(\d{4})-(\d{2})-(\d{2}):(\w+)\]\]/g, (_, y, m, d, lang) =>
      moved(y, m, d).toLocaleDateString(LOCALES[lang] || 'pt-PT', {weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC'}));
    if (!delta) return out;
    out = out.replace(/(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)/g, (_, y, m, d) => iso(moved(y, m, d)));
    out = out.replace(/(?:(?:segunda|terça|quarta|quinta|sexta)-feira|sábado|domingo), (\d{2})\/(\d{2})\/(\d{4})/g, (_, d, m, y) => {
      const date = moved(y, m, d);
      return `${WEEKDAYS[date.getUTCDay()]}, ${pad(date.getUTCDate())}/${pad(date.getUTCMonth() + 1)}/${date.getUTCFullYear()}`;
    });
    return out.replace(/(?<!\d)(\d{2})\/(\d{2})\/(\d{4})(?!\d)/g, (_, d, m, y) => {
      const date = moved(y, m, d);
      return `${pad(date.getUTCDate())}/${pad(date.getUTCMonth() + 1)}/${date.getUTCFullYear()}`;
    });
  }
  function shift(value) {
    if (typeof value === 'string') return shiftText(value);
    if (Array.isArray(value)) return value.map(shift);
    if (value && typeof value === 'object') {
      return Object.fromEntries(Object.entries(value).map(([key, item]) => [shiftText(key), shift(item)]));
    }
    return value;
  }
  const blobs = shift(D.blobs);
  const stages = D.stages.map(stage => Object.fromEntries(Object.entries(stage).map(([key, index]) => [shiftText(key), index])));
  const generated = shift(D.generated), notes = shift(D.notes), previews = shift(D.previews);
  const recordedActive = shift(D.active), actions = shift(D.actions), prompts = shift(D.prompts), fuel = shift(D.fuel);

  // Where the demo is: 0 as it opens, 1 after «Ler emails», 2 after «Gerar respostas», 3 after an «Enviar».
  const progress = {read: false, generated: false, sent: false};
  const stageNow = () => (progress.sent ? 3 : progress.generated ? 2 : progress.read ? 1 : 0);
  const sortKeys = value => (value && typeof value === 'object' && !Array.isArray(value)
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, sortKeys(value[key])])) : value);
  const keyOf = (path, body) => path + (body === undefined ? '' : '|' + JSON.stringify(sortKeys(body)));
  function snap(path, body, stage = stageNow()) {
    const recorded = stages[stage];
    const key = keyOf(path, body);
    const found = key in recorded ? key : Object.keys(recorded).find(item => item.split('|')[0] === path);
    return found === undefined ? undefined : clone(blobs[recorded[found]]);
  }

  // The queue, email by email, on top of the recorded one: drafts written, emails sent or taken off, new ones added.
  const gone = new Set(), edits = {}, added = {}, activeAdded = {}, activeGone = new Set(), sendable = {};
  const lower = text => String(text || '').toLowerCase();
  const addressOf = email => lower((email.recipient || {}).email || (email.customer || {}).email);
  function view() {
    const state = snap('api/state', undefined, progress.read ? 1 : 0);
    for (const queue of state.properties) {
      const ref = queue.property_ref;
      const own = new Set(queue.emails.map(email => email.id));
      const emails = queue.emails.concat(clone((added[ref] || []).filter(email => !own.has(email.id))))
        .filter(email => !gone.has(email.id)).map(email => clone(edits[email.id]) || email);
      queue.emails = emails;
      const waiting = new Set(emails.map(addressOf));
      let active = (queue.active || []).filter(item => !activeGone.has(ref + '|' + item.email));
      for (const item of Object.values(activeAdded[ref] || {})) {
        active = [clone(item), ...active.filter(other => other.email !== item.email)];
      }
      queue.active = active.filter(item => !waiting.has(lower(item.email)));
    }
    return state;
  }
  const queueOf = (state, ref) => state.properties.find(queue => queue.property_ref === (ref ?? null)) || state.properties[0];
  const propertyInfo = ref => ((snap('api/metrics', {days: 14}) || {}).properties || []).find(item => item.property_ref === ref) || {};

  function demoDraft(email, ref) {
    // An email the recordings do not know (one the viewer created in the demo): a draft in the agency's voice.
    const name = (email.recipient || {}).name || (email.customer || {}).name || '';
    const info = propertyInfo(ref);
    const house = info.description ? `🏠 ${info.description} — ${info.listing_url || ''}\n\n` : '';
    const signature = '\n\nCom os melhores cumprimentos,\nEquipa Casa Exemplo Imobiliária';
    const window_ = email.visit_window;
    const body = window_
      ? `Estamos a organizar visitas ao imóvel no dia ${new Date(window_.day + 'T12:00:00').toLocaleDateString('pt-PT', {weekday: 'long', day: 'numeric', month: 'long'})}, `
        + `entre as ${window_.start} e as ${window_.end}. Qual a hora que lhe dá mais jeito dentro deste intervalo? Se nenhuma lhe servir, `
        + 'diga-nos por favor a sua disponibilidade habitual nos dias seguintes.'
      : 'Obrigado pela sua mensagem. (Rascunho de demonstração: na versão completa, a IA escreve aqui a resposta com a voz da '
        + 'agência, o conhecimento do imóvel e a conversa toda com o cliente.)';
    return `${name ? `Caro(a) ${name.split(' ')[0]},` : 'Bom dia,'}\n\n${house}${body}${signature}`;
  }

  function notSaved(text = 'Demonstração: esta alteração não fica gravada.') {
    setTimeout(() => { if (typeof window.toast === 'function') window.toast(text, 'warn'); }, 700);
  }
  const UNAVAILABLE = 'Demonstração: esta ação precisa da versão completa, ligada ao teu Gmail e à tua chave da IA.';

  function takeAction(path, body) {
    const recorded = clone(actions[path + '|' + lower(body.email)] || actions[path]);
    if (!recorded) throw new Error(UNAVAILABLE);
    for (const [ref, emails] of Object.entries(recorded.new_emails || {})) {
      added[ref] = [...(added[ref] || []), ...emails.filter(email => !(added[ref] || []).some(other => other.id === email.id))];
    }
    delete recorded.new_emails;
    return {...recorded, state: view()};
  }

  const handlers = {
    'GET api/state': () => view(),

    'POST api/read': async () => {
      await wait(1600);
      let count = 0;
      if (!progress.read) {
        const before = new Set(snap('api/state', undefined, 0).properties.flatMap(queue => queue.emails.map(email => email.id)));
        count = snap('api/state', undefined, 1).properties.flatMap(queue => queue.emails).filter(email => !before.has(email.id)).length;
        progress.read = true;
      }
      return {...view(), added: count, direct: 0};
    },

    'POST api/prompt/generate': async body => {
      const ids = body.ids || [];
      if (!ids.length) throw new Error('Seleciona os emails.');
      await wait(1400 + 350 * ids.length);
      const current = queueOf(view(), body.property_ref);
      let saved = 0;
      for (const id of ids) {
        const email = current.emails.find(item => item.id === id);
        if (!email || email.blocked) continue;
        edits[id] = generated[id] ? clone(generated[id])
          : {...email, reply_text: demoDraft(email, current.property_ref), reply_status: 'draft'};
        saved += 1;
      }
      if (saved) progress.generated = true;
      const tokens = {prompt_tokens: 2400 + 950 * saved, completion_tokens: 290 * saved};
      tokens.total_tokens = tokens.prompt_tokens + tokens.completion_tokens;
      return {saved, notes: ids.map(id => notes[id]).filter(Boolean), visits: 0, fichas: 0, model: 'gpt-4o-mini',
              prompts: prompts[current.property_ref] || [], tokens, fuel: fuel[current.property_ref], state: view()};
    },

    'POST api/drafts': body => {
      const current = queueOf(view(), body.property_ref);
      for (const reply of body.replies || []) {
        const email = current.emails.find(item => item.id === reply.id);
        if (email) edits[reply.id] = {...email, reply_text: reply.reply_text, reply_status: reply.reply_text.trim() ? 'draft' : email.reply_status};
      }
      return view();
    },

    'POST api/preview': body => {
      const current = queueOf(view(), body.property_ref);
      const chosen = (body.ids || []).map(id => current.emails.find(item => item.id === id)).filter(Boolean);
      if (!chosen.length) throw new Error('Seleciona os emails.');
      const missing = chosen.filter(email => !String(email.reply_text || '').trim());
      if (missing.length) {
        const names = missing.map(email => (email.customer || {}).name || (email.recipient || {}).name || 'sem nome').join(', ');
        throw new Error(`${missing.length} email(s) selecionado(s) ainda sem rascunho (${names}). Gera-os no passo 2, `
          + 'ou escreve o rascunho no próprio email e guarda-o, antes de pré-visualizar.');
      }
      const token = 'demo-' + Math.random().toString(36).slice(2);
      sendable[token] = {ref: current.property_ref, ids: chosen.map(email => email.id)};
      return {preview_token: token, expires_in_seconds: 900, property_ref: current.property_ref,
              replies: chosen.map(email => ({id: email.id, reply_text: email.reply_text, warnings: email.warnings || [],
                to: (previews[email.id] || {}).to || addressOf(email), subject: (previews[email.id] || {}).subject || email.subject || ''}))};
    },

    'POST api/send': async body => {
      const batch = sendable[body.preview_token];
      if (!batch) throw new Error('Pré-visualização inválida ou expirada. Prepara novamente o envio.');
      delete sendable[body.preview_token];
      await wait(900 + 250 * batch.ids.length);
      const current = queueOf(view(), batch.ref);
      for (const id of batch.ids) {
        const email = current.emails.find(item => item.id === id);
        gone.add(id);
        if (email && recordedActive[id]) {
          activeAdded[batch.ref] = activeAdded[batch.ref] || {};
          activeAdded[batch.ref][recordedActive[id].email] = {...recordedActive[id], last_text: email.reply_text,
                                                             last_sent_at: new Date().toISOString()};
        }
      }
      progress.sent = true;
      return {results: batch.ids.map(id => ({id, status: 'sent'})), remaining: queueOf(view(), batch.ref).emails.length};
    },

    'POST api/dismiss': body => { (body.ids || []).forEach(id => gone.add(id)); return view(); },

    'POST api/contacts/ignore': body => {
      const current = queueOf(view(), body.property_ref);
      let removed = 0;
      if (body.ignored !== false) {
        for (const email of current.emails) if (addressOf(email) === lower(body.email)) { gone.add(email.id); removed += 1; }
        activeGone.add(current.property_ref + '|' + lower(body.email));
      }
      notSaved('Demonstração: na versão completa, este cliente fica na lista a ignorar deste imóvel.');
      return {property_ref: current.property_ref, removed, state: view()};
    },

    'POST api/active/remove': body => {
      activeGone.add(queueOf(view(), body.property_ref).property_ref + '|' + lower(body.email));
      return {state: view()};
    },
    'POST api/active/write': body => takeAction('api/active/write', body),
    'POST api/visits/thanks': body => takeAction('api/visits/thanks', body),
    'POST api/visits/analyze': async body => { await wait(1800); return takeAction('api/visits/analyze', body); },
    'POST api/knowledge/note': body => { notSaved(); return {...takeAction('api/knowledge/note', body), scope: body.scope}; },
    'POST api/fuel/fill': body => { notSaved(); return takeAction('api/fuel/fill', body); },

    'POST api/visits/propose': body => {
      const ref = body.property_ref;
      const customers = (snap('api/visits/candidates', {property_ref: ref}) || {}).customers || [];
      const window_ = {day: body.day, start: body.start, end: body.end};
      if (!window_.day || !window_.start || !window_.end) throw new Error('Indica o dia e o intervalo.');
      const emails = (body.emails || []).map(address => {
        const known = customers.find(item => lower(item.email) === lower(address)) || {};
        return {id: `visita-demo-${window_.day}-${lower(address)}`, kind: 'visit_proposal', date: new Date().toISOString(),
                recipient: {name: known.name || '', email: address}, customer: {name: known.name || null, email: address, phone: null, message: null},
                blocked: null, warnings: [], visit_window: window_, history: [], reply_text: '', send_reply: false, reply_status: 'pending'};
      });
      added[ref] = [...(added[ref] || []).filter(email => !emails.some(other => other.id === email.id)), ...emails];
      notSaved('Demonstração: as propostas entram na fila, mas a ronda não fica gravada na agenda.');
      return {created: emails.length, state: view(), settings: snap('api/settings')};
    },

    'POST api/agenda/sync': async () => {
      await wait(1500);
      const refs = view().properties.map(queue => queue.property_ref);
      return {properties: refs.map(ref => ({property_ref: ref, confirmed: 0, moved: 0, accepted: 0, offered: 0})),
              settings: snap('api/settings'), state: view()};
    },
    'POST api/visits/check': body => {
      notSaved();
      return {property_ref: body.property_ref, at: body.at, settings: snap('api/settings'),
              check: {attended: body.attended, private: body.private_note || '', public: body.public_note || ''}};
    },
    'POST api/digest/save': () => { notSaved(); return snap('api/digest'); },
    'POST api/digest/refresh': () => snap('api/digest'),
    'POST api/digest/send': async () => { await wait(800); notSaved('Demonstração: nada foi enviado.'); return {status: 'sent'}; },
    'POST api/digest/send-all': async () => { await wait(800); notSaved('Demonstração: nada foi enviado.'); return {status: 'sent'}; },
    'POST api/ai/model': body => { notSaved(); return {...(snap('api/settings').ai || {}), model: body.model}; },
    'POST api/property/panel': body => {
      notSaved();
      return {panel: {reply_hours_max: Number(body.reply_hours_max) || 24, distance_km: Number(body.distance_km) || 0,
                      l_per_100km: Number(body.l_per_100km) || 0}};
    },
    'POST api/property/active': () => { notSaved(); return {settings: snap('api/settings'), state: view()}; },
    'POST api/knowledge/save': body => {
      notSaved();
      return {file: body.file, scope: body.scope, knowledge: snap('api/knowledge', {property_ref: body.property_ref ?? null}), state: view()};
    }
  };
  for (const path of ['api/voice', 'api/property/prompts', 'api/property/photo']) {
    handlers['POST ' + path] = () => { notSaved(); return snap('api/settings'); };
  }
  for (const path of ['api/contacts/save', 'api/contacts/delete', 'api/selection/set', 'api/selection/doc',
                      'api/selection/request', 'api/contacts/purge', 'api/fichas/fill', 'api/fichas/import']) {
    handlers['POST ' + path] = () => { notSaved(); return {...snap('api/contacts'), state: view()}; };
  }

  async function answer(method, path, body) {
    const handler = handlers[method + ' ' + path];
    if (handler) return handler(body || {});
    const recorded = snap(path, body);
    if (recorded !== undefined) { await wait(120); return recorded; }
    throw new Error(UNAVAILABLE);
  }

  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const address = typeof input === 'string' ? input : input.url;
    const path = new URL(address, location.href).pathname.replace(/^.*?\/(api\/.*)$/, '$1');
    if (!path.startsWith('api/')) return realFetch(input, init);
    const method = (init.method || 'GET').toUpperCase();
    const json = (data, status) => new Response(JSON.stringify(data), {status, headers: {'Content-Type': 'application/json'}});
    try {
      return json(await answer(method, path, init.body ? JSON.parse(init.body) : undefined), 200);
    } catch (error) {
      return json({error: error.message || 'Erro inesperado.'}, 400);
    }
  };

  // The ribbon that says what this is, with a way to start over.
  const ribbon = document.createElement('div');
  ribbon.className = 'demo-ribbon';
  ribbon.setAttribute('role', 'note');
  const label = document.createElement('span');
  label.textContent = 'Demonstração · dados fictícios · nada é enviado nem gravado';
  const restart = document.createElement('button');
  restart.type = 'button';
  restart.textContent = 'Recomeçar';
  restart.addEventListener('click', () => location.reload());
  ribbon.append(label, restart);
  const place = () => document.body.append(ribbon);
  if (document.body) place(); else document.addEventListener('DOMContentLoaded', place);
})();
