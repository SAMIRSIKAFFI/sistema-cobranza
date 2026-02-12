import streamlit as st
import pandas as pd

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
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


# ---------------------------------------------------
# CARGA ARCHIVOS DEUDA Y PAGOS
# ---------------------------------------------------

archivo_deuda = st.file_uploader("📂 Subir Archivo DEUDA", type=["xlsx"])
archivo_pagos = st.file_uploader("📂 Subir Archivo PAGOS", type=["xlsx"])

if archivo_deuda is not None and archivo_pagos is not None:

    df_deuda = pd.read_excel(archivo_deuda)
    df_deuda = limpiar_columnas(df_deuda)

    df_pagos = pd.read_excel(archivo_pagos)
    df_pagos = limpiar_columnas(df_pagos)

    # Validaciones archivo DEUDA
    columnas_deuda = ["ID_COBRANZA", "DEUDA", "TIPO"]
    for col in columnas_deuda:
        if col not in df_deuda.columns:
            st.error(f"❌ Falta columna '{col}' en archivo DEUDA")
            st.write("Columnas detectadas:", df_deuda.columns.tolist())
            st.stop()

    # Validaciones archivo PAGOS
    columnas_pagos = ["ID_COBRANZA", "IMPORTE"]
    for col in columnas_pagos:
        if col not in df_pagos.columns:
            st.error(f"❌ Falta columna '{col}' en archivo PAGOS")
            st.write("Columnas detectadas:", df_pagos.columns.tolist())
            st.stop()

    # Normalización tipos
    df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)

    df_deuda["DEUDA"] = pd.to_numeric(df_deuda["DEUDA"], errors="coerce").fillna(0)
    df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

    # Agrupar pagos por ID_COBRANZA
    pagos_resumen = df_pagos.groupby("ID_COBRANZA")["IMPORTE"].sum().reset_index()

    # Cruce
    df = df_deuda.merge(
        pagos_resumen,
        on="ID_COBRANZA",
        how="left"
    )

    df["IMPORTE"] = df["IMPORTE"].fillna(0)
    df["PENDIENTE"] = df["DEUDA"] - df["IMPORTE"]

    # ---------------------------------------------------
    # DASHBOARD EJECUTIVO
    # ---------------------------------------------------

    st.subheader("📊 Dashboard Ejecutivo")

    col1, col2, col3 = st.columns(3)

    col1.metric("💰 Total Deuda", f"{df['DEUDA'].sum():,.2f}")
    col2.metric("💵 Total Pagado", f"{df['IMPORTE'].sum():,.2f}")
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

if archivo_suscriptor is not None and archivo_pagos is not None:

    df_suscriptor = pd.read_excel(archivo_suscriptor)
    df_suscriptor = limpiar_columnas(df_suscriptor)

    df_pagos_sms = pd.read_excel(archivo_pagos)
    df_pagos_sms = limpiar_columnas(df_pagos_sms)

    columnas_sms = ["CODIGO", "TIPO", "NUMERO", "NOMBRE", "FECHA", "MONTO"]

    for col in columnas_sms:
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
    df_pagos_sms["IMPORTE"] = pd.to_numeric(df_pagos_sms["IMPORTE"], errors="coerce").fillna(0)

    periodos = sorted(df_suscriptor["PERIODO"].unique())
    tipos = sorted(df_suscriptor["TIPO"].unique())

    periodos_sel = st.multiselect("📅 Seleccionar PERÍODOS", periodos)
    tipos_sel = st.multiselect("📌 Seleccionar TIPO", tipos, default=tipos)

    cantidad_archivos = st.number_input("📁 Cantidad de archivos CSV", 1, 50, 10)
    depurar = st.checkbox("☑ Depurar pagos automáticamente", value=True)

    if st.button("🚀 Generar Archivos SMS"):

        df_filtrado = df_suscriptor[
            (df_suscriptor["PERIODO"].isin(periodos_sel)) &
            (df_suscriptor["TIPO"].isin(tipos_sel))
        ].copy()

        if depurar:
            codigos_pagados = df_pagos_sms[df_pagos_sms["IMPORTE"] > 0]["ID_COBRANZA"].unique()
            df_filtrado = df_filtrado[~df_filtrado["CODIGO"].isin(codigos_pagados)]

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
