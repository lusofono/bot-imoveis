// The page's logic. It only talks to the API (fetch); every rule is decided there.
// TOKEN is written into index.html by the server at each start and goes with every API call.
const STATUS ={pending: 'por responder', draft: 'rascunho', error: 'erro no envio', sending: 'a enviar', uncertain: 'envio incerto'};
const AUX_KINDS = ['reminder', 'consent_request', 'visits_closed', 'addition'];
// 06/10: every email the program prepares (backend PROGRAM_KINDS): ours to send, never a customer's message to answer
const OUR_KINDS = new Set([...AUX_KINDS, 'visit_thanks', 'visit_reminder', 'docs_request', 'visit_missed', 'visit_proposal']);
const FIELDS = ['reference', 'sender', 'deal', 'listing_id', 'listing_url', 'advertiser', 'advertised_rent_eur', 'description',
  'owner_email'];
const $ = id => document.getElementById(id);
let state = {properties: []}, settings = null, preview = null;

// Only the visual preference is stored locally; never account or email content.
// APalace is first, and the one a browser with no choice saved starts in (27/09).
// «Default» (id amber, once «Âmbar») first and the one to start with (27/09): the interface is being simplified in it,
// the others follow later.
const THEMES = ['amber', 'apalace', 'agentval', 'night', 'day', 'indigo', 'racing', 'boat', 'scooter', 'cabrio', 'kw'];
function applyTheme(theme) {
  const chosen = THEMES.includes(theme) ? theme : 'amber';
  document.documentElement.dataset.theme = chosen;
  $('theme-select').value = chosen;
}
try { applyTheme(localStorage.getItem('bot-mail-theme')); }
catch { applyTheme('amber'); }
// 04/10: 00's UK Cabrio's ambient light, day or night — kept in this browser like the theme; only that skin dresses it
function ambient() { return document.documentElement.dataset.ambient === 'night' ? 'night' : 'day'; }
function applyAmbient(value) {
  document.documentElement.dataset.ambient = value === 'night' ? 'night' : 'day';
  try { localStorage.setItem('bot-mail-ambient', document.documentElement.dataset.ambient); } catch { /* Storage may be unavailable. */ }
}
try { document.documentElement.dataset.ambient = localStorage.getItem('bot-mail-ambient') === 'night' ? 'night' : 'day'; }
catch { document.documentElement.dataset.ambient = 'day'; }
$('theme-select').addEventListener('change', event => {
  applyTheme(event.target.value);
  try { localStorage.setItem('bot-mail-theme', event.target.value); } catch { /* Storage may be unavailable. */ }
  applySkin();
  // A skin brings its own instruments: the property panel on screen is redrawn with them.
  if (settings && !$('tab-properties').hidden) renderPropertySlider();
});
let activeTab = 'dashboard', skinSelector = null;
// Voz e estilo first (27/09): the settings are «R», reverse, before the Painel's 1st gear, in every theme.
// 02/10: in the menu's order (the scooter's drum follows it): Voz e estilo, Painel, Comunicações, Contactos, Visitas,
// Imóveis, Proprietários
const TAB_NAMES = {voice: 'Voz e estilo', dashboard: 'Painel', replies: 'Emails', contacts: 'Clientes',  // 04/10: once «Centro de Comunicações», «Contactos»
 
  agenda: 'Visitas', properties: 'Imóveis', owners: 'Proprietários'};  // the tab is «Visitas» since 27/09 (id stays agenda)

// Skins: a rich theme goes beyond colours. It may bring the words on the page headings, the instruments on
// each property's panel (from the same signals: see panelSignals), a tab selector of its own and an analog
// clock; its stylesheet is in frontend/themes/. The plain themes use none of it. 80's RacingCar (id racing) is the first;
// 90's Boat (id boat) fills the same slots with its own words, instruments and selector (its clock is dressed in its
// stylesheet); a grand-luxury skin would do the same.
const SKINS = {
  // 30/09: AgentVal speaks with a warmer, more human voice; its colours and type are in themes/agentval.css
  agentval: {
    words: {
      'dashboard.eyebrow': 'O SEU DIA',
      'activity.eyebrow': 'PERCURSO', 'activity.title': 'Pedidos e respostas, lado a lado',
      'setup.eyebrow': 'PRÓXIMO PASSO', 'setup.title': 'Tudo pronto para acompanhar',
      'replies.eyebrow': 'CONVERSAS',
      'properties.eyebrow': 'SELEÇÃO',
      'contacts.eyebrow': 'PESSOAS',
      'agenda.eyebrow': 'VISITAS',
      'voice.eyebrow': 'A NOSSA VOZ', 'voice.title': 'As tuas palavras. O estilo da Agência.',
    },
  },
  racing: {
    words: {
      'dashboard.eyebrow': 'COCKPIT',
      'dashboard.step': 'Contactos, respostas e imóveis: todos os instrumentos à vista.',
      'activity.eyebrow': 'ROAD BOOK', 'activity.title': 'Pedidos e respostas, volta a volta',
      'setup.eyebrow': 'CHECK-LIST DE PARTIDA', 'setup.title': 'Pronto para arrancar',
      'replies.eyebrow': 'BOX',
      'properties.eyebrow': 'GARAGEM',
      'properties.step': 'Um quadro de instrumentos por imóvel: temperatura, rotação, velocidade e combustível.',
      'contacts.eyebrow': 'PADDOCK',
      'agenda.eyebrow': 'GRELHA DA SEMANA',
      'voice.eyebrow': 'AFINAÇÃO', 'voice.title': 'Afinação: as tuas palavras, o estilo da Agência.',
      'cluster.eyebrow': 'QUADRO DE INSTRUMENTOS', 'cluster.chart': 'TELEMETRIA DESTE IMÓVEL',
      'lamp.heat': 'Sobreaquecido', 'heat.limit': 'H =', 'trip.title': 'Computador de bordo',
    },
    instruments: carInstruments,
    selector: gearbox,
    sounds: {send: racingSend, read: racingStart, click: switchClack, shift: racingGear},
  },
  boat: {
    words: {
      'dashboard.eyebrow': 'PONTE DE COMANDO',
      'dashboard.step': 'Contactos, respostas e imóveis: todos os instrumentos de bordo à vista.',
      'activity.eyebrow': 'DIÁRIO DE BORDO', 'activity.title': 'Pedidos e respostas, milha a milha',
      'setup.eyebrow': 'ANTES DE LARGAR', 'setup.title': 'Pronto para largar amarras',
      'replies.eyebrow': 'RÁDIO DE BORDO',
      'properties.eyebrow': 'FROTA',
      'properties.step': 'Um posto de comando por imóvel: os instrumentos, o rumo e o combustível.',
      'contacts.eyebrow': 'LISTA DE PASSAGEIROS',
      'agenda.eyebrow': 'TÁBUA DE MARÉS',
      'voice.eyebrow': 'PAVILHÃO', 'voice.title': 'O teu pavilhão: as tuas palavras, o estilo da Agência.',
      'cluster.eyebrow': 'INSTRUMENTOS DE BORDO', 'cluster.chart': 'PLOTTER · O RITMO DESTE IMÓVEL',
      'lamp.heat': 'Tempestade', 'heat.limit': 'Tempestade às', 'trip.title': 'Computador de bordo',
    },
    instruments: boatInstruments,
    selector: helm,
    sounds: {send: boatHorn, read: boatBell, click: brassTick, shift: boatEngine},
  },
  scooter: {
    words: {
      'dashboard.eyebrow': 'GUIADOR',
      'dashboard.step': 'Contactos, respostas e imóveis: tudo à vista, entre os punhos.',
      'activity.eyebrow': 'ROAD BOOK', 'activity.title': 'Pedidos e respostas, curva a curva',
      'setup.eyebrow': 'ANTES DO ARRANQUE', 'setup.title': 'Pronto para dar ao pedal',
      'replies.eyebrow': 'CORREIO EXPRESSO',
      'properties.eyebrow': 'A FROTA',
      'properties.step': 'Um guiador por imóvel: velocímetro, conta-rotações, temperatura e depósito.',
      'contacts.eyebrow': 'A PIAZZA',
      'agenda.eyebrow': 'ROTEIRO',
      'voice.eyebrow': 'OFICINA', 'voice.title': 'Oficina: as tuas palavras, o estilo da Agência.',
      'cluster.eyebrow': 'GUIADOR · INSTRUMENTOS', 'cluster.chart': 'O PERCURSO DESTE IMÓVEL',
      'lamp.heat': 'Motor quente', 'heat.limit': 'Quente às', 'trip.title': 'Diário de viagem',
    },
    instruments: scooterInstruments,
    selector: twistGrip,
    sounds: {send: scooterRev, read: scooterStart, click: chromeTick, shift: scooterGear},
  },
  // 04/10: 00's UK Cabrio — a British convertible hatch of the 2000s, in racing green, tan leather and white stripes;
  // inspired by the cars of the time, with no brand, badge or name (as the other skins). Its look is in themes/cabrio.css.
  cabrio: {
    words: {
      'dashboard.eyebrow': 'TABLIER',
      'dashboard.step': 'Contactos, respostas e imóveis: tudo no velocímetro central.',
      'activity.eyebrow': 'ROAD TRIP', 'activity.title': 'Pedidos e respostas, milha a milha',
      'setup.eyebrow': 'ANTES DE ARRANCAR', 'setup.title': 'Capota aberta, pronto a sair',
      'replies.eyebrow': 'A CONSOLA',
      'properties.eyebrow': 'A GARAGEM',
      'properties.step': 'Um tablier por imóvel: o velocímetro central, o conta-rotações, a temperatura e o depósito.',
      'contacts.eyebrow': 'O CLUBE',
      'agenda.eyebrow': 'ROTEIRO',
      'voice.eyebrow': 'AFINAÇÃO', 'voice.title': 'Afinação: as tuas palavras, o estilo da Agência.',
      'cluster.eyebrow': 'TABLIER · INSTRUMENTOS', 'cluster.chart': 'O PERCURSO DESTE IMÓVEL',
      'lamp.heat': 'Motor quente', 'heat.limit': 'Quente às', 'trip.title': 'Computador de bordo',
    },
    instruments: cabrioInstruments,
    selector: cabrioConsole,
    // 06/10: a real engine (CC0, credits in frontend/sounds/CREDITS.md), the synthesised sounds as a fallback
    // 06/10: no click on the buttons (the owner's wish): only the engine, and the console's switch on the panel's levers
    sounds: {send: cabrioRev, read: cabrioIdle, toggle: cabrioToggle, shift: cabrioGear},
    // 06/10: in the garage — Settings, where the car is tuned (the owner's word) — the engine ticking over, in a loop
    ambient: {tab: 'workshop', clip: 'cabrio-loop', level: 0.22},  // the level the owner liked (in Imóveis, at first)
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
  renderSoundSwitch();
  updateAmbient();  // 06/10: another theme, another loop (or none)
}

// A skin's sounds, made on the spot with the Web Audio API: no files. 90's Boat: a ship's horn when emails go out,
// the ship's bell twice when new ones come in, a small brass tick on every button. 80's RacingCar: a V12 blip, the
// pit radio's two beeps, a toggle switch's clack. Off until the owner turns them on with the Sons switch, which only
// shows in a skin that has sounds; like the theme, the choice stays in this browser.
let audio = null;
function soundsOn() {
  try { return localStorage.getItem('bot-mail-sounds') === 'on'; } catch { return false; }
}
function playSound(name, ...details) {
  const sound = skin()?.sounds?.[name];
  if (!sound || !soundsOn()) return;
  try {
    audio ??= new AudioContext();
    if (audio.state === 'suspended') audio.resume();
    sound(audio, ...details);
  } catch { /* No audio in this browser: the page works the same without it. */ }
}
// 06/10: a skin's ambient sound, in a loop while one of its tabs is open (00's UK Cabrio: the engine ticking over in the
// garage, Settings); it fades out on leaving it, turning the sounds off or changing the theme.
let ambientLoop = null;
function updateAmbient() {
  const want = soundsOn() && skin()?.ambient?.tab === activeTab ? skin().ambient : null;
  if (ambientLoop && ambientLoop.clip !== want?.clip) {
    const {source, gain} = ambientLoop;
    if (source) { gain.gain.setTargetAtTime(0, audio.currentTime, 0.15); source.stop(audio.currentTime + 0.8); }
    ambientLoop = null;
  }
  if (!want || ambientLoop) return;
  try {
    audio ??= new AudioContext();
    if (audio.state === 'suspended') audio.resume();
    const entry = ambientLoop = {clip: want.clip};
    loadSample(audio, want.clip).then(buffer => {
      if (!buffer || ambientLoop !== entry) return;
      const source = audio.createBufferSource(), gain = audio.createGain();
      source.buffer = buffer; source.loop = true;
      gain.gain.setValueAtTime(0, audio.currentTime); gain.gain.linearRampToValueAtTime(want.level, audio.currentTime + 0.8);
      source.connect(gain).connect(audio.destination); source.start();
      Object.assign(entry, {source, gain});
    });
  } catch { /* No audio in this browser: the page works the same without it. */ }
}
function renderSoundSwitch() {
  const toggle = $('sound-toggle'), available = !!skin()?.sounds;
  toggle.hidden = !available;
  toggle.setAttribute('aria-pressed', String(available && soundsOn()));
}
// 06/10: after a reload the browser keeps the sound locked until the first gesture on the page, and only a button's
// click unlocked it: a lever, a switch, a list or a key left the garage's idle (started at load) silent. Any of them now.
['pointerdown', 'keydown'].forEach(type => document.addEventListener(type, () => {
  if (audio?.state === 'suspended' && soundsOn()) audio.resume().catch(() => {});
}, {capture: true}));
// 06/10: Safari can leave the page's audio «playing» to an output that is gone (headphones, a screen): the tab shows the
// speaker and nothing is heard until the browser closes. Turning «Sons» on, or the outputs changing, starts it anew.
function freshAudio() {
  try { audio?.close(); } catch { /* already closed */ }
  audio = null; ambientLoop = null;
  for (const cache of [SAMPLES, PLAYING]) for (const key of Object.keys(cache)) delete cache[key];
}
navigator.mediaDevices?.addEventListener?.('devicechange', () => { if (audio) { freshAudio(); updateAmbient(); } });
$('sound-toggle').addEventListener('click', () => {
  const on = !soundsOn();
  if (on) freshAudio();
  try { localStorage.setItem('bot-mail-sounds', on ? 'on' : 'off'); } catch { /* Storage may be unavailable. */ }
  renderSoundSwitch();
  if (on) playSound('read');  // this click unlocks the audio, and the bell (or the radio) says what turned on
  updateAmbient();  // 06/10: the garage's idle starts or stops with the switch
  // 06/10: the browser may still hold the sound (a muted tab, a policy): said, not silent
  if (on) setTimeout(() => {
    if (audio && audio.state !== 'running') soundTrouble(`O browser não deixou tocar som nesta página (estado: ${audio.state}). `
      + 'Vê se o separador não está em silêncio e carrega outra vez em «Sons».');
  }, 800);
});
// Every button clicks in a skin that has a click — before its own action runs (capture), so a button that
// disables itself while working still sounds. The Sons switch plays its own sound.
document.addEventListener('click', event => {
  const button = event.target.closest?.('button');
  // A tab is a gear change where the skin has one (showTab plays it): no switch click on top of it.
  const shifts = button?.classList.contains('tab') && skin()?.sounds?.shift;
  if (button && button.id !== 'sound-toggle' && !button.disabled && !shifts) playSound('click');
}, true);

// A short burst of noise, shaped: the body of the mechanical sounds below.
function noiseBurst(context, at, length, filterType, frequency, level) {
  const buffer = context.createBuffer(1, Math.ceil(context.sampleRate * length), context.sampleRate);
  const samples = buffer.getChannelData(0);
  for (let i = 0; i < samples.length; i++) samples[i] = (Math.random() * 2 - 1) * (1 - i / samples.length) ** 3;
  const source = context.createBufferSource(), filter = context.createBiquadFilter(), gain = context.createGain();
  source.buffer = buffer; filter.type = filterType; filter.frequency.value = frequency; gain.gain.value = level;
  source.connect(filter).connect(gain).connect(context.destination);
  source.start(at);
}
// 80's RacingCar, emails out: a V12 blip — three sawtooth voices rising and falling together, with some grit.
function engineBlip(context) {
  const t = context.currentTime, out = context.createGain(), filter = context.createBiquadFilter(), grit = context.createWaveShaper();
  const curve = new Float32Array(256);
  for (let i = 0; i < 256; i++) { const x = i / 128 - 1; curve[i] = Math.tanh(2.5 * x); }
  grit.curve = curve;
  filter.type = 'lowpass'; filter.frequency.setValueAtTime(900, t); filter.frequency.linearRampToValueAtTime(2200, t + 0.35);
  filter.frequency.linearRampToValueAtTime(700, t + 1.1);
  out.gain.setValueAtTime(0.0001, t);
  out.gain.exponentialRampToValueAtTime(0.16, t + 0.06);
  out.gain.setValueAtTime(0.16, t + 0.7);
  out.gain.exponentialRampToValueAtTime(0.0001, t + 1.25);
  grit.connect(filter).connect(out).connect(context.destination);
  for (const [ratio, detune] of [[1, 0], [1.5, 6], [2, -4]]) {
    const voice = context.createOscillator();
    voice.type = 'sawtooth'; voice.detune.value = detune;
    voice.frequency.setValueAtTime(62 * ratio, t);
    voice.frequency.exponentialRampToValueAtTime(215 * ratio, t + 0.35);
    voice.frequency.exponentialRampToValueAtTime(78 * ratio, t + 1.2);
    voice.connect(grit); voice.start(t); voice.stop(t + 1.3);
  }
}
// 80's RacingCar, new emails: the pit radio — a squelch, then two short beeps.
function pitRadio(context) {
  const t = context.currentTime;
  noiseBurst(context, t, 0.08, 'bandpass', 1800, 0.08);
  for (const at of [t + 0.1, t + 0.28]) {
    const beep = context.createOscillator(), gain = context.createGain();
    beep.type = 'square'; beep.frequency.value = 1320;
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.05, at + 0.01);
    gain.gain.setValueAtTime(0.05, at + 0.09);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.12);
    beep.connect(gain).connect(context.destination);
    beep.start(at); beep.stop(at + 0.13);
  }
}
// 80's RacingCar, a tab is a gear change: the lever through the gate, then the engine pulling in that gear. Each gear
// sits a step higher than the one below (1st a low growl, 6th the highest), like a car gathering speed; going up,
// the revs drop and pull again; going down, a throttle blip first (heel and toe), then it settles.
function gearShift(context, gear, from = 0) {
  const t = context.currentTime, pull = t + 0.06, down = from > 0 && gear < from;
  noiseBurst(context, t, 0.03, 'bandpass', 1400, 0.14);
  const base = 46 * 1.2 ** (Math.max(1, gear) - 1);
  const out = context.createGain(), filter = context.createBiquadFilter(), grit = context.createWaveShaper();
  const curve = new Float32Array(256);
  for (let i = 0; i < 256; i++) { const x = i / 128 - 1; curve[i] = Math.tanh(2.2 * x); }
  grit.curve = curve;
  filter.type = 'lowpass'; filter.frequency.setValueAtTime(900 + gear * 150, pull);
  filter.frequency.linearRampToValueAtTime(1600 + gear * 250, pull + 0.45);
  out.gain.setValueAtTime(0.0001, t);
  out.gain.exponentialRampToValueAtTime(0.12, pull + 0.05);
  out.gain.setValueAtTime(0.12, pull + 0.6);
  out.gain.exponentialRampToValueAtTime(0.0001, pull + 1);
  grit.connect(filter).connect(out).connect(context.destination);
  for (const [ratio, detune] of [[1, 0], [1.5, 5], [2, -5]]) {
    const voice = context.createOscillator();
    voice.type = 'sawtooth'; voice.detune.value = detune;
    voice.frequency.setValueAtTime(base * (down ? 1.9 : 0.8) * ratio, pull);
    if (down) voice.frequency.exponentialRampToValueAtTime(base * 1.2 * ratio, pull + 0.18);
    voice.frequency.exponentialRampToValueAtTime(base * 2.1 * ratio, pull + 0.55);
    voice.frequency.exponentialRampToValueAtTime(base * 1.4 * ratio, pull + 0.95);
    voice.connect(grit); voice.start(pull); voice.stop(pull + 1.05);
  }
}
// 80's RacingCar, every button: a dashboard toggle switch — a sharp click over a small low thump.
function switchClack(context) {
  const t = context.currentTime, thump = context.createOscillator(), gain = context.createGain();
  noiseBurst(context, t, 0.025, 'highpass', 2500, 0.18);
  thump.type = 'sine'; thump.frequency.setValueAtTime(140, t); thump.frequency.exponentialRampToValueAtTime(60, t + 0.05);
  gain.gain.setValueAtTime(0.12, t); gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.06);
  thump.connect(gain).connect(context.destination); thump.start(t); thump.stop(t + 0.07);
}
// 90's Boat, every button: a small brass tick, like a switch on the bridge console.
function brassTick(context) {
  const t = context.currentTime;
  for (const [frequency, level] of [[2350, 0.05], [3700, 0.025]]) {
    const partial = context.createOscillator(), gain = context.createGain();
    partial.type = 'sine'; partial.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(level, t + 0.002);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
    partial.connect(gain).connect(context.destination); partial.start(t); partial.stop(t + 0.1);
  }
}

// A ship's horn: two low sawtooth voices a fifth apart (one slightly detuned), softened by a low-pass filter.
function shipHorn(context) {
  const t = context.currentTime, out = context.createGain(), filter = context.createBiquadFilter();
  filter.type = 'lowpass'; filter.frequency.value = 700;
  out.gain.setValueAtTime(0.0001, t);
  out.gain.exponentialRampToValueAtTime(0.2, t + 0.08);
  out.gain.setValueAtTime(0.2, t + 1.2);
  out.gain.exponentialRampToValueAtTime(0.0001, t + 1.7);
  filter.connect(out).connect(context.destination);
  for (const frequency of [92, 92.8, 138]) {
    const voice = context.createOscillator();
    voice.type = 'sawtooth'; voice.frequency.value = frequency;
    voice.connect(filter); voice.start(t); voice.stop(t + 1.75);
  }
}
// The ship's bell, struck twice: a bell's inharmonic partials, each fading at its own pace.
function shipBell(context) {
  const strike = at => {
    for (const [ratio, level] of [[0.5, 0.25], [1, 0.5], [2.01, 0.22], [2.76, 0.12], [4.07, 0.06]]) {
      const partial = context.createOscillator(), gain = context.createGain();
      partial.type = 'sine'; partial.frequency.value = 660 * ratio;
      gain.gain.setValueAtTime(0.0001, at);
      gain.gain.exponentialRampToValueAtTime(level * 0.35, at + 0.005);
      gain.gain.exponentialRampToValueAtTime(0.0001, at + 2.2 / ratio ** 0.3);
      partial.connect(gain).connect(context.destination);
      partial.start(at); partial.stop(at + 2.4);
    }
  };
  strike(context.currentTime); strike(context.currentTime + 0.42);
}

// 70's Scooter's recorded engine (26/09): a real 200 cc two-stroke scooter, cut into three clips in frontend/sounds/
// (CC0, credits there). Each clip is fetched once, decoded, and played from memory; the synthesised sounds below stay
// as a fallback while a clip loads or if it cannot be played.
const SAMPLES = {}, PLAYING = {};
function loadSample(context, name) {
  return SAMPLES[name] ??= fetch(`sounds/${name}.m4a`).then(response => {
    if (!response.ok) throw new Error(`o servidor respondeu ${response.status}`);
    return response.arrayBuffer();
  }).then(bytes => context.decodeAudioData(bytes)).catch(error => {
    // 06/10: said once, not silent: a sound that never plays left no clue
    soundTrouble(`O browser não conseguiu abrir o som gravado «${name}» (${error?.message || error}): toca um som sintetizado.`);
    return null;
  });
}
let soundWarned = false;
function soundTrouble(text) {
  console.warn(text);
  if (!soundWarned) { soundWarned = true; toast(text, 'warn'); }
}
function playSample(context, name, fallback, rate = 1, level = 0.8) {
  loadSample(context, name).then(buffer => {
    if (!buffer) return fallback?.();
    // The clips are a few seconds long: a new one of the same kind fades the one still playing (tabs clicked in a row).
    const playing = PLAYING[name];
    if (playing) { playing.gain.gain.setTargetAtTime(0, context.currentTime, 0.05); playing.source.stop(context.currentTime + 0.3); }
    const source = context.createBufferSource(), gain = context.createGain();
    source.buffer = buffer; source.playbackRate.value = rate; gain.gain.value = level;
    source.connect(gain).connect(context.destination); source.start();
    PLAYING[name] = {source, gain};
    source.onended = () => { if (PLAYING[name]?.source === source) delete PLAYING[name]; };
  });
}
// Emails out: the throttle opened, the engine pulling up to its peak. New emails: the engine starting and ticking over.
function scooterRev(context) { playSample(context, 'scooter-rev', () => scooterHorn(context), 1, 0.85); }
function scooterStart(context) { playSample(context, 'scooter-start', () => kickStart(context), 1, 0.8); }
// A tab: a short burst of the engine, a little higher in each gear (the clip played faster).
function scooterGear(context, gear, from = 0) {
  playSample(context, 'scooter-gear', () => scooterShift(context, gear, from), 0.86 + Math.max(1, gear) * 0.07, 0.6);
}

// 80's RacingCar's and 90's Boat's recorded sounds (27/09, CC0, credits in frontend/sounds/CREDITS.md), each falling back
// on its synthesised sound. The car: a racing engine starting (new emails); an Italian GT pulling hard, closing with a
// turbo's blow-off (emails out); short revs, higher in each gear (tabs). The boat: the ship's bell struck twice (new
// emails); a boat's horn (emails out); a diesel engine running, a little higher at each tab (tabs).
function racingStart(context) { playSample(context, 'car-start', () => pitRadio(context), 1, 0.75); }
function racingSend(context) { playSample(context, 'car-send', () => engineBlip(context), 1, 0.85); }
// The Painel (1st) and Voz e estilo (R, reverse) keep the short rev; the tabs in between pull away harder, a clip of a
// racing engine winding right up, a little higher in each gear (27/09).
function racingGear(context, gear, from = 0) {
  if (gear <= 1) return playSample(context, 'car-gear', () => gearShift(context, 1, from), 0.93, 0.6);
  playSample(context, 'car-accel', () => gearShift(context, gear, from), 0.92 + (gear - 2) * 0.05, 0.6);
}
function boatBell(context) { playSample(context, 'boat-bell', () => shipBell(context), 1, 0.7); }
function boatHorn(context) { playSample(context, 'boat-horn', () => shipHorn(context), 1, 0.7); }
// 06/10: 00's UK Cabrio's recorded engine, a compact British car's (CC0): ticking over (new emails), revved twice
// (emails out), one short rev a little higher at each tab, after the switch's click (tabs); each falls back on its
// synthesised sound (the horn, the indicator, the flick)
function cabrioIdle(context) { playSample(context, 'cabrio-idle', () => cabrioIndicator(context), 1, 0.7); }
function cabrioRev(context) { playSample(context, 'cabrio-rev', () => cabrioHorn(context), 1, 0.8); }
function cabrioGear(context, gear, from = 0) {
  cabrioToggle(context);
  playSample(context, 'cabrio-gear', () => cabrioFlick(context, gear), 0.92 + Math.max(1, gear) * 0.04, 0.55);
}
function boatEngine(context, gear) { playSample(context, 'boat-engine', () => brassTick(context), 0.9 + Math.max(1, gear) * 0.04, 0.5); }

// 70's Scooter, emails out: the horn — two short, bright honks from a twin-tone buzzer.
function scooterHorn(context) {
  const t = context.currentTime, filter = context.createBiquadFilter(), out = context.createGain();
  filter.type = 'bandpass'; filter.frequency.value = 900; filter.Q.value = 0.8;
  out.gain.value = 0.9;
  filter.connect(out).connect(context.destination);
  for (const at of [t, t + 0.26]) {
    const gain = context.createGain();
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.09, at + 0.015);
    gain.gain.setValueAtTime(0.09, at + 0.15);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.2);
    gain.connect(filter);
    for (const frequency of [587, 740]) {  // a small scooter's horn: high and nasal
      const voice = context.createOscillator();
      voice.type = 'square'; voice.frequency.value = frequency;
      voice.connect(gain); voice.start(at); voice.stop(at + 0.21);
    }
  }
}
// A small two-stroke single (a 125): a buzzing sawtooth whose loudness pops at the firing rate (the LFO), the lows cut
// and the highs kept, so it rasps like a scooter's «ring-ding-ding» and not like a car's rumble.
function twoStroke(context, at, length, pitch, rate, level) {
  const engine = context.createOscillator(), pops = context.createOscillator(), depth = context.createGain();
  const gain = context.createGain(), filter = context.createBiquadFilter(), lows = context.createBiquadFilter();
  engine.type = 'sawtooth'; pops.type = 'square';
  engine.frequency.setValueAtTime(pitch[0], at); engine.frequency.exponentialRampToValueAtTime(pitch[1], at + length * 0.6);
  engine.frequency.exponentialRampToValueAtTime(pitch[2], at + length);
  pops.frequency.setValueAtTime(rate[0], at); pops.frequency.linearRampToValueAtTime(rate[1], at + length * 0.6);
  depth.gain.value = level / 2;
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.exponentialRampToValueAtTime(level / 2, at + 0.04);
  gain.gain.setValueAtTime(level / 2, at + length * 0.8);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
  filter.type = 'lowpass'; filter.frequency.value = 3600;
  lows.type = 'highpass'; lows.frequency.value = 220;
  pops.connect(depth).connect(gain.gain);
  engine.connect(gain).connect(lows).connect(filter).connect(context.destination);
  engine.start(at); pops.start(at); engine.stop(at + length + 0.02); pops.stop(at + length + 0.02);
}
// 70's Scooter, new emails: the kick-start — the pedal's clunk, then the engine catching, «ring-ding-ding».
function kickStart(context) {
  const t = context.currentTime;
  noiseBurst(context, t, 0.07, 'lowpass', 500, 0.3);
  twoStroke(context, t + 0.12, 1.1, [150, 330, 210], [24, 55], 0.12);
}
// 70's Scooter, a tab is a gear on the twist grip: the clunk of the shift, then the engine pulling in that gear, each
// a little higher than the one below; going down, a quick blip of throttle first.
function scooterShift(context, gear, from = 0) {
  const t = context.currentTime, g = Math.max(1, gear), down = from > 0 && gear < from, base = 170 * 1.13 ** (g - 1);
  noiseBurst(context, t, 0.04, 'bandpass', 900, 0.18);
  twoStroke(context, t + 0.05, 0.8, down ? [base * 1.7, base * 1.3, base * 1.1] : [base * 0.8, base * 1.6, base * 1.25],
    [30 + g * 4, 48 + g * 5], 0.1);
}
// 70's Scooter, every button: a small chrome switch on the handlebar — a bright tick.
function chromeTick(context) {
  const t = context.currentTime, partial = context.createOscillator(), gain = context.createGain();
  noiseBurst(context, t, 0.02, 'highpass', 3500, 0.12);
  partial.type = 'triangle'; partial.frequency.value = 2900;
  gain.gain.setValueAtTime(0.05, t); gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.07);
  partial.connect(gain).connect(context.destination); partial.start(t); partial.stop(t + 0.08);
}

// 00's UK Cabrio (04/10), made on the spot like the others' fallbacks. Emails out: the horn, «bip-bip» — two short
// twin-tone honks, fuller and lower than the scooter's.
function cabrioHorn(context) {
  const t = context.currentTime, filter = context.createBiquadFilter(), out = context.createGain();
  filter.type = 'bandpass'; filter.frequency.value = 650; filter.Q.value = 0.7;
  out.gain.value = 0.9;
  filter.connect(out).connect(context.destination);
  for (const at of [t, t + 0.22]) {
    const gain = context.createGain();
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.1, at + 0.012);
    gain.gain.setValueAtTime(0.1, at + 0.12);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.16);
    gain.connect(filter);
    for (const frequency of [415, 494]) {  // a small car's twin horn
      const voice = context.createOscillator();
      voice.type = 'square'; voice.frequency.value = frequency;
      voice.connect(gain); voice.start(at); voice.stop(at + 0.17);
    }
  }
}
// The indicator's relay: a click with a little body, high on the «tick», lower on the «tock».
function relayClick(context, at, frequency, level) {
  noiseBurst(context, at, 0.018, 'bandpass', frequency, level);
  const body = context.createOscillator(), gain = context.createGain();
  body.type = 'triangle'; body.frequency.value = frequency / 3;
  gain.gain.setValueAtTime(level * 0.5, at); gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.03);
  body.connect(gain).connect(context.destination); body.start(at); body.stop(at + 0.035);
}
// New emails: the indicator ticking, three times — tick-tock, tick-tock, tick-tock.
function cabrioIndicator(context) {
  const t = context.currentTime;
  for (let i = 0; i < 3; i++) {
    relayClick(context, t + i * 0.5, 2600, 0.09);
    relayClick(context, t + i * 0.5 + 0.25, 1700, 0.07);
  }
}
// The panel's levers: a toggle switch on the console — a firm metal click, a short spring ring and a small thump.
function cabrioToggle(context) {
  const t = context.currentTime;
  noiseBurst(context, t, 0.02, 'highpass', 3000, 0.16);
  const ring = context.createOscillator(), gain = context.createGain();
  ring.type = 'sine'; ring.frequency.value = 3400;
  gain.gain.setValueAtTime(0.025, t + 0.004); gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.12);
  ring.connect(gain).connect(context.destination); ring.start(t); ring.stop(t + 0.13);
  const thump = context.createOscillator(), low = context.createGain();
  thump.type = 'sine'; thump.frequency.setValueAtTime(180, t); thump.frequency.exponentialRampToValueAtTime(70, t + 0.05);
  low.gain.setValueAtTime(0.1, t); low.gain.exponentialRampToValueAtTime(0.0001, t + 0.06);
  thump.connect(low).connect(context.destination); thump.start(t); thump.stop(t + 0.07);
}
// A tab: its toggle flicked over, and the small four-cylinder answering, a touch higher in each gear.
function cabrioFlick(context, gear) {
  cabrioToggle(context);
  const t = context.currentTime + 0.05, g = Math.max(1, gear), base = 55 * 1.1 ** (g - 1);
  const out = context.createGain(), filter = context.createBiquadFilter();
  filter.type = 'lowpass'; filter.frequency.setValueAtTime(700, t); filter.frequency.linearRampToValueAtTime(1300 + g * 120, t + 0.25);
  out.gain.setValueAtTime(0.0001, t); out.gain.exponentialRampToValueAtTime(0.07, t + 0.05);
  out.gain.setValueAtTime(0.07, t + 0.3); out.gain.exponentialRampToValueAtTime(0.0001, t + 0.6);
  filter.connect(out).connect(context.destination);
  for (const [ratio, detune] of [[1, 0], [2, 4]]) {
    const voice = context.createOscillator();
    voice.type = 'sawtooth'; voice.detune.value = detune;
    voice.frequency.setValueAtTime(base * ratio, t);
    voice.frequency.exponentialRampToValueAtTime(base * 1.8 * ratio, t + 0.25);
    voice.frequency.exponentialRampToValueAtTime(base * 1.2 * ratio, t + 0.6);
    voice.connect(filter); voice.start(t); voice.stop(t + 0.62);
  }
}

// 70's Scooter's tab selector: the twist grip of a 70s Italian scooter, with its gear drum in a chrome housing. The
// tabs are gears: the drum slides until the open tab's number sits in the window, and ▲ and ▼ on the black grip move
// one gear up or down (02/10). Like the gearbox and the helm, it repeats the nav for the mouse only (aria-hidden).
function twistGrip(box) {
  const tabs = Object.keys(TAB_NAMES), pitch = 30, windowX = 62;
  const gradient = (id, attrs, colours) => svg(attrs.r ? 'radialGradient' : 'linearGradient', {id, ...attrs},
    colours.map(([offset, colour]) => svg('stop', {offset, 'stop-color': colour})));
  const drum = svg('g', {class: 'grip-drum'}, tabs.map((tab, i) =>
    svg('text', {x: windowX + i * pitch, y: 59, class: 'grip-number'}, tab === 'voice' ? 'R' : String(i))));
  // 02/10: the row of notches under the handlebar (R to 6) is gone, for room: ▲ and ▼ on the black grip move one gear
  // up or down, and the drum turns to the new number
  const shift = delta => {
    const next = Math.min(tabs.length - 1, Math.max(0, tabs.indexOf(activeTab) + delta));
    if (tabs[next] !== activeTab) showTab(tabs[next]);
  };
  const gripButton = (y, d, delta, label) => {
    const button = svg('g', {class: 'grip-button', transform: `translate(141 ${y})`},
      svg('rect', {x: -27, y: -7.5, width: 54, height: 15, class: 'grip-hit'}), svg('path', {d, class: 'grip-arrow'}),
      svg('title', {}, label));
    button.addEventListener('click', () => shift(delta));
    return button;
  };
  const grip = svg('g', {class: 'grip-rubber'},
    svg('rect', {x: 112, y: 38, width: 58, height: 30, rx: 11, fill: 'url(#grip-rubber)'}),
    [...Array(9)].map((_, i) => svg('path', {d: `M${119 + i * 5.6} 41v24`, stroke: '#000', 'stroke-opacity': 0.55, 'stroke-width': 1.6})));
  const buttons = [gripButton(45.5, 'M-5 2.2L0 -2.6L5 2.2', 1, 'Mudança acima'),
    gripButton(60.5, 'M-5 -2.2L0 2.6L5 -2.2', -1, 'Mudança abaixo')];
  box.append(svg('svg', {viewBox: '0 0 176 82', class: 'twist-grip'},
    svg('defs', {},
      gradient('grip-chrome', {x1: 0, y1: 0, x2: 0, y2: 1}, [[0, '#fff'], [0.3, '#d6dce0'], [0.52, '#8d969d'], [0.62, '#eef1f3'], [1, '#9aa3aa']]),
      gradient('grip-rubber', {x1: 0, y1: 0, x2: 0, y2: 1}, [[0, '#4a4644'], [0.4, '#1d1b1a'], [1, '#0b0a0a']]),
      gradient('grip-paint', {x1: 0, y1: 0, x2: 0, y2: 1}, [[0, '#c6ecdf'], [0.55, '#8fd5c3'], [1, '#5fb3a0']]),
      svg('clipPath', {id: 'grip-window'}, svg('rect', {x: 47, y: 42, width: 30, height: 24, rx: 5}))),
    svg('rect', {x: 2, y: 46, width: 116, height: 14, rx: 7, fill: 'url(#grip-chrome)', stroke: '#6d767d', 'stroke-width': 0.6}),
    grip,
    svg('rect', {x: 30, y: 30, width: 64, height: 46, rx: 12, fill: 'url(#grip-paint)', stroke: '#3f8f7d', 'stroke-width': 0.8}),
    svg('rect', {x: 33, y: 33, width: 58, height: 40, rx: 10, fill: 'none', stroke: 'url(#grip-chrome)', 'stroke-width': 2.4}),
    svg('rect', {x: 47, y: 42, width: 30, height: 24, rx: 5, class: 'grip-window'}),
    svg('g', {'clip-path': 'url(#grip-window)'}, drum),
    svg('path', {d: 'M62 38.5l-3.2-4h6.4Z', class: 'grip-pointer'}),
    buttons));
  telltales(box, 'scooter');
  // The drum moves in the SVG's own units (its transform attribute), tweened here: a CSS transform in px went by
  // screen pixels in Safari once the drawing was scaled, and stopped between two numbers (26/09).
  let current = null, drumX = 0, frame = null;
  const place = x => { drumX = x; drum.setAttribute('transform', `translate(${x.toFixed(2)} 0)`); };
  const slide = target => {
    cancelAnimationFrame(frame);
    const from = drumX, start = performance.now(), length = 520;
    const ease = t => 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2;  // eases out, with a small click past the notch
    const step = now => {
      const t = Math.min(1, (now - start) / length);
      place(from + (target - from) * ease(t));
      if (t < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
  };
  return {update(tab) {
    const index = tabs.indexOf(tab);
    if (index < 0) return;
    const target = -index * pitch;
    if (current === null || matchMedia('(prefers-reduced-motion: reduce)').matches) place(target);
    else if (current !== index) {
      slide(target);
      grip.classList.remove('twist'); grip.getBoundingClientRect(); grip.classList.add('twist');
    }
    current = index;
  }};
}

// 00's UK Cabrio's toggle bank (04/10): the chrome toggle switches on the centre console of a British hatch of the
// 2000s, under its chrome guard bar. The gears below are the tab selector; what these extra switches do is for later —
// for now R, 5 and 6 still open their tabs (Voz e estilo, Imóveis, Proprietários), and the last one, apart, switches the
// ambient light between day and night. It repeats the nav for the mouse only (aria-hidden).
function toggleBank(box) {
  // 04/10: only R, 5 and 6 (and the light) are left, wider and further apart, at the same height; drawn like the real
  // ones — a short chrome lever, tilted, in a dark socket with a chrome collar, between glossy black guard loops
  const tabs = ['voice', 'properties', 'owners'], places = [34, 78, 122], light_at = 168, loops = [12, 56, 100, 145, 186], y = 46;
  const gradient = (tag, id, attrs, colours) => svg(tag, {id, ...attrs},
    colours.map(([offset, colour]) => svg('stop', {offset, 'stop-color': colour})));
  // 06/10: seen from the front and upright, one lever that really moves: down (off) or up (on); on the way it shortens
  // (pointing at you, only its round end showing) and grows the other way, as a real toggle flipped — drawn per frame
  const LENGTH = 16;
  const lever = (x, label, extra = '') => {
    const arm = svg('g', {class: 'bank-arm'},
      svg('rect', {x: -3.2, y: 0, width: 6.4, height: LENGTH, rx: 3.2, class: 'bank-shaft'}),
      svg('path', {d: `M-1.1 2V${LENGTH - 2}`, class: 'bank-shine'}));
    const shadow = svg('ellipse', {rx: 4.8, ry: 2.2, class: 'bank-shadow'});
    const head = svg('g', {class: 'bank-head'},
      svg('ellipse', {rx: 4.9, ry: 4.9, class: 'bank-tip'}),
      svg('ellipse', {cx: -1.5, cy: -1.4, rx: 1.7, ry: 1.2, class: 'bank-tip-shine'}));
    const node = svg('g', {class: 'bank-toggle' + extra, transform: `translate(${x} ${y})`},
      svg('rect', {x: -18, y: -22, width: 36, height: 52, class: 'bank-hit'}),
      svg('circle', {r: 11.5, class: 'bank-socket'}),
      svg('circle', {r: 7.6, class: 'bank-ring'}),
      svg('circle', {r: 3.4, class: 'bank-hole'}),
      shadow, arm, head,
      svg('text', {y: 33, class: 'bank-label'}, label));
    // s: 1 down, -1 up; the round end squashed while the lever lies along the panel, round while it points at you
    const draw = s => {
      arm.setAttribute('transform', `scale(1 ${s})`);
      head.setAttribute('transform', `translate(0 ${LENGTH * s}) scale(1 ${0.62 + 0.38 * (1 - Math.abs(s))})`);
      shadow.setAttribute('transform', `translate(2.2 ${LENGTH * s + 3.2})`);
      shadow.setAttribute('opacity', String(0.18 + 0.2 * Math.abs(s)));
    };
    let current = 1, frame = 0;
    node.flip = on => {
      const target = on ? -1 : 1;
      if (target === current && !frame) return draw(current);
      cancelAnimationFrame(frame);
      const from = current, start = performance.now(), quick = matchMedia('(prefers-reduced-motion: reduce)').matches;
      const step = now => {
        const t = quick ? 1 : Math.min(1, (now - start) / 200), eased = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;
        current = from + (target - from) * eased; draw(current);
        frame = t < 1 ? requestAnimationFrame(step) : 0;
      };
      frame = requestAnimationFrame(step);
    };
    draw(current);
    return node;
  };
  const toggles = tabs.map((tab, i) => {
    const node = lever(places[i], tab === 'voice' ? 'R' : String(gearOf(tab)));
    node.append(svg('title', {}, TAB_NAMES[tab]));
    node.addEventListener('click', () => showTab(tab));
    return node;
  });
  const light = lever(light_at, 'LUZ', ' light');
  const title = svg('title', {});
  light.append(title);
  const paintLight = () => {
    light.classList.toggle('on', ambient() === 'night');
    light.flip(ambient() === 'night');
    title.textContent = ambient() === 'night' ? 'Luz ambiente: noite (clica para dia)' : 'Luz ambiente: dia (clica para noite)';
  };
  light.addEventListener('click', () => { applyAmbient(ambient() === 'night' ? 'day' : 'night'); playSound('toggle'); paintLight(); });
  const loop = x => [svg('path', {d: `M${x - 5} 76V32Q${x - 5} 21 ${x} 21Q${x + 5} 21 ${x + 5} 32V76`, class: 'bank-loop'}),
    svg('path', {d: `M${x - 3.3} 70V33Q${x - 3.3} 24.5 ${x} 24`, class: 'bank-loop-shine'})];
  box.append(svg('svg', {viewBox: '0 0 198 92', class: 'toggle-bank'},
    svg('defs', {},
      gradient('linearGradient', 'bank-panel', {x1: 0, y1: 0, x2: 0, y2: 1}, [[0, '#2a2f2c'], [0.5, '#121513'], [1, '#050605']]),
      gradient('linearGradient', 'bank-chrome', {x1: 0, y1: 0, x2: 0, y2: 1},
        [[0, '#fff'], [0.3, '#d6dce0'], [0.52, '#8d969d'], [0.62, '#eef1f3'], [1, '#9aa3aa']]),
      gradient('linearGradient', 'bank-barrel', {x1: 0, y1: 0, x2: 1, y2: 0},
        [[0, '#5f676d'], [0.28, '#eef1f3'], [0.45, '#ffffff'], [0.7, '#b9c1c6'], [1, '#4f565c']]),
      gradient('radialGradient', 'bank-socket', {cx: 0.5, cy: 0.45, r: 0.55}, [[0, '#000'], [0.75, '#0d0d0d'], [1, '#2e2e2e']]),
      // 06/10: the lever's round chrome end, lit from the top left
      gradient('radialGradient', 'bank-tip', {cx: 0.38, cy: 0.34, r: 0.7}, [[0, '#ffffff'], [0.45, '#d9dee2'], [0.8, '#8d969d'], [1, '#5f676d']])),
    svg('rect', {x: 2, y: 12, width: 194, height: 76, rx: 13, class: 'bank-panel'}),
    loops.map(loop),
    toggles, light));
  paintLight();
  return {update(tab) {
    tabs.forEach((name, i) => { toggles[i].classList.toggle('on', name === tab); toggles[i].flip(name === tab); });
  }};
}

// 00's UK Cabrio's gears (04/10): the gear stick of a British hatch of the 2000s, seen from above — a round base with a
// chrome ring and black leather in the middle, stitched round, the gear numbers in the leather where each gear is (an
// H, R and 1 to 6, one per tab, like the RacingCar's), and the knob — a dark ball in a chrome band, the engaged gear on
// its top — moving inside it with its leather boot. It goes through neutral like a real one; a click on a gear changes
// tab. Like the other selectors, it repeats the nav for the mouse only (aria-hidden).
const CABRIO_GEARS = {voice: [-36, -26], dashboard: [-12, -26], replies: [-12, 26], contacts: [12, -26], agenda: [12, 26],
  properties: [36, -26], owners: [36, 26]};
function cabrioGears(box) {
  const cx = 70, cy = 70, ring = 64, columns = [-36, -12, 12, 36], row = 26;
  const gradient = (tag, id, attrs, colours) => svg(tag, {id, ...attrs},
    colours.map(([offset, colour]) => svg('stop', {offset, 'stop-color': colour})));
  const tabs = Object.keys(CABRIO_GEARS);
  const number = tab => tab === 'voice' ? 'R' : String(gearOf(tab) || tabs.indexOf(tab));
  const spots = tabs.map(tab => svg('text', {x: cx + CABRIO_GEARS[tab][0], y: cy + CABRIO_GEARS[tab][1] + 4.5, class: 'mg-spot',
    'data-tab': tab}, number(tab)));
  const hits = tabs.map(tab => svg('circle', {cx: cx + CABRIO_GEARS[tab][0], cy: cy + CABRIO_GEARS[tab][1], r: 11, fill: 'transparent',
    class: 'mg-hit', 'data-tab': tab}, svg('title', {}, TAB_NAMES[tab])));
  for (const node of [...spots, ...hits]) node.addEventListener('click', () => showTab(node.dataset.tab));
  // the gate, as a faint stitched seam in the leather
  const seam = `M${cx + columns[0]} ${cy}H${cx + columns[3]}`
    + columns.map((x, i) => `M${cx + x} ${cy - row}V${cy + (i ? row : 0)}`).join('');
  const engaged = svg('text', {y: 5, class: 'mg-knob-number'}, '');
  const knob = svg('g', {class: 'mg-knob'}, svg('g', {transform: 'scale(1.2)'},  // 04/10: the ball 20 % bigger
    svg('circle', {r: 23, fill: 'url(#mg-boot)'}),
    [0, 72, 144, 216, 288].map(turn => svg('path', {d: 'M0 -22Q5 -12 0 -4', class: 'mg-fold', transform: `rotate(${turn})`})),
    svg('circle', {cx: 1, cy: 3.5, r: 15, fill: '#000', opacity: 0.45}),
    svg('circle', {r: 15, fill: 'url(#mg-chrome-ball)', stroke: '#4a5157', 'stroke-width': 0.6}),
    svg('circle', {r: 11, fill: 'url(#mg-top)'}),
    engaged,
    svg('ellipse', {cx: -4.5, cy: -7, rx: 6, ry: 2.6, fill: '#fff', opacity: 0.28})));
  box.append(svg('svg', {viewBox: '0 0 140 142', class: 'cabrio-gears'},
    svg('defs', {},
      gradient('linearGradient', 'mg-chrome', {x1: 0, y1: 0, x2: 0, y2: 1},
        [[0, '#fff'], [0.3, '#d6dce0'], [0.52, '#8d969d'], [0.62, '#eef1f3'], [1, '#9aa3aa']]),
      gradient('radialGradient', 'mg-leather', {cx: 0.5, cy: 0.45, r: 0.6}, [[0, '#2c2824'], [0.7, '#171513'], [1, '#0b0a09']]),
      gradient('radialGradient', 'mg-boot', {cx: 0.45, cy: 0.4, r: 0.6}, [[0, '#3c352e'], [0.75, '#1a1714'], [1, '#0b0a0900']]),
      gradient('radialGradient', 'mg-chrome-ball', {cx: 0.38, cy: 0.32, r: 0.8}, [[0, '#ffffff'], [0.45, '#c9d0d4'], [0.8, '#7c858c'], [1, '#4a5157']]),
      gradient('radialGradient', 'mg-top', {cx: 0.4, cy: 0.35, r: 0.8}, [[0, '#3a3a3a'], [1, '#0b0b0b']])),
    svg('circle', {cx, cy: cy + 3, r: ring + 4, fill: '#000', opacity: 0.3}),
    svg('circle', {cx, cy, r: ring, class: 'mg-ring'}),
    svg('circle', {cx, cy, r: ring - 6, class: 'mg-leather'}),
    svg('circle', {cx, cy, r: ring - 11, class: 'mg-stitch'}),
    svg('path', {d: seam, class: 'mg-seam'}),
    spots, hits, knob));
  // The knob moves in the drawing's own units (its transform attribute), tweened here, as the scooter's drum
  const spot = tab => [cx + CABRIO_GEARS[tab][0], cy + CABRIO_GEARS[tab][1]];
  let at = null, frame = null;
  const place = ([x, y]) => knob.setAttribute('transform', `translate(${x.toFixed(2)} ${y.toFixed(2)})`);
  const travel = points => {
    cancelAnimationFrame(frame);
    let from = at.slice(), index = 0, start = performance.now();
    const step = now => {
      const target = points[index], t = Math.min(1, (now - start) / 130);
      place([from[0] + (target[0] - from[0]) * t, from[1] + (target[1] - from[1]) * t]);
      if (t < 1) frame = requestAnimationFrame(step);
      else if (++index < points.length) { from = target; start = now; frame = requestAnimationFrame(step); }
    };
    frame = requestAnimationFrame(step);
  };
  return {update(tab) {
    if (!CABRIO_GEARS[tab]) return;
    const target = spot(tab);
    engaged.textContent = number(tab);
    for (const node of spots) node.classList.toggle('active', node.dataset.tab === tab);
    if (!at || matchMedia('(prefers-reduced-motion: reduce)').matches) { cancelAnimationFrame(frame); place(target); }
    else if (target[0] !== at[0] || target[1] !== at[1]) travel([[at[0], cy], [target[0], cy], target]);
    at = target;
  }};
}
// 00's UK Cabrio's console (04/10): on top, the gears choosing the tab; below them, one piano black panel, as on the
// car — the warning lights as a row of keys with a small LED on top, and under them the toggle bank between its half
// loops (what its extra switches do is for later).
function cabrioConsole(box) {
  const gears = cabrioGears(box), panel = el('div', {class: 'cabrio-panel'});
  box.append(panel);
  telltales(panel, 'cabrio');
  const bank = toggleBank(panel);
  return {update(tab) { bank.update(tab); gears.update(tab); }};
}

// 80's RacingCar's tab selector: the open gated gearbox of a GT of the time. Gears 1 to 6 are the six tabs (reverse is
// only there for the look); the lever goes through neutral like a real one, and a click on a gear changes
// tab. It repeats the nav for the mouse: the nav itself stays the accessible way (aria-hidden here).
// 02/10: in the menu's order — Painel, Comunicações, Contactos, Visitas, then Imóveis and Proprietários (the 6th)
const GEARS = {dashboard: [71, 29], replies: [71, 103], contacts: [106, 29], agenda: [106, 103], properties: [141, 29],
  owners: [141, 103], voice: [36, 29]};  // Voz e estilo is reverse (27/09)
function gearbox(box) {
  const neutral = 66, gate = 'M36 66H141M36 66V29M71 29V103M106 29V103M141 29V103';
  const gradient = (id, attrs, colours) => svg(attrs.r ? 'radialGradient' : 'linearGradient', {id, ...attrs},
    colours.map(([offset, colour]) => svg('stop', {offset, 'stop-color': colour})));
  const channel = (colour, width, extra = {}) => svg('path', {d: gate, fill: 'none', stroke: colour, 'stroke-width': width,
    'stroke-linecap': 'round', ...extra});
  const tabs = Object.keys(GEARS);
  const labels = [...tabs.map((tab, i) => svg('text', {x: GEARS[tab][0], y: GEARS[tab][1] < neutral ? 14 : 120, class: 'gate-label',
    'data-tab': tab}, tab === 'voice' ? 'R' : String(i + 1)))];
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
  telltales(box, 'car');
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

// 90's Boat's tab selector: the helm of a 90s motor yacht, a varnished wheel with six chrome spokes, one per tab.
// Each spoke points at its tab's signal flag (the same flags as the nav); the wheel turns the short way until the
// open tab's spoke is at the top, under the lubber mark, and the flags stay upright while it turns. A click on a
// flag changes tab. Like the gearbox, it repeats the nav for the mouse only (aria-hidden).
const HELM_FLAGS = {  // International Code of Signals, on a 30 × 20 cloth: V (the settings, first), P, R, I, C, A
  voice: [['rect', {width: 30, height: 20, fill: '#fff'}], ['path', {d: 'M0 0L30 20M30 0L0 20', stroke: '#c8102e', 'stroke-width': 4}]],
  dashboard: [['rect', {width: 30, height: 20, fill: '#1f4fa0'}], ['rect', {x: 10, y: 6.67, width: 10, height: 6.66, fill: '#fff'}]],
  replies: [['rect', {width: 30, height: 20, fill: '#c8102e'}], ['rect', {x: 12.5, width: 5, height: 20, fill: '#ffcc00'}],
    ['rect', {y: 7.5, width: 30, height: 5, fill: '#ffcc00'}]],
  contacts: [['rect', {width: 30, height: 20, fill: '#1f4fa0'}], ['rect', {y: 4, width: 30, height: 12, fill: '#fff'}],
    ['rect', {y: 8, width: 30, height: 4, fill: '#c8102e'}]],
  agenda: [['path', {d: 'M0 0H15V20H0Z', fill: '#fff'}], ['path', {d: 'M15 0H30L22 10L30 20H15Z', fill: '#1f4fa0'}]],
  properties: [['rect', {width: 30, height: 20, fill: '#ffcc00'}], ['circle', {cx: 15, cy: 10, r: 5, fill: '#121212'}]],
  // 02/10: Proprietários, O (Oscar): red over yellow, on the diagonal; the wheel gets a seventh spoke
  owners: [['path', {d: 'M0 0H30V20Z', fill: '#c8102e'}], ['path', {d: 'M0 0V20H30Z', fill: '#ffcc00'}]],
};
function helm(box) {
  const c = 90, rim = 50, tabs = Object.keys(HELM_FLAGS), step = 360 / tabs.length;
  const gradient = (id, attrs, colours) => svg(attrs.r ? 'radialGradient' : 'linearGradient', {id, ...attrs},
    colours.map(([offset, colour]) => svg('stop', {offset, 'stop-color': colour})));
  const at = (degrees, radius) => [c + radius * Math.sin(degrees * Math.PI / 180), c - radius * Math.cos(degrees * Math.PI / 180)];
  const flags = tabs.map((tab, i) => {
    const edge = tab === 'agenda' ? 'M.5 .5H29L21.4 10L29 19.5H.5Z' : 'M.5 .5H29.5V19.5H.5Z';
    const cloth = svg('g', {class: 'helm-flag', 'data-tab': tab},
      svg('circle', {r: 15, fill: 'transparent'}, svg('title', {}, TAB_NAMES[tab])),
      svg('g', {transform: 'translate(-12 -8) scale(.8)'}, HELM_FLAGS[tab].map(([tag, attrs]) => svg(tag, attrs)),
        svg('path', {d: edge, fill: 'none', class: 'helm-flag-edge'})));
    cloth.addEventListener('click', () => showTab(tab));
    const [x, y] = at(i * step, 73);
    return {tab, cloth, holder: svg('g', {transform: `translate(${x} ${y})`}, cloth)};
  });
  const wheel = svg('g', {class: 'helm-wheel'},
    tabs.map((_, i) => svg('rect', {x: c - 2.3, y: c - rim + 2, width: 4.6, height: rim - 16, rx: 2.3, fill: 'url(#helm-chrome)',
      transform: `rotate(${i * step} ${c} ${c})`})),
    svg('circle', {cx: c, cy: c, r: rim + 4.2, fill: 'none', stroke: '#2a0f04', 'stroke-opacity': 0.3, 'stroke-width': 1.6}),
    svg('circle', {cx: c, cy: c, r: rim, fill: 'none', stroke: 'url(#helm-wood)', 'stroke-width': 9}),
    svg('circle', {cx: c, cy: c, r: rim - 2.3, fill: 'none', stroke: '#fff', 'stroke-opacity': 0.4, 'stroke-width': 1.1}),
    svg('circle', {cx: c, cy: c, r: 15, fill: 'url(#helm-hub)', stroke: '#5f666e', 'stroke-width': 0.8}),
    svg('circle', {cx: c, cy: c, r: 8.5, fill: 'url(#helm-dome)'}),
    svg('ellipse', {cx: c - 4, cy: c - 5, rx: 5, ry: 2.6, fill: '#fff', opacity: 0.55}),
    flags.map(flag => flag.holder));
  box.append(svg('svg', {viewBox: '0 0 180 180', class: 'helm'},
    svg('defs', {},
      gradient('helm-wood', {x1: 0, y1: 0, x2: 1, y2: 1}, [[0, '#c9743a'], [0.3, '#8a3a13'], [0.55, '#b35d27'], [0.8, '#6a2a0c'], [1, '#a24f1f']]),
      gradient('helm-chrome', {x1: 0, y1: 0, x2: 1, y2: 0}, [[0, '#7d848c'], [0.35, '#fff'], [0.6, '#c3c9cf'], [1, '#6f767e']]),
      gradient('helm-hub', {cx: 0.35, cy: 0.3, r: 0.8}, [[0, '#fff'], [0.4, '#dfe3e7'], [0.8, '#8d949c'], [1, '#5f666e']]),
      gradient('helm-dome', {cx: 0.4, cy: 0.35, r: 0.7}, [[0, '#fff'], [0.5, '#c9ced4'], [1, '#7d848c']])),
    svg('path', {d: `M${c - 5} 0H${c + 5}L${c} 7Z`, class: 'helm-lubber'}),
    wheel));
  boatSensors(box);
  let angle = null;
  return {update(tab) {
    const index = tabs.indexOf(tab);
    if (index < 0) return;
    for (const flag of flags) flag.cloth.classList.toggle('active', flag.tab === tab);
    const first = angle === null, target = -index * step, turning = [wheel, ...flags.map(flag => flag.cloth)];
    angle = first ? target : angle + ((target - angle) % 360 + 540) % 360 - 180;
    if (first) turning.forEach(node => { node.style.transition = 'none'; });  // first draw: already on course
    wheel.style.transform = `rotate(${angle}deg)`;
    for (const flag of flags) flag.cloth.style.transform = `rotate(${-angle}deg)`;
    if (first) { wheel.getBoundingClientRect(); turning.forEach(node => { node.style.transition = ''; }); }
  }};
}

// 90's Boat, under the helm (27/09): «Sensores a bordo», a 40-foot 1980 motorsailer (ketch, pilothouse) at night, with a
// sensor on each part of the boat that reads a part of the app — a green, amber or red light that pulses; a click goes to
// the tab. Radio (masthead): the last Gmail read. Bilge (keel): emails waiting, the water in the bilge. Wheelhouse
// (windows): drafts ready to send. Engine (hull): the API tanks. Bow (anchor): today's visits. The drawing is fixed,
// trusted markup; nothing from an email ever goes into it.
const SAILER = '<defs> <radialGradient id="bs-night" cx="0.5" cy="0.2" r="0.9"><stop offset="0" stop-color="#1c3f6e"/><stop offset="1" stop-color="#0a1a33"/></radialGradient> <linearGradient id="bs-hull" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="0.7" stop-color="#dfe6ee"/><stop offset="1" stop-color="#b9c6d4"/></linearGradient> <linearGradient id="bs-sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a5a8f" stop-opacity="0.9"/><stop offset="1" stop-color="#0a1a33"/></linearGradient> </defs> <rect width="200" height="116" rx="10" fill="url(#bs-night)"/> <g stroke="#dfe6ee" stroke-width="0.5" fill="none" opacity="0.85"> <path d="M66 7 L16 66"/><path d="M66 7 L100 64"/><path d="M66 7 L148 26"/><path d="M148 26 L184 66"/><path d="M148 26 L136 64"/> </g> <path d="M66 7 V66" stroke="#eef2f6" stroke-width="1.6"/> <path d="M148 24 V66" stroke="#eef2f6" stroke-width="1.3"/> <path d="M66 58 H112" stroke="#c9d3de" stroke-width="1.2"/><rect x="67" y="54.5" width="44" height="4" rx="2" fill="#1f4f8a"/> <path d="M148 60 H176" stroke="#c9d3de" stroke-width="1"/><rect x="149" y="57" width="26" height="3.4" rx="1.7" fill="#1f4f8a"/> <path d="M10 64 L184 64 L190 68 C186 78 170 84 150 86 L60 87 C40 86 24 78 10 64 Z" fill="url(#bs-hull)"/> <path d="M22 74 C40 83 60 84.5 90 85 L150 84.5 C168 83 180 78 186 72" fill="none" stroke="#0e3a66" stroke-width="2"/> <path d="M26 77 C44 84.5 62 86 90 86.4 L150 86 C166 85 176 81 183 76" fill="none" stroke="#c8102e" stroke-width="1.1"/> <path d="M84 64 L88 50 L126 50 L132 58 L132 64 Z" fill="#f4f7fa" stroke="#b9c6d4" stroke-width="0.6"/> <path d="M90 52.5 L93.5 52.5 L92.5 58 L88.8 58 Z M96 52.5 L104 52.5 L104 58 L95 58 Z M106.5 52.5 L114.5 52.5 L114.5 58 L106.5 58 Z M117 52.5 L124.8 52.5 L128.5 57.2 L128.5 58 L117 58 Z" fill="#12375f"/> <g stroke="#dfe6ee" stroke-width="0.5"><path d="M14 60 H30 M14 60 V64 M22 60 V64 M30 60 V64"/><path d="M160 60 H186 M186 60 V66 M172 60 V64"/></g> <path d="M0 90 C20 86 40 94 60 90 S100 86 120 90 S160 94 200 89 V116 H0 Z" fill="url(#bs-sea)"/> <path d="M0 92 C24 89 44 96 70 92 S118 88 140 92 S178 95 200 91" fill="none" stroke="#7fb3e0" stroke-width="0.6" opacity="0.7"/>';
const BOAT_SENSORS = [
  {key: 'radio', label: 'Rádio', x: 66, y: 7, tab: 'replies'},
  {key: 'wheelhouse', label: 'Casa do leme', x: 108, y: 55, tab: 'replies'},
  {key: 'bilge', label: 'Porão', x: 88, y: 83, tab: 'replies'},
  {key: 'engine', label: 'Motor', x: 118, y: 76, tab: 'properties'},
  {key: 'bow', label: 'Proa', x: 20, y: 68, tab: 'agenda'},
];
function boatSensors(box) {
  const drawing = svg('svg', {viewBox: '0 0 200 116', class: 'boat-sensors-drawing', role: 'img', 'aria-label': 'Sensores a bordo'});
  drawing.innerHTML = SAILER;
  for (const sensor of BOAT_SENSORS) {
    // 02/10: no legend under the boat any more: hovering a circle shows what it read, in a tooltip over the panel
    const dot = svg('g', {class: 'boat-sensor off', 'data-sensor': sensor.key, transform: `translate(${sensor.x} ${sensor.y})`},
      svg('circle', {r: 9, class: 'boat-sensor-hit'}), svg('circle', {r: 7, class: 'boat-sensor-ring'}),
      svg('circle', {r: 3.2, class: 'boat-sensor-dot'}));
    dot.addEventListener('click', () => showTab(sensor.tab));
    dot.addEventListener('mouseenter', () => {
      tip.replaceChildren(el('strong', {}, sensor.label), el('span', {class: 'boat-sensor-now'}, dot.dataset.text || ''),
        el('span', {class: 'boat-sensor-go'}, `Clica para ir a ${TAB_NAMES[sensor.tab]}.`));
      tip.className = 'boat-sensor-tip ' + (dot.dataset.tone || 'off');
      tip.hidden = false;
    });
    dot.addEventListener('mouseleave', () => { tip.hidden = true; });
    drawing.append(dot);
  }
  const tip = el('div', {class: 'boat-sensor-tip', 'aria-hidden': 'true', hidden: true});
  box.append(el('div', {class: 'boat-sensors'}, el('p', {class: 'boat-sensors-title'}, 'SENSORES A BORDO'), drawing, tip));
  updateSkinPanels();
}
// What the skins' panels read (27/09): the boat's sensors, the car's warning lights, the scooter's jewels.
function appStatus() {
  const queues = state?.properties || [], emails = queues.flatMap(queue => queue.emails || []);
  const lastRead = queues.map(queue => queue.last_read_at).filter(Boolean).sort().pop();
  const tanks = (settings?.properties || []).map(property => property.api_fuel).filter(Boolean);
  const today = new Date().toLocaleDateString('sv-SE');  // AAAA-MM-DD, local day
  return {
    waiting: emails.filter(email => (email.reply_status ?? 'pending') === 'pending' && !email.blocked).length,
    drafts: emails.filter(email => email.reply_status === 'draft').length,
    blocked: emails.filter(email => email.blocked).length,
    uncertain: emails.filter(email => ['sending', 'uncertain'].includes(email.reply_status)).length,
    lastRead, hours: lastRead ? (Date.now() - new Date(lastRead).getTime()) / 3600000 : null,
    empty: tanks.some(tank => tank.empty), reserve: tanks.some(tank => tank.reserve && !tank.empty),
    visits: (settings?.properties || []).flatMap(property => property.visits?.slots || [])
      .filter(slot => String(slot.at).startsWith(today)).length,
    model: settings?.ai?.model || '',
  };
}
function updateSkinPanels() { updateBoatSensors(); updateTelltales(); }

// Warning lights (27/09). 80's RacingCar: ten telltales under the gearbox, dark until they have a reason, in their own
// colour (the turn signals blink). 70's Scooter: the headset's row of round jewels — green, oil, black, fuel. Each
// says on hover what it reads; a click goes to the tab.
const TELLTALE_ICONS = {
  turn: [['path', {d: 'M2 12l6-5.5v11z M22 12l-6-5.5v11z', class: 'fill'}]],
  low: [['path', {d: 'M11 5.5C7 5.5 4.5 8.4 4.5 12S7 18.5 11 18.5z', class: 'fill'}], ['path', {d: 'M14 8.5l7 2.2M14 12.5l7 2.2M14 16.5l7 2.2'}]],
  high: [['path', {d: 'M11 5.5C7 5.5 4.5 8.4 4.5 12S7 18.5 11 18.5z', class: 'fill'}], ['path', {d: 'M14 7.5h7M14 10.5h7M14 13.5h7M14 16.5h7'}]],
  eco: [['text', {x: 12, y: 15.5, class: 'fill telltale-text'}, 'ECO']],
  engine: [['path', {d: 'M3.5 10h3V8h6v2h3l2.2-2H20v8.5h-2.3l-2.2-2H14v3H8l-2-2H3.5z', class: 'fill'}]],
  oil: [['path', {d: 'M2.5 11h5.5l2.5-2h4.5l6.5-2.5-5.5 8H5z', class: 'fill'}], ['path', {d: 'M20.6 14.2c0 1.4-.8 2.3-1.4 2.3s-1.4-.9-1.4-2.3l1.4-2z', class: 'fill'}]],
  fuel: [['path', {d: 'M5 20V5a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v15M3.5 20h12M14 9h1.5l2.5 2.5V17a1.4 1.4 0 0 0 2.8 0V8.5L18 6'}], ['rect', {x: 7, y: 6.5, width: 5, height: 4, class: 'fill'}]],
  battery: [['path', {d: 'M3 8h18v11H3zM6.5 8V6h3v2M14.5 8V6h3v2M6.5 13.5h3M15 13.5h3M16.5 12v3'}]],
  belt: [['circle', {cx: 12, cy: 5, r: 2.2, class: 'fill'}], ['path', {d: 'M8 21v-7.5L12 9l4 4.5V21M7.5 10.5l9 8'}]],
  door: [['path', {d: 'M3.5 16.5v-4l2.5-4h11l2.5 4v4zM6.5 16.5v2M17.5 16.5v2M12 12.5l6.5-4.5'}]],
  headlamp: [['path', {d: 'M11 5.5C7 5.5 4.5 8.4 4.5 12S7 18.5 11 18.5z', class: 'fill'}], ['path', {d: 'M14 8.5l7 2.2M14 12.5l7 2.2M14 16.5l7 2.2'}]],
  neutral: [['text', {x: 12, y: 16, class: 'fill telltale-text'}, 'N']],
};
const TELLTALES = {
  car: [
    {key: 'turn', icon: 'turn', tone: 'green', blink: true, tab: 'replies', on: s => s.waiting > 0, text: s => `${s.waiting} por responder`},
    {key: 'low', icon: 'low', tone: 'green', tab: 'replies', on: s => s.hours != null && s.hours < 1, text: s => 'Gmail: ' + ago(s.lastRead)},
    {key: 'high', icon: 'high', tone: 'blue', tab: 'agenda', on: s => s.visits > 0, text: s => `${s.visits} visita(s) hoje`},
    {key: 'eco', icon: 'eco', tone: 'green', tab: 'voice', on: s => s.model === 'gpt-4o-mini', text: s => 'modelo ' + (s.model || '—')},
    {key: 'engine', icon: 'engine', tone: 'amber', tab: 'replies', on: s => s.blocked > 0, text: s => `${s.blocked} email(s) bloqueado(s)`},
    {key: 'oil', icon: 'oil', tone: 'red', tab: 'properties', on: s => s.empty, text: s => s.empty ? 'um depósito da API vazio' : 'depósitos com tokens'},
    {key: 'fuel', icon: 'fuel', tone: 'amber', tab: 'properties', on: s => s.reserve, text: s => s.reserve ? 'depósito da API na reserva' : 'depósitos sem reserva'},
    {key: 'battery', icon: 'battery', tone: 'red', tab: 'replies', on: s => s.hours == null || s.hours >= 24, text: s => 'Gmail: ' + ago(s.lastRead)},
    {key: 'belt', icon: 'belt', tone: 'red', tab: 'replies', on: s => s.drafts > 0, text: s => `${s.drafts} rascunho(s) por enviar`},
    {key: 'door', icon: 'door', tone: 'red', tab: 'replies', on: s => s.uncertain > 0, text: s => `${s.uncertain} envio(s) incerto(s)`},
  ],
  // 04/10: 00's UK Cabrio, the warning lights of the speedometer's rim
  cabrio: [
    {key: 'turn', icon: 'turn', tone: 'green', blink: true, tab: 'replies', on: s => s.waiting > 0, text: s => `${s.waiting} por responder`},
    {key: 'headlamp', icon: 'headlamp', tone: 'green', tab: 'replies', on: s => s.hours != null && s.hours < 24, text: s => 'Gmail: ' + ago(s.lastRead)},
    {key: 'high', icon: 'high', tone: 'blue', tab: 'agenda', on: s => s.visits > 0, text: s => `${s.visits} visita(s) hoje`},
    {key: 'engine', icon: 'engine', tone: 'amber', tab: 'replies', on: s => s.blocked > 0, text: s => `${s.blocked} email(s) bloqueado(s)`},
    {key: 'fuel', icon: 'fuel', tone: 'amber', tab: 'properties', on: s => s.empty || s.reserve,
      text: s => s.empty ? 'um depósito da API vazio' : s.reserve ? 'depósito da API na reserva' : 'depósitos com tokens'},
    {key: 'belt', icon: 'belt', tone: 'red', tab: 'replies', on: s => s.drafts > 0, text: s => `${s.drafts} rascunho(s) por enviar`},
  ],
  scooter: [
    {key: 'headlamp', icon: 'headlamp', tone: 'green', tab: 'replies', on: s => s.hours != null && s.hours < 24, text: s => 'Gmail: ' + ago(s.lastRead)},
    {key: 'oil', icon: 'oil', tone: 'red', tab: 'replies', on: s => s.waiting > 0, text: s => `${s.waiting} por responder`},
    {key: 'neutral', icon: 'neutral', tone: 'white', tab: 'replies', on: s => s.drafts > 0, text: s => `${s.drafts} rascunho(s) por enviar`},
    {key: 'fuel', icon: 'fuel', tone: 'yellow', tab: 'properties', on: s => s.empty || s.reserve,
      text: s => s.empty ? 'um depósito da API vazio' : s.reserve ? 'depósito da API na reserva' : 'depósitos com tokens'},
  ],
};
const TELLTALE_NAMES = {turn: 'Setas', low: 'Médios', high: 'Máximos', eco: 'ECO', engine: 'Motor', oil: 'Óleo', fuel: 'Gasolina',
  battery: 'Bateria', belt: 'Cinto', door: 'Porta', headlamp: 'Farol', neutral: 'Ponto morto'};
// 02/10: what each light means, for the hover (the browser's own title came late and only said the reading)
const TELLTALE_MEANS = {
  car: {turn: 'Pisca quando há emails de clientes por responder.',
    low: 'Acesa quando a última leitura do Gmail foi há menos de uma hora.',
    high: 'Acende quando há visitas marcadas para hoje.',
    eco: 'Acende quando a IA usa o modelo mais económico.',
    engine: 'Acende quando há emails bloqueados, que não se podem enviar: tratar à mão.',
    oil: 'Acende quando o depósito da API de um imóvel está vazio: a API parou nesse imóvel.',
    fuel: 'Acende quando o depósito da API de um imóvel está na reserva.',
    battery: 'Acende quando o Gmail não é lido há 24 horas ou mais.',
    belt: 'Acende quando há rascunhos por rever e enviar.',
    door: 'Acende quando há envios com resultado incerto: confirma no Gmail antes de repetir.'},
  cabrio: {turn: 'Pisca quando há emails de clientes por responder.',
    headlamp: 'Acesa quando o Gmail foi lido nas últimas 24 horas.',
    high: 'Acende quando há visitas marcadas para hoje.',
    engine: 'Acende quando há emails bloqueados, que não se podem enviar: tratar à mão.',
    fuel: 'Acende quando o depósito da API de um imóvel está na reserva ou vazio.',
    belt: 'Acende quando há rascunhos por rever e enviar.'},
  scooter: {headlamp: 'Acesa quando o Gmail foi lido nas últimas 24 horas.',
    oil: 'Acende quando há emails de clientes por responder.',
    neutral: 'Acende quando há rascunhos por rever e enviar.',
    fuel: 'Acende quando o depósito da API de um imóvel está na reserva ou vazio.'},
};
function telltales(box, kind) {
  const panel = el('div', {class: `telltales telltales-${kind}`, 'data-kind': kind});
  // 02/10: one explanation for the whole panel, over it (a bubble per light was cut by the sidebar's edge): the light's
  // name and whether it is on, what it means, what it reads now and where a click goes
  const tip = el('div', {class: 'telltale-tip', 'aria-hidden': 'true', hidden: true});
  const explain = button => {
    const lamp = TELLTALES[kind].find(item => item.key === button.dataset.lamp), lit = button.classList.contains('lit');
    tip.replaceChildren(el('strong', {}, `${TELLTALE_NAMES[lamp.key]} · ${lit ? 'acesa' : 'apagada'}`),
      el('span', {}, TELLTALE_MEANS[kind][lamp.key]), el('span', {class: 'telltale-now'}, 'Agora: ' + lamp.text(appStatus())),
      el('span', {class: 'telltale-go'}, `Clica para ir a ${TAB_NAMES[lamp.tab]}.`));
    tip.hidden = false;
  };
  for (const lamp of TELLTALES[kind]) {
    const icon = svg('svg', {viewBox: '0 0 24 24', class: 'telltale-icon', 'aria-hidden': 'true'},
      TELLTALE_ICONS[lamp.icon].map(([tag, attrs, text]) => svg(tag, attrs, text)));
    panel.append(el('button', {type: 'button', class: `telltale ${lamp.tone}`, 'data-lamp': lamp.key, onclick: () => showTab(lamp.tab),
      onmouseenter: event => explain(event.currentTarget), onfocus: event => explain(event.currentTarget),
      onblur: () => { tip.hidden = true; }}, icon));
  }
  panel.addEventListener('mouseleave', () => { tip.hidden = true; });
  panel.append(tip);
  box.append(panel);
  updateTelltales();
}
function updateTelltales() {
  const panels = document.querySelectorAll('.telltales');
  if (!panels.length) return;
  const status = appStatus();
  for (const panel of panels) {
    for (const button of panel.querySelectorAll('.telltale')) {
      const lamp = TELLTALES[panel.dataset.kind].find(item => item.key === button.dataset.lamp);
      const lit = !!lamp.on(status);
      button.classList.toggle('lit', lit);
      button.classList.toggle('blink', lit && !!lamp.blink);
      // 02/10: the explanation is the panel's own tooltip; no browser title on top of it
      button.setAttribute('aria-label', `${TELLTALE_NAMES[lamp.key]}: ${lamp.text(status)}` + (lit ? ' (aceso)' : ''));
    }
  }
}

function updateBoatSensors() {
  const panel = document.querySelector('.boat-sensors');
  if (!panel) return;
  const {waiting, drafts, lastRead, hours, empty, reserve, visits} = appStatus();
  const fuel = empty ? 'red' : reserve ? 'amber' : 'green';
  const reading = {
    radio: [hours == null ? 'red' : hours < 1 ? 'green' : hours < 24 ? 'amber' : 'red', 'Gmail: ' + ago(lastRead)],
    wheelhouse: [drafts ? 'amber' : 'green', drafts ? `${drafts} rascunho(s) por enviar` : 'nada por enviar'],
    bilge: [waiting === 0 ? 'green' : waiting <= 5 ? 'amber' : 'red', `${waiting} por responder`],
    engine: [fuel, fuel === 'red' ? 'um depósito da API vazio' : fuel === 'amber' ? 'depósito na reserva' : 'depósitos da API bem'],
    bow: [visits ? 'blue' : 'off', visits ? `${visits} visita(s) hoje` : 'sem visitas hoje']};
  for (const dot of panel.querySelectorAll('.boat-sensor')) {
    const [tone, text] = reading[dot.dataset.sensor];
    dot.setAttribute('class', 'boat-sensor ' + tone);
    dot.dataset.tone = tone; dot.dataset.text = text;  // 02/10: for the tooltip (the legend is gone)
  }
  const drawing = panel.querySelector('.boat-sensors-drawing');
  drawing.setAttribute('aria-label', 'Sensores a bordo: ' + BOAT_SENSORS.map(sensor => `${sensor.label}, ${reading[sensor.key][1]}`).join('; '));
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

// 02/10: a text the page made, saved by the browser as a file (nothing leaves the computer)
function downloadText(filename, text) {
  const link = el('a', {href: URL.createObjectURL(new Blob([text], {type: 'text/plain;charset=utf-8'})), download: filename});
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

// 29/09: while api/send runs (one email or a whole round), the sending banner stays up and leaving the page asks first
let sendingNow = 0;
function sendingBanner(delta) {
  sendingNow = Math.max(0, sendingNow + delta);
  $('sending-banner').hidden = !sendingNow;
}
window.addEventListener('beforeunload', event => { if (sendingNow) { event.preventDefault(); event.returnValue = ''; } });
// 02/10: the calls that may leave a message on the notice board (a send, a read, the API's tank): the board and the
// count on the Painel tab are fetched again after each one
const NOTICE_SOURCES = new Set(['api/send', 'api/read', 'api/prompt/generate', 'api/review', 'api/visits/round-generate',
  'api/visits/analyze', 'api/testlab/advance', 'api/testlab/clients', 'api/fichas/fill', 'api/property/extract']);
async function call(path, body) {
  if (path === 'api/send') sendingBanner(1);
  try { return await request(path, body); } finally {
    if (path === 'api/send') sendingBanner(-1);
    if (NOTICE_SOURCES.has(path)) refreshNotices();
  }
}
function refreshNotices() {
  request('api/notices').then(renderNotices).catch(() => { /* the board waits for the next call */ });
}
async function request(path, body) {
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
  // 27/09: the button's own nodes are put back, not only its text, so its number or icon comes back with it
  const original = button ? [...button.childNodes] : null;
  if (button) { button.disabled = true; button.textContent = 'A trabalhar…'; }
  try { await action(); }
  catch (error) { toast(error.message, 'bad'); }
  // data-hold: something else keeps it off (an empty API tank), data-lock: a step's 10 minutes (27/09): finishing a
  // click must not switch it back on.
  finally { if (button) { button.disabled = button.dataset.hold === '1' || button.dataset.lock === '1' || button.dataset.busy === '1';
    button.replaceChildren(...original); } }
}

async function copyText(text, done, fallbackBox) {
  try { await navigator.clipboard.writeText(text); toast(done); }
  catch { fallbackBox.open = true; toast('Não consegui copiar sozinho: seleciona o texto do prompt e copia-o.', 'warn'); }
}

// The gear of a tab (its place in the menu, 1 to 6): 80's RacingCar changes gear with the tabs, and sounds it.
function gearOf(tab) { return Number(document.querySelector(`nav [data-tab="${tab}"]`)?.dataset.gear) || 0; }

function showTab(name) {
  if (name !== activeTab) playSound('shift', gearOf(name), gearOf(activeTab));
  activeTab = name;
  skinSelector?.update(name);
  document.querySelectorAll('nav [data-tab]').forEach(button => {
    button.classList.toggle('active', button.dataset.tab === name);
    if (button.dataset.tab === name) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  $('page-label').textContent = TAB_NAMES[name];
  applySharedProperty(name);  // 05/10: the property chosen in any tab
  updateAmbient();  // 06/10: a skin's loop while its tab is open (the Cabrio's garage)
  for (const tab of Object.keys(TAB_NAMES)) $('tab-' + tab).hidden = tab !== name;
  $('tab-workshop').hidden = true; $('workshop-link').classList.remove('active');
  window.scrollTo({top: 0, behavior: 'instant'});
  if (name === 'dashboard') { run(loadMetrics); run(loadDigest); }
  if (name === 'voice') run(loadMetrics);  // «O teu espaço» (27/09) lives at the top of the settings now
  if (name === 'contacts') run(loadContacts);
  if (name === 'replies') maybeAutoRead();  // 06/10: reads by itself when the last read is old (Settings)
  if (name === 'owners') { renderOwners(); run(loadOwnersDigest); }
  if (name === 'agenda') renderAgenda();
  // Sends, refills and reads elsewhere change its numbers: the cluster is never shown out of date.
  if (name === 'properties' && settings) renderPropertySlider();
}

// 29/09: the Oficina, outside the tabs (the skins' gearboxes and helms know six of them): the AI engine, the token
// prices and the test platform. Its link shows only with "admin": true in config.json.
function showWorkshop() {
  activeTab = 'workshop';
  document.querySelectorAll('nav [data-tab]').forEach(button => { button.classList.remove('active'); button.removeAttribute('aria-current'); });
  for (const tab of Object.keys(TAB_NAMES)) $('tab-' + tab).hidden = true;
  $('tab-workshop').hidden = false; $('workshop-link').classList.add('active');
  $('page-label').textContent = 'Settings';  // 04/10: once «Oficina»
  updateAmbient();  // 06/10: the Cabrio's garage: the engine ticking over while Settings is open
  window.scrollTo({top: 0, behavior: 'instant'});
  renderWorkshop();
  run(async () => renderLab(await call('api/testlab/state', {})));
}

// 02/10: the portal — what is particular to it (Idealista today): who sends its notices, how its subject names the
// customer, its listing code and link, its call notices. Changed here if the portal changes its emails, or for another.
function portalCard(view) {
  const inputs = Object.fromEntries(Object.keys(view.labels).map(key => [key, el('input', {value: view.fields[key] || '',
    class: ['nome', 'remetente_pedidos', 'remetente_chamadas', 'link_anuncio_forma'].includes(key) ? '' : 'rule-input',
    'aria-label': view.labels[key], spellcheck: 'false'})]));
  const save = (reset, button) => run(async () => {
    const fields = Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, input.value]));
    portalCard(await call('api/portal/save', {fields, reset}));
    toast(reset ? 'O portal voltou ao de origem.' : 'Portal guardado: a próxima leitura já o usa.');
  }, button);
  $('workshop-portal').replaceChildren(
    el('p', {class: 'eyebrow'}, 'PORTAL · ' + (view.fields.nome || '').toUpperCase()), el('h2', {}, 'De onde vêm os pedidos'),
    el('p', {class: 'step'}, 'O que é próprio do portal: quem envia os avisos, como o assunto diz o nome do cliente, o código e o '
      + 'link do anúncio, e os avisos de chamadas. Se o portal mudar os emails, muda-se aqui; as regras são expressões '
      + 'regulares e são conferidas antes de guardar.'),
    el('div', {class: 'portal-fields'}, Object.entries(view.labels).map(([key, label]) => el('label', {class: 'field'},
      label + (view.changed.includes(key) ? ' · alterado' : ''), inputs[key]))),
    el('div', {class: 'actions'},
      el('button', {class: 'primary', onclick: event => save(false, event.currentTarget)}, 'Guardar'),
      view.changed.length ? el('button', {class: 'link', onclick: event => {
        if (confirm('Repor o portal de origem? As alterações feitas aqui perdem-se.')) save(true, event.currentTarget);
      }}, 'Repor os de origem') : null));
}

// 02/10: the backups — the data folder zipped once a day, at the first read, into a folder chosen here (one Google Drive
// syncs, say); never the keys. «Fazer cópia agora» for one more.
function backupCard(info) {
  const folder = el('input', {value: info.folder || '', placeholder: '/Users/…/Google Drive/ARIA-copias', 'aria-label': 'Pasta das cópias'});
  const size = bytes => bytes < 1048576 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1048576).toFixed(1).replace('.', ',')} MB`;
  const choose = (path, create, button) => run(async () => {
    backupCard(await call('api/backup/folder', {folder: path, create}));
    toast(path ? 'Pasta das cópias guardada.' : 'Sem cópias de segurança.');
  }, button);
  // 02/10: Google Drive for desktop, found on this Mac: one click to use (and make) its ARIA-copias folder
  const drives = (info.drives || []).filter(drive => drive.path !== info.folder);
  $('workshop-backup').replaceChildren(
    el('p', {class: 'eyebrow'}, 'CÓPIAS DE SEGURANÇA'), el('h2', {}, 'Cópia diária dos dados'),
    el('p', {class: 'step'}, 'Uma cópia por dia da pasta de dados (imóveis, conversas, agenda, contactos, conhecimento, voz, '
      + 'proprietários), na primeira leitura do dia. Nada se apaga: as cópias só se acrescentam (cada uma tem menos de 1 MB). '
      + 'As chaves do Gmail e da OpenAI não vão. Tem os dados dos clientes: usa uma pasta só tua. Para repor, fecha a ARIA e '
      + 'descomprime a cópia para a pasta da ARIA.'),
    drives.length ? el('div', {class: 'actions'}, drives.map(drive => el('button', {class: 'primary',
      onclick: event => choose(drive.path, true, event.currentTarget)}, `Usar o Google Drive (${drive.account})`)))
      : !info.folder && el('p', {class: 'muted small'}, 'Para as cópias irem para o Google Drive, instala o «Google Drive para '
        + 'computador» neste Mac: aparece aqui um botão para o usar. (A palavra-passe do Gmail não dá acesso ao Drive.)'),
    el('div', {class: 'row'}, folder,
      // 02/10: the Mac's own folder chooser (opened by the ARIA on this Mac)
      el('button', {onclick: event => run(async () => {
        const result = await call('api/backup/choose', {});
        backupCard(result); toast('Pasta das cópias guardada.');
      }, event.currentTarget)}, 'Escolher pasta…'),
      el('button', {onclick: event => choose(folder.value.trim(), false, event.currentTarget)}, 'Guardar'),
      el('button', {class: info.folder ? 'primary' : '', disabled: !info.folder, onclick: event => run(async () => {
        const result = await call('api/backup/now', {});
        backupCard(result); toast(`Cópia feita: ${result.last.file}.`);
      }, event.currentTarget)}, 'Fazer cópia agora')),
    el('p', {class: 'muted small'}, info.last
      ? `Última cópia: ${when(info.last.at)} · ${info.last.file} · ${size(info.last.bytes)} · ${info.count} na pasta.`
      : info.folder ? 'Ainda sem cópias nesta pasta: a primeira faz-se na próxima leitura, ou agora.' : 'Sem pasta escolhida: não há cópias.'));
}

// 06/10, Settings: Emails reads the mailbox by itself when it is opened and there was no read yet, or the last one is
// older than the minutes chosen here (10 by default); on or off.
function autoReadCard() {
  const auto = settings?.auto_read || {on: true, minutes: 10};
  const on = el('input', {type: 'checkbox', checked: auto.on});
  const minutes = el('input', {type: 'number', min: 1, max: 720, step: 1, value: auto.minutes, class: 'price-input',
    'aria-label': 'Minutos desde a última leitura'});
  return [el('p', {class: 'eyebrow'}, 'LEITURA AUTOMÁTICA'),
    el('p', {class: 'step'}, 'Ao abrir Emails, lê o Gmail sozinha se ainda não houver leitura ou se a última tiver sido há '
      + 'mais do que estes minutos. Nada é enviado: só lê.'),
    el('div', {class: 'row'}, el('label', {class: 'check'}, on, ' Ligada'),
      el('label', {}, 'Ler de novo passados ', minutes, ' minutos'),
      el('button', {type: 'button', onclick: event => run(async () => {
        settings.auto_read = await call('api/auto-read', {on: on.checked, minutes: minutes.value});
        toast(settings.auto_read.on ? `Leitura automática ligada: ao abrir Emails, se a última leitura tiver mais de `
          + `${settings.auto_read.minutes} minutos.` : 'Leitura automática desligada.');
      }, event.currentTarget)}, 'Guardar'))];
}
// 06/10: opening Emails reads by itself, when that is on (Settings) and the last read is missing or old enough — as a
// click on «Ler emails do Gmail» (its progress, its rest), never while it rests, is held or is busy
function maybeAutoRead() {
  const auto = settings?.auto_read;
  if (!auto?.on || !state?.properties || state.error) return;
  const last = Math.max(0, ...state.properties.map(queue => Date.parse(queue.last_read_at || '') || 0));
  if (last && Date.now() - last < auto.minutes * 60000) return;
  const button = $('read');
  if (button.disabled || button.dataset.busy === '1' || button.dataset.lock === '1') return;
  button.click();
}
function renderWorkshop() {
  $('workshop-link').hidden = !settings?.admin;
  // 30/09: without "admin", the prompts are never shown (with the customers' data in them): only «Copiar»
  document.body.classList.toggle('admin', !!settings?.admin);
  if (!settings?.admin) return;
  $('workshop-prompts').replaceChildren(...promptsCard());
  $('workshop-engine').replaceChildren(el('p', {class: 'eyebrow'}, 'MOTOR DE IA · API OPENAI'), engineConsole(), effortRow());
  $('workshop-auto-read').replaceChildren(...autoReadCard());
  run(async () => backupCard(await call('api/backup', {})));
  run(async () => portalCard(await call('api/portal', {})));
  // Token prices, US$ per 1M tokens as OpenAI writes them: change one, add a model, or put the table's own back
  const models = (settings.ai?.models || []).slice().sort((a, b) => a.id.localeCompare(b.id));
  const price = value => el('input', {type: 'number', min: 0, step: 'any', value: value ?? '', class: 'price-input'});
  const apply = next => { settings.ai = next; renderWorkshop(); applyAiMode(); };
  const row = model => {
    const input = price(model.input_usd_per_1m), output = price(model.output_usd_per_1m);
    // 29/09: the model's context window, in tokens; «por confirmar» while it is only the default
    const context = el('input', {type: 'number', min: 4000, step: 1000, value: model.context_tokens, class: 'price-input',
      title: model.context_known ? '' : 'Por confirmar: vale 128.000 até indicares o que a OpenAI anuncia para este modelo.'});
    return el('tr', {},
      el('td', {}, model.id, model.builtin ? '' : el('span', {class: 'tag'}, 'de Settings'),
        model.edited && model.builtin ? el('span', {class: 'tag draft'}, 'alterado') : '',
        model.hidden ? el('span', {class: 'tag warn'}, 'fora da escolha') : ''),
      el('td', {}, input), el('td', {}, output),
      el('td', {}, context, model.context_known ? '' : el('span', {class: 'tag warn'}, 'por confirmar')),
      el('td', {}, el('button', {type: 'button', onclick: event => run(async () => {
        if (Number(input.value) !== model.input_usd_per_1m || Number(output.value) !== model.output_usd_per_1m)
          apply(await call('api/ai/price', {model: model.id, input_usd_per_1m: input.value, output_usd_per_1m: output.value}));
        if (Number(context.value) !== model.context_tokens) apply(await call('api/ai/context', {model: model.id, tokens: context.value}));
        toast(`${model.id} guardado: vale para todas as estimativas e chamadas a partir de agora.`);
      }, event.currentTarget)}, 'Guardar'),
      // 02/10: off the list on offer (kept here, for the old costs) or back on it
      el('button', {type: 'button', class: 'link', onclick: event => run(async () => {
        apply(await call('api/ai/hidden', {model: model.id, hidden: !model.hidden}));
        toast(model.hidden ? `${model.id} volta a poder escolher-se no motor.` : `${model.id} saiu da escolha do motor.`);
      }, event.currentTarget)}, model.hidden ? 'Mostrar' : 'Esconder'),
      model.edited && el('button', {type: 'button', class: 'link', onclick: event => run(async () => {
        apply(await call('api/ai/price', {model: model.id, reset: true}));
        toast(model.builtin ? `${model.id}: de volta ao preço da tabela.` : `${model.id} saiu da lista.`);
      }, event.currentTarget)}, model.builtin ? 'Repor' : 'Tirar')));
  };
  const newModel = el('input', {type: 'text', placeholder: 'ex.: gpt-6-nova', 'aria-label': 'Nome do modelo novo'});
  const newIn = price(null), newOut = price(null);
  $('workshop-prices').replaceChildren(
    el('p', {class: 'eyebrow'}, 'PREÇOS DOS TOKENS'),
    el('p', {class: 'step'}, 'Em dólares por 1 milhão de tokens, como a OpenAI os publica. Valem para todos os imóveis: o custo de '
      + 'cada chamada, os depósitos e o «/ 100 interações». Um modelo novo passa a poder escolher-se no motor acima.'),
    el('div', {class: 'pipeline-scroll'}, el('table', {class: 'price-table'},
      el('thead', {}, el('tr', {}, ['Modelo', 'Input', 'Output', 'Contexto (tokens)', ''].map(label => el('th', {scope: 'col'}, label)))),
      el('tbody', {}, models.map(row),
        el('tr', {}, el('td', {}, newModel), el('td', {}, newIn), el('td', {}, newOut), el('td', {}),
          el('td', {}, el('button', {type: 'button', class: 'primary', onclick: event => run(async () => {
            apply(await call('api/ai/price', {model: newModel.value, input_usd_per_1m: newIn.value, output_usd_per_1m: newOut.value}));
            toast('Modelo acrescentado: já o podes escolher no motor.');
          }, event.currentTarget)}, 'Acrescentar')))))),
    limitsSection());
}

// 29/09: how big one call may be — so a batch never gets near the model's limit, where the answers get worse
function limitsSection() {
  const limits = settings.ai?.limits || {context_share: 50, batch_emails: 5};
  const share = el('input', {type: 'number', min: 10, max: 90, value: limits.context_share, class: 'price-input'});
  const batch = el('input', {type: 'number', min: 1, max: 10, value: limits.batch_emails, class: 'price-input'});
  return el('div', {class: 'limits-section'},
    el('p', {class: 'eyebrow'}, 'LIMITES DE CADA CHAMADA'),
    el('p', {class: 'step'}, '«Gerar respostas» junta emails na mesma chamada enquanto couberem nos dois limites; se não couberem, '
      + 'faz mais chamadas (custa o mesmo por token). Hoje, uma chamada de 5 emails anda pelos 15% do contexto de 128.000 tokens.'),
    el('div', {class: 'row'},
      el('label', {}, 'Não ultrapassar (% do contexto do modelo)', share),
      el('label', {}, 'Emails por chamada, no máximo', batch),
      el('button', {type: 'button', onclick: event => run(async () => {
        settings.ai = await call('api/ai/limits', {context_share: share.value, batch_emails: batch.value});
        renderWorkshop(); toast('Limites guardados: valem a partir do próximo «Gerar respostas».');
      }, event.currentTarget)}, 'Guardar')),
    reviewerSection());
}

// 02/10: how much the model reasons before writing — «nenhum» by default (short replies, every rule in the prompt):
// faster and cheaper. Only the models that take it (gpt-5.x, gpt-6) get it.
const EFFORT_LABELS = {none: 'Nenhum (o mais rápido)', minimal: 'Mínimo', low: 'Baixo (por defeito)', medium: 'Médio', high: 'Alto',
  '': 'O do modelo'};
function effortRow() {
  const effort = el('select', {'aria-label': 'Esforço de raciocínio'}, Object.entries(EFFORT_LABELS).map(([value, label]) =>
    el('option', {value}, label)));
  effort.value = settings.ai?.reasoning_effort ?? 'low';
  return el('div', {class: 'row effort-row'},
    el('label', {}, 'Esforço de raciocínio', effort),
    el('span', {class: 'muted small'}, 'Quanto o modelo pensa antes de escrever (só gpt-5.x e gpt-6; os outros não o têm). '
      + '«Baixo» chega para estas respostas; «Nenhum» é ainda mais rápido e barato, «Médio» e «Alto» só se for preciso. '
      + 'Vale para as respostas aos clientes (também no imóvel de teste), as rondas e o avaliador; os emails dos clientes '
      + 'de teste vão sempre com «Nenhum».'),
    el('button', {type: 'button', onclick: event => run(async () => {
      settings.ai = await call('api/ai/effort', {effort: effort.value});
      renderWorkshop(); toast(`Esforço de raciocínio: ${EFFORT_LABELS[effort.value]}.`);
    }, event.currentTarget)}, 'Guardar'));
}

// 30/09: the evaluator — its model (stronger than the one that writes) and whether it reviews the real drafts by itself
function reviewerSection() {
  const reviewer = settings.ai?.reviewer || {model: 'gpt-4o', auto: true};
  const model = el('select', {'aria-label': 'Modelo do avaliador'}, (settings.ai?.models || []).filter(item => !item.hidden).map(item =>
    el('option', {value: item.id}, item.id)));
  model.value = reviewer.model;
  const auto = el('input', {type: 'checkbox', checked: reviewer.auto});
  return el('div', {class: 'limits-section'},
    el('p', {class: 'eyebrow'}, 'AVALIADOR'),
    el('p', {class: 'step'}, 'Um segundo modelo, mais forte do que o que escreve, dá nota às respostas (factos, perguntas do cliente, '
      + 'qualificação, regras da agência, voz e avanço) e aponta os erros concretos. Revê os rascunhos reais e avalia as '
      + 'rondas da plataforma de testes (ARIA e consultor).'),
    el('div', {class: 'row'},
      el('label', {}, 'Modelo do avaliador', model),
      el('label', {class: 'check'}, auto, ' Rever os rascunhos logo depois de «Gerar respostas»'),
      el('button', {type: 'button', onclick: event => run(async () => {
        settings.ai = await call('api/ai/reviewer', {model: model.value, auto: auto.checked});
        renderWorkshop(); toast('Avaliador guardado.');
      }, event.currentTarget)}, 'Guardar')));
}

// 30/09: every prompt, to change when needed — those common to every property (voice.json) and each property's own
// (its profile.json). Only here: Voz e estilo and Imóveis no longer show them.
const COMMON_PROMPT_FIELDS = [
  ['application_instructions', 'Comportamento geral: como aplicar a voz em todas as respostas', 5],
  // 02/10: after the 4th interaction — the customer goes on writing with no visit booked — and then the closing
  ['later_reply', '5.ª a 7.ª interação: o cliente continua a escrever, sem visita marcada (responde e aguarda por ti)', 5],
  ['conclusive_reply', '8.ª interação: conclusiva (e um aviso para ti intervires)', 5],
  ['closing_reply', 'Fecho, da 9.ª interação em diante: agradece e despede-se até as condições mudarem', 5],
  ['owner_reply', 'Respostas ao proprietário (separador Proprietários)', 5],
  ['after_visit', 'Pós-visita: instruções do agradecimento', 5],
  ['after_visit_template', 'Pós-visita: conteúdo base (inquérito de 1 a 5 e ficha de visita; os <…> são preenchidos)', 12],
  ['survey_reply', 'Resposta ao inquérito pós-visita', 5],
  ['visit_reminder', 'Lembrete de visita (na véspera e no dia)', 5],
  ['booked_reply', 'Cliente com visita marcada', 5],
  ['visited_reply', 'Cliente que já visitou', 5],
  ['visit_missed', 'Visita que não aconteceu', 4],
  ['reminder_rule', 'Lembrete sem resposta (aos 2 e aos 4 dias, quando não há frase fixa)', 4],
  ['docs_request', 'Pedido de documentos (sem nunca dizer «short list»)', 5],
  // 03/10: a short-list customer's next reply asks for the documents; then each reply says what came and what is missing
  ['shortlist_request', 'Short list: a resposta seguinte pede os documentos', 5],
  ['shortlist_docs', 'Short list: o que chegou (pelo que disse e pelos nomes dos anexos) e o que falta', 5]];
const PROPERTY_PROMPT_FIELDS = [
  ['general', 'Prompt base: contexto do imóvel', 4], ['first', '1.ª interação: primeira resposta', 4],
  ['first_template', 'Texto base da 1.ª resposta (opcional)', 5], ['second', '2.ª interação: qualificação (pedir o que falta)', 5],
  ['third', '3.ª interação: proposta de visita', 4], ['fourth', '4.ª interação: marcar a visita', 6],
  ['knowledge', 'Como usar a base de conhecimento (RAG)', 3]];
let promptsProperty = null;
function promptsCard() {
  const boxes = Object.fromEntries(COMMON_PROMPT_FIELDS.map(([key, , rows]) =>
    [key, el('textarea', {rows}, settings.voice[key] || '')]));
  const properties = settings.properties || [];
  if (!properties.some(property => property.reference === promptsProperty)) promptsProperty = properties[0]?.reference || null;
  const property = properties.find(item => item.reference === promptsProperty);
  const select = el('select', {'aria-label': 'Imóvel'}, properties.map(item =>
    el('option', {value: item.reference}, item.reference + (item.test ? ' (teste)' : ''))));
  select.value = promptsProperty || '';
  select.addEventListener('change', () => { promptsProperty = select.value; renderWorkshop(); });
  const own = Object.fromEntries(PROPERTY_PROMPT_FIELDS.map(([key, , rows]) =>
    [key, el('textarea', {rows}, property?.prompts?.[key] || '')]));
  const field = (label, box) => el('label', {class: 'field'}, el('span', {}, label, kind('prompt')), box);
  return [
    el('p', {class: 'eyebrow'}, 'PROMPTS'),
    el('p', {class: 'step'}, 'Tudo o que a IA segue, para mudares quando precisares. Um texto apagado volta ao de partida. '
      + 'Quem usa a página não os vê nem os muda: só copia o prompt, sem o ver.'),
    el('details', {class: 'prompts-group'}, el('summary', {}, 'Comuns a todos os imóveis'),
      COMMON_PROMPT_FIELDS.map(([key, label]) => field(label, boxes[key])),
      el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
        settings = await call('api/prompts/common', {prompts: Object.fromEntries(Object.entries(boxes).map(([key, box]) => [key, box.value]))});
        renderSettings(); await refreshState(); toast('Prompts comuns guardados.');
      }, event.currentTarget)}, 'Guardar prompts comuns'))),
    property && el('details', {class: 'prompts-group'}, el('summary', {}, 'De cada imóvel'),
      el('div', {class: 'row'}, el('label', {}, 'Imóvel', select)),
      PROPERTY_PROMPT_FIELDS.map(([key, label]) => field(label, own[key])),
      el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
        settings = await call('api/property/prompts', {reference: property.reference,
          prompts: Object.fromEntries(Object.entries(own).map(([key, box]) => [key, box.value]))});
        renderSettings(); await refreshState(); toast(`Prompts de ${property.reference} guardados.`);
      }, event.currentTarget)}, `Guardar prompts de ${property.reference}`)))];
}

// 30/09: the evaluator's report in the lab — each side's average per criterion (ARIA and, with the Human contest, the
// consultant), the waiting time, and the last round's marks with the mistakes quoted
const CRITERIA_LABELS = {factos: 'Factos', perguntas: 'Perguntas do cliente', qualificacao: 'Qualificação',
  regras: 'Regras da agência', voz: 'Voz', avanco: 'Avanço'};
function labEvaluation(evaluation) {
  if (!evaluation?.aria && !evaluation?.consultant) return null;
  const cell = value => value == null ? '—' : decimal(value);
  const both = !!evaluation.consultant;
  return el('div', {class: 'lab-eval'},
    el('p', {class: 'lab-eval-title'}, 'AVALIAÇÃO'),
    el('table', {class: 'lab-eval-table'},
      el('thead', {}, el('tr', {}, el('th', {}, ''), el('th', {}, 'ARIA'), both && el('th', {}, 'Consultor'))),
      el('tbody', {},
        Object.entries(CRITERIA_LABELS).map(([key, label]) => el('tr', {}, el('td', {}, label),
          el('td', {}, cell(evaluation.aria?.criteria?.[key])), both && el('td', {}, cell(evaluation.consultant?.criteria?.[key])))),
        el('tr', {class: 'lab-eval-total'}, el('td', {}, 'Nota geral'), el('td', {}, cell(evaluation.aria?.score)),
          both && el('td', {}, cell(evaluation.consultant?.score))),
        el('tr', {}, el('td', {}, 'Tempo de resposta (h)'), el('td', {}, cell(evaluation.waited?.aria)),
          both && el('td', {}, cell(evaluation.waited?.consultant))),
        el('tr', {}, el('td', {}, 'Respostas avaliadas'), el('td', {}, evaluation.aria?.count ?? 0),
          both && el('td', {}, evaluation.consultant?.count ?? 0)))),
    // 02/10: the last round's marks and mistakes, closed to begin with (it is a lot)
    evaluation.last?.length ? el('details', {class: 'lab-eval-last'}, el('summary', {class: 'lab-eval-title'},
      `ÚLTIMA RONDA (${evaluation.last.length})`),
      evaluation.last.map(item => el('div', {class: 'lab-eval-item'},
        el('span', {}, `${shortName(item.name)} · ${item.side === 'aria' ? 'ARIA' : 'consultor'} · ${decimal(item.score)}/10`),
        item.errors?.length ? el('ul', {}, item.errors.map(error => el('li', {}, error)))
          : el('span', {class: 'muted small'}, ' sem erros')))) : null);
}

// The test platform: fictitious customers of the test property, whose emails go through Gmail for real
const labLog = [];  // what each «Avançar o teste» of this page view did, newest first
function renderLab(lab) {
  const count = el('input', {type: 'number', min: 1, max: 20, value: 3, 'aria-label': 'Quantos clientes'});
  const contestOn = el('input', {type: 'checkbox', checked: !!lab.contest?.on});
  const contestEmail = el('input', {type: 'email', value: lab.contest?.email || '', placeholder: 'email do consultor',
    'aria-label': 'Email do consultor'});
  const newPercent = el('input', {type: 'number', min: 0, max: 100, value: lab.new_percent ?? 10, 'aria-label': 'Clientes novos por ronda, em %'});
  const settingsNow = () => ({on: contestOn.checked, email: contestEmail.value, new_percent: newPercent.value});
  // el() leaves out null, false and 0 — replaceChildren would print them as text
  $('workshop-lab').replaceChildren(el('div', {class: 'lab-body'},
    el('p', {class: 'eyebrow', 'aria-label': 'Plataforma de testes'}),  // the console's own badge and cursor (CSS)
    el('p', {class: 'step'}, lab.property_ref
      ? `Imóvel de teste: ${lab.property_ref}. Cada cliente é inventado pela IA; o aviso dele sai mesmo pelo Gmail, desta conta `
        + 'para ela própria, com o cliente no Reply-To (um endereço +cdN desta conta). Depois, «Ler emails» em Emails traz-os.'
      : 'Ainda não há imóvel de teste (um profile.json com "test": true).'),
    // 02/10: in the order they are done — 1 the Human contest, 2 the customers, 3 a round —, each button numbered
    lab.property_ref && el('div', {class: 'row lab-row'},
      el('label', {class: 'check'}, contestOn, ' Human contest: cada aviso vai também, numa cópia à parte, para o consultor'),
      contestEmail,
      el('button', {type: 'button', onclick: event => run(async () => {
        renderLab(await call('api/testlab/contest', settingsNow()));
        toast('Guardado.' + (contestOn.checked ? ' Human contest ligado.' : ''));
      }, event.currentTarget)}, el('span', {class: 'step-num', 'aria-hidden': 'true'}, '1'), 'Guardar'),
      lab.contest?.on && lab.clients?.some(client => !client.consultant) && el('button', {type: 'button', onclick: event => run(async () => {
        const result = await call('api/testlab/consultant', {});
        renderLab(result); toast(`${result.sent} cópia(s) enviadas ao consultor.`);
      }, event.currentTarget)}, `Enviar ao consultor os que faltam (${lab.clients.filter(client => !client.consultant).length})`)),
    lab.property_ref && el('div', {class: 'row lab-row'},
      el('label', {}, 'Clientes novos', count),
      el('label', {}, 'Clientes novos por ronda (%)', newPercent),
      el('button', {type: 'button', class: 'primary needs-fuel', 'data-ref': lab.property_ref, onclick: event => run(async () => {
        const result = await call('api/testlab/clients', {count: Number(count.value),
          contest: settingsNow()});
        applyFuel(result.fuel, lab.property_ref); renderLab(result);
        toast(`${result.created.length} cliente(s) de teste enviados: ${result.created.join(', ')}. Lê os emails em Emails.`);
      }, event.currentTarget)}, el('span', {class: 'step-num', 'aria-hidden': 'true'}, '2'), 'Gerar clientes de teste')),
    lab.property_ref && el('div', {class: 'row lab-row lab-advance'},
      el('button', {type: 'button', class: 'primary needs-fuel', 'data-ref': lab.property_ref, onclick: event => run(async () => {
        const result = await call('api/testlab/advance', {});
        applyFuel(result.fuel, lab.property_ref); renderLab(result);
        const said = [result.aria.length && `${result.aria.length} responderam à ARIA`,
          result.consultant.length && `${result.consultant.length} ao consultor`,
          result.silent.length && `${result.silent.length} ficaram calados`,
          result.new.length && `${result.new.length} novos`, result.evaluated && `${result.evaluated} avaliada(s)`]
          .filter(Boolean).join(', ') || 'ninguém tinha email nosso por responder';
        labLog.unshift(`${new Date().toLocaleTimeString('pt-PT', {hour: '2-digit', minute: '2-digit'})} · ${said}`
          + (result.aria.length ? ` · ARIA: ${result.aria.join(', ')}` : '')
          + (result.consultant.length ? ` · consultor: ${result.consultant.join(', ')}` : '')
          + (result.new.length ? ` · novos: ${result.new.join(', ')}` : ''));
        renderLab(result);
        toast(`Ronda de teste: ${said}. Lê os emails em Emails.`);
      }, event.currentTarget)}, el('span', {class: 'step-num', 'aria-hidden': 'true'}, '3'), 'Avançar o teste'),
      el('span', {class: 'muted small'}, 'Os clientes com um email nosso por responder respondem (à ARIA e, com o Human contest, '
        + 'ao consultor) ou ficam calados; entram os clientes novos da percentagem do passo 2.')),
    labLog.length ? el('pre', {class: 'lab-log'}, labLog.slice(0, 12).join('\n')) : null,
    labEvaluation(lab.evaluation),
    lab.clients?.length ? el('div', {class: 'client-list'}, lab.clients.slice().reverse().map(client => el('div', {class: 'client-row'},
      el('span', {}, `${client.number}. ${shortName(client.name)}`), el('span', {class: 'tag'}, client.language || '?'),
      lab.contest?.on && el('span', {class: 'tag' + (client.consultant ? ' draft' : '')}, client.consultant ? 'consultor ✓' : 'sem cópia'),
      client.ended ? el('span', {class: 'tag'}, 'terminou') : client.rounds ? el('span', {class: 'tag draft'}, `${client.rounds} resp.`) : null,
      el('span', {class: 'muted small'}, client.address)))) : el('p', {class: 'muted small'}, 'Ainda sem clientes de teste.'),
    lab.property_ref && lab.clients?.length && el('div', {class: 'actions'},
      // 02/10: every test customer's whole story in one text file, to read at leisure (before a wipe, say)
      el('button', {type: 'button', onclick: event => run(async () => {
        const result = await call('api/testlab/transcript', {});
        downloadText(result.filename, result.text);
        toast(`Conversas de ${result.clients} clientes de teste descarregadas: ${result.filename}.`);
      }, event.currentTarget)}, 'Descarregar as conversas (.txt)'),
      el('button', {type: 'button', class: 'link danger',
      onclick: event => run(async () => {
        if (!confirm(`Apagar os ${lab.clients.length} clientes de teste e tudo do ${lab.property_ref} (fila, conversas, agenda e `
            + 'contactos), para começar de novo? Os emails ficam no Gmail, mas a página nunca mais os lê.')) return;
        const result = await call('api/testlab/wipe', {});
        state = await call('api/state'); renderState(); renderLab(result);
        toast(`${result.removed} clientes de teste apagados: o ${lab.property_ref} começa de novo.`);
      }, event.currentTarget)}, 'Apagar clientes de teste'))));
  holdFuelButtons();
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
// 29/09: the day, the hour and the minutes of a visit change with arrows, without typing (typing still works); the
// day always shows its weekday beside it.
function stepperArrow(label, title, action) {
  return el('button', {type: 'button', class: 'stepper-arrow', title, 'aria-label': title, onclick: action}, label);
}
function shiftTime(input, minutes) {
  const [hours, mins] = (input.value || '00:00').split(':').map(Number);
  const total = ((hours * 60 + mins + minutes) % 1440 + 1440) % 1440;
  input.value = `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
  input.dispatchEvent(new Event('change', {bubbles: true}));
}
function timeStepper(input, slot) {
  const pair = (unit, step, what) => el('div', {class: 'stepper-pair'},
    stepperArrow('▲', `Mais ${what}`, () => shiftTime(input, step)), el('span', {class: 'stepper-unit'}, unit),
    stepperArrow('▼', `Menos ${what}`, () => shiftTime(input, -step)));
  // 29/09: both pairs on the right of the field, hours then minutes, in the order they are read
  return el('div', {class: 'stepper stepper-time'}, input, pair('h', 60, 'uma hora'), pair('min', slot, `${slot} minutos`));
}
// The end moves with the start, keeping the interval chosen (also after the end itself was changed).
function linkTimes(start, end) {
  const minutes = value => { const [h, m] = (value || '00:00').split(':').map(Number); return h * 60 + m; };
  let last = start.value;
  start.addEventListener('change', () => {
    const delta = minutes(start.value) - minutes(last);
    last = start.value;
    if (delta && start.value) shiftTime(end, delta);
  });
}
function dateStepper(input) {
  const today = new Date().toLocaleDateString('sv-SE');
  input.min = today;
  const weekday = el('span', {class: 'stepper-weekday'});
  const show = () => {
    // 29/09: on the same line, in three letters (Ter)
    weekday.textContent = input.value ? ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'][new Date(input.value + 'T12:00:00').getDay()]
      : '';
  };
  const shift = days => {
    const base = new Date((input.value || today) + 'T12:00:00');
    if (input.value) base.setDate(base.getDate() + days);
    const next = base.toLocaleDateString('sv-SE');
    input.value = next < today ? today : next;
    input.dispatchEvent(new Event('change', {bubbles: true}));
  };
  if (!input.value) input.value = today;
  // the browser may put back a date typed before a reload without an event: shown again once it settled
  for (const type of ['input', 'change', 'focus', 'blur']) input.addEventListener(type, show);
  show(); setTimeout(show, 0); window.addEventListener('pageshow', show);
  return el('div', {class: 'stepper stepper-date'}, stepperArrow('◀', 'Dia anterior', () => shift(-1)),
    el('div', {class: 'stepper-field'}, input, weekday), stepperArrow('▶', 'Dia seguinte', () => shift(1)));
}
function slotLabel(value) { const [day, time] = String(value).split(' '); return `${dayLabel(day)}, ${time}`; }

function when(value) { return value ? new Date(value).toLocaleString('pt-PT', {dateStyle: 'short', timeStyle: 'short'}) : ''; }
function currentQueue() {
  return state.properties.find(queue => String(queue.property_ref ?? '') === $('queue').value) || state.properties[0];
}
function queueRef() { return currentQueue()?.property_ref ?? null; }
function selectedIds() { return [...document.querySelectorAll('.pick:checked')].map(box => box.dataset.id); }
// 02/10: the AI's notes on the drafts, in their own panel under the steps (the full width, side by side); the name
// first, to find the card; the panel hides without any
function showNotes(notes = []) {
  $('notes').replaceChildren(...notes.map(note => el('p', {class: 'alert warn'}, el('strong', {}, nameOf(note.id)), ' — ', note.nota)));
  $('notes-panel').hidden = !notes.length;
}

function nameOf(id) {
  const email = (currentQueue()?.emails || []).find(item => item.id === id) || {};
  return shortName((email.customer || {}).name) || id;
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

// 29/09: the cards in the order chosen in «Ordenar»: by the customer's latest message, newest or oldest first,
// or by the customer's step in the table above (first or last steps first, the newest first within a step).
const CARD_SORTS = ['recent', 'oldest', 'early', 'late', 'name'];
// 29/09: «Por nome (A–Z)»: the customer's name, else the email, in Portuguese alphabetical order (accents ignored)
const nameKey = email => ((email.customer || {}).name || (email.recipient || {}).name || (email.customer || {}).email
  || (email.recipient || {}).email || '').trim();
const byName = (a, b) => a.localeCompare(b, 'pt', {sensitivity: 'base'});
let cardSortChoice = null;  // this page view's choice, also when the browser keeps nothing
function cardSort() {
  if (cardSortChoice) return cardSortChoice;
  try { const value = localStorage.getItem('aria-card-sort'); return CARD_SORTS.includes(value) ? value : 'recent'; }
  catch { return 'recent'; }
}
function sortCards(emails, queue) {
  const order = cardSort(), steps = PIPELINE.map(([key]) => key);
  const stepOf = Object.fromEntries((queue?.pipeline || []).map(customer => [customer.email, steps.indexOf(customer.column)]));
  const step = email => {
    const found = stepOf[((email.recipient || {}).email || (email.customer || {}).email || '').toLowerCase()];
    return found === undefined || found < 0 ? 0 : found;
  };
  const sign = order === 'oldest' ? 1 : -1;
  return emails.map((email, index) => ({email, index, at: lastActivity(email), step: step(email)}))
    .sort((a, b) => (order === 'name' ? byName(nameKey(a.email), nameKey(b.email)) : 0)
      || (order === 'early' ? a.step - b.step : order === 'late' ? b.step - a.step : 0)
      || sign * (a.at - b.at) || a.index - b.index)
    .map(item => item.email);
}
// 29/09: the customer's latest message this card answers (the email itself and those merged into it) — never our own
// sends, or a round or a batch sent a few seconds apart would decide the order
// 30/09: «HOJE, », «ONTEM, » or «HÁ 3 DIAS, » before the day of the last read, by the calendar days of this computer
function daysAgo(value) {
  const day = moment => { const d = new Date(moment); return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()); };
  const days = Math.round((day(Date.now()) - day(value)) / 86400000);
  return days <= 0 ? 'HOJE, ' : days === 1 ? 'ONTEM, ' : `HÁ ${days} DIAS, `;
}
function lastActivity(email) {
  const moments = [email.date, ...(email.merged || []).map(part => part.date)];
  return Math.max(0, ...moments.map(value => Date.parse(value || '') || 0));
}

function renderState() {
  $('account').textContent = state.account || '';
  $('nav-count').textContent = state.properties.reduce((n, q) => n + q.emails.filter(email => !email.round && !email.owner).length, 0);
  // 02/10: the owners' messages have their own tab and count
  const ownerWaiting = state.properties.reduce((n, q) => n + q.emails.filter(email => email.owner).length, 0)
    + (state.owners?.inbox?.length || 0);
  $('owner-count').textContent = String(ownerWaiting); $('owner-count').hidden = !ownerWaiting;
  if (activeTab === 'owners') renderOwners();
  $('error').hidden = !state.error; $('error').textContent = state.error || '';
  const select = $('queue'), chosen = select.value;
  // Only ATIVO properties; an INATIVO one still shows while it has emails waiting, so none gets lost.
  const listed = state.properties.filter(queue => !queue.inactive || queue.emails.length);
  select.replaceChildren(...(listed.length ? listed : state.properties).map(queue => el('option', {value: queue.property_ref ?? ''},
    (queue.property_ref ?? 'Todos') + (queue.inactive ? ' (inativo)' : ''))));
  if ([...select.options].some(option => option.value === chosen)) select.value = chosen;
  const queue = currentQueue();
  // 27/09: no «Dias para trás» — each read goes on from the last one; a new property's first one from the day it chose.
  // 29/09: «Última leitura: terça-feira, 29/09/26, 18:40» bigger and bold. 05/10: only that (no «A próxima traz…»)
  $('last-read').replaceChildren(...(queue?.last_read_at
    ? [el('strong', {class: 'last-read-when'}, `Última leitura: ${daysAgo(queue.last_read_at)}`
        + `${new Date(queue.last_read_at).toLocaleDateString('pt-PT', {weekday: 'long'})}, ${when(queue.last_read_at)}`)]
    : queue?.read_from ? [`Ainda por ler: a primeira leitura traz os emails desde ${dayLabel(queue.read_from)}.`] : []));
  // 29/09: a round with one text for all is reviewed and sent in its own panel (Agenda), not card by card here.
  const emails = sortCards((queue?.emails || []).filter(email => !email.round && !email.owner), queue);
  const inRound = (queue?.emails || []).length - emails.length;
  $('round-notice').hidden = !inRound;
  $('round-notice').textContent = inRound ? `${inRound} proposta(s) de visita da ronda com texto comum: revê-as e envia-as `
    + 'no painel «Ronda de visitas», na Agenda.' : '';
  renderQueueBoard(queue);
  $('emails').replaceChildren(...(emails.length ? emails.map(card)
    : [el('div', {class: 'empty-state'}, el('strong', {}, state.error ? 'Configuração pendente' : 'Tudo em dia.'), state.error ? 'Verifica o aviso acima para continuar.' : 'Não há emails em tratamento. Faz uma nova leitura quando quiseres.')]));
  const active = queue?.active || [];
  const writeAll = writeAllPanel(queue);  // 04/10: «Escrever a todos», above the sent cards
  $('active-cards').replaceChildren(...(active.length ? [
    el('div', {class: 'section-heading active-heading'}, el('h2', {}, 'Enviados · clientes ativos'), el('span', {class: 'tag'}, String(active.length))),
    el('p', {class: 'step'}, 'Já respondidos, pela página ou no teu Gmail. Ficam aqui até haver visita marcada ou até os retirares; «Escrever mais» abre um rascunho na conversa do cliente.'),
    writeAll, ...active.map(activeCard)] : [writeAll]).filter(Boolean));
  renderPipeline(queue);  // after the cards: its names go to them
  // 02/10: the test property's Comunicações on a light purple page, to be sure nothing is tried on a real one
  const testing = !!(settings?.properties || []).find(item => item.reference === queue?.property_ref)?.test;
  $('tab-replies').classList.toggle('test-mode', testing);
  $('test-badge').hidden = !testing;  // 05/10: in the place of «Prepara em lote…», on the same line
  $('replies-step-text').hidden = testing;
  $('instructions').textContent = queue?.instructions || '';
  preview = null; $('preview-box').replaceChildren();
  // 29/09: «3 Enviar todos» follows the approvals of the selected emails (refreshSendButton, from updateSelection)
  // A fresh batch of emails makes any earlier "done" (import, send) stale: back to work, not finished.
  $('import-status').hidden = true; markStep('import-step', false); markStep('send-step', false);
  updateSelection();
  holdFuelButtons();  // the email cards were just rebuilt (or the queue changed), their API buttons with them
  updateSteps();
  updateSkinPanels();
}

// The steps 1, 2 and 3 are always in view (01/10). «1 Ler emails do Gmail» and «2 Gerar respostas» rest for 5 minutes
// after each use (no second read nor a second bill for one batch); «3 Enviar todos» follows the approvals. The read's
// time is the server's (last_read_at); the batch's, this browser's.
const STEP_REST_MS = 5 * 60 * 1000;  // 01/10: 5 minutes (was 10)
const TEST_REST_MS = 60 * 1000;  // 02/10: the test property, 1 minute: its rounds go fast
function stepRest() {
  return (settings?.properties || []).find(property => property.reference === queueRef())?.test ? TEST_REST_MS : STEP_REST_MS;
}
const stepsDone = {read: false, generated: false};
// 02/10: «2 Gerar respostas» rests per property: another property has its own counter (one read of the Gmail, «1»,
// brings every property's emails at once, so that one stays the same for all)
function generatedTimes() {
  try { return JSON.parse(localStorage.getItem('aria-generated-at-by-property') || '{}') || {}; } catch { return {}; }
}
function generatedAt() { return Number(generatedTimes()[queueRef() || ''] || 0); }
function markGenerated() {
  try {
    localStorage.setItem('aria-generated-at-by-property', JSON.stringify({...generatedTimes(), [queueRef() || '']: Date.now()}));
  } catch { /* Storage may be unavailable. */ }
}
function restButton(button, since, what, done) {
  const until = since + stepRest(), resting = Date.now() < until;
  button.dataset.lock = resting ? '1' : '';
  // 29/09: resting reads as a step done (green, «✓ Emails lidos»), not as a switched-off button; a class, so a click's
  // own label coming back (run) never undoes it
  button.dataset.done = done;
  button.classList.toggle('step-done', resting && button.dataset.hold !== '1');
  button.disabled = resting || button.dataset.hold === '1' || button.dataset.busy === '1';
  const hhmm = moment => new Date(moment).toLocaleTimeString('pt-PT', {hour: '2-digit', minute: '2-digit'});
  if (resting) button.title = `${what} às ${hhmm(since)}: volta a estar disponível às ${hhmm(until)}.`;
  else if (button.title.includes('volta a estar disponível')) button.title = '';
  return resting;
}
function updateSteps() {
  const lastRead = Math.max(0, ...(state.properties || []).map(queue => Date.parse(queue.last_read_at || '') || 0));
  const reading = restButton($('read'), lastRead, 'Leitura feita', 'Emails lidos');
  const generating = restButton($('generate-api'), generatedAt(), 'Respostas geradas', 'Respostas geradas');
  // 01/10: steps 1, 2 and 3 always in view (the 2nd no longer comes and goes); only 1 and 2 rest, 5 minutes after use
  $('prepare-step').hidden = false;
  $('send-step').hidden = false;
}
setInterval(() => { if (state.properties) updateSteps(); }, 15000);  // 02/10: often enough for the test's 1 minute

// 27/09: where each customer of the property stands, one column each (the furthest they got), a name per line;
// under the table, «Desistiu» (declined the visit, open by default), then, only counted, the many that would make it
// long: «Sem resposta», the greylist and the blacklist, whose names open there in a line that wraps. The dots say what
// needs doing, as set in Voz e estilo, each on its own hover; a name with a card below scrolls to it.
const PIPELINE = [
  ['contacto', '1.º contacto', 'Pediram informação e ainda não lhes respondemos.'],
  ['qualificacao', 'Em qualificação', 'Já lhes respondemos e ainda estamos a recolher os dados da ficha; sem proposta de visita.'],
  ['pronto', 'Pronto para visita', 'Ficha completa e ainda sem proposta de visita: são os clientes a convidar na próxima ronda.'],
  ['proposta', 'Proposta de visita', 'Já receberam uma proposta de visita (numa ronda ou na conversa) e ainda não escolheram hora.'],
  ['por_confirmar', 'Hora por confirmar', 'Aceitaram ou pediram uma hora que ainda não confirmámos na agenda.'],
  ['marcada', 'Visita marcada', 'Têm visita na agenda.'],
  ['visitou', 'Visitou', 'Já visitaram o imóvel.'],
  ['shortlist', 'Short list', 'Na short list de Visitas (com os suplentes).']];
const PIPELINE_SHOWN = 10;  // names shown per column; the rest counted in one line
// 03/10: «Desistiu» left the columns: a line under the table, open by default (the others closed). 04/10: «Selecionado»
// (the one selected, documents in, the contract prepared elsewhere) left them too: the first line, always open, a little
// bold, the names in gold and bold (no frame).
const PIPELINE_BELOW = [
  ['selecionado', 'Selecionado', 'documentação pedida e recebida, contrato a preparar (noutro sistema)'],
  ['desistiu', 'Desistiu', 'recusaram a visita'],
  ['sem_resposta', 'Sem resposta', 'o nosso último email está sem resposta há 3 dias ou mais, seja qual for a interação'],
  ['greylist', 'Greylist', 'ignorados por agora: disseram que não têm interesse; se voltarem a escrever, entram com um aviso'],
  ['blacklist', 'Blacklist', 'ignorados sempre: nada do que escrevem volta a entrar']];
const belowOpen = {};  // which of those lines show their names, kept while the page redraws
// 29/09: one dot in two halves — the left, what the customer gave; the right, what we have to do
function dotMeaning(color) {
  const hours = settings?.voice?.alerts || {our_turn_hours: 48, no_visit_hours: 96};
  // 29/09: short, so the legend fits in fewer lines
  return {red: 'nada dado', yellow: 'ficha a meio', green: 'ficha completa', black: 'desistiu / ignorado',
    late: `resposta atrasada (+${hours.our_turn_hours} h)`, amber: 'responder em breve',
    blue: `sem visita há +${hours.no_visit_hours} h`, ok: 'em dia', none: 'incógnito'}[color];
}
function splitDot(them, us, label = '') {
  return el('span', {class: `pipeline-dot split them-${them || 'none'} us-${us || 'none'}`, role: 'img',
    'aria-label': label || [them && 'eles: ' + dotMeaning(them), us && 'nós: ' + dotMeaning(us)].filter(Boolean).join('; ')});
}
// A person's name on the page: first name and surname, «Ana Maria Exemplo» → «Ana Exemplo». 04/10: everywhere a name is
// shown (never the first name alone when there are more), cut at about NAME_CHARS characters.
const NAME_CHARS = 22;
function shortName(name) {
  const words = String(name || '').trim().split(/\s+/).filter(Boolean);
  const text = words.length > 2 ? `${words[0]} ${words[words.length - 1]}` : words.join(' ');
  return text.length > NAME_CHARS ? text.slice(0, NAME_CHARS - 1).trimEnd() + '…' : text;
}
function renderPipeline(queue) {
  const customers = queue?.pipeline || [], box = $('pipeline');
  box.hidden = !customers.length;
  if (!customers.length) { box.replaceChildren(); return; }
  const oldest = cardSort() === 'oldest';  // 29/09: the names in each column follow «Ordenar» (newest, oldest, A–Z)
  const columns = PIPELINE.map(([key]) => customers.filter(customer => customer.column === key)
    .sort((a, b) => cardSort() === 'name' ? byName(a.name || a.email, b.name || b.email)
      : (oldest ? 1 : -1) * String(a.last_at || '').localeCompare(String(b.last_at || ''))));
  // 29/09: at most PIPELINE_SHOWN names a column (the most recent); past that, one more line with «+ N casos»
  const rows = Math.min(PIPELINE_SHOWN + 1, Math.max(0, ...columns.map(list => list.length)));
  const cell = (list, row) => row < PIPELINE_SHOWN || list.length === PIPELINE_SHOWN + 1 ? list[row] && name(list[row])
    : row === PIPELINE_SHOWN && list.length > PIPELINE_SHOWN + 1
      && el('span', {class: 'pipeline-more muted small'}, `+ ${list.length - PIPELINE_SHOWN} casos`);
  const name = customer => {
    const target = document.querySelector(`[data-customer="${CSS.escape(customer.email)}"]`);
    // 29/09: no hover texts (they never showed well): the dots are explained in the legend under the table, and the
    // name is only the link to the customer's card
    const parts = [splitDot(customer.them, customer.us), shortName(customer.name) || customer.email];
    // 04/10: a registered owner in red and bold, the one selected in gold and bold
    const kind = 'pipeline-name' + (customer.owner ? ' owner' : '') + (customer.column === 'selecionado' ? ' selected' : '')
      + (customer.column === 'shortlist' ? ' short' : '');  // 05/10: the short list in silver
    const hint = customer.owner ? 'Proprietário' : null;
    return target ? el('button', {type: 'button', class: kind, title: hint, onclick: () => {
      target.scrollIntoView({behavior: 'smooth', block: 'center'});
      target.classList.add('flash'); setTimeout(() => target.classList.remove('flash'), 1600);
    }}, ...parts) : el('span', {class: kind, title: hint}, ...parts);
  };
  const below = PIPELINE_BELOW.map(([key, label, hint]) => {
    const list = customers.filter(customer => customer.column === key);
    const always = key === 'selecionado';  // 04/10: never closes, and shows even with no one selected yet
    return (list.length || always) && el('details', {class: 'pipeline-below' + (always ? ' pipeline-selected' : ''),
      open: always || (key === 'desistiu' ? belowOpen[key] !== false : !!belowOpen[key]),
      ontoggle: event => { if (!always) belowOpen[key] = event.currentTarget.open; }},
      el('summary', always ? {onclick: event => event.preventDefault()} : {}, label + ' ', el('strong', {}, String(list.length)), el('span', {class: 'muted small'}, ' · ' + hint)),
      // 27/09: on the greylist and the blacklist, the reason after the name, when there is one
      el('div', {class: 'pipeline-below-names'}, !list.length
        ? el('span', {class: 'muted small'}, 'Ainda ninguém. Para selecionar: Clientes, na short list, «Selecionar».')
        : list.map(customer => customer.reason
        ? el('span', {class: 'pipeline-entry'}, name(customer), el('span', {class: 'muted small'}, ' — ' + customer.reason))
        : name(customer))));
  });
  box.replaceChildren(el('div', {class: 'pipeline-scroll'}, el('table', {class: 'pipeline', 'aria-label': 'Clientes por fase'},
    el('thead', {}, el('tr', {}, PIPELINE.map(([key, label, hint], index) => el('th', {scope: 'col', title: hint},
      label, el('span', {class: 'pipeline-count'}, String(columns[index].length)))))),
    el('tbody', {}, Array.from({length: rows}, (_, row) => el('tr', {}, columns.map(list => el('td', {}, cell(list, row)))))))),
    // 29/09: the dots' legend, under the table, on the right
    el('div', {class: 'pipeline-legend'},
      el('p', {}, el('strong', {}, 'Eles (esquerda):'),
        el('span', {}, splitDot(null, null, dotMeaning('none')), dotMeaning('none')),
        ['red', 'yellow', 'green'].map(color => el('span', {}, splitDot(color, null, dotMeaning(color)), dotMeaning(color))),
        el('span', {}, splitDot('black', 'black', dotMeaning('black')), dotMeaning('black'))),
      el('p', {}, el('strong', {}, 'Nós (direita):'), ['ok', 'amber', 'late', 'blue'].map(color =>
        el('span', {}, splitDot(null, color, dotMeaning(color)), dotMeaning(color))))),
    ...below.filter(Boolean));
}

// 05/10: above «Emails em tratamento», the property's queue in numbers: how many wait for an answer (big; those answered
// straight in Gmail apart), without a draft yet, with a draft to review and send, blocked, and the owners' emails waiting
// (they have their own tab). 06/10: only the work to do now; the period's numbers (replies sent, reply times, visits)
// left, as they are in the property's panel in Imóveis — and with them the Painel's metrics, asked every 20 seconds
// while Emails was open.
function renderQueueBoard(queue) {
  const box = $('queue-board');
  if (!queue || state.error) { box.hidden = true; return; }
  box.hidden = false;
  const emails = (queue.emails || []).filter(email => !email.round && !email.owner);
  const open = emails.filter(email => !email.answered_direct), direct = emails.length - open.length;
  // 06/10: «por responder» is what customers wrote; an email of ours prepared to send (a proposal taken out of the round,
  // a reminder, an extra email, a thanks) is not, and is counted apart
  const ours = open.filter(email => email.visit_window || OUR_KINDS.has(email.kind)).length, theirs = open.length - ours;
  const drafted = open.filter(email => !email.blocked && (email.reply_text || '').trim()).length;
  const blocked = open.filter(email => email.blocked).length;
  const owners = (queue.emails || []).filter(email => email.owner && !email.outbound
    && ['pending', 'draft', undefined, null].includes(email.reply_status)).length;
  box.replaceChildren(
    el('article', {class: 'metric queue-main' + (theirs ? ' bad' : ' ok')},
      el('div', {class: 'value'}, String(theirs)),
      el('div', {class: 'label'}, theirs ? 'Por responder neste imóvel' : 'Tudo respondido neste imóvel'),
      ours ? el('div', {class: 'label muted'}, `+ ${ours} ${ours === 1 ? 'email nosso' : 'emails nossos'} por enviar `
        + '(não são mensagens de clientes)') : null,
      direct ? el('div', {class: 'label muted'}, `+ ${direct} já respondido${direct === 1 ? '' : 's'} no Gmail, por retirar`) : null),
    metricCard(open.length - drafted - blocked, 'Sem rascunho: «Gerar respostas»', 'warn'),
    metricCard(drafted, 'Rascunhos prontos: rever e enviar', 'ok'),
    metricCard(blocked, 'Bloqueados: tratar à mão', 'bad'),
    metricCard(owners, 'Proprietários por responder', 'warn'));
}

// 04/10, «Escrever a todos»: the owner's words to every active customer of the property, or only to those who have not
// answered our last email — one addition draft each in the queue (the words kept on it for the AI), then «Gerar
// respostas», review and send as always. What is being written survives the page's redraws.
const writeAllDraft = {open: false, audience: 'all', note: ''};
function writeAllPanel(queue) {
  const counts = queue?.write_all;
  if (!queue?.property_ref || !counts || !(counts.all || counts.queued)) return null;
  const audience = el('select', {'aria-label': 'A quem escrever'},
    el('option', {value: 'all'}, `Todos os clientes ativos (${counts.all})`),
    el('option', {value: 'unanswered'}, `Só os que não responderam ao nosso último email (${counts.unanswered})`));
  audience.value = writeAllDraft.audience;
  audience.addEventListener('change', () => { writeAllDraft.audience = audience.value; });
  const note = el('textarea', {rows: '3', 'aria-label': 'O que queres dizer a todos',
    placeholder: 'O que queres dizer a todos. A IA escreve um email para cada um, na conversa dele (ex.: a casa fica livre '
      + 'na terça; precisamos da disponibilidade para as visitas de 7 a 9 de outubro).'});
  note.value = writeAllDraft.note;
  note.addEventListener('input', () => { writeAllDraft.note = note.value; });
  return el('details', {class: 'card write-all', open: writeAllDraft.open,
    ontoggle: event => { writeAllDraft.open = event.currentTarget.open; }},
    el('summary', {}, el('strong', {}, 'Escrever a todos'),
      el('span', {class: 'muted small'}, ' · um email para cada cliente deste imóvel, com o que escreveres')),
    audience, note,
    el('p', {class: 'muted small'}, 'Ficam de fora a blacklist, a greylist, quem disse que não quer visitar e os contactos encerrados.'
      + (counts.queued ? ` ${counts.queued} com um email na fila recebem-no quando lhes responderes: põe a mesma mensagem `
        + 'nas instruções extra do passo 2.' : '')),
    el('div', {class: 'actions'}, el('button', {type: 'button', class: 'primary', onclick: event => run(async () => {
      const count = counts[audience.value];
      if (!note.value.trim()) throw new Error('Escreve o que queres dizer a todos.');
      if (!count) throw new Error('Ninguém a quem escrever com esta escolha.');
      if (!confirm(`Criar ${count} rascunho(s), um por cliente? Nada é enviado: geras com a IA, revês e envias.`)) return;
      const result = await call('api/active/write-all', {property_ref: queue.property_ref, audience: audience.value, note: note.value});
      writeAllDraft.note = '';
      state = result.state; renderState();
      toast(`${result.created} rascunho(s) na fila, acima: gera-os com «Gerar respostas» (passo 2), revê e envia.`);
    }, event.currentTarget)}, 'Criar os rascunhos')));
}

// A sent card: an active customer already answered, until a visit is booked or the owner takes it out.
function activeCard(active) {
  const act = (path, message) => run(async () => {
    state = (await call(path, {property_ref: queueRef(), email: active.email})).state; renderState(); toast(message);
  });
  // 05/10: «Escrever mais» opens a box here, and nothing is saved until there is something in it: what to add, which
  // the AI writes into an email («Gerar com a IA»), or the email itself («Guardar como rascunho»); «Cancelar» closes it.
  const more = el('textarea', {rows: '3', 'aria-label': 'O que queres acrescentar',
    placeholder: 'O que queres acrescentar. «Gerar com a IA»: a IA escreve o email a partir disto. «Guardar como rascunho»: '
      + 'isto já é o email.'});
  const writeOne = (body, button) => run(async () => {
    const made = await call('api/active/write', {property_ref: queueRef(), email: active.email, ...body});
    state = made.state;
    if (body.note) {
      const result = await call('api/prompt/generate', {property_ref: queueRef(), ids: [made.id], extra: '', only_extra: false});
      state = result.state; applyFuel(result.fuel, queueRef());
      toast(result.saved ? 'Acrescento escrito pela IA, na fila, acima: revê-o e envia.'
        : 'A IA não escreveu o acrescento: ficou na fila com a tua nota; escreve-o tu ou cancela-o.', result.saved ? 'ok' : 'warn');
    } else toast('Acrescento na fila, acima: revê-o e envia.');
    renderState();
  }, button);
  const generate = el('button', {type: 'button', class: 'primary needs-fuel', disabled: true,
    onclick: event => writeOne({note: more.value.trim()}, event.currentTarget)}, 'Gerar com a IA');
  const keep = el('button', {type: 'button', disabled: true,
    onclick: event => writeOne({text: more.value.trim()}, event.currentTarget)}, 'Guardar como rascunho');
  more.addEventListener('input', () => {
    for (const button of [generate, keep]) button.disabled = !more.value.trim() || button.dataset.hold === '1';
  });
  const editor = el('div', {class: 'write-more', hidden: true}, more, el('div', {class: 'actions'}, generate, keep,
    el('button', {type: 'button', class: 'link', onclick: () => { editor.hidden = true; more.value = '';
      generate.disabled = keep.disabled = true; }}, 'Cancelar')));
  return el('article', {class: 'card email-card sent-card', 'data-customer': active.email},
    el('div', {class: 'card-head'},
      el('span', {class: 'who'}, el('strong', {}, shortName(active.name) || active.email)),
      el('span', {class: 'muted small contact-line head-contact'}, el('span', {}, active.email, copyButton(active.email, 'Copiar o email'))),
      el('span', {class: 'tag sent'}, 'enviado'),
      el('span', {class: 'tag'}, active.stage + '.ª interação'),
      active.visit_accepted && el('span', {class: 'tag visit'}, 'aceite ' + slotLabel(active.visit_accepted)),
      active.visit && el('span', {class: 'tag warn'}, VISIT_STATES[active.visit] || active.visit),
      el('span', {class: 'muted small'}, when(active.last_sent_at))),
    // 27/09: the whole conversation always in view, newest first, in a box of its own height (our last email on top)
    (active.history || []).length ? el('div', {class: 'conversation-box'}, conversationTurns(active.history, null))
      : active.last_text && el('blockquote', {}, active.last_text),
    el('div', {class: 'actions'},
      el('button', {type: 'button', onclick: () => {
        editor.hidden = !editor.hidden;
        if (!editor.hidden) more.focus();
      }}, 'Escrever mais'),
      el('button', {type: 'button', class: 'link', onclick: () => act('api/active/remove', 'Retirado da fila até a conversa voltar a mexer.')}, 'Retirar da fila')),
    editor);
}

function updateSelection() {
  const count = selectedIds().length;
  $('selection-count').textContent = `${count} selecionado(s)`;
  $('build-prompt').disabled = !count;
  refreshSendButton();
  markStep('inbox-step', count > 0);
  // A prompt already created stops matching once the selection (or the extra instructions) changes.
  $('copy-prompt').disabled = true;
  $('prompt').textContent = ''; $('prompt-box').open = false;
  markStep('prepare-step', false);
}

// The whole exchange with this customer, newest first: this email, and — when ours is the latest word —
// the reply we sent after it (in Gmail, or one more email), marked as still unanswered. Never less than
// the prompt gets (which keeps the conversation oldest first).
// Day AND time of a turn («qui., 24/09, 21:40»): with only the day, two messages of the same day cannot be told
// apart. Older turns kept only the day; a merged card still knows each message's own time (dates).
function turnWhen(turn, dates) {
  const moment = new Date(turn.ts || dates?.get((turn.text || '').trim()) || '');
  if (!isNaN(moment)) {
    return moment.toLocaleString('pt-PT', {weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'});
  }
  return turn.at ? turn.at.slice(8, 10) + '/' + turn.at.slice(5, 7) : '';
}

// ===== Proprietários (02/10; 03/10 by owner): the owners' list — with or without properties — chosen on top; for the one
// chosen, their properties, every message of theirs (from any property, or the inbox when they have none), «Escrever ao
// proprietário», the ponto de situação of each property and what is known of them alone.
const CAIXA = '_caixa';
let ownerChosen = null, ownerDigestRef = null, ownersKnowledgeShown = null;
function ownersData() { return state?.owners || {owners: [], inbox: []}; }
function ownerMessages(email) {
  const mine = item => (item.recipient?.email || '').toLowerCase() === email;
  return [...(state?.properties || []).flatMap(queue => (queue.emails || []).filter(item => item.owner && mine(item))
    .map(item => ({...item, property_ref: queue.property_ref}))), ...ownersData().inbox.filter(mine)];
}
function renderOwners() {
  const owners = ownersData().owners;
  if (!owners.some(owner => owner.email === ownerChosen)) ownerChosen = owners[0]?.email || null;
  const select = $('owners-select');
  select.replaceChildren(...owners.map(owner => el('option', {value: owner.email},
    `${shortName(owner.name) || owner.email}${owner.name ? ' — ' + owner.email : ''} · ${owner.refs.length ? owner.refs.join(', ') : 'sem imóveis'}`
    + (ownerMessages(owner.email).length ? ` · ${ownerMessages(owner.email).length} por responder` : ''))));
  select.value = ownerChosen || '';
  select.hidden = !owners.length;
  const owner = owners.find(item => item.email === ownerChosen);
  renderOwnerBox(owner);
  const emails = owner ? ownerMessages(owner.email) : [];
  $('owners-emails').replaceChildren(...(emails.length ? emails.map(email => ownerCard(email, email.property_ref))
    : [el('p', {class: 'empty-state'}, el('strong', {}, owner ? 'Sem mensagens deste proprietário' : 'Ainda sem proprietários'),
        owner ? 'Quando ele escrever, a mensagem aparece aqui depois de «Ler emails».' : 'Junta o primeiro em «Novo proprietário».')]));
  if (owner && ownersKnowledgeShown !== owner.email) {
    ownersKnowledgeShown = owner.email;
    $('owners-knowledge').replaceChildren(el('p', {class: 'step'}, 'O que se sabe deste proprietário: só entra nas respostas a ele, em todos os imóveis dele.'),
      knowledgeEditor('owner', null, owner.email));
  }
  if (!owner) $('owners-knowledge').replaceChildren(el('p', {class: 'muted small'}, 'Escolhe um proprietário.'));
  holdFuelButtons();
}
$('owners-select').addEventListener('change', event => { ownerChosen = event.target.value; ownerDigestRef = null; renderOwners(); run(loadOwnersDigest); });

function renderOwnerBox(owner) {
  const box = $('owners-box');
  const properties = activeProperties().filter(property => !property.test);
  const name = el('input', {placeholder: 'Nome do proprietário', 'aria-label': 'Nome do novo proprietário'});
  const address = el('input', {type: 'email', placeholder: 'email@exemplo.com', 'aria-label': 'Email do novo proprietário'});
  const adding = el('details', {class: 'owner-new'}, el('summary', {class: 'muted small'}, '+ Novo proprietário (com ou sem imóveis)'),
    el('div', {class: 'row owner-fields'}, name, address, el('button', {onclick: event => run(async () => {
      state = (await call('api/owners/add', {email: address.value.trim(), name: name.value.trim()})).state;
      ownerChosen = address.value.trim().toLowerCase(); renderState(); renderOwners();
      toast('Proprietário na lista: as mensagens dele passam a vir para aqui.');
    }, event.currentTarget)}, 'Juntar')));
  if (!owner) { box.replaceChildren(el('p', {class: 'eyebrow'}, 'PROPRIETÁRIOS'), adding); return; }
  const rename = el('input', {value: owner.name || '', placeholder: 'Nome', 'aria-label': 'Nome do proprietário'});
  const others = properties.filter(property => !owner.refs.includes(property.reference));
  const join = el('select', {'aria-label': 'Juntar um imóvel'}, el('option', {value: ''}, 'Juntar um imóvel…'),
    others.map(property => el('option', {value: property.reference}, `${property.reference}${property.owner_email ? ' (tem outro proprietário)' : ''}`)));
  const subject = el('input', {placeholder: 'Assunto (opcional)', 'aria-label': 'Assunto do email novo'});
  const about = el('select', {'aria-label': 'Sobre que imóvel'}, owner.refs.length
    ? owner.refs.map(ref => el('option', {value: ref}, ref)) : el('option', {value: CAIXA}, 'sem imóvel'));
  const setOwner = (ref, email, label) => run(async () => {
    const result = await call('api/owners/set', {property_ref: ref, email, name: owner.name || ''});
    state = result.state; settings = result.settings; renderSettings(); renderState(); renderOwners(); toast(label);
  });
  box.replaceChildren(
    el('p', {class: 'eyebrow'}, 'PROPRIETÁRIO · ' + owner.email),
    el('div', {class: 'row owner-fields'}, rename, el('button', {onclick: event => run(async () => {
      state = (await call('api/owners/add', {email: owner.email, name: rename.value.trim()})).state; renderState(); renderOwners();
      toast('Nome guardado.');
    }, event.currentTarget)}, 'Guardar o nome')),
    el('div', {class: 'owner-refs'}, el('span', {class: 'muted small'}, owner.refs.length ? 'Imóveis:' : 'Ainda sem imóveis nesta pasta de dados.'),
      owner.refs.map(ref => el('span', {class: 'tag'}, ref, ' ', el('button', {type: 'button', class: 'link', title: 'Tirar este imóvel ao proprietário',
        onclick: () => { if (confirm(`Tirar ${ref} a este proprietário?`)) setOwner(ref, '', `${ref} já não tem este proprietário.`); }}, '×'))),
      others.length ? join : null),
    el('div', {class: 'row owner-write'}, subject, about,
      el('button', {class: 'primary', onclick: event => run(async () => {
        const result = await call('api/owners/write', {property_ref: about.value, subject: subject.value.trim(), owner: owner.email});
        state = result.state; renderState();
        // 06/10: one card per owner, as for the customers: with one already waiting, that one
        toast(result.existing ? 'Já há um email por enviar a este proprietário: escreve tudo nesse cartão, abaixo (vai tudo junto).'
          : 'Email novo ao proprietário: escreve-o no cartão abaixo, ou com «Gerar resposta», e envia.');
      }, event.currentTarget)}, 'Escrever ao proprietário')),
    adding);
  join.addEventListener('change', () => { if (join.value) setOwner(join.value, owner.email, `${join.value} passou a ser deste proprietário.`); });
}

function ownerCard(email, ref) {
  const inbox = ref === CAIXA;
  const who = shortName(email.customer?.name || email.recipient?.name) || 'Proprietário';
  const draft = el('textarea', {rows: 9, 'aria-label': 'Resposta ao proprietário'}, email.reply_text || '');
  const turns = email.conversation?.length ? email.conversation
    : [{who: 'cliente', text: email.customer?.message || email.body_text || '', ts: email.date}];
  const save = async () => (await call(inbox ? 'api/owners/drafts' : 'api/drafts',
    inbox ? {replies: [{id: email.id, reply_text: draft.value}]} : {property_ref: ref, replies: [{id: email.id, reply_text: draft.value}]}));
  const keep = result => { state = result.state || result; };
  const extra = el('textarea', {rows: 2, 'aria-label': 'O que lhe queres dizer',
    placeholder: email.outbound ? 'O que lhe queres dizer (opcional): por exemplo, propor baixar a renda 50 €.'
      : 'Instruções para esta resposta (opcional).'});
  return el('article', {class: 'card email-card owner-card' + (email.outbound ? ' outbound' : '')},
    el('div', {class: 'card-head'}, el('div', {class: 'who'}, el('strong', {}, who), el('span', {class: 'muted small'}, email.recipient?.email || '')),
      el('span', {class: 'tag'}, inbox ? 'sem imóvel' : ref),
      el('span', {class: 'tag'}, email.outbound ? 'email novo · ' + (email.new_subject || '') : 'proprietário'),
      el('span', {class: 'tag' + (email.reply_status === 'draft' ? ' draft' : '')}, STATUS[email.reply_status] || email.reply_status || ''),
      el('span', {class: 'muted small'}, when(email.date))),
    (email.warnings || []).map(warning => el('p', {class: 'alert warn'}, warning)),
    email.reply_error && el('p', {class: 'alert bad'}, email.reply_error),
    el('div', {class: 'owner-history'}, [...turns].filter(turn => turn.text).reverse().slice(0, 8).map(turn => el('div', {class: 'history-turn ' + (turn.who === 'cliente' ? 'theirs' : 'ours')},
      el('p', {class: 'muted small'}, turn.who === 'cliente' ? 'Proprietário' : 'Nós', ' · ' + turnWhen(turn)), el('pre', {}, turn.text)))),
    draft, extra,
    el('div', {class: 'actions'},
      el('button', {class: 'needs-fuel', onclick: event => run(async () => {
        if (draft.value.trim() && draft.value !== (email.reply_text || '')
            && !confirm('O rascunho tem alterações por guardar, e a resposta nova substitui-as. Continuar?')) return;
        const result = await call('api/owners/generate', {property_ref: ref, ids: [email.id], extra: extra.value.trim()});
        state = result.state; if (!inbox) applyFuel(result.fuel, ref); renderState();
        const note = (result.notes || []).find(item => item.id === email.id)?.nota;
        toast(result.saved ? 'Resposta ao proprietário gerada: revê-a antes de enviar.' + (note ? ` Nota: ${note}` : '')
          : 'A IA não escreveu a resposta.' + (note ? ` Porquê: ${note}` : ''), result.saved ? 'ok' : 'warn');
      }, event.currentTarget)}, 'Gerar resposta'),
      el('button', {onclick: event => run(async () => { keep(await save()); renderState(); toast('Rascunho guardado.'); }, event.currentTarget)}, 'Guardar'),
      el('button', {class: 'primary send-action', onclick: event => run(async () => {
        if (!draft.value.trim()) throw new Error('Escreve o texto antes de enviar.');
        keep(await save());
        let sent = false, to = '';
        if (inbox) {
          const check = await call('api/owners/preview', {id: email.id});
          if (!confirm(`Enviar ao proprietário, tal como está?\n\nPara: ${check.to}\nAssunto: ${check.subject}`)) { renderState(); return; }
          const result = await call('api/owners/send', {id: email.id, check: check.check, confirmed: true});
          state = result.state; sent = result.status === 'sent'; to = check.to;
        } else {
          const check = await call('api/preview', {property_ref: ref, ids: [email.id]});
          const [reply] = check.replies;
          if (!confirm(`Enviar ao proprietário, tal como está?\n\nPara: ${reply.to}\nAssunto: ${reply.subject}`)) { renderState(); return; }
          const result = await call('api/send', {property_ref: ref, preview_token: check.preview_token, confirmed: true});
          sent = result.results[0]?.status === 'sent'; to = reply.to;
          state = await call('api/state');
        }
        if (sent) playSound('send');
        renderState();
        toast(sent ? `Enviado para ${to}.` : 'Não saiu: vê o aviso no próprio cartão antes de repetir.', sent ? 'ok' : 'bad');
      }, event.currentTarget)}, 'Enviar'),
      el('button', {class: 'link', onclick: event => run(async () => {
        if (!confirm('Esta mensagem do proprietário não precisa de resposta? Sai da lista; o Gmail não muda.')) return;
        keep(await call(inbox ? 'api/owners/dismiss' : 'api/dismiss', inbox ? {id: email.id} : {property_ref: ref, ids: [email.id]}));
        renderState();
      }, event.currentTarget)}, 'Não precisa de resposta')));
}

function conversationTurns(turns, current, dates) {
  const newest = [...turns].reverse();
  // 06/10: the customer's last message always first: after it only ours (a round, a reminder), it sat at the bottom of
  // the box, under all of ours, and the card seemed to have only our emails
  const theirs = newest.findIndex(turn => turn.who === 'cliente');
  if (theirs > 0) newest.unshift(...newest.splice(theirs, 1));
  const ourLast = theirs > 0 ? 1 : 0;
  // 01/10: «ours» or «theirs», so ours can be greyed and theirs stand out on the theme's own background
  return [
    theirs < 0 && turns.length && el('p', {class: 'muted small history-none'},
      'Nenhuma mensagem escrita pelo cliente nesta conversa: o pedido do portal veio sem texto, ou só temos os nossos emails.'),
    ...newest.map((turn, index) => el('div', {class: 'history-turn ' + (turn.who === 'cliente' ? 'theirs' : 'ours')
      + (current?.has(turn) ? ' current' : '')},
    el('p', {class: 'muted small'}, turn.who === 'cliente' ? 'Cliente' : 'Nós', ' · ' + turnWhen(turn, dates),
      current?.has(turn) ? ' · por responder' : '',
      index === 0 && theirs > 0 ? ' · a última mensagem do cliente; depois dela, só emails nossos (abaixo)' : '',
      index === ourLast && turn.who !== 'cliente' ? ' · a nossa última resposta, ainda sem resposta do cliente' : '',
      copyButton(turn.text, 'Copiar esta mensagem')),
    el('pre', {}, turn.text)))].filter(Boolean);
}

// 05/10: an addition's card says, in plain words, what it is (an extra email of ours, not a message of the customer's),
// when it was made and what was added — or, an old empty one, that nothing was sent and how to drop it. «Email extra»
// on the page: «acrescento» said nothing to the owner.
function additionNote(email) {
  const moment = email.date ? new Date(email.date) : null;
  const at = moment ? `${moment.toLocaleDateString('pt-PT', {day: '2-digit', month: '2-digit'})} às `
    + moment.toLocaleTimeString('pt-PT', {hour: '2-digit', minute: '2-digit'}) : '';
  const how = email.addition_scope === 'all' ? 'com «Escrever a todos»' : 'com «Escrever mais»';
  if (email.addition_note) return `(Email extra teu a este cliente, criado a ${at} ${how}. Não é uma mensagem do cliente. `
    + `O que quiseste dizer: «${email.addition_note}»)`;
  if ((email.reply_text || '').trim()) return `(Email extra teu a este cliente, criado a ${at} ${how}. Não é uma mensagem `
    + 'do cliente: o texto é o rascunho, abaixo)';
  return `(Email extra teu a este cliente, aberto a ${at} ${how} e ainda vazio. Não é uma mensagem do cliente e nada `
    + 'foi enviado. Se já não precisas dele, carrega em «Cancelar email extra»)';
}
function programNote(email) {
  // 06/10: «Proposta de visita: …» read as if the customer had proposed it: it is ours, and nothing new came from them
  return email.visit_window
    ? `A nossa proposta de visita${email.round ? ' (ronda)' : ''}: ${dayLabel(email.visit_window.day)}, das `
      + `${email.visit_window.start} às ${email.visit_window.end}. Não há mensagem nova do cliente: este email é nosso.`
    : email.kind === 'visit_thanks' ? `(agradecimento pela visita de ${slotLabel(email.visit_done?.at || '')}, com o inquérito e a ficha de visita`
      + (email.visit_done?.public ? `; nota pública: «${email.visit_done.public}»)` : ')')
    : email.kind === 'addition' ? additionNote(email)
    : AUX_KINDS.includes(email.kind) || email.closing ? '(sem mensagem nova do cliente: email preparado automaticamente, ver o rascunho abaixo)'
    : '';
}

function historyBlock(email) {
  // The customer's message(s) of this card: one, or several merged into one card (one reply answers all).
  const parts = email.merged?.length ? email.merged : [{message: (email.customer || {}).message || email.body_text || '', date: email.date}];
  const texts = new Set(parts.map(part => (part.message || '').trim()).filter(Boolean));
  const dates = new Map(parts.filter(part => part.date).map(part => [(part.message || '').trim(), part.date]));
  let turns = [...(email.conversation || [])];
  if (!turns.length) turns = [...(email.history || [])];
  const current = new Set(turns.filter(turn => turn.who === 'cliente' && texts.has(turn.text.trim())));
  const program = email.visit_window || AUX_KINDS.includes(email.kind) || email.closing;
  if (!program) {
    // Any not in the conversation yet: put each where it belongs in time, not simply last (27/09: each one, now that
    // the box is the only place the card shows the customer's words).
    for (const part of parts) {
      if (!(part.message || '').trim() || [...current].some(turn => turn.text.trim() === part.message.trim())) continue;
      const own = {who: 'cliente', text: part.message || '', at: (part.date || '').slice(0, 10), ts: part.date || undefined};
      const stamp = part.date ? new Date(part.date).toISOString() : own.at;
      const later = turns.findIndex(turn => turn.ts ? turn.ts > stamp : (turn.at || '') > own.at);
      turns.splice(later < 0 ? turns.length : later, 0, own); current.add(own);
    }
  }
  if (!turns.length) return false;
  // 27/09: no «Email completo» to open — the whole conversation always in view, newest first (what this card answers
  // marked), in a box of a fixed height that scrolls.
  return el('div', {class: 'conversation-box', 'aria-label': `Conversa: ${turns.length} mensagem(ns), a mais recente primeiro`},
    conversationTurns(turns, current, dates));
}

const sameText = (a, b) => [a, b].map(text => String(text || '').replace(/\r\n?/g, '\n').replace(/\s+$/, ''))
  .reduce((x, y) => x === y);

// 27/09: small line icons for an email's own buttons (update the reply, send it by email, send it by WhatsApp), drawn
// in the button's own colour.
const BUTTON_ICONS = {
  refresh: ['M20 11a8 8 0 1 0-2.34 5.66', 'M20 4v7h-7'],
  mail: ['M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z', 'M3.5 7 12 13l8.5-6'],
  chat: ['M12 4a8 8 0 1 1-3.7 15.1L4 20l1-3.9A8 8 0 0 1 12 4z', 'M9 10.5h6M9 13.5h4'],
  copy: ['M9 8h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z', 'M5 16V5a1 1 0 0 1 1-1h9'],
  phone: ['M8 3h8a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z', 'M11 18h2'],
  save: ['M5 4h11l3 3v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z', 'M8 4v5h7V4', 'M8 20v-6h8v6']};
function buttonIcon(name) {
  return svg('svg', {viewBox: '0 0 24 24', width: 16, height: 16, class: 'button-icon', 'aria-hidden': 'true', fill: 'none',
    stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round', 'stroke-linejoin': 'round'},
    BUTTON_ICONS[name].map(d => svg('path', {d})));
}

// 27/09: a small icon that copies a text to the clipboard (a customer's email address, one message of a conversation).
function copyButton(text, label) {
  return el('button', {type: 'button', class: 'copy-icon', title: label, 'aria-label': label, onclick: async () => {
    try { await navigator.clipboard.writeText(text); toast('Copiado.'); }
    catch { toast('Não consegui copiar sozinho: seleciona o texto e copia-o com ⌘C.', 'warn'); }
  }}, buttonIcon('copy'));
}

// 27/09: what the last «Atualizar resposta» of each email spent, shown under the button until the page reloads.
const lastGeneration = {};
function generationUsage(result) {
  const tokens = (result.tokens?.prompt_tokens || 0) + (result.tokens?.completion_tokens || 0);
  return `${tokens.toLocaleString('pt-PT')} tokens · ${costText(result.cost_usd)}`;
}

function card(email, index, list) {
  const customer = email.customer || {}, sender = (email.from || [])[0] || {};
  const saved = email.reply_text || '';
  const writable = !email.blocked || email.phone_only;  // 27/09: no email, but a phone: written for WhatsApp or SMS
  const draft = el('textarea', {'aria-label': 'Rascunho da resposta', rows: 7, placeholder: apiOnly()
    ? 'Rascunho: gera-o com a IA no passo 2 ou escreve aqui.' : 'Rascunho: cola a resposta do ChatGPT no passo 3 ou escreve aqui.'}, saved);
  // 27/09: under the name, the email, the phone (the notice's, contactos.csv's, or one they wrote) and the portal profile
  const address = customer.email || (email.recipient || {}).email || '', phoneShown = customer.phone || email.whatsapp || '';
  const profileUrl = /^https:\/\//.test(email.profile_url || '') ? email.profile_url : '';
  const ignoreEmail = customer.email || (email.recipient || {}).email;
  const ignoreTarget = ignoreEmail && {email: ignoreEmail, name: customer.name};
  // 29/09: no «Guardar rascunho» button nor «Por guardar»: a small floppy in the draft's corner, beside its copy icon,
  // for when the owner wants to keep a text without sending it (lit while the box differs from what was saved).
  // «Enviar já este por email» saves what is in the box itself; «Enviar por WhatsApp» and «SMS» only show once there is
  // a text to send (written, pasted or generated).
  const saveIcon = el('button', {type: 'button', class: 'copy-icon save-icon', title: 'Guardar rascunho',
    'aria-label': 'Guardar rascunho', onclick: event => run(async () => {
      state = await call('api/drafts', {property_ref: queueRef(), replies: [{id: email.id, reply_text: draft.value}]});
      renderState(); toast('Rascunho guardado.');
    }, event.currentTarget)}, buttonIcon('save'));
  const draftCopy = el('button', {type: 'button', class: 'copy-icon', title: 'Copiar o rascunho', 'aria-label': 'Copiar o rascunho',
    onclick: async () => {
      try { await navigator.clipboard.writeText(draft.value); toast('Copiado.'); }
      catch { toast('Não consegui copiar sozinho: seleciona o texto e copia-o com ⌘C.', 'warn'); }
    }}, buttonIcon('copy'));
  const refreshDraftActions = () => {
    // compared without line-ending or trailing-space differences, which the text box itself may introduce
    saveIcon.classList.toggle('unsaved', !sameText(draft.value, saved));
    for (const button of [sendOne, whatsapp, sms]) if (button) button.hidden = !draft.value.trim();
  };
  draft.addEventListener('input', refreshDraftActions);
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
    if (sent) playSound('send');
    state = await call('api/state'); renderState();
    toast(sent ? `Enviado para ${reply.to}. Saiu da lista.` : 'Não saiu: vê o aviso no próprio email antes de repetir.',
      sent ? 'ok' : 'warn');
  }, event.currentTarget)}, buttonIcon('mail'), 'Enviar já este por email');
  // WhatsApp (26/09): opens the owner's own WhatsApp on this customer with the draft written in; they press Enter
  // there. Nothing is sent from here and nothing is recorded: the email still goes (or is taken off) as usual.
  // 27/09: «Enviar por WhatsApp» (it was «Abrir no WhatsApp», and hidden without a phone number): without one it stays
  // in view, switched off, and says why.
  const phone = whatsappNumber(email.whatsapp);
  const whatsapp = writable && el('button', {type: 'button', class: 'whatsapp-action', disabled: !phone,
    title: phone ? 'Abre o WhatsApp do Mac na conversa deste cliente, com o rascunho escrito. Envias tu, lá.'
      : 'Sem telemóvel deste cliente: não há número para o WhatsApp.',
    onclick: () => run(async () => {  // 03/10: noted in the customer's context, then the app opens
      if (address) state = (await call('api/context/add', {property_ref: queueRef(), email: address, source: 'whatsapp'})).state;
      location.href = `whatsapp://send?phone=${phone}&text=${encodeURIComponent(whatsappText(draft.value))}`;
    })},
    buttonIcon('chat'), 'Enviar por WhatsApp');
  // 27/09: the same by SMS or iMessage: opens the Mac's Messages on this number with the draft written in; sent there
  const sms = writable && el('button', {type: 'button', class: 'sms-action', disabled: !phone,
    title: phone ? 'Abre as Mensagens do Mac (SMS ou iMessage) para este número, com o rascunho escrito. Envias tu, lá.'
      : 'Sem telemóvel deste cliente: não há número para a mensagem.',
    onclick: () => run(async () => {
      if (address) state = (await call('api/context/add', {property_ref: queueRef(), email: address, source: 'sms'})).state;
      location.href = `sms:+${phone}&body=${encodeURIComponent(whatsappText(draft.value))}`;
    })},
    buttonIcon('phone'), 'Enviar por SMS / iMessage');
  refreshDraftActions();
  // 27/09: a reply from the API for this email alone (the same call as «Gerar respostas», with its extra instructions),
  // after what was written in «Acrescentar ao conhecimento»: saved to the knowledge first, or for this reply only.
  const noteField = noteBox(queueRef(), null, true, writable);
  // 05/10: made here, so «Atualizar resposta» saves what was written in it first (it has no «Juntar» any more)
  const context = address && contextBox(email, address);
  const generateOne = writable && el('button', {class: 'needs-fuel',
    title: settings?.openai_configured ? 'O prompt leva as instruções e a mensagem, sem o email nem o telefone do cliente.'
      : 'Sem chave OpenAI configurada: o clique explica como.',
    onclick: event => run(async () => {
      if (draft.value.trim() && !sameText(draft.value, saved)
          && !confirm('O rascunho tem alterações por guardar, e a resposta nova substitui-as. Continuar?')) return;
      if (context) await context.beforeGenerate();  // 05/10: the customer's context first, so this reply reads it
      const fact = await noteField.beforeGenerate();
      const extra = [$('extra').value.trim(), fact.extra].filter(Boolean).join('\n');
      const result = await call('api/prompt/generate', {property_ref: queueRef(), ids: [email.id], extra, only_extra: fact.only});
      lastGeneration[email.id] = generationUsage(result);
      state = result.state; renderState(); applyFuel(result.fuel, queueRef());
      const note = (result.notes || []).find(item => item.id === email.id)?.nota;
      const kept = fact.saved === 'agency' ? ' A informação ficou no know-how da agência.'
        : fact.saved ? ' A informação ficou no conhecimento do imóvel.' : '';
      // 27/09: with no draft, the AI's own note says why (it used to be dropped)
      toast(result.saved ? `Resposta gerada (${lastGeneration[email.id]}): revê-a antes de enviar.` + kept + (note ? ` Nota: ${note}` : '')
        : 'A IA não escreveu um rascunho para este email.' + (note ? ` Porquê, nas palavras dela: ${note}` : ' Não deixou nenhuma nota.')
          + kept, result.saved ? 'ok' : 'warn');
      if (fact.saved) await loadSettings();  // the Imóveis tab lists the knowledge files: keep it current
    }, event.currentTarget)}, buttonIcon('refresh'),
    // 27/09: what the last generation spent, inside the button, in small letters under its name (no taller button)
    el('span', {class: 'button-text'}, el('span', {}, 'Atualizar resposta'),
      lastGeneration[email.id] && el('small', {class: 'button-sub'}, 'Última: ' + lastGeneration[email.id])),
    // 27/09: the engine in the button's right corner, small (it was a line of its own, «Resposta API · …», above it)
    el('span', {class: 'kind button-badge'}, 'API · ' + (settings?.ai?.model || '')));
  // 27/09: the email and its draft on the left (2/3); on the right (1/3), what can be done with it: save, send, a reply
  // from the API, a fact for the knowledge, and, last, taking it out of the queue.
  // 27/09: taking it out of the queue sits on the left, under the customer's name and tags, as pills with a hover
  const exits = el('div', {class: 'exit-actions'},
    // 05/10: an addition («Escrever mais», «Escrever a todos») is cancelled here: it leaves the queue, nothing is sent
    email.kind === 'addition' ? el('button', {class: 'pill-action remove', title: 'Tira este acrescento da fila sem o enviar. '
        + 'O Gmail não muda; podes abrir outro com «Escrever mais».', onclick: event => run(async () => {
      if ((draft.value || '').trim() && !confirm('Cancelar este email extra? O que está escrito no rascunho perde-se e nada é enviado.')) return;
      state = await call('api/dismiss', {property_ref: queueRef(), ids: [email.id]});
      renderState(); toast('Email extra cancelado: saiu da fila, nada foi enviado.');
    }, event.currentTarget)}, 'Cancelar email extra')
    : el('button', {class: 'pill-action remove', title: 'Tira este email da fila sem responder. O Gmail não muda, e se o cliente '
        + 'voltar a escrever, a mensagem nova entra normalmente.', onclick: event => run(async () => {
      if (!confirm('Este email não precisa de resposta? Sai da fila sem resposta; o Gmail não é alterado e este email não '
          + 'volta a entrar (se o cliente voltar a escrever, a mensagem nova entra normalmente).')) return;
      state = await call('api/dismiss', {property_ref: queueRef(), ids: [email.id]});
      renderState(); toast('Sem resposta: o email saiu da fila.');
    }, event.currentTarget)}, 'Não precisa de resposta'),
    // 02/10: closing the contact without the grey list: a cordial goodbye, reviewed and sent like any reply
    ignoreTarget && !email.farewell && ['lead', 'follow_up'].includes(email.kind) && el('button', {class: 'pill-action farewell',
      title: 'Encerra o contacto com uma despedida cordial (o prompt do fecho), que revês antes de enviar. Depois de enviada, '
        + 'deixamos de lhe escrever primeiro (rondas e lembretes), sem lista cinzenta; se voltar a escrever, entra normalmente.',
      onclick: event => run(async () => {
        const who = shortName(ignoreTarget.name) || ignoreTarget.email;
        if (!confirm(`Encerrar o contacto com ${who}? A resposta passa a ser uma despedida cordial, que revês antes de enviar.`)) return;
        state = (await call('api/contact/farewell', {property_ref: queueRef(), id: email.id})).state;
        renderState();
        if (!settings?.openai_configured) {
          toast(`${who}: a resposta vai ser a despedida. Gera-a (copiar/colar) e envia.`);
          return;
        }
        const result = await call('api/prompt/generate', {property_ref: queueRef(), ids: [email.id], extra: '', only_extra: false});
        state = result.state; renderState(); applyFuel(result.fuel, queueRef());
        toast(result.saved ? `Despedida para ${who} escrita: revê-a e envia.` : 'A despedida não foi escrita: usa «Atualizar resposta».',
          result.saved ? 'ok' : 'warn');
      }, event.currentTarget)}, 'Encerrar contacto'),
    ignoreTarget && el('button', {class: 'pill-action grey', title: 'O cliente disse que não quer: sai da fila e deixamos de lhe '
        + 'escrever primeiro (propostas de visita, lembretes e outros envios automáticos). Se voltar a escrever, a mensagem '
        + 'entra, com um aviso. Reverte-se em Imóveis.', onclick: event => run(async () => {
      if (!confirm(`${shortName(ignoreTarget.name) || ignoreTarget.email} disse que não tem interesse? Sai da fila e deixa de `
          + 'receber propostas de visita e outros envios automáticos, neste imóvel. Se voltar a escrever, a mensagem '
          + 'entra, com um aviso. Podes reverter mais tarde em Imóveis.')) return;
      const result = await call('api/contacts/ignore', {property_ref: queueRef(), email: ignoreTarget.email,
        ignored: true, kind: 'grey', reason: 'Cliente disse que não tem interesse.'});
      state = result.state; renderState();
      toast(`${shortName(ignoreTarget.name) || ignoreTarget.email} passou a ser ignorado(a) neste imóvel.`);
    }, event.currentTarget)}, 'Não tem interesse'),
    ignoreTarget && el('button', {class: 'pill-action danger', title: 'Blacklist, para quem não queres ouvir mais: sai da fila '
        + 'e nada do que escrever volta a entrar, neste imóvel. Não recebe nenhum envio nosso. Reverte-se em Imóveis.',
      onclick: event => run(async () => {
      if (!confirm(`Ignorar ${shortName(ignoreTarget.name) || ignoreTarget.email} sempre (blacklist), neste imóvel? Este email sai da `
          + 'fila e nunca mais volta a entrar, mesmo que escreva de novo — e não recebe propostas de visita '
          + 'nem outros envios automáticos. Podes reverter mais tarde em Imóveis.')) return;
      const result = await call('api/contacts/ignore', {property_ref: queueRef(), email: ignoreTarget.email,
        ignored: true, kind: 'black'});
      state = result.state; renderState();
      toast(`${shortName(ignoreTarget.name) || ignoreTarget.email} passou para a blacklist deste imóvel.`);
    }, event.currentTarget)}, 'Ignorar sempre / Blacklist'));
  const approve = reviewBar(email, draft);  // 29/09: «Aprovar» in the card's top corner
  // 02/10: «3 / 20» in the card's corner, to know where one is in a long queue (in the order chosen in «Ordenar»)
  const position = list?.length > 1 && el('span', {class: 'card-position', 'aria-label': `Email ${index + 1} de ${list.length}`},
    `${index + 1} / ${list.length}`);
  const reviewer = reviewNote(email, draft, saved);  // 30/09: the reviewer's marks and warnings, under the draft
  // 30/09: already answered straight in Gmail: greyed out and not ticked (it stays, for something to add)
  // 05/10: an instruction left for this reply makes a card answered in Gmail a live one again
  const greyed = email.answered_direct && !email.reply_note;
  const article = el('article', {class: 'card email-card' + (email.blocked ? ' blocked' : '') + (greyed ? ' answered-direct' : '')},
    position,
    el('div', {class: 'card-head'},
      el('label', {class: 'who'}, el('input', {type: 'checkbox', class: 'pick', 'data-id': email.id,
        checked: !email.blocked && !greyed, disabled: !!email.blocked}),
        el('strong', {}, shortName(customer.name || sender.name) || sender.email || 'Sem nome')),
      // 05/10: the email (and phone, and profile) on the name's line, after it: one line less
      (address || phoneShown || profileUrl) && el('span', {class: 'muted small contact-line head-contact'},
        address && el('span', {}, address, copyButton(address, 'Copiar o email')),
        phoneShown && el('span', {}, phoneShown, copyButton(phoneShown, 'Copiar o telefone')),
        profileUrl && el('a', {href: profileUrl, target: '_blank', rel: 'noopener noreferrer', title: 'Abre o perfil do cliente no Idealista'},
          'Perfil no Idealista ↗')),
      // 02/10: «Encerrar contacto»: the reply is a cordial goodbye
      email.farewell ? el('span', {class: 'tag warn', title: 'A resposta é uma despedida cordial (o prompt do fecho). Depois de '
        + 'enviada, deixamos de lhe escrever primeiro (rondas e lembretes), sem lista cinzenta.'}, 'encerrar contacto · despedida')
        : email.kind === 'visit_thanks' ? el('span', {class: 'tag visit'}, 'pós-visita')
        : email.kind === 'docs_request' ? el('span', {class: 'tag visit'}, 'pedido de documentos')
        : email.kind === 'visit_missed' ? el('span', {class: 'tag warn'}, 'visita falhada')
        : email.survey_reply ? el('span', {class: 'tag ' + (email.survey_reply.alerts?.length ? 'warn' : 'visit')}, 'resposta ao inquérito')
        : email.kind === 'visit_reminder' ? el('span', {class: 'tag visit'},
          (email.visit_reminder?.when === 'vespera' ? 'lembrete de visita · amanhã ' : 'lembrete de visita · hoje ')
          + String(email.visit_reminder?.at || '').slice(11))
        : email.kind === 'addition' ? el('span', {class: 'tag visit'}, 'email extra')
        : email.phase === 'shortlist' ? el('span', {class: 'tag visit', title: email.docs_requested
          ? 'Já lhe pedimos os documentos: a resposta diz o que chegou e o que falta.' : 'A resposta pede os documentos.'},
          email.docs_requested ? 'short list · documentos' : 'short list · pedir documentos')
        : email.phase === 'visited' ? el('span', {class: 'tag visit'}, 'já visitou')
        : email.phase === 'booked' ? el('span', {class: 'tag visit', title: email.booked_at ? 'Visita: ' + slotLabel(email.booked_at) : ''}, 'visita marcada')
        // 02/10: from the 9th on, the closing — the reply says goodbye and the rounds leave them out
        : email.closing_reply ? el('span', {class: 'tag warn', title: 'Já trocámos muitos emails sem a visita avançar: a '
          + 'resposta é o fecho (agradece e despede-se) e as rondas de visitas deixam de o incluir. Muda-se em Settings.'},
          email.interaction + '.ª interação · fecho')
        : email.conclusive_reply ? el('span', {class: 'tag warn', title: 'A resposta é conclusiva e a próxima é o fecho: '
          + 'decide agora (lista cinzenta, propor visita ou deixar seguir).'}, email.interaction + '.ª interação · conclusiva')
        : email.interaction && el('span', {class: 'tag'}, email.interaction + '.ª interação'),
      contactCounts(email.contact_counts),
      // 06/10: a silent customer, on the card too
      email.silence && el('span', {class: 'tag ' + (email.silence.state === 'inativo' ? 'warn' : 'draft'),
        title: email.silence.reason + (email.silence.state === 'inativo' ? ': fora das rondas e dos lembretes até voltar a escrever.'
          : ': continua nas rondas e nos lembretes; ao 4.º sem resposta, 2 dias úteis depois, fica inativo.')}, email.silence.state),
      email.merged?.length > 1 && el('span', {class: 'tag visit', title: 'Vários emails deste cliente juntos: uma só resposta responde a todos.'},
        email.merged.length + ' mensagens'),
      el('span', {class: 'tag' + (email.reply_status === 'draft' ? ' draft' : '')}, STATUS[email.reply_status] || email.reply_status || ''),
      email.kind === 'visit_proposal' && el('span', {class: 'tag visit'}, 'proposta de visita'),
      email.kind === 'reminder' && el('span', {class: 'tag visit'}, email.reminder === '4d' ? 'lembrete aos 4 dias' : 'lembrete aos 2 dias'),
      email.kind === 'consent_request' && el('span', {class: 'tag visit'}, 'pedido de consentimento'),
      email.closing && el('span', {class: 'tag visit'}, 'visitas fechadas'),
      email.consent_confirmed && el('span', {class: 'tag visit'}, 'consentimento: sim'),
      email.visit_slot && el('span', {class: 'tag visit'}, 'visita ' + slotLabel(email.visit_slot)),
      email.visit_status && el('span', {class: 'tag warn'}, VISIT_STATES[email.visit_status] || email.visit_status),
      email.interaction === 2 && fichaTag(email.ficha_summary),
      el('span', {class: 'muted small'}, when(email.date)),
      approve),
    exits,
    email.recipient_editable && recipientEditor(email),
    email.blocked && (email.phone_only
      ? el('p', {class: 'alert warn'}, 'Sem email do cliente no aviso: a resposta não segue por email. Gera-a com «Atualizar resposta» e envia-a por WhatsApp ou SMS.')
      : el('p', {class: 'alert bad'}, email.blocked)),
    (email.warnings || []).map(warning => el('p', {class: 'alert warn'}, warning)),
    // 03/10: the attached files, by name (nothing is opened here); on the short list they tell what came
    // 05/10: «> 0», or an empty list printed a «0»
    email.attachments?.length > 0 && el('p', {class: 'muted small attachments-line'}, '📎 ' + email.attachments.join(' · ')),
    email.phase === 'shortlist' && email.docs_requested && email.docs_missing?.length > 0
      && el('p', {class: 'muted small'}, 'Ainda faltam: ' + email.docs_missing.join('; ') + '.'),
    // 05/10: the owner's instruction for this reply only (as «Pedir documentos» leaves here), with «tirar»
    email.reply_note && el('p', {class: 'alert ok reply-note'}, el('strong', {}, 'Só para esta resposta: '), email.reply_note, ' ',
      el('button', {type: 'button', class: 'link', onclick: event => run(async () => {
        state = (await call('api/reply-note', {property_ref: queueRef(), id: email.id, note: ''})).state; renderState();
      }, event.currentTarget)}, 'tirar')),
    email.reply_error && el('p', {class: 'alert bad'}, email.reply_error),
    (email.draft_checks || []).map(check => el('p', {class: 'alert warn'}, 'Verificação do rascunho: ' + check)),
    email.consent_suggested && el('p', {class: 'alert warn'}, 'O cliente parece ter dito que sim: confirma para gravar em contactos.csv.'),
    // An email the program prepared has no new message of the customer's: a line says what it is, over the conversation.
    programNote(email) && el('blockquote', {}, programNote(email)),
    historyBlock(email) || (!programNote(email) && el('blockquote', {}, customer.message || email.body_text || '')),
    el('div', {class: 'draft-box'}, draft, el('div', {class: 'draft-tools'}, draftCopy, saveIcon)),
    reviewer);
  // 27/09: in the order of the work — a fact for the knowledge (open), the reply from the API, then sending it.
  // 02/10: a new customer's first email has no use for the quick replies (thanks, wait, still interested, the email
  // before, the documents…): nothing of ours yet to follow up on
  const firstEmail = email.interaction === 1
    && ![...(email.conversation || []), ...(email.history || [])].some(turn => turn.who === 'nos');
  const actions = el('aside', {class: 'card email-actions', 'aria-label': 'O que fazer com este email'},
    email.consent_suggested && el('button', {class: 'primary', onclick: event => run(async () => {
      state = await call('api/consent/confirm', {property_ref: queueRef(), id: email.id});
      renderState(); toast('Consentimento confirmado e registado em contactos.csv.');
    }, event.currentTarget)}, 'Confirmar consentimento (RGPD)'),
    generateOne && !firstEmail && quickReplies(noteField),
    context,
    noteField,
    generateOne && el('div', {class: 'email-generate'},
      generateOne),
    sendOne, whatsapp, sms);
  return el('div', {class: 'email-row', 'data-customer': ((email.recipient || {}).email || '').toLowerCase()}, article, actions);
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

// 05/10: the open/closed triangle at the start of a title drawn as the theme's eyebrow (the band in the rich themes hides
// the browser's own): an element of its own, so a theme's eyebrow ::before (AgentVal's line) stays as it is
function foldMark() { return el('span', {class: 'fold-mark', 'aria-hidden': 'true'}); }
// 27/09: quick replies — switches over «Acrescentar ao conhecimento», any number of them at once: each on writes its
// line in that box (for this reply only, unless another place is chosen there), and «Atualizar resposta» uses it.
const QUICK_REPLIES = [
  ['Agradecer o email e as informações', 'Agradece o email e as informações que o cliente nos enviou.'],
  ['Pedir que aguarde uns dias', 'Pede, por favor, que aguarde uns dias, para passarmos à próxima fase.'],
  ['Perguntar se mantém o interesse', 'Pergunta, com cordialidade, se o cliente mantém o interesse no imóvel.'],
  ['Perguntar se recebeu o email anterior', 'Pergunta se recebeu o nosso email anterior, porque não tivemos resposta e '
    + 'pode ter ido parar à pasta de spam ou lixo; se for o caso, pede que o procure lá.'],
  ['Confirmar que recebemos os documentos', 'Confirma que recebemos os documentos e que os vamos analisar.'],
  ['Propor falar por telefone ou WhatsApp', 'Propõe falar por telefone ou WhatsApp e pergunta qual é a melhor hora para o contactarmos.'],
  ['Enviar a morada e o link do Google Maps', 'Envia a morada completa do imóvel e o link do Google Maps, tal como estão na base de '
    + 'conhecimento; se lá não estiverem, não os inventes e diz em nota que faltam.']];
// 03/10: the customer's context — the owner's notes, our WhatsApp and SMS, their calls — read by the AI only in this
// customer's replies; each entry goes with ✕ (a call is only hidden from it), and «Apagar tudo» clears it
function contactCounts(counts) {
  if (!counts || !(counts.calls || counts.whatsapp || counts.sms)) return null;
  return el('span', {class: 'tag', title: 'Chamadas recebidas do portal e WhatsApp/SMS abertos pela ARIA'},
    [counts.calls && `📞 ${counts.calls} (${counts.answered} atendida${counts.answered === 1 ? '' : 's'})`,
     counts.whatsapp && `WhatsApp ${counts.whatsapp}`, counts.sms && `SMS ${counts.sms}`].filter(Boolean).join(' · '));
}
function contextBox(email, address) {
  const entries = email.context || [];
  const input = el('input', {placeholder: 'Ex.: prefere ser contactado depois das 18h', 'aria-label': 'Contexto deste cliente',
    title: 'Fica guardado ao carregar em «Atualizar resposta» (ou já, com Enter)'});
  const stamp = at => at ? `${at.slice(8, 10)}/${at.slice(5, 7)} ${at.slice(11, 16)}` : '';
  const change = (path, body, button) => run(async () => { state = (await call(path, {property_ref: queueRef(), email: address, ...body})).state; renderState(); }, button);
  // 05/10: closed by default (its title says how many entries there are)
  const box = el('details', {class: 'context-box'},
    el('summary', {class: 'eyebrow'}, foldMark(), 'CONTEXTO DESTE CLIENTE' + (entries.length ? ` · ${entries.length}` : '')),
    el('p', {class: 'muted small'}, 'Só entra nas respostas a este cliente. O que escreveres fica guardado com «Atualizar resposta» (ou já, com Enter).'),
    entries.length ? el('ul', {class: 'context-list'}, entries.slice().reverse().map(entry => el('li', {class: 'context-entry ' + entry.source},
      el('span', {class: 'muted small'}, stamp(entry.at)), el('span', {}, entry.text),
      el('button', {type: 'button', class: 'link', title: entry.source === 'call' ? 'Tirar esta chamada do contexto' : 'Apagar',
        onclick: event => change('api/context/delete', {id: entry.id}, event.currentTarget)}, '✕'))))
      : null,
    // 05/10: no «Juntar»: «Atualizar resposta» saves it first (box.beforeGenerate), or Enter saves it now
    el('div', {class: 'row context-add'}, input),
    entries.length > 1 && el('button', {type: 'button', class: 'link', onclick: event => {
      if (confirm('Apagar todo o contexto deste cliente?')) change('api/context/delete', {}, event.currentTarget);
    }}, 'Apagar tudo'));
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && input.value.trim()) {
      event.preventDefault();
      change('api/context/add', {text: input.value.trim(), source: 'manual'});
    }
  });
  box.beforeGenerate = async () => {
    const text = input.value.trim();
    if (!text) return;
    state = (await call('api/context/add', {property_ref: queueRef(), email: address, text, source: 'manual'})).state;
    input.value = '';
  };
  return box;
}

function quickReplies(noteField) {
  // 27/09: the last one, a little apart and only with one or more of the others on, is a mode, not a line: the reply is
  // then written with the chosen points only, leaving aside the interaction's prompt and what came before.
  const only = el('button', {type: 'button', class: 'quick-reply only-these', 'aria-pressed': 'false', disabled: true,
    title: 'Escreve só com os pontos marcados acima: sem seguir o prompt da interação nem responder ao que veio antes.',
    onclick: event => {
      const on = event.currentTarget.getAttribute('aria-pressed') !== 'true';
      event.currentTarget.setAttribute('aria-pressed', String(on));
      noteField.onlyThese = on;
    }}, 'Ignorar os emails anteriores');
  const count = el('span', {});  // 04/10: how many are on, in the closed box's title
  const toggles = QUICK_REPLIES.map(([label, line]) => el('button', {type: 'button', class: 'quick-reply', 'aria-pressed': 'false', title: line,
    onclick: event => {
      const on = event.currentTarget.getAttribute('aria-pressed') !== 'true';
      event.currentTarget.setAttribute('aria-pressed', String(on));
      noteField.setLine(line, on);
      noteField.open = true;
      const pressed = toggles.filter(toggle => toggle.getAttribute('aria-pressed') === 'true').length;
      count.textContent = pressed ? ` · ${pressed}` : '';
      only.disabled = !pressed;
      if (!pressed) { only.setAttribute('aria-pressed', 'false'); noteField.onlyThese = false; }
    }}, label));
  // 05/10: in a box of their own, «MENSAGENS RÁPIDAS», closed until opened, titled like «CONTEXTO DESTE CLIENTE»
  return el('details', {class: 'quick-box', open: true}, el('summary', {class: 'eyebrow'}, foldMark(), 'MENSAGENS RÁPIDAS', count),
    el('div', {class: 'quick-replies', role: 'group', 'aria-label': 'Mensagens rápidas'}, toggles, only));
}

// One more fact while reviewing a reply: it goes to notas.md and the next prompt already carries it.
// inCard (27/09): in an email's card it comes open, just above «Atualizar resposta». withGenerate: that card has the
// button, and then there is no «Guardar no conhecimento» — «Atualizar resposta» saves the fact first (this property or
// every one) or, with «Só para esta resposta», only hands it to this one reply (box.beforeGenerate).
function noteBox(ref, onSaved, inCard = false, withGenerate = false) {
  const text = el('textarea', {rows: 2, 'aria-label': 'Informação a acrescentar ao conhecimento',
    placeholder: 'Ex.: Não tem arrecadação, mas pode guardar algumas coisas no lugar de garagem.'});
  // 27/09: in an email's card, «Só para esta resposta» comes first and chosen: nothing is saved unless asked for
  const scope = el('select', {'aria-label': 'Onde guardar'},
    withGenerate && el('option', {value: 'reply', selected: true}, 'Só para esta resposta'),
    el('option', {value: 'property', selected: !withGenerate}, 'Só este imóvel'),
    // 30/09: every property of this one's kind (the agency's rentals-only or sales-only know-how)
    el('option', {value: 'agency-deal'}, (settings?.properties || []).find(item => item.reference === ref)?.deal === 'venda'
      ? 'Todos os imóveis à venda (agência)' : 'Todos os arrendamentos (agência)'),
    el('option', {value: 'agency'}, 'Todos os imóveis (agência)'));
  const saveNote = async () => {
    const result = await call('api/knowledge/note', {property_ref: ref, scope: scope.value, text: text.value});
    text.value = '';
    state = result.state; renderState();
    if (onSaved) onSaved();
    else await loadSettings();  // the Imóveis tab lists the knowledge files: keep it current
    return result;
  };
  const save = el('button', {class: 'primary', onclick: event => run(async () => {
    const result = await saveNote();
    toast((result.scope === 'agency' ? 'Guardado no know-how da agência.' : 'Guardado no conhecimento do imóvel.')
      + (inCard ? ' «Atualizar resposta» já o usa.' : ' O próximo prompt já o leva.'));
  }, event.currentTarget)}, 'Guardar no conhecimento');
  // 05/10: titled like «CONTEXTO DESTE CLIENTE» (the theme's eyebrow, its coloured band in the rich themes), and closed
  // by default (a quick reply switched on opens it, to show its line)
  const box = el('details', {class: 'note-box'}, el('summary', {class: 'eyebrow'}, foldMark(), 'ACRESCENTAR AO CONHECIMENTO'),
    text, el('div', {class: 'actions'}, scope, !withGenerate && save));
  // 27/09: a quick reply switched on writes its line in the box; switched off, takes it out again
  box.setLine = (line, on) => {
    const lines = text.value.split('\n').filter(item => item.trim() && item.trim() !== line);
    text.value = (on ? [...lines, line] : lines).join('\n');
  };
  // Before «Atualizar resposta»: a fact is saved (and the box emptied, so a retry does not save it twice); a line for
  // this reply only comes back as an extra instruction. saved: where it went, if anywhere.
  box.beforeGenerate = async () => {
    const fact = text.value.trim();
    if (!fact) return {extra: '', saved: null, only: false};
    const points = fact.split('\n').map(line => line.trim()).filter(Boolean).map(line => '- ' + line).join('\n');
    // 27/09: «Ignorar os emails anteriores»: these points are the whole reply (saved first if a place was chosen)
    if (box.onlyThese) {
      const saved = scope.value === 'reply' ? null : (await call('api/knowledge/note', {property_ref: ref, scope: scope.value, text: fact})).scope;
      return {extra: 'Escreve só estes pontos:\n' + points, saved, only: true};
    }
    // 27/09: one point per line, added to the reply (the quick replies are lines here too), never the whole of it
    if (scope.value === 'reply') return {extra: 'Só para esta resposta, junta também estes pontos ao que a interação pede:\n'
      + points, saved: null, only: false};
    const result = await call('api/knowledge/note', {property_ref: ref, scope: scope.value, text: fact});
    text.value = '';
    return {extra: '', saved: result.scope, only: false};
  };
  return box;
}

// 29/09: «3 Enviar todos» — every draft is approved in its own card (the whole conversation, the draft and its buttons
// are there already): «Aprovar» under the draft saves what is in the box; changing the text takes the approval back.
// The button lights up once every selected email is approved, and still shows the recipients before sending.
const approvals = new Map();  // email id → the text approved (this page view: a reload asks again)
function approvedNow(id) {
  const text = approvals.get(id);
  const box = document.querySelector(`.pick[data-id="${CSS.escape(id)}"]`)?.closest('article')
    ?.querySelector('textarea[aria-label="Rascunho da resposta"]');
  return text != null && !!box && sameText(text, box.value);
}

function reviewBar(email, draft) {
  if (email.blocked) return null;  // never sent by email (a phone-only one goes by WhatsApp or SMS)
  const bar = el('div', {class: 'review-bar'});
  const draw = () => {
    const approved = approvals.get(email.id);
    const current = approved != null && sameText(approved, draft.value);
    bar.hidden = !draft.value.trim();
    bar.classList.toggle('approved', current);
    bar.replaceChildren(...(current
      ? [el('span', {class: 'review-state'}, '✓ Aprovado'),
         el('button', {type: 'button', class: 'link', onclick: () => { approvals.delete(email.id); draw(); refreshSendButton(); }}, 'Desfazer')]
      : [el('span', {class: 'review-state'}, approved != null ? 'Alterado: aprova outra vez' : 'Por aprovar'),
         el('button', {type: 'button', class: 'primary', onclick: event => run(async () => {
           if (!draft.value.trim()) throw new Error('Escreve o texto antes de aprovar.');
           // what is in the box is what gets approved, and saved as its draft
           state = await call('api/drafts', {property_ref: queueRef(), replies: [{id: email.id, reply_text: draft.value}]});
           approvals.set(email.id, draft.value);
           draw(); refreshSendButton();
           const next = selectedIds().find(id => !approvedNow(id));
           if (next) {
             document.querySelector(`.pick[data-id="${CSS.escape(next)}"]`)?.closest('article')
               ?.scrollIntoView({behavior: 'smooth', block: 'start'});
           } else {
             // 29/09: the last one approved: up to «3 Enviar todos», now lit, for the owner to press
             $('preview').scrollIntoView({behavior: 'smooth', block: 'center'});
             $('preview').classList.add('flash'); setTimeout(() => $('preview').classList.remove('flash'), 1600);
             toast('Todos aprovados: carrega em «3 Enviar todos».');
           }
         }, event.currentTarget)}, 'Aprovar')]));
  };
  draft.addEventListener('input', () => { draw(); refreshSendButton(); });
  draw();
  return bar;
}

// 30/09: the reviewer — the evaluator's marks on this draft and the mistakes it found; valid only for the text it read.
// «Rever com a IA» saves what is in the box and asks for a new review.
const decimal = value => String(value).replace('.', ',');
function reviewNote(email, draft, saved) {
  if (email.blocked && !email.phone_only) return null;
  const box = el('div', {class: 'review-note'});
  const draw = () => {
    const review = email.review, fresh = email.review_fresh && sameText(draft.value, saved);
    const tooShort = draft.value.trim().length < 40;  // 30/09: the server does not review a draft this short
    const ask = el('button', {type: 'button', class: 'link', onclick: event => run(async () => {
      if (!draft.value.trim()) throw new Error('Escreve o texto antes de o rever.');
      state = await call('api/drafts', {property_ref: queueRef(), replies: [{id: email.id, reply_text: draft.value}]});
      const result = await call('api/review', {property_ref: queueRef(), ids: [email.id]});
      applyFuel(result.fuel, queueRef()); state = result.state; renderState();
      toast(result.reviewed ? 'Revisto: vê a nota e os avisos por baixo do rascunho.' : 'O revisor não devolveu nada: tenta outra vez.');
    }, event.currentTarget)}, review ? 'Rever outra vez' : 'Rever com a IA');
    box.hidden = !draft.value.trim();
    // 02/10: nothing until a review was asked for (the reviewer runs only when the owner decides)
    if (!review || tooShort) { box.hidden = true; return; }
    if (!fresh) {
      box.className = 'review-note muted';
      box.replaceChildren(el('span', {class: 'small'}, 'Revisão de outra versão do texto.'), ask);
      return;
    }
    const level = review.score >= 8 ? 'ok' : review.score >= 6 ? 'warn' : 'bad';
    box.className = 'review-note ' + level;
    box.replaceChildren(
      el('div', {class: 'review-head'}, el('strong', {}, `Revisor: ${decimal(review.score)}/10`),
        review.summary && el('span', {class: 'small'}, review.summary), ask),
      review.errors?.length ? el('ul', {}, review.errors.map(error => el('li', {}, '⚠ ' + error))) : null);
  };
  draft.addEventListener('input', draw);
  draw();
  return box;
}

function refreshSendButton() {
  const ids = selectedIds(), approved = ids.filter(approvedNow).length, all = ids.length > 0 && approved === ids.length;
  const button = $('preview');
  button.replaceChildren(el('span', {class: 'step-num', 'aria-hidden': 'true'}, '3'),
    !ids.length ? 'Enviar todos' : all ? `Enviar todos (${ids.length})` : `Enviar todos (${approved} de ${ids.length} aprovados)`);
  button.disabled = !all;
  button.title = all ? '' : 'Aprova primeiro cada email selecionado, no seu cartão.';
}

async function sendApproved() {
  const ids = selectedIds();
  if (!ids.length || !ids.every(approvedNow)) throw new Error('Aprova primeiro cada email selecionado, no seu cartão.');
  if ($('answer').value.trim()) {
    // Only the page knows this: the server never sees a paste until "Guardar rascunhos".
    $('import-step').scrollIntoView({behavior: 'smooth', block: 'center'});
    throw new Error('Tens uma resposta colada no passo 03 que ainda não foi guardada. Carrega em «Guardar rascunhos» '
      + '(ou apaga-a) antes de enviar.');
  }
  const check = await call('api/preview', {property_ref: queueRef(), ids});
  const changed = check.replies.filter(reply => !sameText(reply.reply_text, approvals.get(reply.id) || ''));
  if (changed.length) throw new Error(`${changed.length} email(s) mudaram depois de aprovados: aprova-os outra vez.`);
  const warned = check.replies.filter(reply => (reply.warnings || []).length).length;
  if (!confirm(`Enviar agora ${ids.length} email(s) aprovados?\n\nPara: ${check.replies.map(reply => reply.to).join(', ')}`
      + (warned ? `\n\n${warned} com avisos (estão no cartão de cada um).` : ''))) return;
  const result = await call('api/send', {property_ref: queueRef(), preview_token: check.preview_token, confirmed: true});
  const sent = result.results.filter(item => item.status === 'sent').length;
  if (sent) playSound('send');
  for (const item of result.results) if (item.status === 'sent') approvals.delete(item.id);
  state = await call('api/state'); keepSteps(renderState);
  $('preview-box').replaceChildren(el('p', {class: 'alert ' + (sent === result.results.length ? 'ok' : 'warn')},
    `✓ Enviados ${sent} de ${result.results.length} email(s).`
    + (sent < result.results.length ? ' Vê os avisos nos que ficaram.' : ' Passa ao próximo lote no passo 01.')));
  markStep('send-step', true);
  toast(`Enviados: ${sent} de ${result.results.length}.` + (sent < result.results.length ? ' Vê os avisos nos que ficaram.' : ''),
    sent === result.results.length ? 'ok' : 'warn');
}

function ago(value) {
  if (!value) return 'ainda não houve leitura';
  const hours = (Date.now() - new Date(value).getTime()) / 3600000;
  if (hours < 1) return `há ${Math.max(1, Math.round(hours * 60))} min`;
  if (hours < 24) return `há ${Math.round(hours)} h`;
  return `há ${Math.round(hours / 24)} dia(s)`;
}

// A number that only informs (27/09): no click, no jump to another tab; what to do is in «A fazer».
// title: what is behind it, on hover.
// 06/10: of the customers we wrote to, the share who never answered any email of ours, with a gauge under the number
function noReplyCard(share) {
  const pct = share?.written ? Math.round(100 * share.never / share.written) : null;
  const fill = el('span', {class: 'gauge-fill'});
  if (pct != null) fill.style.setProperty('--fill', pct + '%');
  // 06/10: those we first wrote to in the period of analysis; in a short one, some have not had the time to answer
  const short = ['3', '5', '7'].includes(replyWindow());
  return el('article', {class: 'metric gauge-card' + (pct >= 50 ? ' warn' : ''), title: share?.written
      ? `${share.never} de ${share.written} clientes a quem escrevemos pela primeira vez ${replyIn()} nunca responderam a `
        + 'nenhum email nosso.' + (short ? ' Num período curto, alguns ainda não tiveram tempo de responder.' : '') : ''},
    el('div', {class: 'value'}, pct == null ? '—' : pct + '%'),
    el('div', {class: 'gauge', 'aria-hidden': 'true'}, fill),
    el('div', {class: 'label'}, `Clientes que nunca responderam (${replyShort()})`));
}
function metricCard(value, label, kind, {title} = {}) {
  return el('article', {class: 'metric' + (kind && value ? ' ' + kind : ''), title},
    el('div', {class: 'value'}, String(value)), el('div', {class: 'label'}, label));
}

// The hover of the four queue numbers (27/09): the last ten emails behind each, newest first — first name, the
// property (with several), when it arrived or was written, and what it is when the program wrote it — and «+ N itens»
// for the rest. header: the split by property, above the list.
const QUEUE_SHOWS = {pending: () => true, drafts: item => item.status === 'draft', blocked: item => item.blocked,
  attention: item => ['uncertain', 'error', 'sending'].includes(item.status)};
const QUEUE_KINDS = {reminder: 'lembrete', visit_proposal: 'proposta de visita', visit_reminder: 'lembrete de visita',
  visit_thanks: 'agradecimento', visit_missed: 'visita falhada', consent_request: 'pedido de consentimento',
  visits_closed: 'visitas fechadas', addition: 'email extra', docs_request: 'pedido de documentos'};
function queueHover(properties, shows, header) {
  const items = properties.flatMap(property => (property.queue || []).filter(shows)
    .map(item => ({...item, ref: property.property_ref || 'Fila única'})))
    .sort((a, b) => (Date.parse(b.date) || 0) - (Date.parse(a.date) || 0));
  if (!items.length) return header;
  const stamp = value => {
    const moment = new Date(value);
    return isNaN(moment) ? '' : moment.toLocaleString('pt-PT', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'});
  };
  const lines = items.slice(0, 10).map(item =>
    [shortName(item.name), properties.length > 1 && item.ref, stamp(item.date), QUEUE_KINDS[item.kind]].filter(Boolean).join(' · '));
  const rest = items.length - lines.length;
  if (rest > 0) lines.push(`+ ${rest} ${rest === 1 ? 'item' : 'itens'}`);
  return (header ? header + '\n\n' : '') + lines.join('\n');
}

// 27/09: the activity chart, redrawn. A y-axis with round ticks on hairline gridlines; per bucket a pair of columns
// (requests, then sent), 2 px apart, with a 4 px rounded cap and square at the baseline; the busiest bucket's requests
// labelled on the cap; and a tooltip per bucket, on hover and on keyboard focus, with both values. The classes are the
// old ones (bar-requests, bar-sent, bar-label, grid-line), so the rich themes keep their colours.
function niceStep(most) {
  const raw = most / 4, power = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map(factor => factor * power).find(step => step >= raw);
}
function bucketLabel(day, bucketDays) {
  const short = `${day.day.slice(8)}/${day.day.slice(5, 7)}`;
  return bucketDays >= 30 ? `30 dias desde ${short}` : bucketDays > 1 ? `Semana de ${short}` : dayLabel(day.day);
}
function chart(days, bucketDays) {
  const width = 640, height = 210, left = 30, right = 6, top = 20, base = height - 24;
  const most = Math.max(1, ...days.map(day => Math.max(day.requests, day.sent)));
  const step = Math.max(1, niceStep(most)), ceiling = Math.ceil(most / step) * step;
  const y = value => base - (base - top) * value / ceiling;
  const slot = (width - left - right) / days.length;
  const bar = Math.max(1.5, Math.min(24, (slot - 6) / 2));  // two columns, 2 px apart, and air around the pair
  const pairLeft = i => left + i * slot + (slot - (2 * bar + 2)) / 2;
  const every = Math.ceil(days.length / 8);
  const column = (value, x, cls) => {
    if (!value) return null;
    const cap = y(value), r = Math.min(4, bar / 2, base - cap);
    return svg('path', {class: cls, d: `M${x} ${base}V${cap + r}Q${x} ${cap} ${x + r} ${cap}H${x + bar - r}`
      + `Q${x + bar} ${cap} ${x + bar} ${cap + r}V${base}Z`});
  };
  const ticks = Array.from({length: ceiling / step + 1}, (_, n) => n * step);
  const busiest = days.reduce((best, day, i) => day.requests > (days[best]?.requests || 0) ? i : best, -1);
  const tooltip = el('div', {class: 'chart-tooltip', role: 'status', hidden: true});
  const band = svg('rect', {class: 'chart-band', x: 0, y: top - 8, width: slot, height: base - top + 8, visibility: 'hidden'});
  const show = i => {
    const day = days[i];
    band.setAttribute('x', left + i * slot); band.setAttribute('visibility', 'visible');
    tooltip.replaceChildren(el('strong', {}, bucketLabel(day, bucketDays)),
      el('span', {class: 'tip-row'}, el('i', {class: 'tip-key requests'}), el('b', {}, String(day.requests)), ' pedido(s) recebido(s)'),
      el('span', {class: 'tip-row'}, el('i', {class: 'tip-key sent'}), el('b', {}, String(day.sent)), ' resposta(s) enviada(s)'));
    const x = (left + (i + 0.5) * slot) / width * 100;
    tooltip.style.left = `${Math.min(88, Math.max(12, x))}%`;
    tooltip.hidden = false;
  };
  const hide = () => { band.setAttribute('visibility', 'hidden'); tooltip.hidden = true; };
  const hits = days.map((day, i) => {
    const hit = svg('rect', {class: 'chart-hit', x: left + i * slot, y: top - 8, width: slot, height: base - top + 8, tabindex: 0,
      'aria-label': `${bucketLabel(day, bucketDays)}: ${day.requests} pedido(s) recebido(s), ${day.sent} resposta(s) enviada(s)`});
    hit.addEventListener('pointerenter', () => show(i)); hit.addEventListener('focus', () => show(i));
    hit.addEventListener('pointerleave', hide); hit.addEventListener('blur', hide);
    return hit;
  });
  const drawing = svg('svg', {viewBox: `0 0 ${width} ${height}`, class: 'chart', role: 'img',
                              'aria-label': 'Pedidos recebidos e respostas enviadas por ' + (bucketDays >= 30 ? '30 dias' : bucketDays > 1 ? 'semana' : 'dia')},
    band,
    ticks.map(value => [
      svg('line', {x1: left, y1: y(value), x2: width - right, y2: y(value), class: 'grid-line' + (value ? ' grid-minor' : '')}),
      svg('text', {x: left - 8, y: y(value) + 3.5, class: 'axis-label'}, value.toLocaleString('pt-PT'))]),
    days.map((day, i) => [
      column(day.requests, pairLeft(i), 'bar-requests'),
      column(day.sent, pairLeft(i) + bar + 2, 'bar-sent'),
      // null, not false: svg() only skips null children, and false would be drawn as the text "false".
      i % every === 0 || i === days.length - 1
        ? svg('text', {x: left + (i + 0.5) * slot, y: height - 6, class: 'bar-label'}, day.day.slice(8) + '/' + day.day.slice(5, 7))
        : null]),
    busiest >= 0 ? svg('text', {x: pairLeft(busiest) + bar / 2, y: y(days[busiest].requests) - 6, class: 'value-label'},
      String(days[busiest].requests)) : null,
    hits);
  return el('div', {class: 'chart-wrap'}, drawing, tooltip);
}

// 27/09: over the activity chart, the period in three numbers; their colour keys are the chart's legend.
function activitySummary(data) {
  const days = data.by_day || [];
  const requests = days.reduce((sum, day) => sum + day.requests, 0), sent = days.reduce((sum, day) => sum + day.sent, 0);
  const span = Math.max(1, days.length * (data.bucket_days || 1));
  const peak = days.reduce((best, day) => !best || day.requests > best.requests ? day : best, null);
  const stat = (key, label, value, note) => el('div', {class: 'activity-stat'},
    el('span', {class: 'activity-label'}, key && el('i', {class: 'stat-key ' + key, 'aria-hidden': 'true'}), label),
    el('strong', {}, value), el('span', {class: 'muted small'}, note));
  return [
    stat('requests', 'Pedidos recebidos', requests.toLocaleString('pt-PT'),
      `≈ ${(requests / span).toLocaleString('pt-PT', {maximumFractionDigits: 1})} por dia`),
    stat('sent', 'Respostas enviadas', sent.toLocaleString('pt-PT'), `que demoramos a responder (${replyShort()}): ${hoursText(data.reply_hours)}`),
    stat(null, (data.bucket_days || 1) > 1 ? 'Período com mais pedidos' : 'Dia com mais pedidos',
      peak && peak.requests ? peak.requests.toLocaleString('pt-PT') : '—',
      peak && peak.requests ? bucketLabel(peak, data.bucket_days || 1) : 'ainda sem pedidos')];
}

// A retro desk clock + calendar in the dashboard header. The calendar marks days with a visit booked,
// from settings.properties[].visits.slots — already loaded for Imóveis, so no call of its own.
const WEEKDAY_NARROW = [...Array(7)].map((_, i) => new Date(2024, 0, 1 + i).toLocaleDateString('pt-PT', {weekday: 'narrow'}));

// The analog face beside it, drawn once in every theme and shown only by a skin that has one (80's RacingCar's
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
  // The watch, for a skin that follows it (90's Boat keeps its night watch from 20:00 to 7:00).
  const watch = now.getHours() >= 20 || now.getHours() < 7 ? 'night' : 'day';
  if (document.documentElement.dataset.watch !== watch) document.documentElement.dataset.watch = watch;
}

function visitDays() {
  const days = {};
  for (const property of settings?.properties || []) {
    for (const slot of property.visits?.slots || []) {
      (days[slot.at.slice(0, 10)] ??= []).push(shortName(slot.name) || slot.customer || 'visita');
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

// The after-visit survey's dials (26/09): one per part asked, 0 to 100, weighted so the 1s pull hardest; green from
// report.green up (excellent), red below report.red. Used in the Painel (every property) and in each property.
// Without any answer yet the needle rests at the middle (50, like noon) and the readout says so (26/09).
function qualityGauges(report, key, size = 'small') {
  const box = el('div', {class: 'quality-gauges'}, Object.entries(report.parts).map(([part, item]) => gauge({
    key: `${key}:${part}`, value: item.score ?? 50, max: 100, red: [0, report.red], green: [report.green, 100],
    unit: 'qualidade', divisions: 4, minor: 5, size, alert: item.score != null && item.score < report.red,
    readout: item.score == null ? 'sem respostas' : `${item.count} resp.`,  // the needle already says the score (27/09)
    caption: item.label + (item.average != null ? ` · média ${item.average.toLocaleString('pt-PT')}/5` : '')
      + (item.ones ? ` · ${item.ones}× nota 1` : '') + (item.no ? ` · ${item.no}× «não»` : '')})));
  box.style.setProperty('--gauges', Object.keys(report.parts).length);  // the page's CSP allows no style attribute
  return box;
}
function renderQuality(report) {
  const box = $('dashboard-quality');
  box.hidden = !report;
  if (!report) return;
  // Through a filter: replaceChildren itself would print a null as the text «null» (26/09). 27/09: no «Continua
  // interessado…» line under the dials; the answers themselves are in Imóveis.
  box.replaceChildren(...[el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, 'QUALIDADE · INQUÉRITOS PÓS-VISITA')),  // 04/10: no subtitle
      el('span', {class: 'tag'}, `${report.responses} resposta(s)`)),
    qualityGauges(report, 'painel:quality'),
    report.responses ? null : el('p', {class: 'muted small'}, 'Ainda não há respostas ao inquérito: os ponteiros ficam a meio até chegarem, depois do agradecimento pós-visita.')]
    .filter(Boolean));
}

// 04/10: the cards' numbers for each property, in one table right under them; a property's name opens its Comunicações.
// With a single property the cards already say it all.
function renderByProperty(properties) {
  // 04/10: the Painel's only list of the properties (the cards below it are gone): from one property on, with the rent
  // and the ways in — the property's Comunicações and its Painel
  const box = $('metric-by-property');
  box.hidden = !properties.length;
  if (box.hidden) { box.replaceChildren(); return; }
  const rent = value => value == null ? '—'
    : new Intl.NumberFormat('pt-PT', {style: 'currency', currency: 'EUR', maximumFractionDigits: 0}).format(value);
  const openReplies = item => openTask({tab: 'replies', property_ref: item.property_ref});
  const openPanel = item => openPropertyPanel(item.property_ref);
  // 04/10: the titles in two lines and the description cut short (the whole of it on hover), so it all fits across
  const columns = [['pending', ['Por', 'responder'], ''], ['drafts', ['Rascunhos'], 'ok'], ['blocked', ['Bloqueados'], 'warn'],
    ['attention', ['A precisar', 'de atenção'], 'bad'], ['answered', ['Respostas', `enviadas (${replyShort()})`], '']];  // 06/10: in the period
  const title = lines => lines.flatMap((line, index) => index ? [el('br'), line] : [line]);
  const short = text => text.length > 36 ? text.slice(0, 35).trimEnd() + '…' : text;
  const cell = (value, tone) => el('td', {class: 'num' + (value ? ' ' + tone : ' zero')}, String(value || 0));
  // 04/10: a dot before each property — green, nothing to do; yellow, emails to answer or drafts to send, in time; orange,
  // a customer waiting past the reply limit (Voz e estilo); red, something needs you (an uncertain or failed send, a
  // blocked email, or a customer waiting 3 days or more)
  const limit = settings?.voice?.alerts?.our_turn_hours || 48;
  const level = item => item.attention || item.blocked || (item.oldest_wait_hours ?? 0) >= 72 ? 'red'
    : (item.oldest_wait_hours ?? 0) >= limit ? 'orange' : item.pending || item.drafts ? 'yellow' : 'green';
  const meaning = {green: 'Nada por responder nem por enviar', yellow: 'Emails por responder ou rascunhos por enviar, dentro do tempo',
    orange: `Um cliente espera há mais de ${limit} h`, red: 'Precisa de ti: envio incerto ou com erro, email bloqueado, ou um cliente à espera há 3 dias ou mais'};
  const brief = {green: 'Tudo em dia', yellow: 'Por tratar, a tempo', orange: `À espera há mais de ${limit} h`,
    red: 'Precisa de ti'};
  const dot = item => { const tone = level(item);
    return el('span', {class: 'state-dot ' + tone, title: meaning[tone], 'aria-label': meaning[tone]}); };
  box.replaceChildren(el('p', {class: 'eyebrow'}, 'POR IMÓVEL'),
    el('div', {class: 'by-property-scroll'}, el('table', {class: 'by-property'},
      el('thead', {}, el('tr', {}, el('th', {scope: 'col'}, 'Imóvel'), el('th', {scope: 'col', class: 'num'}, 'Renda'),
        columns.map(([, label]) => el('th', {scope: 'col', class: 'num'}, title(label))),
        el('th', {scope: 'col', class: 'num'}, title(['Que demoramos', `a responder (${replyShort()})`])),  // 06/10: as the card
        el('th', {scope: 'col', class: 'by-property-links'}, el('span', {class: 'sr-only'}, 'Abrir')))),
      el('tbody', {}, properties.map(item => el('tr', {class: item.test ? 'test-row' : ''},
        el('th', {scope: 'row'}, dot(item), el('button', {type: 'button', class: 'link', title: 'Abrir em Emails',
          onclick: () => openReplies(item)}, item.property_ref || 'Fila única'),
          item.test ? el('span', {class: 'tag test-tag', title: 'Fora dos totais e do ponto de situação'}, 'TESTE') : null,
          item.description ? el('span', {class: 'muted small by-property-desc', title: item.description}, ' · ' + short(item.description)) : null),
        el('td', {class: 'num'}, rent(item.advertised_rent_eur)),
        columns.map(([key, , tone]) => cell(item[key], tone)),
        el('td', {class: 'num'}, item.reply_hours == null ? '—' : hoursText(item.reply_hours)),
        el('td', {class: 'by-property-links'},
          el('button', {type: 'button', class: 'link', onclick: () => openReplies(item)}, 'Emails'),
          item.property_ref ? el('button', {type: 'button', class: 'link', title: 'O painel do imóvel, em Imóveis',
            onclick: () => openPanel(item)}, 'Painel') : null)))))),
    // 04/10: the legend in short, on one line; the whole meaning on hover (as on the dots)
    el('p', {class: 'by-property-legend muted small'}, ['green', 'yellow', 'orange', 'red'].map(tone =>
      el('span', {title: meaning[tone]}, el('span', {class: 'state-dot ' + tone, 'aria-hidden': 'true'}), brief[tone]))));
}

function renderDashboard(data) {
  renderQuality(data.quality);
  const totals = data.totals;
  // The dashboard carries no customer data, only counts, and they only inform (27/09): what to do is in «A fazer».
  const split = field => data.properties.length > 1
    ? data.properties.map(item => `${item.property_ref || 'Fila única'}: ${item[field]}`).join('\n') : undefined;
  const dm = day => day ? day.slice(8, 10) + '/' + day.slice(5, 7) : '?';
  // Who was answered: first name, the day they first wrote (when known), our last reply and how many.
  // 06/10: those answered in the period of analysis
  const answeredList = () => {
    const answered = data.properties.reduce((sum, item) => sum + (item.answered_customers || []).length, 0);
    const lines = [`${totals.answered} resposta(s) ${replyIn()} · ${answered} cliente(s)`];
    for (const item of data.properties) {
      const people = item.answered_customers || [];
      if (!people.length) continue;
      if (data.properties.length > 1) lines.push('', item.property_ref || 'Fila única');
      for (const person of people) {
        lines.push(`${shortName(person.name)} · ${person.first_contact ? 'pedido ' + dm(person.first_contact) + ' · ' : ''}`
          + `respondido ${dm(person.last_reply)} · ${person.interactions} interaç${person.interactions === 1 ? 'ão' : 'ões'}`);
      }
    }
    return lines.join('\n');
  };
  const ownersSplit = () => [...data.properties.filter(item => item.owners_pending)
    .map(item => `${item.property_ref || 'Fila única'}: ${item.owners_pending}`),
    ...(data.owners_inbox_pending ? [`Sem imóvel (caixa dos proprietários): ${data.owners_inbox_pending}`] : [])].join('\n') || undefined;
  $('metric-cards').replaceChildren(
    // 06/10: every customer, as in Clientes, and the active ones, first
    metricCard(totals.customers || 0, 'Total de clientes', null,
      {title: [CUSTOMERS_HOVER, split('customers')].filter(Boolean).join('\n\n')}),
    metricCard(totals.customers_active || 0, 'Clientes ativos', null,
      {title: [ACTIVE_HOVER, split('customers_active')].filter(Boolean).join('\n\n')}),
    metricCard(totals.pending, 'Pedidos por responder', null,
      {title: queueHover(data.properties, QUEUE_SHOWS.pending, split('pending'))}),
    metricCard(totals.drafts, 'Rascunhos prontos', 'ok', {title: queueHover(data.properties, QUEUE_SHOWS.drafts, split('drafts'))}),
    metricCard(totals.blocked, 'Bloqueados', 'warn', {title: queueHover(data.properties, QUEUE_SHOWS.blocked, split('blocked'))}),
    // 04/10: a fourth column — the owners' emails to answer (Proprietários) above, the visits booked from today below
    metricCard(totals.owners_pending || 0, 'Proprietários por responder', 'warn', {title: ownersSplit()}),
    metricCard(totals.attention, 'A precisar de atenção', 'bad',
      {title: queueHover(data.properties, QUEUE_SHOWS.attention, split('attention'))}),
    // 06/10: the period of analysis, between the rows: the second follows it (as in Emails and Imóveis), every property together
    periodRow(() => run(loadMetrics)),
    ...periodCards({...data, ...totals}, {answered: answeredList(), visits: split('visits_booked')}));
  renderByProperty([...data.properties, ...(data.test_properties || [])]);  // 04/10: the test one last, marked
  $('dashboard-read').textContent = `Última leitura ${ago(data.last_read_at)}`
    + (data.last_read_at ? ` (${when(data.last_read_at)})` : '') + ` · conta ${data.account}`;
  $('activity-summary').replaceChildren(...activitySummary(data));
  $('dashboard-chart').replaceChildren(chart(data.by_day, data.bucket_days || 1));
  $('chart-note').textContent = data.bucket_days >= 30 ? 'Cada barra soma 30 dias.' : data.bucket_days > 1 ? 'Cada barra soma uma semana.' : '';
  // 04/10: no property cards any more — «Por imóvel» has it all; here only the word when there is no property yet
  const none = !data.properties.length && !(data.test_properties || []).length;
  $('dashboard-properties').hidden = !none;
  $('dashboard-properties').replaceChildren(...(none
    ? [el('div', {class: 'empty-state'}, 'Ainda não há imóveis configurados. Adiciona o primeiro em Imóveis.')] : []));
  const check = (ok, label, hint) => el('li', {},
    el('span', {class: 'dot' + (ok ? '' : ' missing')}), el('span', {}, label,
      !ok && hint ? el('span', {class: 'muted small'}, ' — ' + hint) : ''));
  $('dashboard-setup').replaceChildren(
    check(data.setup.account, 'Conta de email configurada', 'corre mac/setup.command'),
    check(data.setup.app_password, 'App Password guardada no Keychain', 'corre mac/password.command'),
    check(data.setup.voice, 'Voz completa', 'preenche o separador Voz e estilo'),
    check(data.setup.properties > 0, `Imóveis configurados: ${data.setup.properties}`, 'cria um no separador Imóveis'));
  renderWallet(data.openai_usage, data.properties.reduce((sum, item) => sum + (item.api_fuel?.capacity_eur || 0), 0));
  renderFuelOverview(data);
}

async function loadMetrics() {
  renderDashboard(await call('api/metrics', {days: chartDays(), reply_window: replyWindow()}));
  renderNotices(await call('api/notices'));
  renderTodo(await call('api/todo'));
}

// 02/10: the notice board — the system's important messages, newest first, the unread in bold; each with «Ver» (where
// it is dealt with) and «Arquivar» (it leaves the board). The Painel tab shows how many are unread.
function renderNotices(data) {
  const notices = data.notices || [], unread = data.unread || 0;
  $('notice-count').textContent = String(unread);
  $('notice-count').hidden = !unread;
  const box = $('dashboard-notices');
  box.hidden = !notices.length;
  if (!notices.length) { box.replaceChildren(); return; }
  const update = (ids, action, button) => run(async () => renderNotices(await call('api/notices/update', {ids, action})), button);
  const stamp = at => { const moment = new Date(at);
    return `${moment.toLocaleDateString('pt-PT', {day: '2-digit', month: '2-digit'})} ${moment.toLocaleTimeString('pt-PT', {hour: '2-digit', minute: '2-digit'})}`; };
  box.replaceChildren(
    el('div', {class: 'section-heading'}, el('div', {}, el('p', {class: 'eyebrow'}, 'QUADRO DE AVISOS'),
      unread ? el('h2', {}, `${unread} aviso${unread === 1 ? '' : 's'} por ler`) : null),  // 04/10: no subtitle when all read
      // 04/10: no archiving — a notice leaves the board by itself once what it says is over. On the right, on the
      // heading's line, what the pin's colour says; below it, «Marcar todos como lidos»
      el('div', {class: 'notices-side'},
        el('p', {class: 'notice-legend'}, Object.entries(NOTICE_COLOURS).map(([level, label]) =>
          el('span', {}, el('span', {class: `notice-pin-key ${level}`, 'aria-hidden': 'true'}), label))),
        // 04/10: asks first
        el('div', {class: 'notices-actions'},
          unread ? el('button', {type: 'button', class: 'link', onclick: event => {
            if (confirm(unread === 1 ? 'Marcar o aviso por ler como lido?' : `Marcar os ${unread} avisos por ler como lidos?`)) {
              update(null, 'read', event.currentTarget);
            }
          }}, 'Marcar todos como lidos') : null))),
    el('ul', {class: 'notice-list'}, notices.slice(0, 40).map(notice => el('li', {
      class: `notice ${notice.level}${notice.read ? '' : ' unread'}${NOTICE_MARKS[notice.mark] ? ` marked mark-${notice.mark}` : ''}`,
      title: NOTICE_COLOURS[notice.level] ? `Pionés: ${NOTICE_COLOURS[notice.level]}` : ''},
      noticePin(), noticeMarks(notice, update, renderNotices),
      el('span', {class: 'notice-when'}, stamp(notice.at)),
      el('span', {class: 'notice-text'}, notice.text),
      el('span', {class: 'notice-buttons'},
        noticeNote(notice, text => run(async () => renderNotices(await call('api/notices/update', {ids: [notice.id], action: 'note', note: text})))),
        notice.tab && notice.tab !== 'dashboard' && el('button', {type: 'button', class: 'link', onclick: () => {
          update([notice.id], 'read'); openTask({tab: notice.tab, property_ref: notice.ref}); }}, 'Ver →'))))));
}
const NOTICE_COLOURS = {ok: 'tudo bem', info: 'informação', watch: 'a vigiar', warn: 'precisa de atenção', bad: 'urgente'};
// 04/10: the post-it's pin, a push pin drawn in 3D and tilted (as the owner showed it), in the level's colour (the CSS
// gives it, «color: var(--pin)»): the plastic in currentColor with light and shade over it, a short metal needle.
let pinCount = 0;
function noticePin() {
  const id = ++pinCount, shade = `pin-shade-${id}`, metal = `pin-metal-${id}`;
  const body = 'M12 12.5c3.5 2 4.6 5 4.6 9.5V34h6.8V22c0-4.5 1.1-7.5 4.6-9.5z', cap = 'M11.5 8.5h17v4.5a8.5 2.8 0 0 1-17 0z';
  return svg('svg', {class: 'notice-pin', viewBox: '-4 0 48 60', 'aria-hidden': 'true'},
    svg('defs', {},
      svg('linearGradient', {id: shade, gradientUnits: 'userSpaceOnUse', x1: 10, y1: 0, x2: 30, y2: 0},
        svg('stop', {offset: 0, 'stop-color': '#fff', 'stop-opacity': .55}), svg('stop', {offset: .38, 'stop-color': '#fff', 'stop-opacity': .08}),
        svg('stop', {offset: .62, 'stop-color': '#000', 'stop-opacity': 0}), svg('stop', {offset: 1, 'stop-color': '#000', 'stop-opacity': .38})),
      svg('linearGradient', {id: metal, gradientUnits: 'userSpaceOnUse', x1: 18.6, y1: 0, x2: 21.4, y2: 0},
        svg('stop', {offset: 0, 'stop-color': '#f2f2f2'}), svg('stop', {offset: .5, 'stop-color': '#a9adb2'}),
        svg('stop', {offset: 1, 'stop-color': '#5d6166'}))),
    svg('g', {transform: 'rotate(30 20 30)'},
      svg('path', {d: 'M19 37h2l-1 10z', fill: `url(#${metal})`}),
      svg('g', {fill: 'currentColor'}, svg('ellipse', {cx: 20, cy: 36, rx: 10, ry: 3}), svg('ellipse', {cx: 20, cy: 34.6, rx: 10, ry: 3}),
        svg('path', {d: body}), svg('path', {d: cap}), svg('ellipse', {cx: 20, cy: 8.5, rx: 8.5, ry: 2.8})),
      svg('g', {fill: `url(#${shade})`}, svg('ellipse', {cx: 20, cy: 36, rx: 10, ry: 3}), svg('path', {d: body}), svg('path', {d: cap})),
      svg('ellipse', {cx: 20, cy: 34.6, rx: 10, ry: 3, fill: '#fff', 'fill-opacity': .18}),
      svg('ellipse', {cx: 20, cy: 8.5, rx: 8.5, ry: 2.8, fill: '#fff', 'fill-opacity': .3}),
      svg('ellipse', {cx: 17, cy: 8.1, rx: 3.6, ry: 1, fill: '#fff', 'fill-opacity': .45})));
}
// 04/10: in each post-it's top-right corner: «lido» (while unread) and our own mark, the post-it's colour — red urgent,
// blue not urgent, green dealt with, and yellow back to the plain post-it (the mark on again takes it off too). A marked
// notice is read.
const NOTICE_MARKS = {urgent: 'Urgente: post-it vermelho', calm: 'Não urgente: post-it azul', done: 'Tratado: post-it verde'};
function noticeMarks(notice, update, redraw) {
  const mark = (value, button) => run(async () => redraw(await call('api/notices/update',
    {ids: [notice.id], action: 'mark', mark: notice.mark === value ? '' : value})), button);
  return el('span', {class: 'notice-marks'},
    !notice.read && el('button', {type: 'button', class: 'link notice-mark read', title: 'Marcar como lido',
      'aria-label': 'Marcar como lido', onclick: event => update([notice.id], 'read', event.currentTarget)}, '✓'),
    Object.entries(NOTICE_MARKS).map(([value, label]) => el('button', {type: 'button', class: `link notice-mark ${value}`,
      'aria-pressed': String(notice.mark === value), 'aria-label': label,
      title: notice.mark === value ? `${label} (carrega para tirar)` : label, onclick: event => mark(value, event.currentTarget)})),
    el('button', {type: 'button', class: 'link notice-mark plain', 'aria-pressed': String(!NOTICE_MARKS[notice.mark]),
      'aria-label': 'Voltar ao post-it normal', title: 'Voltar ao post-it normal (sem marca)',
      onclick: event => { if (NOTICE_MARKS[notice.mark]) mark(notice.mark, event.currentTarget); }}));
}
// 04/10: our own note on a notice, up to 25 characters: «+» to write it; written, a click changes it (empty takes it
// off). Enter or leaving the field keeps it, Esc gives up.
const NOTICE_NOTE_CHARS = 25;
function noticeNote(notice, save) {
  const box = el('span', {class: 'notice-note-box'});
  const show = () => box.replaceChildren(notice.note
    ? el('button', {type: 'button', class: 'link notice-note', title: 'A nossa nota: clica para mudar ou apagar', onclick: edit}, notice.note)
    : el('button', {type: 'button', class: 'link notice-add', title: `Acrescentar uma nota nossa (até ${NOTICE_NOTE_CHARS} caracteres)`,
      'aria-label': 'Acrescentar uma nota', onclick: edit}, '+'));
  function edit() {
    let done = false;
    const input = el('input', {type: 'text', class: 'notice-note-input', maxlength: String(NOTICE_NOTE_CHARS), value: notice.note || '',
      placeholder: `Nota (até ${NOTICE_NOTE_CHARS} caracteres)`, 'aria-label': 'A nossa nota neste aviso'});
    const finish = keep => {
      if (done) return;
      done = true;
      const text = input.value.trim();
      if (keep && text !== (notice.note || '')) save(text); else show();
    };
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); finish(true); }
      else if (event.key === 'Escape') finish(false);
    });
    input.addEventListener('blur', () => finish(true));
    box.replaceChildren(input);
    input.focus();
  }
  show();
  return box;
}

// «A fazer» (26/09): worked out from the data, most urgent first; each line takes you to where it is done.
const TODO_URGENT = new Set(['survey_alert', 'visit_reminder', 'uncertain', 'blocked', 'reply', 'accepted', 'check']);
function openTask(task) {
  const ref = task.property_ref;
  shareProperty(ref);  // 05/10: the task's property, then, in every tab
  // A menu not drawn yet has no options: the value is kept by an option of its own, which the redraw keeps.
  const choose = select => {
    if (![...select.options].some(option => option.value === ref)) select.append(el('option', {value: ref}, ref));
    select.value = ref;
  };
  if (ref && task.tab === 'agenda') choose($('agenda-property'));
  if (ref && task.tab === 'contacts') { $('fichas-property').dataset.touched = '1'; choose($('fichas-property')); }
  if (ref && task.tab === 'properties') selectProperty(ref);
  showTab(task.tab);
  // 04/10: Emails on the task's property, chosen once the tab is open and told to the page as a change of the menu
  // (its slider and the queue redraw): setting the menu's value alone left Emails on the property it was on
  if (ref && task.tab === 'replies' && [...$('queue').options].some(option => option.value === ref)) {
    $('queue').value = ref;
    $('queue').dispatchEvent(new Event('change'));
  }
}
function renderTodo(data) {
  const tasks = data.tasks || [];
  const many = new Set(tasks.map(task => task.property_ref).filter(Boolean)).size > 1;
  $('dashboard-todo').hidden = false;
  $('dashboard-todo').replaceChildren(
    el('div', {class: 'section-heading'}, el('div', {}, el('p', {class: 'eyebrow'}, 'A FAZER'),
      tasks.length ? null : el('h2', {}, 'Tudo em dia')),  // 04/10: no subtitle over the tasks; «Tudo em dia» says something
      el('span', {class: 'tag'}, String(tasks.reduce((sum, task) => sum + task.count, 0)))),
    tasks.length ? el('ul', {class: 'todo-list'}, tasks.map(task => el('li', {},
      el('button', {type: 'button', class: 'todo-item' + (TODO_URGENT.has(task.kind) ? ' urgent' : ''), onclick: () => openTask(task)},
        el('span', {class: 'todo-count'}, String(task.count)),
        el('span', {class: 'todo-text'}, task.text,
          task.names.length ? el('span', {class: 'muted small'}, ' · ' + task.names.join(', ') + (task.count > task.names.length ? '…' : '')) : null),
        many && task.property_ref ? el('span', {class: 'tag'}, task.property_ref) : null,
        el('span', {'aria-hidden': 'true'}, '→')))))
      : el('p', {class: 'muted small'}, 'Sem emails por tratar, visitas por registar nem clientes à espera. Faz uma nova leitura quando quiseres.'));
}
// «Desde sempre» first and by default (27/09): a new key, so a period saved before starts over there too; one that
// left the menu (3 days) as well.
try { $('chart-period').value = localStorage.getItem('bot-mail-period-2') || 'all'; } catch { /* Storage may be unavailable. */ }
if (!$('chart-period').value) $('chart-period').value = 'all';
const chartDays = () => $('chart-period').value === 'all' ? 'all' : Number($('chart-period').value) || 14;
// 06/10: the period of analysis («Período de análise»), chosen between the two rows of numbers in the Painel and in
// Imóveis: days back, or since 1 January. One choice, kept in this browser.
const REPLY_WINDOW_WORDS = {3: ['3 dias', 'dos últimos 3 dias', 'nos últimos 3 dias', 'últimos 3 dias'],
  5: ['5 dias', 'dos últimos 5 dias', 'nos últimos 5 dias', 'últimos 5 dias'],
  7: ['semana', 'da última semana', 'na última semana', 'última semana'],
  30: ['mês', 'do último mês', 'no último mês', 'último mês'],
  ano: ['este ano', 'desde o início do ano', 'desde o início do ano', 'desde o início do ano']};
function replyWindow() {
  try { const kept = localStorage.getItem('bot-mail-reply-window'); if (kept in REPLY_WINDOW_WORDS) return kept; } catch { /* none */ }
  return '5';
}
const replyShort = () => REPLY_WINDOW_WORDS[replyWindow()][0], replyLong = () => REPLY_WINDOW_WORDS[replyWindow()][1];
const replyIn = () => REPLY_WINDOW_WORDS[replyWindow()][2];
// The row between the two rows of cards: redraw, what to draw again once it changes
function periodRow(redraw) {
  const select = el('select', {'aria-label': 'Período de análise'},
    Object.entries(REPLY_WINDOW_WORDS).map(([value, words]) => el('option', {value}, words[3])));
  select.value = replyWindow();
  select.addEventListener('change', () => {
    try { localStorage.setItem('bot-mail-reply-window', select.value); } catch { /* Storage may be unavailable. */ }
    redraw();
  });
  return el('label', {class: 'period-row'}, el('span', {class: 'muted small'}, 'Período de análise'), select);
}
// 06/10: «Total de clientes» and «Clientes ativos», first in the first row of the Painel and of Imóveis
const CUSTOMERS_HOVER = 'Todos os clientes, como em Clientes: aqueles a quem já escrevemos e os pedidos novos ainda por responder.';
const ACTIVE_HOVER = 'Os clientes em curso: os pedidos novos, quem tem um email por responder ou uma visita marcada, e quem '
  + 'segue a conversa. Não contam os inativos, a blacklist e a greylist, quem não quer visitar ou só pode noutra data, '
  + 'nem os contactos encerrados.';
// The second row of numbers, the same in the Painel and Imóveis, all in the period of analysis.
// titles: the Painel's own hovers (who was answered; the visits by property)
function periodCards(numbers, titles = {}) {
  const value = key => numbers ? numbers[key] || 0 : '—';
  const visits = numbers ? [`As visitas que marcámos ${replyIn()}.`, titles.visits,
    `De hoje em diante: ${numbers.visits_upcoming || 0} visita(s) marcada(s).`].filter(Boolean).join('\n') : undefined;
  return [
    metricCard(value('answered'), `Respostas enviadas (${replyShort()})`, null,
      {title: titles.answered || `As respostas que enviámos ${replyIn()}. Os lembretes e os outros avisos não contam.`}),
    metricCard(numbers ? hoursText(numbers.reply_hours) : '—', `Que demoramos a responder (${replyShort()})`, null,
      {title: `Desde que o email do cliente chega até lhe enviarmos a resposta, nas respostas ${replyLong()}. Os emails `
        + 'ainda por responder não contam.'}),
    metricCard(numbers ? hoursText(numbers.client_reply_hours) : '—', `Que clientes demoram a responder (${replyShort()})`, null,
      {title: `Desde o nosso email até o cliente responder, nas respostas ${replyLong()}. Só conta cada email a que `
        + 'responderam; os que ainda esperam resposta e quem nunca respondeu não contam (estão no número ao lado).'}),
    noReplyCard(numbers?.no_reply),
    metricCard(value('visits_booked'), `Visitas marcadas (${replyShort()})`, null, {title: visits})];
}
$('chart-period').addEventListener('change', event => {
  try { localStorage.setItem('bot-mail-period-2', event.target.value); } catch { /* Storage may be unavailable. */ }
  run(loadMetrics);
});

const DIGEST_STATUS = {draft: 'rascunho', sending: 'a enviar', sent: 'enviado',
  error: 'erro no envio', uncertain: 'envio incerto'};

// «Ponto de situação» (27/09): on the left, each property's numbers as its owner wants them — who contacted us, who
// answered our first email, who is still active, the visits booked and done; on the right, a notepad with the report
// for the owner, one page per property (each owner gets only their own). Written from the data until edited here; an
// edit is kept for the day, and «Atualizar» writes it again. Nothing goes without «Enviar».
const ACTIVE_HINT = 'Dos que responderam, os que continuam: sem os que deixaram de responder, recusaram a visita '
  + 'ou pediram para não serem contactados.';
let notepadProperty = null;
function renderDigest(view) {
  const pages = view?.properties || [];
  // 27/09: the notepad shows the property picked here (it had tabs of its own)
  if (!pages.some(page => page.property_ref === notepadProperty)) notepadProperty = pages[0]?.property_ref ?? null;
  const pick = page => { notepadProperty = page.property_ref; renderDigest(view); };
  const total = key => pages.reduce((sum, page) => sum + (Array.isArray(page[key]) ? page[key].length : page[key] || 0), 0);
  const tile = (value, label, tone = '', title) => el('div', {class: 'digest-kpi ' + tone, title},
    el('strong', {}, String(value)), el('span', {}, label));
  const pill = (value, label, tone = '', title) => el('span', {class: 'digest-pill ' + tone, title}, el('b', {}, String(value)), ' ' + label);
  const property = page => el('div', {class: 'digest-property' + (page.active ? '' : ' inactive')
      + (page.property_ref === notepadProperty ? ' selected' : ''), role: 'button', tabindex: 0,
    'aria-pressed': String(page.property_ref === notepadProperty), title: 'Ver o texto para o proprietário no bloco de notas',
    onclick: () => pick(page), onkeydown: event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); pick(page); } }},
    el('div', {class: 'digest-property-head'},
      el('span', {class: 'property-ref'}, page.property_ref), el('strong', {}, page.description),
      !page.active && el('span', {class: 'tag warn'}, 'INATIVO')),
    el('div', {class: 'digest-pills'},
      pill(page.contacted, 'contactaram'), pill(page.responded, 'responderam'),
      pill(page.still_active, 'ainda ativos', '', ACTIVE_HINT), pill(page.booked, 'marcaram visita'),
      pill(page.visited.length, 'visitaram', page.visited.length ? 'ok' : '')),
    page.visited.length ? el('div', {class: 'digest-names'}, el('span', {class: 'muted small'}, 'Visitaram:'),
      page.visited.map(person => el('span', {class: 'digest-chip'}, shortName(person.name))))
      : el('p', {class: 'muted small digest-clear'}, 'Ainda sem visitas feitas'
        + (page.upcoming.length ? `; a próxima é ${slotLabel(page.upcoming[0])}.` : '.')));
  $('digest-panel').replaceChildren(el('article', {class: 'card digest-card'},
    el('p', {class: 'eyebrow'}, 'PONTO DE SITUAÇÃO'), el('h2', {}, 'Situação de ' + fullDay(view?.date)),
    ...(pages.length ? [
      el('div', {class: 'digest-kpis'},
        tile(total('contacted'), 'contactaram'), tile(total('responded'), 'responderam à 1.ª mensagem'),
        tile(total('still_active'), 'ainda ativos', '', ACTIVE_HINT), tile(total('booked'), 'marcaram visita'),
        tile(total('visited'), 'visitaram', 'ok')),
      el('p', {class: 'muted small digest-now'}, 'Os números são os de agora. Clica num imóvel para ver, ao lado, o texto '
        + 'para o proprietário.'),
      el('div', {class: 'digest-properties'}, pages.map(property)),
      pages.length > 1 && view.recipient && sendAll(view)]
      : [el('p', {class: 'muted small'}, 'Sem imóveis configurados: o ponto de situação é de cada imóvel.')])));
  renderNotepad(view);
}

// The summary of every property for the user (27/09, the option kept from before): the pages as they stand, one after
// the other, to the address in Voz e estilo; the user decides what to do with each. It leaves the pages as they are.
function sendAll(view) {
  const all = view.all || {};
  const done = all.reply_status === 'sent' || all.reply_status === 'sending';
  return el('div', {class: 'digest-all'},
    all.reply_error && el('p', {class: 'alert bad'}, all.reply_error),
    done ? el('p', {class: 'muted small'}, all.reply_status === 'sent'
      ? `Resumo de todos os imóveis enviado para ${view.recipient}${all.sent_at ? ' em ' + when(all.sent_at) : ''}.`
      : 'O resumo de todos os imóveis está a ser enviado.')
    : el('button', {class: 'send-action', onclick: event => run(async () => {
      if (!confirm(`Enviar para ${view.recipient} o resumo dos ${view.properties.length} imóveis, como está nos blocos de notas?`)) return;
      const result = await call('api/digest/send-all', {confirmed: true});
      if (result.status === 'sent') playSound('send');
      renderDigest(await call('api/digest'));
      toast(result.status === 'sent' ? 'Resumo de todos os imóveis enviado.'
        : 'Envio incerto: verifica Enviados no Gmail antes de repetir.', result.status === 'sent' ? 'ok' : 'warn');
    }, event.currentTarget)}, 'Enviar-me o resumo de todos'));
}

// The notepad: one page per property, the one picked in the ponto de situação (27/09: no tabs). The text is kept on
// leaving it (no button); a page sent, or maybe sent, stays as it went.
// 02/10: the same notepad in Proprietários too (place: its box and the property chosen there); after a change, both
// places are drawn again.
function renderNotepad(view, place = null) {
  const box = place?.box || $('digest-notepad'), pages = view?.properties || [];
  const redraw = next => { renderDigest(next); if (activeTab === 'owners') renderOwnersDigest(next); };
  if (place) {
    const own = pages.find(item => item.property_ref === place.ref);
    if (!own) { box.replaceChildren(); return; }
  } else {
    if (!pages.length) { box.replaceChildren(); return; }
    if (!pages.some(page => page.property_ref === notepadProperty)) notepadProperty = pages[0].property_ref;
  }
  const page = pages.find(item => item.property_ref === (place ? place.ref : notepadProperty));
  const ref = page.property_ref, recipient = view.recipient, status = page.reply_status;
  const editable = status === 'draft' || status === 'error';
  const text = el('textarea', {class: 'notepad-paper', rows: 18, spellcheck: 'true', readonly: !editable,
    'aria-label': `Ponto de situação para o proprietário de ${ref}`}, page.reply_text);
  const saved = el('span', {class: 'notepad-saved', 'aria-live': 'polite'});
  const save = async () => {
    if (!editable || text.value === page.reply_text) return;
    await call('api/digest/save', {property_ref: ref, text: text.value});
    page.reply_text = text.value; page.edited = true;
    saved.textContent = 'Texto guardado.';
  };
  if (editable) text.addEventListener('change', () => run(save));
  const tag = status === 'draft' && page.edited ? 'editado' : DIGEST_STATUS[status] || status;
  // Two ways out (27/09): to the owner (the email in Imóveis), with a copy to the user; or only to the user, who
  // forwards it with something of their own. Once a day per property, whichever way.
  const owner = page.owner_email, sendable = ['draft', 'error', 'uncertain'].includes(status);
  const send = (to, label, primary) => el('button', {class: (primary ? 'primary ' : '') + 'send-action',
    onclick: event => run(async () => {
      const target = to === 'owner' ? `ao proprietário (${owner})${recipient ? `, com cópia para ${recipient}` : ''}` : `para ${recipient}`;
      if (!confirm(`Enviar agora o ponto de situação de ${ref} ${target}?`)) return;
      await save();
      const result = await call('api/digest/send', {property_ref: ref, to, confirmed: true});
      if (result.status === 'sent') playSound('send');
      redraw(await call('api/digest'));
      toast(result.status === 'sent' ? 'Ponto de situação enviado.'
        : 'Envio incerto: verifica Enviados no Gmail antes de repetir.', result.status === 'sent' ? 'ok' : 'warn');
    }, event.currentTarget)}, label);
  box.replaceChildren(el('article', {class: 'card notepad-card'},
    el('div', {class: 'section-heading'},
      // 04/10: the property's reference is the subtitle (it was in the label, under «Bloco de notas»)
      el('div', {}, el('p', {class: 'eyebrow'}, 'PARA O PROPRIETÁRIO'), el('h2', {}, ref)),
      el('span', {class: 'tag' + (status === 'draft' ? ' draft' : status === 'sent' ? ' visit' : '')}, tag)),
    page.reply_error && el('p', {class: 'alert bad'}, page.reply_error),
    el('div', {class: 'notepad'}, text),
    el('p', {class: 'muted small notepad-to'}, status === 'sent'
      ? `Enviado ${page.sent_to === 'owner' ? `ao proprietário (${owner || '—'})` : `para ${recipient || '—'}`}`
        + `${page.sent_at ? ' em ' + when(page.sent_at) : ''}.`
      : (owner ? `Proprietário: ${owner}${recipient ? `, com cópia para ${recipient}` : ''}.`
        : 'Sem email do proprietário: põe-no em Imóveis, nos dados do imóvel.')
        + (recipient ? '' : ' Para o receberes tu, põe o teu email em Voz e estilo.'),
      ' ', saved),
    el('div', {class: 'actions notepad-actions'},
      sendable && owner && send('owner', 'Enviar ao proprietário', true),
      sendable && recipient && send('me', 'Enviar para mim', !owner),
      el('button', {type: 'button', onclick: async () => {
        try { await navigator.clipboard.writeText(text.value); toast('Copiado: cola-o no email ou no WhatsApp do proprietário.'); }
        catch { text.select(); toast('Não consegui copiar sozinho: o texto ficou selecionado, copia-o com ⌘C.', 'warn'); }
      }}, 'Copiar'),
      editable && el('button', {class: 'link', onclick: event => run(async () => {
        if (page.edited && !confirm('O texto volta a ser escrito com os números de agora e perdes o que alteraste. Continuar?')) return;
        redraw(await call('api/digest/refresh', {property_ref: ref})); toast('Texto atualizado com a situação de agora.');
      }, event.currentTarget)}, 'Atualizar com a situação de agora'))));
}

async function loadDigest() { renderDigest(await call('api/digest')); }
// 02/10: Proprietários shows the ponto de situação of the property chosen there (it stays in the Painel too)
// 03/10: the ponto de situação of one of the owner's properties (a menu when they have several); none without property
function renderOwnersDigest(view) {
  const owner = ownersData().owners.find(item => item.email === ownerChosen);
  const refs = owner?.refs || [];
  if (!refs.includes(ownerDigestRef)) ownerDigestRef = refs[0] || null;
  if (!ownerDigestRef) { $('owners-digest').replaceChildren(); return; }
  const holder = el('div');
  renderNotepad(view, {box: holder, ref: ownerDigestRef});
  const pick = refs.length > 1 && el('select', {'aria-label': 'Ponto de situação de que imóvel', onchange: event => {
    ownerDigestRef = event.target.value; renderOwnersDigest(view); }}, refs.map(ref => el('option', {value: ref, selected: ref === ownerDigestRef}, ref)));
  $('owners-digest').replaceChildren(...[pick, holder].filter(Boolean));
}
async function loadOwnersDigest() { renderOwnersDigest(await call('api/digest')); }

// What a past round looked like: who it went to, and where each one stands now (booked and when, declined,
// still an unsent draft, or sent and awaiting a reply) — otherwise a sent round leaves no trace to check. 04/10: shown
// (in Visitas) only the first `shown`, then «+ N clientes», a closed list that opens to the rest, each as above (the hover
// with the names did not show well); kept open or closed while the page redraws.
let roundMoreOpen = false;
function roundSummaryContent(data, shown = Infinity) {
  if (!data.window) return [el('p', {class: 'muted small'}, 'Ainda sem nenhuma ronda para este imóvel.')];
  // 06/10: «por enviar» while the round's proposal to them has not gone out (it said «por responder», as if they owed
  // us an answer); «por responder» only for an email of theirs waiting for ours
  const stateLabel = {...CLIENT_STATE_LABEL, nao_quer: 'não quer visitar', outra_data: 'só pode noutra data', unsent: 'por enviar'};
  const note = person => person.state === 'ok' ? 'enviado, a aguardar resposta'
    : person.state === 'unsent' ? 'a proposta ainda não saiu' : person.state === 'pending' ? 'escreveu e espera a nossa resposta'
    : person.reason || '';
  const row = person => el('div', {class: 'client-row'},
    el('span', {}, shortName(person.name) || person.email),
    el('span', {class: 'tag' + (person.state === 'booked' ? ' visit' : person.state === 'unsent' ? ' draft' : '')},
      person.visit_at ? slotLabel(person.visit_at) : (stateLabel[person.state] || person.state)),
    el('span', {class: 'muted small'}, note(person)));
  const rest = data.recipients.slice(shown);
  const unsent = data.recipients.length && data.recipients.every(person => person.state === 'unsent');
  return [
    el('p', {class: 'muted small'},
      `Última ronda: ${dayLabel(data.window.day)}, das ${data.window.start} às ${data.window.end}`
      + (unsent ? ' · ainda por enviar' : '')),
    // 06/10: a newer round prepared and not sent, said apart (the last round is the one that went out)
    data.unsent_round && el('p', {class: 'alert warn round-unsent'}, `Há uma ronda mais recente ainda por enviar: `
      + `${dayLabel(data.unsent_round.day)}, das ${data.unsent_round.start} às ${data.unsent_round.end}. Está preparada acima; `
      + 'se foi por engano, «Cancelar esta ronda».'),
    el('div', {class: 'client-list'}, data.recipients.slice(0, shown).map(row)),
    rest.length && el('details', {class: 'round-more', open: roundMoreOpen,
      ontoggle: event => { roundMoreOpen = event.currentTarget.open; }},
      el('summary', {class: 'muted small'}, `+ ${rest.length} ${rest.length === 1 ? 'cliente' : 'clientes'}`),
      el('div', {class: 'client-list'}, rest.map(row)))].filter(Boolean);
}

// One click, all of a property's active clients: skips the per-client picking in Imóveis → Visitas for
// the common case (everyone eligible gets the same day and window). Fine control still lives there.
// 02/10: who this round reaches now, and who stays out and why (5 of 20 was a surprise). Those still waiting for our
// answer include the new requests, which have no conversation until the first reply goes out; those whose only
// email waiting is our visit proposal (a round prepared, not sent) are counted apart.
// 05/10: each group with its names too, for the line to open: [count, its words, the names]
function roundGroups(data) {
  const customers = data.customers || [], out = data.left_out || {}, names = data.left_out_names || {};
  const of = state => customers.filter(customer => customer.state === state).map(customer => customer.name || customer.email);
  const proposal = new Set(names.proposal || []);
  const waiting = [...of('pending').filter(name => !proposal.has(name)), ...(names.new || [])];
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  return [
    [of('ok'), n => plural(n, 'recebe o convite', 'recebem o convite')],
    [names.proposal || [], n => `${n} com a proposta de visita ainda por enviar`],
    [waiting, n => `${n} com email por responder em Emails (entram depois de lhes responderes)`],
    [of('booked'), n => `${n} já com visita marcada`],
    [of('nao_quer'), n => plural(n, 'não quer visitar', 'não querem visitar')],
    [of('outra_data'), n => plural(n, 'só pode noutra data', 'só podem noutra data')],
    [of('closed'), n => plural(n, 'já levou o email de fecho', 'já levaram o email de fecho')],
    [names.ignored || [], n => `${n} na lista de ignorados`],
    [names.inactive || [], n => plural(n, 'inativo', 'inativos') + ' (o 4.º email nosso 2 dias úteis sem resposta)']]
    .filter(([list], index) => index === 0 || list.length).map(([list, text]) => ({text: text(list.length), names: list}));
}
// 05/10: «Agora: …», a line that opens to the names of each group (kept open or closed while the panel redraws)
let roundCountsOpen = false;
function roundCountsBox(box, data) {
  const groups = roundGroups(data);
  box.open = roundCountsOpen;
  box.replaceChildren(el('summary', {}, 'Agora: ' + groups.map(group => group.text).join(' · ') + '.'),
    el('ul', {class: 'round-groups'}, groups.map(group => el('li', {},
      el('strong', {}, group.text.replace(/ \(.*\)$/, '') + ': '),
      group.names.length ? group.names.map(name => shortName(name) || name).join(', ') : '—'))));
}

// 02/10: the property is the one chosen at the top of Visitas (the switcher), not a menu of its own down here.
let roundPanelProperty = null;
const roundDraft = {};  // 06/10: property → the day, times and note being chosen in «Ronda de visitas»  // the property the panel was drawn for: renderAgenda redraws it when the top one changes
function renderVisitsRound() {
  const box = $('visits-round-panel');
  const ref = $('agenda-property').value;
  roundPanelProperty = ref;
  const property = activeProperties().find(item => item.reference === ref);
  const card = (...body) => box.replaceChildren(el('article', {class: 'card'},
    el('p', {class: 'eyebrow'}, 'RONDA DE VISITAS'), el('h2', {}, 'Avisa os clientes ativos'), ...body));
  if (!property) {
    card(el('p', {class: 'muted small'}, 'Escolhe o imóvel lá em cima, nas setas: a ronda é de um imóvel de cada vez.'));
    return;
  }
  if (property.visits?.closed_at) {
    card(el('p', {class: 'muted small'}, `As visitas de ${ref} estão fechadas: não há ronda.`));
    return;
  }
  const slot = settings.voice.visits?.slot_minutes || 30;
  // 06/10: the day opens on tomorrow (a round for today was a date left as it came: 05/10 went out for the 6th), and the
  // day, the times and the note chosen survive the page's redraws, per property
  const draft = roundDraft[ref] ||= {};
  const tomorrow = new Date(Date.now() + 86400000).toLocaleDateString('sv-SE');
  const day = el('input', {type: 'date', 'aria-label': 'Dia das visitas',
    value: draft.day && draft.day >= new Date().toLocaleDateString('sv-SE') ? draft.day : tomorrow});
  const start = el('input', {type: 'time', value: draft.start || '17:00', step: slot * 60, 'aria-label': 'Hora de início'});
  const end = el('input', {type: 'time', value: draft.end || '19:00', step: slot * 60, 'aria-label': 'Hora de fim'});
  linkTimes(start, end);
  // 29/09: what this round's emails should say, and one text for everyone unless the owner individualizes
  const note = el('textarea', {rows: 3, 'aria-label': 'Conhecimento desta ronda',
    placeholder: 'Conhecimento desta ronda (opcional): o que estes emails devem dizer — por exemplo, que o inquilino '
      + 'ainda lá está, onde estacionar ou quanto dura a visita.'}, draft.note || '');
  for (const [key, field] of Object.entries({day, start, end, note})) {
    for (const type of ['input', 'change']) field.addEventListener(type, () => { draft[key] = field.value; });
  }
  const individual = el('input', {type: 'checkbox'});
  // 29/09: nothing is sent at this click. With one text for all, it prepares the round and writes the draft at once
  // (via API), shown at the end of this panel to review; only «Enviar a todos», there, sends.
  // 29/09: 1 prepares the draft, 2 («Enviar a todos», beside it once there is a draft) sends
  const stepNum = number => el('span', {class: 'step-num', 'aria-hidden': 'true'}, number);
  const startLabel = () => individual.checked ? ['Iniciar ronda'] : [stepNum('1'), 'Preparar o texto da ronda'];
  const roundActions = el('span', {class: 'round-actions'});
  const startButton = el('button', {class: 'primary', onclick: event => run(async () => {
    if (!day.value) throw new Error('Escolhe o dia das visitas.');
    if (day.value === new Date().toLocaleDateString('sv-SE')
        && !confirm(`A ronda é para hoje, ${dayLabel(day.value)}, das ${start.value} às ${end.value}. É mesmo para hoje?`)) return;
    const common = !individual.checked;
    const data = await call('api/visits/candidates', {property_ref: ref});
    const emails = data.customers.filter(customer => customer.state === 'ok').map(customer => customer.email);
    if (!emails.length) throw new Error('Não há clientes elegíveis agora (por responder, já convidados ou recusaram).');
    if (!common && !confirm(`Vais criar ${emails.length} proposta(s) de visita, uma por cliente de ${ref}, em Emails: `
        + `${dayLabel(day.value)}, das ${start.value} às ${end.value}. Nada é enviado antes de as reveres. Continuar?`)) return;
    const result = await call('api/visits/propose', {property_ref: ref, day: day.value, start: start.value, end: end.value,
      emails, note: note.value, common});
    state = result.state; settings = result.settings;
    let drafted = false;
    if (common && (apiOnly() || settings.openai_configured)) {
      try {
        const generated = await call('api/visits/round-generate', {property_ref: ref});
        state = generated.state; applyFuel(generated.fuel, ref); drafted = true;
      } catch (error) { toast(`A ronda ficou preparada, mas o texto não foi gerado: ${error.message}`, 'warn'); }
    }
    roundScroll = common;
    renderState(); renderSettings();
    if (!common) toast(`${result.created} proposta(s) de visita na fila de Emails: ${apiOnly() ? 'gera-as com «Gerar respostas»' : 'prepara-as no ChatGPT ou via API'}, como as outras.`);
    else if (drafted) toast(`Rascunho da ronda pronto (${result.created} cliente(s)), logo abaixo: revê-o e depois «2 Enviar a todos». Nada foi enviado.`);
  }, event.currentTarget)}, startLabel());
  individual.addEventListener('change', () => { startButton.replaceChildren(...startLabel()); });
  const summaryBox = el('div', {class: 'round-summary'});
  const commonBox = el('div', {class: 'round-common'});
  const counts = el('details', {class: 'muted small round-counts', ontoggle: event => { roundCountsOpen = event.currentTarget.open; }});
  const loadSummary = () => run(async () => {
    roundCountsBox(counts, await call('api/visits/candidates', {property_ref: ref}));
    const data = await call('api/visits/round-summary', {property_ref: ref});
    summaryBox.replaceChildren(...roundSummaryContent(data, 10));  // 04/10: the first 10, the rest on a hover
    renderRoundCommon(commonBox, await call('api/visits/round', {property_ref: ref}), loadSummary, roundActions);
  });
  // 05/10: the whole width again, in two columns: what the round says on the left, «Agora: …», «Individualizar» and the
  // buttons on the right
  card(
    el('div', {class: 'round-layout'},
      el('div', {class: 'round-main'},
        el('p', {class: 'step'},
          // 05/10: the owner's own words
          'Um email a cada cliente ativo deste imóvel, a propor o dia e o intervalo e a perguntar a hora que lhe dá mais '
          + 'jeito dentro dele. Ficará um email por cliente preparado.'),
        el('div', {class: 'row'}, dateStepper(day), timeStepper(start, slot), timeStepper(end, slot)),
        note),
      // 05/10: «Agora: …» (who gets the invitation and who is left out) at the top of the right column
      el('div', {class: 'round-side'}, counts,
        el('label', {class: 'check'}, individual, ' Individualizar: uma resposta por cliente, em Emails'),
        el('div', {class: 'actions'}, startButton, roundActions))),
    commonBox, summaryBox);
  loadSummary();
}

// 29/09: the round with one text for everyone: generate it (API, or copy/paste), review the Portuguese and the English
// text, each customer's greeting and the short summaries in other languages, then send them all — each customer gets
// it in their own conversation. «Individualizar» takes one customer to Comunicações, to be answered on their own.
const ROUND_LANGS = {pt: 'português', en: 'inglês', es: 'espanhol'};  // 06/10: Spanish a text of its own
// 06/10: a language by its name, not its code («escreve em und» said nothing); «und» is no language: the AI could not tell
function langName(code) {
  if (!code || code === 'und') return '';
  try { return new Intl.DisplayNames(['pt-PT'], {type: 'language'}).of(code) || code; } catch { return ROUND_LANGS[code] || code; }
}
let roundScroll = false;  // after «Preparar o texto da ronda»: show the draft, right under the buttons
const roundOff = new Set();  // 06/10: the round's customers switched off (left out when the others are sent)
const stepNum2 = () => el('span', {class: 'step-num', 'aria-hidden': 'true'}, '2');
function renderRoundCommon(box, data, reload, actions) {
  actions.replaceChildren();
  if (!data.items?.length) { box.replaceChildren(); roundScroll = false; return; }
  const ref = data.property_ref, items = data.items, hasTexts = Object.keys(data.texts || {}).length > 0;
  const redraw = next => { state = next.state || state; renderState(); renderRoundCommon(box, next, reload, actions); };
  const count = lang => items.filter(item => item.language === lang).length;
  const texts = Object.fromEntries(Object.keys(ROUND_LANGS).filter(lang => data.texts?.[lang]).map(lang =>
    [lang, el('textarea', {rows: 12, 'aria-label': `Texto em ${ROUND_LANGS[lang]}`}, data.texts[lang])]));
  const summaries = Object.fromEntries(Object.entries(data.summaries || {}).map(([lang, text]) =>
    [lang, el('textarea', {rows: 4, 'aria-label': `Resumo em ${lang}`}, text)]));
  const common = () => ({texts: Object.fromEntries(Object.entries(texts).map(([lang, box]) => [lang, box.value])),
    summaries: Object.fromEntries(Object.entries(summaries).map(([lang, box]) => [lang, box.value])),
    // 06/10: each customer's greeting as the AI wrote it (no box to change it any more: the name is what it is)
    clients: Object.fromEntries(items.map(item => [item.id, {language: item.language, lang: item.lang, greeting: item.greeting || ''}]))});
  const save = () => call('api/visits/round-save', {property_ref: ref, window_id: data.window_id, common: common()});
  const promptText = el('pre', {}, '');
  const promptBox = el('details', {class: 'copy-only prompt-view'}, el('summary', {class: 'muted small'}, 'Prompt da ronda'), promptText);
  const pasted = el('textarea', {class: 'copy-only', rows: 4, placeholder: 'Cola aqui a resposta do ChatGPT (o bloco JSON).',
    'aria-label': 'Resposta colada'});
  const span = data.window || {};
  box.replaceChildren(el('div', {class: 'round-common-body'},
    el('h3', {}, 'Ronda com texto comum'),
    el('p', {class: 'muted small'}, `${dayLabel(span.day)}, das ${span.start} às ${span.end} · ${items.length} cliente(s) por enviar`),
    span.note && el('p', {class: 'step'}, el('strong', {}, 'Conhecimento desta ronda: '), span.note),
    el('div', {class: 'actions'},
      el('button', {class: (hasTexts ? '' : 'primary ') + 'needs-fuel', 'data-ref': ref,
        title: settings.openai_configured ? '' : 'Sem chave OpenAI configurada: o clique explica como.',
        onclick: event => run(async () => {
          if (hasTexts && !confirm('O texto é escrito de novo pela IA e perdes o que alteraste. Continuar?')) return;
          const result = await call('api/visits/round-generate', {property_ref: ref});
          applyFuel(result.fuel, ref); redraw(result);
          toast('Texto comum pronto: revê-o abaixo antes de enviar.');
        }, event.currentTarget)}, hasTexts ? 'Gerar de novo' : (apiOnly() ? 'Gerar o texto comum' : 'Gerar o texto comum via API')),
      el('button', {class: 'copy-only', onclick: event => run(async () => {
        promptText.textContent = (await call('api/visits/round-prompt', {property_ref: ref})).prompt;
        await copyText(promptText.textContent, 'Prompt da ronda copiado: cola-o no ChatGPT e traz a resposta para a caixa abaixo.', promptBox);
      }, event.currentTarget)}, 'Copiar o prompt'),
      el('button', {class: 'copy-only', onclick: event => run(async () => {
        if (!pasted.value.trim()) throw new Error('Cola primeiro a resposta do ChatGPT.');
        redraw(await call('api/visits/round-paste', {property_ref: ref, text: pasted.value}));
        toast('Texto comum pronto: revê-o abaixo antes de enviar.');
      }, event.currentTarget)}, 'Usar a resposta colada')),
    promptBox, pasted,
    // 06/10: the Portuguese open, the other texts and the translations closed, each under its title
    Object.entries(texts).map(([lang, textarea]) => el('details', {class: 'round-text', open: lang === 'pt'},
      el('summary', {class: 'muted small'}, `Texto em ${ROUND_LANGS[lang]} (${count(lang)} cliente(s))`
        + (lang === 'en' ? ' — o completo e oficial para quem não escreve em português nem em espanhol' : '')), textarea)),
    Object.entries(summaries).map(([lang, textarea]) => el('details', {class: 'round-text'},
      el('summary', {class: 'muted small'}, `Tradução em «${lang}», a seguir ao texto em inglês (`
        + `${items.filter(item => item.lang === lang).length} cliente(s))`), textarea)),
    el('div', {class: 'client-list'}, items.map(item => el('div', {class: 'client-row'},
      // 06/10: on (sent) or off (left out of the round when the others go); all on at first
      el('label', {class: 'round-pick', title: 'Desliga para o deixar fora desta ronda'},
        el('input', {type: 'checkbox', checked: !roundOff.has(item.id), onchange: event => {
          if (event.target.checked) roundOff.delete(item.id); else roundOff.add(item.id);
          sendLabel();
        }}), el('span', {}, shortName(item.name) || item.email)),
      el('span', {class: 'tag' + (item.reply_status === 'error' ? ' warn' : ''), title: item.lang === 'und'
          ? 'Não há nenhuma mensagem escrita por este cliente nem bandeira no aviso do portal: a IA não sabe a língua dele '
            + '(«und», indeterminada) e manda-lhe o texto em inglês.' : ''},
        item.reply_status === 'error' ? `não saiu: ${item.reply_error || 'erro'}`
          : item.language ? (ROUND_LANGS[item.language] + (item.lang === 'und' ? ' · língua desconhecida'
            : item.lang && item.lang !== item.language ? ` · escreve em ${langName(item.lang)}` : ''))
          : 'sem texto'),
      el('button', {class: 'link', title: 'Tira-o da ronda: fica em Emails, para escreveres e enviares só a ele.',
        onclick: event => run(async () => {
          redraw(await call('api/visits/round-individual', {property_ref: ref, id: item.id}));
          toast(`${shortName(item.name) || item.email} passou para Emails.`);
        }, event.currentTarget)}, 'Individualizar'))))));
  const sendButton = el('button', {class: 'primary send-action', onclick: event => run(async () => {
        const saved = await save();
        const off = saved.items.filter(item => roundOff.has(item.id)).map(item => item.id);
        const ids = saved.items.map(item => item.id).filter(id => !off.includes(id));
        if (!ids.length) throw new Error('Liga pelo menos um cliente para enviar.');
        const check = await call('api/preview', {property_ref: ref, ids});
        const warned = check.replies.filter(reply => (reply.warnings || []).length).length;
        if (!confirm(`Enviar agora ${ids.length} email(s) reais, um a cada cliente ligado da ronda, na conversa de cada um?`
            + `\n\nPara: ${check.replies.map(reply => reply.to).join(', ')}`
            + (off.length ? `\n\n${off.length} desligado(s): ficam fora e saem da ronda, sem receber nada.` : '')
            + (warned ? `\n\n${warned} com avisos: vê-os em Emails antes, se quiseres.` : ''))) { redraw(saved); return; }
        const result = await call('api/send', {property_ref: ref, preview_token: check.preview_token, confirmed: true});
        const sent = result.results.filter(item => item.status === 'sent').length;
        if (sent) playSound('send');
        if (off.length) {
          await call('api/visits/round-cancel', {property_ref: ref, window_id: data.window_id, ids: off});
          off.forEach(id => roundOff.delete(id));
        }
        state = await call('api/state'); renderState(); reload();
        toast(`Ronda: enviados ${sent} de ${ids.length}.` + (off.length ? ` ${off.length} ficaram fora e saíram da ronda.` : '')
          + (sent < ids.length ? ' Os que não saíram continuam aqui, com o aviso.' : ''), sent === ids.length ? 'ok' : 'warn');
      }, event.currentTarget)});
  if (hasTexts) actions.replaceChildren(
      el('button', {onclick: event => run(async () => {
        redraw(await save()); toast('Alterações guardadas em todos os emails da ronda.');
      }, event.currentTarget)}, 'Guardar alterações'),
      sendButton);
  if (hasTexts) sendLabel();
  // 06/10: only the customers switched on go; those switched off leave the round afterwards (nothing sent to them)
  function sendLabel() {
    const on = items.filter(item => !roundOff.has(item.id)).length;
    sendButton.replaceChildren(stepNum2(), buttonIcon('mail'), on === items.length ? `Enviar a todos (${on})` : `Enviar a todos (${on} de ${items.length})`);
    sendButton.disabled = !on;
  }
  // 05/10: a round prepared by mistake (or for the wrong day) is cancelled here: its proposals leave, nothing is sent
  const roundWhen = data.window ? `${dayLabel(data.window.day)}, das ${data.window.start} às ${data.window.end}` : 'esta ronda';
  actions.append(el('button', {type: 'button', class: 'link danger', onclick: event => run(async () => {
    if (!confirm(`Cancelar a ronda de ${roundWhen}? As ${items.length} proposta(s) por enviar saem da fila e nada é enviado.`)) return;
    const result = await call('api/visits/round-cancel', {property_ref: ref, window_id: data.window_id});
    state = result.state; renderState(); reload();
    toast(`Ronda cancelada: ${result.cancelled} proposta(s) tirada(s) da fila, nada foi enviado.`);
  }, event.currentTarget)}, 'Cancelar esta ronda'));
  holdFuelButtons();
  if (roundScroll) { roundScroll = false; box.scrollIntoView({behavior: 'smooth', block: 'start'}); }
}

// Contactos: contactos.csv as a table. The filters run here (it is one small file); every change goes to the API.
let contactsData = {contacts: [], properties: [], rgpd_states: {}};
const fullDay = day => day ? day.split('-').reverse().join('/') : '—';

// The property menus list only ATIVO properties; Imóveis shows them all, with the switch.
function activeProperties() { return (settings?.properties || []).filter(property => property.active !== false); }

function fillSelect(select, options, first) {
  const chosen = select.value;
  select.replaceChildren(...(first ? [el('option', {value: ''}, first)] : []),
    ...Object.entries(options).map(([value, label]) => el('option', {value}, label)));
  if ([...select.options].some(option => option.value === chosen)) select.value = chosen;
}

// 04/10: a long address cut for the table: at most 20 characters before the @ and 20 after, «…» where it was cut (the
// whole address on the hover).
const EMAIL_PART = 20;
function shortEmail(email) {
  const text = String(email || ''), at = text.lastIndexOf('@');
  const cut = part => part.length > EMAIL_PART ? part.slice(0, EMAIL_PART - 1) + '…' : part;
  return at < 0 ? cut(text) : cut(text.slice(0, at)) + '@' + cut(text.slice(at + 1));
}
function contactRow(contact) {
  const nome = el('input', {value: contact.nome, 'aria-label': 'Nome'});
  const telefone = el('input', {value: contact.telefone, 'aria-label': 'Telefone'});
  // 04/10: the RGPD state only shown, as plain text (it changes by the consent emails, not here)
  const rgpd = el('span', {}, contactsData.rgpd_states[contact.rgpd] || contact.rgpd || '—');
  // The proof of a «sim» confirmed from an email is its Message-ID; one changed here says so itself.
  const proof = contact.rgpd_data && el('div', {class: 'muted small'},
    fullDay(contact.rgpd_data) + ' · ' + (contact.rgpd_prova.startsWith('<') ? 'por email' : contact.rgpd_prova || '—'));
  return el('tr', {},
    el('td', {}, nome), el('td', {class: 'email', title: contact.email}, shortEmail(contact.email)),
    // 04/10: «Respostas» right after the email, a little wider (the count and «inativo» side by side)
    el('td', {class: 'replies-cell'}, String(contact.interactions),
      contact.inactive && el('span', {class: 'tag warn', title: 'O 4.º email nosso seguido ficou 2 dias úteis sem resposta: sai das '
        + 'rondas e dos lembretes até voltar a escrever.'}, 'inativo'),
      // 06/10: a step before: still in the rounds and the reminders, only marked
      contact.absent && !contact.inactive && el('span', {class: 'tag draft', title: 'O 3.º email nosso seguido ficou 48 horas '
        + 'sem resposta: continua nas rondas e nos lembretes; ao 4.º sem resposta, 2 dias úteis depois, fica inativo.'}, 'ausente')),
    el('td', {}, telefone),
    el('td', {class: 'nowrap'}, fullDay(contact.primeiro_contacto)),  // 04/10: the property is the group's title, above
    el('td', {}, rgpd, proof),
    el('td', {class: 'actions-cell'},
      el('button', {onclick: event => run(async () => {
        contactsData = await call('api/contacts/save', {contact: {...contact, nome: nome.value, telefone: telefone.value}});
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

// Customer files (26/09): what the qualification gathered, per property, a few at a time above the full list.
const FICHA_LABELS = {trabalho: 'Situação profissional e rendimentos', agregado: 'Agregado familiar',
  datas: 'Datas ou duração do contrato', disponibilidade: 'Disponibilidade para visitas', empresa: 'Empresa',
  animais: 'Animais'};
// No (valid) Reply-To on a portal notice (26/09): the recipient comes from the notice's body, or none; the owner
// confirms it or types another here.
function recipientEditor(email) {
  const input = el('input', {type: 'email', value: email.recipient?.email || '', placeholder: 'email do cliente',
    'aria-label': 'Destinatário'});
  return el('div', {class: 'row recipient-edit'}, el('span', {class: 'muted small'}, 'Destinatário'), input,
    el('button', {type: 'button', onclick: event => run(async () => {
      const result = await call('api/recipient', {property_ref: queueRef(), id: email.id, email: input.value});
      state = result.state; keepSteps(renderState); toast(`Destinatário: ${input.value.trim()}.`);
    }, event.currentTarget)}, email.recipient ? 'Mudar destinatário' : 'Usar este destinatário'));
}

// The draft as it goes to WhatsApp (26/09): the email's «🏠 Apartamento T3 … — link» line reads oddly in a chat, so it
// joins the greeting — «Cara Ana, relativo ao seu contacto via Idealista do T3 … — link». The email itself is unchanged.
function whatsappText(text) {
  text = String(text || '');
  const portal = /idealista\./i.test(text) ? 'Idealista' : '';
  // The phrase follows the greeting's language (the voice writes in the customer's): English, French, Spanish or Portuguese.
  const first = (text.trim().split(/[\s,]+/)[0] || '').toLowerCase();
  const phrase = /^(dear|hello|hi|good)$/.test(first) ? `regarding your enquiry${portal ? ' via ' + portal : ''} about the `
    : /^(bonjour|cher|chère|madame|monsieur)$/.test(first) ? `concernant votre demande${portal ? ' via ' + portal : ''} pour le `
    : /^(estimado|estimada|hola|buenos|buenas)$/.test(first) ? `en relación con su contacto${portal ? ' vía ' + portal : ''} sobre el `
    : `relativo ao seu contacto${portal ? ' via ' + portal : ' pelo portal'} do `;
  const type = '(?:(?:Apartamento|Moradia|Casa|Estúdio|Quarto)\\s+)?';
  return text
    .replace(new RegExp(`,[ \\t]*\\n+[ \\t]*🏠\\s*${type}`, 'u'), ', ' + phrase)
    .replace(new RegExp(`^[ \\t]*🏠\\s*${type}`, 'mu'), phrase.charAt(0).toUpperCase() + phrase.slice(1));
}


// A phone as WhatsApp wants it: digits with the country code; a Portuguese 9-digit number gets +351.
function whatsappNumber(phone) {
  let digits = String(phone || '').replace(/\D/g, '');
  if (digits.startsWith('00')) digits = digits.slice(2);
  if (digits.length === 9 && /^[29]/.test(digits)) digits = '351' + digits;
  return digits.length >= 10 ? digits : '';
}
// 05/10: «dados N/M», coloured by how much came in: red nothing yet, yellow halfway, green complete (as the dots)
function fichaTag(summary) {
  if (!summary) return false;
  const missing = summary.falta.map(key => FICHA_LABELS[key] || key).join(', ');
  return el('span', {class: 'tag ' + (summary.complete ? 'data-full' : summary.known ? 'data-some' : 'data-none'),
    title: summary.complete ? 'Dados completos: pronto para proposta de visita.' : 'Falta: ' + missing},
    `dados ${summary.known}/${summary.total}`);
}

let fichasPage = 0;
function fichasPerPage() {  // 05/10: always 3 side by side (it was 3 to 5, as the width fitted)
  return 3;
}
// 05/10: a long text kept to a few lines, «…» at the end; a click opens it whole and another closes it again
const CLAMP_HINT = 'Carrega para ver tudo (ou para encolher)';
function clampClass(lines) { return `clamp clamp-${lines}`; }
document.addEventListener('click', event => {
  const box = event.target.closest('.clamp');
  if (box && !event.target.closest('a, button, input, select, textarea')) box.classList.toggle('open');
});
function fichaCard(item) {
  const optional = ['empresa', 'animais'].filter(key => item.ficha[key] || item.falta.includes(key));
  const rows = ['trabalho', 'agregado', 'datas', 'disponibilidade', ...optional].flatMap(key => [
    el('dt', {}, FICHA_LABELS[key]),
    // 05/10: known, dark green; at most 3 lines (5 for the work and income), «…» opening the rest on a click
    el('dd', {class: item.ficha[key] ? 'ficha-known ' + clampClass(key === 'trabalho' ? 5 : 3) : 'ficha-missing',
      title: item.ficha[key] ? CLAMP_HINT : null}, item.ficha[key] || 'falta')]);
  return el('article', {class: 'ficha-card'},
    el('div', {class: 'card-head'}, el('strong', {}, shortName(item.name) || item.email),
      fichaTag({falta: item.falta, complete: item.complete, known: item.known, total: item.total})),
    el('div', {class: 'muted small'}, [item.phase, item.pending && 'email por responder',
      item.last && 'última troca ' + when(item.last)].filter(Boolean).join(' · ')),
    el('div', {class: 'muted small ficha-email'}, item.email),
    el('dl', {}, rows),
    profileImport(item),
    el('div', {class: 'actions'}, shortlistToggle(item.selection, shortName(item.name) || item.email,
      status => selectionCall('set', item, {status}))));
}

// «Colar perfil do Idealista»: the tenant profile lives behind «Ver perfil» on the portal, never in the email.
function profileImport(item) {
  const text = el('textarea', {rows: 4, 'aria-label': 'Perfil do Idealista', placeholder: 'Abre «Ver perfil» no Idealista, seleciona o perfil, copia e cola aqui'});
  return el('details', {class: 'profile-import'}, el('summary', {class: 'muted small'}, 'Colar perfil do Idealista'), text,
    el('div', {class: 'actions'}, el('button', {type: 'button', class: 'needs-fuel', 'data-ref': item.property_ref, onclick: event => run(async () => {
      const result = await call('api/fichas/import', {property_ref: item.property_ref, email: item.email, text: text.value});
      contactsData = result; applyFuel(result.fuel, item.property_ref); renderContacts();
      toast('Ficha preenchida com o perfil: revê o que a API tirou de lá.', 'warn');
    }, event.currentTarget)}, 'Preencher a ficha')));
}

// RGPD (26/09): contacts without consent past 6 months, listed; erased only when the owner confirms.
function renderExpired() {
  const expired = contactsData.expired || [];
  $('contacts-expired').hidden = !expired.length;
  $('contacts-expired').replaceChildren(...(expired.length ? [
    el('span', {}, `${expired.length} contacto(s) sem consentimento com mais de 6 meses: `
      + expired.slice(0, 8).map(item => `${shortName(item.name)} (${item.imovel})`).join(', ') + (expired.length > 8 ? '…' : '') + '. '),
    el('button', {type: 'button', class: 'link danger', onclick: event => run(async () => {
      if (!confirm(`Apagar de vez ${expired.length} contacto(s), com as conversas, fichas e visitas? Não se pode desfazer.`)) return;
      const result = await call('api/contacts/purge', {});
      contactsData = result; state = result.state; renderState(); renderContacts();
      toast(`${result.purged} contacto(s) apagado(s) (RGPD).`);
    }, event.currentTarget)}, 'Apagar agora')] : []));
}

// The short list (26/09): one column per candidate, with what the decision needs. Every change reloads Contactos.
async function selectionCall(action, item, extra, message) {
  const result = await call('api/selection/' + action, {property_ref: item.property_ref, email: item.email, ...extra});
  contactsData = result; if (result.state) { state = result.state; renderState(); }
  renderContacts(); if (message) toast(message);
  return result;
}
const SCORE_LABELS = {imovel: 'imóvel', consultor: 'consultor', marcacao: 'marcação'};
// «Escolher» is the one decision that ends the search (26/09): an emergency button behind a striped safety guard. The first
// click lifts the guard (armed: red, pulsing, «Confirmar»); the second chooses. Left armed, it closes again after 6 s.
function ejectChoose(item) {
  const name = shortName(item.name) || item.email;
  const guard = el('span', {class: 'eject-guard'});
  let timer = null;
  const disarm = () => { clearTimeout(timer); guard.classList.remove('armed'); guard.replaceChildren(closed()); };
  const closed = () => el('button', {type: 'button', class: 'eject', title: 'Selecionar o inquilino: carrega para levantar a tampa',
    onclick: () => {
      guard.classList.add('armed');
      guard.replaceChildren(
        el('button', {type: 'button', class: 'eject armed', onclick: event => run(async () => {
          clearTimeout(timer);
          await selectionCall('set', item, {status: 'chosen'}, `${name} está selecionado(a).`);
        }, event.currentTarget)}, `Confirmar: selecionar ${name}`),
        el('button', {type: 'button', class: 'link eject-cancel', onclick: disarm}, 'cancelar'));
      timer = setTimeout(disarm, 6000);
    }}, 'Selecionar');
  guard.append(closed());
  return guard;
}

const docsOpen = new Set();  // 05/10: whose «DOCUMENTOS» is open, kept while the page redraws
function selectionColumn(item) {
  const docs = item.documents, labels = contactsData.documents || {};
  const tick = (who, key) => el('label', {class: 'doc-tick'},
    el('input', {type: 'checkbox', checked: !!docs.received[`${who}:${key}`], onchange: event => run(() =>
      selectionCall('doc', item, {document: `${who}:${key}`, received: event.target.checked}))}), labels[key]);
  const visit = item.visit, survey = item.survey;
  return el('article', {class: 'selection-column ' + item.status},
    el('div', {class: 'card-head'}, el('strong', {}, shortName(item.name) || item.email),
      el('span', {class: 'tag ' + (item.status === 'chosen' ? 'golden' : item.status === 'suplente' ? 'visit' : 'silver')}, item.label),
      // 05/10: in the card's top right corner (it was at the foot, on the left)
      el('button', {type: 'button', class: 'link danger selection-out', onclick: event => run(() =>
        selectionCall('set', item, {status: null}, 'Saiu da short list.'), event.currentTarget)}, 'Tirar da short list')),
    el('div', {class: 'muted small ficha-email'}, item.email),
    el('p', {class: 'eyebrow'}, 'FICHA'),
    el('dl', {}, ['trabalho', 'agregado', 'datas', 'disponibilidade', 'empresa', 'animais']
      .filter(key => item.ficha[key] || ['trabalho', 'agregado', 'datas'].includes(key))
      .flatMap(key => [el('dt', {}, FICHA_LABELS[key]), el('dd', {class: item.ficha[key] ? clampClass(key === 'trabalho' ? 5 : 3)
        : 'ficha-missing', title: item.ficha[key] ? CLAMP_HINT : null}, item.ficha[key] || 'falta')])),
    el('p', {class: 'eyebrow'}, 'VISITA'),
    el('p', {class: 'small'}, visit.at ? `${slotLabel(visit.at)} · ${visit.attended === true ? 'veio' : visit.attended === false ? 'não veio' : 'por registar'}` : 'Sem visita marcada.'),
    visit.private && el('p', {class: 'small ' + clampClass(3), title: CLAMP_HINT}, el('span', {class: 'muted'}, 'Nota privada: '), visit.private),
    visit.public && el('p', {class: 'small ' + clampClass(3), title: CLAMP_HINT}, el('span', {class: 'muted'}, 'Nota pública: '), visit.public),
    el('p', {class: 'eyebrow'}, 'INQUÉRITO'),
    el('p', {class: 'small' + (survey ? ' ' + clampClass(3) : ''), title: survey ? CLAMP_HINT : null}, survey ? Object.entries(SCORE_LABELS).map(([key, label]) => `${label} ${survey[key] ?? '–'}`).join(' · ')
      + (survey.interesse ? ` · interesse: ${survey.interesse}` : '') + (survey.comentario ? ` · «${survey.comentario}»` : '') : 'Sem resposta.'),
    // 05/10: «DOCUMENTOS» opens and closes (closed at first), the ticks and the buttons
    // («Pedir documentos», «Selecionar», «Suplente») inside; no limit of lines
    el('details', {class: 'docs-box', open: docsOpen.has(item.email),
      ontoggle: event => { if (event.currentTarget.open) docsOpen.add(item.email); else docsOpen.delete(item.email); }},
      // 05/10: the title says what is inside: «DOCUMENTOS · Pedir, Selecionar, Suplente» (the actions this candidate has);
      // on its line, at the right, a pill with what is missing (or that they are complete)
      el('summary', {class: 'docs-summary'},
        el('span', {class: 'eyebrow'}, foldMark(), 'DOCUMENTOS · ' + ['Pedir', item.status !== 'chosen' && 'Selecionar',
          item.status !== 'suplente' && 'Suplente'].filter(Boolean).join(', ')),
        el('span', {class: 'tag docs-state ' + (docs.complete ? 'data-full' : Object.values(docs.received || {}).some(Boolean)
          ? 'data-some' : 'data-none')}, docs.complete ? 'Documentos completos'
          : 'Falta: ' + docs.missing.join(', ').toLowerCase())),
      el('div', {class: 'doc-list'}, Object.keys(labels).map(key => tick('candidato', key))),
      el('label', {class: 'doc-tick'}, el('input', {type: 'checkbox', checked: docs.fiador, onchange: event => run(() =>
        selectionCall('doc', item, {fiador: event.target.checked}))}), 'Tem fiador'),
      docs.fiador && el('div', {class: 'doc-list fiador'}, el('span', {class: 'muted small'}, 'Do fiador:'),
        Object.keys(labels).map(key => tick('fiador', key))),
      el('div', {class: 'actions'},
        el('button', {type: 'button', onclick: event => run(async () => {
          const result = await selectionCall('request', item, {});
        toast(result.attached ? 'O pedido dos documentos que faltam vai na resposta ao email deste cliente que já está em '
          + 'Emails («Só para esta resposta»): gera-a, revê e envia.' : 'Pedido de documentos em Emails: gera-o, revê e envia.');
        }, event.currentTarget)}, item.docs_requested_at ? 'Pedir de novo' : 'Pedir documentos'),
        item.status !== 'chosen' && ejectChoose(item),
        item.status !== 'suplente' && el('button', {type: 'button', onclick: event => run(() =>
          selectionCall('set', item, {status: 'suplente'}, `${shortName(item.name) || item.email} fica como suplente.`), event.currentTarget)}, 'Suplente'))));
}
// 05/10: one candidate, the whole width; two, half each; three or more, three a page with «Anteriores» and «Seguintes»
let selectionPage = 0;
function renderSelection(ref, inactive) {
  const board = (contactsData.selection || []).filter(item => ref ? item.property_ref === ref : !inactive.has(item.property_ref));
  const size = 3, pages = Math.max(1, Math.ceil(board.length / size));
  selectionPage = Math.min(selectionPage, pages - 1);
  const shown = board.slice(selectionPage * size, selectionPage * size + size);
  $('shortlist-count').replaceChildren(el('strong', {}, !board.length ? 'vazia'
    : pages > 1 ? `${selectionPage * size + 1}–${selectionPage * size + shown.length} de ${board.length} candidatos`
    : `${board.length} candidato${board.length === 1 ? '' : 's'}`));
  $('selection-board').style.setProperty('--selection-columns', Math.max(1, Math.min(size, board.length)));
  $('selection-board').replaceChildren(...(board.length ? shown.map(selectionColumn)
    : [el('p', {class: 'muted small'}, 'A short list está vazia: junta 2 ou 3 clientes com «+ Short list» nas fichas abaixo.')]));
  $('selection-pager').hidden = pages <= 1;
  $('selection-prev').disabled = selectionPage === 0;
  $('selection-next').disabled = selectionPage >= pages - 1;
}
$('selection-prev').addEventListener('click', () => { selectionPage--; renderFichas(); });
$('selection-next').addEventListener('click', () => { selectionPage++; renderFichas(); });
function renderFichas() {
  const inactive = new Set(contactsData.inactive || []);
  const refs = contactsData.properties.filter(ref => !inactive.has(ref));
  const select = $('fichas-property');
  // 05/10: no «Todos»: one property at a time (it is managed there)
  fillSelect(select, Object.fromEntries(refs.map(ref => [ref, ref])));
  if (!select.dataset.touched && refs.length > 1 && !select.value) select.value = refs[0];
  renderSelection(select.value, inactive);
  const all = (contactsData.fichas || []).filter(item => select.value ? item.property_ref === select.value
    : !inactive.has(item.property_ref));
  const size = fichasPerPage(), pages = Math.max(1, Math.ceil(all.length / size));
  fichasPage = Math.min(fichasPage, pages - 1);
  const shown = all.slice(fichasPage * size, fichasPage * size + size);
  // 05/10: one customer, the whole width; two, half each; three or more, three a page with «Anteriores» and «Seguintes»
  $('fichas-list').style.setProperty('--fichas-columns', Math.max(1, Math.min(size, all.length)));
  $('fichas-list').replaceChildren(...(shown.length ? shown.map(fichaCard)
    : [el('p', {class: 'muted small'}, 'Ainda não há fichas: enchem-se a cada resposta preparada pela IA.')]));
  // 05/10: «1–3 de 15 clientes», in bold
  $('fichas-count').replaceChildren(el('strong', {}, all.length
    ? `${fichasPage * size + 1}–${fichasPage * size + shown.length} de ${all.length} cliente${all.length === 1 ? '' : 's'}` : '0'));
  $('fichas-prev').disabled = fichasPage === 0;
  $('fichas-next').disabled = fichasPage >= pages - 1;
  $('fichas-pager').hidden = pages <= 1;  // 05/10: only when there is more than one page, «2 de 5» between the buttons
  $('fichas-page').textContent = `${fichasPage + 1} de ${pages}`;
}
$('fichas-property').addEventListener('change', event => { event.target.dataset.touched = '1'; fichasPage = 0; selectionPage = 0; renderFichas(); });
$('fichas-prev').addEventListener('click', () => { fichasPage--; renderFichas(); });
$('fichas-fill').addEventListener('click', event => run(async () => {
  const ref = $('fichas-property').value || null;
  const result = await call('api/fichas/fill', {property_ref: ref});
  contactsData = result; renderContacts();
  toast(result.fill.map(item => item.skipped ? `${item.property_ref}: ${item.skipped}`
    : `${item.property_ref}: ${item.filled} ficha(s) preenchida(s) de ${item.asked} cliente(s)`).join(' · ') || 'Nada a preencher.');
}, event.currentTarget));
$('fichas-next').addEventListener('click', () => { fichasPage++; renderFichas(); });

const contactsOpen = new Set();  // 06/10: the groups whose «Mais N…» line is open: "<ref>|active" or "<ref>|inactive"
function renderContacts() {
  renderExpired();
  renderFichas();
  const inactive = new Set(contactsData.inactive || []);
  const properties = Object.fromEntries(contactsData.properties.filter(ref => !inactive.has(ref)).map(ref => [ref, ref]));
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
  // 04/10: no «Imóvel» column: the contacts grouped by property, its reference (and description) as the group's title
  const groups = new Map();
  for (const contact of shown) groups.set(contact.imovel || '', [...(groups.get(contact.imovel || '') || []), contact]);
  const title = (ref, list) => el('tr', {class: 'contacts-group'}, el('th', {colspan: 7, scope: 'colgroup'},
    ref || 'Sem imóvel', el('span', {class: 'contacts-group-about'},
      [settings?.properties?.find(property => property.reference === ref)?.description, `${list.length} contacto(s)`,
        list.some(contact => contact.inactive) && `${list.filter(contact => contact.inactive).length} inativo(s)`]
        .filter(Boolean).join(' · '))));
  // 06/10: in each property the active first and the inactive at the end; of the active the first 20 and of the inactive
  // the first 5, the rest behind a line that opens (kept open while the page redraws). A search shows everything found.
  const part = (ref, people, kind, limit, words) => {
    const key = `${ref}|${kind}`, open = text || contactsOpen.has(key), rest = people.length - limit;
    const rows = people.map((contact, index) => {
      const row = contactRow(contact);
      if (index >= limit && !open) row.hidden = true;
      return row;
    });
    if (rest > 0 && !text) rows.push(el('tr', {class: 'contacts-more'}, el('td', {colspan: 7},
      el('button', {type: 'button', class: 'link', 'aria-expanded': String(open), onclick: () => {
        if (open) contactsOpen.delete(key); else contactsOpen.add(key);
        renderContacts();
      }}, open ? `▾ Esconder os últimos ${rest} ${words[rest === 1 ? 0 : 1]}` : `▸ Mais ${rest} ${words[rest === 1 ? 0 : 1]}`))));
    return rows;
  };
  const groupRows = (ref, list) => [title(ref, list),
    ...part(ref, [...list.filter(contact => !contact.inactive && !contact.absent),
      ...list.filter(contact => !contact.inactive && contact.absent)], 'active', 20, ['cliente ativo', 'clientes ativos']),
    ...part(ref, list.filter(contact => contact.inactive), 'inactive', 5, ['inativo', 'inativos'])];
  $('contacts-body').replaceChildren(...(shown.length ? [...groups].flatMap(([ref, list]) => groupRows(ref, list))
    : [el('tr', {}, el('td', {colspan: 7, class: 'muted'}, contactsData.contacts.length
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

// «Modo: só API» (26/09): on unless config.json says otherwise; the ChatGPT copy/paste stays in the page, hidden.
function apiOnly() { return (settings?.ai?.mode ?? 'api') === 'api'; }
// The engines on offer (27/09): each one's own name, short (the car-like modes, TURBO and the like, come later with
// the themes), its family's colour and how strong it writes (1 to 5, indicative). A model not listed here still gets a
// button, plain. Every model with a confirmed price is here; the values get tuned as they are used.
const ENGINE_MODES = {
  'gpt-4.1-nano': {mode: '4.1 NANO', tone: 'g41', power: 1, note: 'O mais barato: para textos curtos e simples.'},
  'gpt-4o-mini': {mode: '4o MINI', tone: 'g4o', power: 2, note: 'Rápido e barato: o de partida.'},
  'gpt-6-luna': {mode: '6 LUNA', tone: 'luna', power: 3, note: 'Geração 6, a mais leve: mais barato que o 4o mini.'},
  'gpt-4.1-mini': {mode: '4.1 MINI', tone: 'g41', power: 3, note: 'Geração 4.1, gama pequena.'},
  'gpt-4.1': {mode: '4.1', tone: 'g41', power: 4, note: 'Geração 4.1, completo.'},
  'gpt-4o': {mode: '4o', tone: 'g4o', power: 4, note: 'Escreve e percebe melhor que o 4o mini; custa bastante mais.'},
  'gpt-5.6-terra': {mode: '5.6 TERRA', tone: 'terra', power: 4, note: 'Geração 5.6, gama média (preço talvez promocional).'},
  'gpt-6-sol': {mode: '6 SOL', tone: 'sol', power: 5, note: 'Geração 6, o do dia a dia mais forte, ao preço do 4o.'},
  'gpt-6-astra': {mode: '6 ASTRA', tone: 'astra', power: 5, note: 'Geração 6, o topo: cinco vezes o preço do 6 sol.'}};
// The client price: to the cent, and from 0,50 € to the nearest 5 cents, a round number to quote (27/09: 1,77 → 1,75).
const clientPrice = value => value >= 0.5 ? Math.round(value * 20) / 20 : Math.round(value * 100) / 100;
function engineConsole() {
  const ai = settings.ai || {models: []}, basis = ai.cost_basis || {};
  // Prices as OpenAI writes them (27/09): dollars with a point, two decimals, per 1M tokens
  const official = value => '$' + value.toFixed(2);
  const box = el('div', {class: 'engine-console voice-section'});
  const readout = (label, value) => el('span', {class: 'engine-readout'}, el('b', {}, label), ' ', value);
  const draw = () => {
    const current = settings.ai || ai;
    const button = model => {
      const info = ENGINE_MODES[model.id] || {mode: 'MODELO', tone: 'plain', power: 0, note: ''};
      const active = model.id === current.model;
      return el('button', {type: 'button', class: 'engine-button' + (active ? ' active' : '') + ' mode-' + info.tone,
        'aria-pressed': String(active), title: info.note, onclick: event => run(async () => {
          if (active) return;
          settings.ai = await call('api/ai/model', {model: model.id});
          applyAiMode(); draw();
          toast(`Motor ${info.mode}: ${settings.ai.model}. Vale para as respostas, a agenda, a análise e os anúncios.`);
        }, event.currentTarget)},
        el('span', {class: 'engine-top'}, el('span', {class: 'engine-mode'}, info.mode),
          el('span', {class: 'engine-led'}, active ? 'ATIVO' : 'EM ESPERA')),
        el('span', {class: 'engine-model'}, model.id),
        el('span', {class: 'engine-meter', 'aria-hidden': 'true'},
          [1, 2, 3, 4, 5].map(step => el('i', {class: step <= info.power ? 'on' : ''}))),
        el('span', {class: 'engine-prices'}, `Input ${official(model.input_usd_per_1m)} · Output ${official(model.output_usd_per_1m)} / 1M tokens`),
        el('span', {class: 'engine-quote'}, model.per_100_eur != null
          ? `≈ ${eurFormat.format(clientPrice(model.per_100_eur))} / 100 interações` : 'sem uso ainda para calcular'),
        info.note && el('span', {class: 'engine-note'}, info.note));
    };
    box.replaceChildren(
      el('div', {class: 'engine-head'},
        el('span', {class: 'engine-title'}, 'AI ENGINE'),
        el('span', {class: 'engine-status'}, el('i', {}), apiOnly() ? 'MODO: SÓ API' : 'MODO: COPIAR/COLAR + API')),
      el('div', {class: 'engine-grid'}, (current.models || []).filter(model => !model.hidden)  // 02/10: on offer only
        .sort((a, b) => (ENGINE_MODES[a.id]?.power ?? 9) - (ENGINE_MODES[b.id]?.power ?? 9)
          || a.input_usd_per_1m - b.input_usd_per_1m).map(button)),  // weakest and cheapest first
      // 27/09: what the «/ 100 interações» stands on, as readouts: the sample, the margin and the exchange rate
      basis.usd_per_eur ? el('div', {class: 'engine-readouts'},
        readout('AMOSTRA', basis.interactions ? `${basis.interactions} emails desde ${fullDay(basis.since).slice(0, 5)}` : 'sem uso ainda'),
        basis.interactions ? readout('MÉDIA', `${Math.round(basis.prompt_tokens / basis.interactions).toLocaleString('pt-PT')} in · `
          + `${Math.round(basis.completion_tokens / basis.interactions).toLocaleString('pt-PT')} out tokens`) : null,
        readout('MARGEM', `+${Math.round(basis.margin * 100)}%`),
        readout('CÂMBIO', `1 € = ${String(basis.usd_per_eur).replace('.', ',')} US$ · ${fullDay(basis.rate_date).slice(0, 5)}`)) : null,
      el('p', {class: 'engine-basis'}, '«/ 100 interações» é o que 100 emails custam aqui, em média, com a margem e em euros, '
        + 'arredondado para propor ao cliente (os emails escritos por ti no Gmail não contam). O custo de cada chamada conta '
        + 'no depósito do imóvel.'));
  };
  draw();
  return box;
}

function applyAiMode() {
  document.body.classList.toggle('api-only', apiOnly());
  // The workflow's steps are numbered as shown: Selecionar, Gerar, Rever e enviar with the API.
  [...document.querySelectorAll('.workflow li')].filter(li => getComputedStyle(li).display !== 'none')
    .forEach((li, index) => { li.querySelector('.num').textContent = String(index + 1).padStart(2, '0'); });
  $('send-step-label').textContent = apiOnly() ? 'PASSO 03' : 'PASSO 04';
  $('ai-model-label').textContent = 'API · ' + (settings?.ai?.model || '');
  $('generate-api').classList.toggle('primary', apiOnly());
}

// The property switcher of Imóveis (27/09), the same in Comunicações, Agenda and Contactos: big arrows, the reference,
// the description, the dots and «1 / 3». It drives the page's own <select> (kept, hidden), so every tab's logic stays
// as it was: a change here sets the select and fires its «change»; a select refilled or changed elsewhere redraws it.
const SWITCHERS = [];
function propertySwitcher(select) {
  const label = select.closest('label');
  const row = label?.parentElement;
  const box = el('div', {class: 'property-slider property-switcher', tabindex: '0', 'aria-label': 'Escolher o imóvel'});
  row.before(box);
  label.hidden = true;
  const go = index => {
    const options = [...select.options];
    if (!options.length) return;
    select.selectedIndex = (index + options.length) % options.length;
    select.dispatchEvent(new Event('change'));
  };
  const render = () => {
    const options = [...select.options], index = Math.max(0, select.selectedIndex), many = options.length > 1;
    const option = options[index];
    if (!option) return box.replaceChildren(el('span', {class: 'muted small'}, 'Sem imóveis.'));
    const ref = option.value, property = (settings?.properties || []).find(item => item.reference === ref);
    box.classList.toggle('test-property', !!property?.test);  // 02/10: the test property, in light purple
    const inactive = property?.active === false || /inativo/i.test(option.textContent);
    box.replaceChildren(...el('div', {},
      many && el('button', {type: 'button', class: 'slider-arrow prev', 'aria-label': 'Imóvel anterior', onclick: () => go(index - 1)}, '‹'),
      // 30/09: a title on the left, on a line of its own, like the other cards' («CAIXA DE CORREIO»)
      el('span', {class: 'eyebrow switcher-label'}, 'IMÓVEL'),
      el('div', {class: 'slider-title'},
        el('span', {class: 'property-ref'}, ref ? ref + (inactive ? ' · INATIVO' : '') : 'TODOS OS IMÓVEIS'),
        el('strong', {}, ref ? property?.description || option.textContent : 'Todos os imóveis, em conjunto'),
        many && el('div', {class: 'slider-dots'}, options.map((other, i) => el('button', {type: 'button',
          class: 'slider-dot' + (i === index ? ' active' : ''), 'aria-label': other.value || 'Todos', title: other.value || 'Todos',
          'aria-current': i === index ? 'true' : false, onclick: () => go(i)})),
          el('span', {class: 'muted small'}, `${index + 1} / ${options.length}`))),
      many && el('button', {type: 'button', class: 'slider-arrow next', 'aria-label': 'Imóvel seguinte', onclick: () => go(index + 1)}, '›')).childNodes);
  };
  box.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') go(select.selectedIndex - 1);
    if (event.key === 'ArrowRight') go(select.selectedIndex + 1);
  });
  select.addEventListener('change', render);
  select.addEventListener('change', () => shareProperty(select.value));  // 05/10: the same property in every tab
  new MutationObserver(render).observe(select, {childList: true});
  SWITCHERS.push(render);
  render();
}
for (const id of ['queue', 'agenda-property', 'fichas-property']) propertySwitcher($(id));

// 04/10: each page's title (where the old ones were, in the same type), with how many properties there are now (the
// active ones, the test property left out); the same in every theme.
function renderTitles() {
  const n = activeProperties().filter(property => !property.test).length;
  const of = (one, many) => n === 1 ? one : many.replace('{n}', n);
  const titles = {
    dashboard: 'Centro de Controlo e de Gestão — Dashboard Executivo',
    replies: `Leitura e Envio de emails aos clientes ${of('do Imóvel', 'dos {n} Imóveis')}`,
    contacts: `Sobre os Clientes que contactaram ${of('o nosso imóvel', 'um dos nossos ({n}) imóveis')}`,  // 05/10
    agenda: `Gestão das Visitas de Clientes ${of('ao Imóvel', 'aos {n} Imóveis')}`,
    properties: 'Gestão de todos os Imóveis',
    owners: `Centro de comunicação com os proprietários ${of('do imóvel', 'dos {n} imóveis')}`,
    workshop: 'Gestão Avançada do Sistema ARIA!'};
  for (const node of document.querySelectorAll('h1[data-title]')) node.textContent = titles[node.dataset.title] ?? node.textContent;
}
function renderSettings() {
  renderTitles();
  SWITCHERS.forEach(render => render());  // the descriptions come with the settings
  updateSkinPanels();
  applyAiMode();
  renderVoice();
  // 30/09: the agency's know-how in three — common to all, rentals only, sales only (they are handled very differently)
  $('agency-knowledge').replaceChildren(el('p', {class: 'eyebrow'}, 'KNOW-HOW DA AGÊNCIA ', kind('rag')),
    el('h2', {}, 'Conhecimento da agência'),
    el('p', {class: 'step'}, 'Cada imóvel recebe o comum e o do seu tipo de negócio (arrendamento ou venda, nos dados do imóvel); '
      + 'o do seu tipo vale sobre o comum, e o do próprio imóvel sobre os dois.'),
    ...[['agency', 'Comum a todos os imóveis'], ['agency-arrendamento', 'Só para arrendamentos'], ['agency-venda', 'Só para vendas'],
      ['owners', 'Para falar com proprietários (todos)']]
      .map(([scope, title]) => el('details', {class: 'knowledge-group', open: scope === 'agency'},
        el('summary', {}, title), knowledgeEditor(scope, null))));
  if (!$('f-first-read').value) $('f-first-read').value = settings.first_read_days || 45;
  renderPropertySlider();
  if (!$('f-sender').value) $('f-sender').value = settings.properties[0]?.sender || settings.portal_sender || 'reply@idealista.pt';
  $('generate-api').title = settings.openai_configured ? '' : 'Sem chave OpenAI configurada: o clique explica como.';
  $('api-hint').hidden = !!settings.openai_configured;
  $('api-hint').textContent = 'Sem chave OpenAI configurada ainda: corre mac/openai_key.command no terminal.';
  renderCalendar();
  renderVisitsRound();
  renderWorkshop();
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
  // 30/09: the property's prompts are edited in the Oficina (promptsCard)
  const link = /^https:\/\//.test(property.listing_url || '')
    && el('a', {href: property.listing_url, target: '_blank', rel: 'noopener noreferrer'}, property.listing_url);
  // Two columns on a wide screen: what the property is on the left, what is happening with it on the right.
  return el('article', {class: 'card property-slide'}, el('div', {class: 'property-identity'},
    propertyCover(property.reference, property.photo),
    el('div', {class: 'card-head'}, el('strong', {}, property.reference), el('span', {}, property.description || ''),
      property.advertised_rent_eur != null && el('span', {class: 'tag'}, property.advertised_rent_eur + ' €'),
      el('span', {class: property.active === false ? 'tag warn' : 'tag draft'}, property.active === false ? 'INATIVO' : 'ATIVO')),
    el('div', {class: 'muted small'}, [property.sender, property.listing_id && 'anúncio ' + property.listing_id,
      property.knowledge_files.length ? 'conhecimento: ' + property.knowledge_files.join(', ') : 'base de conhecimento vazia']
      .filter(Boolean).join(' · ')),
    link,
    knowledgeDetails(property.reference),
    el('button', {class: 'link', onclick: () => openPropertyEditor(property, property.reference)}, 'Editar dados do anúncio'),
    activeSwitch(property)),
    el('div', {class: 'property-operations'},
      surveyReport(property),
      activeClientsList(property),
      callsList(property),
      rebuildPanel(property),
      analysisPanel(property),
      visitsPanel(property)));
}

// ATIVO / INATIVO: an inactive property leaves the property menus (Respostas, Agenda, Contactos, ronda de
// visitas) but stays here with everything it has; switching back brings it all back.
function activeSwitch(property) {
  const active = property.active !== false;
  return el('button', {class: 'link', onclick: event => run(async () => {
    const result = await call('api/property/active', {reference: property.reference, active: !active});
    settings = result.settings; state = result.state;
    renderSettings(); renderState();
    toast(active ? `${property.reference} ficou inativo: sai dos menus, mas continua aqui.` : `${property.reference} está outra vez ativo.`);
  }, event.currentTarget)}, active ? 'Marcar como inativo' : 'Voltar a ativar');
}

// The property's survey report: the three dials and every answer, the bad ones first to catch the eye. 04/10: always
// open (its summary does not close it).
function surveyReport(property) {
  const report = property.survey_report;
  const summary = text => el('summary', {class: 'muted small', onclick: event => event.preventDefault()}, text);
  if (!report?.responses) return el('details', {class: 'visits-panel always-open', open: true},
    summary('Relatório dos inquéritos (0)'),
    report && qualityGauges(report, 'imovel:quality:' + property.reference, 'mini'),
    el('p', {class: 'muted small'}, 'Sem respostas ainda: o inquérito vai no agradecimento pós-visita.'));
  const answers = [...report.answers].sort((a, b) => (b.alerts.length > 0) - (a.alerts.length > 0));
  return el('details', {class: 'visits-panel always-open', open: true},
    summary(`Relatório dos inquéritos (${report.responses})` + (report.alerts ? ` · ${report.alerts} com alerta` : '')),
    qualityGauges(report, 'imovel:quality:' + property.reference, 'mini'),
    el('p', {class: 'muted small'}, `Continua interessado: sim ${report.interest.sim} · talvez ${report.interest.talvez} · não ${report.interest['não']}`),
    el('div', {class: 'client-list'}, answers.map(answer => el('div', {class: 'client-row survey-row'},
      el('span', {}, shortName(answer.name), el('span', {class: 'muted small'}, ' ' + when(answer.at))),
      el('span', {class: 'tag ' + (answer.alerts.length ? 'warn' : 'draft')},
        `imóvel ${answer.imovel ?? '–'} · consultor ${answer.consultor ?? '–'} · marcação ${answer.marcacao ?? '–'}`),
      answer.interest && el('span', {class: 'muted small'}, 'interesse: ' + answer.interest),
      answer.comment && el('span', {class: 'muted small survey-comment'}, '«' + answer.comment + '»')))));
}

function knowledgeDetails(ref) {
  const view = el('div', {});
  const show = () => view.replaceChildren(knowledgeEditor('property', ref));
  return el('details', {ontoggle: event => { if (event.target.open) show(); }},
    el('summary', {class: 'muted small'}, 'Conhecimento deste imóvel ', kind('rag')),
    view, noteBox(ref, show));
}

// The knowledge files as the owner wrote them: each one editable whole, and new ones can be added.
function knowledgeEditor(scope, ref, owner = null) {
  const box = el('div', {class: 'knowledge-editor'}, el('p', {class: 'muted small'}, 'A carregar…'));
  const load = () => run(async () => {
    const data = await call('api/knowledge', {property_ref: ref, owner});
    const save = (file, area, button) => run(async () => {
      const result = await call('api/knowledge/save', {scope, property_ref: ref, owner, file, text: area.value});
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
        : scope === 'agency-arrendamento' ? 'Só para os imóveis para arrendar: os imóveis à venda nunca o recebem.'
        : scope === 'agency-venda' ? 'Só para os imóveis à venda: os arrendamentos nunca o recebem.'
        : scope === 'owners' ? 'Como a agência fala com proprietários: o tom, o que se reporta e quando. Só nas respostas aos proprietários.'
        : scope === 'owner' ? 'Só deste proprietário: só nas respostas a ele.'
        : 'Só para este imóvel. O texto entre <!-- e --> fica para ti: não chega ao assistente.'),
      ...(files.length ? files.map(block) : [el('p', {class: 'muted small'}, 'Ainda não há ficheiros.')]),
      el('details', {}, el('summary', {class: 'muted small'}, '+ Novo ficheiro'), name, text,
        el('div', {class: 'actions'}, el('button', {onclick: event => save(name.value.trim(), text, event.currentTarget)}, 'Criar ficheiro'))));
  });
  load();
  return box;
}

const CLIENT_STATE_LABEL = {ok: 'ativo', pending: 'por responder', booked: 'visita marcada', closed: 'conversa fechada'};

// Persistent, not behind a click: everyone this property has written to, and where they stand — until
// the property closes (sold/rented/withdrawn is the same "Fechar visitas" event, not a separate state).
// 02/10: the portal's calls for this property — answered or not, when (the call's own time), the phone and, when the
// number is known, the customer — with WhatsApp, SMS and a call back. A call whose notice names no property and whose
// number is no customer's yet shows at the foot, in every property, until the number turns up.
function callsList(property) {
  const box = el('div', {class: 'calls-list'}, el('p', {class: 'eyebrow'}, 'CHAMADAS DO PORTAL'),
    el('p', {class: 'muted small'}, 'A carregar…'));
  const days = el('input', {type: 'number', min: 1, max: 365, value: 30, class: 'days-input', 'aria-label': 'Dias para trás'});
  const stamp = at => { const [day, clock] = String(at || '').split(' ');
    return day ? `${day.slice(8, 10)}/${day.slice(5, 7)} ${String(clock || '').slice(0, 5)}` : ''; };
  const row = item => el('div', {class: 'call-row' + (item.answered ? '' : ' missed')},
    el('span', {class: 'call-when'}, stamp(item.at)),
    el('span', {class: 'tag ' + (item.answered ? 'visit' : 'warn')}, item.answered
      ? 'atendida' + (item.seconds ? ` · ${item.seconds} s` : '') : 'não atendida'),
    el('strong', {}, shortName(item.name) || 'sem nome'),
    el('span', {class: 'muted small'}, item.phone_shown),
    el('span', {class: 'call-actions'},
      el('a', {class: 'link', href: `whatsapp://send?phone=${item.international}`}, 'WhatsApp'),
      el('a', {class: 'link', href: `sms:+${item.international}`}, 'SMS'),
      el('a', {class: 'link', href: `tel:+${item.international}`}, 'Ligar')));
  const draw = data => {
    const mine = data.calls.filter(item => item.property_ref === property.reference);
    // a notice naming a listing that is not in the ARIA (another of the agency's) is not «sem imóvel»: it is left out
    const loose = data.calls.filter(item => !item.property_ref && !item.ref);
    const missed = mine.filter(item => !item.answered).length;
    box.replaceChildren(el('p', {class: 'eyebrow'}, 'CHAMADAS DO PORTAL'),
      el('p', {class: 'muted small'}, mine.length ? `${mine.length} chamada(s), ${missed} não atendida(s).`
        : 'Ainda sem chamadas deste imóvel.' + (data.added === undefined ? ' As novas chegam com «Ler emails»; as antigas, com «Procurar».' : '')),
      ...mine.slice(0, 30).map(row),
      loose.length ? el('details', {class: 'calls-loose'}, el('summary', {class: 'muted small'},
        `${loose.length} chamada(s) sem imóvel identificado (o aviso não diz o imóvel e o número ainda não é de nenhum cliente)`),
        ...loose.slice(0, 30).map(row)) : null,
      el('div', {class: 'row calls-scan'}, el('span', {class: 'muted small'}, 'Procurar no Gmail as chamadas dos últimos'), days,
        el('span', {class: 'muted small'}, 'dias'),
        el('button', {onclick: event => run(async () => {
          const result = await call('api/calls/scan', {days: Number(days.value)});
          draw(result); toast(`${result.added} chamada(s) nova(s) encontrada(s) no Gmail.`);
        }, event.currentTarget)}, 'Procurar')));
  };
  run(async () => draw(await call('api/calls', {})));
  return box;
}

// 03/10: «Reconstruir a partir do Gmail»: after a loss, or to start from months of replies written by hand. Reads the
// Gmail twice N days back, then lists what is missing — visits, surveys, the short list, the queue tidied — each ticked
// to go in; nothing is sent.
function rebuildPanel(property) {
  const box = el('details', {class: 'rebuild-panel'}, el('summary', {class: 'eyebrow'}, 'RECONSTRUIR A PARTIR DO GMAIL'));
  const days = el('select', {'aria-label': 'Quantos dias para trás'},
    [30, 60, 90, 180].map(value => el('option', {value, selected: value === 60}, `últimos ${value} dias`)));
  const list = el('div', {class: 'rebuild-list'});
  const label = entry => entry.kind === 'visit' ? `Visita de ${shortName(entry.name)} a ${entry.at.slice(8, 10)}/${entry.at.slice(5, 7)} às ${entry.at.slice(11, 16)}`
      + (entry.at.slice(0, 10) < new Date().toLocaleDateString('sv-SE') ? ' (já passou: fica por registar)' : '')
    : entry.kind === 'survey' ? `Inquérito de ${shortName(entry.name)}: imóvel ${entry.survey?.imovel ?? '—'}, consultor ${entry.survey?.consultor ?? '—'}`
    : entry.kind === 'shortlist' ? `${shortName(entry.name)} na short list (${entry.status === 'chosen' ? 'selecionado' : entry.status === 'suplente' ? 'suplente' : 'short list'})`
    : `Tirar da fila ${entry.count} email(s) já respondidos no Gmail`;
  const source = entry => entry.source === 'marca' ? 'pela marca do email' : entry.source === 'ia' ? 'lido pela IA'
    : entry.source ? entry.source : '';
  const show = result => {
    const boxes = result.proposals.map(entry => ({entry, box: el('input', {type: 'checkbox', checked: true})}));
    list.replaceChildren(
      result.ai_error ? el('p', {class: 'alert warn'}, 'A leitura das visitas pela IA falhou: ' + result.ai_error) : null,
      boxes.length ? el('div', {}, boxes.map(({entry, box: tick}) => el('label', {class: 'check rebuild-entry'}, tick, ' ', label(entry),
        source(entry) && el('span', {class: 'muted small'}, ' · ' + source(entry)))),
        el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
          const ids = boxes.filter(item => item.box.checked).map(item => item.entry.id);
          const done = await call('api/rebuild/apply', {property_ref: property.reference, ids});
          state = done.state; settings = done.settings; renderSettings(); renderState();
          list.replaceChildren(el('p', {class: 'muted small'}, 'Feito: ' + (Object.entries(done.done).map(([kind, count]) =>
            `${count} ${{visit: 'visita(s)', survey: 'inquérito(s)', shortlist: 'na short list', tidy: 'fila arrumada'}[kind] || kind}`).join(', ') || 'nada') + '.'));
          toast('Reconstrução aplicada. Nada foi enviado.');
        }, event.currentTarget)}, 'Adicionar os marcados')))
        : el('p', {class: 'muted small'}, 'Nada em falta: o que o Gmail tem já está na ARIA.'));
  };
  box.append(el('p', {class: 'step'}, 'Lê o Gmail duas vezes, para trás, e mostra o que falta na ARIA: visitas, inquéritos, short list '
      + 'e emails já respondidos. Escolhes o que entra; nada é enviado. Serve depois de perder dados, ou para começar a partir '
      + 'de meses de respostas escritas à mão. Pode demorar alguns minutos.'),
    el('div', {class: 'row'}, days, el('button', {onclick: event => run(async () => {
      show(await call('api/rebuild/scan', {property_ref: property.reference, days: Number(days.value)}));
      state = await call('api/state'); renderState();
    }, event.currentTarget)}, 'Procurar')), list);
  return box;
}

function activeClientsList(property) {
  const box = el('div', {class: 'client-list'}, el('p', {class: 'muted small'}, 'A carregar…'));
  if (property.visits?.closed_at) {
    box.replaceChildren(el('p', {class: 'muted small'}, 'Imóvel fechado: já não há clientes ativos.'));
  } else {
    run(async () => {
      const data = await call('api/visits/candidates', {property_ref: property.reference});
      box.replaceChildren(...(data.customers.length ? data.customers.map(customer => el('div', {class: 'client-row'},
        el('span', {}, shortName(customer.name) || customer.email),
        el('span', {class: 'tag' + (customer.state === 'booked' ? ' visit' : customer.state === 'ok' ? ' draft' : '')},
          CLIENT_STATE_LABEL[customer.state] || customer.state),
        fichaTag(customer.ficha),
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
  const promptBox = el('details', {class: 'copy-only prompt-view'}, el('summary', {class: 'muted small'}, 'Prompt de análise'), promptText);
  const copyBtn = el('button', {class: 'copy-only', disabled: true, onclick: event => run(async () => {
    await copyText(promptText.textContent, 'Prompt copiado. Cola-o numa conversa do ChatGPT e lê a resposta lá — não é preciso trazê-la de volta.', promptBox);
  }, event.currentTarget)}, 'Copiar');
  const summaryBox = el('div', {});
  return el('details', {class: 'visits-panel'}, el('summary', {class: 'muted small'}, 'Analisar antes de propor'),
    el('p', {class: 'step'}, 'Resume o que os clientes ativos já disseram (disponibilidade, urgência, preferências), para te ajudar a escolher o dia e o intervalo abaixo.'),
    el('div', {class: 'actions'},
      el('button', {class: 'copy-only', onclick: event => run(async () => {
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
        }, event.currentTarget)}, apiOnly() ? 'Analisar' : 'Analisar via API')),
    promptBox, summaryBox);
}

function visitsPanel(property) {
  const visits = property.visits || {windows: [], slots: [], closed_at: null};
  const closed = !!visits.closed_at;
  const slot = settings.voice.visits?.slot_minutes || 30;
  const day = el('input', {type: 'date', 'aria-label': 'Dia das visitas'});
  const start = el('input', {type: 'time', value: '17:00', step: slot * 60, 'aria-label': 'Hora de início'});
  const end = el('input', {type: 'time', value: '19:00', step: slot * 60, 'aria-label': 'Hora de fim'});
  linkTimes(start, end);
  const list = el('div', {class: 'visit-candidates'});
  const choose = event => run(async () => {
    const data = await call('api/visits/candidates', {property_ref: property.reference});
    const rows = data.customers.map(customer => el('label', {class: 'candidate'},
      el('input', {type: 'checkbox', 'data-email': customer.email, checked: customer.state === 'ok',
        disabled: customer.state === 'pending' || customer.state === 'booked'}),
      el('span', {}, shortName(customer.name) || customer.email),
      customer.reason && el('span', {class: 'muted small'}, '— ' + customer.reason)));
    list.replaceChildren(...(rows.length ? rows : [el('p', {class: 'muted small'}, 'Ainda não escrevemos a nenhum cliente deste imóvel.')]),
      rows.length && el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
        const emails = [...list.querySelectorAll('input[type=checkbox]:checked')].map(box => box.dataset.email);
        const result = await call('api/visits/propose', {property_ref: property.reference, day: day.value,
          start: start.value, end: end.value, emails});
        state = result.state; settings = result.settings; renderState(); renderSettings();
        toast(`${result.created} proposta(s) de visita na fila de Emails: ${apiOnly() ? 'gera-as com «Gerar respostas»' : 'prepara-as no ChatGPT'} como as outras.`);
      }, event.currentTarget)}, 'Criar propostas')));
    toast(`${data.customers.length} cliente(s) encontrados.`);
  }, event.currentTarget);
  const closeVisits = el('button', {class: 'link danger', onclick: event => run(async () => {
    if (!confirm(`Fechar as visitas de ${property.reference}? Prepara um email de agradecimento para cada cliente (pendentes e já respondidos) e os pedidos novos deste imóvel passam a ser respondidos automaticamente.`)) return;
    const result = await call('api/visits/close', {property_ref: property.reference});
    state = result.state; settings = result.settings; renderState(); renderSettings();
    toast(`Visitas fechadas: ${result.drafted} rascunho(s) na fila de Emails, prontos a rever e enviar.`);
  }, event.currentTarget)}, 'Fechar visitas e agradecer a todos');
  const requestConsent = el('button', {onclick: event => run(async () => {
    const result = await call('api/consent/request', {property_ref: property.reference});
    state = result.state; renderState();
    toast(result.drafted ? `${result.drafted} pedido(s) de consentimento na fila de Emails.` : 'Ninguém por pedir: já foi pedido a todos os que responderam.');
  }, event.currentTarget)}, 'Pedir consentimento RGPD a quem respondeu');
  return el('details', {class: 'visits-panel'}, el('summary', {class: 'muted small'}, 'Visitas: propor e marcar' + (closed ? ' (fechadas)' : '')),
    closed && el('p', {class: 'alert warn'}, `Visitas fechadas em ${when(visits.closed_at)}. Novos pedidos deste imóvel recebem a resposta automática.`),
    !closed && (visits.windows.length
      ? visits.windows.map(window => el('p', {class: 'small'}, `Proposta: ${dayLabel(window.day)}, das ${window.start} às ${window.end}`))
      : [el('p', {class: 'muted small'}, 'Sem visitas propostas.')]),
    !closed && visits.slots.map(booked => el('p', {class: 'small'}, el('strong', {}, slotLabel(booked.at)), ' · ', shortName(booked.name) || booked.customer)),
    !closed && el('p', {class: 'step'}, `Escolhe o dia e o intervalo. Marcam-se de ${slot} em ${slot} minutos (em Voz e estilo).`),
    !closed && el('div', {class: 'row'}, dateStepper(day), timeStepper(start, slot), timeStepper(end, slot),
      el('button', {onclick: choose}, 'Escolher clientes')), !closed && list,
    el('div', {class: 'actions'}, !closed && closeVisits, requestConsent));
}

// Agenda: a weekly planner, filofax-style — one paper page per day, day pages laid side by side. Each day is a
// time column ruled every 15 minutes (hours written in the margin, half hours dashed), stretched down to the
// bottom of the window, so a visit sits at its own time and its length reads at a glance. Four colours tell
// where each time stands: grey the window proposed in a round, orange the time a customer accepted (still a
// draft), green the visit the owner confirmed (email sent, booked), brick two visits at overlapping times.
// Reads only what the page already holds — settings.properties[].visits and the queues in state — so no
// request of its own. Export to a real calendar is deliberately not built yet — for now this page is the agenda.
let agendaWeekOffset = 0;
const AGENDA_DAY = [9 * 60, 19 * 60];  // always shown; a visit earlier or later widens the whole week
// Blackout: a weekday switched off leaves the week and the other days widen. It is a way of looking at the week,
// kept in this browser like the theme (Monday 0 … Sunday 6); a blackout day that still has visits stays, hatched,
// so no visit is ever hidden.
const WEEKDAY_SHORT = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
let agendaOff = new Set();
try {
  agendaOff = new Set(JSON.parse(localStorage.getItem('bot-mail-agenda-off') || '[]').filter(day => Number.isInteger(day) && day >= 0 && day < 7));
} catch { /* Storage may be unavailable or hold something else. */ }

function toggleAgendaDay(index) {
  if (agendaOff.has(index)) agendaOff.delete(index); else agendaOff.add(index);
  try { localStorage.setItem('bot-mail-agenda-off', JSON.stringify([...agendaOff])); } catch { /* Storage may be unavailable. */ }
  renderAgenda();
}

function startOfWeek(date) {
  const start = new Date(date);
  start.setDate(date.getDate() - ((date.getDay() + 6) % 7));  // Monday-first, matching the retro calendar
  start.setHours(0, 0, 0, 0);
  return start;
}

function isoDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function minutesOf(time) {
  const [hours, minutes] = String(time).split(':').map(Number);
  return hours * 60 + (minutes || 0);
}

const AGENDA_KINDS = {window: 'Janela proposta', accepted: 'Aceite pelo cliente, por confirmar',
  offered: 'Proposta nossa, à espera do cliente', confirmed: 'Confirmada'};

// Every entry of one day, of every property: the filter only hides, so a clash with a hidden property still shows.
function agendaEntries(iso) {
  const properties = settings?.properties || [];
  const labels = Object.fromEntries(properties.map(property =>
    [property.reference, property.reference || property.description || 'Imóvel']));
  const length = settings?.voice?.visits?.slot_minutes || 30;  // a visit fills its whole slot
  const entries = [];
  const visit = (ref, at, name, kind, evidence, before, slot) => {
    const [day, time] = String(at).split(' ');
    const came = slot?.check?.attended;
    if (day === iso) entries.push({ref, label: labels[ref] || ref || 'Imóvel', kind, start: minutesOf(time), at, name,
      end: Math.min(minutesOf(time) + length, 24 * 60),
      text: `${came === true ? '✓ ' : came === false ? '✗ ' : ''}${time} · ${name || 'visita'}${slot?.survey ? ' ★' : ''}`
        + (slot?.ficha ? (slot.ficha.complete ? ' · ficha ok' : ` · ficha ${slot.ficha.known}/${slot.ficha.total}`) : ''),
      customer: slot?.customer, check: slot?.check, survey: slot?.survey, thanksSentAt: slot?.thanks_sent_at, ficha: slot?.ficha,
      came, evidence: [evidence && `lido nos emails pela IA: «${evidence}»`, before && `antes: ${String(before).slice(11)}`]
        .filter(Boolean).join(' · ')});
  };
  for (const property of properties) {
    for (const window of [...(property.visits?.past_windows || []), ...(property.visits?.windows || [])]) {
      if (window.day === iso) entries.push({ref: property.reference, label: labels[property.reference], kind: 'window',
        start: minutesOf(window.start), end: minutesOf(window.end), text: `Janela: ${window.start}–${window.end}`});
    }
    for (const slot of property.visits?.slots || []) {
      visit(property.reference, slot.at, shortName(slot.name) || slot.customer, 'confirmed', slot.source === 'api' && slot.evidence,
        slot.previous, slot);
    }
    // Still to be agreed, found by «Atualizar agenda»: accepted by the customer (orange), offered by us (blue).
    for (const accepted of property.visits?.accepted || []) {
      visit(property.reference, accepted.at, shortName(accepted.name) || accepted.customer, 'accepted', accepted.evidence, accepted.replaces,
        {customer: accepted.customer});
    }
    for (const offered of property.visits?.offered || []) {
      visit(property.reference, offered.at, shortName(offered.name) || offered.customer, 'offered', offered.evidence, offered.replaces,
        {customer: offered.customer});
    }
  }
  // The time a customer accepted sits in a draft until the owner sends it; only then is it booked (green).
  for (const queue of state?.properties || []) {
    for (const email of queue.emails || []) {
      if (email.visit_slot) visit(queue.property_ref, email.visit_slot,
        shortName(email.recipient?.name || email.customer?.name) || email.recipient?.email, 'accepted');
    }
  }
  // Overbooking: two visits (accepted or confirmed, any property) whose times overlap.
  const visits = entries.filter(entry => entry.kind !== 'window');
  for (const entry of visits) entry.clashes = visits.filter(other => other !== entry && other.start < entry.end && entry.start < other.end);
  return entries.sort((one, other) => one.start - other.start);
}

// Side by side only where they overlap (two properties under «Todos»): items that overlap, directly or through
// a neighbour, share the width of their group; each takes the first free lane in it.
function agendaLanes(items) {
  let group = [], groupEnd = -1;
  const close = () => { const lanes = Math.max(0, ...group.map(item => item.lane)) + 1; group.forEach(item => { item.lanes = lanes; }); };
  for (const item of items) {
    if (item.start >= groupEnd && group.length) { close(); group = []; }
    const taken = group.filter(other => other.end > item.start).map(other => other.lane);
    item.lane = [...Array(taken.length + 1).keys()].find(lane => !taken.includes(lane));
    group.push(item);
    groupEnd = Math.max(groupEnd, item.end);
  }
  if (group.length) close();
}

// The CSP allows no style attribute, so every position goes through the element's style object, in quarters.
// Proposals span the whole width (overlapping ones just tint deeper); booked visits take their lane.
function agendaPlace(node, from, item) {
  const lanes = item.lanes || 1, lane = item.lane || 0;
  node.style.top = `calc(var(--quarter) * ${(item.start - from) / 15})`;
  node.style.height = `calc(var(--quarter) * ${(item.end - item.start) / 15})`;
  node.style.left = `calc(var(--gutter) + (100% - var(--gutter)) * ${lane / lanes})`;
  node.style.width = `calc((100% - var(--gutter)) / ${lanes} - 2px)`;
  return node;
}

function agendaRuling(from, quarters) {
  return [...Array(quarters + 1)].flatMap((_, quarter) => {
    const kind = quarter % 4 === 0 ? 'hour' : quarter % 2 === 0 ? 'half' : 'quarter';
    const rule = el('div', {class: 'filofax-rule ' + kind});
    rule.style.top = `calc(var(--quarter) * ${quarter})`;
    if (kind !== 'hour' || quarter === quarters) return [rule];
    const hour = el('span', {class: 'filofax-hour'}, `${Math.floor((from + quarter * 15) / 60)}h`);
    hour.style.top = rule.style.top;
    return [rule, hour];
  });
}

// Down to the bottom of the window: a quarter of an hour gets whatever whole pixels the room below the day
// heads allows (so every rule lands on a pixel), never fewer than 12, so a 15-minute mark is never lost.
// The week shows four hours of the day at a time (about half the height it used to take), scrolling inside, with
// the day heads kept on top; a quarter of an hour keeps the size it had when the whole day filled the window.
// On a phone the days stack, so each still shows whole.
const AGENDA_VIEW_HOURS = 4;
let agendaScroll = {key: '', top: 0};

function fitAgenda() {
  const box = $('agenda-week'), day = box.querySelector('.filofax-day');
  if (!day || $('tab-agenda').hidden) return;
  const narrow = window.matchMedia('(max-width: 760px)').matches;
  if (narrow) { box.style.setProperty('--quarter', '12px'); box.style.removeProperty('--agenda-view'); return; }
  const top = box.getBoundingClientRect().top;
  const offset = day.getBoundingClientRect().top - top + box.scrollTop;  // the page's padding and the day's head
  const room = window.innerHeight - (top + window.scrollY) - offset - 34;
  const quarter = Math.max(12, Math.floor(room / Number(box.dataset.quarters)));
  box.style.setProperty('--quarter', `${quarter}px`);
  box.style.setProperty('--agenda-view', `${Math.round(offset + AGENDA_VIEW_HOURS * 4 * quarter)}px`);
}

// Where the four hours open: where you left them (same week, same property), else the week's first visit or
// window, else now (this week), else the start of the day.
function focusAgenda(key, target, from) {
  const box = $('agenda-week');
  if (agendaScroll.key === key) { box.scrollTop = agendaScroll.top; return; }
  const quarter = parseFloat(box.style.getPropertyValue('--quarter')) || 14;
  box.scrollTop = Math.max(0, Math.round(((target - from) / 15 - 1) * quarter));
  agendaScroll = {key, top: box.scrollTop};
}

function renderAgenda() {
  const properties = Object.fromEntries(activeProperties().map(property =>
    [property.reference, property.reference || property.description || 'Imóvel']));
  fillSelect($('agenda-property'), properties);  // 05/10: no «Todos»: one property at a time
  // 06/10: on top, as the mailbox in Emails: when «Atualizar visitas» last ran (one run reads every property)
  const synced = Math.max(0, ...activeProperties().map(property => Date.parse(property.visits?.synced_at || '') || 0));
  $('agenda-synced').replaceChildren(...(synced
    ? [el('strong', {class: 'last-read-when'}, `Última atualização: ${daysAgo(synced)}`
        + `${new Date(synced).toLocaleDateString('pt-PT', {weekday: 'long'})}, ${when(synced)}`)]
    : ['Ainda por atualizar: a IA lê as conversas e põe aqui as visitas combinadas.']));
  const monday = startOfWeek(new Date());
  monday.setDate(monday.getDate() + agendaWeekOffset * 7);
  const days = [...Array(7)].map((_, i) => { const d = new Date(monday); d.setDate(monday.getDate() + i); return d; });
  const dayMonth = date => date.toLocaleDateString('pt-PT', {day: '2-digit', month: '2-digit'});
  const [first, last] = [days[0], days[6]];
  $('agenda-range').textContent = first.getFullYear() === last.getFullYear()
    ? `${dayMonth(first)} – ${dayMonth(last)}/${last.getFullYear()}`
    : `${dayMonth(first)}/${first.getFullYear()} – ${dayMonth(last)}/${last.getFullYear()}`;
  $('agenda-today').disabled = agendaWeekOffset === 0;
  $('agenda-today').title = agendaWeekOffset === 0 ? 'Já estás na semana atual.' : '';
  const weekday = index => days[index].toLocaleDateString('pt-PT', {weekday: 'long'});
  $('agenda-days').replaceChildren(el('span', {class: 'muted small'}, 'Dias:'), ...WEEKDAY_SHORT.map((name, index) =>
    el('button', {type: 'button', class: 'agenda-day', 'aria-pressed': String(!agendaOff.has(index)),
      title: agendaOff.has(index) ? `${weekday(index)} em blackout: clica para voltar a mostrar`
        : `${weekday(index)} disponível: clica para pôr em blackout`, onclick: () => toggleAgendaDay(index)}, name)));
  const todayIso = isoDate(new Date());
  const filter = $('agenda-property').value;
  renderVisitTodo(filter);
  const showLabel = Object.keys(properties).length > 1;
  const week = days.map((date, index) => ({date, index, iso: isoDate(date), off: agendaOff.has(index),
    entries: agendaEntries(isoDate(date)).filter(entry => !filter || entry.ref === filter)}))
    .filter(day => !day.off || day.entries.length);
  const all = week.flatMap(day => day.entries);
  const from = Math.max(0, Math.floor(Math.min(AGENDA_DAY[0], ...all.map(entry => entry.start)) / 60) * 60);
  const to = Math.min(24 * 60, Math.ceil(Math.max(AGENDA_DAY[1], ...all.map(entry => entry.end)) / 60) * 60);
  const quarters = (to - from) / 15;
  const box = $('agenda-week');
  box.dataset.quarters = quarters;
  box.replaceChildren(...week.map(({date, index, iso, off, entries}) => {
    const windows = entries.filter(entry => entry.kind === 'window'), visits = entries.filter(entry => entry.kind !== 'window');
    agendaLanes(visits);
    const tip = entry => [entry.clashes?.length ? 'Sobreposta (overbooking)' : AGENDA_KINDS[entry.kind], entry.text,
      showLabel && entry.label, entry.evidence,
      entry.clashes?.length && 'com ' + entry.clashes.map(other => `${other.text} (${other.label})`).join(', ')]
      .filter(Boolean).join(' · ');
    const count = (items, one, many) => items.length && `${items.length} ${items.length === 1 ? one : many}`;
    const summary = [...windows.map(entry => entry.text),
      count(visits.filter(entry => entry.kind === 'confirmed'), 'confirmada', 'confirmadas'),
      count(visits.filter(entry => entry.kind === 'accepted'), 'por confirmar', 'por confirmar'),
      count(visits.filter(entry => entry.kind === 'offered'), 'proposta nossa', 'propostas nossas'),
      count(visits.filter(entry => entry.clashes.length), 'sobreposta', 'sobrepostas')].filter(Boolean).join(' · ');
    const day = el('div', {class: 'filofax-day'}, agendaRuling(from, quarters),
      windows.map(entry => agendaPlace(el('div', {class: 'filofax-entry window', title: tip(entry)}), from, entry)),
      visits.map(entry => {
        // A visit opens its check (who came, the notes, the thanks) below the week — booked (green), and also a
        // time still offered or accepted (blue, orange): if the customer came, that was the visit.
        const clickable = ['confirmed', 'offered', 'accepted'].includes(entry.kind) && entry.customer;
        const came = entry.came === true ? ' attended' : entry.came === false ? ' noshow' : '';
        const node = el('div', {class: `filofax-entry visit ${entry.clashes.length ? 'overbooked' : entry.kind}${came}${clickable ? ' clickable' : ''}`,
          title: tip(entry) + (clickable ? ' · clica para o check da visita' : '')},
          el('strong', {}, entry.text), showLabel && el('span', {}, entry.label));
        if (clickable) node.addEventListener('click', () => openVisitCheck(entry));
        return agendaPlace(node, from, entry);
      }));
    day.style.height = `calc(var(--quarter) * ${quarters})`;
    const shown = off ? `Blackout, mas com visitas · ${summary}` : summary || 'Sem visitas previstas.';
    return el('div', {class: 'filofax-page' + (iso === todayIso ? ' today' : '') + (off ? ' blackout' : '')},
      el('div', {class: 'filofax-head'},
        el('span', {class: 'filofax-weekday'}, weekday(index)),
        el('span', {class: 'filofax-date'}, dayMonth(date)),
        // 05/10: no «Blackout» / «Disponível» on each day: the «Dias» buttons above do it
        el('span', {class: 'muted small filofax-summary', title: shown}, shown)),
      day);
  }));
  if (!week.length) box.replaceChildren(el('p', {class: 'empty-state filofax-none'}, 'Todos os dias estão em blackout. Liga um dia em «Dias».'));
  fitAgenda();
  if ($('agenda-property').value !== roundPanelProperty) renderVisitsRound();  // 02/10: the round follows the property on top
  const clock = new Date(), minutesNow = clock.getHours() * 60 + clock.getMinutes();
  const target = all.length ? Math.min(...all.map(entry => entry.start))
    : agendaWeekOffset === 0 && minutesNow >= from && minutesNow < to ? minutesNow : from;
  focusAgenda(`${agendaWeekOffset}|${filter}`, target, from);
}

// After the visit: did the customer come, a private note (only for the owner: never in an email nor to the AI),
// a public one (it goes into the thanks), and «Criar agradecimento», which puts the after-visit draft in Comunicações.
// «Depois das visitas»: the visits already past (last 14 days) nobody has checked yet, as buttons above the week —
// the way into the after-visit step (who came, the notes, the thanks), without hunting for the blocks.
function renderVisitTodo(filter) {
  const now = new Date(), days = [];
  for (let back = 14; back >= 0; back--) { const day = new Date(now); day.setDate(now.getDate() - back); days.push(isoDate(day)); }
  const past = entry => new Date(entry.at.replace(' ', 'T')) <= now;
  const todo = days.flatMap(iso => agendaEntries(iso)).filter(entry => (!filter || entry.ref === filter) && entry.customer
    && ['confirmed', 'offered', 'accepted'].includes(entry.kind) && entry.check?.attended == null && past(entry));
  $('agenda-todo').replaceChildren(...(todo.length ? [
    el('strong', {}, 'Depois das visitas'),
    el('span', {class: 'muted small'}, 'quem apareceu, notas e agradecimento:'),
    ...todo.map(entry => el('button', {type: 'button', class: 'agenda-todo-item ' + entry.kind,
      title: 'Assinalar esta visita e criar o agradecimento', onclick: () => openVisitCheck(entry)},
      `${shortName(entry.name) || entry.customer} · ${entry.at.slice(8, 10)}/${entry.at.slice(5, 7)} ${entry.at.slice(11)}`))] : []));
  $('agenda-todo').hidden = !todo.length;
}

function openVisitCheck(entry) {
  const check = entry.check || {}, survey = entry.survey;
  const box = $('agenda-check');
  const name = 'came-' + entry.customer;
  const came = el('input', {type: 'radio', name, checked: check.attended === true});
  const missed = el('input', {type: 'radio', name, checked: check.attended === false});
  const privateNote = el('textarea', {rows: 3, placeholder: 'Só para ti: nunca vai em nenhum email nem para a IA.'}, check.private || '');
  const publicNote = el('textarea', {rows: 3, placeholder: 'Vai no agradecimento ao cliente, ex.: «foi um prazer mostrar-lhe o apartamento».'}, check.public || '');
  const save = async () => {
    const attended = came.checked ? true : missed.checked ? false : null;
    const result = await call('api/visits/check', {property_ref: entry.ref, email: entry.customer, attended,
      private_note: privateNote.value, public_note: publicNote.value, at: entry.at});
    settings = result.settings; renderAgenda();
    return attended;
  };
  const score = value => value == null ? '–' : `${value}/5`;
  box.replaceChildren(el('section', {class: 'card visit-check'},
    el('div', {class: 'section-heading'}, el('h2', {}, `Visita · ${shortName(entry.name) || entry.customer}`),
      el('button', {type: 'button', class: 'link', onclick: () => box.replaceChildren()}, 'Fechar')),
    el('p', {class: 'muted small'}, `${slotLabel(entry.at)} · ${entry.label} · ${entry.customer}`),
    entry.ficha && el('p', {class: 'alert ' + (entry.ficha.complete ? 'ok' : 'warn')}, entry.ficha.complete
      ? 'Ficha do cliente completa: temos toda a informação necessária.'
      : 'Ficha incompleta. Falta: ' + entry.ficha.falta.map(key => FICHA_LABELS[key] || key).join(', ').toLowerCase()
        + '. Decides tu se confirmas a visita.'),
    el('div', {class: 'row'}, el('label', {}, came, 'Apareceu'), el('label', {}, missed, 'Não apareceu')),
    el('label', {class: 'field'}, 'Nota privada (só para ti)', privateNote),
    el('label', {class: 'field'}, 'Nota pública (vai no agradecimento ao cliente)', publicNote),
    entry.thanksSentAt && el('p', {class: 'alert ok'}, `Agradecimento enviado em ${when(entry.thanksSentAt)}.`),
    survey && el('p', {class: 'alert ok'}, `Inquérito respondido (${when(survey.at)}): imóvel ${score(survey.imovel)} · `
      + `consultor ${score(survey.consultor)} · marcação e emails ${score(survey.marcacao)} · interesse: ${survey.interesse || '–'}`
      + (survey.ficha_confirmada ? ' · ficha de visita confirmada ✓' : ' · ficha de visita por confirmar')
      + (survey.comentario ? ` · «${survey.comentario}»` : '')),
    el('div', {class: 'actions'},
      el('button', {type: 'button', onclick: event => run(async () => { await save(); toast('Visita registada.'); }, event.currentTarget)}, 'Guardar'),
      el('button', {type: 'button', class: 'primary', onclick: event => run(async () => {
        if (await save() !== true) throw new Error('Marca «Apareceu» para criar o agradecimento.');
        const result = await call('api/visits/thanks', {property_ref: entry.ref, email: entry.customer});
        state = result.state; renderState();
        toast(`Agradecimento em Emails: gera-o com a IA (${apiOnly() ? '«Gerar respostas»' : 'Criar prompt ou via API'}), revê e envia.`);
      }, event.currentTarget)}, 'Guardar e criar agradecimento'))));
  box.scrollIntoView({block: 'nearest', behavior: 'smooth'});
}

// «Atualizar agenda»: the API reads the active customers' conversations and updates the agenda by itself.
async function syncAgenda() {
  const result = await call('api/agenda/sync', {days: Number($('agenda-sync-days').value) || 0});
  settings = result.settings; state = result.state; renderSettings(); renderState();
  if (activeTab === 'agenda') renderAgenda();
  const done = result.properties.map(item => item.skipped ? `${item.property_ref}: ${item.skipped}`
    : `${item.property_ref}: ${item.confirmed} nova(s), ${item.moved} mudada(s) de hora, ${item.accepted} aceite(s) `
      + `por confirmar, ${item.offered} proposta(s) nossa(s)` + (item.past ? `, ${item.past} já passada(s), por registar` : ''));
  toast('Visitas atualizadas. ' + done.join(' · '));
}
$('agenda-sync-here').addEventListener('click', event => run(syncAgenda, event.currentTarget));

$('agenda-week').addEventListener('scroll', () => { agendaScroll.top = $('agenda-week').scrollTop; }, {passive: true});
$('agenda-prev').addEventListener('click', () => { agendaWeekOffset--; renderAgenda(); });
$('agenda-next').addEventListener('click', () => { agendaWeekOffset++; renderAgenda(); });
$('agenda-today').addEventListener('click', () => { agendaWeekOffset = 0; renderAgenda(); });
$('agenda-property').addEventListener('change', renderAgenda);
window.addEventListener('resize', () => { if (activeTab === 'agenda') fitAgenda(); });

// Imóveis: one property at a time (a slider, not side by side), each with its own instrument cluster;
// creating or editing a property's ad data is a view of its own. The property shown is remembered in
// this browser only, like the theme.
let propertyRef = null, slideDirection = 0, editorRef = null;
try { propertyRef = localStorage.getItem('bot-mail-property'); } catch { /* Storage may be unavailable. */ }

// 05/10: one property chosen for every tab (Emails, Clientes, Visitas, Imóveis, and the owners' digest): changing it in
// one, the others open on it too. It is Imóveis' own choice, kept in this browser.
function shareProperty(ref) {
  if (!ref) return;
  propertyRef = ref;
  try { localStorage.setItem('bot-mail-property', ref); } catch { /* Storage may be unavailable. */ }
}
function applySharedProperty(tab) {
  if (!propertyRef) return;
  const put = select => {  // a menu not drawn yet keeps the value by an option of its own, which the redraw keeps
    if (![...select.options].some(option => option.value === propertyRef)) select.append(el('option', {value: propertyRef}, propertyRef));
    const changed = select.value !== propertyRef;
    select.value = propertyRef;
    return changed;
  };
  if (tab === 'replies' && [...$('queue').options].some(option => option.value === propertyRef) && $('queue').value !== propertyRef) {
    $('queue').value = propertyRef;
    $('queue').dispatchEvent(new Event('change'));
  }
  if (tab === 'contacts') { $('fichas-property').dataset.touched = '1'; if (put($('fichas-property'))) { fichasPage = 0; selectionPage = 0; } }
  if (tab === 'agenda') put($('agenda-property'));
  if (tab === 'owners') ownerDigestRef = propertyRef;
}
// 06/10: a property's panel in Imóveis, from elsewhere (the Painel's «Por imóvel»)
function openPropertyPanel(ref) { selectProperty(ref, 0, false); showPropertiesView('list'); showTab('properties'); }
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
  // The owner's email is not in the listing: filled from an extraction, the form keeps the one already saved (27/09).
  const saved = settings?.properties?.find(property => property.reference === ref);
  // 30/09: the kind of business: the one saved, else a rental
  const keep = {owner_email: saved?.owner_email, deal: saved?.deal || 'arrendamento'};
  for (const name of FIELDS) if (name !== 'sender' || fields.sender) $('f-' + name).value = fields[name] ?? keep[name] ?? '';
  $('f-facts').value = (fields.facts || []).join('\n');
  $('editor-title').textContent = ref ? `Editar ${ref}` : 'Novo imóvel';
  // How far back the first read goes: asked only for a new property (45 days unless changed).
  $('first-read-field').hidden = Boolean(ref);
  $('f-first-read').value = settings?.first_read_days || 45;
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
  $('property-slider').classList.toggle('test-property', !!property?.test);  // 02/10: the test property, in light purple
  // Through el(), which drops a false child: replaceChildren itself would print it as the text "false".
  $('property-slider').replaceChildren(...el('div', {},
    many && el('button', {class: 'slider-arrow prev', 'aria-label': 'Imóvel anterior', onclick: () => stepProperty(-1)}, '‹'),
    el('span', {class: 'eyebrow switcher-label'}, 'IMÓVEL'),  // 30/09: titled like the other switchers
    el('div', {class: 'slider-title'},
      el('span', {class: 'property-ref'}, property.reference + (property.active === false ? ' · INATIVO' : '')),
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
function gauge({key, value, max, red = null, green = null, unit, caption, readout, size = 'small', face = 'dark', labels = null,
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
    svg('svg', {viewBox: '0 0 200 200', role: 'img', 'aria-label': `${caption || unit}: ${readout}`},
      svg('defs', {}, svg('linearGradient', {id: id + '-bezel', x1: 0, y1: 0, x2: 0, y2: 1},
        svg('stop', {offset: '0%', 'stop-color': '#f6f6f6'}), svg('stop', {offset: '50%', 'stop-color': '#7d8186'}),
        svg('stop', {offset: '100%', 'stop-color': '#dcdde0'}))),
      svg('circle', {cx: c, cy: c, r: 99, fill: `url(#${id}-bezel)`, class: 'gauge-bezel'}),
      svg('circle', {cx: c, cy: c, r: 93, class: 'gauge-face'}),
      red && red[0] < red[1] ? svg('path', {d: arc(angle(red[0]), angle(red[1]), r - 4), class: 'gauge-red'}) : null,
      green && green[0] < green[1] ? svg('path', {d: arc(angle(green[0]), angle(green[1]), r - 4), class: 'gauge-green'}) : null,
      marks,
      svg('text', {x: c, y: c - 32, class: 'gauge-unit'}, unit.toUpperCase()),
      icon ? gaugeIcon(icon, c, c + 31) : null,  // between the needle's cap and the readout
      // Below the first and last numbers (at ±135°, y ≈ c + 40): in the dial's open bottom, never over them.
      svg('rect', {x: c - 42, y: c + 52, width: 84, height: 22, rx: 3, class: 'gauge-readout-box'}),
      svg('text', {x: c, y: c + 63.5, class: 'gauge-readout'}, readout),
      needle,
      svg('circle', {cx: c, cy: c, r: 9, class: 'gauge-cap'})),
    caption ? el('figcaption', {}, caption) : null);  // a dial may say all on its face (27/09: the API tank)
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
// 27/09: what the API cost, to the cent and no further; a positive amount under half a cent reads «< 0,01 €».
const costText = value => value > 0 && value < 0.005 ? '< 0,01 €' : eurFormat.format(value || 0);
const litresText = litres => litres == null ? '— L' : litres.toLocaleString('pt-PT', {maximumFractionDigits: 1}) + ' L';

// A property's API tank as a fuel gauge: E to F, the red at the empty end (the reserve), needle on what is left.
function fuelGauge(fuel, key, caption, size = 'small') {
  const capacity = fuel.capacity_eur, left = fuel.configured ? Math.max(0, fuel.remaining_eur) : capacity;
  return gauge({key, value: left, max: capacity, red: [0, capacity * 0.15], unit: 'Token$', labels: ['E', '½', 'F'],
    divisions: 2, minor: 4, icon: 'fuel', role: 'fuel', alert: fuel.empty, size,
    readout: fuel.configured ? eurFormat.format(left) : 'sem limite', caption});
}

// A real automotive dial (27/09, after the user's reference): a white face with a chrome bezel, a blue scale, and two
// half scales that rise from the bottom towards the top, like a car's combination gauge — each half with its needle
// (blue on the left, red on the right), its value at the bottom and its own hover. left / right: {value, max, labels
// (bottom, middle, top), text, hover, click, reserve (the right half's red end)}.
function realDial({key, label, left, right, sizeClass = 'small', alert = false, caption = null}) {
  const id = 'gauge' + (++gaugeCount), c = 100, r = 80, low = 135, high = 12;
  const share = (value, max) => max ? Math.max(0, Math.min(1, value / max)) : 1;
  const leftAngle = value => -low + (low - high) * share(value, left.max);
  const rightAngle = value => low - (low - high) * share(value, right.max);
  const point = (a, radius) => [c + radius * Math.sin(a * Math.PI / 180), c - radius * Math.cos(a * Math.PI / 180)];
  const arc = (a1, a2, radius) => {
    const [x1, y1] = point(a1, radius), [x2, y2] = point(a2, radius);
    return `M ${x1} ${y1} A ${radius} ${radius} 0 0 1 ${x2} ${y2}`;
  };
  const scale = (angleOf, max, labels) => {
    const marks = [];
    for (let i = 0; i <= 20; i++) {
      const a = angleOf(max * i / 20), major = i % 5 === 0;
      const [x1, y1] = point(a, r - (major ? 13 : 7)), [x2, y2] = point(a, r - 1);
      marks.push(svg('line', {x1, y1, x2, y2, class: 'real-tick' + (major ? ' major' : '')}));
      if (i % 10 === 0) {
        const [x, y] = point(a, r - 25);
        marks.push(svg('text', {x, y, class: 'real-number'}, labels[i / 10]));
      }
    }
    return marks;
  };
  const needle = (name, start, target) => {
    const node = svg('g', {class: 'gauge-needle real-needle ' + name},
      svg('path', {d: `M ${c - 2.6} ${c + 16} L ${c - 0.9} ${c - r + 10} L ${c + 0.9} ${c - r + 10} L ${c + 2.6} ${c + 16} Z`}));
    const memory = key + ':' + name;
    node.style.transform = `rotate(${needles[memory] ?? start}deg)`;
    needles[memory] = target;
    requestAnimationFrame(() => requestAnimationFrame(() => { node.style.transform = `rotate(${target}deg)`; }));
    return node;
  };
  const half = (sweep, text, click) => {
    const node = svg('path', {d: `M ${c} 1 A 99 99 0 0 ${sweep} ${c} 199 Z`, class: 'real-hit' + (click ? ' clickable' : '')},
      svg('title', {}, text));
    if (click) node.addEventListener('click', click);
    return node;
  };
  return el('figure', {class: `gauge gauge-${sizeClass} gauge-fuel gauge-real` + (alert ? ' gauge-alert' : '')},
    svg('svg', {viewBox: '0 0 200 200', role: 'img', 'aria-label': `${left.hover} ${right.hover}`},
      svg('defs', {},
        svg('linearGradient', {id: id + '-bezel', x1: 0, y1: 0, x2: 0, y2: 1},
          svg('stop', {offset: '0%', 'stop-color': '#fbfbfb'}), svg('stop', {offset: '45%', 'stop-color': '#a9adb3'}),
          svg('stop', {offset: '100%', 'stop-color': '#eceef0'})),
        svg('radialGradient', {id: id + '-face', cx: '50%', cy: '42%', r: '62%'},
          svg('stop', {offset: '0%', 'stop-color': '#ffffff'}), svg('stop', {offset: '80%', 'stop-color': '#f3f5f8'}),
          svg('stop', {offset: '100%', 'stop-color': '#dfe3e9'}))),
      svg('circle', {cx: c, cy: c, r: 99, fill: `url(#${id}-bezel)`, class: 'real-bezel'}),
      svg('circle', {cx: c, cy: c, r: 92, fill: `url(#${id}-face)`, class: 'real-face'}),
      right.reserve > 0 ? svg('path', {d: arc(rightAngle(right.reserve), rightAngle(0), r - 4), class: 'real-reserve'}) : null,
      scale(leftAngle, left.max, left.labels),
      scale(rightAngle, right.max || 1, right.labels),
      // under the needles' pivot, the dial's name; at the bottom, each needle's value
      svg('text', {x: c, y: c + 27, class: 'real-label'}, label),
      svg('text', {x: c - 27, y: c + 60, class: 'real-readout spent'}, left.text),
      svg('text', {x: c + 27, y: c + 60, class: 'real-readout tank'}, right.text),
      needle('needle-spent', -low, leftAngle(left.value)),
      needle('needle-tank', low, rightAngle(right.value)),
      svg('circle', {cx: c, cy: c, r: 9, class: 'real-cap'}),
      half(0, left.hover, left.click), half(1, right.hover, right.click)),  // on top of everything
    caption ? el('figcaption', {}, caption) : null);
}
const dialEuros = value => value.toLocaleString('pt-PT', {maximumFractionDigits: 1});

// A property's API tank (27/09): the left half is what its API has cost so far, in euros (blue needle); the right
// half is what is left in its token tank, E to F (red needle), with the reserve in red.
function tankGauge(fuel, usage, key, caption, sizeClass = 'small', onFill = null) {
  const spent = usage?.all_time?.cost_usd || 0;
  const capacity = fuel.capacity_eur || 0, left = fuel.configured ? Math.max(0, fuel.remaining_eur ?? 0) : capacity;
  const spentMax = niceMax(Math.max(capacity, spent || 0, 1));
  const spentText = costText(spent), leftText = fuel.configured ? eurFormat.format(left) : 'sem limite';
  const size = eurFormat.format(capacity);
  // What each needle says, in words, on hover over its half (27/09: they were lines of text beside the gauge)
  const spentHover = usage ? spendingText(usage) : `Gasto até hoje: ${spentText}.`;
  const tankHover = (!fuel.configured ? 'Sem depósito: a via API não tem limite neste imóvel.'
    : fuel.empty ? 'Vazio: a API está desligada neste imóvel.'
    : fuel.reserve ? `Na reserva: restam ${leftText} de ${size}.` : `Restam ${leftText} de ${size}.`)
    + (onFill ? ' Clicar para mudar os limites de gastos.' : '');
  return realDial({key, label: 'TOKEN$', sizeClass, alert: fuel.empty, caption,
    left: {value: spent, max: spentMax, labels: ['0', dialEuros(spentMax / 2), dialEuros(spentMax)], text: spentText, hover: spentHover},
    right: {value: left, max: capacity, labels: ['E', '½', 'F'], text: leftText, hover: tankHover, click: onFill,
            reserve: fuel.configured ? capacity * 0.15 : 0}});
}

// Each property has its own tank (settings.properties[].api_fuel); settings.api_fuel is only for a folder
// without properties.
function fuelOf(ref) {
  return (ref ? settings?.properties.find(property => property.reference === ref)?.api_fuel : null) ?? settings?.api_fuel;
}

// An empty tank switches off that property's API buttons (data-ref, else the queue open in Comunicações):
// data-hold stops run() from switching them back on, and the title says why. Copy/paste is untouched, and
// the server refuses the call too — this is only the signal.
function holdFuelButtons() {
  if (!settings) return;
  for (const button of document.querySelectorAll('.needs-fuel')) {
    const ref = button.dataset.ref || queueRef(), fuel = fuelOf(ref);
    button.dataset.hold = fuel?.empty ? '1' : '';
    button.disabled = !!fuel?.empty || button.dataset.lock === '1';
    if (fuel?.empty) button.title = `Depósito da API${ref ? ' de ' + ref : ''} vazio: enche-o no painel do imóvel `
      + '(Imóveis).' + (apiOnly() ? '' : ' O copiar/colar com o ChatGPT continua a funcionar.');
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
// What this property spent on the API (26/09): its own numbers under its own tank; the folder's total is below, apart.
function spendingText(usage) {
  const text = item => item.calls ? `${costText(item.cost_usd)} · ${item.calls} pedido(s)` : 'nada';
  const same = usage.period.calls === usage.all_time.calls && usage.period.cost_usd === usage.all_time.cost_usd;
  return same ? `Gasto neste período e desde sempre: ${text(usage.all_time)}.`
    : `Gasto neste período: ${text(usage.period)} · desde sempre: ${text(usage.all_time)}.`;
}

// Changing a property's spending limit (27/09): from the pump, or a click on its gauge's tank side. Asks how much; from
// then on the API may spend up to that here, counted from zero. after: what to redraw once it is filled.
function fillTank(ref, capacity, after, button) {
  return run(async () => {
    const answer = prompt(`Limite de gastos de ${ref}: quantos euros? A partir daí, a via API pode gastar até esse `
      + 'valor neste imóvel (estimativa a partir dos tokens), e o depósito volta a contar do zero.', String(capacity ?? 5));
    if (answer === null) return;
    const amount = Number(String(answer).replace(',', '.'));
    if (!(amount >= 0.5 && amount <= 1000)) throw new Error('Indica um valor entre 0,5 e 1000 €.');
    const result = await call('api/fuel/fill', {property_ref: ref, capacity_eur: amount});
    applyFuel(result.fuel, ref);
    toast(`Depósito de ${ref} cheio: ${eurFormat.format(result.fuel.capacity_eur)}.`);
    await after();
  }, button);
}

// Depósitos (27/09): what the API cost, every property together, at the right of the tanks — a dial like theirs (it
// was a wallet, and clashed): on the left since always, on the right the last month, both on one scale in euros, to
// the cent; requests and tokens on each half's hover. capacity: the tanks together, for the scale.
function renderWallet(usage, capacity = 0) {
  const detail = item => `${item.calls} pedido${item.calls === 1 ? '' : 's'} · `
    + `${(item.prompt_tokens + item.completion_tokens).toLocaleString('pt-PT')} tokens`;
  const total = usage.all_time, month = usage.month || usage.period;
  const max = niceMax(Math.max(capacity, total.cost_usd || 0, 1));
  const labels = ['0', dialEuros(max / 2), dialEuros(max)];
  $('usage-wallet').replaceChildren(
    el('p', {class: 'eyebrow wallet-title'}, 'GASTO TOTAL · TODOS OS IMÓVEIS'),
    realDial({key: 'painel:wallet', label: 'GASTO €', sizeClass: 'wallet', caption: '← desde sempre · último mês →',
      left: {value: total.cost_usd || 0, max, labels, text: costText(total.cost_usd),
             hover: `Desde sempre: ${costText(total.cost_usd)}` + (total.calls ? ` · ${detail(total)}.` : ' · sem pedidos ainda.')},
      right: {value: month.cost_usd || 0, max, labels, text: costText(month.cost_usd),
              hover: `Último mês: ${costText(month.cost_usd)}` + (month.calls ? ` · ${detail(month)}.` : ' · sem pedidos.')}}));
}

function renderFuelOverview(metrics) {
  // 02/10: the test property's tank too (3 € unless filled otherwise), last and marked as the test one
  const tanks = [...metrics.properties, ...(metrics.test_tanks || []).map(item => ({...item, test: true}))];
  const rows = tanks.filter(item => item.property_ref && item.api_fuel).map(item => {
    // 27/09: what was spent and what is left are the gauge's hovers now, one per half; only an empty tank (the API off
    // here) still says so in words. The pump, or a click on the tank's half, changes the limit right here.
    const fuel = item.api_fuel, ref = item.property_ref;
    const fill = button => fillTank(ref, fuel.capacity_eur, loadMetrics, button);
    return el('div', {class: 'fuel-row' + (item.test ? ' test-tank' : '')},
      tankGauge(fuel, item.openai_usage, 'painel:fuel:' + ref, item.test ? `${ref} · TESTE` : ref, 'small', () => fill()),
      el('div', {class: 'fuel-side'},
        fuel.empty && el('p', {class: 'fuel-status bad'},
          'Vazio: a API está desligada neste imóvel.' + (apiOnly() ? '' : ' O copiar/colar continua.')),
        el('button', {class: 'link', title: 'Clicar para mudar os limites de gastos', 'aria-label': `Mudar o limite de gastos de ${ref}`,
          onclick: event => fill(event.currentTarget)}, 'Encher')));
  });
  // 04/10: the total, the big dial, in the middle; the tanks on either side of it, the first half on the left
  const half = Math.ceil(rows.length / 2);
  $('fuel-panel').replaceChildren(...(rows.length ? rows.slice(0, half) : [fuelGauge(metrics.api_fuel, 'painel:fuel', 'Depósito da API')]));
  $('fuel-panel-right').replaceChildren(...rows.slice(half));
}

// What a property's panel measures, whatever a skin draws it as: emails waiting, the average reply time
// against this property's own limit, requests per day in the chosen period, its API tank and the petrol
// its visits took.
function panelSignals(data, metrics) {
  const hoursMax = data.reply_hours_max || 24;
  return {pending: data.pending, pendingMax: data.pending <= 20 ? 20 : niceMax(data.pending),
    hours: data.reply_hours, hoursMax, hot: data.reply_hours != null && data.reply_hours >= hoursMax,
    perDay: data.by_day.reduce((sum, day) => sum + day.requests, 0) / (metrics.period_days || 14),
    fuel: data.api_fuel || metrics.api_fuel, usage: data.openai_usage,
    petrol: data.petrol || {distance_km: null, l_per_100km: 7, trips: 0, planned_trips: 0, km: null, litres: null}};
}
// Hours in at most three digits (26/09): 214 h from a hundred up, 45,3 h below; the «h» never wraps away from the number.
const hoursText = hours => hours == null ? '—'
  : (hours >= 100 ? Math.round(hours) : Math.round(hours * 10) / 10).toLocaleString('pt-PT') + '\u00a0h';

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
      unit: 'horas', divisions: 4, minor: 3, readout: hoursText(s.hours), caption: `Que demoramos a responder (${replyShort()})`, alert: s.hot}),
    gauge({key: ref + ':pending', role: 'tach', value: s.pending, max: s.pendingMax, red: [s.pendingMax / 2, s.pendingMax],
      unit: 'emails', size: 'big', face: 'yellow', divisions: 10, minor: 2, readout: String(s.pending), caption: 'Por responder'}),
    tankGauge(s.fuel, s.usage, 'cluster:fuel', null, 'small', s.onFill),
    petrolGauge(ref, s.petrol, 'Gasolina das visitas')];
}

// 80's RacingCar: a GT's binnacle. Water temperature is the average reply time, with this property's own limit
// as its H; the yellow tachometer, the emails waiting; the speedometer, requests per day; fuel, the property's
// token tank; and, smaller beside it, the petrol its visits took.
function carInstruments(ref, s) {
  const speedMax = Math.max(10, niceMax(Math.max(1, s.perDay)));
  return [
    gauge({key: ref + ':hours', role: 'heat', value: s.hours || 0, max: s.hoursMax, red: [s.hoursMax * 0.75, s.hoursMax],
      unit: '', icon: 'heat', labels: ['C', '', 'H'], divisions: 2, minor: 4, readout: hoursText(s.hours),
      caption: `Que demoramos a responder (${replyShort()})`, alert: s.hot}),
    gauge({key: ref + ':pending', role: 'tach', value: s.pending, max: s.pendingMax, red: [s.pendingMax / 2, s.pendingMax],
      unit: 'emails', size: 'big', face: 'yellow', divisions: 10, minor: 2, readout: String(s.pending),
      caption: 'Por responder'}),
    gauge({key: ref + ':speed', role: 'speedo', value: s.perDay, max: speedMax, unit: 'pedidos / dia', size: 'big',
      divisions: 5, minor: 4, readout: s.perDay.toLocaleString('pt-PT', {maximumFractionDigits: 1}) + ' /dia',
      caption: 'Pedidos por dia'}),
    fuelGauge(s.fuel, 'cluster:fuel'),
    petrolGauge(ref, s.petrol, 'Gasolina · visitas')];
}

// 90's Boat: the helm's instruments, white faces in chrome bezels. The barometer is the average reply time, from
// fair weather to storm at this property's own limit; the anemometer, the emails waiting; the log, requests per
// day; the tank, the property's tokens; and, smaller beside it, the petrol its visits took (by car, as ever).
function boatInstruments(ref, s) {
  const speedMax = Math.max(10, niceMax(Math.max(1, s.perDay)));
  return [
    gauge({key: ref + ':hours', role: 'heat', value: s.hours || 0, max: s.hoursMax, red: [s.hoursMax * 0.75, s.hoursMax],
      unit: 'horas', face: 'white', labels: ['BOM TEMPO', 'VARIÁVEL', 'TEMPESTADE'], divisions: 2, minor: 4,
      readout: hoursText(s.hours), caption: `Que demoramos a responder (${replyShort()})`, alert: s.hot}),
    gauge({key: ref + ':pending', role: 'tach', value: s.pending, max: s.pendingMax, red: [s.pendingMax / 2, s.pendingMax],
      unit: 'emails', size: 'big', face: 'white', divisions: 10, minor: 2, readout: String(s.pending),
      caption: 'Por responder'}),
    gauge({key: ref + ':speed', role: 'speedo', value: s.perDay, max: speedMax, unit: 'pedidos / dia', size: 'big',
      face: 'white', divisions: 5, minor: 4, readout: s.perDay.toLocaleString('pt-PT', {maximumFractionDigits: 1}) + ' /dia',
      caption: 'Pedidos por dia'}),
    fuelGauge(s.fuel, 'cluster:fuel'),
    petrolGauge(ref, s.petrol, 'Gasolina · visitas')];
}

// 70's Scooter: the headset of a 70s Italian scooter, cream faces with italic numbers in chrome rings. The speedometer is
// the requests per day; the rev counter, the emails waiting; the engine temperature, the average reply time against
// this property's own limit; the tank, the property's tokens; and, smaller, the petrol its visits took.
function scooterInstruments(ref, s) {
  const speedMax = Math.max(10, niceMax(Math.max(1, s.perDay)));
  return [
    gauge({key: ref + ':hours', role: 'heat', value: s.hours || 0, max: s.hoursMax, red: [s.hoursMax * 0.75, s.hoursMax],
      unit: 'motor', face: 'cream', icon: 'heat', labels: ['C', '', 'H'], divisions: 2, minor: 4, readout: hoursText(s.hours),
      caption: `Que demoramos a responder (${replyShort()})`, alert: s.hot}),
    gauge({key: ref + ':speed', role: 'speedo', value: s.perDay, max: speedMax, unit: 'pedidos / dia', size: 'big',
      face: 'cream', divisions: 5, minor: 4, readout: s.perDay.toLocaleString('pt-PT', {maximumFractionDigits: 1}) + ' /dia',
      caption: 'Pedidos por dia'}),
    gauge({key: ref + ':pending', role: 'tach', value: s.pending, max: s.pendingMax, red: [s.pendingMax / 2, s.pendingMax],
      unit: 'emails', size: 'big', face: 'cream', divisions: 10, minor: 2, readout: String(s.pending),
      caption: 'Por responder'}),
    fuelGauge(s.fuel, 'cluster:fuel'),
    petrolGauge(ref, s.petrol, 'Gasolina · visitas')];
}

// 00's UK Cabrio (04/10): the dash of a British hatch of the 2000s. The giant round speedometer in the middle of the dash
// is the requests per day, with the ambient light around it; the rev counter on the steering column, the emails waiting;
// the engine temperature, the average reply time against this property's own limit; the tank, the property's tokens;
// and, smaller, the petrol its visits took. Black faces, white numbers, orange needles (in themes/cabrio.css).
function cabrioInstruments(ref, s) {
  const speedMax = Math.max(10, niceMax(Math.max(1, s.perDay)));
  return [
    gauge({key: ref + ':pending', role: 'tach', value: s.pending, max: s.pendingMax, red: [s.pendingMax / 2, s.pendingMax],
      unit: 'emails', face: 'cabrio', divisions: 5, minor: 2, readout: String(s.pending), caption: 'Por responder'}),
    gauge({key: ref + ':speed', role: 'speedo', value: s.perDay, max: speedMax, unit: 'pedidos / dia', size: 'big',
      face: 'cabrio', divisions: 5, minor: 4, readout: s.perDay.toLocaleString('pt-PT', {maximumFractionDigits: 1}) + ' /dia',
      caption: 'Pedidos por dia'}),
    gauge({key: ref + ':hours', role: 'heat', value: s.hours || 0, max: s.hoursMax, red: [s.hoursMax * 0.75, s.hoursMax],
      unit: 'motor', face: 'cabrio', icon: 'heat', labels: ['C', '', 'H'], divisions: 2, minor: 4, readout: hoursText(s.hours),
      caption: `Que demoramos a responder (${replyShort()})`, alert: s.hot}),
    fuelGauge(s.fuel, 'cluster:fuel'),
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

// Filling this property's tank, beside its fuel gauge: only the pump (27/09); a click asks how much. From then on
// the API may spend up to that here.
function fuelFill(property, fuel) {
  const ref = property.reference;
  return el('div', {class: 'gauge-setting'}, el('button', {type: 'button', class: 'link pump-button',
    title: 'Clicar para mudar os limites de gastos', 'aria-label': `Mudar o limite de gastos de ${ref}`,
    onclick: event => fillTank(ref, fuel.capacity_eur, () => renderPropertyDashboard(property), event.currentTarget)}, 'Encher'));
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
  signals.onFill = () => fillTank(ref, signals.fuel.capacity_eur, () => renderPropertyDashboard(property));
  const unattributed = metrics.openai_usage.unattributed;
  const dials = (skin()?.instruments || plainInstruments)(ref, signals);
  dials.find(dial => dial.classList.contains('gauge-heat'))?.append(heatLimit(property, signals.hoursMax));
  dials.find(dial => dial.classList.contains('gauge-fuel'))?.append(fuelFill(property, signals.fuel));
  return el('article', {class: 'card cluster'},
    el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, word('cluster.eyebrow', 'PAINEL DO IMÓVEL')), el('h2', {}, ref)),
      el('span', {class: 'muted small'}, `Última leitura ${ago(data.last_read_at)}`)),
    tripComputer(property, signals.petrol),  // first, above the instruments, in one compact line (26/09)
    el('div', {class: 'cluster-gauges'}, dials),
    el('div', {class: 'cluster-odometers'},
      odometer(data.answered, 'Respostas enviadas'),
      odometer(data.customers_active || 0, 'Clientes ativos'),  // 06/10: as the card, the new requests too
      odometer(data.customers, 'Clientes'),
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
    unattributed.calls ? el('p', {class: 'cluster-note'},
      `${unattributed.calls} pedido(s) à API anteriores a 24/09 (${costText(unattributed.cost_usd)}) não guardaram `
      + 'o imóvel: contam no custo total do Painel, mas não aqui.') : null);
}

// The property's rhythm (requests in, replies out), its own card after the lists since 26/09.
function propertyChartCard(property, data, metrics) {
  const period = el('select', {class: 'period-select', 'aria-label': 'Período do gráfico'},
    [...$('chart-period').options].map(option => el('option', {value: option.value}, option.textContent)));
  period.value = $('chart-period').value;
  period.addEventListener('change', () => {  // the same period as the Painel's chart, in both places
    $('chart-period').value = period.value;
    try { localStorage.setItem('bot-mail-period-2', period.value); } catch { /* Storage may be unavailable. */ }
    renderPropertyDashboard(property);
  });
  return el('article', {class: 'card cluster-chart-card'},
    el('div', {class: 'section-heading'}, el('p', {class: 'eyebrow'}, word('cluster.chart', 'O RITMO DESTE IMÓVEL')), period),
    chart(data.by_day, metrics.bucket_days || 1),
    el('div', {class: 'legend'}, el('span', {class: 'requests'}, 'Pedidos recebidos'), el('span', {class: 'sent'}, 'Respostas enviadas')));
}

// The Painel's numbers, for this property only (26/09), above its instruments since 04/10 (ten since 06/10); like
// the Painel's, they only inform (27/09). 06/10: the period of analysis between the two rows, as in the Painel; redraw,
// this property's panel once it changes.
function propertyMetrics(data, redraw) {
  return el('div', {class: 'metrics property-metrics'},
    metricCard(data.customers || 0, 'Total de clientes', null, {title: CUSTOMERS_HOVER}),  // 06/10: the two totals first
    metricCard(data.customers_active || 0, 'Clientes ativos', null, {title: ACTIVE_HOVER}),
    metricCard(data.pending, 'Pedidos por responder', null, {title: queueHover([data], QUEUE_SHOWS.pending)}),
    metricCard(data.drafts, 'Rascunhos prontos', 'ok', {title: queueHover([data], QUEUE_SHOWS.drafts)}),
    metricCard(data.blocked, 'Bloqueados', 'warn', {title: queueHover([data], QUEUE_SHOWS.blocked)}),
    metricCard(data.owners_pending || 0, 'Proprietários por responder', 'warn'),  // 04/10: the Painel's fourth column too
    metricCard(data.attention, 'A precisar de atenção', 'bad', {title: queueHover([data], QUEUE_SHOWS.attention)}),
    periodRow(redraw),
    ...periodCards(data));
}

// The customers' satisfaction with this property, always in view under its instruments (26/09): one dial per part of
// the after-visit survey; with no answer yet, the needles rest at the middle.
function satisfactionCard(property) {
  const report = property.survey_report;
  if (!report) return null;
  return el('article', {class: 'card satisfaction-card'},
    el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, 'SATISFAÇÃO DOS CLIENTES'), el('h2', {}, 'O que dizem depois da visita')),
      el('span', {class: 'tag' + (report.alerts ? ' warn' : '')}, `${report.responses} resposta(s)` + (report.alerts ? ` · ${report.alerts} com alerta` : ''))),
    qualityGauges(report, 'imovel:satisfaction:' + property.reference),
    el('p', {class: 'muted small'}, report.responses
      ? `Continua interessado: sim ${report.interest.sim} · talvez ${report.interest.talvez} · não ${report.interest['não']}. O detalhe de cada resposta está no relatório, no cartão do imóvel.`
      : 'Ainda sem respostas ao inquérito: os ponteiros ficam a meio até chegarem.'));
}

// The short-list switch (26/09), the same in Imóveis and in the files of Contactos: lit when the customer is on the list
// (short list, chosen or reserve); a click puts them on it or takes them off (asking first for the chosen and the reserve).
const SELECTION_LABEL = {shortlist: 'Na short list', chosen: 'Selecionado', suplente: 'Suplente'};
function shortlistToggle(status, name, change) {
  // 05/10: on, silver on the short list, gold when selected
  return el('button', {type: 'button', class: 'shortlist-toggle' + (status ? ' on ' + status : ''), 'aria-pressed': String(!!status),
    title: status ? 'Carrega para tirar da short list' : 'Carrega para juntar à short list (no topo de Clientes)',
    onclick: event => run(async () => {
      if (status && status !== 'shortlist' && !confirm(`Tirar ${name} da short list? Deixa de ser ${SELECTION_LABEL[status].toLowerCase()}.`)) return;
      await change(status ? null : 'shortlist');
      toast(status ? `${name} saiu da short list.` : `${name} está na short list (vê-a no topo de Clientes).`);
    }, event.currentTarget)}, status ? `★ ${SELECTION_LABEL[status] || 'Na short list'}` : '☆ Short list');
}

// Who already visited this property (26/09): the finalists in the making — each with the survey, the file and where
// they stand in the selection; «+ Short list» puts them on the board at the top of Contactos.
function visitorsCard(property) {
  const slots = (property.visits?.slots || []).filter(slot => slot.check?.attended != null)
    .sort((a, b) => b.at.localeCompare(a.at));
  const came = slots.filter(slot => slot.check.attended === true), missed = slots.filter(slot => slot.check.attended === false);
  const row = slot => {
    const survey = slot.survey;
    return el('div', {class: 'client-row visitor-row'},
      el('span', {}, el('strong', {}, shortName(slot.name) || slot.customer), el('span', {class: 'muted small'}, ' · ' + slotLabel(slot.at))),
      survey ? el('span', {class: 'tag ' + (['imovel', 'consultor', 'marcacao'].some(key => survey[key] <= 2) || survey.interesse === 'não' ? 'warn' : 'draft')},
        `imóvel ${survey.imovel ?? '–'} · consultor ${survey.consultor ?? '–'} · marcação ${survey.marcacao ?? '–'}`
          + (survey.interesse ? ` · ${survey.interesse}` : '')) : el('span', {class: 'muted small'}, 'sem inquérito'),
      fichaTag(slot.ficha),
      // 04/10: here the short list is only shown; it changes in Contactos (the link above)
      el('span', {class: 'tag ' + (slot.selection === 'chosen' ? 'golden' : slot.selection === 'shortlist' ? 'silver' : slot.selection ? 'draft' : ''),
        title: 'Muda-se em Clientes, na short list'},
        slot.selection ? `★ ${SELECTION_LABEL[slot.selection] || 'Na short list'}` : '☆ Fora da short list'));
  };
  return el('article', {class: 'card visitors-card'},
    el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, 'QUEM JÁ VISITOU · FINALISTAS'), el('h2', {}, 'Os que vieram à visita')),
      el('div', {class: 'row'}, el('button', {type: 'button', class: 'link', onclick: () => showTab('contacts')}, 'Short list em Clientes →'),
        el('span', {class: 'tag'}, `${came.length} visitaram`))),
    came.length ? el('div', {class: 'client-list'}, came.map(row))
      : el('p', {class: 'muted small'}, 'Ainda ninguém registado como tendo vindo: marca-o em Visitas, depois de cada visita.'),
    missed.length ? el('p', {class: 'muted small'}, `Não apareceram: ${missed.map(slot => shortName(slot.name) || slot.customer).join(', ')}.`) : null);
}

// 04/10: beside «Quem já visitou», in Imóveis: the one selected (gold) and the reserve, with their documents — only shown;
// the choice is made in Clientes, on the short list.
function selectedCard(items) {
  const chosen = items.find(item => item.status === 'chosen'), reserve = items.find(item => item.status === 'suplente');
  const docs = item => !item.docs_requested_at ? el('span', {class: 'tag'}, 'documentos por pedir')
    : item.documents?.complete ? el('span', {class: 'tag visit'}, 'documentos completos')
    : el('span', {class: 'tag warn', title: 'Faltam: ' + (item.documents?.missing || []).join(', ')},
      `faltam ${(item.documents?.missing || []).length} documento(s)`);
  const person = (item, main) => el('div', {class: 'selected-person'},
    el('strong', {class: main ? 'selected-name' : ''}, shortName(item.name) || item.email),
    el('div', {class: 'muted small'}, item.email),
    el('div', {class: 'row selected-tags'}, docs(item),
      item.visit?.at && el('span', {class: 'muted small'}, (item.visit.attended ? 'visitou ' : 'visita ') + slotLabel(item.visit.at))));
  return el('article', {class: 'card selected-card'},
    el('div', {class: 'section-heading'},
      el('div', {}, el('p', {class: 'eyebrow'}, 'SELECIONADOS'), el('h2', {}, 'A escolha final')),
      el('button', {type: 'button', class: 'link', onclick: () => showTab('contacts')}, 'Clientes →')),
    chosen ? person(chosen, true)
      : el('p', {class: 'muted small'}, 'Ainda ninguém selecionado. Seleciona em Clientes, na short list.'),
    reserve && el('div', {class: 'selected-reserve'}, el('p', {class: 'eyebrow'}, 'SUPLENTE'), person(reserve, false)));
}

// Black list (the owner decided): never queued again, whatever they write. Grey list (the customer opted out,
// 26/09): we never write first again, but what they write still comes in and can be answered.
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
      ? 'Disseram que não têm interesse: não recebem mais nada nosso (lembretes, rondas, fecho). Se voltarem a escrever, o email entra na fila e podes responder.'
      : 'Por decisão tua: nunca mais entram em Emails, mesmo que escrevam, nem recebem envios automáticos.'),
    el('div', {class: 'client-list'}, customers.length ? customers.map(customer => el('div', {class: 'client-row'},
      el('span', {}, shortName(customer.name) || customer.email,
        customer.reason ? el('span', {class: 'muted small ignore-reason'}, customer.reason) : null),
      el('button', {class: 'link', onclick: event => run(async () => {
        done(await call('api/contacts/ignore', {property_ref: property.reference, email: customer.email, ignored: false}));
        toast(`${shortName(customer.name) || customer.email} deixou de ser ignorado(a).`);
      }, event.currentTarget)}, 'Deixar de ignorar')))
      : el('p', {class: 'muted small'}, 'Ninguém.')),
    el('div', {class: 'row'}, input, el('button', {onclick: event => run(async () => {
      if (!input.value.trim()) throw new Error('Escreve o email.');
      done(await call('api/contacts/ignore', {property_ref: property.reference, email: input.value.trim(), ignored: true,
        kind, reason: grey ? 'Cliente disse que não tem interesse.' : ''}));
      toast(`Acrescentado à ${grey ? 'greylist' : 'blacklist'}.`);
    }, event.currentTarget)}, 'Acrescentar')));
}

// 04/10: the test property is kept out of the Painel's numbers, but its panel in Imóveis still shows: what the Painel
// knows of it (its queue in numbers, its tank, its reply-time limit) and zeros for the rest, the dials resting at zero.
function testPropertyData(ref, metrics) {
  const row = (metrics.test_properties || []).find(item => item.property_ref === ref);
  const tank = (metrics.test_tanks || []).find(item => item.property_ref === ref);
  if (!row && !tank) return null;
  return {property_ref: ref, pending: 0, drafts: 0, blocked: 0, attention: 0, answered: 0, customers: 0, visits_booked: 0,
    reply_hours: null, reply_hours_max: 24, queue: [], answered_customers: [], last_read_at: null, petrol: null,
    by_day: (metrics.by_day || []).map(day => ({...day, requests: 0, sent: 0})),
    api_fuel: tank?.api_fuel || fuelOf(ref) || metrics.api_fuel, openai_usage: tank?.openai_usage || null,
    clients: {ok: 0, pending: 0, booked: 0, outra_data: 0, nao_quer: 0},
    ...row, ignored: {black: 0, grey: 0, ...(row?.ignored || {})}, test: true};
}
async function renderPropertyDashboard(property, slide = '') {
  // Only the latest request draws: switching property mid-load must not be overwritten by the older one.
  const token = renderPropertyDashboard.token = (renderPropertyDashboard.token || 0) + 1;
  await run(async () => {
    const ref = property.reference;
    const metrics = await call('api/metrics', {days: chartDays(), reply_window: replyWindow()});
    const selection = ((await call('api/contacts')).selection || []).filter(item => item.property_ref === ref);
    const ignored = await call('api/contacts/ignored', {property_ref: ref});
    const data = metrics.properties.find(item => item.property_ref === ref) || testPropertyData(ref, metrics);
    if (token !== renderPropertyDashboard.token || !data) return;
    // 04/10: the numbers first, above the instruments
    const wrap = el('div', {class: slide}, propertyMetrics(data, () => renderPropertyDashboard(property)),
      propertyCluster(property, data, metrics),
      satisfactionCard(property),
      // 04/10: «Quem já visitou» and, beside it, a little narrower, the selected; under them, side by side, the blacklist
      // and the greylist; the last round went to Visitas (where it already was, in full)
      el('div', {class: 'finalists-row'}, visitorsCard(property), selectedCard(selection)),
      el('div', {class: 'dashboard-lists ignore-lists'},
        ignoreListCard(property, 'black', ignored.customers.filter(customer => customer.kind === 'black')),
        ignoreListCard(property, 'grey', ignored.customers.filter(customer => customer.kind === 'grey'))),
      propertyChartCard(property, data, metrics));
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
  // 02/10: the program puts it under every AI draft's closing; one or more lines (a bigger signature)
  const signature = el('textarea', {rows: 3, placeholder: 'ex.: Equipa APalace Imobiliária\nTel. … · www.…'}, settings.voice.signature || '');
  const senderName = el('input', {value: settings.voice.sender_name || '', placeholder: 'vazio: só o endereço de email'});
  const replySubject = el('input', {value: settings.voice.reply_subject || ''});
  const visits = settings.voice.visits || {};
  const slot = el('input', {type: 'number', min: 10, max: 180, step: 5, value: visits.slot_minutes || 30});
  const rental = el('input', {value: visits.rental || '', placeholder: 'ex.: 15 a 20 minutos'});
  const sale = el('input', {value: visits.sale || '', placeholder: 'ex.: 30 a 40 minutos'});
  const reminders = settings.voice.reminders || {day2: '', day4: ''};
  const reminderDay2 = el('textarea', {rows: 2, placeholder: 'ex.: Ainda precisa de alguma informação sobre o imóvel?'}, reminders.day2 || '');
  const reminderDay4 = el('textarea', {rows: 2, placeholder: 'ex.: Ficamos à disposição se ainda tiver interesse em visitar.'}, reminders.day4 || '');
  const visitsClosed = el('textarea', {rows: 4, placeholder: 'ex.: Agradecemos o interesse. As visitas a este imóvel já estão fechadas.'}, settings.voice.visits_closed || '');
  const consentRequest = el('textarea', {rows: 4, placeholder: 'ex.: Podemos guardar o seu contacto para futuras oportunidades semelhantes? Responda "sim" se concordar.'}, settings.voice.consent_request || '');
  const digestRecipient = el('input', {type: 'email', value: settings.voice.digest_recipient || '', placeholder: 'o teu email: recebe as cópias e o resumo de todos'});
  // 30/09: the prompts (behaviour, after the visit, reminders, booked and visited, documents) are in the Oficina now
  // 27/09: the hours behind two of the dots in Comunicações' table of customers
  const alerts = settings.voice.alerts || {our_turn_hours: 48, no_visit_hours: 96};
  const ourTurnHours = el('input', {type: 'number', min: 1, max: 720, value: alerts.our_turn_hours});
  const noVisitHours = el('input', {type: 'number', min: 1, max: 720, value: alerts.no_visit_hours});
  // The AI engine (27/09): a console of its own, one button per model, as modes (ECO, TURBO…), each with its prices
  // and what 100 interactions cost here — the price to quote a client. A click switches the model for everything.
  // 29/09: it moved to the Oficina, with the token prices (renderWorkshop)
  $('voice-form').replaceChildren(el('p', {class: 'eyebrow'}, 'VOZ ', kind('voice')),
    choice('greeting', 'Saudação'), choice('languages', 'Idiomas'), choice('closing', 'Fecho'),
    el('label', {class: 'field'}, 'Assinatura: o programa põe-na por baixo do fecho de cada resposta da IA, sempre igual e sem '
      + 'tradução (pode ter várias linhas, até 8)', signature),
    el('label', {class: 'field'}, 'Nome do remetente, ao lado do endereço', senderName),
    el('label', {class: 'field'},
      'Assunto das respostas a pedidos do portal ({imovel} e {referencia}). Nas respostas do próprio cliente mantém-se o assunto dele.',
      replySubject),
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
    el('p', {class: 'eyebrow voice-section'}, 'BOLINHAS DA TABELA DE CLIENTES'),
    el('p', {class: 'step voice-section'},
      'Em Emails, ao lado de cada nome. Vermelha: nunca nos respondeu, ou respondeu sem nada do que pedimos. '
      + 'Verde: ficha completa. As outras duas contam horas:'),
    el('div', {class: 'grid'},
      el('label', {class: 'field'}, 'Laranja: à espera de resposta nossa há mais de … horas', ourTurnHours),
      el('label', {class: 'field'}, 'Azul (em vez da verde): ficha completa há mais de … horas sem data de visita', noVisitHours)),
    el('p', {class: 'eyebrow voice-section'}, 'PONTO DE SITUAÇÃO ', kind('voice')),
    el('p', {class: 'step voice-section'},
      'O relatório de cada imóvel está no bloco de notas do Painel. Vai ao proprietário (o email dele fica em Imóveis), '
      + 'com cópia para este endereço, ou só para este endereço, para o reencaminhares; daqui também recebes o resumo de '
      + 'todos os imóveis. Nada sai sem confirmares.'),
    el('label', {class: 'field'}, 'O teu email para o ponto de situação', digestRecipient),
    el('div', {class: 'actions'}, el('button', {class: 'primary', onclick: event => run(async () => {
      const choices = Object.fromEntries(Object.entries(selects).map(([key, select]) => [key, select.value]));
      settings = await call('api/voice', {...choices, signature: signature.value,
        sender_name: senderName.value, reply_subject: replySubject.value,
        visits: {slot_minutes: Number(slot.value), rental: rental.value, sale: sale.value},
        reminders: {day2: reminderDay2.value, day4: reminderDay4.value},
        alerts: {our_turn_hours: Number(ourTurnHours.value), no_visit_hours: Number(noVisitHours.value)},
        visits_closed: visitsClosed.value, consent_request: consentRequest.value, digest_recipient: digestRecipient.value});
      renderSettings(); await refreshState(); toast('Voz guardada.');
    }, event.currentTarget)}, 'Guardar voz')));
}

document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
$('queue').addEventListener('change', () => { showNotes([]); renderState(); });  // 02/10: the notes were about the other property
$('workshop-link').addEventListener('click', showWorkshop);
$('card-sort').value = cardSort();
$('card-sort').addEventListener('change', event => {
  cardSortChoice = event.currentTarget.value;
  try { localStorage.setItem('aria-card-sort', cardSortChoice); } catch { /* only this page view keeps it */ }
  renderState();
});
$('emails').addEventListener('change', updateSelection);
// 02/10: while the Gmail is being read, «2 Gerar respostas» stays off (it would write for emails still coming in)
$('read').addEventListener('click', event => {
  const button = event.currentTarget;
  // 02/10: what the read is doing, on the button itself, asked every half second while it lasts
  // in up to three lines beside the button: the step, how far, and the email being read now
  const box = $('read-progress');
  const shown = progress => progress.stage === 'connect' ? [el('strong', {}, 'A ligar ao Gmail…')]
    : progress.stage === 'read' ? [el('strong', {}, `A ler o email ${progress.number} de ${progress.total}`),
      progress.sender && el('span', {}, `De: ${progress.sender}`), progress.subject && el('span', {}, `«${progress.subject}»`)]
    : progress.stage === 'save' ? [el('strong', {}, 'A guardar os emails novos e a ver as respostas do Gmail…')] : null;
  box.hidden = false; box.replaceChildren(el('strong', {}, 'A começar…'));
  const poll = setInterval(async () => {
    try {
      const response = await fetch('api/read/progress', {headers: {'X-Bot-Mail-Token': TOKEN}});
      const lines = shown(await response.json());
      if (lines) box.replaceChildren(...lines.filter(Boolean));
    } catch { /* only the lines: the read goes on */ }
  }, 500);
  return run(async () => {
  $('generate-api').dataset.busy = '1'; $('generate-api').disabled = true;
  try { state = await call('api/read', {}); } finally { $('generate-api').dataset.busy = ''; clearInterval(poll); }
  stepsDone.read = true; renderState();
  if (state.added) playSound('read');
  // Replies written straight in Gmail (found in All Mail or Sent) answer their emails here too.
  const direct = state.direct ? ` ${state.direct} resposta(s) tua(s) enviada(s) diretamente do Gmail registada(s).` : '';
  toast((state.added ? `${state.added} email(s) novo(s).` : 'Leitura concluída: nada de novo.') + direct);
  }, button).finally(() => { clearInterval(poll); box.hidden = true; box.replaceChildren(); });
});
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
// 27/09: in «Modo: só API», the ChatGPT way stays at hand, folded under «Gerar respostas»: the same prompt (selected
// emails and extra instructions), copied, and its answer pasted back into the same drafts as the API's.
$('gpt-prompt').addEventListener('click', event => run(async () => {
  const ids = selectedIds();
  if (!ids.length) throw new Error('Seleciona pelo menos um email.');
  const {prompt} = await call('api/prompt', {property_ref: queueRef(), ids, extra: $('extra').value});
  $('gpt-prompt-text').textContent = prompt; $('gpt-prompt-text').hidden = false;
  await copyText(prompt, 'Prompt copiado. Cola-o numa conversa do ChatGPT e traz a resposta para aqui.', $('gpt-box'));
}, event.currentTarget));
$('gpt-paste').addEventListener('click', event => run(async () => {
  const text = $('gpt-answer').value;
  if (!text.trim()) throw new Error('Cola primeiro a resposta do ChatGPT.');
  const result = await call('api/paste', {property_ref: queueRef(), text});
  state = result.state; keepSteps(renderState);
  showNotes(result.notes);
  $('gpt-answer').value = '';
  toast(`${result.saved} rascunho(s) guardado(s)` + (result.visits ? ` e ${result.visits} marcação(ões) de visita` : '')
    + '. Revê-os antes de enviar.');
}, event.currentTarget));
// 02/10: the batches as their own calls, up to 4 at a time, each one's drafts shown as soon as it comes back (the last
// before the first, if it is quicker) — no waiting for all of them
$('generate-api').addEventListener('click', event => run(async () => {
  const ids = selectedIds(), ref = queueRef(), extra = $('extra').value;
  if (!ids.length) throw new Error('Seleciona pelo menos um email.');
  const {batches, context_used: contextUsed} = await call('api/prompt/plan', {property_ref: ref, ids, extra});
  stepsDone.generated = true;
  markGenerated();
  const totals = {saved: 0, visits: 0, reviewed: 0, cost: 0, tokens: 0, notes: [], prompts: [], errors: [], model: ''};
  let next = 0, done = 0;
  const one = async () => {
    while (next < batches.length) {
      const batch = batches[next++];
      try {
        const result = await call('api/prompt/generate', {property_ref: ref, ids: batch, extra});
        totals.saved += result.saved; totals.visits += result.visits || 0; totals.reviewed += result.reviewed || 0;
        totals.cost += result.cost_usd || 0; totals.model = result.model || totals.model;
        totals.tokens += (result.tokens?.prompt_tokens || 0) + (result.tokens?.completion_tokens || 0);
        totals.notes.push(...(result.notes || [])); totals.prompts.push(...(result.prompts || []));
        if (result.review_error) totals.errors.push(`revisão: ${result.review_error}`);
        if (result.generation_error) totals.errors.push(result.generation_error);
        applyFuel(result.fuel, ref);
      } catch (error) { totals.errors.push(error.message); }
      done += batch.length;
      // what is ready so far, at once (always the state as it is now: batches come back in any order)
      state = await call('api/state'); keepSteps(renderState);
      if (done < ids.length) toast(`${done} de ${ids.length} rascunho(s) prontos… os outros continuam a ser escritos.`);
    }
  };
  await Promise.all(Array.from({length: Math.min(4, batches.length)}, one));
  showNotes(totals.notes);
  markStep('prepare-step', true); markStep('import-step', true);  // this one button does the work of both
  $('sent-prompt').textContent = totals.prompts.join('\n\n════════ lote seguinte ════════\n\n');
  $('sent-prompt-box').hidden = !totals.prompts.length;
  const cost = totals.cost ? ` · ${costText(totals.cost)}` : '';
  toast(`${totals.saved} rascunho(s) gerado(s) com ${totals.model || 'a API'}`
    + (totals.visits ? ` e ${totals.visits} marcação(ões) de visita` : '')
    + (totals.tokens ? ` (${totals.tokens.toLocaleString('pt-PT')} tokens${cost}, ${batches.length} chamada(s); a maior usou `
      + `${String(contextUsed).replace('.', ',')}% do contexto)` : '') + '.'
    + (totals.reviewed ? ` O revisor leu ${totals.reviewed}.` : '')
    + (totals.errors.length ? ` Atenção: ${totals.errors.join(' · ')}` : '') + ' Revê-os antes de enviar.',
    totals.errors.length ? 'warn' : 'ok');
}, event.currentTarget));
$('paste').addEventListener('click', event => run(async () => {
  const text = $('answer').value;
  if (!text.trim()) throw new Error('Cola primeiro a resposta do ChatGPT.');
  const result = await call('api/paste', {property_ref: queueRef(), text});
  state = result.state; keepSteps(renderState);
  showNotes(result.notes);
  $('answer').value = '';
  const summary = `${result.saved} rascunho(s) guardado(s)` + (result.visits ? ` e ${result.visits} marcação(ões) de visita` : '') + '.';
  $('import-status').hidden = false;
  $('import-status').textContent = `✓ ${summary} Revê-os no passo 01, ou cola outra resposta aqui para acrescentar mais.`;
  markStep('import-step', true);
  toast(summary + ' Revê-os no passo 01 antes de enviar.');
}, event.currentTarget));
$('answer').addEventListener('input', () => { $('import-status').hidden = true; markStep('import-step', false); });
$('preview').addEventListener('click', event => run(sendApproved, event.currentTarget).then(refreshSendButton));
// 02/10: «Rever os selecionados» — the reviewer, only when the owner asks; the marks show under each draft
$('review-run').addEventListener('click', event => run(async () => {
  const ids = selectedIds().filter(id => {
    const email = (currentQueue()?.emails || []).find(item => item.id === id);
    return String(email?.reply_text || '').trim().length >= 40;
  });
  if (!ids.length) throw new Error('Nenhum dos emails selecionados tem um rascunho para rever (gera-os primeiro, no passo 2).');
  const result = await call('api/review', {property_ref: queueRef(), ids});
  applyFuel(result.fuel, queueRef()); state = result.state; keepSteps(renderState);
  toast(result.reviewed ? `O revisor leu ${result.reviewed} rascunho(s): vê a nota e os avisos por baixo de cada um.`
    : 'O revisor não devolveu nada: tenta outra vez.', result.reviewed ? 'ok' : 'warn');
}, event.currentTarget));
$('listing-prompt').addEventListener('click', event => run(async () => {
  const {prompt} = await call('api/property/prompt', {listing_url: $('listing-url').value});
  $('listing-prompt-text').textContent = prompt;
  await copyText(prompt, 'Prompt copiado. Cola-o no ChatGPT e traz a resposta.', $('listing-prompt-box'));
}, event.currentTarget));
$('listing-extract').addEventListener('click', event => run(async () => {
  const {fields} = await call('api/property/extract', {text: $('listing-text').value, listing_url: $('listing-url').value});
  const existing = settings.properties.some(property => property.reference === fields.reference);
  openPropertyEditor({...fields, sender: null}, existing ? fields.reference : null);
  $('listing-text').value = '';
  toast('Campos extraídos pela API: revê-os antes de guardar.', 'warn');
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
  const result = await call('api/property/save', {fields, first_read_days: editorRef ? undefined : Number($('f-first-read').value) || undefined});
  settings = result.settings; editorRef = result.reference;
  selectProperty(result.reference, 0, false); renderSettings(); showPropertiesView('list'); await refreshState();
  toast(`Imóvel ${result.reference} ${result.created ? 'criado' : 'atualizado'}. Revê a base de conhecimento na pasta do imóvel.`);
}, event.currentTarget));

applySkin();  // here, once everything it draws with is defined
// 27/09: the cards drawn once more after the settings arrive (the model's name and the API buttons depend on them)
run(async () => { await loadMetrics(); await loadDigest(); await refreshState(); await loadSettings(); renderState(); });
