# Fonctions de traitement des transactions.
# Toutes les fonctions ici sont pures : elles ne modifient pas le DataFrame reçu
# et ne dépendent que de leurs paramètres. C'est ce qui les rend faciles à tester.
import re

import pandas as pd

from pipeline.loader import COLONNES

# Format simplifié d'un IBAN : 2 lettres pays, 2 chiffres de clé, puis des lettres/chiffres
REGEX_IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")


def valider_transactions(df):
    """Vérifie que les données sont propres avant de les traiter.

    Renvoie la liste des erreurs trouvées (liste vide si tout est bon).
    On préfère bloquer un fichier faux plutôt que d'insérer n'importe quoi en base.
    """
    erreurs = []

    colonnes_manquantes = [c for c in COLONNES if c not in df.columns]
    if colonnes_manquantes:
        # Pas la peine d'aller plus loin si la structure n'est pas bonne
        return [f"colonnes manquantes : {colonnes_manquantes}"]

    if df.empty:
        return ["aucune transaction dans le fichier"]

    if df[COLONNES].isnull().any().any():
        erreurs.append("il y a des valeurs vides")

    montants = pd.to_numeric(df["montant"], errors="coerce")
    if montants.isnull().any():
        erreurs.append("certains montants ne sont pas des nombres")
    elif (montants <= 0).any():
        erreurs.append("certains montants sont négatifs ou nuls")

    dates = pd.to_datetime(df["date_transaction"], errors="coerce", format="%Y-%m-%d %H:%M:%S")
    if dates.isnull().any():
        erreurs.append("certaines dates sont invalides")

    for colonne in ["iban_origine", "iban_destinataire"]:
        for iban in df[colonne].dropna():
            if not REGEX_IBAN.match(str(iban)):
                erreurs.append(f"IBAN invalide dans {colonne} : {iban}")

    return erreurs


def ajouter_flag(df, seuil=5000):
    """Ajoute une colonne flag_suspect à True si le montant est strictement au dessus du seuil."""
    # assign renvoie une copie, le DataFrame d'origine n'est pas touché
    return df.assign(flag_suspect=df["montant"].astype(float) > seuil)


def _somme_par(df, colonne_groupe, nom_colonne):
    """Petite fonction commune aux 3 sommes pour ne pas répéter le même groupby."""
    resultat = (
        df.assign(montant=df["montant"].astype(float))
        .groupby(colonne_groupe, as_index=False)["montant"]
        .sum()
        .rename(columns={colonne_groupe: nom_colonne, "montant": "total"})
    )
    resultat["total"] = resultat["total"].round(2)
    return resultat.sort_values(nom_colonne).reset_index(drop=True)


def somme_envoyee_par_iban(df):
    """Somme des montants envoyés par chaque IBAN d'origine."""
    return _somme_par(df, "iban_origine", "iban")


def somme_envoyee_par_banque(df):
    """Somme des montants envoyés par chaque banque source."""
    return _somme_par(df, "banque_source", "banque")


def somme_recue_par_iban(df):
    """Somme des montants reçus par chaque IBAN destinataire."""
    return _somme_par(df, "iban_destinataire", "iban")


def traiter(df, seuil=5000):
    """Enchaîne tous les traitements et renvoie un dict avec les résultats.

    C'est ce dict qui est ensuite passé à la fonction d'insertion en base.
    """
    return {
        "transactions": ajouter_flag(df, seuil),
        "envoye_par_iban": somme_envoyee_par_iban(df),
        "envoye_par_banque": somme_envoyee_par_banque(df),
        "recu_par_iban": somme_recue_par_iban(df),
    }
