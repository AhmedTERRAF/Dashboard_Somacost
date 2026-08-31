# -*- coding: utf-8 -*-
"""
app.py — SAP SD Intelligence · Sales & Operations Analytics
==============================================================
Dashboard Streamlit sur les données historiques SAP SD (module Sales &
Distribution). Thème sombre, navigation latérale par section, cartes KPI,
graphiques Plotly.

Lancement :  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import data_loader as dl

# --------------------------------------------------------------------------
# CONFIGURATION GÉNÉRALE
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="SAP SD Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

ACCENT = "#7EC8F5"       # bleu clair des barres / accents
ACCENT_STRONG = "#4A9EDA"
BG_DARK = "#0B0F19"
CARD_BG = "#131A2A"
CARD_BORDER = "#1F2A3D"
TEXT_GREY = "#8B96A8"
RED_DOT = "#E5484D"

PLOTLY_TEMPLATE = "plotly_dark"

PAGES = [
    "0 · Qualité des données",
    "1 · Vue d'ensemble",
    "2 · Performance commerciale (CA)",
    "3 · Clients",
    "4 · Produits / Articles",
    "5 · Logistique",
    "6 · Financier — Encours & DSO",
    "7 · Chaîne documentaire",
]

# --------------------------------------------------------------------------
# STYLE (CSS) — reproduit l'esthétique sombre / cartes / navigation
# --------------------------------------------------------------------------

st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {BG_DARK};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {BG_DARK};
            border-right: 1px solid {CARD_BORDER};
        }}
        div[data-testid="stMetric"] {{
            background-color: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 10px;
            padding: 14px 16px 10px 16px;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {TEXT_GREY} !important;
            font-size: 0.72rem !important;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}
        div[data-testid="stMetricValue"] {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }}
        .kpi-card {{
            background-color: {CARD_BG};
            border: 1px solid {CARD_BORDER};
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 14px;
        }}
        .kpi-label {{
            color: {TEXT_GREY};
            font-size: 0.72rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        .kpi-value {{
            color: #FFFFFF;
            font-size: 1.9rem;
            font-weight: 700;
            line-height: 1.1;
        }}
        .kpi-sub {{
            color: {TEXT_GREY};
            font-size: 0.78rem;
            margin-top: 4px;
        }}
        .section-title-bar {{
            border-left: 4px solid {ACCENT_STRONG};
            padding-left: 10px;
            margin: 22px 0 4px 0;
            font-size: 1.05rem;
            font-weight: 700;
            color: #FFFFFF;
        }}
        .section-subtitle {{
            color: {TEXT_GREY};
            font-size: 0.85rem;
            margin-bottom: 12px;
        }}
        .page-kicker {{
            color: {ACCENT_STRONG};
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .page-title {{
            color: #FFFFFF;
            font-size: 2.1rem;
            font-weight: 800;
            margin-top: 2px;
        }}
        .page-desc {{
            color: {TEXT_GREY};
            margin-bottom: 18px;
        }}
        .app-logo-title {{
            font-weight: 800;
            font-size: 1.05rem;
            color: #FFFFFF;
            line-height: 1.15;
        }}
        .app-logo-sub {{
            font-size: 0.78rem;
            color: {TEXT_GREY};
        }}
        .nav-caption {{
            color: {TEXT_GREY};
            font-size: 0.72rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin: 14px 0 6px 0;
        }}
        .info-banner {{
            background-color: rgba(74, 158, 218, 0.10);
            border: 1px solid rgba(74, 158, 218, 0.35);
            color: #CFE4F5;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 0.85rem;
            margin-top: 10px;
        }}
        .warn-banner {{
            background-color: rgba(229, 72, 77, 0.08);
            border: 1px solid rgba(229, 72, 77, 0.35);
            color: #F3C9CA;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 0.85rem;
            margin-top: 10px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


def section_title(title: str, subtitle: str = ""):
    st.markdown(f'<div class="section-title-bar">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def page_header(kicker: str, title: str, desc: str):
    st.markdown(f'<div class="page-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-desc">{desc}</div>', unsafe_allow_html=True)
    st.markdown(f'<hr style="border-color:{CARD_BORDER}; margin-bottom:20px;">', unsafe_allow_html=True)


def kpi_card(col, label: str, value: str, sub: str = ""):
    with col:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def fmt_mad(x) -> str:
    if x is None or pd.isna(x):
        return "N/D"
    return f"{x:,.0f} MAD".replace(",", " ")


def fmt_num(x) -> str:
    if x is None or pd.isna(x):
        return "N/D"
    return f"{x:,.0f}".replace(",", " ")


def fmt_pct(x, decimals=1) -> str:
    if x is None or pd.isna(x):
        return "N/D"
    return f"{x:.{decimals}f} %"


def style_fig(fig, height=380):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#D6DEEA",
        margin=dict(l=10, r=10, t=30, b=10),
        height=height,
    )
    return fig


# --------------------------------------------------------------------------
# CHARGEMENT DES DONNÉES (mis en cache)
# --------------------------------------------------------------------------

@st.cache_data(show_spinner="Chargement des données SAP…")
def load_model():
    return dl.build_model()


model = load_model()

# --------------------------------------------------------------------------
# SIDEBAR — logo, navigation, filtres globaux
# --------------------------------------------------------------------------

with st.sidebar:
    logo_col, text_col = st.columns([1, 4])
    with logo_col:
        st.markdown(
            f"""<div style="width:38px;height:38px;border-radius:9px;
            background:linear-gradient(135deg,{ACCENT_STRONG},{ACCENT});
            display:flex;align-items:center;justify-content:center;
            font-size:1.1rem;">📊</div>""",
            unsafe_allow_html=True,
        )
    with text_col:
        st.markdown(
            '<div class="app-logo-title">SAP SD<br/>Intelligence</div>'
            '<div class="app-logo-sub">Sales &amp; Operations Analytics</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="nav-caption">Navigation</div>', unsafe_allow_html=True)
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div class="nav-caption">Filtres globaux</div>', unsafe_allow_html=True)

    # Période : bornée par les dates réellement présentes dans les données
    all_dates = pd.concat([
        model.invoices_items.get("FKDAT", pd.Series(dtype="datetime64[ns]")),
        model.orders.get("ERDAT", pd.Series(dtype="datetime64[ns]")),
    ]).dropna()
    if not all_dates.empty:
        min_d, max_d = all_dates.min().date(), all_dates.max().date()
    else:
        min_d, max_d = None, None

    if min_d and max_d:
        period = st.date_input("Période", value=(min_d, max_d), min_value=min_d, max_value=max_d)
        if isinstance(period, tuple) and len(period) == 2:
            start_date, end_date = period
        else:
            start_date, end_date = min_d, max_d
    else:
        start_date, end_date = None, None
        st.caption("Aucune date exploitable dans les données chargées.")

# --------------------------------------------------------------------------
# PAGE 0 · QUALITÉ DES DONNÉES
# --------------------------------------------------------------------------

if page == PAGES[0]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Qualité des données",
        "Contrôles de complétude et de cohérence sur les tables sources.",
    )

    dq = model.data_quality
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Tables chargées", f"{7 - len(dq['missing_tables'])}/7")
    kpi_card(c2, "Commandes (VBAK)", fmt_num(dq.get("n_orders")))
    kpi_card(c3, "Lignes de facture (VBRP)", fmt_num(dq.get("n_invoice_items")))
    kpi_card(c4, "Livraisons (LIKP)", fmt_num(dq.get("n_deliveries")))

    if dq["missing_tables"]:
        st.markdown(
            f'<div class="warn-banner">⚠️ Tables introuvables dans le dossier data/ : '
            f'{", ".join(dq["missing_tables"])}.</div>',
            unsafe_allow_html=True,
        )

    section_title("Répartition des documents de facturation")
    fig = px.pie(
        names=["Chiffre d'affaires (F2)", "Avoirs", "Autres (ex. acomptes)"],
        values=[dq["n_invoices_ca"], dq["n_invoices_avoir"], dq["n_invoices_autre"]],
        hole=0.55,
        color_discrete_sequence=[ACCENT, "#E5484D", "#5B667A"],
    )
    st.plotly_chart(style_fig(fig, 320), use_container_width=True)

    section_title("Anomalies détectées")
    st.markdown(
        f"""
        <div class="info-banner">
        • Bureau des ventes (VKBUR) : {"vide sur l'ensemble de l'extrait — l'analyse par bureau des ventes n'est pas exploitable." if dq.get("vkbur_empty") else "renseigné."}<br/>
        • Livraisons sans date exploitable (planifiée ou réelle manquante) : {fmt_num(dq.get("n_deliveries_missing_dates"))}<br/>
        • Écarts de livraison aberrants (&gt; {dl.ECART_OUTLIER_THRESHOLD} jours, exclus des statistiques) : {fmt_num(dq.get("n_deliveries_outliers"))}<br/>
        • Lignes de facture sans en-tête correspondant : {fmt_num(dq.get("n_items_unmatched_header"))}
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------
# PAGE 1 · VUE D'ENSEMBLE
# --------------------------------------------------------------------------

elif page == PAGES[1]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Vue d'ensemble",
        "Synthèse exécutive de la performance commerciale et opérationnelle.",
    )

    k = dl.kpi_overview(model, start_date, end_date)
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    kpi_card(r1c1, "CA net total", fmt_mad(k["ca_net"]), "Chiffre d'affaires net")
    kpi_card(r1c2, "Commandes", fmt_num(k["n_commandes"]), "Nombre de commandes")
    kpi_card(r1c3, "Factures", fmt_num(k["n_factures"]), "Factures comptabilisées")
    kpi_card(r1c4, "Clients actifs", fmt_num(k["n_clients"]), "Clients avec CA positif")

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    kpi_card(r2c1, "Panier moyen", fmt_mad(k["panier_moyen"]), "CA net / factures")
    kpi_card(r2c2, "Taux de service", fmt_pct(k["taux_service"]), "Livraison à l'heure")
    kpi_card(r2c3, "Encours", "N/D", "BSID non disponible")
    kpi_card(r2c4, "DSO", "N/D", "BSID / BSAD non disponibles")

    section_title("Évolution journalière du CA net", "Chiffre d'affaires net facturé, par jour.")
    daily = dl.ca_daily(model, start_date, end_date)
    if not daily.empty:
        fig = px.bar(daily, x="Date", y="CA_net", labels={"CA_net": "CA net (MAD)"})
        fig.update_traces(marker_color=ACCENT)
        st.plotly_chart(style_fig(fig), use_container_width=True)
        with st.expander("Voir le détail par jour"):
            st.dataframe(daily, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune donnée de chiffre d'affaires sur la période sélectionnée.")

    col_a, col_b = st.columns(2)
    with col_a:
        section_title("CA net par organisation commerciale", "Répartition du chiffre d'affaires entre les VKORG.")
        vkorg = dl.ca_by_dimension(model, "VKORG", start_date, end_date)
        if not vkorg.empty:
            fig = px.pie(vkorg, names="VKORG", values="CA", hole=0.6,
                         color_discrete_sequence=[ACCENT_STRONG, ACCENT, "#B7DFFB"])
            fig.update_traces(textinfo="percent")
            st.plotly_chart(style_fig(fig, 340), use_container_width=True)
        else:
            st.info("Donnée VKORG non disponible.")
    with col_b:
        section_title("Commandes vs factures", "Comparaison des volumes documentaires.")
        cvf = dl.commandes_vs_factures(model, start_date, end_date)
        fig = px.bar(cvf, x="Type", y="Nombre", labels={"Nombre": "Nombre"})
        fig.update_traces(marker_color=ACCENT)
        st.plotly_chart(style_fig(fig, 340), use_container_width=True)

# --------------------------------------------------------------------------
# PAGE 2 · PERFORMANCE COMMERCIALE (CA)
# --------------------------------------------------------------------------

elif page == PAGES[2]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Performance commerciale",
        "Analyse de la formation du chiffre d'affaires et de sa répartition.",
    )

    items = dl.filter_period(model.invoices_items, "FKDAT", start_date, end_date)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    avoir_items = items[items["TYPE_FACTURE"] == "AVOIR"] if "TYPE_FACTURE" in items.columns else items.iloc[0:0]
    ca_brut = ca_items["NETWR"].sum() + avoir_items["NETWR"].sum().__abs__() if not avoir_items.empty else (ca_items["NETWR"].sum() if not ca_items.empty else 0)
    avoirs = avoir_items["NETWR"].sum().__abs__() if not avoir_items.empty else 0
    ca_net = ca_items["NETWR"].sum() if not ca_items.empty else 0
    taux_avoir = (avoirs / ca_brut * 100) if ca_brut else 0

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "CA brut", fmt_mad(ca_brut))
    kpi_card(c2, "Avoirs / retours", fmt_mad(avoirs))
    kpi_card(c3, "CA net", fmt_mad(ca_net))
    kpi_card(c4, "Taux d'avoirs", fmt_pct(taux_avoir))

    col_a, col_b = st.columns(2)
    with col_a:
        section_title("CA par organisation commerciale", "Classement des VKORG par chiffre d'affaires.")
        vkorg = dl.ca_by_dimension(model, "VKORG", start_date, end_date)
        if not vkorg.empty:
            fig = px.bar(vkorg, x="VKORG", y="CA", labels={"CA": "CA (MAD)"})
            fig.update_traces(marker_color=ACCENT)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Non disponible sur cet extrait.")
    with col_b:
        section_title("CA par canal de distribution", "Répartition du CA selon le VTWEG.")
        vtweg = dl.ca_by_dimension(model, "VTWEG", start_date, end_date)
        if not vtweg.empty:
            fig = px.bar(vtweg, x="VTWEG", y="CA", labels={"CA": "CA (MAD)"})
            fig.update_traces(marker_color=ACCENT)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Non disponible sur cet extrait.")

    section_title("Évolution journalière du CA net")
    daily = dl.ca_daily(model, start_date, end_date)
    if not daily.empty:
        fig = px.bar(daily, x="Date", y="CA_net", labels={"CA_net": "CA net (MAD)"})
        fig.update_traces(marker_color=ACCENT)
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.dataframe(daily, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------
# PAGE 3 · CLIENTS
# --------------------------------------------------------------------------

elif page == PAGES[3]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Clients",
        "Analyse du portefeuille client et de sa concentration.",
    )

    items = dl.filter_period(model.invoices_items, "FKDAT", start_date, end_date)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    n_clients_actifs = ca_items["KUNAG"].nunique() if "KUNAG" in ca_items.columns else 0
    ca_total = ca_items["NETWR"].sum() if not ca_items.empty else 0
    ca_moyen_client = (ca_total / n_clients_actifs) if n_clients_actifs else 0

    c1, c2, c3 = st.columns(3)
    kpi_card(c1, "Clients actifs", fmt_num(n_clients_actifs), "CA positif sur la période")
    kpi_card(c2, "Nouveaux clients", "N/D", "Nécessite un historique multi-mois")
    kpi_card(c3, "CA moyen / client", fmt_mad(ca_moyen_client))

    st.markdown(
        '<div class="info-banner">Les indicateurs de rétention et de clients dormants '
        'nécessitent un historique multi-mois.</div>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        section_title("Top 15 clients par CA", "Clients classés par contribution au chiffre d'affaires.")
        top15 = dl.top_clients(model, 15, start_date, end_date)
        if not top15.empty:
            fig = px.bar(top15.sort_values("CA"), x="CA", y="Client", orientation="h",
                         labels={"CA": "CA (MAD)"})
            fig.update_traces(marker_color=ACCENT)
            st.plotly_chart(style_fig(fig, 460), use_container_width=True)
        else:
            st.info("Nom de client non disponible (KNA1 manquant ou non joint).")
    with col_b:
        section_title("Concentration du portefeuille", "Courbe de Pareto — contribution cumulée au CA.")
        all_clients = dl.ca_by_dimension(model, "Client" if "Client" in items.columns else "KUNAG", start_date, end_date) \
            if "Client" in items.columns else pd.DataFrame()
        if all_clients.empty:
            g = ca_items.groupby("KUNAG")["NETWR"].sum().reset_index().rename(columns={"NETWR": "CA"}) \
                if "KUNAG" in ca_items.columns else pd.DataFrame(columns=["KUNAG", "CA"])
            pareto = dl.pareto_curve(g, "KUNAG", "CA")
        else:
            label_col = "Client" if "Client" in all_clients.columns else all_clients.columns[0]
            pareto = dl.pareto_curve(all_clients, label_col, "CA")
        if not pareto.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pareto["pct_rang"], y=pareto["pct_cumule"],
                                      mode="lines+markers", line=dict(color=ACCENT)))
            fig.add_hline(y=80, line_dash="dot", line_color=TEXT_GREY)
            fig.update_layout(xaxis_title="% des clients", yaxis_title="% CA cumulé")
            st.plotly_chart(style_fig(fig, 460), use_container_width=True)
        else:
            st.info("Non disponible sur cet extrait.")

# --------------------------------------------------------------------------
# PAGE 4 · PRODUITS / ARTICLES
# --------------------------------------------------------------------------

elif page == PAGES[4]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Produits / Articles",
        "Performance et concentration du catalogue produit.",
    )

    items = dl.filter_period(model.invoices_items, "FKDAT", start_date, end_date)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    n_articles_actifs = ca_items["ARKTX"].nunique() if "ARKTX" in ca_items.columns else 0
    n_mara = len(model.materials)
    n_sans_vente = max(n_mara - (ca_items["MATNR"].nunique() if "MATNR" in ca_items.columns else 0), 0) if n_mara else 0

    c1, c2 = st.columns(2)
    kpi_card(c1, "Articles actifs", fmt_num(n_articles_actifs), "≥ 1 vente sur la période")
    kpi_card(c2, "Références sans vente", fmt_num(n_sans_vente), "Présentes dans MARA")

    col_a, col_b = st.columns(2)
    with col_a:
        section_title("Top 10 articles par CA", "Articles générant le plus de chiffre d'affaires.")
        top10 = dl.top_articles(model, 10, start_date, end_date)
        if not top10.empty:
            fig = px.bar(top10.sort_values("CA"), x="CA", y="ARKTX", orientation="h",
                         labels={"CA": "CA (MAD)", "ARKTX": "Article"})
            fig.update_traces(marker_color=ACCENT)
            st.plotly_chart(style_fig(fig, 420), use_container_width=True)
        else:
            st.info("Non disponible sur cet extrait.")
    with col_b:
        section_title("CA par famille de produits", "Contribution des familles MATKL.")
        fam = dl.ca_by_family(model, start_date, end_date)
        if not fam.empty:
            fig = px.treemap(fam, path=["MATKL"], values="CA",
                              color_discrete_sequence=[ACCENT])
            st.plotly_chart(style_fig(fig, 420), use_container_width=True)
        else:
            st.info("Non disponible sur cet extrait.")

    section_title("Quantité vendue par article", "Top 10 des articles par quantité vendue.")
    if not top10.empty:
        fig = px.bar(top10.sort_values("FKIMG"), x="FKIMG", y="ARKTX", orientation="h",
                     labels={"FKIMG": "Quantité", "ARKTX": "Article"})
        fig.update_traces(marker_color=ACCENT)
        st.plotly_chart(style_fig(fig, 380), use_container_width=True)

    section_title("Concentration Pareto — articles", "Contribution cumulative des articles au CA.")
    all_articles = ca_items.groupby("ARKTX")["NETWR"].sum().reset_index().rename(columns={"NETWR": "CA"}) \
        if "ARKTX" in ca_items.columns else pd.DataFrame(columns=["ARKTX", "CA"])
    pareto = dl.pareto_curve(all_articles, "ARKTX", "CA")
    if not pareto.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=pareto["pct_rang"], y=pareto["pct_cumule"],
                                  mode="lines+markers", line=dict(color=ACCENT)))
        fig.add_hline(y=80, line_dash="dot", line_color=TEXT_GREY)
        fig.update_layout(xaxis_title="% des articles", yaxis_title="% CA cumulé")
        st.plotly_chart(style_fig(fig, 380), use_container_width=True)

    if n_mara:
        st.caption(f"ℹ️ MARA contient {n_mara} article(s) référencé(s). "
                   f"{max(n_articles_actifs - n_mara, 0)} article(s) vendu(s) ne figurent pas dans le référentiel fourni "
                   f"si ce nombre est positif.")

# --------------------------------------------------------------------------
# PAGE 5 · LOGISTIQUE
# --------------------------------------------------------------------------

elif page == PAGES[5]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Logistique",
        "Performance des livraisons, respect des délais et volumes expédiés.",
    )

    deliv = dl.filter_period(model.deliveries, "DATE_PLANIFIEE", start_date, end_date)
    ecarts = dl.ecart_livraison_series(model, start_date, end_date)
    taux_service = (ecarts <= 0).mean() * 100 if len(ecarts) else float("nan")
    poids_net_total = deliv["POIDS_NET"].sum() if "POIDS_NET" in deliv.columns else float("nan")

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Taux de service", fmt_pct(taux_service), "Livraison réelle ≤ prévue")
    kpi_card(c2, "Écart moyen", f"{ecarts.mean():.1f} j" if len(ecarts) else "N/D", "Écart de livraison")
    kpi_card(c3, "Écart médian", f"{ecarts.median():.1f} j" if len(ecarts) else "N/D", "Écart de livraison")
    kpi_card(c4, "P90", f"{ecarts.quantile(0.9):.1f} j" if len(ecarts) else "N/D", "90 % des livraisons")

    c5, c6 = st.columns(2)
    kpi_card(c5, "Poids net livré", f"{poids_net_total:,.0f} KG".replace(",", " ") if pd.notna(poids_net_total) else "N/D", "Poids total")
    kpi_card(c6, "Livraisons", fmt_num(len(deliv)), "Nombre de documents LIKP")

    if model.data_quality.get("vkbur_empty"):
        st.markdown(
            '<div class="warn-banner">⚠️ LIPS/VBUK ne sont pas disponibles : les indicateurs '
            'logistiques sont mesurés au niveau en-tête LIKP.</div>',
            unsafe_allow_html=True,
        )

    col_a, col_b = st.columns(2)
    with col_a:
        section_title("Poids net par point d'expédition", "Top 15 des VSTEL selon le poids expédié.")
        pw = dl.poids_par_point_expedition(model, 15, start_date, end_date)
        if not pw.empty:
            fig = px.bar(pw, x="VSTEL", y="POIDS_NET", labels={"POIDS_NET": "Poids net (KG)", "VSTEL": "Point d'expédition"})
            fig.update_traces(marker_color=ACCENT)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Non disponible sur cet extrait.")
    with col_b:
        section_title("Distribution des écarts de livraison", "Nombre de jours entre date réelle et date prévue.")
        if len(ecarts):
            fig = px.histogram(ecarts, nbins=30, labels={"value": "Écart (jours)"})
            fig.update_traces(marker_color=ACCENT)
            fig.update_layout(showlegend=False, xaxis_title="Écart (jours)", yaxis_title="count")
            st.plotly_chart(style_fig(fig), use_container_width=True)
        else:
            st.info("Non disponible sur cet extrait.")

    section_title("Livraisons par type", "Répartition des documents selon LFART.")
    types = dl.livraisons_par_type(model, start_date, end_date)
    if not types.empty:
        st.dataframe(types, use_container_width=True, hide_index=True)
    else:
        st.info("Non disponible sur cet extrait.")

# --------------------------------------------------------------------------
# PAGE 6 · FINANCIER — ENCOURS & DSO
# --------------------------------------------------------------------------

elif page == PAGES[6]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Financier — Encours & DSO",
        "Analyse du risque client et du délai moyen de recouvrement.",
    )
    st.markdown(
        '<div class="warn-banner">⚠️ Ces indicateurs nécessitent les tables comptables '
        'BSID (créances ouvertes) et BSAD (créances soldées), non disponibles dans cet extrait. '
        'Connectez ces tables pour activer cette page.</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    kpi_card(c1, "Encours total", "N/D", "BSID non disponible")
    kpi_card(c2, "DSO", "N/D", "BSID / BSAD non disponibles")
    kpi_card(c3, "Créances échues", "N/D", "BSID non disponible")

# --------------------------------------------------------------------------
# PAGE 7 · CHAÎNE DOCUMENTAIRE
# --------------------------------------------------------------------------

elif page == PAGES[7]:
    page_header(
        "SAP SD · BUSINESS INTELLIGENCE",
        "Chaîne documentaire",
        "Suivi du cycle Order-to-Cash : commande → livraison → facture.",
    )

    flow = dl.doc_flow_completeness(model)
    c1, c2, c3 = st.columns(3)
    kpi_card(c1, "Commandes", fmt_num(flow["orders"]))
    kpi_card(c2, "… avec livraison", fmt_num(flow["with_delivery"]) if flow["with_delivery"] is not None else "N/D")
    kpi_card(c3, "… avec facture", fmt_num(flow["with_invoice"]) if flow["with_invoice"] is not None else "N/D")

    if flow["orders"] and flow["with_delivery"] is not None:
        section_title("Taux de conversion du cycle Order-to-Cash")
        fig = go.Figure(go.Funnel(
            y=["Commandes", "Livrées", "Facturées"],
            x=[flow["orders"], flow["with_delivery"], flow["with_invoice"]],
            marker={"color": [ACCENT_STRONG, ACCENT, "#B7DFFB"]},
        ))
        st.plotly_chart(style_fig(fig, 380), use_container_width=True)
        st.caption(
            "Basé sur le flux documentaire VBFA (TySub = J pour les livraisons, "
            "M pour les factures)."
        )
    else:
        st.info("Table VBFA non disponible ou incomplète : la chaîne documentaire ne peut pas être reconstituée.")

# --------------------------------------------------------------------------
# PIED DE PAGE
# --------------------------------------------------------------------------

st.markdown(
    f'<div style="text-align:center;color:{TEXT_GREY};font-size:0.72rem;'
    f'margin-top:40px;padding-top:14px;border-top:1px solid {CARD_BORDER};">'
    "SAP SD INTELLIGENCE · ANALYTICAL DASHBOARD · DATA-DRIVEN DECISION SUPPORT</div>",
    unsafe_allow_html=True,
)
