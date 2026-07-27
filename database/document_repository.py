"""
=========================================================
document_repository.py

Administración de documentos

Corporate Intelligence AI
=========================================================
"""

from database.db import Database

from logger import logger


def save_document(documento):

    db = Database()

    sql = """

    INSERT INTO Documents(

        nombre_pdf,
        ruta_pdf,
        hash_pdf,
        paginas,
        palabras,
        caracteres,
        tamano_kb,
        fecha_proceso,
        tiempo_proceso,
        estado,
        texto_completo

    )

    VALUES(

        ?,?,?,?,?,?,?,?,?,?,?

    )

    """

    document_id = db.execute(

        sql,

        (

            documento["nombre"],
            documento["ruta"],
            documento["hash"],
            documento["paginas"],
            documento["palabras"],
            documento["caracteres"],
            documento["tamano_kb"],
            documento["fecha_proceso"],
            documento["tiempo_proceso"],
            "PROCESADO",
            documento["texto_completo"]

        )

    )

    logger.info(f"Documento almacenado. ID={document_id}")

    db.close()

    return document_id


def get_all_documents():

    db = Database()

    documentos = db.fetchall("""

        SELECT *

        FROM Documents

        ORDER BY fecha_proceso DESC

    """)

    db.close()

    return documentos


def get_document(document_id):

    db = Database()

    documento = db.fetchone(

        """

        SELECT *

        FROM Documents

        WHERE id = ?

        """,

        (document_id,)

    )

    db.close()

    return documento


def delete_document(document_id):

    db = Database()

    db.execute(

        """

        DELETE FROM Documents

        WHERE id = ?

        """,

        (document_id,)

    )

    db.close()

    logger.info(f"Documento eliminado. ID={document_id}")