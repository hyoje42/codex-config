"""Codex adapter. Only this file knows tool homes and rollout/parser schemas."""

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
import time
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
TOOL = "codex"
ADAPTER_VERSION = 1


class SourceError(Exception):
    def __init__(self, message, observation=None):
        super().__init__(message)
        # Private, bounded hash proof; never contains source bytes or excerpts.
        self.observation = observation


def byte_proof(data, checkpoints=()):
    sizes = {size for size in checkpoints if 0 <= size <= len(data)} | {len(data)}
    hasher, prefixes, start = hashlib.sha256(), {}, 0
    view = memoryview(data)
    for size in sorted(sizes):
        hasher.update(view[start:size])
        prefixes[str(size)] = hasher.hexdigest()
        start = size
    return {"size": len(data), "digest": hasher.hexdigest(), "prefixes": prefixes}


def expand_gzip(physical, limit):
    """Bound the decoder itself, including concatenated members and padding."""
    pending, expanded = physical, bytearray()
    while pending:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        expanded.extend(decoder.decompress(pending, limit + 1 - len(expanded)))
        if len(expanded) > limit:
            return bytes(expanded)
        if not decoder.eof:
            raise EOFError("incomplete gzip member")
        pending = decoder.unused_data.lstrip(b"\x00")
    return bytes(expanded)


def dependency(path=None):
    path = path or Path(__file__).resolve().parents[2] / "inspect-session/scripts/session_digest.py"
    try:
        spec = importlib.util.spec_from_file_location("dashboard_session_digest", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in ("Catalog", "Session", "redact", "file_id", "injected", "failed", "patch_paths"):
            if not callable(getattr(module, name, None)):
                raise AttributeError(name)
        if not callable(getattr(module.Session, "active", None)):
            raise AttributeError("Session.active")
        return module
    except (OSError, ImportError, AttributeError, TypeError, SyntaxError) as exc:
        raise SourceError("inspect-session 의존성이 없거나 호환되지 않습니다. 같은 skills 폴더에 inspect-session을 설치하세요.") from exc


def defaults():
    return {"home": str(Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))),
            "self_id": os.environ.get("CODEX_THREAD_ID")}


def signature(path):
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise SourceError("일반 파일이 아닌 기록은 읽지 않습니다.")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class Adapter:
    tool = TOOL
    version = ADAPTER_VERSION

    def __init__(self, home, max_bytes, text_limit=2000, recent_limit=40, evidence_limit=100,
                 parser_path=None):
        self.parser = dependency(parser_path)
        self.home = Path(home)
        self.max_bytes = max_bytes
        self.text_limit = text_limit
        self.recent_limit = recent_limit
        self.evidence_limit = evidence_limit
        self.titles = {}
        self.index_signature = None
        self.metrics = {"read_calls": 0, "read_bytes": 0, "expanded_bytes": 0,
                        "parse_calls": 0, "metadata_reads": 0, "index_reads": 0}

    def clean(self, value, limit=None):
        text = self.parser.redact(value)
        # Attached documents and harness instructions are not dashboard evidence.
        text = re.sub(r"(?is)<(attachment|attached_files|file_content|file|environment_context|"
                      r"instructions|system-reminder|permissions|skill)(?:\s[^>]*)?>.*?</\1\s*>",
                      "[첨부·주입 본문 제외]", text)
        return text[:self.text_limit if limit is None else limit]

    def bounded(self, path, limit=None, checkpoints=()):
        """Read physical bytes once; independently bound raw and expanded snapshots."""
        limit = self.max_bytes if limit is None else limit
        observed_ns = time.time_ns()
        before = signature(path)
        if before[2] > limit:
            raise SourceError("기록 파일이 바이트 상한을 초과하여 수집하지 않았습니다.")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as raw:
            info = os.fstat(raw.fileno())
            if (info.st_dev, info.st_ino) != before[:2]:
                raise SourceError("읽기 전에 기록 파일이 교체되었습니다.")
            self.metrics["read_calls"] += 1
            physical = raw.read(limit + 1)
            self.metrics["read_bytes"] += len(physical)
        if signature(path) != before:
            raise SourceError("읽는 동안 기록이 바뀌었습니다. 다음 수집에서 다시 확인합니다.")
        if len(physical) > limit:
            raise SourceError("기록 파일이 바이트 상한을 초과하여 수집하지 않았습니다.")
        observation = {"observed_ns": observed_ns, "file_stat": list(before),
                       "raw": byte_proof(physical, checkpoints), "logical": None, "failure": None}
        if path.suffix == ".gz":
            try:
                data = expand_gzip(physical, limit)
            except (OSError, EOFError, zlib.error) as exc:
                observation["failure"] = "decode"
                raise SourceError("압축 기록이 손상되어 해제할 수 없습니다.", observation) from exc
        else:
            data = physical
        self.metrics["expanded_bytes"] += len(data)
        if len(data) > limit:
            observation["failure"] = "bounds"
            raise SourceError("압축 해제된 기록이 바이트 상한을 초과하여 수집하지 않았습니다.", observation)
        observation["logical"] = byte_proof(data, checkpoints)
        return data, before, observation

    def discover(self):
        warnings = []
        index = self.home / "session_index.jsonl"
        try:
            current = signature(index)
        except FileNotFoundError:
            current = None
            self.titles = {}
        except (OSError, SourceError):
            current = None
            self.titles = {}
            warnings.append("세션 제목 인덱스를 읽을 수 없습니다.")
        if current is not None and current != self.index_signature:
            try:
                data, current, _ = self.bounded(index, min(self.max_bytes, 8 * 1024 * 1024))
                with tempfile.TemporaryDirectory(prefix="session-dashboard-index-") as tmp:
                    target = Path(tmp) / "session_index.jsonl"
                    with open(target, "xb") as stream:
                        os.chmod(target, 0o600)
                        stream.write(data)
                    self.metrics["index_reads"] += 1
                    catalog = self.parser.Catalog(Path(tmp))
                    self.titles = {str(k): self.clean(v, 240) for k, v in catalog.titles.items()}
            except (OSError, SourceError, ValueError, TypeError):
                self.titles = {}
                warnings.append("세션 제목 인덱스를 해석할 수 없습니다.")
        self.index_signature = current
        # Catalog must never read an unbounded index in the real home.
        with tempfile.TemporaryDirectory(prefix="session-dashboard-catalog-") as tmp:
            catalog = self.parser.Catalog(Path(tmp))
            catalog.home = self.home
            paths = catalog.paths()
        return paths, warnings

    def file_id(self, path):
        return self.clean(self.parser.file_id(path), 200)

    def read(self, path, checkpoints=()):
        data, file_stat, observation = self.bounded(path, checkpoints=checkpoints)
        with tempfile.TemporaryDirectory(prefix="session-dashboard-record-") as tmp:
            target = Path(tmp) / "snapshot.jsonl"
            with open(target, "xb") as stream:
                os.chmod(target, 0o600)
                stream.write(data)
            self.metrics["parse_calls"] += 1
            self.metrics["metadata_reads"] += 1
            try:
                session = self.parser.Session(target)
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
                observation["failure"] = "parse"
                raise SourceError("기록의 구조를 해석할 수 없습니다.", observation) from exc
        try:
            meta, active = session.meta, session.active()
            sid = self.clean(meta.get("id") or self.parser.file_id(path), 200)
            origin = meta.get("source")
            subagent = bool(meta.get("parent_thread_id") or meta.get("parent_session_id")
                            or (isinstance(origin, dict) and "subagent" in origin)
                            or (isinstance(origin, str) and "subagent" in origin.lower()))
            events, omitted_chars, excluded = [], 0, 0
            names = {"U": "user", "A": "assistant", "C": "compaction", "T": "tool", "F": "file"}
            for event in active:
                kind = event["kind"]
                if kind not in names:
                    excluded += 1
                    continue
                if kind in {"U", "A", "C"}:
                    raw = str(event["text"])
                    if self.parser.injected(raw):
                        excluded += 1
                        continue
                    text = self.clean(raw)
                    omitted_chars += max(0, len(self.parser.redact(raw)) - self.text_limit)
                elif kind == "T":
                    tool = self.clean(event.get("tool", "unknown"), 100)
                    result = event.get("result")
                    status = "unknown" if result is None else ("failed" if self.parser.failed(result) else "recorded")
                    text = f"도구 {tool}: 결과 {status}"
                else:
                    paths = sorted(self.parser.patch_paths(event.get("changes")))[:40]
                    status = {True: "success", False: "failed"}.get(event.get("success"), "unknown")
                    text = self.clean("파일 변경: " + status + " " + ", ".join(str(p) for p in paths))
                events.append({"id": str(event["n"]), "kind": names[kind],
                               "timestamp": self.clean(event.get("ts") or "", 80) or None,
                               "text": text})
            selected = set(range(max(0, len(events) - self.evidence_limit), len(events)))
            users = [i for i, event in enumerate(events) if event["kind"] == "user"]
            compactions = [i for i, event in enumerate(events) if event["kind"] == "compaction"]
            anchors = set(users[:1] + users[-1:] + compactions[-1:])
            selected.update(anchors)
            while len(selected) > self.evidence_limit:
                selected.remove(min(selected - anchors))
            evidence = [events[i] for i in sorted(selected)]
            # Epoch canonicalization may renumber old messages on ordinary append.
            # Only explicit branch/rewind records change this lineage fingerprint.
            controls = [event["text"] for event in session.events if event["kind"] == "N"
                        and any(marker in str(event["text"]) for marker in
                                ('"thread_rolled_back"', '"thread_revert"', '"thread_reverted"'))]
            lineage = hashlib.sha256(json.dumps([meta.get("git"), meta.get("forked_from_id"), controls],
                                                 sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            observation["logical"]["lineage"] = lineage
            revision = {**observation["logical"], "identity": list(file_stat[:2])}
            first = next((event["text"] for event in events if event["kind"] == "user"), "")
            cwd = meta.get("cwd")
            return {"id": sid, "cwd": self.clean(cwd, 2000) if isinstance(cwd, str) else None,
                    "scope_cwd": str(Path(cwd).expanduser().resolve()) if isinstance(cwd, str) and cwd else None,
                    "subagent": subagent, "automatic_title": re.sub(r"\s+", " ", first)[:100],
                    "live": {"state": "unknown", "provenance": "transcript", "observed_at": None},
                    "recorded_turn": self.clean(session.status, 240),
                    "last_activity": self.clean(session.last_ts or "", 80) or None,
                    "revision": revision, "events": events[-self.recent_limit:], "evidence": evidence,
                    "warnings": [self.clean(f"{key} ({value})", 240) for key, value in session.warnings.items()][:20],
                    "truncation": {"recent_events": max(0, len(events) - self.recent_limit),
                                   "evidence_events": max(0, len(events) - len(evidence)),
                                   "text_characters": omitted_chars, "excluded_events": excluded},
                    "source_mtime": file_stat[3] / 1e9, "_observation": observation}
        except (AttributeError, KeyError, TypeError) as exc:
            observation["failure"] = "parse"
            raise SourceError("inspect-session 파서의 반환 형식이 호환되지 않습니다.", observation) from exc
