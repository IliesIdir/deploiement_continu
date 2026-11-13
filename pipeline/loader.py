# Fonctions de chargement des données.
# On les garde à part des traitements pour que ces derniers restent purs
# (pas de lecture de fichier ni d'appel réseau dans processing.py).
import io

import pandas as pd

COLONNES = [
    "date_transaction",
    "iban_origine",
    "pays_source",
    "banque_source",
    "iban_destinataire",
    "pays_destinataire",
    "montant",
]


def charger_csv(contenu):
    """Transforme le contenu brut d'un csv (bytes) en DataFrame."""
    # On force les IBAN en texte pour éviter que pandas essaye de les convertir
    return pd.read_csv(io.BytesIO(contenu), dtype={"iban_origine": str, "iban_destinataire": str})


def charger_csv_local(chemin):
    """Version niveau 1 : lecture depuis le disque. Gardée pour debug en local."""
    with open(chemin, "rb") as f:
        return charger_csv(f.read())


def charger_transactions_ocr(liste_transactions):
    """Construit un DataFrame à partir des dicts extraits des images par l'OCR."""
    return pd.DataFrame(liste_transactions, columns=COLONNES)
