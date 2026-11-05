"""Retrieve immutable, size-limited public GitHub Python snapshots."""
import io
import json
from pathlib import PurePosixPath
import re
import stat
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import BadZipFile, ZipFile

MAX_ARCHIVE = 4 * 1024 * 1024
MAX_EXPANDED = 12 * 1024 * 1024
REPOSITORY = re.compile(r"https://github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100})/?")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url, limit):
    request = Request(url, headers={"User-Agent": "VersionBridge-AI"})
    try:
        with build_opener(NoRedirect).open(request, timeout=12) as response:
            data = response.read(limit + 1)
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("GitHub could not return a public snapshot for this repository and ref.") from exc
    if len(data) > limit:
        raise RuntimeError("GitHub snapshot exceeded the download limit.")
    return data


def snapshot(repository, ref, project):
    match = REPOSITORY.fullmatch(repository)
    if not match or match[2] in {".", ".."} or (ref and not REF.fullmatch(ref)):
        raise RuntimeError("Enter a public https://github.com/owner/repository URL and a valid branch or commit.")
    slug = "/".join(match.groups())
    base = f"https://api.github.com/repos/{slug}"
    try:
        if not ref:
            ref = json.loads(fetch(base, 131072))["default_branch"]
        revision = json.loads(fetch(f"{base}/commits/{quote(ref, safe='')}", 524288))["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("Invalid revision")
        data = fetch(f"https://codeload.github.com/{slug}/zip/{revision}", MAX_ARCHIVE)
        with ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 400 or sum(item.file_size for item in members) > MAX_EXPANDED:
                raise RuntimeError("Repository exceeded the snapshot size or file count limit.")
            for item in members:
                parts = PurePosixPath(item.filename).parts
                if (not parts or parts[0] == "/" or ".." in parts or "\\" in item.filename
                        or stat.S_ISLNK(item.external_attr >> 16)):
                    raise RuntimeError("Repository contains an unsupported archive path.")
                if len(parts) == 1 or item.is_dir() or item.filename.endswith((".pyc", ".pyo")):
                    continue
                target = project.joinpath(*parts[1:])
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(archive.read(item))
    except (ValueError, KeyError, TypeError, OSError, BadZipFile) as exc:
        raise RuntimeError("Could not read the GitHub snapshot safely.") from exc
    return revision


PINNED_REPOSITORY = "https://github.com/Hari-Aditya-003/versionbridge-ai"
PINNED_REVISION = "274b7ba6ec8fd8d418f686f37538517d4f87ca82"


def is_pinned_example(repository, ref, profile):
    return repository == PINNED_REPOSITORY and ref == PINNED_REVISION and profile == "pandas"
