"""Terminal setup of the voice and the properties.

It writes the files a future frontend will edit: voice.json, properties/<REF>/profile.json and the
knowledge texts in properties/<REF>/knowledge/. Nothing here reads or sends email.
"""
from datetime import date
from pathlib import Path
from .properties import EMAIL, KNOWLEDGE_RULE, REFERENCE, describe, load_profiles, load_voice
from .storage import load_json, save_json

TEMPLATES = Path(__file__).resolve().parent.parent / "apalace/rent"
STARTER = """# Conhecimento do imóvel {ref}

<!-- Escreve aqui os factos que o ChatGPT pode usar nas respostas. O texto dentro destes
comentários é ignorado, tal como as secções vazias. Podes criar mais ficheiros .md nesta pasta. -->

## Condições do arrendamento
<!-- Ex.: renda, caução, fiador, duração mínima, despesas incluídas. -->

## Regras da casa
<!-- Ex.: animais, fumadores, número de pessoas. -->

## Equipamento e estado
<!-- Ex.: mobília, eletrodomésticos, aquecimento, estacionamento. -->

## Zona e transportes
<!-- Ex.: escolas, comércio, transportes. -->

## Perguntas frequentes
<!-- Ex.: «Aceita animais?» e a resposta. -->
"""


def ask(label, default=""):
    return input(f"{label} [{default}]: ").strip() or default


def ask_valid(label, default, valid, error):
    while not valid(value := ask(label, default)):
        print(error)
    return value


def yes(label, default=False):
    answer = input(f"{label} [{'S/n' if default else 's/N'}]: ").strip().lower()
    return answer.startswith("s") if answer else default


def ask_choice(label, options, current):
    for name, option in options.items():
        print(f"  {name}: {describe(option)}")
    return ask_valid(f"{label} ({' / '.join(options)})", current or "", lambda v: v in options,
                     "Escolhe uma das opções indicadas.")


def ask_text(label, current):
    """Multi-line text: Enter on the first line keeps it; a line with only "." ends the new text."""
    print(f"\n{label}\nAtual: {current or '(vazio)'}\n"
          "Enter mantém. Para mudar, escreve o texto e termina com uma linha só com um ponto (.).")
    lines = []
    while (line := input()).strip() != ".":
        if not lines and not line.strip():
            return current
        lines.append(line)
    return "\n".join(lines).strip()


def configure_voice(folder):
    """Greeting, languages and closing are chosen among the options in voice.json; the signature is typed."""
    path = Path(folder) / "voice.json"
    voice = load_json(path, None)
    if voice is None:
        # A new owner starts from the published options, with nothing chosen and no signature.
        voice = load_json(TEMPLATES / "voice.json", {})
        for key in ("greeting", "languages", "closing"):
            voice["style"][key].update(selected=None, status="awaiting_owner_choice")
        voice["style"]["signature"]["text"] = ""
    style = voice["style"]
    print("\nVoz e estilo, comuns a todos os imóveis.")
    for key, label in (("greeting", "Saudação"), ("languages", "Idiomas"), ("closing", "Fecho")):
        style[key].update(selected=ask_choice(label, style[key]["options"], style[key].get("selected")),
                          status="configured")
    signature = ask_valid("Texto da assinatura", style["signature"].get("text", ""), str.strip,
                          "A assinatura é obrigatória.")
    style["signature"].update(text=signature.strip(), status="configured")
    save_json(path, voice)
    load_voice(folder)


def example_profile(folder):
    local = Path(folder) / "properties" / "profile.example.json"
    return load_json(local if local.exists() else TEMPLATES / "properties/profile.example.json", {})


def configure_property(folder, account, ref):
    """Listing data, base context prompt, interaction prompts and RAG prompt of one property."""
    path = Path(folder) / "properties" / ref / "profile.json"
    profile = load_json(path, None)
    example = None
    if profile is None:
        if not yes(f"O imóvel {ref} não existe. Criar?", True):
            return
        # Same rules as the published example; only this property's identifiers change.
        profile = example_profile(folder)
        example = dict(profile["property"])
        profile["account"] = account
        profile["property"].update(reference=ref, advertiser="", listing_id="", listing_url="", description="",
                                   advertised_rent_eur=None, information_source=f"Setup em {date.today().isoformat()}")
        profile["match"]["subject_property_reference_equals"] = ref
        profile["reply"]["never_reply_to"] = []
    prop, match, reply = profile["property"], profile["match"], profile["reply"]
    prompts = reply.setdefault("prompts", {})

    print(f"\nImóvel {ref}: dados do anúncio.")
    sender = ask_valid("Remetente dos avisos do portal", match.get("from_address_equals") or "reply@idealista.pt",
                       EMAIL.fullmatch, "Indica um endereço de email.")
    listing = ask_valid("Código do anúncio", str(prop.get("listing_id") or ""),
                        lambda v: not v or v.isdigit(), "Usa só algarismos.")
    url = ask("Link do anúncio", prop.get("listing_url") or "")
    description = ask_valid("Descrição curta do imóvel", prop.get("description") or "", bool,
                            "A descrição é obrigatória.")
    rent = ask_valid("Renda anunciada em euros", str(prop.get("advertised_rent_eur") or ""),
                     lambda v: not v or v.isdigit(), "Usa só algarismos.")
    prop.update(listing_id=listing, listing_url=url, description=description,
                advertised_rent_eur=int(rent) if rent else None)
    match.update(from_address_equals=sender, if_body_listing_id_present_must_equal=listing or None)
    reply["never_reply_to"] = list(dict.fromkeys([*reply.get("never_reply_to", []), sender, account]))

    general = prompts.setdefault("general", {})
    default = general.get("text") or ""
    if example:
        default = default.replace(example["reference"], ref).replace(example["description"], description)
    while not (text := ask_text("Prompt base de contexto do imóvel", default)):
        print("O prompt base é obrigatório.")
    general.update(status="configured", text=text)
    for key, label in (("first_interaction", "1.ª"), ("second_interaction", "2.ª")):
        prompt = prompts.setdefault(key, {})
        prompt["text"] = ask_text(f"Prompt da {label} interação (vazio = o ChatGPT avisa-te e aguarda)",
                                  prompt.get("text") or "") or None
        if key == "first_interaction":
            prompt["reply_template"] = ask_text("Texto base da 1.ª resposta (opcional)",
                                                prompt.get("reply_template") or "") or None
        prompt["status"] = "configured" if prompt["text"] else "awaiting_owner"
    knowledge = prompts.setdefault("knowledge", {})
    rule = ask_text("Prompt de RAG: como usar a base de conhecimento", knowledge.get("text") or KNOWLEDGE_RULE)
    knowledge.update(status="configured", text=rule or KNOWLEDGE_RULE)
    save_json(path, profile)

    base = path.parent / "knowledge"
    if not base.exists():
        base.mkdir(mode=0o700)
        starter = base / "imovel.md"
        starter.write_text(STARTER.format(ref=ref), encoding="utf-8")
        starter.chmod(0o600)
    print(f"Base de conhecimento (RAG): escreve os factos em ficheiros .md em {base}")


def configure_properties(folder, account):
    existing = sorted(path.parent.name for path in (Path(folder) / "properties").glob("*/profile.json"))
    print("\nImóveis: cada um tem o seu perfil, a sua fila e a sua base de conhecimento."
          + (f" Configurados: {', '.join(existing)}." if existing else ""))
    while ref := input("Referência do imóvel a configurar (Enter termina): ").strip():
        if REFERENCE.fullmatch(ref):
            configure_property(folder, account, ref)
        else:
            print("Usa só letras, algarismos, _ ou - (até 64 caracteres).")
    load_profiles(folder, account)
