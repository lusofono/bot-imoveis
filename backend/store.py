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
from .rules import REFERENCE, check_profile, check_voice, knowledge

PHOTO_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def load_json(path, default):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, data):
    """Atomic write: a temporary file, fsync and rename, so a crash never leaves half a JSON."""
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
    """One operation at a time on a data folder. A second one fails at once instead of waiting."""
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
    """The voice in <folder>/voice.json is shared by every property of the same owner, and so is the
    agency's know-how in <folder>/knowledge/ (runtime only: never written back to voice.json)."""
    voice = check_voice(load_json(Path(folder) / "voice.json", {}))
    try:
        voice["_knowledge"] = load_knowledge(folder)
    except (ValueError, OSError) as exc:
        raise ValueError(f"Know-how comum: {exc}") from None
    return voice


def load_events(folder, limit=5000):
    """The last operations from logs/events.jsonl. It never holds bodies, addresses or subjects."""
    path = Path(folder) / "logs" / "events.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            events.append(json.loads(line))
        except ValueError:
            continue  # a half-written line never stops the page from opening
    return events


def property_folder(folder, ref):
    """A property's private folder; the reference is checked again here before it becomes a path."""
    if not REFERENCE.fullmatch(str(ref or "")):
        raise ValueError("Referência de imóvel inválida.")
    return Path(folder) / "properties" / ref


def write_photo(folder, ref, kind, data):
    """properties/<REF>/foto.<jpg|png|webp>, private (600). A new photo replaces the old one."""
    base = property_folder(folder, ref)
    for old in PHOTO_TYPES:
        (base / f"foto.{old}").unlink(missing_ok=True)
    fd = os.open(base / f"foto.{kind}", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def find_photo(folder, ref):
    """(path, media type) of the property's photo, or None."""
    base = property_folder(folder, ref)
    return next(((base / f"foto.{kind}", media) for kind, media in PHOTO_TYPES.items()
                 if (base / f"foto.{kind}").is_file()), None)


def read_photo(folder, ref):
    """(bytes, media type) of the property's photo, or None."""
    found = find_photo(folder, ref)
    return (found[0].read_bytes(), found[1]) if found else None
