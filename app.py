import streamlit as st
import pandas as pd
import io
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="SISTEMA DE COBRANZA - RESULTADOS", layout="wide")

st.sidebar.title("SISTEMA DE COBRANZA - RESULTADOS")

menu = st.sidebar.radio(
    "MENÚ PRINCIPAL",
    [
        "📊 Dashboard Cruce Deuda vs Pagos",
        "📲 GENERADOR DE SMS",
        "🚧 Módulo Histórico (En Desarrollo)"
    ]
)

# ==========================================================
# MODULO 1 - CRUCE DEUDA VS PAGOS (NO MODIFICADO)
# ==========================================================

def modulo_cruce():

    st.title("⚖️ Sistema Profesional de Gestión de Cobranza")

    def limpiar_columnas(df):
        df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
        return df

    if "df_deuda_base" not in st.session_state:
        st.session_state.df_deuda_base = None

    if st.session_state.df_deuda_base is None:

        archivo_deuda = st.file_uploader(
            "📂 Subir archivo CARTERA / DEUDA",
            type=["xlsx"]
        )

        if archivo_deuda:

            df_deuda = limpiar_columnas(pd.read_excel(archivo_deuda))

            columnas_deuda = {"ID_COBRANZA", "PERIODO", "DEUDA", "TIPO"}

            if not columnas_deuda.issubset(df_deuda.columns):
                st.error("Estructura incorrecta en CARTERA.")
                return

            df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
            df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)
            df_deuda["DEUDA"] = pd.to_numeric(df_deuda["DEUDA"], errors="coerce").fillna(0)

            st.session_state.df_deuda_base = df_deuda
            st.success("Cartera cargada.")
            st.rerun()

        return

    else:
        st.success("Cartera en memoria.")
        if st.button("Reemplazar Cartera"):
            st.session_state.df_deuda_base = None
            st.rerun()

    archivo_pagos = st.file_uploader("💵 Subir archivo PAGOS", type=["xlsx"])

    if not archivo_pagos:
        return

    df_deuda = st.session_state.df_deuda_base.copy()
    df_pagos = limpiar_columnas(pd.read_excel(archivo_pagos))

    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
    df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

    pagos = df_pagos.groupby(["ID_COBRANZA", "PERIODO"])["IMPORTE"].sum().reset_index()
    pagos.rename(columns={"IMPORTE": "TOTAL_PAGADO"}, inplace=True)

    resultado = df_deuda.merge(
        pagos,
        on=["ID_COBRANZA", "PERIODO"],
        how="left"
    )

    resultado["TOTAL_PAGADO"] = resultado["TOTAL_PAGADO"].fillna(0)
    resultado["ESTADO"] = resultado.apply(
        lambda r: "PAGADO" if r["TOTAL_PAGADO"] >= r["DEUDA"] else "PENDIENTE",
        axis=1
    )

    pendientes = resultado[resultado["ESTADO"] == "PENDIENTE"]

    st.subheader("Pendientes")
    st.dataframe(pendientes)


# ==========================================================
# MODULO 2 - GENERADOR DE SMS PROFESIONAL
# ==========================================================

def modulo_sms():

    st.title("📲 GENERADOR PROFESIONAL DE SMS")

    def limpiar_columnas(df):
        df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
        return df

    archivo_suscriptor = st.file_uploader("📂 BASE POR SUSCRIPTOR", type=["xlsx"])
    archivo_pagos = st.file_uploader("💵 BASE DE PAGOS", type=["xlsx"])

    if not archivo_suscriptor or not archivo_pagos:
        return

    df_suscriptor = limpiar_columnas(pd.read_excel(archivo_suscriptor))
    df_pagos = limpiar_columnas(pd.read_excel(archivo_pagos))

    # Normalizar
    df_suscriptor["CODIGO"] = df_suscriptor["CODIGO"].astype(str)
    df_suscriptor["MONTO"] = pd.to_numeric(df_suscriptor["MONTO"], errors="coerce").fillna(0)
    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)

    # ===============================
    # LOGICA POR PERIODOS
    # ===============================

    pagos_periodos = df_pagos.groupby("ID_COBRANZA")["PERIODO"].nunique().reset_index()
    pagos_periodos.rename(columns={"PERIODO": "PERIODOS_PAGADOS"}, inplace=True)

    periodos_totales = df_suscriptor.groupby("CODIGO")["FECHA"].count().reset_index()
    periodos_totales.rename(columns={"FECHA": "PERIODOS_TOTALES"}, inplace=True)

    df_control = periodos_totales.merge(
        pagos_periodos,
        left_on="CODIGO",
        right_on="ID_COBRANZA",
        how="left"
    )

    df_control["PERIODOS_PAGADOS"] = df_control["PERIODOS_PAGADOS"].fillna(0)

    df_control["PERIODOS_PENDIENTES"] = (
        df_control["PERIODOS_TOTALES"] - df_control["PERIODOS_PAGADOS"]
    )

    # Opciones estratégicas
    st.subheader("Configuración de Gestión")

    gestionar_parciales = st.checkbox(
        "Gestionar clientes que pagaron 1 o más periodos pero aún tienen pendientes",
        value=True
    )

    # ===============================
    # FILTRO SEGUN DECISION
    # ===============================

    if gestionar_parciales:
        codigos_validos = df_control[df_control["PERIODOS_PENDIENTES"] > 0]["CODIGO"]
    else:
        codigos_validos = df_control[df_control["PERIODOS_PAGADOS"] == 0]["CODIGO"]

    df_final = df_suscriptor[df_suscriptor["CODIGO"].isin(codigos_validos)]

    # ===============================
    # FECHA EDITABLE
    # ===============================

    fecha_sms = st.text_input(
        "Fecha formato largo (Ej: sábado, 14 de febrero de 2026)"
    )

    if fecha_sms:
        df_final["FECHA"] = fecha_sms

    # ===============================
    # ESTRUCTURA FINAL CSV
    # ===============================

    df_export = df_final[["NUMERO", "NOMBRE", "FECHA", "CODIGO", "MONTO"]].copy()

    # ===============================
    # DIVISION DE ARCHIVOS
    # ===============================

    partes = st.number_input("Cantidad de archivos CSV", min_value=1, value=1)
    prefijo = st.text_input("Prefijo archivos", value="SMS")

    st.subheader("Vista previa final")
    st.dataframe(df_export)

    if st.button("Generar Archivos CSV"):

        if df_export.empty:
            st.warning("No existen registros para exportar.")
            return

        tamaño = len(df_export) // partes + 1

        for i in range(partes):

            inicio = i * tamaño
            fin = inicio + tamaño
            df_parte = df_export.iloc[inicio:fin]

            if df_parte.empty:
                continue

            csv = df_parte.to_csv(
                index=False,
                sep=",",
                encoding="utf-8-sig"
            )

            st.download_button(
                label=f"Descargar {prefijo}_{i+1}.csv",
                data=csv,
                file_name=f"{prefijo}_{i+1}.csv",
                mime="text/csv"
            )

        st.success("Archivos CSV generados correctamente.")


# ==========================================================
# EJECUCION
# ==========================================================

if menu == "📊 Dashboard Cruce Deuda vs Pagos":
    modulo_cruce()

elif menu == "📲 GENERADOR DE SMS":
    modulo_sms()

elif menu == "🚧 Módulo Histórico (En Desarrollo)":
    st.title("Módulo Histórico en construcción")
