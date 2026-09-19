"""The data folder: JSON written atomically, one lock per folder, and the private files of the owner
(voice.json) and of each property (profile.json, knowledge/). Local files today; S3 or DynamoDB on AWS later.

Layout of the folder: config.json, voice.json, properties/<REF>/{profile.json, queue.json, knowledge/*.md},
logs/events.jsonl. It stays out of Git.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
from .rules import check_profile, check_voice, knowledge


def load_json(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def locked(folder, name="queue"):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    fd = os.open(folder / f".{name}.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Já existe uma operação em curso. Tenta novamente.") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def load_knowledge(folder):
    """The owner-written .md/.txt files in the property's knowledge/, whole, in name order."""
    base = Path(folder) / "knowledge"
    files = []
    for path in sorted(base.iterdir()) if base.is_dir() else []:
        if path.name.startswith(".") or path.suffix.lower() not in (".md", ".txt") or not path.is_file():
            continue
        if not path.resolve().is_relative_to(base.resolve()):
            raise ValueError(f"{path.name} aponta para fora da pasta knowledge.")
        files.append((path.name, path.read_text(encoding="utf-8")))
    return knowledge(files)


def load_profiles(folder, account):
    """Profiles live in <folder>/properties/<REF>/profile.json and stay private (never in Git)."""
    profiles = {}
    for path in sorted((Path(folder) / "properties").glob("*/profile.json")):
        ref = path.parent.name
        profile = load_json(path, {})
        check_profile(ref, profile, account)
        try:
            # Runtime only: never written back to profile.json.
            profile["_knowledge"] = load_knowledge(path.parent)
        except (ValueError, OSError) as exc:
            raise ValueError(f"Conhecimento do imóvel {ref}: {exc}") from None
        profiles[ref] = profile
    return profiles


def load_voice(folder):
    """The voice in <folder>/voice.json is shared by every property of the same owner."""
    return check_voice(load_json(Path(folder) / "voice.json", {}))
