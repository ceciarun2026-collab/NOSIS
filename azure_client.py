"""
=========================================================
azure_client.py

Cliente Azure AI Foundry

Versión 2.0
=========================================================
"""

import json
import re

from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
)

from PROMPT_EMPRESA import PROMPT_EMPRESA


# =====================================================
# CLIENTE AZURE
# =====================================================

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
)


# =====================================================
# ANALIZAR EMPRESA
# =====================================================

def analizar_empresa(texto: str) -> dict:

    prompt = PROMPT_EMPRESA.replace("{texto}", texto)

    respuesta = client.chat.completions.create(

        model=AZURE_OPENAI_DEPLOYMENT,

        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista experto en riesgo corporativo. "
                    "Siempre responde únicamente con un JSON válido."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    contenido = respuesta.choices[0].message.content.strip()

    # Eliminar posibles bloques Markdown
    contenido = re.sub(r"```json", "", contenido)
    contenido = re.sub(r"```", "", contenido)
    contenido = contenido.strip()

    try:

        return json.loads(contenido)

    except json.JSONDecodeError:

        inicio = contenido.find("{")
        fin = contenido.rfind("}") + 1

        if inicio >= 0 and fin > inicio:
            return json.loads(contenido[inicio:fin])

        raise Exception("La respuesta del modelo no contiene un JSON válido.")