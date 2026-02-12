import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema Integral de Cobranza", layout="wide")

st.title("⚖️ Sistema Profesional de Cobranza")

# ===================================================
# FUNCION LIMPIAR COLUMNAS
# ===================================================

def limpiar_columnas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    return df


# ===================================================
# MODULO 1 - DASHBOARD DEUDA VS PAGOS (INDEPENDIENTE)
# ===================================================

st.header("📊 Módulo 1 - Dashboard Ejecutivo")

archivo_deuda = st.file_uploader("Subir Archivo DEUDA", type=["xlsx"], key="deuda")
archivo_pagos = st.file_uploader("Subir Archivo PAGOS", type=["xlsx"], key="pagos")

if archivo_deuda is not None and archivo_pagos is not None:

    df_deuda = limpiar_columnas(pd.read_excel(archivo_deuda))
    df_pagos = limpiar_columnas(pd.read_excel(archivo_pagos))

    if not all(col in df_deuda.columns for col in ["ID_COBRANZA", "DEUDA", "TIPO"]):
        st.error("Archivo DEUDA debe contener: ID_COBRANZA, DEUDA, TIPO")
    elif not all(col in df_pagos.columns for col in ["ID_COBRANZA", "IMPORTE"]):
        st.error("Archivo PAGOS debe contener: ID_COBRANZA, IMPORTE")
    else:

        df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
        df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)

        df_deuda["DEUDA"] = pd.to_numeric(df_deuda["DEUDA"], errors="coerce").fillna(0)
        df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

        pagos_resumen = df_pagos.groupby("ID_COBRANZA")["IMPORTE"].sum().reset_index()

        df = df_deuda.merge(pagos_resumen, on="ID_COBRANZA", how="left")
        df["IMPORTE"] = df["IMPORTE"].fillna(0)
        df["PENDIENTE"] = df["DEUDA"] - df["IMPORTE"]

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Deuda", f"{df['DEUDA'].sum():,.2f}")
        col2.metric("Total Pagado", f"{df['IMPORTE'].sum():,.2f}")
        col3.metric("Total Pendiente", f"{df['PENDIENTE'].sum():,.2f}")

        st.bar_chart(df.groupby("TIPO")["PENDIENTE"].sum())


# ===================================================
# MODULO 2 - GENERADOR MASIVO SMS (INDEPENDIENTE)
# ===================================================

st.markdown("---")
st.header("📲 Módulo 2 - Generador Masivo SMS")

archivo_suscriptor = st.file_uploader(
    "Subir Base Suscriptor (SMS)",
    type=["xlsx"],
    key="suscriptor"
)

archivo_pagos_sms = st.file_uploader(
    "Subir Archivo PAGOS (opcional para depuración)",
    type=["xlsx"],
    key="pagos_sms"
)

if archivo_suscriptor is not None:

    df_suscriptor = limpiar_columnas(pd.read_excel(archivo_suscriptor))

    columnas_sms = ["CODIGO", "TIPO", "NUMERO", "NOMBRE", "FECHA", "MONTO"]

    if not all(col in df_suscriptor.columns for col in columnas_sms):
        st.error("La Base Suscriptor debe contener: CODIGO, TIPO, NUMERO, NOMBRE, FECHA, MONTO")
    else:

        # Conversión segura de FECHA
        df_suscriptor["FECHA"] = pd.to_datetime(
            df_suscriptor["FECHA"],
            errors="coerce",
            dayfirst=True
        )

        # Si no se pudo convertir fecha, mostrar advertencia
        if df_suscriptor["FECHA"].isna().all():
            st.warning("No se pudieron interpretar las fechas. Se usará el valor original como período.")
            df_suscriptor["PERIODO"] = df_suscriptor["FECHA"].astype(str)
        else:
            df_suscriptor["PERIODO"] = df_suscriptor["FECHA"].dt.strftime("%Y-%m")

        df_suscriptor["CODIGO"] = df_suscriptor["CODIGO"].astype(str)
        df_suscriptor["TIPO"] = df_suscriptor["TIPO"].astype(str)

        # Filtros dinámicos
        periodos = sorted(df_suscriptor["PERIODO"].dropna().unique())
        tipos = sorted(df_suscriptor["TIPO"].dropna().unique())

        periodos_sel = st.multiselect("Seleccionar PERÍODOS", periodos)
        tipos_sel = st.multiselect("Seleccionar TIPO", tipos, default=tipos)

        cantidad_archivos = st.number_input("Cantidad de archivos CSV", 1, 50, 10)
        depurar = st.checkbox("Depurar pagos automáticamente")

        if st.button("Generar Archivos SMS"):

            df_filtrado = df_suscriptor.copy()

            if periodos_sel:
                df_filtrado = df_filtrado[df_filtrado["PERIODO"].isin(periodos_sel)]

            if tipos_sel:
                df_filtrado = df_filtrado[df_filtrado["TIPO"].isin(tipos_sel)]

            # Depuración opcional
            if depurar and archivo_pagos_sms is not None:

                df_pagos_sms = limpiar_columnas(pd.read_excel(archivo_pagos_sms))

                if all(col in df_pagos_sms.columns for col in ["ID_COBRANZA", "IMPORTE"]):

                    df_pagos_sms["ID_COBRANZA"] = df_pagos_sms["ID_COBRANZA"].astype(str)
                    df_pagos_sms["IMPORTE"] = pd.to_numeric(
                        df_pagos_sms["IMPORTE"], errors="coerce"
                    ).fillna(0)

                    codigos_pagados = df_pagos_sms[
                        df_pagos_sms["IMPORTE"] > 0
                    ]["ID_COBRANZA"].unique()

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
                            label=f"Descargar SMS_{i+1}",
                            data=csv,
                            file_name=f"SMS_{i+1}.csv",
                            mime="text/csv"
                        )
