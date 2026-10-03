"""The hidden mark (02/10): every email the ARIA sends carries, in plain ASCII and out of the reader's sight, what it was
— the property, our nth email to that customer, the kind of email, the visit and the window it named, the customer's
place on the short list. Two places, both kept by Gmail:

- the X-ARIA header: read back from our Sent copies, it rebuilds what happened if the data folder is lost;
- the Message-ID, which the customer's mail program copies into its reply (In-Reply-To, References): the reply says,
  by itself, which of our emails it answers.

Both travel with the email, and anyone can see them in «Mostrar original»: so they are sealed — enciphered and signed
with a key that never leaves the Mac (secrets.tag_key) — and read as an opaque token, «1.k3f9…». Without the key they
say nothing; changed, they are refused. The seal: a keystream from HMAC-SHA256 in counter mode, then an HMAC over the
nonce and the cipher text (standard library only). Pure functions: no files or network.
"""
import base64
import hashlib
import hmac
import re
import secrets

ORDER = ("ref", "n", "k", "vis", "win", "sel")  # property, our nth email, kind, visit, visit window, short list
SAFE = re.compile(r"[A-Za-z0-9_:/.+-]{1,64}")
MESSAGE_ID = re.compile(r"<a1\.([a-z2-7]{20,200})@[^>]+>")
NONCE, TAG = 8, 8


def _mac(key, label, data):
    return hmac.new(str(key).encode(), label + data, hashlib.sha256).digest()


def _stream(key, nonce, length):
    out, counter = b"", 0
    while len(out) < length:
        out += _mac(key, b"aria-stream", nonce + counter.to_bytes(4, "big"))
        counter += 1
    return out[:length]


def _b32(raw):
    return base64.b32encode(raw).decode().rstrip("=").lower()


def seal(key, text):
    """text → an opaque ASCII token (lower-case base32): only the same key opens it."""
    nonce, data = secrets.token_bytes(NONCE), text.encode()
    cipher = bytes(a ^ b for a, b in zip(data, _stream(key, nonce, len(data))))
    return _b32(nonce + cipher + _mac(key, b"aria-seal", nonce + cipher)[:TAG])


def unseal(key, token):
    """The text a token holds, or None: no key, not one of ours, or changed on the way."""
    if not key:
        return None
    try:
        token = str(token or "").strip().upper()
        raw = base64.b32decode(token + "=" * (-len(token) % 8))
    except (ValueError, TypeError):
        return None
    if len(raw) < NONCE + TAG + 1:
        return None
    nonce, cipher, tag = raw[:NONCE], raw[NONCE:-TAG], raw[-TAG:]
    if not hmac.compare_digest(tag, _mac(key, b"aria-seal", nonce + cipher)[:TAG]):
        return None
    return bytes(a ^ b for a, b in zip(cipher, _stream(key, nonce, len(cipher)))).decode(errors="replace")


def clean(fields):
    """Only the known fields, and only plain ASCII values without spaces or separators."""
    return {name: str(fields[name]) for name in ORDER
            if fields.get(name) not in (None, "") and SAFE.fullmatch(str(fields[name]))}


def _pairs(text):
    return {name: value for name, value in (part.split("=", 1) for part in text.split(";") if "=" in part) if name in ORDER}


def header(fields, key):
    """The X-ARIA header: «1.<sealed ref=…;n=…;k=…;vis=…;win=…;sel=…>»."""
    return "1." + seal(key, ";".join(f"{name}={value}" for name, value in clean(fields).items()))


def read_header(value, key):
    """The fields of an X-ARIA header, or None when it is not ours or cannot be opened with this key."""
    version, _, token = str(value or "").strip().partition(".")
    text = unseal(key, token) if version == "1" else None
    return _pairs(text) if text is not None else None


def message_id(fields, key, domain="gmail.com"):
    """Our Message-ID, «<a1.<sealed n and kind>@gmail.com>»: unique (a new nonce each time), opened only by this key."""
    kind = re.sub(r"[^a-z_]", "", str(fields.get("k") or "email").lower())[:24] or "email"
    number = int(fields.get("n") or 0)
    return f"<a1.{seal(key, f'n={number};k={kind}')}@{domain}>"


def read_message_id(value, key):
    """From any Message-ID, In-Reply-To or References: our nth email and its kind, or None when none of ours."""
    for token in MESSAGE_ID.findall(str(value or "")):
        text = unseal(key, token)
        if text is not None:
            fields = _pairs(text)
            return {"n": int(fields.get("n") or 0), "k": fields.get("k") or ""}
    return None
