import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Gestión Profesional de Cobranza", layout="wide")

st.title("📊 Sistema Profesional de Gestión de Cobranza")
st.write("Cruce automático de cartera vs pagos con separación por períodos pendientes")

archivo_deuda = st.file_uploader(
    "📄 Subir archivo de DEUDA / CARTERA",
    type=["xlsx"]
)

archivo_pagos = st.file_uploader(
    "📄 Subir archivo de PAGOS",
    type=["xlsx"]
)

if archivo_deuda and archivo_pagos:

    df_deuda = pd.read_excel(archivo_deuda)
    df_pagos = pd.read_excel(archivo_pagos)

    # Normalizar nombres de columnas
    df_deuda.columns = df_deuda.columns.str.upper().str.strip()
    df_pagos.columns = df_pagos.columns.str.upper().str.strip()

    # Renombrar columnas de pagos
    df_pagos = df_pagos.rename(columns={
        "ID COBRANZA": "ID_COBRANZA",
        "FECHA PAGO": "FECHA_PAGO"
    })

    # Convertir campos clave a texto
    df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
    df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)

    df_pagos["ID_COBRANZA"] = df_pagos["ID_COBRANZA"].astype(str)
    df_pagos["PERIODO"] = df_pagos["PERIODO"].astype(str)

    # Cruce
    df_resultado = df_deuda.merge(
        df_pagos[["ID_COBRANZA", "PERIODO", "FECHA_PAGO"]],
        on=["ID_COBRANZA", "PERIODO"],
        how="left"
    )

    # Estado
    df_resultado["ESTADO_PAGO"] = df_resultado["FECHA_PAGO"].apply(
        lambda x: "PAGADO" if pd.notnull(x) else "PENDIENTE"
    )

    st.success("✅ Proceso completado")

    st.subheader("📋 Resultado General")
    st.dataframe(df_resultado)

    # Crear Excel en memoria
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        # Hoja general
        df_resultado.to_excel(writer, sheet_name="RESULTADO_GENERAL", index=False)

        # Filtrar pendientes
        pendientes = df_resultado[df_resultado["ESTADO_PAGO"] == "PENDIENTE"]

        # Crear hojas por PERIODO (solo pendientes)
        for periodo in pendientes["PERIODO"].unique():
            df_periodo = pendientes[pendientes["PERIODO"] == periodo]
            nombre_hoja = f"{periodo}_PENDIENTES"
            df_periodo.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)

    st.download_button(
        label="📥 Descargar Excel Profesional",
        data=output.getvalue(),
        file_name="resultado_cobranza_profesional.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
