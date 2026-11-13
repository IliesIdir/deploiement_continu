-- Schéma de la base qui reçoit les résultats des traitements.
-- On utilise IF NOT EXISTS pour pouvoir relancer la pipeline sans erreur.

-- Liste des fichiers déjà traités : c'est ce qui nous évite de traiter deux fois le même fichier.
-- Le nom et le checksum sont uniques, donc même en cas de bug la base refusera un doublon.
CREATE TABLE IF NOT EXISTS fichiers_traites (
    id SERIAL PRIMARY KEY,
    nom_fichier TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL UNIQUE,
    type_fichier TEXT NOT NULL,
    nb_transactions INTEGER NOT NULL,
    date_traitement TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Les transactions brutes avec le flag calculé, reliées au fichier d'où elles viennent
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    fichier_id INTEGER NOT NULL REFERENCES fichiers_traites(id),
    date_transaction TIMESTAMP NOT NULL,
    iban_origine TEXT NOT NULL,
    pays_source TEXT NOT NULL,
    banque_source TEXT NOT NULL,
    iban_destinataire TEXT NOT NULL,
    pays_destinataire TEXT NOT NULL,
    montant NUMERIC(12, 2) NOT NULL CHECK (montant > 0),
    flag_suspect BOOLEAN NOT NULL
);

-- Les 3 tables d'agrégats. Les totaux sont cumulés fichier après fichier.
CREATE TABLE IF NOT EXISTS somme_envoyee_par_iban (
    iban TEXT PRIMARY KEY,
    total NUMERIC(14, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS somme_envoyee_par_banque (
    banque TEXT PRIMARY KEY,
    total NUMERIC(14, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS somme_recue_par_iban (
    iban TEXT PRIMARY KEY,
    total NUMERIC(14, 2) NOT NULL
);
