"""
=========================================================
indicator_repository.py

Indicadores de la empresa

Corporate Intelligence AI
=========================================================
"""

from database.db import Database

from logger import logger


def save_indicators(company_id: int, indicadores: dict):

    db = Database()

    consultas = indicadores.get("consultas", {})
    deuda = indicadores.get("deuda_fiscal", {})
    cheques = indicadores.get("cheques", {})
    riesgo = indicadores.get("riesgo", {})

    sql = """

    INSERT INTO CompanyIndicators(

        company_id,

        consultas,
        periodo_consultas,

        deuda_fiscal,
        ultimo_periodo,
        monto_deuda,
        detalle_deuda,

        cheques_rechazados,
        monto_cheques,
        tipo_cheques,
        detalle_cheques,

        riesgo_nivel,
        riesgo_puntaje,
        riesgo_justificacion

    )

    VALUES(

        ?,?,?,?,?,?,?,?,?,?,?,?,?,?

    )

    """

    db.execute(

        sql,

        (

            company_id,

            consultas.get("cantidad"),
            consultas.get("periodo"),

            deuda.get("existe"),
            deuda.get("ultimo_periodo"),
            deuda.get("monto_total"),
            deuda.get("detalle"),

            cheques.get("cantidad_rechazados"),
            cheques.get("monto_total"),
            cheques.get("tipo"),
            cheques.get("detalle"),

            riesgo.get("nivel"),
            riesgo.get("puntaje"),
            riesgo.get("justificacion")

        )

    )

    db.close()

    logger.info("Indicadores almacenados correctamente.")


def get_indicators(company_id: int):

    db = Database()

    indicadores = db.fetchone(

        """

        SELECT *

        FROM CompanyIndicators

        WHERE company_id = ?

        """,

        (company_id,)

    )

    db.close()

    return indicadores