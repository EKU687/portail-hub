# =====================================================================
# APPLICATION : PORTAIL CENTRAL HUB (portail-gnc)
# Inclus : Catalogue dynamique, Matrice de droits granulaire, 
#           Gestion Utilisateurs, Chiffrement / Modification de MDP autonome,
#           et REFERO (Gestion des référentiels MDM).
# =====================================================================
import cadre_entreprise.auth as auth
import cadre_entreprise.ui as ui
from cadre_entreprise.database import supabase
import streamlit as st
import pandas as pd

# =====================================================================
# 1. CONFIGURATION DE LA PAGE
# =====================================================================
st.set_page_config(
    page_title="Portail Central HUB - GNC",
    layout="wide",
    page_icon="🏛️",
)

# =====================================================================
# 2. AUTHENTIFICATION
# =====================================================================
if not auth.est_connecte():
    ui.afficher_ecran_login("Portail Central HUB", "🏛️")
    st.stop()

ui.afficher_sidebar_standard()

# =====================================================================
# 3. PROFIL UTILISATEUR & MODIFICATION DE MOT DE PASSE
# =====================================================================
user = auth.get_user_info()
user_login = str(user.get("login", "")).lower().strip()
user_role = str(user.get("role", "")).upper().strip()

# Définition des privilèges Administrateur
est_admin = (user_role == "ADMIN") or (user_login in ["admin", "eric.kuter"])

with st.sidebar:
    st.divider()
    with st.expander("🔑 Modifier mon mot de passe"):
        with st.form("form_changement_mdp_utilisateur", clear_on_submit=True):
            old_pass = st.text_input("Mot de passe actuel", type="password")
            new_pass1 = st.text_input("Nouveau mot de passe", type="password")
            new_pass2 = st.text_input("Confirmer le nouveau", type="password")

            btn_valider_changement = st.form_submit_button(
                "💾 Valider la modification", use_container_width=True
            )

        if btn_valider_changement:
            if not old_pass or not new_pass1 or not new_pass2:
                st.warning("⚠️ Tous les champs sont obligatoires.")
            elif new_pass1 != new_pass2:
                st.error("❌ Les deux nouveaux mots de passe ne correspondent pas.")
            else:
                succes, msg = auth.changer_mon_mot_de_passe(
                    user_login, old_pass, new_pass1
                )
                if succes:
                    st.success(msg)
                else:
                    st.error(msg)

# =====================================================================
# 4. EN-TÊTE ET ONGLETS DE NAVIGATION
# =====================================================================
st.title("🏛️ Portail Central HUB – GNC")
st.caption(
    f"Connecté en tant que : **{user.get('nom')}** (`{user_login}`) | Service :"
    f" **{user.get('service')}**"
)
st.divider()

if est_admin:
    tab_apps, tab_cat_apps, tab_droits, tab_users, tab_refero = st.tabs([
        "🚀 Vos Applications",
        "📱 Catalogue Apps",
        "🔑 Matrice des Droits",
        "👥 Comptes Utilisateurs",
        "⚙️ Référentiels (REFERO)"
    ])
else:
    tab_apps = st.container()
    tab_cat_apps, tab_droits, tab_users, tab_refero = None, None, None, None


# =====================================================================
# ONGLET 1 : CATALOGUE FILTRÉ
# =====================================================================
with tab_apps:
    st.subheader("🚀 Vos Applications Autorisées")
    try:
        res_apps = supabase.table("Application").select("*").eq("actif", True).order("nom").execute()
        toutes_les_apps = res_apps.data or []

        if not est_admin:
            res_droits = supabase.table("Autorisation").select("code_app").eq("login", user_login).execute()
            codes_autorises = [d["code_app"] for d in (res_droits.data or [])]
            apps_visibles = [a for a in toutes_les_apps if (a.get("code_app") or a.get("code")) in codes_autorises]
        else:
            apps_visibles = toutes_les_apps
    except Exception as e:
        st.error(f"Erreur lors du filtrage du catalogue : {e}")
        apps_visibles = []

    if apps_visibles:
        cols = st.columns(2)
        for index, app in enumerate(apps_visibles):
            with cols[index % 2]:
                with st.container(border=True):
                    st.markdown(f"### {app.get('icone', '📱')} {app.get('nom')}")
                    st.caption(app.get("description", ""))
                    st.link_button(f"Ouvrir {app.get('nom')} ↗️", app.get("url", "#"), use_container_width=True)
    else:
        st.info("ℹ️ Aucune application ne vous est actuellement attribuée.")


# =====================================================================
# ONGLETS D'ADMINISTRATION (RÉSERVÉS ADMIN)
# =====================================================================
if est_admin:

    # --- ONGLET 2 : CATALOGUE ---
    with tab_cat_apps:
        st.subheader("📱 Administration du Catalogue (Table `Application`)")
        with st.expander("➕ Déclarer une Nouvelle Application", expanded=False):
            with st.form("form_add_app"):
                c1, c2 = st.columns(2)
                with c1:
                    f_app_code = st.text_input("Code Unique App").upper().strip()
                    f_app_nom = st.text_input("Nom de l'application")
                    f_app_icone = st.text_input("Icône (Emoji)", value="🔥")
                with c2:
                    f_app_url = st.text_input("URL Streamlit Cloud", value="https://")
                    f_app_desc = st.text_area("Description rapide")

                if st.form_submit_button("➕ Ajouter au Catalogue", use_container_width=True):
                    if f_app_code and f_app_nom and f_app_url:
                        try:
                            supabase.table("Application").insert({
                                "code_app": f_app_code, "nom": f_app_nom, "icone": f_app_icone,
                                "url": f_app_url, "description": f_app_desc, "actif": True,
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
                        liste_cat, key="editeur_catalogue_apps", use_container_width=True, hide_index=True, num_rows="dynamic",
                        column_order=["code_app", "nom", "icone", "url", "description", "actif"],
                        column_config={
                            "code_app": st.column_config.TextColumn("Code App", disabled=True),
                            "nom": st.column_config.TextColumn("Nom", required=True),
                            "icone": st.column_config.TextColumn("Emoji"),
                            "url": st.column_config.TextColumn("URL Publique"),
                            "actif": st.column_config.CheckboxColumn("Actif", default=True),
                        },
                    )
                    if st.form_submit_button("💾 Sauvegarder les modifications du Catalogue", use_container_width=True):
                        j_cat = st.session_state["editeur_catalogue_apps"]
                        if j_cat.get("deleted_rows"):
                            for idx in j_cat["deleted_rows"]:
                                supabase.table("Application").delete().eq("code_app", liste_cat[int(idx)]["code_app"]).execute()
                        if j_cat.get("edited_rows"):
                            for idx, modifs in j_cat["edited_rows"].items():
                                supabase.table("Application").update(modifs).eq("code_app", liste_cat[int(idx)]["code_app"]).execute()
                        st.success("✅ Catalogue mis à jour !")
                        st.rerun()
        except Exception as e:
            st.error(f"Erreur catalogue : {e}")

    # --- ONGLET 3 : DROITS GRANULAIRES (RÔLES & PÉRIMÈTRES) ---
    with tab_droits:
        st.subheader("🔑 Matrice des Droits (Table `Autorisation`)")
        st.caption("Gestion granulaire des accès applicatifs, rôles et périmètres d'intervention.")
        
        try:
            res_u = supabase.table("Utilisateur").select("login, nom").execute()
            users_list = {u["login"]: u["nom"] for u in (res_u.data or [])}
            
            u_selectionne = st.selectbox(
                "👤 Choisir un Utilisateur à habiliter :", 
                options=list(users_list.keys()), 
                format_func=lambda x: f"{x} ({users_list.get(x)})"
            )

            if u_selectionne:
                # Récupération de l'ensemble des autorisations enregistrées pour cet utilisateur
                res_d = supabase.table("Autorisation").select("*").eq("login", u_selectionne).execute()
                auths_utilisateur = {d["code_app"]: d for d in (res_d.data or [])}

                st.markdown("---")
                st.markdown(f"#### Configuration des accès pour **{users_list.get(u_selectionne)}** (`{u_selectionne}`)")

                with st.form(f"form_matrice_autorisation_{u_selectionne}"):
                    modifications = {}

                    for app in toutes_les_apps:
                        code_app = app.get("code_app") or app.get("code")
                        nom_app = app.get("nom")
                        icone_app = app.get("icone", "📱")

                        if code_app:
                            # État actuel en base de données
                            auth_actuelle = auths_utilisateur.get(code_app, {})
                            est_autorise = code_app in auths_utilisateur
                            role_actuel = auth_actuelle.get("role") or "UTILISATEUR"
                            perim_actuel = auth_actuelle.get("perimetre") or "RESTREINT"

                            st.markdown(f"##### {icone_app} **{nom_app}** (`{code_app}`)")
                            col_chk, col_role, col_perim = st.columns([1.5, 2, 2])

                            # 1. Case d'activation d'accès
                            acces = col_chk.checkbox(
                                "Autoriser l'accès", 
                                value=est_autorise, 
                                key=f"chk_{u_selectionne}_{code_app}"
                            )

                            # 2. Sélecteur de Rôle (Spécifique IDENTIS vs Standard)
                            if code_app == "IDENTIS":
                                liste_roles = ["GESTIONNAIRE_LOCAL", "ADMIN_NEDAP", "IMPRIMEUR", "SUPER_ADMIN"]
                            else:
                                liste_roles = ["UTILISATEUR", "ADMINISTRATEUR", "SUPER_ADMIN"]

                            idx_role = liste_roles.index(role_actuel) if role_actuel in liste_roles else 0
                            
                            role = col_role.selectbox(
                                "Rôle attribué",
                                options=liste_roles,
                                index=idx_role,
                                disabled=not acces,
                                key=f"role_{u_selectionne}_{code_app}"
                            )

                            # 3. Sélecteur de Périmètre
                            liste_perim = ["RESTREINT", "TOUT"]
                            idx_perim = liste_perim.index(perim_actuel) if perim_actuel in liste_perim else 0
                            
                            perim = col_perim.selectbox(
                                "Périmètre de vision",
                                options=liste_perim,
                                index=idx_perim,
                                disabled=not acces,
                                help="RESTREINT = Sa direction uniquement | TOUT = Toutes les directions",
                                key=f"perim_{u_selectionne}_{code_app}"
                            )

                            modifications[code_app] = {
                                "acces": acces,
                                "role": role,
                                "perimetre": perim
                            }
                            st.divider()

                    btn_sauver_droits = st.form_submit_button("💾 Enregistrer les Autorisations", type="primary", use_container_width=True)

                if btn_sauver_droits:
                    for code_app, data in modifications.items():
                        if data["acces"]:
                            # Upsert pour insérer ou mettre à jour la ligne avec le rôle et périmètre
                            supabase.table("Autorisation").upsert({
                                "login": u_selectionne,
                                "code_app": code_app,
                                "role": data["role"],
                                "perimetre": data["perimetre"]
                            }, on_conflict="login, code_app").execute()
                        else:
                            # Suppression si l'accès a été décoché
                            supabase.table("Autorisation") \
                                .delete() \
                                .eq("login", u_selectionne) \
                                .eq("code_app", code_app) \
                                .execute()

                    st.success(f"✅ Habilitations mises à jour avec succès pour '{u_selectionne}' !")
                    st.balloons()
                    st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de la gestion des habilitations : {e}")

    # --- ONGLET 4 : COMPTES UTILISATEURS ---
    with tab_users:
        st.subheader("👥 Gestion des Comptes Utilisateurs (Table `Utilisateur`)")
        with st.expander("➕ Créer ou Réinitialiser un Compte", expanded=False):
            with st.form("form_gestion_compte_portail", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                f_login = c1.text_input("Identifiant / Login").lower().strip()
                f_mdp = c1.text_input("Nouveau Mot de Passe", type="password")
                f_nom = c2.text_input("Nom Complet / Libellé")
                f_role = c2.selectbox("Rôle", ["USER", "ADMIN"])
                f_service = c3.text_input("Code Service")

                if st.form_submit_button("💾 Enregistrer le Compte", use_container_width=True):
                    if not f_login or not f_mdp or not f_nom:
                        st.warning("⚠️ Le Login, le Mot de Passe et le Nom sont requis.")
                    else:
                        hash_mdp = auth.hacher_mot_de_passe(f_mdp)
                        try:
                            res_exist = supabase.table("Utilisateur").select("id").eq("login", f_login).execute()
                            donnees_compte = {"login": f_login, "mdp": hash_mdp, "nom": f_nom, "role": f_role, "service": f_service or "NON DÉFINI"}
                            if res_exist.data:
                                supabase.table("Utilisateur").update(donnees_compte).eq("login", f_login).execute()
                                st.success(f"✅ Compte '{f_login}' mis à jour !")
                            else:
                                supabase.table("Utilisateur").insert(donnees_compte).execute()
                                st.success(f"✅ Compte '{f_login}' créé !")
                            st.rerun()
                        except Exception as err:
                            st.error(f"❌ Erreur Supabase : {err}")

        st.divider()
        try:
            res_users = supabase.table("Utilisateur").select("*").order("login").execute()
            liste_users = res_users.data or []
            if liste_users:
                with st.form("form_editeur_liste_utilisateurs"):
                    st.data_editor(
                        liste_users, key="editeur_utilisateurs_portail", use_container_width=True, hide_index=True, num_rows="dynamic",
                        column_order=["login", "nom", "role", "service"],
                        column_config={
                            "login": st.column_config.TextColumn("Login", disabled=True),
                            "nom": st.column_config.TextColumn("Nom", required=True),
                            "role": st.column_config.SelectboxColumn("Rôle", options=["USER", "ADMIN"], required=True),
                            "service": st.column_config.TextColumn("Service"),
                        },
                    )
                    if st.form_submit_button("💾 Sauvegarder les modifications Comptes", use_container_width=True):
                        j_u = st.session_state["editeur_utilisateurs_portail"]
                        if j_u.get("deleted_rows"):
                            for idx in j_u["deleted_rows"]:
                                supabase.table("Utilisateur").delete().eq("login", liste_users[int(idx)]["login"]).execute()
                        if j_u.get("edited_rows"):
                            for idx, modifs in j_u["edited_rows"].items():
                                supabase.table("Utilisateur").update(modifs).eq("login", liste_users[int(idx)]["login"]).execute()
                        st.success("✅ Base Utilisateurs mise à jour !")
                        st.rerun()
        except Exception as e:
            st.error(f"Erreur utilisateurs : {e}")

    # =====================================================================
    # --- ONGLET 5 : RÉFÉRENTIELS (REFERO) ---
    # =====================================================================
    with tab_refero:
        st.subheader("⚙️ Administration des Référentiels (REFERO)")
        st.caption("Gestion du Master Data Management (Directions, Services, Sites).")
        
        sub_dir, sub_serv, sub_site, sub_soc = st.tabs(["🏢 Directions", "📂 Services", "📍 Sites", "🤝 Sociétés"])
        
        # -------------------------------------------------------------
        # 5.1 DIRECTIONS
        # -------------------------------------------------------------
        with sub_dir:
            with st.expander("➕ Ajouter une Direction", expanded=False):
                with st.form("form_add_direction", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    nom_dir = c1.text_input("Nom de la direction *")
                    sigle_dir = c2.text_input("Sigle (ex: DTSI) *").upper()
                    code_dir = st.text_input("Code direction")
                    
                    if st.form_submit_button("💾 Enregistrer Direction", type="primary"):
                        if nom_dir and sigle_dir:
                            try:
                                supabase.table("Directions").insert({
                                    "nom_direction": nom_dir, "sigle_direction": sigle_dir,
                                    "code_direction": code_dir, "actif": True
                                }).execute()
                                st.success(f"✅ Direction {sigle_dir} ajoutée !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                        else:
                            st.warning("Le nom et le sigle sont obligatoires.")
            
            try:
                res_dir = supabase.table("Directions").select("*").order("sigle_direction").execute()
                liste_dir = res_dir.data or []
                if liste_dir:
                    st.markdown("#### 📋 Base des Directions")
                    with st.form("form_edit_directions"):
                        st.data_editor(
                            liste_dir, key="edit_directions", use_container_width=True, hide_index=True, num_rows="dynamic",
                            column_order=["sigle_direction", "nom_direction", "code_direction", "actif"],
                            column_config={
                                "sigle_direction": st.column_config.TextColumn("Sigle", required=True),
                                "nom_direction": st.column_config.TextColumn("Nom complet"),
                                "code_direction": st.column_config.TextColumn("Code"),
                                "actif": st.column_config.CheckboxColumn("Actif", default=True)
                            }
                        )
                        if st.form_submit_button("💾 Sauvegarder les modifications"):
                            j_dir = st.session_state["edit_directions"]
                            if j_dir.get("deleted_rows"):
                                for idx in j_dir["deleted_rows"]:
                                    supabase.table("Directions").delete().eq("id", liste_dir[int(idx)]["id"]).execute()
                            if j_dir.get("edited_rows"):
                                for idx, modifs in j_dir["edited_rows"].items():
                                    supabase.table("Directions").update(modifs).eq("id", liste_dir[int(idx)]["id"]).execute()
                            st.success("✅ Base Directions mise à jour !")
                            st.rerun()
            except Exception as e:
                st.error(f"Erreur Directions : {e}")

        # -------------------------------------------------------------
        # 5.2 SERVICES
        # -------------------------------------------------------------
        with sub_serv:
            directions_dispo = {d['sigle_direction']: d['id'] for d in (liste_dir if 'liste_dir' in locals() else [])}
            with st.expander("➕ Ajouter un Service", expanded=False):
                if not directions_dispo:
                    st.warning("⚠️ Créez d'abord une Direction.")
                else:
                    with st.form("form_add_service", clear_on_submit=True):
                        c1, c2 = st.columns(2)
                        nom_srv = c1.text_input("Nom du service *")
                        sigle_srv = c2.text_input("Sigle (ex: SINF) *").upper()
                        
                        c3, c4 = st.columns(2)
                        dir_parente = c3.selectbox("Rattaché à la Direction *", options=list(directions_dispo.keys()))
                        code_srv = c4.text_input("Code service")
                        
                        if st.form_submit_button("💾 Enregistrer Service", type="primary"):
                            if nom_srv and sigle_srv:
                                try:
                                    supabase.table("Services").insert({
                                        "nom_service": nom_srv, "sigle_service": sigle_srv,
                                        "code_service": code_srv, "id_direction": directions_dispo[dir_parente],
                                        "actif": True
                                    }).execute()
                                    st.success(f"✅ Service {sigle_srv} ajouté dans {dir_parente} !")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur : {e}")
                            else:
                                st.warning("Le nom et le sigle sont obligatoires.")

            try:
                res_srv = supabase.table("Services").select("*, Directions(sigle_direction)").order("sigle_service").execute()
                if res_srv.data:
                    st.markdown("#### 📋 Base des Services")
                    df_srv = pd.DataFrame(res_srv.data)
                    df_srv['Direction_Parente'] = df_srv['Directions'].apply(lambda x: x['sigle_direction'] if isinstance(x, dict) else 'N/A')
                    st.dataframe(
                        df_srv[['sigle_service', 'nom_service', 'Direction_Parente', 'code_service', 'actif']],
                        column_config={"sigle_service": "Sigle", "nom_service": "Nom du service", "Direction_Parente": "Direction", "code_service": "Code", "actif": "Actif"},
                        use_container_width=True, hide_index=True
                    )
            except Exception as e:
                st.error(f"Erreur Services : {e}")
                
        # -------------------------------------------------------------
        # 5.3 SITES (AVEC NORME NEDAP)
        # -------------------------------------------------------------
        with sub_site:
            types_nedap = ["Généraux", "Sensibles", "Critiques"]
            with st.expander("➕ Ajouter un Site", expanded=False):
                with st.form("form_add_site", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    nom_site = c1.text_input("Nom du site *")
                    code_site = c2.text_input("Code site (ex: NOUA)")

                    c3, c4 = st.columns(2)
                    type_site = c3.selectbox("Type de site (Standard NEDAP) *", options=types_nedap)
                    commune = c4.text_input("Commune (ex: Nouméa)")

                    if st.form_submit_button("💾 Enregistrer Site", type="primary"):
                        if nom_site:
                            try:
                                supabase.table("Sites").insert({
                                    "nom_site": nom_site, "code_site": code_site,
                                    "type_site": type_site, "commune": commune, "actif": True
                                }).execute()
                                st.success(f"✅ Site '{nom_site}' ajouté !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                        else:
                            st.warning("Le nom du site est obligatoire.")

            try:
                res_site = supabase.table("Sites").select("*").order("nom_site").execute()
                liste_sites = res_site.data or []
                if liste_sites:
                    st.markdown("#### 📋 Base des Sites")
                    with st.form("form_edit_sites"):
                        st.data_editor(
                            liste_sites, key="edit_sites", use_container_width=True, hide_index=True, num_rows="dynamic",
                            column_order=["nom_site", "code_site", "type_site", "commune", "actif"],
                            column_config={
                                "nom_site": st.column_config.TextColumn("Nom du site", required=True),
                                "code_site": st.column_config.TextColumn("Code"),
                                "type_site": st.column_config.SelectboxColumn("Type (NEDAP)", options=types_nedap, required=True),
                                "commune": st.column_config.TextColumn("Commune"),
                                "actif": st.column_config.CheckboxColumn("Actif", default=True)
                            }
                        )
                        if st.form_submit_button("💾 Sauvegarder les modifications"):
                            j_site = st.session_state["edit_sites"]
                            if j_site.get("deleted_rows"):
                                for idx in j_site["deleted_rows"]:
                                    supabase.table("Sites").delete().eq("id", liste_sites[int(idx)]["id"]).execute()
                            if j_site.get("edited_rows"):
                                for idx, modifs in j_site["edited_rows"].items():
                                    supabase.table("Sites").update(modifs).eq("id", liste_sites[int(idx)]["id"]).execute()
                            st.success("✅ Base Sites mise à jour !")
                            st.rerun()
            except Exception as e:
                st.error(f"Erreur Sites : {e}")

        # -------------------------------------------------------------
        # 5.4 GESTION DES SOCIÉTÉS (PRESTATAIRES)
        # -------------------------------------------------------------
        with sub_soc:
            with st.expander("➕ Ajouter une Société", expanded=False):
                with st.form("form_add_societe", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    nom_soc = c1.text_input("Nom de la société *")
                    num_ridet = c2.text_input("N° RIDET (Optionnel)")

                    c3, c4 = st.columns(2)
                    contact_nom = c3.text_input("Nom du contact principal")
                    contact_email = c4.text_input("Email du contact")

                    if st.form_submit_button("💾 Enregistrer Société", type="primary"):
                        if nom_soc:
                            try:
                                supabase.table("Societes").insert({
                                    "nom_societe": nom_soc,
                                    "num_ridet": num_ridet,
                                    "contact_nom": contact_nom,
                                    "contact_email": contact_email,
                                    "actif": True
                                }).execute()
                                st.success(f"✅ Société '{nom_soc}' ajoutée au référentiel !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur Supabase : {e}")
                        else:
                            st.warning("Le nom de la société est obligatoire.")

            # Affichage et Édition des Sociétés
            try:
                res_soc = supabase.table("Societes").select("*").order("nom_societe").execute()
                liste_soc = res_soc.data or []

                if liste_soc:
                    st.markdown("#### 📋 Base des Sociétés Prestataires")
                    with st.form("form_edit_societes"):
                        st.data_editor(
                            liste_soc,
                            key="edit_societes",
                            use_container_width=True,
                            hide_index=True,
                            num_rows="dynamic",
                            column_order=["nom_societe", "num_ridet", "contact_nom", "contact_email", "actif"],
                            column_config={
                                "nom_societe": st.column_config.TextColumn("Nom de la société", required=True),
                                "num_ridet": st.column_config.TextColumn("N° RIDET"),
                                "contact_nom": st.column_config.TextColumn("Contact"),
                                "contact_email": st.column_config.TextColumn("Email"),
                                "actif": st.column_config.CheckboxColumn("Actif", default=True)
                            }
                        )
                        
                        if st.form_submit_button("💾 Sauvegarder les modifications"):
                            j_soc = st.session_state["edit_societes"]
                            if j_soc.get("deleted_rows"):
                                for idx in j_soc["deleted_rows"]:
                                    id_del = liste_soc[int(idx)]["id"]
                                    supabase.table("Societes").delete().eq("id", id_del).execute()
                            if j_soc.get("edited_rows"):
                                for idx, modifs in j_soc["edited_rows"].items():
                                    id_mod = liste_soc[int(idx)]["id"]
                                    supabase.table("Societes").update(modifs).eq("id", id_mod).execute()

                            st.success("✅ Base Sociétés mise à jour !")
                            st.rerun()
            except Exception as e:
                st.error(f"Erreur de lecture Sociétés : {e}")