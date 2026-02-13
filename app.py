import streamlit as st
import pandas as pd
import io
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

# ============================================
# CONFIGURACIÓN GENERAL
# ============================================
st.set_page_config(
    page_title="Sistema Ejecutivo de Cobranza",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# ESTILO VISUAL CORPORATIVO
# ============================================
st.markdown("""
<style>
.main {
    background-color: #f4f6f9;
}
h1, h2, h3 {
    color: #1f2937;
}
.sidebar .sidebar-content {
    background-color: #111827;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# MENÚ PRINCIPAL
# ============================================
st.sidebar.title("⚖️ SISTEMA DE COBRANZA")
menu = st.sidebar.radio(
    "Menú Principal",
    [
        "📊 Dashboard Cobranza",
        "📈 Aging Report (Próximamente)",
        "🧾 Intereses (Próximamente)",
        "📄 Cartas Automáticas (Próximamente)",
        "⚙️ Configuración"
    ]
)

# ============================================
# FUNCIÓN LIMPIAR COLUMNAS
# ============================================
def limpiar_columnas(df):
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    return df

# ============================================
# 1️⃣ DASHBOARD PRINCIPAL
# ============================================
if menu == "📊 Dashboard Cobranza":

    st.title("📊 Dashboard Ejecutivo de Recuperación")

    archivo_deuda = st.file_uploader("📂 Subir archivo CARTERA / DEUDA", type=["xlsx"])
    archivo_pagos = st.file_uploader("📂 Subir archivo PAGOS", type=["xlsx"])

    if archivo_deuda and archivo_pagos:

        columnas_deuda_obligatorias = {"ID_COBRANZA", "PERIODO", "TIPO", "DEUDA"}
        columnas_pagos_obligatorias = {"ID_COBRANZA", "PERIODO", "IMPORTE"}

        df_deuda = limpiar_columnas(pd.read_excel(archivo_deuda))
        df_pagos = limpiar_columnas(pd.read_excel(archivo_pagos))

        if not columnas_deuda_obligatorias.issubset(df_deuda.columns):
            st.error("El archivo CARTERA no contiene las columnas obligatorias.")
            st.stop()

        if not columnas_pagos_obligatorias.issubset(df_pagos.columns):
            st.error("El archivo PAGOS no contiene las columnas obligatorias.")
            st.stop()

        df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
        df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)
        df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
        df_pagos["PERIODO"] = df_pagos["PERIODO"].astype(str)

        df_deuda["DEUDA"] = pd.to_numeric(df_deuda["DEUDA"], errors="coerce").fillna(0)
        df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

        pagos_resumen = (
            df_pagos
            .groupby(["ID_COBRANZA", "PERIODO"])["IMPORTE"]
            .sum()
            .reset_index()
            .rename(columns={"IMPORTE": "TOTAL_PAGADO"})
        )

        resultado = df_deuda.merge(
            pagos_resumen,
            on=["ID_COBRANZA", "PERIODO"],
            how="left"
        )

        resultado["TOTAL_PAGADO"] = resultado["TOTAL_PAGADO"].fillna(0)
        resultado["SALDO"] = resultado["DEUDA"] - resultado["TOTAL_PAGADO"]
        resultado["ESTADO"] = resultado["SALDO"].apply(
            lambda x: "PAGADO" if x <= 0 else "PENDIENTE"
        )

        pendientes = resultado[resultado["ESTADO"] == "PENDIENTE"]

        # ================= KPIs =================
        total_deuda = resultado["DEUDA"].sum()
        total_pagado = resultado["TOTAL_PAGADO"].sum()
        total_pendiente = pendientes["SALDO"].sum()
        porcentaje_recuperacion = (
            (total_pagado / total_deuda) * 100 if total_deuda > 0 else 0
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("💼 Total Cartera", f"Bs. {total_deuda:,.2f}")
        col2.metric("💰 Total Pagado", f"Bs. {total_pagado:,.2f}")
        col3.metric("⚠️ Total Pendiente", f"Bs. {total_pendiente:,.2f}")
        col4.metric("📈 % Recuperación", f"{porcentaje_recuperacion:.2f}%")

        # ================= GRÁFICOS =================
        resumen_tipo = pendientes.groupby("TIPO")["SALDO"].sum().reset_index()
        resumen_periodo = pendientes.groupby("PERIODO")["SALDO"].sum().reset_index()

        colA, colB = st.columns(2)

        with colA:
            st.subheader("📊 Deuda Pendiente por TIPO")
            st.bar_chart(resumen_tipo.set_index("TIPO"))

        with colB:
            st.subheader("📆 Deuda Pendiente por PERIODO")
            st.line_chart(resumen_periodo.set_index("PERIODO"))

        # ================= RANKING =================
        st.subheader("🏆 Top 10 Mayores Deudores")

        top_morosos = (
            pendientes
            .groupby("ID_COBRANZA")["SALDO"]
            .sum()
            .reset_index()
            .sort_values(by="SALDO", ascending=False)
            .head(10)
        )

        st.dataframe(top_morosos, use_container_width=True)

        # ================= EXPORTAR =================
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            resultado.to_excel(writer, sheet_name="RESULTADO", index=False)
            pendientes.to_excel(writer, sheet_name="PENDIENTES", index=False)

            workbook = writer.book

            for sheet in workbook.worksheets:
                for col in sheet.columns:
                    max_length = 0
                    col_letter = get_column_letter(col[0].column)

                    for cell in col:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))

                    sheet.column_dimensions[col_letter].width = max_length + 2

                for cell in sheet[1]:
                    cell.font = Font(bold=True)

        st.download_button(
            label="📥 Descargar Reporte Profesional",
            data=output.getvalue(),
            file_name="reporte_cobranza.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ============================================
# 2️⃣ MÓDULOS FUTUROS
# ============================================
elif menu == "📈 Aging Report (Próximamente)":
    st.title("📈 Aging Report")
    st.info("Este módulo permitirá clasificar la cartera por rangos de mora (0-30, 31-60, 61-90, 90+ días).")

elif menu == "🧾 Intereses (Próximamente)":
    st.title("🧾 Cálculo de Intereses")
    st.info("Aquí podremos calcular intereses automáticos por mora.")

elif menu == "📄 Cartas Automáticas (Próximamente)":
    st.title("📄 Generador de Cartas")
    st.info("Permitirá generar cartas de cobranza automáticas en Word o PDF.")

elif menu == "⚙️ Configuración":
    st.title("⚙️ Configuración del Sistema")
    st.write("Aquí podrás definir tasas de interés, metas de recuperación y parámetros generales.")
