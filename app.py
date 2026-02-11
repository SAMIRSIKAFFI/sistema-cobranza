import streamlit as st
import pandas as pd
import io
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="Sistema Profesional de Cobranza", layout="wide")

st.title("⚖️ Sistema Profesional de Gestión de Cobranza")

archivo_deuda = st.file_uploader("📂 Subir archivo CARTERA / DEUDA", type=["xlsx"])
archivo_pagos = st.file_uploader("📂 Subir archivo PAGOS", type=["xlsx"])

def limpiar_columnas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "_")
    )
    return df

if archivo_deuda and archivo_pagos:

    df_deuda = pd.read_excel(archivo_deuda)
    df_pagos = pd.read_excel(archivo_pagos)

    df_deuda = limpiar_columnas(df_deuda)
    df_pagos = limpiar_columnas(df_pagos)

    # Asegurar nombres correctos
    df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
    df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)

    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
    df_pagos["PERIODO"] = df_pagos["PERIODO"].astype(str)

    pagos_resumen = df_pagos.groupby(
        ["ID_COBRANZA", "PERIODO"]
    )["IMPORTE"].sum().reset_index()

    pagos_resumen.rename(columns={
        "IMPORTE": "TOTAL_PAGADO"
    }, inplace=True)

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

    resumen_tipo = pendientes.groupby("TIPO")["DEUDA"].sum().reset_index()
    resumen_periodo = pendientes.groupby("PERIODO")["DEUDA"].sum().reset_index()
    pagos_por_periodo = pagos_resumen.groupby("PERIODO")["TOTAL_PAGADO"].sum().reset_index()

    total_pendiente = pendientes["DEUDA"].sum()
    total_pagado = resultado["TOTAL_PAGADO"].sum()

    st.success("Cruce realizado correctamente")

    col1, col2 = st.columns(2)
    col1.metric("💰 Total Pagado", f"Bs. {total_pagado:,.2f}")
    col2.metric("⚠️ Total Pendiente", f"Bs. {total_pendiente:,.2f}")

    st.subheader("📊 Resumen por TIPO")
    st.dataframe(resumen_tipo)

    st.subheader("📆 Deuda Pendiente por PERIODO")
    st.dataframe(resumen_periodo)

    st.subheader("💵 Pagos por PERIODO")
    st.dataframe(pagos_por_periodo)

    st.subheader("📊 Comparativo Pagado vs Pendiente")
    comparativo = pd.DataFrame({
        "Pagado": [total_pagado],
        "Pendiente": [total_pendiente]
    })
    st.bar_chart(comparativo)

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

            # Aplicar formato solo a columnas monetarias
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


