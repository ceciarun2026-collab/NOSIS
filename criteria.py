"""
criteria.py

Administración de los criterios de extracción y de su ponderación
(peso) para el cálculo del scoring / semáforo de riesgo.
"""

from database.db import Database
from logger import logger


# ======================================================
# CRITERIOS INICIALES
# ======================================================
# Tupla: (categoria, campo, descripcion, tipo, activo, orden, peso)
# Los pesos suman 100 entre los criterios activos por defecto.

DEFAULT_CRITERIA = [

    # --------------------------------------------------
    # EMPRESA
    # --------------------------------------------------

    ("Empresa", "Razón Social",
     "Nombre legal de la empresa.",
     "Texto", 1, 1, 5),

    ("Empresa", "CUIT",
     "Identificación tributaria de la empresa.",
     "Texto", 1, 2, 5),

    ("Empresa", "Antigüedad",
     "Tiempo de existencia de la empresa.",
     "Texto", 1, 3, 10),

    ("Empresa", "Actividad",
     "Actividad económica principal.",
     "Texto", 1, 4, 5),

    # --------------------------------------------------
    # CONSULTAS
    # --------------------------------------------------

    ("Consultas", "Cantidad",
     "Cantidad total de consultas registradas.",
     "Número", 1, 5, 10),

    # --------------------------------------------------
    # DEUDAS
    # --------------------------------------------------

    ("Deudas", "Deudas",
     "Información sobre deudas vigentes.",
     "Texto", 1, 6, 25),

    # --------------------------------------------------
    # CHEQUES
    # --------------------------------------------------

    ("Cheques", "Cheques",
     "Información sobre cheques rechazados o vigentes.",
     "Texto", 1, 7, 25),

    # --------------------------------------------------
    # HISTORIAL
    # --------------------------------------------------

    ("Historial", "Historial",
     "Movimientos, antecedentes e historial completo de la empresa.",
     "Texto", 1, 8, 15),

]


# ======================================================
# Inicializar criterios
# ======================================================

def initialize_criteria():
    """
    Inserta los criterios por defecto
    únicamente la primera vez.
    """

    db = Database()

    db.create_tables()

    row = db.fetchone(
        "SELECT COUNT(*) AS total FROM Criteria"
    )

    total = row["total"]

    if total == 0:

        logger.info("Insertando criterios iniciales...")

        db.executemany("""

            INSERT INTO Criteria(

                categoria,
                campo,
                descripcion,
                tipo,
                activo,
                orden,
                peso

            )

            VALUES(?,?,?,?,?,?,?)

        """, DEFAULT_CRITERIA)

        logger.info("Criterios creados correctamente.")

    else:

        logger.info("Los criterios ya existen.")

    db.close()


# ======================================================
# Obtener todos los criterios
# ======================================================

def get_all():

    db = Database()

    rows = db.fetchall("""

        SELECT *

        FROM Criteria

        ORDER BY orden

    """)

    db.close()

    return rows


# ======================================================
# Obtener criterios activos
# ======================================================

def get_active():

    db = Database()

    rows = db.fetchall("""

        SELECT *

        FROM Criteria

        WHERE activo = 1

        ORDER BY orden

    """)

    db.close()

    return rows


# ======================================================
# Activar / Desactivar criterio
# ======================================================

def set_active(id_criterio: int, activo: bool):

    db = Database()

    db.execute("""

        UPDATE Criteria

        SET activo = ?

        WHERE id = ?

    """, (int(activo), id_criterio))

    db.close()


# ======================================================
# Actualizar el peso (ponderación) de un criterio
# ======================================================

def set_peso(id_criterio: int, peso: int):

    db = Database()

    db.execute("""

        UPDATE Criteria

        SET peso = ?

        WHERE id = ?

    """, (int(peso), id_criterio))

    db.close()


# ======================================================
# Agregar criterio
# ======================================================

def add(
        categoria,
        campo,
        descripcion,
        tipo="Texto",
        activo=True,
        orden=999,
        peso=10):

    db = Database()

    db.execute("""

        INSERT INTO Criteria(

            categoria,
            campo,
            descripcion,
            tipo,
            activo,
            orden,
            peso

        )

        VALUES(?,?,?,?,?,?,?)

    """, (

        categoria,
        campo,
        descripcion,
        tipo,
        int(activo),
        orden,
        int(peso)

    ))

    db.close()

    logger.info(f"Criterio agregado: {campo}")


# ======================================================
# Editar criterio
# ======================================================

def update(
        id_criterio,
        categoria,
        campo,
        descripcion,
        tipo="Texto",
        peso=None):

    db = Database()

    if peso is None:
        db.execute("""

            UPDATE Criteria

            SET categoria = ?,
                campo = ?,
                descripcion = ?,
                tipo = ?

            WHERE id = ?

        """, (

            categoria,
            campo,
            descripcion,
            tipo,
            id_criterio

        ))
    else:
        db.execute("""

            UPDATE Criteria

            SET categoria = ?,
                campo = ?,
                descripcion = ?,
                tipo = ?,
                peso = ?

            WHERE id = ?

        """, (

            categoria,
            campo,
            descripcion,
            tipo,
            int(peso),
            id_criterio

        ))

    db.close()

    logger.info(f"Criterio editado: {campo}")


# ======================================================
# Eliminar criterio
# ======================================================

def delete(id_criterio):

    db = Database()

    db.execute("""

        DELETE

        FROM Criteria

        WHERE id = ?

    """, (id_criterio,))

    db.close()

    logger.info(f"Criterio eliminado: {id_criterio}")
