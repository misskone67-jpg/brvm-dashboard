"""
app.py — BRVM : Analyses des Titres et leur Dividende
======================================================
Étape 1 : Top 10 titres ayant payé le maximum de dividende
Étape 2 : Étude du coût des actions qui paient des dividendes

Lancement : streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BRVM — Analyses des Titres et Dividendes",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

CSV_FILE = "dividendes.csv"

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2rem; font-weight: 800; color: #1F4E79;
        border-bottom: 3px solid #FFD700; padding-bottom: 10px; margin-bottom: 5px;
    }
    .subtitle { font-size: 1rem; color: #888; margin-bottom: 20px; }
    .etape-header {
        font-size: 1.4rem; font-weight: 800; color: white;
        background: linear-gradient(90deg, #1F4E79, #2E75B6);
        padding: 12px 20px; border-radius: 8px; margin: 25px 0 15px 0;
    }
    .section-header {
        font-size: 1.1rem; font-weight: 700; color: #1F4E79;
        padding-left: 10px; border-left: 4px solid #FFD700; margin: 15px 0 10px 0;
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1F4E79, #2E75B6);
        border-radius: 10px; padding: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    div[data-testid="metric-container"] label { color: #BDD7EE !important; font-size: 0.82rem; }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #FFD700 !important; font-size: 1.3rem; font-weight: 700;
    }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
        color: #90EE90 !important; font-size: 0.85rem;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1F4E79 0%, #2E75B6 100%);
    }
    section[data-testid="stSidebar"] * { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ── Chargement données ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def charger_donnees():
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame()
        df["Dividende_net"] = pd.to_numeric(df["Dividende_net"], errors="coerce").fillna(0)
        if "Prix_action" in df.columns:
            df["Prix_action"] = pd.to_numeric(df["Prix_action"], errors="coerce").fillna(0)
        if "Rendement" in df.columns:
            df["Rendement"] = pd.to_numeric(df["Rendement"], errors="coerce").fillna(0)
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


# ── Fonction principale d'affichage des 2 étapes ──────────────────────────────
def afficher_analyses(df):
    if df.empty:
        st.info("💡 Aucune donnée disponible.")
        return

    # Filtre années
    if "Exercice" in df.columns:
        annees_dispo = ["Toutes"] + sorted([int(x) for x in df["Exercice"].dropna().unique().tolist()], reverse=True)
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            annee_select = st.selectbox("📅 Filtrer par année", annees_dispo)
        if annee_select != "Toutes":
            df = df[df["Exercice"] == annee_select]

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    #  ÉTAPE 1
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="etape-header">📊 Étape 1 — Les 10 Titres ayant payé le Maximum de Dividende</div>', unsafe_allow_html=True)

    top10 = (
        df.groupby("Emetteur")["Dividende_net"]
        .sum().sort_values(ascending=False).head(10).reset_index()
    )
    top10.columns = ["Emetteur", "Dividende cumulé (FCFA)"]

    best_div_nom = top10.iloc[0]["Emetteur"] if not top10.empty else "N/A"
    best_div_val = top10.iloc[0]["Dividende cumulé (FCFA)"] if not top10.empty else 0
    rend_max_val = df["Rendement"].max() if "Rendement" in df.columns else 0
    rend_max_nom = df.loc[df["Rendement"].idxmax(), "Emetteur"] if rend_max_val > 0 else "N/A"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📋 Total annonces",     f"{len(df):,}")
    k2.metric("🏢 Émetteurs",          f"{df['Emetteur'].nunique()}")
    k3.metric("🏆 Meilleur dividende", f"{best_div_val:,.0f} FCFA", delta=best_div_nom)
    k4.metric("💹 Meilleur rendement", f"{rend_max_val:.2f}%", delta=rend_max_nom if rend_max_val > 0 else "N/A")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">🏆 Top 10 — Dividende cumulé</div>', unsafe_allow_html=True)
        fig1 = px.bar(
            top10, x="Dividende cumulé (FCFA)", y="Emetteur",
            orientation="h", text="Dividende cumulé (FCFA)",
            color="Dividende cumulé (FCFA)",
            color_continuous_scale=["#BDD7EE","#1F4E79"],
            template="plotly_dark",
            labels={"Dividende cumulé (FCFA)":"Dividende cumulé (FCFA)","Emetteur":""}
        )
        fig1.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                           textfont=dict(color="white", size=10))
        fig1.update_layout(height=400, coloraxis_showscale=False,
                           yaxis=dict(categoryorder="total ascending"),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           font=dict(color="white"), margin=dict(l=10,r=80,t=10,b=10))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">💹 Top 10 — Meilleur rendement</div>', unsafe_allow_html=True)
        if "Rendement" in df.columns and df["Rendement"].sum() > 0:
            top10_rend = (
                df[df["Rendement"]>0].groupby("Emetteur")["Rendement"]
                .max().sort_values(ascending=False).head(10).reset_index()
            )
            fig2 = px.bar(
                top10_rend, x="Rendement", y="Emetteur",
                orientation="h", text="Rendement",
                color="Rendement",
                color_continuous_scale=["#D9F0D3","#1A7A36"],
                template="plotly_dark",
                labels={"Rendement":"Rendement max (%)","Emetteur":""}
            )
            fig2.update_traces(texttemplate="%{text:.2f}%", textposition="outside",
                               textfont=dict(color="white", size=10))
            fig2.update_layout(height=400, coloraxis_showscale=False,
                               yaxis=dict(categoryorder="total ascending"),
                               plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                               font=dict(color="white"), margin=dict(l=10,r=80,t=10,b=10))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Aucune donnée de rendement disponible.")

    st.markdown('<div class="section-header">📋 Classement Top 10 Dividendes</div>', unsafe_allow_html=True)
    top10_display = top10.copy()
    top10_display.index += 1
    st.dataframe(top10_display, use_container_width=True, height=380)

    # ══════════════════════════════════════════════════════════════════════════
    #  ÉTAPE 2
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="etape-header">💵 Étape 2 — Étude du Coût des Actions qui paient des Dividendes</div>', unsafe_allow_html=True)

    df_prix = df[df["Prix_action"] > 0].copy() if "Prix_action" in df.columns else pd.DataFrame()

    if df_prix.empty:
        st.warning("⚠️ Aucune donnée de prix disponible.")
        return

    synthese = (
        df_prix.groupby("Emetteur")
        .agg(
            Prix_action     = ("Prix_action",  "mean"),
            Dividende_moyen = ("Dividende_net", "mean"),
            Dividende_max   = ("Dividende_net", "max"),
            Rendement_moyen = ("Rendement",     "mean"),
            Rendement_max   = ("Rendement",     "max"),
            Nb_versements   = ("Dividende_net", "count"),
        )
        .reset_index()
        .sort_values("Prix_action", ascending=False)
        .reset_index(drop=True)
    )

    plus_chere_nom  = synthese.iloc[0]["Emetteur"]
    plus_chere_val  = synthese.iloc[0]["Prix_action"]
    moins_chere_nom = synthese.iloc[-1]["Emetteur"]
    moins_chere_val = synthese.iloc[-1]["Prix_action"]
    prix_moyen_val  = synthese["Prix_action"].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📊 Nb actions analysées",  f"{len(synthese)}")
    k2.metric("💎 Action la plus chère",  f"{plus_chere_val:,.0f} FCFA", delta=plus_chere_nom)
    k3.metric("💡 Action la moins chère", f"{moins_chere_val:,.0f} FCFA", delta=moins_chere_nom)
    k4.metric("💰 Prix moyen par action", f"{prix_moyen_val:,.0f} FCFA")

    st.markdown("---")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-header">💎 Prix des actions (FCFA)</div>', unsafe_allow_html=True)
        fig3 = px.bar(
            synthese.sort_values("Prix_action", ascending=False),
            x="Prix_action", y="Emetteur",
            orientation="h", text="Prix_action",
            color="Prix_action",
            color_continuous_scale=["#FFE5CC","#FF6B35"],
            template="plotly_dark",
            labels={"Prix_action":"Prix action (FCFA)","Emetteur":""},
            title="Prix des actions qui paient des dividendes"
        )
        fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                           textfont=dict(color="white", size=9))
        fig3.update_layout(height=500, coloraxis_showscale=False,
                           yaxis=dict(categoryorder="total ascending"),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           font=dict(color="white"), title_font=dict(color="#FFD700"),
                           margin=dict(l=10,r=80,t=50,b=10))
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown('<div class="section-header">📊 Prix action vs Dividende versé</div>', unsafe_allow_html=True)
        top15 = synthese.sort_values("Prix_action", ascending=False).head(15)
        fig4 = px.bar(
            top15.melt(id_vars="Emetteur",
                       value_vars=["Prix_action", "Dividende_moyen"],
                       var_name="Indicateur", value_name="Valeur (FCFA)"),
            x="Emetteur", y="Valeur (FCFA)",
            color="Indicateur", barmode="group",
            text="Valeur (FCFA)",
            color_discrete_map={"Prix_action":"#2E75B6","Dividende_moyen":"#FFD700"},
            template="plotly_dark",
            labels={"Emetteur":"", "Valeur (FCFA)":"Valeur (FCFA)"},
            title="Prix de l'action vs Dividende moyen versé"
        )
        fig4.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                           textfont=dict(size=9, color="white"))
        fig4.update_layout(height=500, xaxis=dict(tickangle=-35),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           font=dict(color="white"), title_font=dict(color="#FFD700"),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                           margin=dict(t=60, b=80))
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown('<div class="section-header">📋 Tableau comparatif — Prix | Dividende | Rendement</div>', unsafe_allow_html=True)
    synthese_aff = synthese.copy().round(2)
    synthese_aff.columns = [
        "Émetteur","Prix action (FCFA)","Dividende moyen (FCFA)",
        "Dividende max (FCFA)","Rendement moyen (%)","Rendement max (%)","Nb versements"
    ]
    synthese_aff.index += 1
    st.dataframe(synthese_aff, use_container_width=True, height=400)

    st.download_button(
        "⬇️ Télécharger les données (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="brvm_analyse_dividendes.csv",
        mime="text/csv"
    )


# ── En-tête ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📈 BRVM — Analyses des Titres et Dividendes</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Bourse Régionale des Valeurs Mobilières — 8 pays UEMOA</div>', unsafe_allow_html=True)

if os.path.exists(CSV_FILE):
    ts = os.path.getmtime(CSV_FILE)
    st.caption(f"🔄 Dernière mise à jour : **{datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M')}**")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗂️ Navigation")
    menu = st.selectbox("", [
        "📊 Analyse",
        "📋 Données complètes",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**BRVM** — 8 pays UEMOA")
    st.markdown("---")
    st.markdown("### 👥 Auteurs")
    st.markdown("**KONE TCHITCHEMEGO**")
    st.markdown("**MELIANE SEFORA LASME**")
    st.caption("© 2025 Dashboard BRVM")

df = charger_donnees()

if df.empty:
    st.warning("⚠️ Aucune donnée disponible. Placez le fichier `dividendes.csv` dans le dossier BRVM.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  📊 ANALYSE
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📊 Analyse":
    afficher_analyses(df)

# ══════════════════════════════════════════════════════════════════════════════
#  📋 DONNÉES COMPLÈTES
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📋 Données complètes":
    st.markdown('<div class="etape-header">📋 Données complètes</div>', unsafe_allow_html=True)

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
    if filtre_annee != "Toutes":
        df_filtre = df_filtre[df_filtre["Exercice"] == filtre_annee]
    df_filtre = df_filtre[df_filtre["Dividende_net"] >= min_div]

    st.metric("Résultats", f"{len(df_filtre):,} lignes")
    st.dataframe(df_filtre, use_container_width=True, height=350)

    if filtre_emetteur != "Tous" and len(df_filtre) > 0 and "Exercice" in df_filtre.columns:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div class="section-header">📈 Historique — {filtre_emetteur}</div>', unsafe_allow_html=True)
            fig = px.bar(
                df_filtre.sort_values("Exercice"), x="Exercice", y="Dividende_net",
                text="Dividende_net", color="Dividende_net",
                color_continuous_scale=["#BDD7EE","#1F4E79"], template="plotly_dark",
                labels={"Dividende_net":"Dividende (FCFA)","Exercice":"Année"}
            )
            fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside",
                              textfont=dict(color="white"))
            fig.update_layout(height=350, coloraxis_showscale=False,
                              xaxis=dict(tickmode="linear", dtick=1),
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.markdown('<div class="section-header">📊 Résumé</div>', unsafe_allow_html=True)
            st.metric("💰 Total versé", f"{df_filtre['Dividende_net'].sum():,.0f} FCFA")
            st.metric("📈 Dividende moyen", f"{df_filtre['Dividende_net'].mean():,.0f} FCFA")
            if len(df_filtre) > 0:
                best_idx = df_filtre['Dividende_net'].idxmax()
                st.metric("🏆 Meilleure année", str(df_filtre.loc[best_idx, 'Exercice']))

    st.download_button(
        "⬇️ Télécharger",
        data=df_filtre.to_csv(index=False).encode("utf-8"),
        file_name="brvm_filtré.csv", mime="text/csv"
    )