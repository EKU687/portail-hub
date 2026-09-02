# =====================================================================
# APPLICATION : PORTAIL CENTRAL HUB (portail-gnc)
# Inclus : Catalogue dynamique, Matrice de droits granulaire,
#          Gestion Utilisateurs (avec Email, Rôles ORBIS / Portail, Site & YubiKey),
#          Chiffrement / Modification de MDP autonome,
#          Redirection Sécurisée par Jeton Inter-Applications (Sessions_Portail),
#          Authentification Hybride (Mot de passe & YubiKey/FIDO2),
#          et REFERO (Gestion des référentiels MDM avec liaison Site/Direction).
# =====================================================================
import uuid
import cadre_entreprise.auth as auth
import cadre_entreprise.ui as ui
from cadre_entreprise.database import supabase
import pandas as pd
import streamlit as st

# =====================================================================
# 1. CONFIGURATION DE LA PAGE
# =====================================================================
st.set_page_config(
    page_title="Portail Central HUB - GNC",
    layout="wide",
    page_icon="🏛️",
)

# =====================================================================
# 2. AUTHENTIFICATION (DÉLÉGUÉE AU SDK SÉCURISÉ)
# =====================================================================
if not auth.est_connecte():
    ui.afficher_ecran_login(nom_application="Portail Central HUB", icone="🏛️")
    st.stop()

ui.afficher_sidebar_standard()

# =====================================================================
# 3. MATRICE GLOBALE DES RÔLES & HELPER SITES
# =====================================================================
# Liste officielle des rôles partagés entre Portail HUB et ORBIS
ROLES_PORTAIL_ET_ORBIS = [
    "AGENT_SECU",    # Agent de Garde / Rondier (ORBIS)
    "HABI_ORBIS",    # Agent Habilité / Chef de Poste (ORBIS)
    "CHARGE_SURETE", # Chargé de Sûreté
    "USER",          # Utilisateur standard Portail
    "ADMIN",         # Administrateur Général
    "IMPRIMEUR",     # Rôle spécifique badges / impression
]


def obtenir_sites_actifs_liste() -> list[str]:
    """Interroge la table 'Sites' de Supabase et retourne la liste des nom_site actifs avec 'TOUS' en première option."""
    try:
        res = (
            supabase.table("Sites")
            .select("nom_site")
            .eq("actif", True)
            .order("nom_site")
            .execute()
        )
        sites = [
            row["nom_site"] for row in (res.data or []) if row.get("nom_site")
        ]
        if "TOUS" not in sites:
            sites.insert(0, "TOUS")
        return sites
    except Exception:
        return ["TOUS", "DINUM", "DOUMER", "GNC", "HÔTEL DU GOUVERNEMENT"]


# =====================================================================
# 4. PROFIL UTILISATEUR, HELPER REDIRECTION & MOT DE PASSE
# =====================================================================
user = auth.get_user_info()
user_login = str(user.get("login", "")).lower().strip()
user_role = str(user.get("role", "")).upper().strip()
user_id_num = user.get("id")  # ID numérique BIGINT de Utilisateur

# Définition des privilèges Administrateur
est_admin = (user_role == "ADMIN") or (user_login in ["admin", "eric.kuter"])


def rediriger_vers_application(app_code: str, app_nom: str, url_base: str):
    """Génère un jeton temporaire unique (Sessions_Portail) et propose le lien sécurisé vers l'application cible."""
    try:
        # 1. Nettoyage de l'URL de base (suppression des slashs finaux)
        url_clean = str(url_base).strip().rstrip("/")

        # 2. Génération du token unique
        token_session = f"GNC-{app_code.upper()}-{uuid.uuid4().hex[:12].upper()}"

        # 3. Enregistrement en BDD Supabase (Table Sessions_Portail)
        payload_session = {
            "token": token_session,
            "user_id": user_id_num,
            "application_cible": app_code.upper(),
            "actif": True,
        }
        supabase.table("Sessions_Portail").insert(payload_session).execute()

        # 4. Construction de l'URL sécurisée
        url_securisee = f"{url_clean}/?session_token={token_session}"

        # 5. Affichage d'un bouton de redirection HTML propre sans boucle JS !
        st.success(f"🔑 Jeton de sécurité généré pour **{app_nom}** !")

        st.markdown(
            f"""
            <div style="margin-top: 15px; margin-bottom: 15px;">
                <a href="{url_securisee}" target="_blank" style="text-decoration: none;">
                    <button style="
                        background-color: #198754;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        font-size: 16px;
                        font-weight: bold;
                        border-radius: 6px;
                        cursor: pointer;
                        width: 100%;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    ">
                        🚀 Cliquez ici pour ouvrir {app_nom} en toute sécurité ↗️
                    </button>
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    except Exception as err:
        st.error(
            f"❌ Erreur lors du lancement sécurisé de l'application {app_nom} :"
            f" {err}"
        )


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
                st.error(
                    "❌ Les deux nouveaux mots de passe ne correspondent pas."
                )
            else:
                succes, msg = auth.changer_mon_mot_de_passe(
                    user_login, old_pass, new_pass1
                )
                if succes:
                    st.success(msg)
                else:
                    st.error(msg)

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
    tab_apps, tab_cat_apps, tab_droits, tab_users, tab_refero = st.tabs([
        "🚀 Vos Applications",
        "📱 Catalogue Apps",
        "🔑 Matrice des Droits",
        "👥 Comptes Utilisateurs",
        "⚙️ Référentiels (REFERO)",
    ])
else:
    tab_apps = st.container()
    tab_cat_apps, tab_droits, tab_users, tab_refero = None, None, None, None


# =====================================================================
# ONGLET 1 : CATALOGUE FILTRÉ (AVEC LANCEMENT SÉCURISÉ)
# =====================================================================
with tab_apps:
    st.subheader("🚀 Vos Applications Autorisées")
    try:
        res_apps = (
            supabase.table("Application")
            .select("*")
            .eq("actif", True)
            .order("nom")
            .execute()
        )
        toutes_les_apps = res_apps.data or []

        if not est_admin:
            res_droits = (
                supabase.table("Autorisation")
                .select("code_app")
                .eq("login", user_login)
                .execute()
            )
            codes_autorises = [d["code_app"] for d in (res_droits.data or [])]
            apps_visibles = [
                a
                for a in toutes_les_apps
                if (a.get("code_app") or a.get("code")) in codes_autorises
            ]
        else:
            apps_visibles = toutes_les_apps
    except Exception as e:
        st.error(f"Erreur lors du filtrage du catalogue : {e}")
        apps_visibles = []

    if apps_visibles:
        cols = st.columns(2)
        for index, app in enumerate(apps_visibles):
            code_app = app.get("code_app") or app.get("code") or f"APP_{index}"
            nom_app = app.get("nom", "Application")
            url_app = app.get("url", "#")
            icone_app = app.get("icone", "📱")

            with cols[index % 2]:
                with st.container(border=True):
                    st.markdown(f"### {icone_app} {nom_app}")
                    st.caption(app.get("description", ""))

                    # 🎯 LANCEMENT SÉCURISÉ PAR JETON DE SESSION (PORTAL GUARD)
                    if st.button(
                        f"🚀 Lancer {nom_app}",
                        key=f"btn_launch_{code_app}_{index}",
                        type="primary",
                        use_container_width=True,
                    ):
                        rediriger_vers_application(
                            app_code=code_app,
                            app_nom=nom_app,
                            url_base=url_app,
                        )
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
                    f_app_code = (
                        st.text_input("Code Unique App").upper().strip()
                    )
                    f_app_nom = st.text_input("Nom de l'application")
                    f_app_icone = st.text_input("Icône (Emoji)", value="🔥")
                with c2:
                    f_app_url = st.text_input(
                        "URL Streamlit Cloud", value="https://"
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
                            st.success(
                                f"✅ Application '{f_app_nom}' ajoutée !"
                            )
                            st.rerun()
                        except Exception as err:
                            st.error(f"Erreur : {err}")
                    else:
                        st.warning("⚠️ Code, Nom et URL sont obligatoires.")

        st.divider()
        try:
            res_cat = (
                supabase.table("Application")
                .select("*")
                .order("nom")
                .execute()
            )
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
                            "nom": st.column_config.TextColumn(
                                "Nom", required=True
                            ),
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
                                supabase.table("Application").delete().eq(
                                    "code_app",
                                    liste_cat[int(idx)]["code_app"],
                                ).execute()
                        if j_cat.get("edited_rows"):
                            for idx, modifs in j_cat["edited_rows"].items():
                                supabase.table("Application").update(
                                    modifs
                                ).eq(
                                    "code_app",
                                    liste_cat[int(idx)]["code_app"],
                                ).execute()
                        st.success("✅ Catalogue mis à jour !")
                        st.rerun()
        except Exception as e:
            st.error(f"Erreur catalogue : {e}")

    # --- ONGLET 3 : DROITS GRANULAIRES (RÔLES & PÉRIMÈTRES) ---
    with tab_droits:
        st.subheader("🔑 Matrice des Droits (Table `Autorisation`)")
        st.caption(
            "Gestion granulaire des accès applicatifs, rôles et périmètres"
            " d'intervention."
        )

        try:
            res_u = (
                supabase.table("Utilisateur").select("login, nom").execute()
            )
            users_list = {u["login"]: u["nom"] for u in (res_u.data or [])}

            u_selectionne = st.selectbox(
                "👤 Choisir un Utilisateur à habiliter :",
                options=list(users_list.keys()),
                format_func=lambda x: f"{x} ({users_list.get(x)})",
            )

            if u_selectionne:
                res_d = (
                    supabase.table("Autorisation")
                    .select("*")
                    .eq("login", u_selectionne)
                    .execute()
                )
                auths_utilisateur = {
                    d["code_app"]: d for d in (res_d.data or [])
                }

                st.markdown("---")
                st.markdown(
                    f"#### Configuration des accès pour"
                    f" **{users_list.get(u_selectionne)}** (`{u_selectionne}`)"
                )

                with st.form(f"form_matrice_autorisation_{u_selectionne}"):
                    modifications = {}

                    for app in toutes_les_apps:
                        code_app = app.get("code_app") or app.get("code")
                        nom_app = app.get("nom")
                        icone_app = app.get("icone", "📱")

                        if code_app:
                            auth_actuelle = auths_utilisateur.get(code_app, {})
                            est_autorise = code_app in auths_utilisateur
                            role_actuel = (
                                auth_actuelle.get("role") or "UTILISATEUR"
                            )
                            perim_actuel = (
                                auth_actuelle.get("perimetre") or "RESTREINT"
                            )

                            st.markdown(
                                f"##### {icone_app} **{nom_app}** (`{code_app}`)"
                            )
                            col_chk, col_role, col_perim = st.columns(
                                [1.5, 2, 2]
                            )

                            acces = col_chk.checkbox(
                                "Autoriser l'accès",
                                value=est_autorise,
                                key=f"chk_{u_selectionne}_{code_app}",
                            )

                            if code_app == "IDENTIS":
                                liste_roles = [
                                    "GESTIONNAIRE_LOCAL",
                                    "ADMIN_NEDAP",
                                    "IMPRIMEUR",
                                    "SUPER_ADMIN",
                                ]
                            else:
                                liste_roles = [
                                    "UTILISATEUR",
                                    "ADMINISTRATEUR",
                                    "SUPER_ADMIN",
                                ]

                            idx_role = (
                                liste_roles.index(role_actuel)
                                if role_actuel in liste_roles
                                else 0
                            )

                            role = col_role.selectbox(
                                "Rôle attribué",
                                options=liste_roles,
                                index=idx_role,
                                disabled=not acces,
                                key=f"role_{u_selectionne}_{code_app}",
                            )

                            liste_perim = ["RESTREINT", "TOUT"]
                            idx_perim = (
                                liste_perim.index(perim_actuel)
                                if perim_actuel in liste_perim
                                else 0
                            )

                            perim = col_perim.selectbox(
                                "Périmètre de vision",
                                options=liste_perim,
                                index=idx_perim,
                                disabled=not acces,
                                help=(
                                    "RESTREINT = Sa direction uniquement | TOUT"
                                    " = Toutes les directions"
                                ),
                                key=f"perim_{u_selectionne}_{code_app}",
                            )

                            modifications[code_app] = {
                                "acces": acces,
                                "role": role,
                                "perimetre": perim,
                            }
                            st.divider()

                    btn_sauver_droits = st.form_submit_button(
                        "💾 Enregistrer les Autorisations",
                        type="primary",
                        use_container_width=True,
                    )

                if btn_sauver_droits:
                    for code_app, data in modifications.items():
                        if data["acces"]:
                            supabase.table("Autorisation").upsert(
                                {
                                    "login": u_selectionne,
                                    "code_app": code_app,
                                    "role": data["role"],
                                    "perimetre": data["perimetre"],
                                },
                                on_conflict="login, code_app",
                            ).execute()
                        else:
                            (
                                supabase.table("Autorisation")
                                .delete()
                                .eq("login", u_selectionne)
                                .eq("code_app", code_app)
                                .execute()
                            )

                    st.success(
                        "✅ Habilitations mises à jour avec succès pour"
                        f" '{u_selectionne}' !"
                    )
                    st.balloons()
                    st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de la gestion des habilitations : {e}")

    # =====================================================================
    # --- ONGLET 4 : COMPTES UTILISATEURS (ROLES, SITES & ENRÔLEMENT YUBIKEY) ---
    # =====================================================================
    with tab_users:
        st.subheader(
            "👥 Gestion des Comptes Utilisateurs (Table `Utilisateur`)"
        )
        st.caption(
            "Création et gestion des comptes utilisateurs avec attribution des"
            " services REFERO, des rôles applicatifs, du site de travail et"
            " enrôlement des clés physiques YubiKey."
        )

        sites_disponibles = obtenir_sites_actifs_liste()

        try:
            res_dirs = (
                supabase.table("Directions")
                .select("id, sigle_direction, nom_direction")
                .eq("actif", True)
                .execute()
            )
            res_servs = (
                supabase.table("Services")
                .select("id, sigle_service, nom_service, id_direction")
                .eq("actif", True)
                .execute()
            )

            liste_dirs = res_dirs.data or []
            liste_servs = res_servs.data or []

            map_dirs_form = {
                f"{d['sigle_direction']} - {d['nom_direction']}": d
                for d in liste_dirs
            }
        except Exception as e:
            st.error(
                f"❌ Erreur lors du chargement des référentiels REFERO : {e}"
            )
            liste_dirs, liste_servs, map_dirs_form = [], [], {}

        with st.expander(
            "➕ Créer ou Réinitialiser un Compte Utilisateur", expanded=False
        ):

            choix_dir_label = st.selectbox(
                "🏢 1. Choisir d'abord la Direction de rattachement (REFERO) :",
                options=["-- Sélectionner une Direction --"]
                + list(map_dirs_form.keys()),
            )

            servs_disponibles = []
            if choix_dir_label != "-- Sélectionner une Direction --":
                dir_obj = map_dirs_form[choix_dir_label]
                servs_disponibles = [
                    f"{s['sigle_service']} - {s['nom_service']}"
                    for s in liste_servs
                    if s.get("id_direction") == dir_obj["id"]
                ]

            with st.form("form_gestion_compte_portail", clear_on_submit=True):
                col_u1, col_u2, col_u3 = st.columns(3)
                f_login = (
                    col_u1.text_input("Identifiant / Login *").lower().strip()
                )
                f_mdp = col_u1.text_input("Mot de Passe *", type="password")

                f_nom = col_u2.text_input("Nom Complet / Libellé *").strip()
                f_email = col_u2.text_input(
                    "Adresse Email Officielle *",
                    placeholder="prenom.nom@gouv.nc",
                ).strip()

                f_role = col_u3.selectbox(
                    "🔑 Rôle & Habilitation *",
                    options=ROLES_PORTAIL_ET_ORBIS,
                    index=0,
                    help=(
                        "AGENT_SECU et HABI_ORBIS sont requis pour l'accès à"
                        " la Main Courante ORBIS."
                    ),
                )
                f_service_str = col_u3.selectbox(
                    "2. Service de rattachement *",
                    options=servs_disponibles
                    if servs_disponibles
                    else ["👈 Choisissez d'abord une direction"],
                )

                f_site_defaut = st.selectbox(
                    "📍 3. Site de travail / PC Garde de rattachement (ORBIS) *",
                    options=sites_disponibles,
                    index=sites_disponibles.index("DINUM")
                    if "DINUM" in sites_disponibles
                    else 0,
                    help=(
                        "Site par défaut affecté aux agents pour la Main"
                        " Courante ORBIS. Choisir 'TOUS' pour les administrateurs."
                    ),
                )

                # 🛡️ SECTION ENRÔLEMENT YUBIKEY
                st.markdown("---")
                st.markdown("##### 🛡️ Habilitation & Enrôlement YubiKey")
                col_y1, col_y2 = st.columns([2, 1])

                f_yubikey_public_id = (
                    col_y1.text_input(
                        "ID Public YubiKey (Device ID)",
                        placeholder="Insérez et pressez la YubiKey (12 premiers caractères)",
                        help="Saisissez ou touchez la YubiKey. Les 12 premiers caractères identifient la clé physique.",
                    )
                    .lower()
                    .strip()
                )

                # Extraction automatique des 12 premiers caractères si un OTP complet est collé
                if f_yubikey_public_id and len(f_yubikey_public_id) >= 12:
                    f_yubikey_public_id = f_yubikey_public_id[:12]

                f_yubikey_mandatory = col_y2.checkbox(
                    "Connexion YubiKey Obligatoire",
                    value=(f_role == "ADMIN"),
                    help="Si coché, l'utilisateur NE POURRA PAS se connecter par mot de passe.",
                )

                btn_valider_compte = st.form_submit_button(
                    "💾 Enregistrer le Compte",
                    type="primary",
                    use_container_width=True,
                )

            if btn_valider_compte:
                code_service_clean = (
                    f_service_str.split(" - ")[0]
                    if " - " in f_service_str
                    else None
                )

                if (
                    not f_login
                    or not f_mdp
                    or not f_nom
                    or not f_email
                    or not code_service_clean
                    or "Choisissez" in f_service_str
                ):
                    st.warning(
                        "⚠️ Tous les champs (Login, Mot de passe, Nom, Email,"
                        " Direction et Service) sont obligatoires."
                    )
                elif "@" not in f_email:
                    st.error("❌ Veuillez renseigner une adresse email valide.")
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
                            "email": f_email,
                            "role": f_role,
                            "service": code_service_clean,
                            "site_defaut": f_site_defaut,
                            "yubikey_public_id": f_yubikey_public_id
                            if f_yubikey_public_id
                            else None,
                            "yubikey_mandatory": f_yubikey_mandatory,
                        }

                        if res_exist.data:
                            supabase.table("Utilisateur").update(
                                donnees_compte
                            ).eq("login", f_login).execute()
                            st.success(
                                f"✅ Compte `{f_login}` mis à jour avec le rôle"
                                f" **{f_role}**, l'email **{f_email}**, le site"
                                f" **{f_site_defaut}** et la YubiKey"
                                f" **{f_yubikey_public_id or 'Aucune'}** !"
                            )
                        else:
                            supabase.table("Utilisateur").insert(
                                donnees_compte
                            ).execute()
                            st.success(
                                f"✅ Compte `{f_login}` créé avec succès avec"
                                f" le rôle **{f_role}** sur le site"
                                f" **{f_site_defaut}** !"
                            )

                        st.rerun()
                    except Exception as err:
                        st.error(
                            "❌ Erreur lors de l'enregistrement Supabase :"
                            f" {err}"
                        )

        st.divider()

        try:
            res_users = (
                supabase.table("Utilisateur")
                .select("*")
                .order("login")
                .execute()
            )
            liste_users = res_users.data or []

            if liste_users:
                st.markdown("#### 📋 Liste des Comptes Utilisateurs")
                with st.form("form_editeur_liste_utilisateurs"):
                    st.data_editor(
                        liste_users,
                        key="editeur_utilisateurs_portail",
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic",
                        column_order=[
                            "login",
                            "nom",
                            "email",
                            "role",
                            "service",
                            "site_defaut",
                            "yubikey_public_id",
                            "yubikey_mandatory",
                        ],
                        column_config={
                            "login": st.column_config.TextColumn(
                                "Login", disabled=True
                            ),
                            "nom": st.column_config.TextColumn(
                                "Nom complet", required=True
                            ),
                            "email": st.column_config.TextColumn(
                                "Adresse Email", required=True
                            ),
                            "role": st.column_config.SelectboxColumn(
                                "Rôle (Portail & ORBIS)",
                                options=ROLES_PORTAIL_ET_ORBIS,
                                required=True,
                            ),
                            "service": st.column_config.TextColumn(
                                "Code Service (REFERO)", required=True
                            ),
                            "site_defaut": st.column_config.SelectboxColumn(
                                "Site de travail (ORBIS)",
                                options=sites_disponibles,
                                required=True,
                            ),
                            "yubikey_public_id": st.column_config.TextColumn(
                                "ID YubiKey (12 car.)"
                            ),
                            "yubikey_mandatory": st.column_config.CheckboxColumn(
                                "YubiKey Obligatoire", default=False
                            ),
                        },
                    )

                    if st.form_submit_button(
                        "💾 Sauvegarder les modifications du tableau",
                        use_container_width=True,
                    ):
                        j_u = st.session_state["editeur_utilisateurs_portail"]

                        if j_u.get("deleted_rows"):
                            for idx in j_u["deleted_rows"]:
                                supabase.table("Utilisateur").delete().eq(
                                    "login", liste_users[int(idx)]["login"]
                                ).execute()

                        if j_u.get("edited_rows"):
                            for idx, modifs in j_u["edited_rows"].items():
                                supabase.table("Utilisateur").update(
                                    modifs
                                ).eq(
                                    "login", liste_users[int(idx)]["login"]
                                ).execute()

                        st.success(
                            "✅ Modifications des comptes sauvegardées !"
                        )
                        st.rerun()
        except Exception as e:
            st.error(f"❌ Erreur de lecture de la table Utilisateur : {e}")

    # =====================================================================
    # --- ONGLET 5 : RÉFÉRENTIELS (REFERO) ---
    # =====================================================================
    with tab_refero:
        st.subheader("⚙️ Administration des Référentiels (REFERO)")
        st.caption(
            "Gestion du Master Data Management (Directions, Services, Sites)."
        )

        sub_dir, sub_serv, sub_site, sub_soc = st.tabs(
            ["🏢 Directions", "📂 Services", "📍 Sites", "🤝 Sociétés"]
        )

        try:
            res_all_sites = (
                supabase.table("Sites")
                .select("id, code_site, nom_site")
                .eq("actif", True)
                .execute()
            )
            map_sites_refero = {
                row["id"]: (
                    f"{row.get('code_site', '')} —"
                    f" {row.get('nom_site', '')}".strip(" —")
                )
                for row in (res_all_sites.data or [])
            }
        except Exception:
            map_sites_refero = {}

        # -------------------------------------------------------------
        # 5.1 DIRECTIONS
        # -------------------------------------------------------------
        with sub_dir:
            with st.expander("➕ Ajouter une Direction", expanded=False):
                with st.form("form_add_direction", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    nom_dir = c1.text_input(
                        "Nom de la direction *",
                        placeholder="Ex: Direction des Affaires Sanitaires",
                    )
                    sigle_dir = (
                        c2.text_input("Sigle (ex: DASS) *").upper().strip()
                    )

                    c3, c4 = st.columns(2)
                    site_id_selected = c3.selectbox(
                        "Site physique d'affectation *",
                        options=[""] + list(map_sites_refero.keys()),
                        format_func=lambda x: map_sites_refero.get(
                            x, "-- Choisir un site physique --"
                        ),
                    )
                    code_dir_input = (
                        c4.text_input(
                            "Code direction (optionnel)",
                            placeholder="Ex: DASS-DOUMER",
                        )
                        .upper()
                        .strip()
                    )

                    if st.form_submit_button(
                        "💾 Enregistrer Direction", type="primary"
                    ):
                        if nom_dir and sigle_dir and site_id_selected:
                            try:
                                code_site_str = map_sites_refero[
                                    site_id_selected
                                ].split(" — ")[0]
                                code_final = (
                                    code_dir_input
                                    if code_dir_input
                                    else f"{sigle_dir}-{code_site_str}"
                                )

                                supabase.table("Directions").insert({
                                    "nom_direction": nom_dir,
                                    "sigle_direction": sigle_dir,
                                    "code_direction": code_final,
                                    "id_site": site_id_selected,
                                    "actif": True,
                                }).execute()
                                st.success(
                                    f"✅ Direction '{sigle_dir}' ajoutée sur"
                                    f" le site {code_site_str} !"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                        else:
                            st.warning(
                                "⚠️ Le nom, le sigle et le site physique"
                                " d'affectation sont obligatoires."
                            )

            try:
                res_dir = (
                    supabase.table("Directions")
                    .select("*")
                    .order("sigle_direction")
                    .execute()
                )
                liste_dir = res_dir.data or []
                if liste_dir:
                    st.markdown("#### 📋 Base des Directions")
                    with st.form("form_edit_directions"):
                        st.data_editor(
                            liste_dir,
                            key="edit_directions",
                            use_container_width=True,
                            hide_index=True,
                            num_rows="dynamic",
                            column_order=[
                                "sigle_direction",
                                "nom_direction",
                                "code_direction",
                                "id_site",
                                "actif",
                            ],
                            column_config={
                                "sigle_direction": st.column_config.TextColumn(
                                    "Sigle", required=True
                                ),
                                "nom_direction": st.column_config.TextColumn(
                                    "Nom complet"
                                ),
                                "code_direction": st.column_config.TextColumn(
                                    "Code Direction"
                                ),
                                "id_site": st.column_config.SelectboxColumn(
                                    "Site d'affectation",
                                    options=list(map_sites_refero.keys()),
                                    format_func=lambda x: map_sites_refero.get(
                                        x, "Non défini"
                                    ),
                                    required=True,
                                ),
                                "actif": st.column_config.CheckboxColumn(
                                    "Actif", default=True
                                ),
                            },
                        )
                        if st.form_submit_button(
                            "💾 Sauvegarder les modifications"
                        ):
                            j_dir = st.session_state["edit_directions"]
                            if j_dir.get("deleted_rows"):
                                for idx in j_dir["deleted_rows"]:
                                    supabase.table("Directions").delete().eq(
                                        "id", liste_dir[int(idx)]["id"]
                                    ).execute()
                            if j_dir.get("edited_rows"):
                                for idx, modifs in j_dir["edited_rows"].items():
                                    supabase.table("Directions").update(
                                        modifs
                                    ).eq("id", liste_dir[int(idx)]["id"]).execute()
                            st.success("✅ Base Directions mise à jour !")
                            st.rerun()
            except Exception as e:
                st.error(f"Erreur Directions : {e}")

        # -------------------------------------------------------------
        # 5.2 SERVICES
        # -------------------------------------------------------------
        with sub_serv:
            directions_dispo = {
                d["sigle_direction"]: d["id"]
                for d in (liste_dir if "liste_dir" in locals() else [])
            }
            with st.expander("➕ Ajouter un Service", expanded=False):
                if not directions_dispo:
                    st.warning("⚠️ Créez d'abord une Direction.")
                else:
                    with st.form("form_add_service", clear_on_submit=True):
                        c1, c2 = st.columns(2)
                        nom_srv = c1.text_input("Nom du service *")
                        sigle_srv = c2.text_input("Sigle (ex: SINF) *").upper()

                        c3, c4 = st.columns(2)
                        dir_parente = c3.selectbox(
                            "Rattaché à la Direction *",
                            options=list(directions_dispo.keys()),
                        )
                        code_srv = c4.text_input("Code service")

                        if st.form_submit_button(
                            "💾 Enregistrer Service", type="primary"
                        ):
                            if nom_srv and sigle_srv:
                                try:
                                    supabase.table("Services").insert({
                                        "nom_service": nom_srv,
                                        "sigle_service": sigle_srv,
                                        "code_service": code_srv,
                                        "id_direction": directions_dispo[
                                            dir_parente
                                        ],
                                        "actif": True,
                                    }).execute()
                                    st.success(
                                        f"✅ Service {sigle_srv} ajouté dans"
                                        f" {dir_parente} !"
                                    )
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur : {e}")
                            else:
                                st.warning(
                                    "Le nom et le sigle sont obligatoires."
                                )

            try:
                res_srv = (
                    supabase.table("Services")
                    .select("*, Directions(sigle_direction)")
                    .order("sigle_service")
                    .execute()
                )
                if res_srv.data:
                    st.markdown("#### 📋 Base des Services")
                    df_srv = pd.DataFrame(res_srv.data)
                    df_srv["Direction_Parente"] = df_srv["Directions"].apply(
                        lambda x: x["sigle_direction"]
                        if isinstance(x, dict)
                        else "N/A"
                    )
                    st.dataframe(
                        df_srv[[
                            "sigle_service",
                            "nom_service",
                            "Direction_Parente",
                            "code_service",
                            "actif",
                        ]],
                        column_config={
                            "sigle_service": "Sigle",
                            "nom_service": "Nom du service",
                            "Direction_Parente": "Direction",
                            "code_service": "Code",
                            "actif": "Actif",
                        },
                        use_container_width=True,
                        hide_index=True,
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
                    type_site = c3.selectbox(
                        "Type de site (Standard NEDAP) *", options=types_nedap
                    )
                    commune = c4.text_input("Commune (ex: Nouméa)")

                    if st.form_submit_button(
                        "💾 Enregistrer Site", type="primary"
                    ):
                        if nom_site:
                            try:
                                supabase.table("Sites").insert({
                                    "nom_site": nom_site,
                                    "code_site": code_site,
                                    "type_site": type_site,
                                    "commune": commune,
                                    "actif": True,
                                }).execute()
                                st.success(f"✅ Site '{nom_site}' ajouté !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {e}")
                        else:
                            st.warning("Le nom du site est obligatoire.")

            try:
                res_site = (
                    supabase.table("Sites")
                    .select("*")
                    .order("nom_site")
                    .execute()
                )
                liste_sites = res_site.data or []
                if liste_sites:
                    st.markdown("#### 📋 Base des Sites")
                    with st.form("form_edit_sites"):
                        st.data_editor(
                            liste_sites,
                            key="edit_sites",
                            use_container_width=True,
                            hide_index=True,
                            num_rows="dynamic",
                            column_order=[
                                "nom_site",
                                "code_site",
                                "type_site",
                                "commune",
                                "actif",
                            ],
                            column_config={
                                "nom_site": st.column_config.TextColumn(
                                    "Nom du site", required=True
                                ),
                                "code_site": st.column_config.TextColumn(
                                    "Code"
                                ),
                                "type_site": st.column_config.SelectboxColumn(
                                    "Type (NEDAP)",
                                    options=types_nedap,
                                    required=True,
                                ),
                                "commune": st.column_config.TextColumn(
                                    "Commune"
                                ),
                                "actif": st.column_config.CheckboxColumn(
                                    "Actif", default=True
                                ),
                            },
                        )
                        if st.form_submit_button(
                            "💾 Sauvegarder les modifications"
                        ):
                            j_site = st.session_state["edit_sites"]
                            if j_site.get("deleted_rows"):
                                for idx in j_site["deleted_rows"]:
                                    supabase.table("Sites").delete().eq(
                                        "id", liste_sites[int(idx)]["id"]
                                    ).execute()
                            if j_site.get("edited_rows"):
                                for idx, modifs in j_site["edited_rows"].items():
                                    supabase.table("Sites").update(modifs).eq(
                                        "id", liste_sites[int(idx)]["id"]
                                    ).execute()
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

                    if st.form_submit_button(
                        "💾 Enregistrer Société", type="primary"
                    ):
                        if nom_soc:
                            try:
                                supabase.table("Societes").insert({
                                    "nom_societe": nom_soc,
                                    "num_ridet": num_ridet,
                                    "contact_nom": contact_nom,
                                    "contact_email": contact_email,
                                    "actif": True,
                                }).execute()
                                st.success(
                                    f"✅ Société '{nom_soc}' ajoutée au"
                                    " référentiel !"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur Supabase : {e}")
                        else:
                            st.warning(
                                "Le nom de la société est obligatoire."
                            )

            try:
                res_soc = (
                    supabase.table("Societes")
                    .select("*")
                    .order("nom_societe")
                    .execute()
                )
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
                            column_order=[
                                "nom_societe",
                                "num_ridet",
                                "contact_nom",
                                "contact_email",
                                "actif",
                            ],
                            column_config={
                                "nom_societe": st.column_config.TextColumn(
                                    "Nom de la société", required=True
                                ),
                                "num_ridet": st.column_config.TextColumn(
                                    "N° RIDET"
                                ),
                                "contact_nom": st.column_config.TextColumn(
                                    "Contact"
                                ),
                                "contact_email": st.column_config.TextColumn(
                                    "Email"
                                ),
                                "actif": st.column_config.CheckboxColumn(
                                    "Actif", default=True
                                ),
                            },
                        )

                        if st.form_submit_button(
                            "💾 Sauvegarder les modifications"
                        ):
                            j_soc = st.session_state["edit_societes"]
                            if j_soc.get("deleted_rows"):
                                for idx in j_soc["deleted_rows"]:
                                    id_del = liste_soc[int(idx)]["id"]
                                    supabase.table("Societes").delete().eq(
                                        "id", id_del
                                    ).execute()
                            if j_soc.get("edited_rows"):
                                for idx, modifs in j_soc["edited_rows"].items():
                                    id_mod = liste_soc[int(idx)]["id"]
                                    supabase.table("Societes").update(
                                        modifs
                                    ).eq("id", id_mod).execute()

                            st.success("✅ Base Sociétés mise à jour !")
                            st.rerun()
            except Exception as e:
                st.error(f"Erreur de lecture Sociétés : {e}")