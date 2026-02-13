import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="SISTEMA DE COBRANZA - RESULTADOS", layout="wide")

# =====================================================
# INICIALIZAR MEMORIA
# =====================================================

if "df_deuda" not in st.session_state:
    st.session_state.df_deuda = None

# =====================================================
# FUNCIONES
# =====================================================

def normalizar_columnas(df):
    df.columns = df.columns.str.strip().str.upper()
    return df


def preparar_deuda(df):
    df = normalizar_columnas(df)

    columnas_requeridas = ["ID_CLIENTE", "NOMBRE_CLIENTE", "ID_COBRANZA", "PERIODO", "DEUDA"]

    if not all(col in df.columns for col in columnas_requeridas):
        st.error(f"El archivo CARTERA debe contener columnas: {columnas_requeridas}")
        return None

    df = df[columnas_requeridas].copy()

    df["ID_COBRANZA"] = df["ID_COBRANZA"].astype(str)
    df["PERIODO"] = df["PERIODO"].astype(str)
    df["DEUDA"] = pd.to_numeric(df["DEUDA"], errors="coerce").fillna(0)

    return df


def preparar_pagos(df):
    df = normalizar_columnas(df)

    columnas_requeridas = ["ID_COBRANZA", "FECHA", "MONTO"]

    if not all(col in df.columns for col in columnas_requeridas):
        st.error(f"El archivo PAGOS debe contener columnas: {columnas_requeridas}")
        return None

    df = df[columnas_requeridas].copy()

    df["ID_COBRANZA"] = df["ID_COBRANZA"].astype(str)
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
    df["PERIODO"] = df["FECHA"].dt.strftime("%Y-%m")
    df["MONTO"] = pd.to_numeric(df["MONTO"], errors="coerce").fillna(0)

    df = df.groupby(["ID_COBRANZA", "PERIODO"], as_index=False)["MONTO"].sum()

    return df


def generar_csv_excel(df):
    df_export = df.copy()

    # Formatear monto con coma decimal
    df_export["MONTO"] = df_export["MONTO"].map(
        lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    buffer = StringIO()

    df_export.to_csv(
        buffer,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    return buffer.getvalue()


# =====================================================
# INTERFAZ
# =====================================================

st.title("SISTEMA DE COBRANZA - RESULTADOS")

menu = st.sidebar.radio(
    "MENÚ PRINCIPAL",
    ["Cargar Cartera", "Cruce Deuda vs Pagos", "Exportar Resultados"]
)

# =====================================================
# CARGAR CARTERA
# =====================================================

if menu == "Cargar Cartera":

    st.header("Cargar Base de Cartera / Deuda")

    archivo_deuda = st.file_uploader("Subir archivo CARTERA", type=["xlsx", "xls", "csv"])

    if archivo_deuda is not None:

        if archivo_deuda.name.endswith(".csv"):
            df = pd.read_csv(archivo_deuda)
        else:
            df = pd.read_excel(archivo_deuda)

        df_preparado = preparar_deuda(df)

        if df_preparado is not None:
            st.session_state.df_deuda = df_preparado
            st.success("Cartera cargada correctamente y guardada en memoria.")
            st.dataframe(df_preparado.head())

# =====================================================
# CRUCE
# =====================================================

elif menu == "Cruce Deuda vs Pagos":

    st.header("Cruce Deuda vs Pagos")

    if st.session_state.df_deuda is None:
        st.warning("Primero debe cargar la CARTERA.")
    else:
        archivo_pagos = st.file_uploader("Subir archivo PAGOS", type=["xlsx", "xls", "csv"])

        if archivo_pagos is not None:

            if archivo_pagos.name.endswith(".csv"):
                df_pagos = pd.read_csv(archivo_pagos)
            else:
                df_pagos = pd.read_excel(archivo_pagos)

            pagos = preparar_pagos(df_pagos)

            if pagos is not None:

                df_deuda = st.session_state.df_deuda.copy()

                resultado = df_deuda.merge(
                    pagos,
                    on=["ID_COBRANZA", "PERIODO"],
                    how="left"
                )

                resultado["MONTO"] = resultado["MONTO"].fillna(0)
                resultado["SALDO"] = resultado["DEUDA"] - resultado["MONTO"]

                st.session_state.resultado = resultado

                st.success("Cruce realizado correctamente.")
                st.dataframe(resultado.head())

# =====================================================
# EXPORTAR
# =====================================================

elif menu == "Exportar Resultados":

    st.header("Exportar CSV para Excel")

    if "resultado" not in st.session_state:
        st.warning("Primero debe realizar el cruce.")
    else:

        df_export = st.session_state.resultado[
            ["ID_CLIENTE", "NOMBRE_CLIENTE", "ID_COBRANZA", "PERIODO", "DEUDA", "MONTO", "SALDO"]
        ]

        csv_final = generar_csv_excel(df_export)

        st.download_button(
            label="Descargar CSV listo para Excel",
            data=csv_final,
            file_name="reporte_cobranza.csv",
            mime="text/csv"
        )
