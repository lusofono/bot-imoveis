"""07/10: properties for sale — their own prompts (the interaction ones per property, a copy of the common ones), a
buyer's file (what they look for, what for, when they can visit: never income, household or a contract), a buyer's
documents and a listing read with a price."""
import json
import pytest
from backend.ai import (LATER_REPLY_RULE, REPLY_FORMAT, RENTAL_FICHA_JSON, SALE_FICHA_JSON, SALE_PROMPTS, listing_text_prompt,
                        reply_prompt)
from backend.rules import clean_property, documents_summary, ficha_summary
from backend.store import load_json, save_json
from test_properties import REF, lead, read, service  # noqa: F401 (service is a fixture)


def profile(service, ref):
    return load_json(service.folder / "properties" / ref / "profile.json", {})


def prompt(service, ref, key):
    return profile(service, ref)["reply"]["prompts"][key]


def queue(service):
    return next(queue for queue in service.pending()["properties"] if queue["property_ref"] == REF)


def test_a_property_for_sale_gets_a_sales_prompts_and_the_next_one_copies_them(service):
    service.save_property({"reference": "VENDA_1", "description": "Moradia T4 em Exemplo", "deal": "venda"})
    first = prompt(service, "VENDA_1", "first_interaction")
    assert first == SALE_PROMPTS["first_interaction"]
    assert "Quando gostaria de fazer uma visita" in first["reply_template"]
    assert "O que procura exatamente" in first["reply_template"] and "rendimentos" not in first["reply_template"]
    # the general prompt is still the property's own
    assert "VENDA_1" in prompt(service, "VENDA_1", "general")["text"]

    # Changed for the first sale, the next sale copies it; a new rental still copies the rental's
    path = service.folder / "properties" / "VENDA_1" / "profile.json"
    data = load_json(path, {})
    data["reply"]["prompts"]["first_interaction"]["text"] = "Primeira resposta de venda, à minha maneira."
    save_json(path, data)
    service.save_property({"reference": "VENDA_2", "description": "Apartamento T2 em Exemplo", "deal": "venda"})
    assert prompt(service, "VENDA_2", "first_interaction")["text"] == "Primeira resposta de venda, à minha maneira."
    service.save_property({"reference": "ARR_2", "description": "Apartamento T1 em Exemplo", "deal": "arrendamento"})
    assert prompt(service, "ARR_2", "first_interaction") == prompt(service, REF, "first_interaction")
    assert "rendimentos" in prompt(service, "ARR_2", "first_interaction")["text"]

    # A property that changes its kind of business gets the new kind's interaction prompts
    service.save_property({"reference": "ARR_2", "description": "Apartamento T1 em Exemplo", "deal": "venda"})
    assert prompt(service, "ARR_2", "first_interaction")["text"] == "Primeira resposta de venda, à minha maneira."


def test_a_new_property_never_takes_the_owner_or_the_test_mark_of_the_one_it_copies(service):
    path = service.folder / "properties" / REF / "profile.json"
    data = load_json(path, {})
    data["property"].update(owner_email="dono@example.com", owner_name="Dono Exemplo", listing_id="11111111")
    data["test"] = True
    save_json(path, data)
    for ref, deal in (("NOVO_V", "venda"), ("NOVO_A", "arrendamento")):
        service.save_property({"reference": ref, "description": "Apartamento T2 em Exemplo", "deal": deal})
        new = profile(service, ref)
        assert "owner_email" not in new["property"] and "owner_name" not in new["property"], ref
        assert new["property"].get("listing_id") != "11111111" and "test" not in new, ref
        assert "NOVO" in new["reply"]["prompts"]["general"]["text"] and REF not in new["reply"]["prompts"]["general"]["text"]


def test_a_buyers_file_asks_what_they_look_for_never_income(service):
    assert ficha_summary(None, "venda")["falta"] == ["procura", "objetivo", "disponibilidade"]
    assert ficha_summary({"procura": "T3 com garagem", "objetivo": "Habitação própria",
                          "disponibilidade": "Sábados de manhã"}, "venda")["complete"]
    assert ficha_summary(None)["falta"] == ["trabalho", "agregado", "datas", "disponibilidade"]  # a rental, as before

    service.save_property({"reference": REF, "description": "Moradia T4 em Exemplo", "deal": "venda"})
    read(service, [lead("1")])
    current = queue(service)
    [email] = current["emails"]
    assert current["deal"] == "venda" and email["ficha_summary"]["falta"] == ["procura", "objetivo", "disponibilidade"]
    text = reply_prompt(current, [email["id"]])
    assert "Ficha do cliente até agora: o que procura: falta; objetivo: falta; disponibilidade para visitas: falta." in text
    assert SALE_FICHA_JSON in text and '"trabalho"' not in text
    instructions = current["instructions"]
    assert "Este imóvel é para vender" in instructions and "condições da venda" in instructions
    assert "O que procura exatamente" in instructions  # the sale's 1st interaction
    assert "Continua interessado em comprar este imóvel?" in instructions
    assert "interessado em arrendar" not in instructions and "condições do arrendamento" not in instructions


def test_the_sales_copies_of_the_common_prompts_are_edited_apart(service):
    service.save_common_prompts({"later_reply": "Venda: responde só ao que perguntou."}, "venda")
    voice = service.settings()["voice"]
    assert voice["sale"]["later_reply"] == "Venda: responde só ao que perguntou."
    assert voice["later_reply"] == LATER_REPLY_RULE  # the rentals' is untouched
    assert "Venda: responde só ao que perguntou." not in queue(service)["instructions"]  # REF is a rental
    service.save_property({"reference": REF, "description": "Moradia T4 em Exemplo", "deal": "venda"})
    assert "Venda: responde só ao que perguntou." in queue(service)["instructions"]
    # left as the code's own text, it keeps following the code
    service.save_common_prompts({"later_reply": LATER_REPLY_RULE}, "venda")
    stored = json.loads((service.folder / "voice.json").read_text())["sale_style"]["later_reply"]
    assert stored["text"] == "" and stored["status"] == "not_configured"
    with pytest.raises(ValueError):
        service.save_common_prompts({}, "trespasse")


def test_a_buyers_documents_and_a_listing_with_a_price():
    missing = documents_summary({"fiador": True}, "venda")["missing"]
    assert len(missing) == 2 and missing[0].startswith("Documento de identificação")
    assert missing[1].startswith("Comprovativo da capacidade financeira")
    assert not any("fiador" in item or "IRS" in item for item in missing)
    assert any("IRS" in item for item in documents_summary({})["missing"])  # a rental, as before

    text = listing_text_prompt("Moradia T4 à venda, 450.000 €, 220 m²…", deal="venda")
    assert "anúncio de venda" in text and "preço de venda em euros" in text and "renda mensal" not in text
    assert "anúncio de arrendamento" in listing_text_prompt("Apartamento T2 para arrendar, 1.200 €/mês…")
    assert clean_property({"reference": "V1", "description": "Moradia", "deal": "venda",
                           "advertised_rent_eur": "1.500.000"})["advertised_rent_eur"] == 1500000
    with pytest.raises(ValueError):
        clean_property({"reference": "A1", "description": "T2", "advertised_rent_eur": "1.500.000"})
    assert RENTAL_FICHA_JSON in REPLY_FORMAT  # the sale's format replaces exactly this
    # an agency's page for the listing is the same listing, saved in the plain form
    agency = clean_property({"reference": "V1", "description": "Moradia",
                             "listing_url": "https://www.idealista.pt/pro/agencia-exemplo/imovel/12345678/"})
    assert agency["listing_id"] == "12345678" and agency["listing_url"] == "https://www.idealista.pt/imovel/12345678/"
