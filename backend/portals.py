"""The portal the leads come from (02/10): everything particular to it in one place, changeable in the Oficina — who
sends its notices, how its subject names the customer, its listing code and link, and its call notices. Today the
Idealista; the same portal changing its emails, or another portal, is a change of these fields, not of the code.
Stored as the Oficina's changes only (config.json "portal"); the rest follows these defaults. Pure: no files."""
import re

DEFAULT = {
    "nome": "Idealista",
    "remetente_pedidos": "reply@idealista.pt",
    "remetente_chamadas": "naoresponder@idealista.pt",
    "assunto_nome": r"\bde (?:teste de )?(.+?) sobre o teu imóvel",
    "codigo_anuncio": r"Código do anúncio:\s*(\d+)",
    "link_anuncio": r"https://(?:www\.)?idealista\.pt/(?:imovel/)?(\d+)/?(?:[?#].*)?",
    "link_anuncio_forma": "https://www.idealista.pt/imovel/{codigo}/",
    "assunto_chamada": r"Chamada (?:atendida|n[aã]o respondida) de um interessado",
    "chamada_telefone": r"n[úu]mero de telefone [ée]:\s*\+?(\d[\d ]{7,15}\d)",
    "chamada_data": r"Data e hora:\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2}(?::\d{2})?)",
    "chamada_estado": r"Estado:\s*([^\n\r]+)",
    "chamada_atendida": r"^\s*atendida",
    "chamada_duracao": r"Dura[çc][ãa]o em segundos:\s*(\d+)",
    "chamada_anuncio": r"an[úu]ncio contactado:\s*(\d+)",
    "chamada_ref": r"an[úu]ncio contactado:\s*\d+\s*-\s*Ref\.\s*([A-Za-z0-9_-]+)",
}
# What each field is, for the Oficina, in the order shown
LABELS = {
    "nome": "Nome do portal",
    "remetente_pedidos": "Quem envia os avisos de pedidos (email)",
    "remetente_chamadas": "Quem envia os avisos de chamadas (email)",
    "assunto_nome": "Nome do cliente no assunto de um pedido (regra; o grupo 1 é o nome)",
    "codigo_anuncio": "Código do anúncio no aviso (regra; o grupo 1 é o código)",
    "link_anuncio": "Link de um anúncio (regra; o grupo 1 é o código)",
    "link_anuncio_forma": "Forma do link de um anúncio ({codigo} é o código)",
    "assunto_chamada": "Assunto de um aviso de chamada (regra)",
    "chamada_telefone": "Telefone de quem ligou (regra; grupo 1)",
    "chamada_data": "Data e hora da chamada (regra; grupo 1, dd/mm/aaaa hh:mm)",
    "chamada_estado": "Estado da chamada (regra; grupo 1)",
    "chamada_atendida": "Estado que quer dizer «atendida» (regra)",
    "chamada_duracao": "Duração em segundos (regra; grupo 1)",
    "chamada_anuncio": "Código do anúncio contactado (regra; grupo 1)",
    "chamada_ref": "Referência do imóvel contactado (regra; grupo 1)",
}
EMAILS = ("remetente_pedidos", "remetente_chamadas")
PLAIN = ("nome", "link_anuncio_forma") + EMAILS
EMAIL = re.compile(r"[^@\s<>(),;:\"\[\]]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")


def merged(changes):
    """The portal as it stands: the defaults with the Oficina's changes over them."""
    return {**DEFAULT, **{key: value for key, value in (changes or {}).items() if key in DEFAULT and value}}


def check(fields):
    """The Oficina's changes, checked: only the known fields, emails that are emails, rules that compile and capture
    what they must (a group 1 where a value is read), the link's form with its {codigo}. Returns only what differs
    from the defaults."""
    changes = {}
    for key, value in (fields or {}).items():
        if key not in DEFAULT:
            continue
        value = str(value or "").strip()
        if not value or value == DEFAULT[key]:
            continue
        if len(value) > 300:
            raise ValueError(f"«{LABELS[key]}»: até 300 caracteres.")
        if key in EMAILS and not EMAIL.fullmatch(value):
            raise ValueError(f"«{LABELS[key]}» tem de ser um endereço de email.")
        if key == "link_anuncio_forma" and "{codigo}" not in value:
            raise ValueError("A forma do link tem de ter {codigo}, onde entra o código do anúncio.")
        if key not in PLAIN:
            try:
                rule = re.compile(value)
            except re.error as exc:
                raise ValueError(f"«{LABELS[key]}»: a regra não é válida ({exc}).") from None
            if "grupo 1" in LABELS[key] and rule.groups < 1:
                raise ValueError(f"«{LABELS[key]}»: falta o grupo 1, entre parênteses, com o valor a ler.")
        changes[key] = value
    return changes
