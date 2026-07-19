# SPEC — Scanner de verificare a site-urilor primăriilor din România

Read `AGENTS.md` in the repo root first and follow it strictly.

**Goal:** a reusable, stdlib-only script `tools/check_primarii.py` that programmatically audits every
city-hall website listed in `data/raport_complet_primarii.csv` (is it alive, is it a real primărie
site, how fresh is its content, does it expose an RSS/Atom feed usable as a news source for izz.ro)
and writes a per-site CSV report — validated on a 40-site sample in this task; the full 3193-site
scan will be run by the manager later, NOT by you.

**Verified premises** (manager checked these against the repo on 2026-07-19):
- `data/raport_complet_primarii.csv` exists, 3194 lines incl. header `Județ,Localitate,Website,Email,Telefon`; Website values like `https://apulum.ro/`, `http://www.aiud.ro/` — verified by reading the file.
- `data/primarii_domains_all.txt` exists (3174 bare domains, one per line, contains some noise like ISP domains) — context only, the CSV is the authoritative input.
- `tools/check_primarii.py` does NOT exist yet — verified via `ls tools/`.
- `tools/feed_check.py` exists and uses stdlib `urllib.request` + `feedparser`; do NOT modify it, but you may read it for conventions (User-Agent, timeouts).
- Python on this machine runs plain `python`; this shell has internet access.

**User WIP — UNTOUCHABLE** (do not restore/stash/stage/commit these):
- `data/entities/salariul-minim.yaml` (modified)
- `generator/render.py` (modified)

**Scope — authorized files ONLY:**
1. `tools/check_primarii.py` — create — the scanner (see requirements below).
2. `data/raport_complet_primarii.csv` — `git add` AS-IS on your branch (input data, do not edit its content).
3. `data/primarii_domains_all.txt` — `git add` AS-IS on your branch (do not edit its content).
4. `data/primarii_status_sample.csv` — create — output of the 40-site sample run.
Touch NOTHING else.

**Requirements for `tools/check_primarii.py`:**
- Stdlib only (`urllib.request`, `ssl`, `socket`, `csv`, `re`, `html.parser` or regex, `concurrent.futures.ThreadPoolExecutor`, `argparse`). No new pip dependencies.
- CLI: `python tools/check_primarii.py --sample 40` (first N data rows) and `--all`; `--workers` (default 30), `--timeout` per request (default 15s), `--out <path>` (default `data/primarii_status.csv`; use `data/primarii_status_sample.csv` for the sample run).
- Per site, tolerate every failure (DNS, TLS, timeout, bad HTML) — a broken site is a RESULT ROW, never a crash. Send a desktop-browser User-Agent (some gov sites block Python UAs).
- Output CSV columns, one row per input row:
  `judet, localitate, url, dns_ok, http_status, final_url, https_ok, is_primarie (yes/no/unclear — heuristics: page title/body contains "primăria"/"primaria"/"consiliul local"/"comuna"/"oraș"/locality name), cms (wordpress/joomla/drupal/e-adm/other/unknown — detect from HTML markers), rss_url (from <link type="application/rss+xml"> or common paths /feed, /rss, /feed.xml — verified to return 200 and contain <rss or <feed), rss_ok, last_signal_date (best-effort freshness: newest ISO date found among RSS item dates, sitemap.xml lastmod, or YYYY dates in HTML; empty if none), copyright_year, error (short reason when dead)`.
- Print an end-of-run summary to stdout: total, alive, dead, real primărie count, sites with working RSS, sites with last_signal_date in 2025–2026.
- Follow redirects (record `final_url`); try https first, fall back to http.

**Verification:** run `python tools/check_primarii.py --sample 40 --out data/primarii_status_sample.csv` —
expected: exit 0, `data/primarii_status_sample.csv` has exactly 41 lines (header + 40 rows), the
summary block prints, and at least one sampled site shows `rss_ok=yes` OR the summary plausibly
explains why none do. Do NOT run `--all`.

**Branch:** `devin/check-primarii` from fresh `main`. Commit on green, then STOP.
Do not push, do not merge, do not open a PR.

**Permission fallback (headless mode):** your session may only allow FILE EDITS, not shell
commands. If a git or python command gets blocked, do NOT stop and do NOT report failure:
write `tools/check_primarii.py` completely anyway (this is the deliverable), then report what
you could not run. The manager will run the sample verification, create the branch and commit.
Never work around a blocked command by other means.
