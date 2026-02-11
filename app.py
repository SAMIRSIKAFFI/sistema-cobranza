import streamlit as st
import pandas as pd
import io

st.title("⚖️ Sistema Profesional de Gestión de Cobranza")

st.write("Suba los archivos para cruzar cartera con pagos")

archivo_deuda = st.file_uploader("📂 Subir archivo CARTERA / DEUDA", type=["xlsx"])
archivo_pagos = st.file_uploader("📂 Subir archivo PAGOS", type=["xlsx"])

if archivo_deuda and archivo_pagos:

    df_deuda = pd.read_excel(archivo_deuda)
    df_pagos = pd.read_excel(archivo_pagos)

    df_deuda["ID_COBRANZA"] = df_deuda["ID_COBRANZA"].astype(str)
    df_deuda["PERIODO"] = df_deuda["PERIODO"].astype(str)

    df_pagos["Id Cobranza"] = df_pagos["Id Cobranza"].astype(str)
    df_pagos["Periodo"] = df_pagos["Periodo"].astype(str)

    pagos_resumen = df_pagos.groupby(
        ["Id Cobranza", "Periodo"]
    )["Importe"].sum().reset_index()

    pagos_resumen.rename(columns={
        "Id Cobranza": "ID_COBRANZA",
        "Periodo": "PERIODO",
        "Importe": "TOTAL_PAGADO"
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

    # 📊 Resumen por TIPO
    resumen_tipo = pendientes.groupby("TIPO")["DEUDA"].sum().reset_index()

    # 📊 Totales por PERIODO
    resumen_periodo = pendientes.groupby("PERIODO")["DEUDA"].sum().reset_index()

    total_pendiente = pendientes["DEUDA"].sum()

    st.success("Cruce realizado correctamente")

    st.subheader("📊 Resumen General")
    st.dataframe(resultado)

    st.subheader("📌 Pendientes")
    st.dataframe(pendientes)

    st.subheader("📊 Resumen por TIPO")
    st.dataframe(resumen_tipo)

    st.subheader("📆 Deuda Pendiente por PERIODO")
    st.dataframe(resumen_periodo)

    st.subheader("💰 Total Deuda Pendiente")
    st.write(f"### Bs. {total_pendiente:,.2f}")

    # 📈 Gráfico por TIPO
    st.subheader("📊 Gráfico Deuda por TIPO")
    st.bar_chart(resumen_tipo.set_index("TIPO"))

    # 📈 Gráfico por PERIODO
    st.subheader("📊 Gráfico Deuda por PERIODO")
    st.bar_chart(resumen_periodo.set_index("PERIODO"))

    # 📥 Exportar Excel con hojas múltiples
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        resultado.to_excel(writer, sheet_name="RESULTADO_GENERAL", index=False)
        resumen_tipo.to_excel(writer, sheet_name="RESUMEN_TIPO", index=False)
        resumen_periodo.to_excel(writer, sheet_name="RESUMEN_PERIODO", index=False)
        pendientes.to_excel(writer, sheet_name="PENDIENTES_TOTALES", index=False)

        # Crear hojas por PERIODO (solo pendientes)
        for periodo in pendientes["PERIODO"].unique():
            df_periodo = pendientes[pendientes["PERIODO"] == periodo]
            nombre_hoja = f"PEND_{periodo}"
            df_periodo.to_excel(writer, sheet_name=nombre_hoja[:31], index=False)

    st.download_button(
        label="📥 Descargar Reporte Profesional",
        data=output.getvalue(),
        file_name="reporte_cobranza_profesional.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


