"""
=========================================================
db.py

Administración de SQLite

Corporate Intelligence AI

Versión 2.0
=========================================================
"""

import sqlite3

from config import DATABASE_FOLDER
from config import DATABASE_PATH

from logger import logger


class Database:

    def __init__(self):

        DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(DATABASE_PATH)

        self.connection.row_factory = sqlite3.Row

        self.cursor = self.connection.cursor()

        # Habilitar Foreign Keys
        self.cursor.execute("PRAGMA foreign_keys = ON;")

        logger.info("SQLite conectado correctamente")

    # =====================================================
    # CREAR TABLAS
    # =====================================================

    def create_tables(self):

        logger.info("Creando tablas...")

        # -------------------------------------------------
        # CRITERIA
        # -------------------------------------------------

        self.cursor.execute("""

        CREATE TABLE IF NOT EXISTS Criteria(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            categoria TEXT NOT NULL,

            campo TEXT NOT NULL,

            descripcion TEXT,

            tipo TEXT,

            activo INTEGER DEFAULT 1,

            orden INTEGER,

            peso INTEGER DEFAULT 10

        )

        """)

        # Migración: si la tabla Criteria ya existía de una versión
        # anterior sin la columna "peso", se agrega ahora.
        try:
            self.cursor.execute("ALTER TABLE Criteria ADD COLUMN peso INTEGER DEFAULT 10")
            self.connection.commit()
        except Exception:
            pass

        # -------------------------------------------------
        # DOCUMENTS
        # -------------------------------------------------

        self.cursor.execute("""

        CREATE TABLE IF NOT EXISTS Documents(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nombre_pdf TEXT NOT NULL,

            ruta_pdf TEXT,

            hash_pdf TEXT UNIQUE,

            paginas INTEGER,

            palabras INTEGER,

            caracteres INTEGER,

            tamano_kb REAL,

            fecha_proceso TEXT,

            tiempo_proceso REAL,

            estado TEXT,

            texto_completo TEXT

        )

        """)

        # -------------------------------------------------
        # COMPANIES
        # -------------------------------------------------

        self.cursor.execute("""

        CREATE TABLE IF NOT EXISTS Companies(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id INTEGER NOT NULL,

            razon_social TEXT,

            cuit TEXT,

            actividad_codigo TEXT,

            actividad_descripcion TEXT,

            fecha_constitucion TEXT,

            antiguedad_anios INTEGER,

            FOREIGN KEY(document_id)
                REFERENCES Documents(id)
                ON DELETE CASCADE

        )

        """)

        # -------------------------------------------------
        # COMPANY INDICATORS
        # -------------------------------------------------

        self.cursor.execute("""

        CREATE TABLE IF NOT EXISTS CompanyIndicators(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id INTEGER NOT NULL,

            consultas INTEGER,

            periodo_consultas TEXT,

            deuda_fiscal INTEGER,

            ultimo_periodo TEXT,

            monto_deuda REAL,

            detalle_deuda TEXT,

            cheques_rechazados INTEGER,

            monto_cheques REAL,

            tipo_cheques TEXT,

            detalle_cheques TEXT,

            riesgo_nivel TEXT,

            riesgo_puntaje INTEGER,

            riesgo_justificacion TEXT,

            FOREIGN KEY(company_id)
                REFERENCES Companies(id)
                ON DELETE CASCADE

        )

        """)

        # -------------------------------------------------
        # COMPANY HISTORY
        # -------------------------------------------------

        self.cursor.execute("""

        CREATE TABLE IF NOT EXISTS CompanyHistory(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id INTEGER NOT NULL,

            fecha TEXT,

            categoria TEXT,

            titulo TEXT,

            descripcion TEXT,

            valor TEXT,

            monto REAL,

            pagina INTEGER,

            FOREIGN KEY(company_id)
                REFERENCES Companies(id)
                ON DELETE CASCADE

        )

        """)

        self.connection.commit()

        logger.info("Tablas creadas correctamente")

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, sql, params=()):

        self.cursor.execute(sql, params)

        self.connection.commit()

        return self.cursor.lastrowid

    # =====================================================
    # EXECUTEMANY
    # =====================================================

    def executemany(self, sql, values):

        self.cursor.executemany(sql, values)

        self.connection.commit()

    # =====================================================
    # FETCHONE
    # =====================================================

    def fetchone(self, sql, params=()):

        self.cursor.execute(sql, params)

        return self.cursor.fetchone()

    # =====================================================
    # FETCHALL
    # =====================================================

    def fetchall(self, sql, params=()):

        self.cursor.execute(sql, params)

        return self.cursor.fetchall()

    # =====================================================
    # TRANSACTION
    # =====================================================

    def begin(self):

        self.connection.execute("BEGIN")

    def commit(self):

        self.connection.commit()

    def rollback(self):

        self.connection.rollback()

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):

        self.connection.close()

        logger.info("SQLite desconectado")