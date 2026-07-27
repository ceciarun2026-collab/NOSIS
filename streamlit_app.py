import os
import tempfile
import sqlite3
import html
from datetime import datetime
import streamlit as st

try:
    from pdf_reader import build_document
except Exception:
    build_document = None

try:
    from azure_client import analizar_empresa
    from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_OPENAI_DEPLOYMENT
    # OJO: el import de azure_client puede tener éxito aunque falten
    # las variables de entorno (el error recién aparece al llamar a la
    # API). Por eso acá se valida también que las credenciales existan,
    # para poder avisarle al usuario ANTES de intentar analizar.
    AZURE_OK = bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY and AZURE_OPENAI_DEPLOYMENT)
except Exception:
    analizar_empresa = None
    AZURE_OK = False

try:
    from utils import guardar_json
except Exception:
    guardar_json = None

try:
    import criteria as criteria_backend
except Exception:
    criteria_backend = None

DB_ERROR = None
try:
    from database.db import Database
    from database.document_repository import save_document
    from database.company_repository import save_company
    from database.indicator_repository import save_indicators
    from database.history_repository import save_history
    DB_OK = True
except Exception as e:
    Database = None
    save_document = save_company = save_indicators = save_history = None
    DB_OK = False
    DB_ERROR = f"{type(e).__name__}: {e}"


# ==========================================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================================

st.set_page_config(
    page_title="Nosis Analisis",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# ESTILOS
# ==========================================================

ACCENT = "#E11D48"
ACCENT_DARK = "#BE123C"
ACCENT_SOFT = "#FFF1F3"
NAVY = "#12162B"
NAVY_SOFT = "#1E2442"
NAVY_BORDER = "#2A3157"

st.markdown(f"""
<style>

/* -------------------- Base -------------------- */

.stApp {{
    background:#F4F6FA;
}}

.block-container{{
    padding-top:1.6rem;
    padding-bottom:3rem;
    max-width:1200px;
}}

html, body, [class*="css"] {{
    font-family:"Segoe UI","Inter",system-ui,sans-serif;
}}

/* -------------------- Sidebar -------------------- */

section[data-testid="stSidebar"]{{
    background:{NAVY};
    border-right:1px solid {NAVY_BORDER};
}}

section[data-testid="stSidebar"] > div {{
    padding-top: 1.2rem;
}}

section[data-testid="stSidebar"] *{{
    color:#E9EAF3;
}}

section[data-testid="stSidebar"] hr{{
    border-color:{NAVY_BORDER};
    margin:1.1rem 0;
}}

.sidebar-logo-row{{
    display:flex;
    align-items:center;
    gap:12px;
    padding: 0 0.2rem 0.4rem 0.2rem;
}}

.sidebar-logo-box{{
    width:46px;
    height:46px;
    border-radius:12px;
    background:linear-gradient(135deg, {ACCENT} 0%, #7C1D3A 100%);
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:800;
    font-size:18px;
    color:white;
    flex-shrink:0;
    box-shadow:0 4px 10px rgba(225,29,72,.35);
}}

.sidebar-brand h1{{
    font-size:17px;
    font-weight:700;
    margin:0;
    line-height:1.2;
    color:white;
}}

.sidebar-caption{{
    font-size:11px;
    letter-spacing:.12em;
    color:#7C84AE;
    text-transform:uppercase;
    margin: 6px 0 2px 2px;
    font-weight:600;
}}

.sidebar-footer{{
    font-size:11px;
    color:#5C639A;
    text-align:center;
    margin-top:1.4rem;
}}

/* Botones de navegación en la sidebar */

section[data-testid="stSidebar"] .stButton > button{{
    width:100%;
    text-align:left;
    justify-content:flex-start;
    background:{NAVY_SOFT};
    border:1px solid {NAVY_BORDER};
    color:#D7DAEC;
    border-radius:10px;
    padding:0.65rem 0.9rem;
    font-weight:500;
    font-size:14.5px;
    box-shadow:none;
    transition:all .15s ease;
}}

section[data-testid="stSidebar"] .stButton > button:hover{{
    background:#262C52;
    border-color:#3A4176;
    color:white;
}}

section[data-testid="stSidebar"] .stButton > button:focus{{
    box-shadow:none !important;
}}

/* Botón activo = kind primary */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"]{{
    background:linear-gradient(135deg, {ACCENT} 0%, {ACCENT_DARK} 100%);
    border:1px solid {ACCENT};
    color:white;
    font-weight:600;
    box-shadow:0 4px 12px rgba(225,29,72,.35);
}}

section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover{{
    filter:brightness(1.05);
    color:white;
}}

/* -------------------- Botones (área principal) -------------------- */

.main .stButton > button, div[data-testid="stForm"] .stButton > button{{
    border-radius:9px;
    font-weight:600;
    padding:0.55rem 1.1rem;
}}

.main .stButton > button[kind="primary"],
.main .stButton > button[data-testid="stBaseButton-primary"]{{
    background:{ACCENT};
    border:1px solid {ACCENT};
    color:white;
}}

.main .stButton > button[kind="primary"]:hover{{
    background:{ACCENT_DARK};
    border-color:{ACCENT_DARK};
}}

.main .stButton > button[kind="secondary"],
.main .stButton > button[data-testid="stBaseButton-secondary"]{{
    background:white;
    border:1px solid #E2E5EE;
    color:#374151;
}}

.main .stButton > button[kind="secondary"]:hover{{
    border-color:{ACCENT};
    color:{ACCENT};
}}

/* -------------------- Encabezado de página -------------------- */

.page-header{{
    margin-bottom:1.6rem;
}}

.page-header h1{{
    font-size:29px;
    font-weight:800;
    color:#161B33;
    margin:0 0 10px 0;
}}

.page-header p{{
    color:#6B7280;
    font-size:14.5px;
    margin:0 0 12px 0;
}}

.page-header .rule{{
    height:3px;
    width:100%;
    background:linear-gradient(90deg, {ACCENT} 0%, {ACCENT} 40%, #F1D3D9 100%);
    border-radius:3px;
}}

/* -------------------- Tarjetas -------------------- */

.card{{
    background:white;
    border-radius:14px;
    padding:22px 24px;
    box-shadow:0 2px 14px rgba(15,23,42,.06);
    border:1px solid #EEF0F6;
    margin-bottom:18px;
}}

.card h3{{
    font-size:17px;
    font-weight:700;
    color:#161B33;
    margin:0 0 6px 0;
}}

.card p.desc{{
    color:#6B7280;
    font-size:13.5px;
    margin:0 0 16px 0;
}}

.dropzone-wrap{{
    border:2px dashed #F3B8C4;
    background:{ACCENT_SOFT};
    border-radius:12px;
    padding:14px 16px 4px 16px;
}}

.info-box{{
    border:2px dashed #F3B8C4;
    background:{ACCENT_SOFT};
    border-radius:12px;
    padding:26px 20px;
    text-align:center;
    min-height:190px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
}}

.info-box h4{{
    color:{ACCENT_DARK};
    font-weight:700;
    font-size:16.5px;
    margin:0 0 8px 0;
}}

.info-box p{{
    color:{ACCENT_DARK};
    opacity:.85;
    font-size:13.5px;
    margin:0;
    max-width:340px;
}}

.status-chip{{
    display:inline-block;
    padding:4px 12px;
    border-radius:20px;
    font-size:12px;
    font-weight:700;
    margin:3px 6px 3px 0;
}}

.chip-neutral{{ background:#F1F3F9; color:#4B5265; }}
.chip-green{{ background:#E7F8EE; color:#12805C; }}
.chip-yellow{{ background:#FEF6E7; color:#B7791F; }}
.chip-red{{ background:#FDECEE; color:{ACCENT_DARK}; }}

/* -------------------- Matriz de criterios (tabla horizontal) -------------------- */

.matrix-wrap{{
    overflow-x:auto;
    border-radius:14px;
    border:1px solid #EEF0F6;
    box-shadow:0 2px 14px rgba(15,23,42,.06);
    margin-bottom:18px;
}}

table.matrix-table{{
    width:100%;
    border-collapse:collapse;
    background:white;
    font-size:13.5px;
}}

table.matrix-table thead th{{
    text-align:left;
    background:#F7F8FB;
    color:#4B5265;
    font-size:11.5px;
    text-transform:uppercase;
    letter-spacing:.04em;
    font-weight:700;
    padding:12px 16px;
    border-bottom:1px solid #EEF0F6;
    white-space:nowrap;
}}

table.matrix-table tbody td{{
    padding:12px 16px;
    border-bottom:1px solid #F1F3F9;
    color:#161B33;
    vertical-align:top;
}}

table.matrix-table tbody tr:last-child td{{
    border-bottom:none;
}}

table.matrix-table tbody tr:hover{{
    background:#FAFBFE;
}}

table.matrix-table td.mx-criterio{{
    font-weight:700;
    white-space:nowrap;
}}

table.matrix-table td.mx-peso{{
    color:#8B93B8;
    font-size:12px;
    white-space:nowrap;
}}

table.matrix-table td.mx-motivo{{
    color:#4B5265;
    min-width:260px;
}}

.mx-estado-dot{{
    display:inline-block;
    width:9px;
    height:9px;
    border-radius:50%;
    margin-right:7px;
    vertical-align:middle;
}}

table.matrix-table td.mx-empresa, table.matrix-table th.mx-empresa{{
    position:sticky;
    left:0;
    background:white;
    z-index:1;
    box-shadow:1px 0 0 #EEF0F6;
}}

table.matrix-table thead th.mx-empresa{{
    background:#F7F8FB;
    z-index:2;
}}

table.matrix-table td.mx-nombre-empresa{{
    font-weight:700;
    color:#161B33;
    white-space:nowrap;
}}

table.matrix-table td.mx-fecha{{
    color:#6B7280;
    white-space:nowrap;
    font-size:12.5px;
}}

table.matrix-table td.mx-score-grande{{
    font-size:22px;
    font-weight:800;
    color:#161B33;
    white-space:nowrap;
}}

table.matrix-table td.mx-crit-cell{{
    text-align:center;
    white-space:nowrap;
}}

table.matrix-table td.mx-estado-final{{
    font-weight:700;
    color:#161B33;
    white-space:nowrap;
}}

table.matrix-table th.mx-col-criterio{{
    text-align:center;
}}

.mx-col-cat{{
    display:block;
    font-size:10px;
    font-weight:600;
    color:#9AA1BD;
    text-transform:none;
    letter-spacing:0;
    margin-bottom:2px;
}}

.mx-col-peso{{
    display:block;
    font-size:10.5px;
    font-weight:600;
    color:#B7BDD6;
    text-transform:none;
    margin-top:2px;
}}

.mx-detalle-link{{
    display:inline-block;
    padding:5px 12px;
    border-radius:8px;
    background:{ACCENT_SOFT};
    color:{ACCENT_DARK};
    font-weight:700;
    font-size:12.5px;
    text-decoration:none;
    white-space:nowrap;
    border:1px solid #F3C6D0;
}}

.mx-detalle-link:hover{{
    background:{ACCENT};
    color:white;
    border-color:{ACCENT};
}}

/* -------------------- Info de empresa -------------------- */

.company-hero{{
    background:linear-gradient(135deg, {NAVY} 0%, #2A2F55 100%);
    border-radius:16px;
    padding:26px 28px;
    color:white;
    margin-bottom:20px;
}}

.company-hero .razon{{
    font-size:24px;
    font-weight:800;
    margin:0 0 4px 0;
}}

.company-hero .cuit{{
    font-size:13.5px;
    color:#C6CAE6;
    margin:0 0 14px 0;
}}

.metric-card{{
    background:white;
    border-radius:14px;
    padding:18px 20px;
    box-shadow:0 2px 14px rgba(15,23,42,.06);
    border:1px solid #EEF0F6;
    text-align:left;
}}

.mini-timeline-track{{
    position:relative;
    height:4px;
    background:#EEF0F6;
    border-radius:3px;
    margin:22px 6px 10px 6px;
}}

.mini-timeline-dot{{
    position:absolute;
    top:-5px;
    width:14px;
    height:14px;
    border-radius:50%;
    background:{ACCENT};
    border:2px solid white;
    box-shadow:0 0 0 2px {ACCENT};
    transform:translateX(-50%);
}}

.mini-timeline-labels{{
    display:flex;
    justify-content:space-between;
    font-size:12px;
    font-weight:600;
    color:#9AA1BF;
    margin:0 6px;
}}

.metric-card .label{{
    font-size:12.5px;
    color:#8B93B8;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.04em;
    margin-bottom:6px;
}}

.metric-card .value{{
    font-size:22px;
    font-weight:800;
    color:#161B33;
}}

.badge-riesgo{{
    display:inline-block;
    padding:5px 14px;
    border-radius:20px;
    font-weight:800;
    font-size:13px;
}}

/* -------------------- Detalle / grillas -------------------- */

.section-label{{
    font-size:12px;
    font-weight:800;
    letter-spacing:.08em;
    text-transform:uppercase;
    color:#9AA1BF;
    margin: 4px 0 10px 2px;
}}

.detail-grid{{
    display:grid;
    grid-template-columns:repeat(3, 1fr);
    gap:14px 22px;
}}

.detail-item .dl-label{{
    font-size:11.5px;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.04em;
    color:#9AA1BF;
    margin-bottom:3px;
}}

.detail-item .dl-value{{
    font-size:14.5px;
    font-weight:600;
    color:#1F2430;
    line-height:1.35;
}}

.mono{{
    font-family:"Cascadia Code","Consolas",monospace;
    font-size:12.5px;
    color:#4B5265;
}}

.subcard{{
    background:#FAFBFD;
    border:1px solid #EEF0F6;
    border-radius:12px;
    padding:16px 18px;
    height:100%;
}}

.subcard .sub-head{{
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-bottom:10px;
}}

.subcard .sub-title{{
    font-size:14.5px;
    font-weight:700;
    color:#161B33;
}}

.subcard .sub-text{{
    font-size:13px;
    color:#4B5265;
    line-height:1.45;
    margin-top:6px;
}}

/* -------------------- Historial -------------------- */

.timeline-item{{
    position:relative;
    padding:2px 0 22px 26px;
    border-left:2px solid #EEF0F6;
    margin-left:8px;
}}

.timeline-item:last-child{{
    border-left:2px solid transparent;
}}

.timeline-dot{{
    position:absolute;
    left:-7px;
    top:4px;
    width:12px;
    height:12px;
    border-radius:50%;
    background:{ACCENT};
    border:2px solid white;
    box-shadow:0 0 0 2px {ACCENT};
}}

.timeline-card{{
    background:white;
    border-radius:12px;
    padding:16px 18px;
    box-shadow:0 2px 14px rgba(15,23,42,.06);
    border:1px solid #EEF0F6;
}}

.timeline-fecha{{
    font-size:12.5px;
    font-weight:700;
    color:{ACCENT_DARK};
    letter-spacing:.02em;
}}

.timeline-titulo{{
    font-size:15.5px;
    font-weight:700;
    color:#161B33;
    margin:2px 0 4px 0;
}}

.timeline-desc{{
    font-size:13.5px;
    color:#4B5265;
    margin:0 0 8px 0;
}}

.timeline-meta{{
    font-size:12px;
    color:#9AA1BF;
}}

/* -------------------- Tabs -------------------- */

button[data-baseweb="tab"]{{
    font-weight:600;
    font-size:14.5px;
}}

button[data-baseweb="tab"][aria-selected="true"]{{
    color:{ACCENT} !important;
}}

div[data-baseweb="tab-highlight"]{{
    background-color:{ACCENT} !important;
}}

/* -------------------- Empty state -------------------- */

.empty-state{{
    background:white;
    border:1px dashed #D8DCEA;
    border-radius:14px;
    padding:50px 20px;
    text-align:center;
    color:#8B93B8;
}}

.empty-state .icon{{
    font-size:34px;
    margin-bottom:10px;
}}

.empty-state h4{{
    color:#4B5265;
    font-size:16px;
    margin:0 0 4px 0;
}}

/* -------------------- File uploader -------------------- */

div[data-testid="stFileUploaderDropzone"]{{
    background:white;
    border-radius:10px;
}}

</style>
""", unsafe_allow_html=True)


# ==========================================================
# VARIABLES DE SESIÓN
# ==========================================================

if "pagina" not in st.session_state:
    st.session_state.pagina = "documento"

if "documento" not in st.session_state:
    st.session_state.documento = None

if "resultado" not in st.session_state:
    st.session_state.resultado = None

if "db_initialized" not in st.session_state:
    if DB_OK:
        try:
            _db_init = Database()
            _db_init.create_tables()
            _db_init.close()
        except Exception as e:
            DB_ERROR = f"{type(e).__name__}: {e}"
    st.session_state.db_initialized = True
    st.session_state.db_error = DB_ERROR

if "criterios_habilitantes" not in st.session_state:
    if criteria_backend is not None:
        try:
            criteria_backend.initialize_criteria()
            filas = criteria_backend.get_all()
            st.session_state.criterios_habilitantes = [
                {
                    "id": f["id"],
                    "categoria": f["categoria"],
                    "campo": f["campo"],
                    "descripcion": f["descripcion"],
                    "tipo": f["tipo"] if "tipo" in f.keys() else "Texto",
                    "orden": f["orden"] if "orden" in f.keys() else 0,
                    "activo": bool(f["activo"]),
                    "peso": f["peso"] if "peso" in f.keys() and f["peso"] is not None else 10,
                }
                for f in filas
            ]
        except Exception:
            st.session_state.criterios_habilitantes = []
    else:
        st.session_state.criterios_habilitantes = []

if "form_add_habilitante" not in st.session_state:
    st.session_state.form_add_habilitante = False


# ==========================================================
# HELPERS
# ==========================================================

def page_header(titulo: str, subtitulo: str = ""):
    st.markdown(
        f"""
        <div class="page-header">
            <h1>{titulo}</h1>
            {f'<p>{subtitulo}</p>' if subtitulo else ''}
            <div class="rule"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_riesgo(nivel):
    nivel = (nivel or "").upper()
    colores = {
        "BAJO": ("#E7F8EE", "#12805C"),
        "MEDIO": ("#FEF6E7", "#B7791F"),
        "ALTO": ("#FDECEE", ACCENT_DARK),
    }
    bg, fg = colores.get(nivel, ("#F1F3F9", "#4B5265"))
    return f'<span class="badge-riesgo" style="background:{bg};color:{fg};">{nivel or "SIN DATO"}</span>'


def _icono_semaforo(nivel: str) -> str:
    """Dibuja un semáforo (3 círculos apilados: rojo, amarillo, verde)
    con el que corresponda 'encendido' según el nivel, bien resaltado.
    Se construye con CSS puro (no es un emoji), reutilizando los mismos
    colores que ya usa el resto de la app."""

    encendidos = {
        "ROJO": ACCENT_DARK,
        "AMARILLO": "#B7791F",
        "VERDE": "#12805C",
    }
    apagado = "#E2E5EE"

    circulos = ""
    for estado in ("ROJO", "AMARILLO", "VERDE"):
        if estado == nivel:
            color = encendidos[estado]
            tamano = "26px"
            sombra = f"box-shadow:0 0 0 5px {color}33, 0 0 14px {color}99;"
        else:
            color = apagado
            tamano = "16px"
            sombra = ""
        circulos += (
            f'<span style="display:block;width:{tamano};height:{tamano};border-radius:50%;'
            f'background:{color};margin:6px auto;{sombra}"></span>'
        )

    return (
        '<div style="background:#F7F8FB;border:1px solid #EEF0F6;border-radius:12px;'
        'padding:14px 10px;display:inline-block;">' + circulos + "</div>"
    )


def _render_semaforo(scoring: dict):
    """Tarjeta de semáforo de riesgo (verde / amarillo / rojo) según el
    scoring calculado a partir de los criterios activos y su ponderación."""

    nivel = scoring["nivel"]
    score = scoring["score"]

    # Se reutilizan los mismos 3 colores que ya usa el badge de riesgo
    # (verde / amarillo / rojo), sin introducir una paleta nueva.
    colores = {
        "VERDE": ("#E7F8EE", "#12805C"),
        "AMARILLO": ("#FEF6E7", "#B7791F"),
        "ROJO": ("#FDECEE", ACCENT_DARK),
        "SIN DATOS": ("#F1F3F9", "#4B5265"),
    }
    bg, fg = colores.get(nivel, colores["SIN DATOS"])

    st.markdown('<div class="card"><h3>Semáforo de riesgo</h3>', unsafe_allow_html=True)

    sc1, sc2 = st.columns([1, 2.4])

    with sc1:
        texto_score = f"{score}/100" if score is not None else "—"
        st.markdown(
            f'<div style="text-align:center;">{_icono_semaforo(nivel)}'
            f'<div style="margin-top:8px;font-size:12.5px;color:#8B93B8;">{texto_score}</div></div>',
            unsafe_allow_html=True,
        )

    with sc2:
        evaluaciones = scoring["evaluaciones"]
        en_rojo = [e for e in evaluaciones if e["estado"] == "rojo"]
        en_verde = [e for e in evaluaciones if e["estado"] == "verde"]
        neutrales = [e for e in evaluaciones if e["estado"] == "neutral"]

        if not evaluaciones:
            st.markdown(
                '<p class="desc">No hay criterios activos para calcular el semáforo. '
                'Activá o agregá criterios en "Documento y Criterios".</p>',
                unsafe_allow_html=True,
            )
        elif score is None:
            st.markdown(
                '<p class="desc">Ninguno de los criterios activos pudo evaluarse con la '
                'información disponible en este documento.</p>',
                unsafe_allow_html=True,
            )
        else:
            partes = []
            if en_verde:
                partes.append(f"{len(en_verde)} criterio(s) en verde")
            if en_rojo:
                partes.append(f"{len(en_rojo)} criterio(s) en rojo")
            if neutrales:
                partes.append(f"{len(neutrales)} sin datos suficientes")
            st.markdown(
                f'<p class="desc">{", ".join(partes)}. Ponderación evaluada: {scoring["peso_evaluado"]}% '
                f'del total de criterios activos.</p>',
                unsafe_allow_html=True,
            )

            if en_rojo:
                motivos = "".join(
                    f'<li style="margin-bottom:4px;"><strong>{e["campo"]}:</strong> {e["motivo"]}</li>'
                    for e in en_rojo
                )
                st.markdown(
                    f'<p class="desc" style="margin-bottom:4px;"><strong>Motivos principales:</strong></p>'
                    f'<ul style="margin:0;padding-left:18px;color:#4B5265;font-size:13px;line-height:1.5;">{motivos}</ul>',
                    unsafe_allow_html=True,
                )
            st.caption("Ver el detalle completo por criterio en “Historial Detallado”.")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_scoring_por_criterio(scoring: dict):
    """Lista, agrupada por categoría, del estado (verde / rojo / sin
    datos) de cada criterio activo, con su motivo."""

    st.markdown("### Calificación por criterio")
    st.caption(
        "Estado de cada criterio activo según la información extraída del documento, "
        "con el motivo de la calificación."
    )

    evaluaciones = scoring["evaluaciones"]

    if not evaluaciones:
        empty_state(
            "Sin criterios activos",
            "Activá o agregá criterios en “Documento y Criterios” para ver la calificación aquí.",
        )
        return

    etiqueta_estado = {"verde": "Cumple", "rojo": "No cumple", "neutral": "Sin datos"}

    chip_clase = {"verde": "chip-green", "rojo": "chip-red", "neutral": "chip-neutral"}

    categorias = sorted({e["categoria"] for e in evaluaciones})
    for cat in categorias:
        grupo = [e for e in evaluaciones if e["categoria"] == cat]
        st.markdown(f'<div class="section-label">{cat}</div>', unsafe_allow_html=True)
        for e in grupo:
            with st.container(border=True):
                cc1, cc2 = st.columns([4, 1])
                with cc1:
                    st.markdown(f"**{e['campo']}**  ·  <span class=\"mono\">peso {e['peso']}%</span>", unsafe_allow_html=True)
                    st.caption(e["motivo"])
                with cc2:
                    st.markdown(
                        f'<span class="status-chip {chip_clase[e["estado"]]}">{etiqueta_estado[e["estado"]]}</span>',
                        unsafe_allow_html=True,
                    )
        st.write("")


def empty_state(titulo, texto, icono=""):
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="icon">{icono}</div>
            <h4>{titulo}</h4>
            <p>{texto}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def valor(v, default="—"):
    if v is None or v == "":
        return default
    return v


def moneda(v, default="—"):
    if isinstance(v, (int, float)):
        return f"$ {v:,.0f}".replace(",", ".")
    return valor(v, default)


def si_no(v, default="—"):
    if isinstance(v, bool):
        return "Sí" if v else "No"
    if v is None or v == "":
        return default
    return v


def detail_grid(pairs, cols=3):
    """pairs: lista de (label, value). Renderiza una grilla de ficha técnica."""
    items_html = "".join(
        f'<div class="detail-item"><div class="dl-label">{label}</div>'
        f'<div class="dl-value">{value}</div></div>'
        for label, value in pairs
    )
    st.markdown(
        f'<div class="detail-grid" style="grid-template-columns:repeat({cols}, 1fr);">{items_html}</div>',
        unsafe_allow_html=True,
    )


CATEGORY_COLORS = [
    ("#EEF2FF", "#4338CA"),
    ("#ECFEFF", "#0E7490"),
    ("#FDF4FF", "#A21CAF"),
    ("#FFF7ED", "#C2410C"),
    ("#F0FDF4", "#15803D"),
    ("#FEF2F2", ACCENT_DARK),
    ("#F5F3FF", "#6D28D9"),
]


def categoria_chip(categoria: str):
    idx = sum(ord(c) for c in categoria) % len(CATEGORY_COLORS)
    bg, fg = CATEGORY_COLORS[idx]
    return f'<span class="status-chip" style="background:{bg};color:{fg};margin:0;">{categoria}</span>'


# ----------------------------------------------------------
# Motor de scoring: evalúa cada criterio ACTIVO contra la
# información extraída del documento y produce, para cada uno,
# un estado (verde / rojo / neutral) con su motivo, además de
# un puntaje global ponderado por el peso de cada criterio.
# ----------------------------------------------------------

_PALABRAS_RIESGO_HISTORIAL = (
    "rechazado", "rechazada", "embargo", "quiebra", "concurso",
    "mora", "incumplimiento", "ejecución", "juicio", "demanda",
)


def _evaluar_criterio(criterio: dict, resultado: dict):
    """Devuelve (estado, motivo) para un criterio, donde estado es
    'verde', 'rojo' o 'neutral' (no se pudo evaluar con los datos
    disponibles)."""

    categoria = (criterio.get("categoria") or "").strip().lower()
    campo = (criterio.get("campo") or "").strip().lower()

    empresa = resultado.get("empresa", {})
    identificacion = empresa.get("identificacion", {})
    constitucion = empresa.get("constitucion", {})
    indicadores = resultado.get("indicadores", {})
    historial = resultado.get("historial", [])

    if categoria == "empresa":
        if "antigü" in campo or "antigu" in campo:
            antiguedad = constitucion.get("antiguedad_anios")
            if antiguedad is None:
                return "neutral", "El documento no informa la antigüedad de la empresa."
            if antiguedad < 2:
                return "rojo", f"La empresa tiene {antiguedad} año(s), por debajo del mínimo esperado (2 años)."
            return "verde", f"La empresa tiene {antiguedad} años de antigüedad."
        # Razón social, CUIT, Actividad, etc.: se evalúa si el dato existe.
        valores_posibles = {
            "razón social": identificacion.get("razon_social"),
            "razon social": identificacion.get("razon_social"),
            "cuit": identificacion.get("cuit"),
            "actividad": empresa.get("actividad", {}).get("descripcion"),
        }
        dato = valores_posibles.get(campo)
        if dato:
            return "verde", f"El dato '{criterio.get('campo')}' fue encontrado en el documento."
        return "rojo", f"El dato '{criterio.get('campo')}' no fue encontrado en el documento."

    if categoria == "consultas":
        cantidad = indicadores.get("consultas", {}).get("cantidad")
        if cantidad is None:
            return "neutral", "El documento no informa la cantidad de consultas."
        if cantidad > 10:
            return "rojo", f"Se registraron {cantidad} consultas, por encima del umbral de referencia (10)."
        return "verde", f"Se registraron {cantidad} consultas, dentro del rango esperado."

    if categoria == "deudas":
        existe = indicadores.get("deuda_fiscal", {}).get("existe")
        if existe is None:
            return "neutral", "El documento no informa si existe deuda fiscal."
        if existe:
            monto = indicadores.get("deuda_fiscal", {}).get("monto_total")
            return "rojo", f"Existe deuda fiscal vigente{f' por {moneda(monto)}' if monto else ''}."
        return "verde", "No se registra deuda fiscal vigente."

    if categoria == "cheques":
        rechazados = indicadores.get("cheques", {}).get("cantidad_rechazados")
        if rechazados is None:
            return "neutral", "El documento no informa cheques rechazados."
        if rechazados > 0:
            return "rojo", f"Se registran {rechazados} cheque(s) rechazado(s)."
        return "verde", "No se registran cheques rechazados."

    if categoria == "historial":
        if not historial:
            return "neutral", "El documento no registra eventos de historial."
        eventos_riesgo = [
            e for e in historial
            if any(
                p in ((e.get("titulo") or "") + " " + (e.get("descripcion") or "") + " " + (e.get("categoria") or "")).lower()
                for p in _PALABRAS_RIESGO_HISTORIAL
            )
        ]
        if eventos_riesgo:
            return "rojo", f"Se detectaron {len(eventos_riesgo)} evento(s) de historial con antecedentes negativos (ej: {eventos_riesgo[0].get('titulo') or eventos_riesgo[0].get('categoria')})."
        return "verde", f"Se registran {len(historial)} evento(s) de historial, sin antecedentes negativos detectados."

    # Categoría personalizada, sin regla de evaluación definida todavía.
    return "neutral", "No hay una regla de evaluación automática definida para esta categoría."


def calcular_scoring(resultado: dict):
    """Evalúa todos los criterios ACTIVOS contra el resultado del
    análisis y devuelve un dict con:
      - evaluaciones: lista de {id, categoria, campo, peso, estado, motivo}
      - peso_evaluado / peso_verde
      - score: 0-100 (o None si no hay criterios evaluables)
      - nivel: 'VERDE' | 'AMARILLO' | 'ROJO' | 'SIN DATOS'
    """

    criterios_activos = [c for c in st.session_state.get("criterios_habilitantes", []) if c.get("activo")]

    evaluaciones = []
    for criterio in criterios_activos:
        estado, motivo = _evaluar_criterio(criterio, resultado)
        evaluaciones.append(
            {
                "id": criterio["id"],
                "categoria": criterio.get("categoria", "General"),
                "campo": criterio.get("campo", ""),
                "peso": criterio.get("peso", 10),
                "estado": estado,
                "motivo": motivo,
            }
        )

    evaluables = [e for e in evaluaciones if e["estado"] in ("verde", "rojo")]
    peso_evaluado = sum(e["peso"] for e in evaluables)
    peso_verde = sum(e["peso"] for e in evaluables if e["estado"] == "verde")

    if peso_evaluado > 0:
        score = round(100 * peso_verde / peso_evaluado)
    else:
        score = None

    if score is None:
        nivel = "SIN DATOS"
    elif score >= 70:
        nivel = "VERDE"
    elif score >= 40:
        nivel = "AMARILLO"
    else:
        nivel = "ROJO"

    return {
        "evaluaciones": evaluaciones,
        "peso_evaluado": peso_evaluado,
        "peso_verde": peso_verde,
        "score": score,
        "nivel": nivel,
    }


# ----------------------------------------------------------
# Persistencia en SQLite (Documents / Companies / CompanyIndicators / CompanyHistory)
# ----------------------------------------------------------

def guardar_resultado_en_db(documento: dict, resultado: dict):
    """
    Guarda la empresa, los indicadores y el historial en la base SQLite,
    asociados al documento (el documento en sí puede haberse guardado
    antes, sin análisis). Si esa empresa ya había sido analizada para
    este mismo documento, no la vuelve a insertar: recupera el registro
    existente.
    Devuelve (document_id, company_id, mensaje, ya_existia).
    """
    if not DB_OK:
        return None, None, "La base de datos no está disponible.", False

    # 1) Asegurar que el documento exista (o recuperarlo si ya estaba).
    document_id, _ya_existia_doc = guardar_documento_en_db(documento)

    if document_id is None:
        return None, None, "No se pudo guardar el documento en la base de datos.", False

    # 2) Ver si esa empresa (Companies) YA fue analizada para este documento.
    db = Database()
    fila_empresa = db.fetchone(
        "SELECT id FROM Companies WHERE document_id = ?", (document_id,)
    )
    db.close()

    if fila_empresa is not None:
        company_id = fila_empresa["id"]
        return document_id, company_id, "Este documento ya había sido analizado antes. Se cargó el registro existente.", True

    # 3) Todavía no hay empresa para este documento: guardarla ahora.
    company_id = save_company(document_id, resultado.get("empresa", {}))
    save_indicators(company_id, resultado.get("indicadores", {}))
    save_history(company_id, resultado.get("historial", []))

    return document_id, company_id, "Análisis guardado en la base de datos.", False


def guardar_documento_en_db(documento: dict):
    """
    Guarda (o recupera si ya existe por hash) SOLO el registro del documento,
    sin requerir un resultado de análisis. Así, aunque Azure no esté configurado
    o el análisis falle, el documento leído queda de todas formas registrado
    en la base de datos y se puede verificar que el guardado funciona.
    Devuelve (document_id, ya_existia).
    """
    if not DB_OK:
        return None, False

    db = Database()
    fila_doc = db.fetchone(
        "SELECT id FROM Documents WHERE hash_pdf = ?", (documento.get("hash"),)
    )
    db.close()

    if fila_doc is not None:
        return fila_doc["id"], True

    document_id = save_document(documento)
    return document_id, False


def estado_base_datos():
    """Devuelve (total_documentos, total_empresas_guardadas) para poder
    verificar en pantalla que la información sí está persistiendo."""
    if not DB_OK:
        return None
    db = Database()
    total_docs = db.fetchone("SELECT COUNT(*) AS total FROM Documents")["total"]
    total_empresas = db.fetchone("SELECT COUNT(*) AS total FROM Companies")["total"]
    db.close()
    return total_docs, total_empresas


def listar_analisis_por_empresa(cuit=None, razon_social=None):
    """Lista todos los análisis (Companies) guardados para la misma empresa,
    identificada por CUIT (preferido) o por razón social, ordenados del más
    reciente al más antiguo según la fecha de proceso del documento."""
    if not DB_OK:
        return []

    db = Database()
    if cuit:
        filas = db.fetchall(
            """
            SELECT c.id AS company_id, c.razon_social, c.cuit,
                   d.id AS document_id, d.nombre_pdf, d.fecha_proceso
            FROM Companies c
            JOIN Documents d ON d.id = c.document_id
            WHERE c.cuit = ?
            ORDER BY d.fecha_proceso DESC
            """,
            (cuit,),
        )
    elif razon_social:
        filas = db.fetchall(
            """
            SELECT c.id AS company_id, c.razon_social, c.cuit,
                   d.id AS document_id, d.nombre_pdf, d.fecha_proceso
            FROM Companies c
            JOIN Documents d ON d.id = c.document_id
            WHERE c.razon_social = ?
            ORDER BY d.fecha_proceso DESC
            """,
            (razon_social,),
        )
    else:
        filas = []
    db.close()
    return filas


def formatear_fecha_ddmmaaaa(fecha_str):
    """Convierte 'YYYY-MM-DD HH:MM:SS' (o 'YYYY-MM-DD') a 'DD/MM/AAAA'."""
    if not fecha_str:
        return "—"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(fecha_str, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return str(fecha_str)


def listar_empresas_guardadas():
    if not DB_OK:
        return []
    db = Database()
    filas = db.fetchall(
        """
        SELECT c.id AS company_id, c.razon_social, c.cuit,
               d.id AS document_id, d.nombre_pdf, d.fecha_proceso
        FROM Companies c
        JOIN Documents d ON d.id = c.document_id
        ORDER BY d.fecha_proceso DESC
        """
    )
    db.close()
    return filas


def cargar_resultado_desde_db(company_id: int):
    """Reconstruye 'documento' y 'resultado' a partir de lo guardado en SQLite,
    con la misma forma que produce el análisis con IA, para reutilizar
    exactamente las mismas pantallas."""
    db = Database()

    company = db.fetchone("SELECT * FROM Companies WHERE id = ?", (company_id,))
    if company is None:
        db.close()
        return None, None

    document = db.fetchone("SELECT * FROM Documents WHERE id = ?", (company["document_id"],))
    indicadores_row = db.fetchone(
        "SELECT * FROM CompanyIndicators WHERE company_id = ?", (company_id,)
    )
    historial_rows = db.fetchall(
        "SELECT * FROM CompanyHistory WHERE company_id = ? ORDER BY fecha DESC", (company_id,)
    )
    db.close()

    documento = {
        "nombre": document["nombre_pdf"],
        "paginas": document["paginas"],
        "palabras": document["palabras"],
        "caracteres": document["caracteres"],
        "tamano_kb": document["tamano_kb"],
        "hash": document["hash_pdf"],
        "fecha_proceso": document["fecha_proceso"],
        "tiempo_proceso": document["tiempo_proceso"],
    }

    resultado = {
        "empresa": {
            "identificacion": {
                "razon_social": company["razon_social"],
                "cuit": company["cuit"],
            },
            "actividad": {
                "codigo": company["actividad_codigo"],
                "descripcion": company["actividad_descripcion"],
            },
            "constitucion": {
                "fecha": company["fecha_constitucion"],
                "antiguedad_anios": company["antiguedad_anios"],
            },
        },
        "indicadores": {
            "consultas": {
                "cantidad": indicadores_row["consultas"] if indicadores_row else None,
                "periodo": indicadores_row["periodo_consultas"] if indicadores_row else None,
            },
            "deuda_fiscal": {
                "existe": bool(indicadores_row["deuda_fiscal"]) if indicadores_row and indicadores_row["deuda_fiscal"] is not None else None,
                "ultimo_periodo": indicadores_row["ultimo_periodo"] if indicadores_row else None,
                "monto_total": indicadores_row["monto_deuda"] if indicadores_row else None,
                "detalle": indicadores_row["detalle_deuda"] if indicadores_row else None,
            },
            "cheques": {
                "cantidad_rechazados": indicadores_row["cheques_rechazados"] if indicadores_row else None,
                "monto_total": indicadores_row["monto_cheques"] if indicadores_row else None,
                "tipo": indicadores_row["tipo_cheques"] if indicadores_row else None,
                "detalle": indicadores_row["detalle_cheques"] if indicadores_row else None,
            },
            "riesgo": {
                "nivel": indicadores_row["riesgo_nivel"] if indicadores_row else None,
                "puntaje": indicadores_row["riesgo_puntaje"] if indicadores_row else None,
                "justificacion": indicadores_row["riesgo_justificacion"] if indicadores_row else None,
            },
        },
        "historial": [
            {
                "fecha": h["fecha"],
                "categoria": h["categoria"],
                "titulo": h["titulo"],
                "descripcion": h["descripcion"],
                "valor": h["valor"],
                "monto": h["monto"],
                "pagina": h["pagina"],
            }
            for h in historial_rows
        ],
        "observaciones": {},
    }

    return documento, resultado


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

    st.markdown(
        """
        <div class="sidebar-logo-row">
            <div class="sidebar-logo-box">NS</div>
            <div class="sidebar-brand">
                <h1>Corporate<br/>Intelligence</h1>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<p class='sidebar-caption'>NOSIS ANALISIS </p>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    nav_items = [
        ("documento",  " Documento y Criterios"),
        ("empresa", " Información de la Empresa"),
        ("historial", " Historial Detallado"),
        ("matriz", " Matriz de Criterios"),
    ]

    for key, label in nav_items:
        activo = st.session_state.pagina == key
        if st.button(
            label,
            key=f"nav_{key}",
            type="primary" if activo else "secondary",
            use_container_width=True,
        ):
            st.session_state.pagina = key
            st.rerun()

    st.markdown("<hr/>", unsafe_allow_html=True)

    st.markdown("<p class='sidebar-caption'>Seleccionar Empresa</p>", unsafe_allow_html=True)

    empresas_guardadas = listar_empresas_guardadas() if DB_OK else []

    if not DB_OK:
        st.caption(" Base de datos no disponible")
        if DB_ERROR:
            st.code(DB_ERROR, language=None)
    elif not empresas_guardadas:
        st.caption("Todavía no hay empresas guardadas.")
    else:
        opciones = {
            f"{e['razon_social'] or e['nombre_pdf']} · {formatear_fecha_ddmmaaaa(e['fecha_proceso'])}": e["company_id"]
            for e in empresas_guardadas
        }
        seleccion = st.multiselect(
            "Elegí una o más empresas",
            list(opciones.keys()),
            key="select_empresas_guardadas",
            label_visibility="collapsed",
            placeholder="Buscar empresa…",
        )
        if len(seleccion) == 1:
            company_id = opciones[seleccion[0]]
            # Se compara contra la última selección hecha DESDE ESTA CAJA
            # (no contra company_id en general), para que elegir una empresa
            # siempre te lleve a verla, aunque ya sea la que se acaba de analizar.
            if st.session_state.get("_selector_empresa_ultimo") != company_id:
                documento_cargado, resultado_cargado = cargar_resultado_desde_db(company_id)
                if resultado_cargado is not None:
                    st.session_state.documento = documento_cargado
                    st.session_state.resultado = resultado_cargado
                    st.session_state.company_id = company_id
                    st.session_state._selector_empresa_ultimo = company_id
                    st.session_state.pagina = "empresa"
                    st.rerun()
        elif len(seleccion) > 1:
            st.caption(f"{len(seleccion)} empresas elegidas — elegí una sola para verla en detalle.")
        else:
            st.session_state._selector_empresa_ultimo = None

    st.markdown("<hr/>", unsafe_allow_html=True)

    if not AZURE_OK:
        st.caption(" Azure AI no configurado (.env)")

    st.markdown(
        "<div class='sidebar-footer'>Nosis </div>",
        unsafe_allow_html=True,
    )


# ==========================================================
# PÁGINA 1 · DOCUMENTO Y CRITERIOS
# ==========================================================

def pagina_documento():

    page_header(
        "Documento y Criterios",
        "Administra la lista de criterios utilizados para analizar el documento base.",
    )

    st.markdown("### Criterios — Editar, Agregar o Eliminar")
    st.caption(
        "Estos criterios determinan qué información se extrae del documento base "
        "cuando se sube y analiza el PDF en “Historial Detallado”."
    )

    render_criterios_habilitantes()


def _peso_disponible(excluir_id=None):
    """Suma el peso de los criterios ACTIVOS (sin contar `excluir_id`,
    útil al editar un criterio existente) y devuelve (disponible, usado),
    donde disponible = cuánto se le puede asignar a un criterio más sin
    que el total activo supere el 100%."""
    usado = sum(
        c.get("peso", 0)
        for c in st.session_state.criterios_habilitantes
        if c["activo"] and c["id"] != excluir_id
    )
    disponible = max(0, 100 - usado)
    return disponible, usado


def render_criterios_habilitantes():

    if st.session_state.get("_criterio_error"):
        st.error(st.session_state.pop("_criterio_error"))

    # IDs de criterios cuyo switch "Activo" hay que forzar a apagado en
    # ESTE run, antes de que el widget se dibuje (Streamlit no permite
    # tocar el session_state de un widget después de instanciado).
    _forzar_off = st.session_state.pop("_forzar_toggle_off", set())

    if st.button("  Agregar criterio habilitante", key="btn_add_habilitante"):
        st.session_state.form_add_habilitante = not st.session_state.form_add_habilitante

    if st.session_state.form_add_habilitante:
        disponible, usado = _peso_disponible()
        with st.form("form_habilitante", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.4, 1.4, 1])
            categoria = c1.text_input("Categoría", placeholder="Ej: Empresa")
            campo = c2.text_input("Campo", placeholder="Ej: Razón Social")
            tipo = c3.selectbox("Tipo de dato", ["Texto", "Número", "Fecha", "Booleano"])
            descripcion = st.text_area("Descripción", placeholder="¿Qué información representa este criterio y de dónde se extrae?")
            st.caption(
                f"Ponderación ya asignada a criterios activos: {usado}%. "
                f"Podés asignarle hasta {disponible}% a este nuevo criterio para no superar el 100% total."
            )
            peso = st.slider(
                "Ponderación en el scoring de riesgo (%)",
                min_value=0, max_value=100, value=min(10, disponible),
                help="Qué tanto pesa este criterio en el puntaje total de la empresa. La suma de todos los criterios activos no puede superar 100%.",
            )
            enviado = st.form_submit_button("Guardar criterio", type="primary")

            if enviado and campo:
                if peso > disponible:
                    st.error(
                        f"No se puede guardar: con {peso}% la ponderación total activa sería "
                        f"{usado + peso}%, más del 100% permitido. Bajá este valor a {disponible}% "
                        f"como máximo, o desactivá/reducí otro criterio primero."
                    )
                else:
                    nuevo_id = max([c["id"] for c in st.session_state.criterios_habilitantes], default=0) + 1
                    nuevo_orden = max([c.get("orden", 0) for c in st.session_state.criterios_habilitantes], default=0) + 1
                    st.session_state.criterios_habilitantes.append(
                        {
                            "id": nuevo_id,
                            "categoria": categoria or "General",
                            "campo": campo,
                            "descripcion": descripcion,
                            "tipo": tipo,
                            "orden": nuevo_orden,
                            "activo": True,
                            "peso": peso,
                        }
                    )
                    if criteria_backend is not None:
                        try:
                            criteria_backend.add(categoria or "General", campo, descripcion, tipo=tipo, orden=nuevo_orden, peso=peso)
                        except Exception:
                            pass
                    st.session_state.form_add_habilitante = False
                    st.rerun()


    st.write("")

    if not st.session_state.criterios_habilitantes:
        empty_state("Sin criterios habilitantes", "Agrega el primer criterio para comenzar.")
        return

    total = len(st.session_state.criterios_habilitantes)
    activos = sum(1 for c in st.session_state.criterios_habilitantes if c["activo"])
    peso_total_activo = sum(c.get("peso", 0) for c in st.session_state.criterios_habilitantes if c["activo"])
    if peso_total_activo == 100:
        chip_peso = "chip-green"
    elif peso_total_activo > 100:
        chip_peso = "chip-red"
    else:
        chip_peso = "chip-yellow"
    st.markdown(
        f'<span class="status-chip chip-neutral">{total} criterios</span>'
        f'<span class="status-chip chip-green">{activos} activos</span>'
        f'<span class="status-chip chip-yellow">{total - activos} inactivos</span>'
        f'<span class="status-chip {chip_peso}">Ponderación activa: {peso_total_activo}%</span>',
        unsafe_allow_html=True,
    )
    if peso_total_activo != 100:
        st.caption(
            "La ponderación de los criterios activos debería sumar 100% para que el "
            "puntaje de riesgo sea comparable entre empresas. Ajustá los pesos con "
            "\"Editar\" en cada criterio."
        )
    st.write("")

    # Agrupar por categoría para una vista más detallada
    categorias_ordenadas = sorted(
        {c["categoria"] for c in st.session_state.criterios_habilitantes}
    )

    for categoria in categorias_ordenadas:
        grupo = sorted(
            [c for c in st.session_state.criterios_habilitantes if c["categoria"] == categoria],
            key=lambda c: c.get("orden", 0),
        )
        st.markdown(
            f'<div class="section-label">{categoria} &nbsp;·&nbsp; {len(grupo)} criterio(s)</div>',
            unsafe_allow_html=True,
        )

        for crit in grupo:
            with st.container(border=True):
                c1, c2, c3, c4, c5, c6 = st.columns([3.4, 0.9, 1, 1.1, 0.7, 0.7])
                with c1:
                    st.markdown(f"**{crit['campo']}**")
                    if crit.get("descripcion"):
                        st.caption(crit["descripcion"])
                with c2:
                    st.markdown(
                        f'<span class="status-chip chip-neutral">{crit.get("tipo","Texto")}</span>',
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.markdown(
                        f'<span class="status-chip chip-neutral">Peso {crit.get("peso", 10)}%</span>',
                        unsafe_allow_html=True,
                    )
                with c4:
                    if crit["id"] in _forzar_off:
                        st.session_state[f"toggle_hab_{crit['id']}"] = False
                        crit["activo"] = False

                    nuevo_estado = st.toggle(
                        "Activo",
                        value=crit["activo"],
                        key=f"toggle_hab_{crit['id']}",
                        label_visibility="visible",
                    )
                    if nuevo_estado != crit["activo"]:
                        if nuevo_estado:
                            # Se está ACTIVANDO: verificar que no se supere el 100%.
                            disponible_act, _usado_act = _peso_disponible(excluir_id=crit["id"])
                            if crit.get("peso", 0) > disponible_act:
                                pendientes = st.session_state.get("_forzar_toggle_off", set())
                                pendientes.add(crit["id"])
                                st.session_state["_forzar_toggle_off"] = pendientes
                                st.session_state["_criterio_error"] = (
                                    f"No se pudo activar '{crit['campo']}': con su ponderación de "
                                    f"{crit.get('peso', 0)}% el total activo superaría el 100% "
                                    f"(solo quedan {disponible_act}% disponibles). Bajá su peso o "
                                    f"desactivá/reducí otro criterio primero."
                                )
                                st.rerun()
                            else:
                                crit["activo"] = nuevo_estado
                                if criteria_backend is not None:
                                    try:
                                        criteria_backend.set_active(crit["id"], nuevo_estado)
                                    except Exception:
                                        pass
                        else:
                            # Desactivar siempre está permitido (libera ponderación).
                            crit["activo"] = nuevo_estado
                            if criteria_backend is not None:
                                try:
                                    criteria_backend.set_active(crit["id"], nuevo_estado)
                                except Exception:
                                    pass
                with c5:
                    if st.button("Editar", key=f"edit_hab_{crit['id']}", help="Editar criterio"):
                        st.session_state.editando_criterio_id = (
                            None if st.session_state.get("editando_criterio_id") == crit["id"] else crit["id"]
                        )
                        st.rerun()
                with c6:
                    if st.button("Eliminar", key=f"del_hab_{crit['id']}", help="Eliminar criterio"):
                        st.session_state.criterios_habilitantes = [
                            c for c in st.session_state.criterios_habilitantes if c["id"] != crit["id"]
                        ]
                        if criteria_backend is not None:
                            try:
                                criteria_backend.delete(crit["id"])
                            except Exception:
                                pass
                        if st.session_state.get("editando_criterio_id") == crit["id"]:
                            st.session_state.editando_criterio_id = None
                        st.rerun()

                if st.session_state.get("editando_criterio_id") == crit["id"]:
                    with st.form(f"form_editar_{crit['id']}"):
                        ec1, ec2, ec3 = st.columns([1.4, 1.4, 1])
                        edit_categoria = ec1.text_input("Categoría", value=crit["categoria"], key=f"ecat_{crit['id']}")
                        edit_campo = ec2.text_input("Campo", value=crit["campo"], key=f"ecampo_{crit['id']}")
                        tipos = ["Texto", "Número", "Fecha", "Booleano"]
                        tipo_actual = crit.get("tipo", "Texto")
                        edit_tipo = ec3.selectbox(
                            "Tipo de dato",
                            tipos,
                            index=tipos.index(tipo_actual) if tipo_actual in tipos else 0,
                            key=f"etipo_{crit['id']}",
                        )
                        edit_descripcion = st.text_area(
                            "Descripción",
                            value=crit.get("descripcion", ""),
                            key=f"edesc_{crit['id']}",
                        )
                        disponible_edit, usado_otros_edit = _peso_disponible(excluir_id=crit["id"])
                        st.caption(
                            f"Ponderación usada por los demás criterios activos: {usado_otros_edit}%. "
                            f"Si este criterio está activo, podés asignarle hasta {disponible_edit}% "
                            f"para no superar el 100% total."
                            if crit["activo"] else
                            f"Este criterio está inactivo, así que su peso todavía no suma al total "
                            f"(hoy usado por los activos: {usado_otros_edit}%)."
                        )
                        edit_peso = st.slider(
                            "Ponderación en el scoring de riesgo (%)",
                            min_value=0, max_value=100,
                            value=int(crit.get("peso", 10)),
                            key=f"epeso_{crit['id']}",
                            help="Qué tanto pesa este criterio en el puntaje total de la empresa. La suma de todos los criterios activos no puede superar 100%.",
                        )
                        fc1, fc2 = st.columns([1, 1])
                        guardar = fc1.form_submit_button("Guardar cambios", type="primary", use_container_width=True)
                        cancelar = fc2.form_submit_button("Cancelar", use_container_width=True)

                        if guardar and edit_campo:
                            if crit["activo"] and edit_peso > disponible_edit:
                                st.error(
                                    f"No se puede guardar: con {edit_peso}% la ponderación total activa "
                                    f"sería {usado_otros_edit + edit_peso}%, más del 100% permitido. "
                                    f"Bajá este valor a {disponible_edit}% como máximo, o desactivá/reducí "
                                    f"otro criterio primero."
                                )
                            else:
                                crit["categoria"] = edit_categoria or "General"
                                crit["campo"] = edit_campo
                                crit["descripcion"] = edit_descripcion
                                crit["tipo"] = edit_tipo
                                crit["peso"] = edit_peso
                                if criteria_backend is not None:
                                    try:
                                        criteria_backend.update(
                                            crit["id"],
                                            crit["categoria"],
                                            crit["campo"],
                                            crit["descripcion"],
                                            tipo=crit["tipo"],
                                            peso=crit["peso"],
                                        )
                                    except Exception:
                                        pass
                            st.session_state.editando_criterio_id = None
                            st.rerun()

                        if cancelar:
                            st.session_state.editando_criterio_id = None
                            st.rerun()

        st.write("")


# ==========================================================
# PÁGINA 2 · INFORMACIÓN DE LA EMPRESA
# ==========================================================

def pagina_empresa():

    page_header(
        "Información de la Empresa",
        "Datos generales de identificación y del documento analizado.",
    )

    resultado = st.session_state.resultado

    if not resultado:
        empty_state(
            "Todavía no hay información",
            "Sube y analiza un documento en “Historial Detallado” para ver los datos aquí.",
        )
        return

    empresa = resultado.get("empresa", {})
    identificacion = empresa.get("identificacion", {})
    actividad = empresa.get("actividad", {})
    constitucion = empresa.get("constitucion", {})
    indicadores = resultado.get("indicadores", {})
    observaciones = resultado.get("observaciones", {})

    consultas = indicadores.get("consultas", {})
    deuda = indicadores.get("deuda_fiscal", {})
    cheques = indicadores.get("cheques", {})
    riesgo = indicadores.get("riesgo", {})

    documento = st.session_state.documento or {}

    # ---------- Hero ----------
    st.markdown(
        f"""
        <div class="company-hero">
            <div class="razon">{valor(identificacion.get('razon_social'))}</div>
            <div class="cuit">CUIT {valor(identificacion.get('cuit'))} &nbsp;·&nbsp;
            {valor(actividad.get('descripcion'))} &nbsp;·&nbsp;
            {valor(constitucion.get('antiguedad_anios'), '—')} años de antigüedad</div>
            {badge_riesgo(riesgo.get('nivel'))}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- Semáforo de riesgo (scoring por criterios) ----------
    scoring = calcular_scoring(resultado)
    _render_semaforo(scoring)

    # ---------- Identificación detallada ----------
    st.markdown('<div class="card"><h3>Identificación de la empresa</h3>', unsafe_allow_html=True)
    detail_grid(
        [
            ("Razón social", valor(identificacion.get("razon_social"))),
            ("CUIT", valor(identificacion.get("cuit"))),
            ("Código de actividad", valor(actividad.get("codigo"))),
            ("Descripción de actividad", valor(actividad.get("descripcion"))),
            ("Fecha de constitución", valor(constitucion.get("fecha"))),
            ("Antigüedad", f"{valor(constitucion.get('antiguedad_anios'), '—')} años" if constitucion.get("antiguedad_anios") is not None else "—"),
        ],
        cols=3,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------- Documento analizado ----------
    if documento:
        st.markdown('<div class="card"><h3>Documento analizado</h3>', unsafe_allow_html=True)
        detail_grid(
            [
                ("Archivo", valor(documento.get("nombre"))),
                ("Páginas", valor(documento.get("paginas"))),
                ("Palabras", valor(documento.get("palabras"))),
                ("Caracteres", valor(documento.get("caracteres"))),
                ("Tamaño", f"{valor(documento.get('tamano_kb'), '—')} KB" if documento.get("tamano_kb") is not None else "—"),
                ("Fecha de proceso", valor(documento.get("fecha_proceso"))),
                ("Tiempo de proceso", f"{valor(documento.get('tiempo_proceso'), '—')} s" if documento.get("tiempo_proceso") is not None else "—"),
                ("Hash SHA-256", f'<span class="mono">{documento.get("hash","—")[:24]}…</span>' if documento.get("hash") else "—"),
            ],
            cols=4,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
# PÁGINA 3 · HISTORIAL DETALLADO
# ==========================================================

def _render_seccion_subir_documento():
    """Bloque de subida y análisis del PDF, usado en Historial Detallado."""

    st.markdown(
        """
        <div class="card">
            <h3>Subir documento</h3>
            <p class="desc">Este es el documento base con el que se generará el análisis de la empresa.</p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="dropzone-wrap">', unsafe_allow_html=True)
    archivo = st.file_uploader(
        "Arrastra o selecciona el documento (PDF)",
        type=["pdf"],
        label_visibility="visible",
        key="uploader_historial",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    analizar = st.button(
        " Analizar documento",
        type="primary",
        use_container_width=True,
        disabled=archivo is None,
        key="btn_analizar_historial",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------- Estado real de la base de datos (para verificar guardado) ----------
    stats = estado_base_datos()
    if stats is not None:
        total_docs, total_empresas = stats
        st.caption(
            f"Base de datos: **{total_docs}** documento(s) y **{total_empresas}** "
            f"análisis de empresa guardados actualmente."
        )
    else:
        st.caption("La base de datos no está disponible en este momento.")
        if DB_ERROR:
            st.code(DB_ERROR, language=None)

    if not AZURE_OK:
        st.warning(
            "El análisis con IA (Azure) no está configurado o faltan credenciales en `.env` "
            "(`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT`). "
            "El documento igual se puede leer y guardar, pero no se podrán extraer los datos de la empresa."
        )

    if analizar and archivo is not None:
        with st.spinner("Analizando documento..."):
            try:
                if build_document is None:
                    raise RuntimeError("El módulo pdf_reader no está disponible.")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(archivo.read())
                    ruta = tmp.name

                documento = build_document(ruta)
                st.session_state.documento = documento

                # --------------------------------------------------
                # Guardar SIEMPRE el documento, haya o no análisis IA,
                # para poder verificar que la persistencia funciona.
                # --------------------------------------------------
                try:
                    doc_id, ya_existia_doc = guardar_documento_en_db(documento)
                    st.session_state.document_id = doc_id
                except Exception as e:
                    doc_id, ya_existia_doc = None, False
                    st.warning(f"No se pudo guardar el documento en la base de datos: {e}")

                if AZURE_OK:
                    resultado_analizado = analizar_empresa(documento["texto_completo"])
                    st.session_state.resultado = resultado_analizado

                    if guardar_json is not None:
                        try:
                            guardar_json(documento["nombre"], resultado_analizado)
                        except Exception:
                            pass

                    try:
                        doc_id, comp_id, mensaje_db, ya_existia = guardar_resultado_en_db(documento, resultado_analizado)
                        st.session_state.document_id = doc_id
                        st.session_state.company_id = comp_id
                        if ya_existia:
                            st.info(mensaje_db)
                        elif doc_id is not None:
                            st.success(f"{mensaje_db}")
                    except sqlite3.IntegrityError as e:
                        st.warning(f"No se pudo guardar en la base de datos (registro duplicado): {e}")
                    except Exception as e:
                        st.warning(f"El análisis se completó, pero no se pudo guardar en la base de datos: {e}")

                    st.success("Documento procesado correctamente.")
                else:
                    if doc_id is not None:
                        if ya_existia_doc:
                            st.info("Este documento (mismo PDF) ya estaba guardado en la base de datos.")
                        else:
                            st.success("Documento leído y guardado en la base de datos (sin análisis IA).")
                    st.warning(
                        "Documento leído correctamente, pero el análisis con IA "
                        "no está disponible (falta configurar Azure en .env)."
                    )

                os.remove(ruta)
                st.rerun()

            except Exception as e:
                st.error(f"No se pudo procesar el documento: {e}")


def _render_linea_de_tiempo(historial, resultado=None):
    categorias = sorted({(item.get("categoria") or "General") for item in historial})

    # ---------- Resumen visual en forma de línea de tiempo ----------
    montos = [item.get("monto") for item in historial if isinstance(item.get("monto"), (int, float))]
    suma_montos = sum(montos)

    # El historial viene ordenado del evento más reciente al más antiguo;
    # para dibujar la línea de izquierda (antiguo) a derecha (reciente) se invierte.
    orden_cronologico = list(reversed(historial))
    n = len(orden_cronologico)

    dots_html = ""
    for i, item in enumerate(orden_cronologico):
        pos = 0 if n <= 1 else (i / (n - 1)) * 100
        titulo_evento = valor(item.get("titulo"), "Evento")
        fecha_evento = valor(item.get("fecha"), "")
        dots_html += f'<span class="mini-timeline-dot" style="left:{pos}%;" title="{fecha_evento} · {titulo_evento}"></span>'

    fecha_inicial = valor(orden_cronologico[0].get("fecha")) if orden_cronologico else "—"
    fecha_final = valor(orden_cronologico[-1].get("fecha")) if orden_cronologico else "—"

    st.markdown(f'<div class="mini-timeline-track">{dots_html}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="mini-timeline-labels"><span>{fecha_inicial}</span><span>{fecha_final}</span></div>',
        unsafe_allow_html=True,
    )

    st.write("")

    resumen_partes = [f"{len(historial)} evento(s)", f"{len(categorias)} categoría(s)"]
    if montos:
        resumen_partes.append(f"{len(montos)} con monto asociado")
        resumen_partes.append(f"total acumulado {moneda(suma_montos)}")
    st.markdown(
        f'<p class="desc" style="margin:0 0 10px 0;">{" · ".join(resumen_partes)}.</p>',
        unsafe_allow_html=True,
    )

    st.write("")
    st.markdown(
        "".join(categoria_chip(f"{c} ({sum(1 for i in historial if (i.get('categoria') or 'General') == c)})") for c in categorias),
        unsafe_allow_html=True,
    )

    st.write("")
    st.divider()

    # ---------- Filtros (incluye la fecha/versión del análisis) ----------
    opciones_fecha, company_id_actual = _opciones_analisis_anteriores(resultado) if resultado else ({}, None)

    fc0, fc1, fc2, fc3 = st.columns([1.3, 1.3, 1.7, 1])

    with fc0:
        if len(opciones_fecha) > 1:
            etiquetas = list(opciones_fecha.keys())
            etiqueta_actual = next(
                (k for k, v in opciones_fecha.items() if v == company_id_actual),
                etiquetas[0],
            )
            fecha_elegida = st.selectbox(
                "Fecha del análisis",
                etiquetas,
                index=etiquetas.index(etiqueta_actual),
                key="select_fecha_analisis_historial",
            )
            company_id_elegido = opciones_fecha[fecha_elegida]
            if company_id_elegido != company_id_actual:
                documento_cargado, resultado_cargado = cargar_resultado_desde_db(company_id_elegido)
                if resultado_cargado is not None:
                    st.session_state.documento = documento_cargado
                    st.session_state.resultado = resultado_cargado
                    st.session_state.company_id = company_id_elegido
                    st.rerun()
        else:
            st.selectbox(
                "Fecha del análisis",
                ["Único análisis disponible"],
                disabled=True,
                key="select_fecha_analisis_historial_unico",
            )
    with fc1:
        filtro = st.selectbox("Categoría", ["Todas"] + categorias)
    with fc2:
        busqueda = st.text_input("Buscar en título o descripción", placeholder="Ej: cheque, deuda, embargo…")
    with fc3:
        orden = st.selectbox("Orden", ["Más reciente primero", "Más antiguo primero"])

    eventos = list(historial)
    if filtro != "Todas":
        eventos = [e for e in eventos if (e.get("categoria") or "General") == filtro]
    if busqueda:
        b = busqueda.lower()
        eventos = [
            e for e in eventos
            if b in (e.get("titulo") or "").lower() or b in (e.get("descripcion") or "").lower()
        ]
    if orden == "Más antiguo primero":
        eventos = list(reversed(eventos))

    st.caption(f"Mostrando {len(eventos)} de {len(historial)} eventos.")
    st.write("")

    if not eventos:
        empty_state("Sin resultados", "Ajusta la búsqueda o el filtro de categoría.")
        return

    for item in eventos:
        categoria = item.get("categoria") or "General"

        monto = item.get("monto")
        monto_html = f'<span class="status-chip chip-neutral" style="margin:0;">{moneda(monto)}</span>' if isinstance(monto, (int, float)) else ""

        valor_campo = item.get("valor")
        valor_html = f'<span class="status-chip chip-neutral" style="margin:0;">Valor: {valor_campo}</span>' if valor_campo not in (None, "") else ""

        st.markdown(
            f"""
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-card">
                    <div class="timeline-fecha">{valor(item.get('fecha'))} &nbsp;·&nbsp; {categoria_chip(categoria)}</div>
                    <div class="timeline-titulo">{valor(item.get('titulo'), 'Evento sin título')}</div>
                    <p class="timeline-desc">{valor(item.get('descripcion'), 'Sin descripción disponible.')}</p>
                    <div style="margin:6px 0 8px 0;">{monto_html} {valor_html}</div>
                    <div class="timeline-meta"> Página {valor(item.get('pagina'))}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_indicadores_de_riesgo(indicadores):
    consultas = indicadores.get("consultas", {})
    deuda = indicadores.get("deuda_fiscal", {})
    cheques = indicadores.get("cheques", {})
    riesgo = indicadores.get("riesgo", {})

    st.markdown("### Indicadores de riesgo")
    st.caption("Detalle completo de cada indicador extraído del documento.")

    ic1, ic2 = st.columns(2, gap="large")

    with ic1:
        st.markdown(
            f"""
            <div class="subcard">
                <div class="sub-head">
                    <span class="sub-title"> Consultas</span>
                </div>
            """,
            unsafe_allow_html=True,
        )
        detail_grid(
            [
                ("Cantidad", valor(consultas.get("cantidad"))),
                ("Período", valor(consultas.get("periodo"))),
            ],
            cols=2,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")

        existe_deuda = deuda.get("existe")
        chip_deuda = "chip-red" if existe_deuda else ("chip-green" if existe_deuda is False else "chip-neutral")
        st.markdown(
            f"""
            <div class="subcard">
                <div class="sub-head">
                    <span class="sub-title"> Deuda fiscal</span>
                    <span class="status-chip {chip_deuda}">{si_no(existe_deuda)}</span>
                </div>
            """,
            unsafe_allow_html=True,
        )
        detail_grid(
            [
                ("Monto total", moneda(deuda.get("monto_total"))),
                ("Último período", valor(deuda.get("ultimo_periodo"))),
            ],
            cols=2,
        )
        if deuda.get("detalle"):
            st.markdown(f'<p class="sub-text">{deuda.get("detalle")}</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with ic2:
        st.markdown(
            f"""
            <div class="subcard">
                <div class="sub-head">
                    <span class="sub-title"> Cheques</span>
                </div>
            """,
            unsafe_allow_html=True,
        )
        detail_grid(
            [
                ("Rechazados", valor(cheques.get("cantidad_rechazados"))),
                ("Monto total", moneda(cheques.get("monto_total"))),
                ("Tipo", valor(cheques.get("tipo"))),
            ],
            cols=3,
        )
        if cheques.get("detalle"):
            st.markdown(f'<p class="sub-text">{cheques.get("detalle")}</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")

        st.markdown(
            f"""
            <div class="subcard">
                <div class="sub-head">
                    <span class="sub-title"> Nivel de riesgo</span>
                    {badge_riesgo(riesgo.get('nivel'))}
                </div>
            """,
            unsafe_allow_html=True,
        )
        puntaje = riesgo.get("puntaje")
        if isinstance(puntaje, (int, float)):
            st.progress(min(max(int(puntaje), 0), 100) / 100, text=f"Puntaje: {puntaje}/100")
        else:
            st.caption("Puntaje: —")
        if riesgo.get("justificacion"):
            st.markdown(f'<p class="sub-text">{riesgo.get("justificacion")}</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def _render_observaciones(observaciones):
    st.markdown("### Observaciones")

    if observaciones.get("resumen_general"):
        st.markdown(
            f'<div class="card"><p class="desc" style="font-size:14.5px;color:#374151;">{observaciones.get("resumen_general")}</p></div>',
            unsafe_allow_html=True,
        )

    oc1, oc2, oc3 = st.columns(3)

    with oc1:
        st.markdown('<div class="card"><h3> Fortalezas</h3>', unsafe_allow_html=True)
        items = observaciones.get("fortalezas") or []
        if items:
            for it in items:
                st.markdown(f"- {it}")
        else:
            st.caption("Sin datos.")
        st.markdown("</div>", unsafe_allow_html=True)

    with oc2:
        st.markdown('<div class="card"><h3> Riesgos</h3>', unsafe_allow_html=True)
        items = observaciones.get("riesgos") or []
        if items:
            for it in items:
                st.markdown(f"- {it}")
        else:
            st.caption("Sin datos.")
        st.markdown("</div>", unsafe_allow_html=True)

    with oc3:
        st.markdown('<div class="card"><h3> Recomendaciones</h3>', unsafe_allow_html=True)
        items = observaciones.get("recomendaciones") or []
        if items:
            for it in items:
                st.markdown(f"- {it}")
        else:
            st.caption("Sin datos.")
        st.markdown("</div>", unsafe_allow_html=True)


def _opciones_analisis_anteriores(resultado):
    """Devuelve (opciones, company_id_actual) para el selector de
    'Fecha del análisis' que vive en la fila de filtros de la línea de
    tiempo. `opciones` es {etiqueta: company_id}, ordenado del análisis
    más reciente al más antiguo (por CUIT o, si no hay, por razón social)."""

    if not DB_OK or not resultado:
        return {}, None

    empresa = resultado.get("empresa", {})
    identificacion = empresa.get("identificacion", {})
    cuit = identificacion.get("cuit")
    razon_social = identificacion.get("razon_social")

    if not cuit and not razon_social:
        return {}, None

    analisis = listar_analisis_por_empresa(cuit=cuit, razon_social=razon_social)
    company_id_actual = st.session_state.get("company_id")

    opciones = {}
    for a in analisis:
        fecha_fmt = formatear_fecha_ddmmaaaa(a["fecha_proceso"])
        marca_actual = " (actual)" if a["company_id"] == company_id_actual else ""
        etiqueta = f"{fecha_fmt} · {a['nombre_pdf']}{marca_actual}"
        opciones[etiqueta] = a["company_id"]

    return opciones, company_id_actual


def pagina_historial():

    page_header(
        "Historial Detallado",
        "Sube el documento, revisa indicadores de riesgo, observaciones y la línea de tiempo de eventos.",
    )

    # ------------------------------------------------------
    # SUBIR Y ANALIZAR DOCUMENTO
    # ------------------------------------------------------
    _render_seccion_subir_documento()

    st.divider()

    resultado = st.session_state.resultado

    if not resultado:
        empty_state(
            "Todavía no hay historial",
            "Sube y analiza un documento arriba para ver el historial, los indicadores de riesgo y las observaciones aquí.",
        )
        return

    # ---------- Línea de tiempo (incluye el selector de fecha/versión del análisis) ----------
    historial = resultado.get("historial", [])

    if not historial:
        empty_state("Sin eventos registrados", "El documento no arrojó eventos de historial.")
    else:
        _render_linea_de_tiempo(historial, resultado)

    st.divider()

    # ---------- Calificación por criterio (verde / rojo) ----------
    scoring = calcular_scoring(resultado)
    _render_scoring_por_criterio(scoring)

    st.divider()

    # ---------- Indicadores de riesgo ----------
    _render_indicadores_de_riesgo(resultado.get("indicadores", {}))

    st.divider()

    # ---------- Observaciones ----------
    _render_observaciones(resultado.get("observaciones", {}))


def _estado_final_peor_caso(evaluaciones):
    """Regla de 'peor caso' para el estado final de una empresa:
    si al menos un criterio quedó en rojo (Alerta) -> ROJO.
    Si no hay rojo pero al menos uno quedó en neutral (Revisión) -> AMARILLO.
    Si todos los evaluados están en verde -> VERDE.
    Si no hay ningún criterio para evaluar -> SIN DATOS.
    Es decir: la empresa NO puede quedar "Aprobada" si tiene aunque sea
    un solo criterio en Revisión o en Alerta."""

    if not evaluaciones:
        return "SIN DATOS"
    if any(e["estado"] == "rojo" for e in evaluaciones):
        return "ROJO"
    if any(e["estado"] == "neutral" for e in evaluaciones):
        return "AMARILLO"
    return "VERDE"


def _resumen_porque_matriz(evaluaciones):
    """Texto corto que explica el estado final: qué criterios están en
    Alerta y cuáles en Revisión (los que bajan a la empresa de Aprobado)."""

    en_alerta = [e["campo"] for e in evaluaciones if e["estado"] == "rojo"]
    en_revision = [e["campo"] for e in evaluaciones if e["estado"] == "neutral"]

    partes = []
    if en_alerta:
        partes.append("Alerta en " + ", ".join(en_alerta))
    if en_revision:
        partes.append("Revisión en " + ", ".join(en_revision))

    if not partes:
        if evaluaciones:
            return "Todos los criterios evaluados están Aprobados."
        return "Sin criterios evaluables."

    return "; ".join(partes) + "."


def pagina_matriz():

    page_header(
        "Matriz de Criterios",
        "Vista horizontal: cada fila es una empresa, cada columna un criterio. "
        "Si un criterio queda en revisión o en alerta, la empresa no puede quedar aprobada.",
    )

    # Colores por estado, reutilizando siempre la misma paleta (verde/amarillo/rojo)
    # que ya usa el resto de la app. El color va SOLO en un punto, sin la palabra.
    COLOR_ESTADO = {
        "verde": "#12805C",
        "rojo": ACCENT_DARK,
        "neutral": "#B7791F",
    }
    NIVEL_INFO = {
        "VERDE":     {"label": "Aprobado",  "chip": "chip-green"},
        "AMARILLO":  {"label": "Revisión",  "chip": "chip-yellow"},
        "ROJO":      {"label": "Alerta",    "chip": "chip-red"},
        "SIN DATOS": {"label": "Sin datos", "chip": "chip-neutral"},
    }

    # ---------- Armar la lista de empresas a mostrar ----------
    empresas = []  # cada item: {razon_social, cuit, nombre_pdf, fecha, resultado}

    if DB_OK:
        for e in listar_empresas_guardadas():
            _doc, _res = cargar_resultado_desde_db(e["company_id"])
            if _res is None:
                continue
            empresas.append(
                {
                    "razon_social": e["razon_social"] or e["nombre_pdf"] or "Empresa sin nombre",
                    "cuit": e["cuit"],
                    "nombre_pdf": e["nombre_pdf"],
                    "fecha": formatear_fecha_ddmmaaaa(e["fecha_proceso"]),
                    "resultado": _res,
                    "company_id": e["company_id"],
                }
            )

    if not empresas and st.session_state.resultado:
        # Sin base de datos disponible (o sin nada guardado todavía):
        # al menos se muestra la empresa cargada actualmente en pantalla.
        _res = st.session_state.resultado
        _ident = _res.get("empresa", {}).get("identificacion", {})
        _doc = st.session_state.get("documento") or {}
        empresas.append(
            {
                "razon_social": _ident.get("razon_social") or _doc.get("nombre") or "Empresa actual",
                "cuit": _ident.get("cuit"),
                "nombre_pdf": _doc.get("nombre"),
                "fecha": formatear_fecha_ddmmaaaa(_doc.get("fecha_proceso")),
                "resultado": _res,
                "company_id": st.session_state.get("company_id"),
            }
        )

    if not empresas:
        empty_state(
            "Todavía no hay empresas para mostrar",
            "Subí y analizá un documento en “Historial Detallado” para que la empresa aparezca acá "
            "automáticamente, con todos sus criterios.",
        )
        return

    criterios_activos = sorted(
        [c for c in st.session_state.get("criterios_habilitantes", []) if c.get("activo")],
        key=lambda c: (c.get("categoria", ""), c.get("orden", 0)),
    )
    if not criterios_activos:
        empty_state(
            "Sin criterios activos",
            "Activá o agregá criterios en “Documento y Criterios” para ver la matriz aquí.",
        )
        return

    # ---------- Filtros ----------
    categorias_disp = sorted({c.get("categoria", "General") for c in criterios_activos})
    f1, f2 = st.columns([2, 2])
    with f1:
        cat_filtro = st.multiselect(
            "Columnas de criterios a mostrar (por categoría)",
            categorias_disp,
            default=categorias_disp,
            key="matriz_filtro_categoria",
        )
    with f2:
        estado_filtro = st.multiselect(
            "Filtrar empresas por estado final",
            ["Aprobado", "Revisión", "Alerta", "Sin datos"],
            default=["Aprobado", "Revisión", "Alerta", "Sin datos"],
            key="matriz_filtro_estado",
        )

    columnas_criterios = [c for c in criterios_activos if c.get("categoria", "General") in cat_filtro]

    if not columnas_criterios:
        empty_state(
            "Sin columnas para mostrar",
            "Elegí al menos una categoría en el filtro de arriba.",
        )
        return

    # ---------- Calcular fila por empresa ----------
    filas_empresas = []
    for emp in empresas:
        scoring = calcular_scoring(emp["resultado"])
        por_id = {e["id"]: e for e in scoring["evaluaciones"]}
        nivel_final = _estado_final_peor_caso(scoring["evaluaciones"])
        nivel_info = NIVEL_INFO.get(nivel_final, NIVEL_INFO["SIN DATOS"])

        if nivel_info["label"] not in estado_filtro:
            continue

        porque = _resumen_porque_matriz(scoring["evaluaciones"])

        filas_empresas.append(
            {
                "empresa": emp,
                "por_id": por_id,
                "scoring": scoring,
                "nivel_info": nivel_info,
                "porque": porque,
            }
        )

    st.write("")

    if not filas_empresas:
        st.caption("Ninguna empresa coincide con el filtro de estado seleccionado.")
        return

    # ---------- Armar la tabla horizontal única ----------
    columnas_header_html = ""
    for crit in columnas_criterios:
        columnas_header_html += (
            f'<th class="mx-col-criterio">'
            f'<span class="mx-col-cat">{html.escape(crit.get("categoria", ""))}</span>'
            f'{html.escape(crit.get("campo", ""))}'
            f'<span class="mx-col-peso">peso {crit.get("peso", 10)}%</span>'
            f"</th>"
        )

    filas_html = ""
    for fila in filas_empresas:
        emp = fila["empresa"]
        por_id = fila["por_id"]
        nivel_info = fila["nivel_info"]
        score = fila["scoring"]["score"]
        score_texto = f"{score}/100" if score is not None else "—"

        celdas_criterios = ""
        for crit in columnas_criterios:
            evaluacion = por_id.get(crit["id"])
            if evaluacion is None:
                color = "#E2E5EE"
                titulo = "Este criterio no estaba activo cuando se analizó este documento."
            else:
                color = COLOR_ESTADO.get(evaluacion["estado"], "#E2E5EE")
                titulo = f'{crit.get("campo","")}: {evaluacion["motivo"]}'
            celdas_criterios += (
                f'<td class="mx-crit-cell" title="{html.escape(titulo)}">'
                f'<span class="mx-estado-dot" style="background:{color};"></span>'
                f"</td>"
            )

        cuit_html = f'CUIT {html.escape(str(emp["cuit"]))}' if emp.get("cuit") else ""

        _cid_emp = emp.get("company_id")
        detalle_href = f"?ver_empresa={_cid_emp}" if _cid_emp is not None else "?ver_empresa=actual"
        detalle_html = f'<a class="mx-detalle-link" href="{detalle_href}" target="_self">Ver detalle →</a>'

        filas_html += (
            "<tr>"
            f'<td class="mx-empresa mx-nombre-empresa">{html.escape(emp["razon_social"])}'
            f'{f"<br/><span style=\'font-weight:400;color:#9AA1BD;font-size:11.5px;\'>{cuit_html}</span>" if cuit_html else ""}'
            f"</td>"
            f'<td class="mx-score-grande">{score_texto}</td>'
            f'<td class="mx-fecha">{emp["fecha"]}</td>'
            f"{celdas_criterios}"
            f'<td class="mx-estado-final"><span class="status-chip {nivel_info["chip"]}">{nivel_info["label"]}</span></td>'
            f'<td class="mx-motivo">{html.escape(fila["porque"])}</td>'
            f'<td>{detalle_html}</td>'
            "</tr>"
        )

    st.markdown(
        f"""
        <div class="matrix-wrap">
            <table class="matrix-table">
                <thead>
                    <tr>
                        <th class="mx-empresa">Empresa</th>
                        <th>Score global</th>
                        <th>Fecha último análisis</th>
                        {columnas_header_html}
                        <th>Estado final</th>
                        <th>Por qué</th>
                        <th>Detalle por empresa</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_html}
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "El score global de cada empresa se calcula sobre el peso de los criterios con datos "
        "disponibles (verde vs. rojo); los criterios en Revisión no cuentan porque el documento "
        "no informa ese dato. El punto de color de cada criterio indica su calificación (pasá el "
        "mouse por encima para ver el motivo). Si una empresa tiene al menos un criterio en "
        "Revisión o en Alerta, su estado final no puede ser Aprobado. Hacé clic en “Ver detalle” "
        "para abrir el Historial Detallado de esa empresa."
    )




# ==========================================================
# CLIC EN "VER DETALLE" (DESDE LA MATRIZ DE CRITERIOS)
# ==========================================================
# El link de la tabla de la Matriz navega a "?ver_empresa=<id>".
# Streamlit no permite botones reales dentro de una tabla HTML armada
# a mano, así que se usa un link con query param: al hacer clic, el
# navegador recarga la página con ese parámetro, y acá se detecta,
# se carga la empresa correspondiente y se muestra "Historial Detallado".

if "ver_empresa" in st.query_params:
    _ver_valor = st.query_params.get("ver_empresa")

    if _ver_valor == "actual":
        if st.session_state.resultado:
            st.session_state.pagina = "historial"
    else:
        try:
            _cid_click = int(_ver_valor)
        except (TypeError, ValueError):
            _cid_click = None

        if _cid_click is not None and DB_OK:
            _doc_click, _res_click = cargar_resultado_desde_db(_cid_click)
            if _res_click is not None:
                st.session_state.documento = _doc_click
                st.session_state.resultado = _res_click
                st.session_state.company_id = _cid_click
                st.session_state.pagina = "historial"

    st.query_params.clear()
    st.rerun()


# ==========================================================
# ROUTER
# ==========================================================

paginas = {
    "documento": pagina_documento,
    "empresa": pagina_empresa,
    "historial": pagina_historial,
    "matriz": pagina_matriz,
}

paginas.get(st.session_state.pagina, pagina_documento)()