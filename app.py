"""
app.py — Dashboard BRVM Dividendes
====================================
✅ Compatible avec le nouveau scraper.py (webdriver-manager)
   → Plus besoin de driver_path !

Installation :
    pip install streamlit selenium webdriver-manager pandas plotly openpyxl

Lancement :
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import threading
from scraper import scraper_page, scraper_toutes_pages
from scheduler import verifier_nouvelles_annonces
import schedule
import time

# ── Lancer le scheduler en arrière-plan ───────────────────────────────────────
def lancer_scheduler():
    schedule.every(1).hours.do(verifier_nouvelles_annonces)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Démarrer le thread une seule fois
if "scheduler_started" not in st.session_state:
    st.session_state.scheduler_started = True
    thread = threading.Thread(target=lancer_scheduler, daemon=True)
    thread.start()

# ── Configuration ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard BRVM – Dividendes",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSV_FILE = "dividendes.csv"

# ── CSS personnalisé ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1F4E79;
        border-bottom: 3px solid #FFD700;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1F4E79, #2E75B6);
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    div[data-testid="metric-container"] label {
        color: #BDD7EE !important;
        font-size: 0.85rem;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #FFD700 !important;
        font-size: 1.6rem;
        font-weight: 700;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1F4E79 0%, #2E75B6 100%);
    }
    section[data-testid="stSidebar"] * { color: white !important; }
    div.stButton > button {
        background: linear-gradient(90deg, #1F4E79, #2E75B6);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #FFD700, #FFA500);
        color: #1F4E79;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1F4E79;
        margin: 20px 0 10px 0;
        padding-left: 10px;
        border-left: 4px solid #FFD700;
    }
</style>
""", unsafe_allow_html=True)

# ── En-tête ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📈 Dashboard BRVM — Dividendes & Rendement</div>', unsafe_allow_html=True)

# ── Rafraîchissement automatique toutes les 5 minutes ─────────────────────────
import os
from datetime import datetime

csv_modif = ""
if os.path.exists(CSV_FILE):
    ts = os.path.getmtime(CSV_FILE)
    csv_modif = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
    st.caption(f"🔄 Dernière mise à jour des données : **{csv_modif}**")

# Rafraîchir automatiquement toutes les 5 minutes
st.markdown("""
<script>
setTimeout(function() {{ window.location.reload(); }}, 300000);
</script>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ Navigation")
    menu = st.selectbox(
        "",
        [
            "🏠 Accueil",
            "🔍 Scraper une page",
            "🕷️ Scraper toutes les pages",
            "🏆 Top 10 Dividendes",
            "💹 Top 10 Rendement",
            "📋 Données complètes",
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")

    # Options scraping
    st.markdown("### ⚙️ Options")
    visible   = False  # Plus de Selenium, pas besoin
    avec_prix = st.toggle("💰 Récupérer les prix", value=True,
                          help="Récupérer le prix de chaque action (plus lent)")
    st.markdown("---")
    st.markdown("**BRVM** – Bourse Régionale des Valeurs Mobilières")
    st.caption("© 2025 Dashboard BRVM")


# ── Chargement des données ─────────────────────────────────────────────────────
@st.cache_data(ttl=300)  # Cache de 5 minutes — se rafraîchit automatiquement
def charger_donnees():
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty or df.columns.tolist() == []:
            return pd.DataFrame()
        df["Dividende_net"] = pd.to_numeric(df["Dividende_net"], errors="coerce").fillna(0)
        if "Prix_action" in df.columns:
            df["Prix_action"] = pd.to_numeric(df["Prix_action"], errors="coerce").fillna(0)
            df["Rendement"] = df.apply(
                lambda r: round(r["Dividende_net"] / r["Prix_action"] * 100, 2)
                if r["Prix_action"] > 0 else 0.0, axis=1
            )
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()

df = charger_donnees()


# ══════════════════════════════════════════════════════════════════════════════
#  🏠 ACCUEIL
# ══════════════════════════════════════════════════════════════════════════════
if menu == "🏠 Accueil":

    if not df.empty:
        # KPIs globaux
        st.markdown("<div class='section-header'>📊 Vue d'ensemble</div>", unsafe_allow_html=True)
        rend_max = df['Rendement'].max() if 'Rendement' in df.columns else 0
        rend_moy = df[df['Rendement']>0]['Rendement'].mean() if 'Rendement' in df.columns and df['Rendement'].sum()>0 else 0

        # Leaders
        leader_div  = df.loc[df['Dividende_net'].idxmax(), 'Emetteur'] if not df.empty else "N/A"
        leader_rend = df.loc[df['Rendement'].idxmax(), 'Emetteur'] if 'Rendement' in df.columns and rend_max > 0 else "N/A"

        # Ligne 1 : KPIs chiffrés
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("📋 Total annonces",     f"{len(df):,}")
        c2.metric("🏢 Émetteurs",          f"{df['Emetteur'].nunique()}")
        c3.metric("🏆 Meilleur dividende", f"{df['Dividende_net'].max():,.0f} FCFA")
        c4.metric("💰 Dividende moyen",    f"{df['Dividende_net'].mean():,.0f} FCFA")
        c5.metric("💹 Meilleur rendement", f"{rend_max:.2f}%" if rend_max > 0 else "N/A")
        c6.metric("📊 Rendement moyen",    f"{rend_moy:.2f}%" if rend_moy > 0 else "N/A")

        # Ligne 2 : Leaders
        st.markdown("&nbsp;", unsafe_allow_html=True)
        l1, l2, l3, l4 = st.columns(4)
        l1.metric("🥇 Leader Dividende",  leader_div)
        l2.metric("🥇 Leader Rendement",  leader_rend)
        l3.metric("📅 Dernière année",    str(df['Exercice'].max()) if 'Exercice' in df.columns else "N/A")
        l4.metric("🕒 Dernière MAJ",      df['Date_scraping'].max() if 'Date_scraping' in df.columns else "N/A")

        st.markdown("---")

        # Top 10 Dividendes + Top 10 Rendement
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-header">🏆 Top 10 Dividendes</div>', unsafe_allow_html=True)
            top10_div = (df.groupby("Emetteur")["Dividende_net"].max()
                         .sort_values(ascending=False).head(10).reset_index())
            fig1 = px.bar(top10_div, x="Dividende_net", y="Emetteur", orientation="h",
                          text="Dividende_net", color="Dividende_net",
                          color_continuous_scale=["#BDD7EE","#1F4E79"], template="plotly_dark",
                          labels={"Dividende_net":"Dividende (FCFA)","Emetteur":""})
            fig1.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                               textfont=dict(color="white", size=10))
            fig1.update_layout(height=380, coloraxis_showscale=False,
                               yaxis=dict(categoryorder="total ascending"),
                               plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="white"), margin=dict(l=10,r=60,t=10,b=10))
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">💹 Top 10 Rendement</div>', unsafe_allow_html=True)
            if "Rendement" in df.columns and df["Rendement"].sum() > 0:
                top10_rend = (df[df["Rendement"]>0].groupby("Emetteur")["Rendement"]
                              .max().sort_values(ascending=False).head(10).reset_index())
                fig2 = px.bar(top10_rend, x="Rendement", y="Emetteur", orientation="h",
                              text="Rendement", color="Rendement",
                              color_continuous_scale=["#D9F0D3","#1A7A36"], template="plotly_dark",
                              labels={"Rendement":"Rendement (%)","Emetteur":""})
                fig2.update_traces(texttemplate="%{text:.2f}%", textposition="outside",
                                   textfont=dict(color="white", size=10))
                fig2.update_layout(height=380, coloraxis_showscale=False,
                                   yaxis=dict(categoryorder="total ascending"),
                                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                   font=dict(color="white"), margin=dict(l=10,r=60,t=10,b=10))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Lance le scraping avec 'Récupérer les prix' pour voir le rendement.")

        st.markdown("---")

        # Évolution + Dernières annonces
        col3, col4 = st.columns(2)
        with col3:
            st.markdown('<div class="section-header">📈 Évolution par année</div>', unsafe_allow_html=True)
            if "Exercice" in df.columns:
                par_annee = df.groupby("Exercice")["Dividende_net"].sum().reset_index()
                fig3 = px.bar(par_annee, x="Exercice", y="Dividende_net", text="Dividende_net",
                              color="Dividende_net", color_continuous_scale=["#BDD7EE","#FFD700"],
                              template="plotly_dark",
                              labels={"Dividende_net":"Total (FCFA)","Exercice":"Année"})
                fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                                   textfont=dict(color="white", size=9))
                fig3.update_layout(height=320, coloraxis_showscale=False,
                                   xaxis=dict(tickmode="linear", dtick=1),
                                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                   font=dict(color="white"), margin=dict(t=20,b=10))
                st.plotly_chart(fig3, use_container_width=True)

        with col4:
            st.markdown('<div class="section-header">🆕 Dernières annonces</div>', unsafe_allow_html=True)
            dernieres = df.sort_values("Date_scraping", ascending=False).head(10)[
                ["Emetteur","Exercice","Dividende_net","Date_paiement"]
            ].reset_index(drop=True)
            dernieres.index += 1
            st.dataframe(dernieres, use_container_width=True, height=320)

    else:
        st.info("💡 Aucune donnée chargée. Lance d'abord le scraping depuis le menu.")
        st.markdown("""
        ### 🚀 Comment démarrer ?
        1. Va dans **🔍 Scraper une page** pour tester
        2. Ou **🕷️ Scraper toutes les pages** pour tout collecter
        3. Explore ensuite **🏆 Top 10 Dividendes** et **💹 Top 10 Rendement**
        """)

# ══════════════════════════════════════════════════════════════════════════════
#  🔍 SCRAPER UNE PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🔍 Scraper une page":
    st.markdown('<div class="section-header">Scraper une page</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        page = st.slider("Numéro de page", min_value=0, max_value=39, value=0,
                         help="Le site BRVM a environ 40 pages de dividendes")
    with col2:
        st.metric("Page sélectionnée", f"{page + 1} / 40")

    # Initialiser session_state
    if "df_scraped" not in st.session_state:
        st.session_state.df_scraped = None

    if st.button("▶️  Lancer le scraping"):
        with st.spinner(f"⏳ Scraping de la page {page} en cours..."):
            try:
                df_page = scraper_page(page=page, visible=visible, avec_prix=avec_prix)
                if df_page.empty:
                    st.warning("⚠️  Aucune donnée trouvée sur cette page.")
                else:
                    # Sauvegarder dans session_state et CSV
                    st.session_state.df_scraped = df_page
                    df_page.to_csv(CSV_FILE, index=False)
                    st.cache_data.clear()

                    # ── KPIs ──────────────────────────────────────────────────
                    st.markdown("---")
                    st.markdown('<div class="section-header">📊 Résumé de la page</div>', unsafe_allow_html=True)
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("📋 Annonces",          f"{len(df_page)}")
                    k2.metric("🏆 Meilleur dividende", f"{df_page['Dividende_net'].max():,.0f} FCFA")
                    k3.metric("💰 Dividende moyen",    f"{df_page['Dividende_net'].mean():,.0f} FCFA")
                    rend = df_page['Rendement'].max() if 'Rendement' in df_page.columns else 0
                    k4.metric("💹 Meilleur rendement", f"{rend:.2f}%" if rend > 0 else "N/A")

                    # ── Tableau ───────────────────────────────────────────────
                    st.markdown("---")
                    st.markdown('<div class="section-header">📋 Données</div>', unsafe_allow_html=True)
                    st.dataframe(df_page[["Emetteur","Exercice","Dividende_net","Prix_action","Rendement","Date_paiement"]],
                                 use_container_width=True, height=280)

                    # ── Graphes ───────────────────────────────────────────────
                    st.markdown("---")
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown('<div class="section-header">🏆 Dividendes</div>', unsafe_allow_html=True)
                        fig_div = px.bar(
                            df_page.sort_values("Dividende_net", ascending=False),
                            x="Dividende_net", y="Emetteur", orientation="h",
                            text="Dividende_net", color="Dividende_net",
                            color_continuous_scale=["#BDD7EE","#1F4E79"],
                            template="plotly_dark",
                            labels={"Dividende_net":"Dividende (FCFA)","Emetteur":""}
                        )
                        fig_div.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                                              textfont=dict(color="white", size=10))
                        fig_div.update_layout(height=350, coloraxis_showscale=False,
                                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                              font=dict(color="white"), margin=dict(l=10,r=60,t=10,b=10))
                        st.plotly_chart(fig_div, use_container_width=True)

                    with col2:
                        st.markdown('<div class="section-header">💹 Rendement</div>', unsafe_allow_html=True)
                        if "Rendement" in df_page.columns and df_page["Rendement"].sum() > 0:
                            fig_rend = px.bar(
                                df_page[df_page["Rendement"]>0].sort_values("Rendement", ascending=False),
                                x="Rendement", y="Emetteur", orientation="h",
                                text="Rendement", color="Rendement",
                                color_continuous_scale=["#D9F0D3","#1A7A36"],
                                template="plotly_dark",
                                labels={"Rendement":"Rendement (%)","Emetteur":""}
                            )
                            fig_rend.update_traces(texttemplate="%{text:.2f}%", textposition="outside",
                                                   textfont=dict(color="white", size=10))
                            fig_rend.update_layout(height=350, coloraxis_showscale=False,
                                                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                                   font=dict(color="white"), margin=dict(l=10,r=60,t=10,b=10))
                            st.plotly_chart(fig_rend, use_container_width=True)
                        else:
                            st.info("Active 'Récupérer les prix' pour voir le rendement.")

                    # ── Téléchargement ────────────────────────────────────────
                    st.download_button(
                        "⬇️  Télécharger en CSV",
                        data=df_page.to_csv(index=False).encode("utf-8"),
                        file_name=f"brvm_page_{page}.csv",
                        mime="text/csv"
                    )
            except Exception as e:
                st.error(f"❌ Erreur : {e}")

    # ── Afficher les résultats stockés en session ─────────────────────────────
    if st.session_state.df_scraped is not None:
        df_page = st.session_state.df_scraped

        st.success(f"✅ {len(df_page)} lignes récupérées !")

        # KPIs
        st.markdown("---")
        st.markdown('<div class="section-header">📊 Résumé</div>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📋 Annonces",           f"{len(df_page)}")
        k2.metric("🏆 Meilleur dividende",  f"{df_page['Dividende_net'].max():,.0f} FCFA")
        k3.metric("💰 Dividende moyen",     f"{df_page['Dividende_net'].mean():,.0f} FCFA")
        rend = df_page['Rendement'].max() if 'Rendement' in df_page.columns else 0
        k4.metric("💹 Meilleur rendement",  f"{rend:.2f}%" if rend > 0 else "N/A")

        # Tableau + Graphes côte à côte
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="section-header">📋 Données</div>', unsafe_allow_html=True)
            st.dataframe(
                df_page[["Emetteur","Exercice","Dividende_net","Prix_action","Rendement","Date_paiement"]],
                use_container_width=True, height=350
            )
            st.download_button(
                "⬇️  Télécharger en CSV",
                data=df_page.to_csv(index=False).encode("utf-8"),
                file_name=f"brvm_page.csv", mime="text/csv"
            )

        with col2:
            st.markdown('<div class="section-header">🏆 Dividendes par émetteur</div>', unsafe_allow_html=True)
            fig_div = px.bar(
                df_page.sort_values("Dividende_net", ascending=False),
                x="Dividende_net", y="Emetteur", orientation="h",
                text="Dividende_net", color="Dividende_net",
                color_continuous_scale=["#BDD7EE","#1F4E79"],
                template="plotly_dark",
                labels={"Dividende_net":"Dividende (FCFA)","Emetteur":""}
            )
            fig_div.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                                  textfont=dict(color="white", size=10))
            fig_div.update_layout(height=350, coloraxis_showscale=False,
                                  plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                  font=dict(color="white"), margin=dict(l=10,r=70,t=10,b=10))
            st.plotly_chart(fig_div, use_container_width=True)

        # Graphe rendement en dessous si disponible
        if "Rendement" in df_page.columns and df_page["Rendement"].sum() > 0:
            st.markdown("---")
            st.markdown('<div class="section-header">💹 Rendement par émetteur</div>', unsafe_allow_html=True)
            fig_rend = px.bar(
                df_page[df_page["Rendement"]>0].sort_values("Rendement", ascending=False),
                x="Emetteur", y="Rendement",
                text="Rendement", color="Rendement",
                color_continuous_scale=["#D9F0D3","#1A7A36"],
                template="plotly_dark",
                labels={"Rendement":"Rendement (%)","Emetteur":""}
            )
            fig_rend.update_traces(texttemplate="%{text:.2f}%", textposition="outside",
                                   textfont=dict(color="white", size=10))
            fig_rend.update_layout(height=320, coloraxis_showscale=False,
                                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                   font=dict(color="white"), margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig_rend, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  🕷️ SCRAPER TOUTES LES PAGES
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🕷️ Scraper toutes les pages":
    st.markdown('<div class="section-header">Scraper toutes les pages</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        nb_pages = st.slider("Nombre de pages", min_value=1, max_value=40, value=40)
    with col2:
        st.metric("Durée estimée", f"~{nb_pages // 8} min")

    st.info("⚡ Scraping rapide — les prix sont chargés en une seule requête.")

    if st.button("▶️  Lancer le scraping complet"):
        progress_bar = st.progress(0, text="Démarrage...")
        status_text  = st.empty()
        frames       = []

        for p in range(nb_pages):
            status_text.text(f"⏳ Page {p + 1}/{nb_pages} en cours...")
            try:
                df_p = scraper_page(page=p, visible=visible, avec_prix=avec_prix)
                if not df_p.empty:
                    frames.append(df_p)
            except Exception as e:
                st.warning(f"Page {p} ignorée : {e}")
            progress_bar.progress((p + 1) / nb_pages, text=f"Page {p + 1}/{nb_pages}")

        if frames:
            df_final = pd.concat(frames, ignore_index=True)
            df_final = df_final.drop_duplicates(subset=["Emetteur", "Exercice"], keep="last")
            df_final.to_csv(CSV_FILE, index=False)
            st.cache_data.clear()
            st.session_state.df_complet = df_final
            status_text.success(f"✅ {len(df_final)} lignes collectées sur {nb_pages} pages !")
        else:
            st.error("❌ Aucune donnée collectée.")

    # ── Afficher les résultats complets ───────────────────────────────────────
    if "df_complet" in st.session_state and st.session_state.df_complet is not None:
        df_final = st.session_state.df_complet

        # KPIs
        st.markdown("---")
        st.markdown('<div class="section-header">📊 Résumé complet</div>', unsafe_allow_html=True)
        rend_max = df_final['Rendement'].max() if 'Rendement' in df_final.columns else 0
        rend_moy = df_final[df_final['Rendement']>0]['Rendement'].mean() if 'Rendement' in df_final.columns and df_final['Rendement'].sum()>0 else 0
        leader_div  = df_final.loc[df_final['Dividende_net'].idxmax(), 'Emetteur']
        leader_rend = df_final.loc[df_final['Rendement'].idxmax(), 'Emetteur'] if rend_max > 0 else "N/A"

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("📋 Total annonces",     f"{len(df_final):,}")
        k2.metric("🏢 Émetteurs",          f"{df_final['Emetteur'].nunique()}")
        k3.metric("🏆 Meilleur dividende", f"{df_final['Dividende_net'].max():,.0f} FCFA")
        k4.metric("💰 Dividende moyen",    f"{df_final['Dividende_net'].mean():,.0f} FCFA")
        k5.metric("💹 Meilleur rendement", f"{rend_max:.2f}%" if rend_max > 0 else "N/A")
        k6.metric("📊 Rendement moyen",    f"{rend_moy:.2f}%" if rend_moy > 0 else "N/A")

        st.markdown("---")
        l1, l2 = st.columns(2)
        l1.metric("🥇 Leader Dividende", leader_div)
        l2.metric("🥇 Leader Rendement", leader_rend)

        # Graphes + Tableau
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="section-header">🏆 Top 10 Dividendes</div>', unsafe_allow_html=True)
            top10_div = df_final.groupby("Emetteur")["Dividende_net"].max().sort_values(ascending=False).head(10).reset_index()
            fig1 = px.bar(top10_div, x="Dividende_net", y="Emetteur", orientation="h",
                          text="Dividende_net", color="Dividende_net",
                          color_continuous_scale=["#BDD7EE","#1F4E79"], template="plotly_dark",
                          labels={"Dividende_net":"Dividende (FCFA)","Emetteur":""})
            fig1.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                               textfont=dict(color="white", size=10))
            fig1.update_layout(height=380, coloraxis_showscale=False,
                               yaxis=dict(categoryorder="total ascending"),
                               plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="white"), margin=dict(l=10,r=70,t=10,b=10))
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">💹 Top 10 Rendement</div>', unsafe_allow_html=True)
            if rend_max > 0:
                top10_rend = df_final[df_final["Rendement"]>0].groupby("Emetteur")["Rendement"].max().sort_values(ascending=False).head(10).reset_index()
                fig2 = px.bar(top10_rend, x="Rendement", y="Emetteur", orientation="h",
                              text="Rendement", color="Rendement",
                              color_continuous_scale=["#D9F0D3","#1A7A36"], template="plotly_dark",
                              labels={"Rendement":"Rendement (%)","Emetteur":""})
                fig2.update_traces(texttemplate="%{text:.2f}%", textposition="outside",
                                   textfont=dict(color="white", size=10))
                fig2.update_layout(height=380, coloraxis_showscale=False,
                                   yaxis=dict(categoryorder="total ascending"),
                                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                   font=dict(color="white"), margin=dict(l=10,r=70,t=10,b=10))
                st.plotly_chart(fig2, use_container_width=True)

        # Évolution par année
        st.markdown("---")
        st.markdown('<div class="section-header">📈 Évolution par année</div>', unsafe_allow_html=True)
        if "Exercice" in df_final.columns:
            par_annee = df_final.groupby("Exercice")["Dividende_net"].sum().reset_index()
            fig3 = px.bar(par_annee, x="Exercice", y="Dividende_net", text="Dividende_net",
                          color="Dividende_net", color_continuous_scale=["#BDD7EE","#FFD700"],
                          template="plotly_dark",
                          labels={"Dividende_net":"Total (FCFA)","Exercice":"Année"})
            fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                               textfont=dict(color="white", size=9))
            fig3.update_layout(height=320, coloraxis_showscale=False,
                               xaxis=dict(tickmode="linear", dtick=1),
                               plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="white"), margin=dict(t=20,b=10))
            st.plotly_chart(fig3, use_container_width=True)

        # Tableau complet
        st.markdown("---")
        st.markdown('<div class="section-header">📋 Toutes les données</div>', unsafe_allow_html=True)
        st.dataframe(df_final, use_container_width=True, height=400)
        st.download_button(
            "⬇️  Télécharger en CSV",
            data=df_final.to_csv(index=False).encode("utf-8"),
            file_name="brvm_dividendes_complet.csv",
            mime="text/csv"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Charger les données pour les pages suivantes
# ══════════════════════════════════════════════════════════════════════════════
else:
    if df.empty:
        st.warning("⚠️  Aucune donnée disponible. Lance d'abord le scraping.")
        st.stop()

    # ══════════════════════════════════════════════════════════════════════════
    #  🏆 TOP 10 DIVIDENDES
    # ══════════════════════════════════════════════════════════════════════════
    if menu == "🏆 Top 10 Dividendes":
        st.markdown('<div class="section-header">Top 10 — Dividende net maximum</div>', unsafe_allow_html=True)

        top10 = (
            df.groupby("Emetteur")["Dividende_net"]
            .max().sort_values(ascending=False).head(10).reset_index()
        )
        top10.columns = ["Emetteur", "Dividende max (FCFA)"]
        top10.index  += 1

        c1, c2, c3 = st.columns(3)
        c1.metric("🥇 Leader", top10.iloc[0]["Emetteur"])
        c2.metric("💰 Dividende max", f"{top10.iloc[0]['Dividende max (FCFA)']:,.0f} FCFA")
        c3.metric("💵 Total dividendes versés", f"{df['Dividende_net'].sum():,.0f} FCFA")

        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("#### 📋 Classement")
            st.dataframe(top10, use_container_width=True)
        with col2:
            st.markdown("#### 📊 Graphique")
            fig = px.bar(
                top10, x="Dividende max (FCFA)", y="Emetteur",
                orientation="h",
                color="Dividende max (FCFA)",
                color_continuous_scale=["#BDD7EE", "#1F4E79"],
                template="plotly_white",
                text="Dividende max (FCFA)"
            )
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig.update_layout(yaxis={"categoryorder": "total ascending"},
                              coloraxis_showscale=False, height=420)
            st.plotly_chart(fig, use_container_width=True)

        if "Exercice" in df.columns:
            st.markdown("---")
            st.markdown("#### 📈 Évolution dans le temps")
            top10_noms = top10["Emetteur"].tolist()
            df_evol = (
                df[df["Emetteur"].isin(top10_noms)]
                .groupby(["Exercice", "Emetteur"])["Dividende_net"]
                .max().reset_index()
            )
            # Palette de couleurs vives
            couleurs = [
                "#1F4E79","#FFD700","#2E75B6","#FF6B35",
                "#00B4D8","#06D6A0","#EF476F","#FFC43D",
                "#8338EC","#FB5607"
            ]
            fig3 = px.bar(
                df_evol,
                x="Exercice", y="Dividende_net",
                color="Emetteur",
                barmode="group",
                text="Dividende_net",
                color_discrete_sequence=couleurs,
                template="plotly_dark",
                labels={"Dividende_net": "Dividende (FCFA)", "Exercice": "Année"},
            )
            fig3.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
                textfont_size=10,
            )
            fig3.update_layout(
                height=450,
                bargap=0.15,
                bargroupgap=0.05,
                xaxis=dict(tickmode="linear", dtick=1, title="Année"),
                yaxis=dict(title="Dividende net (FCFA)"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
            )
            st.plotly_chart(fig3, use_container_width=True)


    # ══════════════════════════════════════════════════════════════════════════
    #  💹 TOP 10 RENDEMENT
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "💹 Top 10 Rendement":
        st.markdown('<div class="section-header">Top 10 — Rendement Dividende (%)</div>', unsafe_allow_html=True)

        if "Prix_action" not in df.columns or df["Prix_action"].sum() == 0:
            st.warning("⚠️  Prix des actions non disponibles. Relance le scraping avec 'Récupérer les prix' activé.")
            st.stop()

        df["Rendement"] = df.apply(
            lambda r: round(r["Dividende_net"] / r["Prix_action"] * 100, 2)
            if r["Prix_action"] > 0 else 0.0, axis=1
        )
        top10_r = (
            df.groupby("Emetteur")["Rendement"]
            .max().sort_values(ascending=False).head(10).reset_index()
        )
        top10_r.columns = ["Emetteur", "Rendement max (%)"]
        top10_r.index  += 1

        c1, c2, c3 = st.columns(3)
        c1.metric("🥇 Meilleur rendement", top10_r.iloc[0]["Emetteur"])
        c2.metric("💹 Rendement max", f"{top10_r.iloc[0]['Rendement max (%)']:.2f}%")
        c3.metric("📊 Rendement moyen Top10", f"{top10_r['Rendement max (%)'].mean():.2f}%")

        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("#### 📋 Classement")
            st.dataframe(top10_r, use_container_width=True)
        with col2:
            st.markdown("#### 📊 Graphique")
            fig = px.bar(
                top10_r, x="Rendement max (%)", y="Emetteur",
                orientation="h",
                color="Rendement max (%)",
                color_continuous_scale=["#D9F0D3", "#1A7A36"],
                template="plotly_white",
                text="Rendement max (%)"
            )
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig.update_layout(yaxis={"categoryorder": "total ascending"},
                              coloraxis_showscale=False, height=420)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🔍 Dividende net vs Rendement")

        df_scatter = df[df["Rendement"] > 0].copy()
        df_scatter = df_scatter.sort_values("Rendement", ascending=False).head(15)

        couleurs = [
            "#FFD700","#1F4E79","#FF6B35","#06D6A0","#EF476F",
            "#00B4D8","#8338EC","#FB5607","#2E75B6","#FFC43D",
            "#SITAB","#3A86FF","#FF006E","#8AC926","#FFBE0B"
        ]
        couleurs = [c for c in couleurs if not c.startswith("#S")]

        fig4 = px.bar(
            df_scatter,
            x="Rendement", y="Emetteur",
            orientation="h",
            color="Emetteur",
            text="Rendement",
            color_discrete_sequence=couleurs,
            template="plotly_dark",
            labels={"Rendement": "Rendement (%)", "Emetteur": ""},
            title="Rendement par action (%)"
        )
        fig4.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside",
            textfont=dict(size=12, color="white"),
        )
        fig4.update_layout(
            height=500,
            showlegend=False,
            yaxis=dict(categoryorder="total ascending"),
            xaxis=dict(title="Rendement (%)"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white", size=12),
            title_font=dict(size=16, color="#FFD700"),
            margin=dict(l=10, r=80, t=50, b=10),
        )
        st.plotly_chart(fig4, use_container_width=True)


    # ══════════════════════════════════════════════════════════════════════════
    #  📋 DONNÉES COMPLÈTES
    # ══════════════════════════════════════════════════════════════════════════
    elif menu == "📋 Données complètes":
        st.markdown('<div class="section-header">Toutes les données</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            emetteurs = ["Tous"] + sorted(df["Emetteur"].dropna().unique().tolist())
            filtre_emetteur = st.selectbox("Filtrer par émetteur", emetteurs)
        with col2:
            if "Exercice" in df.columns:
                annees = ["Toutes"] + sorted(df["Exercice"].dropna().unique().tolist(), reverse=True)
                filtre_annee = st.selectbox("Filtrer par exercice", annees)
            else:
                filtre_annee = "Toutes"
        with col3:
            min_div = st.number_input("Dividende min (FCFA)", min_value=0, value=0, step=100)

        df_filtre = df.copy()
        if filtre_emetteur != "Tous":
            df_filtre = df_filtre[df_filtre["Emetteur"] == filtre_emetteur]
        if filtre_annee != "Toutes" and "Exercice" in df.columns:
            df_filtre = df_filtre[df_filtre["Exercice"] == filtre_annee]
        df_filtre = df_filtre[df_filtre["Dividende_net"] >= min_div]

        st.metric("Résultats", f"{len(df_filtre):,} lignes")
        st.dataframe(df_filtre, use_container_width=True, height=300)

        st.download_button(
            "⬇️  Télécharger les données filtrées (CSV)",
            data=df_filtre.to_csv(index=False).encode("utf-8"),
            file_name="brvm_filtré.csv",
            mime="text/csv"
        )

        # ── Graphe historique si un émetteur est sélectionné ──────────────────
        if filtre_emetteur != "Tous" and "Exercice" in df_filtre.columns and len(df_filtre) > 0:
            st.markdown("---")
            st.markdown(f"#### 📈 Historique des dividendes — {filtre_emetteur}")

            df_hist = df_filtre.sort_values("Exercice")

            col1, col2 = st.columns(2)

            with col1:
                # Graphe dividende par exercice
                fig_hist = px.bar(
                    df_hist,
                    x="Exercice", y="Dividende_net",
                    text="Dividende_net",
                    color="Dividende_net",
                    color_continuous_scale=["#BDD7EE", "#1F4E79"],
                    template="plotly_dark",
                    labels={"Dividende_net": "Dividende net (FCFA)", "Exercice": "Année"},
                    title=f"Dividende net par année"
                )
                fig_hist.update_traces(
                    texttemplate="%{text:,.2f} FCFA",
                    textposition="outside",
                    textfont=dict(size=11, color="white"),
                )
                fig_hist.update_layout(
                    height=380,
                    coloraxis_showscale=False,
                    xaxis=dict(tickmode="linear", dtick=1),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    title_font=dict(size=14, color="#FFD700"),
                    margin=dict(t=50, b=10),
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            with col2:
                # Graphe rendement par exercice (si disponible)
                if "Rendement" in df_hist.columns and df_hist["Rendement"].sum() > 0:
                    fig_rend = px.bar(
                        df_hist,
                        x="Exercice", y="Rendement",
                        text="Rendement",
                        color="Rendement",
                        color_continuous_scale=["#D9F0D3", "#1A7A36"],
                        template="plotly_dark",
                        labels={"Rendement": "Rendement (%)", "Exercice": "Année"},
                        title="Rendement dividende par année (%)"
                    )
                    fig_rend.update_traces(
                        texttemplate="%{text:.2f}%",
                        textposition="outside",
                        textfont=dict(size=11, color="white"),
                    )
                    fig_rend.update_layout(
                        height=380,
                        coloraxis_showscale=False,
                        xaxis=dict(tickmode="linear", dtick=1),
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="white"),
                        title_font=dict(size=14, color="#FFD700"),
                        margin=dict(t=50, b=10),
                    )
                    st.plotly_chart(fig_rend, use_container_width=True)
                else:
                    # Métriques résumées
                    st.markdown("#### 📊 Résumé")
                    st.metric("💰 Dividende total versé",
                              f"{df_hist['Dividende_net'].sum():,.2f} FCFA")
                    st.metric("📈 Dividende moyen",
                              f"{df_hist['Dividende_net'].mean():,.2f} FCFA")
                    st.metric("🏆 Meilleure année",
                              str(df_hist.loc[df_hist['Dividende_net'].idxmax(), 'Exercice']))
                    st.metric("📉 Moins bonne année",
                              str(df_hist.loc[df_hist['Dividende_net'].idxmin(), 'Exercice']))