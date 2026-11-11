// r2-paznic.js — paznicul de cost pentru Cloudflare R2.
//
// DE CE EXISTA: R2 nu are plafon de cheltuiala. Peste pragurile gratuite taxeaza automat
// cardul contului (developers.cloudflare.com/r2/pricing/, citit 2026-11-11):
//   stocare   10 GB-luna      apoi 0,015 $/GB-luna
//   Clasa A   1.000.000/luna  apoi 4,50 $/milion   (scrieri, listari)
//   Clasa B   10.000.000/luna apoi 0,36 $/milion   (citiri)
// Paznicul masoara consumul lunii si TAIE accesul public la citire inainte de prag.
//
// CE NU POATE (scris aici ca sa nu fie redescoperit pe factura):
//   * Ruleaza la 20 de minute, iar analytics are intarziere de ordinul minutelor. Un val care
//     ocoleste cache-ul poate consuma intre doua rulari. Apararea pentru asta e regula de cache
//     de pe domeniul imaginilor (ignora query string), nu paznicul.
//   * Stocarea NU se opreste taind citirile. La depasire, paznicul doar ridica steagul
//     `scrieri_oprite`; cine scrie (pipeline-ul) trebuie sa-l respecte, iar regula de lifecycle
//     a bucket-ului sterge ce e vechi.
//   * Taie doar domeniile publice. Un Worker cu binding R2 sau o cheie S3 raman deschise.
//   * Nu reactiveaza singur. Dupa o taiere, repornirea e manuala, cu contorul sub prag.
//
// INERT fara configurare: fara `R2_PAZNIC_BUCKET` nu face nimic, deci deploy-ul codului nu
// schimba comportamentul pana cand bucket-ul exista si variabila e setata.

export const GRATUIT = Object.freeze({
  // 10 GB socotiti zecimal (10^9), varianta mai mica dintre cele doua citiri posibile: daca
  // Cloudflare socoteste binar (2^30), pragul nostru cade mai devreme, nu mai tarziu.
  stocare_octeti: 10 * 1e9,
  clasa_a: 1_000_000,
  clasa_b: 10_000_000,
});

export const PRAG_AVERTISMENT = 0.7;
export const PRAG_TAIERE = 0.9;
// 6 rulari x 20 min = 2 ore fara masuratoare, cu domeniul public deschis -> taiem pe nevazute.
export const ESECURI_PANA_LA_TAIERE = 6;
export const CHEIE_KV = "r2-paznic";

const API = "https://api.cloudflare.com/client/v4";

// Listele sunt cele din pagina de preturi R2. Un tip care nu apare in niciuna e socotit
// Clasa A (cea scumpa) si raportat, ca o operatie noua sa nu treaca nenumarata.
const CLASA_A = new Set([
  "ListBuckets", "PutBucket", "ListObjects", "PutObject", "CopyObject",
  "CompleteMultipartUpload", "CreateMultipartUpload", "LifecycleStorageTierTransition",
  "ListMultipartUploads", "UploadPart", "UploadPartCopy", "ListParts",
  "PutBucketEncryption", "PutBucketCors", "PutBucketLifecycleConfiguration",
]);
const CLASA_B = new Set([
  "HeadBucket", "HeadObject", "GetObject", "UsageSummary", "GetBucketEncryption",
  "GetBucketLocation", "GetBucketCors", "GetBucketLifecycleConfiguration",
]);
const GRATIS = new Set(["DeleteObject", "DeleteBucket", "AbortMultipartUpload"]);

export function clasifica(actionType) {
  if (CLASA_A.has(actionType)) return "a";
  if (CLASA_B.has(actionType)) return "b";
  if (GRATIS.has(actionType)) return "gratis";
  return "necunoscut";
}

/** Aduna randurile `{actionType, requests}` pe clase. Necunoscutele intra la Clasa A. */
export function aduna(randuri) {
  const total = { clasa_a: 0, clasa_b: 0, necunoscute: [] };
  for (const rand of randuri || []) {
    const n = Number(rand && rand.requests) || 0;
    const clasa = clasifica(rand && rand.actionType);
    if (clasa === "a") total.clasa_a += n;
    else if (clasa === "b") total.clasa_b += n;
    else if (clasa === "necunoscut") {
      total.clasa_a += n;
      if (!total.necunoscute.includes(String(rand && rand.actionType))) {
        total.necunoscute.push(String(rand && rand.actionType));
      }
    }
  }
  return total;
}

function nivel(fractie) {
  if (fractie >= PRAG_TAIERE) return "taie";
  if (fractie >= PRAG_AVERTISMENT) return "avertisment";
  return "ok";
}

/**
 * Din consum -> decizie. Operatiile si stocarea se judeca separat, fiindca se opresc
 * diferit: operatiile prin taierea accesului public, stocarea doar prin oprirea scrierilor.
 */
export function decide(consum) {
  const f = {
    clasa_a: consum.clasa_a / GRATUIT.clasa_a,
    clasa_b: consum.clasa_b / GRATUIT.clasa_b,
    stocare: consum.stocare_octeti / GRATUIT.stocare_octeti,
  };
  const ordine = { ok: 0, avertisment: 1, taie: 2 };
  const a = nivel(f.clasa_a);
  const b = nivel(f.clasa_b);
  const operatii = ordine[a] >= ordine[b] ? a : b;
  const stocare = nivel(f.stocare);
  const motive = [];
  for (const [nume, fr] of Object.entries(f)) {
    if (fr >= PRAG_AVERTISMENT) motive.push(`${nume}=${(fr * 100).toFixed(1)}%`);
  }
  return {
    operatii,
    stocare,
    procente: {
      clasa_a: +(f.clasa_a * 100).toFixed(2),
      clasa_b: +(f.clasa_b * 100).toFixed(2),
      stocare: +(f.stocare * 100).toFixed(2),
    },
    motive,
  };
}

export function lunaCurenta(acum) {
  return acum.toISOString().slice(0, 7);
}

function stareGoala(luna) {
  return {
    luna,
    operatii: "ok",
    stocare: "ok",
    taiat: false,
    scrieri_oprite: false,
    domenii_oprite: [],
    esecuri: 0,
    motiv_taiere: null,
  };
}

/**
 * Starea pentru luna curenta. La schimbarea lunii contoarele pornesc de la zero, dar
 * `taiat`, `scrieri_oprite` si `domenii_oprite` RAMAN: paznicul nu reactiveaza singur.
 */
export function stareaLunii(veche, luna) {
  if (!veche || typeof veche !== "object") return stareGoala(luna);
  // `esecuri` trece prin Number: un NaN ajuns in KV ar face `NaN >= 6` fals pentru totdeauna
  // si ar opri pe tacute taierea pe nevazute.
  const esecuri = Number.isInteger(veche.esecuri) && veche.esecuri > 0 ? veche.esecuri : 0;
  if (veche.luna === luna) return { ...stareGoala(luna), ...veche, esecuri };
  return {
    ...stareGoala(luna),
    // Sirul de masuratori esuate NU tine de luna de facturare: resetat la miezul noptii de
    // 1 ale lunii ar amana taierea pe nevazute cu pana la doua ore.
    esecuri,
    taiat: !!veche.taiat,
    scrieri_oprite: !!veche.scrieri_oprite,
    domenii_oprite: Array.isArray(veche.domenii_oprite) ? [...veche.domenii_oprite] : [],
    motiv_taiere: veche.motiv_taiere || null,
  };
}

async function cere(env, fetchFn, metoda, cale, corp) {
  const r = await fetchFn(`${API}${cale}`, {
    method: metoda,
    headers: {
      authorization: `Bearer ${env.CF_API_TOKEN_R2}`,
      "content-type": "application/json",
    },
    body: corp === undefined ? undefined : JSON.stringify(corp),
  });
  let date = null;
  try {
    date = await r.json();
  } catch {
    // corp ne-JSON: tratat mai jos ca esec
  }
  if (!r.ok || !date || date.success === false || (Array.isArray(date.errors) && date.errors.length)) {
    const mesaj = date && Array.isArray(date.errors) && date.errors[0] ? date.errors[0].message : "fara detalii";
    throw new Error(`${metoda} ${cale} -> HTTP ${r.status}: ${mesaj}`);
  }
  return date;
}

const INTEROGARE = `query($cont:String!,$luna:Time!,$recent:Time!){viewer{accounts(filter:{accountTag:$cont}){
r2OperationsAdaptiveGroups(limit:1000,filter:{datetime_geq:$luna}){sum{requests} dimensions{actionType}}
r2StorageAdaptiveGroups(limit:1000,filter:{datetime_geq:$recent}){max{payloadSize metadataSize} dimensions{bucketName}}
}}}`;

/**
 * Consumul contului: operatiile de la inceputul lunii (UTC) si stocarea curenta.
 * Stocarea = maximul ultimelor 48h pe fiecare bucket, adunat. Nu maximul lunii: un varf
 * sters de mult ar bloca scrierile degeaba. E totusi mai pesimist decat factura, care
 * socoteste media zilnica — pesimismul e directia sigura.
 */
export async function masoara(env, acum, fetchFn) {
  const luna = new Date(Date.UTC(acum.getUTCFullYear(), acum.getUTCMonth(), 1)).toISOString();
  const recent = new Date(acum.getTime() - 48 * 3600 * 1000).toISOString();
  const raspuns = await cere(env, fetchFn, "POST", "/graphql", {
    query: INTEROGARE,
    variables: { cont: env.CF_ACCOUNT_ID, luna, recent },
  });
  const cont = raspuns.data && raspuns.data.viewer && raspuns.data.viewer.accounts && raspuns.data.viewer.accounts[0];
  if (!cont || !Array.isArray(cont.r2OperationsAdaptiveGroups) || !Array.isArray(cont.r2StorageAdaptiveGroups)) {
    // Un raspuns fara cele doua liste NU inseamna „consum zero": e o masuratoare esuata.
    throw new Error("raspuns GraphQL fara datele R2 asteptate");
  }
  const operatii = aduna(
    cont.r2OperationsAdaptiveGroups.map((g) => ({
      actionType: g.dimensions && g.dimensions.actionType,
      requests: g.sum && g.sum.requests,
    }))
  );
  const peBucket = new Map();
  for (const g of cont.r2StorageAdaptiveGroups) {
    const nume = (g.dimensions && g.dimensions.bucketName) || "";
    const octeti = (Number(g.max && g.max.payloadSize) || 0) + (Number(g.max && g.max.metadataSize) || 0);
    peBucket.set(nume, Math.max(peBucket.get(nume) || 0, octeti));
  }
  let stocare_octeti = 0;
  for (const v of peBucket.values()) stocare_octeti += v;
  return { ...operatii, stocare_octeti };
}

/**
 * Opreste citirea publica a bucket-ului: toate domeniile proprii + adresa r2.dev.
 * Idempotent — se cheama la fiecare rulare cat timp nivelul e „taie", ca o
 * reactivare manuala facuta peste prag sa nu ramana deschisa.
 */
export async function taieAccesPublic(env, fetchFn) {
  const bucket = encodeURIComponent(env.R2_PAZNIC_BUCKET);
  const baza = `/accounts/${env.CF_ACCOUNT_ID}/r2/buckets/${bucket}/domains`;
  const oprite = [];
  const lista = await cere(env, fetchFn, "GET", `${baza}/custom`);
  const domenii = (lista.result && Array.isArray(lista.result.domains) && lista.result.domains) || [];
  for (const d of domenii) {
    if (!d || !d.domain || d.enabled === false) continue;
    await cere(env, fetchFn, "PUT", `${baza}/custom/${encodeURIComponent(d.domain)}`, { enabled: false });
    oprite.push(d.domain);
  }
  const gestionat = await cere(env, fetchFn, "GET", `${baza}/managed`);
  if (gestionat.result && gestionat.result.enabled) {
    await cere(env, fetchFn, "PUT", `${baza}/managed`, { enabled: false });
    oprite.push("r2.dev");
  }
  return oprite;
}

async function trimiteEmailImplicit(env, subiect, text) {
  // Optional: fara binding sau fara adrese, alerta ramane doar in loguri (console.error).
  if (!env.ALERTA_EMAIL || !env.ALERTA_DE || !env.ALERTA_CATRE) return false;
  const { EmailMessage } = await import("cloudflare:email");
  const domeniu = String(env.ALERTA_DE).split("@")[1] || "izz.ro";
  const brut = [
    `From: izz-watchdog <${env.ALERTA_DE}>`,
    `To: <${env.ALERTA_CATRE}>`,
    `Subject: ${subiect}`,
    `Message-ID: <${Date.now()}.${Math.random().toString(36).slice(2)}@${domeniu}>`,
    `Date: ${new Date().toUTCString()}`,
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=utf-8",
    "",
    text,
  ].join("\r\n");
  await env.ALERTA_EMAIL.send(new EmailMessage(env.ALERTA_DE, env.ALERTA_CATRE, brut));
  return true;
}

async function anunta(env, trimiteEmail, subiect, text) {
  console.error(`R2 PAZNIC ALERT: ${subiect} - ${text}`);
  try {
    await trimiteEmail(env, subiect, text);
  } catch (err) {
    console.error(`R2 PAZNIC ALERT: e-mailul de alerta a esuat - ${err && err.message}`);
  }
}

/**
 * O rulare a paznicului. Nu arunca: orice esec devine log + contor, ca sonda de origini
 * din acelasi Worker sa nu fie afectata.
 * Scrie in KV DOAR cand starea se schimba (KV Free: 1.000 de scrieri/zi).
 */
export async function ruleazaPaznic(env, optiuni = {}) {
  const acum = optiuni.acum || new Date();
  const fetchFn = optiuni.fetchFn || fetch;
  const trimiteEmail = optiuni.trimiteEmail || trimiteEmailImplicit;

  if (!env.R2_PAZNIC_BUCKET) return { rulat: false, motiv: "neconfigurat" };
  if (!env.CF_API_TOKEN_R2 || !env.CF_ACCOUNT_ID) {
    // Bucket declarat, dar fara cheie: protectia e OPRITA fara sa se vada. Eroare, nu info.
    console.error("R2 PAZNIC ALERT: R2_PAZNIC_BUCKET e setat, dar lipseste CF_API_TOKEN_R2 sau CF_ACCOUNT_ID - consumul R2 NU e pazit");
    return { rulat: false, motiv: "fara-cheie" };
  }

  const luna = lunaCurenta(acum);
  let brut = null;
  let veche = null;
  // Citire esuata != cheie lipsa. Daca KV nu raspunde, rularea masoara si taie in continuare,
  // dar NU scrie starea la final: altfel o stare goala ar sterge `taiat`, `scrieri_oprite`
  // si contorul de esecuri. Un JSON stricat, in schimb, se inlocuieste.
  let citireEsuata = false;
  try {
    brut = await env.WATCHDOG_KV.get(CHEIE_KV);
  } catch (err) {
    citireEsuata = true;
    console.error(`R2 PAZNIC ALERT: citirea starii din KV a esuat - ${err && err.message}`);
  }
  try {
    veche = brut ? JSON.parse(brut) : null;
  } catch {
    veche = null;
  }
  const stare = stareaLunii(veche, luna);

  let consum = null;
  let decizie = null;
  try {
    consum = await masoara(env, acum, fetchFn);
    stare.esecuri = 0;
    decizie = decide(consum);
    if (consum.necunoscute.length) {
      console.log(`R2 PAZNIC WARN: tipuri de operatii necunoscute, socotite Clasa A: ${consum.necunoscute.join(", ")}`);
    }
  } catch (err) {
    stare.esecuri += 1;
    console.error(`R2 PAZNIC ALERT: masuratoarea a esuat (${stare.esecuri} la rand) - ${err && err.message}`);
    // Fara `&& !stare.taiat`: steagul ramane ridicat si dupa o repornire manuala, deci
    // conditionat de el paznicul n-ar mai taia pe nevazute niciodata dupa prima taiere.
    // Taierea e idempotenta: pe domenii deja oprite nu face si nu anunta nimic.
    if (stare.esecuri >= ESECURI_PANA_LA_TAIERE) {
      decizie = {
        operatii: "taie",
        stocare: stare.stocare,
        procente: null,
        motive: [`masuratoare esuata de ${stare.esecuri} ori la rand`],
      };
    }
  }

  if (decizie) {
    if (decizie.operatii === "taie") {
      try {
        const oprite = await taieAccesPublic(env, fetchFn);
        for (const d of oprite) if (!stare.domenii_oprite.includes(d)) stare.domenii_oprite.push(d);
        if (!stare.taiat) {
          stare.taiat = true;
          stare.motiv_taiere = decizie.motive.join("; ");
          await anunta(env, trimiteEmail, "R2: acces public TAIAT",
            `motiv: ${stare.motiv_taiere}; domenii oprite: ${stare.domenii_oprite.join(", ") || "niciunul activ"}; repornirea e manuala`);
        } else if (oprite.length) {
          await anunta(env, trimiteEmail, "R2: acces public taiat DIN NOU",
            `motiv: ${decizie.motive.join("; ")}; erau reactivate: ${oprite.join(", ")}`);
        }
      } catch (err) {
        // Cel mai rau caz: stim ca trebuie taiat si nu putem. Se striga la fiecare rulare.
        await anunta(env, trimiteEmail, "R2: TAIEREA A ESUAT",
          `consumul e peste prag si accesul public NU a putut fi oprit - ${err && err.message}`);
      }
    } else if (decizie.operatii === "avertisment" && stare.operatii === "ok") {
      await anunta(env, trimiteEmail, "R2: avertisment operatii", decizie.motive.join("; "));
    }

    if (decizie.stocare === "taie" && !stare.scrieri_oprite) {
      stare.scrieri_oprite = true;
      await anunta(env, trimiteEmail, "R2: stocare la prag, scrieri oprite",
        `${decizie.motive.join("; ")}; taierea citirilor NU elibereaza spatiu`);
    } else if (decizie.stocare === "avertisment" && stare.stocare === "ok") {
      await anunta(env, trimiteEmail, "R2: avertisment stocare", decizie.motive.join("; "));
    }

    if (decizie.procente) {
      stare.operatii = decizie.operatii;
      stare.stocare = decizie.stocare;
    }
  }

  const acumText = JSON.stringify(stare);
  if (acumText !== brut && !citireEsuata) {
    try {
      await env.WATCHDOG_KV.put(CHEIE_KV, acumText);
    } catch (err) {
      console.error(`R2 PAZNIC ALERT: scrierea starii in KV a esuat - ${err && err.message}`);
    }
  }
  return { rulat: true, stare, consum, decizie };
}
