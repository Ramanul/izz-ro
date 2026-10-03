// Web Push cu VAPID pentru izz.ro — ruleaza in Workerul existent, pe planul Cloudflare FREE.
//
// DE CE EXISTA FISIERUL ASTA SI NU O LIBRARIE. `web-push` (npm) ar aduce un build step si un
// runtime Node pe un proiect care azi e Python + fisiere statice servite de un Worker. Tot ce
// face libraria se poate face cu WebCrypto, care e deja in runtime: semnarea VAPID e ECDSA
// P-256, iar criptarea e RFC 8291 (ECDH + HKDF) peste RFC 8188 (aes128gcm). Codul de mai jos
// e acea potentiala dependenta, scrisa o data si testata mecanic: tests/test_push_criptare.py
// ruleaza criptarea in Node si DECRIPTEAZA rezultatul cu cheia privata a clientului.
//
// CE NU FACE, spus ca sa nu fie citit mai mult decat e: nu alege CE e stire de ultima ora.
// Alegerea e editoriala si ramane la om; aici se aplica doar doua reguli mecanice — maxim o
// alerta pe zi si refuzul formularilor de tip momitor (verificaAlerta).
//
// LIMITELE PLANULUI FREE, de care depinde forma codului (citite pe
// developers.cloudflare.com/workers/platform/pricing/ si /kv/platform/limits/):
//   · 10 ms CPU per invocare -> trimiterea se face PE LOTURI, cu cursor (trimiteLot).
//   · KV: 100.000 citiri/zi, 1.000 scrieri/zi, 1.000 stergeri/zi, 1.000 listari/zi.
//     De aici: cate o cheie per abonament (nu un blob rescris la fiecare abonare — ar manca
//     plafonul de scrieri si ar pierde abonari prin citire-scriere concurenta) si refuzul
//     endpointurilor care nu apartin unui serviciu de push cunoscut.
//
// CHEILE NU SUNT IN REPO. Se pun cu `wrangler secret put` (vezi infra/PUSH-SETUP.md):
//   VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT, PUSH_ADMIN_TOKEN.
// Fara ele, rutele raspund 503 si site-ul functioneaza exact ca inainte.

const PREFIX = '/push/';
const PREFIX_ABONARE = 'sub:';
const PREFIX_CAP = 'cap:';
const CHEIE_STARE = 'stare:ultima';

// Un lot mic dinadins: cei 10 ms de CPU ai planului Free nu cuprind sute de perechi
// ECDH + AES-GCM. Limita se poate ridica pana la LIMITA_MAXIMA, nu peste.
const LIMITA_IMPLICITA = 40;
const LIMITA_MAXIMA = 100;

// Cat timp tine un push in coada serviciului daca dispozitivul e offline (secunde).
const TTL_SECUNDE = 24 * 3600;

// Durata de viata a cheii de plafon zilnic in KV. Doua zile: daca o trimitere esueaza, cheia
// dispare singura pana la finalul zilei urmatoare, deci nu ramane nimic de curatat manual.
const CAP_TTL_SECUNDE = 48 * 3600;

// Serviciile de push acceptate. Filtrul NU e cosmetica: o abonare scrie in KV, iar KV are
// 1.000 de scrieri pe zi pe planul Free. Fara el, oricine poate goli plafonul zilnic cu un
// sir de POST-uri catre /push/abonare, iar alertele reale nu se mai pot inregistra.
const GAZDE_PUSH = [
  'fcm.googleapis.com',
  'fcm.googleapis.cn',
  'updates.push.services.mozilla.com',
  'updates-autopush.stage.mozaws.net',
  'push.services.mozilla.com',
  'web.push.apple.com',
  'api.push.apple.com',
  'wns2-bl2p.notify.windows.com',
  'notify.windows.com',
  'sg2p.notify.windows.com',
];

// Cuvinte care transforma o stire in momitor. Lista e scurta DINADINS: o lista lunga produce
// refuzuri pe care nimeni nu le intelege, iar regula pe care o apara („zero zgomot") se
// apara cu cateva interdictii clare, nu cu un dictionar de sinonime.
//
// LIPSESTE deliberat „bomba"/„bombă": e un obiect real in stirile romanesti (o bombă
// gasita, o amenintare cu bombă), deci un refuz automat ar bloca exact stirea de ultima ora
// pe care alerta trebuie s-o duca. Majoritatea cuvintelor de mai jos, in schimb, sunt doar
// indemnuri: nu pot aparea intr-o formulare faptica fara sa o strice.
const MOMITOARE = [
  'soc', 'socant', 'socanta', 'incredibil', 'incredibilul', 'uluito', 'uluitoare',
  'senzațional', 'senzaționalul', 'cutremurător', 'dezvaluire', 'exclusiv',
  'nu vei crede', 'vezi aici', 'vezi ce', 'afla acum', 'click', 'surpriza',
];

// Acronime care SUNT legal cu majuscule si nu reprezinta vocea ridicata. Lista e inchisa:
// un cuvant nou intra aici prin decizie, nu prin analogie.
const ACRONIME = new Set([
  'SUA', 'UE', 'NATO', 'ONU', 'DNA', 'DIICOT', 'SRI', 'SPP', 'ANPC', 'BNR', 'ISU', 'CNAS',
  'ANRE', 'ANCOM', 'MAE', 'MAI', 'MAPN', 'PSD', 'PNL', 'USR', 'AUR', 'UDMR', 'CFR', 'TVR',
  'OMS', 'FMI', 'BCE', 'ITM', 'ANAF', 'DSU', 'IGPR', 'IPJ', 'CJ', 'PMB', 'CSM', 'ICCJ',
  'INS', 'CNA', 'SRR', 'STB', 'BVB', 'ASF', 'SMURD', 'COVID', 'ANM', 'INSP', 'BOR',
  'FBI', 'CIA', 'NASA', 'PIB', 'TVA',
]);

const EMOJI = /\p{Extended_Pictographic}/u;
const CALE_ARTICOL = /^\/[a-z0-9-]+\/[a-z0-9-]+\/$/;
const SUBIECT_IMPLICIT = 'mailto:contact@izz.ro';

/* Fara diacritice, pentru comparatii: „Șoc!" si „Soc!" sunt acelasi momitor, iar
   `String.toLowerCase()` NU le aduce impreuna — „ș" (U+0219, cu virgula) nu are
   descompunere canonica, deci nici `normalize('NFD')` nu ajuta. Doar aici, nu si in
   mesajul trimis: textul ajunge la cititor exact cum a fost scris. */
function faraDiacritice(text) {
  return String(text).toLowerCase()
    .replace(/[ăâ]/g, 'a')
    .replace(/î/g, 'i')
    .replace(/[șş]/g, 's')
    .replace(/[țţ]/g, 't');
}

// --- base64url ------------------------------------------------------------------

export function b64url(sir) {
  const brut = atob(sir.replace(/-/g, '+').replace(/_/g, '/'));
  const out = new Uint8Array(brut.length);
  for (let i = 0; i < brut.length; i++) out[i] = brut.charCodeAt(i);
  return out;
}

export function dinB64url(octeti) {
  let brut = '';
  for (const b of octeti) brut += String.fromCharCode(b);
  return btoa(brut).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

const enc = new TextEncoder();

function concat(...bucati) {
  const total = bucati.reduce((n, b) => n + b.length, 0);
  const out = new Uint8Array(total);
  let p = 0;
  for (const b of bucati) { out.set(b, p); p += b.length; }
  return out;
}

// --- validari -------------------------------------------------------------------

/** Endpointul e al unui serviciu de push cunoscut? (Vezi nota de la GAZDE_PUSH.) */
export function gazdaAcceptata(endpoint) {
  let url;
  try { url = new URL(endpoint); } catch { return false; }
  if (url.protocol !== 'https:') return false;
  return GAZDE_PUSH.includes(url.hostname);
}

/** Un obiect de abonare asa cum il da browserul e complet si credibil? */
export function valideazaAbonament(sub) {
  if (!sub || typeof sub !== 'object') return 'abonament lipsa';
  if (typeof sub.endpoint !== 'string' || !gazdaAcceptata(sub.endpoint)) {
    return 'endpoint de push neacceptat';
  }
  const chei = sub.keys || {};
  if (typeof chei.p256dh !== 'string' || typeof chei.auth !== 'string') {
    return 'cheile abonamentului lipsesc';
  }
  try {
    if (b64url(chei.p256dh).length !== 65) return 'cheia publica a abonamentului are lungimea gresita';
    if (b64url(chei.auth).length < 16) return 'secretul de autentificare e prea scurt';
  } catch {
    return 'cheile abonamentului nu sunt base64url';
  }
  return null;
}

/** Cuvinte scrise cu majuscule care NU sunt acronime — adica vocea ridicata din titlu. */
export function strigate(titlu) {
  return (String(titlu).match(/\p{Lu}{4,}/gu) || []).filter((w) => !ACRONIME.has(w));
}

/**
 * Politica «Zgomot zero», aplicata mecanic inainte ca alerta sa plece.
 *
 * Intoarce `{ ok: true }` sau `{ ok: false, motive: [...] }` cu motive in romaneste: refuzul
 * trebuie sa fie inteligibil pentru cine a scris alerta, nu doar un cod HTTP.
 */
export function verificaAlerta(alerta) {
  const motive = [];
  if (!alerta || typeof alerta !== 'object') {
    return { ok: false, motive: ['alerta lipsa'] };
  }
  const titlu = String(alerta.titlu || '').trim();
  const text = String(alerta.text || '').trim();
  const url = String(alerta.url || '').trim();

  if (titlu.length < 12) motive.push('titlul e prea scurt ca sa spuna ceva');
  if (titlu.length > 90) motive.push('titlul depaseste 90 de caractere — nu se vede intreg pe telefon');
  if (text.length < 30) motive.push('textul e prea scurt: o alerta trebuie sa spuna fapta, nu doar s-o anunte');
  if (text.length > 200) motive.push('textul depaseste 200 de caractere');
  if (titlu && titlu === text) motive.push('textul repeta titlul; nu adauga nimic');

  for (const [camp, valoare] of [['titlul', titlu], ['textul', text]]) {
    if (/[!?]/.test(valoare)) motive.push(`${camp} nu are voie sa contina „!" sau „?" — sunt semne de chemare, nu de informare`);
    if (/…|\.\.\./.test(valoare)) motive.push(`${camp} se intrerupe cu „..." ca sa creeze suspans`);
    if (EMOJI.test(valoare)) motive.push(`${camp} contine emoji`);
  }
  const tipete = strigate(titlu);
  if (tipete.length) motive.push(`titlul ridica vocea: ${tipete.join(', ')}`);

  const jos = faraDiacritice(titlu + ' ' + text);
  const gasit = MOMITOARE.filter((m) => jos.includes(m));
  if (gasit.length) motive.push(`formulare de tip momitor: ${gasit.join(', ')}`);

  // Alerta trebuie sa duca exact la articol: nu la prima pagina, nu la un URL cu parametri
  // de urmarire. Cine primeste alerta ajunge pe stire, nu pe o pagina de alegeri.
  let cale = '';
  try {
    const u = new URL(url);
    if (u.protocol !== 'https:' || u.hostname !== 'izz.ro') {
      motive.push('adresa trebuie sa fie pe https://izz.ro');
    }
    cale = u.pathname;
    // Parametrii de urmarire nu au ce cauta intr-o alerta: scopul ei e sa duca omul la
    // stire, nu sa masoare pe unde a intrat.
    if (u.search) motive.push('adresa are parametri (de urmarire sau de alt fel)');
  } catch {
    motive.push('adresa nu e un URL valid');
  }
  if (cale && !CALE_ARTICOL.test(cale)) {
    motive.push('adresa trebuie sa fie pagina articolului (/{categorie}/{slug}/)');
  }

  return motive.length ? { ok: false, motive } : { ok: true };
}

// --- chei VAPID -----------------------------------------------------------------

function jwkDinBrut(publica, privata) {
  return {
    kty: 'EC',
    crv: 'P-256',
    x: dinB64url(publica.subarray(1, 33)),
    y: dinB64url(publica.subarray(33, 65)),
    d: dinB64url(privata),
  };
}

/**
 * Cheia privata VAPID, in oricare din cele doua forme pe care le produc uneltele obisnuite
 * (`npx web-push generate-vapid-keys`, `openssl`): base64url brut (32 de octeti) sau PEM
 * PKCS#8. Ambele sunt acceptate pentru ca secretul se lipeste manual intr-un dashboard, iar
 * o forma gresita inseamna 503 pe toate rutele, fara niciun alt simptom.
 */
export async function importaCheieVapid(publicaB64, privataB64) {
  const publica = b64url(publicaB64);
  if (publica.length !== 65 || publica[0] !== 4) {
    throw new Error('VAPID_PUBLIC_KEY nu e un punct P-256 necomprimat (65 de octeti)');
  }
  let privata = null;
  try {
    privata = b64url(privataB64);
  } catch { /* nu e base64url; incercam PEM mai jos */ }
  if (privata && privata.length === 32) {
    return crypto.subtle.importKey('jwk', jwkDinBrut(publica, privata),
      { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
  }
  const der = String(privataB64)
    .replace(/-----BEGIN [A-Z ]+-----/g, '')
    .replace(/-----END [A-Z ]+-----/g, '')
    .replace(/\s+/g, '');
  const octeti = Uint8Array.from(atob(der), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey('pkcs8', octeti,
    { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
}

/** JWT-ul VAPID: `{"typ":"JWT","alg":"ES256"}` semnat cu cheia privata a site-ului. */
export async function semnVapid(cheiePrivata, publicaB64, audienta,
  subiect = SUBIECT_IMPLICIT, acum = Date.now()) {
  const antet = { typ: 'JWT', alg: 'ES256' };
  const corp = { aud: audienta, exp: Math.floor(acum / 1000) + 12 * 3600, sub: subiect || SUBIECT_IMPLICIT };
  const parte = (o) => dinB64url(enc.encode(JSON.stringify(o)));
  const deSemnat = enc.encode(`${parte(antet)}.${parte(corp)}`);
  const semnatura = await crypto.subtle.sign(
    { name: 'ECDSA', hash: 'SHA-256' }, cheiePrivata, deSemnat);
  // ECDSA in WebCrypto intoarce semnatura in format IEEE P1363 (r||s), exact ce cere JWT,
  // nu formatul DER.
  return `${parte(antet)}.${parte(corp)}.${dinB64url(new Uint8Array(semnatura))}`;
}

// --- criptare (RFC 8291 + RFC 8188) --------------------------------------------

/**
 * Cripteaza un payload pentru UN abonament.
 *
 * Perechea de chei a serverului si sarea se pot refolosi intre destinatari: cheia de
 * criptare se deriveaza din secretul ECDH, care e diferit pentru fiecare abonat. Asta nu e
 * o economisire de gust, e diferenta dintre a trimite un lot de 40 si a nu-l putea trimite
 * deloc in cei 10 ms de CPU.
 */
export async function cripteaza(mesaj, abonament, perecheServer, sare) {
  const uaPublica = b64url(abonament.keys.p256dh);
  const auth = b64url(abonament.keys.auth);
  const asPublica = new Uint8Array(await crypto.subtle.exportKey('raw', perecheServer.publicKey));

  const cheieClient = await crypto.subtle.importKey(
    'jwk',
    { kty: 'EC', crv: 'P-256',
      x: dinB64url(uaPublica.subarray(1, 33)),
      y: dinB64url(uaPublica.subarray(33, 65)) },
    { name: 'ECDH', namedCurve: 'P-256' }, false, []);
  const secretComun = new Uint8Array(await crypto.subtle.deriveBits(
    { name: 'ECDH', public: cheieClient }, perecheServer.privateKey, 256));

  // IKM = HKDF(salt=auth, ikm=secretComun, info="WebPush: info" || 0x00 || ua || as, 32).
  // Un singur apel WebCrypto face HKDF-Extract(salt, material) urmat de Expand(info), deci
  // acopera exact cei doi pasi din RFC 8291 §3.3.
  const infoCheie = concat(enc.encode('WebPush: info'), new Uint8Array([0]), uaPublica, asPublica);
  const material = await crypto.subtle.importKey('raw', secretComun, { name: 'HKDF' }, false, ['deriveBits']);
  const ikm = await crypto.subtle.deriveBits(
    { name: 'HKDF', hash: 'SHA-256', salt: auth, info: infoCheie }, material, 256);

  const bazaCheie = await crypto.subtle.importKey('raw', ikm, { name: 'HKDF' }, false, ['deriveBits']);
  // AMBELE siruri se termina cu un octet ZERO (RFC 8291 §3.4: `cek_info =
  // "Content-Encoding: aes128gcm" || 0x00`). Fara octetul ala, cheia iese alta si NICIUN
  // browser nu poate decripta alerta — iar singurul simptom e o notificare care nu afiseaza
  // nimic. Prins de tests/test_push_criptare.py pe vectorul din RFC, nu de ochi.
  const [brutCheie, brutNonce] = await Promise.all([
    crypto.subtle.deriveBits(
      { name: 'HKDF', hash: 'SHA-256', salt: sare, info: enc.encode('Content-Encoding: aes128gcm\0') },
      bazaCheie, 128),
    crypto.subtle.deriveBits(
      { name: 'HKDF', hash: 'SHA-256', salt: sare, info: enc.encode('Content-Encoding: nonce\0') },
      bazaCheie, 96),
  ]);

  const cheieAes = await crypto.subtle.importKey('raw', brutCheie, { name: 'AES-GCM' }, false, ['encrypt']);
  // RFC 8188: o singura inregistrare, terminata cu delimitatorul 0x02. Fara delimitator
  // unele servicii de push refuza corpul.
  const clar = concat(mesaj, new Uint8Array([2]));
  const cifru = new Uint8Array(await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: new Uint8Array(brutNonce) }, cheieAes, clar));

  const antet = new Uint8Array(86);
  antet.set(sare, 0);
  // Dimensiunea inregistrarii: RFC 8291 §4 cere o SINGURA inregistrare si un `rs` strict
  // MAI MARE decat textul clar + delimitator + padare + eticheta (adica decat cifrul).
  // Egalitatea nu ajunge: „greater than", nu „at least".
  new DataView(antet.buffer).setUint32(16, cifru.length + 1, false);
  antet[20] = asPublica.length;
  antet.set(asPublica, 21);
  return concat(antet, cifru);
}

export async function trimiteUnuia(abonament, jwt, publicaB64, mesaj, perecheServer, sare) {
  const corp = await cripteaza(mesaj, abonament, perecheServer, sare);
  const audienta = new URL(abonament.endpoint).origin;
  const semnatura = await semnVapid(jwt.cheie, publicaB64, audienta, jwt.subiect, jwt.acum);
  const raspuns = await fetch(abonament.endpoint, {
    method: 'POST',
    headers: {
      'content-type': 'application/octet-stream',
      'content-encoding': 'aes128gcm',
      'content-length': String(corp.length),
      ttl: String(TTL_SECUNDE),
      urgency: 'high',
      authorization: `vapid t=${semnatura}, k=${publicaB64}`,
      // Antet mostenit, cerut inca de unele implementari vechi; costul lui e zero.
      'crypto-key': `p256ecdsa=${publicaB64}`,
    },
    body: corp,
  });
  return raspuns.status;
}

// --- rute -----------------------------------------------------------------------

export function esteCalePush(pathname) {
  return pathname === '/push' || pathname.startsWith(PREFIX);
}

function json(date, status = 200) {
  return new Response(JSON.stringify(date), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  });
}

function faraKV() {
  return json({ eroare: 'alertele nu sunt configurate pe acest deployment (lipseste legatura KV)' }, 503);
}

function configLipsa() {
  return json({
    eroare: 'cheile VAPID nu sunt setate; vezi infra/PUSH-SETUP.md',
    lipsesc: ['VAPID_PUBLIC_KEY', 'VAPID_PRIVATE_KEY', 'VAPID_SUBJECT', 'PUSH_ADMIN_TOKEN'],
  }, 503);
}

/** Comparare de lungime constanta: nu lasa lungimea tokenului sa scurteze comparatia. */
export function tokenCorect(primite, asteptat) {
  if (typeof primite !== 'string' || !asteptat) return false;
  let diferit = primite.length ^ asteptat.length;
  const n = Math.max(primite.length, asteptat.length);
  for (let i = 0; i < n; i++) {
    diferit |= (primite.charCodeAt(i) || 0) ^ (asteptat.charCodeAt(i) || 0);
  }
  return diferit === 0;
}

function admin(request, env) {
  return tokenCorect((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''),
    env.PUSH_ADMIN_TOKEN);
}

export function cheieZi(azi = new Date()) {
  return azi.toISOString().slice(0, 10);
}

export async function idAbonament(endpoint) {
  const urme = await crypto.subtle.digest('SHA-256', enc.encode(endpoint));
  return PREFIX_ABONARE + Array.from(new Uint8Array(urme))
    .map((b) => b.toString(16).padStart(2, '0')).join('');
}

function cursorUrmator(pagina) {
  return pagina.list_complete ? null : pagina.cursor;
}

/** Numaratoare pentru un om (`/push/stare`); NU se apeleaza la fiecare trimitere. */
async function stare(kv) {
  let abonati = 0;
  let cursor;
  do {
    const pagina = await kv.list({ prefix: PREFIX_ABONARE, cursor, limit: 1000 });
    abonati += pagina.keys.length;
    cursor = pagina.list_complete ? undefined : pagina.cursor;
  } while (cursor);
  return { abonati, ultima: (await kv.get(CHEIE_STARE, 'json')) || null };
}

export async function raspunsPush(request, env, url, ctx) {
  if (request.method === 'OPTIONS') return new Response(null, { status: 204 });
  const cale = url.pathname;
  const kv = env.PUSH_SUBS;

  // Cheia publica se cere INAINTE de abonare, deci nu are nevoie de KV: un vizitator o
  // poate citi si pe un deployment care n-a primit inca legatura.
  if (cale === '/push/cheie' && request.method === 'GET') {
    if (!env.VAPID_PUBLIC_KEY) return configLipsa();
    return json({ cheie: env.VAPID_PUBLIC_KEY });
  }

  if (cale === '/push/abonare' && request.method === 'POST') {
    if (!env.VAPID_PUBLIC_KEY) return configLipsa();
    if (!kv) return faraKV();
    let corp;
    try { corp = await request.json(); } catch { return json({ eroare: 'corp JSON invalid' }, 400); }
    const problema = valideazaAbonament(corp && corp.subscription);
    if (problema) return json({ eroare: problema }, 400);
    const sub = corp.subscription;
    const id = await idAbonament(sub.endpoint);
    // Re-abonarea aceluiasi dispozitiv NU rescrie: scrierile in KV sunt 1.000 pe zi, iar
    // browserul re-abona la fiecare vizita daca i s-ar cere.
    if (await kv.get(id)) return json({ ok: true, nou: false });
    await kv.put(id, JSON.stringify({
      endpoint: sub.endpoint,
      keys: { p256dh: sub.keys.p256dh, auth: sub.keys.auth },
      la: new Date().toISOString(),
    }));
    return json({ ok: true, nou: true }, 201);
  }

  if (cale === '/push/dezabonare' && request.method === 'POST') {
    if (!kv) return faraKV();
    let corp;
    try { corp = await request.json(); } catch { return json({ eroare: 'corp JSON invalid' }, 400); }
    const endpoint = corp && corp.endpoint;
    if (typeof endpoint !== 'string' || !gazdaAcceptata(endpoint)) {
      return json({ eroare: 'endpoint de push neacceptat' }, 400);
    }
    await kv.delete(await idAbonament(endpoint));
    return json({ ok: true });
  }

  if (cale === '/push/stare' && request.method === 'GET') {
    if (!admin(request, env)) return json({ eroare: 'lipsa autorizare' }, 401);
    if (!kv) return faraKV();
    return json(await stare(kv));
  }

  if (cale === '/push/trimite' && request.method === 'POST') {
    if (!admin(request, env)) return json({ eroare: 'lipsa autorizare' }, 401);
    if (!env.VAPID_PUBLIC_KEY || !env.VAPID_PRIVATE_KEY) return configLipsa();
    if (!kv) return faraKV();
    let corp;
    try { corp = await request.json(); } catch { return json({ eroare: 'corp JSON invalid' }, 400); }
    return trimiteLot(corp, env, ctx);
  }

  return json({ eroare: 'ruta de push necunoscuta' }, 404);
}

/**
 * Un lot de trimiteri. Intoarce `cursor_urmator`; cand e null, lotul a fost ultimul.
 *
 * ORDINEA OPERATIILOR E ALEASA, nu intamplatoare: plafonul zilnic se scrie INAINTE de
 * trimitere. Daca Workerul moare la jumatatea lotului, ziua se considera consumata si nu se
 * mai trimite — adica greseste in directia promisa („maxim o alerta pe zi"), nu impotriva
 * ei. Continuarea se face reluand cu acelasi cursor.
 *
 * Plafonul se verifica doar pe PRIMUL lot (`cursor` lipsa): loturile urmatoare ale aceleiasi
 * alerte trec mai departe, altfel al doilea apel s-ar lovi de cheia scrisa de primul.
 */
export async function trimiteLot(corp, env, ctx) {
  const kv = env.PUSH_SUBS;
  const verdict = verificaAlerta(corp);
  if (!verdict.ok) return json({ refuzat: true, motive: verdict.motive }, 422);

  const zi = cheieZi();
  const cap = `${PREFIX_CAP}${zi}`;
  const uscat = corp.uscat === true;   // repetitie: totul, mai putin plecarea alertei
  const primul = !corp.cursor;
  if (primul && !uscat && (await kv.get(cap))) {
    return json({ refuzat: true, motive: ['azi s-a trimis deja o alerta; maxim una pe zi'], zi }, 409);
  }

  const limita = Math.min(Number(corp.limita) || LIMITA_IMPLICITA, LIMITA_MAXIMA);
  const pagina = await kv.list({ prefix: PREFIX_ABONARE, cursor: corp.cursor || undefined, limit: limita });

  const mesaj = enc.encode(JSON.stringify({
    titlu: corp.titlu.trim(),
    text: corp.text.trim(),
    url: corp.url.trim(),
    tag: corp.tag || 'ultima-ora',
  }));

  const jwt = {
    cheie: await importaCheieVapid(env.VAPID_PUBLIC_KEY, env.VAPID_PRIVATE_KEY),
    subiect: env.VAPID_SUBJECT || SUBIECT_IMPLICIT,
    acum: Date.now(),
  };
  const perecheServer = await crypto.subtle.generateKey(
    { name: 'ECDH', namedCurve: 'P-256' }, false, ['deriveBits']);
  const sare = crypto.getRandomValues(new Uint8Array(16));

  if (uscat) {
    return json({ uscat: true, arFiPlecat: pagina.keys.length, cursor_urmator: cursorUrmator(pagina) });
  }

  await kv.put(cap, new Date().toISOString(), { expirationTtl: CAP_TTL_SECUNDE });

  let trimise = 0;
  let esecuri = 0;
  const stergeri = [];

  for (const cheie of pagina.keys) {
    const abonament = await kv.get(cheie.name, 'json');
    if (!abonament) continue;
    let status;
    try {
      status = await trimiteUnuia(abonament, jwt, env.VAPID_PUBLIC_KEY, mesaj, perecheServer, sare);
    } catch {
      esecuri++;
      continue;
    }
    if (status === 201 || status === 200) {
      trimise++;
    } else if (status === 404 || status === 410) {
      // Abonament mort (aplicatie dezinstalata, permisiune retrasa). Se sterge, altfel KV
      // creste cu morti si fiecare trimitere plateste cate o cerere pentru ele.
      stergeri.push(kv.delete(cheie.name));
    } else {
      esecuri++;
    }
  }
  if (stergeri.length) await Promise.all(stergeri);
  // `waitUntil`: raportul nu trebuie sa astepte o scriere in KV ca sa ajunga la cel care
  // a declansat alerta.
  if (ctx && ctx.waitUntil) {
    ctx.waitUntil(kv.put(CHEIE_STARE, JSON.stringify({
      la: new Date().toISOString(),
      titlu: corp.titlu.trim(),
      trimise, esecuri, sterse: stergeri.length,
    })));
  }
  return json({
    trimise, esecuri, sterse: stergeri.length,
    cursor_urmator: cursorUrmator(pagina), zi,
  });
}
