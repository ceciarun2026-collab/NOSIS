"""
=========================================================
history_repository.py

Historial de empresas

Corporate Intelligence AI
=========================================================
"""

from database.db import Database

from logger import logger


def save_history(company_id: int, historial: list):

    db = Database()

    sql = """

    INSERT INTO CompanyHistory(

        company_id,

        fecha,

        categoria,

        titulo,

        descripcion,

        valor,

        monto,

        pagina

    )

    VALUES(

        ?,?,?,?,?,?,?,?

    )

    """

    registros = []

    for evento in historial:

        registros.append(

            (

                company_id,

                evento.get("fecha"),

                evento.get("categoria"),

                evento.get("titulo"),

                evento.get("descripcion"),

                evento.get("valor"),

                evento.get("monto"),

                evento.get("pagina")

            )

        )

    if registros:

        db.executemany(sql, registros)

        logger.info(f"{len(registros)} eventos almacenados.")

    db.close()


def get_history(company_id: int):

    db = Database()

    historial = db.fetchall(

        """

        SELECT *

        FROM CompanyHistory

        WHERE company_id = ?

        ORDER BY fecha DESC

        """,

        (company_id,)

    )

    db.close()

    return historial


def get_history_by_category(company_id: int, categoria: str):

    db = Database()

    historial = db.fetchall(

        """

        SELECT *

        FROM CompanyHistory

        WHERE company_id = ?

        AND categoria = ?

        ORDER BY fecha DESC

        """,

        (

            company_id,

            categoria

        )

    )

    db.close()

    return historial