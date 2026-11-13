# Script principal de la pipeline :
# setup de la base, récupération des fichiers dans le S3, traitement puis insertion.
# Les fichiers déjà traités sont ignorés, on peut donc le relancer autant de fois qu'on veut.
import hashlib
import logging
import sys

import config
from pipeline import database, storage
from pipeline.loader import charger_csv, charger_transactions_ocr
from pipeline.ocr import extraire_texte_image, parser_texte_transaction
from pipeline.processing import traiter, valider_transactions
from pipeline.retry import avec_retry

logger = logging.getLogger(__name__)


def charger_fichier(cle, contenu):
    """Choisit la bonne façon de lire le fichier selon son dossier dans le bucket."""
    if cle.startswith(config.PREFIXE_IMAGES):
        transaction = parser_texte_transaction(extraire_texte_image(contenu))
        return charger_transactions_ocr([transaction]), "image"
    return charger_csv(contenu), "csv"


def traiter_un_fichier(conn, client, cle):
    """Traite un seul fichier du S3. Renvoie True si inséré, False si déjà traité."""
    # Premier contrôle sur le nom, avant même de télécharger le fichier
    if database.fichier_deja_traite(conn, cle):
        logger.info("%s déjà traité, on passe", cle)
        return False

    contenu = avec_retry(
        lambda: storage.telecharger_fichier(client, config.S3_BUCKET, cle, config.SIMULER_BUG_S3),
        config.NB_ESSAIS, config.ATTENTE_RETRY, f"téléchargement de {cle}",
    )

    # Deuxième contrôle sur le contenu : un même fichier renommé ne sera pas retraité
    checksum = hashlib.md5(contenu).hexdigest()
    if database.fichier_deja_traite(conn, cle, checksum):
        logger.info("%s a le même contenu qu'un fichier déjà traité, on passe", cle)
        return False

    df, type_fichier = charger_fichier(cle, contenu)

    erreurs = valider_transactions(df)
    if erreurs:
        raise ValueError(f"{cle} invalide : {erreurs}")

    resultats = traiter(df, config.SEUIL_FLAG)

    avec_retry(
        lambda: database.inserer_resultats(conn, cle, checksum, type_fichier, resultats,
                                           config.SIMULER_BUG_INSERTION),
        config.NB_ESSAIS, config.ATTENTE_RETRY, f"insertion de {cle}",
    )
    return True


def lancer_pipeline():
    """Lance un passage complet de la pipeline et renvoie le nombre de fichiers en erreur."""
    # La base peut ne pas être encore prête au démarrage, d'où le retry sur la connexion
    conn = avec_retry(database.connexion, config.NB_ESSAIS, config.ATTENTE_RETRY, "connexion à la base")
    database.creer_tables(conn)

    client = storage.client_s3()
    cles = avec_retry(lambda: storage.lister_fichiers(client, config.S3_BUCKET),
                      config.NB_ESSAIS, config.ATTENTE_RETRY, "listing du bucket")
    logger.info("%d fichiers trouvés dans le bucket %s", len(cles), config.S3_BUCKET)

    nb_inseres = 0
    nb_erreurs = 0
    for cle in cles:
        # Un fichier en erreur ne doit pas empêcher de traiter les autres
        try:
            if traiter_un_fichier(conn, client, cle):
                nb_inseres += 1
        except Exception as erreur:
            nb_erreurs += 1
            logger.error("Erreur sur %s : %s", cle, erreur)

    conn.close()
    logger.info("Fin de la pipeline : %d fichiers insérés, %d en erreur", nb_inseres, nb_erreurs)
    return nb_erreurs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Code retour 1 s'il y a eu une erreur, pour que la CI passe au rouge
    sys.exit(1 if lancer_pipeline() > 0 else 0)
