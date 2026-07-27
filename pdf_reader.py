import fitz
import hashlib
import time

from pathlib import Path
from datetime import datetime

from logger import logger


def build_document(pdf_path):

    inicio = time.time()

    pdf = Path(pdf_path)

    if not pdf.exists():
        raise FileNotFoundError(f"No existe {pdf}")

    logger.info(f"Leyendo PDF: {pdf.name}")

    document = fitz.open(pdf)

    paginas = []

    texto_completo = ""

    logger.info(f"Total páginas: {document.page_count}")

    for numero in range(document.page_count):

        page = document.load_page(numero)

        texto = page.get_text()

        texto = " ".join(texto.split())

        paginas.append({

            "pagina": numero + 1,

            "texto": texto

        })

        texto_completo += texto + "\n"

        logger.info(f"Página {numero+1} procesada")

    document.close()

    logger.info("Calculando HASH...")

    sha = hashlib.sha256()

    with open(pdf, "rb") as archivo:

        while True:

            bloque = archivo.read(4096)

            if not bloque:
                break

            sha.update(bloque)

    tiempo = round(time.time() - inicio, 2)

    documento = {

        "nombre": pdf.name,

        "ruta": str(pdf),

        "paginas": len(paginas),

        "palabras": len(texto_completo.split()),

        "caracteres": len(texto_completo),

        "tamano_kb": round(pdf.stat().st_size / 1024, 2),

        "hash": sha.hexdigest(),

        "fecha_proceso": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        "tiempo_proceso": tiempo,

        "texto_completo": texto_completo,

        "texto_paginas": paginas

    }

    logger.info("Documento construido correctamente")

    return documento