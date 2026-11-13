# Config centralisée du projet.
# On passe par des variables d'environnement pour pouvoir utiliser les mêmes scripts
# en local, dans la CI GitHub et en prod dans Docker sans toucher au code.
import os

# Base PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "transactions")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# S3 local (SeaweedFS)
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:8333")
S3_BUCKET = os.getenv("S3_BUCKET", "transactions")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "admin")

# Dossiers dans le bucket, un pour les csv et un pour les images (OCR)
PREFIXE_CSV = "csv/"
PREFIXE_IMAGES = "images/"

# Montant à partir duquel une transaction est flaguée (strictement au dessus)
SEUIL_FLAG = 5000

# Paramètres du retry
NB_ESSAIS = int(os.getenv("NB_ESSAIS", "5"))
ATTENTE_RETRY = float(os.getenv("ATTENTE_RETRY", "2"))

# Pour simuler des bugs et montrer que le retry marche (mettre à 1 pour activer)
SIMULER_BUG_INSERTION = os.getenv("SIMULER_BUG_INSERTION", "0") == "1"
SIMULER_BUG_S3 = os.getenv("SIMULER_BUG_S3", "0") == "1"

# Pour le scénario d'échec de la pipeline : on génère volontairement une donnée fausse
BUG_GENERATION = os.getenv("BUG_GENERATION", "0") == "1"

# Intervalle (en secondes) entre deux passages du script en prod
INTERVALLE_SCHEDULER = int(os.getenv("INTERVALLE_SCHEDULER", "300"))
