// The demo's steps, as the page calls them. Prints one JSON line: {failures, facts}.
var failures = [], facts = {};
function check(ok, message) { if (!ok) failures.push(message); }
async function api(path, body) {
  var response = await fetch(path, body === undefined ? {} : {method: 'POST', body: JSON.stringify(body)});
  return {status: response.status, data: await response.json()};
}
function count(state) { return state.properties.reduce(function (n, q) { return n + q.emails.length; }, 0); }
function queue(state, ref) { return state.properties.find(function (q) { return q.property_ref === ref; }); }
(async function () {
  try {
    var opening = (await api('api/state')).data;
    facts.opening = count(opening);
    for (var path of ['api/settings', 'api/digest', 'api/todo', 'api/contacts']) {
      check((await api(path)).status === 200, path + ' answers');
    }
    for (var days of [3, 7, 14, 30, 90]) check((await api('api/metrics', {days: days})).status === 200, 'metrics ' + days);
    check((await api('api/visits/candidates', {property_ref: 'DEMO_T1_PORTO'})).data.customers.length > 0, 'candidates');
    var read = (await api('api/read', {days: 7})).data;
    facts.added = read.added; facts.afterRead = count(read);
    check((await api('api/read', {days: 7})).data.added === 0, 'a second read brings nothing new');
    var lisboa = queue(read, 'DEMO_T2_LISBOA'), ids = lisboa.emails.map(function (e) { return e.id; });
    var generated = (await api('api/prompt/generate', {property_ref: 'DEMO_T2_LISBOA', ids: ids, extra: ''})).data;
    facts.saved = generated.saved; facts.prompts = generated.prompts.length;
    var drafted = queue(generated.state, 'DEMO_T2_LISBOA').emails;
    check(drafted.every(function (e) { return e.reply_status === 'draft' && e.reply_text.indexOf('🏠') > 0; }), 'every Lisbon draft is written');
    check(drafted.some(function (e) { return e.visit_slot; }), 'the booking carries its visit time');
    check(drafted.every(function (e) { return e.reply_text.indexOf('[[D:') < 0; }), 'no date marker is left');
    var edited = (await api('api/drafts', {property_ref: 'DEMO_T2_LISBOA', replies: [{id: ids[1], reply_text: 'Texto editado.'}]})).data;
    check(queue(edited, 'DEMO_T2_LISBOA').emails[1].reply_text === 'Texto editado.', 'a hand edit is kept');
    var preview = (await api('api/preview', {property_ref: 'DEMO_T2_LISBOA', ids: ids})).data;
    facts.preview = preview.replies.length;
    check(preview.replies[1].reply_text === 'Texto editado.', 'the preview shows the edited text');
    check(preview.replies.every(function (r) { return r.to.indexOf('@') > 0 && r.subject; }), 'recipient and subject in the preview');
    var sent = (await api('api/send', {property_ref: 'DEMO_T2_LISBOA', preview_token: preview.preview_token, confirmed: true})).data;
    facts.sent = sent.results.filter(function (r) { return r.status === 'sent'; }).length;
    check((await api('api/send', {property_ref: 'DEMO_T2_LISBOA', preview_token: preview.preview_token, confirmed: true})).status === 400,
      'a preview sends once');
    var after = (await api('api/state')).data;
    facts.lisboaLeft = queue(after, 'DEMO_T2_LISBOA').emails.length; facts.total = count(after);
    facts.active = queue(after, 'DEMO_T2_LISBOA').active.map(function (a) { return a.name; });
    var porto = queue(after, 'DEMO_T1_PORTO');
    check(!(await api('api/preview', {property_ref: 'DEMO_T1_PORTO', ids: [porto.emails[0].id]})).data.replies,
      'no preview without a draft');
    var proposed = (await api('api/visits/propose', {property_ref: 'DEMO_T3_CASCAIS', day: '2030-01-10', start: '10:00', end: '12:00',
                                                   emails: ['olivia.brown@example.com']})).data;
    var proposal = queue(proposed.state, 'DEMO_T3_CASCAIS').emails.find(function (e) { return e.kind === 'visit_proposal'; });
    check(proposal && proposal.visit_window.day === '2030-01-10', 'the round puts a proposal in the queue');
    var drafted2 = (await api('api/prompt/generate', {property_ref: 'DEMO_T3_CASCAIS', ids: [proposal.id]})).data;
    check(queue(drafted2.state, 'DEMO_T3_CASCAIS').emails.find(function (e) { return e.id === proposal.id; }).reply_text.indexOf('10:00') > 0,
      'a proposal made in the demo gets a draft');
    var active = queue(after, 'DEMO_T1_PORTO').active[0];
    if (active) check((await api('api/active/write', {property_ref: 'DEMO_T1_PORTO', email: active.email})).status === 200, 'Escrever mais');
    var refused = await api('api/consent/request', {property_ref: 'DEMO_T1_PORTO'});
    check(refused.status === 400 && /versão completa/.test(refused.data.error), 'an action the demo lacks says so');
    check((await api('api/voice', {})).status === 200 && toasts.length > 0, 'a settings save answers and warns');
    var settings = (await api('api/settings')).data;
    facts.slots = settings.properties.flatMap(function (p) { return p.visits.slots.map(function (s) { return s.at; }); });
    facts.lastRead = read.properties[0].last_read_at;
    var sound = await fetch('sounds/car-send.m4a');
    check((await sound.json()) === 'real:sounds/car-send.m4a', 'other files are fetched as they are');
    check(appended.length === 1, 'the ribbon is shown');
    var everything = JSON.stringify([opening, read, generated, after, settings, (await api('api/metrics', {days: 14})).data]);
    check(everything.indexOf('[[D:') < 0, 'no date marker anywhere');
  } catch (error) { failures.push('exception: ' + error + ' ' + error.stack); }
  print(JSON.stringify({failures: failures, facts: facts}));
})();
