from dataclasses import dataclass
from typing import Optional


@dataclass
class Empresa:

    razon_social: Optional[str] = None
    cuit: Optional[str] = None
    actividad: Optional[str] = None
    antiguedad: Optional[str] = None
    consultas: Optional[str] = None
    deudas: Optional[str] = None
    cheques: Optional[str] = None
    resumen: Optional[str] = None