"""Tests for tools/sync.py against a throwaway home directory (never the real one)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC = os.path.join(REPO, "tools", "sync.py")


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="rapihin-home-")
        os.makedirs(os.path.join(self.home, ".codex"))
        with open(os.path.join(self.home, ".codex", "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("# My rules\n\nAlways run tests.\n")

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def sync(self, *args, code=0):
        env = dict(os.environ)
        env.pop("CODEX_HOME", None)
        env.pop("KIMI_CODE_HOME", None)
        p = subprocess.run([sys.executable, SYNC] + list(args) + ["--home", self.home],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def agents_md(self):
        with open(os.path.join(self.home, ".codex", "AGENTS.md"), encoding="utf-8") as f:
            return f.read()

    def test_install_is_idempotent_and_preserves_existing_instructions(self):
        hosts = "codex,claude,antigravity"
        plan = self.sync("plan", "--hosts", hosts)
        self.assertFalse(os.path.exists(os.path.join(self.home, ".agents")), "plan must not write")
        self.assertTrue(all(c["status"].startswith("would") for c in plan["skill_copies"]))
        self.sync("install", "--hosts", hosts)
        again = self.sync("install", "--hosts", hosts)
        self.assertEqual({c["status"] for c in again["skill_copies"]}, {"unchanged"})
        self.assertEqual({r["status"] for r in again["reminders"]}, {"unchanged"})
        text = self.agents_md()
        self.assertTrue(text.startswith("# My rules\n\nAlways run tests.\n"))
        self.assertEqual(text.count("<!-- rapih-in:begin -->"), 1)
        ag = os.path.join(self.home, ".gemini", "config", "rules", "rapih-in.md")
        with open(ag, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("---\ntrigger: always_on\n"))
        v = self.sync("verify")
        self.assertTrue(v["ok"])
        self.assertEqual(len(v["skill_copies"]), 3 * 8)  # main skill + 7 shortcuts per root
        names = sorted(os.listdir(os.path.join(self.home, ".claude", "skills")))
        self.assertEqual(names, ["rapih-in", "rapih-in-all", "rapih-in-audit", "rapih-in-check", "rapih-in-fix",
                                 "rapih-in-place", "rapih-in-plan", "rapih-in-resume"])

    def test_unmanaged_existing_skill_is_not_overwritten(self):
        other = os.path.join(self.home, ".claude", "skills", "rapih-in")
        os.makedirs(other)
        with open(os.path.join(other, "SKILL.md"), "w") as f:
            f.write("someone else's skill\n")
        out = self.sync("install", "--hosts", "claude", code=1)
        self.assertTrue(out["skill_copies"][0]["status"].startswith("conflict"))
        with open(os.path.join(other, "SKILL.md")) as f:
            self.assertEqual(f.read(), "someone else's skill\n")

    def test_drift_is_detected_and_local_edits_are_protected(self):
        self.sync("install", "--hosts", "codex")
        installed = os.path.join(self.home, ".agents", "skills", "rapih-in", "SKILL.md")
        with open(installed, "a", encoding="utf-8") as f:
            f.write("\nlocal edit\n")
        self.assertFalse(self.sync("verify", code=1)["ok"])
        out = self.sync("install", "--hosts", "codex", code=1)
        self.assertIn("edited locally", out["skill_copies"][0]["status"])

    def test_shortcuts_are_manual_only_and_optional(self):
        self.sync("install", "--hosts", "claude", "--no-shortcuts")
        self.assertEqual(os.listdir(os.path.join(self.home, ".claude", "skills")), ["rapih-in"])
        self.sync("install", "--hosts", "claude")
        sk = os.path.join(self.home, ".claude", "skills", "rapih-in-fix", "SKILL.md")
        with open(sk, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("disable-model-invocation: true", text)
        self.assertIn("../rapih-in/SKILL.md", text)
        oy = os.path.join(self.home, ".claude", "skills", "rapih-in-fix", "agents", "openai.yaml")
        with open(oy, encoding="utf-8") as f:
            self.assertIn("allow_implicit_invocation: false", f.read())

    def test_stale_shortcut_is_reported(self):
        self.sync("install", "--hosts", "codex")
        stale = os.path.join(self.home, ".agents", "skills", "rapih-in-old-mode")
        shutil.copytree(os.path.join(self.home, ".agents", "skills", "rapih-in-audit"), stale)
        v = self.sync("verify", code=1)
        self.assertTrue(any(c.get("error", "").startswith("no longer in source") for c in v["skill_copies"]))
        self.sync("uninstall", "--hosts", "codex")
        self.assertEqual(os.listdir(os.path.join(self.home, ".agents", "skills")), [])

    def test_uninstall_removes_only_rapih_in_parts(self):
        self.sync("install", "--hosts", "codex,claude")
        self.sync("uninstall", "--hosts", "codex,claude")
        self.assertEqual(self.agents_md(), "# My rules\n\nAlways run tests.\n")
        self.assertFalse(os.path.exists(os.path.join(self.home, ".agents", "skills", "rapih-in")))
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude", "rules", "rapih-in.md")))

    def test_project_scope_uses_shared_agents_dir_and_single_block(self):
        proj = os.path.join(self.home, "work", "my app")
        os.makedirs(proj)
        self.sync("install", "--scope", "project", "--project", proj, "--hosts", "codex,cursor,kimi,claude")
        self.assertTrue(os.path.isfile(os.path.join(proj, ".agents", "skills", "rapih-in", "SKILL.md")))
        with open(os.path.join(proj, "AGENTS.md"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("<!-- rapih-in:begin -->"), 1)
        # no CLAUDE.md: Claude Code reads the same AGENTS.md, so no extra rule file
        self.assertFalse(os.path.exists(os.path.join(proj, ".claude", "rules", "rapih-in.md")))


if __name__ == "__main__":
    unittest.main()
