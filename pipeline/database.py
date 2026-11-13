# Tout ce qui touche à PostgreSQL : connexion, création des tables et insertion.
import logging
import os

import psycopg2

import config

logger = logging.getLogger(__name__)

CHEMIN_SCHEMA = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")

# Sert uniquement à la simulation de bug : on veut planter une seule fois puis réussir au retry
_bug_deja_simule = False


def connexion():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def creer_tables(conn):
    """Exécute le fichier schema.sql (setup de la base)."""
    with open(CHEMIN_SCHEMA, encoding="utf-8") as f:
        schema = f.read()
    with conn:
        with conn.cursor() as cur:
            cur.execute(schema)


def fichier_deja_traite(conn, nom_fichier, checksum=None):
    """Regarde dans fichiers_traites si on a déjà vu ce fichier (par nom ou par contenu)."""
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM fichiers_traites WHERE nom_fichier = %s OR checksum = %s",
                (nom_fichier, checksum),
            )
            return cur.fetchone() is not None


def _upsert_somme(cur, table, colonne, df):
    """Ajoute les totaux du fichier aux totaux déjà présents en base."""
    for ligne in df.itertuples(index=False):
        cur.execute(
            f"INSERT INTO {table} ({colonne}, total) VALUES (%s, %s) "
            f"ON CONFLICT ({colonne}) DO UPDATE SET total = {table}.total + EXCLUDED.total",
            (getattr(ligne, colonne), float(ligne.total)),
        )


def inserer_resultats(conn, nom_fichier, checksum, type_fichier, resultats, simuler_bug=False):
    """Insère les résultats d'un fichier en base.

    Tout est fait dans une seule transaction SQL : soit tout passe (transactions, sommes
    et marquage du fichier), soit rien ne passe. Comme ça si on plante au milieu
    et qu'on relance, on n'a pas de doublons et le fichier n'est pas marqué comme traité.
    """
    global _bug_deja_simule
    transactions = resultats["transactions"]

    # "with conn" fait un commit si tout va bien et un rollback si une exception est levée
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fichiers_traites (nom_fichier, checksum, type_fichier, nb_transactions) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (nom_fichier, checksum, type_fichier, len(transactions)),
            )
            fichier_id = cur.fetchone()[0]

            for t in transactions.to_dict("records"):
                cur.execute(
                    "INSERT INTO transactions (fichier_id, date_transaction, iban_origine, pays_source, "
                    "banque_source, iban_destinataire, pays_destinataire, montant, flag_suspect) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        fichier_id,
                        str(t["date_transaction"]),
                        t["iban_origine"],
                        t["pays_source"],
                        t["banque_source"],
                        t["iban_destinataire"],
                        t["pays_destinataire"],
                        float(t["montant"]),
                        # psycopg2 ne sait pas gérer le bool de numpy, on le convertit
                        bool(t["flag_suspect"]),
                    ),
                )

            # Bug simulé au pire moment : les transactions sont insérées mais pas encore commit
            if simuler_bug and not _bug_deja_simule:
                _bug_deja_simule = True
                raise ConnectionError("Bug simulé pendant l'insertion en base")

            _upsert_somme(cur, "somme_envoyee_par_iban", "iban", resultats["envoye_par_iban"])
            _upsert_somme(cur, "somme_envoyee_par_banque", "banque", resultats["envoye_par_banque"])
            _upsert_somme(cur, "somme_recue_par_iban", "iban", resultats["recu_par_iban"])

    logger.info("%s inséré en base (%d transactions)", nom_fichier, len(transactions))
