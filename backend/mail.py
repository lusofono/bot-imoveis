"""Gmail: read by IMAP (headers first; then only the text parts, never attachments) and build the replies.

Adapted from the original gmail_cycle_mac.zip. The SMTP connection itself is still opened in service.py.
"""
from __future__ import annotations

import imaplib
import re
import unicodedata
from datetime import datetime, timedelta
from email import policy
from email.header import decode_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formataddr, formatdate, getaddresses, make_msgid, parsedate_to_datetime

class GmailReadError(RuntimeError):
    pass

def decode_mime(value):
    if not value:
        return ""
    out = []
    for part, enc in decode_header(value):
        if isinstance(part, bytes):
            for candidate in (enc, "utf-8", "latin-1"):
                if not candidate:
                    continue
                try:
                    out.append(part.decode(candidate))
                    break
                except (UnicodeDecodeError, LookupError):
                    pass
            else:
                out.append(part.decode("utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)

def normalise(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").casefold().strip()

def parse_addresses(values):
    values = values or []
    decoded = [decode_mime(v) for v in values]
    result = []
    for name, address in getaddresses(decoded):
        if name or address:
            result.append({"name": decode_mime(name).strip(),
                           "email": address.strip()})
    return result

def extract_text(msg) -> str:
    texts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            # Anexos são ignorados por completo.
            if (part.get_content_disposition() or "").lower() == "attachment":
                continue
            if part.get_content_type() != "text/plain":
                continue
            try:
                content = part.get_content()
                if isinstance(content, str) and content.strip():
                    texts.append(content.strip())
            except Exception:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        texts.append(payload.decode(charset, errors="replace").strip())
                    except LookupError:
                        texts.append(payload.decode("utf-8", errors="replace").strip())
    else:
        if msg.get_content_type() == "text/plain":
            try:
                content = msg.get_content()
                if isinstance(content, str):
                    texts.append(content.strip())
            except Exception:
                pass
    return "\n\n".join(t for t in texts if t).strip()

def mailbox_name_from_list(raw: bytes):
    text = raw.decode("utf-8", errors="replace")
    m = re.match(r'^\((?P<flags>[^)]*)\)\s+"[^"]*"\s+(?P<name>.+)$', text)
    if not m:
        return None
    flags = m.group("flags")
    name = m.group("name").strip()
    if name.startswith('"') and name.endswith('"'):
        name = name[1:-1].replace(r'\"', '"').replace(r'\\', '\\')
    return flags, name

def find_all_mailbox(mail):
    status, boxes = mail.list()
    if status == "OK" and boxes:
        for raw in boxes:
            parsed = mailbox_name_from_list(raw)
            if parsed and "\\All" in parsed[0].split():
                return parsed[1]
    for candidate in ("[Gmail]/All Mail", "[Google Mail]/All Mail"):
        status, _ = mail.select('"' + candidate + '"', readonly=True)
        if status == "OK":
            return candidate
    raise GmailReadError("Não consegui localizar a pasta All Mail do Gmail.")

def connect(account: str, password: str):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
        mail.login(account, password)
        return mail
    except imaplib.IMAP4.error as exc:
        raise GmailReadError(
            "Falhou o login IMAP. Usa a Google App Password, não a password normal."
        ) from exc

def meta_from_fetch(meta: bytes):
    text = meta.decode("utf-8", errors="replace")
    def grab(pattern):
        m = re.search(pattern, text)
        return m.group(1) if m else ""
    return {
        "thread_id": grab(r"X-GM-THRID\s+(\d+)"),
        "gmail_message_id": grab(r"X-GM-MSGID\s+(\d+)"),
    }

def read_messages(account, password, subject_contains, date_from, date_to,
                  mailbox="all", incoming_only=True, accept=None):
    """Messages between two dates, as dicts: (messages, number scanned, mailbox).

    Headers first; accept(item) decides on them, so mail that is not ours never has its text fetched.
    Everything is read with BODY.PEEK: nothing is marked as read, and read or unread does not matter.
    """
    start = datetime.strptime(date_from, "%Y-%m-%d")
    end = datetime.strptime(date_to, "%Y-%m-%d")
    if end < start:
        raise GmailReadError("Data final anterior à inicial.")

    mail = connect(account, password)
    try:
        box = "INBOX" if mailbox == "inbox" else find_all_mailbox(mail)
        status, _ = mail.select('"' + box.replace('"', r'\"') + '"', readonly=True)
        if status != "OK":
            raise GmailReadError(f"Não consegui abrir {box}.")

        status, data = mail.uid(
            "search", None,
            "SINCE", start.strftime("%d-%b-%Y"),
            "BEFORE", (end + timedelta(days=1)).strftime("%d-%b-%Y")
        )
        if status != "OK":
            raise GmailReadError("Erro na pesquisa IMAP.")

        wanted = normalise(subject_contains)
        result = []
        uids = data[0].split() if data and data[0] else []

        for uid in uids:
            status, fetched = mail.uid(
                "fetch", uid, "(BODY.PEEK[HEADER] BODYSTRUCTURE X-GM-THRID X-GM-MSGID)"
            )
            if status != "OK":
                raise GmailReadError("Falha ao obter mensagem; a leitura não foi concluída.")

            raw = None
            meta = {}
            structure_bytes = b""
            for item in fetched:
                # Only found values: the trailing b")" must not blank IDs read before it.
                if isinstance(item, tuple) and len(item) >= 2:
                    meta.update({k: v for k, v in meta_from_fetch(item[0]).items() if v})
                    structure_bytes += item[0] + b" "
                    raw = item[1]
                elif isinstance(item, bytes):
                    meta.update({k: v for k, v in meta_from_fetch(item).items() if v})
                    structure_bytes += item + b" "
            if not raw:
                raise GmailReadError("Cabeçalhos em falta; tenta novamente.")

            msg = BytesParser(policy=policy.default).parsebytes(raw)
            subject = decode_mime(msg.get("Subject"))
            if wanted and wanted not in normalise(subject):
                continue

            from_list = parse_addresses(msg.get_all("From", []))
            if incoming_only:
                from_emails = {x["email"].casefold() for x in from_list if x["email"]}
                if account.casefold() in from_emails:
                    continue

            raw_date = msg.get("Date", "") or ""
            iso_date = ""
            try:
                dt = parsedate_to_datetime(raw_date)
                if dt:
                    iso_date = dt.isoformat()
            except Exception:
                pass

            item = {
                "uid": uid.decode("ascii", errors="ignore"),
                "gmail_message_id": meta.get("gmail_message_id", ""),
                "thread_id": meta.get("thread_id", ""),
                "date": iso_date,
                "date_raw": raw_date,
                "from": from_list,
                "to": parse_addresses(msg.get_all("To", [])),
                "cc": parse_addresses(msg.get_all("Cc", [])),
                "reply_to": parse_addresses(msg.get_all("Reply-To", [])),
                "subject": subject,
                "message_id": (msg.get("Message-ID", "") or "").strip(),
                "in_reply_to": (msg.get("In-Reply-To", "") or "").strip(),
                "references": (msg.get("References", "") or "").strip(),
            }
            # Headers decide first: unrelated mail never has its text fetched.
            if accept and not accept(item):
                continue
            item["body_text"], item["body_truncated"] = fetch_text_only(mail, uid, structure_bytes)
            result.append(item)

        return result, len(uids), box
    finally:
        try:
            mail.logout()
        except Exception:
            pass


# IMAP BODYSTRUCTURE lets us choose text parts without fetching attachment bodies.
def parse_structure(raw):
    match = re.search(rb"BODYSTRUCTURE\s+", raw, re.I)
    if not match:
        raise GmailReadError("Servidor não devolveu BODYSTRUCTURE.")
    source = raw[match.end():]
    pos = 0

    def value():
        nonlocal pos
        while pos < len(source) and source[pos:pos+1].isspace():
            pos += 1
        if pos >= len(source):
            raise GmailReadError("BODYSTRUCTURE incompleto.")
        if source[pos:pos+1] == b"(":
            pos += 1
            out = []
            while True:
                while pos < len(source) and source[pos:pos+1].isspace():
                    pos += 1
                if pos >= len(source):
                    raise GmailReadError("BODYSTRUCTURE incompleto.")
                if source[pos:pos+1] == b")":
                    pos += 1
                    return out
                out.append(value())
        if source[pos:pos+1] == b'"':
            pos += 1
            out = bytearray()
            while pos < len(source):
                char = source[pos]
                pos += 1
                if char == 34:
                    return out.decode("utf-8", "replace")
                if char == 92 and pos < len(source):
                    char = source[pos]
                    pos += 1
                out.append(char)
            raise GmailReadError("BODYSTRUCTURE inválido.")
        literal = re.match(rb"\{(\d+)\}\r\n", source[pos:])
        if literal:
            pos += literal.end()
            length = int(literal[1])
            result = source[pos:pos+length]
            pos += length
            return result.decode("utf-8", "replace")
        atom = re.match(rb"[^\s()]+", source[pos:])
        if not atom:
            raise GmailReadError("BODYSTRUCTURE inválido.")
        pos += atom.end()
        text = atom[0].decode("ascii", "replace")
        return None if text.upper() == "NIL" else text
    return value()


def body_sections(node, prefix=""):
    """Return only plain/html leaf sections; skip attached multipart trees too."""
    if not isinstance(node, list) or not node:
        return []
    if isinstance(node[0], list):
        n = 0
        while n < len(node) and isinstance(node[n], list):
            n += 1
        disposition = node[n+2] if len(node) > n+2 else None
        if isinstance(disposition, list) and str(disposition[0]).lower() == "attachment":
            return []
        sections = []
        for i, child in enumerate(node[:n], 1):
            sections.extend(body_sections(child, f"{prefix}.{i}" if prefix else str(i)))
        if str(node[n]).lower() == "alternative":
            plain = [part for part in sections if part[1] == "plain"]
            return plain or sections[:1]
        return sections
    if len(node) < 7 or str(node[0]).lower() != "text" or str(node[1]).lower() not in ("plain", "html"):
        return []
    params = node[2] or []
    if any(str(k).lower() in ("name", "filename") for k in params[::2]):
        return []
    disposition = node[9] if len(node) > 9 else None
    if isinstance(disposition, list):
        if str(disposition[0]).lower() == "attachment":
            return []
        if len(disposition) > 1 and disposition[1]:
            if any(str(k).lower() in ("name", "filename") for k in disposition[1][::2]):
                return []
    return [(prefix or "1", str(node[1]).lower())]


def fetch_literal(mail, uid, section):
    status, data = mail.uid("fetch", uid, f"(BODY.PEEK[{section}]<0.131073>)")
    if status != "OK":
        raise GmailReadError("Falha ao ler texto; tenta novamente.")
    for entry in data or []:
        if isinstance(entry, tuple) and isinstance(entry[1], bytes):
            return entry[1]
    raise GmailReadError("Texto esperado não recebido.")


BLOCK_TAGS = {"br", "p", "div", "li", "ul", "ol", "tr", "td", "th", "table", "blockquote", "hr",
              "h1", "h2", "h3", "h4", "h5", "h6"}
HIDDEN_TAGS = {"script", "style", "title"}


def html_to_text(markup):
    """Visible text only; every block and table cell on its own line (portal emails are tables)."""
    from html.parser import HTMLParser
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
            self.hidden = 0
        def handle_starttag(self, tag, attrs):
            if tag in HIDDEN_TAGS:
                self.hidden += 1
            elif tag in BLOCK_TAGS:
                self.parts.append("\n")
        def handle_endtag(self, tag):
            if tag in HIDDEN_TAGS:
                self.hidden = max(0, self.hidden-1)
            elif tag in BLOCK_TAGS:
                self.parts.append("\n")
        def handle_data(self, text):
            if not self.hidden:
                # Source newlines are just spaces in HTML; only block tags break lines.
                self.parts.append(re.sub(r"\s+", " ", text))
    parser = Text()
    parser.feed(markup)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def fetch_text_only(mail, uid, structure_bytes):
    """The text parts only (plain, or HTML turned into text), never attachments; long texts are cut and flagged."""
    sections = body_sections(parse_structure(structure_bytes))
    texts = []
    truncated = len(sections) > 10
    for section, kind in sections[:10]:
        mime = fetch_literal(mail, uid, section + ".MIME")
        payload = fetch_literal(mail, uid, section)
        truncated |= len(payload) > 131072
        msg = BytesParser(policy=policy.default).parsebytes(mime + b"\r\n" + payload[:131072])
        try:
            text = msg.get_content()
        except (LookupError, ValueError):
            text = (msg.get_payload(decode=True) or b"").decode("utf-8", "replace")
        if not isinstance(text, str):
            continue
        if kind == "html":
            text = html_to_text(text)
        texts.append(text.strip())
    joined = "\n\n".join(texts)
    return joined[:100000], truncated or len(joined) > 100000


# Replies: one plain-text message per email, threaded under the original.
class GmailReplyError(RuntimeError):
    pass

def first_address(value):
    if not isinstance(value, list):
        return "", ""
    for item in value:
        if isinstance(item, dict) and str(item.get("email", "")).strip():
            return str(item.get("name", "")).strip(), str(item["email"]).strip()
    return "", ""

def choose_recipient(item, account):
    name, address = first_address(item.get("reply_to"))
    if not address:
        name, address = first_address(item.get("from"))
    if not address:
        raise GmailReplyError("Sem Reply-To/From.")
    if address.casefold() == account.casefold():
        raise GmailReplyError("O destinatário calculado é a própria conta.")
    return name, address

def build_reply(item, account, sender_name="", subject=None):
    """The reply to one email. The From name and, for a portal lead, the subject come from the voice."""
    text = str(item.get("reply_text", "")).strip()
    if not text:
        raise GmailReplyError("reply_text vazio.")

    if "recipient" in item:
        # Property emails: the recipient was fixed at READ by the profile rules; no fallback.
        name, recipient = first_address([item["recipient"]])
        if not recipient or recipient.casefold() == account.casefold():
            raise GmailReplyError("Sem destinatário válido; revê manualmente.")
    else:
        name, recipient = choose_recipient(item, account)
    if subject is None:
        # Answering under the customer's own subject: keep their thread.
        subject = str(item.get("subject", "")).strip()
        if not subject.lower().startswith("re:"):
            subject = "Re: " + subject if subject else "Re:"
    else:
        subject = " ".join(str(subject).split())

    msg = EmailMessage()
    msg["Date"] = formatdate(localtime=True)
    msg["From"] = formataddr((sender_name, account)) if sender_name else account
    msg["To"] = formataddr((name, recipient)) if name else recipient
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="gmail.com")

    original_id = str(item.get("message_id", "")).strip()
    refs = str(item.get("references", "")).strip().split()
    if original_id:
        msg["In-Reply-To"] = original_id
        if original_id not in refs:
            refs.append(original_id)
    if refs:
        msg["References"] = " ".join(refs)

    msg.set_content(text)
    return msg, recipient


def build_digest(account, recipient, subject, text):
    """The daily status digest: a plain new message from the account to the owner's own address.

    Never a reply (no In-Reply-To/References): it is not part of any customer's conversation.
    """
    if not text.strip():
        raise GmailReplyError("reply_text vazio.")
    if recipient.casefold() == account.casefold():
        raise GmailReplyError("O destinatário calculado é a própria conta.")
    msg = EmailMessage()
    msg["Date"] = formatdate(localtime=True)
    msg["From"] = account
    msg["To"] = recipient
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    msg.set_content(text)
    return msg
