import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from data_loader import (
    load_all_tables,
    prepare_tables,
)


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="SOMACOST | SAP SD Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #f6f8fb;
    }

    section[data-testid="stSidebar"] {
        background-color: #111827;
    }

    section[data-testid="stSidebar"] * {
        color: white;
    }

    .hero {
        background: linear-gradient(
            135deg,
            #111827 0%,
            #1f2937 100%
        );

        padding: 30px 35px;
        border-radius: 18px;
        margin-bottom: 25px;
        color: white;
    }

    .hero-title {
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 4px;
    }

    .hero-subtitle {
        font-size: 15px;
        opacity: 0.75;
    }

    .period-box {
        background: rgba(
            255,
            255,
            255,
            0.08
        );

        padding: 15px 20px;
        border-radius: 12px;
        margin-top: 18px;
    }

    .kpi {
        background: white;
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 15px rgba(
            0,
            0,
            0,
            0.04
        );
    }

    .kpi-title {
        color: #6b7280;
        font-size: 13px;
        font-weight: 600;
    }

    .kpi-value {
        color: #111827;
        font-size: 28px;
        font-weight: 800;
        margin-top: 5px;
    }

    .section-title {
        font-size: 21px;
        font-weight: 750;
        margin-top: 25px;
        margin-bottom: 12px;
        color: #111827;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data(show_spinner=False)
def get_data():

    raw, status = load_all_tables()

    prepared = prepare_tables(
        raw
    )

    return prepared, status


tables, status = get_data()


# ============================================================
# HELPERS
# ============================================================

def fmt_number(value):

    if value is None or pd.isna(value):
        return "—"

    return f"{value:,.0f}"


def fmt_money(value):

    if value is None or pd.isna(value):
        return "—"

    return f"{value:,.0f}"


def safe_unique(
    df,
    column
):

    if (
        df is None
        or column not in df.columns
    ):
        return 0

    return df[column].nunique()


def safe_sum(
    df,
    column
):

    if (
        df is None
        or column not in df.columns
    ):
        return 0

    return pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0).sum()


# ============================================================
# DETECT GLOBAL PERIOD
# ============================================================

def get_global_period():

    candidates = []

    if (
        "VBRK" in tables
        and "_DATE" in tables["VBRK"].columns
    ):

        candidates.append(
            tables["VBRK"]["_DATE"]
        )

    if (
        "VBRP" in tables
        and "_DATE" in tables["VBRP"].columns
    ):

        candidates.append(
            tables["VBRP"]["_DATE"]
        )

    if (
        "VBAK" in tables
        and "_DATE" in tables["VBAK"].columns
    ):

        candidates.append(
            tables["VBAK"]["_DATE"]
        )

    dates = []

    for series in candidates:

        dates.extend(
            series.dropna().tolist()
        )

    if not dates:
        return None, None

    dates = pd.to_datetime(
        dates
    )

    return (
        dates.min(),
        dates.max()
    )


min_date, max_date = get_global_period()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    """
    <h2 style="color:white;">
    SOMACOST
    </h2>

    <p style="color:#9ca3af;">
    SAP SD Analytics
    </p>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Sales",
        "Customers",
        "Products",
        "Logistics",
        "Order-to-Cash",
        "Data Quality",
    ],
)


# ============================================================
# HEADER
# ============================================================

if min_date is not None:

    period_text = (
        f"{min_date.strftime('%d %b %Y')}"
        f"  →  "
        f"{max_date.strftime('%d %b %Y')}"
    )

    days = (
        max_date - min_date
    ).days + 1

else:

    period_text = "Période non détectée"
    days = 0


st.markdown(
    f"""
    <div class="hero">

        <div class="hero-title">
            SOMACOST
        </div>

        <div class="hero-subtitle">
            SAP SD • Sales & Distribution Analytics
        </div>

        <div class="period-box">
            📅 <b>Période réelle des transactions</b><br>
            {period_text}
            &nbsp; • &nbsp;
            {days} jour(s)
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":

    st.markdown(
        '<div class="section-title">'
        'Executive Overview'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # VBRP
    # --------------------------------------------------------

    vbrp = tables.get(
        "VBRP"
    )

    vbrk = tables.get(
        "VBRK"
    )

    vbak = tables.get(
        "VBAK"
    )

    likp = tables.get(
        "LIKP"
    )

    revenue = safe_sum(
        vbrp,
        "NETWR"
    )

    quantity = safe_sum(
        vbrp,
        "FKIMG"
    )

    invoices = safe_unique(
        vbrp,
        "VBELN"
    )

    orders = safe_unique(
        vbak,
        "VBELN"
    )

    customers = safe_unique(
        vbrp,
        "KUNAG"
    )

    deliveries = safe_unique(
        likp,
        "VBELN"
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    cols = st.columns(
        5
    )

    metrics = [
        ("CA NET", fmt_money(revenue)),
        ("QUANTITÉ", fmt_number(quantity)),
        ("FACTURES", fmt_number(invoices)),
        ("COMMANDES", fmt_number(orders)),
        ("LIVRAISONS", fmt_number(deliveries)),
    ]

    for col, (
        title,
        value
    ) in zip(
        cols,
        metrics
    ):

        col.markdown(
            f"""
            <div class="kpi">

                <div class="kpi-title">
                    {title}
                </div>

                <div class="kpi-value">
                    {value}
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # DAILY REVENUE
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">'
        'Performance journalière'
        '</div>',
        unsafe_allow_html=True,
    )

    if (
        vbrp is not None
        and "_DATE" in vbrp.columns
        and "NETWR" in vbrp.columns
    ):

        daily = (
            vbrp
            .dropna(
                subset=["_DATE"]
            )
            .groupby("_DATE")
            .agg(
                CA=("NETWR", "sum"),
                Quantite=(
                    "FKIMG",
                    "sum"
                )
                if "FKIMG" in vbrp.columns
                else (
                    "NETWR",
                    "count"
                ),
                Factures=(
                    "VBELN",
                    "nunique"
                )
                if "VBELN" in vbrp.columns
                else (
                    "NETWR",
                    "count"
                ),
            )
            .reset_index()
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=daily["_DATE"],
                y=daily["CA"],
                mode="lines+markers",
                name="CA",
                line=dict(
                    width=3
                ),
                marker=dict(
                    size=8
                ),
                hovertemplate=
                "<b>%{x|%d %b %Y}</b>"
                "<br>CA: %{y:,.0f}"
                "<extra></extra>",
            )
        )

        fig.update_layout(
            height=430,
            template="plotly_white",
            margin=dict(
                l=20,
                r=20,
                t=30,
                b=20
            ),
            xaxis=dict(
                title="Jour",
                tickformat="%d %b",
                dtick="D1",
            ),
            yaxis=dict(
                title="CA",
                tickformat=",.0f",
            ),
            hovermode="x unified",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # SECOND ROW
    # --------------------------------------------------------

    col1, col2 = st.columns(
        2
    )

    with col1:

        st.markdown(
            '<div class="section-title">'
            'CA par organisation'
            '</div>',
            unsafe_allow_html=True,
        )

        if (
            vbrp is not None
            and "VKORG" in vbrp.columns
        ):

            org = (
                vbrp
                .groupby("VKORG")["NETWR"]
                .sum()
                .reset_index()
                .sort_values(
                    "NETWR",
                    ascending=True
                )
            )

            fig = px.bar(
                org,
                x="NETWR",
                y="VKORG",
                orientation="h",
                text="NETWR",
            )

            fig.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
            )

            fig.update_layout(
                template="plotly_white",
                height=350,
                xaxis_title="CA",
                yaxis_title="Organisation",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    with col2:

        st.markdown(
            '<div class="section-title">'
            'Top produits'
            '</div>',
            unsafe_allow_html=True,
        )

        if (
            vbrp is not None
            and "MATNR" in vbrp.columns
        ):

            products = (
                vbrp
                .groupby("MATNR")["NETWR"]
                .sum()
                .reset_index()
                .sort_values(
                    "NETWR",
                    ascending=False
                )
                .head(10)
                .sort_values(
                    "NETWR"
                )
            )

            fig = px.bar(
                products,
                x="NETWR",
                y="MATNR",
                orientation="h",
                text="NETWR",
            )

            fig.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
            )

            fig.update_layout(
                template="plotly_white",
                height=350,
                xaxis_title="CA",
                yaxis_title="Produit",
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )


# ============================================================
# SALES
# ============================================================

elif page == "Sales":

    st.markdown(
        '<div class="section-title">'
        'Sales Performance'
        '</div>',
        unsafe_allow_html=True,
    )

    vbrp = tables.get(
        "VBRP"
    )

    if vbrp is None:

        st.error(
            "VBRP n'est pas disponible."
        )

        st.stop()

    # --------------------------------------------------------
    # Daily sales
    # --------------------------------------------------------

    if (
        "_DATE" in vbrp.columns
        and "NETWR" in vbrp.columns
    ):

        daily = (
            vbrp
            .groupby("_DATE")["NETWR"]
            .sum()
            .reset_index()
        )

        fig = px.area(
            daily,
            x="_DATE",
            y="NETWR",
            markers=True,
            title="CA journalier",
        )

        fig.update_traces(
            hovertemplate=
            "%{x|%d %b %Y}"
            "<br>CA: %{y:,.0f}"
            "<extra></extra>"
        )

        fig.update_layout(
            template="plotly_white",
            height=430,
            xaxis=dict(
                title="Jour",
                tickformat="%d %b",
                dtick="D1",
            ),
            yaxis=dict(
                title="CA",
                tickformat=",.0f",
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Organization / office
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        if "VKORG" in vbrp.columns:

            data = (
                vbrp
                .groupby("VKORG")["NETWR"]
                .sum()
                .reset_index()
            )

            fig = px.pie(
                data,
                names="VKORG",
                values="NETWR",
                hole=0.55,
                title="Répartition du CA",
            )

            fig.update_layout(
                template="plotly_white"
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    with col2:

        if "VKBUR" in vbrp.columns:

            data = (
                vbrp
                .groupby("VKBUR")["NETWR"]
                .sum()
                .reset_index()
                .sort_values(
                    "NETWR"
                )
            )

            fig = px.bar(
                data,
                x="NETWR",
                y="VKBUR",
                orientation="h",
                title="CA par bureau",
            )

            fig.update_layout(
                template="plotly_white"
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    # --------------------------------------------------------
    # Daily invoices
    # --------------------------------------------------------

    if (
        "_DATE" in vbrp.columns
        and "VBELN" in vbrp.columns
    ):

        daily_invoice = (
            vbrp
            .groupby("_DATE")["VBELN"]
            .nunique()
            .reset_index(
                name="Factures"
            )
        )

        fig = px.bar(
            daily_invoice,
            x="_DATE",
            y="Factures",
            title="Factures par jour",
        )

        fig.update_layout(
            template="plotly_white",
            xaxis=dict(
                tickformat="%d %b",
                dtick="D1",
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# ============================================================
# CUSTOMERS
# ============================================================

elif page == "Customers":

    st.markdown(
        '<div class="section-title">'
        'Customer Analysis'
        '</div>',
        unsafe_allow_html=True,
    )

    vbrp = tables.get(
        "VBRP"
    )

    if (
        vbrp is None
        or "KUNAG" not in vbrp.columns
    ):

        st.warning(
            "KUNAG n'est pas disponible "
            "dans VBRP."
        )

        st.stop()

    customers = (
        vbrp
        .groupby("KUNAG")
        .agg(
            CA=("NETWR", "sum"),
            Factures=(
                "VBELN",
                "nunique"
            )
            if "VBELN" in vbrp.columns
            else (
                "NETWR",
                "count"
            ),
        )
        .reset_index()
        .sort_values(
            "CA",
            ascending=False
        )
    )

    # --------------------------------------------------------
    # Top customers
    # --------------------------------------------------------

    top = (
        customers
        .head(20)
        .sort_values(
            "CA"
        )
    )

    fig = px.bar(
        top,
        x="CA",
        y="KUNAG",
        orientation="h",
        text="CA",
        title="Top 20 clients par CA",
    )

    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
    )

    fig.update_layout(
        template="plotly_white",
        height=550,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # --------------------------------------------------------
    # Pareto
    # --------------------------------------------------------

    customers["CA_CUMULE"] = (
        customers["CA"].cumsum()
    )

    total = customers["CA"].sum()

    if total != 0:

        customers["CA_CUMULE_PCT"] = (
            customers["CA_CUMULE"]
            / total
            * 100
        )

        fig = px.line(
            customers,
            x=np.arange(
                1,
                len(customers) + 1
            ),
            y="CA_CUMULE_PCT",
            title="Pareto clients",
        )

        fig.add_hline(
            y=80,
            line_dash="dash",
        )

        fig.update_layout(
            template="plotly_white",
            xaxis_title="Nombre de clients",
            yaxis_title="% CA cumulé",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# ============================================================
# PRODUCTS
# ============================================================

elif page == "Products":

    st.markdown(
        '<div class="section-title">'
        'Product Analysis'
        '</div>',
        unsafe_allow_html=True,
    )

    vbrp = tables.get(
        "VBRP"
    )

    if (
        vbrp is None
        or "MATNR" not in vbrp.columns
    ):

        st.warning(
            "MATNR n'est pas disponible."
        )

        st.stop()

    products = (
        vbrp
        .groupby("MATNR")
        .agg(
            CA=("NETWR", "sum"),
            Quantite=(
                "FKIMG",
                "sum"
            )
            if "FKIMG" in vbrp.columns
            else (
                "NETWR",
                "count"
            ),
        )
        .reset_index()
        .sort_values(
            "CA",
            ascending=False
        )
    )

    # --------------------------------------------------------
    # Top 15
    # --------------------------------------------------------

    top = (
        products
        .head(15)
        .sort_values(
            "CA"
        )
    )

    fig = px.bar(
        top,
        x="CA",
        y="MATNR",
        orientation="h",
        text="CA",
        title="Top 15 produits",
    )

    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
    )

    fig.update_layout(
        template="plotly_white",
        height=500,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        products.head(100),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# LOGISTICS
# ============================================================

elif page == "Logistics":

    st.markdown(
        '<div class="section-title">'
        'Logistics'
        '</div>',
        unsafe_allow_html=True,
    )

    likp = tables.get(
        "LIKP"
    )

    if likp is None:

        st.warning(
            "LIKP n'est pas disponible."
        )

        st.stop()

    deliveries = safe_unique(
        likp,
        "VBELN"
    )

    st.metric(
        "Livraisons",
        fmt_number(deliveries)
    )

    if (
        "_DATE" in likp.columns
    ):

        daily = (
            likp
            .groupby("_DATE")
            .size()
            .reset_index(
                name="Livraisons"
            )
        )

        fig = px.bar(
            daily,
            x="_DATE",
            y="Livraisons",
            title="Livraisons par jour",
        )

        fig.update_layout(
            template="plotly_white",
            xaxis=dict(
                tickformat="%d %b",
                dtick="D1",
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# ============================================================
# ORDER TO CASH
# ============================================================

elif page == "Order-to-Cash":

    st.markdown(
        '<div class="section-title">'
        'Order-to-Cash'
        '</div>',
        unsafe_allow_html=True,
    )

    vbak = tables.get(
        "VBAK"
    )

    likp = tables.get(
        "LIKP"
    )

    vbrk = tables.get(
        "VBRK"
    )

    orders = safe_unique(
        vbak,
        "VBELN"
    )

    deliveries = safe_unique(
        likp,
        "VBELN"
    )

    invoices = safe_unique(
        vbrk,
        "VBELN"
    )

    cols = st.columns(3)

    cols[0].metric(
        "Commandes",
        fmt_number(orders)
    )

    cols[1].metric(
        "Livraisons",
        fmt_number(deliveries)
    )

    cols[2].metric(
        "Factures",
        fmt_number(invoices)
    )

    funnel = pd.DataFrame(
        {
            "Étape": [
                "Commandes",
                "Livraisons",
                "Factures",
            ],
            "Volume": [
                orders,
                deliveries,
                invoices,
            ],
        }
    )

    fig = px.funnel(
        funnel,
        x="Volume",
        y="Étape",
        title="Chaîne Order-to-Cash",
    )

    fig.update_layout(
        template="plotly_white",
        height=450,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# DATA QUALITY
# ============================================================

elif page == "Data Quality":

    st.markdown(
        '<div class="section-title">'
        'Data Quality'
        '</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        status,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        '<div class="section-title">'
        'Valeurs manquantes'
        '</div>',
        unsafe_allow_html=True,
    )

    rows = []

    for table_name, df in tables.items():

        for column in df.columns:

            missing = (
                df[column]
                .isna()
                .sum()
            )

            if missing:

                rows.append(
                    {
                        "Table": table_name,
                        "Champ": column,
                        "Manquants": missing,
                        "Total": len(df),
                        "Taux (%)": round(
                            missing
                            / len(df)
                            * 100,
                            2,
                        ),
                    }
                )

    if rows:

        quality = (
            pd.DataFrame(rows)
            .sort_values(
                "Taux (%)",
                ascending=False
            )
        )

        st.dataframe(
            quality,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.success(
            "Aucune valeur manquante."
        )