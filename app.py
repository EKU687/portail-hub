# =====================================================================
# APPLICATION : PORTAIL CENTRAL HUB (portail-gnc)
# Correctif de la condition de filtrage des habilitations
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

# 2. Authentification via le SDK Centralisé
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

# Définition des privilèges Administrateur (Uniquement si rôle ADMIN ou comptes admins explicites)
est_admin = (user_role == "ADMIN") or (user_login in ["admin", "eric.kuter"])

# =====================================================================
# 5. EN-TÊTE ET ONGLETS DE NAVIGATION
# =====================================================================
st.title("🏛️ Portail Central HUB – GNC")
st.caption(
    f"Connecté en tant que : **{user.get('nom')}** (`{user_login}`) | Service :"
    f" **{user.get('service')}**"
)
st.divider()

if est_admin:
  tab_apps, tab_cat_apps, tab_droits, tab_users = st.tabs([
      "🚀 Vos Applications",
      "📱 Catalogue Apps",
      "🔑 Matrice des Droits",
      "👥 Comptes Utilisateurs",
  ])
else:
  tab_apps = st.container()
  tab_cat_apps = None
  tab_droits = None
  tab_users = None

# =====================================================================
# ONGLET 1 : CATALOGUE FILTRÉ SELON LA TABLE 'Autorisation'
# =====================================================================
with tab_apps:
  st.subheader("🚀 Vos Applications Autorisées")

  try:
    # 1. Chargement de toutes les applications actives du catalogue
    res_apps = (
        supabase.table("Application")
        .select("*")
        .eq("actif", True)
        .order("nom")
        .execute()
    )
    toutes_les_apps = res_apps.data or []

    # 2. Chargement des autorisations spécifiques pour l'utilisateur non-admin
    if not est_admin:
      res_droits = (
          supabase.table("Autorisation")
          .select("code_app")
          .eq("login", user_login)
          .execute()
      )
      codes_autorises = [d["code_app"] for d in (res_droits.data or [])]

      # 🎯 CORRECTION MAJEURE DU FILTRAGE PYTHON
      apps_visibles = [
          a
          for a in toutes_les_apps
          if (a.get("code_app") or a.get("code")) in codes_autorises
      ]
    else:
      # Les Administrateurs ont une vue complète sur toutes les applications
      apps_visibles = toutes_les_apps

  except Exception as e:
    st.error(f"Erreur lors du filtrage du catalogue : {e}")
    apps_visibles = []

  # Affichage des tuiles sous forme de grille (2 colonnes)
  if apps_visibles:
    cols = st.columns(2)
    for index, app in enumerate(apps_visibles):
      col_courante = cols[index % 2]
      with col_courante:
        with st.container(border=True):
          st.markdown(f"### {app.get('icone', '📱')} {app.get('nom')}")
          st.caption(app.get("description", ""))
          st.link_button(
              f"Ouvrir {app.get('nom')} ↗️",
              app.get("url", "#"),
              use_container_width=True,
          )
  else:
    st.info(
        "ℹ️ Aucune application ne vous est actuellement attribuée dans la table"
        " 'Autorisation'. Veuillez contacter un administrateur."
    )

# =====================================================================
# ONGLETS D'ADMINISTRATION (RÉSERVÉS ADMIN / ERIC.KUTER)
# =====================================================================
if est_admin:

  # --- ONGLET 2 : GESTION DU CATALOGUE DES APPLICATIONS ---
  with tab_cat_apps:
    st.subheader("📱 Administration du Catalogue (Table `Application`)")

    with st.expander("➕ Déclarer une Nouvelle Application", expanded=False):
      with st.form("form_add_app"):
        c1, c2 = st.columns(2)
        with c1:
          f_app_code = (
              st.text_input("Code Unique App (ex: SECURITE_INCENDIE)")
              .upper()
              .strip()
          )
          f_app_nom = st.text_input("Nom de l'application")
          f_app_icone = st.text_input("Icône (Emoji)", value="🔥")
        with c2:
          f_app_url = st.text_input(
              "URL Streamlit Cloud",
              value="https://securite-incendie.streamlit.app",
          )
          f_app_desc = st.text_area("Description rapide")

        if st.form_submit_button(
            "➕ Ajouter au Catalogue", use_container_width=True
        ):
          if f_app_code and f_app_nom and f_app_url:
            try:
              supabase.table("Application").insert({
                  "code_app": f_app_code,
                  "nom": f_app_nom,
                  "icone": f_app_icone,
                  "url": f_app_url,
                  "description": f_app_desc,
                  "actif": True,
              }).execute()
              st.success(f"✅ Application '{f_app_nom}' ajoutée !")
              st.rerun()
            except Exception as err:
              st.error(f"Erreur : {err}")
          else:
            st.warning("⚠️ Code, Nom et URL sont obligatoires.")

    st.divider()

    try:
      res_cat = supabase.table("Application").select("*").order("nom").execute()
      liste_cat = res_cat.data or []
      if liste_cat:
        with st.form("form_edit_catalogue"):
          st.data_editor(
              liste_cat,
              key="editeur_catalogue_apps",
              use_container_width=True,
              hide_index=True,
              num_rows="dynamic",
              column_order=[
                  "code_app",
                  "nom",
                  "icone",
                  "url",
                  "description",
                  "actif",
              ],
              column_config={
                  "code_app": st.column_config.TextColumn(
                      "Code App", disabled=True
                  ),
                  "nom": st.column_config.TextColumn("Nom", required=True),
                  "icone": st.column_config.TextColumn("Emoji"),
                  "url": st.column_config.TextColumn("URL Publique"),
                  "actif": st.column_config.CheckboxColumn(
                      "Actif", default=True
                  ),
              },
          )
          if st.form_submit_button(
              "💾 Sauvegarder les modifications du Catalogue",
              use_container_width=True,
          ):
            j_cat = st.session_state["editeur_catalogue_apps"]

            if j_cat.get("deleted_rows"):
              for idx in j_cat["deleted_rows"]:
                c_del = liste_cat[int(idx)]["code_app"]
                supabase.table("Application").delete().eq(
                    "code_app", c_del
                ).execute()

            if j_cat.get("edited_rows"):
              for idx, modifs in j_cat["edited_rows"].items():
                c_mod = liste_cat[int(idx)]["code_app"]
                supabase.table("Application").update(modifs).eq(
                    "code_app", c_mod
                ).execute()

            st.success("✅ Catalogue mis à jour !")
            st.rerun()
    except Exception as e:
      st.error(f"Erreur catalogue : {e}")

  # --- ONGLET 3 : MATRICE DES DROITS SUR LA TABLE 'Autorisation' ---
  with tab_droits:
    st.subheader("🔑 Matrice des Droits (Table `Autorisation`)")
    st.caption(
        "Cochez ou décochez les applications pour ajouter ou supprimer les"
        " lignes dans la table Autorisation."
    )

    try:
      res_u = supabase.table("Utilisateur").select("login, nom").execute()
      users_list = {u["login"]: u["nom"] for u in (res_u.data or [])}

      u_selectionne = st.selectbox(
          "👤 Choisir un Utilisateur à habiliter :",
          options=list(users_list.keys()),
          format_func=lambda x: f"{x} ({users_list.get(x)})",
      )

      if u_selectionne:
        st.write(
            "Gestion des accès pour :"
            f" **{users_list.get(u_selectionne)}** (`{u_selectionne}`)"
        )

        res_d = (
            supabase.table("Autorisation")
            .select("code_app")
            .eq("login", u_selectionne)
            .execute()
        )
        apps_autorisees_actuelles = [
            d["code_app"] for d in (res_d.data or [])
        ]

        with st.form("form_matrice_autorisation"):
          cochages = {}
          for app in toutes_les_apps:
            code_app = app.get("code_app") or app.get("code")

            if code_app:
              est_coche = code_app in apps_autorisees_actuelles
              cochages[code_app] = st.checkbox(
                  f"{app.get('icone', '📱')} **{app.get('nom')}** (`{code_app}`)",
                  value=est_coche,
              )

          if st.form_submit_button(
              "💾 Enregistrer les Autorisations de cet Utilisateur",
              use_container_width=True,
          ):
            for code_app, coche in cochages.items():
              deja_en_base = code_app in apps_autorisees_actuelles

              if coche and not deja_en_base:
                supabase.table("Autorisation").insert({
                    "login": u_selectionne,
                    "code_app": code_app,
                }).execute()

              elif not coche and deja_en_base:
                supabase.table("Autorisation").delete().eq(
                    "login", u_selectionne
                ).eq("code_app", code_app).execute()

            st.success(
                f"✅ Autorisations mises à jour pour '{u_selectionne}' !"
            )
            st.rerun()

    except Exception as e:
      st.error(f"Erreur lors de la gestion des autorisations : {e}")

  # --- ONGLET 4 : GESTION DES COMPTES UTILISATEURS ---
  with tab_users:
    st.subheader("👥 Gestion des Comptes Utilisateurs (Table `Utilisateur`)")

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
            "💾 Enregistrer le Compte", use_container_width=True
        )

      if btn_valider_compte:
        if not f_login or not f_mdp or not f_nom:
          st.warning("⚠️ Le Login, le Mot de Passe et le Nom sont requis.")
        else:
          hash_mdp = auth.hacher_mot_de_passe(f_mdp)
          try:
            res_exist = (
                supabase.table("Utilisateur")
                .select("id")
                .eq("login", f_login)
                .execute()
            )
            donnees_compte = {
                "login": f_login,
                "mdp": hash_mdp,
                "nom": f_nom,
                "role": f_role,
                "service": f_service or "NON DÉFINI",
            }
            if res_exist.data:
              supabase.table("Utilisateur").update(donnees_compte).eq(
                  "login", f_login
              ).execute()
              st.success(f"✅ Compte '{f_login}' mis à jour !")
            else:
              supabase.table("Utilisateur").insert(donnees_compte).execute()
              st.success(f"✅ Compte '{f_login}' créé !")
            st.rerun()
          except Exception as err:
            st.error(f"❌ Erreur Supabase : {err}")

    st.divider()

    try:
      res_users = (
          supabase.table("Utilisateur").select("*").order("login").execute()
      )
      liste_users = res_users.data or []
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
                      "Login", disabled=True
                  ),
                  "nom": st.column_config.TextColumn("Nom", required=True),
                  "role": st.column_config.SelectboxColumn(
                      "Rôle", options=["USER", "ADMIN"], required=True
                  ),
                  "service": st.column_config.TextColumn("Service"),
              },
          )
          if st.form_submit_button(
              "💾 Sauvegarder les modifications Comptes",
              use_container_width=True,
          ):
            j_u = st.session_state["editeur_utilisateurs_portail"]
            if j_u.get("deleted_rows"):
              for idx in j_u["deleted_rows"]:
                log_del = liste_users[int(idx)]["login"]
                supabase.table("Utilisateur").delete().eq(
                    "login", log_del
                ).execute()
            if j_u.get("edited_rows"):
              for idx, modifs in j_u["edited_rows"].items():
                log_mod = liste_users[int(idx)]["login"]
                supabase.table("Utilisateur").update(modifs).eq(
                    "login", log_mod
                ).execute()
            st.success("✅ Base Utilisateurs mise à jour !")
            st.rerun()
    except Exception as e:
      st.error(f"Erreur utilisateurs : {e}")