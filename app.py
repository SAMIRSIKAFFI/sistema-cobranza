import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime

st.set_page_config(page_title="SISTEMA DE COBRANZA - RESULTADOS", layout="wide")

st.title("SISTEMA DE COBRANZA - RESULTADOS")
st.markdown("### Generador de archivo CSV listo para Excel")

archivo = st.file_uploader("Subir archivo base", type=["xlsx", "xls", "csv"])

if archivo is not None:

    # Leer archivo
    if archivo.name.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        df = pd.read_excel(archivo)

    columnas_requeridas = ["NUMERO", "NOMBRE", "FECHA", "CODIGO", "MONTO"]

    if not all(col in df.columns for col in columnas_requeridas):
        st.error("El archivo debe contener las columnas: NUMERO, NOMBRE, FECHA, CODIGO, MONTO")
    else:

        df = df[columnas_requeridas].copy()

        # Convertir fecha
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")

        meses = {
            1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
            7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"
        }

        dias = {
            0:"lunes",1:"martes",2:"miércoles",3:"jueves",
            4:"viernes",5:"sábado",6:"domingo"
        }

        def formatear_fecha(fecha):
            if pd.isnull(fecha):
                return ""
            return f"{dias[fecha.weekday()]}, {fecha.day} de {meses[fecha.month]} de {fecha.year}"

        df["FECHA"] = df["FECHA"].apply(formatear_fecha)

        # Formatear monto con coma decimal
        df["MONTO"] = pd.to_numeric(df["MONTO"], errors="coerce").fillna(0)
        df["MONTO"] = df["MONTO"].map(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Generar CSV delimitado por punto y coma
        csv_buffer = StringIO()
        df.to_csv(
            csv_buffer,
            index=False,
            sep=";",              # ← CLAVE para que Excel lo abra en columnas
            encoding="utf-8-sig"
        )

        st.success("Archivo CSV generado correctamente.")

        st.download_button(
            label="Descargar CSV listo para Excel",
            data=csv_buffer.getvalue(),
            file_name="reporte_sms_cobranza.csv",
            mime="text/csv"
        )
