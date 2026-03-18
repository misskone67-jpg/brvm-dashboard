"""
scheduler.py — Mise à jour automatique BRVM
=============================================
✅ Vérifie toutes les heures si de nouvelles annonces sont disponibles
✅ Met à jour dividendes.csv automatiquement
✅ Envoie un email Gmail si nouvelle annonce détectée

Configuration :
    1. Remplis EMAIL_EXPEDITEUR, MOT_DE_PASSE_APP et EMAIL_DESTINATAIRE
    2. Lance : python scheduler.py
    3. Laisse tourner en arrière-plan (ne pas fermer le terminal)

Dépendances :
    pip install schedule requests beautifulsoup4 pandas lxml
"""

import schedule
import time
import smtplib
import logging
import pandas as pd
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from scraper import scraper_page, COLONNES

# ── Logs ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.FileHandler("brvm_scheduler.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURATION — À REMPLIR
# ══════════════════════════════════════════════════════════════════════════════
EMAIL_EXPEDITEUR   = "misskone67@gmail.com"       # Ton adresse Gmail
MOT_DE_PASSE_APP   = "isnx wkep urgh pmwy"       # Mot de passe d'application Gmail (16 caractères)
EMAIL_DESTINATAIRE = "misskone67@gmail.com"       # Adresse qui reçoit les notifications

CSV_FILE           = "dividendes.csv"            # Fichier de données
NB_PAGES_SCRAPING  = 3                           # Nombre de pages à vérifier (les + récentes)
# ══════════════════════════════════════════════════════════════════════════════


def charger_donnees_existantes() -> pd.DataFrame:
    """Charge le CSV existant ou retourne un DataFrame vide."""
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=COLONNES)
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=COLONNES)


def sauvegarder_donnees(df: pd.DataFrame):
    """Sauvegarde le DataFrame dans le CSV."""
    df.to_csv(CSV_FILE, index=False)
    log.info(f"✅ CSV mis à jour : {len(df)} lignes → {CSV_FILE}")


def detecter_nouvelles_annonces(df_ancien: pd.DataFrame,
                                 df_nouveau: pd.DataFrame) -> pd.DataFrame:
    """
    Compare les deux DataFrames et retourne les nouvelles lignes.
    Une ligne est nouvelle si la combinaison Emetteur+Exercice n'existait pas.
    """
    if df_ancien.empty:
        return df_nouveau

    # Créer une clé unique Emetteur|Exercice
    cle_ancien  = set(
        df_ancien["Emetteur"].astype(str) + "|" + df_ancien["Exercice"].astype(str)
    )
    cle_nouveau = (
        df_nouveau["Emetteur"].astype(str) + "|" + df_nouveau["Exercice"].astype(str)
    )

    nouvelles = df_nouveau[~cle_nouveau.isin(cle_ancien)]
    return nouvelles


def envoyer_email(nouvelles: pd.DataFrame):
    """Envoie un email de notification avec les nouvelles annonces."""
    if EMAIL_EXPEDITEUR == "ton.email@gmail.com":
        log.warning("⚠️  Email non configuré. Remplis EMAIL_EXPEDITEUR et MOT_DE_PASSE_APP.")
        return

    nb = len(nouvelles)
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")

    # ── Corps de l'email ──────────────────────────────────────────────────────
    lignes_html = ""
    for _, row in nouvelles.iterrows():
        lignes_html += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd;">{row.get('Emetteur','')}</td>
            <td style="padding:8px; border:1px solid #ddd; text-align:center;">{row.get('Exercice','')}</td>
            <td style="padding:8px; border:1px solid #ddd; text-align:right;">
                <strong>{row.get('Dividende_net', 0):,.2f} FCFA</strong>
            </td>
            <td style="padding:8px; border:1px solid #ddd; text-align:center;">{row.get('Date_paiement','')}</td>
        </tr>
        """

    html = f"""
    <html><body style="font-family: Arial, sans-serif; background:#f5f5f5; padding:20px;">
        <div style="background:white; border-radius:12px; padding:24px; max-width:700px; margin:auto;
                    box-shadow:0 4px 12px rgba(0,0,0,0.1);">

            <div style="background:#1F4E79; color:white; padding:16px; border-radius:8px; margin-bottom:20px;">
                <h2 style="margin:0;">📈 BRVM — Nouvelles annonces de dividendes</h2>
                <p style="margin:4px 0 0 0; opacity:0.8;">Détecté le {date_str}</p>
            </div>

            <p style="color:#333; font-size:16px;">
                <strong>{nb} nouvelle(s) annonce(s)</strong> de paiement de dividendes
                ont été publiées sur brvm.org :
            </p>

            <table style="width:100%; border-collapse:collapse; margin:16px 0;">
                <thead>
                    <tr style="background:#1F4E79; color:white;">
                        <th style="padding:10px; text-align:left;">Émetteur</th>
                        <th style="padding:10px; text-align:center;">Exercice</th>
                        <th style="padding:10px; text-align:right;">Dividende net</th>
                        <th style="padding:10px; text-align:center;">Date paiement</th>
                    </tr>
                </thead>
                <tbody>{lignes_html}</tbody>
            </table>

            <div style="background:#FFF9E6; border-left:4px solid #FFD700;
                        padding:12px 16px; border-radius:4px; margin-top:16px;">
                <p style="margin:0; color:#555;">
                    💡 Ouvre ton dashboard BRVM pour voir l'analyse complète.
                </p>
            </div>

            <p style="color:#999; font-size:12px; margin-top:20px; text-align:center;">
                Dashboard BRVM — Mise à jour automatique toutes les heures
            </p>
        </div>
    </body></html>
    """

    # ── Envoi via Gmail SMTP ──────────────────────────────────────────────────
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📈 BRVM — {nb} nouvelle(s) annonce(s) de dividendes ({date_str})"
        msg["From"]    = EMAIL_EXPEDITEUR
        msg["To"]      = EMAIL_DESTINATAIRE
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_EXPEDITEUR, MOT_DE_PASSE_APP)
            smtp.sendmail(EMAIL_EXPEDITEUR, EMAIL_DESTINATAIRE, msg.as_string())

        log.info(f"📧 Email envoyé à {EMAIL_DESTINATAIRE} ({nb} nouvelles annonces)")

    except smtplib.SMTPAuthenticationError:
        log.error("❌ Erreur authentification Gmail. Vérifie EMAIL_EXPEDITEUR et MOT_DE_PASSE_APP.")
    except Exception as e:
        log.error(f"❌ Erreur envoi email : {e}")


def verifier_nouvelles_annonces():
    """
    Fonction principale appelée toutes les heures :
    1. Scrape les premières pages (les plus récentes)
    2. Compare avec les données existantes
    3. Met à jour le CSV si nouvelles annonces
    4. Envoie un email de notification
    """
    log.info("=" * 55)
    log.info("🔍 Vérification des nouvelles annonces BRVM...")
    log.info("=" * 55)

    # Charger les données existantes
    df_ancien = charger_donnees_existantes()
    log.info(f"   Données existantes : {len(df_ancien)} lignes")

    # Scraper les premières pages (les plus récentes)
    frames = []
    for page in range(NB_PAGES_SCRAPING):
        log.info(f"   Scraping page {page + 1}/{NB_PAGES_SCRAPING}...")
        try:
            df_page = scraper_page(page=page, avec_prix=True)
            if not df_page.empty:
                frames.append(df_page)
        except Exception as e:
            log.error(f"   Erreur page {page} : {e}")
        time.sleep(1.5)

    if not frames:
        log.warning("⚠️  Aucune donnée récupérée lors de cette vérification.")
        return

    df_nouveau = pd.concat(frames, ignore_index=True)
    log.info(f"   Données récupérées : {len(df_nouveau)} lignes")

    # Détecter les nouvelles annonces
    nouvelles = detecter_nouvelles_annonces(df_ancien, df_nouveau)

    if nouvelles.empty:
        log.info("✅ Aucune nouvelle annonce détectée.")
    else:
        log.info(f"🆕 {len(nouvelles)} nouvelle(s) annonce(s) détectée(s) !")
        for _, row in nouvelles.iterrows():
            log.info(f"   → {row.get('Emetteur','')} | {row.get('Exercice','')} | {row.get('Dividende_net',0):,.2f} FCFA")

        # Mettre à jour le CSV
        df_mis_a_jour = pd.concat([df_ancien, nouvelles], ignore_index=True)
        df_mis_a_jour = df_mis_a_jour.drop_duplicates(
            subset=["Emetteur", "Exercice"], keep="last"
        ).sort_values(["Emetteur", "Exercice"]).reset_index(drop=True)
        sauvegarder_donnees(df_mis_a_jour)

        # Envoyer l'email
        envoyer_email(nouvelles)

    log.info(f"⏰ Prochaine vérification dans 1 heure.")


# ── Planification ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🚀 Démarrage du scheduler BRVM")
    log.info(f"   Vérification toutes les heures")
    log.info(f"   Notifications envoyées à : {EMAIL_DESTINATAIRE}")
    log.info(f"   Fichier de données : {CSV_FILE}")
    log.info("=" * 55)

    # Vérifier immédiatement au démarrage
    verifier_nouvelles_annonces()

    # Puis toutes les heures
    schedule.every(1).hours.do(verifier_nouvelles_annonces)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes si une tâche est en attente