#!/usr/bin/env python3
"""Static checks for the rapih-in package and its documentation.

    python tools/validate.py

Checks: SKILL.md frontmatter and size, name/folder match, reference links both ways,
host-specific syntax kept out of the core, helper compiles, openai.yaml keys,
README language switch, README parity (headings, tables, code blocks), relative
links and images, LICENSE text. Exit 1 on any failure.
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "rapih-in")
failures, notes = [], []


def check(cond, msg):
    (notes if cond else failures).append(("ok   " if cond else "FAIL ") + msg)


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as f:
        return f.read()


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith(" "):
            out[k.strip()] = v.strip()
    return out


skill_md = read(SKILL, "SKILL.md")
fm = frontmatter(skill_md)
check(fm is not None, "SKILL.md has YAML frontmatter")
fm = fm or {}
check(set(fm) == {"name", "description"}, "frontmatter has only name and description (%s)" % sorted(fm))
check(fm.get("name") == os.path.basename(SKILL) == "rapih-in", "name matches folder")
check(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm.get("name", "")) is not None, "name is lowercase-hyphen")
desc = fm.get("description", "")
check(0 < len(desc) <= 1024, "description length %d <= 1024" % len(desc))
check("<" not in desc and ">" not in desc, "description has no angle brackets")
lines = skill_md.count("\n")
check(lines <= 500, "SKILL.md %d lines <= 500" % lines)
notes.append("info SKILL.md lines: %d (target 150-250)" % lines)

refs_dir = os.path.join(SKILL, "references")
refs = sorted(f for f in os.listdir(refs_dir) if f.endswith(".md"))
linked = set(re.findall(r"references/([a-z0-9-]+\.md)", skill_md))
for r in refs:
    check(r in linked, "SKILL.md links references/%s" % r)
for r in sorted(linked):
    check(os.path.isfile(os.path.join(refs_dir, r)), "linked reference exists: %s" % r)
check(os.path.isfile(os.path.join(SKILL, "scripts", "rapihin_state.py")), "helper script exists")

for name in refs:
    text = read(refs_dir, name)
    for target in re.findall(r"`([a-z0-9-]+\.md)(?:#[a-z0-9-]+)?`", text):
        check(os.path.isfile(os.path.join(refs_dir, target)), "%s mentions existing %s" % (name, target))
    if len(text.splitlines()) > 100:
        check(text.lstrip().splitlines()[2].lower().startswith("contents") or "Contents:" in text[:600],
              "%s (>100 lines) starts with a contents line" % name)

for token in ("$ARGUMENTS", "allowed-tools", "disable-model-invocation", "/skill:", "C:\\Users", "/Users/"):
    check(token not in skill_md, "SKILL.md core free of host-specific token %r" % token)

try:  # compile in memory only; a checker must not write __pycache__ into the skill
    helper_path = os.path.join(SKILL, "scripts", "rapihin_state.py")
    compile(read(helper_path), helper_path, "exec")
    check(True, "helper compiles")
except SyntaxError as e:
    check(False, "helper compiles: %s" % e)

yaml = read(SKILL, "agents", "openai.yaml")
keys = set(re.findall(r"^\s*([a-z_]+):", yaml, re.M))
allowed = {"interface", "display_name", "short_description", "icon_small", "icon_large", "brand_color",
           "default_prompt", "policy", "allow_implicit_invocation", "dependencies", "tools", "type", "value",
           "description", "transport", "url"}
check(keys <= allowed, "openai.yaml uses documented keys only (%s)" % sorted(keys - allowed))
check("allow_implicit_invocation: true" in yaml, "openai.yaml keeps implicit invocation")

import subprocess
sc = subprocess.run([sys.executable, os.path.join(REPO, "tools", "shortcuts.py"), "--check"],
                    capture_output=True, text=True)
check(sc.returncode == 0, "shortcut skills match tools/shortcuts.py template (%s)" % sc.stdout.strip())
skills_root = os.path.join(REPO, "skills")
for d in sorted(os.listdir(skills_root)):
    if not d.startswith("rapih-in-"):
        continue
    sfm = frontmatter(read(skills_root, d, "SKILL.md")) or {}
    check(sfm.get("name") == d, "shortcut %s name matches folder" % d)
    check(sfm.get("disable-model-invocation") == "true", "shortcut %s is manual-only" % d)
    check(len(sfm.get("description", "")) <= 1024, "shortcut %s description length" % d)
    check("allow_implicit_invocation: false" in read(skills_root, d, "agents", "openai.yaml"),
          "shortcut %s disables Codex implicit invocation" % d)
    check(d[len("rapih-in-"):] in ("audit", "plan", "fix", "check", "place", "all", "resume"),
          "shortcut %s maps to a real mode" % d)

# ---------------------------------------------------------------- docs
en, idn = read(REPO, "README.md"), read(REPO, "README.id.md")
switch = "[English](README.md) | [Bahasa Indonesia](README.id.md)"
check(switch in en[:1500], "README.md has language switch near the top")
check(switch in idn[:1500], "README.id.md has language switch near the top")


def outline(text):
    no_code = re.sub(r"```.*?```", "", text, flags=re.S)
    return {
        "h2": len(re.findall(r"^## ", no_code, re.M)),
        "h3": len(re.findall(r"^### ", no_code, re.M)),
        "code": len(re.findall(r"^```", text, re.M)),
        "tables": len(re.findall(r"^\|[ :-]+\|", no_code, re.M)),
    }


oe, oi = outline(en), outline(idn)
for k in oe:
    check(oe[k] == oi[k], "README parity %s: en=%d id=%d" % (k, oe[k], oi[k]))
code_en = re.findall(r"```.*?```", en, re.S)
code_id = re.findall(r"```.*?```", idn, re.S)
def commands(blocks):
    """Literal part of each example: prefix, mode, options, IDs, paths (free text may be translated)."""
    out = set()
    for line in re.findall(r"(?:/|\$)rapih-in[^\n`]*", "".join(blocks)):
        keep = [t for t in line.split() if t.startswith(("/", "$", "--", "R0", '"')) or "/" in t
                or t in ("help", "audit", "plan", "fix", "check", "place", "all", "resume")]
        out.add(" ".join(keep))
    return sorted(out)


cmd_en, cmd_id = commands(code_en), commands(code_id)
check(cmd_en == cmd_id, "README command examples identical in both languages (%d)" % len(cmd_en))
for mode in ("help", "audit", "plan", "fix", "check", "place", "all", "resume"):
    pat = r"`%s[ `]" % mode
    check(re.search(pat, en) is not None and re.search(pat, idn) is not None,
          "both READMEs document mode `%s`" % mode)
for opt in ("--dry-run", "--exclude", "--only", "[path]"):
    check(opt in en and opt in idn, "both READMEs document %s" % opt)

for name, text in (("README.md", en), ("README.id.md", idn)):
    no_code = re.sub(r"```.*?```", "", text, flags=re.S)
    for target in re.findall(r"\]\(([^)\s]+)\)", no_code) + re.findall(r'(?:src|srcset)="([^"]+)"', no_code):
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        path = target.split("#")[0]
        check(os.path.exists(os.path.join(REPO, path)), "%s link target exists: %s" % (name, target))
    for anchor in re.findall(r"\]\(#([^)]+)\)", no_code):
        heads = re.findall(r"^#+ (.+)$", no_code, re.M)
        slugs = {re.sub(r"[^\w\- ]", "", h.strip().lower()).replace(" ", "-") for h in heads}
        check(anchor in slugs, "%s anchor resolves: #%s" % (name, anchor))
    check("api.star-history.com" not in text or "repos=" in text, "%s Star History embed well-formed" % name)

lic = read(REPO, "LICENSE")
check(lic.startswith("MIT License"), "LICENSE starts with MIT License")
check("Permission is hereby granted, free of charge" in lic and 'THE SOFTWARE IS PROVIDED "AS IS"' in lic,
      "LICENSE contains the MIT grant and warranty disclaimer")
check(re.search(r"Copyright \(c\) \d{4} rapih-in contributors", lic) is not None, "LICENSE copyright line")
check(os.path.isfile(os.path.join(REPO, "assets", "branding", "rapih-in-logo.png")), "logo asset present")

for line in notes:
    print(line)
for line in failures:
    print(line)
print("\n%d checks, %d failed" % (len(notes) + len(failures), len(failures)))
sys.exit(1 if failures else 0)
