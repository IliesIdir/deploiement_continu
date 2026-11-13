# Mini projet Data Engineering : pipeline de transactions financières

Pipeline data qui part de fichiers csv (et d'images) de transactions, les stocke dans un S3 local,
calcule des agrégats, insère le tout dans PostgreSQL et affiche les résultats dans un dashboard.
La qualité est vérifiée à chaque push par GitHub Actions.

## Organisation du projet

```
config.py              variables de config (lues dans l'environnement)
generate_data.py       génère les csv et les images de test et les envoie dans le S3
run_pipeline.py        setup de la base + traitement des fichiers du S3 + insertion
scheduler.py           relance run_pipeline à intervalle régulier (prod)
dashboard.py           dashboard Streamlit
pipeline/
  loader.py            chargement des données (csv, résultats OCR)
  processing.py        traitements purs (sommes, flag, validation)
  database.py          connexion, création des tables, insertion
  storage.py           accès au S3 (boto3)
  ocr.py               lecture des images avec Tesseract
  retry.py             fonction de retry utilisée pour le S3 et la base
sql/schema.sql         schéma de la base
tests/unit             tests des fonctions pures (sans base ni S3)
tests/integration      vérifie les valeurs insérées dans PostgreSQL
.github/workflows      ci.yml (intégration continue) et cd.yml (déploiement)
docker-compose.yml     base + S3 pour le local et la CI
docker-compose.prod.yml  setup de prod complet
```

## Ce qui a été fait

**Niveau 1**

- Données écrites en dur dans `generate_data.py` (3 csv de 6 à 8 transactions) pour connaître
  à l'avance les résultats. On a ajouté une colonne `montant` qui manquait dans le format demandé.
- Traitements dans `processing.py` : somme envoyée par IBAN, par banque, somme reçue par IBAN
  et flag si le montant est strictement au dessus de 5000. Les fonctions sont pures,
  le chargement est à part dans `loader.py`.
- Base : une table `transactions`, trois tables d'agrégats et une table `fichiers_traites`.
- Pas de double traitement : avant de traiter un fichier on regarde dans `fichiers_traites`
  son nom puis son checksum md5. L'insertion d'un fichier se fait dans une seule transaction SQL
  avec son marquage, donc un plantage au milieu ne laisse rien à moitié inséré.
- Retry : `pipeline/retry.py`, utilisé pour l'insertion. Le bug d'insertion se simule avec
  `SIMULER_BUG_INSERTION=1`.
- Scénarios d'échec : voir `SCENARIO_ECHEC.md`.

**Niveau 2**

- S3 local avec SeaweedFS, lancé au début de la pipeline par docker compose.
- Les fichiers générés partent directement dans le bucket (`csv/` et `images/`), plus rien en local.
- Le traitement lit les fichiers depuis le S3, avec retry sur le téléchargement
  (`SIMULER_BUG_S3=1` pour simuler une panne).

**Niveau 3**

- CD Docker : `Dockerfile` + `docker-compose.prod.yml` avec le S3, la base, le script de traitement
  qui tourne en boucle (`scheduler.py`, toutes les 5 minutes par défaut) et le dashboard.
  Le workflow `cd.yml` construit l'image, la pousse sur ghcr.io et la déploie sur une VM en SSH.
- OCR : des avis de virement en image sont aussi générés, lus avec Tesseract puis traités
  comme les csv. On a choisi cette amélioration car elle ajoute une vraie nouvelle source
  de données à la pipeline.

## Lancer en local

Il faut Docker, Python 3.11 et Tesseract installés.

```bash
pip install -r requirements-dev.txt
```

```bash
docker compose up -d --wait
```

```bash
python generate_data.py
```

```bash
python run_pipeline.py
```

```bash
pytest
```

```bash
streamlit run dashboard.py
```

Pour tester le retry en local, mettre `SIMULER_BUG_INSERTION=1` et `SIMULER_BUG_S3=1`
dans l'environnement avant de lancer `run_pipeline.py`.

## Lancer le setup de prod en local

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Le dashboard est sur http://localhost:8501. Pour avoir des données il suffit d'envoyer des fichiers
dans le bucket (par exemple avec `python generate_data.py`), le scheduler les traite au passage suivant.

## Déploiement

Le workflow `cd.yml` a besoin des secrets `VM_HOST`, `VM_USER`, `VM_SSH_KEY` et `GHCR_TOKEN`.
Sur la VM il faut Docker et un fichier `~/transactions/.env` avec `DB_PASSWORD=...`.
