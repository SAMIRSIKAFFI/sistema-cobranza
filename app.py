import streamlit as st
import pandas as pd
import io
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="Sistema Profesional de Cobranza", layout="wide")

st.title("⚖️ Sistema Profesional de Gestión de Cobranza")
st.markdown("### 📊 Dashboard Ejecutivo de Recuperación")

archivo_deuda = st.file_uploader("📂 Subir archivo CARTERA / DEUDA", type=["xlsx"])
archivo_pagos = st.file_uploader("📂 Subir archivo PAGOS", type=["xlsx"])


def limpiar_columnas(df):
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    return df


if archivo_deuda and archivo_pagos:

    # =============================
    # CARGA Y LIMPIEZA
    # =============================
    df_deuda = pd.read_excel(archivo_deuda)
    df_pagos = pd.read_excel(archivo_pagos)

    df_deuda = limpiar_columnas(df_deuda)
    df_pagos = limpiar_columnas(df_pagos)

    df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
    df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)

    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
    df_pagos["PERIODO"] = df_pagos["PERIODO"].astype(str)

    df_deuda["DEUDA"] = pd.to_numeric(df_deuda["DEUDA"], errors="coerce").fillna(0)
    df_pagos["IMPORTE"] = pd.to_numeric(df_pagos["IMPORTE"], errors="coerce").fillna(0)

    # =============================
    # CRUCE DE INFORMACIÓN
    # =============================
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

    # =============================
    # INDICADORES EJECUTIVOS
    # =============================
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

    # =============================
    # SEMÁFORO FINANCIERO
    # =============================
    if porcentaje_recuperacion >= 80:
        st.success("🟢 Nivel de recuperación saludable")
    elif porcentaje_recuperacion >= 50:
        st.warning("🟡 Nivel de recuperación medio")
    else:
        st.error("🔴 Nivel de recuperación bajo")

    # =============================
    # RESÚMENES
    # =============================
    resumen_tipo = pendientes.groupby("TIPO")["DEUDA"].sum().reset_index()
    resumen_periodo = pendientes.groupby("PERIODO")["DEUDA"].sum().reset_index()
    pagos_por_periodo = pagos_resumen.groupby("PERIODO")["TOTAL_PAGADO"].sum().reset_index()

    st.subheader("📊 Deuda Pendiente por TIPO")
    st.bar_chart(resumen_tipo.set_index("TIPO"))

    st.subheader("📆 Deuda Pendiente por PERIODO")
    st.line_chart(resumen_periodo.set_index("PERIODO"))

    st.subheader("💵 Pagos por PERIODO")
    st.line_chart(pagos_por_periodo.set_index("PERIODO"))

    # =============================
    # RANKING MOROSOS
    # =============================
    top_morosos = pendientes.groupby("ID_COBRANZA")["DEUDA"].sum().reset_index()
    top_morosos = top_morosos.sort_values(by="DEUDA", ascending=False).head(10)

    st.subheader("🏆 Top 10 Mayores Deudores")
    st.dataframe(top_morosos)

    # =============================
    # COMPARATIVO GLOBAL
    # =============================
    st.subheader("📊 Comparativo Global")

    comparativo = pd.DataFrame({
        "Concepto": ["Pagado", "Pendiente"],
        "Monto": [total_pagado, total_pendiente]
    })

    st.bar_chart(comparativo.set_index("Concepto"))

    # =============================
    # EXPORTACIÓN PROFESIONAL EXCEL
    # =============================
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        resultado.to_excel(writer, sheet_name="RESULTADO_GENERAL", index=False)
        resumen_tipo.to_excel(writer, sheet_name="RESUMEN_TIPO", index=False)
        resumen_periodo.to_excel(writer, sheet_name="RESUMEN_PERIODO", index=False)
        pagos_por_periodo.to_excel(writer, sheet_name="PAGOS_POR_PERIODO", index=False)
        pendientes.to_excel(writer, sheet_name="PENDIENTES_TOTALES", index=False)

        for periodo in pendientes["PERIODO"].unique():
            df_periodo = pendientes[pendientes["PERIODO"] == periodo]
            nombre_hoja = f"PEND_{periodo}"
            df_periodo.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)

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

            columnas_monetarias = ["DEUDA", "TOTAL_PAGADO", "IMPORTE"]

            for col in sheet.columns:
                header = col[0].value
                if header in columnas_monetarias:
                    for cell in col[1:]:
                        if isinstance(cell.value, (int, float)):
                            cell.number_format = '#,##0.00'

    st.download_button(
        label="📥 Descargar Reporte Financiero Profesional",
        data=output.getvalue(),
        file_name="reporte_financiero_cobranza.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
