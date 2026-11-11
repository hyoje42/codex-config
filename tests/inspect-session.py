#!/usr/bin/env python3
"""Behavioral checks using isolated rollout fixtures, never the real home."""
import contextlib
import gzip
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "home/skills/inspect-session/scripts/session_digest.py"
SPEC = importlib.util.spec_from_file_location("session_digest", SCRIPT)
digest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(digest)
SID = "11111111-1111-4111-8111-111111111111"
OTHER = "11111111-1111-4111-8111-222222222222"


def record(kind, **payload):
    return {"timestamp": "2026-11-11T01:00:00Z", "type": kind, "payload": payload}


def event(kind, **payload):
    return record("event_msg", type=kind, **payload)


def message(role, text, **extra):
    return record("response_item", type="message", role=role,
                  content=[{"type": "input_text", "text": text}], **extra)


class DigestTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)

    def write(self, rows, sid=SID, archived=False, compressed=False):
        directory = self.home / ("archived_sessions" if archived else "sessions/2026/11/11")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"rollout-2026-11-11T01-00-00-{sid}.jsonl"
        data = "\n".join(json.dumps(row) for row in rows) + "\n"
        if compressed:
            path = path.with_suffix(".jsonl.gz")
            with gzip.open(path, "wt") as stream:
                stream.write(data)
        else:
            path.write_text(data)
        return path

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = digest.main(["--home", str(self.home), *args])
        return code, out.getvalue(), err.getvalue()

    def test_locate_title_prefix_archive_gzip_and_self(self):
        path = self.write([record("session_meta", id=SID, cwd=str(Path.cwd()))], compressed=True)
        other = self.write([record("session_meta", id=OTHER, cwd="/different")], sid=OTHER, archived=True)
        (self.home / "session_index.jsonl").write_text(
            json.dumps({"id": SID, "thread_name": "old title"}) + "\n" +
            json.dumps({"id": SID, "thread_name": "Digest work"}) + "\n")
        self.assertEqual(digest.Catalog(self.home).resolve("@Digest work [123]"), [path])
        self.assertEqual(digest.Catalog(self.home).resolve(OTHER), [other])
        self.assertEqual(self.cli("locate", "11111111")[0], 2)
        code, out, _ = self.cli("--self", SID, "locate", "--here")
        self.assertEqual(code, 0)
        self.assertIn("현재 세션", out)
        self.assertNotIn(OTHER, out)
        self.assertNotIn("old title", out)
        self.assertEqual(self.cli("locate", "missing")[0], 2)

    def test_modern_duplicate_messages_and_injected_context(self):
        path = self.write([
            record("session_meta", id=SID), event("task_started", turn_id="one"),
            message("developer", "injected instruction"),
            message("user", "# AGENTS.md instructions: not the actual goal"),
            message("user", "Fix the parser"),
            event("item_completed", item={"type": "UserMessage", "content": [{"type": "Text", "text": "Fix the parser"}]}),
            event("item_completed", item={"type": "AgentMessage", "content": [{"text": "Done"}]}),
            message("assistant", "Done"), event("task_complete", last_agent_message="Done"),
        ])
        self.assertEqual([(e["kind"], e["text"]) for e in digest.Session(path).events],
                         [("U", "Fix the parser"), ("A", "Done")])
        _, out, _ = self.cli("overview", SID)
        self.assertNotIn("injected", out)
        self.assertIn("실제 실행 여부는 알 수 없습니다", out)

    def test_legacy_compaction_rollback_and_stable_line_ids(self):
        path = self.write([
            event("task_started", turn_id="one"), message("user", "original goal"),
            event("user_message", message="original goal"),
            record("response_item", type="reasoning", summary=[{"text": "recorded summary"}], encrypted_content="opaque"),
            message("assistant", "first answer"), event("agent_message", message="first answer"),
            record("compacted", message="retained summary", replacement_history=[{"text": "do not duplicate"}]),
            event("task_started", turn_id="two"), event("user_message", message="discarded goal"),
            message("assistant", "discarded answer"), event("thread_rolled_back", num_turns=1),
            event("task_started", turn_id="three"), event("user_message", message="new goal"),
        ])
        self.assertEqual([e["text"] for e in digest.Session(path).active() if e["kind"] == "U"],
                         ["original goal", "new goal"])
        self.assertNotIn("discarded answer", self.cli("overview", SID)[1])
        _, out, _ = self.cli("timeline", SID, "--no-rewound")
        self.assertIn("#7", out)
        self.assertNotIn("original goal", out)
        self.assertNotIn("discarded goal", out)
        plain = self.cli("timeline", SID, "--full")[1]
        thinking = self.cli("timeline", SID, "--full", "--thinking")[1]
        self.assertIn("#5", plain)
        self.assertIn("#5", thinking)
        self.assertNotIn("#4", plain)
        self.assertIn("#4", thinking)
        self.assertNotIn("opaque", thinking)
        shown = self.cli("show", SID, "3-5")[1]
        self.assertIn("original goal", shown)
        self.assertIn("first answer", shown)

    def test_tools_results_approval_answers_and_patch_paths(self):
        path = self.write([
            record("response_item", type="function_call", call_id="a", name="exec_command", arguments='{"cmd":"false"}'),
            record("response_item", type="function_call_output", call_id="a", output="Process exited with code 1\nfailed"),
            record("response_item", type="custom_tool_call", call_id="b", name="apply_patch", input="*** Begin Patch\n*** Update File: src/app.py\n*** End Patch"),
            record("response_item", type="custom_tool_call_output", call_id="b", output="Success"),
            record("response_item", type="function_call", call_id="c", name="request_user_input", arguments="{}"),
            record("response_item", type="function_call_output", call_id="c", output={"answers": {"decision": "wait"}}),
            record("response_item", type="custom_tool_call", call_id="pending", name="exec", input="long task"),
        ])
        self.assertEqual(len(digest.Session(path).events), 4)
        out = self.cli("timeline", SID)[1]
        self.assertIn("failed", out)
        self.assertIn("wait", out)
        self.assertNotIn("Success", out)
        out = self.cli("show", SID, "1")[1]
        self.assertIn('"cmd": "false"', out)
        self.assertIn("Process exited", out)
        out = self.cli("overview", SID)[1]
        self.assertIn("src/app.py", out)
        self.assertIn("결과가 없는 호출: #7", out)
        self.assertIn("#1", self.cli("grep", SID, "FAILED", "-i")[1])

    def test_redaction_precedes_clipping_and_grep_windows(self):
        secret = "sk-" + "a" * 80
        self.write([message("user", secret + " findme"), message("assistant", '{"api_key":"private-value"}')])
        out = self.cli("timeline", SID, "--width", "12")[1]
        self.assertNotIn("sk-", out)
        self.assertNotIn("private", out)
        out = self.cli("grep", SID, "findme")[1]
        self.assertIn("[REDACTED]", out)
        self.assertNotIn("aaaa", out)
        self.assertNotIn("private-value", self.cli("show", SID, "2")[1])

    def test_unknown_partial_records_and_invalid_inputs(self):
        path = self.write([message("user", "visible"), record("future_event", foo=True),
                           event("item_completed", item="unsupported shape")])
        with path.open("a") as stream:
            stream.write('{"unfinished":')
        code, out, err = self.cli("overview", SID)
        self.assertEqual(code, 0)
        self.assertIn("visible", out)
        self.assertIn("future_event", err)
        self.assertIn("item_completed", err)
        self.assertIn("JSON", err)
        self.assertEqual(self.cli("grep", SID, "[")[0], 2)
        self.assertEqual(self.cli("show", SID, "9-1")[0], 2)
        self.assertEqual(self.cli("show", SID, "999")[0], 2)

    def test_structured_commands_and_file_changes(self):
        self.write([
            event("item_completed", item={"type": "CommandExecution", "id": "nested", "command": "false",
                                           "exit_code": 2, "aggregated_output": "oops"}),
            event("item_completed", item={"type": "FileChange", "changes": [{"path": "a.txt"}], "status": "completed"}),
        ])
        out = self.cli("overview", SID)[1]
        self.assertIn("#1 command_execution", out)
        self.assertIn("구조화된 파일 변경 기록: #2", out)
        self.assertIn("a.txt", self.cli("show", SID, "2")[1])

    def test_read_only(self):
        self.write([record("session_meta", id=SID), message("user", "hello"), message("assistant", "world")])
        def snapshot():
            return {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.home.rglob("*") if p.is_file()}
        before = snapshot()
        for args in (("locate",), ("overview", SID), ("timeline", SID), ("show", SID, "2"), ("grep", SID, "hello")):
            self.assertEqual(self.cli(*args)[0], 0)
        self.assertEqual(before, snapshot())

    def test_failure_detection_respects_status_before_output_text(self):
        cases = [
            ("except ValueError:\n    pass", False),
            ("except sqlite3.Error:\n    pass", False),
            ({"exit_code": 0, "output": "Error: quoted source"}, False),
            ({"metadata": {"exit_code": 0}, "output": "permission denied"}, False),
            (json.dumps({"metadata": {"exit_code": 0}, "output": "Error: quoted source"}), False),
            ({"isError": False, "output": "Error: example"}, False),
            ({"error": None, "output": "Error: example"}, False),
            ("Process exited with code 0\nFinal output:\nError: example", False),
            ({"exit_code": 2, "output": "ordinary text"}, True),
            ({"exit_code": -9, "output": ""}, True),
            ({"isError": True, "output": "ordinary text"}, True),
            (json.dumps({"error": "tool unavailable"}), True),
            ("Process exited with code 1\nFinal output:\nfailed", True),
            ("Error: tool unavailable", True),
            ("Tool execution failed: unavailable", True),
            ("some source\n" * 200 + "Error: example", False),
        ]
        for result, expected in cases:
            with self.subTest(result=str(result)[:120]):
                self.assertEqual(digest.failed(result), expected)

    def test_source_code_is_not_expanded_or_reported_as_failure(self):
        self.write([
            record("response_item", type="function_call", call_id="read", name="exec_command", arguments='{"cmd":"cat app.py"}'),
            record("response_item", type="function_call_output", call_id="read", output="except sqlite3.Error:\n    pass"),
        ])
        self.assertNotIn("except sqlite3", self.cli("timeline", SID)[1])
        self.assertNotIn("최근 도구 실패", self.cli("overview", SID)[1])
        self.assertIn("except sqlite3", self.cli("timeline", SID, "--results")[1])

    def test_patch_outcomes_are_retained_and_summarized_without_diff(self):
        path = self.write([
            event("patch_apply_end", call_id="ok", success=True, changes={
                "a.py": {"type": "update", "unified_diff": "PRIVATE_DIFF_BODY", "move_path": "renamed.py"}}),
            event("patch_apply_end", call_id="bad", success=False,
                  changes={"bad.py": {"type": "add", "content": "PRIVATE_FILE_BODY"}}, stderr="patch rejected"),
            event("patch_apply_end", call_id="unknown", changes={"unknown.py": {"type": "delete"}}),
        ])
        session = digest.Session(path)
        self.assertEqual(len(session.events), 3)
        self.assertFalse(session.warnings)
        code, out, _ = self.cli("overview", SID)
        self.assertEqual(code, 0)
        self.assertIn("패치 적용 성공", out)
        self.assertIn("패치 적용 실패", out)
        self.assertIn("패치 결과 불명", out)
        self.assertIn("renamed.py", out)
        self.assertIn("bad.py", out)
        self.assertNotIn("PRIVATE_DIFF_BODY", out)
        timeline = self.cli("timeline", SID)[1]
        self.assertNotIn("PRIVATE_DIFF_BODY", timeline)
        self.assertNotIn("PRIVATE_FILE_BODY", timeline)
        self.assertIn("patch rejected", self.cli("show", SID, "2")[1])
        self.assertIn("PRIVATE_DIFF_BODY", self.cli("show", SID, "1")[1])

    def test_all_file_lists_report_omitted_count(self):
        self.write([
            record("response_item", type="custom_tool_call", name="apply_patch", call_id="attempt",
                   input="*** Add File: x.py\n*** Add File: y.py\n*** Add File: z.py"),
            event("patch_apply_end", call_id="ok", success=True,
                  changes={f"{i}.py": {"type": "delete"} for i in range(3)}),
            event("item_completed", item={"type": "FileChange", "changes": []}),
            event("item_completed", item={"type": "FileChange", "changes": []}),
        ])
        out = self.cli("overview", SID, "--files", "1")[1]
        self.assertGreaterEqual(out.count("외 2개"), 2)
        self.assertIn("외 1개", out)

    def test_state_changing_commands_are_listed_without_read_only_git(self):
        def shell(call_id, cmd, code=0):
            return [record("response_item", type="function_call", name="exec_command", call_id=call_id,
                           arguments=json.dumps({"cmd": cmd})),
                    record("response_item", type="function_call_output", call_id=call_id,
                           output=json.dumps({"output": "", "metadata": {"exit_code": code}}))]
        self.write([
            *shell("a", "git status && git commit -F - <<'EOF'\nfix: avoid git push race\nEOF"),
            *shell("b", "git -C sub push origin main", code=1),
            *shell("c", "git merge-base a b; git stash list; git tag --points-at HEAD; git checkout-index -f x"),
            *shell("d", "codex-sync-to-home --dry-run"),
            *shell("e", "codex-sync-to-home"),
        ])
        out = self.cli("overview", SID)[1]
        section = out.split("git·sync 명령 후보를 포함한 셸 호출", 1)[1].split("\n\n", 1)[0]
        self.assertIn("호출 종료 0  git status && git commit -F - <<'EOF'", section)
        self.assertNotIn("race", section)
        self.assertIn("호출 종료 1  git -C sub push origin main", section)
        self.assertIn("호출 종료 0  codex-sync-to-home", section)
        for read_only in ("merge-base", "stash list", "points-at", "checkout-index", "--dry-run"):
            self.assertNotIn(read_only, section)

    def test_state_ops_ignore_patch_and_quoted_command_text(self):
        path = self.write([
            record("response_item", type="custom_tool_call", name="apply_patch", call_id="patch",
                   input="*** Begin Patch\n*** Add File: guide.md\n+Run git push origin main\n*** End Patch"),
            record("response_item", type="function_call", name="exec_command", call_id="print",
                   arguments=json.dumps({"cmd": "printf '%s\\n' 'git push origin main; git reset --hard'"})),
            record("response_item", type="function_call", name="exec_command", call_id="quoted",
                   arguments=json.dumps({"cmd": 'echo "text\ngit push origin main\ntext"'})),
        ])
        self.assertEqual(digest.state_ops(digest.Session(path).active()), [])

    def test_state_ops_detect_shell_wrappers_options_and_word_hashes(self):
        commands = [
            "curl http://x/#a; git push",
            "echo a#b && git push",
            "if true; then git commit -m x; fi",
            "for r in a b; do git push origin $r; done",
            "{ git push; }",
            "! git push",
            "sudo -u me git push",
            "sudo -g staff git push",
            "sudo -E -u me -g staff env -i FOO=1 command -- git push",
            "env FOO=1 git push",
            "command -- git push",
            "exec git push",
            "nohup git push",
            "while git pull; do true; done",
            "until git pull; do true; done",
            "if false; then true; elif git pull; then true; else git push; fi",
            "time git push",
            "git --no-pager -C dir push",
            "git -c user.name=me --git-dir repo --work-tree dir --namespace ns --exec-path bin push",
            "git --git-dir=repo push",
            "git pull --rebase",
            "bash ./codex-sync-to-home",
            "sh ./codex-sync-to-home",
            "zsh ./codex-sync-to-home",
            "echo hi # git status\ngit push",
            'git push # "unfinished quote',
            'echo hi # "unfinished quote\ngit push',
        ]
        for cmd in commands:
            with self.subTest(cmd=cmd):
                path = self.write([
                    record("response_item", type="function_call", name="exec_command", call_id="a",
                           arguments=json.dumps({"cmd": cmd})),
                ])
                self.assertEqual(len(digest.state_ops(digest.Session(path).active())), 1)

    def test_state_ops_ignore_comments_and_wrapped_read_only_commands(self):
        commands = [
            "echo hi # git push",
            "echo hi;# git push",
            "echo hi # comment; git push",
            "# git push\necho hi",
            "env FOO=1 git status",
            "sudo -u me git --no-pager status",
            "git --git-dir push status",
            "git --work-tree push status",
            "git --namespace push status",
            "git --exec-path push status",
            "bash ./codex-sync-to-home --dry-run",
            "echo '#literal; git push'",
        ]
        for cmd in commands:
            with self.subTest(cmd=cmd):
                path = self.write([
                    record("response_item", type="function_call", name="exec_command", call_id="a",
                           arguments=json.dumps({"cmd": cmd})),
                ])
                self.assertEqual(digest.state_ops(digest.Session(path).active()), [])

    def test_state_ops_preserve_conditions_and_do_not_infer_completion(self):
        cases = [
            ("false && git push origin main; true", {"exit_code": 0}, "호출 종료 0"),
            ("git push origin main", {"session_id": 123, "exit_code": None}, "백그라운드 실행"),
            ("git push origin main", "Process running with session ID 123", "백그라운드 실행"),
            ("git push origin main", {"output": "", "isError": False}, "완료 미확인"),
            ("git push origin main", "Process exited with code 1\nFinal output:\nfailed", "호출 종료 1"),
        ]
        for cmd, result, expected in cases:
            with self.subTest(result=result):
                self.write([
                    record("response_item", type="function_call", name="exec_command", call_id="a",
                           arguments=json.dumps({"cmd": cmd})),
                    record("response_item", type="function_call_output", call_id="a", output=result),
                ])
                section = self.cli("overview", SID)[1].split("git·sync 명령 후보를 포함한 셸 호출", 1)[1].split("\n\n", 1)[0]
                self.assertIn("개별 실행 여부는 미확인", section)
                self.assertIn(expected + "  " + cmd, section)
                self.assertNotIn("성공", section)

    def test_overview_limits_ops_independently_from_files(self):
        self.write([
            record("response_item", type="custom_tool_call", name="apply_patch", call_id="patch",
                   input="*** Add File: a.py\n*** Add File: b.py\n*** Add File: c.py"),
            *[record("response_item", type="function_call", name="exec_command", call_id=f"op-{i}",
                     arguments=json.dumps({"cmd": f"git push origin branch-{i:02d}"})) for i in range(17)],
        ])
        for options, limit, file_count in [
                ((), 15, 3),
                (("--files", "1"), 15, 1),
                (("--ops", "2"), 2, 3),
                (("--files", "1", "--ops", "2"), 2, 1),
                (("--ops", "17"), 17, 3)]:
            with self.subTest(options=options):
                code, out, _ = self.cli("overview", SID, *options)
                self.assertEqual(code, 0)
                section = out.split("git·sync 명령 후보를 포함한 셸 호출", 1)[1].split("\n\n", 1)[0]
                self.assertEqual(section.count("git push origin branch-"), limit)
                self.assertIn("git push origin branch-16", section)
                self.assertIn(f"git push origin branch-{17 - limit:02d}", section)
                if limit < 17:
                    self.assertNotIn(f"git push origin branch-{16 - limit:02d}", section)
                    self.assertIn(f"… 이전 호출 {17 - limit}개 생략", section)
                else:
                    self.assertNotIn("생략", section)
                self.assertIn("a.py", out)
                self.assertEqual("b.py" in out, file_count > 1)
                self.assertEqual("c.py" in out, file_count > 1)


if __name__ == "__main__":
    unittest.main()
