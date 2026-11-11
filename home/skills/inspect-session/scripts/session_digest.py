#!/usr/bin/env python3
"""Read-only digest of Codex rollout JSONL files. Standard library only."""

import argparse
import gzip
import json
import os
import re
import shlex
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


KINDS = {"U": "user", "A": "assistant", "T": "tool", "P": "peer",
         "C": "compact", "F": "file", "N": "notice", "K": "summary"}
UUID = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.I)
SECRETS = [
    re.compile(r"sk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r'''(?i)["']?\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)["']?\s*[:=]\s*(?:"[^"\n]*"|'[^'\n]*'|[^\s,;}]+)'''),
]


def redact(value):
    text = str(value)
    for pattern in SECRETS:
        text = pattern.sub("[REDACTED]", text)
    # Keep terminal control sequences from replaying from untrusted transcripts.
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)


def display(value, width=0, single=False):
    text = redact(value).strip()
    if single:
        text = re.sub(r"\s+", " ", text)
    if width and len(text) > width:
        return text[:width] + f" …(+{len(text) - width}자)"
    return text


def emit(value=""):
    print(redact(value))


def block_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(filter(None, (block_text(part) for part in value)))
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if value.get("type") in {"image", "input_image", "Image", "LocalImage"}:
            return "[image]"
        if "content" in value:
            return block_text(value["content"])
    return ""


def as_text(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def records(path, warnings=None):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("not an object")
            except ValueError:
                if warnings is not None:
                    warnings["잘못되었거나 아직 기록 중인 JSON 줄"] += 1
                continue
            yield number, record


def metadata(path):
    for number, record in records(path):
        if record.get("type") == "session_meta":
            payload = record.get("payload")
            if isinstance(payload, dict):
                return payload
        if number >= 20:
            break
    return {}


def file_id(path):
    match = UUID.search(path.name)
    return match.group(1).lower() if match else path.name.removesuffix(".gz").removesuffix(".jsonl")


class Catalog:
    def __init__(self, home):
        self.home = home
        self.titles = {}
        index = home / "session_index.jsonl"
        if index.is_file():
            for _, record in records(index):
                if record.get("id") and isinstance(record.get("thread_name"), str):
                    self.titles[record["id"]] = record["thread_name"]
        self._paths = None

    def paths(self):
        if self._paths is None:
            paths = set()
            for directory in ("sessions", "archived_sessions"):
                root = self.home / directory
                paths.update(p for p in root.rglob("*.jsonl") if p.is_file())
                paths.update(p for p in root.rglob("*.jsonl.gz") if p.is_file())
            # Prefer the uncompressed copy only when both share the same path.
            self._paths = sorted(p for p in paths if p.suffix != ".gz" or p.with_suffix("") not in paths)
        return self._paths

    def resolve(self, query):
        path = Path(query).expanduser()
        if path.is_file() and (path.name.endswith(".jsonl") or path.name.endswith(".jsonl.gz")):
            return [path.resolve()]
        needle = re.sub(r"\s+\[[^\]]*\]\s*$", "", query.strip()).lstrip("@").casefold()
        if not needle:
            return []
        paths = self.paths()
        exact_id = [p for p in paths if file_id(p).casefold() == needle]
        prefix = [p for p in paths if file_id(p).casefold().startswith(needle)]
        exact_title = [p for p in paths if self.titles.get(file_id(p), "").casefold() == needle]
        partial_title = [p for p in paths if needle in self.titles.get(file_id(p), "").casefold()]
        return exact_id or prefix or exact_title or partial_title


def grouped_records(path, warnings=None):
    """Turn epochs let canonical UI messages replace duplicated model messages."""
    epoch = 0
    for number, record in records(path, warnings):
        payload = record.get("payload", {})
        if not isinstance(payload, dict):
            if warnings is not None:
                warnings["지원하지 않는 payload"] += 1
            continue
        if record.get("type") == "event_msg" and payload.get("type") in {"task_started", "turn_started"}:
            epoch += 1
        yield epoch, number, record, payload


def injected(text):
    return text.lstrip().startswith(("# AGENTS.md instructions", "<environment_context>",
                                    "<INSTRUCTIONS>", "<permissions instructions>", "<skill>"))


def failed(result):
    # Legacy tool results often serialize the entire result envelope as JSON.
    if isinstance(result, str):
        try:
            decoded = json.loads(result)
        except ValueError:
            decoded = None
        if isinstance(decoded, dict):
            result = decoded
    if isinstance(result, dict):
        evidence = []
        for key in ("isError", "error"):
            if key in result:
                evidence.append(bool(result[key]))
        metadata_value = result.get("metadata")
        metadata_value = metadata_value if isinstance(metadata_value, dict) else {}
        code = result.get("exit_code")
        if type(code) is not int:
            code = metadata_value.get("exit_code")
        if type(code) is int:
            evidence.append(code != 0)
        if evidence:
            return any(evidence)
        text = result.get("output")
        text = text if isinstance(text, str) else block_text(result.get("content"))
    else:
        text = as_text(result)
    # Recognize the shell tool's status header, never status-like source text
    # inside its Final output section. Explicit success overrides quoted errors.
    for line in text.splitlines()[:12]:
        if line.strip() == "Final output:":
            break
        match = re.fullmatch(r"Process exited with code (-?\d+)", line.strip())
        if match:
            return int(match[1]) != 0
    # A conservative fallback for short, unstructured tool error messages.
    # In particular, neither ValueError: nor sqlite3.Error: is an error envelope.
    return len(text) <= 1000 and bool(re.match(
        r"\s*(?:Error:|tool execution failed\b|rejected by user\b|permission denied\b)", text, re.I))


SHELL_KEYWORDS = {"if", "then", "elif", "else", "while", "until", "do", "!", "{", "time"}
COMMAND_PREFIXES = {"sudo", "env", "command", "exec", "nohup"}
SHELLS = {"bash", "sh", "zsh"}
GIT_OPTIONS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def state_command(words):
    """Recognize command positions, never command names inside arguments."""
    words = [word[1:-1] if len(word) > 1 and word[0] == word[-1] and word[0] in "'\""
             else word for word in words]
    while words:
        head = words[0]
        if re.match(r"^[A-Za-z_]\w*=", head) or head in SHELL_KEYWORDS:
            words = words[1:]
        elif head in COMMAND_PREFIXES:
            words = words[1:]
            while words and words[0].startswith("-"):
                takes_value = head == "sudo" and words[0] in {"-u", "-g"}
                words = words[2:] if takes_value else words[1:]
        elif Path(head).name in SHELLS and len(words) > 1 and not words[1].startswith("-"):
            words = words[1:]
        else:
            break
    if not words:
        return False
    name = Path(words[0]).name
    if name.endswith("sync-to-home"):
        return not any(flag in words[1:] for flag in ("--dry-run", "-n"))
    if name != "git":
        return False
    args = words[1:]
    while args and args[0].startswith("-"):
        args = args[2:] if args[0] in GIT_OPTIONS_WITH_ARG else args[1:]
    if not args:
        return False
    subcommand, rest = args[0], args[1:]
    if subcommand in {"commit", "push", "pull", "reset", "rebase", "merge", "cherry-pick",
                      "revert", "checkout", "switch", "restore", "clean", "rm", "mv"}:
        return True
    if subcommand == "stash":
        return not rest or rest[0] not in {"list", "show"}
    if subcommand == "tag":
        return bool(rest) and (not rest[0].startswith("-") or
                              rest[0] in {"-a", "-s", "-d", "-f", "--delete", "--force"})
    if subcommand == "submodule":
        return bool(rest) and rest[0] == "update"
    return subcommand == "branch" and bool(rest) and rest[0] in {"-d", "-D", "-m", "-M"}


def state_shell_call(command):
    """Conservative shell scan; retain the call's control flow, omit heredoc bodies.

    This is not a shell interpreter. Matches are candidates, never proof that
    a branch ran. Unsupported or unfinished quoting is not guessed.
    """
    headers, heredocs = [], []
    pending = ""
    found = False
    for line in command.splitlines():
        if heredocs:
            delimiter, strip_tabs = heredocs[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                heredocs.pop(0)
            continue
        pending += line
        if pending.endswith("\\"):
            pending = pending[:-1]
            continue
        lexer = shlex.shlex(pending, posix=False, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        # A shell comment starts at a word boundary, not inside a URL or argument.
        lexer.commenters = ""
        try:
            tokens = []
            for token in lexer:
                if token.startswith("#"):
                    break
                tokens.append(token)
        except ValueError:
            pending += "\n"
            continue
        headers.append(pending)
        pending = ""
        for index, token in enumerate(tokens[:-1]):
            if token == "<<":
                delimiter = tokens[index + 1]
                strip_tabs = delimiter.startswith("-")
                delimiter = delimiter[1:] if strip_tabs else delimiter
                if len(delimiter) > 1 and delimiter[0] == delimiter[-1] and delimiter[0] in "'\"":
                    delimiter = delimiter[1:-1]
                heredocs.append((delimiter, strip_tabs))
        words = []
        for token in tokens + [";"]:
            if token and all(char in ";&|()" for char in token):
                found = state_command(words) or found
                words = []
            else:
                words.append(token)
    if pending or heredocs:
        return ""
    return "\n".join(headers) if found else ""


def command_text(value):
    if isinstance(value, dict):
        value = value.get("cmd", value.get("command", ""))
    if isinstance(value, list):
        return " ".join(str(part) for part in value)
    return value if isinstance(value, str) else ""


def state_ops(events):
    """Shell calls containing candidate state operations, with call-level results."""
    ops = []
    for event in events:
        if event["kind"] != "T" or event.get("tool", "").rsplit(".", 1)[-1] not in {
                "exec_command", "shell_command", "shell", "local_shell_call", "command_execution"}:
            continue
        command = state_shell_call(command_text(event.get("input")))
        if command:
            ops.append((event, command))
    return ops


def shell_call_status(result):
    if result is None:
        return "결과 없음"
    if isinstance(result, str):
        try:
            decoded = json.loads(result)
        except ValueError:
            decoded = None
        if isinstance(decoded, dict):
            result = decoded
    if isinstance(result, dict):
        metadata = result.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        code = result.get("exit_code")
        if type(code) is not int:
            code = metadata.get("exit_code")
        if type(code) is int:
            return f"호출 종료 {code}"
        if result.get("session_id") is not None:
            return "백그라운드 실행"
        text = result.get("output")
        text = text if isinstance(text, str) else block_text(result.get("content"))
    else:
        text = as_text(result)
    for line in text.splitlines()[:12]:
        if line.strip() == "Final output:":
            break
        match = re.fullmatch(r"Process exited with code (-?\d+)", line.strip())
        if match:
            return f"호출 종료 {match[1]}"
        if re.fullmatch(r"Process running with session ID \S+", line.strip()):
            return "백그라운드 실행"
    return "호출 실패" if failed(result) else "완료 미확인"


def patch_paths(changes):
    paths = set(changes) if isinstance(changes, dict) else set()
    if isinstance(changes, dict):
        for change in changes.values():
            if isinstance(change, dict) and isinstance(change.get("move_path"), str):
                paths.add(change["move_path"])
    return paths


def patch_label(success):
    if success is True:
        return "패치 적용 성공"
    if success is False:
        return "패치 적용 실패"
    return "패치 결과 불명"


class Session:
    def __init__(self, path):
        self.path = path
        self.meta = {}
        self.events = []
        self.warnings = Counter()
        self.status = "불명"
        self.first_ts = None
        self.last_ts = None
        self.cwds = []
        before = self.path.stat()
        self._parse()
        after = self.path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            self.warnings["읽는 동안 기록이 바뀌었습니다. 필요한 구간을 다시 확인하세요"] += 1

    def _parse(self):
        # First pass stores only source preferences, not large tool outputs.
        user_sources = {}
        assistant_sources = set()
        for epoch, _, record, payload in grouped_records(self.path):
            kind = payload.get("type")
            if record.get("type") == "event_msg":
                if kind == "user_message":
                    user_sources[epoch] = max(user_sources.get(epoch, 0), 1)
                item = payload.get("item")
                if kind == "item_completed" and isinstance(item, dict) and item.get("type") == "UserMessage":
                    user_sources[epoch] = 2
            if record.get("type") == "response_item" and kind == "message" and payload.get("role") == "assistant":
                assistant_sources.add(epoch)

        calls = {}
        turn_ids = {}
        for epoch, number, record, payload in grouped_records(self.path, self.warnings):
            outer, kind = record.get("type"), payload.get("type")
            ts = record.get("timestamp")
            self.first_ts = self.first_ts or ts
            self.last_ts = ts or self.last_ts

            def add(event_kind, text, **extra):
                event = {"n": number, "kind": event_kind, "text": text, "ts": ts,
                         "epoch": epoch, "off": False, **extra}
                self.events.append(event)
                return event

            if outer == "session_meta":
                self.meta.update(payload)
            elif outer == "turn_context":
                cwd = payload.get("cwd")
                if cwd and cwd not in self.cwds:
                    self.cwds.append(cwd)
            elif outer == "compacted":
                add("C", payload.get("message") or "압축 경계가 기록되었으며 요약 본문은 없습니다.")
            elif outer == "response_item":
                if kind == "message":
                    role = payload.get("role")
                    text = block_text(payload.get("content"))
                    if role == "user" and not user_sources.get(epoch) and not injected(text):
                        add("P" if text.lstrip().startswith("<subagent_notification>") else "U", text)
                    elif role == "assistant" and text:
                        add("K" if payload.get("channel") == "analysis" else "A", text)
                elif kind in {"function_call", "custom_tool_call", "local_shell_call"}:
                    inp = payload.get("arguments", payload.get("input", payload.get("action", "")))
                    if isinstance(inp, str):
                        try:
                            inp = json.loads(inp)
                        except ValueError:
                            pass
                    event = add("T", "", tool=payload.get("name", kind), input=inp, result=None,
                                call_id=payload.get("call_id") or payload.get("id"))
                    calls[payload.get("call_id") or payload.get("id") or f"line:{number}"] = event
                elif kind in {"function_call_output", "custom_tool_call_output", "local_shell_call_output"}:
                    result = payload.get("output", "")
                    event = calls.get(payload.get("call_id") or payload.get("id"))
                    if event is None:
                        add("N", "대응 호출이 없는 도구 결과:\n" + as_text(result))
                    else:
                        # Some streaming tools append several result chunks to one call.
                        old = event.get("result")
                        event["result"] = result if old is None else as_text(old) + "\n" + as_text(result)
                elif kind == "reasoning":
                    text = block_text(payload.get("summary")) or block_text(payload.get("content"))
                    if text:
                        add("K", text)
                elif kind == "web_search_call":
                    add("T", "", tool=kind, input=payload.get("action", {}), result=payload.get("status"))
                elif kind not in {"additional_tools", "compaction"}:
                    self.warnings[f"지원하지 않는 response_item/{kind}"] += 1
            elif outer == "event_msg":
                if kind in {"task_started", "turn_started"}:
                    self.status = "턴 시작이 기록되었지만 완료 기록은 없습니다."
                    if payload.get("turn_id"):
                        turn_ids[payload["turn_id"]] = epoch
                elif kind in {"task_complete", "task_completed", "turn_complete", "turn_aborted"}:
                    self.status = f"마지막 턴 기록: {kind}"
                    if kind == "turn_aborted":
                        add("N", as_text(payload))
                elif kind == "user_message" and user_sources.get(epoch) == 1:
                    add("U", block_text(payload.get("message")))
                elif kind == "agent_message" and epoch not in assistant_sources:
                    add("A", block_text(payload.get("message")))
                elif kind == "patch_apply_end":
                    add("F", as_text(payload), patch=True, success=payload.get("success"),
                        changes=payload.get("changes"), call_id=payload.get("call_id"))
                elif kind == "item_completed":
                    item = payload.get("item")
                    if not isinstance(item, dict):
                        self.warnings["지원하지 않는 item_completed payload"] += 1
                        continue
                    item_kind = item.get("type")
                    if item_kind == "UserMessage" and user_sources.get(epoch) == 2:
                        add("U", block_text(item.get("content")))
                    elif item_kind == "AgentMessage" and epoch not in assistant_sources:
                        add("A", block_text(item.get("content")))
                    elif item_kind == "FileChange":
                        add("F", as_text(item))
                    elif item_kind == "CommandExecution":
                        # Reuse raw calls if this structured event carries their ID.
                        event = calls.get(item.get("id"))
                        result = {"output": item.get("aggregated_output", ""), "exit_code": item.get("exit_code")}
                        if event is None:
                            event = add("T", "", tool="command_execution",
                                        input={"command": item.get("command"), "cwd": item.get("cwd")}, result=result)
                            calls[item.get("id") or f"line:{number}"] = event
                        elif event.get("result") is None:
                            event["result"] = result
                    elif item_kind not in {"UserMessage", "AgentMessage", "Reasoning", "McpToolCall",
                                           "WebSearch", "ContextCompaction", "Plan"}:
                        self.warnings[f"지원하지 않는 item_completed/{item_kind}"] += 1
                elif kind == "thread_rolled_back":
                    count = payload.get("num_turns", 0)
                    if isinstance(count, int) and count > 0:
                        epochs = list(dict.fromkeys(e["epoch"] for e in self.events if e["kind"] == "U" and not e["off"]))
                        removed = set(epochs[-count:])
                        for event in self.events:
                            if event["epoch"] in removed:
                                event["off"] = True
                    add("N", as_text(payload))
                    self.status = "대화 되돌리기가 기록되었습니다."
                elif kind in {"thread_reverted", "thread_revert"}:
                    before = payload.get("before_turn_id") or payload.get("beforeTurnId")
                    if before in turn_ids:
                        for event in self.events:
                            if event["epoch"] >= turn_ids[before]:
                                event["off"] = True
                    else:
                        self.warnings["되돌리기 대상 턴을 해석하지 못했습니다"] += 1
                    add("N", as_text(payload))
                elif kind in {"error", "warning", "context_compacted"} or (kind or "").startswith("collab_"):
                    add("P" if (kind or "").startswith("collab_") else "N", as_text(payload))
                elif kind not in {"token_count", "thread_settings_applied", "user_message", "agent_message",
                                   "agent_reasoning", "agent_reasoning_raw_content", "agent_reasoning_section_break"}:
                    self.warnings[f"지원하지 않는 event_msg/{kind}"] += 1
            elif outer not in {"world_state", "token_usage_record"}:
                self.warnings[f"지원하지 않는 record/{outer}"] += 1

    def active(self):
        return [event for event in self.events if not event["off"]]


def time_text(value, tz):
    if not value:
        return "?"
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            return value + " (시간대 불명)"
        return date.astimezone(tz).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return str(value)


def print_candidates(paths, catalog, args, tz):
    count = 0
    for path in sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True):
        meta = metadata(path)
        if args.here and Path(meta.get("cwd") or "/__unknown__").resolve() != Path.cwd().resolve():
            continue
        sid = meta.get("id") or file_id(path)
        marker = " [현재 세션]" if sid == args.self_id else ""
        emit(f"- {sid}{marker}  {display(catalog.titles.get(sid, ''), 160, True)}")
        emit(f"  cwd: {display(meta.get('cwd', '?'), 240, True)}")
        emit(f"  기록 시작: {time_text(meta.get('timestamp'), tz)}")
        emit(f"  path: {path}")
        count += 1
        if count >= args.limit:
            break
    if count == 0:
        emit("표시할 로컬 세션 기록이 없습니다.")


def overview(session, catalog, args, tz):
    meta, events = session.meta, session.active()
    sid = meta.get("id") or file_id(session.path)
    emit(f"세션: {sid}" + (" [현재 세션]" if sid == args.self_id else ""))
    emit(f"제목: {catalog.titles.get(sid, '로컬 인덱스에 없음')}")
    emit(f"경로: {session.path}")
    emit(f"cwd: {meta.get('cwd', '?')}" + (f" → {', '.join(session.cwds)}" if session.cwds else ""))
    git = meta.get("git") or {}
    emit(f"시작 시 Git: branch={git.get('branch', '?')} HEAD={git.get('commit_hash', '?')}")
    emit(f"기록 기간: {time_text(session.first_ts, tz)} → {time_text(session.last_ts, tz)} ({tz.key})")
    emit(f"기록 상태: {session.status} 실제 실행 여부는 알 수 없습니다.")
    emit(f"출처: {as_text(meta.get('source', '?'))}")
    counts = Counter(e["kind"] for e in events)
    emit("이벤트: " + ", ".join(f"{KINDS[k]}={v}" for k, v in counts.items()))
    emit(f"되돌린 이벤트: {sum(e['off'] for e in session.events)}")
    tool_counts = Counter(e["tool"] for e in events if e["kind"] == "T")
    emit("도구: " + ", ".join(f"{k}={v}" for k, v in tool_counts.most_common(12)))
    paths = set()
    patches = [e for e in events if e.get("patch")]
    completed_calls = {e["call_id"] for e in patches if e.get("call_id")}
    for event in events:
        if (event["kind"] == "T" and event["tool"].split(".")[-1] == "apply_patch"
                and event.get("call_id") not in completed_calls):
            paths.update(re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$",
                                    as_text(event["input"]), re.M))
    if paths:
        emit("패치에 명시된 경로 (시도 기록이며, 적용 성공과 전체 변경 목록은 별도 확인):")
        for path in sorted(paths)[:args.files]:
            emit(f"  {path}")
        if len(paths) > args.files:
            emit(f"  … 외 {len(paths) - args.files}개")
    # These are historical outcomes, not a claim about the present worktree.
    for status in (True, False, None):
        group = [e for e in patches if (e.get("success") if type(e.get("success")) is bool else None) is status]
        if not group:
            continue
        recorded_paths = {path: e["n"] for e in group for path in patch_paths(e.get("changes"))}
        emit(f"{patch_label(status)} (완료 이벤트 {len(group)}건):")
        for path in sorted(recorded_paths)[:args.files]:
            emit(f"  {path}  #{recorded_paths[path]}")
        if len(recorded_paths) > args.files:
            emit(f"  … 외 {len(recorded_paths) - args.files}개")
        if not recorded_paths:
            emit(f"  경로 기록 없음; 마지막 이벤트 #{group[-1]['n']}")
    file_events = [e for e in events if e["kind"] == "F" and not e.get("patch")]
    if file_events:
        emit("구조화된 파일 변경 기록: " + ", ".join(f"#{e['n']}" for e in file_events[-args.files:]))
        if len(file_events) > args.files:
            emit(f"  … 외 {len(file_events) - args.files}개")
    ops = state_ops(events)
    if ops:
        emit("git·sync 명령 후보를 포함한 셸 호출 (전체 호출 결과; 개별 실행 여부는 미확인):")
        for event, line in ops[-args.ops:]:
            status = shell_call_status(event["result"])
            emit(f"  #{event['n']} {time_text(event['ts'], tz)} {status}  {display(line, 140, True)}")
        if len(ops) > args.ops:
            emit(f"  … 이전 호출 {len(ops) - args.ops}개 생략")
    for label, kind, first in (("첫 요청", "U", True), ("마지막 요청", "U", False),
                               ("최근 압축 요약", "C", False), ("마지막 응답", "A", False)):
        matches = [e for e in events if e["kind"] == kind]
        if matches:
            event = matches[0] if first else matches[-1]
            emit(f"\n{label} #{event['n']}:\n{display(event['text'], args.width)}")
    errors = [e for e in events if e["kind"] == "T" and e["result"] is not None and failed(e["result"])]
    if errors:
        emit("\n최근 도구 실패: " + ", ".join(f"#{e['n']} {e['tool']}" for e in errors[-5:]))
    pending = [e for e in events if e["kind"] == "T" and e["result"] is None]
    if pending:
        emit("결과가 없는 호출: " + ", ".join(f"#{e['n']}" for e in pending[-10:]))


def event_text(event):
    if event["kind"] == "T":
        result = "(결과 기록 없음)" if event["result"] is None else as_text(event["result"])
        return f"도구: {event['tool']}\n입력:\n{as_text(event['input'])}\n결과:\n{result}"
    return event["text"]


def render(event, args, tz, expanded=False):
    marker = " [rewound]" if event["off"] else ""
    emit(f"#{event['n']} {time_text(event['ts'], tz)} {KINDS[event['kind']]}{marker}")
    if expanded:
        emit(display(event_text(event), args.max))
    elif event.get("patch"):
        paths = ", ".join(sorted(patch_paths(event.get("changes")))) or "경로 기록 없음"
        emit(f"  {patch_label(event.get('success'))}: {display(paths, args.width, True)}")
    elif event["kind"] == "T":
        emit(f"  {event['tool']}: {display(as_text(event['input']), args.width, True)}")
        result = event["result"]
        if result is None:
            emit("  → 결과 기록 없음")
        elif args.results or failed(result) or "request_user_input" in event["tool"]:
            emit("  → " + display(as_text(result), args.width))
    else:
        emit(display(event["text"], args.width))


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("1 이상의 정수가 필요합니다.")
    return number


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("0 이상의 정수가 필요합니다.")
    return number


def parser():
    ap = argparse.ArgumentParser(description="Codex 세션 기록을 읽기 전용으로 요약합니다.")
    ap.add_argument("--home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
    ap.add_argument("--self", dest="self_id", default=os.environ.get("CODEX_THREAD_ID"))
    ap.add_argument("--tz", default=os.environ.get("INSPECT_SESSION_TZ", "Asia/Seoul"))
    subs = ap.add_subparsers(dest="cmd", required=True)
    locate = subs.add_parser("locate", help="세션을 찾거나 최근 기록을 나열합니다.")
    locate.add_argument("query", nargs="?")
    locate.add_argument("--here", action="store_true")
    locate.add_argument("--limit", type=positive, default=12)
    for command in ("overview", "timeline", "show", "grep"):
        sub = subs.add_parser(command)
        sub.add_argument("session")
        if command in {"timeline", "show", "grep"}:
            sub.add_argument("--thinking", action="store_true")
        if command in {"overview", "timeline"}:
            sub.add_argument("--width", type=nonnegative, default=600)
        if command == "overview":
            sub.add_argument("--files", type=positive, default=15)
            sub.add_argument("--ops", type=positive, default=15, help="표시할 git·sync 셸 호출의 최대 개수입니다.")
        elif command == "timeline":
            sub.add_argument("--full", action="store_true")
            sub.add_argument("--from", dest="from_n", type=positive)
            sub.add_argument("--to", dest="to_n", type=positive)
            sub.add_argument("--last", type=positive)
            sub.add_argument("--kinds", help="U,A,T,P,C,F,N,K 중 쉼표로 구분합니다.")
            sub.add_argument("--results", action="store_true")
            sub.add_argument("--no-rewound", action="store_true")
        elif command == "show":
            sub.add_argument("numbers", nargs="+")
            sub.add_argument("--max", type=nonnegative, default=8000)
        else:
            sub.add_argument("pattern")
            sub.add_argument("-i", "--ignore-case", action="store_true")
            sub.add_argument("--max-hits", type=positive, default=40)
    return ap


def run(args):
    tz = ZoneInfo(args.tz)
    catalog = Catalog(args.home.expanduser())
    if args.cmd == "locate":
        paths = catalog.resolve(args.query) if args.query else catalog.paths()
        if args.query and len(paths) == 1:
            emit(f"RESOLVED {paths[0]}")
            return 0
        if args.query:
            emit(f"AMBIGUOUS: 후보 {len(paths)}개" if paths else "일치하는 로컬 세션 기록이 없습니다.")
        print_candidates(paths, catalog, args, tz)
        return 2 if args.query else 0
    paths = catalog.resolve(args.session)
    if len(paths) != 1:
        emit("세션을 하나로 확인하지 못했습니다. locate로 ID나 경로를 선택하세요.")
        for path in paths[:12]:
            emit(path)
        return 2
    session = Session(paths[0])
    for warning, count in session.warnings.items():
        print(redact(f"주의: {warning} ({count}건); 요약에서 누락된 내용이 있을 수 있습니다."), file=sys.stderr)
    if not session.events:
        emit("읽을 수 있는 이벤트가 없습니다. 기록 형식이나 저장 위치를 확인하세요.")
        return 2
    if args.cmd == "overview":
        overview(session, catalog, args, tz)
        return 0
    events = [e for e in session.events if args.thinking or e["kind"] != "K"]
    if args.cmd == "timeline":
        kinds = {k.strip().upper() for k in args.kinds.split(",")} if args.kinds else set(KINDS)
        if kinds - KINDS.keys():
            raise ValueError("--kinds에 알 수 없는 이벤트 종류가 있습니다.")
        start = args.from_n or 1
        if not args.full and args.from_n is None and args.last is None:
            compactions = [e["n"] for e in events if e["kind"] == "C" and not e["off"]]
            if compactions:
                start = compactions[-1]
                emit(f"최근 압축 #{start}부터 표시합니다. 이전 기록은 --full로 확인하세요.")
        events = [e for e in events if e["n"] >= start and (args.to_n is None or e["n"] <= args.to_n)
                  and (e["kind"] in kinds or e["kind"] == "C") and (not args.no_rewound or not e["off"])]
        if args.last:
            events = events[-args.last:]
        for event in events:
            render(event, args, tz)
    elif args.cmd == "show":
        ranges = []
        for spec in args.numbers:
            match = re.fullmatch(r"([1-9]\d*)(?:-([1-9]\d*))?", spec)
            if not match:
                raise ValueError(f"이벤트 번호나 범위가 잘못되었습니다: {spec}")
            lo, hi = int(match[1]), int(match[2] or match[1])
            if hi < lo:
                raise ValueError("범위 끝은 시작보다 작을 수 없습니다.")
            ranges.append((lo, hi))
        selected = [e for e in events if any(lo <= e["n"] <= hi for lo, hi in ranges)]
        if not selected:
            emit("선택한 번호에 표시할 이벤트가 없습니다. timeline의 #N을 사용하세요.")
            return 2
        for event in selected:
            render(event, args, tz, expanded=True)
    else:
        pattern = re.compile(args.pattern, re.I if args.ignore_case else 0)
        hits = 0
        for event in events:
            text = redact(event_text(event))
            match = pattern.search(text)
            if match:
                snippet = text[max(0, match.start() - 100):match.end() + 150]
                marker = " [rewound]" if event["off"] else ""
                emit(f"#{event['n']} {KINDS[event['kind']]}{marker}: {display(snippet, 400, True)}")
                hits += 1
                if hits >= args.max_hits:
                    emit(f"최대 {args.max_hits}건까지 표시했습니다.")
                    break
        if not hits:
            emit("일치하는 내용이 없습니다.")
    return 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return run(args)
    except (OSError, EOFError, ValueError, ZoneInfoNotFoundError, re.error) as exc:
        print(redact(f"기록을 읽지 못했습니다: {exc}"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
