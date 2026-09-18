from bot_mail.gmail import parse_structure, body_sections, fetch_text_only


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
