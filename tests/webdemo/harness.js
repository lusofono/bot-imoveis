// Minimal browser for demo-api.js in jsc: window, document, location, URL, Response.
var window = globalThis;
var toasts = [];
window.toast = function (text, kind) { toasts.push([kind, text]); };
var location = {href: 'https://demo.example/vendas/index.html', reload: function () {}};
var appended = [];
var document = {body: {append: function (node) { appended.push(node); }}, addEventListener: function () {},
  createElement: function (tag) { return {tag: tag, children: [], setAttribute: function () {}, addEventListener: function () {},
    append: function () { for (var i = 0; i < arguments.length; i++) this.children.push(arguments[i]); }}; }};
function URL(address, base) { this.pathname = address.startsWith('http') ? address.replace(/^https?:\/\/[^/]+/, '') : base.replace(/^https?:\/\/[^/]+/, '').replace(/[^/]*$/, '') + address; }
function Response(body, init) { this.body = body; this.status = init.status; this.ok = init.status < 300; }
Response.prototype.json = function () { return Promise.resolve(JSON.parse(this.body)); };
window.fetch = function (address) { return Promise.resolve(new Response('"real:' + address + '"', {status: 200})); };
// The demo's pauses (it «thinks» for a second or two, like the real page) run at once here.
globalThis.setTimeout = function (callback) { Promise.resolve().then(callback); return 0; };
