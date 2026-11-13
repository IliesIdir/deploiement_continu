# Niveau 3 : extraction de transactions contenues dans des images avec Tesseract.
# On sépare la partie OCR (qui dépend de Tesseract) du parsing du texte (fonction pure)
# pour pouvoir tester le parsing sans avoir Tesseract installé.
import io
import re

# Les libellés écrits dans les images et la colonne correspondante dans nos données
LIBELLES = {
    "DATE": "date_transaction",
    "IBAN ORIGINE": "iban_origine",
    "PAYS SOURCE": "pays_source",
    "BANQUE SOURCE": "banque_source",
    "IBAN DESTINATAIRE": "iban_destinataire",
    "PAYS DESTINATAIRE": "pays_destinataire",
    "MONTANT": "montant",
}


def extraire_texte_image(contenu):
    """Lance Tesseract sur l'image (bytes) et renvoie le texte lu."""
    # Imports ici pour ne pas obliger à avoir Pillow/pytesseract juste pour importer le module
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(contenu))
    # psm 6 = on dit à Tesseract que c'est un bloc de texte uniforme, ça marche mieux ici
    return pytesseract.image_to_string(image, config="--psm 6")


def _nettoyer_iban(valeur):
    # L'OCR peut ajouter des espaces ou confondre O et 0, on corrige après les 2 lettres du pays
    valeur = valeur.replace(" ", "").upper()
    return valeur[:2] + valeur[2:].replace("O", "0")


def parser_texte_transaction(texte):
    """Transforme le texte lu par l'OCR en dict de transaction.

    Le texte attendu ressemble à des lignes "LIBELLE : valeur".
    """
    transaction = {}
    for ligne in texte.splitlines():
        if ":" not in ligne:
            continue
        # On coupe sur le premier ":" seulement, sinon l'heure de la date serait coupée
        libelle, valeur = ligne.split(":", 1)
        libelle = libelle.strip().upper()
        valeur = valeur.strip()
        if libelle in LIBELLES:
            transaction[LIBELLES[libelle]] = valeur

    if "iban_origine" in transaction:
        transaction["iban_origine"] = _nettoyer_iban(transaction["iban_origine"])
    if "iban_destinataire" in transaction:
        transaction["iban_destinataire"] = _nettoyer_iban(transaction["iban_destinataire"])
    if "montant" in transaction:
        montant = re.sub(r"[^0-9.,]", "", transaction["montant"]).replace(",", ".")
        transaction["montant"] = float(montant) if montant else None
    if "date_transaction" in transaction:
        # Tesseract met parfois des espaces en trop autour des ":" de l'heure
        transaction["date_transaction"] = re.sub(r"\s*:\s*", ":", transaction["date_transaction"])

    return transaction
