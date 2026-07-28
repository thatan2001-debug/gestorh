"""
Estilos CSS globales para Gestor RH IA.
Diseño limpio y profesional: blanco + azul corporativo.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Reset y base ── */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1B3F6E 0%, #0F2547 100%) !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: rgba(255,255,255,0.85) !important;
    font-size: 0.9rem !important;
    padding: 6px 0 !important;
    transition: color 0.2s;
}
[data-testid="stSidebar"] .stRadio label:hover {
    color: #ffffff !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: rgba(255,255,255,0.6) !important;
    font-size: 0.78rem !important;
}
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15) !important;
}

/* ── Área principal ── */
.main .block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 900px !important;
}

/* ── Títulos ── */
h1 {
    font-weight: 700 !important;
    font-size: 1.9rem !important;
    color: #111827 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.2 !important;
    margin-bottom: 0.3rem !important;
}
h2 {
    font-weight: 600 !important;
    font-size: 1.2rem !important;
    color: #1B3F6E !important;
    margin-top: 1.5rem !important;
}
h3 {
    font-weight: 600 !important;
    color: #374151 !important;
}

/* ── Botón primario ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2D6BE4 0%, #1B3F6E 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 1.5rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(45,107,228,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(45,107,228,0.4) !important;
}

/* ── Botón secundario ── */
.stButton > button[kind="secondary"] {
    border: 1.5px solid #2D6BE4 !important;
    color: #2D6BE4 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    background: white !important;
}

/* ── Cards de métricas ── */
[data-testid="metric-container"] {
    background: #F8FAFC !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 10px !important;
    padding: 1rem !important;
}
[data-testid="metric-container"] label {
    color: #6B7280 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #1B3F6E !important;
    font-weight: 700 !important;
}

/* ── Inputs ── */
.stTextInput input, .stSelectbox select {
    border-radius: 8px !important;
    border: 1.5px solid #D1D5DB !important;
    font-size: 0.93rem !important;
    transition: border-color 0.2s !important;
}
.stTextInput input:focus {
    border-color: #2D6BE4 !important;
    box-shadow: 0 0 0 3px rgba(45,107,228,0.1) !important;
}

/* ── Alertas ── */
.stAlert {
    border-radius: 8px !important;
    font-size: 0.9rem !important;
}

/* ── Divider ── */
hr {
    border-color: #E5E7EB !important;
    margin: 1.5rem 0 !important;
}

/* ── Tabla de datos ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid #E5E7EB !important;
}

/* ── Progress bar ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #2D6BE4, #1B3F6E) !important;
    border-radius: 4px !important;
}

/* ── Checkboxes ── */
.stCheckbox label {
    font-size: 0.95rem !important;
    color: #374151 !important;
}

/* ── Card plan ── */
.plan-card {
    background: white;
    border: 2px solid #E5E7EB;
    border-radius: 14px;
    padding: 1.5rem;
    text-align: center;
    transition: all 0.2s ease;
    height: 100%;
}
.plan-card:hover {
    border-color: #2D6BE4;
    box-shadow: 0 4px 20px rgba(45,107,228,0.12);
    transform: translateY(-2px);
}
.plan-card.destacado {
    border-color: #2D6BE4;
    background: linear-gradient(135deg, #EFF6FF 0%, #ffffff 100%);
}
.plan-precio {
    font-size: 2rem;
    font-weight: 700;
    color: #1B3F6E;
    line-height: 1;
}
.plan-periodo {
    font-size: 0.8rem;
    color: #9CA3AF;
    margin-bottom: 0.8rem;
}
.plan-feature {
    font-size: 0.85rem;
    color: #374151;
    margin: 0.3rem 0;
    text-align: left;
}
.badge-gratis {
    background: #D1FAE5;
    color: #065F46;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-popular {
    background: #2D6BE4;
    color: white;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-pro {
    background: #1B3F6E;
    color: white;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* ── Banner de límite/upgrade ── */
.banner-upgrade {
    background: linear-gradient(135deg, #1B3F6E 0%, #2D6BE4 100%);
    color: white;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin: 1rem 0;
}
.banner-upgrade h3 {
    color: white !important;
    margin: 0 0 0.3rem 0 !important;
}
.banner-upgrade p {
    color: rgba(255,255,255,0.85);
    margin: 0;
    font-size: 0.9rem;
}

/* ── Sidebar plan badge ── */
.sidebar-plan-badge {
    background: rgba(255,255,255,0.15);
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    margin: 0.5rem 0;
}
.sidebar-plan-nombre {
    font-weight: 700;
    font-size: 0.85rem;
    color: white;
}
.sidebar-plan-docs {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.7);
    margin-top: 2px;
}
</style>
"""
