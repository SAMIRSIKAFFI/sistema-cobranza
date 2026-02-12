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
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    return df


if archivo_deuda and archivo_pagos:

    df_deuda = pd.read_excel(archivo_deuda)
    df_pagos = pd.read_excel(archivo_pagos)

    df_deuda = limpiar_columnas(df_deuda)
    df_pagos = limpiar_columnas(df_pagos)

    df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
    df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)

    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
    df_pagos["PERIODO"] = df_pagos["PERIODO"].astype(str)

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

    # ---------- EXPORTACIÓN EXCEL PROFESIONAL ----------
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

            # Ajustar ancho columnas
            for col in sheet.columns:
                max_length = 0
                col_letter = get_column_letter(col[0].column)

                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))

                sheet.column_dimensions[col_letter].width = max_length + 2

            # Encabezados en negrita
            for cell in sheet[1]:
                cell.font = Font(bold=True)

            # Formato monetario SOLO columnas correctas
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
st.markdown("---")
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

    df_suscriptor["CODIGO"] = df_suscriptor["CODIGO"].astype(str)
    df_suscriptor["PERIODO"] = df_suscriptor["PERIODO"].astype(str)
    df_suscriptor["TIPO"] = df_suscriptor["TIPO"].astype(str)

    df_pagos_sms["ID_COBRANZA"] = df_pagos_sms["ID_COBRANZA"].astype(str)
    df_pagos_sms["PERIODO"] = df_pagos_sms["PERIODO"].astype(str)

    # 🔹 Selección múltiple de periodos
    periodos_disponibles = sorted(df_suscriptor["PERIODO"].unique())

    periodos_seleccionados = st.multiselect(
        "📅 Seleccionar PERÍODOS a gestionar",
        periodos_disponibles,
        default=periodos_disponibles[:1]
    )

    # 🔹 Selección de TIPO
    tipos_disponibles = sorted(df_suscriptor["TIPO"].unique())

    tipos_seleccionados = st.multiselect(
        "📌 Seleccionar TIPO",
        tipos_disponibles,
        default=tipos_disponibles
    )

    cantidad_archivos = st.number_input(
        "📁 Cantidad de archivos CSV a generar",
        min_value=1,
        max_value=50,
        value=10
    )

    depurar = st.checkbox("☑ Depurar pagos automáticamente", value=True)

    if st.button("🚀 Generar Archivos SMS"):

        # Filtrar por periodo y tipo
        df_filtrado = df_suscriptor[
            (df_suscriptor["PERIODO"].isin(periodos_seleccionados)) &
            (df_suscriptor["TIPO"].isin(tipos_seleccionados))
        ].copy()

        if depurar and periodos_seleccionados:

            pagos_filtrados = df_pagos_sms[
                (df_pagos_sms["PERIODO"].isin(periodos_seleccionados)) &
                (df_pagos_sms["IMPORTE"] > 0)
            ]

            codigos_pagados = pagos_filtrados["ID_COBRANZA"].unique()

            df_filtrado = df_filtrado[
                ~df_filtrado["CODIGO"].isin(codigos_pagados)
            ]

        total_registros = len(df_filtrado)

        if total_registros == 0:
            st.warning("No existen registros para generar archivos.")
        else:

            st.success(f"Total registros a enviar: {total_registros}")

            tamaño_lote = total_registros // cantidad_archivos + 1

            for i in range(cantidad_archivos):

                inicio = i * tamaño_lote
                fin = inicio + tamaño_lote

                df_parte = df_filtrado.iloc[inicio:fin]

                if not df_parte.empty:

                    csv = df_parte[
                        ["NUMERO", "NOMBRE", "FECHA", "CODIGO", "MONTO", "TIPO"]
                    ].to_csv(index=False)

                    st.download_button(
                        label=f"📥 Descargar Archivo_SMS_{i+1}.csv",
                        data=csv,
                        file_name=f"SMS_{'_'.join(periodos_seleccionados)}_{i+1}.csv",
                        mime="text/csv"
                    )
