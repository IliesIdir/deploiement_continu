import logging
import time

logger = logging.getLogger(__name__)


def avec_retry(fonction, nb_essais=3, attente=1.0, description="opération"):
    """Relance une fonction tant qu'elle plante, jusqu'à nb_essais fois.

    On l'utilise pour le téléchargement S3 et pour l'insertion en base,
    ce sont les deux endroits où une erreur réseau peut arriver.
    """
    for essai in range(1, nb_essais + 1):
        try:
            return fonction()
        except Exception as erreur:
            logger.warning("Echec de %s (essai %d/%d) : %s", description, essai, nb_essais, erreur)
            # Si c'était le dernier essai on laisse remonter l'erreur
            if essai == nb_essais:
                raise
            time.sleep(attente)
