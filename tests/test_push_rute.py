"""Rutele de push si compozitia Workerului, rulate cu un KV SIMULAT.

DE CE EXISTA, PE LANGA `test_push_criptare.py`. Acolo se verifica MATEMATICA (cheile,
cifrul, semnatura). Aici se verifica LOGICA DE SERVICIU, care e exact ce nu se vede in
browser pana cand e prea tarziu:

  · plafonul de o alerta pe zi — daca nu tine, abonatii primesc doua si promisiunea
    «Zgomot zero» e incalcata de propriul nostru cod;
  · degradarea fara KV si fara chei — PR-ul asta se publica INAINTE ca tu sa creezi
    namespace-ul, deci 503-ul curat e comportamentul asteptat, nu o eroare;
  · loturile cu cursor (10 ms de CPU pe planul Free) — al doilea lot NU are voie sa se
    loveasca de plafonul scris de primul;
  · stergerea abonamentelor moarte (404/410), altfel KV-ul creste cu morti.

KV-ul e o clasa de cativa octeti, nu un emulator: implementeaza doar ce foloseste codul
(get/put/delete/list cu prefix, cursor si limit), plus contoare ca testele sa poata AFIRMA
ca nu s-a scris de doua ori. `fetch` e inlocuit cu un stub care inregistreaza cererile —
nicio cerere nu iese din masina, deci suita nu depinde de retea si nici de FCM.

Rulare manuala: `python -m pytest tests/test_push_rute.py -q -p no:randomly`
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"

NODE = shutil.which("node")
FARA_NODE = "Node lipseste: nu se poate rula codul Workerului"

# Conventia repo-ului (vezi test_calc_salariu.py): garda e la nivel de MODUL, nu pe
# fiecare test. Pe unele medii `node` pur si simplu nu e in PATH (niciun workflow din
# .github/workflows/ nu-l instaleaza, in afara de harta-data.yml), iar o garda pusa doar
# pe o parte din teste lasa restul sa ruleze `subprocess.run([None, ...])` — au ramas 18
# asa si au inrosit CI-ul in timp ce local, cu node instalat, treceau toate.
pytestmark = pytest.mark.skipif(NODE is None, reason=FARA_NODE)


PRELUDIU = r"""
/*
 * PRELUDIU de test, NU de productie. Pe Workers, `crypto`, `fetch`, `Request` si `Response`
 * sint globale oferite de runtime. In Node, `crypto` global a aparut abia in 19/20 (pina
 * atunci trebuia --experimental-global-webcrypto), iar pe 18 `fetch`/`Request` tiparesc un
 * ExperimentalWarning pe stderr. Fara puntea asta testele pica pe un runtime mai vechi
 * pentru un motiv care n-are nicio legatura cu codul verificat — si exact asa au facut in
 * CI, unde runnerul aduce alt Node decit masina de lucru.
 *
 * Se injecteaza DOAR daca lipseste: unde Node il are deja, nu se schimba nimic.
 */
import { webcrypto as __webcrypto } from 'node:crypto';
if (!globalThis.crypto) globalThis.crypto = __webcrypto;
"""


def _ruleaza(script: str) -> dict:
    """Copiaza `infra/` intr-un director temporar ca ESM si ruleaza scriptul in Node.

    Copia e necesara pentru ca Node decide formatul modulului dupa extensie: importat ca
    `.js` fara `type: module` in vreun package.json, `infra/push.js` ar fi citit drept
    CommonJS si ar cadea la primul `export`. Se copiaza TOT directorul, nu doar push.js,
    pentru ca `infra/worker.js` il importa pe `./worker-404-mirror.js` prin cale relativa.
    """
    with tempfile.TemporaryDirectory(prefix="izz-rute-") as tmp:
        dest = Path(tmp) / "infra"
        dest.mkdir()
        for sursa in INFRA.glob("*.js"):
            # Importurile relative din `infra/worker.js` poarta extensia `.js`; in copie
            # fisierul se numeste `.mjs`, deci calea se rescrie. DOAR importurile: un
            # `replace(".js'")` orb ar rescrie si sirul '/sw.js' din tabela de rute, iar
            # testul ar „verifica" altceva decat ce ruleaza in productie.
            text = re.sub(r"from '\./([^']+)\.js'", r"from './\1.mjs'",
                          sursa.read_text(encoding="utf-8"))
            (dest / (sursa.stem + ".mjs")).write_text(text, encoding="utf-8")
        proba = Path(tmp) / "proba.mjs"
        proba.write_text(PRELUDIU + script, encoding="utf-8")
        proc = subprocess.run([NODE, str(proba)], capture_output=True, text=True, timeout=180,
                              cwd=tmp)
    # Se judeca dupa CODUL DE IESIRE, nu dupa stderr: Node poate scrie avertismente
    # (ExperimentalWarning pe versiunile unde `fetch` e experimental) fara ca proba sa fi
    # gresit cu ceva. A confunda avertismentul cu esecul a facut testele sa pice in CI
    # in timp ce treceau local, doar pentru ca cele doua medii au versiuni diferite.
    if proc.returncode != 0:
        pytest.fail(f"proba a esuat ({proc.returncode}):\n{proc.stderr}\n{proc.stdout}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"proba n-a scris JSON pe stdout:\n{proc.stderr}\n{proc.stdout}")
    return {}


MEDIU = r"""
import * as push from './infra/push.mjs';
import * as worker from './infra/worker.mjs';

/* --- KV simulat: doar ce foloseste codul, plus contoare ca testele sa poata AFIRMA --- */
class KV {
  constructor() {
    this.date = new Map(); this.scrieri = 0; this.stergeri = 0; this.listari = 0;
  }
  async get(cheie, tip) {
    const v = this.date.get(cheie);
    if (v === undefined) return null;
    return tip === 'json' ? JSON.parse(v) : v;
  }
  async put(cheie, valoare) { this.scrieri++; this.date.set(cheie, valoare); }
  async delete(cheie) { this.stergeri++; return this.date.delete(cheie); }
  async list({ prefix = '', cursor, limit = 1000 } = {}) {
    this.listari++;
    const toate = [...this.date.keys()].filter((k) => k.startsWith(prefix)).sort();
    const start = cursor ? Number(cursor) : 0;
    const bucata = toate.slice(start, start + limit);
    const urmator = start + bucata.length;
    return { keys: bucata.map((name) => ({ name })),
             list_complete: urmator >= toate.length, cursor: String(urmator) };
  }
}

/* --- chei VAPID reale: politica si plafonul nu depind de ele, dar importul da, eroare daca
       nu se poate importa --- */
const chei = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign']);
const jwkPrivata = await crypto.subtle.exportKey('jwk', chei.privateKey);
const publica = new Uint8Array(await crypto.subtle.exportKey('raw', chei.publicKey));
const VAPID_PUB = Buffer.from(publica).toString('base64')
  .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

/* --- stub de fetch: inregistreaza si raspunde cu ce i se cere --- */
let cereri = [];
let raspunsuri = null;      // {status} sau functie(cerere)
globalThis.fetch = async (intrare, optiuni) => {
  // Codul cheama `fetch(url_string, {...})`, iar un stub care asteapta un obiect Request
  // ar arunca in interiorul buclei de trimitere — si atunci testul ar numara ESECURI in
  // loc de trimiteri, adica ar verifică altceva.
  const cerere = intrare instanceof Request ? intrare : new Request(intrare, optiuni);
  cereri.push({ url: cerere.url, headers: Object.fromEntries(cerere.headers) });
  const r = typeof raspunsuri === 'function' ? raspunsuri(cerere) : raspunsuri;
  return new Response('', { status: (r && r.status) || 201 });
};

/* Cheia clientului e REALA, nu un sir de 'A': criptarea face ECDH cu ea, deci un punct
   invalid arunca si fiecare abonat ar fi numarat ca esec — testul ar verifica logica de
   raportare, nu trimiterea. */
const client = await crypto.subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
const P256DH = Buffer.from(new Uint8Array(await crypto.subtle.exportKey('raw', client.publicKey)))
  .toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const ABONAMENT = (n) => ({
  endpoint: 'https://updates.push.services.mozilla.com/wpush/v2/abonament-' + n,
  keys: { p256dh: P256DH, auth: 'B'.repeat(22) },
});

function mediu(cuKV = true, cuChei = true) {
  const env = { PUSH_ADMIN_TOKEN: 'token-de-proba' };
  if (cuKV) env.PUSH_SUBS = new KV();
  if (cuChei) { env.VAPID_PUBLIC_KEY = VAPID_PUB; env.VAPID_PRIVATE_KEY = jwkPrivata.d; }
  return env;
}

async function cheama(modul, cale, optiuni = {}, env = mediu()) {
  const url = new URL('https://izz.ro' + cale);
  // Tokenul de administrator se pune IMPLICIT: aproape toate apelurile de aici il cer, iar
  // cele care verifica lipsa lui il scot explicit (`faraToken`).
  const faraToken = optiuni.faraToken;
  const { method, body, faraToken: _ignorat, ...rest } = optiuni;
  const cerere = new Request(url, {
    ...rest,
    ...(method ? { method } : {}),
    ...(body ? { body } : {}),
    ...(faraToken ? {} : { headers: { 'content-type': 'application/json',
      authorization: 'Bearer ' + (env.PUSH_ADMIN_TOKEN || 'token-de-proba') } }),
  });
  const ctx = { waitUntil: (p) => p };
  const raspuns = modul === 'push'
    ? await push.raspunsPush(cerere, env, url, ctx)
    : await worker.default.fetch(cerere, env, ctx);
  let corp = null;
  try { corp = await raspuns.json(); } catch { corp = null; }
  return { status: raspuns.status, corp };
}

const ALERTA = {
  titlu: 'Guvernul a publicat ordonanța cu noile salarii din sănătate',
  text: 'Documentul stabilește creșteri eșalonate începând cu 1 ianuarie, pentru toate categoriile de personal.',
  url: 'https://izz.ro/economic/cresteri-salariale-sanatate/'
};
const post = (corp) => ({ method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify(corp) });

const iesire = {};

/* 1. fara configuratie: 503 curat, nu exceptie, nu 200 gol */
iesire.cheie_fara_vapid = await cheama('push', '/push/cheie', {}, mediu(true, false));
const envFaraKV = mediu(false, true);
iesire.abonare_fara_kv = await cheama('push', '/push/abonare', post({ subscription: ABONAMENT(1) }), envFaraKV);

/* 2. cheia publica se citeste si fara KV: un vizitator o poate vedea inainte ca
      namespace-ul sa existe, iar asta e intentionat */
iesire.cheie_cu_vapid = await cheama('push', '/push/cheie', {}, envFaraKV);

/* 3. ciclul de viata al unui abonament */
const env = mediu();
iesire.abonare_noua = await cheama('push', '/push/abonare', post({ subscription: ABONAMENT(1) }), env);
iesire.abonare_rescrisa = await cheama('push', '/push/abonare', post({ subscription: ABONAMENT(1) }), env);
iesire.scrieri_dupa_abonare = env.PUSH_SUBS.scrieri;
iesire.abonare_straina = await cheama('push', '/push/abonare',
  post({ subscription: { endpoint: 'https://exemplu.rau/push', keys: { p256dh: 'A'.repeat(87), auth: 'B'.repeat(22) } } }), env);
iesire.abonare_fara_chei = await cheama('push', '/push/abonare',
  post({ subscription: { endpoint: 'https://fcm.googleapis.com/wp/x' } }), env);

for (let i = 2; i <= 5; i++) {
  await cheama('push', '/push/abonare', post({ subscription: ABONAMENT(i) }), env);
}
iesire.stare = await cheama('push', '/push/stare', {
  headers: { authorization: 'Bearer token-de-proba' } }, env);
iesire.stare_fara_token = await cheama('push', '/push/stare', { faraToken: true }, env);

/* 4. politica: refuz inainte de orice scriere sau cerere */
iesire.trimite_fara_token = await cheama('push', '/push/trimite', { ...post(ALERTA), faraToken: true }, env);
iesire.trimite_prost = await cheama('push', '/push/trimite',
  post({ ...ALERTA, titlu: 'Șoc!' }), env);
iesire.trimite_cu_token = { ...ALERTA, __: 0 };

/* 5. repetitie: nimic nu pleaca, ziua NU se consuma */
cereri = [];
iesire.uscat = await cheama('push', '/push/trimite', post({ ...ALERTA, uscat: true }), env);
iesire.uscat_cereri = cereri.length;
iesire.uscat_cap = await env.PUSH_SUBS.get('cap:' + push.cheieZi());

/* 6. trimitere reala, in loturi: primul scrie plafonul, al doilea NU se loveste de el */
raspunsuri = { status: 201 };
cereri = [];
iesire.trimite_lot1 = await cheama('push', '/push/trimite', post({ ...ALERTA, limita: 2 }), env);
iesire.trimite_cereri1 = cereri.length;
iesire.trimite_antete = cereri[0] ? {
  encoding: cereri[0].headers['content-encoding'],
  vapid: (cereri[0].headers.authorization || '').startsWith('vapid t='),
  ttl: cereri[0].headers.ttl,
} : null;
cereri = [];
iesire.trimite_lot2 = await cheama('push', '/push/trimite',
  post({ ...ALERTA, limita: 2, cursor: iesire.trimite_lot1.corp.cursor_urmator }), env);
iesire.cap_dupa = await env.PUSH_SUBS.get('cap:' + push.cheieZi());

/* 7. a doua alerta in aceeasi zi: refuz, zero cereri */
cereri = [];
iesire.a_doua_zi = await cheama('push', '/push/trimite', post(ALERTA), env);
iesire.a_doua_cereri = cereri.length;

/* 8. abonamente moarte: 404/410 se sterg, celelalte se pastreaza */
const env2 = mediu();
await cheama('push', '/push/abonare', post({ subscription: ABONAMENT(1) }), env2);
await cheama('push', '/push/abonare', post({ subscription: ABONAMENT(2) }), env2);
raspunsuri = (c) => ({ status: c.url.endsWith('abonament-1') ? 410 : 201 });
iesire.morti = await cheama('push', '/push/trimite', post(ALERTA), env2);
iesire.morti_ramase = (await cheama('push', '/push/stare',
  { headers: { authorization: 'Bearer token-de-proba' } }, env2)).corp.abonati;
iesire.morti_stergeri = env2.PUSH_SUBS.stergeri;

/* 9. dezabonare */
const env3 = mediu();
await cheama('push', '/push/abonare', post({ subscription: ABONAMENT(7) }), env3);
iesire.dezabonare = await cheama('push', '/push/dezabonare',
  post({ endpoint: ABONAMENT(7).endpoint }), env3);
iesire.dezabonare_ramase = (await cheama('push', '/push/stare',
  { headers: { authorization: 'Bearer token-de-proba' } }, env3)).corp.abonati;
iesire.dezabonare_straina = await cheama('push', '/push/dezabonare',
  post({ endpoint: 'https://exemplu.rau/push' }), env3);

/* 10. compozitia Workerului: pushul ajunge la push.js, restul la oglinda, /sw.js cu antet */
const ASSETS = { fetch: async (r) => (r.url.endsWith('/sw.js')
  ? new Response('// sw', { status: 200, headers: { 'content-type': 'text/javascript' } })
  : new Response('404', { status: 404 })) };
globalThis.fetch = async () => new Response('', { status: 404 });
const envW = { ...mediu(), ASSETS };
iesire.worker_push = await cheama('worker', '/push/cheie', {}, envW);
const swRaspuns = await worker.default.fetch(new Request('https://izz.ro/sw.js'), envW, { waitUntil: (p) => p });
iesire.worker_sw_cache = swRaspuns.headers.get('cache-control');
iesire.worker_sw_status = swRaspuns.status;
iesire.worker_sw_antete = Object.fromEntries(swRaspuns.headers);
const oglindaRaspuns = await worker.default.fetch(new Request('https://izz.ro/pagina-care-nu-exista/'),
  envW, { waitUntil: (p) => p });
iesire.worker_oglinda_status = oglindaRaspuns.status;
iesire.worker_ruta_necunoscuta = await cheama('worker', '/push/necunoscuta', {}, envW);

console.log(JSON.stringify(iesire));
"""


@pytest.fixture(scope="module")
def rulat() -> dict:
    return _ruleaza(MEDIU)


def test_fara_configuratie_raspunde_503_curat(rulat):
    assert rulat["cheie_fara_vapid"]["status"] == 503
    assert "VAPID_PUBLIC_KEY" in rulat["cheie_fara_vapid"]["corp"]["lipsesc"]
    assert rulat["abonare_fara_kv"]["status"] == 503
    # Un vizitator care deschide panoul de alerte vede un mesaj, nu o eroare de retea:
    # cheia publica se serveste si fara KV, pentru ca nu are nevoie de el.
    assert rulat["cheie_cu_vapid"]["status"] == 200
    assert rulat["cheie_cu_vapid"]["corp"]["cheie"]


def test_abonarea_se_scrie_o_singura_data(rulat):
    assert rulat["abonare_noua"]["status"] == 201
    assert rulat["abonare_noua"]["corp"]["nou"] is True
    # Re-abonarea aceluiasi dispozitiv NU consuma o scriere: KV are 1.000 de scrieri pe zi.
    assert rulat["abonare_rescrisa"]["corp"]["nou"] is False
    assert rulat["scrieri_dupa_abonare"] == 1
    assert rulat["abonare_straina"]["status"] == 400
    assert rulat["abonare_fara_chei"]["status"] == 400


def test_starea_numara_si_cere_token(rulat):
    assert rulat["stare"]["corp"]["abonati"] == 5
    assert rulat["stare_fara_token"]["status"] == 401


def test_politica_refuza_inainte_de_orice_trimitere(rulat):
    assert rulat["trimite_fara_token"]["status"] == 401
    assert rulat["trimite_prost"]["status"] == 422
    assert rulat["trimite_prost"]["corp"]["refuzat"] is True


def test_repetitia_nu_trimite_si_nu_consuma_ziua(rulat):
    assert rulat["uscat"]["corp"]["uscat"] is True
    assert rulat["uscat"]["corp"]["arFiPlecat"] == 5
    assert rulat["uscat_cereri"] == 0, "repetitia a trimis ceva"
    assert rulat["uscat_cap"] is None, "repetitia a consumat plafonul zilei"


def test_loturile_se_continua_fara_sa_se_ciocneasca_de_plafon(rulat):
    assert rulat["trimite_lot1"]["corp"]["trimise"] == 2
    assert rulat["trimite_cereri1"] == 2
    # Al doilea lot al ACELEIASI alerte trece mai departe: plafonul e pe zi, nu pe lot.
    assert rulat["trimite_lot2"]["status"] == 200
    assert rulat["trimite_lot2"]["corp"]["trimise"] == 2
    assert rulat["cap_dupa"], "plafonul zilnic trebuie scris o data, la primul lot"
    assert rulat["trimite_antete"]["encoding"] == "aes128gcm"
    assert rulat["trimite_antete"]["vapid"], "antetul VAPID lipseste"
    assert rulat["trimite_antete"]["ttl"] == str(24 * 3600)


def test_maxim_o_alerta_pe_zi(rulat):
    assert rulat["a_doua_zi"]["status"] == 409
    assert rulat["a_doua_cereri"] == 0, "a doua alerta din aceeasi zi a plecat totusi"


def test_abonamentele_moarte_se_sterg(rulat):
    assert rulat["morti"]["corp"]["trimise"] == 1
    assert rulat["morti"]["corp"]["sterse"] == 1
    assert rulat["morti_ramase"] == 1
    assert rulat["morti_stergeri"] == 1


def test_dezabonarea_scoate_cheia(rulat):
    assert rulat["dezabonare"]["status"] == 200
    assert rulat["dezabonare_ramase"] == 0
    assert rulat["dezabonare_straina"]["status"] == 400


def test_workerul_compune_rutele(rulat):
    assert rulat["worker_push"]["status"] == 200, "pushul nu ajunge la push.js prin worker"
    assert rulat["worker_sw_cache"] == "public, max-age=0, must-revalidate"
    # Restul trece prin oglinda: aici activul lipseste si oglinda e 404, deci 404.
    assert rulat["worker_oglinda_status"] == 404
    assert rulat["worker_ruta_necunoscuta"]["status"] == 404
