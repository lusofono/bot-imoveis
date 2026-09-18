#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, formatdate

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

def build_reply(item, account):
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
    subject = str(item.get("subject", "")).strip()
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject if subject else "Re:"

    msg = EmailMessage()
    msg["Date"] = formatdate(localtime=True)
    msg["From"] = account
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
