import logging
from pathlib import Path
from config import LOG_FOLDER

LOG_FOLDER.mkdir(exist_ok=True)

LOG_FILE = LOG_FOLDER / "app.log"


def get_logger():

    logger = logging.getLogger("CorporateAI")

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # Consola
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # Archivo
    file = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file)

    return logger


logger = get_logger()