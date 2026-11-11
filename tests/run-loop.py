#!/usr/bin/env python3
"""Exercise run-loop helpers in disposable repositories, never the real HOME."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1] / "home/skills/run-loop"


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="run-loop-test-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.run_cmd("git", "init", "-q")
        self.write("tracked.txt", "initial\n")
        self.write(".gitignore", "ignored/\n.loop/\n")
        self.run_cmd("git", "add", ".")
        # Only this disposable fixture gets commits; the user's repository is untouched.
        self.run_cmd("git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                     "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                     "commit", "-qm", "fixture")
        self.base = Path(self.temp.name) / "base.snap"

    def run_cmd(self, *args):
        return subprocess.check_output(args, cwd=self.repo, text=True)

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def snapshot(self):
        self.base.write_text(self.run_cmd("bash", str(SKILL / "scripts/tree_snapshot.sh"), "take"))

    def changed(self):
        return set(self.run_cmd("bash", str(SKILL / "scripts/tree_snapshot.sh"),
                                "changed", str(self.base)).splitlines())

    def test_changes_and_read_only_operation(self):
        self.snapshot()
        self.write("tracked.txt", "updated\n")
        self.write("space name.txt", "new\n")
        before = self.run_cmd("git", "status", "--porcelain=v1", "-uall")
        self.assertEqual(self.changed(), {"tracked.txt", "space name.txt"})
        self.assertEqual(self.run_cmd("git", "status", "--porcelain=v1", "-uall"), before)

    def test_existing_dirty_file_changes_and_restoration(self):
        self.write("tracked.txt", "user work\n")
        self.snapshot()
        self.assertEqual(self.changed(), set())
        self.write("tracked.txt", "different work\n")
        self.assertEqual(self.changed(), {"tracked.txt"})
        self.write("tracked.txt", "initial\n")
        self.assertEqual(self.changed(), {"tracked.txt"})

    def test_index_change_without_content_change(self):
        self.write("tracked.txt", "updated\n")
        self.snapshot()
        self.run_cmd("git", "add", "tracked.txt")
        self.assertEqual(self.changed(), {"!INDEX"})

    def test_deleted_file_and_symlink_target(self):
        self.write("target-a", "a")
        self.write("target-b", "b")
        link = self.repo / "link"
        link.symlink_to("target-a")
        self.snapshot()
        link.unlink()
        link.symlink_to("target-b")
        (self.repo / "tracked.txt").unlink()
        self.assertEqual(self.changed(), {"tracked.txt", "link"})

    def test_executable_change_on_already_dirty_file(self):
        self.write("tracked.txt", "updated\n")
        self.snapshot()
        (self.repo / "tracked.txt").chmod(0o755)
        self.assertEqual(self.changed(), {"tracked.txt"})

    def test_ignored_grading_inputs_but_not_logs(self):
        self.write(".loop/task/2-spec.md", "approved spec")
        self.snapshot()
        self.write(".loop/task/2-spec.md", "changed spec")
        self.write(".loop/task/logs/run.jsonl", "log")
        self.write("ignored/cache", "cache")
        self.assertEqual(self.changed(), {".loop/task/2-spec.md"})

    def test_unborn_repository(self):
        empty = self.repo / "unborn"
        empty.mkdir()
        self.repo = empty
        self.run_cmd("git", "init", "-q")
        self.snapshot()
        self.write("first file", "new")
        self.assertEqual(self.changed(), {"first file"})

    def test_non_repository_fails(self):
        result = subprocess.run(["bash", str(SKILL / "scripts/tree_snapshot.sh"), "take"],
                                cwd=self.temp.name, text=True, capture_output=True)
        self.assertEqual(result.returncode, 3)
        self.assertIn("Git 저장소가 아닙니다", result.stderr)


class PaneTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("jq"), "jq is optional")
    def test_codex_events(self):
        events = [
            {"type": "thread.started", "thread_id": "test-thread"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "review complete"}},
            {"type": "item.started", "item": {"type": "command_execution", "command": "git diff"}},
            {"type": "item.completed", "item": {"type": "command_execution", "exit_code": 1}},
            {"type": "turn.failed", "error": {"message": "denied"}},
            {"type": "turn.completed"},
            {"type": "future.event"},
        ]
        result = subprocess.run(["jq", "-r", "-f", str(SKILL / "scripts/pane-filter.jq")],
                                input="\n".join(map(json.dumps, events)), text=True,
                                capture_output=True, check=True)
        self.assertEqual(result.stdout.splitlines(), ["[start] thread=test-thread", "review complete",
                         "[command] git diff", "[exit] 1", "[failed] denied", "[done]"])


if __name__ == "__main__":
    unittest.main()
