"""02/10: what is particular to the portal (Idealista today) lives in one place, changeable in the Oficina: who sends its
notices, how its subject names the customer, its listing code and link, and its call notices."""
import pytest
from backend import rules
from test_properties import service  # noqa: F401 (service is a fixture)

CALL = {"from": [{"name": "idealista", "email": "naoresponder@idealista.pt"}],
        "subject": "Chamada nao respondida de um interessado nos teus anuncios",
        "body_text": "Uma pessoa interessada nos teus anúncios realizou uma chamada:\nO seu número de telefone é: 351910000001\n"
                     "Data e hora: 30/09/2026 16:18:14\nEstado: nao respondida\nDuração em segundos: 0\n"
                     "Recebida neste nº de telefone de controlo de chamadas: 210000000\n"
                     "Código do anúncio contactado: 12345678 - Ref. AP_EXEMPLO\n"}


def test_a_call_notice_is_read_with_its_own_time_and_answered_or_not(service):
    service.config()  # the portal as it stands (the defaults)
    assert rules.parse_call(CALL) == {"phone": "351910000001", "at": "2026-09-30 16:18:14", "state": "nao respondida",
                                      "answered": False, "seconds": 0, "listing": "12345678", "ref": "AP_EXEMPLO"}
    answered = {**CALL, "subject": "Chamada atendida de um interessado nos teus anuncios",
                "body_text": CALL["body_text"].split("Código")[0].replace("nao respondida", "atendida").replace(": 0", ": 44")}
    found = rules.parse_call(answered)
    assert (found["answered"], found["seconds"], found["listing"], found["ref"]) == (True, 44, None, None)
    assert rules.parse_call({**CALL, "from": [{"email": "reply@idealista.pt"}]}) is None  # another sender: not a call notice


def test_the_portal_changes_in_the_oficina_and_goes_back_to_its_defaults(service):
    with pytest.raises(ValueError, match="endereço de email"):
        service.save_portal({"remetente_chamadas": "não é email"})
    with pytest.raises(ValueError, match="falta o grupo 1"):
        service.save_portal({"chamada_telefone": r"telefone: \d+"})
    with pytest.raises(ValueError, match="não é válida"):
        service.save_portal({"assunto_nome": "(sem fechar"})
    view = service.save_portal({"remetente_chamadas": "chamadas@portal.example", "nome": "Idealista"})
    assert view["changed"] == ["remetente_chamadas"] and view["fields"]["remetente_chamadas"] == "chamadas@portal.example"
    service.config()
    assert rules.parse_call(CALL) is None  # the old sender no longer counts
    assert rules.parse_call({**CALL, "from": [{"email": "chamadas@portal.example"}]})["phone"] == "351910000001"
    assert service.save_portal({}, reset=True)["changed"] == []
    service.config()
    assert rules.parse_call(CALL) is not None
    assert service.settings()["portal_sender"] == "reply@idealista.pt"
