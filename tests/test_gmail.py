from unittest.mock import patch
from backend.mail import parse_structure, body_sections, fetch_text_only, parse_addresses, read_messages


def test_selects_text_without_attachments():
    raw = b'''1 (BODYSTRUCTURE (("TEXT" "PLAIN" ("CHARSET" "UTF-8") NIL NIL "7BIT" 10 1 NIL NIL)("APPLICATION" "PDF" ("NAME" "file.pdf") NIL NIL "BASE64" 100 NIL ("ATTACHMENT" ("FILENAME" "file.pdf"))) "MIXED"))'''
    assert body_sections(parse_structure(raw)) == [("1", "plain")]


def test_alternative_and_attached_text():
    raw = b'''BODYSTRUCTURE (("TEXT" "PLAIN" NIL NIL NIL "7BIT" 10 1 NIL NIL)("TEXT" "HTML" NIL NIL NIL "7BIT" 30 1 NIL NIL) "ALTERNATIVE")'''
    assert body_sections(parse_structure(raw)) == [("1", "plain")]
    raw = b'''BODYSTRUCTURE ("TEXT" "PLAIN" NIL NIL NIL "7BIT" 10 1 NIL ("ATTACHMENT" ("FILENAME" "secret.txt")))'''
    assert body_sections(parse_structure(raw)) == []


def test_fetch_only_selected_parts():
    class Mail:
        calls = []
        def uid(self, cmd, uid, spec):
            self.calls.append(spec)
            payload = b"Content-Type: text/plain; charset=utf-8\r\n" if ".MIME" in spec else b"Hello"
            return "OK", [(b"", payload)]
    mail = Mail()
    raw = b'''BODYSTRUCTURE (("TEXT" "PLAIN" NIL NIL NIL "7BIT" 10 1 NIL NIL)("APPLICATION" "PDF" NIL NIL NIL "BASE64" 100 NIL NIL) "MIXED")'''
    assert fetch_text_only(mail, b"1", raw) == ("Hello", False)
    assert mail.calls == ["(BODY.PEEK[1.MIME]<0.131073>)", "(BODY.PEEK[1]<0.131073>)"]


def test_parse_addresses_decodes_names():
    assert parse_addresses(["=?utf-8?q?Ana_Exemplo?= <ana@example.com>, b@example.com"]) == [
        {"name": "Ana Exemplo", "email": "ana@example.com"}, {"name": "", "email": "b@example.com"}]


LEAD = ("From: idealista <reply@idealista.pt>\r\nTo: owner@example.com\r\nReply-To: ana.exemplo@example.com\r\n"
        "Subject: =?utf-8?q?Nova_mensagem_de_Ana_Exemplo_sobre_o_teu_im=C3=B3vel?=\r\n"
        "Message-ID: <lead@example.com>\r\nDate: Thu, 17 Sep 2026 08:58:43 +0100\r\n\r\n").encode()
OTHER = b"From: Loja <news@example.com>\r\nTo: owner@example.com\r\nSubject: Promo\r\nMessage-ID: <n@example.com>\r\n\r\n"
HTML = ("<html><head><title>idealista</title><style>td {color: red}</style></head><body><table>"
        "<tr><td>Tens uma nova mensagem</td></tr><tr><td>Ana Exemplo</td></tr>"
        "<tr><td>900 000 001</td><td>ana.exemplo@example.com</td></tr>"
        "<tr><td>Bom dia,\n   gostaria de visitar.</td></tr></table></body></html>").encode()


def test_read_messages_with_fake_imap_fetches_text_only_when_accepted():
    structure = b'BODYSTRUCTURE ("TEXT" "HTML" ("CHARSET" "utf-8") NIL NIL "8BIT" 300 1 NIL NIL NIL NIL)'
    class Mail:
        calls = []
        def list(self):
            return "OK", [b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"']
        def select(self, box, readonly=True):
            return "OK", [b"2"]
        def uid(self, command, *args):
            if command == "search":
                return "OK", [b"1 2"]
            uid, spec = args
            self.calls.append((uid, spec))
            if "HEADER" in spec:
                header = LEAD if uid == b"1" else OTHER
                prefix = b"%s (X-GM-THRID 70 X-GM-MSGID 8%s %s BODY[HEADER] {%d}" % (uid, uid, structure, len(header))
                return "OK", [(prefix, header), b")"]
            if ".MIME" in spec:
                return "OK", [(b"", b"Content-Type: text/html; charset=utf-8\r\nContent-Transfer-Encoding: 8bit\r\n")]
            return "OK", [(b"", HTML)]
        def logout(self):
            pass
    mail = Mail()
    with patch("backend.mail.connect", return_value=mail):
        items, scanned, box = read_messages("owner@example.com", "x", "", "2026-09-16", "2026-09-18",
                                            accept=lambda item: item["from"][0]["email"] == "reply@idealista.pt")
    assert (scanned, box, len(items)) == (2, "[Gmail]/All Mail", 1)
    lead = items[0]
    assert (lead["gmail_message_id"], lead["thread_id"]) == ("81", "70")
    assert lead["reply_to"] == [{"name": "", "email": "ana.exemplo@example.com"}]
    assert lead["subject"] == "Nova mensagem de Ana Exemplo sobre o teu imóvel"
    assert [line for line in lead["body_text"].splitlines() if line] == [
        "Tens uma nova mensagem", "Ana Exemplo", "900 000 001", "ana.exemplo@example.com", "Bom dia, gostaria de visitar."]
    # The unrelated message was never downloaded beyond its headers.
    assert [spec for uid, spec in mail.calls if uid == b"2"] == ["(BODY.PEEK[HEADER] BODYSTRUCTURE X-GM-THRID X-GM-MSGID)"]


OWN = ("From: Equipa <owner@example.com>\r\nTo: ana.exemplo@example.com\r\nSubject: Re: Nova mensagem\r\n"
       "Message-ID: <direct@example.com>\r\nDate: Thu, 17 Sep 2026 10:00:00 +0100\r\n\r\n").encode()


def fake_imap(boxes):
    """boxes: mailbox name → {uid: raw headers}; the LIST flags mark All Mail and Sent as Gmail does."""
    structure = b'BODYSTRUCTURE ("TEXT" "PLAIN" ("CHARSET" "utf-8") NIL NIL "8BIT" 30 1 NIL NIL NIL NIL)'
    class Mail:
        selected, calls = None, []
        def list(self):
            return "OK", [b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"', b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Enviados"']
        def select(self, box, readonly=True):
            self.selected = box.strip('"')
            return "OK", [b"1"]
        def uid(self, command, *args):
            messages = boxes[self.selected]
            if command == "search":
                return "OK", [b" ".join(messages)]
            uid, spec = args
            self.calls.append((self.selected, uid, spec))
            if "HEADER" in spec:
                header = messages[uid]
                prefix = b"%s (X-GM-THRID 70 X-GM-MSGID 9%s %s BODY[HEADER] {%d}" % (uid, uid, structure, len(header))
                return "OK", [(prefix, header), b")"]
            if ".MIME" in spec:
                return "OK", [(b"", b"Content-Type: text/plain; charset=utf-8\r\n")]
            return "OK", [(b"", "Pode visitar amanhã.".encode())]
        def logout(self):
            pass
    return Mail()


def test_read_messages_hands_over_the_owners_own_replies_apart():
    # All Mail holds both: the customer's email comes back as incoming, the owner's reply only as outgoing.
    mail = fake_imap({"[Gmail]/All Mail": {b"1": LEAD, b"2": OWN}})
    outgoing = []
    with patch("backend.mail.connect", return_value=mail):
        items, scanned, box = read_messages("owner@example.com", "x", "", "2026-09-16", "2026-09-18",
                                            accept=lambda item: True, outgoing=outgoing,
                                            accept_outgoing=lambda item: item["to"][0]["email"] == "ana.exemplo@example.com")
    assert [item["message_id"] for item in items] == ["<lead@example.com>"]
    assert [(item["message_id"], item["body_text"]) for item in outgoing] == [("<direct@example.com>", "Pode visitar amanhã.")]
    # Without the outgoing list, the owner's own mail is skipped exactly as before.
    with patch("backend.mail.connect", return_value=fake_imap({"[Gmail]/All Mail": {b"1": LEAD, b"2": OWN}})):
        items, _, _ = read_messages("owner@example.com", "x", "", "2026-09-16", "2026-09-18", accept=lambda item: True)
    assert [item["message_id"] for item in items] == ["<lead@example.com>"]


def test_with_the_inbox_only_the_sent_folder_is_read_too_whatever_its_language():
    mail = fake_imap({"INBOX": {b"1": LEAD}, "[Gmail]/Enviados": {b"7": OWN}})
    outgoing = []
    with patch("backend.mail.connect", return_value=mail):
        items, scanned, box = read_messages("owner@example.com", "x", "", "2026-09-16", "2026-09-18", mailbox="inbox",
                                            accept=lambda item: True, outgoing=outgoing, accept_outgoing=lambda item: True)
    assert (box, scanned, len(items)) == ("INBOX", 1, 1)
    assert [item["message_id"] for item in outgoing] == ["<direct@example.com>"]
