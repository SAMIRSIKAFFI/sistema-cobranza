import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Sistema Integral de Cobranza", layout="wide")

st.title("⚖️ Sistema Profesional de Cobranza")

# ---------------------------------------------------
# FUNCION LIMPIAR COLUMNAS
# ---------------------------------------------------

def limpiar_columnas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    return df


# ---------------------------------------------------
# CARGA ARCHIVOS PRINCIPALES
# ---------------------------------------------------

archivo_deuda = st.file_uploader("📂 Subir Archivo Deuda", type=["xlsx"])
archivo_pagos = st.file_uploader("📂 Subir Archivo Pagos", type=["xlsx"])

if archivo_deuda and archivo_pagos:

    df_deuda = pd.read_excel(archivo_deuda)
    df_deuda = limpiar_columnas(df_deuda)

    df_pagos = pd.read_excel(archivo_pagos)
    df_pagos = limpiar_columnas(df_pagos)

    # Normalización básica
    # Detectar columna ID en deuda
if "ID_COBRANZA" in df_deuda.columns:
    col_id_deuda = "ID_COBRANZA"
elif "CODIGO" in df_deuda.columns:
    col_id_deuda = "CODIGO"
else:
    st.error("No se encontró columna ID_COBRANZA o CODIGO en archivo Deuda")
    st.write("Columnas detectadas:", df_deuda.columns.tolist())
    st.stop()

# Detectar columna ID en pagos
if "ID_COBRANZA" in df_pagos.columns:
    col_id_pago = "ID_COBRANZA"
elif "CODIGO" in df_pagos.columns:
    col_id_pago = "CODIGO"
else:
    st.error("No se encontró columna ID_COBRANZA o CODIGO en archivo Pagos")
    st.write("Columnas detectadas:", df_pagos.columns.tolist())
    st.stop()

df_deuda[col_id_deuda] = df_deuda[col_id_deuda].astype(str)
df_pagos[col_id_pago] = df_pagos[col_id_pago].astype(str)

df_deuda["IMPORTE"] = pd.to_numeric(df_deuda["IMPORTE"], errors="coerce").fillna(0)
df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

# Cruce dinámico
df = df_deuda.merge(
    df_pagos,
    left_on=col_id_deuda,
    right_on=col_id_pago,
    how="left",
    suffixes=("_DEUDA", "_PAGO")
)


    df_deuda["IMPORTE"] = pd.to_numeric(df_deuda["IMPORTE"], errors="coerce").fillna(0)
    df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

    # Cruce
    df = df_deuda.merge(
        df_pagos,
        on="ID_COBRANZA",
        how="left",
        suffixes=("_DEUDA", "_PAGO")
    )

    df["IMPORTE_PAGO"] = df["IMPORTE_PAGO"].fillna(0)
    df["PENDIENTE"] = df["IMPORTE_DEUDA"] - df["IMPORTE_PAGO"]

    # Dashboard Ejecutivo
    st.subheader("📊 Dashboard Ejecutivo")

    col1, col2, col3 = st.columns(3)

    col1.metric("💰 Total Deuda", f"{df['IMPORTE_DEUDA'].sum():,.2f}")
    col2.metric("💵 Total Pagado", f"{df['IMPORTE_PAGO'].sum():,.2f}")
    col3.metric("⚠ Total Pendiente", f"{df['PENDIENTE'].sum():,.2f}")

    st.bar_chart(df.groupby("TIPO")["PENDIENTE"].sum())

# ---------------------------------------------------
# MODULO SMS MASIVO
# ---------------------------------------------------

st.markdown("---")
st.header("📲 Módulo Generador Masivo de SMS")

archivo_suscriptor = st.file_uploader(
    "📂 Subir Base Suscriptor (SMS)",
    type=["xlsx"],
    key="sms"
)

if archivo_suscriptor and archivo_pagos:

    df_suscriptor = pd.read_excel(archivo_suscriptor)
    df_suscriptor = limpiar_columnas(df_suscriptor)

    df_pagos_sms = pd.read_excel(archivo_pagos)
    df_pagos_sms = limpiar_columnas(df_pagos_sms)

    # Validar columnas necesarias
    columnas_requeridas = ["CODIGO", "TIPO", "NUMERO", "NOMBRE", "FECHA", "MONTO"]

    for col in columnas_requeridas:
        if col not in df_suscriptor.columns:
            st.error(f"❌ Falta columna '{col}' en Base Suscriptor")
            st.write("Columnas detectadas:", df_suscriptor.columns.tolist())
            st.stop()

    # Crear PERIODO desde FECHA
    df_suscriptor["FECHA"] = pd.to_datetime(df_suscriptor["FECHA"], dayfirst=True)
    df_suscriptor["PERIODO"] = df_suscriptor["FECHA"].dt.strftime("%Y-%m")

    df_suscriptor["CODIGO"] = df_suscriptor["CODIGO"].astype(str)
    df_suscriptor["TIPO"] = df_suscriptor["TIPO"].astype(str)

    df_pagos_sms["ID_COBRANZA"] = df_pagos_sms["ID_COBRANZA"].astype(str)
    df_pagos_sms["PERIODO"] = df_pagos_sms["PERIODO"].astype(str)

    # Selección múltiple periodos
    periodos = sorted(df_suscriptor["PERIODO"].unique())

    periodos_sel = st.multiselect(
        "📅 Seleccionar PERÍODOS",
        periodos,
        default=periodos[:1]
    )

    # Selección tipo
    tipos = sorted(df_suscriptor["TIPO"].unique())

    tipos_sel = st.multiselect(
        "📌 Seleccionar TIPO",
        tipos,
        default=tipos
    )

    cantidad_archivos = st.number_input(
        "📁 Cantidad de archivos CSV",
        min_value=1,
        max_value=50,
        value=10
    )

    depurar = st.checkbox("☑ Depurar pagos automáticamente", value=True)

    if st.button("🚀 Generar Archivos SMS"):

        df_filtrado = df_suscriptor[
            (df_suscriptor["PERIODO"].isin(periodos_sel)) &
            (df_suscriptor["TIPO"].isin(tipos_sel))
        ].copy()

        if depurar and periodos_sel:

            pagos_filtrados = df_pagos_sms[
                (df_pagos_sms["PERIODO"].isin(periodos_sel)) &
                (df_pagos_sms["IMPORTE"] > 0)
            ]

            codigos_pagados = pagos_filtrados["ID_COBRANZA"].unique()

            df_filtrado = df_filtrado[
                ~df_filtrado["CODIGO"].isin(codigos_pagados)
            ]

        total = len(df_filtrado)

        if total == 0:
            st.warning("No existen registros para generar archivos.")
        else:

            st.success(f"Total registros a enviar: {total}")

            tamaño = total // cantidad_archivos + 1

            for i in range(cantidad_archivos):

                inicio = i * tamaño
                fin = inicio + tamaño

                df_parte = df_filtrado.iloc[inicio:fin]

                if not df_parte.empty:

                    csv = df_parte[
                        ["NUMERO", "NOMBRE", "FECHA", "CODIGO", "MONTO", "TIPO"]
                    ].to_csv(index=False)

                    st.download_button(
                        label=f"📥 Descargar SMS_{i+1}",
                        data=csv,
                        file_name=f"SMS_{i+1}.csv",
                        mime="text/csv"
                    )


