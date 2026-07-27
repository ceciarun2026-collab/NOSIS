"""
Extractor del documento utilizando Azure AI Foundry
"""

from azure_client import analizar_empresa
from utils import guardar_json
from logger import logger


def procesar_documento(documento):

    logger.info("Iniciando análisis con Azure AI Foundry...")

    datos = analizar_empresa(
        documento["texto_completo"]
    )

    guardar_json(
        documento["nombre"],
        datos
    )

    logger.info("JSON generado correctamente.")

    return datos