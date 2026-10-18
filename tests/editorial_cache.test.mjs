import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../static/sw.js', import.meta.url), 'utf8');
function runtime(online) {
  const saved = new Map();
  const handlers = {};
  const cache = {
    match: async key => saved.get(typeof key === 'string' ? key : key.url)?.clone(),
    put: async (key, response) => saved.set(typeof key === 'string' ? key : key.url, response.clone()),
    keys: async () => [], delete: async () => true,
  };
  const context = vm.createContext({
    Response, Request, Headers, URL,
    setTimeout: fn => { fn(); return 1; },
    self: { location: { origin: 'https://izz.ro' }, addEventListener: (name, fn) => { handlers[name] = fn; } },
    caches: { open: async () => cache, match: cache.match },
    fetch: async () => {
      if (!online) throw new Error('offline');
      return new Response('<body>Corrected current article</body>', { headers: { 'content-type': 'text/html' } });
    },
  });
  vm.runInContext(source, context);
  return { context, cache, handlers };
}

test('cached HTML declares unverified freshness, without changing cache', async () => {
  const { context, cache } = runtime(false);
  const request = new Request('https://izz.ro/local/test/');
  await cache.put(request.url, new Response('<html><body>Old article</body></html>',
    { headers: { 'content-type': 'text/html', 'content-length': '49' } }));
  context.request = request;
  const response = await vm.runInContext("reteaIntai(request, ARTICOLE, {waitUntil(){}})", context);
  assert.match(await response.text(), /actualitatea și eventualele corecții nu pot fi verificate/);
  assert.equal(response.headers.get('X-IZZ-Cached-Copy'), 'unverified');
  assert.equal(response.headers.has('content-length'), false);
  assert.doesNotMatch(await (await cache.match(request.url)).text(), /Copie salvată/);
});

test('online response replaces the old cached article', async () => {
  const { context, cache } = runtime(true);
  const request = new Request('https://izz.ro/local/test/');
  await cache.put(request.url, new Response('Old article'));
  context.request = request;
  const response = await vm.runInContext("reimprospateaza(request, ARTICOLE)", context);
  assert.match(await response.text(), /Corrected current article/);
  assert.match(await (await cache.match(request.url)).text(), /Corrected current article/);
});

test('editorial version requests bypass saved responses', () => {
  const { handlers } = runtime(false);
  let intercepted = false;
  handlers.fetch({request: new Request('https://izz.ro/editorial-revisions.json'),
    respondWith() { intercepted = true; }});
  assert.equal(intercepted, false);
});

const clientSource = fs.readFileSync(new URL('../static/editorial-updates.js', import.meta.url), 'utf8');
function reader(version = 'original', online = true) {
  const events = {};
  const status = {hidden: true, children: [], replaceChildren(node) { this.children = [node]; },
    append(node) { this.children.push(node); }};
  let resolve, reject, reloads = 0, requests = 0;
  const response = new Promise((yes, no) => { resolve = yes; reject = no; });
  const context = vm.createContext({
    document: {
      hidden: false, getElementById: () => status, querySelector: () => ({content: version}),
      createTextNode: text => ({textContent: text}),
      createElement: () => ({addEventListener(name, callback) { this[name] = callback; }}),
      addEventListener: (name, callback) => { events[name] = callback; },
    },
    navigator: {onLine: online}, location: {reload() { reloads++; }},
    addEventListener: (name, callback) => { events[name] = callback; },
    fetch: (url, options) => {
      assert.equal(url, '/editorial-revisions.json');
      assert.equal(options.cache, 'no-store');
      requests++;
      return response;
    },
  });
  vm.runInContext(clientSource, context);
  return {context, status, events, resolve, reject, reloads: () => reloads, requests: () => requests};
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test('late online revision offers reload without replacing what the reader sees', async () => {
  const page = reader();
  assert.equal(page.status.hidden, true);
  page.resolve({ok: true, json: async () => ({schema_version: 1, version: 'corrected-version'})});
  await flush();
  assert.equal(page.status.hidden, false);
  assert.match(page.status.children[0].textContent, /versiune editorială mai nouă/);
  const button = page.status.children[1];
  assert.equal(button.textContent, 'Încarcă versiunea actuală');
  assert.equal(page.reloads(), 0);
  button.click();
  assert.equal(page.reloads(), 1);
});

test('offline copies do not claim freshness and reconnect checks the new revision', async () => {
  const page = reader('original', false);
  assert.equal(page.requests(), 0);
  assert.match(page.status.children[0].textContent, /actualitatea nu poate fi verificată/);
  assert.equal(page.status.children.length, 1);
  page.context.navigator.onLine = true;
  page.events.online();
  page.resolve({ok: true, json: async () => ({schema_version: 1, version: 'withdrawal-version'})});
  await flush();
  assert.equal(page.status.children[1].type, 'button');
});

test('unchanged revision stays quiet and failed checks do not promise an update', async () => {
  const same = reader();
  same.resolve({ok: true, json: async () => ({schema_version: 1, version: 'original'})});
  await flush();
  assert.equal(same.status.hidden, true);
  const failed = reader();
  failed.reject(new Error('network unavailable'));
  await flush();
  assert.equal(failed.status.hidden, false);
  assert.match(failed.status.children[0].textContent, /nu a putut fi verificată/);
  assert.equal(failed.status.children.length, 1);
});
