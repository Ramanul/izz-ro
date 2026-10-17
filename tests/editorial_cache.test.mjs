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
