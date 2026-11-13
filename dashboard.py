# Petit dashboard Streamlit branché sur la base PostgreSQL.
# Lancement : streamlit run dashboard.py
import pandas as pd
import streamlit as st

from pipeline.database import connexion

st.set_page_config(page_title="Transactions", layout="wide")
st.title("Suivi des transactions financières")


def lire(requete):
    # On ouvre une connexion par requête, c'est suffisant pour un petit dashboard
    conn = connexion()
    try:
        with conn.cursor() as cur:
            cur.execute(requete)
            colonnes = [c[0] for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=colonnes)
    finally:
        conn.close()


try:
    transactions = lire("SELECT * FROM transactions ORDER BY date_transaction")
except Exception as erreur:
    st.error(f"Impossible de lire la base : {erreur}")
    st.stop()

if transactions.empty:
    st.info("Aucune transaction en base pour l'instant, la pipeline n'a pas encore tourné.")
    st.stop()

transactions["montant"] = transactions["montant"].astype(float)

# Quelques chiffres clés en haut de la page
col1, col2, col3 = st.columns(3)
col1.metric("Transactions", len(transactions))
col2.metric("Montant total", f"{transactions['montant'].sum():,.2f} EUR")
col3.metric("Transactions suspectes (> 5000)", int(transactions["flag_suspect"].sum()))

st.subheader("Montants envoyés par banque")
par_banque = lire("SELECT banque, total FROM somme_envoyee_par_banque ORDER BY total DESC")
st.bar_chart(par_banque.astype({"total": float}).set_index("banque"))

gauche, droite = st.columns(2)
with gauche:
    st.subheader("Envoyé par IBAN")
    st.dataframe(lire("SELECT iban, total FROM somme_envoyee_par_iban ORDER BY total DESC"), hide_index=True)
with droite:
    st.subheader("Reçu par IBAN")
    st.dataframe(lire("SELECT iban, total FROM somme_recue_par_iban ORDER BY total DESC"), hide_index=True)

st.subheader("Transactions flaguées")
st.dataframe(transactions[transactions["flag_suspect"]], hide_index=True)

st.subheader("Fichiers traités")
st.dataframe(lire("SELECT nom_fichier, type_fichier, nb_transactions, date_traitement FROM fichiers_traites"),
             hide_index=True)
