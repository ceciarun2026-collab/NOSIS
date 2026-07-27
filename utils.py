import json

from pathlib import Path

from config import JSON_FOLDER


def guardar_json(nombre_archivo: str, datos: dict):

    JSON_FOLDER.mkdir(parents=True, exist_ok=True)

    archivo = Path(JSON_FOLDER) / f"{Path(nombre_archivo).stem}.json"

    with open(archivo, "w", encoding="utf-8") as f:

        json.dump(
            datos,
            f,
            indent=4,
            ensure_ascii=False
        )

    return archivo


def cargar_json(texto: str):

    try:
        return json.loads(texto)

    except Exception:

        return {}