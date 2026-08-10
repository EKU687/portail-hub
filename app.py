import cadre_entreprise.auth as auth
import cadre_entreprise.ui as ui
from cadre_entreprise.database import supabase
import streamlit as st

# 1. Configuration de la page Streamlit
st.set_page_config(
    page_title="Portail Applicatif GNC", layout="wide", page_icon="🚀"
)

# 2. Contrôle d'Accès & Connexion Standardisée (via SDK)
if not auth.est_connecte():
  ui.afficher_ecran_login(
      nom_application="Portail Central GNC", icone="🚀"
  )
  st.stop()

# 3. Barre Latérale Standardisée (Profil, Rôle & Déconnexion via SDK)
ui.afficher_sidebar_standard()

# =====================================================================
# ÉCRAN PRINCIPAL : ESPACE CONNECTÉ (PORTAIL + MODULE ADMIN)
# =====================================================================
user = auth.get_user_info()
user_login = user.get("login")
user_role = str(user.get("role", "")).upper().strip()

# Menu interne de navigation dans la sidebar
options_menu = ["🌐 Mes Applications"]
if user_role == "ADMIN":
  options_menu.append("⚙️ Administration & Droits")

choix_menu = st.sidebar.radio("Navigation", options_menu)

# ---------------------------------------------------------------------
# OPTION 1 : CATALOGUE DES APPLICATIONS (Visible selon les droits)
# ---------------------------------------------------------------------
if choix_menu == "🌐 Mes Applications":
  st.title("🌐 Vos Applications Disponibles")
  st.write("Sélectionnez un outil pour l'ouvrir dans un nouvel onglet :")
  st.divider()

  try:
    res_apps = (
        supabase.table("Application").select("*").eq("actif", True).execute()
    )
    toutes_les_apps = res_apps.data or []

    if user_role == "ADMIN":
      apps_autorisees = toutes_les_apps
    else:
      res_aut = (
          supabase.table("Autorisation")
          .select("code_app")
          .eq("login", user_login)
          .execute()
      )
      codes_autorises = [a["code_app"] for a in (res_aut.data or [])]
      apps_autorisees = [
          app for app in toutes_les_apps if app["code_app"] in codes_autorises
      ]

    if apps_autorisees:
      cols = st.columns(3)
      for idx, app in enumerate(apps_autorisees):
        with cols[idx % 3]:
          with st.container(border=True):
            st.subheader(f"{app.get('icone', '📱')} {app.get('nom')}")
            st.caption(
                app.get("description", "Aucune description renseignée.")
            )
            st.write("")
            st.link_button(
                "Accéder à l'application ↗️",
                app.get("url", "#"),
                use_container_width=True,
            )
    else:
      st.info("🔒 Vous ne disposez d'accès à aucune application actuellement.")

  except Exception as err:
    st.error(f"Erreur lors du chargement des droits applicatifs : {err}")

# ---------------------------------------------------------------------
# OPTION 2 : MODULE ADMIN (Réservé aux Rôles ADMIN)
# ---------------------------------------------------------------------
elif choix_menu == "⚙️ Administration & Droits":
  st.title("⚙️ Administration Centralisée du Portail")
  st.write("Gérez les comptes utilisateurs et attribuez les accès applicatifs.")
  st.divider()

  tab_users, tab_droits, tab_apps = st.tabs([
      "👤 Créer un Utilisateur",
      "🔑 Affectation des Droits",
      "📱 Catalogue d'Apps",
  ])

  # --- TAB 1 : CRÉATION D'UTILISATEUR ---
  with tab_users:
    st.subheader("➕ Ajouter un nouvel utilisateur")
    with st.form("form_add_user"):
      col_u1, col_u2 = st.columns(2)
      with col_u1:
        new_nom = st.text_input("Nom Complet (ex: Jean DUPONT)")
        new_login = st.text_input("Identifiant / Login").lower().strip()
        new_mdp = st.text_input("Mot de passe temporaire", type="password")
      with col_u2:
        new_service = st.text_input("Service (ex: INFORMATIQUE)")
        new_role = st.selectbox("Rôle", ["USER", "ADMIN"], index=0)

      btn_create_user = st.form_submit_button(
          "Créer le compte", use_container_width=True
      )

    if btn_create_user:
      if not new_login or not new_mdp or not new_nom:
        st.warning("⚠️ Les champs Nom, Login et Mot de passe sont requis.")
      else:
        try:
          check = (
              supabase.table("Utilisateur")
              .select("login")
              .eq("login", new_login)
              .execute()
          )
          if check.data:
            st.error(f"❌ Le login '{new_login}' existe déjà !")
          else:
            # Utilisation de la fonction de hachage du SDK
            mdp_hache = auth.hacher_mot_de_passe(new_mdp)
            supabase.table("Utilisateur").insert({
                "login": new_login,
                "nom": new_nom,
                "mdp": mdp_hache,
                "role": new_role,
                "service": new_service,
            }).execute()
            st.success(f"✅ Compte '{new_login}' créé avec succès !")
        except Exception as e:
          st.error(f"Erreur lors de la création : {e}")

  # --- TAB 2 : AFFECTATION DES DROITS ---
  with tab_droits:
    st.subheader("🔑 Matrice des Autorisations Applicatives")

    res_users = supabase.table("Utilisateur").select("login, nom, role").execute()
    liste_users = res_users.data or []

    if liste_users:
      user_target_login = st.selectbox(
          "Sélectionnez un utilisateur à paramétrer :",
          options=[u["login"] for u in liste_users],
          format_func=lambda x: (
              f"{x} - {next((u['nom'] for u in liste_users if u['login'] == x), '')}"
          ),
      )

      droits_actuels_res = (
          supabase.table("Autorisation")
          .select("code_app")
          .eq("login", user_target_login)
          .execute()
      )
      codes_droits_actuels = [
          d["code_app"] for d in (droits_actuels_res.data or [])
      ]

      all_apps_res = supabase.table("Application").select("*").execute()
      all_apps = all_apps_res.data or []

      st.write(
          f"Cochez les applications autorisées pour **{user_target_login}** :"
      )

      with st.form("form_matrice_droits"):
        nouveaux_droits = {}
        for app in all_apps:
          c_code = app["code_app"]
          est_oche = c_code in codes_droits_actuels
          nouveaux_droits[c_code] = st.checkbox(
              f"{app.get('icone', '')} **{app['nom']}** (`{c_code}`)",
              value=est_oche,
          )

        btn_save_droits = st.form_submit_button(
            "Enregistrer les autorisations", use_container_width=True
        )

      if btn_save_droits:
        try:
          supabase.table("Autorisation").delete().eq(
              "login", user_target_login
          ).execute()

          lignes_a_inserer = [
              {"login": user_target_login, "code_app": code}
              for code, coche in nouveaux_droits.items()
              if coche
          ]

          if lignes_a_inserer:
            supabase.table("Autorisation").insert(lignes_a_inserer).execute()

          st.success("✅ Autorisations mises à jour instantanément !")
          st.rerun()
        except Exception as e:
          st.error(f"Erreur lors de la mise à jour des droits : {e}")

  # --- TAB 3 : GESTION DU CATALOGUE D'APPS ---
  with tab_apps:
    st.subheader("📱 Déclarer une nouvelle Application")
    with st.form("form_add_app"):
      col_a1, col_a2 = st.columns(2)
      with col_a1:
        app_code = (
            st.text_input("Code Unique App (ex: RH_FLOTTE)")
            .upper()
            .strip()
            .replace(" ", "_")
        )
        app_nom = st.text_input("Nom d'affichage (ex: Gestion Flotte)")
        app_icone = st.text_input("Émoji / Icône", value="🚗")
      with col_a2:
        app_url = st.text_input(
            "URL Streamlit Cloud", value="https://xxx.streamlit.app"
        )
        app_desc = st.text_area("Description courte")

      btn_add_app = st.form_submit_button(
          "Ajouter au Catalogue", use_container_width=True
      )

    if btn_add_app:
      if not app_code or not app_nom or not app_url:
        st.warning("⚠️ Code, Nom et URL sont obligatoires.")
      else:
        try:
          supabase.table("Application").insert({
              "code_app": app_code,
              "nom": app_nom,
              "icone": app_icone,
              "url": app_url,
              "description": app_desc,
              "actif": True,
          }).execute()
          st.success(f"✅ Application '{app_nom}' ajoutée au catalogue !")
          st.rerun()
        except Exception as e:
          st.error(f"Erreur lors de l'ajout : {e}")