# Test d'intégration : on vérifie directement dans PostgreSQL que la pipeline
# a inséré les bonnes valeurs. A lancer après generate_data.py et run_pipeline.py.
# Les valeurs attendues ont été calculées à la main à partir des données de generate_data.py.
from decimal import Decimal

import pytest

from pipeline.database import connexion
from run_pipeline import lancer_pipeline


@pytest.fixture
def cur():
    conn = connexion()
    with conn.cursor() as cur:
        yield cur
    conn.close()


def test_tous_les_fichiers_sont_traites_une_seule_fois(cur):
    cur.execute("SELECT type_fichier, COUNT(*) FROM fichiers_traites GROUP BY type_fichier")
    assert dict(cur.fetchall()) == {"csv": 3, "image": 2}


def test_nombre_de_transactions(cur):
    cur.execute("SELECT COUNT(*) FROM transactions")
    assert cur.fetchone()[0] == 23


def test_montant_total(cur):
    cur.execute("SELECT SUM(montant) FROM transactions")
    assert cur.fetchone()[0] == Decimal("65725.75")


def test_transactions_flaguees(cur):
    cur.execute("SELECT montant FROM transactions WHERE flag_suspect ORDER BY montant")
    montants = [m for (m,) in cur.fetchall()]
    assert montants == [Decimal(x) for x in ["5000.01", "5600.00", "6400.00", "7800.00", "9999.99", "12000.00"]]


def test_5000_pile_pas_flague(cur):
    cur.execute("SELECT flag_suspect FROM transactions WHERE montant = 5000")
    assert cur.fetchall() == [(False,)]


def test_somme_envoyee_par_iban(cur):
    cur.execute("SELECT iban, total FROM somme_envoyee_par_iban")
    assert dict(cur.fetchall()) == {
        "FR7630006000011234567890189": Decimal("14940.00"),
        "FR7610107001011234567890129": Decimal("6310.51"),
        "DE89370400440532013000": Decimal("14275.25"),
        "ES9121000418450200051332": Decimal("4140.00"),
        "IT60X0542811101000000123456": Decimal("11429.99"),
        "BE68539007547034": Decimal("1900.00"),
        "NL91ABNA0417164300": Decimal("12730.00"),
    }


def test_somme_envoyee_par_banque(cur):
    cur.execute("SELECT banque, total FROM somme_envoyee_par_banque")
    assert dict(cur.fetchall()) == {
        "ABN AMRO": Decimal("12730.00"),
        "BNP Paribas": Decimal("14940.00"),
        "Deutsche Bank": Decimal("14275.25"),
        "ING": Decimal("1900.00"),
        "Santander": Decimal("4140.00"),
        "Societe Generale": Decimal("6310.51"),
        "UniCredit": Decimal("11429.99"),
    }


def test_somme_recue_par_iban(cur):
    cur.execute("SELECT iban, total FROM somme_recue_par_iban")
    assert dict(cur.fetchall()) == {
        "FR7630006000011234567890189": Decimal("6900.50"),
        "FR7610107001011234567890129": Decimal("3600.00"),
        "DE89370400440532013000": Decimal("24099.99"),
        "ES9121000418450200051332": Decimal("18700.01"),
        "IT60X0542811101000000123456": Decimal("6825.25"),
        "BE68539007547034": Decimal("4140.00"),
        "NL91ABNA0417164300": Decimal("1460.00"),
    }


def test_transactions_ocr(cur):
    # Les deux transactions qui viennent des images doivent être identiques à celles générées
    cur.execute(
        "SELECT t.date_transaction::text, t.iban_origine, t.iban_destinataire, t.banque_source, t.montant "
        "FROM transactions t JOIN fichiers_traites f ON f.id = t.fichier_id "
        "WHERE f.type_fichier = 'image' ORDER BY t.date_transaction"
    )
    assert cur.fetchall() == [
        ("2026-11-04 10:00:00", "FR7630006000011234567890189", "ES9121000418450200051332",
         "BNP Paribas", Decimal("5600.00")),
        ("2026-11-04 15:30:00", "NL91ABNA0417164300", "FR7610107001011234567890129",
         "ABN AMRO", Decimal("430.00")),
    ]


def test_relancer_la_pipeline_ne_cree_pas_de_doublons(cur):
    # On relance une deuxième fois : tous les fichiers sont déjà traités donc rien ne doit bouger
    assert lancer_pipeline() == 0
    cur.execute("SELECT COUNT(*) FROM transactions")
    assert cur.fetchone()[0] == 23
    cur.execute("SELECT COUNT(*) FROM fichiers_traites")
    assert cur.fetchone()[0] == 5
    cur.execute("SELECT total FROM somme_envoyee_par_banque WHERE banque = 'BNP Paribas'")
    assert cur.fetchone()[0] == Decimal("14940.00")
