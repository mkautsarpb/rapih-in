"""Tests for skills/rapih-in/scripts/rapihin_state.py.

Run from the repository root:  python -m unittest discover -s tests -v

Every test works on throwaway fixtures in a temporary directory and a temporary
state directory; nothing touches ~/.rapih-in or a real project.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(os.path.dirname(HERE), "skills", "rapih-in", "scripts", "rapihin_state.py")


def sh(*args, cwd=None):
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)


class HelperCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rapihin-test-")
        self.state = os.path.join(self.tmp, "state dir")  # space on purpose
        self.repo = os.path.join(self.tmp, "my repo")      # space on purpose
        os.makedirs(os.path.join(self.repo, "src", "features", "checkout"))
        self.write("src/features/checkout/CheckoutPage.tsx", "export function CheckoutPage() {}\n")
        self.write("src/index.ts", "import { CheckoutPage } from './features/checkout/CheckoutPage';\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers -----------------------------------------------------------
    def run_helper(self, *args, expect=None):
        p = subprocess.run([sys.executable, HELPER, "--state-dir", self.state] + list(args),
                           capture_output=True, text=True)
        try:
            out = json.loads(p.stdout)
        except ValueError:
            self.fail("non-JSON output (%s): %s %s" % (p.returncode, p.stdout, p.stderr))
        if expect is not None:
            self.assertEqual(p.returncode, expect, out)
        return p.returncode, out

    def write(self, rel, text):
        full = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def read(self, rel):
        with open(os.path.join(self.repo, rel), encoding="utf-8") as f:
            return f.read()

    def acquire(self, run_id="R-test"):
        _, out = self.run_helper("lock", "acquire", self.repo, "--run-id", run_id, expect=0)
        return out["token"]

    def simulate_dead_owner(self, ancient=False):
        key = self.run_helper("repo-key", self.repo)[1]["key"]
        lock_file = os.path.join(self.state, "locks", key, "owner.json")
        with open(lock_file, encoding="utf-8") as f:
            owner = json.load(f)
        owner["invoker_pid"] = 999999  # not running
        if ancient:
            owner["acquired_at"] = "2001-01-01T00:00:00Z"
        with open(lock_file, "w", encoding="utf-8") as f:
            json.dump(owner, f)

    def new_run(self, token, **kw):
        args = ["run", "init", self.repo, "--token", token, "--mode", kw.get("mode", "fix"),
                "--scope", kw.get("scope", "src/"), "--audit-id", "A-20261016T000000-abcdef"]
        for x in kw.get("exclude", []):
            args += ["--exclude", x]
        if kw.get("only"):
            args += ["--only", kw["only"]]
        _, out = self.run_helper(*args, expect=0)
        return out["run_id"]


class LockTests(HelperCase):
    def test_read_only_commands_create_no_state(self):
        self.run_helper("lock", "status", self.repo, expect=0)
        self.run_helper("run", "list", self.repo, expect=0)
        self.run_helper("hash", self.repo, "src/index.ts", expect=0)
        self.assertFalse(os.path.exists(self.state), "read-only commands must not create state")

    def test_two_processes_exactly_one_acquires(self):
        start = time.time() + 1.5
        code = ("import subprocess,sys,time\n"
                "time.sleep(max(0,%r-time.time()))\n"
                "p=subprocess.run([sys.executable,%r,'--state-dir',%r,'lock','acquire',%r,'--run-id',sys.argv[1]],"
                "capture_output=True,text=True)\n"
                "print(p.returncode)\n") % (start, HELPER, self.state, self.repo)
        procs = [subprocess.Popen([sys.executable, "-c", code, "R-p%d" % i], stdout=subprocess.PIPE, text=True)
                 for i in range(8)]
        codes = [int(p.communicate()[0].strip()) for p in procs]
        self.assertEqual(codes.count(0), 1, codes)
        self.assertEqual(codes.count(3), 7, codes)
        _, st = self.run_helper("lock", "status", self.repo, expect=0)
        self.assertEqual(st["status"], "held")

    def test_busy_reports_owner_and_does_not_write(self):
        self.acquire("R-first")
        _, out = self.run_helper("lock", "acquire", self.repo, "--run-id", "R-second", expect=3)
        self.assertEqual(out["status"], "busy")
        self.assertEqual(out["owner"]["run_id"], "R-first")
        self.assertNotIn("token", out["owner"])

    def test_release_requires_owner_token(self):
        token = self.acquire()
        self.run_helper("lock", "release", self.repo, "--token", "0" * 32, expect=3)
        _, st = self.run_helper("lock", "status", self.repo, expect=0)
        self.assertEqual(st["status"], "held")
        self.run_helper("lock", "release", self.repo, "--token", token, expect=0)
        _, st = self.run_helper("lock", "status", self.repo, expect=0)
        self.assertEqual(st["status"], "free")

    def test_alias_path_shares_lock_identity(self):
        alias = os.path.join(self.tmp, "alias link")
        if os.name == "nt":
            r = sh("cmd", "/c", "mklink", "/J", alias, self.repo)
        else:
            os.symlink(self.repo, alias)
            r = None
        if r is not None and r.returncode != 0:
            self.skipTest("cannot create junction: %s" % r.stderr)
        _, a = self.run_helper("repo-key", self.repo, expect=0)
        _, b = self.run_helper("repo-key", alias, expect=0)
        _, c = self.run_helper("repo-key", os.path.join(alias, "src"), expect=0)
        self.assertEqual(a["key"], b["key"])
        self.acquire()
        self.run_helper("lock", "acquire", alias, "--run-id", "R-alias", expect=3)
        if os.name == "nt":
            os.rmdir(alias)  # removes the junction only
        else:
            os.unlink(alias)
        del c

    def test_git_worktrees_get_distinct_keys(self):
        if not shutil.which("git"):
            self.skipTest("git not available")
        for cmd in (["git", "init", "-q"], ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"],
                    ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"]):
            self.assertEqual(sh(*cmd, cwd=self.repo).returncode, 0)
        wt = os.path.join(self.tmp, "second worktree")
        r = sh("git", "worktree", "add", "-q", "--detach", wt, cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        _, main = self.run_helper("repo-key", os.path.join(self.repo, "src"), expect=0)
        _, other = self.run_helper("repo-key", wt, expect=0)
        self.assertTrue(main["git"])
        self.assertNotEqual(main["key"], other["key"])
        self.acquire()
        t2 = self.run_helper("lock", "acquire", wt, "--run-id", "R-wt", expect=0)[1]["token"]
        self.assertTrue(t2)

    def test_stale_lock_is_never_taken_by_age_or_without_confirmation(self):
        token = self.acquire("R-crashed")
        self.simulate_dead_owner(ancient=True)
        # a new run cannot acquire, however old the lock looks
        self.run_helper("lock", "acquire", self.repo, "--run-id", "R-new", expect=3)
        # recovery without confirmation is refused
        _, out = self.run_helper("lock", "recover", self.repo, "--run-id", "R-new",
                                 "--expected-token", token[:8], expect=3)
        self.assertIn("not confirmed", out["error"])
        # wrong expected owner is refused
        self.run_helper("lock", "recover", self.repo, "--run-id", "R-new", "--expected-token", "deadbeef",
                        "--user-confirmed-owner-inactive", expect=3)
        # explicit confirmation + matching owner: atomic takeover
        _, out = self.run_helper("lock", "recover", self.repo, "--run-id", "R-new", "--expected-token",
                                 token[:8], "--user-confirmed-owner-inactive", expect=0)
        self.assertEqual(out["status"], "acquired")
        self.assertEqual(out["recovered_from"]["run_id"], "R-crashed")
        # the crashed owner's token no longer authorizes writes
        self.run_helper("lock", "verify", self.repo, "--token", token, expect=3)

    def test_recovery_marks_interrupted_run(self):
        token = self.acquire("R-crash2")
        run_id = self.new_run(token)
        self.assertEqual(run_id[:2], "R-")
        self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b1",
                        "--files", "src/index.ts", expect=0)
        # owner still alive on this host: refused even with confirmation
        self.run_helper("lock", "recover", self.repo, "--run-id", run_id, "--expected-token",
                        token[:8], "--user-confirmed-owner-inactive", expect=3)
        self.simulate_dead_owner()
        _, out = self.run_helper("lock", "recover", self.repo, "--run-id", run_id, "--expected-token",
                                 token[:8], "--user-confirmed-owner-inactive", expect=0)
        self.assertEqual(out["recovered_from"]["journal"]["batches"]["b1"]["status"], "in_progress")
        _, show = self.run_helper("run", "show", self.repo, run_id, expect=0)
        self.assertEqual(show["checkpoint"]["status"], "interrupted")


class RunTests(HelperCase):
    def test_run_init_requires_lock(self):
        self.run_helper("run", "init", self.repo, "--token", "x" * 32, "--mode", "fix", "--scope", "src/",
                        expect=3)

    def test_guard_detects_external_edit(self):
        token = self.acquire()
        _, h = self.run_helper("hash", self.repo, "src/index.ts", expect=0)
        before = h["hashes"]["src/index.ts"]
        self.run_helper("guard", self.repo, "--token", token, "--expect", "src/index.ts=" + before, expect=0)
        self.write("src/index.ts", "// user edit\n")
        _, out = self.run_helper("guard", self.repo, "--token", token, "--expect", "src/index.ts=" + before,
                                 expect=4)
        self.assertEqual(out["conflicts"][0]["path"], "src/index.ts")
        self.assertEqual(self.read("src/index.ts"), "// user edit\n")

    def test_batch_begin_rejects_stale_preimage(self):
        token = self.acquire()
        run_id = self.new_run(token)
        _, out = self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b1",
                                 "--files", "src/index.ts", "--expect", "src/index.ts=" + "0" * 64, expect=4)
        self.assertIn("preimage", out["error"])

    def test_selection_scope_and_exclusions_are_persisted_and_protected(self):
        token = self.acquire()
        run_id = self.new_run(token, only="R003,R001,R001", exclude=["src/generated/**", "src/legacy/**"])
        _, show = self.run_helper("run", "show", self.repo, run_id, expect=0)
        cp = show["checkpoint"]
        self.assertEqual(cp["selected_ids"], ["R001", "R003"])
        self.assertEqual(cp["exclusions"], ["src/generated/**", "src/legacy/**"])
        self.run_helper("run", "update", self.repo, run_id, "--token", token, "--set-json",
                        json.dumps({"selected_ids": ["R009"]}), expect=2)
        self.run_helper("run", "update", self.repo, run_id, "--token", token, "--set-json",
                        json.dumps({"scope": "."}), expect=2)

    def test_run_from_other_worktree_is_not_used(self):
        token = self.acquire()
        run_id = self.new_run(token)
        other = os.path.join(self.tmp, "other repo")
        os.makedirs(other)
        self.run_helper("run", "show", other, run_id, expect=5)
        _, lst = self.run_helper("run", "list", other, expect=0)
        self.assertEqual(lst["runs"], [])

    def test_path_escape_and_sensitive_files_refused(self):
        token = self.acquire()
        run_id = self.new_run(token)
        self.write(".env", "SECRET=1\n")
        self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b1",
                        "--files", "../outside.txt", expect=2)
        self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b2",
                        "--files", ".env", expect=2)
        snaps = os.path.join(self.state, "runs")
        for dirpath, _, files in os.walk(snaps):
            for name in files:
                with open(os.path.join(dirpath, name), "rb") as f:
                    self.assertNotIn(b"SECRET=1", f.read())


class BatchRecoveryTests(HelperCase):
    """Extraction: CheckoutPage.tsx -> new hooks/useCheckout.ts, callers updated."""

    SRC = "src/features/checkout/CheckoutPage.tsx"
    NEW = "src/features/checkout/hooks/useCheckout.ts"
    CALLER = "src/index.ts"

    def begin(self, token, run_id, batch="b1"):
        self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", batch,
                        "--findings", "R001", "--files", "modify:" + self.SRC, "create:" + self.NEW,
                        "modify:" + self.CALLER, expect=0)

    def apply_extraction(self):
        self.write(self.NEW, "export function useCheckout() { return {}; }\n")
        self.write(self.SRC, "import { useCheckout } from './hooks/useCheckout';\n"
                             "export function CheckoutPage() { useCheckout(); }\n")

    def test_interrupted_after_new_file_is_diagnosed_not_replayed(self):
        token = self.acquire()
        run_id = self.new_run(token)
        self.begin(token, run_id)
        self.write(self.NEW, "export function useCheckout() { return {}; }\n")
        self.run_helper("batch", "record", self.repo, run_id, "--token", token, "--batch", "b1", self.NEW,
                        expect=0)
        # crash here: source file not yet edited
        _, d = self.run_helper("diagnose", self.repo, run_id, expect=0)
        b = d["batches"]["b1"]
        states = {f["path"]: f["state"] for f in b["files"]}
        self.assertEqual(b["verdict"], "interrupted_partial")
        self.assertEqual(states[self.NEW], "post")
        self.assertEqual(states[self.SRC], "pre")
        # re-beginning the same batch is refused (no blind replay)
        _, out = self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b1",
                                 "--files", self.SRC, expect=2)
        self.assertIn("diagnose", out["error"])

    def test_unrecorded_partial_write_needs_inspection(self):
        token = self.acquire()
        run_id = self.new_run(token)
        self.begin(token, run_id)
        self.write(self.SRC, "// half-written\n")
        _, d = self.run_helper("diagnose", self.repo, run_id, expect=0)
        self.assertEqual(d["batches"]["b1"]["verdict"], "interrupted_needs_inspection")
        _, r = self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token, expect=4)
        self.assertEqual(self.read(self.SRC), "// half-written\n")
        self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token,
                        "--include-unrecorded", self.SRC, expect=0)
        self.assertEqual(self.read(self.SRC), "export function CheckoutPage() {}\n")

    def test_restore_returns_run_changes_and_removes_untouched_new_file(self):
        token = self.acquire()
        run_id = self.new_run(token)
        self.begin(token, run_id)
        self.apply_extraction()
        self.run_helper("batch", "end", self.repo, run_id, "--token", token, "--batch", "b1", expect=0)
        self.run_helper("batch", "mark", self.repo, run_id, "--token", token, "--batch", "b1", "--status",
                        "validated", "--checks-json", json.dumps({"cmd": "tsc --noEmit", "result": "pass"}),
                        expect=0)
        _, dry = self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--dry-run", expect=0)
        self.assertEqual(dry["conflicts"], [])
        self.assertTrue(os.path.exists(os.path.join(self.repo, self.NEW)), "dry-run must not change files")
        self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token, expect=0)
        self.assertEqual(self.read(self.SRC), "export function CheckoutPage() {}\n")
        self.assertFalse(os.path.exists(os.path.join(self.repo, self.NEW)))
        _, d = self.run_helper("diagnose", self.repo, run_id, expect=0)
        self.assertEqual(d["batches"]["b1"]["verdict"], "restored")

    def test_restore_keeps_user_edits_made_after_the_batch(self):
        token = self.acquire()
        run_id = self.new_run(token)
        self.begin(token, run_id)
        self.apply_extraction()
        self.run_helper("batch", "end", self.repo, run_id, "--token", token, "--batch", "b1", expect=0)
        user_hook = "export function useCheckout() { return { userAdded: true }; }\n"
        self.write(self.NEW, user_hook)  # user keeps working on the extracted file
        _, out = self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token, expect=4)
        self.assertFalse(out["applied"])
        self.assertEqual(self.read(self.NEW), user_hook)
        # partial restore: separable files return, the user-edited one is untouched
        _, out = self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token,
                                 "--partial", expect=0)
        self.assertEqual(self.read(self.SRC), "export function CheckoutPage() {}\n")
        self.assertEqual(self.read(self.NEW), user_hook)
        self.assertEqual([c["path"] for c in out["conflicts"]], [self.NEW])

    def test_pre_existing_uncommitted_user_change_is_the_baseline(self):
        self.write(self.CALLER, "// user's uncommitted work\n")
        token = self.acquire()
        run_id = self.new_run(token)
        self.begin(token, run_id)
        self.write(self.CALLER, "// user's uncommitted work\n// rapih-in updated import\n")
        self.run_helper("batch", "end", self.repo, run_id, "--token", token, "--batch", "b1", expect=0)
        self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token, expect=0)
        self.assertEqual(self.read(self.CALLER), "// user's uncommitted work\n")

    def test_missing_snapshot_is_reported_not_guessed(self):
        token = self.acquire()
        run_id = self.new_run(token)
        self.begin(token, run_id)
        self.apply_extraction()
        self.run_helper("batch", "end", self.repo, run_id, "--token", token, "--batch", "b1", expect=0)
        key = self.run_helper("repo-key", self.repo)[1]["key"]
        shutil.rmtree(os.path.join(self.state, "runs", key, run_id, "snapshots", "b1", "pre"))
        _, out = self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token, expect=4)
        reasons = {c["path"]: c["reason"] for c in out["conflicts"]}
        self.assertIn("snapshot missing", reasons[self.SRC])
        self.assertTrue(os.path.exists(os.path.join(self.repo, self.NEW)))

    def test_move_with_existing_target_collision_is_restorable(self):
        self.write("src/shared/Button.tsx", "// existing target owned by someone\n")
        self.write("src/features/checkout/Button.tsx", "// feature button\n")
        token = self.acquire()
        run_id = self.new_run(token)
        _, out = self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b1",
                                 "--files", "move:src/features/checkout/Button.tsx=>src/shared/Button.tsx",
                                 "--expect", "src/shared/Button.tsx=missing", expect=4)
        self.assertEqual(out["path"], "src/shared/Button.tsx")

    def test_move_restore(self):
        self.write("src/features/checkout/Price.ts", "export const price = 1;\n")
        token = self.acquire()
        run_id = self.new_run(token)
        self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b1",
                        "--files", "move:src/features/checkout/Price.ts=>src/shared/price/Price.ts",
                        "--expect", "src/shared/price/Price.ts=missing", expect=0)
        os.makedirs(os.path.join(self.repo, "src", "shared", "price"))
        os.replace(os.path.join(self.repo, "src/features/checkout/Price.ts"),
                   os.path.join(self.repo, "src/shared/price/Price.ts"))
        self.run_helper("batch", "end", self.repo, run_id, "--token", token, "--batch", "b1", expect=0)
        self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token, expect=0)
        self.assertEqual(self.read("src/features/checkout/Price.ts"), "export const price = 1;\n")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "src/shared/price/Price.ts")))

    def test_writes_need_current_lock_token(self):
        token = self.acquire()
        run_id = self.new_run(token)
        self.run_helper("lock", "release", self.repo, "--token", token, expect=0)
        self.run_helper("batch", "begin", self.repo, run_id, "--token", token, "--batch", "b1",
                        "--files", self.SRC, expect=3)
        self.run_helper("restore", self.repo, run_id, "--batch", "b1", "--token", token, expect=3)
        # resume: reacquire, same run continues
        token2 = self.acquire(run_id)
        self.run_helper("batch", "begin", self.repo, run_id, "--token", token2, "--batch", "b1",
                        "--files", self.SRC, expect=0)

    def test_checkpoint_survives_leftover_temp_file(self):
        token = self.acquire()
        run_id = self.new_run(token)
        key = self.run_helper("repo-key", self.repo)[1]["key"]
        rd = os.path.join(self.state, "runs", key, run_id)
        with open(os.path.join(rd, ".tmp-123-dead"), "w") as f:
            f.write("{partial")
        _, show = self.run_helper("run", "show", self.repo, run_id, expect=0)
        self.assertEqual(show["checkpoint"]["run_id"], run_id)


class FingerprintTests(HelperCase):
    def test_fingerprint_ignores_order_case_and_separators(self):
        _, a = self.run_helper("fingerprint", "--kind", "mixed-responsibility", "--path",
                               "src\\Features\\Checkout\\CheckoutPage.tsx", "--symbol", "submitOrder",
                               "--symbol", "CheckoutPage", expect=0)
        _, b = self.run_helper("fingerprint", "--kind", "Mixed-Responsibility", "--path",
                               "src/features/checkout/CheckoutPage.tsx", "--symbol", "CheckoutPage",
                               "--symbol", "submitOrder", expect=0)
        _, c = self.run_helper("fingerprint", "--kind", "misplaced-file", "--path",
                               "src/features/checkout/CheckoutPage.tsx", expect=0)
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertNotEqual(a["fingerprint"], c["fingerprint"])


if __name__ == "__main__":
    unittest.main()
