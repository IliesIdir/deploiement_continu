# Script de génération des données de test.
# Les transactions sont écrites en dur (pas de random) pour que la pipeline soit testable :
# on connait à l'avance les sommes et les flags attendus en base.
# Les fichiers sont envoyés directement dans le S3 local (niveau 2), plus rien sur le disque.
import csv
import io
import logging

import config
from pipeline.retry import avec_retry
from pipeline.storage import client_s3, creer_bucket, envoyer_fichier

logger = logging.getLogger(__name__)

# Chaque IBAN est rattaché à un pays et une banque fixes
COMPTES = {
    "FR7630006000011234567890189": ("FR", "BNP Paribas"),
    "FR7610107001011234567890129": ("FR", "Societe Generale"),
    "DE89370400440532013000": ("DE", "Deutsche Bank"),
    "ES9121000418450200051332": ("ES", "Santander"),
    "IT60X0542811101000000123456": ("IT", "UniCredit"),
    "BE68539007547034": ("BE", "ING"),
    "NL91ABNA0417164300": ("NL", "ABN AMRO"),
}

# Raccourcis pour écrire les transactions plus facilement
A, B, C, D, E, F, G = COMPTES.keys()

# (date, iban origine, iban destinataire, montant)
# On a mis exprès un montant à 5000 pile (pas flagué) et un à 5000.01 (flagué)
FICHIERS_CSV = {
    "transactions_2026-11-01.csv": [
        ("2026-11-01 09:15:00", A, C, 1200.00),
        ("2026-11-01 10:30:00", B, A, 350.50),
        ("2026-11-01 11:45:00", C, D, 7800.00),
        ("2026-11-01 14:00:00", A, E, 5000.00),
        ("2026-11-01 16:20:00", D, B, 220.00),
        ("2026-11-01 18:05:00", E, F, 980.00),
    ],
    "transactions_2026-11-02.csv": [
        ("2026-11-02 09:00:00", F, A, 150.00),
        ("2026-11-02 09:40:00", G, C, 12000.00),
        ("2026-11-02 10:10:00", A, G, 640.00),
        ("2026-11-02 11:25:00", B, D, 5000.01),
        ("2026-11-02 13:50:00", C, E, 75.25),
        ("2026-11-02 15:30:00", D, F, 3100.00),
        ("2026-11-02 17:15:00", E, B, 450.00),
        ("2026-11-02 19:45:00", B, C, 900.00),
    ],
    "transactions_2026-11-03.csv": [
        ("2026-11-03 08:30:00", A, B, 2500.00),
        ("2026-11-03 09:55:00", C, A, 6400.00),
        ("2026-11-03 11:10:00", G, D, 300.00),
        ("2026-11-03 12:40:00", F, E, 1750.00),
        ("2026-11-03 14:20:00", D, G, 820.00),
        ("2026-11-03 16:00:00", E, C, 9999.99),
        ("2026-11-03 18:30:00", B, F, 60.00),
    ],
}

# Transactions "scannées" pour la partie OCR, une par image
IMAGES = {
    "virement_2026-11-04_1.png": ("2026-11-04 10:00:00", A, D, 5600.00),
    "virement_2026-11-04_2.png": ("2026-11-04 15:30:00", G, B, 430.00),
}


def construire_ligne(date, iban_origine, iban_destinataire, montant):
    """Complète une transaction avec les pays et la banque à partir des IBAN."""
    pays_source, banque_source = COMPTES[iban_origine]
    pays_destinataire, _ = COMPTES[iban_destinataire]
    return {
        "date_transaction": date,
        "iban_origine": iban_origine,
        "pays_source": pays_source,
        "banque_source": banque_source,
        "iban_destinataire": iban_destinataire,
        "pays_destinataire": pays_destinataire,
        "montant": f"{montant:.2f}",
    }


def generer_csv(transactions):
    """Renvoie le contenu du csv en bytes, prêt à être envoyé dans le S3."""
    lignes = [construire_ligne(*t) for t in transactions]

    # Scénario d'échec : on casse volontairement une ligne pour voir la pipeline tomber
    if config.BUG_GENERATION:
        lignes[0]["montant"] = "-150.00"

    sortie = io.StringIO()
    writer = csv.DictWriter(sortie, fieldnames=list(lignes[0].keys()))
    writer.writeheader()
    writer.writerows(lignes)
    return sortie.getvalue().encode("utf-8")


def _police():
    # DejaVu Sans Mono est dispo sur Ubuntu (CI et Docker), sinon on prend la police par défaut
    from PIL import ImageFont
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf", 28)
    except OSError:
        return ImageFont.load_default(size=28)


def generer_image(transaction):
    """Dessine la transaction sur une image blanche, comme un avis de virement scanné."""
    from PIL import Image, ImageDraw

    ligne = construire_ligne(*transaction)
    # On écrit les IBAN par blocs de 4 comme sur un vrai document bancaire
    iban_o = " ".join(ligne["iban_origine"][i:i + 4] for i in range(0, len(ligne["iban_origine"]), 4))
    iban_d = " ".join(ligne["iban_destinataire"][i:i + 4] for i in range(0, len(ligne["iban_destinataire"]), 4))
    texte = [
        "DATE : " + ligne["date_transaction"],
        "IBAN ORIGINE : " + iban_o,
        "PAYS SOURCE : " + ligne["pays_source"],
        "BANQUE SOURCE : " + ligne["banque_source"],
        "IBAN DESTINATAIRE : " + iban_d,
        "PAYS DESTINATAIRE : " + ligne["pays_destinataire"],
        "MONTANT : " + ligne["montant"],
    ]

    image = Image.new("RGB", (1100, 60 + 50 * len(texte)), "white")
    dessin = ImageDraw.Draw(image)
    police = _police()
    for i, t in enumerate(texte):
        dessin.text((30, 30 + i * 50), t, fill="black", font=police)

    sortie = io.BytesIO()
    image.save(sortie, format="PNG")
    return sortie.getvalue()


def main():
    client = client_s3()
    # Le S3 vient juste d'être lancé dans la pipeline, il peut mettre quelques secondes à répondre
    avec_retry(lambda: creer_bucket(client, config.S3_BUCKET), config.NB_ESSAIS, config.ATTENTE_RETRY,
               "création du bucket")

    for nom, transactions in FICHIERS_CSV.items():
        envoyer_fichier(client, config.S3_BUCKET, config.PREFIXE_CSV + nom, generer_csv(transactions))
        logger.info("%s envoyé dans le S3 (%d transactions)", nom, len(transactions))

    for nom, transaction in IMAGES.items():
        envoyer_fichier(client, config.S3_BUCKET, config.PREFIXE_IMAGES + nom, generer_image(transaction))
        logger.info("%s envoyé dans le S3", nom)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
