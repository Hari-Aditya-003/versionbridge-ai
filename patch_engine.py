"""Validate immutable edit manifests and preview atomic, non-stacked Python edits."""

import difflib
import hashlib
import json
import re
from pathlib import Path
from policy_gate import safe_path, parse_safe_change


def physical_lines(text):
    parts = text.split("\n")
    return [line + "\n" for line in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def source_files(root, allowed):
    if not 1 <= len(allowed) <= 4 or len(set(allowed)) != len(allowed):
        raise ValueError("Allow one to four unique application source files.")
    result = {}
    for name in allowed:
        safe_path(name)
        p = Path(root) / name
        if any(
            (Path(root).joinpath(*Path(name).parts[:i])).is_symlink()
            for i in range(1, len(Path(name).parts) + 1)
        ):
            raise ValueError("Symlink paths are prohibited.")
        if not p.is_file() or p.stat().st_size > 24000:
            raise ValueError("Source missing or exceeds 24 KB.")
        try:
            result[name] = p.read_bytes().decode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Source must be UTF-8.") from exc
    if sum(len(t.encode()) for t in result.values()) > 48000:
        raise ValueError("Source context exceeds 48 KB.")
    return result


def snapshot_hash(root, allowed):
    files = source_files(root, allowed)
    return sha(
        json.dumps({p: sha(t) for p, t in sorted(files.items())}, sort_keys=True)
    )


def apply_manifest(root, manifest, allowed):
    files = source_files(root, allowed)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"schema_version", "source_sha", "diagnosis", "edits"}
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["source_sha"] != snapshot_hash(root, allowed)
        or not isinstance(manifest["diagnosis"], str)
        or not 1 <= len(manifest["diagnosis"]) <= 600
    ):
        raise ValueError("Invalid manifest or original source identity.")
    edits = manifest["edits"]
    if not isinstance(edits, list) or not 1 <= len(edits) <= 8:
        raise ValueError("Allow one to eight scoped edits.")
    groups = {}
    line_count = 0
    byte_count = 0
    for e in edits:
        if not isinstance(e, dict) or set(e) != {
            "path",
            "start_line",
            "end_line",
            "old_sha256",
            "new_text",
            "reason",
        }:
            raise ValueError("Invalid edit fields.")
        name = safe_path(e["path"])
        if name not in files:
            raise ValueError("Edit outside the source allowlist.")
        start, end = e["start_line"], e["end_line"]
        lines = physical_lines(files[name])
        text = e["new_text"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= len(lines)
            or not isinstance(text, str)
            or "\x00" in text
            or not isinstance(e["reason"], str)
            or not 1 <= len(e["reason"]) <= 360
        ):
            raise ValueError("Invalid edit span or replacement.")
        old = "".join(lines[start - 1 : end])
        if e["old_sha256"] != sha(old):
            raise ValueError("Old span checksum mismatch.")
        line_count += max(end - start + 1, len(text.splitlines()))
        byte_count += len(text.encode())
        if line_count > 128 or byte_count > 16000:
            raise ValueError("Patch exceeds line or byte allowance.")
        groups.setdefault(name, []).append(e)
    output = {}
    diffs = []
    checks = []
    for name, group in sorted(groups.items()):
        lines = physical_lines(files[name])
        last = 0
        for e in sorted(group, key=lambda e: e["start_line"]):
            if e["start_line"] <= last:
                raise ValueError("Overlapping edits.")
            last = e["end_line"]
        for e in sorted(group, key=lambda e: e["start_line"], reverse=True):
            lines[e["start_line"] - 1 : e["end_line"]] = [e["new_text"]]
        after = "".join(lines)
        if after == files[name]:
            raise ValueError("Candidate made no change.")
        checks.append({"path": name, **parse_safe_change(files[name], after)})
        output[name] = after
        changes = difflib.unified_diff(
            physical_lines(files[name]),
            physical_lines(after),
            fromfile="a/" + name,
            tofile="b/" + name,
        )
        diff = "".join(
            line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
            for line in changes
        )
        diffs.append(diff)
    diff = "".join(diffs)
    return {
        "files": output,
        "diff": diff,
        "patch_sha256": sha(diff),
        "static_checks": checks,
        "source_sha": manifest["source_sha"],
        "candidate_sha": sha(json.dumps({**files, **output}, sort_keys=True)),
    }


def bind_proposal(root, proposal, allowed, expected_sha):
    """Trusted hashes bind an untrusted span proposal to the original intake."""
    if snapshot_hash(root, allowed) != expected_sha:
        raise ValueError("Original source changed before manifest binding.")
    if not isinstance(proposal, dict) or set(proposal) != {"diagnosis", "edits"}:
        raise ValueError("Invalid model edit proposal fields.")
    edits = proposal["edits"]
    if not isinstance(edits, list) or not 1 <= len(edits) <= 8:
        raise ValueError("Expected one to eight edit proposals.")
    files = source_files(root, allowed)
    bound = []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {
            "path",
            "start_line",
            "end_line",
            "new_text",
            "reason",
        }:
            raise ValueError("Invalid model edit fields.")
        name = safe_path(edit["path"])
        start = edit["start_line"]
        end = edit["end_line"]
        if name not in files:
            raise ValueError("Model edit is outside the allowed source paths.")
        lines = physical_lines(files[name])
        if (
            type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= len(lines)
        ):
            raise ValueError("Model edit span is outside the original file.")
        normalized = dict(edit)
        text = edit["new_text"]
        if start == end and isinstance(text, str) and len(physical_lines(text)) == 1:
            prefix = re.match(r"[ \t]*", lines[start - 1])[0]
            normalized["new_text"] = prefix + text.lstrip(" \t")
            if lines[start - 1].endswith("\n") and not normalized["new_text"].endswith(
                "\n"
            ):
                normalized["new_text"] += "\n"
        bound.append({**normalized, "old_sha256": sha("".join(lines[start - 1 : end]))})
    return {
        "schema_version": 1,
        "source_sha": expected_sha,
        "diagnosis": proposal["diagnosis"],
        "edits": bound,
    }
