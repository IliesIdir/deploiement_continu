# Accès au S3 local (SeaweedFS). On utilise boto3 comme pour un vrai S3 AWS,
# il suffit de changer l'endpoint pour pointer sur notre service local.
import logging

import boto3
from botocore.client import Config

import config

logger = logging.getLogger(__name__)

# Même principe que pour la base, on ne veut planter qu'une fois pour tester le retry
_bug_deja_simule = False


def client_s3():
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name="us-east-1",
        # SeaweedFS fonctionne mieux avec des URL du type endpoint/bucket/cle
        config=Config(s3={"addressing_style": "path"}),
    )


def creer_bucket(client, bucket):
    """Crée le bucket s'il n'existe pas encore."""
    buckets = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if bucket not in buckets:
        client.create_bucket(Bucket=bucket)
        logger.info("Bucket %s créé", bucket)


def envoyer_fichier(client, bucket, cle, contenu):
    client.put_object(Bucket=bucket, Key=cle, Body=contenu)


def lister_fichiers(client, bucket, prefixe=""):
    """Renvoie la liste triée des clés présentes dans le bucket."""
    cles = []
    # Le paginator évite d'être limité à 1000 fichiers par appel
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefixe):
        for objet in page.get("Contents", []):
            cles.append(objet["Key"])
    return sorted(cles)


def telecharger_fichier(client, bucket, cle, simuler_bug=False):
    """Récupère le contenu d'un fichier du bucket en bytes."""
    global _bug_deja_simule
    if simuler_bug and not _bug_deja_simule:
        _bug_deja_simule = True
        raise ConnectionError(f"Bug simulé pendant le téléchargement de {cle}")
    reponse = client.get_object(Bucket=bucket, Key=cle)
    return reponse["Body"].read()
