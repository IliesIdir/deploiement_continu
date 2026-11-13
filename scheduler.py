# Utilisé en prod (niveau 3) : relance la pipeline à intervalle régulier
# pour traiter les nouveaux fichiers qui arrivent dans le S3.
# On a fait une simple boucle plutôt qu'un cron, c'est plus simple à faire tourner dans Docker.
import logging
import time

import config
from run_pipeline import lancer_pipeline

logger = logging.getLogger(__name__)


def main():
    while True:
        try:
            lancer_pipeline()
        except Exception as erreur:
            # Si la base ou le S3 sont down on ne veut pas que le conteneur s'arrête
            logger.error("La pipeline a planté : %s", erreur)
        logger.info("Prochain passage dans %d secondes", config.INTERVALLE_SCHEDULER)
        time.sleep(config.INTERVALLE_SCHEDULER)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
