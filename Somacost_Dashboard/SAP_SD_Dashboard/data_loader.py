"""
data_loader.py
==================================================
Chargement et préparation des données SAP SD (module Sales & Distribution)
pour le dashboard "SAP SD Intelligence".

Les fichiers sources sont des exports bruts SAP GUI (SE16 / VA05 / VL06O)
enregistrés au format ".XLS" mais qui sont en réalité du texte
tabulé encodé en UTF-16 (format d'export standard de SAP GUI).
Ce module sait lire ce format directement, sans dépendre d'Excel/xlrd.

Tables attendues dans DATA_DIR :
    KNA1.XLS   -> Clients (une ligne par client)
    MARA.XLS   -> Articles / matières (une ligne par article)
    VBAK.XLS   -> Commandes de vente, en-tête (une ligne par commande)
    VBRK.XLS   -> Factures, en-tête (une ligne par facture)
    VBRP.XLS   -> Factures, lignes (une ligne par poste facturé)
    LIKP.XLS   -> Livraisons, en-tête (une ligne par livraison)
    VBFA.XLS   -> Flux documentaire (commande -> livraison -> facture)

NB : les noms de fichiers réels peuvent contenir un suffixe de période
(ex. "vbak_010713_050713.XLS") ou être en minuscules/majuscules mixtes ;
`resolve_file()` gère ces variantes automatiquement.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# 0. CONFIGURATION
# --------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Pour chaque table : combien de lignes d'en-tête SAP faut-il sauter avant
# la vraie ligne de titres de colonnes ? (déterminé en inspectant les
# fichiers réels : la plupart des exports SAP GUI ont un bandeau de 3 lignes
# — date d'édition, ligne vide, ligne vide — avant les titres de colonnes,
# sauf VBRK ici, exporté sans bandeau.)
HEADER_ROWS = {
    "KNA1": 3,
    "MARA": 3,
    "VBAK": 3,
    "VBRK": 0,
    "VBRP": 3,
    "LIKP": 3,
    "VBFA": 3,
}

# Motifs de recherche de fichiers (insensibles à la casse et au suffixe de
# période éventuel type "_010713_050713").
FILE_PATTERNS = {
    "KNA1": "KNA1*",
    "MARA": "MARA*",
    "VBAK": "vbak*",
    "VBRK": "VBRK*",
    "VBRP": "VBRP*",
    "LIKP": "likp*",
    "VBFA": "vbfa*",
}

# Types de facture (FKART) considérés comme du chiffre d'affaires "normal"
CA_FKART = {"F2"}
# Types de facture considérés comme des avoirs / notes de crédit
AVOIR_FKART = {"G2", "S1", "ZG2", "RE"}
# Tout le reste (ex. "ZC" = demandes d'acompte) est classé "AUTRE" et exclu
# du chiffre d'affaires net.

# Seuil (en jours, valeur absolue) au-delà duquel un écart de livraison est
# considéré comme une anomalie de saisie plutôt qu'un vrai retard/avance,
# et donc exclu du calcul des statistiques (mais visible dans la page
# "Qualité des données").
ECART_OUTLIER_THRESHOLD = 60


# --------------------------------------------------------------------------
# 1. UTILITAIRES BAS NIVEAU — lecture des exports SAP GUI
# --------------------------------------------------------------------------

def resolve_file(key: str, data_dir: str = DATA_DIR) -> Optional[str]:
    """Retrouve le chemin réel d'une table à partir de motifs de noms de
    fichiers tolérants (casse, suffixe de période, extension). Les noms de
    fichiers SAP sont exportés tantôt en majuscules, tantôt en minuscules
    (ex. "VBAK.XLS" vs "vbak_010713_050713.XLS"), donc la recherche se
    fait insensible à la casse."""
    if not os.path.isdir(data_dir):
        return None
    prefix = key.lower()
    candidates = [
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.lower().startswith(prefix) and os.path.isfile(os.path.join(data_dir, f))
    ]
    candidates.sort()
    return candidates[0] if candidates else None


def _dedup_columns(cols) -> list:
    """SAP exporte parfois deux colonnes avec le même intitulé (ex. 'Dev.'
    apparaît 3 fois dans VBAK). On les distingue par un suffixe numérique
    pour éviter les collisions lors de la sélection de colonnes."""
    seen: dict = {}
    out = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
    return out


def read_sap_export(path: str, header_row: int) -> pd.DataFrame:
    """Lit un export SAP GUI (texte tabulé, encodage UTF-16) et retourne un
    DataFrame propre : colonnes nettoyées, dédupliquées, cellules "trim",
    lignes totalement vides supprimées."""
    df = pd.read_csv(
        path,
        sep="\t",
        encoding="utf-16",
        skiprows=header_row,
        header=0,
        dtype=str,
        engine="python",
    )
    df.columns = [str(c).strip() for c in df.columns]
    # colonnes sans nom (bordures de tableau SAP) -> on les enlève
    df = df.loc[:, [c for c in df.columns if not str(c).startswith("Unnamed") and c != ""]]
    df.columns = _dedup_columns(list(df.columns))
    df = df.dropna(how="all").reset_index(drop=True)
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        df[c] = df[c].replace({"nan": np.nan, "": np.nan, "None": np.nan})
    return df


def parse_sap_number(series: pd.Series) -> pd.Series:
    """Convertit un nombre au format SAP français ("31.060,91" ou
    "1.050,000") en float. Gère aussi la notation scientifique
    résiduelle parfois présente dans VBFA."""
    if series is None:
        return series
    s = series.astype(str).str.strip()
    s = s.replace({"nan": np.nan, "": np.nan})
    # notation scientifique type "1,0500000000000000E+03" -> "1.05E+03"
    is_sci = s.str.contains("E[+-]", regex=True, na=False)
    s_sci = s.where(is_sci).str.replace(",", ".", regex=False)
    # format standard SAP : point = séparateur de milliers, virgule = décimale
    s_std = s.where(~is_sci).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    combined = s_sci.fillna(s_std)
    return pd.to_numeric(combined, errors="coerce")


def parse_sap_date(series: pd.Series) -> pd.Series:
    """Convertit une date SAP au format JJ.MM.AAAA en datetime."""
    return pd.to_datetime(series, format="%d.%m.%Y", errors="coerce")


# --------------------------------------------------------------------------
# 2. CHARGEMENT DES TABLES BRUTES
# --------------------------------------------------------------------------

@dataclass
class RawTables:
    kna1: pd.DataFrame = field(default_factory=pd.DataFrame)
    mara: pd.DataFrame = field(default_factory=pd.DataFrame)
    vbak: pd.DataFrame = field(default_factory=pd.DataFrame)
    vbrk: pd.DataFrame = field(default_factory=pd.DataFrame)
    vbrp: pd.DataFrame = field(default_factory=pd.DataFrame)
    likp: pd.DataFrame = field(default_factory=pd.DataFrame)
    vbfa: pd.DataFrame = field(default_factory=pd.DataFrame)
    missing: list = field(default_factory=list)


def load_raw_tables(data_dir: str = DATA_DIR) -> RawTables:
    """Charge les 7 tables SAP brutes depuis data_dir. Une table absente
    n'interrompt pas le chargement : elle reste un DataFrame vide et son
    nom est ajouté à `missing` (affiché dans la page Qualité des données)."""
    tables = RawTables()
    for key in HEADER_ROWS:
        path = resolve_file(key, data_dir)
        attr = key.lower()
        if path is None:
            tables.missing.append(key)
            continue
        df = read_sap_export(path, HEADER_ROWS[key])
        setattr(tables, attr, df)
    return tables


# --------------------------------------------------------------------------
# 3. NORMALISATION DES IDENTIFIANTS DE DOCUMENTS
# --------------------------------------------------------------------------

def _norm_id(series: pd.Series, width: int = 10) -> pd.Series:
    """Les numéros de document SAP sont stockés avec des largeurs de
    zéros de tête variables selon la table d'origine (VBRK: 8 chiffres,
    VBRP/VBAK/LIKP/VBFA: 10 chiffres). On les uniformise pour permettre
    les jointures."""
    if series is None:
        return series
    return series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(width)


# --------------------------------------------------------------------------
# 4. CONSTRUCTION DU MODÈLE ANALYTIQUE
# --------------------------------------------------------------------------

@dataclass
class Model:
    orders: pd.DataFrame          # VBAK nettoyé
    invoices_header: pd.DataFrame  # VBRK nettoyé + classification CA/AVOIR/AUTRE
    invoices_items: pd.DataFrame   # VBRP x VBRK (lignes de facture enrichies)
    deliveries: pd.DataFrame       # LIKP nettoyé + écart de livraison calculé
    customers: pd.DataFrame        # KNA1 nettoyé
    materials: pd.DataFrame        # MARA nettoyé
    doc_flow: pd.DataFrame         # VBFA nettoyé
    missing_tables: list
    data_quality: dict             # petits indicateurs pour la page 0


def build_model(data_dir: str = DATA_DIR) -> Model:
    raw = load_raw_tables(data_dir)
    dq: dict = {"missing_tables": raw.missing}

    # ---- Clients (KNA1) ----------------------------------------------
    customers = raw.kna1.copy()
    if not customers.empty:
        customers["KUNNR"] = _norm_id(customers["KUNNR"], width=10)
        customers = customers.rename(columns={"NAME1": "Client"})

    # ---- Articles (MARA) ----------------------------------------------
    materials = raw.mara.copy()

    # ---- Commandes (VBAK) ----------------------------------------------
    orders = raw.vbak.copy()
    if not orders.empty:
        orders = orders.rename(columns={
            "Doc. vente": "VBELN",
            "Créé le": "ERDAT",
            "OrgCm": "VKORG",
            "CDis": "VTWEG",
            "SA": "SPART",
            "Valeur nette": "NETWR",
        })
        orders["VBELN"] = _norm_id(orders["VBELN"], width=10)
        orders["ERDAT"] = parse_sap_date(orders["ERDAT"])
        orders["NETWR"] = parse_sap_number(orders["NETWR"])
    dq["n_orders"] = len(orders)

    # ---- Factures en-tête (VBRK) ---------------------------------------
    inv_h = raw.vbrk.copy()
    if not inv_h.empty:
        inv_h["VBELN"] = _norm_id(inv_h["VBELN"], width=10)
        inv_h["FKDAT"] = parse_sap_date(inv_h["FKDAT"])
        inv_h["NETWR"] = parse_sap_number(inv_h["NETWR"])

        def classify(fkart):
            if fkart in CA_FKART:
                return "CA"
            if fkart in AVOIR_FKART:
                return "AVOIR"
            return "AUTRE"

        inv_h["TYPE_FACTURE"] = inv_h["FKART"].apply(classify)
    dq["n_invoices_total"] = len(inv_h)
    dq["n_invoices_ca"] = int((inv_h["TYPE_FACTURE"] == "CA").sum()) if not inv_h.empty else 0
    dq["n_invoices_avoir"] = int((inv_h["TYPE_FACTURE"] == "AVOIR").sum()) if not inv_h.empty else 0
    dq["n_invoices_autre"] = int((inv_h["TYPE_FACTURE"] == "AUTRE").sum()) if not inv_h.empty else 0

    # ---- Lignes de facture (VBRP) x en-tête (VBRK) ----------------------
    items = raw.vbrp.copy()
    if not items.empty:
        items["VBELN"] = _norm_id(items["VBELN"], width=10)
        for col in ("FKIMG", "NETWR", "BRGEW", "NTGEW"):
            if col in items.columns:
                items[col] = parse_sap_number(items[col])
        keep_header_cols = [c for c in ["VBELN", "FKDAT", "VKORG", "VTWEG", "SPART",
                                         "KUNAG", "KUNRG", "TYPE_FACTURE", "FKART"]
                             if c in inv_h.columns or c == "VBELN"]
        header_slim = inv_h[keep_header_cols] if not inv_h.empty else pd.DataFrame(columns=keep_header_cols)
        items = items.merge(header_slim, on="VBELN", how="left", suffixes=("", "_hdr"))
        # jointure client -> nom
        if not customers.empty and "KUNAG" in items.columns:
            items["KUNAG"] = _norm_id(items["KUNAG"], width=10)
            items = items.merge(
                customers[["KUNNR", "Client"]], left_on="KUNAG", right_on="KUNNR", how="left"
            )
    dq["n_invoice_items"] = len(items)
    dq["n_items_unmatched_header"] = int(items["TYPE_FACTURE"].isna().sum()) if not items.empty and "TYPE_FACTURE" in items.columns else 0

    # ---- Livraisons (LIKP) ----------------------------------------------
    deliv = raw.likp.copy()
    if not deliv.empty:
        deliv = deliv.rename(columns={
            "Livraison": "VBELN",
            "PExp": "VSTEL",
            "OrgCm": "VKORG",
            "TLvr.": "LFART",
            "Poids net": "POIDS_NET",
            "Poids total": "POIDS_TOTAL",
        })
        deliv["VBELN"] = _norm_id(deliv["VBELN"], width=10)
        deliv["DATE_PLANIFIEE"] = parse_sap_date(deliv["DtePlanMS"])
        # "SM réelle" = date réelle de sortie marchandise (goods issue réel)
        deliv["DATE_REELLE"] = parse_sap_date(deliv["SM réelle"]) if "SM réelle" in deliv.columns else pd.NaT
        deliv["POIDS_NET"] = parse_sap_number(deliv["POIDS_NET"]) if "POIDS_NET" in deliv.columns else np.nan
        deliv["POIDS_TOTAL"] = parse_sap_number(deliv["POIDS_TOTAL"]) if "POIDS_TOTAL" in deliv.columns else np.nan

        deliv["ECART_JOURS"] = (deliv["DATE_REELLE"] - deliv["DATE_PLANIFIEE"]).dt.days
        deliv["ECART_ANOMALIE"] = deliv["ECART_JOURS"].abs() > ECART_OUTLIER_THRESHOLD
    dq["n_deliveries"] = len(deliv)
    dq["n_deliveries_missing_dates"] = int(deliv["ECART_JOURS"].isna().sum()) if not deliv.empty else 0
    dq["n_deliveries_outliers"] = int(deliv["ECART_ANOMALIE"].sum()) if not deliv.empty else 0
    dq["vkbur_empty"] = bool(not items.empty and "VKBUR" in raw.vbrp.columns and raw.vbrp["VKBUR"].notna().sum() == 0)

    # ---- Flux documentaire (VBFA) ---------------------------------------
    doc_flow = raw.vbfa.copy()

    return Model(
        orders=orders,
        invoices_header=inv_h,
        invoices_items=items,
        deliveries=deliv,
        customers=customers,
        materials=materials,
        doc_flow=doc_flow,
        missing_tables=raw.missing,
        data_quality=dq,
    )


# --------------------------------------------------------------------------
# 5. FONCTIONS D'AGRÉGATION UTILISÉES PAR LES PAGES DU DASHBOARD
# --------------------------------------------------------------------------

def filter_period(df: pd.DataFrame, date_col: str, start, end) -> pd.DataFrame:
    """Filtre un DataFrame sur une période, en tolérant une colonne de
    date absente ou entièrement vide (retourne le DataFrame tel quel)."""
    if df.empty or date_col not in df.columns:
        return df
    mask = df[date_col].notna()
    if start is not None:
        mask &= df[date_col] >= pd.Timestamp(start)
    if end is not None:
        mask &= df[date_col] <= pd.Timestamp(end)
    return df.loc[mask].copy()


def kpi_overview(model: Model, start=None, end=None) -> dict:
    items = filter_period(model.invoices_items, "FKDAT", start, end)
    orders = filter_period(model.orders, "ERDAT", start, end)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items

    ca_net = ca_items["NETWR"].sum() if "NETWR" in ca_items.columns else 0.0
    n_commandes = orders["VBELN"].nunique() if "VBELN" in orders.columns else 0
    n_factures = ca_items["VBELN"].nunique() if "VBELN" in ca_items.columns else 0
    n_clients = ca_items["KUNAG"].nunique() if "KUNAG" in ca_items.columns else 0
    panier_moyen = (ca_net / n_factures) if n_factures else 0.0

    deliv = filter_period(model.deliveries, "DATE_PLANIFIEE", start, end)
    deliv_valid = deliv[~deliv["ECART_ANOMALIE"]] if "ECART_ANOMALIE" in deliv.columns else deliv
    taux_service = (deliv_valid["ECART_JOURS"] <= 0).mean() * 100 if len(deliv_valid) else np.nan

    return {
        "ca_net": ca_net,
        "n_commandes": n_commandes,
        "n_factures": n_factures,
        "n_clients": n_clients,
        "panier_moyen": panier_moyen,
        "taux_service": taux_service,
    }


def ca_daily(model: Model, start=None, end=None) -> pd.DataFrame:
    items = filter_period(model.invoices_items, "FKDAT", start, end)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    if ca_items.empty:
        return pd.DataFrame(columns=["Date", "CA_net"])
    g = ca_items.groupby(ca_items["FKDAT"].dt.date)["NETWR"].sum().reset_index()
    g.columns = ["Date", "CA_net"]
    g["Variation_%"] = g["CA_net"].pct_change() * 100
    return g.sort_values("Date")


def ca_by_dimension(model: Model, dim: str, start=None, end=None) -> pd.DataFrame:
    """dim = 'VKORG' (organisation commerciale), 'VTWEG' (canal), 'SPART'
    (division) ou 'VKBUR' (bureau des ventes)."""
    items = filter_period(model.invoices_items, "FKDAT", start, end)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    if ca_items.empty or dim not in ca_items.columns or ca_items[dim].notna().sum() == 0:
        return pd.DataFrame(columns=[dim, "CA"])
    g = ca_items.groupby(dim)["NETWR"].sum().reset_index().rename(columns={"NETWR": "CA"})
    return g.sort_values("CA", ascending=False)


def top_articles(model: Model, n: int = 10, start=None, end=None) -> pd.DataFrame:
    items = filter_period(model.invoices_items, "FKDAT", start, end)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    if ca_items.empty:
        return pd.DataFrame(columns=["ARKTX", "CA", "FKIMG"])
    g = ca_items.groupby("ARKTX").agg(CA=("NETWR", "sum"), FKIMG=("FKIMG", "sum")).reset_index()
    return g.sort_values("CA", ascending=False).head(n)


def pareto_curve(df: pd.DataFrame, label_col: str, value_col: str) -> pd.DataFrame:
    """Construit une courbe de Pareto (% cumulé du total) pour n'importe
    quel DataFrame agrégé (articles, clients...)."""
    if df.empty:
        return pd.DataFrame(columns=[label_col, value_col, "pct_cumule", "pct_rang"])
    d = df.sort_values(value_col, ascending=False).reset_index(drop=True)
    d["pct_cumule"] = d[value_col].cumsum() / d[value_col].sum() * 100
    d["pct_rang"] = (d.index + 1) / len(d) * 100
    return d


def ca_by_family(model: Model, start=None, end=None) -> pd.DataFrame:
    items = filter_period(model.invoices_items, "FKDAT", start, end)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    if ca_items.empty or "MATKL" not in ca_items.columns:
        return pd.DataFrame(columns=["MATKL", "CA"])
    g = ca_items.groupby("MATKL")["NETWR"].sum().reset_index().rename(columns={"NETWR": "CA"})
    return g.sort_values("CA", ascending=False)


def top_clients(model: Model, n: int = 15, start=None, end=None) -> pd.DataFrame:
    items = filter_period(model.invoices_items, "FKDAT", start, end)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    if ca_items.empty or "Client" not in ca_items.columns:
        return pd.DataFrame(columns=["Client", "CA"])
    g = ca_items.groupby("Client")["NETWR"].sum().reset_index().rename(columns={"NETWR": "CA"})
    return g.sort_values("CA", ascending=False).head(n)


def poids_par_point_expedition(model: Model, n: int = 15, start=None, end=None) -> pd.DataFrame:
    deliv = filter_period(model.deliveries, "DATE_PLANIFIEE", start, end)
    if deliv.empty or "VSTEL" not in deliv.columns:
        return pd.DataFrame(columns=["VSTEL", "POIDS_NET"])
    g = deliv.groupby("VSTEL")["POIDS_NET"].sum().reset_index()
    return g.sort_values("POIDS_NET", ascending=False).head(n)


def ecart_livraison_series(model: Model, start=None, end=None) -> pd.Series:
    deliv = filter_period(model.deliveries, "DATE_PLANIFIEE", start, end)
    if deliv.empty:
        return pd.Series(dtype=float)
    valid = deliv[~deliv["ECART_ANOMALIE"]] if "ECART_ANOMALIE" in deliv.columns else deliv
    return valid["ECART_JOURS"].dropna()


def livraisons_par_type(model: Model, start=None, end=None) -> pd.DataFrame:
    deliv = filter_period(model.deliveries, "DATE_PLANIFIEE", start, end)
    if deliv.empty or "LFART" not in deliv.columns:
        return pd.DataFrame(columns=["Type de livraison", "Nombre"])
    g = deliv["LFART"].value_counts().reset_index()
    g.columns = ["Type de livraison", "Nombre"]
    return g


def commandes_vs_factures(model: Model, start=None, end=None) -> pd.DataFrame:
    orders = filter_period(model.orders, "ERDAT", start, end)
    items = filter_period(model.invoices_items, "FKDAT", start, end)
    ca_items = items[items["TYPE_FACTURE"] == "CA"] if "TYPE_FACTURE" in items.columns else items
    n_cmd = orders["VBELN"].nunique() if "VBELN" in orders.columns else 0
    n_fac = ca_items["VBELN"].nunique() if "VBELN" in ca_items.columns else 0
    return pd.DataFrame({"Type": ["Commandes", "Factures"], "Nombre": [n_cmd, n_fac]})


def doc_flow_completeness(model: Model) -> dict:
    """Page 7 - Chaîne documentaire : pour chaque commande, la commande
    a-t-elle donné lieu à une livraison ? à une facture ? Utilise VBFA
    (flux de documents) quand disponible."""
    flow = model.doc_flow
    orders_n = model.orders["VBELN"].nunique() if not model.orders.empty else 0
    if flow.empty or "Précédent" not in flow.columns:
        return {"orders": orders_n, "with_delivery": None, "with_invoice": None}

    prec = _norm_id(flow["Précédent"], width=10)
    sub_type = flow["TySub"] if "TySub" in flow.columns else pd.Series(dtype=str)
    # TySub SAP standard : J = livraison, M = facture
    has_delivery = flow.loc[sub_type == "J", "Précédent"]
    has_invoice = flow.loc[sub_type == "M", "Précédent"]
    with_delivery = _norm_id(has_delivery, width=10).nunique()
    with_invoice = _norm_id(has_invoice, width=10).nunique()
    return {"orders": orders_n, "with_delivery": with_delivery, "with_invoice": with_invoice}
