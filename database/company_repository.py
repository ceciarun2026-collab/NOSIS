"""
=========================================================
company_repository.py

Empresas

Corporate Intelligence AI
=========================================================
"""

from database.db import Database


def save_company(document_id, empresa):

    db = Database()

    sql = """

    INSERT INTO Companies(

        document_id,

        razon_social,

        cuit,

        actividad_codigo,

        actividad_descripcion,

        fecha_constitucion,

        antiguedad_anios

    )

    VALUES(

        ?,?,?,?,?,?,?

    )

    """

    identificacion = empresa.get("identificacion", {})

    actividad = empresa.get("actividad", {})

    constitucion = empresa.get("constitucion", {})

    company_id = db.execute(

        sql,

        (

            document_id,

            identificacion.get("razon_social"),

            identificacion.get("cuit"),

            actividad.get("codigo"),

            actividad.get("descripcion"),

            constitucion.get("fecha"),

            constitucion.get("antiguedad_anios")

        )

    )

    db.close()

    return company_id