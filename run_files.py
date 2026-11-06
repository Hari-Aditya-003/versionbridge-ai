"""Bounded text snapshots for the read-only sandbox inspector and TXT bundle."""

import hashlib
from pathlib import Path, PurePosixPath


def capture(root, paths, phase):
    files = []
    omitted = 0
    remaining = 65536
    for name in dict.fromkeys(str(p) for p in paths):
        pure = PurePosixPath(name)
        if (
            len(files) >= 16
            or remaining <= 0
            or pure.is_absolute()
            or ".." in pure.parts
            or "\\" in name
            or str(pure) != name
            or any(p.startswith(".") for p in pure.parts)
            or any(
                word in pure.name.lower()
                for word in ("secret", "credential", "private_key")
            )
            or any(
                (Path(root).joinpath(*pure.parts[:i])).is_symlink()
                for i in range(1, len(pure.parts) + 1)
            )
        ):
            omitted += 1
            continue
        path = Path(root) / name
        try:
            with path.open("rb") as handle:
                raw = handle.read(remaining + 1)
            text = raw[:remaining].decode("utf-8")
        except (OSError, UnicodeError):
            omitted += 1
            continue
        truncated = len(raw) > remaining or path.stat().st_size > len(raw)
        files.append(
            {
                "path": name,
                "content": text,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "bytes": len(text.encode()),
                "truncated": truncated,
            }
        )
        remaining -= len(text.encode())
        if truncated:
            omitted += 1
    return {
        "phase": phase,
        "files": files,
        "complete": omitted == 0,
        "omitted": omitted,
        "scope": "Scoped application and test text snapshots; 16 files / 64 KiB per phase.",
    }
