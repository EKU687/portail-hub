# =====================================================================
# APPLICATION : PORTAIL CENTRAL HUB (portail-gnc)
# =====================================================================
import cadre_entreprise.auth as auth
import cadre_entreprise.ui as ui
from cadre_entreprise.database import supabase
import streamlit as st

# 1. Configuration de la page Streamlit
st.set_page_config(
    page_title="Portail Central HUB - GNC",
    layout="wide",
    page_icon="🏛️",
)

# 2. Vérification de la connexion via le SDK Centralisé
if not auth.est_connecte():
  ui.afficher_ecran_login("Portail Central HUB", "🏛️")
  st.stop()

# 3. Barre latérale de profil standardisée
ui.afficher_sidebar_standard()

# =====================================================================
# 4. PROFIL UTILISATEUR & DROITS D'ADMINISTRATION
# =====================================================================
user = auth.get_user_info()
user_login = str(user.get("login", "")).lower().strip()
user_role = str(user.get("role", "")).upper().strip()

# Définition des privilèges Administrateur (Role ADMIN ou logins spécifiques)
est_admin = (user_role == "ADMIN") or (user_login in ["admin", "eric.kuter"])

# =====================================================================
# 5. EN-TÊTE ET ONGLETS DE NAVIGATION
# =====================================================================
st.title("🏛️ Portail Central HUB – GNC")
st.caption(
    f"Connecté en tant que : **{user.get('nom')}** | Service :"
    f" **{user.get('service')}**"
)
st.divider()

if est_admin:
  tab_apps, tab_admin = st.tabs(
      ["🚀 Applications Métiers", "⚙️ Administration des Comptes & Droits"]
  )
else:
  tab_apps = st.container()
  tab_admin = None

# =====================================================================
# ONGLET 1 : CATALOGUE DES APPLICATIONS
# =====================================================================
with tab_apps:
  st.subheader("📱 Vos Applications Disponibles")

  col1, col2 = st.columns(2)

  with col1:
    with st.container(border=True):
      st.markdown("### 💰 Gestion Budgétaire")
      st.caption(
          "Préparation et suivi budgétaire, gestion des devis et exports PDF."
      )
      st.link_button(
          "Accéder au Budget ↗️",
          "https://gestion-budget.streamlit.app",
          use_container_width=True,
      )

  with col2:
    with st.container(border=True):
      st.markdown("### 🔥 Sécurité Incendie")
      st.caption(
          "Tableau du jour de l'équipe d'évacuation, consignes et main"
          " courante PC Sécurité."
      )
      # URL Streamlit Cloud définitive du module Sécurité Incendie
      st.link_button(
          "Accéder au Poste Sécurité ↗️",
          "https://securite-incendie.streamlit.app",
          use_container_width=True,
      )

# =====================================================================
# ONGLET 2 : ADMINISTRATION DES COMPTES (RÉSERVÉ ADMIN / ERIC.KUTER)
# =====================================================================
if est_admin and tab_admin:
  with tab_admin:
    st.subheader("👥 Gestion des Comptes Utilisateurs (Table `Utilisateur`)")

    # --- SECTION A : CRÉATION ET RÉINITIALISATION DE COMPTE ---
    with st.expander("➕ Créer ou Réinitialiser un Compte", expanded=False):
      with st.form("form_gestion_compte_portail", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
          f_login = st.text_input("Identifiant / Login").lower().strip()
          f_mdp = st.text_input("Nouveau Mot de Passe", type="password")
        with c2:
          f_nom = st.text_input("Nom Complet / Libellé")
          f_role = st.selectbox("Rôle", ["USER", "ADMIN"])
        with c3:
          f_service = st.text_input(
              "Code Service (ex: CSPP - SURETE, SANL, TOUS)"
          )

        btn_valider_compte = st.form_submit_button(
            "💾 Enregistrer / Mettre à jour le Compte",
            use_container_width=True,
        )

      if btn_valider_compte:
        if not f_login or not f_mdp or not f_nom:
          st.warning("⚠️ Le Login, le Mot de Passe et le Nom sont requis.")
        else:
          # Hachage sécurisé Bcrypt via le SDK
          hash_mdp = auth.hacher_mot_de_passe(f_mdp)

          # Vérification de l'existence du compte en BDD
          try:
            res_exist = (
                supabase.table("Utilisateur")
                .select("id")
                .eq("login", f_login)
                .execute()
            )
            existe = bool(res_exist.data and len(res_exist.data) > 0)

            donnees_compte = {
                "login": f_login,
                "mdp": hash_mdp,
                "nom": f_nom,
                "role": f_role,
                "service": f_service or "NON DÉFINI",
            }

            if existe:
              # Mise à jour
              supabase.table("Utilisateur").update(donnees_compte).eq(
                  "login", f_login
              ).execute()
              st.success(
                  f"✅ Compte '{f_login}' réinitialisé avec succès !"
              )
            else:
              # Insertion
              supabase.table("Utilisateur").insert(donnees_compte).execute()
              st.success(f"✅ Nouveau compte '{f_login}' créé avec succès !")

            st.rerun()
          except Exception as err:
            st.error(f"❌ Erreur de sauvegarde Supabase : {err}")

    st.divider()

    # --- SECTION B : ÉDITEUR INTERACTIF DES COMPTES EXISTANTS ---
    st.markdown("##### 📋 Liste Générale des Comptes")
    try:
      res_users = (
          supabase.table("Utilisateur").select("*").order("login").execute()
      )
      liste_users = res_users.data or []
    except Exception as e:
      st.error(f"Erreur de lecture Supabase : {e}")
      liste_users = []

    if liste_users:
      with st.form("form_editeur_liste_utilisateurs"):
        st.data_editor(
            liste_users,
            key="editeur_utilisateurs_portail",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_order=["login", "nom", "role", "service"],
            column_config={
                "login": st.column_config.TextColumn(
                    "Login (Identifiant)", disabled=True
                ),
                "nom": st.column_config.TextColumn(
                    "Nom Complet", required=True
                ),
                "role": st.column_config.SelectboxColumn(
                    "Rôle", options=["USER", "ADMIN"], required=True
                ),
                "service": st.column_config.TextColumn("Code Service"),
            },
        )
        btn_sauver_table = st.form_submit_button(
            "💾 Sauvegarder les modifications du Référentiel Utilisateurs",
            use_container_width=True,
        )

      if btn_sauver_table:
        try:
          j_u = st.session_state["editeur_utilisateurs_portail"]

          # 1. Suppressions
          if j_u.get("deleted_rows"):
            for idx in j_u["deleted_rows"]:
              log_del = liste_users[int(idx)]["login"]
              supabase.table("Utilisateur").delete().eq(
                  "login", log_del
              ).execute()

          # 2. Modifications (Nom, Rôle, Service)
          if j_u.get("edited_rows"):
            for idx, modifs in j_u["edited_rows"].items():
              log_mod = liste_users[int(idx)]["login"]
              supabase.table("Utilisateur").update(modifs).eq(
                  "login", log_mod
              ).execute()

          st.success("✅ Base Utilisateurs mise à jour !")
          st.rerun()
        except Exception as e:
          st.error(f"Erreur de mise à jour : {e}")