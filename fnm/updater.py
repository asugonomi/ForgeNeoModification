"""Download a commit-pinned manager package, without executing downloaded code."""
import io
import json
from pathlib import Path
import stat
import urllib.request
import zipfile

from .engine import Conflict, Package, path_in

REPOSITORY = "asugonomi/ForgeNeoModification"
LIMIT = 64 * 1024 * 1024


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ForgeNeoModification/0.1.0", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise Conflict("Download exceeds the 64 MiB limit")
    return data


def unpack(data, directory):
    directory = Path(directory)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = archive.infolist()
        if not files or sum(f.file_size for f in files) > 128 * 1024 * 1024 or len(files) > 3000:
            raise Conflict("Invalid/oversized package archive")
        top = files[0].filename.split("/")[0]
        seen = set()
        for item in files:
            if not item.filename.startswith(top + "/"):
                raise Conflict("Unexpected archive root")
            name = item.filename[len(top) + 1:].rstrip("/")
            if not name:
                continue
            path = path_in(directory, name)
            if name.lower() in seen or stat.S_ISLNK(item.external_attr >> 16):
                raise Conflict("Duplicate/link archive entry")
            seen.add(name.lower())
            if not item.is_dir():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(item))
    return Package(directory)


def latest(directory):
    info = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/commits/main"))
    commit = info["sha"]
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise Conflict("Invalid release commit")
    data = fetch(f"https://codeload.github.com/{REPOSITORY}/zip/{commit}")
    return unpack(data, directory), commit
