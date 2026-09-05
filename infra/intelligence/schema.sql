-- IZZ Intelligence shared data layer.
-- Designed for Cloudflare D1; no credentials or deployment are embedded here.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('rss', 'ckan', 'web', 'api', 'seap')),
  license TEXT,
  last_seen_at TEXT,
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1))
);

CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('company', 'institution', 'person', 'place', 'topic', 'project', 'tender')),
  canonical_name TEXT NOT NULL,
  external_key TEXT,
  city TEXT,
  region TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(kind, external_key)
);

CREATE TABLE IF NOT EXISTS observations (
  id TEXT PRIMARY KEY,
  entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  observed_at TEXT NOT NULL,
  published_at TEXT,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT,
  url TEXT,
  value_number REAL,
  value_currency TEXT,
  confidence INTEGER NOT NULL DEFAULT 0 CHECK (confidence BETWEEN 0 AND 100),
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS observations_entity_time ON observations(entity_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS observations_source_time ON observations(source_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS opportunities (
  id TEXT PRIMARY KEY,
  entity_id TEXT REFERENCES entities(id) ON DELETE SET NULL,
  observation_id TEXT REFERENCES observations(id) ON DELETE SET NULL,
  kind TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
  status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'qualified', 'dismissed', 'converted')),
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS opportunities_score ON opportunities(score DESC, updated_at DESC);

CREATE TABLE IF NOT EXISTS monitors (
  id TEXT PRIMARY KEY,
  owner_key TEXT NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('company', 'institution', 'topic', 'profession', 'competitor')),
  target_id TEXT NOT NULL,
  frequency TEXT NOT NULL DEFAULT 'weekly',
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(owner_key, target_type, target_id)
);

CREATE TABLE IF NOT EXISTS provider_profiles (
  entity_id TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
  categories_json TEXT NOT NULL DEFAULT '[]',
  cities_json TEXT NOT NULL DEFAULT '[]',
  budgets_json TEXT NOT NULL DEFAULT '[]',
  contact TEXT,
  verified INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0,1)),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  session_key TEXT,
  need TEXT NOT NULL,
  city TEXT,
  budget TEXT,
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'matched', 'sent', 'accepted', 'rejected', 'closed')),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS leads_status_time ON leads(status, created_at DESC);

CREATE TABLE IF NOT EXISTS lead_matches (
  lead_id TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  provider_entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
  reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'sent', 'accepted', 'rejected', 'closed')),
  created_at TEXT NOT NULL,
  PRIMARY KEY (lead_id, provider_entity_id)
);

CREATE INDEX IF NOT EXISTS lead_matches_score ON lead_matches(lead_id, score DESC);

CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  observation_id TEXT REFERENCES observations(id) ON DELETE SET NULL,
  action_type TEXT NOT NULL,
  label TEXT NOT NULL,
  href TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  starts_at TEXT NOT NULL,
  ends_at TEXT,
  location TEXT,
  online_url TEXT,
  description TEXT,
  capacity INTEGER,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'cancelled', 'past')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_exports (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  format TEXT NOT NULL CHECK (format IN ('json', 'csv')),
  generated_at TEXT NOT NULL,
  object_key TEXT NOT NULL,
  row_count INTEGER NOT NULL DEFAULT 0
);
