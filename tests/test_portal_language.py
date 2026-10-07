"""06/10: the flag the portal puts before the customer's name («🇬🇧 Nome») is the language they chose there: the replies
use it until the customer writes in another one."""
from backend.ai import reply_prompt
from backend.rules import flag_language
from test_properties import CUSTOMER, REF, draft_and_send, lead, read, service  # noqa: F401 (service is a fixture)


def flagged(key, flag="🇬🇧"):
    message = lead(key)
    message["body_text"] = message["body_text"].replace("\nAna Exemplo\n", f"\n{flag} Ana Exemplo\n", 1)
    return message


def test_the_flag_is_a_language():
    assert flag_language("Tens uma nova mensagem que aguarda resposta\n🇬🇧 Ana\nVer perfil") == "en"
    assert (flag_language("🇪🇸 Ana"), flag_language("🇧🇷 Ana"), flag_language("🇩🇪 Ana")) == ("es", "pt", "de")
    assert flag_language("Ana Exemplo\nVer perfil") is None
    assert flag_language("Ana\nBom dia, gosto muito 🇬🇧") is None  # only a flag that starts a line (the name's)


def test_the_portal_language_reaches_the_card_the_prompt_and_the_conversation(service):
    read(service, [flagged("1")])
    queue = service.pending()["properties"][0]
    [card] = queue["emails"]
    assert card["customer"]["portal_lang"] == "en" and card["portal_lang"] == "en"
    assert card["customer"]["name"] == "Ana Exemplo"  # the flag is not part of the name
    prompt = reply_prompt(queue, ["1"])
    assert "Língua que o cliente escolheu no portal (a bandeira do aviso): en" in prompt
    assert "se ele já escreveu noutra, continua na língua em que ele escreve" in prompt
    draft_and_send(service, "1", "Hello.")
    assert service.load(REF)["conversations"][CUSTOMER]["portal_lang"] == "en"


def test_no_flag_no_language(service):
    read(service, [lead("1")])
    [card] = service.pending()["properties"][0]["emails"]
    assert "portal_lang" not in card["customer"] and "portal_lang" not in card


def test_the_round_knows_the_portal_language(service):
    # 06/10: two customers of a round had never written a word: «escreve em und», and they got the English
    from backend.ai import round_prompt
    from test_visits import DAY
    read(service, [flagged("1", "🇪🇸")])
    draft_and_send(service, "1", "Hola.")
    service.propose_visits(REF, DAY, "17:00", "19:00", [CUSTOMER])
    queue = service.pending()["properties"][0]
    [proposal] = [email for email in queue["emails"] if email.get("visit_window")]
    prompt = round_prompt(queue, [proposal["id"]])
    assert "Língua que escolheu no portal: es" in prompt and "Sem nenhuma mensagem dele, é a que escolheu no portal" in prompt
