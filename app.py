"""
=========================================================
app.py

Corporate Intelligence AI

Proceso principal de extracción

Versión 2.0
=========================================================
"""

from pathlib import Path

from logger import logger
from criteria import initialize_criteria
from pdf_reader import build_document
from azure_client import analizar_empresa

from config import PDF_FOLDER
from utils import guardar_json

from database.db import Database


# =====================================================
# GUARDAR DOCUMENTO
# =====================================================

def guardar_documento(db, documento):

    db.execute(
        """
        INSERT OR IGNORE INTO Documents(

            nombre_pdf,
            ruta_pdf,
            hash_pdf,
            paginas,
            palabras,
            caracteres,
            fecha_proceso,
            estado,
            texto_completo

        )

        VALUES(?,?,?,?,?,?,?,?,?)

        """,
        (

            documento["nombre"],
            documento["ruta"],
            documento["hash"],
            documento["paginas"],
            documento["palabras"],
            documento["caracteres"],
            documento["fecha_proceso"],
            "Procesado",
            documento["texto_completo"]

        )

    )


# =====================================================
# MAIN
# =====================================================

def main():

    logger.info("=" * 60)
    logger.info("Corporate Intelligence AI")
    logger.info("=" * 60)

    # -----------------------------------------
    # Base de datos
    # -----------------------------------------

    db = Database()

    db.create_tables()

    initialize_criteria()

    # -----------------------------------------
    # Carpeta PDFs
    # -----------------------------------------

    PDF_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    pdfs = list(
        Path(PDF_FOLDER).glob("*.pdf")
    )

    if len(pdfs) == 0:

        logger.warning("No se encontraron PDFs.")

        logger.warning(
            f"Copie los PDFs en:\n{PDF_FOLDER}"
        )

        db.close()

        return

    logger.info(f"Se encontraron {len(pdfs)} PDF(s).")

    # -----------------------------------------
    # Procesamiento
    # -----------------------------------------

    for pdf in pdfs:

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Procesando {pdf.name}")
        logger.info("=" * 60)

        # --------------------------
        # Leer PDF
        # --------------------------

        documento = build_document(pdf)

        logger.info("Documento leído correctamente.")

        # --------------------------
        # Guardar PDF en SQLite
        # --------------------------

        guardar_documento(
            db,
            documento
        )

        logger.info("Documento almacenado.")

        # --------------------------
        # Azure AI Foundry
        # --------------------------

        logger.info("Enviando documento a GPT-5 Mini...")

        try:

            resultado = analizar_empresa(

                documento["texto_completo"]

            )

            logger.info("Respuesta recibida.")

            guardar_json(

                documento["nombre"],

                resultado

            )

            logger.info("JSON almacenado correctamente.")

        except Exception as ex:

            logger.error("")

            logger.error("Error durante el análisis")

            logger.error(str(ex))

        logger.info("")

    db.close()

    logger.info("=" * 60)
    logger.info("Proceso finalizado correctamente.")
    logger.info("=" * 60)


# =====================================================
# INICIO
# =====================================================

if __name__ == "__main__":

    main()