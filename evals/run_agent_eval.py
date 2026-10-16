#!/usr/bin/env python3
"""Run one behavioral evaluation case through a real agent CLI on a throwaway fixture copy.

    python evals/run_agent_eval.py --case CASE_ID --fixture web-shop --prompt "/rapih-in audit"
        [--host claude|codex] [--model sonnet] [--workdir DIR] [--continue-from DIR] [--pre-lock]

The fixture is copied into a fresh work directory (path contains a space), committed to a
throwaway git repo, and the agent runs there with RAPIH_IN_STATE_DIR pointing at a state
directory inside the work area, so ~/.rapih-in and the source fixtures are never touched.
Writes <workdir>/result.json with: final text, changed files (git status), state files,
before/after tree hashes, exit code, duration. Assertions are reviewed in docs/evaluation.md.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(os.path.dirname(HERE), "skills", "rapih-in", "scripts", "rapihin_state.py")


def rmtree(path):
    """shutil.rmtree that also clears read-only files (git objects on Windows)."""
    import stat

    def onerror(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if os.path.exists(path):
        shutil.rmtree(path, onerror=onerror)


def tree(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__")]
        for n in fn:
            p = os.path.join(dp, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(f.read()).hexdigest()[:12]
    return out


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.email=eval@rapih-in", "-c", "user.name=eval"] + list(args),
                          cwd=cwd, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)


def helper(state, *args):
    p = subprocess.run([sys.executable, HELPER, "--state-dir", state] + list(args), capture_output=True, text=True)
    out = json.loads(p.stdout)
    if p.returncode:
        raise SystemExit("setup failed: %s" % out)
    return out


def setup_interrupted(work, state):
    """Simulate a crashed run: batch b1 extracted validateCheckout into a new file, recorded it,
    then died before editing CheckoutPage.js. The lock is left behind with a dead owner pid.
    Afterwards the user edits an unrelated file (src/main.js)."""
    tok = helper(state, "lock", "acquire", work, "--run-id", "R-20261016T080000-dead")["token"]
    helper(state, "run", "init", work, "--token", tok, "--mode", "all", "--scope", ".",
           "--exclude", "src/generated/**", "--audit-id", "A-20261016T075900-sim",
           "--audit-json", json.dumps({"findings": [{"id": "R001", "kind": "mixed-responsibility",
                                                   "paths": ["src/features/checkout/CheckoutPage.js"],
                                                   "symbols": ["validateCheckout", "submitOrder"]}]}),
           "--plan-json", json.dumps({"batches": [
               {"id": "b1", "findings": ["R001"], "op": "extract validateCheckout + EMAIL_RE",
                "to": "src/features/checkout/validation/checkoutValidation.js"},
               {"id": "b2", "findings": ["R001"], "op": "extract submitOrder", "to": "src/features/checkout/api/checkout.js"}]}),
           "--only", "R001")
    helper(state, "batch", "begin", work, "R-20261016T080000-dead", "--token", tok, "--batch", "b1",
           "--findings", "R001", "--files", "modify:src/features/checkout/CheckoutPage.js",
           "create:src/features/checkout/validation/checkoutValidation.js")
    src = open(os.path.join(work, "src/features/checkout/CheckoutPage.js"), encoding="utf-8").read()
    start = src.index("const EMAIL_RE")
    end = src.index("export async function submitOrder")
    newf = os.path.join(work, "src/features/checkout/validation/checkoutValidation.js")
    os.makedirs(os.path.dirname(newf), exist_ok=True)
    with open(newf, "w", encoding="utf-8", newline="\n") as f:
        f.write(src[start:end].rstrip() + "\n")
    helper(state, "batch", "record", work, "R-20261016T080000-dead", "--token", tok, "--batch", "b1",
           "src/features/checkout/validation/checkoutValidation.js")
    key = helper(state, "repo-key", work)["key"]
    lf = os.path.join(state, "locks", key, "owner.json")
    owner = json.load(open(lf, encoding="utf-8"))
    owner["invoker_pid"] = 999999
    json.dump(owner, open(lf, "w", encoding="utf-8"))
    with open(os.path.join(work, "src/main.js"), "a", encoding="utf-8", newline="\n") as f:
        f.write("\n// user note added after the crash\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--fixture")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--host", default="claude", choices=["claude", "codex"])
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--base", default=os.path.join(tempfile.gettempdir(), "rapih-in-evals"))
    ap.add_argument("--continue-from", help="reuse the work dir and session of an earlier case")
    ap.add_argument("--pre-lock", action="store_true", help="hold the writer lock as another run first")
    ap.add_argument("--from-work", help="copy an earlier case's work dir (with its git history) as the fixture")
    ap.add_argument("--new-session", action="store_true", help="with --continue-from: same work dir, new session")
    ap.add_argument("--setup", choices=["interrupted-extraction"], help="prepare state before the agent runs")
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args()

    if a.continue_from:
        with open(os.path.join(a.continue_from, "result.json"), encoding="utf-8") as f:
            prev = json.load(f)
        work, session = prev["work"], (None if a.new_session else prev.get("session_id"))
        area = os.path.join(a.base, a.case)
        os.makedirs(area, exist_ok=True)
        state = prev["state_dir"]
    else:
        area = os.path.join(a.base, a.case)
        rmtree(area)
        work = os.path.join(area, "app copy")
        state = os.path.join(area, "state")
        if a.from_work:
            shutil.copytree(a.from_work, work)
            git(work, "add", "-A")
            git(work, "commit", "-qm", "state after earlier case")
        else:
            shutil.copytree(os.path.join(HERE, "fixtures", a.fixture), work)
            git(work, "init", "-q")
            git(work, "add", "-A")
            git(work, "commit", "-qm", "fixture baseline")
        session = None

    env = dict(os.environ, RAPIH_IN_STATE_DIR=state)
    pre_lock = None
    if a.pre_lock:
        p = subprocess.run([sys.executable, HELPER, "--state-dir", state, "lock", "acquire", work,
                            "--run-id", "R-other-session"], capture_output=True, text=True)
        pre_lock = json.loads(p.stdout)

    if a.setup == "interrupted-extraction":
        setup_interrupted(work, state)

    before = tree(work)
    t0 = time.time()
    if a.host == "claude":
        cmd = [shutil.which("claude") or "claude", "-p", a.prompt, "--model", a.model,
               "--output-format", "stream-json", "--verbose",
               "--permission-mode", "acceptEdits",
               "--allowedTools", "Bash", "Read", "Edit", "Write", "Glob", "Grep", "Skill"]
        if session:
            cmd += ["--resume", session]
    else:
        cmd = [shutil.which("codex") or "codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write",
               "-c", "sandbox_workspace_write.writable_roots=[%s]" % json.dumps(state), a.prompt]
    p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8",
                       stdin=subprocess.DEVNULL,
                       errors="replace", timeout=a.timeout)
    dur = round(time.time() - t0, 1)
    after = tree(work)

    text, session_id, cost, tools, skills = p.stdout, None, None, [], []
    if a.host == "claude":
        for line in p.stdout.splitlines():
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if j.get("type") == "assistant":
                for c in j.get("message", {}).get("content", []):
                    if c.get("type") == "tool_use":
                        tools.append(c.get("name"))
                        if c.get("name") == "Skill":
                            skills.append(c.get("input", {}).get("skill"))
            elif j.get("type") == "user" and "rapih-in" in json.dumps(j)[:400] and "<command-name>" in json.dumps(j)[:400]:
                skills.append("rapih-in (slash command)")
            elif j.get("type") == "result":
                text, session_id, cost = j.get("result", ""), j.get("session_id"), j.get("total_cost_usd")
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    state_files = []
    if os.path.isdir(state):
        for dp, _, fn in os.walk(state):
            state_files += [os.path.relpath(os.path.join(dp, n), state).replace(os.sep, "/") for n in fn]
    res = {"case": a.case, "host": a.host, "model": a.model if a.host == "claude" else "codex default",
           "fixture": a.fixture, "prompt": a.prompt, "work": work, "state_dir": state,
           "exit_code": p.returncode, "duration_s": dur, "session_id": session_id or session,
           "cost_usd": cost, "tools_used": sorted(set(t for t in tools if t)), "skills_invoked": skills,
           "changed_files": changed, "git_status": git(work, "status", "--porcelain").stdout,
           "state_files": sorted(state_files), "pre_lock": pre_lock, "stderr_tail": p.stderr[-2000:],
           "final_text": text}
    with open(os.path.join(area, "result.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: res[k] for k in ("case", "exit_code", "duration_s", "skills_invoked", "changed_files",
                                          "state_files")},
                     indent=2))


if __name__ == "__main__":
    main()
