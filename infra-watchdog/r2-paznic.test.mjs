// Teste pentru paznicul de cost R2. Rulare: node --test infra-watchdog/r2-paznic.test.mjs
// Fara retea: fetch si KV sunt inlocuite cu dubluri care tin minte ce li s-a cerut.
import test from "node:test";
import assert from "node:assert/strict";
import {
  GRATUIT, ESECURI_PANA_LA_TAIERE, CHEIE_KV,
  clasifica, aduna, decide, stareaLunii, ruleazaPaznic,
} from "./r2-paznic.js";

const ACUM = new Date("2026-11-11T12:00:00Z");

function kvFals(initial) {
  const date = new Map(initial ? [[CHEIE_KV, JSON.stringify(initial)]] : []);
  const scrieri = [];
  return {
    scrieri,
    async get(k) { return date.has(k) ? date.get(k) : null; },
    async put(k, v) { scrieri.push(v); date.set(k, v); },
    stare() { return date.has(CHEIE_KV) ? JSON.parse(date.get(CHEIE_KV)) : null; },
  };
}

function raspuns(corp, status = 200) {
  return { ok: status >= 200 && status < 300, status, async json() { return corp; } };
}

/** fetch fals: `consum` = {operatii: {tip: n}, stocare: {bucket: octeti}}; `domenii` = starea publica. */
function fetchFals({ consum, domenii, graphqlPica = false, putPica = false }) {
  const apeluri = [];
  const fn = async (url, init) => {
    const cale = url.replace("https://api.cloudflare.com/client/v4", "");
    apeluri.push({ metoda: init.method, cale, corp: init.body ? JSON.parse(init.body) : undefined });
    if (cale === "/graphql") {
      if (graphqlPica) return raspuns({ data: null, errors: [{ message: "analytics jos" }] }, 200);
      return raspuns({
        data: { viewer: { accounts: [{
          r2OperationsAdaptiveGroups: Object.entries(consum.operatii || {}).map(([actionType, requests]) => ({ sum: { requests }, dimensions: { actionType } })),
          r2StorageAdaptiveGroups: Object.entries(consum.stocare || {}).map(([bucketName, payloadSize]) => ({ max: { payloadSize, metadataSize: 0 }, dimensions: { bucketName } })),
        }] } },
        errors: null,
      });
    }
    if (init.method === "PUT" && putPica) return raspuns({ success: false, errors: [{ message: "interzis" }] }, 403);
    if (cale.endsWith("/domains/custom") && init.method === "GET") {
      return raspuns({ success: true, result: { domains: domenii.custom.map((d) => ({ ...d })) } });
    }
    if (cale.includes("/domains/custom/") && init.method === "PUT") {
      const nume = decodeURIComponent(cale.split("/").pop());
      domenii.custom.find((d) => d.domain === nume).enabled = false;
      return raspuns({ success: true, result: {} });
    }
    if (cale.endsWith("/domains/managed") && init.method === "GET") {
      return raspuns({ success: true, result: { enabled: domenii.r2dev } });
    }
    if (cale.endsWith("/domains/managed") && init.method === "PUT") {
      domenii.r2dev = false;
      return raspuns({ success: true, result: {} });
    }
    return raspuns({ success: false, errors: [{ message: "ruta neasteptata " + cale }] }, 404);
  };
  fn.apeluri = apeluri;
  return fn;
}

function mediu(kv, extra = {}) {
  return { WATCHDOG_KV: kv, R2_PAZNIC_BUCKET: "izz-imagini", CF_API_TOKEN_R2: "t", CF_ACCOUNT_ID: "cont", ...extra };
}

function posta() {
  const trimise = [];
  const fn = async (_env, subiect, text) => { trimise.push({ subiect, text }); return true; };
  fn.trimise = trimise;
  return fn;
}

// console.error e suprafata de alerta; in teste il tinem deoparte ca sa nu polueze iesirea.
function faraZgomot(t) {
  const erori = [];
  t.mock.method(console, "error", (m) => erori.push(String(m)));
  t.mock.method(console, "log", () => {});
  return erori;
}

test("clasifica: listele din pagina de preturi", () => {
  assert.equal(clasifica("PutObject"), "a");
  assert.equal(clasifica("ListObjects"), "a");
  assert.equal(clasifica("GetObject"), "b");
  assert.equal(clasifica("HeadObject"), "b");
  assert.equal(clasifica("DeleteObject"), "gratis");
  assert.equal(clasifica("OperatieNoua"), "necunoscut");
});

test("aduna: tipul necunoscut se socoteste la clasa scumpa si se raporteaza", () => {
  const t = aduna([
    { actionType: "GetObject", requests: 100 },
    { actionType: "PutObject", requests: 7 },
    { actionType: "DeleteObject", requests: 999 },
    { actionType: "OperatieNoua", requests: 5 },
  ]);
  assert.deepEqual(t, { clasa_a: 12, clasa_b: 100, necunoscute: ["OperatieNoua"] });
});

test("decide: pragurile de 70% si 90%, pe fiecare contor separat", () => {
  const zero = { clasa_a: 0, clasa_b: 0, stocare_octeti: 0 };
  assert.equal(decide(zero).operatii, "ok");
  assert.equal(decide({ ...zero, clasa_b: GRATUIT.clasa_b * 0.69 }).operatii, "ok");
  assert.equal(decide({ ...zero, clasa_b: GRATUIT.clasa_b * 0.7 }).operatii, "avertisment");
  assert.equal(decide({ ...zero, clasa_b: GRATUIT.clasa_b * 0.9 }).operatii, "taie");
  assert.equal(decide({ ...zero, clasa_a: GRATUIT.clasa_a * 0.9 }).operatii, "taie");
  // stocarea plina NU taie citirile: se opreste altfel
  const plin = decide({ ...zero, stocare_octeti: GRATUIT.stocare_octeti * 0.95 });
  assert.equal(plin.operatii, "ok");
  assert.equal(plin.stocare, "taie");
});

test("stareaLunii: luna noua reseteaza nivelurile, dar NU reactiveaza si NU uita esecurile", () => {
  const veche = { luna: "2026-10", operatii: "taie", stocare: "avertisment", taiat: true, scrieri_oprite: true, domenii_oprite: ["img.izz.ro"], esecuri: 3, motiv_taiere: "clasa_b=91.0%" };
  const noua = stareaLunii(veche, "2026-11");
  assert.equal(noua.luna, "2026-11");
  assert.equal(noua.operatii, "ok");
  // sirul de esecuri nu tine de luna de facturare: trece peste granita
  assert.equal(noua.esecuri, 3);
  assert.equal(noua.taiat, true);
  assert.equal(noua.scrieri_oprite, true);
  assert.deepEqual(noua.domenii_oprite, ["img.izz.ro"]);
});

test("neconfigurat: nu atinge nici reteaua, nici KV", async () => {
  const kv = kvFals();
  const f = fetchFals({ consum: {}, domenii: { custom: [], r2dev: false } });
  const r = await ruleazaPaznic({ WATCHDOG_KV: kv }, { acum: ACUM, fetchFn: f });
  assert.deepEqual(r, { rulat: false, motiv: "neconfigurat" });
  assert.equal(f.apeluri.length, 0);
  assert.equal(kv.scrieri.length, 0);
});

test("bucket setat fara cheie: eroare vizibila, nu tacere", async (t) => {
  const erori = faraZgomot(t);
  const r = await ruleazaPaznic({ WATCHDOG_KV: kvFals(), R2_PAZNIC_BUCKET: "izz-imagini" }, { acum: ACUM });
  assert.equal(r.motiv, "fara-cheie");
  assert.equal(erori.length, 1);
  assert.match(erori[0], /NU e pazit/);
});

test("consum mic: nicio taiere, o singura scriere in KV, apoi zero", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  const consum = { operatii: { GetObject: 1000, PutObject: 50 }, stocare: { "izz-imagini": 5e8 } };
  for (let i = 0; i < 3; i++) {
    const f = fetchFals({ consum, domenii });
    const r = await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: f, trimiteEmail: posta() });
    assert.equal(r.decizie.operatii, "ok");
    assert.equal(f.apeluri.filter((a) => a.metoda === "PUT").length, 0);
  }
  assert.equal(kv.scrieri.length, 1, "starea neschimbata nu se rescrie");
  assert.equal(domenii.custom[0].enabled, true);
});

test("avertisment la 70%: un singur e-mail, fara taiere", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  const consum = { operatii: { GetObject: GRATUIT.clasa_b * 0.75 }, stocare: {} };
  const p = posta();
  for (let i = 0; i < 3; i++) {
    await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum, domenii }), trimiteEmail: p });
  }
  assert.equal(p.trimise.length, 1);
  assert.match(p.trimise[0].subiect, /avertisment operatii/);
  assert.equal(domenii.custom[0].enabled, true);
  assert.equal(kv.stare().taiat, false);
});

test("taiere la 90%: domeniul propriu si r2.dev se opresc, un singur anunt", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }, { domain: "vechi.izz.ro", enabled: false }], r2dev: true };
  const consum = { operatii: { GetObject: GRATUIT.clasa_b * 0.93 }, stocare: {} };
  const p = posta();
  const f = fetchFals({ consum, domenii });
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: f, trimiteEmail: p });
  assert.equal(domenii.custom[0].enabled, false);
  assert.equal(domenii.r2dev, false);
  const puturi = f.apeluri.filter((a) => a.metoda === "PUT");
  assert.equal(puturi.length, 2, "domeniul deja oprit nu se mai atinge");
  assert.ok(puturi.every((a) => a.corp.enabled === false));
  assert.equal(kv.stare().taiat, true);
  assert.deepEqual(kv.stare().domenii_oprite, ["img.izz.ro", "r2.dev"]);
  // a doua rulare, tot peste prag: nimic de oprit, niciun anunt nou, nicio scriere noua
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum, domenii }), trimiteEmail: p });
  assert.equal(p.trimise.length, 1);
  assert.match(p.trimise[0].subiect, /TAIAT/);
  assert.equal(kv.scrieri.length, 1);
});

test("reactivare manuala peste prag: se taie din nou si se anunta", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  const consum = { operatii: { GetObject: GRATUIT.clasa_b * 0.95 }, stocare: {} };
  const p = posta();
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum, domenii }), trimiteEmail: p });
  domenii.custom[0].enabled = true; // cineva il reporneste din dashboard
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum, domenii }), trimiteEmail: p });
  assert.equal(domenii.custom[0].enabled, false);
  assert.equal(p.trimise.length, 2);
  assert.match(p.trimise[1].subiect, /DIN NOU/);
});

test("stocare la prag: ridica steagul de scrieri, NU taie citirile", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  // doua bucket-uri: stocarea se aduna pe cont, nu se ia maximul
  const consum = { operatii: {}, stocare: { "izz-imagini": 5e9, altul: 4.5e9 } };
  const p = posta();
  const r = await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum, domenii }), trimiteEmail: p });
  assert.equal(r.consum.stocare_octeti, 9.5e9);
  assert.equal(kv.stare().scrieri_oprite, true);
  assert.equal(kv.stare().taiat, false);
  assert.equal(domenii.custom[0].enabled, true);
  assert.match(p.trimise[0].subiect, /scrieri oprite/);
});

test("masuratoare cazuta: taie abia dupa pragul de esecuri la rand", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  const p = posta();
  for (let i = 1; i < ESECURI_PANA_LA_TAIERE; i++) {
    await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum: {}, domenii, graphqlPica: true }), trimiteEmail: p });
    assert.equal(domenii.custom[0].enabled, true, `inca deschis dupa ${i} esecuri`);
    assert.equal(kv.stare().esecuri, i);
  }
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum: {}, domenii, graphqlPica: true }), trimiteEmail: p });
  assert.equal(domenii.custom[0].enabled, false);
  assert.equal(kv.stare().taiat, true);
  assert.match(kv.stare().motiv_taiere, /masuratoare esuata/);
});

test("o masuratoare reusita readuce contorul de esecuri la zero", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum: {}, domenii, graphqlPica: true }), trimiteEmail: posta() });
  assert.equal(kv.stare().esecuri, 1);
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum: { operatii: {}, stocare: {} }, domenii }), trimiteEmail: posta() });
  assert.equal(kv.stare().esecuri, 0);
});

test("taierea esuata se striga la fiecare rulare si nu se marcheaza ca facuta", async (t) => {
  const erori = faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  const consum = { operatii: { GetObject: GRATUIT.clasa_b * 0.95 }, stocare: {} };
  const p = posta();
  for (let i = 0; i < 2; i++) {
    await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum, domenii, putPica: true }), trimiteEmail: p });
  }
  assert.equal(p.trimise.length, 2);
  assert.match(p.trimise[0].subiect, /TAIEREA A ESUAT/);
  assert.equal(kv.stare().taiat, false);
  assert.ok(erori.some((e) => /NU a putut fi oprit/.test(e)));
});

test("e-mailul care pica nu opreste taierea", async (t) => {
  faraZgomot(t);
  const kv = kvFals();
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  const consum = { operatii: { GetObject: GRATUIT.clasa_b * 0.95 }, stocare: {} };
  const r = await ruleazaPaznic(mediu(kv), {
    acum: ACUM, fetchFn: fetchFals({ consum, domenii }),
    trimiteEmail: async () => { throw new Error("adresa neverificata"); },
  });
  assert.equal(domenii.custom[0].enabled, false);
  assert.equal(r.stare.taiat, true);
});

test("stareaLunii: un contor de esecuri stricat devine zero, nu NaN", () => {
  assert.equal(stareaLunii({ luna: "2026-11", esecuri: "x" }, "2026-11").esecuri, 0);
  assert.equal(stareaLunii({ luna: "2026-10", esecuri: null }, "2026-11").esecuri, 0);
});

test("dupa o taiere veche si o repornire manuala, taierea pe nevazute functioneaza in continuare", async (t) => {
  faraZgomot(t);
  // `taiat` a ramas ridicat de la o taiere trecuta; proprietarul a repornit domeniul.
  const kv = kvFals({ luna: "2026-11", operatii: "ok", stocare: "ok", taiat: true, scrieri_oprite: false, domenii_oprite: ["img.izz.ro"], esecuri: ESECURI_PANA_LA_TAIERE - 1, motiv_taiere: "clasa_b=91.0%" });
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  const p = posta();
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum: {}, domenii, graphqlPica: true }), trimiteEmail: p });
  assert.equal(domenii.custom[0].enabled, false);
  assert.equal(p.trimise.length, 1);
  assert.match(p.trimise[0].text, /masuratoare esuata/);
  // rularea urmatoare, tot fara masuratoare: domeniul e deja oprit, deci niciun anunt nou
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum: {}, domenii, graphqlPica: true }), trimiteEmail: p });
  assert.equal(p.trimise.length, 1);
});

test("KV care nu raspunde la citire: taie in continuare, dar NU suprascrie starea", async (t) => {
  const erori = faraZgomot(t);
  const kv = kvFals({ luna: "2026-11", operatii: "taie", stocare: "ok", taiat: true, scrieri_oprite: true, domenii_oprite: ["img.izz.ro"], esecuri: 0, motiv_taiere: "clasa_b=91.0%" });
  kv.get = async () => { throw new Error("KV jos"); };
  const domenii = { custom: [{ domain: "img.izz.ro", enabled: true }], r2dev: false };
  await ruleazaPaznic(mediu(kv), { acum: ACUM, fetchFn: fetchFals({ consum: { operatii: { GetObject: GRATUIT.clasa_b * 0.95 }, stocare: {} }, domenii }), trimiteEmail: posta() });
  assert.equal(domenii.custom[0].enabled, false, "taierea nu depinde de KV");
  assert.equal(kv.scrieri.length, 0, "starea goala nu are voie sa ajunga in KV");
  assert.equal(kv.stare().scrieri_oprite, true);
  assert.ok(erori.some((m) => /citirea starii din KV a esuat/.test(m)));
});
