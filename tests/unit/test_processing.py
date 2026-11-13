# Tests unitaires des fonctions de traitement.
# Pas besoin de base ni de S3 ici, c'est l'avantage d'avoir des fonctions pures.
import pandas as pd
import pytest

from pipeline.processing import (
    ajouter_flag,
    somme_envoyee_par_banque,
    somme_envoyee_par_iban,
    somme_recue_par_iban,
    traiter,
    valider_transactions,
)

IBAN_1 = "FR7630006000011234567890189"
IBAN_2 = "DE89370400440532013000"
IBAN_3 = "BE68539007547034"


@pytest.fixture
def df():
    # Petit jeu de données fait à la main, on connait les résultats attendus
    return pd.DataFrame([
        ["2026-11-01 09:00:00", IBAN_1, "FR", "BNP Paribas", IBAN_2, "DE", 100.0],
        ["2026-11-01 10:00:00", IBAN_1, "FR", "BNP Paribas", IBAN_3, "BE", 5000.0],
        ["2026-11-01 11:00:00", IBAN_2, "DE", "Deutsche Bank", IBAN_3, "BE", 5000.01],
        ["2026-11-01 12:00:00", IBAN_3, "BE", "ING", IBAN_1, "FR", 250.5],
    ], columns=["date_transaction", "iban_origine", "pays_source", "banque_source",
                "iban_destinataire", "pays_destinataire", "montant"])


def test_somme_envoyee_par_iban(df):
    resultat = somme_envoyee_par_iban(df).set_index("iban")["total"].to_dict()
    assert resultat == {IBAN_1: 5100.0, IBAN_2: 5000.01, IBAN_3: 250.5}


def test_somme_envoyee_par_banque(df):
    resultat = somme_envoyee_par_banque(df).set_index("banque")["total"].to_dict()
    assert resultat == {"BNP Paribas": 5100.0, "Deutsche Bank": 5000.01, "ING": 250.5}


def test_somme_recue_par_iban(df):
    resultat = somme_recue_par_iban(df).set_index("iban")["total"].to_dict()
    assert resultat == {IBAN_1: 250.5, IBAN_2: 100.0, IBAN_3: 10000.01}


def test_flag_strictement_au_dessus_de_5000(df):
    flags = ajouter_flag(df, 5000)["flag_suspect"].tolist()
    # 5000 pile ne doit pas être flagué, 5000.01 oui
    assert flags == [False, False, True, False]


def test_les_fonctions_ne_modifient_pas_le_df(df):
    # On vérifie que les fonctions sont bien pures
    copie = df.copy()
    traiter(df)
    pd.testing.assert_frame_equal(df, copie)


def test_validation_ok(df):
    assert valider_transactions(df) == []


def test_validation_montant_negatif(df):
    df.loc[0, "montant"] = -10
    assert "certains montants sont négatifs ou nuls" in valider_transactions(df)


def test_validation_colonne_manquante(df):
    erreurs = valider_transactions(df.drop(columns=["montant"]))
    assert len(erreurs) == 1 and "colonnes manquantes" in erreurs[0]


def test_validation_iban_invalide(df):
    df.loc[1, "iban_destinataire"] = "PAS_UN_IBAN"
    assert any("IBAN invalide" in e for e in valider_transactions(df))


def test_validation_date_invalide(df):
    df.loc[2, "date_transaction"] = "hier"
    assert "certaines dates sont invalides" in valider_transactions(df)
