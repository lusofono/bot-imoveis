"""The data folder: JSON written atomically, one lock per folder, and the private files of the owner
(voice.json) and of each property (profile.json, knowledge/). Local files today; S3 or DynamoDB on AWS later.

Layout of the folder: config.json, voice.json, properties/<REF>/{profile.json, queue.json, knowledge/*.md},
logs/events.jsonl. It stays out of Git.
"""
from contextlib import contextmanager
import csv
import fcntl
import json
import os
from pathlib import Path
import tempfile
from .rules import KNOWLEDGE_LIMIT, REFERENCE, check_profile, check_voice, knowledge

PHOTO_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
CONTACT_FIELDS = ("email", "nome", "telefone", "primeiro_contacto", "imovel", "fonte",
                  "rgpd", "rgpd_data", "rgpd_prova")
# The file where facts added from the page go, one per line; the assistant reads the text under the title.
NOTES_HEADING = ("# Notas do proprietário\n\n"
                 "Acrescentadas ao rever as respostas. Se contradisserem o resto, valem estas.\n\n")


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
    return knowledge(knowledge_files(folder))


def knowledge_files(folder):
    """(name, text) of each file in <folder>/knowledge/, exactly as written, comments included."""
    base = Path(folder) / "knowledge"
    files = []
    for path in sorted(base.iterdir()) if base.is_dir() else []:
        if path.name.startswith(".") or path.suffix.lower() not in (".md", ".txt") or not path.is_file():
            continue
        if not path.resolve().is_relative_to(base.resolve()):
            raise ValueError(f"{path.name} aponta para fora da pasta knowledge.")
        files.append((path.name, path.read_text(encoding="utf-8")))
    return files


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


def save_text(path, text):
    """Written like save_json: whole or not at all, and private (600)."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def add_note(base, text, day):
    """One fact at the end of <base>/knowledge/notas.md, if the whole base stays within its limit.

    The date goes in an HTML comment: the owner sees it in the file, the assistant never does.
    """
    size = sum(len(part["text"]) for part in load_knowledge(base))
    if size + len(text) > KNOWLEDGE_LIMIT:
        raise ValueError(f"A base de conhecimento já tem {size} caracteres; o limite é {KNOWLEDGE_LIMIT}. "
                         "Resume os ficheiros antes de acrescentar.")
    path = Path(base) / "knowledge" / "notas.md"
    current = path.read_text(encoding="utf-8").rstrip("\n") + "\n" if path.exists() else NOTES_HEADING
    save_text(path, current + f"- {text} <!-- {day:%d/%m/%Y} -->\n")


def load_contacts(folder):
    """<folder>/contactos.csv, keyed by (email, imovel); empty when nothing has been registered yet."""
    path = Path(folder) / "contactos.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as stream:
        return {(row["email"], row["imovel"]): row for row in csv.DictReader(stream)}


def save_contacts(folder, contacts):
    """Atomic write of contactos.csv, private (600) like the rest of data/, sorted by email then imóvel."""
    path = Path(folder) / "contactos.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=CONTACT_FIELDS)
            writer.writeheader()
            for row in sorted(contacts.values(), key=lambda r: (r["email"], r["imovel"])):
                writer.writerow(row)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def add_contacts(folder, entries):
    """Adds or updates rows for READ-extracted contacts: (email, nome, telefone, primeiro_contacto, imovel, fonte).

    A pair (email, imóvel) not seen before gets a new row, RGPD "por_pedir". A known pair only fills a
    blank name or phone: primeiro_contacto and the RGPD fields already recorded are never touched.
    """
    if not entries:
        return
    contacts = load_contacts(folder)
    for entry in entries:
        key = (entry["email"], entry["imovel"])
        row = contacts.get(key)
        if row is None:
            contacts[key] = {"email": entry["email"], "nome": entry["nome"] or "",
                             "telefone": entry["telefone"] or "", "primeiro_contacto": entry["primeiro_contacto"],
                             "imovel": entry["imovel"], "fonte": entry["fonte"],
                             "rgpd": "por_pedir", "rgpd_data": "", "rgpd_prova": ""}
        else:
            row["nome"] = row["nome"] or entry["nome"] or ""
            row["telefone"] = row["telefone"] or entry["telefone"] or ""
    save_contacts(folder, contacts)


def load_digest(folder):
    """<folder>/digest.json: today's status digest for the owner's own inbox, or None before the first READ."""
    return load_json(Path(folder) / "digest.json", None)


def save_digest(folder, digest):
    save_json(Path(folder) / "digest.json", digest)


def load_visits(folder, ref):
    """properties/<REF>/visitas.json: the windows proposed, the times booked, and whether visits are closed."""
    agenda = load_json(property_folder(folder, ref) / "visitas.json", {"windows": [], "slots": []})
    agenda.setdefault("closed_at", None)
    return agenda


def save_visits(folder, ref, agenda):
    save_json(property_folder(folder, ref) / "visitas.json", agenda)
