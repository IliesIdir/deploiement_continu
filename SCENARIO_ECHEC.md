# Scénarios d'échec de la pipeline

Le but ici est de montrer que la CI détecte bien les problèmes et passe au rouge.
Les captures d'écran sont à mettre dans le dossier `captures/`.

## Scénario 1 : bug dans la génération des données

On a ajouté une option `BUG_GENERATION` dans `generate_data.py`. Quand elle est activée,
le premier montant de chaque csv devient négatif (`-150.00`).

Pour le lancer :

1. Aller dans l'onglet **Actions** du repo GitHub
2. Choisir le workflow **CI pipeline data** puis **Run workflow**
3. Cocher **Générer une donnée fausse pour faire échouer la pipeline**

Ce qui se passe :

- `generate_data.py` envoie les csv faux dans le S3
- `run_pipeline.py` valide chaque fichier avant de le traiter, la validation trouve
  "certains montants sont négatifs ou nuls" et refuse les 3 csv
- le script sort avec le code 1 donc l'étape **Traitement et insertion en base** est en rouge
- les fichiers refusés ne sont pas marqués comme traités, ils seront repris quand la donnée sera corrigée

Captures à faire :

- `captures/echec_generation_workflow.png` : la vue du workflow avec l'étape en rouge
- `captures/echec_generation_logs.png` : les logs avec le message d'erreur de validation

## Scénario 2 : bug dans le traitement

On modifie volontairement le flag dans `pipeline/processing.py` en remplaçant `>` par `>=` :

```python
return df.assign(flag_suspect=df["montant"].astype(float) >= seuil)
```

Puis on push sur une branche. Ce qui se passe :

- le job **tests-unitaires** échoue sur `test_flag_strictement_au_dessus_de_5000`
  (la transaction de 5000 pile est maintenant flaguée)
- le job **pipeline** ne se lance même pas car il dépend des tests unitaires

Si on désactive ce test, c'est le test d'intégration `test_5000_pile_pas_flague` qui
attrape l'erreur directement dans la base, donc le bug ne passe pas non plus.

Captures à faire :

- `captures/echec_traitement_workflow.png`
- `captures/echec_traitement_pytest.png` : la sortie de pytest avec l'assert qui échoue

## Scénario 3 : bug d'insertion en base et retry

Celui là ne fait pas échouer la pipeline, c'est le but. Dans la CI on lance toujours
`run_pipeline.py` avec `SIMULER_BUG_INSERTION=1` et `SIMULER_BUG_S3=1` :

- le premier téléchargement S3 plante, le retry le relance et ça passe
- la première insertion plante après avoir inséré les transactions mais avant le commit,
  PostgreSQL fait un rollback et le retry réinsère proprement

Le test d'intégration vérifie ensuite qu'il y a bien 23 transactions et pas plus,
donc pas de doublon malgré le plantage. Dans les logs on voit les lignes
`Echec de insertion de csv/transactions_2026-11-01.csv (essai 1/5)`.

Capture à faire : `captures/retry_logs.png`
