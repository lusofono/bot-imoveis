"""A data folder with fictitious properties and leads, for working on the page without real customers.

`bot-mail demo <pasta>` creates it; open it with `bot-mail --instance <pasta> web`. Never point a design
tool or another assistant at data/: that folder holds real customers' names, emails and phones.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import struct
import zlib
from .rules import prepare
from .store import load_json, save_json, write_photo

TEMPLATES = Path(__file__).resolve().parent / "templates"
ACCOUNT = "demo@example.com"
PROPERTIES = [("DEMO_T3_LISBOA", "Apartamento T3 na Rua Exemplo, Lisboa", 1500, "10000001", (47, 91, 234)),
              ("DEMO_T1_PORTO", "Apartamento T1 na Avenida Teste, Porto", 850, "10000002", (6, 118, 71))]
# (name, phone, message, days ago, state): state is pending, draft, blocked or answered.
LEADS = [("Ana Exemplo", "900 000 001", "Bom dia, gostaria de visitar o imóvel. Pode ser ao fim da tarde?", 0, "pending"),
         ("Bruno Teste", "900 000 002", "Olá, o apartamento ainda está disponível? Somos um casal com um filho.", 1, "draft"),
         ("Carla Demo", "900 000 003", "Boa tarde, aceitam animais de estimação?", 2, "pending"),
         ("Duarte Ficticio", "900 000 004", "Queria saber as condições do arrendamento.", 3, "blocked"),
         ("Eva Modelo", "900 000 005", "Posso marcar uma visita para sábado?", 5, "answered")]


def picture(color, width=320, height=200):
    """A plain PNG gradient, so the page has a photo to show without any real image."""
    rows = b"".join(b"\x00" + bytes(channel for x in range(width)
                                     for channel in (min(255, color[0] + y // 3), min(255, color[1] + y // 3),
                                                     min(255, color[2] + x // 6)))
                    for y in range(height))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def lead(key, ref, listing, name, phone, message, date, reply_to=True):
    """A portal notice as the Gmail reader returns it (fictitious customer)."""
    email = name.lower().replace(" ", ".") + "@example.com"
    body = "\n".join(["Tens uma nova mensagem que aguarda resposta", name, phone, email, message,
                      f"Ref. {ref} | Anunciante Exemplo", f"Código do anúncio: {listing}"])
    return {"uid": key, "gmail_message_id": key, "thread_id": f"t{key}", "date": date.isoformat(),
            "from": [{"name": "idealista", "email": "reply@idealista.pt"}], "to": [{"name": "", "email": ACCOUNT}],
            "cc": [], "reply_to": [{"name": "", "email": email}] if reply_to else [],
            "subject": f"Nova mensagem de {name} sobre o teu imóvel, com ref: {ref} | Anunciante Exemplo",
            "message_id": f"<{key}@portal.example>", "in_reply_to": "", "references": "",
            "body_text": body, "body_truncated": False}


def create_demo(folder):
    """Creates a new folder with two fictitious properties, their leads and a photo. Never overwrites."""
    folder = Path(folder).resolve()
    if folder.exists():
        raise ValueError("O destino já existe; escolhe uma pasta nova para a demonstração.")
    now = datetime.now(timezone.utc)
    save_json(folder / "config.json", {**load_json(TEMPLATES / "config.example.json", {}),
                                        "account": ACCOUNT, "lookback_days": 3})
    save_json(folder / "voice.json", load_json(TEMPLATES / "voice.example.json", {}))
    events = []
    for number, (ref, description, rent, listing, color) in enumerate(PROPERTIES):
        profile = load_json(TEMPLATES / "profile.example.json", {})
        example = profile["property"]
        general = profile["reply"]["prompts"]["general"]
        general["text"] = general["text"].replace(example["reference"], ref).replace(example["description"], description)
        profile["account"] = ACCOUNT
        profile["property"].update(reference=ref, description=description, advertised_rent_eur=rent, listing_id=listing,
                                   listing_url=f"https://www.idealista.pt/imovel/{listing}/", advertiser="Anunciante Exemplo",
                                   information_source="Demonstração com dados fictícios.")
        profile["match"].update(subject_property_reference_equals=ref, if_body_listing_id_present_must_equal=listing)
        profile["reply"]["never_reply_to"] = ["reply@idealista.pt", ACCOUNT]
        save_json(folder / "properties" / ref / "profile.json", profile)
        if number == 0:
            write_photo(folder, ref, "png", picture(color))
        emails, conversations = [], {}
        for index, (name, phone, message, days, state) in enumerate(LEADS[number:] if number else LEADS):
            key = f"{number}{index}"
            item = lead(key, ref, listing, name, phone, message, now - timedelta(days=days, hours=index * 3),
                        reply_to=state != "blocked")
            item.update(prepare(item, "lead", None, profile, ACCOUNT), kind="lead", id=key, send_reply=False,
                        reply_text="", reply_status="pending")
            if state == "draft":
                item.update(reply_text=f"Caro {name.split()[0]},\n\nObrigado pelo seu contacto. (rascunho de exemplo)",
                            reply_status="draft")
            if state == "answered":
                conversations[item["recipient"]["email"].casefold()] = {
                    "stage": 1, "sent_message_ids": [f"<sent{key}@example.com>"], "thread_ids": [item["thread_id"]],
                    "last_sent_at": (now - timedelta(days=days - 1)).isoformat()}
                events.append({"at": (now - timedelta(days=days - 1)).isoformat(), "event": "send", "message_id": key,
                               "status": "sent", "waited_hours": 20.0 + index})
                continue
            emails.append(item)
        save_json(folder / "properties" / ref / "queue.json", {
            "account": ACCOUNT, "created_at": now.isoformat(), "revision": 1, "emails": emails,
            "replied_message_ids": [event["message_id"] for event in events if event["message_id"][0] == str(number)],
            "dismissed_message_ids": [], "property": ref, "conversations": conversations,
            "last_read_at": now.isoformat(), "stats": {"emails_in_queue": len(emails)}})
    (folder / "logs").mkdir(mode=0o700)
    fd = os.open(folder / "logs" / "events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.writelines(json.dumps(event) + "\n" for event in events)
    return folder
