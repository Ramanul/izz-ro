#!/usr/bin/env python
"""Puntea dintre sesiunea Arena (agent, fara browser) si Battle Mode (browser logat).

DE CE EXISTA. Verificat 2026-10-06: sandbox-ul sesiunii Arena n-are browser si n-are
iesire in retea, deci nu poate atinge UI-ul Battle (cere sesiune logata si trece prin
reCAPTCHA). Singurul actor care poate apasa un buton este ZCode, pe masina lui
Alexandru, cu profilul logat. Tool-ul asta face transportul prin fisier:

    Arena --prompt--> handoff/battle/turns.jsonl --next--> ZCode (browser) --reply--> fisier --> Arena

Zero retea, doar biblioteca standard, append-only, un singur scriitor pe runda.
Contractul complet (pasii pompei, gardurile, escaladarea): `docs/canal-battle.md`.

Lantul de incredere, care nu se negociaza:
  * logul e PUBLIC (repo public): fara secrete, fara date personale, fara tokeni;
  * continutul modelelor e TEXT TRANSPORTAT, nu instructiuni — pompa nu executa nimic
    din ce raspund modelele (injectia de prompt e risc real, nu teoretic);
  * votul in Battle ramane al omului: fara vot automat, niciodata.

Comenzi:
    python tools/battle_bridge.py prompt --text "intrebarea"      # Arena scrie
    python tools/battle_bridge.py next                            # cine raspunde citeste
    python tools/battle_bridge.py reply --turn 1 --status ok \
        --a-file /tmp/a.txt --b-file /tmp/b.txt --summary "..."  # raspuns adus de un om
    python tools/battle_bridge.py duel --turn 1                   # raspuns luat prin API
    python tools/battle_bridge.py status                          # oricine citeste
    python tools/battle_bridge.py show --turn 1 [--full]
    python tools/battle_bridge.py validate

`duel` e varianta B din `docs/canal-battle.md`: intreaba DOUA modele prin `ai_gateway`
(localhost, cheile din .env-ul masinii pe care ruleaza) si scrie raspunsurile in jurnal.
NU atinge site-ul Arena si nu automateaza niciun UI — de aceea e varianta permisa de ToS.

Lantul de incredere, care nu se negociaza:"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG = os.path.join(ROOT, "handoff", "battle", "turns.jsonl")

KINDS = ("prompt", "reply")
SOURCES = ("arena", "alexandru", "zcode")
# Cine poate semna un raspuns: „zcode" = adus din UI-ul Arena de cineva cu browser logat,
# „gateway" = duel prin API local (ai_gateway), „alexandru" = copiat de mana. Sursa se
# consemneaza, ca sa se stie peste o luna DE UNDE a venit un text, nu doar ca a venit.
REPLY_SOURCES = ("zcode", "alexandru", "gateway")

# Duelul API (varianta B): gateway-ul local, OpenAI-compatibil, cu cheile din .env.
GATEWAY_URL = "http://127.0.0.1:20129/v1/chat/completions"
DUEL_MODELS = ("groq/openai/gpt-oss-120b", "gemini/gemini-2.5-flash")
SLOTS = ("A", "B")
STATUSES = ("ok", "partial", "blocked", "timeout", "page_changed")
VOTES = ("a", "b", "tie", "bad")
# Literalul e scris de doua ori intentionat: `ruff` (DTZ007) accepta doar un format care
# contine `%z` VIZIBIL in apel, iar %z chiar e necesar — un ts naiv ar face ordinea turelor
# sa depinda de fusul masinii care citeste.
TS_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# Peste MAX_INLINE, textul verbatim iese in `captures/` si in linia JSONL ramane doar
# inceputul + referinta. Motivul e economic: JSONL-ul e citit de agenti, iar un raspuns
# de 30k caractere pe o singura linie otrăvește contextul fiecarei citiri.
MAX_INLINE = 8000
INLINE_KEEP = 2000
MAX_SUMMARY = 900


class BridgeError(Exception):
    """Eroare de contract: fisier stricat, record invalid, comanda imposibila."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_records(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BridgeError(f"{path}:{number}: linie care nu e JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise BridgeError(f"{path}:{number}: linia nu e un obiect JSON")
            records.append(record)
    return records


def append_record(path: str, record: dict) -> None:
    """Append atomic: o singura scriere cu O_APPEND, apoi fsync."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n"
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(handle, line.encode("utf-8"))
        os.fsync(handle)
    finally:
        os.close(handle)


def validate(records: list[dict]) -> list[str]:
    """Invariantele canalului. Intoarce lista de erori (goala = contract respectat)."""
    errors: list[str] = []
    prompts: dict[int, dict] = {}
    replies: dict[int, list[dict]] = {}
    expected_turn = 1

    for index, record in enumerate(records, start=1):
        where = f"linia {index}"
        kind = record.get("kind")
        if kind not in KINDS:
            errors.append(f"{where}: kind necunoscut: {kind!r}")
            continue
        ts = record.get("ts", "")
        try:
            datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
        except (TypeError, ValueError):
            errors.append(f"{where}: ts nu e UTC in formatul {TS_FORMAT}: {ts!r}")
        turn = record.get("turn")
        if not isinstance(turn, int) or turn < 1:
            errors.append(f"{where}: turn trebuie sa fie intreg >= 1, e {turn!r}")
            continue

        if kind == "prompt":
            if turn != expected_turn:
                errors.append(f"{where}: prompt cu turn {turn}, asteptat {expected_turn}")
            expected_turn = max(expected_turn, turn + 1)
            if turn in prompts:
                errors.append(f"{where}: al doilea prompt pentru tura {turn}")
            if record.get("from") not in SOURCES:
                errors.append(f"{where}: from invalid: {record.get('from')!r}")
            if not str(record.get("text", "")).strip():
                errors.append(f"{where}: prompt fara text")
            prompts[turn] = record
            continue

        if turn not in prompts:
            errors.append(f"{where}: reply pentru tura {turn} fara prompt inainte")
        if record.get("status") not in STATUSES:
            errors.append(f"{where}: status invalid: {record.get('status')!r}")
        summary = record.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            errors.append(f"{where}: reply fara summary (obligatoriu pentru citire ieftina)")
        elif len(summary) > MAX_SUMMARY:
            errors.append(f"{where}: summary peste {MAX_SUMMARY} caractere ({len(summary)})")
        if record.get("from") not in REPLY_SOURCES:
            errors.append(
                f"{where}: reply scris de {record.get('from')!r}, "
                f"acceptat: {', '.join(REPLY_SOURCES)}"
            )
        models = record.get("models", [])
        if not isinstance(models, list) or len(models) > 2:
            errors.append(f"{where}: models trebuie sa fie lista de maximum 2")
            models = []
        seen_slots = set()
        for model in models:
            if not isinstance(model, dict):
                errors.append(f"{where}: element din models care nu e obiect")
                continue
            slot = model.get("slot")
            if slot not in SLOTS:
                errors.append(f"{where}: slot invalid: {slot!r}")
            elif slot in seen_slots:
                errors.append(f"{where}: slot {slot} de doua ori in aceeasi tura")
            seen_slots.add(slot)
            if not str(model.get("text", "")).strip() and not model.get("text_ref"):
                errors.append(f"{where}: slot {slot} fara text si fara text_ref")
        if record.get("vote") is not None:
            if record.get("vote") not in VOTES:
                errors.append(f"{where}: vote invalid: {record.get('vote')!r}")
            if record.get("vote_approved_by") != "alexandru":
                errors.append(
                    f"{where}: vot fara aprobarea numita a lui Alexandru "
                    f"(vote_approved_by={record.get('vote_approved_by')!r})"
                )
        if record.get("status") == "ok" and len(models) < 2:
            errors.append(f"{where}: status ok cu {len(models)} raspunsuri, astept 2")
        correction = record.get("correction_of")
        if correction is not None and correction != turn:
            errors.append(f"{where}: correction_of={correction!r} diferit de turn={turn}")
        replies.setdefault(turn, []).append(record)

    for turn in prompts:
        if turn not in replies:
            continue
        if len(replies[turn]) > 1 and not all(
            reply.get("correction_of") == turn for reply in replies[turn][1:]
        ):
            errors.append(f"tura {turn}: doua reply-uri fara correction_of")
    for turn in replies:
        if turn not in prompts:
            errors.append(f"tura {turn}: reply fara prompt (lipseste linia de prompt)")
    return errors


def pending_prompts(records: list[dict]) -> list[dict]:
    answered = {record.get("turn") for record in records if record.get("kind") == "reply"}
    return [
        record
        for record in records
        if record.get("kind") == "prompt" and record.get("turn") not in answered
    ]


def latest_reply(records: list[dict], turn: int) -> dict | None:
    found = None
    for record in records:
        if record.get("kind") == "reply" and record.get("turn") == turn:
            found = record
    return found


def _externalize(text: str, captures_dir: str, turn: int, slot: str) -> tuple[str, str | None]:
    """Text prea lung pentru JSONL: verbatim in `captures/`, inline doar inceputul."""
    if len(text) <= MAX_INLINE:
        return text, None
    os.makedirs(captures_dir, exist_ok=True)
    name = f"tura-{turn:03d}-{slot}.md"
    path = os.path.join(captures_dir, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    marker = f"\n\n[...trunchiat la {INLINE_KEEP} caractere din {len(text)}: textul intreg in text_ref]"
    return text[:INLINE_KEEP] + marker, name


def _read_source(text: str | None, path: str | None, what: str) -> str | None:
    if text and path:
        raise BridgeError(f"{what}: da-mi ori --{what.lower()}-text, ori --{what.lower()}-file, nu amandoua")
    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        except OSError as exc:
            raise BridgeError(f"{what}: nu pot citi {path}: {exc}") from exc
    return text


def build_prompt(text: str, source: str) -> dict:
    if not text.strip():
        raise BridgeError("prompt gol")
    return {"kind": "prompt", "turn": 1, "from": source, "ts": utc_now(), "text": text}


def _make_reply(records: list[dict], turn: int, status: str, models: list[dict], summary: str,
                source: str = "zcode", notes: str | None = None, screen: str | None = None,
                vote: str = "none", approved_by: str | None = None,
                correction: bool = False) -> dict:
    """Recordul de reply, cu toate gardurile intr-un singur loc (reply din fisiere si duel)."""
    if not any(r.get("kind") == "prompt" and r.get("turn") == turn for r in records):
        raise BridgeError(f"tura {turn}: nu exista prompt cu acest turn")
    if latest_reply(records, turn) and not correction:
        raise BridgeError(f"tura {turn}: are deja reply — pentru indreptare foloseste --correction")
    if vote != "none" and approved_by != "alexandru":
        raise BridgeError(
            "votul in Battle e al omului (docs/canal-battle.md). Un vot se inregistreaza doar "
            "daca l-a exprimat Alexandru: --vote <valoare> --approved-by alexandru"
        )
    if status == "ok" and len(models) < 2:
        raise BridgeError("status ok cere ambele raspunsuri")
    if status in ("blocked", "timeout", "page_changed") and models:
        raise BridgeError(f"status {status}: nu trimite text de model, doar notes")
    if source not in REPLY_SOURCES:
        raise BridgeError(f"sursa {source!r} nu e acceptata pentru un reply")
    if not summary.strip():
        raise BridgeError("reply fara summary")

    record = {
        "kind": "reply",
        "turn": turn,
        "from": source,
        "ts": utc_now(),
        "status": status,
        "models": models,
        "summary": summary.strip(),
        "vote": None if vote == "none" else vote,
        "vote_approved_by": None if vote == "none" else approved_by,
        "screen_path": screen,
        "notes": notes,
    }
    if correction:
        record["correction_of"] = turn
    return record


def build_reply(args, records: list[dict], log_path: str) -> dict:
    captures_dir = os.path.join(os.path.dirname(os.path.abspath(log_path)), "captures")
    models = []
    for slot, text_arg, file_arg in (("A", args.a_text, args.a_file), ("B", args.b_text, args.b_file)):
        raw = _read_source(text_arg, file_arg, slot)
        if raw is None:
            continue
        inline, text_ref = _externalize(raw.strip(), captures_dir, args.turn, slot)
        models.append({"slot": slot, "name": args.a_name if slot == "A" else args.b_name,
                       "text": inline, "text_ref": text_ref})
    return _make_reply(records, args.turn, args.status, models, args.summary,
                       source="zcode", notes=args.notes, screen=args.screen, vote=args.vote,
                       approved_by=args.approved_by, correction=args.correction)


# ---- duelul prin API (varianta B: fara Arena, fara UI) -------------------------------

def ask_gateway(endpoint: str, model: str, question: str, timeout: int = 120,
                token: str | None = None) -> str:
    """O intrebare, un model, prin gateway-ul local (OpenAI-compatibil). Fara secrete aici:
    cheile providerilor stau in .env-ul masinii care ruleaza gateway-ul, nu in cod."""
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": question}]})
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(endpoint, data=body.encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise BridgeError(f"{model}: HTTP {exc.code} de la gateway: {detail}") from exc
    except urllib.error.URLError as exc:
        raise BridgeError(
            f"{model}: gateway-ul nu raspunde la {endpoint} ({exc.reason}). "
            "Porneste-l intai: python -m ai_gateway serve"
        ) from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise BridgeError(f"{model}: raspuns care nu e JSON: {exc}") from exc
    try:
        choices = payload["choices"]
        content = choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise BridgeError(f"{model}: raspuns fara choices[0].message.content ({exc})") from exc
    if not isinstance(content, str) or not content.strip():
        raise BridgeError(f"{model}: continut gol")
    return content


def cmd_duel(args) -> int:
    records = read_records(args.log)
    prompt = next(
        (r for r in records if r.get("kind") == "prompt" and r.get("turn") == args.turn), None
    )
    if prompt is None:
        raise BridgeError(f"tura {args.turn}: nu exista prompt cu acest turn")

    captures_dir = os.path.join(os.path.dirname(os.path.abspath(args.log)), "captures")
    models, errors = [], []
    for slot, model in (("A", args.a), ("B", args.b)):
        try:
            text = ask_gateway(args.gateway, model, prompt["text"], args.timeout, args.token)
        except BridgeError as exc:
            errors.append(str(exc))
            print(f"slot {slot} ({model}): {exc}", file=sys.stderr)
            continue
        inline, text_ref = _externalize(text.strip(), captures_dir, args.turn, slot)
        models.append({"slot": slot, "name": model, "text": inline, "text_ref": text_ref})

    if len(models) == 2:
        status = "ok"
    elif len(models) == 1:
        status = "partial"
    else:
        status = "blocked"
    summary = args.summary or (
        f"duel API ({args.a} vs {args.b}): "
        + (", ".join(f"{m['slot']}={len(m['text'])} caractere" for m in models) or "niciun raspuns")
        + ("; erori: " + " | ".join(errors) if errors else "")
        + " — textul verbatim in model.text/text_ref, nu in summary"
    )
    record = _make_reply(records, args.turn, status, models, summary, source="gateway",
                         notes=args.notes or ("; ".join(errors) or None), screen=args.screen,
                         correction=args.correction)
    _write_checked(args.log, records, record)
    print(f"tura {args.turn}: duel incheiat cu status {status} ({len(models)}/2 raspunsuri)")
    return 0


def _write_checked(path: str, records: list[dict], record: dict) -> None:
    candidate = records + [record]
    errors = validate(candidate)
    if errors:
        raise BridgeError("record respins de contract:\n  " + "\n  ".join(errors))
    append_record(path, record)


def cmd_prompt(args) -> int:
    records = read_records(args.log)
    record = build_prompt(args.text, args.source)
    record["turn"] = len([r for r in records if r.get("kind") == "prompt"]) + 1
    _write_checked(args.log, records, record)
    print(f"tura {record['turn']} scrisa in {args.log}")
    return 0


def cmd_reply(args) -> int:
    records = read_records(args.log)
    record = build_reply(args, records, args.log)
    _write_checked(args.log, records, record)
    verb = "corectata" if args.correction else "scrisa"
    print(f"tura {record['turn']} {verb} (status {args.status}) in {args.log}")
    return 0


def cmd_next(args) -> int:
    records = read_records(args.log)
    pending = pending_prompts(records)
    if not pending:
        print("NOTHING")
        return 0
    print(json.dumps(pending[0], ensure_ascii=False, indent=2))
    return 0


def cmd_status(args) -> int:
    records = read_records(args.log)
    prompts = [r for r in records if r.get("kind") == "prompt"]
    if not prompts:
        print(f"canal gol ({args.log})")
        return 0
    for prompt in prompts:
        turn = prompt["turn"]
        reply = latest_reply(records, turn)
        first = " ".join(str(prompt.get("text", "")).split())[:70]
        if reply is None:
            print(f"t{turn:>3}  [asteapta]  {first}")
            continue
        names = ", ".join(
            f"{m.get('slot')}={m.get('name') or '?'}" for m in reply.get("models", [])
        ) or "-"
        print(f"t{turn:>3}  [{reply.get('status')}]  {names}  vot={reply.get('vote')}  {first}")
    return 0


def cmd_show(args) -> int:
    records = read_records(args.log)
    prompt = next((r for r in records if r.get("kind") == "prompt" and r.get("turn") == args.turn), None)
    if prompt is None:
        raise BridgeError(f"tura {args.turn}: nu exista")
    print(f"--- prompt tura {args.turn} ({prompt.get('from')}, {prompt.get('ts')})")
    print(prompt.get("text", ""))
    reply = latest_reply(records, args.turn)
    if reply is None:
        print(f"--- tura {args.turn}: fara reply inca")
        return 0
    print(f"--- reply ({reply.get('status')}, {reply.get('ts')}, vot={reply.get('vote')})")
    print(f"summary: {reply.get('summary')}")
    for model in reply.get("models", []):
        head = f"slot {model.get('slot')}"
        if model.get("name"):
            head += f" = {model['name']}"
        if model.get("text_ref"):
            head += f" [text intreg: {model['text_ref']}]"
        print(f"\n### {head}")
        print(model.get("text", "") if args.full else "(foloseste --full pentru textul verbatim)")
    if reply.get("notes"):
        print(f"notes: {reply['notes']}")
    return 0


def cmd_validate(args) -> int:
    records = read_records(args.log)
    errors = validate(records)
    if errors:
        print(f"INVALID ({len(errors)} erori):")
        for error in errors:
            print(f"  - {error}")
        return 2
    print(f"OK: {len(records)} linii, contract respectat")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", default=DEFAULT_LOG, help=f"jurnalul JSONL (implicit {DEFAULT_LOG})")
    sub = parser.add_subparsers(dest="command", required=True)

    prompt = sub.add_parser("prompt", help="Arena scrie o intrebare pentru Battle")
    prompt.add_argument("--text", required=True)
    prompt.add_argument("--from", dest="source", default="arena", choices=SOURCES)
    prompt.set_defaults(func=cmd_prompt)

    reply = sub.add_parser("reply", help="pompa scrie raspunsul Battle")
    reply.add_argument("--turn", type=int, required=True)
    reply.add_argument("--status", required=True, choices=STATUSES)
    reply.add_argument("--summary", required=True)
    reply.add_argument("--a-text")
    reply.add_argument("--a-file")
    reply.add_argument("--b-text")
    reply.add_argument("--b-file")
    reply.add_argument("--a-name")
    reply.add_argument("--b-name")
    reply.add_argument("--screen")
    reply.add_argument("--notes")
    reply.add_argument("--correction", action="store_true",
                       help="al doilea raspuns pentru aceeasi tura (corectie), nu unul nou")
    reply.add_argument("--vote", default="none", choices=(*VOTES, "none"),
                       help="votul exprimat de Alexandru (cere si --approved-by alexandru)")
    reply.add_argument("--approved-by", default=None,
                       help="cine a exprimat votul; singura valoare acceptata: alexandru")
    reply.set_defaults(func=cmd_reply)

    duel = sub.add_parser("duel", help="doua modele prin ai_gateway local, fara Arena (varianta B)")
    duel.add_argument("--turn", type=int, required=True)
    duel.add_argument("--a", default=DUEL_MODELS[0], help="modelul pentru slotul A (provider/model)")
    duel.add_argument("--b", default=DUEL_MODELS[1], help="modelul pentru slotul B (provider/model)")
    duel.add_argument("--gateway", default=GATEWAY_URL, help="endpoint-ul local, OpenAI-compatibil")
    duel.add_argument("--timeout", type=int, default=120, help="secunde per model")
    duel.add_argument("--token", default=None,
                      help="Bearer pentru gateway, doar daca GATEWAY_API_KEY e setata in .env")
    duel.add_argument("--summary", help="daca lipseste, se scrie unul mecanic (dimensiuni + erori)")
    duel.add_argument("--notes")
    duel.add_argument("--screen")
    duel.add_argument("--correction", action="store_true")
    duel.set_defaults(func=cmd_duel)

    sub.add_parser("next", help="urmatorul prompt fara reply (pentru pompa)").set_defaults(func=cmd_next)
    sub.add_parser("status", help="tabelul canalului").set_defaults(func=cmd_status)

    show = sub.add_parser("show", help="o tura anume")
    show.add_argument("--turn", type=int, required=True)
    show.add_argument("--full", action="store_true", help="include textul verbatim al modelelor")
    show.set_defaults(func=cmd_show)

    sub.add_parser("validate", help="verifica invariantii pe tot jurnalul").set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BridgeError as exc:
        print(f"EROARE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
