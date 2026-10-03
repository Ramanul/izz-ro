"""Alertele IZZ.ro: criptarea Web Push si politica «Zgomot zero», verificate RULAND codul.

DE CE RULEAZA CODUL IN LOC SA-L CITEASCA. `infra/push.js` e JavaScript pe un repo de
Python, deci nimic din suita nu-l putea atinge: o greseala in criptare ar fi fost invizibila
pana la prima alerta reala — adica pana cand niste oameni ar fi primit o notificare care nu
se deschide. Testele de aici importa modulul in Node (prezent si pe masina locala, si pe
runnerele GitHub) si ii cer doua lucruri care nu se pot preface:

  1. **Vectorul de test din RFC 8291 §5 + Anexa A.** Cheile, sarea, secretul de
     autentificare si textul clar sunt DIN RFC; se compara octet cu octet cu rezultatul pe
     care RFC-ul il publica. Asta NU e un test de rotund (criptare -> decriptare cu aceeasi
     implementare), e un test de CONFORMITATE: daca vreun pas din HKDF e gresit, cifrul nu
     mai iese `8pfeW0KbunFT06SuDKoJH9Ql87S1QUrd...` si testul pica.
  2. **Decriptarea cu cheia PRIVATA a clientului** (scrisa in test, cu WebCrypto din Node):
     exact ce face browserul cand primeste alerta.

CE NU ACOPERA, spus ca sa nu para mai mult decat e: nu exista nicio cerere catre un serviciu
de push real (ar face suita dependenta de retea si de FCM/Mozilla). Antetele
`Authorization`/`Crypto-Key` si codurile de raspuns ale serviciului raman NEVERIFICATE aici;
prima proba adevarata e un `--uscat` urmat de o alerta reala, pe dispozitivul tau.

Rulare manuala: `python -m pytest tests/test_push_criptare.py -q -p no:randomly`
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUSH_JS = ROOT / "infra" / "push.js"

NODE = shutil.which("node")
FARA_NODE = "Node lipseste: nu se poate rula codul Workerului"


def _ruleaza(script: str, modul: Path | None = None) -> dict:
    """Ruleaza `script` in Node, cu modulul dat importabil ca ESM.

    Extensia e `.mjs` in ambele parti pentru ca Node decide formatul modulului dupa
    extensie, iar `infra/push.js` e ESM (`export`): importat ca `.js`, fara un
    `package.json` cu `type: module`, ar fi citit drept CommonJS si ar cadea la primul
    `export`.
    """
    with tempfile.TemporaryDirectory(prefix="izz-push-") as tmp:
        copie = Path(tmp) / "push.mjs"
        shutil.copy(modul or PUSH_JS, copie)
        proba = Path(tmp) / "proba.mjs"
        proba.write_text(script.replace("__PUSH__", copie.as_uri()), encoding="utf-8")
        proc = subprocess.run([NODE, str(proba)], capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or proc.stderr.strip():
        pytest.fail(f"proba a esuat ({proc.returncode}):\n{proc.stderr}\n{proc.stdout}")
    return json.loads(proc.stdout)


# Vectorul din RFC 8291, §5 si Anexa A (spatiile albe din document sunt scoase).
VECTOR = r"""
import * as push from '__PUSH__';

const enc = new TextEncoder();
const b64 = (s) => new Uint8Array(Buffer.from(s, 'base64'));
const b64u = (b) => Buffer.from(b).toString('base64')
  .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

const PLAIN   = 'V2hlbiBJIGdyb3cgdXAsIEkgd2FudCB0byBiZSBhIHdhdGVybWVsb24';
const AS_PUB  = 'BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8';
const AS_PRIV = 'yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw';
const UA_PUB  = 'BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4';
const UA_PRIV = 'q1dXpw3UpT5VOmu_cf_v6ih07Aems3njxI-JWgLcM94';
const SALT    = 'DGv6ra1nlYgDCS1FRnbzlw';
const AUTH    = 'BTBZMqHH6r4Tts7J_aSIgg';
const CIFRU   = '8pfeW0KbunFT06SuDKoJH9Ql87S1QUrdirN6GcG7sFz1y1sqLgVi1VhjVkHsUoEsbI_0LpXMuGvnzQ';

const jwk = (brut, d) => ({
  kty: 'EC', crv: 'P-256',
  x: b64u(brut.subarray(1, 33)),
  y: b64u(brut.subarray(33, 65)),
  ...(d ? { d } : {}),
});

async function perecheDinPrivata(privataB64, publicaBrut) {
  const privata = await crypto.subtle.importKey('jwk', jwk(publicaBrut, privataB64),
    { name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const publica = await crypto.subtle.importKey('raw', publicaBrut,
    { name: 'ECDH', namedCurve: 'P-256' }, true, []);
  return { privateKey: privata, publicKey: publica };
}

const iesire = {};
const pereche = await perecheDinPrivata(AS_PRIV, b64(AS_PUB));
const abonament = { keys: { p256dh: UA_PUB, auth: AUTH } };
const corp = await push.cripteaza(b64(PLAIN), abonament, pereche, b64(SALT));

iesire.sare_corecta = Buffer.from(corp.subarray(0, 16)).equals(Buffer.from(b64(SALT)));
iesire.idlen = corp[20];
iesire.cheie_server_corecta = Buffer.from(corp.subarray(21, 86)).equals(Buffer.from(b64(AS_PUB)));
iesire.cifru_conforme = Buffer.from(corp.subarray(86)).equals(Buffer.from(b64(CIFRU)));
// Dimensiunea inregistrarii e a NOASTRA (nu 4096 ca in RFC), dar RFC 8291 §4 cere ca `rs`
// sa fie strict MAI MARE decat lungimea cifrului — o singura inregistrare, garantat.
const rs = new DataView(corp.buffer, corp.byteOffset).getUint32(16, false);
iesire.rs_acopera = rs > corp.length - 86;
iesire.rs = rs;

// --- decriptarea, asa cum o face browserul: cu cheia PRIVATA a clientului ---
const uaPriv = await crypto.subtle.importKey('jwk', jwk(b64(UA_PUB), UA_PRIV),
  { name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
const asPub = await crypto.subtle.importKey('raw', corp.subarray(21, 86),
  { name: 'ECDH', namedCurve: 'P-256' }, true, []);
const dh = new Uint8Array(await crypto.subtle.deriveBits({ name: 'ECDH', public: asPub }, uaPriv, 256));
const info = new Uint8Array([...enc.encode('WebPush: info'), 0, ...b64(UA_PUB), ...corp.subarray(21, 86)]);
const mat = await crypto.subtle.importKey('raw', dh, 'HKDF', false, ['deriveBits']);
const ikm = await crypto.subtle.deriveBits(
  { name: 'HKDF', hash: 'SHA-256', salt: b64(AUTH), info }, mat, 256);
const baza = await crypto.subtle.importKey('raw', ikm, 'HKDF', false, ['deriveBits']);
const cek = await crypto.subtle.deriveBits(
  { name: 'HKDF', hash: 'SHA-256', salt: corp.subarray(0, 16),
    info: enc.encode('Content-Encoding: aes128gcm\0') }, baza, 128);
const nonce = await crypto.subtle.deriveBits(
  { name: 'HKDF', hash: 'SHA-256', salt: corp.subarray(0, 16),
    info: enc.encode('Content-Encoding: nonce\0') }, baza, 96);
const aes = await crypto.subtle.importKey('raw', cek, 'AES-GCM', false, ['decrypt']);
const clar = new Uint8Array(await crypto.subtle.decrypt(
  { name: 'AES-GCM', iv: new Uint8Array(nonce) }, aes, corp.subarray(86)));
iesire.roundtrip = Buffer.from(clar.subarray(0, clar.length - 1)).equals(Buffer.from(b64(PLAIN)));
iesire.delimitator = clar[clar.length - 1];

// --- VAPID: se semneaza cu cheia privata si se verifica cu cea publica ---
const vapid = await crypto.subtle.generateKey(
  { name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
const jwkPrivata = await crypto.subtle.exportKey('jwk', vapid.privateKey);
const brutPub = new Uint8Array(await crypto.subtle.exportKey('raw', vapid.publicKey));
const brutPkcs8 = new Uint8Array(await crypto.subtle.exportKey('pkcs8', vapid.privateKey));
const pubB64 = b64u(brutPub);
const pem = '-----BEGIN PRIVATE KEY-----\n' +
  Buffer.from(brutPkcs8).toString('base64').match(/.{1,64}/g).join('\n') +
  '\n-----END PRIVATE KEY-----';

const importataJwk = await push.importaCheieVapid(pubB64, jwkPrivata.d);
const importataPem = await push.importaCheieVapid(pubB64, pem);
const jwt = await push.semnVapid(importataJwk, pubB64, 'https://fcm.googleapis.com',
  'mailto:contact@izz.ro', 1700000000000);
const jwtPem = await push.semnVapid(importataPem, pubB64, 'https://fcm.googleapis.com',
  'mailto:contact@izz.ro', 1700000000000);
const parti = jwt.split('.');
const semnatura = Buffer.from(parti[2].replace(/-/g, '+').replace(/_/g, '/'), 'base64');
iesire.jwt_antet = JSON.parse(Buffer.from(parti[0], 'base64url').toString());
iesire.jwt_corp = JSON.parse(Buffer.from(parti[1], 'base64url').toString());
iesire.jwt_semnat = await crypto.subtle.verify(
  { name: 'ECDSA', hash: 'SHA-256' }, vapid.publicKey, semnatura,
  enc.encode(parti[0] + '.' + parti[1]));
// Semnatura ECDSA e aleatorie (k diferit de fiecare data), deci cele doua JWT-uri NU pot fi
// identice. Ce trebuie sa fie adevarat: ambele se verifica cu aceeasi cheie publica.
const partiPem = jwtPem.split('.');
iesire.jwt_pem_verificat = await crypto.subtle.verify(
  { name: 'ECDSA', hash: 'SHA-256' }, vapid.publicKey,
  Buffer.from(partiPem[2].replace(/-/g, '+').replace(/_/g, '/'), 'base64'),
  enc.encode(partiPem[0] + '.' + partiPem[1]));

console.log(JSON.stringify(iesire));
"""

POLITICA = r"""
import * as push from '__PUSH__';
const bun = {
  titlu: 'Guvernul a publicat ordonanța cu noile salarii din sănătate',
  text: 'Documentul stabilește creșteri eșalonate începând cu 1 ianuarie, pentru toate categoriile de personal.',
  url: 'https://izz.ro/economic/cresteri-salariale-sanatate/'
};
const iesire = {};
iesire.bun = push.verificaAlerta(bun);
iesire.gol = push.verificaAlerta({});
iesire.emoji = push.verificaAlerta({ ...bun, titlu: '🚨 ' + bun.titlu });
iesire.exclamare = push.verificaAlerta({ ...bun, titlu: bun.titlu + '!' });
iesire.intrebare = push.verificaAlerta({ ...bun, titlu: 'Se scumpesc facturile din ianuarie?' });
iesire.suspans = push.verificaAlerta({ ...bun, text: 'Guvernul a amânat decizia și nu a explicat de ce...' });
iesire.tipat = push.verificaAlerta({ ...bun, titlu: 'ATENȚIE ' + bun.titlu });
iesire.acronim_bun = push.verificaAlerta({ ...bun, titlu: 'SUA anunță noi sancțiuni economice pentru 2027' });
iesire.momitor = push.verificaAlerta({ ...bun, titlu: 'Șoc total: ' + bun.titlu });
iesire.text_scurt = push.verificaAlerta({ ...bun, text: 'A apărut.' });
iesire.url_strain = push.verificaAlerta({ ...bun, url: 'https://altcineva.ro/economic/x/' });
iesire.url_prima = push.verificaAlerta({ ...bun, url: 'https://izz.ro/' });
iesire.url_cu_urmatoare = push.verificaAlerta({ ...bun, url: 'https://izz.ro/economic/x/?utm_source=push' });
iesire.repetat = push.verificaAlerta({ ...bun, text: bun.titlu });

iesire.gazde = {
  bun: push.gazdaAcceptata('https://fcm.googleapis.com/wp/x'),
  http: push.gazdaAcceptata('http://fcm.googleapis.com/wp/x'),
  straina: push.gazdaAcceptata('https://exemplu.rau/push'),
  mozilla: push.gazdaAcceptata('https://updates.push.services.mozilla.com/wpush/v2/abc')
};
iesire.abonament = {
  bun: push.valideazaAbonament({ endpoint: 'https://fcm.googleapis.com/wp/x',
    keys: { p256dh: 'A'.repeat(87), auth: 'B'.repeat(22) } }),
  fara_chei: push.valideazaAbonament({ endpoint: 'https://fcm.googleapis.com/wp/x' }),
  auth_scurt: push.valideazaAbonament({ endpoint: 'https://fcm.googleapis.com/wp/x',
    keys: { p256dh: 'A'.repeat(87), auth: 'B'.repeat(10) } }),
  publica_scurta: push.valideazaAbonament({ endpoint: 'https://fcm.googleapis.com/wp/x',
    keys: { p256dh: 'A'.repeat(40), auth: 'B'.repeat(22) } })
};
iesire.token = {
  corect: push.tokenCorect('abc', 'abc'),
  gresit: push.tokenCorect('abd', 'abc'),
  scurt: push.tokenCorect('ab', 'abc'),
  gol: push.tokenCorect('', 'abc'),
  fara_secret: push.tokenCorect('abc', '')
};
iesire.zi = push.cheieZi(new Date('2026-10-03T22:15:00Z'));
iesire.cai = {
  push: push.esteCalePush('/push/abonare'),
  radacina: push.esteCalePush('/push'),
  articol: push.esteCalePush('/economic/ceva/'),
  inceput: push.esteCalePush('/pushulete')
};
console.log(JSON.stringify(iesire));
"""


def test_modulul_exista():
    assert PUSH_JS.is_file(), "infra/push.js lipseste"


@pytest.mark.skipif(NODE is None, reason=FARA_NODE)
def test_harnessul_poate_pica():
    """Cazul negativ al intregii metode: un modul STRICAT trebuie sa se vada, nu sa treaca."""
    with tempfile.TemporaryDirectory() as tmp:
        stricat = Path(tmp) / "push.js"
        stricat.write_text(PUSH_JS.read_text(encoding="utf-8") + "\nexport const ),(;\n",
                           encoding="utf-8")
        # Scriptul TREBUIE sa importe modulul: fara import, un modul stricat n-ar fi citit
        # de nimeni si „testul care dovedeste ca testele pot pica" ar fi el insusi decor.
        # `pytest.fail` ridica `Failed`, care coboara din BaseException, nu din Exception.
        with pytest.raises(BaseException, match="proba a esuat"):
            _ruleaza("import * as p from '__PUSH__'; console.log(JSON.stringify({ raspuns: !!p }))",
                     stricat)


@pytest.mark.skipif(NODE is None, reason=FARA_NODE)
def test_criptarea_respecta_vectorul_din_rfc8291():
    r = _ruleaza(VECTOR)
    assert r["sare_corecta"], "sarea nu ajunge in antet"
    assert r["idlen"] == 65, "lungimea cheii serverului trebuie sa fie 65 de octeti"
    assert r["cheie_server_corecta"], "cheia publica a serverului nu e in antet"
    assert r["cifru_conforme"], (
        "cifrul NU e cel din RFC 8291 §5 — inseamna ca derivarea CEK/nonce sau AES-GCM e "
        "gresita si nicio alerta nu s-ar putea decripta pe telefon")
    assert r["rs_acopera"], "dimensiunea inregistrarii nu acopera cifrul: mesajul s-ar imparti in bucati"


@pytest.mark.skipif(NODE is None, reason=FARA_NODE)
def test_alerta_se_decripteaza_cu_cheia_clientului():
    r = _ruleaza(VECTOR)
    assert r["roundtrip"], "mesajul criptat nu se intoarce la textul initial"
    assert r["delimitator"] == 2, "RFC 8188 cere delimitatorul 0x02 la finalul textului clar"


@pytest.mark.skipif(NODE is None, reason=FARA_NODE)
def test_vapid_jwt_e_semnat_corect():
    r = _ruleaza(VECTOR)
    assert r["jwt_antet"] == {"typ": "JWT", "alg": "ES256"}
    assert r["jwt_corp"]["aud"] == "https://fcm.googleapis.com"
    assert r["jwt_corp"]["sub"] == "mailto:contact@izz.ro"
    assert r["jwt_corp"]["exp"] == 1700000000 + 12 * 3600
    assert r["jwt_semnat"], "semnatura VAPID nu se verifica — serviciul de push ar refuza alerta"
    assert r["jwt_pem_verificat"], "cheia in forma PEM nu semneaza la fel ca cea in base64url"


@pytest.mark.skipif(NODE is None, reason=FARA_NODE)
def test_politica_accepta_alerta_faptica():
    r = _ruleaza(POLITICA)
    assert r["bun"]["ok"] is True, r["bun"]["motive"]
    assert r["acronim_bun"]["ok"] is True, f"SUA e acronim, nu tipat: {r['acronim_bun']['motive']}"


@pytest.mark.skipif(NODE is None, reason=FARA_NODE)
@pytest.mark.parametrize("caz", ["gol", "emoji", "exclamare", "intrebare", "suspans",
                                 "tipat", "momitor", "text_scurt", "url_strain",
                                 "url_prima", "url_cu_urmatoare", "repetat"])
def test_politica_refuza_clickbaitul(caz):
    """Fiecare refuz trebuie sa si POATA sa apara: o politica ce accepta tot nu e politica."""
    r = _ruleaza(POLITICA)
    assert r[caz]["ok"] is False
    assert r[caz]["motive"], "refuzul fara motiv nu ajuta pe nimeni"


@pytest.mark.skipif(NODE is None, reason=FARA_NODE)
def test_validari_de_intrare():
    r = _ruleaza(POLITICA)
    g = r["gazde"]
    assert g["bun"] and g["mozilla"]
    assert not g["http"] and not g["straina"]
    a = r["abonament"]
    assert a["bun"] is None, a["bun"]
    assert a["fara_chei"] and a["auth_scurt"] and a["publica_scurta"]
    t = r["token"]
    assert t["corect"] and not t["gresit"] and not t["scurt"] and not t["gol"] and not t["fara_secret"]
    assert r["zi"] == "2026-10-03"
    c = r["cai"]
    assert c["push"] and c["radacina"]
    assert not c["articol"] and not c["inceput"]
