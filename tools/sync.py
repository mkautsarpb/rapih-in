#!/usr/bin/env python3
"""Install, update, verify, and uninstall rapih-in from this repository (one source).

    python tools/sync.py plan      [--scope user|project] [--project DIR] [--hosts LIST]
    python tools/sync.py install   [--scope user|project] [--project DIR] [--hosts LIST] [--force]
    python tools/sync.py verify    [--scope user|project] [--project DIR]
    python tools/sync.py uninstall [--scope user|project] [--project DIR] [--hosts LIST]
    python tools/sync.py reminder           # print the reminder text (for Cursor User Rules)

--hosts: auto (default; detected hosts only) or a comma list of
         codex, claude, antigravity, antigravity-cli, cursor, kimi
--home:  alternate home directory for tests (does not change environment variables)

Only copies/blocks created by this tool are updated or removed: copies carry
.rapih-in-install.json, reminder blocks sit between rapih-in markers, reminder
files carry a rapih-in header. Anything else is reported, never overwritten.
Installing never runs an audit or changes application source.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import datetime as _dt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO, "skills")
SOURCE = os.path.join(SKILLS_DIR, "rapih-in")
MANIFEST = ".rapih-in-install.json"
SKIP = {"__pycache__", MANIFEST, ".DS_Store"}
HOSTS = ["codex", "claude", "antigravity", "antigravity-cli", "cursor", "kimi"]
BEGIN, END = "<!-- rapih-in:begin -->", "<!-- rapih-in:end -->"
FILE_HEADER = "<!-- managed by rapih-in tools/sync.py; edit the source repo instead -->"

REMINDER = (
    "Use the rapih-in skill when placing, creating, moving, or renaming source files and folders, "
    "and for the modularization the current task needs. Follow the repository's ownership and "
    "local patterns. Split code by responsibility and clear benefit; line count is only an audit "
    "signal. Preserve contracts and behavior, then validate references and affected parts. Keep "
    "automatic help limited to the current task. rapih-in audit, plan, check, and place never "
    "change source; fix and all run only on an explicit tidy-up request. A small bug fix never "
    "triggers a repo-wide audit or split.")


def tree_hash(root):
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
        for name in sorted(filenames):
            if name in SKIP or name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as f:
                data = f.read().replace(b"\r\n", b"\n")
            h.update(rel.encode() + b"\0" + hashlib.sha256(data).digest())
    return h.hexdigest()


def sources(shortcuts=True):
    """(name, source dir) for the main skill and, unless disabled, the per-mode shortcuts."""
    out = [("rapih-in", SOURCE)]
    if shortcuts:
        out += [(d, os.path.join(SKILLS_DIR, d)) for d in sorted(os.listdir(SKILLS_DIR))
                if d.startswith("rapih-in-") and os.path.isfile(os.path.join(SKILLS_DIR, d, "SKILL.md"))]
    return out


def version():
    with open(os.path.join(SOURCE, "scripts", "rapihin_state.py"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("VERSION"):
                return line.split("=")[1].strip().strip('"')
    return "unknown"


def which(name):
    return shutil.which(name) is not None


def detect(home):
    j = lambda *p: os.path.join(home, *p)
    kimi_home = os.environ.get("KIMI_CODE_HOME") or j(".kimi-code")
    return {
        "codex": which("codex") or os.path.isdir(j(".codex")),
        "claude": which("claude") or os.path.isdir(j(".claude")),
        "antigravity": os.path.isdir(j(".gemini", "config")) or os.path.isdir(j(".gemini", "antigravity-ide")),
        "antigravity-cli": os.path.isdir(j(".gemini", "antigravity-cli")),
        "cursor": os.path.isdir(j(".cursor")) or which("cursor-agent"),
        "kimi": which("kimi") or os.path.isdir(kimi_home),
    }


def targets(scope, home, project, hosts):
    """Return (skill copy dirs -> hosts served, reminder actions)."""
    j = lambda *p: os.path.join(home, *p)
    copies, reminders = {}, []
    add = lambda path, host: copies.setdefault(path, []).append(host)
    if scope == "user":
        codex_home = os.environ.get("CODEX_HOME") or j(".codex")
        kimi_home = os.environ.get("KIMI_CODE_HOME") or j(".kimi-code")
        for h in hosts:
            if h in ("codex", "cursor", "kimi"):
                add(j(".agents", "skills", "rapih-in"), h)
            if h == "claude":
                add(j(".claude", "skills", "rapih-in"), h)
            if h == "antigravity":
                add(j(".gemini", "config", "skills", "rapih-in"), h)
            if h == "antigravity-cli":
                add(j(".gemini", "antigravity-cli", "skills", "rapih-in"), h)
        if "codex" in hosts:
            override = os.path.join(codex_home, "AGENTS.override.md")
            effective = override if os.path.isfile(override) and os.path.getsize(override) else \
                os.path.join(codex_home, "AGENTS.md")
            reminders.append(("block", effective, "codex"))
        if "claude" in hosts:
            reminders.append(("file", j(".claude", "rules", "rapih-in.md"), "claude"))
        if "antigravity" in hosts:
            reminders.append(("file-ag", j(".gemini", "config", "rules", "rapih-in.md"), "antigravity"))
        if "antigravity-cli" in hosts:
            reminders.append(("file-ag", j(".gemini", "antigravity-cli", "rules", "rapih-in.md"),
                              "antigravity-cli"))
        if "kimi" in hosts:
            reminders.append(("block", os.path.join(kimi_home, "AGENTS.md"), "kimi"))
        if "cursor" in hosts:
            reminders.append(("manual", "Cursor Settings > Customize > Rules > User Rules", "cursor"))
    else:
        p = lambda *x: os.path.join(project, *x)
        for h in hosts:
            if h in ("codex", "cursor", "kimi", "antigravity", "antigravity-cli"):
                add(p(".agents", "skills", "rapih-in"), h)
            if h == "claude":
                add(p(".claude", "skills", "rapih-in"), h)
        others = [h for h in hosts if h != "claude"]
        if others:
            reminders.append(("block", p("AGENTS.md"), ",".join(others)))
        if "claude" in hosts:
            has_claude_md = any(os.path.isfile(p(n)) for n in ("CLAUDE.md", os.path.join(".claude", "CLAUDE.md"),
                                                               "CLAUDE.local.md"))
            if has_claude_md or not others:
                reminders.append(("file", p(".claude", "rules", "rapih-in.md"), "claude"))
            # otherwise Claude Code reads the same AGENTS.md block (no CLAUDE.md present)
    return copies, reminders


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".rapih-in-tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def block_text():
    return "%s\n## rapih-in\n\n%s\n%s\n" % (BEGIN, REMINDER, END)


def file_text(kind):
    body = "# rapih-in\n\n%s\n" % REMINDER
    if kind == "file-ag":
        return "---\ntrigger: always_on\ndescription: rapih-in placement reminder\n---\n%s\n%s" % (FILE_HEADER, body)
    return "%s\n%s" % (FILE_HEADER, body)


def strip_block(text):
    if BEGIN not in text:
        return text, 0
    out, n, rest = [], 0, text
    while BEGIN in rest:
        pre, _, after = rest.partition(BEGIN)
        if END not in after:
            break
        _, _, rest = after.partition(END)
        out.append(pre.rstrip("\n") + ("\n" if pre.strip() else ""))
        rest = rest.lstrip("\n")
        n += 1
    out.append(rest)
    return "".join(out), n


def copy_skill(src, dest, force, dry):
    src_hash = tree_hash(src)
    man_path = os.path.join(dest, MANIFEST)
    if os.path.exists(dest):
        if not os.path.isfile(man_path) and not force:
            return "conflict: unmanaged rapih-in exists (not overwritten; use --force after review)"
        if os.path.isfile(man_path):
            man = json.loads(read_text(man_path) or "{}")
            current = tree_hash(dest)
            if current == src_hash:
                return "unchanged"
            if man.get("source_hash") != current and not force:
                return "conflict: installed copy was edited locally (not overwritten; use --force)"
    if dry:
        return "would install/update"
    parent = os.path.dirname(dest)
    os.makedirs(parent, exist_ok=True)
    staging = dest + ".rapih-in-new"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.copytree(src, staging, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", MANIFEST))
    write_text(os.path.join(staging, MANIFEST), json.dumps({
        "source": src, "source_hash": src_hash, "version": version(),
        "installed_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, indent=2))
    old = dest + ".rapih-in-old"
    if os.path.exists(dest):
        os.replace(dest, old)
    os.replace(staging, dest)
    shutil.rmtree(old, ignore_errors=True)
    return "installed"


def apply_reminder(kind, path, dry):
    if kind == "manual":
        return "manual: paste `python tools/sync.py reminder` output into " + path
    current = read_text(path)
    if kind == "block":
        base, n = strip_block(current or "")
        new = (base.rstrip("\n") + "\n\n" if base.strip() else "") + block_text()
        if current == new:
            return "unchanged"
        if dry:
            return "would %s block" % ("update" if n else "add")
        write_text(path, new)
        return "%s block" % ("updated" if n else "added")
    want = file_text(kind)
    if current is not None and FILE_HEADER not in current:
        return "conflict: %s exists and is not managed by rapih-in" % path
    if current == want:
        return "unchanged"
    if dry:
        return "would write file"
    write_text(path, want)
    return "written"


def discovery_roots(home, project):
    j = lambda *p: os.path.join(home, *p)
    roots = [j(".agents", "skills"), j(".claude", "skills"), j(".codex", "skills"), j(".cursor", "skills"),
             j(".gemini", "config", "skills"), j(".gemini", "antigravity", "skills"),
             j(".gemini", "antigravity-cli", "skills"),
             os.path.join(os.environ.get("KIMI_CODE_HOME") or j(".kimi-code"), "skills")]
    if project:
        roots += [os.path.join(project, d, "skills") for d in (".agents", ".claude", ".cursor", ".kimi-code",
                                                              ".codex", ".agent")]
    return roots


def cmd_verify(home, project):
    src = dict(sources())
    src_hash = tree_hash(SOURCE)
    found, ok = [], True
    for root in discovery_roots(home, project):
        if not os.path.isdir(root):
            continue
        names = sorted(n for n in os.listdir(root) if n == "rapih-in" or n.startswith("rapih-in-"))
        if names and "rapih-in" not in names:
            ok = False
            found.append({"path": root, "error": "shortcuts present without the main rapih-in skill"})
        for name in names:
            d = os.path.join(root, name)
            if not os.path.isdir(d) or name.endswith((".rapih-in-new", ".rapih-in-old")):
                continue
            managed = os.path.isfile(os.path.join(d, MANIFEST))
            if name not in src:
                ok = False
                found.append({"path": d, "managed": managed, "error": "no longer in source (stale)"})
                continue
            same = tree_hash(d) == tree_hash(src[name])
            ok &= same
            found.append({"path": d, "managed": managed, "identical_to_source": same})
    rem = []
    for path in [os.path.join(os.environ.get("CODEX_HOME") or os.path.join(home, ".codex"), n)
                 for n in ("AGENTS.md", "AGENTS.override.md")] + \
                [os.path.join(os.environ.get("KIMI_CODE_HOME") or os.path.join(home, ".kimi-code"), "AGENTS.md"),
                 os.path.join(home, ".agents", "AGENTS.md"), os.path.join(home, ".claude", "CLAUDE.md"),
                 os.path.join(home, ".claude", "rules", "rapih-in.md"),
                 os.path.join(home, ".gemini", "GEMINI.md"), os.path.join(home, ".gemini", "AGENTS.md"),
                 os.path.join(home, ".gemini", "config", "rules", "rapih-in.md"),
                 os.path.join(home, ".gemini", "antigravity-cli", "rules", "rapih-in.md")] + \
                ([os.path.join(project, n) for n in ("AGENTS.md", "CLAUDE.md", os.path.join(".claude", "rules", "rapih-in.md"))]
                 if project else []):
        text = read_text(path)
        if text is None:
            continue
        blocks = text.count(BEGIN)
        managed_file = FILE_HEADER in text
        if blocks or managed_file or "rapih-in" in text:
            dup = blocks > 1
            ok &= not dup
            rem.append({"path": path, "blocks": blocks, "managed_file": managed_file, "duplicate": dup,
                        "current": (REMINDER in text)})
    return {"ok": ok, "source": SOURCE, "source_hash": src_hash[:16], "version": version(),
            "skill_copies": found, "reminders": rem}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["plan", "install", "verify", "uninstall", "reminder"])
    ap.add_argument("--scope", choices=["user", "project"], default="user")
    ap.add_argument("--project")
    ap.add_argument("--hosts", default="auto")
    ap.add_argument("--home", default=os.path.expanduser("~"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-shortcuts", action="store_true",
                    help="install only the main skill, without the per-mode shortcut commands")
    a = ap.parse_args(argv)
    home = os.path.abspath(a.home)
    project = os.path.abspath(a.project) if a.project else None
    if a.cmd == "reminder":
        print(REMINDER)
        return 0
    if a.scope == "project" and not project:
        ap.error("--scope project needs --project DIR")
    if project and os.path.normcase(os.path.realpath(project)) == os.path.normcase(os.path.realpath(REPO)) \
            and a.cmd == "install":
        ap.error("refusing to install into the rapih-in source repository itself")
    if a.cmd == "verify":
        res = cmd_verify(home, project)
        print(json.dumps(res, indent=2))
        return 0 if res["ok"] else 1
    det = detect(home)
    hosts = [h for h in HOSTS if det[h]] if a.hosts == "auto" else [h.strip() for h in a.hosts.split(",") if h.strip()]
    bad = [h for h in hosts if h not in HOSTS]
    if bad:
        ap.error("unknown host(s): %s" % ", ".join(bad))
    copies, reminders = targets(a.scope, home, project, hosts)
    report = {"scope": a.scope, "detected": det, "hosts": hosts, "version": version(), "skill_copies": [],
              "reminders": []}
    if a.cmd == "uninstall":
        for main_dest in copies:
            root = os.path.dirname(main_dest)
            names = {n for n, _ in sources()} | {n for n in (os.listdir(root) if os.path.isdir(root) else [])
                                                 if n.startswith("rapih-in-")}
            for name in sorted(names):
                dest = os.path.join(root, name)
                if os.path.isfile(os.path.join(dest, MANIFEST)):
                    shutil.rmtree(dest)
                    status = "removed"
                else:
                    status = "absent" if not os.path.exists(dest) else "kept: not managed by rapih-in"
                report["skill_copies"].append({"path": dest, "status": status})
        for kind, path, host in reminders:
            if kind == "manual":
                status = "manual: remove the rapih-in text from Cursor User Rules"
            elif kind == "block":
                text = read_text(path)
                base, n = strip_block(text or "")
                if n:
                    write_text(path, base)
                status = "removed block" if n else "absent"
            else:
                text = read_text(path)
                if text is not None and FILE_HEADER in text:
                    os.remove(path)
                    status = "removed"
                else:
                    status = "absent" if text is None else "kept: not managed by rapih-in"
            report["reminders"].append({"host": host, "path": path, "status": status})
        print(json.dumps(report, indent=2))
        return 0
    dry = a.cmd == "plan"
    for main_dest, served in copies.items():
        root = os.path.dirname(main_dest)
        for name, src in sources(not a.no_shortcuts):
            dest = os.path.join(root, name)
            report["skill_copies"].append({"path": dest, "serves": served,
                                           "status": copy_skill(src, dest, a.force, dry)})
    for kind, path, host in reminders:
        report["reminders"].append({"host": host, "path": path, "status": apply_reminder(kind, path, dry)})
    report["note"] = ("Installation only places files; it never audits or changes application source. "
                      "Claude Code may need /reload-skills if ~/.claude/skills did not exist at session start; "
                      "restart Codex/Antigravity sessions if the skill does not appear.")
    print(json.dumps(report, indent=2))
    return 1 if any(str(x["status"]).startswith("conflict") for x in report["skill_copies"] + report["reminders"]) else 0


if __name__ == "__main__":
    sys.exit(main())
