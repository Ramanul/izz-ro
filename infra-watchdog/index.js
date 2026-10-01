/**
 * izz-watchdog — sondă gratuită la edge pentru pipeline-ul de build izz.ro.
 *
 * De ce există: site-ul e reconstruit de GitHub Actions, iar Actions poate
 * întârzia cronurile programate cu 62-200 de minute — „cronul a întârziat" e
 * de nedistins de „site-ul e căzut" dacă nimeni nu sondează independent.
 * Worker-ul rulează la fiecare 20 de minute, ia build.json de pe ambele origini
 * (domeniul primar izz.ro + oglinda GitHub Pages), compară cu starea
 * anterioară ținută în KV și scrie un WATCHDOG ALERT prin console.error când o
 * origine pică repetat. Workers Observability colectează logurile de eroare —
 * singura suprafață de alertă gratuită disponibilă aici.
 *
 * Fără dependențe, fără rute, fără trafic HTTP: rulează doar la cron.
 */

const KV_KEY = "status";
const FETCH_TIMEOUT_MS = 10000; // 10s per origine, acoperă fetch + citirea corpului
const ALERT_STREAK = 2;

const ORIGINS = {
  primary: "https://izz.ro/build.json",
  // Oglinda GitHub Pages (repo-ul extern ramanul.github.io, jobul `mirror` din build.yml).
  // Spec-ul initial zicea subdomenia workers.dev, dar prima rulare reala a sondei (KV,
  // 2026-10-01 17:20 UTC) a primit 404 de acolo — fetch din worker catre un workers.dev al
  // ACELUIASI cont, in timp ce acelasi URL raspunde 200 din exterior. Oglinda pe host
  // independent (GitHub) e accesibila din edge si testeaza efectiv failover-ul final.
  public: "https://ramanul.github.io/build.json",
};

const USER_AGENT = "izz-watchdog/1.0 (+https://izz.ro)";

function errText(err) {
  return err && err.message ? err.message : String(err);
}

/**
 * Sondează o origine. Nu aruncă niciodată: orice mod de eșec (eroare de rețea,
 * timeout, non-200, JSON neparsabil) devine rezultat de eșec, nu crash total.
 * code=0 înseamnă că cererea însăși a eșuat (DNS, TLS, timeout).
 * Un 200 cu JSON neparsabil e contorizat ca eșec INTENȚIONAT: zona izz.ro are
 * bot challenge, iar interstitiul se servește uneori cu 200 — fără verificaarea
 * asta, o origine blocată de challenge ar arăta „sănătoasă".
 */
async function probe(url) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    let res;
    try {
      res = await fetch(url, {
        signal: ctrl.signal,
        headers: { "User-Agent": USER_AGENT },
      });
    } catch (err) {
      const reason =
        err && err.name === "AbortError"
          ? `timeout after ${FETCH_TIMEOUT_MS}ms`
          : `fetch error: ${errText(err)}`;
      return { ok: false, code: 0, commit: null, reason };
    }

    if (res.status !== 200) {
      return { ok: false, code: res.status, commit: null, reason: `http ${res.status}` };
    }

    let body;
    try {
      body = await res.json();
    } catch (err) {
      if (err && err.name === "AbortError") {
        return { ok: false, code: res.status, commit: null, reason: "timeout while reading body" };
      }
      return {
        ok: false,
        code: res.status,
        commit: null,
        reason: `200 with unparsable JSON: ${errText(err)}`,
      };
    }

    const commit = body && typeof body.commit === "string" ? body.commit : null;
    return { ok: true, code: res.status, commit, reason: null };
  } finally {
    // Timerele se anulează DUPĂ citirea corpului, ca timeout-ul să acopere tot.
    clearTimeout(timer);
  }
}

/** Citește starea anterioară din KV; date lipsă sau corupte = „fără stare". */
async function readPrevState(env) {
  try {
    const raw = await env.WATCHDOG_KV.get(KV_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

/**
 * Combină rezultatul sondei cu starea anterioară a originii.
 * Succes: fail_streak revine la 0 și commitul se actualizează.
 * Eșec: fail_streak crește; se păstrează ultimul commit cunoscut, ca alerta
 * să arate pe ce build era originea înainte să apună.
 */
function mergeSlot(prevSlot, result) {
  const prev = prevSlot && typeof prevSlot === "object" ? prevSlot : {};
  const prevStreak =
    Number.isInteger(prev.fail_streak) && prev.fail_streak >= 0 ? prev.fail_streak : 0;
  const commit = result.ok ? result.commit : typeof prev.commit === "string" ? prev.commit : null;
  return {
    ok: result.ok,
    code: result.code,
    commit,
    fail_streak: result.ok ? 0 : prevStreak + 1,
  };
}

export default {
  async scheduled(controller, env, ctx) {
    if (
      !env ||
      !env.WATCHDOG_KV ||
      typeof env.WATCHDOG_KV.get !== "function" ||
      typeof env.WATCHDOG_KV.put !== "function"
    ) {
      console.error("WATCHDOG ALERT: KV binding WATCHDOG_KV missing or invalid - cannot track state");
      return;
    }

    const prev = await readPrevState(env);

    // Sondele pornesc simultan; probe() nu aruncă, deci o origine căzută
    // nu poate crash-ui rularea celeilalte.
    const [primaryResult, publicResult] = await Promise.all([
      probe(ORIGINS.primary),
      probe(ORIGINS.public),
    ]);

    const record = {
      ts: new Date().toISOString(),
      primary: mergeSlot(prev && prev.primary, primaryResult),
      public: mergeSlot(prev && prev.public, publicResult),
    };

    const slots = [
      ["primary", ORIGINS.primary, primaryResult, record.primary],
      ["public", ORIGINS.public, publicResult, record.public],
    ];

    for (const [name, url, result, slot] of slots) {
      if (slot.fail_streak >= ALERT_STREAK) {
        // Singura suprafață de alertă: console.error -> Workers Observability.
        console.error(
          `WATCHDOG ALERT: origin "${name}" (${url}) is failing - ` +
            `fail_streak=${slot.fail_streak}, http_code=${slot.code}, ` +
            `last_commit=${slot.commit ?? "none"}, reason=${result.reason ?? "n/a"}, ` +
            `checked_at=${record.ts}`
        );
      } else if (!slot.ok) {
        // Sub pragul de alertă; se loghează ca să fie vizibilă și o singură defecțiune.
        console.log(
          `WATCHDOG WARN: origin "${name}" (${url}) failed this run - ` +
            `fail_streak=${slot.fail_streak}, http_code=${slot.code}, ` +
            `reason=${result.reason ?? "n/a"}, checked_at=${record.ts}`
        );
      }
    }

    // Starea nouă se scrie prin waitUntil: nu blochează întoarcerea handlerului.
    ctx.waitUntil(
      env.WATCHDOG_KV.put(KV_KEY, JSON.stringify(record)).catch((err) => {
        console.error(`WATCHDOG ALERT: KV write failed - ${errText(err)}`);
      })
    );
  },
};
