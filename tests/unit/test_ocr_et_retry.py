# Tests du parsing OCR et du mécanisme de retry.
import pytest

from pipeline.ocr import parser_texte_transaction
from pipeline.retry import avec_retry


def test_parser_texte_ocr():
    # Texte comme Tesseract pourrait le sortir, avec des espaces et un O à la place d'un 0
    texte = (
        "DATE : 2026-11-04 10:00:00\n"
        "IBAN ORIGINE : FR76 3000 6000 O112 3456 7890 189\n"
        "PAYS SOURCE : FR\n"
        "BANQUE SOURCE : BNP Paribas\n"
        "\n"
        "IBAN DESTINATAIRE : ES91 2100 0418 4502 0005 1332\n"
        "PAYS DESTINATAIRE : ES\n"
        "MONTANT : 5600.00\n"
    )
    assert parser_texte_transaction(texte) == {
        "date_transaction": "2026-11-04 10:00:00",
        "iban_origine": "FR7630006000011234567890189",
        "pays_source": "FR",
        "banque_source": "BNP Paribas",
        "iban_destinataire": "ES9121000418450200051332",
        "pays_destinataire": "ES",
        "montant": 5600.0,
    }


def test_retry_reussit_apres_des_echecs():
    appels = []

    def fonction_instable():
        appels.append(1)
        if len(appels) < 3:
            raise ConnectionError("pas encore")
        return "ok"

    assert avec_retry(fonction_instable, nb_essais=5, attente=0) == "ok"
    assert len(appels) == 3


def test_retry_abandonne_apres_le_dernier_essai():
    def fonction_cassee():
        raise ConnectionError("toujours cassé")

    with pytest.raises(ConnectionError):
        avec_retry(fonction_cassee, nb_essais=2, attente=0)
