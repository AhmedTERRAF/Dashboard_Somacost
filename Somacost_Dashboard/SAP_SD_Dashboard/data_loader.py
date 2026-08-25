from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "real"


# ============================================================
# FILE DISCOVERY
# ============================================================

TABLES = [
    "VBRP",
    "VBRK",
    "VBAK",
    "VBFA",
    "MARA",
    "LIKP",
    "KNA1",
    "VBAP",
    "LIPS",
    "VBUK",
    "BSID",
    "BSAD",
]


def find_table_file(table_name):
    """
    Find the SAP file corresponding to a table.

    The original filename is not modified.
    """

    if not DATA_DIR.exists():
        return None

    table_name = table_name.upper()

    for file in DATA_DIR.iterdir():

        if not file.is_file():
            continue

        if file.name.upper().startswith(table_name):
            return file

    return None


# ============================================================
# SAP XLS READER
# ============================================================

def read_sap_file(path):

    # --------------------------------------------------------
    # Try real Excel first
    # --------------------------------------------------------

    try:

        df = pd.read_excel(
            path,
            dtype=str
        )

        if df.shape[1] > 1:
            return clean_dataframe(df)

    except Exception:
        pass

    # --------------------------------------------------------
    # SAP dynamic list
    # --------------------------------------------------------

    encodings = [
        "utf-16",
        "utf-16-le",
        "utf-8",
        "latin1",
    ]

    lines = None

    for encoding in encodings:

        try:

            with open(
                path,
                "r",
                encoding=encoding
            ) as f:

                lines = f.readlines()

            break

        except Exception:
            continue

    if lines is None:

        raise ValueError(
            f"Impossible de lire {path.name}"
        )

    # --------------------------------------------------------
    # Find header
    # --------------------------------------------------------

    header_index = None

    for i, line in enumerate(lines):

        upper = line.upper()

        if (
            "MANDT" in upper
            and (
                "VBELN" in upper
                or "MATNR" in upper
            )
        ):

            header_index = i
            break

    if header_index is None:

        raise ValueError(
            f"Header SAP introuvable dans {path.name}"
        )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    header = lines[
        header_index
    ].rstrip("\r\n").split("\t")

    header = [
        x.strip()
        for x in header
    ]

    # Remove initial empty SAP column
    if header and header[0] == "":
        header = header[1:]

    # --------------------------------------------------------
    # Data
    # --------------------------------------------------------

    rows = []

    for line in lines[
        header_index + 1:
    ]:

        if not line.strip():
            continue

        values = line.rstrip(
            "\r\n"
        ).split("\t")

        if values and values[0].strip() == "":
            values = values[1:]

        if len(values) < len(header):

            values += [
                ""
            ] * (
                len(header)
                - len(values)
            )

        if len(values) > len(header):

            values = values[
                :len(header)
            ]

        rows.append(values)

    df = pd.DataFrame(
        rows,
        columns=header
    )

    return clean_dataframe(df)


# ============================================================
# CLEANING
# ============================================================

def clean_dataframe(df):

    df = df.copy()

    df.columns = [
        str(c).strip().upper()
        for c in df.columns
    ]

    # Do NOT modify the original files.
    # This only cleans the dataframe in memory.

    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = (
                df[column]
                .astype(str)
                .str.strip()
                .replace(
                    {
                        "": np.nan,
                        "NAN": np.nan,
                        "NONE": np.nan,
                    }
                )
            )

    return df


# ============================================================
# SAP NUMBER
# ============================================================

def sap_number(series):

    def convert(value):

        if pd.isna(value):
            return np.nan

        value = str(value).strip()

        if value == "":
            return np.nan

        value = value.replace(
            " ",
            ""
        )

        # European format
        if "," in value:

            value = value.replace(
                ".",
                ""
            )

            value = value.replace(
                ",",
                "."
            )

        try:

            return float(value)

        except Exception:

            return np.nan

    return series.apply(convert)


# ============================================================
# SAP DATE
# ============================================================

def sap_date(series):

    return pd.to_datetime(
        series,
        format="%d.%m.%Y",
        errors="coerce"
    )


# ============================================================
# COLUMN HELPER
# ============================================================

def find_column(
    df,
    candidates
):

    if df is None:
        return None

    columns = {
        str(c).upper().strip(): c
        for c in df.columns
    }

    for candidate in candidates:

        candidate = (
            candidate
            .upper()
            .strip()
        )

        if candidate in columns:
            return columns[candidate]

    return None


# ============================================================
# TIME COLUMNS
# ============================================================

def add_daily_time_columns(
    df,
    date_column
):

    if date_column is None:
        return df

    df = df.copy()

    df["_DATE"] = sap_date(
        df[date_column]
    )

    df["_DAY"] = (
        df["_DATE"].dt.day
    )

    df["_DAY_NAME"] = (
        df["_DATE"]
        .dt.strftime("%A")
    )

    df["_DAY_LABEL"] = (
        df["_DATE"]
        .dt.strftime("%d %b")
    )

    df["_WEEK"] = (
        df["_DATE"]
        .dt.isocalendar()
        .week
    )

    df["_YEAR"] = (
        df["_DATE"].dt.year
    )

    return df


# ============================================================
# VBRP
# ============================================================

def prepare_vbrp(df):

    if df is None:
        return None

    df = df.copy()

    for column in [
        "FKIMG",
        "NETWR",
        "NTGEW",
        "BRGEW",
    ]:

        if column in df.columns:

            df[column] = sap_number(
                df[column]
            )

    # For VBRP we use FBUDA as the
    # operational date when available.

    date_column = find_column(
        df,
        [
            "FBUDA",
            "PRSDT",
        ]
    )

    if date_column:

        df = add_daily_time_columns(
            df,
            date_column
        )

    return df


# ============================================================
# VBRK
# ============================================================

def prepare_vbrk(df):

    if df is None:
        return None

    df = df.copy()

    for column in [
        "NETWR",
        "MWSBK",
        "KURRF",
    ]:

        if column in df.columns:

            df[column] = sap_number(
                df[column]
            )

    # Billing date has priority.
    date_column = find_column(
        df,
        [
            "FKDAT",
        ]
    )

    if date_column:

        df = add_daily_time_columns(
            df,
            date_column
        )

    return df


# ============================================================
# VBAK
# ============================================================

def prepare_vbak(df):

    if df is None:
        return None

    df = df.copy()

    if "NETWR" in df.columns:

        df["NETWR"] = sap_number(
            df["NETWR"]
        )

    date_column = find_column(
        df,
        [
            "AUDAT",
        ]
    )

    if date_column:

        df = add_daily_time_columns(
            df,
            date_column
        )

    return df


# ============================================================
# LIKP
# ============================================================

def prepare_likp(df):

    if df is None:
        return None

    df = df.copy()

    for column in [
        "NTGEW",
        "BRGEW",
        "VOLUM",
    ]:

        if column in df.columns:

            df[column] = sap_number(
                df[column]
            )

    date_column = find_column(
        df,
        [
            "WADAT_IST",
            "WADAT",
        ]
    )

    if date_column:

        df = add_daily_time_columns(
            df,
            date_column
        )

    return df


# ============================================================
# LOAD TABLES
# ============================================================

def load_all_tables():

    tables = []

    loaded_data = {}

    for table_name in TABLES:

        path = find_table_file(
            table_name
        )

        if path is None:

            tables.append({
                "Table": table_name,
                "Status": "Missing",
                "Rows": 0,
                "File": "",
            })

            continue

        try:

            df = read_sap_file(
                path
            )

            loaded_data[
                table_name
            ] = df

            tables.append({
                "Table": table_name,
                "Status": "Loaded",
                "Rows": len(df),
                "File": path.name,
            })

        except Exception as error:

            tables.append({
                "Table": table_name,
                "Status": "Error",
                "Rows": 0,
                "File": path.name,
                "Error": str(error),
            })

    return (
        loaded_data,
        pd.DataFrame(tables)
    )


# ============================================================
# PREPARE
# ============================================================

def prepare_tables(tables):

    prepared = {}

    for table_name, df in tables.items():

        if table_name == "VBRP":

            prepared[
                table_name
            ] = prepare_vbrp(df)

        elif table_name == "VBRK":

            prepared[
                table_name
            ] = prepare_vbrk(df)

        elif table_name == "VBAK":

            prepared[
                table_name
            ] = prepare_vbak(df)

        elif table_name == "LIKP":

            prepared[
                table_name
            ] = prepare_likp(df)

        else:

            prepared[
                table_name
            ] = df.copy()

    return prepared