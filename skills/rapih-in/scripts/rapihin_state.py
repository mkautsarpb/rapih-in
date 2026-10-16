#!/usr/bin/env python3
"""rapih-in state helper: writer lock, run checkpoints, snapshots, guarded restore.

Standard library only (Python 3.8+). Every command prints one JSON object to stdout.

Exit codes:
  0 ok
  2 usage or validation error
  3 lock busy / not owner / recovery refused
  4 conflict (file content differs from what was expected)
  5 not found (run, batch, snapshot)

State directory: --state-dir, else $RAPIH_IN_STATE_DIR, else ~/.rapih-in
  locks/<repo-key>/owner.json          lock is held while this directory exists
  runs/<repo-key>/<run-id>/checkpoint.json
  runs/<repo-key>/<run-id>/journal.jsonl
  runs/<repo-key>/<run-id>/snapshots/<batch>/{pre,post}/<n>.bin

Read-only commands (repo-key, new-id, hash, fingerprint, lock status, lock verify,
run list, run show, diagnose, restore --dry-run) never create or modify state.
"""

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time

VERSION = "1.0.0"

EXIT_OK, EXIT_USAGE, EXIT_BUSY, EXIT_CONFLICT, EXIT_NOT_FOUND = 0, 2, 3, 4, 5

RUN_STATUSES = {"planned", "in_progress", "applied_unverified", "validated", "blocked",
                "failed", "interrupted", "completed"}
BATCH_MARKS = {"validated", "applied_unverified", "failed", "blocked", "restored"}
OPS = {"create", "modify", "move", "delete"}
SENSITIVE = [".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*",
             "*.keystore", ".npmrc", ".pypirc", "credentials*.json", "*.log"]
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


class Fail(Exception):
    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code = code
        self.payload = {"status": "error", "error": message}
        self.payload.update(extra)


# ---------------------------------------------------------------- utilities

def now_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def file_hash(path):
    """sha256 of a regular file, None if missing, 'dir' if a directory."""
    if os.path.isdir(path):
        return "dir"
    if not os.path.lexists(path):
        return None
    return sha256_file(path)


def atomic_write(path, data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, ".tmp-%s-%s" % (os.getpid(), secrets.token_hex(4)))
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: target briefly open by a reader
            time.sleep(0.05 * (attempt + 1))
    os.replace(tmp, path)


def write_json(path, obj):
    atomic_write(path, json.dumps(obj, indent=2, sort_keys=True))


def read_json(path, retries=10):
    for attempt in range(retries):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def append_journal(run_dir, event, **fields):
    entry = dict(ts=now_iso(), event=event, **fields)
    with open(os.path.join(run_dir, "journal.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def state_dir(args):
    d = args.state_dir or os.environ.get("RAPIH_IN_STATE_DIR") or os.path.join(
        os.path.expanduser("~"), ".rapih-in")
    return os.path.abspath(d)


def check_id(value, what):
    if not ID_RE.match(value or ""):
        raise Fail(EXIT_USAGE, "invalid %s %r (use letters, digits, . _ -)" % (what, value))
    return value


def rename_retry(src, dst):
    """os.rename that retries transient Windows sharing violations, never an existing target."""
    for attempt in range(20):
        try:
            os.rename(src, dst)
            return
        except FileExistsError:
            raise
        except PermissionError:
            if os.name != "nt" or attempt == 19:
                raise
            time.sleep(0.05 * (attempt + 1))


def pid_alive(pid):
    if not pid:
        return None
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if os.name == "nt":
        try:
            out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH", "/FO", "CSV"],
                                 capture_output=True, text=True, timeout=10).stdout
            return ('"%d"' % pid) in out
        except Exception:
            return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return None


# ---------------------------------------------------------------- repo identity

def normalize_root(path):
    """Canonical worktree root: git top-level if inside a git worktree, else the path."""
    if not os.path.exists(path):
        raise Fail(EXIT_USAGE, "path does not exist: %s" % path)
    real = os.path.realpath(os.path.abspath(path))
    start = real if os.path.isdir(real) else os.path.dirname(real)
    git = False
    try:
        out = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=15)
        if out.returncode == 0 and out.stdout.strip():
            real = os.path.realpath(out.stdout.strip())
            git = True
    except (OSError, subprocess.SubprocessError):
        pass
    if not git and not os.path.isdir(real):
        real = os.path.dirname(real)
    norm = os.path.normcase(os.path.normpath(real))
    return real, norm, git


def repo_identity(path):
    real, norm, git = normalize_root(path)
    key = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
    return {"root": real, "key": key, "git": git}


def rel_inside(root, p):
    """Return normalized relative path of p inside root, or raise."""
    full = os.path.realpath(os.path.join(root, p))
    root_real = os.path.realpath(root)
    rel = os.path.relpath(full, root_real)
    if rel == os.curdir or rel.startswith(os.pardir + os.sep) or rel == os.pardir or os.path.isabs(rel):
        raise Fail(EXIT_USAGE, "path escapes the worktree root: %s" % p)
    rel = rel.replace(os.sep, "/")
    name = rel.rsplit("/", 1)[-1]
    for pat in SENSITIVE:
        if fnmatch.fnmatch(name.lower(), pat):
            raise Fail(EXIT_USAGE, "refusing to snapshot a sensitive file: %s" % rel)
    return rel


# ---------------------------------------------------------------- lock

def lock_path(sd, key):
    return os.path.join(sd, "locks", key)


def read_owner(lp):
    try:
        return read_json(os.path.join(lp, "owner.json"))
    except FileNotFoundError:
        return None
    except (ValueError, OSError):
        return {"corrupt": True}


def lock_status_obj(sd, ident):
    lp = lock_path(sd, ident["key"])
    if not os.path.isdir(lp):
        return {"status": "free", "root": ident["root"], "key": ident["key"], "lock_dir": lp}
    owner = read_owner(lp) or {}
    same_host = owner.get("host") == socket.gethostname()
    alive = pid_alive(owner.get("invoker_pid")) if same_host else None
    return {"status": "held", "root": ident["root"], "key": ident["key"], "lock_dir": lp,
            "owner": {k: v for k, v in owner.items() if k != "token"},
            "owner_token_prefix": (owner.get("token") or "")[:8],
            "diagnosis": {"same_host": same_host, "invoker_pid_alive": alive,
                          "note": ("age and pid are diagnostics only and never release a lock; the invoker pid "
                                   "is the short-lived shell that ran the helper, so a dead pid does not "
                                   "prove the owning agent session has ended")}}


def acquire(sd, ident, run_id, session):
    locks = os.path.join(sd, "locks")
    os.makedirs(locks, exist_ok=True)
    lp = lock_path(sd, ident["key"])
    token = secrets.token_hex(16)
    owner = {"token": token, "run_id": run_id, "root": ident["root"], "key": ident["key"],
             "host": socket.gethostname(), "pid": os.getpid(), "invoker_pid": os.getppid(),
             "session": session or os.environ.get("RAPIH_IN_SESSION", ""),
             "acquired_at": now_iso(), "helper_version": VERSION}
    staging = os.path.join(locks, ".staging-%s" % token)
    os.makedirs(staging)
    write_json(os.path.join(staging, "owner.json"), owner)
    try:
        # Atomic: fails when the lock directory already exists (it is never empty).
        rename_retry(staging, lp)
    except OSError:
        shutil.rmtree(staging, ignore_errors=True)
        st = lock_status_obj(sd, ident)
        st["status"] = "busy"
        raise Fail(EXIT_BUSY, "worktree lock is held by another run", **st)
    owner_now = read_owner(lp) or {}
    if owner_now.get("token") != token:  # defensive: POSIX rename over an empty dir
        raise Fail(EXIT_BUSY, "lock acquisition raced; not acquired", lock_dir=lp)
    return {"status": "acquired", "token": token, "run_id": run_id, "root": ident["root"],
            "key": ident["key"], "lock_dir": lp}


def require_owner(sd, ident, token):
    lp = lock_path(sd, ident["key"])
    owner = read_owner(lp) if os.path.isdir(lp) else None
    if not owner or owner.get("token") != token:
        raise Fail(EXIT_BUSY, "caller does not own the worktree lock; no write allowed",
                   lock=lock_status_obj(sd, ident))
    return owner


def release(sd, ident, token):
    require_owner(sd, ident, token)
    lp = lock_path(sd, ident["key"])
    grave = os.path.join(sd, "locks", ".released-%s-%s" % (token[:8], secrets.token_hex(4)))
    rename_retry(lp, grave)
    moved = read_owner(grave) or {}
    if moved.get("token") != token:  # should be impossible; put it back
        rename_retry(grave, lp)
        raise Fail(EXIT_BUSY, "lock changed owner during release; left in place")
    shutil.rmtree(grave, ignore_errors=True)
    return {"status": "released", "key": ident["key"]}


def recover(sd, ident, expected_token_prefix, run_id, confirmed, session):
    st = lock_status_obj(sd, ident)
    if st["status"] == "free":
        return acquire(sd, ident, run_id, session)
    lp = lock_path(sd, ident["key"])
    owner = read_owner(lp) or {}
    tok = owner.get("token") or ""
    if not expected_token_prefix or not tok.startswith(expected_token_prefix):
        raise Fail(EXIT_BUSY, "expected owner token does not match the current lock owner", lock=st)
    if not confirmed:
        raise Fail(EXIT_BUSY, "recovery refused: owner inactivity not confirmed by the user. Show the owner "
                   "run and its journal, ask the user to confirm that session has ended, then retry with "
                   "--user-confirmed-owner-inactive", lock=st)
    if st["diagnosis"].get("invoker_pid_alive"):
        raise Fail(EXIT_BUSY, "recovery refused: recorded owner process is still running on this host",
                   lock=st)
    journal = None
    if owner.get("run_id"):
        rd = os.path.join(sd, "runs", ident["key"], owner["run_id"])
        if os.path.isdir(rd):
            journal = summarize_run(rd)
    grave = os.path.join(sd, "locks", ".recovered-%s-%s" % (tok[:8], secrets.token_hex(4)))
    try:
        rename_retry(lp, grave)
    except OSError:
        raise Fail(EXIT_BUSY, "lock changed during recovery; retry status first")
    moved = read_owner(grave) or {}
    if moved.get("token") != tok:
        try:
            rename_retry(grave, lp)
        finally:
            raise Fail(EXIT_BUSY, "lock owner changed during recovery; nothing taken over")
    shutil.rmtree(grave, ignore_errors=True)
    if journal and owner.get("run_id"):
        rd = os.path.join(sd, "runs", ident["key"], owner["run_id"])
        append_journal(rd, "lock_recovered", previous_owner_token_prefix=tok[:8], by_run=run_id)
        cp = read_json(os.path.join(rd, "checkpoint.json"))
        if cp.get("status") == "in_progress":
            cp["status"] = "interrupted"
            cp["updated_at"] = now_iso()
            write_json(os.path.join(rd, "checkpoint.json"), cp)
    res = acquire(sd, ident, run_id, session)
    res["recovered_from"] = {"run_id": owner.get("run_id"), "token_prefix": tok[:8],
                             "journal": journal}
    return res


# ---------------------------------------------------------------- runs

def run_dir(sd, ident, run_id):
    return os.path.join(sd, "runs", ident["key"], check_id(run_id, "run id"))


def load_run(sd, ident, run_id):
    rd = run_dir(sd, ident, run_id)
    cpf = os.path.join(rd, "checkpoint.json")
    if not os.path.isfile(cpf):
        raise Fail(EXIT_NOT_FOUND, "no checkpoint for run %s in this worktree" % run_id)
    cp = read_json(cpf)
    if os.path.normcase(cp.get("root", "")) != os.path.normcase(ident["root"]):
        raise Fail(EXIT_CONFLICT, "run belongs to a different root/worktree", run_root=cp.get("root"))
    return rd, cp


def save_run(rd, cp):
    cp["updated_at"] = now_iso()
    write_json(os.path.join(rd, "checkpoint.json"), cp)


def summarize_run(rd):
    try:
        cp = read_json(os.path.join(rd, "checkpoint.json"))
    except (OSError, ValueError):
        return {"error": "checkpoint unreadable", "dir": rd}
    batches = {b: {"status": v.get("status"), "findings": v.get("findings", [])}
               for b, v in cp.get("batches", {}).items()}
    return {"run_id": cp.get("run_id"), "mode": cp.get("mode"), "status": cp.get("status"),
            "scope": cp.get("scope"), "exclusions": cp.get("exclusions"),
            "selected_ids": cp.get("selected_ids"), "audit_id": cp.get("audit_id"),
            "updated_at": cp.get("updated_at"), "next_step": cp.get("next_step"),
            "batches": batches, "dir": rd}


def load_json_arg(value):
    if value is None:
        return None
    if value == "-":
        return json.load(sys.stdin)
    if os.path.isfile(value):
        with open(value, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(value)


def cmd_run_init(sd, ident, a):
    owner = require_owner(sd, ident, a.token)
    run_id = a.run_id or owner.get("run_id")
    if run_id != owner.get("run_id"):
        raise Fail(EXIT_USAGE, "run id must match the lock owner's run id (%s)" % owner.get("run_id"))
    rd = run_dir(sd, ident, run_id)
    if os.path.exists(os.path.join(rd, "checkpoint.json")):
        raise Fail(EXIT_USAGE, "run already exists: %s" % run_id)
    selected = sorted(set(x.strip() for x in (a.only or "").split(",") if x.strip()))
    cp = {"run_id": run_id, "root": ident["root"], "key": ident["key"], "mode": a.mode,
          "skill_version": a.skill_version, "helper_version": VERSION, "scope": a.scope,
          "exclusions": a.exclude or [], "selected_ids": selected, "audit_id": a.audit_id,
          "audit": load_json_arg(a.audit_json), "plan": load_json_arg(a.plan_json),
          "baseline": load_json_arg(a.baseline_json), "status": "planned", "batches": {},
          "next_step": "begin first batch", "created_at": now_iso(),
          "lock_owner_hint": {"token_prefix": a.token[:8]}}
    os.makedirs(rd, exist_ok=True)
    save_run(rd, cp)
    append_journal(rd, "run_init", mode=a.mode, scope=a.scope, selected_ids=selected)
    return {"status": "ok", "run_id": run_id, "checkpoint": os.path.join(rd, "checkpoint.json")}


def cmd_run_update(sd, ident, a):
    require_owner(sd, ident, a.token)
    rd, cp = load_run(sd, ident, a.run_id)
    if a.status:
        if a.status not in RUN_STATUSES:
            raise Fail(EXIT_USAGE, "unknown run status %s" % a.status)
        cp["status"] = a.status
    if a.next_step is not None:
        cp["next_step"] = a.next_step
    extra = load_json_arg(a.set_json)
    if extra:
        protected = {"run_id", "root", "key", "batches", "selected_ids", "scope", "exclusions"}
        bad = protected & set(extra)
        if bad:
            raise Fail(EXIT_USAGE, "these run fields cannot be changed: %s" % ", ".join(sorted(bad)))
        cp.update(extra)
    cp["lock_owner_hint"] = {"token_prefix": a.token[:8]}
    save_run(rd, cp)
    append_journal(rd, "run_update", status=cp["status"], next_step=cp.get("next_step"))
    return {"status": "ok", "run": summarize_run(rd)}


def cmd_run_list(sd, ident, a):
    base = os.path.join(sd, "runs", ident["key"])
    runs = []
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            rd = os.path.join(base, name)
            if os.path.isfile(os.path.join(rd, "checkpoint.json")):
                s = summarize_run(rd)
                if a.all or s.get("status") not in ("completed",):
                    runs.append(s)
    return {"status": "ok", "root": ident["root"], "key": ident["key"], "runs": runs,
            "lock": lock_status_obj(sd, ident)}


def cmd_run_show(sd, ident, a):
    rd, cp = load_run(sd, ident, a.run_id)
    return {"status": "ok", "checkpoint": cp, "dir": rd}


# ---------------------------------------------------------------- batches

def parse_files(root, items, default_op):
    """items: 'path' or 'op:path' or 'move:src=>dst'."""
    files = []
    for raw in items or []:
        op, _, rest = raw.partition(":") if raw.split(":", 1)[0] in OPS else (default_op, "", raw)
        if op == "move":
            src, sep, dst = rest.partition("=>")
            if not sep:
                raise Fail(EXIT_USAGE, "move needs 'move:src=>dst': %s" % raw)
            files.append({"op": "move-src", "path": rel_inside(root, src.strip())})
            files.append({"op": "move-dst", "path": rel_inside(root, dst.strip())})
        else:
            files.append({"op": op, "path": rel_inside(root, rest)})
    seen, out = set(), []
    for f in files:
        if f["path"] not in seen:
            seen.add(f["path"])
            out.append(f)
    return out


def snapshot_files(rd, batch, kind, root, entries):
    snapdir = os.path.join(rd, "snapshots", batch, kind)
    os.makedirs(snapdir, exist_ok=True)
    for e in entries:
        full = os.path.join(root, e["path"])
        h = file_hash(full)
        if h == "dir":
            raise Fail(EXIT_USAGE, "snapshot entries must be files, not directories: %s" % e["path"])
        e[kind + "_hash"] = h
        if h is not None:
            name = hashlib.sha256(e["path"].encode("utf-8")).hexdigest()[:20]
            blob = os.path.join(snapdir, name + ".bin")
            shutil.copyfile(full, blob)
            if sha256_file(blob) != h:
                raise Fail(EXIT_CONFLICT, "file changed while snapshotting: %s" % e["path"])
            e[kind + "_blob"] = os.path.relpath(blob, rd).replace(os.sep, "/")


def cmd_batch_begin(sd, ident, a):
    require_owner(sd, ident, a.token)
    rd, cp = load_run(sd, ident, a.run_id)
    b = check_id(a.batch, "batch id")
    if b in cp["batches"] and cp["batches"][b]["status"] not in ("restored", "failed"):
        raise Fail(EXIT_USAGE, "batch %s already exists with status %s; diagnose it instead of "
                   "re-running" % (b, cp["batches"][b]["status"]))
    entries = parse_files(ident["root"], a.files, "modify")
    if not entries:
        raise Fail(EXIT_USAGE, "batch begin needs --files")
    expected = dict(x.split("=", 1) for x in (a.expect or []))
    for e in entries:
        cur = file_hash(os.path.join(ident["root"], e["path"]))
        want = expected.get(e["path"])
        if want is not None and (cur or "missing") != want:
            raise Fail(EXIT_CONFLICT, "file differs from the planned preimage: %s" % e["path"],
                       path=e["path"], expected=want, current=cur or "missing")
    snapshot_files(rd, b, "pre", ident["root"], entries)
    cp["batches"][b] = {"status": "in_progress", "findings": [x for x in (a.findings or "").split(",") if x],
                        "description": a.description or "", "files": entries,
                        "started_at": now_iso(), "checks": []}
    cp["status"] = "in_progress"
    cp["next_step"] = "apply batch %s, then batch end" % b
    save_run(rd, cp)
    append_journal(rd, "batch_begin", batch=b, files=[e["path"] for e in entries])
    return {"status": "ok", "batch": b, "files": entries}


def cmd_batch_end(sd, ident, a):
    require_owner(sd, ident, a.token)
    rd, cp = load_run(sd, ident, a.run_id)
    bt = cp["batches"].get(a.batch)
    if not bt:
        raise Fail(EXIT_NOT_FOUND, "unknown batch %s" % a.batch)
    snapshot_files(rd, a.batch, "post", ident["root"], bt["files"])
    bt["status"] = "applied_unverified"
    bt["ended_at"] = now_iso()
    cp["status"] = "applied_unverified"
    cp["next_step"] = "run checks for batch %s, then batch mark" % a.batch
    save_run(rd, cp)
    append_journal(rd, "batch_end", batch=a.batch)
    return {"status": "ok", "batch": a.batch,
            "changed": [e["path"] for e in bt["files"] if e.get("pre_hash") != e.get("post_hash")]}


def cmd_batch_mark(sd, ident, a):
    require_owner(sd, ident, a.token)
    rd, cp = load_run(sd, ident, a.run_id)
    bt = cp["batches"].get(a.batch)
    if not bt:
        raise Fail(EXIT_NOT_FOUND, "unknown batch %s" % a.batch)
    if a.status not in BATCH_MARKS:
        raise Fail(EXIT_USAGE, "batch status must be one of %s" % ", ".join(sorted(BATCH_MARKS)))
    if a.status == "validated" and bt["status"] == "in_progress":
        raise Fail(EXIT_USAGE, "cannot validate a batch that was never ended")
    bt["status"] = a.status
    checks = load_json_arg(a.checks_json)
    if checks:
        bt["checks"] = bt.get("checks", []) + (checks if isinstance(checks, list) else [checks])
    if a.note:
        bt["note"] = a.note
    save_run(rd, cp)
    append_journal(rd, "batch_mark", batch=a.batch, mark=a.status, note=a.note)
    return {"status": "ok", "batch": a.batch, "mark": a.status}


def classify(root, e):
    """State of one batch file now, compared with its recorded pre/post hashes.

    pre        content equals the pre-batch snapshot
    post       content equals what this run recorded after writing it
    unchanged  run recorded no change and the file still matches
    modified_outside_run  differs from both pre and recorded post (someone else edited it)
    changed_unrecorded    differs from pre, but the run never recorded a post state
                          (partial write of an interrupted batch, or an external edit)
    """
    cur = file_hash(os.path.join(root, e["path"]))
    pre = e.get("pre_hash")
    has_post = "post_hash" in e
    post = e.get("post_hash")
    if has_post and cur == post:
        state = "unchanged" if post == pre else "post"
    elif cur == pre:
        state = "pre"
    elif has_post:
        state = "modified_outside_run"
    else:
        state = "changed_unrecorded"
    return state, cur


def diagnose_run(sd, ident, rd, cp):
    out = {}
    for b, bt in cp["batches"].items():
        files = []
        for e in bt["files"]:
            state, cur = classify(ident["root"], e)
            files.append({"path": e["path"], "op": e["op"], "state": state,
                          "pre_snapshot": os.path.join(rd, e["pre_blob"]) if e.get("pre_blob") else None})
        states = {f["state"] for f in files}
        if bt["status"] == "in_progress":
            if states <= {"pre"}:
                verdict = "interrupted_before_writes"
            elif "modified_outside_run" in states:
                verdict = "interrupted_with_foreign_edits"
            elif "changed_unrecorded" in states:
                verdict = "interrupted_needs_inspection"
            else:
                verdict = "interrupted_partial"
        elif bt["status"] == "restored" and states <= {"pre", "unchanged"}:
            verdict = "restored"
        elif states <= {"post", "unchanged"}:
            verdict = "as_recorded"
        elif "modified_outside_run" in states or "changed_unrecorded" in states:
            verdict = "changed_after_batch"
        else:
            verdict = "reverted_or_mixed"
        out[b] = {"status": bt["status"], "verdict": verdict, "files": files}
    return out


def cmd_batch_record(sd, ident, a):
    """Record the post-write hash of specific files while a batch is in progress."""
    require_owner(sd, ident, a.token)
    rd, cp = load_run(sd, ident, a.run_id)
    bt = cp["batches"].get(a.batch)
    if not bt:
        raise Fail(EXIT_NOT_FOUND, "unknown batch %s" % a.batch)
    wanted = {rel_inside(ident["root"], p) for p in a.paths}
    entries = [e for e in bt["files"] if e["path"] in wanted]
    missing = wanted - {e["path"] for e in entries}
    if missing:
        raise Fail(EXIT_USAGE, "not part of batch %s: %s" % (a.batch, ", ".join(sorted(missing))))
    snapshot_files(rd, a.batch, "post", ident["root"], entries)
    save_run(rd, cp)
    append_journal(rd, "batch_record", batch=a.batch, files=sorted(wanted))
    return {"status": "ok", "recorded": sorted(wanted)}


def cmd_diagnose(sd, ident, a):
    rd, cp = load_run(sd, ident, a.run_id)
    return {"status": "ok", "run": summarize_run(rd), "batches": diagnose_run(sd, ident, rd, cp),
            "lock": lock_status_obj(sd, ident)}


def cmd_guard(sd, ident, a):
    require_owner(sd, ident, a.token)
    conflicts = []
    for item in a.expect or []:
        p, sep, want = item.partition("=")
        if not sep:
            raise Fail(EXIT_USAGE, "--expect needs path=sha256|missing: %s" % item)
        rel = rel_inside(ident["root"], p)
        cur = file_hash(os.path.join(ident["root"], rel)) or "missing"
        if cur != want:
            conflicts.append({"path": rel, "expected": want, "current": cur})
    if conflicts:
        raise Fail(EXIT_CONFLICT, "external change detected; do not write these files",
                   conflicts=conflicts)
    return {"status": "ok", "checked": len(a.expect or [])}


def cmd_restore(sd, ident, a):
    if not a.dry_run:
        require_owner(sd, ident, a.token)
    rd, cp = load_run(sd, ident, a.run_id)
    bt = cp["batches"].get(a.batch)
    if not bt:
        raise Fail(EXIT_NOT_FOUND, "unknown batch %s" % a.batch)
    accepted = {rel_inside(ident["root"], p) for p in (a.include_unrecorded or [])}
    actions, conflicts = [], []
    for e in bt["files"]:
        state, cur = classify(ident["root"], e)
        if state in ("pre", "unchanged"):
            actions.append({"path": e["path"], "action": "none (already pre-batch)"})
            continue
        if state == "modified_outside_run":
            conflicts.append({"path": e["path"], "reason": "changed after the batch; not overwritten",
                              "current": cur or "missing"})
            continue
        if state == "changed_unrecorded" and e["path"] not in accepted:
            conflicts.append({"path": e["path"], "reason": "changed but the run never recorded its own "
                              "write; diff against the pre snapshot, then pass --include-unrecorded "
                              "only if the change is solely this run's", "current": cur or "missing",
                              "pre_snapshot": os.path.join(rd, e["pre_blob"]) if e.get("pre_blob") else None})
            continue
        if e.get("pre_hash") is None:
            actions.append({"path": e["path"], "action": "delete (created by run, unchanged since)"})
        else:
            blob = os.path.join(rd, e.get("pre_blob", ""))
            if not e.get("pre_blob") or not os.path.isfile(blob) or sha256_file(blob) != e["pre_hash"]:
                conflicts.append({"path": e["path"], "reason": "pre-batch snapshot missing or damaged"})
                continue
            actions.append({"path": e["path"], "action": "restore pre-batch content"})
    result = {"status": "ok" if not conflicts else "conflict", "batch": a.batch,
              "dry_run": bool(a.dry_run), "actions": actions, "conflicts": conflicts}
    if a.dry_run:
        return result
    if conflicts and not a.partial:
        result["applied"] = False
        result["hint"] = ("nothing restored; resolve conflicts or rerun with --partial to restore "
                          "only the separable files")
        raise Fail(EXIT_CONFLICT, "restore has conflicts", **result)
    by_path = {e["path"]: e for e in bt["files"]}
    for act in actions:
        e = by_path[act["path"]]
        full = os.path.join(ident["root"], e["path"])
        state, cur = classify(ident["root"], e)  # recheck right before writing
        if not (state == "post" or (state == "changed_unrecorded" and e["path"] in accepted)):
            continue
        if act["action"].startswith("delete"):
            os.remove(full)
        elif act["action"].startswith("restore"):
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            tmp = full + ".rapih-in-restore"
            shutil.copyfile(os.path.join(rd, e["pre_blob"]), tmp)
            os.replace(tmp, full)
        act["done"] = True
    bt["status"] = "restored" if not conflicts else "failed"
    bt["restore"] = {"at": now_iso(), "conflicts": conflicts}
    save_run(rd, cp)
    append_journal(rd, "batch_restore", batch=a.batch, conflicts=len(conflicts))
    result["applied"] = True
    return result


# ---------------------------------------------------------------- misc

def cmd_fingerprint(a):
    paths = sorted(p.replace("\\", "/").strip("/").lower() for p in a.path or [])
    symbols = sorted(a.symbol or [])
    basis = "\n".join([a.kind.strip().lower()] + paths + ["#" + s for s in symbols])
    return {"status": "ok", "fingerprint": hashlib.sha256(basis.encode("utf-8")).hexdigest()[:12],
            "kind": a.kind, "paths": paths, "symbols": symbols}


def build_parser():
    p = argparse.ArgumentParser(prog="rapihin_state.py", description=__doc__.split("\n")[0])
    p.add_argument("--state-dir")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("repo-key"); s.add_argument("root")
    s = sub.add_parser("new-id"); s.add_argument("kind", choices=["audit", "run"]); s.add_argument("root")
    s = sub.add_parser("hash"); s.add_argument("root"); s.add_argument("paths", nargs="+")
    s = sub.add_parser("fingerprint"); s.add_argument("--kind", required=True)
    s.add_argument("--path", action="append"); s.add_argument("--symbol", action="append")

    lk = sub.add_parser("lock").add_subparsers(dest="sub", required=True)
    s = lk.add_parser("status"); s.add_argument("root")
    s = lk.add_parser("acquire"); s.add_argument("root"); s.add_argument("--run-id", required=True)
    s.add_argument("--session")
    s = lk.add_parser("verify"); s.add_argument("root"); s.add_argument("--token", required=True)
    s = lk.add_parser("release"); s.add_argument("root"); s.add_argument("--token", required=True)
    s = lk.add_parser("recover"); s.add_argument("root"); s.add_argument("--run-id", required=True)
    s.add_argument("--expected-token", required=True, help="token prefix shown by lock status")
    s.add_argument("--user-confirmed-owner-inactive", action="store_true",
                   help="only after the user explicitly confirmed the owning session has ended"); s.add_argument("--session")

    rn = sub.add_parser("run").add_subparsers(dest="sub", required=True)
    s = rn.add_parser("init"); s.add_argument("root"); s.add_argument("--token", required=True)
    s.add_argument("--run-id"); s.add_argument("--mode", required=True, choices=["fix", "all", "contextual"])
    s.add_argument("--scope", required=True); s.add_argument("--exclude", action="append")
    s.add_argument("--only"); s.add_argument("--audit-id"); s.add_argument("--skill-version", default=VERSION)
    s.add_argument("--audit-json"); s.add_argument("--plan-json"); s.add_argument("--baseline-json")
    s = rn.add_parser("update"); s.add_argument("root"); s.add_argument("run_id")
    s.add_argument("--token", required=True); s.add_argument("--status"); s.add_argument("--next-step")
    s.add_argument("--set-json")
    s = rn.add_parser("list"); s.add_argument("root"); s.add_argument("--all", action="store_true")
    s = rn.add_parser("show"); s.add_argument("root"); s.add_argument("run_id")

    bt = sub.add_parser("batch").add_subparsers(dest="sub", required=True)
    s = bt.add_parser("begin"); s.add_argument("root"); s.add_argument("run_id")
    s.add_argument("--token", required=True); s.add_argument("--batch", required=True)
    s.add_argument("--files", nargs="+", help="path | create:path | modify:path | delete:path | move:src=>dst")
    s.add_argument("--expect", action="append", help="path=sha256|missing planned preimage")
    s.add_argument("--findings"); s.add_argument("--description")
    s = bt.add_parser("record"); s.add_argument("root"); s.add_argument("run_id")
    s.add_argument("--token", required=True); s.add_argument("--batch", required=True)
    s.add_argument("paths", nargs="+")
    s = bt.add_parser("end"); s.add_argument("root"); s.add_argument("run_id")
    s.add_argument("--token", required=True); s.add_argument("--batch", required=True)
    s = bt.add_parser("mark"); s.add_argument("root"); s.add_argument("run_id")
    s.add_argument("--token", required=True); s.add_argument("--batch", required=True)
    s.add_argument("--status", required=True); s.add_argument("--checks-json"); s.add_argument("--note")

    s = sub.add_parser("guard"); s.add_argument("root"); s.add_argument("--token", required=True)
    s.add_argument("--expect", action="append", required=True)
    s = sub.add_parser("diagnose"); s.add_argument("root"); s.add_argument("run_id")
    s = sub.add_parser("restore"); s.add_argument("root"); s.add_argument("run_id")
    s.add_argument("--batch", required=True); s.add_argument("--token")
    s.add_argument("--dry-run", action="store_true"); s.add_argument("--partial", action="store_true")
    s.add_argument("--include-unrecorded", action="append",
                   help="path whose unrecorded change was inspected and belongs only to this run")
    return p


def dispatch(a):
    if a.cmd == "fingerprint":
        return cmd_fingerprint(a)
    ident = repo_identity(a.root)
    sd = state_dir(a)
    if a.cmd == "repo-key":
        return dict(status="ok", **ident)
    if a.cmd == "new-id":
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
        if a.kind == "audit":
            new = "A-%s-%s" % (stamp, ident["key"][:6])
        else:
            new = "R-%s-%s" % (stamp, secrets.token_hex(2))
        return {"status": "ok", "id": new, "root": ident["root"], "key": ident["key"]}
    if a.cmd == "hash":
        return {"status": "ok", "root": ident["root"],
                "hashes": {rel_inside(ident["root"], p): file_hash(os.path.join(ident["root"], p)) or "missing"
                           for p in a.paths}}
    if a.cmd == "lock":
        if a.sub == "status":
            return lock_status_obj(sd, ident)
        if a.sub == "acquire":
            return acquire(sd, ident, check_id(a.run_id, "run id"), a.session)
        if a.sub == "verify":
            require_owner(sd, ident, a.token)
            return {"status": "ok", "owner": True}
        if a.sub == "release":
            return release(sd, ident, a.token)
        if a.sub == "recover":
            return recover(sd, ident, a.expected_token, check_id(a.run_id, "run id"),
                           a.user_confirmed_owner_inactive, a.session)
    if a.cmd == "run":
        return {"init": cmd_run_init, "update": cmd_run_update, "list": cmd_run_list,
                "show": cmd_run_show}[a.sub](sd, ident, a)
    if a.cmd == "batch":
        return {"begin": cmd_batch_begin, "record": cmd_batch_record, "end": cmd_batch_end,
                "mark": cmd_batch_mark}[a.sub](sd, ident, a)
    if a.cmd == "guard":
        return cmd_guard(sd, ident, a)
    if a.cmd == "diagnose":
        return cmd_diagnose(sd, ident, a)
    if a.cmd == "restore":
        if not a.dry_run and not a.token:
            raise Fail(EXIT_USAGE, "restore needs --token (or --dry-run)")
        return cmd_restore(sd, ident, a)
    raise Fail(EXIT_USAGE, "unknown command")


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        res = dispatch(a)
        code = EXIT_OK
    except Fail as f:
        res, code = f.payload, f.code
    except OSError as e:
        res, code = {"status": "error", "error": "%s: %s" % (type(e).__name__, e)}, EXIT_USAGE
    sys.stdout.write(json.dumps(res, indent=2, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
