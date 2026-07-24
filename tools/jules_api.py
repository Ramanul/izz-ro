"""Headless driver for the official Jules API (jules.googleapis.com/v1alpha).

ALTERNATIVE route. The primary route is the official `jules` CLI, verified
working 2026-07-24 (the 401 diagnosed on 2026-07-19 was NOT a CLI bug: the
GitHub App was not yet connected to the repo). Use this script instead of the
CLI when you need structured JSON, watch with plan auto-approve, or
AUTO_CREATE_PR.

Auth: set the JULES_API_KEY environment variable yourself (create the key at
https://jules.google.com/settings#api). This script never prints the key.
Known state 2026-07-24: the key currently in env returns 401
ACCESS_TOKEN_TYPE_UNSUPPORTED — regenerate it before relying on this route.

Usage (from repo root):
  python tools/jules_api.py sources
  python tools/jules_api.py new --repo Ramanul/izz-ro --branch main "task prompt"
  python tools/jules_api.py list
  python tools/jules_api.py get <session-id>
  python tools/jules_api.py activities <session-id>
  python tools/jules_api.py send <session-id> "follow-up message"
  python tools/jules_api.py approve <session-id>
  python tools/jules_api.py watch <session-id> [--timeout 1800]

Free plan: 15 tasks/day, 3 concurrent. Session states: QUEUED, PLANNING,
AWAITING_PLAN_APPROVAL, IN_PROGRESS, PAUSED, COMPLETED, FAILED.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://jules.googleapis.com/v1alpha"

if hasattr(sys.stdout, "reconfigure"):  # cp1252 console guard (Windows)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def api(method: str, path: str, body: dict | None = None) -> dict:
    key = os.environ.get("JULES_API_KEY")
    if not key:
        sys.exit("JULES_API_KEY is not set. Create a key at "
                 "https://jules.google.com/settings#api and set the env var "
                 "in YOUR terminal (setx JULES_API_KEY \"...\").")
    req = urllib.request.Request(
        f"{BASE}/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"API {method} {path} -> HTTP {e.code}\n{detail[:800]}")


def cmd_sources(_args):
    data = api("GET", "sources")
    for s in data.get("sources", []):
        print(s.get("name", "?"))
    if not data.get("sources"):
        print("(no sources — connect the GitHub repo in the Jules web app first)")


def cmd_new(args):
    body = {
        "prompt": args.prompt,
        "sourceContext": {
            "source": f"sources/github/{args.repo}",
            "githubRepoContext": {"startingBranch": args.branch},
        },
        "requirePlanApproval": False,
        "automationMode": "AUTO_CREATE_PR",
    }
    if args.title:
        body["title"] = args.title
    s = api("POST", "sessions", body)
    print(json.dumps({k: s.get(k) for k in ("name", "id", "state", "url")},
                     ensure_ascii=False, indent=2))


def cmd_list(_args):
    data = api("GET", "sessions?pageSize=20")
    for s in data.get("sessions", []):
        print(f"{s.get('name','?'):<28} {s.get('state','?'):<22} {s.get('title','')[:50]}")


def _session_path(sid: str) -> str:
    return sid if sid.startswith("sessions/") else f"sessions/{sid}"


def cmd_get(args):
    print(json.dumps(api("GET", _session_path(args.session)), ensure_ascii=False, indent=2))


def cmd_activities(args):
    data = api("GET", f"{_session_path(args.session)}/activities?pageSize=50")
    for a in data.get("activities", []):
        desc = a.get("description") or json.dumps(
            {k: v for k, v in a.items() if k not in ("name", "createTime")},
            ensure_ascii=False)[:300]
        print(f"[{a.get('createTime','?')}] {desc[:400]}")


def cmd_send(args):
    api("POST", f"{_session_path(args.session)}:sendMessage", {"prompt": args.message})
    print("sent")


def cmd_approve(args):
    api("POST", f"{_session_path(args.session)}:approvePlan", {})
    print("approved")


def cmd_watch(args):
    deadline = time.time() + args.timeout
    last_state = None
    while time.time() < deadline:
        s = api("GET", _session_path(args.session))
        state = s.get("state")
        if state != last_state:
            print(f"state: {state}", flush=True)
            last_state = state
        if state == "AWAITING_PLAN_APPROVAL":
            api("POST", f"{_session_path(args.session)}:approvePlan", {})
            print("plan auto-approved", flush=True)
        if state in ("COMPLETED", "FAILED"):
            print(json.dumps(s.get("outputs", []), ensure_ascii=False, indent=2))
            sys.exit(0 if state == "COMPLETED" else 1)
        time.sleep(30)
    sys.exit(f"timeout after {args.timeout}s (state={last_state})")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sources").set_defaults(fn=cmd_sources)
    n = sub.add_parser("new")
    n.add_argument("--repo", required=True)
    n.add_argument("--branch", default="main")
    n.add_argument("--title")
    n.add_argument("prompt")
    n.set_defaults(fn=cmd_new)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    for name, fn in (("get", cmd_get), ("activities", cmd_activities), ("approve", cmd_approve)):
        sp = sub.add_parser(name)
        sp.add_argument("session")
        sp.set_defaults(fn=fn)
    snd = sub.add_parser("send")
    snd.add_argument("session")
    snd.add_argument("message")
    snd.set_defaults(fn=cmd_send)
    w = sub.add_parser("watch")
    w.add_argument("session")
    w.add_argument("--timeout", type=int, default=1800)
    w.set_defaults(fn=cmd_watch)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
