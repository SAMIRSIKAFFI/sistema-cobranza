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
# MODULO 1 - CRUCE DEUDA VS PAGOS
# ==========================================================

def modulo_cruce():

    st.title("⚖️ Sistema Profesional de Gestión de Cobranza")
    st.markdown("### 📊 Dashboard Ejecutivo de Recuperación")

    def limpiar_columnas(df):
        df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
        return df

    if "df_deuda_base" not in st.session_state:
        st.session_state.df_deuda_base = None

    if st.session_state.df_deuda_base is None:

        archivo_deuda = st.file_uploader(
            "📂 Subir archivo CARTERA / DEUDA (Se cargará una sola vez)",
            type=["xlsx"]
        )

        if archivo_deuda:

            df_deuda = pd.read_excel(archivo_deuda)
            df_deuda = limpiar_columnas(df_deuda)

            columnas_deuda = {"ID_COBRANZA", "PERIODO", "DEUDA", "TIPO"}

            if not columnas_deuda.issubset(df_deuda.columns):
                st.error("El archivo CARTERA no tiene las columnas obligatorias.")
                return

            df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
            df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)
            df_deuda["DEUDA"] = pd.to_numeric(df_deuda["DEUDA"], errors="coerce").fillna(0)

            st.session_state.df_deuda_base = df_deuda

            st.success("✅ Cartera cargada correctamente y guardada en memoria.")
            st.rerun()

        return

    else:
        st.success("📁 Cartera base cargada en memoria.")

        if st.button("🔄 Reemplazar Cartera"):
            st.session_state.df_deuda_base = None
            st.rerun()

    archivo_pagos = st.file_uploader(
        "💵 Subir archivo PAGOS (Puede actualizarse constantemente)",
        type=["xlsx"]
    )

    if not archivo_pagos:
        return

    df_deuda = st.session_state.df_deuda_base.copy()
    df_pagos = pd.read_excel(archivo_pagos)

    df_pagos = limpiar_columnas(df_pagos)

    columnas_pagos = {"ID_COBRANZA", "PERIODO", "IMPORTE"}

    if not columnas_pagos.issubset(df_pagos.columns):
        st.error("El archivo PAGOS no tiene las columnas obligatorias.")
        return

    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
    df_pagos["PERIODO"] = df_pagos["PERIODO"].astype(str)
    df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

    pagos_resumen = df_pagos.groupby(
        ["ID_COBRANZA", "PERIODO"]
    )["IMPORTE"].sum().reset_index()

    pagos_resumen.rename(columns={"IMPORTE": "TOTAL_PAGADO"}, inplace=True)

    resultado = df_deuda.merge(
        pagos_resumen,
        on=["ID_COBRANZA", "PERIODO"],
        how="left"
    )

    resultado["TOTAL_PAGADO"] = resultado["TOTAL_PAGADO"].fillna(0)

    resultado["ESTADO"] = resultado.apply(
        lambda row: "PAGADO" if row["TOTAL_PAGADO"] >= row["DEUDA"] else "PENDIENTE",
        axis=1
    )

    pendientes = resultado[resultado["ESTADO"] == "PENDIENTE"]

    total_deuda = resultado["DEUDA"].sum()
    total_pagado = resultado["TOTAL_PAGADO"].sum()
    total_pendiente = pendientes["DEUDA"].sum()

    porcentaje_recuperacion = 0
    if total_deuda > 0:
        porcentaje_recuperacion = (total_pagado / total_deuda) * 100

    st.success("Cruce realizado correctamente")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("💼 Total Cartera", f"Bs. {total_deuda:,.2f}")
    col2.metric("💰 Total Pagado", f"Bs. {total_pagado:,.2f}")
    col3.metric("⚠️ Total Pendiente", f"Bs. {total_pendiente:,.2f}")
    col4.metric("📈 % Recuperación", f"{porcentaje_recuperacion:.2f}%")

    resumen_tipo = pendientes.groupby("TIPO")["DEUDA"].sum().reset_index()
    resumen_periodo = pendientes.groupby("PERIODO")["DEUDA"].sum().reset_index()
    pagos_por_periodo = pagos_resumen.groupby("PERIODO")["TOTAL_PAGADO"].sum().reset_index()

    st.subheader("📊 Deuda Pendiente por TIPO")
    if not resumen_tipo.empty:
        st.bar_chart(resumen_tipo.set_index("TIPO"))

    st.subheader("📆 Deuda Pendiente por PERIODO")
    if not resumen_periodo.empty:
        st.line_chart(resumen_periodo.set_index("PERIODO"))

    st.subheader("💵 Pagos por PERIODO")
    if not pagos_por_periodo.empty:
        st.line_chart(pagos_por_periodo.set_index("PERIODO"))

    top_morosos = pendientes.groupby("ID_COBRANZA")["DEUDA"].sum().reset_index()
    top_morosos = top_morosos.sort_values(by="DEUDA", ascending=False).head(10)

    st.subheader("🏆 Top 10 Mayores Deudores")
    st.dataframe(top_morosos)

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        resultado.to_excel(writer, sheet_name="RESULTADO_GENERAL", index=False)
        resumen_tipo.to_excel(writer, sheet_name="RESUMEN_TIPO", index=False)
        resumen_periodo.to_excel(writer, sheet_name="RESUMEN_PERIODO", index=False)
        pagos_por_periodo.to_excel(writer, sheet_name="PAGOS_POR_PERIODO", index=False)
        pendientes.to_excel(writer, sheet_name="PENDIENTES_TOTALES", index=False)

    st.download_button(
        label="📥 Descargar Reporte Financiero Profesional",
        data=output.getvalue(),
        file_name="reporte_financiero_cobranza.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ==========================================================
# MODULO 2 - GENERADOR DE SMS
# ==========================================================

def modulo_sms():

    st.title("📲 GENERADOR PROFESIONAL DE SMS")

    def limpiar_columnas(df):
        df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
        return df

    archivo_suscriptor = st.file_uploader("📂 Cargar BASE POR SUSCRIPTOR", type=["xlsx"])
    archivo_pagos = st.file_uploader("💵 Cargar BASE DE PAGOS", type=["xlsx"])

    if not archivo_suscriptor or not archivo_pagos:
        return

    df_suscriptor = limpiar_columnas(pd.read_excel(archivo_suscriptor))
    df_pagos = limpiar_columnas(pd.read_excel(archivo_pagos))

    df_suscriptor["CODIGO"] = df_suscriptor["CODIGO"].astype(str)
    df_suscriptor["MONTO"] = pd.to_numeric(df_suscriptor["MONTO"], errors="coerce").fillna(0)
    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
    df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

    pagos_totales = df_pagos.groupby("ID_COBRANZA")["IMPORTE"].sum().reset_index()
    pagos_totales.rename(columns={"IMPORTE": "TOTAL_PAGADO"}, inplace=True)

    df_final = df_suscriptor.merge(
        pagos_totales,
        left_on="CODIGO",
        right_on="ID_COBRANZA",
        how="left"
    )

    df_final["TOTAL_PAGADO"] = df_final["TOTAL_PAGADO"].fillna(0)

    df_final = df_final[df_final["TOTAL_PAGADO"] < df_final["MONTO"]]

    st.subheader("Vista previa final")
    st.dataframe(df_final)

    partes = st.number_input("Cantidad de archivos CSV", min_value=1, value=1)
    prefijo = st.text_input("Prefijo archivos", value="SMS")

    if st.button("Generar CSV"):

        if df_final.empty:
            st.warning("No existen registros.")
            return

        tamaño = len(df_final) // partes + 1

        for i in range(partes):
            inicio = i * tamaño
            fin = inicio + tamaño
            df_parte = df_final.iloc[inicio:fin]

            if df_parte.empty:
                continue

            csv = df_parte.to_csv(index=False, encoding="utf-8-sig")

            st.download_button(
                label=f"Descargar {prefijo}_{i+1}.csv",
                data=csv,
                file_name=f"{prefijo}_{i+1}.csv",
                mime="text/csv"
            )


# ==========================================================
# EJECUCIÓN
# ==========================================================

if menu == "📊 Dashboard Cruce Deuda vs Pagos":
    modulo_cruce()

elif menu == "📲 GENERADOR DE SMS":
    modulo_sms()

elif menu == "🚧 Módulo Histórico (En Desarrollo)":
    st.title("📈 Histórico")
    st.info("Aquí construiremos el dashboard acumulado mensual.")
