"""
i18n.py — YASAFlaskified v0.9.6
Volledig drietalig: NL / FR / EN  (gelijkwaardig, gebruiker kiest bij login)

Gebruik:
  In templates : {{ t('key') }}
  In Python    : from i18n import get_translation; get_translation('key', lang)
"""

TRANSLATIONS = {

    # ── NAVIGATIE & LAYOUT ──────────────────────────────────────────────────
    "upload":               {"nl":"Upload",           "fr":"Télécharger",      "en":"Upload"},
    "history":              {"nl":"Geschiedenis",     "fr":"Historique",       "en":"History"},
    "dashboard":            {"nl":"Dashboard",        "fr":"Tableau de bord",  "en":"Dashboard"},
    "login":                {"nl":"Inloggen",         "fr":"Connexion",        "en":"Login"},
    "logout":               {"nl":"Uitloggen",        "fr":"Déconnexion",      "en":"Logout"},
    "sign_in":              {"nl":"Aanmelden",        "fr":"Se connecter",     "en":"Sign in"},
    "status":               {"nl":"Status",           "fr":"État",             "en":"Status"},
    "change_password":      {"nl":"Wachtwoord wijzigen","fr":"Changer mot de passe","en":"Change password"},
    "language":             {"nl":"Taal",             "fr":"Langue",           "en":"Language"},
    "choose_language":      {"nl":"Kies uw taal",    "fr":"Choisissez votre langue","en":"Choose your language"},
    "only_authorized":      {"nl":"Enkel voor bevoegde zorgverleners",
                             "fr":"Réservé aux professionnels de santé autorisés",
                             "en":"Authorized healthcare professionals only"},
    "disc_header":          {"nl":"Dit is onderzoekssoftware — geen medisch hulpmiddel. Geen CE-markering, geen FDA-goedkeuring. Alle resultaten vereisen verificatie door een arts.",
                             "fr":"Logiciel de recherche — pas un dispositif médical. Pas de marquage CE, pas d'autorisation FDA. Tous les résultats nécessitent une vérification par un médecin.",
                             "en":"This is research software — not a medical device. No CE mark, no FDA clearance. All results require physician verification.",
                             "de":"Dies ist Forschungssoftware — kein Medizinprodukt. Keine CE-Kennzeichnung, keine FDA-Zulassung. Alle Ergebnisse müssen von einem Arzt überprüft werden."},
    "settings":             {"nl":"Instellingen",    "fr":"Paramètres",       "en":"Settings"},
    "admin_panel":          {"nl":"Beheercentrum",   "fr":"Panneau d'admin",  "en":"Admin panel"},
    "user_management":      {"nl":"Gebruikersbeheer","fr":"Gestion des utilisateurs","en":"User management"},
    "site_management":      {"nl":"Sitebeheer",      "fr":"Gestion des sites","en":"Site management"},

    # ── AUTH ────────────────────────────────────────────────────────────────
    "username":             {"nl":"Gebruikersnaam",  "fr":"Nom d'utilisateur","en":"Username"},
    "password":             {"nl":"Wachtwoord",      "fr":"Mot de passe",     "en":"Password"},
    "current_password":     {"nl":"Huidig wachtwoord","fr":"Mot de passe actuel","en":"Current password"},
    "new_password":         {"nl":"Nieuw wachtwoord","fr":"Nouveau mot de passe","en":"New password"},
    "confirm_password":     {"nl":"Bevestig wachtwoord","fr":"Confirmer le mot de passe","en":"Confirm password"},
    "login_success":        {"nl":"Aanmelding geslaagd!","fr":"Connexion réussie !","en":"Login successful!"},
    "login_failed":         {"nl":"Ongeldige gebruikersnaam of wachtwoord.",
                             "fr":"Nom d'utilisateur ou mot de passe invalide.",
                             "en":"Invalid username or password."},
    "logged_out":           {"nl":"U bent uitgelogd.","fr":"Vous êtes déconnecté.","en":"You have been logged out."},
    "password_changed":     {"nl":"Wachtwoord succesvol gewijzigd.",
                             "fr":"Mot de passe modifié avec succès.",
                             "en":"Password changed successfully."},
    "admin_only_register":  {"nl":"Nieuwe gebruikers worden aangemaakt door de beheerder.",
                             "fr":"Les nouveaux utilisateurs sont créés par l'administrateur.",
                             "en":"New users are created by the administrator."},
    "experimental_warning": {"nl":"Experimenteel hulpmiddel — niet voor klinische diagnosestelling.",
                             "fr":"Outil expérimental — non destiné au diagnostic clinique.",
                             "en":"Experimental tool — not for clinical diagnosis."},

    # ── ROLLEN ──────────────────────────────────────────────────────────────
    "role":                 {"nl":"Rol",             "fr":"Rôle",             "en":"Role"},
    "role_admin":           {"nl":"Admin",           "fr":"Administrateur",   "en":"Admin"},
    "role_site":            {"nl":"Sitebeheerder",  "fr":"Gestionnaire site","en":"Site manager"},
    "role_user":            {"nl":"Gebruiker",       "fr":"Utilisateur",      "en":"User"},
    "role_desc_admin":      {"nl":"Volledige toegang, alle sites, gebruikersbeheer",
                             "fr":"Accès complet, tous les sites, gestion des utilisateurs",
                             "en":"Full access, all sites, user management"},
    "role_desc_site":       {"nl":"Beheert één site: eigen patiënten en gebruikers",
                             "fr":"Gère un site : patients et utilisateurs propres",
                             "en":"Manages one site: own patients and users"},
    "role_desc_user":       {"nl":"Uploaden + eigen resultaten + resultaten van eigen site",
                             "fr":"Téléchargement + propres résultats + résultats du site",
                             "en":"Upload + own results + site results"},
    "insufficient_rights":  {"nl":"Onvoldoende rechten voor deze pagina.",
                             "fr":"Droits insuffisants pour cette page.",
                             "en":"Insufficient rights for this page."},
    "site":                 {"nl":"Site / Ziekenhuis","fr":"Site / Hôpital",  "en":"Site / Hospital"},
    "all_sites":            {"nl":"Alle sites",      "fr":"Tous les sites",   "en":"All sites"},
    "no_site_assigned":     {"nl":"Geen site toegewezen","fr":"Aucun site attribué","en":"No site assigned"},

    # ── GEBRUIKERSBEHEER ────────────────────────────────────────────────────
    "add_user":             {"nl":"Gebruiker toevoegen","fr":"Ajouter un utilisateur","en":"Add user"},
    "delete_user":          {"nl":"Verwijderen",     "fr":"Supprimer",        "en":"Delete"},
    "reset_password":       {"nl":"Wachtwoord resetten","fr":"Réinitialiser mot de passe","en":"Reset password"},
    "user_created":         {"nl":"Gebruiker aangemaakt.","fr":"Utilisateur créé.","en":"User created."},
    "user_deleted":         {"nl":"Gebruiker verwijderd.","fr":"Utilisateur supprimé.","en":"User deleted."},
    "user_exists":          {"nl":"Gebruikersnaam bestaat al.","fr":"Ce nom d'utilisateur existe déjà.","en":"Username already exists."},
    "cannot_delete_admin":  {"nl":"Admin-gebruiker kan niet worden verwijderd.",
                             "fr":"L'utilisateur administrateur ne peut pas être supprimé.",
                             "en":"Admin user cannot be deleted."},
    "all_fields_required":  {"nl":"Alle velden zijn verplicht.","fr":"Tous les champs sont requis.","en":"All fields are required."},
    "admin_only":           {"nl":"Enkel voor beheerders.","fr":"Réservé aux administrateurs.","en":"Administrators only."},
    "set_role":             {"nl":"Rol instellen",   "fr":"Définir le rôle",  "en":"Set role"},
    "assign_site":          {"nl":"Site toewijzen",  "fr":"Attribuer un site","en":"Assign site"},

    # ── SITEBEHEER ──────────────────────────────────────────────────────────
    "site_name":            {"nl":"Sitenaam",        "fr":"Nom du site",      "en":"Site name"},
    "site_address":         {"nl":"Adres",           "fr":"Adresse",          "en":"Address"},
    "site_email":           {"nl":"E-mail",          "fr":"E-mail",           "en":"E-mail"},
    "site_phone":           {"nl":"Telefoon",        "fr":"Téléphone",        "en":"Phone"},
    "site_logo":            {"nl":"Logo (pad)",      "fr":"Logo (chemin)",    "en":"Logo (path)"},
    "site_url":             {"nl":"Website",         "fr":"Site web",         "en":"Website"},
    "site_language":        {"nl":"Standaardtaal",   "fr":"Langue par défaut","en":"Default language"},
    "site_added":           {"nl":"Site toegevoegd.","fr":"Site ajouté.",     "en":"Site added."},
    "site_updated":         {"nl":"Site bijgewerkt.","fr":"Site mis à jour.", "en":"Site updated."},
    "site_deleted":         {"nl":"Site verwijderd.","fr":"Site supprimé.",   "en":"Site deleted."},

    # ── UPLOAD ──────────────────────────────────────────────────────────────
    "upload_title":         {"nl":"EDF-bestand uploaden","fr":"Télécharger un fichier EDF","en":"Upload EDF file"},
    "select_file":          {"nl":"Bestand selecteren","fr":"Sélectionner un fichier","en":"Select file"},
    "start_upload":         {"nl":"Upload starten",  "fr":"Démarrer le téléchargement","en":"Start upload"},
    "uploading":            {"nl":"Bezig met uploaden…","fr":"Téléchargement en cours…","en":"Uploading…"},
    "upload_complete":      {"nl":"Upload voltooid.",  "fr":"Téléchargement terminé.","en":"Upload complete."},
    "file_too_large":       {"nl":"Bestand te groot.","fr":"Fichier trop volumineux.","en":"File too large."},

    # ── KANALEN ─────────────────────────────────────────────────────────────
    "channel_select_title": {"nl":"Kanaalkeuze & patiëntgegevens",
                             "fr":"Sélection des canaux et données patient",
                             "en":"Channel selection & patient data"},
    "eeg_channel":          {"nl":"EEG-kanaal (primair)","fr":"Canal EEG (primaire)","en":"EEG channel (primary)"},
    "eog_channel":          {"nl":"EOG-kanaal",       "fr":"Canal EOG",         "en":"EOG channel"},
    "emg_channel":          {"nl":"EMG-kanaal",       "fr":"Canal EMG",         "en":"EMG channel"},
    "extra_eeg_channels":   {"nl":"Extra EEG-kanalen","fr":"Canaux EEG supplémentaires","en":"Extra EEG channels"},
    "file":                 {"nl":"Bestand",          "fr":"Fichier",           "en":"File"},
    "channels_found":       {"nl":"kanalen gevonden", "fr":"canaux trouvés",    "en":"channels found"},
    "start_analysis":       {"nl":"Analyse starten",  "fr":"Lancer l'analyse",  "en":"Start analysis"},

    # ── PATIËNTGEGEVENS ─────────────────────────────────────────────────────
    "patient_data":         {"nl":"Patiëntgegevens",  "fr":"Données patient",   "en":"Patient data"},
    "patient_name":         {"nl":"Achternaam",        "fr":"Nom de famille",    "en":"Last name"},
    "patient_firstname":    {"nl":"Voornaam",          "fr":"Prénom",            "en":"First name"},
    "patient_id":           {"nl":"Patiënt-ID",        "fr":"ID patient",        "en":"Patient ID"},
    "dob":                  {"nl":"Geboortedatum",     "fr":"Date de naissance", "en":"Date of birth"},
    "sex":                  {"nl":"Geslacht",          "fr":"Sexe",              "en":"Sex"},
    "sex_m":                {"nl":"Man",               "fr":"Homme",             "en":"Male"},
    "sex_f":                {"nl":"Vrouw",             "fr":"Femme",             "en":"Female"},
    "bmi":                  {"nl":"BMI",               "fr":"IMC",               "en":"BMI"},
    "weight":               {"nl":"Gewicht (kg)",      "fr":"Poids (kg)",        "en":"Weight (kg)"},
    "height":               {"nl":"Lengte (cm)",       "fr":"Taille (cm)",       "en":"Height (cm)"},
    "diagnosis":            {"nl":"Diagnose",          "fr":"Diagnostic",        "en":"Diagnosis"},
    "comments":             {"nl":"Opmerkingen",       "fr":"Commentaires",      "en":"Comments"},
    "scorer":               {"nl":"Scorer",            "fr":"Scoreur",           "en":"Scorer"},
    "institution":          {"nl":"Instelling",        "fr":"Établissement",     "en":"Institution"},
    "recording_date":       {"nl":"Opnamedatum",       "fr":"Date d'enregistrement","en":"Recording date"},

    # ── PATIËNTKAART LABELS ─────────────────────────────────────────────────
    "name_label":           {"nl":"Naam",              "fr":"Nom",               "en":"Name"},
    "dob_label":            {"nl":"Geb.",              "fr":"Nais.",             "en":"DoB"},
    "sex_label":            {"nl":"Gesl.",             "fr":"Sexe",              "en":"Sex"},
    "inst_label":           {"nl":"Inst.",             "fr":"Étab.",             "en":"Inst."},
    "scorer_label":         {"nl":"Scorer",            "fr":"Scoreur",           "en":"Scorer"},

    # ── ANALYSE ─────────────────────────────────────────────────────────────
    "analysis_running":     {"nl":"Analyse wordt uitgevoerd",
                             "fr":"Analyse en cours",
                             "en":"Analysis in progress"},
    "analysis_description": {"nl":"De analyse combineert YASA AI-slaapstaging met regel-gebaseerde respiratoire scoring. "
                                   "Op het mesa_shhs profiel wordt daarbovenop een "
                                   "LightGBM candidate-classifier toegepast (psgscoring v0.6).",
                             "fr":"L'analyse combine le staging IA YASA avec un scoring respiratoire à base de règles. "
                                   "Sur le profil mesa_shhs s'y ajoute un "
                                   "classificateur de candidats LightGBM (psgscoring v0.6).",
                             "en":"The analysis combines YASA AI sleep staging with rule-based respiratory scoring. "
                                   "On the mesa_shhs profile a LightGBM candidate "
                                   "classifier is applied on top (psgscoring v0.6)."},
    "analysis_duration":    {"nl":"De analyse-duur hangt af van de opnameduur en welk profiel u kiest "
                                   "(typisch 3–10 min per recording).",
                             "fr":"La durée dépend de la durée d'enregistrement et du profil choisi "
                                   "(typiquement 3 à 10 min par enregistrement).",
                             "en":"Duration depends on recording length and chosen profile "
                                   "(typically 3–10 min per recording)."},
    "waiting_for_worker":   {"nl":"Wachten op worker…",   "fr":"En attente du worker…","en":"Waiting for worker…"},
    "analysis_complete":    {"nl":"Analyse voltooid!",    "fr":"Analyse terminée !",  "en":"Analysis complete!"},
    "all_results_available":{"nl":"Alle resultaten zijn beschikbaar.",
                             "fr":"Tous les résultats sont disponibles.",
                             "en":"All results are available."},
    "analysis_in_progress": {"nl":"Analyse bezig…",      "fr":"Analyse en cours…",   "en":"Analysis in progress…"},
    "analysis_results":     {"nl":"Analyseresultaten",   "fr":"Résultats d'analyse", "en":"Analysis results"},
    "clinical_usability":   {"nl":"Screening-tool en second opinion (~85% epoch-overeenkomst). "
                                   "Vervangt geen manuele scoring of medische diagnose.",
                             "fr":"Outil de dépistage et second avis (~85% concordance par époque). "
                                   "Ne remplace pas un scoring manuel ni un diagnostic médical.",
                             "en":"Screening tool and second opinion (~85% epoch agreement). "
                                   "Does not replace manual scoring or medical diagnosis."},

    # ── RESULTATEN ──────────────────────────────────────────────────────────
    "sleep_analysis_report":{"nl":"Slaapanalyse Rapport",
                             "fr":"Rapport d'Analyse du Sommeil",
                             "en":"Sleep Analysis Report"},
    "view_report":          {"nl":"Bekijk rapport",   "fr":"Voir le rapport",   "en":"View report"},
    "download_excel":       {"nl":"Download Excel",   "fr":"Télécharger Excel", "en":"Download Excel"},
    "download_psg":         {"nl":"Download PSG",     "fr":"Télécharger PSG",   "en":"Download PSG"},
    "download_fhir":        {"nl":"Download FHIR",    "fr":"Télécharger FHIR",  "en":"Download FHIR"},
    "generate_edfplus":     {"nl":"Genereer EDF+",    "fr":"Générer EDF+",      "en":"Generate EDF+"},
    "download_edfplus":     {"nl":"Download EDF+",    "fr":"Télécharger EDF+",  "en":"Download EDF+"},
    "download_json":        {"nl":"Download JSON",    "fr":"Télécharger JSON",  "en":"Download JSON"},
    "manual_scoring":       {"nl":"Manueel scoren",   "fr":"Scoring manuel",    "en":"Manual scoring"},

    # ── TABS ────────────────────────────────────────────────────────────────
    "tab_statistics":       {"nl":"Statistieken",     "fr":"Statistiques",      "en":"Statistics"},
    "tab_hypnogram":        {"nl":"Hypnogram",        "fr":"Hypnogramme",       "en":"Hypnogram"},
    "tab_spindles":         {"nl":"Spindels",         "fr":"Fuseaux",           "en":"Spindles"},
    "tab_slow_waves":       {"nl":"Trage golven",     "fr":"Ondes lentes",      "en":"Slow waves"},
    "tab_rem":              {"nl":"REM",              "fr":"REM",               "en":"REM"},
    "tab_bandpower":        {"nl":"Bandvermogen",     "fr":"Puissance spectrale","en":"Band power"},
    "tab_cycles":           {"nl":"Cycli",            "fr":"Cycles",            "en":"Cycles"},
    "tab_artifacts":        {"nl":"Artefacten",       "fr":"Artéfacts",         "en":"Artifacts"},
    "tab_respiratory":      {"nl":"Respiratoir",      "fr":"Respiratoire",      "en":"Respiratory"},
    "tab_spo2":             {"nl":"SpO2",             "fr":"SpO2",              "en":"SpO2"},
    "tab_plm":              {"nl":"PLM",              "fr":"MPJ",               "en":"PLM"},

    # ── SLAAPSTATISTIEKEN ───────────────────────────────────────────────────
    "sleep_statistics":     {"nl":"Slaapstatistieken","fr":"Statistiques du sommeil","en":"Sleep statistics"},
    "total_sleep_time":     {"nl":"Totale slaaptijd (TST)","fr":"Durée totale de sommeil (TST)","en":"Total sleep time (TST)"},
    "sleep_efficiency":     {"nl":"Slaapefficiëntie","fr":"Efficacité du sommeil","en":"Sleep efficiency"},
    "sleep_onset_latency":  {"nl":"Slaapladentie",   "fr":"Latence d'endormissement","en":"Sleep onset latency"},
    "waso":                 {"nl":"WASO",             "fr":"ETSA",              "en":"WASO"},
    "rem_latency":          {"nl":"REM-latentie",     "fr":"Latence REM",       "en":"REM latency"},
    "stage_w":              {"nl":"Stadium W",        "fr":"Stade W",           "en":"Stage W"},
    "stage_n1":             {"nl":"Stadium N1",       "fr":"Stade N1",          "en":"Stage N1"},
    "stage_n2":             {"nl":"Stadium N2",       "fr":"Stade N2",          "en":"Stage N2"},
    "stage_n3":             {"nl":"Stadium N3",       "fr":"Stade N3",          "en":"Stage N3"},
    "stage_rem":            {"nl":"REM",              "fr":"REM",               "en":"REM"},

    # ── RESPIRATOIR ─────────────────────────────────────────────────────────
    "respiratory_analysis": {"nl":"Respiratoire analyse","fr":"Analyse respiratoire","en":"Respiratory analysis"},
    "ahi":                  {"nl":"AHI",              "fr":"IAH",               "en":"AHI"},
    "oahi":                 {"nl":"OAHI",             "fr":"IOAH",              "en":"OAHI"},
    "severity":             {"nl":"Ernst",            "fr":"Sévérité",          "en":"Severity"},
    "normal":               {"nl":"Normaal",          "fr":"Normal",            "en":"Normal"},
    "mild_osa":             {"nl":"Mild OSA",         "fr":"SAOS léger",        "en":"Mild OSA"},
    "moderate_osa":         {"nl":"Matig OSA",        "fr":"SAOS modéré",       "en":"Moderate OSA"},
    "severe_osa":           {"nl":"Ernstig OSA",      "fr":"SAOS sévère",       "en":"Severe OSA"},
    # ── Analysegeschiedenis: OSAS/CSAS-type + ernst (v0.12.8) ──────────────
    "resp_type":            {"nl":"Type",             "fr":"Type",              "en":"Type"},
    "central_ahi_short":    {"nl":"Centr.",           "fr":"Centr.",            "en":"Centr."},
    "central_ahi_full":     {"nl":"Centrale apnoe-index (CAI, /u)",
                             "fr":"Index d'apnées centrales (IAC, /h)",
                             "en":"Central apnea index (CAI, /h)"},
    "osas":                 {"nl":"OSAS",             "fr":"SAOS",              "en":"OSAS"},
    "csas":                 {"nl":"CSAS",             "fr":"SASC",              "en":"CSAS"},
    "osas_full":            {"nl":"Obstructief slaapapneusyndroom",
                             "fr":"Syndrome d'apnées obstructives du sommeil",
                             "en":"Obstructive sleep apnea syndrome"},
    "csas_full":            {"nl":"Centraal slaapapneusyndroom (centrale events ≥ 50% van de AHI)",
                             "fr":"Syndrome d'apnées centrales du sommeil (≥ 50% des événements centraux)",
                             "en":"Central sleep apnea syndrome (central events ≥ 50% of AHI)"},
    # sev_normal/mild/moderate/severe: canonieke set staat verderop (~regel 540)
    "spo2_mean":            {"nl":"Gem. SpO2",        "fr":"SpO2 moyen",        "en":"Mean SpO2"},
    "spo2_min":             {"nl":"Min. SpO2",        "fr":"SpO2 min.",         "en":"Min. SpO2"},
    "time_below_90":        {"nl":"Tijd < 90%",       "fr":"Temps < 90%",       "en":"Time < 90%"},

    # ── DASHBOARD ───────────────────────────────────────────────────────────
    "patient_overview":     {"nl":"Patiëntenoverzicht","fr":"Aperçu des patients","en":"Patient overview"},
    "total_studies":        {"nl":"Totaal studies",   "fr":"Total études",      "en":"Total studies"},
    "analyses_ready":       {"nl":"Analyses klaar",   "fr":"Analyses terminées","en":"Analyses ready"},
    "osa_detected":         {"nl":"OSA gedetecteerd", "fr":"SAOS détecté",      "en":"OSA detected"},
    "search_placeholder":   {"nl":"Zoek op naam, ID, datum…",
                             "fr":"Rechercher par nom, ID, date…",
                             "en":"Search by name, ID, date…"},
    "all_severities":       {"nl":"Alle ernst-niveaus","fr":"Toutes sévérités", "en":"All severities"},
    "all_statuses":         {"nl":"Alle statussen",   "fr":"Tous les statuts",  "en":"All statuses"},
    "clear_filters":        {"nl":"Wissen",           "fr":"Effacer",           "en":"Clear"},
    "new_analysis":         {"nl":"Nieuwe analyse",   "fr":"Nouvelle analyse",  "en":"New analysis"},
    "status_ready":         {"nl":"Klaar",            "fr":"Terminé",           "en":"Ready"},
    "status_running":       {"nl":"Bezig",            "fr":"En cours",          "en":"Running"},
    "status_failed":        {"nl":"Mislukt",          "fr":"Échoué",            "en":"Failed"},
    "no_studies_found":     {"nl":"Nog geen analyses gevonden.",
                             "fr":"Aucune analyse trouvée.",
                             "en":"No analyses found yet."},
    "reports":              {"nl":"Rapporten",        "fr":"Rapports",          "en":"Reports"},

    # ── MANUELE SCORING (v10) ───────────────────────────────────────────────
    "score_editor_title":   {"nl":"Manuele scoring — epoch-per-epoch",
                             "fr":"Scoring manuel — époque par époque",
                             "en":"Manual scoring — epoch by epoch"},
    "score_editor_help":    {"nl":"Klik op een epoch of gebruik toetsenbord: W N1 N2 N3 R  |  Ctrl+Z = ongedaan",
                             "fr":"Cliquez sur une époque ou utilisez le clavier : W N1 N2 N3 R  |  Ctrl+Z = annuler",
                             "en":"Click an epoch or use keyboard: W N1 N2 N3 R  |  Ctrl+Z = undo"},
    "save_scoring":         {"nl":"Opslaan & rapport hergeneren",
                             "fr":"Enregistrer & régénérer le rapport",
                             "en":"Save & regenerate report"},
    "scoring_saved":        {"nl":"Scoring opgeslagen. Rapport wordt herberekend.",
                             "fr":"Scoring enregistré. Rapport en cours de recalcul.",
                             "en":"Scoring saved. Report is being recalculated."},
    "corrections_count":    {"nl":"wijzigingen t.o.v. AI",
                             "fr":"modifications vs IA",
                             "en":"changes vs AI"},
    "epoch":                {"nl":"Epoch",            "fr":"Époque",            "en":"Epoch"},
    "ai_staging":           {"nl":"AI-staging",       "fr":"Staging IA",        "en":"AI staging"},
    "manual_staging":       {"nl":"Manuele staging",  "fr":"Staging manuel",    "en":"Manual staging"},
    "reset_to_ai":          {"nl":"Terug naar AI",    "fr":"Revenir à l'IA",    "en":"Reset to AI"},

    # ── E-MAIL NOTIFICATIES (v10) ────────────────────────────────────────────
    "email_subject_done":   {"nl":"YASAFlaskified — Analyse klaar",
                             "fr":"YASAFlaskified — Analyse terminée",
                             "en":"YASAFlaskified — Analysis complete"},
    "email_body_done":      {"nl":"De analyse van {patient} is voltooid. Bekijk het rapport via {url}.",
                             "fr":"L'analyse de {patient} est terminée. Consultez le rapport via {url}.",
                             "en":"The analysis of {patient} is complete. View the report at {url}."},

    # ── FOUT & STATUS ───────────────────────────────────────────────────────
    "not_available":        {"nl":"Niet beschikbaar", "fr":"Non disponible",    "en":"Not available"},
    "error_occurred":       {"nl":"Er is een fout opgetreden.",
                             "fr":"Une erreur s'est produite.",
                             "en":"An error occurred."},
    "session_expired":      {"nl":"Sessie verlopen. Probeer opnieuw.",
                             "fr":"Session expirée. Veuillez réessayer.",
                             "en":"Session expired. Please try again."},
    "file_not_found":       {"nl":"Bestand niet gevonden.",
                             "fr":"Fichier non trouvé.",
                             "en":"File not found."},
    "too_many_requests":    {"nl":"Te veel verzoeken. Wacht even.",
                             "fr":"Trop de requêtes. Veuillez patienter.",
                             "en":"Too many requests. Please wait."},
    "username_exists":            {"nl": "Gebruikersnaam bestaat al.", "fr": "Ce nom d'utilisateur existe déjà.", "en": "Username already exists."},
    "wrong_password":             {"nl": "Huidig wachtwoord is onjuist.", "fr": "Mot de passe actuel incorrect.", "en": "Current password is incorrect."},
    "password_mismatch":          {"nl": "Nieuw wachtwoord en bevestiging komen niet overeen.", "fr": "Le nouveau mot de passe et la confirmation ne correspondent pas.", "en": "New password and confirmation do not match."},

    "list_view":                 {"nl": "Lijst-weergave", "fr": "Vue en liste", "en": "List view"},
    "all_severity":              {"nl": "Alle ernst-niveaus", "fr": "Tous les niveaux de sévérité", "en": "All severity levels"},
    "severity_normal_label":     {"nl": "Normaal (AHI < 5)", "fr": "Normal (IAH < 5)", "en": "Normal (AHI < 5)"},
    "severity_mild_label":       {"nl": "Mild (AHI 5-15)", "fr": "Léger (IAH 5-15)", "en": "Mild (AHI 5-15)"},
    "severity_moderate_label":   {"nl": "Matig (AHI 15-30)", "fr": "Modéré (IAH 15-30)", "en": "Moderate (AHI 15-30)"},
    "severity_severe_label":     {"nl": "Ernstig (AHI > 30)", "fr": "Sévère (IAH > 30)", "en": "Severe (AHI > 30)"},
    "status_done":               {"nl": "Klaar", "fr": "Terminé", "en": "Done"},
    "status_busy":               {"nl": "Bezig", "fr": "En cours", "en": "In progress"},
    "study_not_found":           {"nl": "Studie niet gevonden.", "fr": "Étude introuvable.", "en": "Study not found."},
    "study_deleted":             {"nl": "Studie en alle bijhorende bestanden verwijderd.", "fr": "Étude et tous les fichiers associés supprimés.", "en": "Study and all associated files deleted."},
    "confirm_delete_study":      {"nl": "Weet u zeker dat u deze studie wilt verwijderen? Dit kan niet ongedaan worden.", "fr": "Êtes-vous sûr de vouloir supprimer cette étude ? Cette action est irréversible.", "en": "Are you sure you want to delete this study? This cannot be undone."},
    "delete_study":              {"nl": "Verwijderen", "fr": "Supprimer", "en": "Delete"},
    "conclusion":                {"nl": "Besluit", "fr": "Conclusion", "en": "Conclusion"},
    "auto_conclusion":           {"nl": "Automatisch besluit", "fr": "Conclusion automatique", "en": "Auto conclusion"},
    "save_conclusion":           {"nl": "Besluit opslaan & PDF genereren", "fr": "Enregistrer conclusion & générer PDF", "en": "Save conclusion & generate PDF"},
    "conclusion_saved":          {"nl": "Besluit opgeslagen en PDF gegenereerd.", "fr": "Conclusion enregistrée et PDF généré.", "en": "Conclusion saved and PDF generated."},
    "standard_conclusions":      {"nl": "Standaardbesluiten", "fr": "Conclusions standard", "en": "Standard conclusions"},
    "insert_standard":           {"nl": "Invoegen", "fr": "Insérer", "en": "Insert"},
    "edf_browser":               {"nl": "EDF Browser", "fr": "Navigateur EDF", "en": "EDF Browser"},
    "event_list":                {"nl": "Eventlijst", "fr": "Liste d'événements", "en": "Event list"},
    "jump_to_event":             {"nl": "Spring naar event", "fr": "Aller à l'événement", "en": "Jump to event"},
    "zoom_in":                   {"nl": "Inzoomen", "fr": "Zoomer", "en": "Zoom in"},
    "zoom_out":                  {"nl": "Uitzoomen", "fr": "Dézoomer", "en": "Zoom out"},
    "zoom_fit":                  {"nl": "Volledige studie", "fr": "Étude complète", "en": "Full study"},
    # ── v13: missing keys fix ──
    "actions": {'nl': 'Acties', 'fr': 'Actions', 'en': 'Actions'},
    "address": {'nl': 'Adres', 'fr': 'Adresse', 'en': 'Address'},
    "all_statistics": {'nl': 'Alle statistieken', 'fr': 'Toutes les statistiques', 'en': 'All statistics'},
    "analysis_failed": {'nl': 'Analyse mislukt', 'fr': 'Analyse échouée', 'en': 'Analysis failed'},
    "analysis_history": {'nl': 'Analysegeschiedenis', 'fr': 'Historique des analyses', 'en': 'Analysis history'},
    "analysis_starting": {'nl': 'Analyse wordt gestart...', 'fr': 'Analyse en cours de démarrage...', 'en': 'Starting analysis...'},
    "appears_on_reports": {'nl': 'verschijnt op alle rapporten', 'fr': 'apparaît sur tous les rapports', 'en': 'appears on all reports'},
    "arousal_index": {'nl': 'Arousal index', 'fr': "Index d'arousal", 'en': 'Arousal index'},
    "arousal_rera": {'nl': 'Arousal & RERA', 'fr': 'Arousal & RERA', 'en': 'Arousal & RERA'},
    "artifacts_found": {'nl': 'epochs bevatten artefacten', 'fr': 'époques contiennent des artéfacts', 'en': 'epochs contain artifacts'},
    "auto_select_eeg": {'nl': 'Auto-selectie (EEG)', 'fr': 'Auto-sélection (EEG)', 'en': 'Auto-select (EEG)'},
    "average": {'nl': 'Gemiddeld', 'fr': 'Moyen', 'en': 'Average'},
    "avg_desaturation": {'nl': 'Gem. desaturatie', 'fr': 'Désaturation moyenne', 'en': 'Avg. desaturation'},
    "avg_duration": {'nl': 'Gem. duur', 'fr': 'Durée moyenne', 'en': 'Avg. duration'},
    "avg_rem_period": {'nl': 'Gem. REM periode', 'fr': 'Période REM moyenne', 'en': 'Avg. REM period'},
    "avg_spo2": {'nl': 'Gem. SpO2', 'fr': 'SpO2 moyenne', 'en': 'Avg. SpO2'},
    "band_ratios": {'nl': "Band ratio's", 'fr': 'Ratios de bande', 'en': 'Band ratios'},
    "baseline_spo2": {'nl': 'Baseline SpO2', 'fr': 'SpO2 de base', 'en': 'Baseline SpO2'},
    "central": {'nl': 'Centraal', 'fr': 'Central', 'en': 'Central'},
    "channel_select": {'nl': 'Kanaalkeuze', 'fr': 'Sélection des canaux', 'en': 'Channel selection'},
    "clear_selection": {'nl': 'Wis selectie', 'fr': 'Effacer la sélection', 'en': 'Clear selection'},
    "clinical_usability_title": {'nl': 'Klinische bruikbaarheid', 'fr': 'Utilité clinique', 'en': 'Clinical usability'},
    "confidence": {'nl': 'Betrouwbaarheid', 'fr': 'Fiabilité', 'en': 'Confidence'},
    "cycle": {'nl': 'Cyclus', 'fr': 'Cycle', 'en': 'Cycle'},
    "date": {'nl': 'Datum', 'fr': 'Date', 'en': 'Date'},
    "date_of_birth": {'nl': 'Geboortedatum', 'fr': 'Date de naissance', 'en': 'Date of birth'},
    "deep_sleep": {'nl': 'Diepe slaap', 'fr': 'Sommeil profond', 'en': 'Deep sleep'},
    "default_time_note": {'nl': 'Indien leeg, wordt een standaardtijd (22:00) gebruikt.', 'fr': 'Si vide, une heure par défaut (22:00) sera utilisée.', 'en': 'If empty, a default time (22:00) will be used.'},
    "desat_index": {'nl': 'Desaturatie index', 'fr': 'Index de désaturation', 'en': 'Desaturation index'},
    "desat_pct": {'nl': 'Desat %', 'fr': 'Désat %', 'en': 'Desat %'},
    "detection_failed": {'nl': 'detectie mislukt', 'fr': 'détection échouée', 'en': 'detection failed'},
    "dur_s": {'nl': 'Duur (s)', 'fr': 'Durée (s)', 'en': 'Duration (s)'},
    "duration": {'nl': 'Duur', 'fr': 'Durée', 'en': 'Duration'},
    "eeg_primary_desc": {'nl': 'Hoofd-EEG voor staging (bv. C4-M1, C3-M2)', 'fr': 'EEG principal pour le staging (ex. C4-M1, C3-M2)', 'en': 'Main EEG for staging (e.g. C4-M1, C3-M2)'},
    "emg_desc": {'nl': 'Spieractiviteit voor staging', 'fr': 'Activité musculaire pour le staging', 'en': 'Muscle activity for staging'},
    "eog_desc": {'nl': 'Oogbewegingen voor REM-detectie', 'fr': 'Mouvements oculaires pour la détection REM', 'en': 'Eye movements for REM detection'},
    "events_first_50": {'nl': 'Events (eerste 50 van', 'fr': 'Événements (50 premiers sur', 'en': 'Events (first 50 of'},
    "extra_eeg_desc": {'nl': 'Voor spindle-, slow-wave- en bandvermogenanalyse (meerkeuze)', 'fr': "Pour l'analyse des fuseaux, ondes lentes et puissance spectrale (choix multiple)", 'en': 'For spindle, slow-wave and band power analysis (multiple choice)'},
    "female": {'nl': 'Vrouw', 'fr': 'Femme', 'en': 'Female'},
    "fields_prefilled": {'nl': 'Velden worden vooringevuld vanuit de EDF-header indien beschikbaar.', 'fr': "Les champs sont préremplis à partir de l'en-tête EDF si disponible.", 'en': 'Fields are pre-filled from EDF header if available.'},
    "first_n": {'nl': 'eerste', 'fr': 'premiers', 'en': 'first'},
    "firstname": {'nl': 'Voornaam', 'fr': 'Prénom', 'en': 'First name'},
    "from_edf": {'nl': 'uit EDF', 'fr': 'depuis EDF', 'en': 'from EDF'},
    "from_stage": {'nl': 'Van fase', 'fr': 'De stade', 'en': 'From stage'},
    "height_cm": {'nl': 'Lengte (cm)', 'fr': 'Taille (cm)', 'en': 'Height (cm)'},
    "hypnogram_timeline": {'nl': 'Hypnogram tijdlijn', 'fr': 'Chronologie hypnogramme', 'en': 'Hypnogram timeline'},
    "hypopnea": {'nl': 'Hypopnea', 'fr': 'Hypopnée', 'en': 'Hypopnea'},
    "lms_sleep": {'nl': 'LMs tijdens slaap', 'fr': 'MJ pendant le sommeil', 'en': 'LMs during sleep'},
    "lms_wake": {'nl': 'LMs tijdens wake', 'fr': "MJ pendant l'éveil", 'en': 'LMs during wake'},
    "longest_rem_period": {'nl': 'Langste REM periode', 'fr': 'Plus longue période REM', 'en': 'Longest REM period'},
    "male": {'nl': 'Man', 'fr': 'Homme', 'en': 'Male'},
    "maximum": {'nl': 'Maximum', 'fr': 'Maximum', 'en': 'Maximum'},
    "min_spo2": {'nl': 'Min SpO2', 'fr': 'SpO2 minimum', 'en': 'Min SpO2'},
    "minimum": {'nl': 'Minimum', 'fr': 'Minimum', 'en': 'Minimum'},
    "mixed": {'nl': 'Gemengd', 'fr': 'Mixte', 'en': 'Mixed'},
    "name": {'nl': 'Naam', 'fr': 'Nom', 'en': 'Name'},
    "no_analyses_yet": {'nl': 'Nog geen analyses', 'fr': 'Aucune analyse', 'en': 'No analyses yet'},
    "no_data": {'nl': 'Geen data', 'fr': 'Pas de données', 'en': 'No data'},
    "nrem_rem_transitions": {'nl': 'NREM → REM Transities', 'fr': 'Transitions NREM → REM', 'en': 'NREM → REM Transitions'},
    "obstructive": {'nl': 'Obstructief', 'fr': 'Obstructif', 'en': 'Obstructive'},
    "optional": {'nl': 'optioneel', 'fr': 'facultatif', 'en': 'optional'},
    "other_file": {'nl': 'Ander bestand uploaden', 'fr': 'Télécharger un autre fichier', 'en': 'Upload another file'},
    # Scoring profile
    "scoring_profile_title": {'nl': 'Scoring profiel', 'fr': 'Profil de scoring', 'en': 'Scoring Profile'},
    "study_type_title":      {"nl": "Studietype", "fr": "Type d'étude", "en": "Study type"},
    "study_diagnostic_psg":  {"nl": "Diagnostische PSG", "fr": "PSG diagnostique", "en": "Diagnostic PSG"},
    "study_diagnostic_pg":   {"nl": "Diagnostische polygrafie", "fr": "Polygraphie diagnostique", "en": "Diagnostic polygraphy", "de": "Diagnostische Polygraphie"},
    "eeg_none_hint":         {"nl": "Kies dit bij een montage zonder EEG — de analyse rekent dan met registratietijd (REI).",
                              "fr": "À choisir pour un montage sans EEG — l'analyse utilise alors le temps d'enregistrement (IER).",
                              "en": "Choose this for a montage without EEG — the analysis then uses recording time (REI).",
                              "de": "Bei einer Montage ohne EEG wählen — die Analyse rechnet dann mit der Aufzeichnungszeit (REI)."},
    "eeg_disabled_polygraphy": {"nl": "Niet van toepassing bij polygrafie: er is geen EEG, dus geen slaapstaging.",
                              "fr": "Sans objet en polygraphie : pas d'EEG, donc pas de staging du sommeil.",
                              "en": "Not applicable to polygraphy: there is no EEG, so no sleep staging.",
                              "de": "Bei Polygraphie nicht zutreffend: kein EEG, also keine Schlafstadien."},
    "study_titration_psg_cpap": {"nl": "Titratie PSG — CPAP", "fr": "PSG de titration — PPC", "en": "Titration PSG — CPAP"},
    "study_titration_pg_cpap":  {"nl": "Titratie polygrafie — CPAP", "fr": "Polygraphie de titration — PPC", "en": "Titration polygraphy — CPAP"},
    "study_titration_pg_mra":   {"nl": "Titratie polygrafie — MRA", "fr": "Polygraphie de titration — OAM", "en": "Titration polygraphy — MAD"},
    "study_type_hint":       {"nl": "Polygrafie: geen slaapstaging (REI i.p.v. AHI). Titratie: residuele events onder therapie.",
                              "fr": "Polygraphie : pas de staging (IER au lieu d'IAH). Titration : événements résiduels sous traitement.",
                              "en": "Polygraphy: no sleep staging (REI instead of AHI). Titration: residual events under therapy."},
    "pdf_titration_cpap":    {"nl": "Titratierapport — CPAP", "fr": "Rapport de titration — PPC", "en": "Titration report — CPAP"},
    "pdf_titration_mra":     {"nl": "Titratierapport — MRA", "fr": "Rapport de titration — OAM", "en": "Titration report — MAD"},
    "pdf_residual":          {"nl": "Residueel", "fr": "Résiduel", "en": "Residual"},
    "pdf_rei":               {"nl": "REI (Respiratory Event Index)", "fr": "IER (Index d'Événements Respiratoires)", "en": "REI (Respiratory Event Index)"},
    "pdf_therapy":           {"nl": "Therapie", "fr": "Thérapie", "en": "Therapy"},
    "pdf_no_staging":        {"nl": "Geen slaapstaging (polygrafie — geen EEG)", "fr": "Pas de staging du sommeil (polygraphie — pas d'EEG)", "en": "No sleep staging (polygraphy — no EEG)"},
    "profile_strict":   {'nl': 'Strikt (machine) — AASM exact, geen smoothing', 'fr': 'Strict (machine) — AASM exact, sans lissage', 'en': 'Strict (machine) — AASM exact, no smoothing'},
    "profile_standard": {'nl': 'Standaard (AASM) — aanbevolen', 'fr': 'Standard (AASM) — recommandé', 'en': 'Standard (AASM) — recommended'},
    "profile_sensitive": {'nl': 'Sensitief (RPSGT) — dichter bij menselijke scoring', 'fr': 'Sensible (RPSGT) — plus proche du scoring humain', 'en': 'Sensitive (RPSGT) — closer to human scoring'},
    "scoring_profile_hint": {'nl': 'Bepaalt drempels voor hypopnea-detectie, SpO2-koppeling en signaal-smoothing.', 'fr': 'Détermine les seuils de détection des hypopnées, le couplage SpO2 et le lissage du signal.', 'en': 'Controls thresholds for hypopnea detection, SpO2 coupling, and signal smoothing.'},
    "arousal_lgbm_label": {'nl': 'ML arousal re-classifier gebruiken (preview)', 'fr': 'Utiliser le re-classificateur ML d’arousals (aperçu)', 'en': 'Use ML arousal re-classifier (preview)', 'de': 'ML-Arousal-Re-Klassifikator verwenden (Vorschau)'},
    "kbd_shortcuts_title": {'nl': 'Toetsenbord-shortcuts', 'fr': 'Raccourcis clavier', 'en': 'Keyboard shortcuts', 'de': 'Tastenkürzel'},
    "kbd_new_analysis":    {'nl': 'Nieuwe analyse',           'fr': 'Nouvelle analyse',         'en': 'New analysis',             'de': 'Neue Analyse'},
    "kbd_dashboard":       {'nl': 'Naar dashboard',           'fr': 'Aller au tableau de bord', 'en': 'Go to dashboard',          'de': 'Zum Dashboard'},
    "kbd_history":         {'nl': 'Naar historiek',           'fr': 'Aller à l’historique',     'en': 'Go to history',            'de': 'Zum Verlauf'},
    "kbd_search":          {'nl': 'Zoekveld activeren',       'fr': 'Activer la recherche',     'en': 'Focus search',             'de': 'Suche fokussieren'},
    "kbd_row_nav":         {'nl': 'Volgende / vorige rij',    'fr': 'Ligne suivante/précéd.',   'en': 'Next / previous row',      'de': 'Nächste / vorh. Zeile'},
    "kbd_open_row":        {'nl': 'Selectie openen',          'fr': 'Ouvrir la sélection',      'en': 'Open selected',            'de': 'Auswahl öffnen'},
    "kbd_presentation":    {'nl': 'Presentatiemodus aan/uit', 'fr': 'Mode présentation',        'en': 'Toggle presentation mode', 'de': 'Präsentationsmodus'},
    "kbd_help":            {'nl': 'Toon deze help',           'fr': 'Afficher cette aide',      'en': 'Show this help',           'de': 'Diese Hilfe zeigen'},
    "kbd_close":           {'nl': 'Sluiten',                  'fr': 'Fermer',                   'en': 'Close',                    'de': 'Schließen'},
    "kbd_hint":            {'nl': 'Shortcuts negeren invoervelden. Druk ? op een lijstpagina.', 'fr': 'Les raccourcis ignorent les champs de saisie. Appuyez sur ? sur une page liste.', 'en': 'Shortcuts ignore input fields. Press ? from any list page.', 'de': 'Kürzel ignorieren Eingabefelder. Drücken Sie ? auf einer Listenseite.'},
    "autodetected_channels": {'nl': 'Auto-gedetecteerde kanalen', 'fr': 'Canaux auto-détectés', 'en': 'Auto-detected channels', 'de': 'Automatisch erkannte Kanäle'},
    "override_selection":   {'nl': 'Handmatig overrulen', 'fr': 'Forcer manuellement', 'en': 'Override manually', 'de': 'Manuell überschreiben'},
    "channel_eeg_primary": {'nl': 'EEG primair', 'fr': 'EEG primaire', 'en': 'EEG primary', 'de': 'EEG primär'},
    "channel_eog":          {'nl': 'EOG',  'fr': 'EOG',  'en': 'EOG',  'de': 'EOG'},
    "channel_emg_chin":     {'nl': 'EMG kin',     'fr': 'EMG menton',  'en': 'EMG chin',     'de': 'EMG Kinn'},
    "channel_flow":         {'nl': 'Luchtstroom', 'fr': 'Débit aérien','en': 'Airflow',      'de': 'Atemstrom'},
    # De twee AASM-sensoren apart, zodat de gebruiker in een oogopslag ziet
    # of ze allebei gevonden zijn — apneu hoort op de thermistor.
    "channel_flow_therm":   {'nl': 'Thermistor (apneu)', 'fr': 'Thermistance (apnée)', 'en': 'Thermistor (apnea)', 'de': 'Thermistor (Apnoe)'},
    "channel_flow_press":   {'nl': 'Nasale druk (hypopneu)', 'fr': 'Pression nasale (hypopnée)', 'en': 'Nasal pressure (hypopnea)', 'de': 'Nasendruck (Hypopnoe)'},
    "channel_thoracic":     {'nl': 'Thoracale RIP','fr':'RIP thoracique','en':'Thoracic RIP','de':'Thorakal RIP'},
    "channel_abdominal":    {'nl': 'Abdominale RIP','fr':'RIP abdominal','en':'Abdominal RIP','de':'Abdominal RIP'},
    "channel_spo2":         {'nl': 'SpO₂',         'fr': 'SpO₂',        'en': 'SpO₂',         'de': 'SpO₂'},
    "channel_not_detected": {'nl': 'Niet gevonden','fr': 'Non détecté', 'en': 'Not detected', 'de': 'Nicht erkannt'},
    "total_studies": {'nl': 'Totaal studies', 'fr': 'Total études', 'en': 'Total studies', 'de': 'Studien gesamt'},
    "osa_detected":  {'nl': 'OSA gedetecteerd', 'fr': 'SAOS détecté', 'en': 'OSA detected', 'de': 'OSA erkannt'},
    "arousal_lgbm_hint": {'nl': 'Hybride: rule-based kandidaten + LightGBM filter (drempel 0,60). Getraind op MESA q∈{5,6}, gevalideerd op q=7 holdout en cross-cohort op PSG-IPA. Niet aan voor klinische scoring; alleen voor onderzoeks-runs of vergelijkende validatie.', 'fr': 'Hybride : candidats règle-base + filtre LightGBM (seuil 0,60). Entraîné sur MESA q∈{5,6}, validé sur q=7 holdout et cross-cohorte sur PSG-IPA. Pas pour le scoring clinique ; uniquement pour les analyses de recherche.', 'en': 'Hybrid: rule-based candidates + LightGBM filter (threshold 0.60). Trained on MESA q∈{5,6}, validated on q=7 holdout and cross-cohort on PSG-IPA. Not for clinical scoring; research and comparative validation only.', 'de': 'Hybrid: regelbasierte Kandidaten + LightGBM-Filter (Schwellenwert 0,60). Trainiert auf MESA q∈{5,6}, validiert am q=7-Holdout und über Kohorten hinweg auf PSG-IPA. Nicht für klinisches Scoring; nur für Forschungs- und Vergleichsläufe.'},
    "parameter": {'nl': 'Parameter', 'fr': 'Paramètre', 'en': 'Parameter'},
    "password_requirements": {'nl': 'Min. 8 tekens, 1 hoofdletter, 1 kleine letter, 1 cijfer.', 'fr': 'Min. 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre.', 'en': 'Min. 8 chars, 1 uppercase, 1 lowercase, 1 digit.'},
    "patient": {'nl': 'Patiënt', 'fr': 'Patient', 'en': 'Patient'},
    "patient_number": {'nl': 'Patiëntnummer', 'fr': 'Numéro de patient', 'en': 'Patient number'},
    "per_channel_summary": {'nl': 'Per kanaal samenvatting', 'fr': 'Résumé par canal', 'en': 'Per channel summary'},
    "per_event_table": {'nl': 'Per-event tabel', 'fr': 'Tableau par événement', 'en': 'Per-event table'},
    "plm_criteria": {'nl': 'LM ≥8μV, 0.5-10s duur | PLM-serie ≥4 LMs, 5-90s interval | Resp-geassocieerde LMs uitgesloten | Alleen slaap-epochs | PLMI ≥15/u = klinisch significant', 'fr': 'MJ ≥8μV, durée 0.5-10s | Série MPJ ≥4 MJ, intervalle 5-90s | MJ associés exclus | Époques de sommeil uniquement | IMPJ ≥15/h = cliniquement significatif', 'en': 'LM ≥8μV, 0.5-10s duration | PLM series ≥4 LMs, 5-90s interval | Resp-associated LMs excluded | Sleep epochs only | PLMI ≥15/h = clinically significant'},
    "plm_details": {'nl': 'PLM Details (AASM)', 'fr': 'Détails MPJ (AASM)', 'en': 'PLM Details (AASM)'},
    "plm_in_series": {'nl': 'PLMs (in series)', 'fr': 'MPJ (en séries)', 'en': 'PLMs (in series)'},
    "recording_time": {'nl': 'Opnametijdstip', 'fr': "Heure d'enregistrement", 'en': 'Recording time'},
    "relative_power_per_stage": {'nl': 'Relatief vermogen per slaapfase', 'fr': 'Puissance relative par stade de sommeil', 'en': 'Relative power per sleep stage'},
    "rem_periods": {'nl': 'REM perioden', 'fr': 'Périodes REM', 'en': 'REM periods'},
    "resp_associated": {'nl': 'Resp-geassocieerd (uitgesloten)', 'fr': 'Associés à la respiration (exclus)', 'en': 'Resp-associated (excluded)'},
    "respiratory_arousals": {'nl': 'Respiratoire arousals', 'fr': 'Arousals respiratoires', 'en': 'Respiratory arousals'},
    "respiratory_summary": {'nl': 'Respiratoire samenvatting', 'fr': 'Résumé respiratoire', 'en': 'Respiratory summary'},
    "rule1b_reinstated": {'nl': 'Rule 1B heractivaties (arousal)', 'fr': 'Réactivations Rule 1B (arousal)', 'en': 'Rule 1B reinstatements (arousal)'},
    "select_all": {'nl': 'Alles selecteren', 'fr': 'Tout sélectionner', 'en': 'Select all'},
    "sleep_cycles_detected": {'nl': 'slaapcycli gedetecteerd', 'fr': 'cycles de sommeil détectés', 'en': 'sleep cycles detected'},
    "slow_waves_detected": {'nl': 'trage golven gedetecteerd', 'fr': 'ondes lentes détectées', 'en': 'slow waves detected'},
    "spindles_detected": {'nl': 'spindels gedetecteerd', 'fr': 'fuseaux détectés', 'en': 'spindles detected'},
    "spo2_details": {'nl': 'SpO2 details', 'fr': 'Détails SpO2', 'en': 'SpO2 details'},
    "spontaneous_arousals": {'nl': 'Spontane arousals', 'fr': 'Arousals spontanés', 'en': 'Spontaneous arousals'},
    "stage": {'nl': 'Fase', 'fr': 'Stade', 'en': 'Stage'},
    "start_first_analysis": {'nl': 'Start eerste analyse', 'fr': 'Démarrer la première analyse', 'en': 'Start first analysis'},
    "start_s": {'nl': 'Start (s)', 'fr': 'Début (s)', 'en': 'Start (s)'},
    "studies_found": {'nl': 'studies gevonden', 'fr': 'études trouvées', 'en': 'studies found'},
    "tab_heart": {'nl': 'Hart', 'fr': 'Cœur', 'en': 'Heart'},
    "time_min": {'nl': 'Tijdstip (min)', 'fr': 'Moment (min)', 'en': 'Time (min)'},
    "total_events": {'nl': 'Totaal events', 'fr': 'Total événements', 'en': 'Total events'},
    "total_lms": {'nl': 'Totaal LMs', 'fr': 'Total MJ', 'en': 'Total LMs'},
    "total_rem_duration": {'nl': 'Totale REM duur', 'fr': 'Durée REM totale', 'en': 'Total REM duration'},
    "unknown_error": {'nl': 'Onbekende fout.', 'fr': 'Erreur inconnue.', 'en': 'Unknown error.'},
    "upload_to_start": {'nl': 'Upload een EDF-bestand om te beginnen.', 'fr': 'Téléchargez un fichier EDF pour commencer.', 'en': 'Upload an EDF file to get started.'},
    "value": {'nl': 'Waarde', 'fr': 'Valeur', 'en': 'Value'},
    "weight_kg": {'nl': 'Gewicht (kg)', 'fr': 'Poids (kg)', 'en': 'Weight (kg)'},

    "admin_cannot_delete":       {"nl": "Admin-gebruiker kan niet worden verwijderd.", "fr": "L'utilisateur admin ne peut pas être supprimé.", "en": "Admin user cannot be deleted."},
    "admin_role_fixed":          {"nl": "Rol van admin kan niet worden gewijzigd.", "fr": "Le rôle de l'admin ne peut pas être modifié.", "en": "Admin role cannot be changed."},
    "invalid_role":              {"nl": "Ongeldige rol.", "fr": "Rôle invalide.", "en": "Invalid role."},
    "user_updated":              {"nl": "Gebruiker bijgewerkt.", "fr": "Utilisateur mis à jour.", "en": "User updated."},
    "site_name_required":        {"nl": "Sitenaam is verplicht.", "fr": "Le nom du site est requis.", "en": "Site name is required."},
    "site_created":              {"nl": "Site aangemaakt.", "fr": "Site créé.", "en": "Site created."},
    "site_has_users":            {"nl": "Site heeft nog gebruikers.", "fr": "Le site a encore des utilisateurs.", "en": "Site still has users."},
    "invalid_file":              {"nl": "Ongeldig bestandspad.", "fr": "Chemin de fichier invalide.", "en": "Invalid file path."},
    "processing_started":        {"nl": "Analyse gestart!", "fr": "Analyse démarrée !", "en": "Processing started!"},
    "invalid_channels":          {"nl": "Ongeldige kanaalselectie. Probeer opnieuw.", "fr": "Sélection de canaux invalide. Réessayez.", "en": "Invalid channel selection. Please try again."},
    "processing_failed":         {"nl": "Analyse starten mislukt. Probeer opnieuw.", "fr": "Échec du lancement de l'analyse. Réessayez.", "en": "Failed to start processing. Please try again."},
    "file_not_available":        {"nl": "Bestand niet meer beschikbaar op server.", "fr": "Fichier plus disponible sur le serveur.", "en": "File no longer available on server."},
    "job_eeg_required":          {"nl": "Job ID en EEG-kanaal zijn verplicht.", "fr": "Job ID et canal EEG sont requis.", "en": "Job ID and EEG channel are required."},
    "internal_error":            {"nl": "Er is een interne fout opgetreden.", "fr": "Une erreur interne s'est produite.", "en": "An internal error occurred."},
    "edf_read_error":            {"nl": "Fout bij lezen EDF-bestand", "fr": "Erreur de lecture du fichier EDF", "en": "Error reading EDF file"},
    "delete_not_allowed":        {"nl": "U heeft geen toestemming om deze studie te verwijderen.", "fr": "Vous n'avez pas l'autorisation de supprimer cette étude.", "en": "You do not have permission to delete this study."},
    "edfplus_generating":        {"nl": "EDF+ wordt op de achtergrond gegenereerd. Dit duurt enkele minuten. Probeer straks opnieuw te downloaden.", "fr": "EDF+ est en cours de génération en arrière-plan. Cela prend quelques minutes. Réessayez le téléchargement plus tard.", "en": "EDF+ is being generated in the background. This takes a few minutes. Try downloading again shortly."},
    "edfplus_failed":            {"nl": "EDF+ generatie mislukt", "fr": "Échec de la génération EDF+", "en": "EDF+ generation failed"},
    "worker_unavailable":        {"nl": "Kon analyse niet starten. Controleer de worker-service.", "fr": "Impossible de démarrer l'analyse. Vérifiez le service worker.", "en": "Could not start analysis. Check the worker service."},
    "rate_limited":              {"nl": "Te veel verzoeken. Wacht even en probeer opnieuw.", "fr": "Trop de requêtes. Veuillez patienter et réessayer.", "en": "Too many requests. Please wait and try again."},
    "edf_not_found":             {"nl": "Origineel EDF-bestand niet gevonden. Her-analyse niet mogelijk.", "fr": "Fichier EDF original introuvable. Réanalyse impossible.", "en": "Original EDF file not found. Re-analysis not possible."},
    "reanalyze_started":         {"nl": "Her-analyse gestart. Kies kanalen en patiëntgegevens.", "fr": "Réanalyse démarrée. Choisissez les canaux et les données patient.", "en": "Re-analysis started. Select channels and patient data."},
    "reanalyze":                 {"nl": "Her-analyseren", "fr": "Réanalyser", "en": "Re-analyze"},
    "edit_report":               {"nl": "Rapport bewerken", "fr": "Modifier le rapport", "en": "Edit report"},
    "back_to_results":           {"nl": "Terug naar resultaten", "fr": "Retour aux résultats", "en": "Back to results"},
    "patient_info":              {"nl": "Patiëntgegevens", "fr": "Données patient", "en": "Patient information"},
    "standard_diagnosis":        {"nl": "Standaarddiagnose", "fr": "Diagnostic standard", "en": "Standard diagnosis"},
    "select_diagnosis":          {"nl": "Selecteer een diagnose om toe te voegen", "fr": "Sélectionnez un diagnostic à ajouter", "en": "Select a diagnosis to add"},
    "diagnosis_text":            {"nl": "Diagnosetekst", "fr": "Texte du diagnostic", "en": "Diagnosis text"},
    "diagnosis_placeholder":     {"nl": "Typ of selecteer een diagnose...", "fr": "Tapez ou sélectionnez un diagnostic...", "en": "Type or select a diagnosis..."},
    "diagnosis_help":            {"nl": "Selecteer standaarddiagnoses uit de dropdown of typ een vrije tekst. Meerdere diagnoses kunnen gecombineerd worden.", "fr": "Sélectionnez des diagnostics standards dans le menu déroulant ou tapez un texte libre.", "en": "Select standard diagnoses from the dropdown or type free text. Multiple diagnoses can be combined."},
    "comments_placeholder":      {"nl": "Optionele opmerkingen voor het rapport...", "fr": "Remarques optionnelles pour le rapport...", "en": "Optional comments for the report..."},
    "save_and_regenerate":       {"nl": "Opslaan & PDF vernieuwen", "fr": "Enregistrer & renouveler PDF", "en": "Save & regenerate PDF"},
    "reset_to_auto":             {"nl": "Reset naar automatisch", "fr": "Réinitialiser automatique", "en": "Reset to automatic"},
    "view_pdf":                  {"nl": "Bekijk PDF", "fr": "Voir PDF", "en": "View PDF"},
    "report_saved":              {"nl": "Rapport opgeslagen", "fr": "Rapport enregistré", "en": "Report saved"},
    "weight":                    {"nl": "Gewicht", "fr": "Poids", "en": "Weight"},
    "height":                    {"nl": "Lengte", "fr": "Taille", "en": "Height"},
    "pneumo_channels":           {"nl": "Respiratoire & PLM kanalen", "fr": "Canaux respiratoires & PLM", "en": "Respiratory & PLM channels"},
    "pneumo_channels_desc":      {"nl": "Auto-gedetecteerd (★). Corrigeer indien nodig.", "fr": "Auto-détecté (★). Corrigez si nécessaire.", "en": "Auto-detected (★). Correct if needed."},
    "auto_detect":               {"nl": "Automatisch detecteren", "fr": "Détection automatique", "en": "Auto-detect"},

    # ── KLINISCHE CONCLUSIES (v0.8.11: gecentraliseerd) ─────────────────────
    # Severity labels
    "sev_normal":       {"nl": "Normaal",       "fr": "Normal",      "en": "Normal"},
    "sev_mild":         {"nl": "Mild",          "fr": "Léger",       "en": "Mild"},
    "sev_moderate":     {"nl": "Matig",         "fr": "Modéré",      "en": "Moderate"},
    "sev_severe":       {"nl": "Ernstig",       "fr": "Sévère",      "en": "Severe"},

    # Conclusion headings
    "concl_diagnosis":  {"nl": "Diagnose",      "fr": "Diagnostic",  "en": "Diagnosis"},
    "concl_conclusion": {"nl": "Besluit",       "fr": "Conclusion",  "en": "Conclusion"},
    "concl_treatment":  {"nl": "Behandelingssuggesties", "fr": "Suggestions de traitement", "en": "Treatment suggestions"},
    "concl_suggestion": {"nl": "Suggestie",     "fr": "Suggestion",  "en": "Suggestion"},

    # Normal
    "concl_normal_title":   {"nl": "Besluit: Normaal polysomnogram.",
                             "fr": "Conclusion : Polysomnogramme normal.",
                             "en": "Conclusion: Normal polysomnogram."},
    "concl_normal_body":    {"nl": "Geen aanwijzingen voor obstructief slaapapneusyndroom (OSAS). Normale slaaparchitectuur. Geen klinisch significante periodieke beenbewegingen.",
                             "fr": "Pas de signe de syndrome d'apnée obstructive du sommeil (SAOS). Architecture du sommeil normale. Pas de mouvements périodiques des jambes cliniquement significatifs.",
                             "en": "No evidence of obstructive sleep apnea syndrome (OSAS). Normal sleep architecture. No clinically significant periodic limb movements."},

    # Mild OSAS
    "concl_mild_title":     {"nl": "Besluit: Mild obstructief slaapapneusyndroom (mild OSAS).",
                             "fr": "Conclusion : Syndrome d'apnée obstructive du sommeil léger (SAOS léger).",
                             "en": "Conclusion: Mild obstructive sleep apnea syndrome (mild OSAS)."},
    "concl_mild_body":      {"nl": "Mild OSAS met beperkte slaapfragmentatie.",
                             "fr": "SAOS léger avec fragmentation limitée du sommeil.",
                             "en": "Mild OSAS with limited sleep fragmentation."},
    "concl_mild_tx":        {"nl": "Positietherapie (vermijden rugligging). Mandibulair repositieapparaat (MRA) overwegen. Slaaphygiëne optimaliseren.",
                             "fr": "Thérapie positionnelle (éviter le décubitus dorsal). Envisager un appareil de repositionnement mandibulaire (ARM). Optimiser l'hygiène du sommeil.",
                             "en": "Positional therapy (avoid supine position). Consider mandibular advancement device (MAD). Optimize sleep hygiene."},

    # Moderate OSAS
    "concl_mod_title":      {"nl": "Besluit: Matig obstructief slaapapneusyndroom (matig OSAS).",
                             "fr": "Conclusion : Syndrome d'apnée obstructive du sommeil modéré (SAOS modéré).",
                             "en": "Conclusion: Moderate obstructive sleep apnea syndrome (moderate OSAS)."},
    "concl_mod_body":       {"nl": "Matig OSAS met slaapfragmentatie.",
                             "fr": "SAOS modéré avec fragmentation du sommeil.",
                             "en": "Moderate OSAS with sleep fragmentation."},
    "concl_mod_tx":         {"nl": "CPAP-therapie aanbevolen (eerste keuze). Alternatief: mandibulair repositieapparaat (MRA) bij CPAP-intolerantie. Positietherapie als adjuvante behandeling.",
                             "fr": "Thérapie CPAP recommandée (premier choix). Alternative : appareil de repositionnement mandibulaire (ARM) en cas d'intolérance au CPAP. Thérapie positionnelle en traitement adjuvant.",
                             "en": "CPAP therapy recommended (first-line). Alternative: mandibular advancement device (MAD) if CPAP-intolerant. Positional therapy as adjunct."},

    # Severe OSAS
    "concl_sev_title":      {"nl": "Besluit: Ernstig obstructief slaapapneusyndroom (ernstig OSAS).",
                             "fr": "Conclusion : Syndrome d'apnée obstructive du sommeil sévère (SAOS sévère).",
                             "en": "Conclusion: Severe obstructive sleep apnea syndrome (severe OSAS)."},
    "concl_sev_body":       {"nl": "Ernstig OSAS met significante slaapfragmentatie.",
                             "fr": "SAOS sévère avec fragmentation significative du sommeil.",
                             "en": "Severe OSAS with significant sleep fragmentation."},
    "concl_sev_tx":         {"nl": "CPAP-therapie strikt aanbevolen (eerste keuze, dringend). Bij ernstige desaturaties: evaluatie voor zuurstoftherapie overwegen. KNO-evaluatie voor chirurgische opties bij anatomische obstructie.",
                             "fr": "Thérapie CPAP strictement recommandée (premier choix, urgent). En cas de désaturations sévères : envisager une évaluation pour oxygénothérapie. Évaluation ORL pour options chirurgicales en cas d'obstruction anatomique.",
                             "en": "CPAP therapy strictly recommended (first-line, urgent). For severe desaturations: consider evaluation for oxygen therapy. ENT evaluation for surgical options in anatomical obstruction."},
    "concl_sev_desat":      {"nl": "Significante nocturne desaturaties.",
                             "fr": "Désaturations nocturnes significatives.",
                             "en": "Significant nocturnal desaturations."},

    # Weight
    "concl_weight":         {"nl": "Gewichtsreductie sterk aanbevolen.",
                             "fr": "Perte de poids fortement recommandée.",
                             "en": "Weight reduction strongly recommended."},
    "concl_weight_essential":{"nl": "Gewichtsreductie essentieel.",
                             "fr": "Perte de poids essentielle.",
                             "en": "Weight reduction essential."},

    # PLM
    "concl_plm_title":      {"nl": "Periodieke beenbewegingen tijdens slaap (PLMS).",
                             "fr": "Mouvements périodiques des jambes pendant le sommeil (MPJS).",
                             "en": "Periodic limb movements during sleep (PLMS)."},
    "concl_plm_body":       {"nl": "Klinisch significante periodieke beenbewegingen.",
                             "fr": "Mouvements périodiques des jambes cliniquement significatifs.",
                             "en": "Clinically significant periodic limb movements."},
    "concl_plm_tx":         {"nl": "IJzerstatus (ferritine) controleren. Bij ferritine < 75 µg/L: ijzersuppletie. Bij persisterende klachten: dopamine-agonist overwegen.",
                             "fr": "Contrôler le statut en fer (ferritine). Si ferritine < 75 µg/L : supplémentation en fer. En cas de plaintes persistantes : envisager un agoniste dopaminergique.",
                             "en": "Check iron status (ferritin). If ferritin < 75 µg/L: iron supplementation. For persistent symptoms: consider dopamine agonist."},

    # Insomnia
    "concl_insomnia_title":  {"nl": "Aanwijzingen voor insomnie.",
                             "fr": "Indices d'insomnie.",
                             "en": "Signs of insomnia."},
    "concl_insomnia_se":    {"nl": "slaapefficiëntie {se:.1f}% (normaal ≥85%)",
                             "fr": "efficacité du sommeil {se:.1f}% (normal ≥85%)",
                             "en": "sleep efficiency {se:.1f}% (normal ≥85%)"},
    "concl_insomnia_tst":   {"nl": "TST {tst:.0f} min (verkort)",
                             "fr": "TST {tst:.0f} min (réduit)",
                             "en": "TST {tst:.0f} min (reduced)"},
    "concl_insomnia_quality":{"nl": "Verminderde slaapkwaliteit",
                             "fr": "Qualité de sommeil réduite",
                             "en": "Reduced sleep quality"},
    "concl_insomnia_tx":    {"nl": "Cognitieve gedragstherapie voor insomnie (CGT-i) is eerste keuze. Evaluatie slaaphygiëne. Medicamenteuze behandeling enkel op korte termijn.",
                             "fr": "La thérapie cognitivo-comportementale pour l'insomnie (TCC-i) est le premier choix. Évaluation de l'hygiène du sommeil. Traitement médicamenteux uniquement à court terme.",
                             "en": "Cognitive behavioral therapy for insomnia (CBT-I) is first-line. Sleep hygiene evaluation. Pharmacotherapy only short-term."},

    # Cheyne-Stokes
    "concl_csr_title":      {"nl": "Cheyne-Stokes respiratie (CSR) gedetecteerd.",
                             "fr": "Respiration de Cheyne-Stokes (RCS) détectée.",
                             "en": "Cheyne-Stokes respiration (CSR) detected."},
    "concl_csr_body":       {"nl": "Cyclische crescendo-decrescendo ademhaling.",
                             "fr": "Respiration cyclique crescendo-decrescendo.",
                             "en": "Cyclic crescendo-decrescendo breathing pattern."},
    "concl_csr_tx":         {"nl": "Verwijzing cardiologie aanbevolen. Echocardiografie ter evaluatie van linkerventrikel-functie. Overweeg adaptieve servo-ventilatie (ASV).",
                             "fr": "Orientation cardiologie recommandée. Échocardiographie pour évaluation de la fonction ventriculaire gauche. Envisager la ventilation auto-asservie (ASV).",
                             "en": "Cardiology referral recommended. Echocardiography to evaluate left ventricular function. Consider adaptive servo-ventilation (ASV)."},

    # Report section headers
    "rpt_sleep_architecture": {"nl": "Slaaparchitectuur",     "fr": "Architecture du sommeil",  "en": "Sleep architecture"},
    "rpt_respiratory":        {"nl": "Respiratoire analyse",  "fr": "Analyse respiratoire",     "en": "Respiratory analysis"},
    "rpt_arousals":           {"nl": "Arousals",              "fr": "Arousals",                 "en": "Arousals"},
    "rpt_plm":                {"nl": "Periodieke beenbewegingen", "fr": "Mouvements périodiques des jambes", "en": "Periodic limb movements"},
    "rpt_spo2":               {"nl": "Zuurstofsaturatie",     "fr": "Saturation en oxygène",    "en": "Oxygen saturation"},
    "rpt_quality":            {"nl": "Signaalkwaliteit",      "fr": "Qualité du signal",        "en": "Signal quality"},
    "rpt_disclaimer":         {"nl": "Dit rapport is gegenereerd door YASAFlaskified (screening tool). Niet voor klinische diagnosestelling zonder verificatie door een slaapspecialist.",
                               "fr": "Ce rapport est généré par YASAFlaskified (outil de dépistage). Non destiné au diagnostic clinique sans vérification par un spécialiste du sommeil.",
                               "en": "This report is generated by YASAFlaskified (screening tool). Not for clinical diagnosis without verification by a sleep specialist."},
    "rpt_verified":           {"nl": "Geverifieerd door {role} {name}.",
                               "fr": "Vérifié par {role} {name}.",
                               "en": "Verified by {role} {name}."},

    # ── ADMIN UI (v0.8.11) ──────────────────────────────────────────────────
    "users":                {"nl": "Gebruikers",        "fr": "Utilisateurs",    "en": "Users"},
    "sites":                {"nl": "Sites",              "fr": "Sites",           "en": "Sites"},
    "actions":              {"nl": "Acties",             "fr": "Actions",         "en": "Actions"},
    "save":                 {"nl": "Opslaan",            "fr": "Enregistrer",     "en": "Save"},
    "cancel":               {"nl": "Annuleren",          "fr": "Annuler",         "en": "Cancel"},
    "delete":               {"nl": "Verwijderen",        "fr": "Supprimer",       "en": "Delete"},
    "edit":                 {"nl": "Bewerken",           "fr": "Modifier",        "en": "Edit"},
    "reset":                {"nl": "Reset",              "fr": "Réinitialiser",   "en": "Reset"},
    "create":               {"nl": "Aanmaken",           "fr": "Créer",           "en": "Create"},
    "you":                  {"nl": "jij",                "fr": "vous",            "en": "you"},
    "all_sites":            {"nl": "alle sites",         "fr": "tous les sites",  "en": "all sites"},
    "no_site":              {"nl": "geen site",          "fr": "aucun site",      "en": "no site"},
    "no_site_option":       {"nl": "— geen site —",     "fr": "— aucun site —",  "en": "— no site —"},
    "no_users_found":       {"nl": "Geen gebruikers gevonden.", "fr": "Aucun utilisateur trouvé.", "en": "No users found."},
    "new_user":             {"nl": "Nieuwe gebruiker aanmaken", "fr": "Créer un nouvel utilisateur", "en": "Create new user"},
    "new_password":         {"nl": "Nieuw wachtwoord",  "fr": "Nouveau mot de passe", "en": "New password"},
    "reset_password":       {"nl": "Wachtwoord resetten", "fr": "Réinitialiser le mot de passe", "en": "Reset password"},
    "confirm_delete_user":  {"nl": "Gebruiker {name} definitief verwijderen?", "fr": "Supprimer définitivement l'utilisateur {name} ?", "en": "Permanently delete user {name}?"},
    "pw_placeholder":       {"nl": "Min. 8 tekens, A-Z, 0-9", "fr": "Min. 8 car., A-Z, 0-9", "en": "Min. 8 chars, A-Z, 0-9"},
    "user_placeholder":     {"nl": "bijv. j.peeters",   "fr": "p.ex. j.dupont",  "en": "e.g. j.smith"},
    "role_desc_full":       {"nl": "user — uploaden & analyseren (eigen site) | site manager — alle studies van eigen site, gebruikers aanmaken | admin — alles: alle sites, gebruikersbeheer, sitebeheer",
                             "fr": "user — télécharger & analyser (son site) | site manager — toutes les études de son site, créer des utilisateurs | admin — tout : tous les sites, gestion des utilisateurs et sites",
                             "en": "user — upload & analyze (own site) | site manager — all studies of own site, create users | admin — everything: all sites, user & site management"},
    "site_only_users":      {"nl": "Als site manager kan je enkel users aanmaken voor jouw eigen site.",
                             "fr": "En tant que gestionnaire de site, vous ne pouvez créer que des utilisateurs pour votre propre site.",
                             "en": "As a site manager, you can only create users for your own site."},

    # Admin sites
    "site_name":            {"nl": "Sitenaam",           "fr": "Nom du site",     "en": "Site name"},
    "address":              {"nl": "Adres",              "fr": "Adresse",         "en": "Address"},
    "phone":                {"nl": "Telefoon",           "fr": "Téléphone",       "en": "Phone"},
    "email":                {"nl": "E-mail",             "fr": "E-mail",          "en": "Email"},
    "logo":                 {"nl": "Logo",               "fr": "Logo",            "en": "Logo"},
    "url":                  {"nl": "Website",            "fr": "Site web",        "en": "Website"},
    "new_site":             {"nl": "Nieuwe site aanmaken", "fr": "Créer un nouveau site", "en": "Create new site"},
    "edit_site":            {"nl": "Site bewerken",      "fr": "Modifier le site", "en": "Edit site"},
    "confirm_delete_site":  {"nl": "Site {name} verwijderen? Alle gekoppelde gebruikers worden ontkoppeld.",
                             "fr": "Supprimer le site {name} ? Tous les utilisateurs liés seront détachés.",
                             "en": "Delete site {name}? All linked users will be unlinked."},
    "n_users":              {"nl": "{n} gebruikers",     "fr": "{n} utilisateurs", "en": "{n} users"},

    # Report editor
    "report_header":        {"nl": "Rapport instellingen", "fr": "Paramètres du rapport", "en": "Report settings"},
    "header_name":          {"nl": "Naam instelling",   "fr": "Nom de l'établissement", "en": "Institution name"},
    "header_address":       {"nl": "Adres instelling",  "fr": "Adresse de l'établissement", "en": "Institution address"},
    "verified_by":          {"nl": "Geverifieerd door",  "fr": "Vérifié par",     "en": "Verified by"},
    "not_verified":         {"nl": "Niet geverifieerd",  "fr": "Non vérifié",     "en": "Not verified"},
    "mark_verified":        {"nl": "Markeer als geverifieerd", "fr": "Marquer comme vérifié", "en": "Mark as verified"},
    "scorer":               {"nl": "Scorer",             "fr": "Scorer",          "en": "Scorer"},
    "physician":            {"nl": "Arts",               "fr": "Médecin",         "en": "Physician"},
    "date":                 {"nl": "Datum",              "fr": "Date",            "en": "Date"},
    "comments":             {"nl": "Opmerkingen",        "fr": "Remarques",       "en": "Comments"},

    # Dashboard / results
    "search":               {"nl": "Zoeken...",          "fr": "Rechercher...",   "en": "Search..."},
    "no_studies":            {"nl": "Nog geen analyses uitgevoerd.", "fr": "Aucune analyse effectuée.", "en": "No analyses performed yet."},
    "delete_study":         {"nl": "Studie verwijderen", "fr": "Supprimer l'étude", "en": "Delete study"},
    "confirm_delete_study": {"nl": "Studie definitief verwijderen? Alle bestanden worden gewist.",
                             "fr": "Supprimer définitivement l'étude ? Tous les fichiers seront effacés.",
                             "en": "Permanently delete study? All files will be removed."},
    "download_pdf":         {"nl": "PDF downloaden",     "fr": "Télécharger PDF", "en": "Download PDF"},
    "download_excel":       {"nl": "Excel downloaden",   "fr": "Télécharger Excel", "en": "Download Excel"},
    "download_edfplus":     {"nl": "EDF+ downloaden",    "fr": "Télécharger EDF+", "en": "Download EDF+"},
    "download_fhir":        {"nl": "FHIR R4 downloaden", "fr": "Télécharger FHIR R4", "en": "Download FHIR R4"},
    "view_signals":         {"nl": "Signalen bekijken",  "fr": "Voir les signaux", "en": "View signals"},
    "open_scorer":          {"nl": "Scorer openen",      "fr": "Ouvrir le scorer", "en": "Open scorer"},

    # PDF report section headers (v0.8.11)
    "rpt_sec0a":            {"nl": "Registratie — Kanalen", "fr": "Enregistrement — Canaux", "en": "Recording — Channels"},
    "rpt_sec0b":            {"nl": "Visueel overzicht", "fr": "Aperçu visuel", "en": "Visual Overview"},
    "pdf_ch_col":           {"nl": "Kanaal", "fr": "Canal", "en": "Channel"},
    "pdf_ch_total":         {"nl": "kanalen in EDF-bestand", "fr": "canaux dans le fichier EDF", "en": "channels in EDF file"},
    "rpt_sec1":             {"nl": "1  Slaaparchitectuur  (AASM)", "fr": "1  Architecture du sommeil  (AASM)", "en": "1  Sleep Architecture  (AASM)"},
    "rpt_sec2":             {"nl": "2  Slaapcycli (NREM-REM)", "fr": "2  Cycles NREM-REM", "en": "2  Sleep Cycles (NREM-REM)"},
    "rpt_sec3":              {"nl": "3  Slaapspoelen", "fr": "3  Fuseaux du sommeil", "en": "3  Sleep Spindles"},
    "rpt_sec4":              {"nl": "4  Trage Golven", "fr": "4  Ondes lentes", "en": "4  Slow Waves"},
    "rpt_sec5":              {"nl": "5  REM Detectie", "fr": "5  Détection REM", "en": "5  REM Detection"},
    "rpt_sec6":              {"nl": "6  Spectrale Bandpower", "fr": "6  Puissance spectrale", "en": "6  Spectral Band Power"},
    "rpt_sec7":              {"nl": "7  Artefacten", "fr": "7  Artéfacts", "en": "7  Artifacts"},
    "rpt_sec7b":             {"nl": "7b  Signaalkwaliteit & Confidence Review", "fr": "7b  Qualité du signal & Revue de confiance", "en": "7b  Signal Quality & Confidence Review"},
    "rpt_sec8":             {"nl": "8  Respiratoire Analyse  (AASM Rule 1A + 1B)", "fr": "8  Analyse respiratoire  (AASM Rule 1A + 1B)", "en": "8  Respiratory Analysis  (AASM Rule 1A + 1B)"},
    "rpt_sec8b":            {"nl": "8b  Arousals & RERA  (AASM 3.9)", "fr": "8b  Arousals & RERA  (AASM 3.9)", "en": "8b  Arousals & RERA  (AASM 3.9)"},
    "rpt_sec8c":             {"nl": "8c  Ademhalingsanalyse", "fr": "8c  Analyse respiratoire détaillée", "en": "8c  Breath-by-Breath Analysis"},
    "rpt_sec9":              {"nl": "9  SpO2 Analyse", "fr": "9  Analyse SpO2", "en": "9  SpO2 Analysis"},
    "rpt_sec10":            {"nl": "10  Periodieke Beenbewegingen (PLM)", "fr": "10  Mouvements périodiques des jambes (PLM)", "en": "10  Periodic Limb Movements (PLM)"},
    "rpt_sec10b":            {"nl": "10b  Ronchopathie (snurk-analyse)", "fr": "10b  Ronchopathie (analyse du ronflement)", "en": "10b  Ronchopathy (Snoring Analysis)"},
    "rpt_sec8d":            {"nl": "8d  Flow-reductie zonder criteria (FRI)", "fr": "8d  Réduction de flux sans critères (IFR)", "en": "8d  Flow Reduction Without Criteria (FRI)"},
    "rpt_sec8e":            {"nl": "8e  Signaalvoorbeelden", "fr": "8e  Exemples de signaux", "en": "8e  Signal Examples"},
    "pdf_epoch_intro":      {"nl": "Representatieve respiratoire events met pneumologische kanalen. Rode band = event-duur.",
                             "fr": "Événements respiratoires représentatifs avec canaux pneumologiques. Bande rouge = durée de l'événement.",
                             "en": "Representative respiratory events with pneumological channels. Red band = event duration."},
    "rpt_sec11":            {"nl": "11  Besluit", "fr": "11  Conclusion", "en": "11  Conclusion"},

    # Common words used across templates
    "name":                 {"nl": "Naam",               "fr": "Nom",             "en": "Name"},
    "type":                 {"nl": "Type",               "fr": "Type",            "en": "Type"},
    "duration":             {"nl": "Duur",               "fr": "Durée",           "en": "Duration"},
    "results":              {"nl": "Resultaten",         "fr": "Résultats",       "en": "Results"},
    "analysis":             {"nl": "Analyse",            "fr": "Analyse",         "en": "Analysis"},
    "report":               {"nl": "Rapport",            "fr": "Rapport",         "en": "Report"},
    "overview":             {"nl": "Overzicht",          "fr": "Aperçu",          "en": "Overview"},
    "loading":              {"nl": "Laden...",            "fr": "Chargement...",   "en": "Loading..."},
    "error":                {"nl": "Fout",               "fr": "Erreur",          "en": "Error"},
    "success":              {"nl": "Gelukt",             "fr": "Réussi",          "en": "Success"},
    "warning":              {"nl": "Waarschuwing",       "fr": "Avertissement",   "en": "Warning"},
    "back":                 {"nl": "Terug",              "fr": "Retour",          "en": "Back"},
    "next":                 {"nl": "Volgende",           "fr": "Suivant",         "en": "Next"},
    "close":                {"nl": "Sluiten",            "fr": "Fermer",          "en": "Close"},
    "confirm":              {"nl": "Bevestigen",         "fr": "Confirmer",       "en": "Confirm"},
    "start_analysis":       {"nl": "Start analyse",      "fr": "Démarrer l'analyse", "en": "Start analysis"},

    # ── UPLOAD PAGINA (v0.8.11) ─────────────────────────────────────────────
    "upload_step1":         {"nl": "Stap 1 van 3 · EDF Upload", "fr": "Étape 1 sur 3 · Upload EDF", "en": "Step 1 of 3 · EDF Upload"},
    "upload_title":         {"nl": "Laad uw opname", "fr": "Chargez votre enregistrement", "en": "Upload your recording"},
    "upload_subtitle":      {"nl": "European Data Format polysomnografie · max 500 MB", "fr": "European Data Format polysomnographie · max 500 Mo", "en": "European Data Format polysomnography · max 500 MB"},
    "upload_drop":          {"nl": "Polysomnografie-opname van elk PSG-apparaat", "fr": "Enregistrement polysomnographique de tout appareil PSG", "en": "Polysomnography recording from any PSG device"},
    "upload_channels":      {"nl": "Kanalen", "fr": "Canaux", "en": "Channels"},
    "upload_duration":      {"nl": "Duur", "fr": "Durée", "en": "Duration"},
    "upload_uploading":     {"nl": "Upload bezig...", "fr": "Upload en cours...", "en": "Uploading..."},
    "upload_btn":           {"nl": "Uploaden & analyseren", "fr": "Uploader & analyser", "en": "Upload & analyze"},
    "upload_btn_uploading": {"nl": "Uploaden...", "fr": "Upload en cours...", "en": "Uploading..."},
    "upload_btn_analyzing": {"nl": "EDF analyseren...", "fr": "Analyse EDF...", "en": "Analyzing EDF..."},
    "upload_ready":         {"nl": "MB — klaar om te uploaden", "fr": "Mo — prêt à uploader", "en": "MB — ready to upload"},
    "upload_started":       {"nl": "Upload gestart", "fr": "Upload démarré", "en": "Upload started"},
    "upload_net_error":     {"nl": "Netwerk fout bij chunk", "fr": "Erreur réseau au chunk", "en": "Network error at chunk"},
    "upload_srv_error":     {"nl": "Server fout bij chunk", "fr": "Erreur serveur au chunk", "en": "Server error at chunk"},
    "upload_parse":         {"nl": "EDF-kanalen analyseren...", "fr": "Analyse des canaux EDF...", "en": "Analyzing EDF channels..."},
    "upload_parse_error":   {"nl": "Parse fout", "fr": "Erreur d'analyse", "en": "Parse error"},
    "upload_parse_fail":    {"nl": "Parse mislukt", "fr": "Analyse échouée", "en": "Parse failed"},
    "upload_channels_found":{"nl": "kanalen gevonden", "fr": "canaux trouvés", "en": "channels found"},
    "upload_analysis_start":{"nl": "Analyse gestart", "fr": "Analyse démarrée", "en": "Analysis started"},
    "upload_async":         {"nl": "Async verwerking", "fr": "Traitement asynchrone", "en": "Async processing"},

    # ── KANAALSELECTIE (v0.8.11) ────────────────────────────────────────────
    "eeg_primary":          {"nl": "EEG primair kanaal", "fr": "Canal EEG principal", "en": "Primary EEG channel"},
    "eog_channel":          {"nl": "EOG kanaal", "fr": "Canal EOG", "en": "EOG channel"},
    "emg_channel":          {"nl": "EMG kanaal", "fr": "Canal EMG", "en": "EMG channel"},
    "extra_eeg":            {"nl": "Extra EEG-kanalen", "fr": "Canaux EEG supplémentaires", "en": "Extra EEG channels"},
    "recording_time_label": {"nl": "Opnametijdstip", "fr": "Heure d'enregistrement", "en": "Recording time"},
    "patient_data":         {"nl": "Patiëntgegevens", "fr": "Données patient", "en": "Patient data"},
    "optional":             {"nl": "optioneel", "fr": "optionnel", "en": "optional"},
    "recommended_staging":  {"nl": "Aanbevolen voor YASA staging", "fr": "Recommandé pour le staging YASA", "en": "Recommended for YASA staging"},
    "address_placeholder":  {"nl": "Straat nr, postcode gemeente (optioneel)", "fr": "Rue n°, code postal ville (optionnel)", "en": "Street no, postal code city (optional)"},

    # ── PDF RAPPORT: patient info labels (v0.8.11) ──────────────────────────
    "pdf_name":             {"nl": "Naam:", "fr": "Nom :", "en": "Name:"},
    "pdf_dob":              {"nl": "Geboortedatum:", "fr": "Date de naissance :", "en": "Date of birth:"},
    "pdf_age":              {"nl": "Leeftijd:", "fr": "Âge :", "en": "Age:"},
    "pdf_sex":              {"nl": "Geslacht:", "fr": "Sexe :", "en": "Sex:"},
    "pdf_bmi":              {"nl": "BMI:", "fr": "IMC :", "en": "BMI:"},
    "pdf_patient_id":       {"nl": "Patiënt-ID:", "fr": "ID Patient :", "en": "Patient ID:"},
    "pdf_rec_date":         {"nl": "Opnamedatum:", "fr": "Date d'enregistrement :", "en": "Recording date:"},
    "pdf_duration":         {"nl": "Duur:", "fr": "Durée :", "en": "Duration:"},
    "pdf_scorer":           {"nl": "Scorer:", "fr": "Scorer :", "en": "Scorer:"},
    "pdf_institution":      {"nl": "Instelling:", "fr": "Établissement :", "en": "Institution:"},
    "pdf_page":             {"nl": "Pagina", "fr": "Page", "en": "Page"},
    "pdf_year":             {"nl": "jaar", "fr": "ans", "en": "years"},

    # ── PDF RAPPORT: sleep architecture table ──────────────────────────────
    "pdf_param":            {"nl": "Parameter", "fr": "Paramètre", "en": "Parameter"},
    "pdf_value":            {"nl": "Waarde", "fr": "Valeur", "en": "Value"},
    "rpt_patient_info":     {"nl": "Patiëntgegevens (uit EDF)", "fr": "Données patient (depuis EDF)", "en": "Patient info (from EDF)"},
    "pdf_name":             {"nl": "Naam", "fr": "Nom", "en": "Name"},
    "pdf_sex":              {"nl": "Geslacht", "fr": "Sexe", "en": "Sex"},
    "pdf_male":             {"nl": "Man", "fr": "Homme", "en": "Male"},
    "pdf_female":           {"nl": "Vrouw", "fr": "Femme", "en": "Female"},
    "pdf_birthdate":        {"nl": "Geboortedatum", "fr": "Date de naissance", "en": "Date of birth"},
    "pdf_patientcode":      {"nl": "Patiëntcode", "fr": "Code patient", "en": "Patient code"},
    "pdf_recording_date":   {"nl": "Opnamedatum", "fr": "Date d'enregistrement", "en": "Recording date"},
    "pdf_technician":       {"nl": "Technicus", "fr": "Technicien", "en": "Technician"},
    "pdf_equipment":        {"nl": "Apparatuur", "fr": "Équipement", "en": "Equipment"},
    "pdf_signal_quality":   {"nl": "Signaalkwaliteit", "fr": "Qualité du signal", "en": "Signal quality"},
    "pdf_channel":          {"nl": "Kanaal", "fr": "Canal", "en": "Channel"},
    "pdf_quality":          {"nl": "Kwaliteit", "fr": "Qualité", "en": "Quality"},
    "pdf_montage_warnings": {"nl": "Montage-waarschuwingen", "fr": "Avertissements montage", "en": "Montage warnings"},
    "pdf_ref":              {"nl": "Ref", "fr": "Réf", "en": "Ref"},
    "pdf_normal":           {"nl": "Normaal", "fr": "Normal", "en": "Normal"},
    "pdf_se":               {"nl": "Slaapefficiëntie (SE)", "fr": "Efficacité du sommeil (SE)", "en": "Sleep Efficiency (SE)"},
    "pdf_sol":              {"nl": "Slaaplatentie (SOL)", "fr": "Latence d'endormissement (SOL)", "en": "Sleep Onset Latency (SOL)"},
    "pdf_rem_lat":          {"nl": "REM-latentie", "fr": "Latence REM", "en": "REM Latency"},

    # ── PDF RAPPORT: KPI labels ────────────────────────────────────────────
    "pdf_rem_periods":      {"nl": "REM-perioden", "fr": "Périodes REM", "en": "REM Periods"},
    "pdf_rem_dur":          {"nl": "REM-duur", "fr": "Durée REM", "en": "REM Duration"},
    "pdf_mean_period":      {"nl": "Gem. periode", "fr": "Période moy.", "en": "Mean Period"},
    "pdf_longest":          {"nl": "Langste", "fr": "La plus longue", "en": "Longest"},

    # ── PDF RAPPORT: respiratory events ────────────────────────────────────
    "pdf_obstructive":      {"nl": "Obstructief apnea", "fr": "Apnée obstructive", "en": "Obstructive Apnea"},
    "pdf_central":          {"nl": "Centraal apnea", "fr": "Apnée centrale", "en": "Central Apnea"},
    "pdf_mixed":            {"nl": "Gemengd apnea", "fr": "Apnée mixte", "en": "Mixed Apnea"},
    "pdf_hypopnea":         {"nl": "Hypopnea", "fr": "Hypopnée", "en": "Hypopnea"},
    "pdf_total_events":     {"nl": "Totaal events (AH)", "fr": "Total événements (AH)", "en": "Total Events (AH)"},
    "pdf_avg_apnea_dur":    {"nl": "Gem. apnea-duur", "fr": "Durée moy. apnée", "en": "Mean Apnea Duration"},
    "pdf_resp_arousals":    {"nl": "Respiratoire arousals", "fr": "Arousals respiratoires", "en": "Respiratory Arousals"},
    "pdf_spont_arousals":   {"nl": "Spontane arousals", "fr": "Arousals spontanés", "en": "Spontaneous Arousals"},
    "pdf_detected_breaths": {"nl": "Gedetecteerde ademhalingen", "fr": "Respirations détectées", "en": "Detected Breaths"},
    "pdf_bb_apneas":        {"nl": "Breath-by-breath apneus", "fr": "Apnées breath-by-breath", "en": "Breath-by-breath Apneas"},
    "pdf_bb_hypopneas":     {"nl": "Breath-by-breath hypopneus", "fr": "Hypopnées breath-by-breath", "en": "Breath-by-breath Hypopneas"},
    "pdf_mean_flattening":  {"nl": "Gem. flattening index", "fr": "Index d'aplatissement moy.", "en": "Mean Flattening Index"},

    # ── PDF RAPPORT: SpO2 ──────────────────────────────────────────────────
    "pdf_time_below90":     {"nl": "Tijd < 90%", "fr": "Temps < 90%", "en": "Time < 90%"},
    "pdf_time_axis":        {"nl": "Tijd (uur)", "fr": "Temps (heures)", "en": "Time (hours)"},
    "pdf_no_channel":       {"nl": "geen kanaal", "fr": "pas de canal", "en": "no channel"},

    # ── PDF RAPPORT: PLM ───────────────────────────────────────────────────
    "pdf_total_lms":        {"nl": "Totaal LMs", "fr": "Total MJ", "en": "Total LMs"},
    "pdf_plms_series":      {"nl": "PLMs (in series)", "fr": "MPS (en série)", "en": "PLMs (in series)"},
    "pdf_plm_series":       {"nl": "PLM-series", "fr": "Séries PLM", "en": "PLM Series"},

    # ── PDF RAPPORT: ronchopathie (snurk) ──────────────────────────────────
    "pdf_snore_min":        {"nl": "Snurkduur", "fr": "Durée de ronflement", "en": "Snoring Duration"},
    "pdf_snore_pct":        {"nl": "Snurk % van TST", "fr": "Ronflement % du TST", "en": "Snoring % of TST"},
    "pdf_snore_index":      {"nl": "Snurk-index", "fr": "Index de ronflement", "en": "Snoring Index"},
    "pdf_snore_no_data":    {"nl": "Geen snurk-kanaal gedetecteerd in de opname.", "fr": "Aucun canal de ronflement détecté dans l'enregistrement.", "en": "No snoring channel detected in the recording."},

    # ── PDF RAPPORT: flow-reductie index (FRI) ────────────────────────────
    "pdf_fri_count":        {"nl": "Flow-reducties zonder criteria", "fr": "Réductions de flux sans critères", "en": "Flow Reductions Without Criteria"},
    # De sterrenkolommen tonen een score van 0 tot 1. Die score rangschikt
    # events naar hoe goed ze aan de AASM-criteria voldoen; hij is GEEN kans
    # dat een scorer het event zou markeren. Gemeten tegen twaalf scorers per
    # opname (PSG-IPA) is de correlatie r = 0,19 en ligt het niveau ruim 30
    # procentpunt te hoog. Zonder deze voetnoot leest "★★★ ≥0,85" als 85%.
    "pdf_conf_bands_note":  {"nl": "Score 0–1 voor hoe goed het event aan de AASM-criteria voldoet. Bedoeld om events onderling te rangschikken, niet als kans dat een scorer het event zou markeren.",
                             "fr": "Score 0–1 indiquant dans quelle mesure l'événement satisfait aux critères AASM. Destiné à classer les événements entre eux, non à exprimer la probabilité qu'un scoreur le marque.",
                             "en": "Score 0–1 for how well the event satisfies the AASM criteria. Intended to rank events relative to each other, not as the probability that a scorer would mark it.",
                             "de": "Score 0–1 dafür, wie gut das Ereignis die AASM-Kriterien erfüllt. Zum Ordnen der Ereignisse untereinander gedacht, nicht als Wahrscheinlichkeit, dass ein Auswerter es markieren würde."},
    # Subtypering van hypopnees. Alleen getoond wanneer er centrale of
    # gemengde hypopnees zijn; anders is het ruis in een rapport waarin
    # vrijwel alles obstructief is.
    "pdf_hyp_sub_central":  {"nl": "waarvan centraal", "fr": "dont centrales",
                             "en": "of which central", "de": "davon zentral"},
    "pdf_hyp_sub_mixed":    {"nl": "waarvan gemengd", "fr": "dont mixtes",
                             "en": "of which mixed", "de": "davon gemischt"},
    # De laagste saturatie TIJDENS een respiratoir event. Niet hetzelfde als
    # het nachtminimum daarboven: dat kan van een artefact of een dip buiten
    # elk event komen.
    "pdf_event_spo2_nadir": {"nl": "Laagste SpO2 tijdens een event",
                             "fr": "SpO2 la plus basse pendant un événement",
                             "en": "Lowest SpO2 during an event",
                             "de": "Niedrigste SpO2 während eines Ereignisses"},
    "pdf_fri_index":        {"nl": "FRI (flow-reductie-index)", "fr": "IFR (indice de réduction de flux)", "en": "FRI (Flow Reduction Index)"},
    "pdf_fri_r1b":          {"nl": "Waarvan hersteld via Rule 1B (arousal)", "fr": "Dont restaurés via Rule 1B (arousal)", "en": "Of which reinstated via Rule 1B (arousal)"},
    "pdf_fri_note":         {"nl": "Flow-reducties (≥30%, ≥10s) die niet voldoen aan hypopnea-criteria: geen ≥3% desaturatie en geen arousal. Geen onderdeel van AHI. Klinische relevantie bij UARS/RDI-evaluatie.",
                             "fr": "Réductions de flux (≥30%, ≥10s) ne répondant pas aux critères d'hypopnée : pas de désaturation ≥3% ni d'arousal. Non incluses dans l'IAH. Pertinence clinique pour l'évaluation SARVAS/IDR.",
                             "en": "Flow reductions (≥30%, ≥10s) not meeting hypopnea criteria: no ≥3% desaturation and no arousal. Not included in AHI. Clinically relevant for UARS/RDI evaluation."},

    # ── PDF RAPPORT: leeg besluit ──────────────────────────────────────────
    "concl_empty":          {"nl": "Besluit in te vullen door behandelend arts.", "fr": "Conclusion à compléter par le médecin traitant.", "en": "Conclusion to be completed by the treating physician."},

    # ── PDF RAPPORT: disclaimer/footer ─────────────────────────────────────
    "pdf_disc_auto":        {"nl": "Automatisch gegenereerd door YASAFlaskified v{version}. YASA AI-slaapstaging (~85% epoch-overeenkomst, Vallat &amp; Walker 2021). Respiratoire scoring volgens psgscoring, conform AASM Rule 1A/1B.",
                             "fr": "Généré automatiquement par YASAFlaskified v{version}. Staging du sommeil par YASA AI (~85% concordance par époque, Vallat &amp; Walker 2021). Scoring respiratoire par psgscoring, conforme à l'AASM Rule 1A/1B.",
                             "en": "Automatically generated by YASAFlaskified v{version}. YASA AI sleep staging (~85% epoch agreement, Vallat &amp; Walker 2021). Respiratory scoring by psgscoring, per AASM Rule 1A/1B."},
    "pdf_disc_verified":    {"nl": "Resultaten geverifieerd door {role} {name}. Klinische interpretatie onder verantwoordelijkheid van de behandelend arts.",
                             "fr": "Résultats vérifiés par {role} {name}. L'interprétation clinique relève de la responsabilité du médecin traitant.",
                             "en": "Results verified by {role} {name}. Clinical interpretation under responsibility of the treating physician."},
    "pdf_disc_screening":   {"nl": "Screening-tool en second opinion — vervangt geen manuele scoring of medische diagnose.",
                             "fr": "Outil de dépistage et second avis — ne remplace pas le scoring manuel ni le diagnostic médical.",
                             "en": "Screening tool and second opinion — does not replace manual scoring or medical diagnosis."},
    "pdf_verified_by":      {"nl": "Dit rapport werd geverifieerd door {role} {name}.",
                             "fr": "Ce rapport a été vérifié par {role} {name}.",
                             "en": "This report was verified by {role} {name}."},
    "pdf_role_tech":        {"nl": "slaaptechnicus", "fr": "technicien du sommeil", "en": "sleep technician"},
    "pdf_role_physician":   {"nl": "arts", "fr": "médecin", "en": "physician"},

    # ── PDF RAPPORT: Cheyne-Stokes detail ──────────────────────────────────
    "pdf_csr_duration":     {"nl": "Duur:", "fr": "Durée :", "en": "Duration:"},

    # ── PDF RAPPORT: table headers ─────────────────────────────────────────
    "cycle":                {"nl": "Cyclus", "fr": "Cycle", "en": "Cycle"},
    "epochs":               {"nl": "Epochs", "fr": "Époques", "en": "Epochs"},
    "composition":          {"nl": "Samenstelling", "fr": "Composition", "en": "Composition"},
}

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("nl", "fr", "en", "de")
LANG_NAMES = {"nl": "Nederlands", "fr": "Français", "en": "English", "de": "Deutsch"}
LANG_FLAGS = {"nl": "🇧🇪", "fr": "🇫🇷", "en": "🇬🇧", "de": "🇩🇪"}


def get_translation(key: str, lang: str = None) -> str:
    """Haal vertaling op. Fallback: gevraagde taal → nl → en → key."""
    lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return (entry.get(lang)
            or entry.get(DEFAULT_LANG)
            or entry.get("en")
            or key)




# v0.8.37: Additional multilingual keys for PDF report
_PDF_KEYS = {
    "pdf_not_available": {"nl": "Niet beschikbaar", "fr": "Non disponible", "en": "Not available", "de": "Nicht verfügbar"},
    "pdf_overcounting_corrections": {"nl": "Overschatting-correctie", "fr": "Corrections de surestimation", "en": "Over-counting corrections", "de": "Überzählungskorrekturen"},
    "pdf_correction": {"nl": "Correctie", "fr": "Correction", "en": "Correction", "de": "Korrektur"},
    "pdf_impact": {"nl": "Impact", "fr": "Impact", "en": "Impact", "de": "Auswirkung"},
    "pdf_explanation": {"nl": "Toelichting", "fr": "Explication", "en": "Explanation", "de": "Erklärung"},
}
TRANSLATIONS.update(_PDF_KEYS)


# ======================================================================
# v0.8.37: German (DE) translations — auto-generated from EN
# ======================================================================

_DE_PATCH = {
    "actions": "Actions",
    "add_user": "Add user",
    "address": "Address",
    "address_placeholder": "Street no, postal code city (optional)",
    "admin_cannot_delete": "Admin user cannot be deleted.",
    "admin_only": "Administrators only.",
    "admin_only_register": "New users are created by the administrator.",
    "admin_panel": "Admin panel",
    "admin_role_fixed": "Admin role cannot be changed.",
    "ahi": "AHI",
    "ai_staging": "AI staging",
    "all_fields_required": "All fields are required.",
    "all_results_available": "All results are available.",
    "all_severities": "All severities",
    "all_severity": "All severity levels",
    "all_sites": "all sites",
    "all_statistics": "All statistics",
    "all_statuses": "All statuses",
    "analyses_ready": "Analyses ready",
    "analysis": "Analyse",
    "analysis_complete": "Analyse complete!",
    "analysis_description": "Die Analyse kombiniert YASA AI-Schlafstaging mit regelbasiertem respiratorischem Scoring. Auf dem mesa_shhs-Profil wird zusätzlich ein LightGBM-Kandidatenklassifikator angewendet (psgscoring v0.6).",
    "analysis_duration": "Die Analysedauer hängt von der Aufzeichnungslänge und vom gewählten Profil ab (typischerweise 3–10 Min pro Aufzeichnung).",
    "analysis_failed": "Analyse failed",
    "analysis_history": "Analyse history",
    "analysis_in_progress": "Analyse in progress…",
    "analysis_results": "Analyse results",
    "analysis_running": "Analyse in progress",
    "analysis_starting": "Starting Analyse...",
    "appears_on_reports": "appears on all Berichts",
    "arousal_index": "Arousal index",
    "arousal_rera": "Arousal & RERA",
    "artifacts_found": "epochs contain artifacts",
    "assign_site": "Assign site",
    "auto_conclusion": "Auto conclusion",
    "auto_detect": "Auto-detect",
    "auto_select_eeg": "Auto-select (EEG)",
    "average": "Durchschnitt",
    "avg_desaturation": "Avg. desaturation",
    "avg_duration": "Avg. duration",
    "avg_rem_period": "Avg. REM period",
    "avg_spo2": "Avg. SpO2",
    "back": "Back",
    "back_to_results": "Back to results",
    "band_ratios": "Band ratios",
    "baseline_spo2": "Basislinie SpO2",
    "bmi": "BMI",
    "cancel": "Abbrechen",
    "cannot_delete_admin": "Admin user cannot be deleted.",
    "central": "Zentral",
    "change_password": "Change password",
    "channel_select": "Kanal selection",
    "channel_select_title": "Kanal selection & patient data",
    "channels_found": "channels found",
    "choose_language": "Choose your language",
    "clear_filters": "Clear",
    "clear_selection": "Clear selection",
    "clinical_usability": "Screening tool and second opinion (~85% epoch agreement). Does not replace manual scoring or medical diagnosis.",
    "clinical_usability_title": "Clinical usability",
    "close": "Close",
    "comments": "Comments",
    "comments_placeholder": "Optional comments for the Bericht...",
    "composition": "Composition",
    "concl_conclusion": "Conclusion",
    "concl_csr_body": "Cyclic crescendo-decrescendo breathing pattern.",
    "concl_csr_title": "Cheyne-Stokes respiration (CSR) detected.",
    "concl_csr_tx": "Cardiology referral recommended. Echocardiography to evaluate left ventricular function. Consider adaptive servo-ventilation (ASV).",
    "concl_diagnosis": "Diagnose",
    "concl_empty": "Conclusion to be completed by the treating physician.",
    "concl_insomnia_quality": "Reduced Schlaf quality",
    "concl_insomnia_se": "Schlaf efficiency {se:.1f}% (normal ≥85%)",
    "concl_insomnia_title": "Signs of insomnia.",
    "concl_insomnia_tst": "TST {tst:.0f} min (reduced)",
    "concl_insomnia_tx": "Cognitive behavioral therapy for insomnia (CBT-I) is first-line. Schlaf hygiene evaluation. Pharmacotherapy only short-term.",
    "concl_mild_body": "Leicht OSAS with limited Schlaf fragmentation.",
    "concl_mild_title": "Conclusion: Leicht obstructive Schlaf Apnoe syndrome (mild OSAS).",
    "concl_mild_tx": "Positional therapy (avoid supine position). Consider mandibular advancement device (MAD). Optimize Schlaf hygiene.",
    "concl_mod_body": "Mittelgradig OSAS with Schlaf fragmentation.",
    "concl_mod_title": "Conclusion: Mittelgradig obstructive Schlaf Apnoe syndrome (moderate OSAS).",
    "concl_mod_tx": "CPAP therapy recommended (first-line). Alternative: mandibular advancement device (MAD) if CPAP-intolerant. Positional therapy as adjunct.",
    "concl_normal_body": "Nein evidence of obstructive Schlaf Apnoe syndrome (OSAS). Neinrmal Schlaf architecture. Nein clinically significant periodic limb movements.",
    "concl_normal_title": "Conclusion: Neinrmal polysomnogram.",
    "concl_plm_body": "Clinically significant periodic limb movements.",
    "concl_plm_title": "Periodic limb movements during Schlaf (PLMS).",
    "concl_plm_tx": "Check iron status (ferritin). If ferritin < 75 µg/L: iron supplementation. For persistent symptoms: consider dopamine agonist.",
    "concl_sev_body": "Schwer OSAS with significant Schlaf fragmentation.",
    "concl_sev_desat": "Significant nocturnal desaturations.",
    "concl_sev_title": "Conclusion: Schwer obstructive Schlaf Apnoe syndrome (severe OSAS).",
    "concl_sev_tx": "CPAP therapy strictly recommended (first-line, urgent). For severe desaturations: consider evaluation for oxygen therapy. ENT evaluation for surgical options in anatomical obstruction.",
    "concl_suggestion": "Suggestion",
    "concl_treatment": "Behandlung suggestions",
    "concl_weight": "Weight reduction strongly recommended.",
    "concl_weight_essential": "Weight reduction essential.",
    "conclusion": "Conclusion",
    "conclusion_saved": "Conclusion saved and PDF generated.",
    "confidence": "Konfidenz",
    "confirm": "Confirm",
    "confirm_delete_site": "Löschen site {name}? All linked users will be unlinked.",
    "confirm_delete_study": "Permanently delete study? All files will be removed.",
    "confirm_delete_user": "Permanently delete user {name}?",
    "confirm_password": "Confirm password",
    "corrections_count": "changes vs AI",
    "create": "Create",
    "current_password": "Current password",
    "cycle": "Zyklus",
    "dashboard": "Dashboard",
    "date": "Datum",
    "date_of_birth": "Datum of birth",
    "deep_sleep": "Deep Schlaf",
    "default_time_note": "If empty, a default time (22:00) will be used.",
    "delete": "Löschen",
    "delete_not_allowed": "You do not have permission to delete this study.",
    "delete_study": "Löschen study",
    "delete_user": "Löschen",
    "desat_index": "Desaturation index",
    "desat_pct": "Desat %",
    "detection_failed": "detection failed",
    "diagnosis": "Diagnose",
    "diagnosis_help": "Select standard diagnoses from the dropdown or type free text. Multiple diagnoses can be combined.",
    "diagnosis_placeholder": "Type or select a diagnosis...",
    "diagnosis_text": "Diagnose text",
    "dob": "Datum of birth",
    "dob_label": "DoB",
    "download_edfplus": "Herunterladen EDF+",
    "download_excel": "Herunterladen Excel",
    "download_fhir": "Herunterladen FHIR R4",
    "download_json": "Herunterladen JSON",
    "download_pdf": "Herunterladen PDF",
    "download_psg": "Herunterladen PSG",
    "dur_s": "Dauer (s)",
    "duration": "Dauer",
    "edf_browser": "EDF Browser",
    "edf_not_found": "Original EDF file not found. Re-Analyse not possible.",
    "edf_read_error": "Fehler reading EDF file",
    "edfplus_failed": "EDF+ generation failed",
    "edfplus_generating": "EDF+ is being generated in the background. This takes a few Minuten. Try downloading again shortly.",
    "edit": "Edit",
    "edit_report": "Edit Bericht",
    "edit_site": "Edit site",
    "eeg_channel": "EEG channel (primary)",
    "eeg_primary": "Primary EEG channel",
    "eeg_primary_desc": "Main EEG for staging (e.g. C4-M1, C3-M2)",
    "email": "Email",
    "email_body_done": "The Analyse of {patient} is complete. View the Bericht at {url}.",
    "email_subject_done": "YASAFlaskified — Analyse complete",
    "emg_channel": "EMG channel",
    "emg_desc": "Muscle activity for staging",
    "eog_channel": "EOG channel",
    "eog_desc": "Eye movements for REM detection",
    "epoch": "Epoche",
    "epochs": "Epoches",
    "error": "Fehler",
    "error_occurred": "An error occurred.",
    "event_list": "Event list",
    "events_first_50": "Events (first 50 of",
    "experimental_warning": "Experimental tool — not for clinical diagnosis.",
    "extra_eeg": "Extra EEG channels",
    "extra_eeg_channels": "Extra EEG channels",
    "extra_eeg_desc": "For spindle, slow-wave and band power Analyse (multiple choice)",
    "female": "Female",
    "fields_prefilled": "Fields are pre-filled from EDF header if available.",
    "file": "File",
    "file_not_available": "File no longer available on server.",
    "file_not_found": "File not found.",
    "file_too_large": "File too large.",
    "first_n": "first",
    "firstname": "First name",
    "from_edf": "from EDF",
    "from_stage": "From stage",
    "generate_edfplus": "Generate EDF+",
    "header_address": "Institution address",
    "header_name": "Institution name",
    "height": "Height",
    "height_cm": "Height (cm)",
    "history": "History",
    "hypnogram_timeline": "Hypnogram timeline",
    "hypopnea": "Hypopnoe",
    "insert_standard": "Insert",
    "inst_label": "Inst.",
    "institution": "Institution",
    "insufficient_rights": "Insufficient rights for this page.",
    "internal_error": "An internal error occurred.",
    "invalid_channels": "Invalid channel selection. Please try again.",
    "invalid_file": "Invalid file path.",
    "invalid_role": "Invalid role.",
    "job_eeg_required": "Job ID and EEG channel are required.",
    "jump_to_event": "Jump to event",
    "language": "Sprache",
    "list_view": "List view",
    "lms_sleep": "LMs during Schlaf",
    "lms_wake": "LMs during wake",
    "loading": "Laden...",
    "logged_out": "You have been logged out.",
    "login": "Login",
    "login_failed": "Invalid username or password.",
    "login_success": "Login successful!",
    "logo": "Logo",
    "logout": "Logout",
    "longest_rem_period": "Longest REM period",
    "male": "Male",
    "manual_scoring": "Manual scoring",
    "manual_staging": "Manual staging",
    "mark_verified": "Mark as verified",
    "maximum": "Maximum",
    "mild_osa": "Leicht OSA",
    "min_spo2": "Min SpO2",
    "minimum": "Minimum",
    "mixed": "Gemischt",
    "moderate_osa": "Mittelgradig OSA",
    "n_users": "{n} users",
    "name": "Name",
    "name_label": "Name",
    "new_analysis": "New Analyse",
    "new_password": "New password",
    "new_site": "Create new site",
    "new_user": "Create new user",
    "next": "Next",
    "no_analyses_yet": "Nein analyses yet",
    "no_data": "Nein data",
    "no_site": "no site",
    "no_site_assigned": "Nein site assigned",
    "no_site_option": "— no site —",
    "no_studies": "Nein analyses performed yet.",
    "no_studies_found": "Nein analyses found yet.",
    "no_users_found": "Nein users found.",
    "normal": "Neinrmal",
    "not_available": "Neint available",
    "not_verified": "Neint verified",
    "nrem_rem_transitions": "NREM → REM Transitions",
    "oahi": "OAHI",
    "obstructive": "Obstruktiv",
    "only_authorized": "Authorized healthcare professionals only",
    "open_scorer": "Open scorer",
    "optional": "optional",
    "osa_detected": "OSA detected",
    "other_file": "Hochladen another file",
    "overview": "Overview",
    "parameter": "Parameter",
    "password": "Password",
    "password_changed": "Password changed successfully.",
    "password_mismatch": "New password and confirmation do not match.",
    "password_requirements": "Min. 8 chars, 1 uppercase, 1 lowercase, 1 digit.",
    "patient": "Patient",
    "patient_data": "Patient data",
    "patient_firstname": "First name",
    "patient_id": "Patient ID",
    "patient_info": "Patient information",
    "patient_name": "Last name",
    "patient_number": "Patient number",
    "patient_overview": "Patient overview",
    "pdf_age": "Age:",
    "pdf_avg_apnea_dur": "Mean Apnoe Dauer",
    "pdf_bb_apneas": "Breath-by-breath Apnoes",
    "pdf_bb_hypopneas": "Breath-by-breath Hypopnoes",
    "pdf_birthdate": "Datum of birth",
    "pdf_bmi": "BMI:",
    "pdf_central": "Zentral Apnoe",
    "pdf_ch_col": "Kanal",
    "pdf_ch_total": "channels in EDF file",
    "pdf_channel": "Kanal",
    "pdf_csr_duration": "Dauer:",
    "pdf_detected_breaths": "Detected Breaths",
    "pdf_disc_auto": "Automatisch generiert von YASAFlaskified v{version}. YASA AI-Schlafstaging (~85% Epoch-Übereinstimmung, Vallat &amp; Walker 2021). Respiratorisches Scoring durch psgscoring, gemäß AASM Rule 1A/1B.",
    "pdf_disc_screening": "Screening tool and second opinion — does not replace manual scoring or medical diagnosis.",
    "pdf_disc_verified": "Ergebnisse verified by {role} {name}. Clinical interpretation under responsibility of the treating physician.",
    "pdf_dob": "Datum of birth:",
    "pdf_duration": "Dauer:",
    "pdf_epoch_intro": "Representative respiratory events with pneumological channels. Red band = event duration.",
    "pdf_equipment": "Equipment",
    "pdf_female": "Female",
    "pdf_fri_count": "Flow Reductions Without Criteria",
    "pdf_fri_index": "FRI (Flow Reduction Index)",
    "pdf_fri_note": "Flow reductions (≥30%, ≥10s) not meeting Hypopnoe criteria: no ≥3% desaturation and no arousal. Neint included in AHI. Clinically relevant for UARS/RDI evaluation.",
    "pdf_fri_r1b": "Of which reinstated via Rule 1B (arousal)",
    "pdf_hypopnea": "Hypopnoe",
    "pdf_institution": "Institution:",
    "pdf_longest": "Longest",
    "pdf_male": "Male",
    "pdf_mean_flattening": "Mean Flattening Index",
    "pdf_mean_period": "Mean Period",
    "pdf_mixed": "Gemischt Apnoe",
    "pdf_montage_warnings": "Montage warnings",
    "pdf_name": "Name",
    "pdf_no_channel": "no channel",
    "pdf_no_staging": "Nein Schlaf staging (polygraphy — no EEG)",
    "pdf_normal": "Neinrmal",
    "pdf_obstructive": "Obstruktiv Apnoe",
    "pdf_page": "Page",
    "pdf_param": "Parameter",
    "pdf_patient_id": "Patient ID:",
    "pdf_patientcode": "Patient code",
    "pdf_plm_series": "PLM Series",
    "pdf_plms_series": "PLMs (in series)",
    "pdf_quality": "Qualität",
    "pdf_rec_date": "Aufnahme date:",
    "pdf_recording_date": "Aufnahme date",
    "pdf_ref": "Ref",
    "pdf_rei": "REI (Respiratorisch Event Index)",
    "pdf_rem_dur": "REM Dauer",
    "pdf_rem_lat": "REM Latency",
    "pdf_rem_periods": "REM Periods",
    "pdf_residual": "Residual",
    "pdf_resp_arousals": "Respiratorisch Arousals",
    "pdf_role_physician": "physician",
    "pdf_role_tech": "Schlaf technician",
    "pdf_scorer": "Scorer:",
    "pdf_se": "Schlaf Efficiency (SE)",
    "pdf_sex": "Sex",
    "pdf_signal_quality": "Signal quality",
    "pdf_snore_index": "Schnarchen Index",
    "pdf_snore_min": "Schnarchen Dauer",
    "pdf_snore_no_data": "Nein snoring channel detected in the recording.",
    "pdf_snore_pct": "Schnarchen % of TST",
    "pdf_sol": "Schlaf Onset Latency (SOL)",
    "pdf_spont_arousals": "Spontaneous Arousals",
    "pdf_technician": "Technician",
    "pdf_therapy": "Therapy",
    "pdf_time_axis": "Zeit (Stunden)",
    "pdf_time_below90": "Zeit < 90%",
    "pdf_titration_cpap": "Titration Bericht — CPAP",
    "pdf_titration_mra": "Titration Bericht — MAD",
    "pdf_total_events": "Gesamt Events (AH)",
    "pdf_total_lms": "Gesamt LMs",
    "pdf_value": "Wert",
    "pdf_verified_by": "This Bericht was verified by {role} {name}.",
    "pdf_year": "years",
    "per_channel_summary": "Per channel summary",
    "per_event_table": "Per-event table",
    "phone": "Phone",
    "physician": "Arzt",
    "plm_criteria": "LM ≥8μV, 0.5-10s duration | PLM series ≥4 LMs, 5-90s interval | Resp-associated LMs excluded | Schlaf epochs only | PLMI ≥15/h = clinically significant",
    "plm_details": "PLM Details (AASM)",
    "plm_in_series": "PLMs (in series)",
    "pneumo_channels": "Respiratorisch & PLM channels",
    "pneumo_channels_desc": "Auto-detected (★). Correct if needed.",
    "processing_failed": "Failed to start processing. Please try again.",
    "processing_started": "Verarbeitung started!",
    "profile_sensitive": "Sensitive (RPSGT) — closer to human scoring",
    "profile_standard": "Standard (AASM) — recommended",
    "profile_strict": "Strict (machine) — AASM exact, no smoothing",
    "pw_placeholder": "Min. 8 chars, A-Z, 0-9",
    "rate_limited": "Too many requests. Please wait and try again.",
    "reanalyze": "Re-analyze",
    "reanalyze_started": "Re-Analyse started. Select channels and patient data.",
    "recommended_staging": "Recommended for YASA staging",
    "recording_date": "Aufnahme date",
    "recording_time": "Aufnahme time",
    "recording_time_label": "Aufnahme time",
    "relative_power_per_stage": "Relative power per Schlaf stage",
    "rem_latency": "REM latency",
    "rem_periods": "REM periods",
    "report": "Bericht",
    "report_header": "Bericht settings",
    "report_saved": "Bericht saved",
    "reports": "Berichts",
    "reset": "Reset",
    "reset_password": "Reset password",
    "reset_to_ai": "Reset to AI",
    "reset_to_auto": "Reset to automatic",
    "resp_associated": "Resp-associated (excluded)",
    "respiratory_analysis": "Respiratorisch Analyse",
    "respiratory_arousals": "Respiratorisch arousals",
    "respiratory_summary": "Respiratorisch summary",
    "results": "Ergebnisse",
    "role": "Role",
    "role_admin": "Admin",
    "role_desc_admin": "Full access, all sites, user management",
    "role_desc_full": "user — upload & analyze (own site) | site manager — all studies of own site, create users | admin — everything: all sites, user & site management",
    "role_desc_site": "Manages one site: own patients and users",
    "role_desc_user": "Hochladen + own results + site results",
    "role_site": "Site manager",
    "role_user": "User",
    "rpt_arousals": "Arousals",
    "rpt_disclaimer": "This Bericht is generated by YASAFlaskified (screening tool). Neint for clinical diagnosis without verification by a Schlaf specialist.",
    "rpt_patient_info": "Patient info (from EDF)",
    "rpt_plm": "Periodic limb movements",
    "rpt_quality": "Signal quality",
    "rpt_respiratory": "Respiratorisch Analyse",
    "rpt_sec0a": "Aufnahme — Kanals",
    "rpt_sec0b": "Visual Overview",
    "rpt_sec1": "1  Schlaf Architecture  (AASM)",
    "rpt_sec10": "10  Periodic Limb Movements (PLM)",
    "rpt_sec10b": "10b  Ronchopathy (Schnarchen Analyse)",
    "rpt_sec11": "11  Conclusion",
    "rpt_sec2": "2  Schlaf Zykluss (NREM-REM)",
    "rpt_sec3": "3  Schlaf Spindels",
    "rpt_sec4": "4  Slow Waves",
    "rpt_sec5": "5  REM Detection",
    "rpt_sec6": "6  Spectral Band Power",
    "rpt_sec7": "7  Artifacts",
    "rpt_sec7b": "7b  Signal Qualität & Konfidenz Review",
    "rpt_sec8": "8  Respiratorisch Analyse  (AASM Rule 1A + 1B)",
    "rpt_sec8b": "8b  Arousals & RERA  (AASM 3.9)",
    "rpt_sec8c": "8c  Breath-by-Breath Analyse",
    "rpt_sec8d": "8d  Flow Reduction Without Criteria (FRI)",
    "rpt_sec8e": "8e  Signal Examples",
    "rpt_sec9": "9  SpO2 Analyse",
    "rpt_sleep_architecture": "Schlaf architecture",
    "rpt_spo2": "Oxygen saturation",
    "rpt_verified": "Verified by {role} {name}.",
    "rule1b_reinstated": "Rule 1B reinstatements (arousal)",
    "save": "Speichern",
    "save_and_regenerate": "Speichern & regenerate PDF",
    "save_conclusion": "Speichern conclusion & generate PDF",
    "save_scoring": "Speichern & regenerate Bericht",
    "score_editor_help": "Click an epoch or use keyboard: W N1 N2 N3 R  |  Ctrl+Z = undo",
    "score_editor_title": "Manual scoring — epoch by epoch",
    "scorer": "Scorer",
    "scorer_label": "Scorer",
    "scoring_profile_hint": "Controls thresholds for Hypopnoe detection, SpO2 coupling, and signal smoothing.",
    "scoring_profile_title": "Scoring Profil",
    "scoring_saved": "Scoring saved. Bericht is being recalculated.",
    "search": "Search...",
    "search_placeholder": "Search by name, ID, date…",
    "select_all": "Select all",
    "select_diagnosis": "Select a diagnosis to add",
    "select_file": "Select file",
    "session_expired": "Session expired. Please try again.",
    "set_role": "Set role",
    "settings": "Einstellungen",
    "sev_mild": "Leicht",
    "sev_moderate": "Mittelgradig",
    "sev_normal": "Neinrmal",
    "sev_severe": "Schwer",
    "severe_osa": "Schwer OSA",
    "severity": "Severity",
    "severity_mild_label": "Leicht (AHI 5-15)",
    "severity_moderate_label": "Mittelgradig (AHI 15-30)",
    "severity_normal_label": "Neinrmal (AHI < 5)",
    "severity_severe_label": "Schwer (AHI > 30)",
    "sex": "Sex",
    "sex_f": "Female",
    "sex_label": "Sex",
    "sex_m": "Male",
    "sign_in": "Sign in",
    "site": "Site / Hospital",
    "site_added": "Site added.",
    "site_address": "Address",
    "site_created": "Site created.",
    "site_deleted": "Site deleted.",
    "site_email": "E-mail",
    "site_has_users": "Site still has users.",
    "site_language": "Default language",
    "site_logo": "Logo (path)",
    "site_management": "Site management",
    "site_name": "Site name",
    "site_name_required": "Site name is required.",
    "site_only_users": "As a site manager, you can only create users for your own site.",
    "site_phone": "Phone",
    "site_updated": "Site updated.",
    "site_url": "Website",
    "sites": "Sites",
    "sleep_analysis_report": "Schlaf Analyse Bericht",
    "sleep_cycles_detected": "Schlaf cycles detected",
    "sleep_efficiency": "Schlaf efficiency",
    "sleep_onset_latency": "Schlaf onset latency",
    "sleep_statistics": "Schlaf statistics",
    "slow_waves_detected": "slow waves detected",
    "spindles_detected": "spindles detected",
    "spo2_details": "SpO2 details",
    "spo2_mean": "Mean SpO2",
    "spo2_min": "Min. SpO2",
    "spontaneous_arousals": "Spontaneous arousals",
    "stage": "Stadium",
    "stage_n1": "Stadium N1",
    "stage_n2": "Stadium N2",
    "stage_n3": "Stadium N3",
    "stage_rem": "REM",
    "stage_w": "Stadium W",
    "standard_conclusions": "Standard conclusions",
    "standard_diagnosis": "Standard diagnosis",
    "start_analysis": "Start Analyse",
    "start_first_analysis": "Start first Analyse",
    "start_s": "Start (s)",
    "start_upload": "Start upload",
    "status": "Status",
    "status_busy": "In progress",
    "status_done": "Done",
    "status_failed": "Failed",
    "status_ready": "Ready",
    "status_running": "Running",
    "studies_found": "studies found",
    "study_deleted": "Study and all associated files deleted.",
    "study_diagnostic_psg": "Diagnostic PSG",
    "study_not_found": "Study not found.",
    "study_titration_pg_cpap": "Titration polygraphy — CPAP",
    "study_titration_pg_mra": "Titration polygraphy — MAD",
    "study_titration_psg_cpap": "Titration PSG — CPAP",
    "study_type_hint": "Polygraphy: no Schlaf staging (REI instead of AHI). Titration: residual events under therapy.",
    "study_type_title": "Study type",
    "success": "Success",
    "tab_artifacts": "Artifacts",
    "tab_bandpower": "Band power",
    "tab_cycles": "Zykluss",
    "tab_heart": "Herz",
    "tab_hypnogram": "Hypnogram",
    "tab_plm": "PLM",
    "tab_rem": "REM",
    "tab_respiratory": "Respiratorisch",
    "tab_slow_waves": "Slow waves",
    "tab_spindles": "Spindels",
    "tab_spo2": "SpO2",
    "tab_statistics": "Statistics",
    "time_below_90": "Zeit < 90%",
    "time_min": "Zeit (min)",
    "too_many_requests": "Too many requests. Please wait.",
    "total_events": "Gesamt events",
    "total_lms": "Gesamt LMs",
    "total_rem_duration": "Gesamt REM duration",
    "total_sleep_time": "Gesamt Schlaf time (TST)",
    "total_studies": "Gesamt studies",
    "type": "Type",
    "unknown_error": "Unknown error.",
    "upload": "Hochladen",
    "upload_analysis_start": "Analyse started",
    "upload_async": "Async processing",
    "upload_btn": "Hochladen & analyze",
    "upload_btn_analyzing": "Analyzing EDF...",
    "upload_btn_uploading": "Hochladening...",
    "upload_channels": "Kanals",
    "upload_channels_found": "channels found",
    "upload_complete": "Hochladen complete.",
    "upload_drop": "Polysomnography recording from any PSG device",
    "upload_duration": "Dauer",
    "upload_net_error": "Network error at chunk",
    "upload_parse": "Analyzing EDF channels...",
    "upload_parse_error": "Parse error",
    "upload_parse_fail": "Parse failed",
    "upload_ready": "MB — ready to upload",
    "upload_srv_error": "Server error at chunk",
    "upload_started": "Hochladen started",
    "upload_step1": "Step 1 of 3 · EDF Hochladen",
    "upload_subtitle": "European Data Format polysomnography · max 500 MB",
    "upload_title": "Hochladen your recording",
    "upload_to_start": "Hochladen an EDF file to get started.",
    "upload_uploading": "Hochladening...",
    "uploading": "Hochladening…",
    "url": "Website",
    "user_created": "User created.",
    "user_deleted": "User deleted.",
    "user_exists": "Username already exists.",
    "user_management": "User management",
    "user_placeholder": "e.g. j.smith",
    "user_updated": "User updated.",
    "username": "Username",
    "username_exists": "Username already exists.",
    "users": "Users",
    "value": "Wert",
    "verified_by": "Verified by",
    "view_pdf": "View PDF",
    "view_report": "View Bericht",
    "view_signals": "View signals",
    "waiting_for_worker": "Waiting for worker…",
    "warning": "Warnung",
    "waso": "WASO",
    "weight": "Weight",
    "weight_kg": "Weight (kg)",
    "worker_unavailable": "Could not start Analyse. Check the worker service.",
    "wrong_password": "Current password is incorrect.",
    "you": "you",
    "zoom_fit": "Full study",
    "zoom_in": "Zoom in",
    "zoom_out": "Zoom out",
}

for _k, _v in _DE_PATCH.items():
    if _k in TRANSLATIONS and "de" not in TRANSLATIONS[_k]:
        TRANSLATIONS[_k]["de"] = _v


# v0.8.37: Complete PDF report multilingual keys
_PDF_V027 = {
    "pdf_artifact_count": {
        "nl": "epochs als artefact",
        "fr": "époques comme artefact",
        "en": "epochs as artefact",
        "de": "Epochen als Artefakt",
    },
    "pdf_central": {
        "nl": "Centraal",
        "fr": "Central",
        "en": "Central",
        "de": "Zentral",
    },
    "pdf_conf_warning": {
        "nl": "van epochs met confidence <70%. Manuele verificatie aanbevolen.",
        "fr": "des époques avec confiance <70%. Vérification manuelle recommandée.",
        "en": "of epochs with confidence <70%. Manual verification recommended.",
        "de": "der Epochen mit Konfidenz <70%. Manuelle Verifizierung empfohlen.",
    },
    "pdf_corrected": {
        "nl": "Gecorrigeerd",
        "fr": "Corrigé",
        "en": "Corrected",
        "de": "Korrigiert",
    },
    "pdf_disc_informative": {
        "nl": "Deze correcties zijn informatief. De officiële AHI en OAHI blijven AASM-conform (alle events). Bovenstaande indices helpen de clinicus de robuustheid van de scoring te beoordelen.",
        "fr": "Ces corrections sont informatives. L'AHI et l'OAHI officiels restent conformes à l'AASM (tous les événements). Les indices ci-dessus aident le clinicien à évaluer la robustesse du scoring.",
        "en": "These corrections are informative. The official AHI and OAHI remain AASM-compliant (all events). The above indices help the clinician assess scoring robustness.",
        "de": "Diese Korrekturen sind informativ. Die offiziellen AHI und OAHI bleiben AASM-konform (alle Ereignisse). Die obigen Indizes helfen dem Kliniker, die Robustheit des Scorings zu bewerten.",
    },
    "pdf_ecg_fix_desc": {
        "nl": "Events herclassificeerd via ECG-afgeleide effort-analyse (Berry 2019)",
        "fr": "Événements reclassifiés via analyse d'effort dérivée de l'ECG (Berry 2019)",
        "en": "Events reclassified via ECG-derived effort analysis (Berry 2019)",
        "de": "Ereignisse über EKG-abgeleitete Effort-Analyse reklassifiziert (Berry 2019)",
    },
    "pdf_ecg_fix_name": {
        "nl": "ECG effort (TECG)",
        "fr": "Effort ECG (TECG)",
        "en": "ECG effort (TECG)",
        "de": "EKG-Effort (TECG)",
    },
    "pdf_fix1_desc": {
        "nl": "Hyperpnea recovery 30s uitgesloten uit basislijnberekening",
        "fr": "Récupération hyperpnée 30s exclue du calcul de base",
        "en": "Hyperpnea recovery 30s excluded from baseline calculation",
        "de": "Hyperpnoe-Erholung 30s aus Basislinienberechnung ausgeschlossen",
    },
    "pdf_fix1_name": {
        "nl": "Fix 1 — Post-apnea basislijn",
        "fr": "Fix 1 — Ligne de base post-apnée",
        "en": "Fix 1 — Post-apnea baseline",
        "de": "Fix 1 — Post-Apnoe-Basislinie",
    },
    "pdf_fix2_desc": {
        "nl": "Hypopneas waarvoor SpO2-nadir mogelijk van vorig event stamt",
        "fr": "Hypopnées dont le nadir SpO2 provient possiblement de l'événement précédent",
        "en": "Hypopneas where SpO2 nadir possibly originates from preceding event",
        "de": "Hypopnoen, bei denen SpO2-Nadir möglicherweise vom vorherigen Ereignis stammt",
    },
    "pdf_fix2_name": {
        "nl": "Fix 2 — SpO2 kruiscontaminatie",
        "fr": "Fix 2 — Contamination croisée SpO2",
        "en": "Fix 2 — SpO2 cross-contamination",
        "de": "Fix 2 — SpO2-Kreuzkontamination",
    },
    "pdf_fix3_desc": {
        "nl": "Events gemarkeerd als CSR-cyclus gerelateerd",
        "fr": "Événements marqués comme liés au cycle CSR",
        "en": "Events flagged as CSR cycle-related",
        "de": "Ereignisse als CSR-Zyklus-bezogen markiert",
    },
    "pdf_fix3_name": {
        "nl": "Fix 3 — Cheyne-Stokes events",
        "fr": "Fix 3 — Événements Cheyne-Stokes",
        "en": "Fix 3 — Cheyne-Stokes events",
        "de": "Fix 3 — Cheyne-Stokes-Ereignisse",
    },
    "pdf_fix4_name": {
        "nl": "Fix 4 — Lage confidence",
        "fr": "Fix 4 — Faible confiance",
        "en": "Fix 4 — Low confidence",
        "de": "Fix 4 — Niedrige Konfidenz",
    },
    "pdf_fix5_desc": {
        "nl": "Post-gap exclusie 15s na signaaluitval ≥10s",
        "fr": "Exclusion post-gap 15s après perte de signal ≥10s",
        "en": "Post-gap exclusion 15s after signal dropout ≥10s",
        "de": "Post-Gap-Ausschluss 15s nach Signalausfall ≥10s",
    },
    "pdf_fix5_name": {
        "nl": "Fix 5 — Artefact-flanken",
        "fr": "Fix 5 — Flancs d'artefact",
        "en": "Fix 5 — Artefact flanks",
        "de": "Fix 5 — Artefakt-Flanken",
    },
    "pdf_fix6_desc": {
        "nl": "Hypopneas met <20% reductie t.o.v. pre-event ademhaling",
        "fr": "Hypopnées avec <20% réduction vs respiration pré-événement",
        "en": "Hypopneas with <20% reduction vs pre-event breathing",
        "de": "Hypopnoen mit <20% Reduktion ggü. Prä-Event-Atmung",
    },
    "pdf_fix6_name": {
        "nl": "Fix 6 — Lokale basislijn",
        "fr": "Fix 6 — Ligne de base locale",
        "en": "Fix 6 — Local baseline",
        "de": "Fix 6 — Lokale Basislinie",
    },
    "pdf_grade_acceptable": {
        "nl": "Acceptabel",
        "fr": "Acceptable",
        "en": "Acceptable",
        "de": "Akzeptabel",
    },
    "pdf_grade_good": {
        "nl": "Goed",
        "fr": "Bon",
        "en": "Good",
        "de": "Gut",
    },
    "pdf_grade_poor": {
        "nl": "Slecht",
        "fr": "Mauvais",
        "en": "Poor",
        "de": "Schlecht",
    },
    "pdf_mixed": {
        "nl": "Gemengd",
        "fr": "Mixte",
        "en": "Mixed",
        "de": "Gemischt",
    },
    "pdf_no": {
        "nl": "Nee",
        "fr": "Non",
        "en": "No",
        "de": "Nein",
    },
    "pdf_obstructive": {
        "nl": "Obstructief",
        "fr": "Obstructif",
        "en": "Obstructive",
        "de": "Obstruktiv",
    },
    "pdf_phase": {
        "nl": "Fase",
        "fr": "Phase",
        "en": "Phase",
        "de": "Phase",
    },
    "pdf_prof_header": {
        "nl": "Profiel",
        "fr": "Profil",
        "en": "Profile",
        "de": "Profil",
    },
    "pdf_prof_hypopnea": {
        "nl": "Hypopnea",
        "fr": "Hypopnée",
        "en": "Hypopnea",
        "de": "Hypopnoe",
    },
    "pdf_prof_nadir": {
        "nl": "Nadir venster",
        "fr": "Fenêtre nadir",
        "en": "Nadir window",
        "de": "Nadir-Fenster",
    },
    "pdf_prof_peak": {
        "nl": "Piek detectie",
        "fr": "Détection pic",
        "en": "Peak detection",
        "de": "Peak-Erkennung",
    },
    "pdf_rejected": {
        "nl": "afgewezen",
        "fr": "rejetés",
        "en": "rejected",
        "de": "abgelehnt",
    },
    "pdf_rera_explanation": {
        "nl": "RERA = flow-reductie (≥30%, ≥10s) + arousal, zonder ≥3% desaturatie.",
        "fr": "RERA = réduction du flux (≥30%, ≥10s) + arousal, sans ≥3% désaturation.",
        "en": "RERA = flow reduction (≥30%, ≥10s) + arousal, without ≥3% desaturation.",
        "de": "RERA = Flussreduktion (≥30%, ≥10s) + Arousal, ohne ≥3% Desaturation.",
    },
    "pdf_sig_warning": {
        "nl": "kanalen onbruikbaar (amplitude < minimum). Staging en micro-architectuur kunnen afwijken.",
        "fr": "canaux inutilisables (amplitude < minimum). Le staging et la micro-architecture peuvent être affectés.",
        "en": "channels unusable (amplitude < minimum). Staging and micro-architecture may be affected.",
        "de": "Kanäle unbrauchbar (Amplitude < Minimum). Staging und Mikro-Architektur können abweichen.",
    },
    "pdf_spo2_averaging_warning": {
        "nl": "SpO2 samplerate < 0.33 Hz (>3s averaging) — ODI en desaturatie-detectie mogelijk onderschat (AASM: max 3s averaging).",
        "fr": "Fréquence d'échantillonnage SpO2 < 0.33 Hz (>3s moyennage) — ODI et détection de désaturation possiblement sous-estimés (AASM: max 3s moyennage).",
        "en": "SpO2 sample rate < 0.33 Hz (>3s averaging) — ODI and desaturation detection possibly underestimated (AASM: max 3s averaging).",
        "de": "SpO2-Abtastrate < 0.33 Hz (>3s Mittelung) — ODI und Desaturationserkennung möglicherweise unterschätzt (AASM: max 3s Mittelung).",
    },
    "pdf_title_pg": {
        "nl": "Polygrafie — Slaaprapport",
        "fr": "Polygraphie — Rapport de sommeil",
        "en": "Polygraphy — Sleep Report",
        "de": "Polygraphie — Schlafbericht",
    },
    "pdf_title_psg": {
        "nl": "Polysomnografie — Slaaprapport",
        "fr": "Polysomnographie — Rapport de sommeil",
        "en": "Polysomnography — Sleep Report",
        "de": "Polysomnographie — Schlafbericht",
    },
    "pdf_to_central": {
        "nl": "→ centraal",
        "fr": "→ central",
        "en": "→ central",
        "de": "→ zentral",
    },
    "pdf_yes": {
        "nl": "Ja",
        "fr": "Oui",
        "en": "Yes",
        "de": "Ja",
    },
}
TRANSLATIONS.update(_PDF_V027)

# v0.8.37: Final remaining PDF keys
_PDF_V027b = {
    "pdf_artifact_of": {
        "nl": "van",
        "fr": "de",
        "en": "of",
        "de": "von",
    },
    "pdf_epochs_as_artifact": {
        "nl": "epochs als artefact.",
        "fr": "époques comme artefact.",
        "en": "epochs as artefact.",
        "de": "Epochen als Artefakt.",
    },
    "pdf_rei_explanation": {
        "nl": "events per uur registratietijd (TIB) i.p.v. TST.",
        "fr": "événements par heure de temps d'enregistrement (TIB) au lieu de TST.",
        "en": "events per hour recording time (TIB) instead of TST.",
        "de": "Ereignisse pro Stunde Aufzeichnungszeit (TIB) statt TST.",
    },
    "pdf_slow_waves_detected": {
        "nl": "trage golven gedetecteerd.",
        "fr": "ondes lentes détectées.",
        "en": "slow waves detected.",
        "de": "langsame Wellen erkannt.",
    },
    "pdf_spindles_detected": {
        "nl": "spindels gedetecteerd (N1+N2).",
        "fr": "fuseaux détectés (N1+N2).",
        "en": "spindles detected (N1+N2).",
        "de": "Spindeln erkannt (N1+N2).",
    },
}
TRANSLATIONS.update(_PDF_V027b)

# ── v0.8.37: HR/ECG + SpO2/PLM i18n ─────────────────────────────────
_PDF_V030 = {
    "pdf_mean_spo2":      {"nl": "Gemiddelde SpO<sub>2</sub>", "fr": "SpO<sub>2</sub> moyenne", "en": "Mean SpO<sub>2</sub>", "de": "Mittlere SpO<sub>2</sub>"},
    "pdf_baseline_spo2":  {"nl": "Baseline SpO<sub>2</sub>",   "fr": "SpO<sub>2</sub> de base", "en": "Baseline SpO<sub>2</sub>", "de": "Baseline SpO<sub>2</sub>"},
    "pdf_min_spo2":       {"nl": "Minimale SpO<sub>2</sub>",   "fr": "SpO<sub>2</sub> minimale", "en": "Minimum SpO<sub>2</sub>", "de": "Minimale SpO<sub>2</sub>"},
    "pdf_mean_hr":        {"nl": "Gem. hartfrequentie", "fr": "FC moyenne",    "en": "Mean heart rate", "de": "Mittl. Herzfrequenz"},
    "pdf_min_hr":         {"nl": "Min. hartfrequentie", "fr": "FC minimale",   "en": "Min heart rate",  "de": "Min. Herzfrequenz"},
    "pdf_max_hr":         {"nl": "Max. hartfrequentie", "fr": "FC maximale",   "en": "Max heart rate",  "de": "Max. Herzfrequenz"},
    "pdf_bradycardia":    {"nl": "Bradycardie (<50)",   "fr": "Bradycardie (<50)", "en": "Bradycardia (<50)", "de": "Bradykardie (<50)"},
    "pdf_tachycardia":    {"nl": "Tachycardie (>100)",  "fr": "Tachycardie (>100)", "en": "Tachycardia (>100)", "de": "Tachykardie (>100)"},
    "pdf_ecg_hr_title":   {"nl": "ECG / Hartritme",     "fr": "ECG / Rythme cardiaque", "en": "ECG / Heart Rate", "de": "EKG / Herzfrequenz"},
    "pdf_lms_sleep":      {"nl": "LMs tijdens slaap",   "fr": "ML pendant le sommeil", "en": "LMs during sleep", "de": "LMs während Schlaf"},
    "pdf_resp_assoc":     {"nl": "Resp.-geassocieerd (excl.)", "fr": "Resp.-associés (excl.)", "en": "Resp.-associated (excl.)", "de": "Resp.-assoziiert (exkl.)"},
    "pdf_cycles_detected":{"nl": "NREM/REM-cycli gedetecteerd.", "fr": "cycles NREM/REM détectés.", "en": "NREM/REM cycles detected.", "de": "NREM/REM-Zyklen erkannt."},
    "pdf_transitions":    {"nl": "Stadiawissels", "fr": "Transitions", "en": "Stage transitions", "de": "Stadienwechsel"},
}
TRANSLATIONS.update(_PDF_V030)

# ── v0.8.37: Medatec-parity PDF sections + OSAS score ────────────────
_PDF_V036 = {
    # Position × stage cross-table
    "pdf_pos_stage_title": {
        "nl": "Respiratoire events per slaapstadium en lichaamshouding",
        "fr": "Événements respiratoires par stade de sommeil et position",
        "en": "Respiratory events by sleep stage and body position",
        "de": "Respiratorische Ereignisse nach Schlafstadium und Körperposition",
    },
    "NREM supine":      {"nl": "NREM ruglig",      "fr": "NREM dorsal",      "en": "NREM supine",      "de": "NREM Rückenlage"},
    "NREM non-supine":  {"nl": "NREM niet-ruglig", "fr": "NREM non-dorsal",  "en": "NREM non-supine",  "de": "NREM Nicht-Rückenlage"},
    "REM supine":       {"nl": "REM ruglig",       "fr": "REM dorsal",       "en": "REM supine",       "de": "REM Rückenlage"},
    "REM non-supine":   {"nl": "REM niet-ruglig",  "fr": "REM non-dorsal",   "en": "REM non-supine",   "de": "REM Nicht-Rückenlage"},
    "Sleep time (min)": {"nl": "Slaaptijd (min)",  "fr": "Temps de sommeil (min)", "en": "Sleep time (min)", "de": "Schlafzeit (min)"},
    "Respiratory events":{"nl": "Respiratoire events", "fr": "Événements respiratoires", "en": "Respiratory events", "de": "Respiratorische Ereignisse"},
    "Mean duration (s)":{"nl": "Gemiddelde duur (s)", "fr": "Durée moyenne (s)", "en": "Mean duration (s)", "de": "Mittlere Dauer (s)"},
    "Supine-dominant OSA": {
        "nl": "Ruglig-dominant OSAS",
        "fr": "SAOS à prédominance dorsale",
        "en": "Supine-dominant OSA",
        "de": "Rückenlage-dominantes OSAS",
    },
    "REM-dominant OSA": {
        "nl": "REM-dominant OSAS",
        "fr": "SAOS à prédominance REM",
        "en": "REM-dominant OSA",
        "de": "REM-dominantes OSAS",
    },
    "supine AHI":       {"nl": "ruglig-AHI",       "fr": "IAH dorsal",       "en": "supine AHI",       "de": "Rückenlage-AHI"},
    "non-supine AHI":   {"nl": "niet-ruglig-AHI",  "fr": "IAH non-dorsal",   "en": "non-supine AHI",   "de": "Nicht-Rückenlage-AHI"},
    "Positional therapy may be considered.": {
        "nl": "Positietherapie kan overwogen worden.",
        "fr": "La thérapie positionnelle peut être envisagée.",
        "en": "Positional therapy may be considered.",
        "de": "Eine Lagetherapie kann erwogen werden.",
    },
    "min REM sleep":    {"nl": "min REM-slaap",    "fr": "min sommeil REM",  "en": "min REM sleep",    "de": "min REM-Schlaf"},
    # Snoring cross-table
    "Snoring by sleep stage and body position": {
        "nl": "Snurken per slaapstadium en lichaamshouding",
        "fr": "Ronflement par stade de sommeil et position",
        "en": "Snoring by sleep stage and body position",
        "de": "Schnarchen nach Schlafstadium und Körperposition",
    },
    "Supine":           {"nl": "Ruglig",           "fr": "Dorsal",           "en": "Supine",           "de": "Rückenlage"},
    "Non-supine":       {"nl": "Niet-ruglig",      "fr": "Non-dorsal",      "en": "Non-supine",       "de": "Nicht-Rückenlage"},
    # Stage latencies
    "Sleep latencies":  {"nl": "Slaaplatentietijden", "fr": "Latences de sommeil", "en": "Sleep latencies", "de": "Schlaflatenzen"},
    "Stage":            {"nl": "Stadium",           "fr": "Stade",            "en": "Stage",            "de": "Stadium"},
    "Latency (min)":    {"nl": "Latentie (min)",   "fr": "Latence (min)",    "en": "Latency (min)",    "de": "Latenz (min)"},
    # SpO2 bands
    "Time in saturation bands": {
        "nl": "Tijd in saturatiebanden",
        "fr": "Temps par bande de saturation",
        "en": "Time in saturation bands",
        "de": "Zeit in Sättigungsbändern",
    },
    "SpO₂ range":      {"nl": "SpO₂-bereik",      "fr": "Plage SpO₂",      "en": "SpO₂ range",      "de": "SpO₂-Bereich"},
    "Duration (min)":   {"nl": "Duur (min)",        "fr": "Durée (min)",      "en": "Duration (min)",   "de": "Dauer (min)"},
    "% of recording":   {"nl": "% van opname",      "fr": "% de l'enregistrement", "en": "% of recording", "de": "% der Aufzeichnung"},
    # ESS + OSAS score
    "Symptom assessment and severity profile": {
        "nl": "Symptoomanalyse en ernstprofiel",
        "fr": "Évaluation des symptômes et profil de sévérité",
        "en": "Symptom assessment and severity profile",
        "de": "Symptomanalyse und Schweregradprofil",
    },
    "OSAS severity profile": {"nl": "OSAS-ernstprofiel", "fr": "Profil de sévérité SAOS", "en": "OSAS severity profile", "de": "OSAS-Schweregradprofil"},
    "OSAS code":        {"nl": "OSAS-code",        "fr": "Code SAOS",        "en": "OSAS code",        "de": "OSAS-Code"},
    "Dimension":        {"nl": "Dimensie",          "fr": "Dimension",        "en": "Dimension",        "de": "Dimension"},
    "Metric":           {"nl": "Maat",              "fr": "Métrique",         "en": "Metric",           "de": "Metrik"},
    "Value":            {"nl": "Waarde",            "fr": "Valeur",           "en": "Value",            "de": "Wert"},
    "Grade (0-3)":      {"nl": "Graad (0-3)",       "fr": "Grade (0-3)",      "en": "Grade (0-3)",      "de": "Grad (0-3)"},
    "Oxygen deficit":   {"nl": "Zuurstoftekort",    "fr": "Déficit en oxygène", "en": "Oxygen deficit",  "de": "Sauerstoffdefizit"},
    "Sleep disruption": {"nl": "Slaapfragmentatie", "fr": "Fragmentation du sommeil", "en": "Sleep disruption", "de": "Schlaffragmentierung"},
    "Apnea frequency":  {"nl": "Apneufrequentie",  "fr": "Fréquence des apnées", "en": "Apnea frequency", "de": "Apnoe-Frequenz"},
    "Symptoms":         {"nl": "Symptomen",         "fr": "Symptômes",        "en": "Symptoms",         "de": "Symptome"},
    "Hypoxic burden":   {"nl": "Hypoxische last",   "fr": "Charge hypoxique", "en": "Hypoxic burden",   "de": "Hypoxische Last"},
    "Arousal index":    {"nl": "Arousal-index",     "fr": "Index d'éveils",   "en": "Arousal index",    "de": "Arousal-Index"},
    "total":            {"nl": "totaal",            "fr": "total",            "en": "total",            "de": "gesamt"},
    "not provided":     {"nl": "niet ingevuld",     "fr": "non renseigné",    "en": "not provided",     "de": "nicht angegeben"},
    "ESS not provided": {"nl": "ESS niet ingevuld", "fr": "ESS non renseigné", "en": "ESS not provided", "de": "ESS nicht angegeben"},
    "normal":           {"nl": "normaal",           "fr": "normal",           "en": "normal",           "de": "normal"},
    "mild sleepiness":  {"nl": "lichte slaperigheid", "fr": "somnolence légère", "en": "mild sleepiness", "de": "leichte Schläfrigkeit"},
    "moderate sleepiness": {"nl": "matige slaperigheid", "fr": "somnolence modérée", "en": "moderate sleepiness", "de": "mäßige Schläfrigkeit"},
    "severe sleepiness":{"nl": "ernstige slaperigheid", "fr": "somnolence sévère", "en": "severe sleepiness", "de": "schwere Schläfrigkeit"},
    "positional":       {"nl": "positioneel",       "fr": "positionnel",      "en": "positional",       "de": "lageabhängig"},
    "REM-dominant":     {"nl": "REM-dominant",      "fr": "à prédominance REM", "en": "REM-dominant",   "de": "REM-dominant"},
    "central component":{"nl": "centraal component", "fr": "composante centrale", "en": "central component", "de": "zentrale Komponente"},
    # Conclusion section
    "Clinical assessment": {
        "nl": "Klinische beoordeling",
        "fr": "Évaluation clinique",
        "en": "Clinical assessment",
        "de": "Klinische Beurteilung",
    },
    "Overall assessment": {"nl": "Globale beoordeling", "fr": "Évaluation globale", "en": "Overall assessment", "de": "Gesamtbeurteilung"},
    "Conclusion":       {"nl": "Besluit",           "fr": "Conclusion",       "en": "Conclusion",       "de": "Schlussfolgerung"},
    "Recommendations":  {"nl": "Advies",            "fr": "Recommandations",  "en": "Recommendations",  "de": "Empfehlungen"},
    "Physician signature": {"nl": "Handtekening arts", "fr": "Signature du médecin", "en": "Physician signature", "de": "Unterschrift Arzt"},
    "Date":             {"nl": "Datum",             "fr": "Date",             "en": "Date",             "de": "Datum"},
    # Clinical input fields (v0.8.37)
    "indication":       {"nl": "Indicatie",          "fr": "Indication",       "en": "Indication",       "de": "Indikation"},
    "indication_placeholder": {
        "nl": "bv. slaapapneusyndroom",
        "fr": "p.ex. syndrome d'apnées du sommeil",
        "en": "e.g. sleep apnea syndrome",
        "de": "z.B. Schlafapnoe-Syndrom",
    },
    "referring_physician": {"nl": "Aanvrager",       "fr": "Médecin référent", "en": "Referring physician", "de": "Überweisender Arzt"},
    "pdf_indication":   {"nl": "Indicatie",          "fr": "Indication",       "en": "Indication",       "de": "Indikation"},
    "pdf_referring":    {"nl": "Aanvrager",          "fr": "Référent",         "en": "Referring",        "de": "Überweiser"},
}
TRANSLATIONS.update(_PDF_V036)

# v0.13.0: phenotype flags (POSA / REM-predominant) + ventilatory burden
_PDF_PHENO_VB = {
    "pdf_ventilatory_burden": {"nl": "Ventilatory burden", "fr": "Charge ventilatoire",
                               "en": "Ventilatory burden", "de": "Ventilatorische Last"},
    "pdf_pheno_hdr":  {"nl": "Klinische fenotypes", "fr": "Phénotypes cliniques",
                       "en": "Clinical phenotypes", "de": "Klinische Phänotypen"},
    "pdf_pheno_posa": {"nl": "Positioneel OSAS (POSA)", "fr": "SAOS positionnel (POSA)",
                       "en": "Positional OSA (POSA)", "de": "Lageabhängige OSA (POSA)"},
    "pdf_pheno_rem":  {"nl": "REM-predominant OSAS", "fr": "SAOS à prédominance REM",
                       "en": "REM-predominant OSA", "de": "REM-prädominante OSA"},
    "pdf_pheno_yes":  {"nl": "ja", "fr": "oui", "en": "yes", "de": "ja"},
    "pdf_pheno_no":   {"nl": "nee", "fr": "non", "en": "no", "de": "nein"},
    "pdf_pheno_posa_therapy": {"nl": "kandidaat voor positietherapie",
                               "fr": "candidat à la thérapie positionnelle",
                               "en": "positional-therapy candidate",
                               "de": "Kandidat für Lagetherapie"},
}
TRANSLATIONS.update(_PDF_PHENO_VB)

# v0.15.0 — AASM v3 clinician-report enrichments (dual AHI, aetiology, flags, conclusion)
_PDF_AASM_V3 = {
    "pdf_severity": {"nl": "Ernst", "fr": "Sévérité", "en": "Severity", "de": "Schweregrad"},
    "pdf_ahi_dual_hdr": {
        "nl": "AHI volgens hypopneu-criterium (AASM v3)",
        "fr": "IAH selon le critère d'hypopnée (AASM v3)",
        "en": "AHI by hypopnea criterion (AASM v3)",
        "de": "AHI nach Hypopnoe-Kriterium (AASM v3)"},
    "pdf_ahi_rule1a": {
        "nl": "Regel 1A — ≥30% flow + (≥3% desat óf arousal)",
        "fr": "Règle 1A — ≥30% débit + (≥3% désat ou micro-éveil)",
        "en": "Rule 1A — ≥30% flow + (≥3% desat or arousal)",
        "de": "Regel 1A — ≥30% Fluss + (≥3% Desat oder Arousal)"},
    "pdf_ahi_rule1b": {
        "nl": "Regel 1B / CMS — ≥30% flow + ≥4% desat",
        "fr": "Règle 1B / CMS — ≥30% débit + ≥4% désat",
        "en": "Rule 1B / CMS — ≥30% flow + ≥4% desat",
        "de": "Regel 1B / CMS — ≥30% Fluss + ≥4% Desat"},
    "pdf_ahi_ref_scale": {
        "nl": "AHI-ernst: &lt;5 normaal · 5–15 mild · 15–30 matig · &gt;30 ernstig",
        "fr": "Sévérité IAH : &lt;5 normal · 5–15 léger · 15–30 modéré · &gt;30 sévère",
        "en": "AHI severity: &lt;5 normal · 5–15 mild · 15–30 moderate · &gt;30 severe",
        "de": "AHI-Schweregrad: &lt;5 normal · 5–15 leicht · 15–30 mittel · &gt;30 schwer"},
    "pdf_resp_arousal_index": {
        "nl": "Respiratoire arousal-index", "fr": "Index de micro-éveils respiratoires",
        "en": "Respiratory arousal index", "de": "Respiratorischer Arousal-Index"},
    "pdf_spont_arousal_index": {
        "nl": "Spontane arousal-index", "fr": "Index de micro-éveils spontanés",
        "en": "Spontaneous arousal index", "de": "Spontaner Arousal-Index"},
    "pdf_plm_arousal_index": {
        "nl": "PLM arousal-index", "fr": "Index de micro-éveils PLM",
        "en": "PLM arousal index", "de": "PLM-Arousal-Index"},
    "pdf_arousal_ref": {"nl": "&lt; 10–15/u", "fr": "&lt; 10–15/h",
                        "en": "&lt; 10–15/h", "de": "&lt; 10–15/h"},
    "pdf_vb_experimental": {
        "nl": "(experimenteel — schaal nog te kalibreren)",
        "fr": "(expérimental — échelle à calibrer)",
        "en": "(experimental — scale not yet calibrated)",
        "de": "(experimentell — Skala noch zu kalibrieren)"},
    # Auto conclusion (B1)
    "pdf_concl_auto_hdr": {
        "nl": "Geautomatiseerde samenvatting (ter info — besluit door de arts)",
        "fr": "Résumé automatisé (à titre indicatif — conclusion par le médecin)",
        "en": "Automated summary (informational — conclusion by the physician)",
        "de": "Automatische Zusammenfassung (informativ — Beurteilung durch den Arzt)"},
    "pdf_concl_none": {
        "nl": "Geen significante slaapapneu (AHI &lt; 5/u).",
        "fr": "Pas d'apnée du sommeil significative (IAH &lt; 5/h).",
        "en": "No significant sleep apnea (AHI &lt; 5/h).",
        "de": "Keine signifikante Schlafapnoe (AHI &lt; 5/h)."},
    "pdf_concl_positional": {"nl": "positioneel", "fr": "positionnel",
                             "en": "positional", "de": "lageabhängig"},
    "pdf_concl_rem": {"nl": "REM-predominant", "fr": "à prédominance REM",
                      "en": "REM-predominant", "de": "REM-prädominant"},
    "pdf_concl_central": {"nl": "met centrale component", "fr": "avec composante centrale",
                          "en": "with a central component", "de": "mit zentraler Komponente"},
    "pdf_concl_hypoxemia": {"nl": "significante nachtelijke hypoxemie",
                            "fr": "hypoxémie nocturne significative",
                            "en": "significant nocturnal hypoxemia",
                            "de": "signifikante nächtliche Hypoxämie"},
    # Clinical flags (B5)
    "pdf_flags_hdr": {
        "nl": "Aandachtspunten (beschrijvend — geen medisch advies)",
        "fr": "Points d'attention (descriptif — pas un avis médical)",
        "en": "Points of attention (descriptive — not medical advice)",
        "de": "Aufmerksamkeitspunkte (beschreibend — keine medizinische Beratung)"},
    "pdf_flag_positional": {
        "nl": "Positioneel OSAS — kandidaat voor positietherapie",
        "fr": "SAOS positionnel — candidat à la thérapie positionnelle",
        "en": "Positional OSA — positional-therapy candidate",
        "de": "Lageabhängige OSA — Kandidat für Lagetherapie"},
    "pdf_flag_rem": {"nl": "REM-predominant OSAS", "fr": "SAOS à prédominance REM",
                     "en": "REM-predominant OSA", "de": "REM-prädominante OSA"},
    "pdf_flag_central": {"nl": "Centrale component aanwezig",
                         "fr": "Composante centrale présente",
                         "en": "Central component present",
                         "de": "Zentrale Komponente vorhanden"},
    "pdf_flag_hypoxemia": {
        "nl": "Significante nachtelijke hypoxemie (T90 {pct}%)",
        "fr": "Hypoxémie nocturne significative (T90 {pct}%)",
        "en": "Significant nocturnal hypoxemia (T90 {pct}%)",
        "de": "Signifikante nächtliche Hypoxämie (T90 {pct}%)"},
    # Het dual-sensor algoritme is gevraagd maar er was maar een
    # flowkanaal. De analyse levert wel een resultaat, maar niet het
    # algoritme dat de gebruiker koos - en dat hoort hij te weten.
    # Corroboratiekolommen: per eventtype hoeveel apneus door BEIDE
    # flowsensoren gezien zijn, en hoeveel maar door een. Alleen
    # getoond wanneer het dual-sensor algoritme gedraaid heeft.
    "pdf_corrob_both":  {"nl": "beide\nsensoren", "fr": "deux\ncapteurs", "en": "both\nsensors", "de": "beide\nSensoren"},
    "pdf_corrob_therm": {"nl": "alleen\nthermistor", "fr": "thermistance\nseule", "en": "thermistor\nonly", "de": "nur\nThermistor"},
    "pdf_corrob_press": {"nl": "alleen\nneusdruk", "fr": "pression\nseule", "en": "pressure\nonly", "de": "nur\nNasendruck"},
    "pdf_corrob_note":  {
        "nl": "Apneus zijn op beide flowsensoren gedetecteerd en ontdubbeld op overlap. Een event dat maar \u00e9\u00e9n sensor ziet wordt behouden, niet afgewezen.",
        "fr": "Les apn\u00e9es sont d\u00e9tect\u00e9es sur les deux capteurs de flux et d\u00e9doublonn\u00e9es par recouvrement. Un \u00e9v\u00e9nement vu par un seul capteur est conserv\u00e9, non rejet\u00e9.",
        "en": "Apneas are detected on both flow sensors and de-duplicated on overlap. An event seen by only one sensor is kept, not rejected.",
        "de": "Apnoen werden auf beiden Flusssensoren erkannt und bei \u00dcberlappung entdoppelt. Ein Ereignis, das nur ein Sensor sieht, bleibt erhalten und wird nicht verworfen.",
    },
    "pdf_flag_dual_fallback": {
        "nl": "Dual-sensor scoring gevraagd maar niet uitgevoerd: slechts \u00e9\u00e9n flowkanaal beschikbaar ({channel}). Apneus en hypopnees zijn beide op dat kanaal gescoord.",
        "fr": "Scoring double capteur demand\u00e9 mais non effectu\u00e9 : un seul canal de flux disponible ({channel}). Apn\u00e9es et hypopn\u00e9es ont toutes deux \u00e9t\u00e9 scor\u00e9es sur ce canal.",
        "en": "Dual-sensor scoring requested but not performed: only one flow channel available ({channel}). Apneas and hypopneas were both scored on that channel.",
        "de": "Dual-Sensor-Scoring angefordert, aber nicht durchgef\u00fchrt: nur ein Flusskanal verf\u00fcgbar ({channel}). Apnoen und Hypopnoen wurden beide auf diesem Kanal gescort.",
    },
    # Kanalen die de gebruiker koos maar die niet in het EDF zitten. Dit
    # stond tot v0.34.1 alleen in de workerlog; de arousal-regressie van
    # v0.27.0 bleef daardoor maanden onzichtbaar.
    # Te weinig slaap in een houding om er een index over te geven. psgscoring
    # gaf hier eerder een deling zonder ondergrens: één event in 0,5 min ruglig
    # leverde "AHI Supine 120,0/u", in dezelfde tabel als de echte indices.
    # Drie aandachtspunten uit de twee motiverende AZORG-rapporten.
    # Beschrijvend, geen advies -- zelfde stijl als de bestaande vlaggen.
    "pdf_flag_desat_discrepancy": {
        "nl": "Desaturatielast disproportioneel t.o.v. de gescoorde events (ODI3 {odi}/u bij AHI {ahi}/u, T90 {t90}%) — beoordeel de ruwe tracing",
        "fr": "Charge de désaturation disproportionnée par rapport aux événements scorés (IDO3 {odi}/h pour un IAH {ahi}/h, T90 {t90}%) — examinez le tracé brut",
        "en": "Desaturation burden disproportionate to the scored events (ODI3 {odi}/h at AHI {ahi}/h, T90 {t90}%) — review the raw tracing",
        "de": "Entsättigungslast unverhältnismäßig zu den gescorten Ereignissen (ODI3 {odi}/h bei AHI {ahi}/h, T90 {t90}%) — Rohsignal beurteilen"},
    "pdf_flag_arousal_implausible": {
        "nl": "Arousal-index onwaarschijnlijk laag t.o.v. de respiratoire eventfrequentie ({ai}/u bij AHI {ahi}/u) — controleer de arousaldetectie",
        "fr": "Index de micro-éveils improbablement bas par rapport à la fréquence des événements respiratoires ({ai}/h pour un IAH {ahi}/h) — vérifiez la détection des micro-éveils",
        "en": "Arousal index implausibly low relative to the respiratory event rate ({ai}/h at AHI {ahi}/h) — check the arousal detection",
        "de": "Arousal-Index unplausibel niedrig im Verhältnis zur respiratorischen Ereignisrate ({ai}/h bei AHI {ahi}/h) — Arousal-Erkennung prüfen"},
    "pdf_flag_bradycardia_mean": {
        "nl": "Gemiddelde hartfrequentie {hr} bpm — onder de referentie 60–100",
        "fr": "Fréquence cardiaque moyenne {hr} bpm — sous la référence 60–100",
        "en": "Mean heart rate {hr} bpm — below the 60–100 reference",
        "de": "Mittlere Herzfrequenz {hr} bpm — unter der Referenz 60–100"},
    "pdf_pos_too_short": {
        "nl": "— ({min} min, < {drempel})",
        "fr": "— ({min} min, < {drempel})",
        "en": "— ({min} min, < {drempel})",
        "de": "— ({min} min, < {drempel})"},
    "pdf_warn_emg_missing": {
        "nl": "Geen kin-EMG in dit EDF-bestand. REM-arousals zijn zonder kin-EMG niet AASM-conform scoorbaar en de ML-arousalstap is overgeslagen; de arousal-index komt uit de regelgebaseerde detectie.",
        "fr": "Pas d'EMG mentonnier dans ce fichier EDF. Sans EMG mentonnier, les micro-éveils en REM ne sont pas scorables selon l'AASM et l'étape d'arousal ML a été omise ; l'index de micro-éveils provient de la détection par règles.",
        "en": "No chin EMG in this EDF file. Without chin EMG, REM arousals are not AASM-conformly scorable and the ML arousal step was skipped; the arousal index comes from the rule-based detector.",
        "de": "Kein Kinn-EMG in dieser EDF-Datei. Ohne Kinn-EMG sind REM-Arousals nicht AASM-konform scorbar und der ML-Arousal-Schritt wurde übersprungen; der Arousal-Index stammt aus der regelbasierten Erkennung.",
    },
    "pdf_warn_eog_missing": {
        "nl": "Geen EOG in dit EDF-bestand. De slaapstadiëring draait zonder oogbewegingen en is daardoor minder betrouwbaar.",
        "fr": "Pas d'EOG dans ce fichier EDF. La stadification du sommeil s'effectue sans mouvements oculaires et est donc moins fiable.",
        "en": "No EOG in this EDF file. Sleep staging runs without eye movements and is therefore less reliable.",
        "de": "Kein EOG in dieser EDF-Datei. Die Schlafstadienbestimmung läuft ohne Augenbewegungen und ist daher weniger zuverlässig.",
    },
    "pdf_warn_all_artefact": {
        "nl": "Alle epochs zijn als artefact gemarkeerd; er blijft geen slaaptijd over om indices op te baseren. Controleer of het opgegeven EEG-kanaal werkelijk een EEG is.",
        "fr": "Toutes les époques sont marquées comme artefact ; il ne reste aucun temps de sommeil pour calculer les index. Vérifiez que le canal EEG indiqué est bien un EEG.",
        "en": "Every epoch is marked as artefact; no sleep time remains on which to base the indices. Check that the EEG channel given really is an EEG.",
        "de": "Alle Epochen sind als Artefakt markiert; es bleibt keine Schlafzeit, auf die sich die Indizes stützen könnten. Prüfen Sie, ob der angegebene EEG-Kanal wirklich ein EEG ist.",
    },
    "pdf_flag_arousal": {
        "nl": "Verhoogde arousal-index ({ai}/u)",
        "fr": "Index de micro-éveils élevé ({ai}/h)",
        "en": "Elevated arousal index ({ai}/h)",
        "de": "Erhöhter Arousal-Index ({ai}/h)"},
    "pdf_flag_csr": {
        "nl": "Cheyne-Stokes-ademhaling (voldoet aan AASM-criteria)",
        "fr": "Respiration de Cheyne-Stokes (critères AASM remplis)",
        "en": "Cheyne-Stokes breathing (AASM criteria met)",
        "de": "Cheyne-Stokes-Atmung (AASM-Kriterien erfüllt)"},
}
TRANSLATIONS.update(_PDF_AASM_V3)

def t(key: str, lang: str = None) -> str:
    """Alias voor get_translation — handig in Python-code."""
    return get_translation(key, lang)


# ═══════════════════════════════════════════════════════════
# v0.8.39: Dashboard Grade/ODI/PLMi columns
# ═══════════════════════════════════════════════════════════
_DASHBOARD_V0839 = {
    # "grade" / "grade_tooltip" stonden hier. Verwijderd 2026-08-06 samen met
    # de A/B/C-kolom zelf; zie de toelichting in app.py.
    "odi_tooltip": {
        "nl": "Oxygen Desaturation Index (3%) \u2014 events/uur slaap",
        "fr": "Index de d\u00e9saturation en oxyg\u00e8ne (3%) \u2014 \u00e9v\u00e9nements/h sommeil",
        "en": "Oxygen Desaturation Index (3%) \u2014 events/hour sleep",
        "de": "Oxygen Desaturation Index (3%) \u2014 Ereignisse/Stunde Schlaf",
    },
    "plmi_tooltip": {
        "nl": "Periodic Limb Movement Index \u2014 beenbewegingen/uur slaap",
        "fr": "Index des mouvements p\u00e9riodiques des membres \u2014 MPM/h sommeil",
        "en": "Periodic Limb Movement Index \u2014 PLMs/hour sleep",
        "de": "Periodischer Bein-Bewegungs-Index \u2014 PLM/Stunde Schlaf",
    },
}
TRANSLATIONS.update(_DASHBOARD_V0839)


# v0.8.39: Dashboard Grade/ODI/PLMi columns
_DASHBOARD_V0839 = {
    # idem — zie het blok hierboven.
    "odi_tooltip": {
        "nl": "Oxygen Desaturation Index (3%) — events/uur slaap",
        "fr": "Index de désaturation en oxygène (3%) — événements/h sommeil",
        "en": "Oxygen Desaturation Index (3%) — events/hour sleep",
        "de": "Oxygen Desaturation Index (3%) — Ereignisse/Stunde Schlaf",
    },
    "plmi_tooltip": {
        "nl": "Periodic Limb Movement Index — beenbewegingen/uur slaap",
        "fr": "Index des mouvements périodiques des membres — MPM/h sommeil",
        "en": "Periodic Limb Movement Index — PLMs/hour sleep",
        "de": "Periodischer Bein-Bewegungs-Index — PLM/Stunde Schlaf",
    },
}
TRANSLATIONS.update(_DASHBOARD_V0839)


# ═══════════════════════════════════════════════════════════
# v0.8.41: Dashboard Signal Quality column (Sig)
# ═══════════════════════════════════════════════════════════
_DASHBOARD_V0841 = {
    "sq": {
        "nl": "Sig",
        "fr": "Sig",
        "en": "Sig",
        "de": "Sig",
    },
    "sq_tooltip_header": {
        "nl": "Signaalkwaliteit (thorax + abdomen RIP sensors)",
        "fr": "Qualité du signal (capteurs RIP thorax + abdomen)",
        "en": "Signal quality (thorax + abdomen RIP sensors)",
        "de": "Signalqualität (Thorax + Abdomen RIP Sensoren)",
    },
    "sq_filter_warning": {
        "nl": "Alleen waarschuwingen",
        "fr": "Avertissements seulement",
        "en": "Warnings only",
        "de": "Nur Warnungen",
    },
}
TRANSLATIONS.update(_DASHBOARD_V0841)


# ═══════════════════════════════════════════════════════════
# v0.10.2: Hardcoded UI strings audit fix
#   Adds keys that were previously hardcoded in templates / app.py
#   Coverage: error pages, admin_sites, dashboard buttons, channel_select,
#   base.html footer + session warning, flash messages.
#   See user message 2026-05-12: "yasaflaskified : volledig vertaald in de 4 talen?"
# ═══════════════════════════════════════════════════════════
_V0102_UI = {
    # Error pages
    "error_404_short": {"nl": "Niet gevonden", "fr": "Introuvable", "en": "Not found", "de": "Nicht gefunden"},
    "error_404_title": {"nl": "Pagina niet gevonden", "fr": "Page introuvable", "en": "Page not found", "de": "Seite nicht gefunden"},
    "error_404_body":  {"nl": "De gevraagde pagina bestaat niet.", "fr": "La page demandée n'existe pas.", "en": "The requested page does not exist.", "de": "Die angeforderte Seite existiert nicht."},
    "error_500_short": {"nl": "Serverfout", "fr": "Erreur serveur", "en": "Server error", "de": "Serverfehler"},
    "error_500_title": {"nl": "Interne serverfout", "fr": "Erreur interne du serveur", "en": "Internal server error", "de": "Interner Serverfehler"},
    "error_500_body":  {"nl": "Er is een onverwachte fout opgetreden. Probeer opnieuw.", "fr": "Une erreur inattendue est survenue. Veuillez réessayer.", "en": "An unexpected error occurred. Please try again.", "de": "Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut."},
    "back_home":       {"nl": "Terug naar home", "fr": "Retour à l'accueil", "en": "Back to home", "de": "Zurück zur Startseite"},

    # admin_sites.html column headers (Naam, Taal, E-mail, Acties already partly covered: e-mail/site_email exists)
    "col_name":     {"nl": "Naam", "fr": "Nom", "en": "Name", "de": "Name"},
    "col_language": {"nl": "Taal", "fr": "Langue", "en": "Language", "de": "Sprache"},
    "col_actions":  {"nl": "Acties", "fr": "Actions", "en": "Actions", "de": "Aktionen"},
    "no_sites_yet": {"nl": "Nog geen sites aangemaakt.", "fr": "Aucun site créé pour l'instant.", "en": "No sites created yet.", "de": "Noch keine Standorte angelegt."},
    "add":          {"nl": "Toevoegen", "fr": "Ajouter", "en": "Add", "de": "Hinzufügen"},

    # dashboard.html
    "clear": {"nl": "Wissen", "fr": "Effacer", "en": "Clear", "de": "Löschen"},

    # channel_select.html
    "not_detected": {"nl": "niet gedetecteerd", "fr": "non détecté", "en": "not detected", "de": "nicht erkannt"},
    "ml_help": {
        "nl": "🤖 ML = profiel past de LightGBM candidate-classifier toe (standaard alleen op mesa_shhs).",
        "fr": "🤖 ML = le profil applique le classificateur de candidats LightGBM (activé par défaut uniquement sur mesa_shhs).",
        "en": "🤖 ML = the profile applies the LightGBM candidate classifier (enabled by default only on mesa_shhs).",
        "de": "🤖 ML = das Profil wendet den LightGBM-Kandidaten-Klassifikator an (standardmäßig nur bei mesa_shhs aktiv).",
    },


    # base.html footer
    "footer_powered_by":   {"nl": "Mogelijk gemaakt door", "fr": "Propulsé par", "en": "Powered by", "de": "Bereitgestellt von"},
    "footer_disclaimer":   {"nl": "Disclaimer", "fr": "Avertissement", "en": "Disclaimer", "de": "Haftungsausschluss"},
    "session_expiring":    {
        "nl": "Sessie verloopt binnenkort — beweeg de muis om ingelogd te blijven",
        "fr": "Session expire bientôt — bougez la souris pour rester connecté",
        "en": "Session expiring soon — move mouse to stay logged in",
        "de": "Sitzung läuft bald ab — bewegen Sie die Maus, um angemeldet zu bleiben",
    },

    # app.py flash messages
    "file_too_large": {
        "nl": "Bestand te groot. Maximum is {max_mb} MB.",
        "fr": "Fichier trop volumineux. Maximum : {max_mb} Mo.",
        "en": "File too large. Maximum is {max_mb} MB.",
        "de": "Datei zu groß. Maximum: {max_mb} MB.",
    },
    "files_word":  {"nl": "bestanden", "fr": "fichiers", "en": "files", "de": "Dateien"},
    "errors_word": {"nl": "fouten",    "fr": "erreurs",  "en": "errors", "de": "Fehler"},

    # admin_sites placeholders
    "logo_path_optional": {"nl": "Logo-pad (optioneel)", "fr": "Chemin du logo (facultatif)", "en": "Logo path (optional)", "de": "Logo-Pfad (optional)"},
}
TRANSLATIONS.update(_V0102_UI)


# ═══════════════════════════════════════════════════════════
# v0.10.2: disclaimer.html — all sections
# ═══════════════════════════════════════════════════════════
_V0102_DISC = {
    "disc_page_title": {
        "nl": "Medische & klinische disclaimer",
        "fr": "Avertissement médical et clinique",
        "en": "Medical & Clinical Disclaimer",
        "de": "Medizinischer & klinischer Haftungsausschluss",
    },
    "disc_s1_title": {
        "nl": "1. Onderzoekssoftware — geen medisch hulpmiddel",
        "fr": "1. Logiciel de recherche — pas un dispositif médical",
        "en": "1. Research Software — Not a Medical Device",
        "de": "1. Forschungssoftware — kein Medizinprodukt",
    },
    "disc_s1_p1": {
        "nl": "YASAFlaskified en <code>psgscoring</code> zijn <strong>onderzoekssoftware</strong>, uitsluitend bedoeld voor gebruik door gekwalificeerde professionals (artsen, onderzoekers, geregistreerde polysomnografisch technologen) in een onderzoek- of klinisch-onderzoekscontext.",
        "fr": "YASAFlaskified et <code>psgscoring</code> sont des <strong>logiciels de recherche</strong>, destinés exclusivement à un usage par des professionnels qualifiés (médecins, chercheurs, technologues en polysomnographie agréés) dans un cadre de recherche ou de recherche clinique.",
        "en": "YASAFlaskified and <code>psgscoring</code> are <strong>research software</strong>, intended exclusively for use by qualified professionals (physicians, researchers, registered polysomnographic technologists) in a research or clinical research context.",
        "de": "YASAFlaskified und <code>psgscoring</code> sind <strong>Forschungssoftware</strong>, ausschließlich bestimmt zur Nutzung durch qualifizierte Fachkräfte (Ärzte, Forschende, registrierte Polysomnographie-Technologen) in einem Forschungs- oder klinischen Forschungskontext.",
    },
    "disc_s1_p2": {
        "nl": "Deze software is <strong>niet</strong> geëvalueerd, vrijgegeven of goedgekeurd door enige regelgevende autoriteit als medisch hulpmiddel, waaronder:",
        "fr": "Ce logiciel n'a <strong>pas</strong> été évalué, autorisé ni approuvé par une autorité réglementaire en tant que dispositif médical, notamment :",
        "en": "This software has <strong>not</strong> been evaluated, cleared, or approved by any regulatory authority as a medical device, including:",
        "de": "Diese Software wurde von keiner Aufsichtsbehörde als Medizinprodukt <strong>bewertet, freigegeben oder zugelassen</strong>, einschließlich:",
    },
    "disc_s1_l1": {
        "nl": "Verordening (EU) 2017/745 betreffende medische hulpmiddelen (MDR) — <strong>geen CE-markering</strong>",
        "fr": "Règlement (UE) 2017/745 relatif aux dispositifs médicaux (MDR) — <strong>pas de marquage CE</strong>",
        "en": "European Union Medical Device Regulation (EU MDR 2017/745) — <strong>no CE mark</strong>",
        "de": "EU-Verordnung über Medizinprodukte (EU MDR 2017/745) — <strong>keine CE-Kennzeichnung</strong>",
    },
    "disc_s1_l2": {
        "nl": "U.S. Food and Drug Administration (FDA 21 CFR Part 820 / 510(k)) — <strong>geen FDA-goedkeuring</strong>",
        "fr": "U.S. Food and Drug Administration (FDA 21 CFR Part 820 / 510(k)) — <strong>pas d'autorisation FDA</strong>",
        "en": "U.S. Food and Drug Administration (FDA 21 CFR Part 820 / 510(k)) — <strong>no FDA clearance</strong>",
        "de": "U.S. Food and Drug Administration (FDA 21 CFR Part 820 / 510(k)) — <strong>keine FDA-Zulassung</strong>",
    },
    "disc_s1_l3": {
        "nl": "Elk gelijkwaardig nationaal of regionaal kader voor medische hulpmiddelen",
        "fr": "Tout cadre national ou régional équivalent pour les dispositifs médicaux",
        "en": "Any equivalent national or regional medical device framework",
        "de": "Jeder gleichwertige nationale oder regionale Rechtsrahmen für Medizinprodukte",
    },
    "disc_s2_title": {
        "nl": "2. Geen vervanging van klinisch oordeel",
        "fr": "2. Ne remplace pas le jugement clinique",
        "en": "2. Not a Substitute for Clinical Judgement",
        "de": "2. Kein Ersatz für klinisches Urteilsvermögen",
    },
    "disc_s2_p1": {
        "nl": "Alle berekende indices — waaronder AHI, OAHI, ODI, PLMI, arousal-index en RDI — zijn <strong>onderzoeksindices</strong>. Deze moeten:",
        "fr": "Tous les indices calculés — y compris l'IAH, l'OAHI, l'ODI, le PLMI, l'index d'éveils et le RDI — sont des <strong>estimations à visée de recherche</strong>. Ils doivent :",
        "en": "All computed indices — including AHI, OAHI, ODI, PLMI, arousal index, and RDI — are <strong>research-grade estimates</strong>. They must be:",
        "de": "Alle berechneten Indizes — einschließlich AHI, OAHI, ODI, PLMI, Arousal-Index und RDI — sind <strong>Schätzwerte für Forschungszwecke</strong>. Sie müssen:",
    },
    "disc_s2_l1": {
        "nl": "Beoordeeld worden door een gekwalificeerde, erkende clinicus vóór elke diagnostische of therapeutische beslissing",
        "fr": "Être examinés par un clinicien qualifié et agréé avant toute décision diagnostique ou thérapeutique",
        "en": "Reviewed by a qualified, licensed clinician before any diagnostic or therapeutic decision",
        "de": "Von einer qualifizierten, zugelassenen Klinikerin oder einem Kliniker vor jeder diagnostischen oder therapeutischen Entscheidung überprüft werden",
    },
    "disc_s2_l2": {
        "nl": "Gevalideerd worden tegen manuele scoring door een geregistreerd polysomnografisch technoloog (RPSGT)",
        "fr": "Être validés par scoring manuel effectué par un technologue en polysomnographie agréé (RPSGT)",
        "en": "Validated against manual scoring by a registered polysomnographic technologist (RPSGT)",
        "de": "Gegen manuelles Scoring durch einen registrierten Polysomnographie-Technologen (RPSGT) validiert werden",
    },
    "disc_s2_l3": {
        "nl": "Geïnterpreteerd worden binnen de volledige klinische context en patiëntgeschiedenis",
        "fr": "Être interprétés dans le contexte clinique global et l'histoire du patient",
        "en": "Interpreted in the context of the full clinical picture and patient history",
        "de": "Im Kontext des gesamten klinischen Bildes und der Patientengeschichte interpretiert werden",
    },
    "disc_s3_title": {
        "nl": "3. Beoogd gebruik",
        "fr": "3. Usage prévu",
        "en": "3. Intended Use",
        "de": "3. Bestimmungsgemäße Verwendung",
    },
    "disc_s3_designed_for": {
        "nl": "Bestemd voor:",
        "fr": "Conçu pour :",
        "en": "Designed for:",
        "de": "Vorgesehen für:",
    },
    "disc_s3_not_for": {
        "nl": "NIET bestemd voor:",
        "fr": "PAS conçu pour :",
        "en": "NOT designed for:",
        "de": "NICHT vorgesehen für:",
    },
    "disc_s3_for_1": {"nl": "Academisch slaaponderzoek", "fr": "Recherche académique sur le sommeil", "en": "Academic sleep research", "de": "Akademische Schlafforschung"},
    "disc_s3_for_2": {"nl": "Algoritme-ontwikkeling en benchmarking", "fr": "Développement et benchmarking d'algorithmes", "en": "Algorithm development and benchmarking", "de": "Algorithmen-Entwicklung und Benchmarking"},
    "disc_s3_for_3": {"nl": "Klinisch onderzoek onder goedkeuring van een ethisch comité", "fr": "Recherche clinique avec approbation d'un comité d'éthique", "en": "Clinical research under ethics committee approval", "de": "Klinische Forschung unter Genehmigung einer Ethikkommission"},
    "disc_s3_for_4": {"nl": "Onderwijsdoeleinden in slaapgeneeskunde", "fr": "Objectifs pédagogiques en médecine du sommeil", "en": "Educational purposes in sleep medicine", "de": "Lehrzwecke in der Schlafmedizin"},
    "disc_s3_for_5": {"nl": "Tweede mening en screening", "fr": "Second avis et dépistage", "en": "Second opinion and screening", "de": "Zweitmeinung und Screening"},
    "disc_s3_not_1": {"nl": "Stand-alone klinische diagnose zonder expertbeoordeling", "fr": "Diagnostic clinique autonome sans revue par un expert", "en": "Standalone clinical diagnosis without expert review", "de": "Eigenständige klinische Diagnose ohne Expertenüberprüfung"},
    "disc_s3_not_2": {"nl": "Geautomatiseerde behandelbeslissingen", "fr": "Décisions thérapeutiques automatisées", "en": "Automated treatment decisions", "de": "Automatisierte Therapieentscheidungen"},
    "disc_s3_not_3": {"nl": "Onbegeleide patiënten-screeningprogramma's", "fr": "Programmes de dépistage non supervisés", "en": "Unsupervised patient screening programmes", "de": "Unbeaufsichtigte Patienten-Screening-Programme"},
    "disc_s3_not_4": {"nl": "Elke setting waar de output rechtstreeks de patiëntenzorg bepaalt", "fr": "Tout contexte où la sortie détermine directement la prise en charge du patient", "en": "Any setting where output directly determines patient care", "de": "Jeder Kontext, in dem die Ausgabe direkt die Patientenversorgung bestimmt"},
    "disc_s4_title": {
        "nl": "4. Validatiestatus",
        "fr": "4. État de la validation",
        "en": "4. Validation Status",
        "de": "4. Validierungsstatus",
    },
    "disc_s4_p1": {
        "nl": "Externe validatie op de PSG-IPA-dataset (PhysioNet, 5 opnames, 47 onafhankelijke scoorder-sessies) toonde gemiddeld |ΔAHI| = 1,9/u en ernst-concordantie van 4/5 (80%).",
        "fr": "La validation externe sur l'ensemble de données PSG-IPA (PhysioNet, 5 enregistrements, 47 sessions de scoring indépendantes) a montré un |ΔIAH| moyen = 1,9/h et une concordance de sévérité de 4/5 (80 %).",
        "en": "External validation on the PSG-IPA dataset (PhysioNet, 5 recordings, 47 independent scorer sessions) demonstrated mean |ΔAHI| = 1.9/h and severity concordance of 4/5 (80%).",
        "de": "Externe Validierung auf dem PSG-IPA-Datensatz (PhysioNet, 5 Aufzeichnungen, 47 unabhängige Scoring-Sitzungen) ergab einen mittleren |ΔAHI| = 1,9/h und eine Schweregrad-Konkordanz von 4/5 (80 %).",
    },
    "disc_s4_p2": {
        "nl": "Een formele monocentrische validatiestudie (AZORG-YASA-2026-001, n≥50) is in voorbereiding. Tot peer-reviewed resultaten gepubliceerd zijn, moeten alle uitkomsten als <strong>voorlopig</strong> worden beschouwd en door een gekwalificeerde clinicus worden geverifieerd.",
        "fr": "Une étude de validation monocentrique formelle (AZORG-YASA-2026-001, n≥50) est en préparation. Jusqu'à publication de résultats évalués par les pairs, toutes les sorties doivent être considérées comme <strong>préliminaires</strong> et vérifiées par un clinicien qualifié.",
        "en": "A formal single-centre validation study (AZORG-YASA-2026-001, n≥50) is in preparation. Until peer-reviewed results are published, all outputs should be treated as <strong>preliminary</strong> and verified by a qualified clinician.",
        "de": "Eine formelle monozentrische Validierungsstudie (AZORG-YASA-2026-001, n≥50) ist in Vorbereitung. Bis zur Veröffentlichung peer-reviewter Ergebnisse sind alle Ausgaben als <strong>vorläufig</strong> zu betrachten und von einer qualifizierten Klinikerin oder einem Kliniker zu verifizieren.",
    },
    "disc_s5_title": {
        "nl": "5. Geen garantie",
        "fr": "5. Aucune garantie",
        "en": "5. No Warranty",
        "de": "5. Keine Gewährleistung",
    },
    "disc_s5_p1": {
        "nl": "DEZE SOFTWARE WORDT GELEVERD \"ZOALS HIJ IS\", ZONDER ENIGE GARANTIE, EXPLICIET OF IMPLICIET, INCLUSIEF MAAR NIET BEPERKT TOT GARANTIES VAN VERKOOPBAARHEID, GESCHIKTHEID VOOR EEN BEPAALD DOEL EN NIET-INBREUK. IN GEEN GEVAL ZIJN DE AUTEURS AANSPRAKELIJK VOOR ENIGE CLAIM, SCHADE OF ANDERE AANSPRAKELIJKHEID.",
        "fr": "CE LOGICIEL EST FOURNI « EN L'ÉTAT », SANS GARANTIE D'AUCUNE SORTE, EXPLICITE OU IMPLICITE, Y COMPRIS, MAIS SANS S'Y LIMITER, LES GARANTIES DE QUALITÉ MARCHANDE, D'ADÉQUATION À UN USAGE PARTICULIER ET D'ABSENCE DE CONTREFAÇON. EN AUCUN CAS LES AUTEURS NE POURRONT ÊTRE TENUS RESPONSABLES D'UNE QUELCONQUE RÉCLAMATION, DOMMAGE OU AUTRE RESPONSABILITÉ.",
        "en": "THIS SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY.",
        "de": "DIESE SOFTWARE WIRD „WIE BESEHEN“ BEREITGESTELLT, OHNE JEGLICHE AUSDRÜCKLICHE ODER STILLSCHWEIGENDE GEWÄHRLEISTUNG, EINSCHLIESSLICH, ABER NICHT BESCHRÄNKT AUF DIE GEWÄHRLEISTUNG DER MARKTGÄNGIGKEIT, EIGNUNG FÜR EINEN BESTIMMTEN ZWECK UND NICHTVERLETZUNG VON RECHTEN. IN KEINEM FALL HAFTEN DIE AUTOREN FÜR ANSPRÜCHE, SCHÄDEN ODER SONSTIGE HAFTUNGEN.",
    },
    "disc_footer": {
        "nl": "Volledige DISCLAIMER.md op GitHub",
        "fr": "DISCLAIMER.md complet sur GitHub",
        "en": "Full DISCLAIMER.md on GitHub",
        "de": "Vollständige DISCLAIMER.md auf GitHub",
    },
}
TRANSLATIONS.update(_V0102_DISC)


# ═══════════════════════════════════════════════════════════
# v0.10.2: frontpage.html — full marketing copy
# ═══════════════════════════════════════════════════════════
_V0102_FRONT = {
    "fp_page_title": {
        "nl": "YASAFlaskified – Geautomatiseerde slaapanalyse",
        "fr": "YASAFlaskified – Analyse automatisée du sommeil",
        "en": "YASAFlaskified – Automated Sleep Analysis",
        "de": "YASAFlaskified – Automatisierte Schlafanalyse",
    },
    "fp_nav_yasa":     {"nl": "Over YASA", "fr": "À propos de YASA", "en": "About YASA", "de": "Über YASA"},
    "fp_nav_app":      {"nl": "Applicatie", "fr": "Application", "en": "Application", "de": "Anwendung"},
    "fp_nav_workflow": {"nl": "Workflow", "fr": "Workflow", "en": "Workflow", "de": "Workflow"},
    "fp_nav_stack":    {"nl": "Stack", "fr": "Stack", "en": "Stack", "de": "Stack"},
    "fp_nav_credits":  {"nl": "Credits", "fr": "Crédits", "en": "Credits", "de": "Credits"},
    "fp_nav_login":    {"nl": "Inloggen", "fr": "Connexion", "en": "Login", "de": "Anmelden"},

    "fp_badge": {"nl": "AASM v3 · geautomatiseerde slaapstadiëring + respiratoire scoring · screening, geen diagnose", "fr": "AASM v3 · stadification du sommeil + scoring respiratoire automatisés", "en": "AASM v3 · automated sleep staging + respiratory scoring · screening, not diagnosis", "de": "AASM v3 · automatisierte Schlafstadien- + Atmungs-Scoring · Screening, keine Diagnose"},
    "fp_hero_title_1": {"nl": "Automatische slaapanalyse,", "fr": "Analyse du sommeil automatisée,", "en": "Automated sleep analysis,", "de": "Automatisierte Schlafanalyse,"},
    "fp_hero_title_2": {"nl": "door de arts nagekeken", "fr": "vérifiée par le médecin", "en": "verified by the physician", "de": "vom Arzt überprüft"},
    "fp_hero_sub": {
        "nl": "YASAFlaskified brengt de YASA slaapstadiëringsmotor naar een klinisch webplatform — upload uw EDF, verkrijg directe hypnogrammen, spindle- en slow-wave-rapporten en volledige statistische samenvattingen.",
        "fr": "YASAFlaskified apporte la puissance du moteur de stadification du sommeil YASA dans une plateforme web de niveau clinique — téléchargez votre EDF, obtenez des hypnogrammes immédiats, des rapports de spindles et d'ondes lentes, et des résumés statistiques complets.",
        "en": "YASAFlaskified brings the power of the YASA sleep-staging engine into a clinical-grade web platform — upload your EDF, get instant hypnograms, spindle & slow-wave reports, and full statistical summaries.",
        "de": "YASAFlaskified bringt die Leistungsfähigkeit der YASA-Schlafstadien-Engine in eine klinisch geeignete Webplattform — laden Sie Ihre EDF-Datei hoch und erhalten Sie sofort Hypnogramme, Spindel- und Slow-Wave-Berichte sowie vollständige statistische Auswertungen.",
    },
    "fp_btn_launch":   {"nl": "▶  App starten", "fr": "▶  Lancer l'app", "en": "▶  Launch App", "de": "▶  App starten"},
    "fp_btn_learn":    {"nl": "Meer info", "fr": "En savoir plus", "en": "Learn more", "de": "Mehr erfahren"},

    "fp_stat_stages":  {"nl": "Slaapstadia", "fr": "Stades du sommeil", "en": "Sleep stages", "de": "Schlafstadien"},
    "fp_stat_input":   {"nl": "Inputformaat", "fr": "Format d'entrée", "en": "Input format", "de": "Eingabeformat"},
    "fp_stat_std":     {"nl": "Standaard", "fr": "Standard", "en": "Standard", "de": "Standard"},
    "fp_stat_queue":   {"nl": "Jobwachtrij", "fr": "File d'attente", "en": "Job queue", "de": "Job-Queue"},
    "fp_stat_live":    {"nl": "Live", "fr": "En direct", "en": "Live", "de": "Live"},

    # About YASA
    "fp_y_tag":   {"nl": "// Over de engine", "fr": "// À propos du moteur", "en": "// About the engine", "de": "// Über die Engine"},
    "fp_y_title": {"nl": "Wat is YASA?", "fr": "Qu'est-ce que YASA ?", "en": "What is YASA?", "de": "Was ist YASA?"},
    "fp_y_lead": {
        "nl": "YASA (Yet Another Spindle Algorithm) is een open-source Python-bibliotheek voor geautomatiseerde analyse van polysomnografische opnames, ontwikkeld door Raphael Vallat. Ze stadieert slaap met een machine-learning-model rechtstreeks vanuit ruwe EEG-signalen.",
        "fr": "YASA (Yet Another Spindle Algorithm) est une bibliothèque Python open source pour l'analyse automatisée d'enregistrements polysomnographiques, développée par Raphael Vallat. Elle stadifie le sommeil à l'aide d'un modèle d'apprentissage automatique, directement à partir des signaux EEG bruts.",
        "en": "YASA (Yet Another Spindle Algorithm) is an open-source Python library for automated analysis of polysomnographic recordings, developed by Raphael Vallat. It stages sleep with a machine-learning model directly from raw EEG signals.",
        "de": "YASA (Yet Another Spindle Algorithm) ist eine Open-Source-Python-Bibliothek zur automatisierten Analyse polysomnographischer Aufzeichnungen, entwickelt von Raphael Vallat. Sie erkennt Schlafstadien mit einem Machine-Learning-Modell direkt aus EEG-Rohdaten.",
    },
    "fp_y_feat1_title": {"nl": "Geautomatiseerde slaapstadiëring", "fr": "Stadification automatique du sommeil", "en": "Automated sleep staging", "de": "Automatisierte Schlafstadien-Erkennung"},
    "fp_y_feat1_body":  {"nl": "— classificeert epochs van 30 s in Wake, N1, N2, N3 en REM met een gradient-boosting-classifier getraind op duizenden PSG-opnames.", "fr": "— classe les époques de 30 s en Wake, N1, N2, N3 et REM à l'aide d'un classifieur gradient-boosting entraîné sur des milliers d'enregistrements PSG.", "en": "— classifies 30-second epochs into Wake, N1, N2, N3, and REM using a gradient-boosting classifier trained on thousands of PSG recordings.", "de": "— klassifiziert 30-Sekunden-Epochen in Wake, N1, N2, N3 und REM mit einem Gradient-Boosting-Klassifikator, der auf Tausenden von PSG-Aufzeichnungen trainiert wurde."},
    "fp_y_feat2_title": {"nl": "Spindle- & slow-wave-detectie", "fr": "Détection de spindles et d'ondes lentes", "en": "Spindle & slow-wave detection", "de": "Spindel- und Slow-Wave-Erkennung"},
    "fp_y_feat2_body":  {"nl": "— detecteert slaapspindles en trage oscillaties met instelbare drempels en geeft per-event statistieken terug.", "fr": "— détecte les spindles et les oscillations lentes avec des seuils configurables et renvoie les statistiques par événement.", "en": "— detects sleep spindles and slow oscillations with configurable thresholds, returning per-event statistics.", "de": "— erkennt Schlafspindeln und langsame Oszillationen mit konfigurierbaren Schwellenwerten und liefert Statistiken pro Ereignis."},
    "fp_y_feat3_title": {"nl": "REM-detectie", "fr": "Détection REM", "en": "REM detection", "de": "REM-Erkennung"},
    "fp_y_feat3_body":  {"nl": "— identificeert REM-epochs en berekent REM-gerelateerde indices, inclusief NREM/REM-overgangen.", "fr": "— identifie les époques REM et calcule les indices liés au REM, y compris les transitions NREM/REM.", "en": "— identifies REM epochs and computes REM-related metrics including NREM/REM transitions.", "de": "— erkennt REM-Epochen und berechnet REM-bezogene Kennwerte einschließlich NREM/REM-Übergängen."},
    "fp_y_feat4_title": {"nl": "Slaapstatistieken", "fr": "Statistiques du sommeil", "en": "Sleep statistics", "de": "Schlafstatistiken"},
    "fp_y_feat4_body":  {"nl": "— berekent totale slaaptijd, slaap-efficiëntie, latenties, WASO en volledige stadium-percentages volgens AASM-standaarden.", "fr": "— calcule le temps total de sommeil, l'efficacité du sommeil, les latences, le WASO et les pourcentages complets par stade selon les standards AASM.", "en": "— computes total sleep time, sleep efficiency, latencies, WASO, and full stage percentages per AASM standards.", "de": "— berechnet Gesamtschlafzeit, Schlafeffizienz, Latenzen, WASO und vollständige Stadien-Prozentwerte gemäß AASM-Standards."},
    "fp_y_feat5_title": {"nl": "Bandpower-analyse", "fr": "Analyse bandpower", "en": "Bandpower analysis", "de": "Bandpower-Analyse"},
    "fp_y_feat5_body":  {"nl": "— spectraal vermogen in delta-, theta-, alpha-, sigma- en betabanden per epoch en per kanaal.", "fr": "— puissance spectrale dans les bandes delta, thêta, alpha, sigma et bêta, par époque et par canal.", "en": "— spectral power in delta, theta, alpha, sigma, and beta bands per epoch and per channel.", "de": "— Spektralleistung in den Delta-, Theta-, Alpha-, Sigma- und Beta-Bändern pro Epoche und Kanal."},

    "fp_code_comment": {"nl": "# Kern YASA-pipeline", "fr": "# Pipeline YASA principal", "en": "# Core YASA pipeline", "de": "# YASA-Kernpipeline"},

    # About YASAFlaskified
    "fp_a_tag":   {"nl": "// De webapplicatie", "fr": "// L'application web", "en": "// The web application", "de": "// Die Webanwendung"},
    "fp_a_title": {"nl": "Wat is YASAFlaskified?", "fr": "Qu'est-ce que YASAFlaskified ?", "en": "What is YASAFlaskified?", "de": "Was ist YASAFlaskified?"},
    "fp_a_lead": {
        "nl": "YASAFlaskified draait de YASA-engine achter een Flask-applicatie, zodat clinici en onderzoekers een slaapanalyse via de browser kunnen starten zonder Python te schrijven. Jobs lopen asynchroon; een volledige opname is doorgaans in enkele minuten klaar, met PDF- en Excel-rapport. De uitkomst is een voorstel dat door een arts nagekeken moet worden.",
        "fr": "YASAFlaskified fait tourner le moteur YASA derrière une application Flask, permettant aux cliniciens et chercheurs de lancer une analyse via le navigateur sans écrire de Python. Les tâches sont asynchrones ; un enregistrement complet est généralement prêt en quelques minutes, avec rapport PDF et Excel. Le résultat est une proposition qui doit être vérifiée par un médecin.",
        "en": "YASAFlaskified runs the YASA engine behind a Flask application, so clinicians and researchers can start an analysis from the browser without writing Python. Jobs run asynchronously; a full recording is usually ready in a few minutes, with a PDF and Excel report. The output is a proposal that a physician must review.",
        "de": "YASAFlaskified betreibt die YASA-Engine hinter einer Flask-Anwendung, sodass Klinikerinnen und Forschende eine Analyse im Browser starten können, ohne Python zu schreiben. Jobs laufen asynchron; eine vollständige Aufnahme ist meist in wenigen Minuten fertig, mit PDF- und Excel-Bericht. Das Ergebnis ist ein Vorschlag, der ärztlich geprüft werden muss.",
    },
    "fp_a_c1_title": {"nl": "EDF-upload", "fr": "Téléversement EDF", "en": "EDF Upload", "de": "EDF-Upload"},
    "fp_a_c1_body":  {"nl": "Drag-and-drop of selecteer een EDF-bestand uit uw PSG-systeem. De app valideert de opname, extraheert beschikbare kanalen en plaatst de job onmiddellijk in de wachtrij.", "fr": "Glissez-déposez ou sélectionnez un fichier EDF de votre système PSG. L'application valide l'enregistrement, extrait les canaux disponibles et met immédiatement la tâche en file d'attente.", "en": "Drag-and-drop or select any EDF file from your PSG system. The app validates the recording, extracts available channels, and queues the job immediately.", "de": "Per Drag-and-Drop oder Auswahl einer EDF-Datei aus Ihrem PSG-System. Die App validiert die Aufnahme, extrahiert die verfügbaren Kanäle und stellt den Job sofort in die Warteschlange."},
    "fp_a_c2_title": {"nl": "Async verwerking", "fr": "Traitement asynchrone", "en": "Async Processing", "de": "Asynchrone Verarbeitung"},
    "fp_a_c2_body":  {"nl": "Aangedreven door Redis Queue (RQ) en achtergrondworkers; zware analyses lopen zonder de UI te blokkeren. Real-time jobstatus houdt u op de hoogte.", "fr": "Propulsé par Redis Queue (RQ) et des workers d'arrière-plan, les analyses lourdes s'exécutent sans bloquer l'UI. Le statut des tâches en temps réel vous tient informé.", "en": "Powered by Redis Queue (RQ) and background workers, heavy analyses run without blocking the UI. Real-time job status keeps you informed throughout.", "de": "Angetrieben durch Redis Queue (RQ) und Hintergrund-Worker laufen aufwändige Analysen, ohne die UI zu blockieren. Echtzeit-Job-Status hält Sie informiert."},
    "fp_a_c3_title": {"nl": "Rijke rapporten", "fr": "Rapports détaillés", "en": "Rich Reports", "de": "Aussagekräftige Berichte"},
    "fp_a_c3_body":  {"nl": "Hypnogrammen, slaapstatistiektabellen, spindle-kaarten, slow-wave-detecties en bandpower-grafieken — alles server-side gerenderd met Matplotlib en downloadbaar als PNG/CSV.", "fr": "Hypnogrammes, tableaux de statistiques du sommeil, cartes de spindles, détections d'ondes lentes et graphiques bandpower — tout rendu côté serveur avec Matplotlib et téléchargeable en PNG/CSV.", "en": "Hypnograms, sleep statistics tables, spindle maps, slow-wave detections, and bandpower charts — all rendered server-side with Matplotlib and downloadable as PNG/CSV.", "de": "Hypnogramme, Schlafstatistik-Tabellen, Spindelkarten, Slow-Wave-Erkennungen und Bandpower-Diagramme — alle serverseitig mit Matplotlib gerendert und als PNG/CSV herunterladbar."},
    "fp_a_c4_title": {"nl": "Veilig & gehardd", "fr": "Sécurisé & durci", "en": "Secure & Hardened", "de": "Sicher & gehärtet"},
    "fp_a_c4_body":  {"nl": "CSRF-bescherming, rate limiting, sterk sessiebeheer, UFW-firewall en Fail2ban — gebouwd voor klinische omgevingen waar gegevensbeveiliging niet onderhandelbaar is.", "fr": "Protection CSRF, limitation de débit, gestion robuste des sessions, pare-feu UFW et Fail2ban — conçu pour les environnements cliniques où la sécurité des données est non négociable.", "en": "CSRF protection, rate limiting, strong session management, UFW firewall, and Fail2ban — built for clinical environments where data security is non-negotiable.", "de": "CSRF-Schutz, Rate Limiting, starkes Sitzungsmanagement, UFW-Firewall und Fail2ban — entwickelt für klinische Umgebungen, in denen Datensicherheit nicht verhandelbar ist."},
    "fp_a_c5_title": {"nl": "Docker-deployment", "fr": "Déploiement Docker", "en": "Docker Deployment", "de": "Docker-Bereitstellung"},
    "fp_a_c5_body":  {"nl": "Volledig gecontaineriseerd met Gunicorn + Nginx reverse proxy. One-command deploy op elke Linux-server, met Nginx Proxy Manager voor multi-domein SSL-setups.", "fr": "Entièrement conteneurisé avec Gunicorn + reverse proxy Nginx. Déploiement en une commande sur n'importe quel serveur Linux, avec Nginx Proxy Manager pour les configurations SSL multi-domaines.", "en": "Fully containerised with Gunicorn + Nginx reverse proxy. One-command deploy on any Linux server, with Nginx Proxy Manager for multi-domain SSL setups.", "de": "Vollständig containerisiert mit Gunicorn + Nginx-Reverse-Proxy. Ein-Befehl-Bereitstellung auf jedem Linux-Server, mit Nginx Proxy Manager für Multi-Domain-SSL-Setups."},
    "fp_a_c6_title": {"nl": "Onderzoekskwaliteit", "fr": "Qualité recherche", "en": "Research-Grade", "de": "Forschungstauglich"},
    "fp_a_c6_body":  {"nl": "Ondersteunt AASM-conforme stadiëring, instelbare epoch-lengte, multi-kanaalselectie en ruwe µV-signaalvoorbewerking — vertrouwd door slaaponderzoekers.", "fr": "Prend en charge la stadification conforme AASM, une longueur d'époque configurable, la sélection multi-canaux et le prétraitement µV brut — apprécié par les chercheurs du sommeil.", "en": "Supports AASM-compliant staging, configurable epoch length, multi-channel selection, and raw µV signal preprocessing — trusted by sleep researchers.", "de": "Unterstützt AASM-konforme Stadien-Erkennung, konfigurierbare Epochenlänge, Multi-Kanal-Auswahl und Rohsignal-Vorverarbeitung in µV — von Schlafforschenden geschätzt."},

    # Workflow
    "fp_w_tag":   {"nl": "// Zo werkt het", "fr": "// Comment ça marche", "en": "// How it works", "de": "// So funktioniert es"},
    "fp_w_title": {"nl": "Van EDF tot inzicht in vier stappen", "fr": "De l'EDF aux résultats en quatre étapes", "en": "From EDF to insights in four steps", "de": "Von EDF zu Einsichten in vier Schritten"},
    "fp_w_s1_title": {"nl": "EDF uploaden", "fr": "Téléverser l'EDF", "en": "Upload EDF", "de": "EDF hochladen"},
    "fp_w_s1_body":  {"nl": "Selecteer uw polysomnografische opname. De app accepteert standaard European Data Format-bestanden van elk PSG-toestel.", "fr": "Sélectionnez votre enregistrement de polysomnographie. L'application accepte les fichiers European Data Format standard de tout dispositif PSG.", "en": "Select your polysomnography recording. The app accepts standard European Data Format files from any PSG device.", "de": "Wählen Sie Ihre Polysomnographie-Aufnahme aus. Die App akzeptiert Standard-European-Data-Format-Dateien von jedem PSG-Gerät."},
    "fp_w_s2_title": {"nl": "Configureren", "fr": "Configurer", "en": "Configure", "de": "Konfigurieren"},
    "fp_w_s2_body":  {"nl": "Kies uw EEG-, EOG- en EMG-kanalen op naam. Stel de epoch-lengte in en selecteer de gewenste analyses.", "fr": "Choisissez vos canaux EEG, EOG et EMG par nom. Définissez la longueur d'époque et sélectionnez les analyses requises.", "en": "Choose your EEG, EOG, and EMG channels by name. Set epoch length and select the analyses you need.", "de": "Wählen Sie EEG-, EOG- und EMG-Kanäle nach Namen. Legen Sie die Epochenlänge fest und wählen Sie die benötigten Analysen aus."},
    "fp_w_s3_title": {"nl": "Analyseren", "fr": "Analyser", "en": "Analyse", "de": "Analysieren"},
    "fp_w_s3_body":  {"nl": "Het gradient-boosting-model van YASA stadieert elke epoch. Spindle-, slow-wave- en bandpower-detectoren lopen op de achtergrond.", "fr": "Le modèle gradient-boosting de YASA stadifie chaque époque. Les détecteurs de spindles, d'ondes lentes et de bandpower s'exécutent en arrière-plan.", "en": "YASA's gradient-boosting model stages every epoch. Spindle, slow-wave, and bandpower detectors run in the background.", "de": "Das Gradient-Boosting-Modell von YASA klassifiziert jede Epoche. Spindel-, Slow-Wave- und Bandpower-Detektoren laufen im Hintergrund."},
    "fp_w_s4_title": {"nl": "Rapport downloaden", "fr": "Télécharger le rapport", "en": "Download Report", "de": "Bericht herunterladen"},
    "fp_w_s4_body":  {"nl": "Ontvang uw hypnogram, statistiektabel en event-kaarten. Exporteer naar PNG en CSV voor verdere analyse of klinische dossiers.", "fr": "Recevez votre hypnogramme, votre tableau de statistiques et vos cartes d'événements. Exportez en PNG et CSV pour analyse ou dossiers cliniques.", "en": "Receive your hypnogram, statistics table, and event maps. Export to PNG and CSV for further analysis or clinical records.", "de": "Erhalten Sie Hypnogramm, Statistiktabelle und Ereigniskarten. Export als PNG und CSV für weitere Analysen oder klinische Akten."},

    # Stack
    "fp_s_tag":   {"nl": "// Techstack", "fr": "// Pile technologique", "en": "// Technology stack", "de": "// Technologie-Stack"},
    "fp_s_title": {"nl": "Gebouwd op bewezen open source", "fr": "Construit sur des outils open source éprouvés", "en": "Built on proven open-source", "de": "Aufgebaut auf bewährtem Open Source"},

    # Credits
    "fp_c_tag":   {"nl": "// Credits & dankwoord", "fr": "// Crédits et remerciements", "en": "// Credits & acknowledgements", "de": "// Credits & Danksagungen"},
    "fp_c_title": {"nl": "De mensen achter YASA", "fr": "Les personnes derrière YASA", "en": "The people behind YASA", "de": "Die Menschen hinter YASA"},
    "fp_c_lead": {
        "nl": "YASAFlaskified bouwt voort op het open-source-werk van slaaponderzoekers die hun tools vrij beschikbaar maakten. Alle credits gaan naar hen.",
        "fr": "YASAFlaskified s'appuie sur le travail open source de chercheurs du sommeil qui ont rendu leurs outils librement disponibles. Tout le mérite leur revient.",
        "en": "YASAFlaskified builds on the open-source work of sleep researchers who made their tools freely available. Full credit goes to them.",
        "de": "YASAFlaskified baut auf der Open-Source-Arbeit von Schlafforschenden auf, die ihre Werkzeuge frei zur Verfügung gestellt haben. Der volle Verdienst gebührt ihnen.",
    },
    "fp_c_rv_role": {"nl": "Maker & maintainer · YASA", "fr": "Créateur & mainteneur · YASA", "en": "Creator & Maintainer · YASA", "de": "Schöpfer & Maintainer · YASA"},
    "fp_c_rv_bio": {
        "nl": "Postdoctoraal onderzoeker aan het <strong>Center for Human Sleep Science</strong>, University of California, Berkeley. Raphael creëerde YASA en houdt het als open-source-project bij, waardoor geautomatiseerde slaapanalyse vrij toegankelijk werd voor onderzoekers en clinici. Hij ontwikkelt ook <em>Pingouin</em> (statistiek) en <em>AntroPy</em> (tijdreeks-complexiteit).",
        "fr": "Chercheur postdoctoral au <strong>Center for Human Sleep Science</strong>, University of California, Berkeley. Raphael a créé YASA et en assure la maintenance en open source, rendant l'analyse automatisée du sommeil librement accessible aux chercheurs et cliniciens. Il développe également <em>Pingouin</em> (statistiques) et <em>AntroPy</em> (complexité des séries temporelles).",
        "en": "Postdoctoral researcher at the <strong>Center for Human Sleep Science</strong>, University of California, Berkeley. Raphael created and maintains YASA as an open-source project, making automated sleep analysis freely accessible to researchers and clinicians. He also develops <em>Pingouin</em> (statistics) and <em>AntroPy</em> (time-series complexity).",
        "de": "Postdoktorand am <strong>Center for Human Sleep Science</strong>, University of California, Berkeley. Raphael hat YASA als Open-Source-Projekt geschaffen und betreut, sodass automatisierte Schlafanalyse für Forschende und Klinikerinnen frei zugänglich ist. Er entwickelt ebenfalls <em>Pingouin</em> (Statistik) und <em>AntroPy</em> (Zeitreihen-Komplexität).",
    },
    "fp_c_link_docs": {"nl": "Documentatie", "fr": "Documentation", "en": "Documentation", "de": "Dokumentation"},

    "fp_c_mw_role": {"nl": "Co-auteur · eLife-paper", "fr": "Co-auteur · article eLife", "en": "Co-author · eLife Paper", "de": "Co-Autor · eLife-Veröffentlichung"},
    "fp_c_mw_bio": {
        "nl": "Hoogleraar neurowetenschappen en psychologie en directeur van het <strong>Center for Human Sleep Science</strong> aan UC Berkeley. Auteur van <em>Why We Sleep</em> en co-auteur van het peer-reviewed validatiepaper dat de klinische geloofwaardigheid van YASA als geautomatiseerd slaapstadiëringsinstrument vastlegde.",
        "fr": "Professeur de neurosciences et de psychologie et directeur du <strong>Center for Human Sleep Science</strong> à UC Berkeley. Auteur de <em>Why We Sleep</em> et co-auteur de l'article de validation évalué par les pairs qui a établi la crédibilité clinique de YASA comme outil automatisé de stadification du sommeil.",
        "en": "Professor of Neuroscience and Psychology and Director of the <strong>Center for Human Sleep Science</strong> at UC Berkeley. Author of <em>Why We Sleep</em> and co-author of the peer-reviewed validation paper that established YASA's clinical credibility as an automated sleep-staging tool.",
        "de": "Professor für Neurowissenschaften und Psychologie und Direktor des <strong>Center for Human Sleep Science</strong> an der UC Berkeley. Autor von <em>Why We Sleep</em> und Co-Autor des peer-reviewten Validierungspapiers, das die klinische Glaubwürdigkeit von YASA als automatisiertes Schlafstadien-Werkzeug begründete.",
    },
    "fp_c_paper_role": {"nl": "Peer-reviewed publicatie · eLife 2021", "fr": "Publication évaluée par les pairs · eLife 2021", "en": "Peer-reviewed publication · eLife 2021", "de": "Peer-reviewte Publikation · eLife 2021"},
    "fp_c_paper_title": {"nl": "Het validatiepaper", "fr": "L'article de validation", "en": "The validation paper", "de": "Das Validierungspapier"},
    "fp_c_paper_bio": {
        "nl": "Getraind en gevalideerd op meer dan <strong>30.000 uur</strong> polysomnografische opnames over heterogene populaties. De mediane staging-nauwkeurigheid was <strong>87,5 %</strong> over 585 testnachten, in lijn met menselijke inter-scoorder-overeenkomst. Gepubliceerd in <em>eLife</em>, oktober 2021.",
        "fr": "Entraîné et validé sur plus de <strong>30 000 heures</strong> d'enregistrements polysomnographiques sur des populations hétérogènes. La précision médiane de stadification était de <strong>87,5 %</strong> sur 585 nuits de test, comparable à la concordance inter-scoreurs humains. Publié dans <em>eLife</em>, octobre 2021.",
        "en": "Trained and validated on over <strong>30,000 hours</strong> of polysomnographic recordings across heterogeneous populations. Median staging accuracy was <strong>87.5%</strong> across 585 testing nights, in line with human interscorer agreement. Published in <em>eLife</em>, October 2021.",
        "de": "Trainiert und validiert auf über <strong>30 000 Stunden</strong> polysomnographischer Aufzeichnungen über heterogene Populationen hinweg. Die mediane Klassifikationsgenauigkeit lag bei <strong>87,5 %</strong> über 585 Test-Nächte, vergleichbar mit der Übereinstimmung menschlicher Scorer. Veröffentlicht in <em>eLife</em>, Oktober 2021.",
    },
    "fp_c_paper_quote": {
        "nl": "« Een open-source, hoogperformant instrument voor geautomatiseerde slaapstadiëring. »",
        "fr": "« Un outil open source haute performance pour la stadification automatisée du sommeil. »",
        "en": "\"An open-source, high-performance tool for automated sleep staging.\"",
        "de": "„Ein leistungsstarkes Open-Source-Werkzeug für die automatisierte Schlafstadien-Erkennung.“",
    },
    "fp_c_thanks": {
        "nl": "<strong>Dank aan Raphael Vallat</strong> voor het bouwen en onderhouden van YASA als open-source-project. YASAFlaskified is in essentie een webwrapper rond zijn werk — het moeilijkste was al gedaan.",
        "fr": "<strong>Merci à Raphael Vallat</strong> pour avoir construit et maintenu YASA en tant que projet open source. YASAFlaskified n'est essentiellement qu'un wrapper web autour de son travail — le plus dur était déjà fait.",
        "en": "<strong>Thanks to Raphael Vallat</strong> for building and maintaining YASA as an open-source project. YASAFlaskified is essentially a web wrapper around his work — the hard part was already done.",
        "de": "<strong>Dank an Raphael Vallat</strong> für den Aufbau und die Pflege von YASA als Open-Source-Projekt. YASAFlaskified ist im Wesentlichen ein Web-Wrapper um seine Arbeit — der schwere Teil war bereits erledigt.",
    },

    # CTA
    "fp_cta_tag":   {"nl": "// Aan de slag", "fr": "// Pour commencer", "en": "// Get started", "de": "// Loslegen"},
    "fp_cta_title": {"nl": "Klaar om te analyseren?", "fr": "Prêt à analyser ?", "en": "Ready to analyse?", "de": "Bereit zu analysieren?"},
    "fp_cta_lead":  {"nl": "Log in op YASAFlaskified en upload uw eerste EDF-opname. Resultaten binnen een minuut.", "fr": "Connectez-vous à YASAFlaskified et téléversez votre premier enregistrement EDF. Résultats en moins d'une minute.", "en": "Log in to YASAFlaskified and upload your first EDF recording. Results in under a minute.", "de": "Melden Sie sich bei YASAFlaskified an und laden Sie Ihre erste EDF-Aufnahme hoch. Ergebnisse in weniger als einer Minute."},
    "fp_cta_box_title": {"nl": "Aanmelden bij uw account", "fr": "Connectez-vous à votre compte", "en": "Sign in to your account", "de": "Bei Ihrem Konto anmelden"},
    "fp_cta_box_body":  {"nl": "Open uw slaapanalyse-dashboard, bekijk eerdere jobs en start nieuwe analyses.", "fr": "Accédez à votre tableau de bord d'analyse du sommeil, consultez les tâches antérieures et démarrez de nouvelles analyses.", "en": "Access your sleep analysis dashboard, review past jobs, and start new analyses.", "de": "Greifen Sie auf Ihr Schlafanalyse-Dashboard zu, prüfen Sie frühere Jobs und starten Sie neue Analysen."},
    "fp_cta_btn": {"nl": "Inloggen op YASAFlaskified", "fr": "Se connecter à YASAFlaskified", "en": "Login to YASAFlaskified", "de": "Bei YASAFlaskified anmelden"},

    "fp_footer_meta": {"nl": "Mogelijk gemaakt door YASA · Flask · Docker", "fr": "Propulsé par YASA · Flask · Docker", "en": "Powered by YASA · Flask · Docker", "de": "Bereitgestellt von YASA · Flask · Docker"},
}
TRANSLATIONS.update(_V0102_FRONT)


# ═══════════════════════════════════════════════════════════
# v0.10.2: PDF generator — hardcoded NL strings replaced
# ═══════════════════════════════════════════════════════════
_V0102_PDF = {
    "pdf_warn_sq_unusable": {
        "nl": "⚠ Signaalkwaliteit: {n} kanalen onbruikbaar (amplitude &lt; minimum). Staging en micro-architectuur (spindles, slow waves) zijn mogelijk onbetrouwbaar.",
        "fr": "⚠ Qualité du signal : {n} canaux inutilisables (amplitude &lt; minimum). Le staging et la micro-architecture (spindles, ondes lentes) peuvent être peu fiables.",
        "en": "⚠ Signal quality: {n} channels unusable (amplitude &lt; minimum). Staging and micro-architecture (spindles, slow waves) may be unreliable.",
        "de": "⚠ Signalqualität: {n} Kanäle unbrauchbar (Amplitude &lt; Minimum). Staging und Mikroarchitektur (Spindeln, Slow Waves) können unzuverlässig sein.",
    },
    "pdf_warn_low_conf": {
        "nl": "⚠ AI-staging confidence: {pct}% van epochs met confidence &lt;70%. Manuele verificatie aanbevolen.",
        "fr": "⚠ Confiance du staging IA : {pct} % des époques avec confiance &lt;70 %. Vérification manuelle recommandée.",
        "en": "⚠ AI staging confidence: {pct}% of epochs below 70%. Manual verification recommended.",
        "de": "⚠ KI-Staging-Konfidenz: {pct} % der Epochen mit Konfidenz &lt;70 %. Manuelle Überprüfung empfohlen.",
    },
    # Event legend
    "pdf_leg_oa":  {"nl": "OA (obstructief)", "fr": "OA (obstructif)", "en": "OA (obstructive)", "de": "OA (obstruktiv)"},
    "pdf_leg_ca":  {"nl": "CA (centraal)",    "fr": "CA (central)",    "en": "CA (central)",     "de": "CA (zentral)"},
    "pdf_leg_ma":  {"nl": "MA (gemengd)",     "fr": "MA (mixte)",      "en": "MA (mixed)",       "de": "MA (gemischt)"},
    "pdf_leg_hyp": {"nl": "HYP (hypopneu)",   "fr": "HYP (hypopnée)",  "en": "HYP (hypopnea)",   "de": "HYP (Hypopnoe)"},
    "pdf_leg_fr":  {"nl": "FR (flow-reductie)","fr": "FR (réduction de flux)","en":"FR (flow reduction)","de":"FR (Flussreduktion)"},
    "pdf_leg_spo2_thr":  {"nl": "90% drempel", "fr": "seuil 90 %", "en": "90% threshold", "de": "90 %-Schwelle"},
    "pdf_leg_spo2_zone": {"nl": "&lt;90% zone", "fr": "zone &lt;90 %", "en": "&lt;90% zone", "de": "&lt;90 %-Bereich"},
    "pdf_leg_phono_thr": {"nl": "P60 drempel", "fr": "seuil P60",     "en": "P60 threshold",      "de": "P60-Schwelle"},
    # Position labels
    "pdf_pos_buk": {"nl": "BUK (buiklig)",         "fr": "DEC (décubitus ventral)", "en": "PR (prone)",      "de": "BL (Bauchlage)"},
    "pdf_pos_lnk": {"nl": "LNK (linker zijlig)",   "fr": "G (côté gauche)",         "en": "L (left side)",   "de": "L (linke Seite)"},
    "pdf_pos_rug": {"nl": "RUG (ruglig)",          "fr": "DOS (décubitus dorsal)",  "en": "SUP (supine)",    "de": "RL (Rückenlage)"},
    "pdf_pos_rec": {"nl": "REC (rechter zijlig)",  "fr": "D (côté droit)",          "en": "R (right side)",  "de": "R (rechte Seite)"},
    "pdf_pos_sta": {"nl": "STA (staand/rechtop)",  "fr": "DEB (debout)",            "en": "UP (upright)",    "de": "ST (stehend)"},
    # Sec 7 artifact summary
    "pdf_artifact_count": {
        "nl": "{n_art} van {n_tot} epochs ({pct}%) als artefact.",
        "fr": "{n_art} sur {n_tot} époques ({pct} %) classées comme artefact.",
        "en": "{n_art} of {n_tot} epochs ({pct}%) classified as artifact.",
        "de": "{n_art} von {n_tot} Epochen ({pct} %) als Artefakt klassifiziert.",
    },
    # Sec 7b staging confidence
    "pdf_staging_conf_line": {
        "nl": "<b>Staging confidence:</b> {n_low}/{n_tot} epochs ({pct}%) AI confidence &lt;70%.",
        "fr": "<b>Confiance du staging :</b> {n_low}/{n_tot} époques ({pct} %) avec confiance IA &lt;70 %.",
        "en": "<b>Staging confidence:</b> {n_low}/{n_tot} epochs ({pct}%) below 70%.",
        "de": "<b>Staging-Konfidenz:</b> {n_low}/{n_tot} Epochen ({pct} %) mit KI-Konfidenz &lt;70 %.",
    },
    "pdf_low_conf_per_stage": {
        "nl": "<i>Low-confidence per stadium: {parts}</i>",
        "fr": "<i>Faible confiance par stade : {parts}</i>",
        "en": "<i>Low-confidence per stage: {parts}</i>",
        "de": "<i>Niedrige Konfidenz pro Stadium: {parts}</i>",
    },
    # OAHI uncertainty section
    "pdf_oahi_uncertainty_hdr": {
        "nl": "OAHI — Klinische onzekerheidsmarge",
        "fr": "OAHI — Marge d'incertitude clinique",
        "en": "OAHI — Clinical uncertainty range",
        "de": "OAHI — Klinische Unsicherheitsspanne",
    },
    "pdf_grade_a_robust": {
        "nl": "Robuust — diagnose stabiel ongeacht scoringsstrengheid",
        "fr": "Robuste — diagnostic stable indépendamment de la sévérité du scoring",
        "en": "Robust — diagnosis stable regardless of scoring strictness",
        "de": "Robust — Diagnose stabil unabhängig von der Scoring-Strenge",
    },
    "pdf_grade_b_likely": {
        "nl": "Waarschijnlijk — klinische correlatie aanbevolen",
        "fr": "Probable — corrélation clinique recommandée",
        "en": "Likely — clinical correlation recommended",
        "de": "Wahrscheinlich — klinische Korrelation empfohlen",
    },
    "pdf_grade_c_uncertain": {
        "nl": "Onzeker — manuele review aanbevolen",
        "fr": "Incertain — revue manuelle recommandée",
        "en": "Uncertain — manual review recommended",
        "de": "Unsicher — manuelle Überprüfung empfohlen",
    },
    "pdf_robust_line": {
        "nl": "Gem. confidence apneas: <b>{avg}</b>  |  Alle events (officieel): OAHI = {oahi:.1f}/u  |  <b>Robustness: {grade}</b> ({desc})",
        "fr": "Confiance moy. apnées : <b>{avg}</b>  |  Tous les événements (officiel) : OAHI = {oahi:.1f}/h  |  <b>Robustesse : {grade}</b> ({desc})",
        "en": "Mean apnea confidence: <b>{avg}</b>  |  All events (official): OAHI = {oahi:.1f}/h  |  <b>Robustness: {grade}</b> ({desc})",
        "de": "Mittlere Apnoe-Konfidenz: <b>{avg}</b>  |  Alle Ereignisse (offiziell): OAHI = {oahi:.1f}/h  |  <b>Robustheit: {grade}</b> ({desc})",
    },
    "pdf_sweep_lenient":   {"nl": "Soepel (c ≥ 0.55)",       "fr": "Souple (c ≥ 0.55)",       "en": "Lenient (c ≥ 0.55)",   "de": "Locker (c ≥ 0.55)"},
    "pdf_sweep_primary":   {"nl": "Primair (c ≥ 0.60)  ← officiële AASM", "fr": "Primaire (c ≥ 0.60)  ← AASM officiel", "en": "Primary (c ≥ 0.60)  ← official AASM", "de": "Primär (c ≥ 0.60)  ← offizielle AASM"},
    "pdf_sweep_strict":    {"nl": "Strikt (c ≥ 0.70)",       "fr": "Strict (c ≥ 0.70)",       "en": "Strict (c ≥ 0.70)",    "de": "Streng (c ≥ 0.70)"},
    "pdf_sweep_spread":    {"nl": "Spreiding (lenient − strict)", "fr": "Étalement (souple − strict)", "en": "Spread (lenient − strict)", "de": "Spannweite (locker − streng)"},
    "pdf_sweep_lenient_desc": {"nl": "Inclusief net-borderline events", "fr": "Inclut les événements limites", "en": "Includes borderline events", "de": "Inklusive Grenzfall-Ereignisse"},
    "pdf_sweep_primary_desc": {"nl": "AASM standaard cutoff", "fr": "Seuil standard AASM", "en": "AASM standard cutoff", "de": "AASM-Standard-Cutoff"},
    "pdf_sweep_strict_desc":  {"nl": "Conservatief, hoge zekerheid", "fr": "Conservateur, haute certitude", "en": "Conservative, high certainty", "de": "Konservativ, hohe Sicherheit"},
    "pdf_sweep_grade_desc":   {"nl": "&lt;5/u: Grade A · 5–10/u: Grade B · ≥10/u: Grade C", "fr": "&lt;5/h : Grade A · 5–10/h : Grade B · ≥10/h : Grade C", "en": "&lt;5/h: Grade A · 5–10/h: Grade B · ≥10/h: Grade C", "de": "&lt;5/h: Grad A · 5–10/h: Grad B · ≥10/h: Grad C"},
    "pdf_sweep_col_threshold": {"nl": "Drempel", "fr": "Seuil", "en": "Threshold", "de": "Schwelle"},
    "pdf_sweep_col_oahi":      {"nl": "OAHI (/u)", "fr": "OAHI (/h)", "en": "OAHI (/h)", "de": "OAHI (/h)"},
    "pdf_sweep_col_severity":  {"nl": "Ernst", "fr": "Sévérité", "en": "Severity", "de": "Schweregrad"},
    "pdf_sweep_col_note":      {"nl": "Toelichting", "fr": "Remarque", "en": "Note", "de": "Anmerkung"},
    "pdf_sweep_unavailable": {
        "nl": "<i>3-punt sweep niet beschikbaar (oude psgscoring versie). Officiële OAHI: {oahi:.1f}/u</i>",
        "fr": "<i>Sweep à 3 points non disponible (ancienne version psgscoring). OAHI officiel : {oahi:.1f}/h</i>",
        "en": "<i>3-point sweep not available (older psgscoring version). Official OAHI: {oahi:.1f}/h</i>",
        "de": "<i>3-Punkt-Sweep nicht verfügbar (ältere psgscoring-Version). Offizieller OAHI: {oahi:.1f}/h</i>",
    },
    # RERA, RDI section
    "pdf_rera_section_hdr":  {"nl": "RERA, RDI en slaapstadium-AHI", "fr": "RERA, RDI et AHI par stade", "en": "RERA, RDI and stage-AHI", "de": "RERA, RDI und Stadien-AHI"},
    "pdf_rera_amp_arousal":  {"nl": "RERA — amplitude-reductie + arousal (FRI)", "fr": "RERA — réduction d'amplitude + éveil (FRI)", "en": "RERA — amplitude reduction + arousal (FRI)", "de": "RERA — Amplituden-Reduktion + Arousal (FRI)"},
    "pdf_rera_flat_arousal": {"nl": "RERA — flattening + arousal (flow limitation)", "fr": "RERA — flattening + éveil (limitation de flux)", "en": "RERA — flattening + arousal (flow limitation)", "de": "RERA — Flattening + Arousal (Flusslimitierung)"},
    "pdf_rera_total":        {"nl": "RERA totaal", "fr": "RERA total", "en": "RERA total", "de": "RERA gesamt"},
    "pdf_fri_no_criteria":   {"nl": "FRI (flow-reductie zonder criteria)", "fr": "FRI (réduction de flux sans critères)", "en": "FRI (flow reduction without criteria)", "de": "FRI (Flussreduktion ohne Kriterien)"},
    "pdf_rdi_formula":       {"nl": "RDI (AHI + RERA-index)", "fr": "RDI (IAH + index RERA)", "en": "RDI (AHI + RERA index)", "de": "RDI (AHI + RERA-Index)"},
    "pdf_rdi_explanation":   {"nl": "RDI = AHI + RERA-index. Klinisch relevant bij vermoeden UARS.", "fr": "RDI = IAH + index RERA. Cliniquement pertinent en cas de suspicion de UARS.", "en": "RDI = AHI + RERA index. Clinically relevant when UARS is suspected.", "de": "RDI = AHI + RERA-Index. Klinisch relevant bei UARS-Verdacht."},
    "pdf_spo2_low_sr_warn":  {
        "nl": "<b><font color='#e74c3c'>⚠ SpO2 samplerate &lt; 0.33 Hz (&gt;3s averaging) — ODI en desaturatie-detectie mogelijk onderschat (AASM: max 3s averaging).</font></b>",
        "fr": "<b><font color='#e74c3c'>⚠ Fréquence d'échantillonnage SpO2 &lt; 0,33 Hz (moyennage &gt;3 s) — ODI et détection des désaturations possiblement sous-estimés (AASM : max 3 s).</font></b>",
        "en": "<b><font color='#e74c3c'>⚠ SpO2 sample rate &lt; 0.33 Hz (&gt;3s averaging) — ODI and desaturation detection may be underestimated (AASM: max 3s averaging).</font></b>",
        "de": "<b><font color='#e74c3c'>⚠ SpO2-Abtastrate &lt; 0,33 Hz (&gt;3 s Mittelung) — ODI und Desaturations-Erkennung möglicherweise unterschätzt (AASM: max 3 s).</font></b>",
    },
    "pdf_conf_signal_noise": {"nl": "conf&lt;0.40 = signaalruis", "fr": "conf&lt;0,40 = bruit du signal", "en": "conf&lt;0.40 = signal noise", "de": "Konfidenz&lt;0,40 = Signalrauschen"},
    "pdf_max_apnea_dur":     {"nl": "Max. apnea-duur", "fr": "Durée max. d'apnée", "en": "Max apnea duration", "de": "Max. Apnoe-Dauer"},
    # ── Visuele eventcontrole (beheerder) ─────────────────────────────
    # De inleiding zegt expliciet dat de selectie NIET representatief is.
    # Wie hier twaalf grensgevallen ziet en denkt dat dat de nacht is, trekt
    # de verkeerde conclusie over de kwaliteit van de scoring.
    "event_review_title": {
        "nl": "Visuele controle van de events", "fr": "Contrôle visuel des événements",
        "en": "Visual event review", "de": "Visuelle Ereignisprüfung"},
    "event_review_intro": {
        "nl": "Deze panelen zijn géén doorsnede van de nacht. Ze tonen bewust de lastigste gevallen — laagste confidence, afgewezen kandidaten die het net niet haalden, en hypopneeën die via een arousal kwalificeerden — aangevuld met enkele duidelijke gevallen om op te ijken. <b>Rood</b> is het event waar het paneel over gaat; <b>blauw</b> zijn andere events die op dezelfde plek gescoord zijn. Staat er geen markering, dan is daar niets gescoord. De y-as is geschaald op de ademhaling naast het event, zodat de reductie te beoordelen valt.",
        "fr": "Ces panneaux ne sont pas un échantillon représentatif de la nuit. Ils montrent délibérément les cas les plus difficiles — confiance la plus faible, candidats rejetés de justesse, hypopnées qualifiées par micro-éveil — complétés par quelques cas nets servant de référence. <b>Rouge</b> : l'événement concerné ; <b>bleu</b> : les autres événements scorés au même endroit. Sans marquage, rien n'a été scoré. L'axe y est calibré sur la respiration adjacente.",
        "en": "These panels are not a cross-section of the night. They deliberately show the hardest cases — lowest confidence, rejected candidates that just missed, and hypopneas that qualified on an arousal — plus a few clear-cut cases to calibrate against. <b>Red</b> is the event the panel is about; <b>blue</b> marks other events scored in the same place. No marking means nothing was scored there. The y-axis is scaled on the breathing beside the event so the reduction can be judged.",
        "de": "Diese Panels sind kein Querschnitt der Nacht. Sie zeigen bewusst die schwierigsten Fälle — niedrigste Konfidenz, knapp abgelehnte Kandidaten und über ein Arousal qualifizierte Hypopnoen — ergänzt um einige eindeutige Fälle als Referenz. <b>Rot</b> ist das Ereignis des Panels; <b>blau</b> sind andere dort gescorte Ereignisse. Ohne Markierung wurde dort nichts gescort. Die y-Achse ist auf die Atmung neben dem Ereignis skaliert."},
    # Telt dit event mee in het hoofdgetal? Bij "uncertain" is dat
    # contra-intuïtief: een niet-onderverdeelde APNEU valt buiten `ahi_total`,
    # een `hypopnea_uncertain` telt gewoon mee. Zonder dit label kan de
    # beoordelaar dat verschil niet zien.
    "event_review_in_ahi": {
        "nl": "telt in AHI", "fr": "compté dans l'IAH",
        "en": "counted in AHI", "de": "im AHI gezählt"},
    "event_review_uncertain_only": {
        "nl": "niet in AHI · wel in AHI incl. onbepaald",
        "fr": "hors IAH · inclus dans l'IAH avec indéterminés",
        "en": "not in AHI · in AHI incl. unclassified",
        "de": "nicht im AHI · im AHI inkl. unbestimmt"},
    # Gescoord maar buiten de AHI (bv. een RERA, die in de RDI zit) — iets
    # anders dan een kandidaat die nooit een event werd.
    "event_review_not_in_ahi": {
        "nl": "gescoord, niet in AHI", "fr": "scoré, hors IAH",
        "en": "scored, not in AHI", "de": "gescort, nicht im AHI"},
    "event_review_not_scored": {
        "nl": "niet gescoord", "fr": "non scoré",
        "en": "not scored", "de": "nicht gescort"},
    "event_review_k_borderline": {"nl": "grensgeval", "fr": "cas limite", "en": "borderline", "de": "Grenzfall"},
    "event_review_k_rejected":   {"nl": "afgewezen", "fr": "rejeté", "en": "rejected", "de": "abgelehnt"},
    "event_review_k_typical":    {"nl": "typevoorbeeld", "fr": "exemple type", "en": "type example", "de": "Typbeispiel"},
    # Regel B = via arousal gekwalificeerd in plaats van via desaturatie. Daar
    # zit de meeste subjectiviteit en de grootste spreiding tussen scoorders.
    "event_review_k_rule_b":     {"nl": "regel B (arousal)", "fr": "règle B (micro-éveil)", "en": "rule B (arousal)", "de": "Regel B (Arousal)"},
    # Oordeel = mening, en verandert de AHI NIET. Corrigeren gebeurt in de PSG
    # Editor, die het event echt toevoegt of weghaalt en de AHI herberekent.
    # Twee verschillende handelingen, dus twee knoppen naast elkaar.
    "event_review_v_score":   {"nl": "hoort gescoord", "fr": "devrait être scoré", "en": "should be scored", "de": "sollte gescort sein"},
    "event_review_v_noscore": {"nl": "hoort niet gescoord", "fr": "ne devrait pas être scoré", "en": "should not be scored", "de": "sollte nicht gescort sein"},
    "event_review_v_unsure":  {"nl": "twijfel", "fr": "incertain", "en": "unsure", "de": "unsicher"},
    "event_review_v_saved":   {"nl": "vastgelegd", "fr": "enregistré", "en": "recorded", "de": "erfasst"},
    "event_review_open_editor": {"nl": "in PSG Editor →", "fr": "dans l'éditeur PSG →", "en": "in PSG Editor →", "de": "im PSG-Editor →"},
    "event_review_open_editor_hint": {
        "nl": "Opent de PSG Editor op dit tijdstip. Daar corrigeer je de scoring écht — de AHI wordt dan herberekend. Een oordeel hiernaast verandert de AHI niet.",
        "fr": "Ouvre l'éditeur PSG à cet instant. C'est là que la scoration est réellement corrigée et l'IAH recalculé ; un avis ci-contre ne modifie pas l'IAH.",
        "en": "Opens the PSG Editor at this moment. That is where scoring is actually corrected and the AHI recomputed; a verdict here does not change the AHI.",
        "de": "Öffnet den PSG-Editor an dieser Stelle. Dort wird die Scorung tatsächlich korrigiert und der AHI neu berechnet; ein Urteil hier ändert den AHI nicht."},
    # Makkelijke gevallen staan er niet om na te kijken maar om te ijken: je
    # moet kunnen zien hoe een onbetwist event eruitziet.
    "event_review_k_easy":       {"nl": "duidelijk geval", "fr": "cas net", "en": "clear-cut", "de": "eindeutiger Fall"},
    "event_review_panels_shown": {"nl": "panelen", "fr": "panneaux", "en": "panels", "de": "Panels"},
    "event_review_show_more":    {"nl": "meer tonen", "fr": "afficher plus", "en": "show more", "de": "mehr anzeigen"},
    "event_review_no_events": {
        "nl": "Deze analyse bevat geen respiratoire events om te tonen.",
        "fr": "Cette analyse ne contient aucun événement respiratoire à afficher.",
        "en": "This analysis contains no respiratory events to show.",
        "de": "Diese Analyse enthält keine respiratorischen Ereignisse."},
    "event_review_no_edf": {
        "nl": "Het originele EDF-bestand is niet meer beschikbaar — na anonimisering of opruiming blijven de resultaten bestaan maar de signalen niet. Zonder signalen valt er niets te tekenen.",
        "fr": "Le fichier EDF d'origine n'est plus disponible : après anonymisation ou nettoyage, les résultats subsistent mais pas les signaux.",
        "en": "The original EDF file is no longer available — after anonymisation or cleanup the results remain but the signals do not.",
        "de": "Die ursprüngliche EDF-Datei ist nicht mehr verfügbar — nach Anonymisierung oder Bereinigung bleiben die Ergebnisse, die Signale nicht."},
    "event_review_no_channels": {
        "nl": "Er is geen kanaaltoewijzing bewaard bij deze analyse, dus is niet vast te stellen welk signaal welk kanaal was.",
        "fr": "Aucune correspondance de canaux n'a été enregistrée pour cette analyse.",
        "en": "No channel mapping was stored with this analysis, so it cannot be determined which signal was which channel.",
        "de": "Zu dieser Analyse wurde keine Kanalzuordnung gespeichert."},
    "event_review_render_failed": {
        "nl": "Geen enkel paneel kon getekend worden. Mogelijk bevat de EDF de respiratoire kanalen niet meer.",
        "fr": "Aucun panneau n'a pu être tracé.",
        "en": "No panel could be drawn. The EDF may no longer contain the respiratory channels.",
        "de": "Es konnte kein Panel gezeichnet werden."},
    # De REM-AHI bestaat ook bij weinig REM — hij is dan alleen niet te
    # vertrouwen. Een REM-AHI van 64/u op 22 minuten leest als
    # REM-predominante OSA terwijl hij op ~24 events berust. Daarom
    # kwalificeren en niet weglaten: weglaten roept de vraag op waar hij bleef.
    "pdf_rem_ahi_caveat": {
        "nl": "slechts {rem} min REM (&lt; {min} min) — te weinig om de REM-AHI op te steunen",
        "fr": "seulement {rem} min de REM (&lt; {min} min) — insuffisant pour fonder l'IAH REM",
        "en": "only {rem} min REM (&lt; {min} min) — too little sleep to rest the REM-AHI on",
        "de": "nur {rem} min REM (&lt; {min} min) — zu wenig Schlaf für einen belastbaren REM-AHI",
    },
    # De drie REM-tegels tellen niet op, en dat is geen rekenfout: een periode
    # is een spanne die korte onderbrekingen overbrugt, de REM-duur telt
    # uitsluitend R-epochs. Zonder deze noot nodigt het paneel uit tot
    # vermenigvuldigen en straft dat af.
    "pdf_rem_period_note": {
        "nl": "Een REM-periode is een aaneengesloten spanne die onderbrekingen tot {gap} min overbrugt; de REM-duur telt alleen R-epochs. Periodes × gemiddelde is daarom hoger dan de REM-duur.",
        "fr": "Une période REM est un intervalle continu tolérant des interruptions jusqu'à {gap} min ; la durée REM ne compte que les époques R. Périodes × moyenne dépasse donc la durée REM.",
        "en": "A REM period is a contiguous span bridging interruptions of up to {gap} min; REM duration counts R epochs only. Periods × mean therefore exceeds REM duration.",
        "de": "Eine REM-Periode ist eine zusammenhängende Spanne, die Unterbrechungen bis {gap} min überbrückt; die REM-Dauer zählt nur R-Epochen. Perioden × Mittelwert liegt daher über der REM-Dauer.",
    },
    # Spiegelnoot: bij EEN sensor moet het rapport zeggen dat de
    # AASM-methodiek niet gevolgd kon worden. Apneus op nasale druk
    # overdetecteren t.o.v. de thermistor; dat mag niet stil blijven.
    "pdf_single_sensor_note": {
        "nl": "<i>Eén flowkanaal beschikbaar: apneu en hypopneu beide gescoord op {apnea}. De AASM vraagt apneu op de oronasale thermistor en hypopneu op de nasale druk; scoren van apneus op nasale druk kan tot overdetectie leiden.</i>",
        "fr": "<i>Un seul canal de flux disponible : apnée et hypopnée toutes deux scorées sur {apnea}. L'AASM demande l'apnée sur la thermistance oronasale et l'hypopnée sur la pression nasale ; scorer les apnées sur la pression nasale peut entraîner une surdétection.</i>",
        "en": "<i>Only one flow channel available: apnea and hypopnea both scored on {apnea}. The AASM specifies apnea on the oronasal thermistor and hypopnea on nasal pressure; scoring apneas on nasal pressure may over-detect.</i>",
        "de": "<i>Nur ein Flusskanal verfügbar: Apnoe und Hypopnoe beide auf {apnea} gescort. Die AASM verlangt Apnoe am oronasalen Thermistor und Hypopnoe am Nasendruck; Apnoen am Nasendruck zu scoren kann zu Überdetektion führen.</i>",
    },
    "pdf_dual_sensor_note":  {"nl": "<i>Dual-sensor scoring: apneu op thermistor, hypopneu op nasale druk (AASM).</i>", "fr": "<i>Scoring double capteur : apnée sur thermistance, hypopnée sur pression nasale (AASM).</i>", "en": "<i>Dual-sensor scoring: apnea on thermistor, hypopnea on nasal pressure (AASM).</i>", "de": "<i>Dual-Sensor-Scoring: Apnoe am Thermistor, Hypopnoe am Nasendruck (AASM).</i>"},
    # Derde geval: de thermistor zat WEL in het bestand, maar is door de
    # kwaliteitstoets afgewezen. Het rapport zei dan "een flowkanaal
    # beschikbaar" terwijl de kanaallijst erboven twee kanalen toonde —
    # het sprak zichzelf tegen. Afwezig en afgekeurd is niet hetzelfde.
    "pdf_thermistor_rejected_note": {
        "nl": "<i>Thermistor ({therm}) aanwezig maar afgekeurd door de kwaliteitscontrole (envelope-overeenstemming met de neusdruk: {agreement}); apneu en hypopneu zijn beide op {apnea} gescoord. De AASM vraagt apneu op de oronasale thermistor; scoren van apneus op nasale druk kan tot overdetectie leiden.</i>",
        "fr": "<i>Thermistance ({therm}) présente mais rejetée par le contrôle qualité (concordance d'enveloppe avec la pression nasale : {agreement}) ; apnée et hypopnée toutes deux scorées sur {apnea}. L'AASM demande l'apnée sur la thermistance oronasale ; scorer les apnées sur la pression nasale peut entraîner une surdétection.</i>",
        "en": "<i>Thermistor ({therm}) present but rejected by the quality check (envelope agreement with nasal pressure: {agreement}); apnea and hypopnea both scored on {apnea}. The AASM specifies apnea on the oronasal thermistor; scoring apneas on nasal pressure may over-detect.</i>",
        "de": "<i>Thermistor ({therm}) vorhanden, aber von der Qualitätsprüfung abgelehnt (Hüllkurven-Übereinstimmung mit dem Nasendruck: {agreement}); Apnoe und Hypopnoe beide auf {apnea} gescort. Die AASM verlangt Apnoe am oronasalen Thermistor; Apnoen am Nasendruck zu scoren kann zu Überdetektion führen.</i>",
    },
    # De duale noot claimt apneus op de thermistor. Draaide de duale pas en
    # heeft de thermistor geen enkele apneu bevestigd, dan spreekt de
    # corroboratiekolom die claim tegen; dat hoort er expliciet bij.
    "pdf_dual_sensor_no_corrob": {
        "nl": "<i>Let op: geen enkele apneu is door de thermistor bevestigd — alle apneus komen van de nasale druk. Beoordeel de thermistortracé bij twijfel visueel.</i>",
        "fr": "<i>Attention : aucune apnée n'a été confirmée par la thermistance — toutes proviennent de la pression nasale. En cas de doute, examinez visuellement le tracé de la thermistance.</i>",
        "en": "<i>Note: no apnea was corroborated by the thermistor — all apneas come from nasal pressure. Review the thermistor trace visually if in doubt.</i>",
        "de": "<i>Hinweis: keine Apnoe wurde vom Thermistor bestätigt — alle Apnoen stammen vom Nasendruck. Im Zweifel das Thermistor-Signal visuell prüfen.</i>",
    },
    # Kolommen die uit de losse geschiedenislijst naar de ene lijst zijn
    # meegekomen (v0.18.3).
    "col_oahi_tooltip": {"nl": "Obstructieve apneu-hypopneu-index: obstructieve en gemengde apneus plus obstructieve hypopneeën per uur slaap.", "fr": "Index d'apnées-hypopnées obstructives : apnées obstructives et mixtes plus hypopnées obstructives par heure de sommeil.", "en": "Obstructive apnea-hypopnea index: obstructive and mixed apneas plus obstructive hypopneas per hour of sleep.", "de": "Obstruktiver Apnoe-Hypopnoe-Index: obstruktive und gemischte Apnoen plus obstruktive Hypopnoen pro Stunde Schlaf."},
    "col_type":         {"nl": "Type", "fr": "Type", "en": "Type", "de": "Typ"},
    "col_type_tooltip": {"nl": "CSAS wanneer de helft of meer van de apneus centraal is, anders OSAS.", "fr": "SACS lorsque la moitié ou plus des apnées sont centrales, sinon SAOS.", "en": "CSAS when half or more of the apneas are central, otherwise OSAS.", "de": "CSAS, wenn die Hälfte oder mehr der Apnoen zentral sind, sonst OSAS."},
    # ── EDF-anonimisatie: twee routes, en het verschil is waar de
    # identificeerbare header terechtkomt.
    "anon_title":        {"nl": "Anonimisatie", "fr": "Anonymisation", "en": "Anonymisation", "de": "Anonymisierung"},
    "anon_client":       {"nl": "Anoniem opladen", "fr": "Téléverser anonymisé", "en": "Upload anonymised", "de": "Anonymisiert hochladen"},
    "anon_client_desc":  {"nl": "De header wordt in uw browser herschreven vóór verzenden. Naam, geboortedatum, patiënt-ID, ziekenhuis en technicus verlaten deze computer niet. De signaaldata blijft ongewijzigd.", "fr": "L'en-tête est réécrit dans votre navigateur avant l'envoi. Nom, date de naissance, identifiant, hôpital et technicien ne quittent pas cet ordinateur. Les données du signal restent inchangées.", "en": "The header is rewritten in your browser before sending. Name, date of birth, patient ID, hospital and technician never leave this computer. The signal data is unchanged.", "de": "Der Header wird im Browser vor dem Senden überschrieben. Name, Geburtsdatum, Patienten-ID, Klinik und Techniker verlassen diesen Rechner nicht. Die Signaldaten bleiben unverändert."},
    "anon_server":       {"nl": "Opladen zoals het is, daarna anonimiseren", "fr": "Téléverser tel quel, anonymiser ensuite", "en": "Upload as is, anonymise afterwards", "de": "Unverändert hochladen, danach anonymisieren"},
    "anon_server_desc":  {"nl": "Het bestand komt ongewijzigd op de server; op de volgende pagina ziet u de headervelden en kunt u ze daar wissen. Kies dit alleen wanneer u de header eerst wilt kunnen nakijken.", "fr": "Le fichier arrive inchangé sur le serveur ; à la page suivante vous voyez les champs d'en-tête et pouvez les effacer. À ne choisir que si vous devez d'abord vérifier l'en-tête.", "en": "The file reaches the server unchanged; on the next page you see the header fields and can clear them there. Choose this only when you need to inspect the header first.", "de": "Die Datei erreicht den Server unverändert; auf der nächsten Seite sehen Sie die Header-Felder und können sie dort löschen. Nur wählen, wenn Sie den Header zuerst prüfen müssen."},
    "anon_code_label":   {"nl": "Studienummer of label (optioneel)", "fr": "Numéro d'étude ou libellé (facultatif)", "en": "Study number or label (optional)", "de": "Studiennummer oder Label (optional)"},
    "anon_code_placeholder": {"nl": "bv. AZORG-2026-014", "fr": "p. ex. AZORG-2026-014", "en": "e.g. AZORG-2026-014", "de": "z. B. AZORG-2026-014"},
    "anon_code_hint":    {"nl": "Komt in het bestand te staan in plaats van de patiëntgegevens. Gebruik géén naam of geboortedatum. Laat leeg voor een automatische code die voor dezelfde opname altijd hetzelfde is.", "fr": "Sera inscrit dans le fichier à la place des données patient. N'utilisez ni nom ni date de naissance. Laissez vide pour un code automatique, identique pour un même enregistrement.", "en": "Goes into the file in place of the patient data. Do not use a name or date of birth. Leave empty for an automatic code that is always the same for the same recording.", "de": "Steht in der Datei anstelle der Patientendaten. Verwenden Sie weder Name noch Geburtsdatum. Leer lassen für einen automatischen Code, der für dieselbe Aufnahme stets gleich ist."},
    "anon_before":       {"nl": "Stond in de header:", "fr": "Dans l'en-tête :", "en": "Was in the header:", "de": "Stand im Header:"},
    "anon_after":        {"nl": "Wordt verzonden als:", "fr": "Sera envoyé comme :", "en": "Will be sent as:", "de": "Wird gesendet als:"},
    "anon_current_header": {"nl": "Nu in de header:", "fr": "Actuellement dans l'en-tête :", "en": "Currently in the header:", "de": "Aktuell im Header:"},
    "anon_failed":       {"nl": "Anonimisatie mislukt — er is niets verzonden of gewijzigd", "fr": "Échec de l'anonymisation — rien n'a été envoyé ni modifié", "en": "Anonymisation failed — nothing was sent or changed", "de": "Anonymisierung fehlgeschlagen — nichts wurde gesendet oder geändert"},
    "anon_server_pending": {"nl": "Wordt ongewijzigd opgeladen; anonimiseren kan op de volgende pagina", "fr": "Téléversé tel quel ; anonymisation possible à la page suivante", "en": "Uploaded unchanged; you can anonymise on the next page", "de": "Unverändert hochgeladen; Anonymisierung auf der nächsten Seite möglich"},
    "anon_panel_title":  {"nl": "EDF-header", "fr": "En-tête EDF", "en": "EDF header", "de": "EDF-Header"},
    "anon_present":      {"nl": "identificeerbaar", "fr": "identifiable", "en": "identifiable", "de": "identifizierbar"},
    "anon_clean":        {"nl": "anoniem", "fr": "anonyme", "en": "anonymous", "de": "anonym"},
    "anon_clean_desc":   {"nl": "Deze header bevat geen naam, geboortedatum of patiënt-ID meer.", "fr": "Cet en-tête ne contient plus de nom, date de naissance ni identifiant.", "en": "This header no longer contains a name, date of birth or patient ID.", "de": "Dieser Header enthält keinen Namen, kein Geburtsdatum und keine Patienten-ID mehr."},
    "anon_do_now":       {"nl": "Anonimiseer dit bestand nu", "fr": "Anonymiser ce fichier maintenant", "en": "Anonymise this file now", "de": "Diese Datei jetzt anonymisieren"},
    "anon_irreversible": {"nl": "Dit herschrijft het bestand op de server en is niet terug te draaien.", "fr": "Ceci réécrit le fichier sur le serveur et est irréversible.", "en": "This rewrites the file on the server and cannot be undone.", "de": "Dies überschreibt die Datei auf dem Server und ist nicht rückgängig zu machen."},
    "anon_done":         {"nl": "EDF-header geanonimiseerd. De signaaldata is ongewijzigd.", "fr": "En-tête EDF anonymisé. Les données du signal sont inchangées.", "en": "EDF header anonymised. The signal data is unchanged.", "de": "EDF-Header anonymisiert. Die Signaldaten sind unverändert."},
    # Herkomstblok: welk kanaal voedde welke analyse. Zonder dit beschrijft het
    # rapport de methode in plaats van de uitvoering, en zijn twee runs van
    # dezelfde nacht niet te vergelijken zonder de logs erbij.
    "rpt_sec_provenance": {"nl": "Herkomst — welk kanaal voedde welke analyse", "fr": "Provenance — quel canal a alimenté quelle analyse", "en": "Provenance — which channel fed which analysis", "de": "Herkunft — welcher Kanal welche Analyse gespeist hat"},
    "pdf_rec_time":      {"nl": "Registratietijd", "fr": "Temps d'enregistrement", "en": "Recording time", "de": "Aufzeichnungszeit"},
    "pdf_rei_denominator": {"nl": "REI-noemer", "fr": "Dénominateur IER", "en": "REI denominator", "de": "REI-Nenner"},
    "prov_ch_absent":    {"nl": "niet in dit EDF-bestand", "fr": "absent de ce fichier EDF", "en": "not present in this EDF file", "de": "nicht in dieser EDF-Datei"},
    "prov_env_overrides": {"nl": "Afwijkende parameters (omgeving)",
                          "fr": "Paramètres modifiés (environnement)",
                          "en": "Overridden parameters (environment)",
                          "de": "Abweichende Parameter (Umgebung)"},
    "prov_arousal_eeg":  {"nl": "Arousal-analyse — EEG", "fr": "Analyse des micro-éveils — EEG", "en": "Arousal analysis — EEG", "de": "Arousal-Analyse — EEG"},
    "prov_staging_eeg":  {"nl": "Slaapstaging — EEG",  "fr": "Stades du sommeil — EEG", "en": "Sleep staging — EEG", "de": "Schlafstadien — EEG"},
    "prov_staging_eog":  {"nl": "Slaapstaging — EOG",  "fr": "Stades du sommeil — EOG", "en": "Sleep staging — EOG", "de": "Schlafstadien — EOG"},
    "prov_staging_emg":  {"nl": "Slaapstaging — EMG",  "fr": "Stades du sommeil — EMG", "en": "Sleep staging — EMG", "de": "Schlafstadien — EMG"},
    "prov_apnea":        {"nl": "Apneudetectie",       "fr": "Détection des apnées",    "en": "Apnea detection",     "de": "Apnoe-Detektion"},
    "prov_hypopnea":     {"nl": "Hypopneudetectie",    "fr": "Détection des hypopnées", "en": "Hypopnea detection",  "de": "Hypopnoe-Detektion"},
    "prov_reference":    {"nl": "Afgeleide analyses (AHI-spreiding, baseline, arousal-koppeling, CSR, ventilatoire last)", "fr": "Analyses dérivées (dispersion IAH, ligne de base, couplage micro-éveils, CSR, charge ventilatoire)", "en": "Derived analyses (AHI sweep, baseline, arousal coupling, CSR, ventilatory burden)", "de": "Abgeleitete Analysen (AHI-Streuung, Baseline, Arousal-Kopplung, CSR, ventilatorische Last)"},
    "prov_thermistor":   {"nl": "Thermistor",          "fr": "Thermistance",            "en": "Thermistor",          "de": "Thermistor"},
    "prov_therm_usable":   {"nl": "bruikbaar",         "fr": "utilisable",              "en": "usable",              "de": "brauchbar"},
    "prov_therm_rejected": {"nl": "afgekeurd door kwaliteitscontrole", "fr": "rejetée par le contrôle qualité", "en": "rejected by quality check", "de": "von der Qualitätsprüfung abgelehnt"},
    # v0.19.0: per-gebruiker voorgeselecteerd scoringsprofiel.
    "default_profile":      {"nl": "Standaardprofiel", "fr": "Profil par défaut", "en": "Default profile", "de": "Standardprofil"},
    "default_profile_hint": {"nl": "Dit profiel staat voorgeselecteerd bij elke nieuwe analyse van deze gebruiker. Hij kan het per opname nog altijd wijzigen.", "fr": "Ce profil est présélectionné pour chaque nouvelle analyse de cet utilisateur. Il reste modifiable par enregistrement.", "en": "This profile is preselected for every new analysis by this user. It can still be changed per recording.", "de": "Dieses Profil ist bei jeder neuen Analyse dieses Benutzers vorausgewählt. Pro Aufnahme weiterhin änderbar."},
    "profile_app_default":  {"nl": "applicatiestandaard", "fr": "valeur par défaut de l'application", "en": "application default", "de": "Anwendungsstandard"},
    "profile_saved":        {"nl": "standaardprofiel opgeslagen", "fr": "profil par défaut enregistré", "en": "default profile saved", "de": "Standardprofil gespeichert"},
    "profile_invalid":      {"nl": "onbekend scoringsprofiel — niets gewijzigd", "fr": "profil de scoring inconnu — rien n'a été modifié", "en": "unknown scoring profile — nothing changed", "de": "unbekanntes Scoring-Profil — nichts geändert"},
    # Vierde geval: onder de drempel maar behouden omdat het profiel additief
    # is. "Bruikbaar" noemen was fout — het rapport sprak zichzelf tegen met de
    # corroboratiekolom, die liet zien dat de sensor niets had bijgedragen.
    "prov_therm_additive": {"nl": "onder de kwaliteitsdrempel, additief gebruikt — mag events toevoegen, niet afwijzen", "fr": "sous le seuil de qualité, utilisée en additif — peut ajouter des événements, pas en rejeter", "en": "below the quality threshold, used additively — may add events, never reject them", "de": "unter der Qualitätsschwelle, additiv genutzt — darf Ereignisse hinzufügen, nicht verwerfen"},
    "prov_therm_absent":   {"nl": "niet in montage",   "fr": "absente du montage",      "en": "not in montage",      "de": "nicht in der Montage"},
    "prov_profile":      {"nl": "Scoringsprofiel",     "fr": "Profil de scoring",       "en": "Scoring profile",     "de": "Scoring-Profil"},
    "prov_software":     {"nl": "Software",            "fr": "Logiciel",                "en": "Software",            "de": "Software"},
    "prov_note":         {"nl": "<i>De kanaalkeuze bepaalt het resultaat. Wijkt een van deze regels af van wat u verwachtte, dan is het rapport niet vergelijkbaar met een run waarin de keuze anders was.</i>", "fr": "<i>Le choix des canaux détermine le résultat. Si l'une de ces lignes diffère de ce que vous attendiez, ce rapport n'est pas comparable à une analyse avec un autre choix.</i>", "en": "<i>The channel selection determines the result. If any row differs from what you expected, this report is not comparable to a run with a different selection.</i>", "de": "<i>Die Kanalauswahl bestimmt das Ergebnis. Weicht eine Zeile von der Erwartung ab, ist dieser Bericht nicht mit einem Lauf mit anderer Auswahl vergleichbar.</i>"},
    # Hartfrequentie: robuuste tegenhangers van min/max, plus de reden waarom
    # het extremum niet getoond wordt.
    "pdf_hr_p1":  {"nl": "Hartfrequentie p1",  "fr": "Fréquence cardiaque p1",  "en": "Heart rate p1",  "de": "Herzfrequenz p1"},
    "pdf_hr_p99": {"nl": "Hartfrequentie p99", "fr": "Fréquence cardiaque p99", "en": "Heart rate p99", "de": "Herzfrequenz p99"},
    "pdf_hr_unreliable": {
        "nl": "<i>Minimum en maximum zijn hier niet betrouwbaar te bepalen ({reason}); getoond zijn de 1e en 99e percentiel. Een gerapporteerd minimum ligt in dat geval op de ondergrens van het plausibiliteitsfilter en niet bij de patiënt.</i>",
        "fr": "<i>Le minimum et le maximum ne sont pas fiables ici ({reason}) ; les 1er et 99e percentiles sont affichés. Un minimum rapporté correspond alors à la limite inférieure du filtre de plausibilité, pas au patient.</i>",
        "en": "<i>Minimum and maximum cannot be determined reliably here ({reason}); the 1st and 99th percentiles are shown instead. A reported minimum in that case sits at the lower bound of the plausibility filter, not at the patient.</i>",
        "de": "<i>Minimum und Maximum sind hier nicht zuverlässig bestimmbar ({reason}); gezeigt werden das 1. und 99. Perzentil. Ein berichtetes Minimum liegt dann an der Untergrenze des Plausibilitätsfilters, nicht beim Patienten.</i>",
    },
    # Hypoxic burden bij aanhoudende hypoxemie.
    "pdf_hb_sustained_hypoxemia": {
        "nl": "<i>Bij aanhoudende hypoxemie onderschat de hypoxic burden de totale zuurstoflast: hij meet event-gerelateerde desaturatie ten opzichte van de baseline, en die ligt hier al laag. Beoordeel samen met T90 en baseline-SpO₂.</i>",
        "fr": "<i>En cas d'hypoxémie soutenue, la charge hypoxique sous-estime la charge totale en oxygène : elle mesure la désaturation liée aux événements par rapport à la ligne de base, déjà basse ici. À interpréter avec le T90 et la SpO₂ de base.</i>",
        "en": "<i>Under sustained hypoxemia the hypoxic burden underestimates the total oxygen load: it measures event-related desaturation relative to baseline, and that baseline is already low here. Interpret together with T90 and baseline SpO₂.</i>",
        "de": "<i>Bei anhaltender Hypoxämie unterschätzt die hypoxische Last die gesamte Sauerstofflast: sie misst ereignisbezogene Entsättigung relativ zur Baseline, und diese liegt hier bereits niedrig. Zusammen mit T90 und Baseline-SpO₂ beurteilen.</i>",
    },
    # Flattening labels
    "pdf_flat_normal":   {"nl": "normaal",                "fr": "normal",                  "en": "normal",                  "de": "normal"},
    "pdf_flat_elevated": {"nl": "verhoogd",               "fr": "élevé",                   "en": "elevated",                "de": "erhöht"},
    "pdf_flat_high":     {"nl": "hoog (flow-limitatie)",  "fr": "élevé (limitation de flux)","en":"high (flow limitation)",  "de": "hoch (Flusslimitierung)"},
    # Arousal table
    "pdf_arousal_index": {"nl": "Arousal index (AI)", "fr": "Index d'éveils (AI)", "en": "Arousal index (AI)", "de": "Arousal-Index (AI)"},
}
TRANSLATIONS.update(_V0102_PDF)


# ═══════════════════════════════════════════════════════════
# v0.10.3: Analysis-section Dutch leaks reported by user 2026-05-12
#   channel_select pneumo labels (Been links, Positie, Snurk, ...),
#   upload page, job_status, results_extended, scorer_v12, report_editor
# ═══════════════════════════════════════════════════════════
_V0103_ANALYSIS = {
    # Pneumo channel labels (channel_select.html L207-216)
    "ch_flow_label":      {"nl": "🌬️ Flow (algemeen)",    "fr": "🌬️ Flux (général)",        "en": "🌬️ Flow (generic)",        "de": "🌬️ Fluss (allgemein)"},
    "ch_flow_desc":       {"nl": "Terugval als de twee sensoren hieronder ontbreken", "fr": "Repli si les deux capteurs ci-dessous manquent", "en": "Fallback when the two sensors below are missing", "de": "Rückfall, wenn die beiden Sensoren unten fehlen"},
    # AASM schrijft twee sensoren voor: apneus op de oronasale thermistor,
    # hypopneeën op de nasale druk. Die twee rollen waren niet instelbaar —
    # ze kwamen uitsluitend uit auto-detectie, en bij Somnomedics ("Flow Th.")
    # faalde die, waarna apneus stilzwijgend op de neusdruk werden gescoord.
    "ch_flow_pressure_label": {"nl": "🌬️ Nasale druk (hypopneu)", "fr": "🌬️ Pression nasale (hypopnée)", "en": "🌬️ Nasal pressure (hypopnea)", "de": "🌬️ Nasendruck (Hypopnoe)"},
    "ch_flow_pressure_desc":  {"nl": "AASM-sensor voor hypopneeën", "fr": "Capteur AASM pour les hypopnées", "en": "AASM sensor for hypopneas", "de": "AASM-Sensor für Hypopnoen"},
    "ch_flow_therm_label":    {"nl": "🌡️ Thermistor (apneu)", "fr": "🌡️ Thermistance (apnée)", "en": "🌡️ Thermistor (apnea)", "de": "🌡️ Thermistor (Apnoe)"},
    "ch_flow_therm_desc":     {"nl": "AASM-sensor voor apneus", "fr": "Capteur AASM pour les apnées", "en": "AASM sensor for apneas", "de": "AASM-Sensor für Apnoen"},
    "ch_thorax_label":    {"nl": "📊 Thorax",                "fr": "📊 Thorax",                  "en": "📊 Thorax",                  "de": "📊 Thorax"},
    "ch_thorax_desc":     {"nl": "Thoracale effort",         "fr": "Effort thoracique",          "en": "Thoracic effort",            "de": "Thorakale Atemanstrengung"},
    "ch_abdomen_label":   {"nl": "📊 Abdomen",               "fr": "📊 Abdomen",                 "en": "📊 Abdomen",                 "de": "📊 Abdomen"},
    "ch_abdomen_desc":    {"nl": "Abdominale effort",        "fr": "Effort abdominal",           "en": "Abdominal effort",           "de": "Abdominale Atemanstrengung"},
    "ch_spo2_label":      {"nl": "💉 SpO2",                  "fr": "💉 SpO2",                    "en": "💉 SpO2",                    "de": "💉 SpO2"},
    "ch_spo2_desc":       {"nl": "Pulse oximetrie",          "fr": "Oxymétrie de pouls",         "en": "Pulse oximetry",             "de": "Pulsoximetrie"},
    "ch_leg_l_label":     {"nl": "🦵 Been links",            "fr": "🦵 Jambe gauche",            "en": "🦵 Left leg",                "de": "🦵 Linkes Bein"},
    "ch_leg_l_desc":      {"nl": "Tibialis anterior links",  "fr": "Tibial antérieur gauche",    "en": "Left tibialis anterior",     "de": "Tibialis anterior links"},
    "ch_leg_r_label":     {"nl": "🦵 Been rechts",           "fr": "🦵 Jambe droite",            "en": "🦵 Right leg",               "de": "🦵 Rechtes Bein"},
    "ch_leg_r_desc":      {"nl": "Tibialis anterior rechts", "fr": "Tibial antérieur droit",     "en": "Right tibialis anterior",    "de": "Tibialis anterior rechts"},
    # Eén ongezijderd beenkanaal. Toewijzen aan links of rechts zou beweren
    # dat er een zijde bekend is; psgscoring behandelt deze rol apart, want
    # de bilaterale ontdubbeling kan op één kanaal niet draaien.
    "ch_leg_label":       {"nl": "🦵 Been (één kanaal)",     "fr": "🦵 Jambe (canal unique)",    "en": "🦵 Leg (single channel)",    "de": "🦵 Bein (ein Kanal)"},
    "ch_leg_desc":        {"nl": "Tibialis, zijde onbekend", "fr": "Tibial, côté inconnu",       "en": "Tibialis, side unknown",     "de": "Tibialis, Seite unbekannt"},
    "ch_position_label":  {"nl": "🔄 Positie",               "fr": "🔄 Position",                "en": "🔄 Position",                "de": "🔄 Position"},
    "ch_position_desc":   {"nl": "Lichaamshouding",          "fr": "Position du corps",          "en": "Body position",              "de": "Körperposition"},
    "ch_snore_label":     {"nl": "🔊 Snurk",                 "fr": "🔊 Ronflement",              "en": "🔊 Snore",                   "de": "🔊 Schnarchen"},
    "ch_snore_desc":      {"nl": "Snurkmicrofoon",           "fr": "Microphone de ronflement",   "en": "Snoring microphone",         "de": "Schnarchmikrofon"},
    "ch_pulse_label":     {"nl": "❤️ Hartritme",             "fr": "❤️ Fréquence cardiaque",     "en": "❤️ Heart rate",              "de": "❤️ Herzfrequenz"},
    "ch_pulse_desc":      {"nl": "Pulse / HR",               "fr": "Pouls / FC",                 "en": "Pulse / HR",                 "de": "Puls / HR"},
    "ch_ecg_label":       {"nl": "💓 ECG",                   "fr": "💓 ECG",                     "en": "💓 ECG",                     "de": "💓 EKG"},
    "ch_ecg_desc":        {"nl": "Electrocardiogram",        "fr": "Électrocardiogramme",        "en": "Electrocardiogram",          "de": "Elektrokardiogramm"},

    # index.html upload card
    "upload_card_title": {"nl": "📂 EDF-bestand uploaden", "fr": "📂 Téléverser un fichier EDF", "en": "📂 Upload an EDF file", "de": "📂 EDF-Datei hochladen"},
    "upload_card_sub":   {"nl": "Polysomnografie-opname in European Data Format (.edf) — max 500 MB",
                          "fr": "Enregistrement de polysomnographie au format European Data Format (.edf) — 500 Mo max",
                          "en": "Polysomnography recording in European Data Format (.edf) — max 500 MB",
                          "de": "Polysomnographie-Aufnahme im European Data Format (.edf) — max. 500 MB"},
    "upload_drop_browse": {"nl": "Klik om te bladeren", "fr": "Cliquez pour parcourir", "en": "Click to browse", "de": "Zum Durchsuchen klicken"},
    "upload_drop_or_drag":{"nl": "of sleep een .edf bestand hiernaartoe", "fr": "ou faites glisser un fichier .edf ici", "en": "or drag an .edf file here", "de": "oder ziehen Sie eine .edf-Datei hierher"},
    "invalid_edf_file":   {"nl": "Selecteer een geldig .edf bestand.", "fr": "Veuillez sélectionner un fichier .edf valide.", "en": "Please select a valid .edf file.", "de": "Bitte wählen Sie eine gültige .edf-Datei aus."},

    # job_status.html
    "retry":                  {"nl": "Opnieuw proberen",     "fr": "Réessayer",                "en": "Retry",                "de": "Erneut versuchen"},
    "check_edf_channels":     {"nl": "Controleer het EDF-bestand en de kanaalkeuze.", "fr": "Vérifiez le fichier EDF et la sélection des canaux.", "en": "Check the EDF file and the channel selection.", "de": "Bitte überprüfen Sie die EDF-Datei und die Kanalauswahl."},
    "timeout_60min":          {"nl": "Time-out na 60 minuten.", "fr": "Délai dépassé après 60 minutes.", "en": "Timed out after 60 minutes.", "de": "Zeitüberschreitung nach 60 Minuten."},
    "error_occurred":         {"nl": "Fout opgetreden", "fr": "Erreur survenue", "en": "An error occurred", "de": "Fehler aufgetreten"},

    # scorer_v12.html keyboard shortcut help
    "kbd_assign_stage":   {"nl": "Stage toekennen (Wake/N1/N2/N3/REM)", "fr": "Assigner un stade (Wake/N1/N2/N3/REM)", "en": "Assign stage (Wake/N1/N2/N3/REM)", "de": "Stadium zuweisen (Wake/N1/N2/N3/REM)"},
    "kbd_prev_next_hyp":  {"nl": "Vorige / volgende epoch (hypnogram)", "fr": "Époque précédente / suivante (hypnogramme)", "en": "Previous / next epoch (hypnogram)", "de": "Vorherige / nächste Epoche (Hypnogramm)"},
    "kbd_prev_next_edf":  {"nl": "Vorige / volgende epoch (EDF viewer)", "fr": "Époque précédente / suivante (visionneuse EDF)", "en": "Previous / next epoch (EDF viewer)", "de": "Vorherige / nächste Epoche (EDF-Viewer)"},
    "kbd_begin_end":      {"nl": "Begin / einde opname", "fr": "Début / fin de l'enregistrement", "en": "Start / end of recording", "de": "Anfang / Ende der Aufnahme"},
    "kbd_undo":           {"nl": "Ongedaan maken (staging)", "fr": "Annuler (staging)", "en": "Undo (staging)", "de": "Rückgängig (Staging)"},
    "kbd_zoom":           {"nl": "Zoom: 30s / 60s / 150s / 300s", "fr": "Zoom : 30 s / 60 s / 150 s / 300 s", "en": "Zoom: 30s / 60s / 150s / 300s", "de": "Zoom: 30 s / 60 s / 150 s / 300 s"},
    "kbd_tool_obs":       {"nl": "Tool: Obstructief apnea", "fr": "Outil : Apnée obstructive", "en": "Tool: Obstructive apnea", "de": "Werkzeug: Obstruktive Apnoe"},
    "kbd_tool_ca":        {"nl": "Tool: Centraal apnea", "fr": "Outil : Apnée centrale", "en": "Tool: Central apnea", "de": "Werkzeug: Zentrale Apnoe"},
    "kbd_tool_mixed":     {"nl": "Tool: Gemengd apnea", "fr": "Outil : Apnée mixte", "en": "Tool: Mixed apnea", "de": "Werkzeug: Gemischte Apnoe"},
    "kbd_tool_hyp":       {"nl": "Tool: Hypopnea", "fr": "Outil : Hypopnée", "en": "Tool: Hypopnea", "de": "Werkzeug: Hypopnoe"},
    "kbd_tool_arousal":   {"nl": "Tool: Arousal", "fr": "Outil : Éveil", "en": "Tool: Arousal", "de": "Werkzeug: Arousal"},
    "kbd_tool_rera":      {"nl": "Tool: RERA", "fr": "Outil : RERA", "en": "Tool: RERA", "de": "Werkzeug: RERA"},
    "kbd_help_toggle":    {"nl": "Deze help tonen/verbergen", "fr": "Afficher/masquer cette aide", "en": "Show/hide this help", "de": "Diese Hilfe ein-/ausblenden"},
    "kbd_next_prev_event":{"nl": "Volgend/vorig event (huidige filter)", "fr": "Événement suivant/précédent (filtre actif)", "en": "Next/previous event (active filter)", "de": "Nächstes/vorheriges Ereignis (aktiver Filter)"},
    "kbd_jump10":         {"nl": "±10 epochs (5 min)", "fr": "±10 époques (5 min)", "en": "±10 epochs (5 min)", "de": "±10 Epochen (5 Min)"},
    "kbd_jump_transition":{"nl": "Spring naar stage-overgang", "fr": "Aller à la transition de stade", "en": "Jump to stage transition", "de": "Zum Stadienwechsel springen"},
    "kbd_scroll_channel": {"nl": "op kanaalnaam", "fr": "sur le nom du canal", "en": "on channel name", "de": "auf Kanalnamen"},
    "kbd_scroll_signal":  {"nl": "op signaal", "fr": "sur le signal", "en": "on the signal", "de": "auf das Signal"},
    "kbd_amp_per_channel":{"nl": "Per-kanaal amplitude aanpassen", "fr": "Ajuster l'amplitude par canal", "en": "Per-channel amplitude adjust", "de": "Amplitude pro Kanal anpassen"},
    "kbd_amp_global":     {"nl": "Globale amplitude aanpassen", "fr": "Ajuster l'amplitude globale", "en": "Adjust global amplitude", "de": "Globale Amplitude anpassen"},

    # Generic "load failed"
    "load_failed":          {"nl": "Laden mislukt", "fr": "Échec du chargement", "en": "Load failed", "de": "Laden fehlgeschlagen"},

    # results_extended.html artifact table
    "col_max_amplitude": {"nl": "Max amplitude (μV)", "fr": "Amplitude max. (μV)", "en": "Max amplitude (μV)", "de": "Max. Amplitude (μV)"},
    "col_flat_signal":   {"nl": "Vlak signaal",       "fr": "Signal plat",        "en": "Flat signal",      "de": "Flaches Signal"},
    "col_high_amp":      {"nl": "Hoge amplitude",     "fr": "Amplitude élevée",   "en": "High amplitude",   "de": "Hohe Amplitude"},

    # EDF+ notification (results_extended.html)
    "edf_ready_title":      {"nl": "EDF+ klaar!", "fr": "EDF+ prêt !", "en": "EDF+ ready!", "de": "EDF+ fertig!"},
    "edf_ready_msg":        {"nl": "Het gescoorde EDF+ bestand is beschikbaar voor download.", "fr": "Le fichier EDF+ scoré est disponible au téléchargement.", "en": "The scored EDF+ file is available for download.", "de": "Die gescorte EDF+-Datei steht zum Download bereit."},
    "edf_ready_btn_title":  {"nl": "EDF+ klaar — klik om te downloaden", "fr": "EDF+ prêt — cliquez pour télécharger", "en": "EDF+ ready — click to download", "de": "EDF+ fertig — zum Herunterladen klicken"},
    "edf_generate":         {"nl": "Genereer EDF+", "fr": "Générer EDF+", "en": "Generate EDF+", "de": "EDF+ erzeugen"},
    "edf_generate_title":   {"nl": "Klik om EDF+ op de achtergrond te genereren (enkele minuten)", "fr": "Cliquer pour générer EDF+ en arrière-plan (quelques minutes)", "en": "Click to generate EDF+ in the background (a few minutes)", "de": "Klicken, um EDF+ im Hintergrund zu erzeugen (einige Minuten)"},
    "close_btn":            {"nl": "Sluiten", "fr": "Fermer", "en": "Close", "de": "Schließen"},
}
TRANSLATIONS.update(_V0103_ANALYSIS)


# ═══════════════════════════════════════════════════════════
# v0.10.4: report_editor.html — verification card, header card,
#          JS strings, diagnosis quick-add labels
# ═══════════════════════════════════════════════════════════
_V0104_EDITOR = {
    # Verification card
    "verif_card_title":   {"nl": "Verificatie rapport",                 "fr": "Vérification du rapport",                 "en": "Report verification",                "de": "Berichtverifizierung"},
    "verif_card_intro":   {"nl": "Geef aan of dit rapport geverifieerd werd door een slaaptechnicus of arts. Dit wordt vermeld in de disclaimer onderaan het PDF-rapport.",
                           "fr": "Indiquez si ce rapport a été vérifié par un technicien du sommeil ou un médecin. L'information est ajoutée à la clause de non-responsabilité au bas du rapport PDF.",
                           "en": "Indicate whether this report has been verified by a sleep technician or physician. This is shown in the disclaimer at the bottom of the PDF report.",
                           "de": "Geben Sie an, ob dieser Bericht von einer schlafmedizinischen Fachkraft oder einer Ärztin/einem Arzt überprüft wurde. Dies wird im Haftungsausschluss am Ende des PDF-Berichts vermerkt."},
    "verif_not_verified": {"nl": "niet geverifieerd",   "fr": "non vérifié",          "en": "not verified",            "de": "nicht überprüft"},
    "verif_role_tech":    {"nl": "Slaaptechnicus",      "fr": "Technicien du sommeil","en": "Sleep technician",        "de": "Schlafmedizinische Fachkraft"},
    "verif_role_phys":    {"nl": "Arts",                "fr": "Médecin",              "en": "Physician",               "de": "Ärztin/Arzt"},
    "verif_name_label":   {"nl": "Naam verificateur",   "fr": "Nom du vérificateur",  "en": "Verifier name",           "de": "Name der prüfenden Person"},
    "verif_name_ph":      {"nl": "Naam technicus of arts","fr": "Nom du technicien ou du médecin","en": "Technician or physician name","de": "Name der Fachkraft oder Ärztin/Arzt"},
    "verif_date_label":   {"nl": "Datum verificatie",   "fr": "Date de vérification", "en": "Verification date",       "de": "Verifizierungsdatum"},

    # Report header / logo card
    "rh_intro":           {"nl": "Pas de naam en het logo in de header van het PDF-rapport aan (bijv. ziekenhuis, kliniek).",
                           "fr": "Modifiez le nom et le logo dans l'en-tête du rapport PDF (ex. hôpital, clinique).",
                           "en": "Customize the name and logo in the header of the PDF report (e.g. hospital, clinic).",
                           "de": "Passen Sie den Namen und das Logo in der Kopfzeile des PDF-Berichts an (z. B. Krankenhaus, Klinik)."},
    "rh_inst_label":      {"nl": "Naam instelling (header)", "fr": "Nom de l'établissement (en-tête)", "en": "Institution name (header)", "de": "Name der Einrichtung (Kopfzeile)"},
    "rh_logo_upload":     {"nl": "Logo uploaden (PNG/JPG, max 500KB)", "fr": "Téléverser un logo (PNG/JPG, max. 500 Ko)", "en": "Upload logo (PNG/JPG, max 500 KB)", "de": "Logo hochladen (PNG/JPG, max. 500 KB)"},
    "rh_current_logo":    {"nl": "Huidig logo",         "fr": "Logo actuel",         "en": "Current logo",         "de": "Aktuelles Logo"},
    "rh_default_azorg":   {"nl": "standaard: AZORG",    "fr": "par défaut : AZORG",  "en": "default: AZORG",       "de": "Standard: AZORG"},
    "rh_use_other_logo":  {"nl": "Gebruik ander logo",  "fr": "Utiliser un autre logo","en": "Use a different logo","de": "Anderes Logo verwenden"},

    # Diagnosis quick-add button labels (short forms used as ＋ buttons)
    "dx_normal":          {"nl": "Normaal",         "fr": "Normal",         "en": "Normal",          "de": "Normal"},
    "dx_mild_osas":       {"nl": "Mild OSAS",       "fr": "SAOS léger",     "en": "Mild OSAS",       "de": "Leichtes OSAS"},
    "dx_moderate_osas":   {"nl": "Matig OSAS",      "fr": "SAOS modéré",    "en": "Moderate OSAS",   "de": "Mittelschweres OSAS"},
    "dx_severe_osas":     {"nl": "Ernstig OSAS",    "fr": "SAOS sévère",    "en": "Severe OSAS",     "de": "Schweres OSAS"},
    "dx_plms":            {"nl": "PLMS",            "fr": "MPJS",           "en": "PLMS",            "de": "PLMS"},
    "dx_insomnia":        {"nl": "Insomnie",        "fr": "Insomnie",       "en": "Insomnia",        "de": "Insomnie"},
    "dx_weight_loss":     {"nl": "Gewichtsreductie","fr": "Perte de poids", "en": "Weight loss",     "de": "Gewichtsabnahme"},
    "dx_csa":             {"nl": "Centraal SA",     "fr": "SA central",     "en": "Central SA",      "de": "Zentrale SA"},
    "dx_csr":             {"nl": "Cheyne-Stokes",   "fr": "Cheyne-Stokes",  "en": "Cheyne-Stokes",   "de": "Cheyne-Stokes"},

    # Save flow JS strings
    "saving_ellipsis":    {"nl": "Opslaan…",         "fr": "Enregistrement…", "en": "Saving…",        "de": "Speichern…"},
    "logo_too_large":     {"nl": "Logo te groot (max 500KB)", "fr": "Logo trop volumineux (max. 500 Ko)", "en": "Logo too large (max 500 KB)", "de": "Logo zu groß (max. 500 KB)"},
    "pdf_regenerated":    {"nl": "PDF vernieuwd",    "fr": "PDF régénéré",   "en": "PDF refreshed",   "de": "PDF erneuert"},
    "edfplus_regenerated":{"nl": "EDF+ vernieuwd",   "fr": "EDF+ régénéré",  "en": "EDF+ refreshed",  "de": "EDF+ erneuert"},
    "saved_but":          {"nl": "Opgeslagen maar:", "fr": "Enregistré mais :", "en": "Saved but:",   "de": "Gespeichert, aber:"},
    "unknown_error":      {"nl": "onbekende fout",   "fr": "erreur inconnue", "en": "unknown error",  "de": "unbekannter Fehler"},
}
TRANSLATIONS.update(_V0104_EDITOR)


# ═══════════════════════════════════════════════════════════
# v0.10.5: full-codebase sweep — remaining Dutch leaks
# ═══════════════════════════════════════════════════════════
_V0105_SWEEP = {
    # dashboard.html — failed status badge
    "status_failed_short": {"nl": "Mislukt", "fr": "Échec", "en": "Failed", "de": "Fehlgeschlagen"},

    # index.html — feature cards
    "feat_staging_title": {"nl": "Slaapstaging",   "fr": "Stadification du sommeil", "en": "Sleep staging",   "de": "Schlafstadien"},
    "feat_staging_body":  {"nl": "Automatisch hypnogram via YASA machine learning",
                           "fr": "Hypnogramme automatique via le machine learning YASA",
                           "en": "Automatic hypnogram via YASA machine learning",
                           "de": "Automatisches Hypnogramm mittels YASA Machine Learning"},
    "feat_spindle_title": {"nl": "Spindle detectie", "fr": "Détection de spindles",  "en": "Spindle detection","de": "Spindel-Erkennung"},
    "feat_spindle_body":  {"nl": "Slaapspoelen per kanaal met frequentie & amplitude",
                           "fr": "Spindles par canal avec fréquence et amplitude",
                           "en": "Sleep spindles per channel with frequency & amplitude",
                           "de": "Schlafspindeln pro Kanal mit Frequenz & Amplitude"},
    "feat_sw_title":      {"nl": "Trage golven",   "fr": "Ondes lentes",          "en": "Slow waves",        "de": "Slow Waves"},
    "feat_sw_body":       {"nl": "Slow oscillations in N3 met duurstatistieken",
                           "fr": "Oscillations lentes en N3 avec statistiques de durée",
                           "en": "Slow oscillations in N3 with duration statistics",
                           "de": "Slow Oscillations in N3 mit Dauerstatistiken"},
    "feat_rem_title":     {"nl": "REM analyse",    "fr": "Analyse REM",           "en": "REM analysis",      "de": "REM-Analyse"},
    "feat_rem_body":      {"nl": "REM-perioden, cycli en NREM→REM transities",
                           "fr": "Périodes REM, cycles et transitions NREM→REM",
                           "en": "REM periods, cycles, and NREM→REM transitions",
                           "de": "REM-Perioden, Zyklen und NREM→REM-Übergänge"},
    "feat_bp_title":      {"nl": "Bandvermogen",   "fr": "Puissance par bande",   "en": "Bandpower",         "de": "Bandpower"},
    "feat_bp_body":       {"nl": "Delta/theta/alpha/sigma/beta per slaapfase",
                           "fr": "Delta/thêta/alpha/sigma/bêta par stade de sommeil",
                           "en": "Delta/theta/alpha/sigma/beta per sleep stage",
                           "de": "Delta/Theta/Alpha/Sigma/Beta pro Schlafstadium"},
    "feat_pdf_title":     {"nl": "PDF & Excel",    "fr": "PDF & Excel",           "en": "PDF & Excel",       "de": "PDF & Excel"},
    "feat_pdf_body":      {"nl": "Professioneel rapport direct downloadbaar",
                           "fr": "Rapport professionnel téléchargeable immédiatement",
                           "en": "Professional report ready to download",
                           "de": "Professioneller Bericht sofort herunterladbar"},

    # report_editor.html — placeholder for institution name
    "rh_inst_placeholder": {"nl": "bv. Slaapkliniek AZORG", "fr": "p.ex. Clinique du sommeil", "en": "e.g. Sleep Clinic", "de": "z. B. Schlafklinik"},

    # results_extended.html — partial-save warning
    "saved_pdf_error": {"nl": "Opgeslagen, maar PDF fout:", "fr": "Enregistré, mais erreur PDF :", "en": "Saved, but PDF error:", "de": "Gespeichert, aber PDF-Fehler:"},

    # scorer_v12.html
    "no_events": {"nl": "Geen events", "fr": "Aucun événement", "en": "No events", "de": "Keine Ereignisse"},

    # upload.html — log + progress JS strings
    "upload_only_edf":          {"nl": "⚠️ Alleen .edf bestanden zijn toegestaan.", "fr": "⚠️ Seuls les fichiers .edf sont autorisés.", "en": "⚠️ Only .edf files are allowed.", "de": "⚠️ Nur .edf-Dateien sind erlaubt."},
    "upload_chunks_uploading":  {"nl": "Chunks uploaden...", "fr": "Téléversement des chunks...", "en": "Uploading chunks...", "de": "Chunks werden hochgeladen..."},
    "upload_channels_detected": {"nl": "Kanalen gedetecteerd...", "fr": "Canaux détectés...", "en": "Channels detected...", "de": "Kanäle erkannt..."},
    "upload_next_channel_sel":  {"nl": "Doorgaan naar kanaalkeuze...", "fr": "Passage à la sélection des canaux...", "en": "Proceeding to channel selection...", "de": "Weiter zur Kanalauswahl..."},
    "upload_channel_sel_load":  {"nl": "Kanaalkeuze laden...", "fr": "Chargement de la sélection des canaux...", "en": "Loading channel selection...", "de": "Kanalauswahl wird geladen..."},
}
TRANSLATIONS.update(_V0105_SWEEP)


# ═══════════════════════════════════════════════════════════
# v0.11.0: light-themed frontpage with embedded login
# ═══════════════════════════════════════════════════════════
_V0110_FRONT_LIGHT = {
    "fp_hero_tagline":  {
        "nl": "Klinische slaapanalyse vanuit één EDF-bestand — automatische staging, ademhalingsevents, signaalkwaliteit en PDF-rapport.",
        "fr": "Analyse clinique du sommeil à partir d'un seul fichier EDF — staging automatique, événements respiratoires, qualité du signal et rapport PDF.",
        "en": "Clinical sleep analysis from a single EDF file — automated staging, respiratory events, signal quality, and PDF report.",
        "de": "Klinische Schlafanalyse aus einer einzigen EDF-Datei — automatisches Staging, respiratorische Ereignisse, Signalqualität und PDF-Bericht.",
    },
    # De beperkingen horen op de eerste pagina te staan, niet alleen in de
    # disclaimer onderaan. Voor een extern onderzoeker is dit bovendien
    # geloofwaardiger dan een superlatief.
    "fp_hero_limits": {
        "nl": "Screeningsinstrument en second opinion. Geen medisch hulpmiddel, geen diagnose: elke uitkomst is een voorstel dat door een arts nagekeken moet worden.",
        "fr": "Outil de dépistage et second avis. Ni dispositif médical, ni diagnostic : chaque résultat est une proposition qui doit être vérifiée par un médecin.",
        "en": "A screening tool and second opinion. Not a medical device and not a diagnosis: every result is a proposal that a physician must review.",
        "de": "Screening-Instrument und Zweitmeinung. Kein Medizinprodukt und keine Diagnose: Jedes Ergebnis ist ein Vorschlag, der ärztlich geprüft werden muss.",
    },
    "fp_login_card_title": {
        "nl": "Aanmelden",
        "fr": "Connexion",
        "en": "Sign in",
        "de": "Anmelden",
    },
    "fp_login_card_sub":   {
        "nl": "Toegang voor bevoegde zorgverleners",
        "fr": "Accès réservé aux professionnels de santé autorisés",
        "en": "Authorized healthcare professionals only",
        "de": "Nur für autorisierte medizinische Fachkräfte",
    },
    "fp_request_demo":     {
        "nl": "Probeer-account aanvragen",
        "fr": "Demander un compte de démo",
        "en": "Request a demo account",
        "de": "Demo-Konto anfragen",
    },
    "fp_explore_below":    {
        "nl": "Of bekijk eerst wat YASAFlaskified doet ↓",
        "fr": "Ou découvrez d'abord les capacités de YASAFlaskified ↓",
        "en": "Or explore what YASAFlaskified does first ↓",
        "de": "Oder erkunden Sie zuerst die Funktionen von YASAFlaskified ↓",
    },

    # New tech / pipeline stats for the hero panel
    "fp_stat_languages":   {"nl": "4 talen UI + rapport", "fr": "4 langues UI + rapport",
                            "en": "4 languages UI + report", "de": "4 Sprachen UI + Bericht"},
    "fp_stat_aasm":        {"nl": "Scoring volgens AASM v3", "fr": "Scoring selon l'AASM v3",
                            "en": "Scored to AASM v3",  "de": "Scoring nach AASM v3"},
    "fp_stat_pipeline":    {"nl": "12-kanaals pipeline", "fr": "Pipeline 12 canaux",
                            "en": "12-channel pipeline", "de": "12-Kanal-Pipeline"},

    # Updated feature cards reflecting v0.10.x capabilities
    "fp_a_c7_title": {"nl": "Signaalkwaliteit per kanaal",       "fr": "Qualité du signal par canal",
                      "en": "Per-channel signal quality",         "de": "Signalqualität pro Kanal"},
    "fp_a_c7_body":  {"nl": "Automatische beoordeling per kanaal (goed / acceptabel / slecht), zichtbaar in dashboard én PDF — voorkomt foutieve diagnoses op slechte opnames.",
                      "fr": "Évaluation automatique par canal (bon / acceptable / médiocre), visible sur le tableau de bord et dans le PDF — évite des diagnostics erronés sur des enregistrements de mauvaise qualité.",
                      "en": "Automatic per-channel grading (good / acceptable / poor), shown on the dashboard and in the PDF — prevents misdiagnosis from poor recordings.",
                      "de": "Automatische Bewertung pro Kanal (gut / akzeptabel / schlecht), im Dashboard und im PDF sichtbar — verhindert Fehldiagnosen bei schlechten Aufnahmen."},
    "fp_a_c8_title": {"nl": "Staging-betrouwbaarheid",            "fr": "Confiance du staging",
                      "en": "Staging confidence",                 "de": "Staging-Konfidenz"},
    "fp_a_c8_body":  {"nl": "Per-epoch confidence-score uit het YASA-model; epochs onder 70% worden gemarkeerd voor manuele review.",
                      "fr": "Score de confiance par époque du modèle YASA ; les époques sous 70 % sont marquées pour revue manuelle.",
                      "en": "Per-epoch confidence score from the YASA model; epochs below 70% are flagged for manual review.",
                      "de": "Konfidenz-Score pro Epoche aus dem YASA-Modell; Epochen unter 70 % werden zur manuellen Überprüfung markiert."},
    "fp_a_c9_title": {"nl": "OAHI-onzekerheidsmarge",             "fr": "Marge d'incertitude OAHI",
                      "en": "OAHI uncertainty range",             "de": "OAHI-Unsicherheitsspanne"},
    "fp_a_c9_body":  {"nl": "3-punt sweep (soepel / primair / strikt) toont hoe stabiel de OSAS-diagnose is bij verschillende scoringscriteria.",
                      "fr": "Sweep à 3 points (souple / primaire / strict) montre la stabilité du diagnostic de SAOS selon les critères de scoring.",
                      "en": "3-point sweep (lenient / primary / strict) shows how stable the OSAS diagnosis is across scoring strictness.",
                      "de": "3-Punkt-Sweep (locker / primär / streng) zeigt, wie stabil die OSAS-Diagnose über verschiedene Scoring-Schwellen ist."},

    # Demo CTA
    "fp_demo_email":   {"nl": "bart.rombaut@gmail.com",  "fr": "bart.rombaut@gmail.com",
                        "en": "bart.rombaut@gmail.com",  "de": "bart.rombaut@gmail.com"},

    "fp_aside_psgscoring": {
        "nl": "Aangedreven door <strong>psgscoring</strong> v0.6 — open-source PSG analyse-bibliotheek (PyPI).",
        "fr": "Propulsé par <strong>psgscoring</strong> v0.6 — bibliothèque d'analyse PSG open source (PyPI).",
        "en": "Powered by <strong>psgscoring</strong> v0.6 — open-source PSG analysis library (PyPI).",
        "de": "Bereitgestellt durch <strong>psgscoring</strong> v0.6 — Open-Source-PSG-Analysebibliothek (PyPI).",
    },
}
TRANSLATIONS.update(_V0110_FRONT_LIGHT)


# ═══════════════════════════════════════════════════════════
# v0.11.2: frontpage content refresh — drop AASM hard claim,
#          add "what's new" + "coming soon" + "work in progress" hint
# ═══════════════════════════════════════════════════════════
_V0112_FRONT_FRESH = {
    # Work-in-progress disclaimer (top of hero, subtle)
    "fp_wip_chip": {
        "nl": "🚧 Actieve ontwikkeling — interface en functies veranderen regelmatig",
        "fr": "🚧 Développement actif — l'interface et les fonctions évoluent régulièrement",
        "en": "🚧 Active development — interface and features change regularly",
        "de": "🚧 Aktive Entwicklung — Oberfläche und Funktionen ändern sich regelmäßig",
    },

    # "What's new" section
    "fp_new_tag":   {"nl": "// Recent toegevoegd",  "fr": "// Récemment ajouté",
                     "en": "// Recently added",     "de": "// Kürzlich hinzugefügt"},
    "fp_new_title": {"nl": "Wat is nieuw in v0.11", "fr": "Nouveautés de la v0.11",
                     "en": "What's new in v0.11",   "de": "Was ist neu in v0.11"},
    "fp_new_lead":  {"nl": "De recentste klinische uitbreidingen van YASAFlaskified:",
                     "fr": "Les ajouts cliniques les plus récents de YASAFlaskified :",
                     "en": "The most recent clinical additions to YASAFlaskified:",
                     "de": "Die neuesten klinischen Erweiterungen von YASAFlaskified:"},

    "fp_new_1_t":   {"nl": "AASM v3-conforme scoring",
                     "fr": "Scoring conforme à l'AASM v3",
                     "en": "AASM v3-compliant scoring",
                     "de": "AASM-v3-konformes Scoring"},
    "fp_new_1_b":   {"nl": "Standaardprofiel volgt AASM-handboek v3 (2023): hypopneu-regel 1A (≥30 % flow + ≥3 % desaturatie óf arousal) en arousals over frontaal, centraal én occipitaal.",
                     "fr": "Le profil par défaut suit le manuel AASM v3 (2023) : règle d'hypopnée 1A (≥30 % débit + ≥3 % désaturation ou micro-éveil) et micro-éveils sur les dérivations frontale, centrale et occipitale.",
                     "en": "The default profile follows the AASM Manual v3 (2023): hypopnea Rule 1A (≥30 % flow + ≥3 % desaturation or arousal) and arousals scored across the frontal, central, and occipital derivations.",
                     "de": "Das Standardprofil folgt dem AASM-Handbuch v3 (2023): Hypopnoe-Regel 1A (≥30 % Fluss + ≥3 % Entsättigung oder Arousal) und Arousals über frontale, zentrale und okzipitale Ableitungen."},

    "fp_new_2_t":   {"nl": "Dubbele AHI (Regel 1A vs 4 %/CMS)",
                     "fr": "Double IAH (règle 1A vs 4 %/CMS)",
                     "en": "Dual AHI (Rule 1A vs 4 %/CMS)",
                     "de": "Doppelter AHI (Regel 1A vs. 4 %/CMS)"},
    "fp_new_2_b":   {"nl": "Het rapport toont beide hypopneu-criteria naast elkaar: 3 %/arousal (klinische standaard) én 4 % desaturatie (CMS/verzekering) — die kunnen een volledige ernstgraad verschillen.",
                     "fr": "Le rapport affiche les deux critères d'hypopnée côte à côte : 3 %/micro-éveil (standard clinique) et 4 % désaturation (CMS/assurance) — pouvant différer d'un grade de sévérité complet.",
                     "en": "The report shows both hypopnea criteria side by side: 3 %/arousal (clinical standard) and 4 % desaturation (CMS/insurance) — which can differ by a full severity grade.",
                     "de": "Der Bericht zeigt beide Hypopnoe-Kriterien nebeneinander: 3 %/Arousal (klinischer Standard) und 4 % Entsättigung (CMS/Versicherung) — die sich um einen ganzen Schweregrad unterscheiden können."},

    "fp_new_3_t":   {"nl": "Ventilatory & hypoxic burden",
                     "fr": "Charge ventilatoire & hypoxique",
                     "en": "Ventilatory & hypoxic burden",
                     "de": "Ventilatorische & hypoxische Last"},
    "fp_new_3_b":   {"nl": "Fysiologische ernstmaten bovenop de AHI: hypoxic burden (SpO₂-tekort) en ventilatory burden (% ademhalingen < 50 % van de baseline, AJRCCM 2023) — geassocieerd met cardiovasculair risico.",
                     "fr": "Mesures de sévérité physiologiques au-delà de l'IAH : charge hypoxique (déficit SpO₂) et charge ventilatoire (% de respirations < 50 % de la ligne de base, AJRCCM 2023) — associées au risque cardiovasculaire.",
                     "en": "Physiology-based severity beyond the AHI: hypoxic burden (SpO₂ deficit) and ventilatory burden (% of breaths < 50 % of baseline, AJRCCM 2023) — associated with cardiovascular risk.",
                     "de": "Physiologische Schweremaße über den AHI hinaus: hypoxische Last (SpO₂-Defizit) und ventilatorische Last (% Atemzüge < 50 % der Basislinie, AJRCCM 2023) — mit kardiovaskulärem Risiko assoziiert."},

    "fp_new_4_t":   {"nl": "Klinische fenotypes",
                     "fr": "Phénotypes cliniques",
                     "en": "Clinical phenotypes",
                     "de": "Klinische Phänotypen"},
    "fp_new_4_b":   {"nl": "Automatische detectie van positioneel OSAS (POSA, Cartwright) en REM-predominant OSAS — met aanwijzing voor positietherapie waar van toepassing.",
                     "fr": "Détection automatique du SAOS positionnel (POSA, Cartwright) et du SAOS à prédominance REM — avec indication de thérapie positionnelle le cas échéant.",
                     "en": "Automatic detection of positional OSA (POSA, Cartwright) and REM-predominant OSA — flagging positional-therapy candidacy where applicable.",
                     "de": "Automatische Erkennung von lageabhängiger OSA (POSA, Cartwright) und REM-prädominanter OSA — mit Hinweis auf Lagetherapie, wo zutreffend."},

    "fp_new_5_t":   {"nl": "Rapport op maat van de clinicus",
                     "fr": "Rapport pensé pour le clinicien",
                     "en": "Clinician-focused report",
                     "de": "Auf den Kliniker zugeschnittener Bericht"},
    "fp_new_5_b":   {"nl": "Geautomatiseerde samenvatting, AASM-referentiewaarden bij elke index en een beschrijvend 'aandachtspunten'-kader — in een viertalig PDF-rapport.",
                     "fr": "Résumé automatisé, valeurs de référence AASM pour chaque index et un encadré descriptif « points d'attention » — dans un rapport PDF quadrilingue.",
                     "en": "An automated summary, AASM reference ranges next to each index, and a descriptive 'points of attention' box — in a four-language PDF report.",
                     "de": "Automatische Zusammenfassung, AASM-Referenzwerte neben jedem Index und ein beschreibendes „Aufmerksamkeitspunkte“-Feld — in einem viersprachigen PDF-Bericht."},

    "fp_new_6_t":   {"nl": "Arousal-etiologie & OSAS/CSAS-typering",
                     "fr": "Étiologie des micro-éveils & typage SAOS/SACS",
                     "en": "Arousal aetiology & OSAS/CSAS typing",
                     "de": "Arousal-Ätiologie & OSAS/ZSAS-Typisierung"},
    "fp_new_6_b":   {"nl": "Respiratoire, spontane en PLM-arousal-index apart; centrale AHI + Cheyne-Stokes-detectie onderscheiden obstructief (OSAS) van centraal (CSAS) slaapapneu.",
                     "fr": "Index de micro-éveils respiratoires, spontanés et PLM séparés ; l'IAH central + la détection de Cheyne-Stokes distinguent l'apnée obstructive (SAOS) de la centrale (SACS).",
                     "en": "Separate respiratory, spontaneous, and PLM arousal indices; central AHI + Cheyne-Stokes detection distinguish obstructive (OSAS) from central (CSAS) sleep apnea.",
                     "de": "Getrennte respiratorische, spontane und PLM-Arousal-Indizes; zentraler AHI + Cheyne-Stokes-Erkennung unterscheiden obstruktive (OSAS) von zentraler (ZSAS) Schlafapnoe."},

    # Scoring profile note
    "fp_scoring_profiles_t": {"nl": "Meerdere scoringsprofielen",
                              "fr": "Plusieurs profils de scoring",
                              "en": "Multiple scoring profiles",
                              "de": "Mehrere Scoring-Profile"},
    "fp_scoring_profiles_b": {"nl": "Naast het standaard AASM-profiel kan de bibliotheek <strong>psgscoring</strong> ook historische regelsets toepassen (R&amp;K 1968, AASM v1.0 → v3.0) — handig voor heranalyse van oudere studies of vergelijkend onderzoek.",
                              "fr": "Outre le profil AASM standard, la bibliothèque <strong>psgscoring</strong> peut appliquer des règles historiques (R&amp;K 1968, AASM v1.0 → v3.0) — utile pour réanalyser d'anciennes études ou pour la recherche comparative.",
                              "en": "Beyond the standard AASM profile, the <strong>psgscoring</strong> library can also apply historical rule sets (R&amp;K 1968, AASM v1.0 → v3.0) — useful for re-analyzing older studies or comparative research.",
                              "de": "Neben dem Standard-AASM-Profil kann die Bibliothek <strong>psgscoring</strong> auch historische Regelwerke anwenden (R&amp;K 1968, AASM v1.0 → v3.0) — nützlich für die Reanalyse älterer Studien oder vergleichende Forschung."},

    # Roadmap / Coming soon
    "fp_road_tag":   {"nl": "// Op de roadmap",        "fr": "// Sur la feuille de route",
                      "en": "// On the roadmap",       "de": "// Auf der Roadmap"},
    "fp_road_title": {"nl": "Wat komt eraan",         "fr": "Ce qui arrive",
                      "en": "What's coming next",     "de": "Was als Nächstes kommt"},
    "fp_road_lead":  {"nl": "YASAFlaskified is een werk in opbouw. Onderstaande punten zijn in voorbereiding of in actief onderzoek.",
                      "fr": "YASAFlaskified est en construction. Les éléments ci-dessous sont en préparation ou en cours de validation.",
                      "en": "YASAFlaskified is a work in progress. The items below are in preparation or under active validation.",
                      "de": "YASAFlaskified ist work in progress. Die folgenden Punkte sind in Vorbereitung oder werden aktiv validiert."},

    "fp_road_1_t":   {"nl": "Klinische validatiestudie",  "fr": "Étude de validation clinique",
                      "en": "Clinical validation study",  "de": "Klinische Validierungsstudie"},
    "fp_road_1_b":   {"nl": "Monocentrische studie AZORG-YASA-2026-001 (n ≥ 50, ethisch protocol v7.0) — vergelijkt automatische scoring met manuele scoring door een geregistreerd polysomnograaf.",
                      "fr": "Étude monocentrique AZORG-YASA-2026-001 (n ≥ 50, protocole éthique v7.0) — compare le scoring automatique au scoring manuel par un polysomnographe agréé.",
                      "en": "Single-centre study AZORG-YASA-2026-001 (n ≥ 50, ethics protocol v7.0) — compares automated scoring to manual scoring by a registered polysomnographer.",
                      "de": "Monozentrische Studie AZORG-YASA-2026-001 (n ≥ 50, Ethikprotokoll v7.0) — vergleicht automatisches Scoring mit manuellem Scoring durch eine registrierte Polysomnographin."},

    "fp_road_2_t":   {"nl": "Peer-reviewed publicatie",   "fr": "Publication évaluée par les pairs",
                      "en": "Peer-reviewed publication",  "de": "Peer-reviewte Publikation"},
    "fp_road_2_b":   {"nl": "Een peer-reviewed publicatie over psgscoring is in voorbereiding.",
                      "fr": "Une publication évaluée par les pairs sur psgscoring est en préparation.",
                      "en": "A peer-reviewed publication on psgscoring is in preparation.",
                      "de": "Eine peer-reviewte Publikation zu psgscoring ist in Vorbereitung."},

    "fp_road_3_t":   {"nl": "MESA-extern validatie",     "fr": "Validation externe MESA",
                      "en": "MESA external validation",  "de": "MESA-Externe Validierung"},
    "fp_road_3_b":   {"nl": "Validatie op de MESA-SHHS-datasets (≥ 2000 nachten) om de generaliseerbaarheid van psgscoring buiten één centrum aan te tonen.",
                      "fr": "Validation sur les ensembles MESA-SHHS (≥ 2000 nuits) pour démontrer la généralisation de psgscoring au-delà d'un seul centre.",
                      "en": "Validation on the MESA-SHHS datasets (≥ 2000 nights) to demonstrate generalization of psgscoring beyond a single centre.",
                      "de": "Validierung auf den MESA-SHHS-Datensätzen (≥ 2000 Nächte) zur Demonstration der Generalisierung von psgscoring über ein Zentrum hinaus."},

    "fp_road_4_t":   {"nl": "FHIR-export",               "fr": "Export FHIR",
                      "en": "FHIR export",               "de": "FHIR-Export"},
    "fp_road_4_b":   {"nl": "Automatische export van slaapdiagnose-bevindingen naar EPD-systemen via HL7 FHIR-resources.",
                      "fr": "Export automatique des résultats de diagnostic du sommeil vers les systèmes DPI via les ressources HL7 FHIR.",
                      "en": "Automatic export of sleep-diagnostic findings to EHR systems via HL7 FHIR resources.",
                      "de": "Automatischer Export von Schlafdiagnose-Befunden in EPA/KIS-Systeme über HL7 FHIR-Ressourcen."},

    "fp_road_5_t":   {"nl": "Update naar AASM Manual v3.0",
                      "fr": "Mise à jour vers AASM Manual v3.0",
                      "en": "Update to AASM Manual v3.0",
                      "de": "Aktualisierung auf AASM Manual v3.0"},
    "fp_road_5_b":   {"nl": "Implementatie van de wijzigingen uit de AASM Manual editie 3.0 (2023) — onder andere herziene RERA-criteria en strengere arousal-regels.",
                      "fr": "Mise en œuvre des changements de l'édition 3.0 (2023) du manuel AASM — entre autres, critères RERA révisés et règles d'éveil plus strictes.",
                      "en": "Implementation of the changes from AASM Manual edition 3.0 (2023) — including revised RERA criteria and stricter arousal rules.",
                      "de": "Umsetzung der Änderungen aus dem AASM Manual Edition 3.0 (2023) — u. a. überarbeitete RERA-Kriterien und strengere Arousal-Regeln."},

    "fp_road_6_t":   {"nl": "Manuele scorer-interface (bèta)",
                      "fr": "Interface de scorage manuel (bêta)",
                      "en": "Manual scorer interface (beta)",
                      "de": "Manuelle Scorer-Oberfläche (Beta)"},
    "fp_road_6_b":   {"nl": "Browser-gebaseerde hypnogram-editor en EDF-viewer — toelaten dat een arts ad-hoc AI-stages corrigeert of events toevoegt zonder externe software.",
                      "fr": "Éditeur d'hypnogramme et visionneuse EDF dans le navigateur — permet à un médecin de corriger les stades IA ou d'ajouter des événements sans logiciel externe.",
                      "en": "Browser-based hypnogram editor and EDF viewer — lets a clinician correct AI stages or add events ad hoc, no external software needed.",
                      "de": "Browserbasierter Hypnogramm-Editor und EDF-Viewer — ermöglicht es einer Klinikerin, KI-Stadien zu korrigieren oder Ereignisse ad hoc hinzuzufügen, ohne externe Software."},
}
TRANSLATIONS.update(_V0112_FRONT_FRESH)


# ═══════════════════════════════════════════════════════════
# v0.12.0: Bulk-onderhoud + archivering (dashboard)
# ═══════════════════════════════════════════════════════════
_MAINTENANCE_V0120 = {
    "select_all":          {"nl": "Alles selecteren",        "fr": "Tout sélectionner",        "en": "Select all",            "de": "Alle auswählen"},
    "n_selected":          {"nl": "geselecteerd",            "fr": "sélectionné(s)",            "en": "selected",              "de": "ausgewählt"},
    "bulk_archive":        {"nl": "Archiveren",              "fr": "Archiver",                  "en": "Archive",               "de": "Archivieren"},
    "bulk_unarchive":      {"nl": "Herstellen",              "fr": "Restaurer",                 "en": "Restore",               "de": "Wiederherstellen"},
    "bulk_delete":         {"nl": "Verwijderen",             "fr": "Supprimer",                 "en": "Delete",                "de": "Löschen"},
    "show_archived":       {"nl": "Toon gearchiveerd",       "fr": "Afficher les archivées",    "en": "Show archived",         "de": "Archivierte anzeigen"},
    "hide_archived":       {"nl": "Verberg gearchiveerd",    "fr": "Masquer les archivées",     "en": "Hide archived",         "de": "Archivierte ausblenden"},
    "archived_badge":      {"nl": "Gearchiveerd",            "fr": "Archivée",                  "en": "Archived",              "de": "Archiviert"},
    "back_to_active":      {"nl": "Terug naar actieve studies","fr": "Retour aux études actives","en": "Back to active studies","de": "Zurück zu aktiven Studien"},
    "archived_view_title": {"nl": "Gearchiveerde studies",   "fr": "Études archivées",          "en": "Archived studies",      "de": "Archivierte Studien"},
    "confirm_bulk_delete": {"nl": "studie(s) definitief verwijderen? Alle bijhorende bestanden worden gewist. Dit kan niet ongedaan worden.",
                            "fr": "étude(s) à supprimer définitivement ? Tous les fichiers associés seront effacés. Action irréversible.",
                            "en": "study/studies permanently? All associated files will be removed. This cannot be undone.",
                            "de": "Studie(n) endgültig löschen? Alle zugehörigen Dateien werden entfernt. Dies kann nicht rückgängig gemacht werden."},
    "bulk_archived":       {"nl": "studie(s) gearchiveerd",  "fr": "étude(s) archivée(s)",      "en": "study/studies archived","de": "Studie(n) archiviert"},
    "bulk_unarchived":     {"nl": "studie(s) hersteld",      "fr": "étude(s) restaurée(s)",     "en": "study/studies restored","de": "Studie(n) wiederhergestellt"},
    "bulk_deleted":        {"nl": "studie(s) verwijderd",    "fr": "étude(s) supprimée(s)",     "en": "study/studies deleted", "de": "Studie(n) gelöscht"},
    "bulk_skipped":        {"nl": "overgeslagen (geen rechten)","fr": "ignorée(s) (pas d'autorisation)","en": "skipped (no permission)","de": "übersprungen (keine Berechtigung)"},
    "bulk_none_selected":  {"nl": "Geen studies geselecteerd.","fr": "Aucune étude sélectionnée.","en": "No studies selected.",  "de": "Keine Studien ausgewählt."},
    "bulk_invalid_action": {"nl": "Ongeldige bulk-actie.",   "fr": "Action groupée invalide.",  "en": "Invalid bulk action.",  "de": "Ungültige Sammelaktion."},
}
TRANSLATIONS.update(_MAINTENANCE_V0120)


# ═══════════════════════════════════════════════════════════
# v0.21.0 — frontpage: invitation to other sleep centres
#
# The caveats are deliberately on the landing page rather than behind a
# link. A centre that adopts this software inherits every limitation
# listed here, and the ones that matter most (single-cohort validation,
# no CE mark, controller responsibility for personal data) are exactly
# the ones a marketing page tends to bury.
# ═══════════════════════════════════════════════════════════
_FRONTPAGE_INVITE_V0210 = {
    "fp_inv_nav": {
        "nl": "Voor slaapcentra",
        "fr": "Pour les centres du sommeil",
        "en": "For sleep centres",
        "de": "Für Schlafzentren"},
    "fp_inv_tag": {
        "nl": "// Uitnodiging aan slaapcentra",
        "fr": "// Invitation aux centres du sommeil",
        "en": "// An invitation to sleep centres",
        "de": "// Einladung an Schlafzentren"},
    "fp_inv_title": {
        "nl": "Gebruik het in uw eigen centrum",
        "fr": "Utilisez-le dans votre propre centre",
        "en": "Use it in your own centre",
        "de": "Nutzen Sie es in Ihrem eigenen Zentrum"},
    "fp_inv_lead": {
        "nl": "psgscoring en YASAFlaskified zijn open source onder BSD-3. Elk slaapcentrum mag ze "
              "installeren, aanpassen en op eigen opnames toetsen — zonder licentiekosten en zonder "
              "toestemming te vragen. Wij nodigen u daar uitdrukkelijk toe uit. Wat we terugvragen is "
              "geen betaling maar tegenspraak: cijfers uit uw eigen cohort, vooral wanneer ze van de "
              "onze afwijken.",
        "fr": "psgscoring et YASAFlaskified sont open source sous licence BSD-3. Tout centre du sommeil "
              "peut les installer, les modifier et les évaluer sur ses propres enregistrements — sans "
              "frais de licence et sans demander d'autorisation. Nous vous y invitons explicitement. Ce "
              "que nous demandons en retour n'est pas un paiement mais une contradiction : des chiffres "
              "issus de votre propre cohorte, surtout lorsqu'ils divergent des nôtres.",
        "en": "psgscoring and YASAFlaskified are open source under BSD-3. Any sleep centre may install "
              "them, modify them and test them on its own recordings — no licence fee, no permission "
              "needed. We explicitly invite you to do so. What we ask in return is not payment but "
              "contradiction: numbers from your own cohort, especially where they disagree with ours.",
        "de": "psgscoring und YASAFlaskified sind Open Source unter BSD-3. Jedes Schlafzentrum darf sie "
              "installieren, anpassen und an eigenen Aufzeichnungen prüfen — ohne Lizenzkosten und ohne "
              "um Erlaubnis zu fragen. Wir laden Sie ausdrücklich dazu ein. Was wir zurückerbitten, ist "
              "keine Bezahlung, sondern Widerspruch: Zahlen aus Ihrer eigenen Kohorte, besonders dort, "
              "wo sie von unseren abweichen."},

    # ── Route 1: hosted instance ──
    "fp_inv_r1_num": {
        "nl": "Route 1 — kennismaken", "fr": "Voie 1 — découvrir",
        "en": "Route 1 — first look",  "de": "Weg 1 — kennenlernen"},
    "fp_inv_r1_t": {
        "nl": "Meekijken op deze instantie",
        "fr": "Essayer sur cette instance",
        "en": "Try it on this instance",
        "de": "Auf dieser Instanz mitschauen"},
    "fp_inv_r1_b": {
        "nl": "Vraag een gratis account aan en laat een gepseudonimiseerde EDF scoren. Binnen vijf à "
              "tien minuten krijgt u het volledige rapport, inclusief de visuele eventcontrole. De "
              "snelste manier om te zien wat het doet — en waar het uw eigen scoring tegenspreekt.",
        "fr": "Demandez un compte gratuit et faites analyser un EDF pseudonymisé. En cinq à dix minutes "
              "vous recevez le rapport complet, y compris la revue visuelle des événements. Le moyen le "
              "plus rapide de voir ce que fait l'outil — et où il contredit votre propre scoring.",
        "en": "Request a free account and have a pseudonymised EDF scored. Within five to ten minutes "
              "you get the full report, including the visual event review. The fastest way to see what "
              "it does — and where it contradicts your own scoring.",
        "de": "Fordern Sie ein kostenloses Konto an und lassen Sie eine pseudonymisierte EDF auswerten. "
              "Innerhalb von fünf bis zehn Minuten erhalten Sie den vollständigen Bericht samt "
              "visueller Ereigniskontrolle. Der schnellste Weg zu sehen, was die Software leistet — und "
              "wo sie Ihrer eigenen Auswertung widerspricht."},
    "fp_inv_r1_cta": {
        "nl": "Account aanvragen", "fr": "Demander un compte",
        "en": "Request an account", "de": "Konto anfragen"},

    # ── Route 2: self-hosting ──
    "fp_inv_r2_num": {
        "nl": "Route 2 — zelf hosten", "fr": "Voie 2 — auto-hébergement",
        "en": "Route 2 — self-hosting", "de": "Weg 2 — selbst hosten"},
    "fp_inv_r2_t": {
        "nl": "Op uw eigen server",
        "fr": "Sur votre propre serveur",
        "en": "On your own server",
        "de": "Auf Ihrem eigenen Server"},
    "fp_inv_r2_b": {
        "nl": "Eén commando op een verse Ubuntu- of Debian-server installeert de volledige stack: "
              "Docker, Nginx, firewall en een Let's Encrypt-certificaat. Uw opnames verlaten daarbij uw "
              "eigen infrastructuur niet.",
        "fr": "Une seule commande sur un serveur Ubuntu ou Debian vierge installe toute la pile : "
              "Docker, Nginx, pare-feu et un certificat Let's Encrypt. Vos enregistrements ne quittent "
              "alors jamais votre propre infrastructure.",
        "en": "A single command on a fresh Ubuntu or Debian server installs the whole stack: Docker, "
              "Nginx, firewall and a Let's Encrypt certificate. Your recordings never leave your own "
              "infrastructure.",
        "de": "Ein einziger Befehl auf einem frischen Ubuntu- oder Debian-Server installiert den "
              "gesamten Stack: Docker, Nginx, Firewall und ein Let's-Encrypt-Zertifikat. Ihre "
              "Aufzeichnungen verlassen dabei Ihre eigene Infrastruktur nicht."},
    "fp_inv_r2_cta": {
        "nl": "Uitrolhandleiding", "fr": "Guide de déploiement",
        "en": "Deployment runbook", "de": "Deployment-Handbuch"},

    # ── Route 3: library only ──
    "fp_inv_r3_num": {
        "nl": "Route 3 — enkel de bibliotheek", "fr": "Voie 3 — la bibliothèque seule",
        "en": "Route 3 — the library alone",    "de": "Weg 3 — nur die Bibliothek"},
    "fp_inv_r3_t": {
        "nl": "In uw eigen pijplijn",
        "fr": "Dans votre propre pipeline",
        "en": "In your own pipeline",
        "de": "In Ihrer eigenen Pipeline"},
    "fp_inv_r3_b": {
        "nl": "Alleen de scoringlogica, zonder webapplicatie. Draai ze op opnames die uw team al "
              "gescoord heeft en vergelijk event per event in plaats van enkel de AHI.",
        "fr": "Uniquement la logique de scoring, sans application web. Exécutez-la sur des "
              "enregistrements déjà cotés par votre équipe et comparez événement par événement plutôt "
              "que le seul IAH.",
        "en": "The scoring logic only, without the web application. Run it over recordings your team has "
              "already scored and compare event by event rather than the AHI alone.",
        "de": "Nur die Auswertungslogik, ohne Webanwendung. Führen Sie sie auf Aufzeichnungen aus, die "
              "Ihr Team bereits ausgewertet hat, und vergleichen Sie Ereignis für Ereignis statt nur "
              "den AHI."},
    "fp_inv_r3_cta": {
        "nl": "Documentatie", "fr": "Documentation",
        "en": "Documentation", "de": "Dokumentation"},

    # ── Caveats ──
    "fp_inv_cav_title": {
        "nl": "Lees dit eerst",
        "fr": "À lire avant tout",
        "en": "Read this first",
        "de": "Bitte zuerst lesen"},
    "fp_inv_cav_lead": {
        "nl": "Wij hebben er belang bij dat u deze software gebruikt. Daarom staan de beperkingen hier, "
              "en niet in de kleine lettertjes.",
        "fr": "Nous avons intérêt à ce que vous utilisiez ce logiciel. C'est pourquoi les limites "
              "figurent ici, et non en petits caractères.",
        "en": "We have an interest in you adopting this software. That is precisely why the limitations "
              "are here, and not in the small print.",
        "de": "Wir haben ein Interesse daran, dass Sie diese Software einsetzen. Genau deshalb stehen "
              "die Einschränkungen hier und nicht im Kleingedruckten."},

    "fp_inv_c1_t": {
        "nl": "Geen medisch hulpmiddel.", "fr": "Pas un dispositif médical.",
        "en": "Not a medical device.",    "de": "Kein Medizinprodukt."},
    "fp_inv_c1_b": {
        "nl": 'Niet CE-gemarkeerd (MDR 2017/745), niet FDA-cleared. Dit is onderzoekssoftware. Elk '
              'rapport moet door een bevoegd arts worden nagekeken vóór enige diagnostische of '
              'therapeutische beslissing. De <a href="/disclaimer">volledige disclaimer</a> staat ook '
              'in elk gegenereerd rapport.',
        "fr": 'Pas de marquage CE (MDR 2017/745), pas d\'autorisation FDA. Il s\'agit d\'un logiciel de '
              'recherche. Chaque rapport doit être vérifié par un médecin qualifié avant toute décision '
              'diagnostique ou thérapeutique. La <a href="/disclaimer">clause de non-responsabilité '
              'complète</a> figure aussi dans chaque rapport généré.',
        "en": 'Not CE-marked (MDR 2017/745), not FDA-cleared. This is research software. Every report '
              'must be reviewed by a qualified physician before any diagnostic or therapeutic decision. '
              'The <a href="/disclaimer">full disclaimer</a> also appears in every generated report.',
        "de": 'Keine CE-Kennzeichnung (MDR 2017/745), keine FDA-Zulassung. Dies ist '
              'Forschungssoftware. Jeder Bericht muss vor jeder diagnostischen oder therapeutischen '
              'Entscheidung von einer qualifizierten Ärztin oder einem qualifizierten Arzt geprüft '
              'werden. Der <a href="/disclaimer">vollständige Haftungsausschluss</a> steht auch in '
              'jedem erzeugten Bericht.'},

    "fp_inv_c2_t": {
        "nl": "Gevalideerd op vijf opnames en één extern cohort.",
        "fr": "Validé sur cinq enregistrements et une cohorte externe.",
        "en": "Validated on five recordings and one external cohort.",
        "de": "An fünf Aufzeichnungen und einer externen Kohorte validiert."},
    "fp_inv_c2_b": {
        "nl": "PSG-IPA (5 opnames, elk door 12 scoorders beoordeeld) en MESA/NSRR (n=150, volledig "
              "achtergehouden). Dat volstaat om te publiceren, niet om uw populatie te "
              "vertegenwoordigen. Montages, sensoren en scoorgewoonten verschillen per centrum, en de "
              "twee cohorten spreken elkaar op onderdelen tegen.",
        "fr": "PSG-IPA (5 enregistrements, cotés chacun par 12 experts) et MESA/NSRR (n=150, "
              "entièrement mise de côté). C'est suffisant pour publier, pas pour représenter votre "
              "population. Les montages, les capteurs et les habitudes de cotation diffèrent d'un "
              "centre à l'autre, et les deux cohortes se contredisent sur certains points.",
        "en": "PSG-IPA (5 recordings, each scored by 12 scorers) and MESA/NSRR (n=150, fully held out). "
              "That is enough to publish, not enough to represent your population. Montages, sensors "
              "and scoring habits differ between centres, and the two cohorts contradict each other on "
              "some points.",
        "de": "PSG-IPA (5 Aufzeichnungen, jeweils von 12 Auswertenden beurteilt) und MESA/NSRR (n=150, "
              "vollständig zurückgehalten). Das genügt für eine Publikation, nicht um Ihre Population "
              "abzubilden. Montagen, Sensoren und Auswertungsgewohnheiten unterscheiden sich je "
              "Zentrum, und die beiden Kohorten widersprechen einander in Teilen."},

    "fp_inv_c3_t": {
        "nl": "Toets het tegen uw eigen scoring vóór u erop steunt.",
        "fr": "Comparez-le à votre propre cotation avant de vous y fier.",
        "en": "Test it against your own scoring before relying on it.",
        "de": "Prüfen Sie es gegen Ihre eigene Auswertung, bevor Sie sich darauf verlassen."},
    "fp_inv_c3_b": {
        "nl": "Laat minstens enkele tientallen opnames scoren die uw team al beoordeeld heeft, en kijk "
              "naar Bland-Altman en gewogen κ — niet naar een gemiddelde AHI. Een gemiddelde verbergt "
              "precies de spreiding waar het om gaat.",
        "fr": "Faites analyser au moins quelques dizaines d'enregistrements déjà cotés par votre équipe "
              "et examinez un Bland-Altman et un κ pondéré — pas un IAH moyen. Une moyenne masque "
              "précisément la dispersion qui importe.",
        "en": "Have at least a few dozen recordings scored that your team has already read, and look at "
              "Bland-Altman and weighted κ — not a mean AHI. An average hides exactly the spread that "
              "matters.",
        "de": "Lassen Sie mindestens einige Dutzend Aufzeichnungen auswerten, die Ihr Team bereits "
              "beurteilt hat, und betrachten Sie Bland-Altman und gewichtetes κ — nicht einen mittleren "
              "AHI. Ein Mittelwert verbirgt genau die Streuung, auf die es ankommt."},

    "fp_inv_c4_t": {
        "nl": "De AHI is een schatting met een interval.",
        "fr": "L'IAH est une estimation assortie d'un intervalle.",
        "en": "The AHI is an estimate with an interval.",
        "de": "Der AHI ist eine Schätzung mit einem Intervall."},
    "fp_inv_c4_b": {
        "nl": "Elke studie wordt op drie strengheidsniveaus gescoord en krijgt een robuustheidsgraad A, "
              "B of C. Een C betekent dat de AHI sterk afhangt van waar de grens wordt gelegd. Dat is "
              "informatie over de opname, geen defect in de software.",
        "fr": "Chaque étude est cotée à trois niveaux de sévérité et reçoit une note de robustesse A, B "
              "ou C. Un C signifie que l'IAH dépend fortement de l'endroit où le seuil est placé. C'est "
              "une information sur l'enregistrement, pas un défaut du logiciel.",
        "en": "Every study is scored at three stringency levels and receives a robustness grade of A, B "
              "or C. A C means the AHI depends heavily on where the threshold is drawn. That is "
              "information about the recording, not a defect in the software.",
        "de": "Jede Studie wird auf drei Strenge-Stufen ausgewertet und erhält eine Robustheitsnote A, B "
              "oder C. Ein C bedeutet, dass der AHI stark davon abhängt, wo die Grenze gezogen wird. "
              "Das ist eine Information über die Aufzeichnung, kein Softwarefehler."},

    "fp_inv_c5_t": {
        "nl": "Persoonsgegevens blijven uw verantwoordelijkheid.",
        "fr": "Les données personnelles restent sous votre responsabilité.",
        "en": "Personal data remains your responsibility.",
        "de": "Personenbezogene Daten bleiben Ihre Verantwortung."},
    "fp_inv_c5_b": {
        "nl": "Deze instantie draait in de EU (Hetzner, Duitsland), maar upload er uitsluitend "
              "gepseudonimiseerde EDF's naartoe; de repository bevat daarvoor anonymize_edf.py. Voor "
              "identificeerbare gegevens host u zelf — dan blijft uw centrum verwerkingsverantwoordelijke "
              "en verlaat er niets uw eigen infrastructuur.",
        "fr": "Cette instance fonctionne dans l'UE (Hetzner, Allemagne), mais n'y téléversez que des EDF "
              "pseudonymisés ; le dépôt fournit anonymize_edf.py à cet effet. Pour des données "
              "identifiables, hébergez vous-même — votre centre reste alors responsable du traitement "
              "et rien ne quitte votre propre infrastructure.",
        "en": "This instance runs in the EU (Hetzner, Germany), but upload only pseudonymised EDFs to "
              "it; the repository ships anonymize_edf.py for that. For identifiable data, self-host — "
              "your centre then remains the data controller and nothing leaves your own "
              "infrastructure.",
        "de": "Diese Instanz läuft in der EU (Hetzner, Deutschland), laden Sie dorthin jedoch "
              "ausschließlich pseudonymisierte EDF-Dateien hoch; das Repository enthält dafür "
              "anonymize_edf.py. Für identifizierbare Daten hosten Sie selbst — dann bleibt Ihr Zentrum "
              "Verantwortlicher und nichts verlässt Ihre eigene Infrastruktur."},

    "fp_inv_c6_t": {
        "nl": "Geen support-SLA.", "fr": "Aucun contrat de support.",
        "en": "No support SLA.",   "de": "Kein Support-SLA."},
    "fp_inv_c6_b": {
        "nl": "Dit is het werk van één klinisch team, niet van een bedrijf. GitHub-issues worden gelezen "
              "en meestal beantwoord, maar er is geen gegarandeerde reactietijd. Wilt u dat scores over "
              "de tijd identiek blijven, pin dan zowel de psgscoring-versie als het profiel: enkel "
              "mesa_shhs en chicago_1999 zijn bevroren, de overige profielen volgen nieuwe metingen.",
        "fr": "C'est le travail d'une seule équipe clinique, pas d'une entreprise. Les tickets GitHub "
              "sont lus et généralement traités, mais aucun délai de réponse n'est garanti. Si vous "
              "voulez que les résultats restent identiques dans le temps, figez à la fois la version de "
              "psgscoring et le profil : seuls mesa_shhs et chicago_1999 sont gelés, les autres profils "
              "suivent les nouvelles mesures.",
        "en": "This is the work of a single clinical team, not a company. GitHub issues are read and "
              "usually answered, but no response time is guaranteed. If you need scored values to stay "
              "identical over time, pin both the psgscoring version and the profile: only mesa_shhs and "
              "chicago_1999 are frozen, the other profiles follow new measurements.",
        "de": "Dies ist die Arbeit eines einzelnen klinischen Teams, nicht eines Unternehmens. "
              "GitHub-Issues werden gelesen und meist beantwortet, eine Reaktionszeit ist jedoch nicht "
              "garantiert. Sollen Auswertungswerte über die Zeit identisch bleiben, fixieren Sie sowohl "
              "die psgscoring-Version als auch das Profil: nur mesa_shhs und chicago_1999 sind "
              "eingefroren, die übrigen Profile folgen neuen Messungen."},

    "fp_inv_contact": {
        "nl": 'Overweegt u het in uw centrum te gebruiken — of hebt u het al getoetst en wijken uw '
              'cijfers af? Dat laatste horen we het liefst. '
              '<a href="mailto:bart.rombaut@gmail.com">bart.rombaut@gmail.com</a>',
        "fr": 'Vous envisagez de l\'utiliser dans votre centre — ou vous l\'avez déjà évalué et vos '
              'chiffres divergent ? C\'est surtout ce dernier cas qui nous intéresse. '
              '<a href="mailto:bart.rombaut@gmail.com">bart.rombaut@gmail.com</a>',
        "en": 'Considering it for your centre — or have you already tested it and your numbers differ? '
              'The latter is what we most want to hear. '
              '<a href="mailto:bart.rombaut@gmail.com">bart.rombaut@gmail.com</a>',
        "de": 'Erwägen Sie den Einsatz in Ihrem Zentrum — oder haben Sie es bereits geprüft und Ihre '
              'Zahlen weichen ab? Gerade Letzteres hören wir am liebsten. '
              '<a href="mailto:bart.rombaut@gmail.com">bart.rombaut@gmail.com</a>'},
}
TRANSLATIONS.update(_FRONTPAGE_INVITE_V0210)


# ─────────────────────────────────────────────────────────────────────────
# v0.22.0 — profielgroepen, waarschuwing en helpsectie op channel_select
#
# De dropdown groepeert sinds 0.22.0 op de FAMILIE die psgscoring meegeeft in
# plaats van op de AASM-versiestring. Reden: tot 0.21.0 stond elk exploratory
# profiel tussen de klinische in dezelfde optgroep, en een nieuw profiel in de
# bibliotheek landde daar automatisch. Bij psgscoring 0.19.0 zouden dat vier
# enveloppe-armen zijn geweest, waarvan één op twee cohorten is afgewezen.
#
# Alle vier de talen zijn verplicht: `t()` valt stil terug op een andere taal,
# dus een ontbrekende sleutel geeft geen fout maar een pagina die er in één taal
# anders uitziet — en dit is de sectie waar dat het meest kost.
# ─────────────────────────────────────────────────────────────────────────

_PROFILE_HELP_V0220 = {
    "prof_grp_v3": {
        "nl": "AASM v3 (2023) — klinisch",
        "fr": "AASM v3 (2023) — clinique",
        "en": "AASM v3 (2023) — clinical",
        "de": "AASM v3 (2023) — klinisch"},
    "prof_grp_hist": {
        "nl": "Historische AASM-versies",
        "fr": "Versions AASM historiques",
        "en": "Historical AASM versions",
        "de": "Historische AASM-Versionen"},
    "prof_grp_dataset": {
        "nl": "Datasetreproductie (bevroren)",
        "fr": "Reproduction de jeux de données (figée)",
        "en": "Dataset reproduction (frozen)",
        "de": "Datensatz-Reproduktion (eingefroren)"},
    "prof_grp_exp": {
        "nl": "Experimenteel — niet voor klinisch gebruik",
        "fr": "Expérimental — pas pour un usage clinique",
        "en": "Experimental — not for clinical use",
        "de": "Experimentell — nicht für den klinischen Einsatz"},

    "prof_exp_warn": {
        "nl": "Deze profielen zijn niet tegen menselijke scoring gevalideerd, of "
              "zijn gemeten en afgewezen. Ze staan in de lijst zodat een negatief "
              "resultaat reproduceerbaar blijft, niet als keuze voor een verslag. "
              "Gebruik ze uitsluitend voor onderzoek, en vermeld altijd welk "
              "profiel is gebruikt.",
        "fr": "Ces profils ne sont pas validés contre la lecture humaine, ou ont "
              "été mesurés et rejetés. Ils figurent dans la liste pour que les "
              "résultats négatifs restent reproductibles, non comme choix pour un "
              "compte rendu. À réserver à la recherche, en indiquant toujours le "
              "profil utilisé.",
        "en": "These profiles are not validated against human scoring, or have "
              "been measured and rejected. They are listed so a negative result "
              "stays reproducible, not as a choice for a report. Use them for "
              "research only, and always state which profile was used.",
        "de": "Diese Profile sind nicht gegen menschliche Auswertung validiert "
              "oder wurden gemessen und verworfen. Sie stehen in der Liste, damit "
              "negative Ergebnisse reproduzierbar bleiben, nicht als Wahl für "
              "einen Befund. Nur für die Forschung verwenden und immer angeben, "
              "welches Profil benutzt wurde."},

    "prof_help_toggle": {
        "nl": "Welk profiel moet ik kiezen?",
        "fr": "Quel profil choisir ?",
        "en": "Which profile should I choose?",
        "de": "Welches Profil soll ich wählen?"},

    "prof_help_intro": {
        "nl": "Een profiel bepaalt welke regels de scoring toepast: de "
              "flowreductiedrempel, of een desaturatie of arousal vereist is, en "
              "welke sensor de apneus scoort. Twijfel je, kies dan "
              "<strong>AASM v3 — Recommended</strong>; dat is de regel die "
              "geaccrediteerde labs sinds 31 december 2023 moeten volgen.",
        "fr": "Un profil détermine les règles appliquées : le seuil de réduction "
              "du débit, l'exigence d'une désaturation ou d'un micro-éveil, et le "
              "capteur qui score les apnées. En cas de doute, choisissez "
              "<strong>AASM v3 — Recommended</strong> : c'est la règle imposée aux "
              "laboratoires accrédités depuis le 31 décembre 2023.",
        "en": "A profile decides which rules the scoring applies: the flow "
              "reduction threshold, whether a desaturation or arousal is "
              "required, and which sensor scores apneas. When in doubt choose "
              "<strong>AASM v3 — Recommended</strong> — the rule accredited labs "
              "have had to follow since 31 December 2023.",
        "de": "Ein Profil legt fest, welche Regeln angewendet werden: die "
              "Flussreduktionsschwelle, ob eine Entsättigung oder ein Arousal "
              "gefordert ist, und welcher Sensor Apnoen scort. Im Zweifel "
              "<strong>AASM v3 — Recommended</strong> wählen — die Regel, an die "
              "akkreditierte Labore seit dem 31. Dezember 2023 gebunden sind."},

    "prof_help_v3": {
        "nl": "De huidige klinische standaard en zijn varianten. "
              "<em>Recommended</em> is de default. <em>Rule 1A, breath-graded</em> "
              "scoort per ademteug in plaats van per sample en geeft elk event een "
              "waarde voor hoe goed het aan de regel voldoet. <em>Dual-sensor</em> "
              "scoort apneus op thermistor én neusdruk. <em>Nasal-pressure "
              "reference</em> laat de afgeleide analyses op de neusdruk lopen in "
              "plaats van op de thermistor. Alle vier volgen dezelfde AASM-regel; "
              "ze verschillen in hoe ze die uitvoeren.",
        "fr": "Le standard clinique actuel et ses variantes. <em>Recommended</em> "
              "est le choix par défaut. <em>Rule 1A, breath-graded</em> score par "
              "cycle respiratoire plutôt que par échantillon et attribue à chaque "
              "événement une valeur de conformité à la règle. <em>Dual-sensor</em> "
              "score les apnées sur la thermistance et la pression nasale. "
              "<em>Nasal-pressure reference</em> fait porter les analyses dérivées "
              "sur la pression nasale. Les quatre suivent la même règle AASM ; "
              "elles diffèrent par la mise en œuvre.",
        "en": "The current clinical standard and its variants. "
              "<em>Recommended</em> is the default. <em>Rule 1A, breath-graded</em> "
              "scores per breath rather than per sample and gives each event a "
              "value for how well it meets the rule. <em>Dual-sensor</em> scores "
              "apneas on both thermistor and nasal pressure. <em>Nasal-pressure "
              "reference</em> points the derived analyses at nasal pressure "
              "instead of the thermistor. All four follow the same AASM rule; they "
              "differ in how they carry it out.",
        "de": "Der aktuelle klinische Standard und seine Varianten. "
              "<em>Recommended</em> ist die Vorgabe. <em>Rule 1A, breath-graded</em> "
              "scort pro Atemzug statt pro Sample und gibt jedem Ereignis einen "
              "Wert dafür, wie gut es die Regel erfüllt. <em>Dual-sensor</em> "
              "scort Apnoen auf Thermistor und Nasendruck. <em>Nasal-pressure "
              "reference</em> lässt die abgeleiteten Analysen auf dem Nasendruck "
              "laufen. Alle vier folgen derselben AASM-Regel; sie unterscheiden "
              "sich in der Umsetzung."},

    "prof_help_hist": {
        "nl": "AASM v1 (2007) en v2 (2012–2020), plus de CMS/Medicare-variant. "
              "Nuttig als je een oudere opname wil scoren volgens de regel die "
              "toen gold, of als een verzekeraar een 4 %-desaturatie eist. Deze "
              "geven stelselmatig een lagere AHI dan v3, en dat is de bedoeling.",
        "fr": "AASM v1 (2007) et v2 (2012–2020), plus la variante CMS/Medicare. "
              "Utiles pour scorer un enregistrement ancien selon la règle de "
              "l'époque, ou lorsqu'un assureur exige une désaturation de 4 %. "
              "Ils donnent systématiquement un IAH plus bas que v3 : c'est voulu.",
        "en": "AASM v1 (2007) and v2 (2012–2020), plus the CMS/Medicare variant. "
              "Useful for scoring an older recording under the rule that applied "
              "at the time, or when an insurer requires a 4 % desaturation. These "
              "give a systematically lower AHI than v3, which is the point.",
        "de": "AASM v1 (2007) und v2 (2012–2020) sowie die CMS/Medicare-Variante. "
              "Nützlich, um eine ältere Aufzeichnung nach der damals geltenden "
              "Regel zu scoren, oder wenn ein Kostenträger eine 4-%-Entsättigung "
              "verlangt. Sie liefern systematisch einen niedrigeren AHI als v3 — "
              "genau das ist der Zweck."},

    "prof_help_dataset": {
        "nl": "Bevroren profielen die gepubliceerde cijfers reproduceren: de "
              "NSRR/MESA-conventie en de Chicago-criteria uit 1999. Ze zijn "
              "afgeschermd tegen wijzigingen die alle andere profielen wél "
              "krijgen, inclusief reparaties. Gebruik ze om een cohort na te "
              "rekenen, niet om een patiënt te scoren.",
        "fr": "Profils figés qui reproduisent des chiffres publiés : la convention "
              "NSRR/MESA et les critères de Chicago de 1999. Ils sont protégés des "
              "modifications que reçoivent tous les autres profils, corrections "
              "comprises. À utiliser pour recalculer une cohorte, pas pour scorer "
              "un patient.",
        "en": "Frozen profiles that reproduce published figures: the NSRR/MESA "
              "convention and the 1999 Chicago criteria. They are shielded from "
              "changes every other profile receives, repairs included. Use them to "
              "recompute a cohort, not to score a patient.",
        "de": "Eingefrorene Profile, die veröffentlichte Zahlen reproduzieren: die "
              "NSRR/MESA-Konvention und die Chicago-Kriterien von 1999. Sie sind "
              "gegen Änderungen abgeschirmt, die alle anderen Profile erhalten, "
              "Reparaturen eingeschlossen. Für die Neuberechnung einer Kohorte, "
              "nicht für die Auswertung eines Patienten."},

    "prof_help_exp": {
        "nl": "Onderzoeksarmen. Sommige zijn nog niet tegen menselijke scoring "
              "gemeten; andere zijn gemeten en afgewezen, en staan er alleen nog "
              "zodat dat negatieve resultaat reproduceerbaar blijft. Hier horen "
              "ook <em>Strict</em> en <em>Sensitive</em>: die zijn opzettelijk te "
              "streng en te ruim en vormen samen met Recommended het "
              "betrouwbaarheidsinterval van de AHI — als losse keuze voor een "
              "verslag zijn ze niet bedoeld. Wat je hier kiest hoort in de "
              "methodesectie van een studie, niet in een patiëntendossier.",
        "fr": "Bras de recherche. Certains ne sont pas encore mesurés contre la "
              "lecture humaine ; d'autres l'ont été et ont été rejetés, et ne "
              "restent là que pour garder ce résultat négatif reproductible. On y "
              "trouve aussi <em>Strict</em> et <em>Sensitive</em> : délibérément "
              "trop stricts et trop larges, ils forment avec Recommended "
              "l'intervalle de confiance de l'IAH — ils ne sont pas prévus comme "
              "choix isolé pour un compte rendu. Ce que vous choisissez ici "
              "appartient à la section méthodes d'une étude, pas à un dossier.",
        "en": "Research arms. Some have not yet been measured against human "
              "scoring; others have been measured and rejected, and remain only so "
              "that negative result stays reproducible. <em>Strict</em> and "
              "<em>Sensitive</em> live here too: they are deliberately too strict "
              "and too permissive and together with Recommended they form the AHI "
              "confidence interval — they are not meant as a standalone choice for "
              "a report. What you pick here belongs in the methods section of a "
              "study, not in a patient record.",
        "de": "Forschungsarme. Einige sind noch nicht gegen menschliche Auswertung "
              "gemessen; andere wurden gemessen und verworfen und bleiben nur "
              "erhalten, damit dieses negative Ergebnis reproduzierbar bleibt. "
              "Auch <em>Strict</em> und <em>Sensitive</em> gehören hierher: "
              "absichtlich zu streng und zu großzügig, bilden sie mit Recommended "
              "das Konfidenzintervall des AHI — als Einzelwahl für einen Befund "
              "sind sie nicht gedacht. Was Sie hier wählen, gehört in den "
              "Methodenteil einer Studie, nicht in eine Patientenakte."},

    "prof_help_pin": {
        "nl": "Het gekozen profiel staat in het rapport en in de metadata van de "
              "job. Wil je dat cijfers over de tijd vergelijkbaar blijven, pin dan "
              "zowel het profiel als de psgscoring-versie — een profielnaam alleen "
              "is daarvoor niet genoeg.",
        "fr": "Le profil retenu figure dans le rapport et dans les métadonnées de "
              "la tâche. Pour que les chiffres restent comparables dans le temps, "
              "fixez à la fois le profil et la version de psgscoring : le nom du "
              "profil seul n'y suffit pas.",
        "en": "The chosen profile appears in the report and in the job metadata. If "
              "you need figures to stay comparable over time, pin both the profile "
              "and the psgscoring version — a profile name alone is not enough.",
        "de": "Das gewählte Profil erscheint im Bericht und in den Metadaten des "
              "Auftrags. Damit Zahlen über die Zeit vergleichbar bleiben, fixieren "
              "Sie Profil und psgscoring-Version — der Profilname allein genügt "
              "nicht."},
}
TRANSLATIONS.update(_PROFILE_HELP_V0220)


# ─────────────────────────────────────────────────────────────────────────
# v0.23.0 — profielmatrix in het rapport (studies)
#
# De matrix is een STUDIE-artefact en verschijnt niet in een klinisch rapport
# zonder studieprofiel-set. De tabel die hij vervangt is in v0.15.0 bewust uit
# de klinische PDF gehaald omdat hij niet gevalideerd is als ernstinstrument;
# dat besluit blijft staan.
#
# Voetnoot 1 benoemt welk profiel het hoofdresultaat draagt, want dat is het
# enige dat de kop, de severity en de besluittekst voedt. De overige rijen zijn
# dezelfde opname onder een andere regelset.
# ─────────────────────────────────────────────────────────────────────────

_PROFILE_MATRIX_V0230 = {
    "pdf_prof_matrix_title": {
        "nl": "Profielmatrix (studie)", "fr": "Matrice de profils (étude)",
        "en": "Profile matrix (study)", "de": "Profilmatrix (Studie)"},
    "pdf_prof_matrix_profile": {
        "nl": "Profiel", "fr": "Profil", "en": "Profile", "de": "Profil"},
    "pdf_prof_matrix_ruleset": {
        "nl": "Regelset", "fr": "Jeu de règles", "en": "Rule set",
        "de": "Regelwerk"},
    "pdf_prof_matrix_events": {
        "nl": "Events", "fr": "Évén.", "en": "Events", "de": "Ereign."},
    "pdf_prof_matrix_severity": {
        "nl": "Ernst", "fr": "Sévérité", "en": "Severity", "de": "Schwere"},
    "pdf_prof_matrix_delta": {
        "nl": "Δ AHI", "fr": "Δ IAH", "en": "Δ AHI", "de": "Δ AHI"},

    "pdf_prof_matrix_fn_primary": {
        "nl": "Hoofdresultaat en besluit volgen ▶ {profile}; de overige rijen "
              "zijn dezelfde opname onder een andere regelset of methode.",
        "fr": "Le résultat principal et la conclusion suivent ▶ {profile} ; les "
              "autres lignes sont le même enregistrement sous un autre jeu de "
              "règles ou une autre méthode.",
        "en": "The main result and the conclusion follow ▶ {profile}; the other "
              "rows are the same recording under a different rule set or method.",
        "de": "Hauptergebnis und Beurteilung folgen ▶ {profile}; die übrigen "
              "Zeilen sind dieselbe Aufzeichnung unter einem anderen Regelwerk "
              "oder Verfahren."},
    "pdf_prof_matrix_fn_channels": {
        "nl": "Alle rijen gebruiken dezelfde kanalen en hetzelfde hypnogram — "
              "dat is wat de vergelijking betekenisvol maakt. De "
              "kanaalherkomst-disclaimer elders in dit rapport geldt voor elke rij.",
        "fr": "Toutes les lignes utilisent les mêmes voies et le même "
              "hypnogramme — c'est ce qui rend la comparaison significative. "
              "L'avertissement sur l'origine des voies vaut pour chaque ligne.",
        "en": "Every row uses the same channels and the same hypnogram — that is "
              "what makes the comparison meaningful. The channel-provenance "
              "disclaimer elsewhere in this report applies to every row.",
        "de": "Alle Zeilen verwenden dieselben Kanäle und dasselbe Hypnogramm — "
              "das macht den Vergleich aussagekräftig. Der Hinweis zur "
              "Kanalherkunft gilt für jede Zeile."},
    "pdf_prof_matrix_fn_rdi": {
        "nl": "„—\" bij RDI: de RERA-detectie levert onder dit profiel geen "
              "waarde. Dat is een ontbrekende meting, niet 0,0.",
        "fr": "« — » pour le RDI : la détection des RERA ne fournit pas de valeur "
              "sous ce profil. C'est une mesure absente, pas 0,0.",
        "en": "“—” in the RDI column: RERA detection yields no value under this "
              "profile. That is a missing measurement, not 0.0.",
        "de": "„—\" beim RDI: Die RERA-Erkennung liefert unter diesem Profil "
              "keinen Wert. Das ist eine fehlende Messung, nicht 0,0."},
    "pdf_prof_matrix_fn_frozen": {
        "nl": "🔒 markeert een bevroren reproductieprofiel. Die bestaan om "
              "gepubliceerde cijfers na te rekenen en zijn afgeschermd tegen "
              "reparaties die elk ander profiel wél krijgt; ze dragen nooit het "
              "hoofdresultaat.",
        "fr": "🔒 signale un profil de reproduction figé. Ils servent à recalculer "
              "des chiffres publiés et sont protégés des corrections que "
              "reçoivent les autres profils ; ils ne portent jamais le résultat "
              "principal.",
        "en": "🔒 marks a frozen reproduction profile. These exist to recompute "
              "published figures and are shielded from repairs every other "
              "profile receives; they never carry the main result.",
        "de": "🔒 kennzeichnet ein eingefrorenes Reproduktionsprofil. Sie dienen "
              "der Nachrechnung veröffentlichter Zahlen und sind gegen "
              "Reparaturen abgeschirmt, die alle anderen Profile erhalten; sie "
              "tragen nie das Hauptergebnis."},
    "pdf_prof_matrix_fn_experimental": {
        "nl": "Deze matrix bevat experimentele profielen. Die zijn niet tegen "
              "menselijke scoring gevalideerd, of gemeten en afgewezen; ze horen "
              "in de methodesectie van een studie, niet in een klinisch besluit.",
        "fr": "Cette matrice contient des profils expérimentaux. Ils ne sont pas "
              "validés contre la lecture humaine, ou ont été mesurés et rejetés ; "
              "ils relèvent de la section méthodes d'une étude, pas d'une "
              "décision clinique.",
        "en": "This matrix contains experimental profiles. They are not validated "
              "against human scoring, or were measured and rejected; they belong "
              "in the methods section of a study, not in a clinical decision.",
        "de": "Diese Matrix enthält experimentelle Profile. Sie sind nicht gegen "
              "menschliche Auswertung validiert oder wurden gemessen und "
              "verworfen; sie gehören in den Methodenteil einer Studie, nicht in "
              "eine klinische Entscheidung."},
    "pdf_prof_matrix_fn_preconfig": {
        "nl": "Deze vergelijking is gegenereerd vóór studieconfiguratie bestond; "
              "welk profiel primair was, is niet vastgelegd.",
        "fr": "Cette comparaison a été générée avant l'existence de la "
              "configuration d'étude ; le profil principal n'est pas enregistré.",
        "en": "This comparison was generated before study configuration existed; "
              "which profile was primary is not recorded.",
        "de": "Dieser Vergleich entstand, bevor es eine Studienkonfiguration gab; "
              "welches Profil primär war, ist nicht festgehalten."},
    "pdf_prof_matrix_fn_mismatch": {
        "nl": "⚠ De primaire rij geeft AHI {matrix}/u terwijl het hoofdresultaat "
              "{head}/u geeft. Twee codepaden zijn uit de pas; behandel dit "
              "rapport als onbetrouwbaar tot het verschil verklaard is.",
        "fr": "⚠ La ligne principale donne un IAH de {matrix}/h alors que le "
              "résultat principal donne {head}/h. Deux chemins de code divergent ; "
              "considérez ce rapport comme non fiable jusqu'à explication.",
        "en": "⚠ The primary row gives AHI {matrix}/h while the main result gives "
              "{head}/h. Two code paths disagree; treat this report as unreliable "
              "until the difference is explained.",
        "de": "⚠ Die primäre Zeile ergibt AHI {matrix}/h, das Hauptergebnis "
              "{head}/h. Zwei Codepfade weichen ab; behandeln Sie diesen Bericht "
              "als unzuverlässig, bis die Abweichung erklärt ist."},
}
TRANSLATIONS.update(_PROFILE_MATRIX_V0230)


# v0.23.0 — meldingen bij de studieprofiel-set (admin)
_STUDY_SET_V0230 = {
    "study_set_saved": {
        "nl": "Studieprofiel-set opgeslagen.",
        "fr": "Ensemble de profils d'étude enregistré.",
        "en": "Study profile set saved.",
        "de": "Studien-Profilsatz gespeichert."},
    "study_set_cleared": {
        "nl": "Studieprofiel-set gewist; rapporten volgen weer het klinische gedrag "
              "zonder profielmatrix.",
        "fr": "Ensemble de profils d'étude effacé ; les comptes rendus reprennent le "
              "comportement clinique sans matrice de profils.",
        "en": "Study profile set cleared; reports return to the clinical behaviour "
              "without a profile matrix.",
        "de": "Studien-Profilsatz gelöscht; Berichte folgen wieder dem klinischen "
              "Verhalten ohne Profilmatrix."},
}
TRANSLATIONS.update(_STUDY_SET_V0230)

# v0.26.0 — het profielrapport als apart onderzoeksdocument.
_PROFILE_REPORT_V0260 = {
    "profile_report_absent": {
        "nl": "Voor deze opname is geen profielvergelijking gedraaid, dus er is "
              "geen profielrapport. Een vergelijking wordt alleen ingeschakeld "
              "wanneer de site een studieprofiel-set heeft.",
        "fr": "Aucune comparaison de profils n'a été effectuée pour cet "
              "enregistrement, donc il n'y a pas de rapport de profils. Une "
              "comparaison n'est lancée que si le site dispose d'un ensemble de "
              "profils d'étude.",
        "en": "No profile comparison was run for this recording, so there is no "
              "profile report. A comparison is only queued when the site has a "
              "study profile set.",
        "de": "Für diese Aufzeichnung wurde kein Profilvergleich durchgeführt, "
              "daher gibt es keinen Profilbericht. Ein Vergleich wird nur "
              "eingeplant, wenn der Standort einen Studien-Profilsatz hat."},
    "profile_report_link": {
        "nl": "Profielrapport (onderzoek)",
        "fr": "Rapport de profils (recherche)",
        "en": "Profile report (research)",
        "de": "Profilbericht (Forschung)"},
    "profile_report_pending": {
        "nl": "Profielvergelijking staat in de wachtrij; dit duurt tientallen "
              "minuten en houdt het klinische rapport niet op.",
        "fr": "La comparaison de profils est en file d'attente ; elle prend "
              "plusieurs dizaines de minutes et ne retarde pas le compte rendu "
              "clinique.",
        "en": "The profile comparison is queued; it takes tens of minutes and "
              "does not hold up the clinical report.",
        "de": "Der Profilvergleich ist eingeplant; er dauert mehrere zehn "
              "Minuten und verzögert den klinischen Bericht nicht."},
}
TRANSLATIONS.update(_PROFILE_REPORT_V0260)

# v0.26.0 — de profielvergelijking aanvragen: vooraf (vinkje) of achteraf (knop).
_STUDY_CMP_V0260 = {
    "study_cmp_label": {
        "nl": "Ook een profielvergelijking draaien (onderzoek)",
        "fr": "Lancer aussi une comparaison de profils (recherche)",
        "en": "Also run a profile comparison (research)",
        "de": "Auch einen Profilvergleich durchführen (Forschung)"},
    "study_cmp_hint": {
        "nl": "Draait ná het klinische rapport, op een aparte wachtrij. Duurt "
              "tientallen minuten en houdt niets op. Kan ook later worden "
              "aangevraagd op de resultatenpagina.",
        "fr": "S'exécute après le compte rendu clinique, sur une file distincte. "
              "Prend plusieurs dizaines de minutes et ne retarde rien. Peut aussi "
              "être demandé plus tard depuis la page de résultats.",
        "en": "Runs after the clinical report, on a separate queue. Takes tens of "
              "minutes and holds nothing up. Can also be requested later from the "
              "results page.",
        "de": "Läuft nach dem klinischen Bericht auf einer eigenen Warteschlange. "
              "Dauert mehrere zehn Minuten und verzögert nichts. Kann auch später "
              "über die Ergebnisseite angefordert werden."},
    "study_cmp_profiles": {
        "nl": "profielen", "fr": "profils", "en": "profiles", "de": "Profile"},
    "study_cmp_primary": {
        "nl": "primair", "fr": "principal", "en": "primary", "de": "primär"},
    "study_cmp_button": {
        "nl": "Profielvergelijking aanvragen",
        "fr": "Demander une comparaison de profils",
        "en": "Request a profile comparison",
        "de": "Profilvergleich anfordern"},
    "study_cmp_queued": {
        "nl": "Profielvergelijking staat in de wachtrij. Ze draait op een aparte "
              "wachtrij en houdt klinisch werk niet op; het rapport verschijnt "
              "hier zodra ze klaar is.",
        "fr": "Comparaison de profils mise en file d'attente. Elle s'exécute sur "
              "une file distincte et ne retarde pas le travail clinique ; le "
              "rapport apparaîtra ici une fois terminé.",
        "en": "Profile comparison queued. It runs on a separate queue and does not "
              "hold up clinical work; the report appears here when it is done.",
        "de": "Profilvergleich eingeplant. Er läuft auf einer eigenen "
              "Warteschlange und verzögert die klinische Arbeit nicht; der "
              "Bericht erscheint hier, sobald er fertig ist."},
    "study_cmp_no_set": {
        "nl": "Deze site heeft geen studieprofiel-set, dus er valt niets te "
              "vergelijken. Een beheerder stelt die in.",
        "fr": "Ce site n'a pas d'ensemble de profils d'étude ; il n'y a donc rien "
              "à comparer. Un administrateur peut le configurer.",
        "en": "This site has no study profile set, so there is nothing to compare. "
              "An administrator can configure one.",
        "de": "Dieser Standort hat keinen Studien-Profilsatz, es gibt also nichts "
              "zu vergleichen. Ein Administrator kann ihn einrichten."},
    "study_cmp_no_edf": {
        "nl": "Het EDF-bestand van deze opname is niet meer aanwezig; een "
              "vergelijking kan alleen op de oorspronkelijke opname draaien.",
        "fr": "Le fichier EDF de cet enregistrement n'est plus disponible ; une "
              "comparaison ne peut s'exécuter que sur l'enregistrement d'origine.",
        "en": "The EDF file for this recording is no longer present; a comparison "
              "can only run on the original recording.",
        "de": "Die EDF-Datei dieser Aufzeichnung ist nicht mehr vorhanden; ein "
              "Vergleich kann nur mit der Originalaufzeichnung laufen."},
    "study_cmp_no_hypno": {
        "nl": "Deze analyse heeft geen opgeslagen hypnogram. Zonder dat zou de "
              "vergelijking opnieuw stageren en mogelijk andere slaapfasen "
              "gebruiken dan het rapport — dat levert een vergelijking op met "
              "iets dat niet in het rapport staat.",
        "fr": "Cette analyse n'a pas d'hypnogramme enregistré. Sans lui, la "
              "comparaison referait le stadification et pourrait utiliser d'autres "
              "stades que le compte rendu — elle comparerait donc avec autre chose "
              "que ce qui figure dans le rapport.",
        "en": "This analysis has no stored hypnogram. Without one the comparison "
              "would re-stage and might use different sleep stages than the "
              "report — comparing against something the report does not contain.",
        "de": "Für diese Analyse ist kein Hypnogramm gespeichert. Ohne dieses "
              "würde der Vergleich neu stadieren und möglicherweise andere "
              "Schlafstadien verwenden als der Bericht."},
    "study_cmp_failed": {
        "nl": "Profielvergelijking kon niet worden ingeschakeld.",
        "fr": "Impossible de mettre la comparaison de profils en file d'attente.",
        "en": "Could not queue the profile comparison.",
        "de": "Der Profilvergleich konnte nicht eingeplant werden."},
}
TRANSLATIONS.update(_STUDY_CMP_V0260)

# v0.27.0 — de RIP-paarpoort in het rapport. Stond er tot nu toe niet in.
_RIP_GATE_V0270 = {
    "pdf_rip_gate_single": {
        "nl": "⚠ Effortclassificatie op één RIP-kanaal",
        "fr": "⚠ Classification de l'effort sur un seul canal RIP",
        "en": "⚠ Effort classification on a single RIP channel",
        "de": "⚠ Effort-Klassifikation auf nur einem RIP-Kanal"},
    "pdf_rip_gate_suspect": {
        "nl": "⚠ Effortclassificatie op één RIP-kanaal — afkeuring twijfelachtig",
        "fr": "⚠ Classification de l'effort sur un seul canal RIP — rejet douteux",
        "en": "⚠ Effort classification on a single RIP channel — rejection doubtful",
        "de": "⚠ Effort-Klassifikation auf einem RIP-Kanal — Ablehnung fraglich"},
    "pdf_rip_mode": {
        "nl": "Modus", "fr": "Mode", "en": "Mode", "de": "Modus"},
    "pdf_rip_working": {
        "nl": "gebruikt kanaal", "fr": "canal utilisé",
        "en": "channel used", "de": "verwendeter Kanal"},
    "pdf_rip_ratio": {
        "nl": "Energieverhouding thorax/abdomen",
        "fr": "Rapport d'énergie thorax/abdomen",
        "en": "Thorax/abdomen energy ratio",
        "de": "Energieverhältnis Thorax/Abdomen"},
}
TRANSLATIONS.update(_RIP_GATE_V0270)
