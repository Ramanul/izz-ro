const json = (body, status = 200, extra = {}) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": status === 200 ? "public, max-age=60" : "no-store", ...extra },
});

const cors = { "access-control-allow-origin": "*", "access-control-allow-headers": "content-type,x-izz-lead-key,x-izz-session", "access-control-allow-methods": "GET,POST,OPTIONS" };

function actionsFor(text) {
  const value = String(text || "").toLocaleLowerCase("ro-RO");
  const actions = [];
  if (["salari", "tax", "impozit", "venit"].some((x) => value.includes(x))) actions.push("Calculează impactul pentru profilul tău");
  if (["lege", "ordonan", "reglement", "guvern", "minister"].some((x) => value.includes(x))) actions.push("Verifică textul oficial și termenul de aplicare");
  if (["achizi", "contract", "licit", "proiect"].some((x) => value.includes(x))) actions.push("Caută oportunități și contracte similare");
  if (["preț", "energie", "credit", "asigur", "rca", "locuin"].some((x) => value.includes(x))) actions.push("Compară ofertele și costul total");
  return actions.length ? actions : ["Salvează subiectul și activează o alertă de schimbare"];
}

function sessionKey(request) {
  const value = request.headers.get("x-izz-session") || "";
  return value.length >= 16 && value.length <= 128 ? value : null;
}

async function getCompany(db, cui) {
  const key = String(cui || "").replace(/\s+/g, "").toUpperCase();
  if (!key) return null;
  const entity = await db.prepare("SELECT id, canonical_name, city, region, external_key FROM entities WHERE kind = 'company' AND external_key = ? LIMIT 1").bind(key).first();
  if (!entity) return null;
  const observations = await db.prepare(`SELECT type, title, summary, url, published_at, observed_at, confidence, value_number, value_currency
    FROM observations WHERE entity_id = ? ORDER BY COALESCE(published_at, observed_at) DESC LIMIT 50`).bind(entity.id).all();
  return { ...entity, changes: observations.results || [] };
}

async function getMarket(db) {
  const result = await db.prepare(`SELECT o.type AS kind, COUNT(*) AS count, ROUND(AVG(o.confidence)) AS confidence
    FROM observations o GROUP BY o.type ORDER BY count DESC LIMIT 50`).all();
  return result.results || [];
}

async function getMonitors(db, request) {
  const owner = sessionKey(request);
  if (!owner) return json({ error: "session_required" }, 401, cors);
  const result = await db.prepare(`SELECT id, target_type, target_id, frequency, active, created_at, updated_at
    FROM monitors WHERE owner_key = ? ORDER BY updated_at DESC`).bind(owner).all();
  return json({ schema: "izz-intelligence-v1", monitors: result.results || [] }, 200, cors);
}

async function getMonitorChanges(db, request, targetType, targetId) {
  const owner = sessionKey(request);
  if (!owner) return json({ error: "session_required" }, 401, cors);
  const monitor = await db.prepare(`SELECT id FROM monitors WHERE owner_key = ? AND target_type = ? AND target_id = ? AND active = 1 LIMIT 1`)
    .bind(owner, targetType, targetId).first();
  if (!monitor) return json({ error: "monitor_not_found" }, 404, cors);
  const result = await db.prepare(`SELECT o.id, o.type, o.title, o.summary, o.url, o.published_at, o.observed_at, o.confidence
    FROM observations o
    JOIN entities e ON e.id = o.entity_id
    WHERE e.id = ?
    ORDER BY COALESCE(o.published_at, o.observed_at) DESC LIMIT 100`).bind(targetId).all();
  return json({ schema: "izz-intelligence-v1", monitor_id: monitor.id, changes: result.results || [] }, 200, cors);
}

async function createMonitor(request, env) {
  const owner = sessionKey(request);
  if (!owner) return json({ error: "session_required" }, 401, cors);
  const body = await request.json();
  const targetType = String(body.target_type || "").trim();
  const targetId = String(body.target_id || "").trim();
  const frequency = String(body.frequency || "weekly").trim();
  const allowed = new Set(["company", "institution", "topic", "profession", "competitor"]);
  const frequencies = new Set(["daily", "weekly"]);
  if (!allowed.has(targetType) || !targetId || targetId.length > 200) return json({ error: "invalid_target" }, 400, cors);
  if (!frequencies.has(frequency)) return json({ error: "invalid_frequency" }, 400, cors);
  const now = new Date().toISOString();
  const id = crypto.randomUUID();
  await env.IZZ_DB.prepare(`INSERT INTO monitors (id, owner_key, target_type, target_id, frequency, active, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
    ON CONFLICT(owner_key, target_type, target_id) DO UPDATE SET frequency = excluded.frequency, active = 1, updated_at = excluded.updated_at`)
    .bind(id, owner, targetType, targetId, frequency, now, now).run();
  const saved = await env.IZZ_DB.prepare(`SELECT id, owner_key, target_type, target_id, frequency, active, created_at, updated_at
    FROM monitors WHERE owner_key = ? AND target_type = ? AND target_id = ? LIMIT 1`).bind(owner, targetType, targetId).first();
  return json({ schema: "izz-intelligence-v1", monitor: saved }, 201, cors);
}

async function createLead(request, env) {
  const expected = env.LEAD_INGEST_KEY;
  const supplied = request.headers.get("x-izz-lead-key");
  if (!expected || supplied !== expected) return json({ error: "lead_ingest_disabled" }, 403, cors);
  const body = await request.json();
  const need = String(body.need || "").trim();
  if (!need) return json({ error: "need_required" }, 400, cors);
  if (need.length > 300 || String(body.city || "").length > 120 || String(body.budget || "").length > 40) {
    return json({ error: "field_too_long" }, 400, cors);
  }
  const now = new Date().toISOString();
  const id = crypto.randomUUID();
  await env.IZZ_DB.prepare(`INSERT INTO leads (id, session_key, need, city, budget, score, status, created_at)
    VALUES (?, ?, ?, ?, ?, 0, 'new', ?)`).bind(id, body.session_key || null, need, body.city || null, body.budget || null, now).run();
  return json({ id, status: "new", created_at: now }, 201, cors);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (!env.IZZ_DB) return json({ error: "intelligence_db_not_configured" }, 503, cors);
    const url = new URL(request.url);
    try {
      if (request.method === "GET" && url.pathname === "/api/intelligence/market") {
        return json({ schema: "izz-intelligence-v1", section: "market", data: await getMarket(env.IZZ_DB) }, 200, cors);
      }
      if (request.method === "GET" && url.pathname === "/api/intelligence/company") {
        const company = await getCompany(env.IZZ_DB, url.searchParams.get("cui"));
        return company ? json({ schema: "izz-intelligence-v1", data: company }, 200, cors) : json({ error: "company_not_found" }, 404, cors);
      }
      if (request.method === "GET" && url.pathname === "/api/intelligence/monitors") return getMonitors(env.IZZ_DB, request);
      if (request.method === "GET" && url.pathname === "/api/intelligence/monitor") {
        return getMonitorChanges(env.IZZ_DB, request, url.searchParams.get("target_type"), url.searchParams.get("target_id"));
      }
      if (request.method === "POST" && url.pathname === "/api/intelligence/monitors") return createMonitor(request, env);
      if (request.method === "POST" && url.pathname === "/api/intelligence/leads") return createLead(request, env);
      if (request.method === "POST" && url.pathname === "/api/intelligence/actions") {
        const body = await request.json();
        if (String(body.text || "").length > 2000) return json({ error: "text_too_long" }, 400, cors);
        return json({ schema: "izz-intelligence-v1", actions: actionsFor(body.text) }, 200, cors);
      }
      return json({ error: "not_found" }, 404, cors);
    } catch (error) {
      console.error("IZZ Intelligence API error", error);
      return json({ error: "internal_error" }, 500, cors);
    }
  },
};
