import streamlit as st
import pandas as pd
import numpy as np
import os
import textwrap
import gc
import duckdb
import plotly.express as px

def _alternar_top_exclusivo(key):
    """Hace que 'Top 5' y 'Top 10 Subpartidas' sean mutuamente excluyentes:
    al activar uno de los dos, se desactiva automáticamente el otro."""
    actual = list(st.session_state.get(key, []))
    anterior = st.session_state.get(f"{key}_prev", [])
    if "Top 10 Subpartidas" in actual and "Top 10 Subpartidas" not in anterior and "Top 5 Subpartidas" in actual:
        actual = [s for s in actual if s != "Top 5 Subpartidas"]
    elif "Top 5 Subpartidas" in actual and "Top 5 Subpartidas" not in anterior and "Top 10 Subpartidas" in actual:
        actual = [s for s in actual if s != "Top 10 Subpartidas"]
    st.session_state[key] = actual
    st.session_state[f"{key}_prev"] = list(actual)

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Dashboard Comercio Binacional | Estados Unidos - México",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Avanzados - Heredados de tu versión anterior
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    @import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');
    
    .stApp {
        background-color: #F8FAFC;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #E2E8F0;
    }
    
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        border-radius: 8px;
        border: none;
        justify-content: flex-start; 
        text-align: left;
        padding: 10px 15px;
        background-color: transparent;
        color: #475569;
        box-shadow: none;
        margin-bottom: 4px;
        transition: all 0.2s ease-in-out;
        font-weight: 500;
    }
            
    [data-testid="stSidebarHeader"] {
        position: sticky !important;
        top: 0px !important;
        z-index: 999 !important;
        background-color: #ffffff !important;
        padding-bottom: 10px;
    }

    [data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
        background-color: #F1F5F9;
        color: #2596be;
    }

    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: #2596be !important;
        color: #ffffff !important; 
        font-weight: 700 !important;
        box-shadow: 0 4px 6px -1px rgba(37, 150, 190, 0.2), 0 2px 4px -1px rgba(37, 150, 190, 0.1) !important;
    }
    
    h1, h2, h3, h4 { color: #0F172A !important; font-weight: 800 !important; letter-spacing: -0.5px; }
    
    /* Ocultar la opción "Select All" del menú desplegable de los multiselect.
       Streamlit 1.55+ renderiza esta opción vía un portal (BaseWeb) que NO
       queda anidado dentro de stMultiSelect, por eso ya no lleva ese scope. */
    [aria-label^="Select all"],
    [aria-label^="Select all"] * {
        display: none !important;
        pointer-events: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Respaldo JS: oculta "Select All" y además cierra el hueco que deja la fila
# reservada por la virtualización del dropdown (cubre ambas gráficas, en un solo lugar).
st.components.v1.html("""
<script>
(function() {
    function ocultarSelectAll() {
        try {
            var doc = window.parent.document;
            var nodos = doc.querySelectorAll('li, div[role="option"], div[data-baseweb="menu-item"]');
            nodos.forEach(function(el) {
                var texto = (el.innerText || el.textContent || "").trim();
                var esSelectAll = texto === "Select all" || texto.indexOf("Select all (") === 0 || texto.indexOf("Select all matches") === 0;
                if (!esSelectAll) return;

                // Buscar el contenedor real reservado por la virtualización
                // (usa position:absolute + height fija para calcular el alto de la lista)
                var fila = el;
                var candidato = el;
                var profundidad = 0;
                while (candidato && profundidad < 6) {
                    if (candidato.style && candidato.style.position === "absolute" && candidato.style.height) {
                        fila = candidato;
                        break;
                    }
                    candidato = candidato.parentElement;
                    profundidad++;
                }
                if (fila.dataset.selectAllOculto) return;

                var alto = parseFloat(fila.style.height) || fila.offsetHeight || 0;
                var topOriginal = parseFloat(fila.style.top) || 0;

                fila.style.display = "none";
                fila.dataset.selectAllOculto = "1";

                // Subir las filas que quedaban debajo, para cerrar el espacio en blanco
                if (fila.parentElement && alto > 0) {
                    Array.prototype.forEach.call(fila.parentElement.children, function(hermano) {
                        if (hermano === fila || !hermano.style) return;
                        var top = parseFloat(hermano.style.top);
                        if (hermano.style.position === "absolute" && !isNaN(top) && top > topOriginal && !hermano.dataset.selectAllAjustado) {
                            hermano.style.top = (top - alto) + "px";
                            hermano.dataset.selectAllAjustado = "1";
                        }
                    });
                }
            });
        } catch (e) {}
    }
    var doc = window.parent.document;
    var observer = new MutationObserver(ocultarSelectAll);
    observer.observe(doc.body, { childList: true, subtree: true });
    ocultarSelectAll();
})();
</script>
""", height=0)

# ==========================================
# 2. CATÁLOGOS Y MAPEOS
# ==========================================
US_STATES = {
    'US': 'Nacional',
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
}

US_FIGURES = {
    'AL': 'Sen. Tommy Tuberville (Republicano) & Sen. Katie Britt (Republicano)', 'AK': 'Sen. Lisa Murkowski (Republicano) & Sen. Dan Sullivan (Republicano)',
    'AZ': 'Sen. Mark Kelly (Demócrata) & Sen. Kyrsten Sinema (Independiente)', 'AR': 'Sen. John Boozman (Republicano) & Sen. Tom Cotton (Republicano)',
    'CA': 'Sen. Alex Padilla (Demócrata) & Sen. Laphonza Butler (Demócrata)', 'CO': 'Sen. Michael Bennet (Demócrata) & Sen. John Hickenlooper (Demócrata)',
    'CT': 'Sen. Richard Blumenthal (Demócrata) & Sen. Chris Murphy (Demócrata)', 'DE': 'Sen. Tom Carper (Demócrata) & Sen. Chris Coons (Demócrata)',
    'FL': 'Sen. Marco Rubio (Republicano) & Sen. Rick Scott (Republicano)', 'GA': 'Sen. Jon Ossoff (Demócrata) & Sen. Raphael Warnock (Demócrata)',
    'HI': 'Sen. Brian Schatz (Demócrata) & Sen. Mazie Hirono (Demócrata)', 'ID': 'Sen. Mike Crapo (Republicano) & Sen. Jim Risch (Republicano)',
    'IL': 'Sen. Dick Durbin (Demócrata) & Sen. Tammy Duckworth (Demócrata)', 'IN': 'Sen. Todd Young (Republicano) & Sen. Mike Braun (Republicano)',
    'IA': 'Sen. Chuck Grassley (Republicano) & Sen. Joni Ernst (Republicano)', 'KS': 'Sen. Jerry Moran (Republicano) & Sen. Roger Marshall (Republicano)',
    'KY': 'Sen. Mitch McConnell (Republicano) & Sen. Rand Paul (Republicano)', 'LA': 'Sen. Bill Cassidy (Republicano) & Sen. John Kennedy (Republicano)',
    'ME': 'Sen. Susan Collins (Republicano) & Sen. Angus King (Independiente)', 'MD': 'Sen. Ben Cardin (Demócrata) & Sen. Chris Van Hollen (Demócrata)',
    'MA': 'Sen. Elizabeth Warren (Demócrata) & Sen. Ed Markey (Demócrata)', 'MI': 'Sen. Debbie Stabenow (Demócrata) & Sen. Gary Peters (Demócrata)',
    'MN': 'Sen. Amy Klobuchar (Demócrata) & Sen. Tina Smith (Demócrata)', 'MS': 'Sen. Roger Wicker (Republicano) & Sen. Cindy Hyde-Smith (Republicano)',
    'MO': 'Sen. Josh Hawley (Republicano) & Sen. Eric Schmitt (Republicano)', 'MT': 'Sen. Jon Tester (Demócrata) & Sen. Steve Daines (Republicano)',
    'NE': 'Sen. Deb Fischer (Republicano) & Sen. Pete Ricketts (Republicano)', 'NV': 'Sen. Catherine Cortez Masto (Demócrata) & Sen. Jacky Rosen (Demócrata)',
    'NH': 'Sen. Jeanne Shaheen (Demócrata) & Sen. Maggie Hassan (Demócrata)', 'NJ': 'Sen. Bob Menendez (Demócrata) & Sen. Cory Booker (Demócrata)',
    'NM': 'Sen. Martin Heinrich (Demócrata) & Sen. Ben Ray Luján (Demócrata)', 'NY': 'Sen. Chuck Schumer (Demócrata) & Sen. Kirsten Gillibrand (Demócrata)',
    'NC': 'Sen. Thom Tillis (Republicano) & Sen. Ted Budd (Republicano)', 'ND': 'Sen. John Hoeven (Republicano) & Sen. Kevin Cramer (Republicano)',
    'OH': 'Sen. Sherrod Brown (Demócrata) & Sen. J.D. Vance (Republicano)', 'OK': 'Sen. James Lankford (Republicano) & Sen. Markwayne Mullin (Republicano)',
    'OR': 'Sen. Ron Wyden (Demócrata) & Sen. Jeff Merkley (Demócrata)', 'PA': 'Sen. Bob Casey (Demócrata) & Sen. John Fetterman (Demócrata)',
    'RI': 'Sen. Jack Reed (Demócrata) & Sen. Sheldon Whitehouse (Demócrata)', 'SC': 'Sen. Lindsey Graham (Republicano) & Sen. Tim Scott (Republicano)',
    'SD': 'Sen. John Thune (Republicano) & Sen. Mike Rounds (Republicano)', 'TN': 'Sen. Marsha Blackburn (Republicano) & Sen. Bill Hagerty (Republicano)',
    'TX': 'Sen. John Cornyn (Republicano) & Sen. Ted Cruz (Republicano)', 'UT': 'Sen. Mike Lee (Republicano) & Sen. Mitt Romney (Republicano)',
    'VT': 'Sen. Bernie Sanders (Independiente) & Sen. Peter Welch (Demócrata)', 'VA': 'Sen. Mark Warner (Demócrata) & Sen. Tim Kaine (Demócrata)',
    'WA': 'Sen. Patty Murray (Demócrata) & Sen. Maria Cantwell (Demócrata)', 'WV': 'Sen. Joe Manchin (Independiente) & Sen. Shelley Moore Capito (Republicano)',
    'WI': 'Sen. Ron Johnson (Republicano) & Sen. Tammy Baldwin (Demócrata)', 'WY': 'Sen. John Barrasso (Republicano) & Sen. Cynthia Lummis (Republicano)'
}

US_TRADE_REPS = {
    'AL': '<b>Rep. Terri A. Sewell</b> (Demócrata)',
    'CA': '<b>Rep. Linda T. Sánchez</b> (Demócrata) - Líder de la minoría del subcomité | <b>Rep. Jimmy Panetta</b> (Demócrata) | <b>Rep. Judy Chu</b> (Demócrata)',
    'CT': '<b>Rep. John B. Larson</b> (Demócrata)',
    'FL': '<b>Rep. Vern Buchanan</b> (Republicano) | <b>Rep. Greg Steube</b> (Republicano)',
    'IL': '<b>Rep. Darin LaHood</b> (Republicano) | <b>Rep. Brad Schneider</b> (Demócrata)',
    'MN': '<b>Rep. Michelle Fischbach</b> (Republicano)',
    'NC': '<b>Rep. Greg Murphy</b> (Republicano)',
    'NE': '<b>Rep. Adrian Smith</b> (Republicano) - Presidente del Subcomité',
    'NY': '<b>Rep. Claudia Tenney</b> (Republicano)',
    'PA': '<b>Rep. Lloyd Smucker</b> (Republicano) | <b>Rep. Brendan Boyle</b> (Demócrata)',
    'TX': '<b>Rep. Jodey Arrington</b> (Republicano) | <b>Rep. Beth Van Duyne</b> (Republicano) | <b>Rep. Lloyd Doggett</b> (Demócrata)',
    'UT': '<b>Rep. Blake Moore</b> (Republicano)',
    'VA': '<b>Rep. Donald S. Beyer Jr.</b> (Demócrata)',
    'WA': '<b>Rep. Suzan K. DelBene</b> (Demócrata)',
    'WI': '<b>Rep. Gwen Moore</b> (Demócrata)',
    'WV': '<b>Rep. Carol Miller</b> (Republicano)'
}

# Secciones del HTS (Basadas en los primeros 2 dígitos)
HTS_SECTIONS = {
    "Total General": ["ALL"],
    "Sección I: Animales vivos y productos del reino animal": ["01", "02", "03", "04", "05"],
    "Sección II: Productos del reino vegetal": [str(i).zfill(2) for i in range(6, 15)],
    "Sección III: Grasas y aceites": ["15"],
    "Sección IV: Productos de las industrias alimentarias": [str(i).zfill(2) for i in range(16, 25)],
    "Sección V: Productos minerales": ["25", "26", "27"],
    "Sección VI: Productos de las industrias químicas": [str(i).zfill(2) for i in range(28, 39)],
    "Sección VII: Plástico y caucho": ["39", "40"],
    "Sección VIII: Pieles, cueros y peletería": ["41", "42", "43"],
    "Sección IX: Madera y manufacturas": [str(i).zfill(2) for i in range(44, 50)],
    "Sección X: Materias textiles": [str(i).zfill(2) for i in range(50, 64)],
    "Sección XI: Calzado, sombreros y paraguas": ["64", "65", "66", "67"],
    "Sección XII: Manufacturas de piedra, yeso y cemento": ["68", "69", "70"],
    "Sección XIII: Perlas naturales, piedras preciosas": ["71"],
    "Sección XIV: Metales comunes": [str(i).zfill(2) for i in range(72, 84) if i != 77],
    "Sección XV: Máquinas, aparatos y material eléctrico": ["84", "85"],
    "Sección XVI: Material de transporte": ["86", "87", "88", "89"],
    "Sección XVII: Instrumentos de óptica y medida": ["90", "91", "92"],
    "Sección XVIII: Armas y municiones": ["93"],
    "Sección XIX: Mercancías y productos diversos": ["94", "95", "96"],
    "Sección XX: Objetos de arte o colección": ["97"],
    "Sección XXI: Operaciones especiales": ["98"]
}

# ==========================================
# 3. CARGA DE METADATA (Bases pesadas se leen con DuckDB en el paso 5)
# ==========================================
# Rutas globales a los directorios particionados (DuckDB leerá todos los parquet combinados)
RUTA_MEX = "data/intermediate/mexico/*.parquet"
RUTA_TOT = "data/intermediate/total/*.parquet"

# # ==========================================
# # 4. LOGOS INSTITUCIONALES & SIDEBAR
# # ==========================================
# col_logo1, col_logo2 = st.sidebar.columns(2)
# try:
#     with col_logo1: st.image("logos/logo-01.png", use_container_width=True)
#     with col_logo2: st.image("logos/logo-02.png", use_container_width=True)
# except: pass
# st.sidebar.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# Selector de Sección HTS
st.sidebar.markdown("<h3 style='font-size: 1.1rem; color:#0F172A; margin-bottom: 5px;'>1. Sección Arancelaria</h3>", unsafe_allow_html=True)
seccion_sel = st.sidebar.selectbox("Filtro HTS", list(HTS_SECTIONS.keys()), label_visibility="collapsed")

st.sidebar.markdown("<h3 style='font-size: 1.1rem; color:#0F172A; margin-top: 15px; margin-bottom: 10px;'>2. Selecciona Estado</h3>", unsafe_allow_html=True)

if 'estado_us_sel' not in st.session_state:
    st.session_state['estado_us_sel'] = 'US'

def cambiar_estado(nuevo_estado):
    st.session_state['estado_us_sel'] = nuevo_estado

for st_code, st_name in US_STATES.items():
    btn_type = "primary" if st.session_state['estado_us_sel'] == st_code else "secondary"
    st.sidebar.button(
        label=st_name, 
        key=f"btn_{st_code}", 
        use_container_width=True, 
        type=btn_type, 
        on_click=cambiar_estado, 
        args=(st_code,)
    )

selected_state_code = st.session_state['estado_us_sel']
selected_state_name = US_STATES[selected_state_code]

# ==========================================
# 5. LÓGICA PRINCIPAL Y BIFURCACIÓN (NACIONAL VS ESTADO)
# ==========================================
capitulos_validos = HTS_SECTIONS[seccion_sel]

if "ALL" in capitulos_validos:
    caps_cond = "1=1"
else:
    caps_sql = ", ".join([f"'{c}'" for c in capitulos_validos])
    caps_cond = f"Chapter IN ({caps_sql})"

# Extraemos la metadata temporal general
max_year = int(duckdb.query(f"SELECT MAX(year) FROM '{RUTA_TOT}'").fetchone()[0])
todos_los_anios_query = duckdb.query(f"SELECT DISTINCT year FROM '{RUTA_TOT}' ORDER BY year DESC").fetchall()
lista_anios = [int(a[0]) for a in todos_los_anios_query]
meses_max_year_query = duckdb.query(f"SELECT DISTINCT month FROM '{RUTA_TOT}' WHERE year = {max_year}").fetchall()
meses_list = sorted([m[0] for m in meses_max_year_query])

if selected_state_code == 'US':
    st.markdown("<h1 style='color: #2596be; font-size: 2.8rem;'>Panorama Nacional: Estados Unidos</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #64748B; margin-top:-15px; margin-bottom:20px; font-weight:600;'>{seccion_sel} | Unidad de Medida: Dólares Estadounidenses</p>", unsafe_allow_html=True)
    
    # ------------------------------------------
    # FILTROS NACIONALES (Se actualizan instantáneamente sin botón de confirmación)
    # ------------------------------------------
    col_f0, col_f1, col_f2, col_f3 = st.columns([1, 1, 1.2, 1.8])
    with col_f0:
        flujo_sel = st.selectbox("Flujo Comercial", ["Comercio Total", "Importaciones", "Exportaciones"], key="nac_flujo")
        if flujo_sel == "Comercio Total":
            flow_cond = "1=1"
        elif flujo_sel == "Importaciones":
            flow_cond = "flow = 'imports'"
        else:
            flow_cond = "flow = 'exports'"
            
    with col_f1:
        # ASIGNACIÓN DE KEY: Evita que el dropdown se resetee en cada recálculo
        anio_sel = st.selectbox("Año de Análisis", lista_anios, key="nac_anio")
    with col_f2:
        periodo_sel = st.selectbox("Tipo de Periodo", ["YTD", "Anual", "Mensual", "Acumulado"], key="nac_per")
        
    meses_query = duckdb.query(f"SELECT DISTINCT month FROM '{RUTA_TOT}' WHERE year = {anio_sel} ORDER BY month").fetchall()
    lista_meses_act = sorted([m[0] for m in meses_query])
    meses_cond = "1=1"
    
    with col_f2: 
        # Los selectores dinámicos se anidan aquí para no romper el layout
        if periodo_sel == "YTD":
            if lista_meses_act:
                mes_max_global = duckdb.query(f"SELECT MAX(month) FROM '{RUTA_TOT}' WHERE year = {max_year}").fetchone()[0]
                m_sql = ", ".join([str(m) for m in lista_meses_act if m <= mes_max_global])
                meses_cond = f"month IN ({m_sql})" if m_sql else "1=0"
        elif periodo_sel == "Mensual":
            mes_sel = st.selectbox("Selecciona Mes", lista_meses_act, key="nac_mes")
            meses_cond = f"month = {mes_sel}"
        elif periodo_sel == "Acumulado":
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mes_ini = st.selectbox("Mes Inicio", lista_meses_act, key="nac_mini")
            with col_m2:
                mes_fin = st.selectbox("Mes Fin", lista_meses_act, index=len(lista_meses_act)-1 if lista_meses_act else 0, key="nac_mfin")
            if mes_ini and mes_fin:
                meses_cond = f"month BETWEEN {mes_ini} AND {mes_fin}"

    with col_f3:
        q_subs = f"SELECT DISTINCT COMMODITY, COM_DESC FROM '{RUTA_TOT}' WHERE {caps_cond} AND {flow_cond} AND year = {anio_sel} AND {meses_cond} ORDER BY COMMODITY"
        df_subs = duckdb.query(q_subs).to_df()
        
        dict_subs = {"Total de la sección": "TOTAL"}
        if not df_subs.empty:
            for _, r in df_subs.iterrows():
                dict_subs[r['COM_DESC']] = r['COMMODITY']  # blindaje: nunca perder ceros a la izquierda
                
        subp_sel_label = st.selectbox("Subpartida Específica", list(dict_subs.keys()), key="nac_subp")
        subp_sel_code = dict_subs[subp_sel_label]

    subp_cond = "1=1"
    if subp_sel_code != "TOTAL":
        subp_cond = f"CAST(COMMODITY AS VARCHAR) = '{str(subp_sel_code)}'"

    # ------------------------------------------
    # MAPA INTERACTIVO Y TOP 3
    # ------------------------------------------
    anio_previo = anio_sel - 1
    
    q_map_tot_curr = f"SELECT STATE, SUM(VALOR) as Total_Trade FROM '{RUTA_TOT}' WHERE {caps_cond} AND {flow_cond} AND year = {anio_sel} AND {meses_cond} AND {subp_cond} GROUP BY STATE"
    q_map_tot_prev = f"SELECT STATE, SUM(VALOR) as Total_Trade_Prev FROM '{RUTA_TOT}' WHERE {caps_cond} AND {flow_cond} AND year = {anio_previo} AND {meses_cond} AND {subp_cond} GROUP BY STATE"
    q_map_mex_curr = f"SELECT STATE, SUM(VALOR) as Mex_Trade FROM '{RUTA_MEX}' WHERE {caps_cond} AND {flow_cond} AND year = {anio_sel} AND {meses_cond} AND {subp_cond} GROUP BY STATE"
    
    df_map_curr = duckdb.query(q_map_tot_curr).to_df()
    
    if not df_map_curr.empty:
        df_map_prev = duckdb.query(q_map_tot_prev).to_df()
        df_map_mex = duckdb.query(q_map_mex_curr).to_df()
        
        df_map = df_map_curr.merge(df_map_prev, on='STATE', how='left').fillna(0)
        df_map = df_map.merge(df_map_mex, on='STATE', how='left').fillna(0)
        
        # Cálculos de Participación y Variación
        df_map['Part_Mex'] = (df_map['Mex_Trade'] / df_map['Total_Trade']) * 100
        df_map['Part_Mex'] = df_map['Part_Mex'].replace([np.inf, -np.inf], 0).fillna(0)
        
        df_map['Var_Anual'] = ((df_map['Total_Trade'] / df_map['Total_Trade_Prev']) - 1) * 100
        df_map['Var_Anual'] = df_map['Var_Anual'].replace([np.inf, -np.inf], np.nan) # Para no mostrar +inf cuando prev es 0
    else:
        df_map = df_map_curr
    
    st.markdown("<hr style='border-color: #2596be; border-width: 2px; margin-top:10px; margin-bottom:20px;'>", unsafe_allow_html=True)
    st.markdown("### Mapa de Comercio por Estado")
    if subp_sel_code == "TOTAL":
        st.markdown("<p style='color: #64748B; font-size: 0.95rem; font-style: italic; margin-top: -10px; margin-bottom: 20px;'>Seleccione cualquier estado para ver el top 3 de subpartidas de importación y exportación. Doble clic para regresar a la vista general.</p>", unsafe_allow_html=True)
    
    if not df_map.empty:
        # 1. Filtramos estrictamente solo los 50 estados, eliminando 'US' (Nacional)
        valid_states = [k for k in US_STATES.keys() if k != 'US']
        df_map = df_map[df_map['STATE'].isin(valid_states)].copy()
        
        # 2. Aseguramos que los 50 estados existan obligatoriamente en el DataFrame. 
        #    Esto evitará que Plotly deforme el mapa o dependa de un 'showland' global.
        all_states_df = pd.DataFrame({'STATE': valid_states})
        df_map = all_states_df.merge(df_map, on='STATE', how='left')
        
        # 3. Llenamos los nulos con 0 para poder operar cálculos correctamente
        for col in ['Total_Trade', 'Mex_Trade', 'Part_Mex']:
            if col in df_map.columns:
                df_map[col] = df_map[col].fillna(0)
        
        if 'Var_Anual' not in df_map.columns:
            df_map['Var_Anual'] = np.nan
            
        df_map = df_map.reset_index(drop=True)
        
        # 4. Dividimos los datos en válidos y nulos. Los nulos se mapearán como un fondo secundario.
        #    Esto evita usar znullcolor (inválido en Choropleth) o showland (que crea spillover geográfico).
        import plotly.graph_objects as go
        
        df_valid = df_map[df_map['Total_Trade'] > 0].copy()
        df_missing = df_map[df_map['Total_Trade'] == 0].copy()
        
        # 5. Calculamos el rango de colores solo con los datos válidos
        if not df_valid.empty:
            zmin_val = float(df_valid['Total_Trade'].min())
            zmax_val = float(df_valid['Total_Trade'].max())
        else:
            zmin_val, zmax_val = 0, 1
            
        df_map['Estado'] = df_map['STATE'].map(US_STATES)
        df_valid['Estado'] = df_valid['STATE'].map(US_STATES)
        df_missing['Estado'] = df_missing['STATE'].map(US_STATES)
        
        # 6. Formateo de los hover para el grupo con datos (Evita cálculos innecesarios en 0s)
        df_valid['Hover_Tot'] = df_valid['Total_Trade'].apply(lambda x: f"${x:,.0f} USD")
        df_valid['Hover_Mex'] = df_valid.apply(lambda r: f"${r['Mex_Trade']:,.0f} USD ({r['Part_Mex']:.1f}%)", axis=1)
        df_valid['Hover_Var'] = df_valid.apply(lambda r: f"{r['Var_Anual']:+.1f}%" if pd.notnull(r['Var_Anual']) else "N/A (Sin base)", axis=1)
        
        fig = px.choropleth(
            df_valid, 
            locations='STATE', 
            locationmode="USA-states", 
            color='Total_Trade',
            scope="usa",
            color_continuous_scale="Teal",
            range_color=[zmin_val, zmax_val],
            hover_name='Estado',
            custom_data=['STATE', 'Hover_Mex', 'Hover_Var', 'Hover_Tot']
        )
        
        etiqueta_flujo = "Comercio Total" if flujo_sel == "Comercio Total" else ("Importaciones" if flujo_sel == "Importaciones" else "Exportaciones")
        
        fig.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br><br>"
                f"<span style='color:#7dd3c8; font-weight:700;'>{etiqueta_flujo}:</span> %{{customdata[3]}}<br>"
                "<span style='color:#7dd3c8; font-weight:700;'>Participación MX:</span> %{customdata[1]}<br>"
                "<span style='color:#7dd3c8; font-weight:700;'>Variación Anual:</span> %{customdata[2]}"
                "<extra></extra>"
            ),
            marker_line_color='white', 
            marker_line_width=1.5,
            hoverlabel=dict(bgcolor='#0F172A', font_size=13, font_family='sans-serif', font_color='#F8FAFC', bordercolor='#0F172A', align='left')
        )
        
        # Agregamos manualmente la capa de estados sin operaciones (Relleno Gris Exacto).
        if not df_missing.empty:
            df_missing['Hover_Tot'] = "Sin operaciones registradas"
            df_missing['Hover_Mex'] = "N/A"
            df_missing['Hover_Var'] = "N/A"
            
            fig.add_trace(go.Choropleth(
                locations=df_missing['STATE'],
                z=[0] * len(df_missing),
                locationmode="USA-states",
                colorscale=[[0, '#E2E8F0'], [1, '#E2E8F0']],  # Color gris sólido
                showscale=False,
                customdata=np.stack((df_missing['STATE'], df_missing['Hover_Mex'], df_missing['Hover_Var'], df_missing['Hover_Tot']), axis=-1),
                hovertemplate=(
                    "<b>%{hovertext}</b><br><br>"
                    f"<span style='color:#7dd3c8; font-weight:700;'>{etiqueta_flujo}:</span> %{{customdata[3]}}<br>"
                    "<span style='color:#7dd3c8; font-weight:700;'>Participación MX:</span> %{customdata[1]}<br>"
                    "<span style='color:#7dd3c8; font-weight:700;'>Variación Anual:</span> %{customdata[2]}"
                    "<extra></extra>"
                ),
                hovertext=df_missing['Estado'],
                marker_line_color='white',
                marker_line_width=1.5,
                hoverlabel=dict(bgcolor='#0F172A', font_size=13, font_family='sans-serif', font_color='#F8FAFC', bordercolor='#0F172A', align='left')
            ))
        
        # 7. Apagamos el 'showland' global. Ahora el mapa se construye únicamente por 
        #    el rompecabezas de los 50 polígonos estatales, eliminando contornos fantasmas.
        fig.update_geos(
            visible=False, 
            showland=False, 
            bgcolor='#F8FAFC'
        )
        
        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0,"pad":0}, 
            height=600, 
            autosize=True, 
            dragmode=False, 
            plot_bgcolor='#F8FAFC', 
            paper_bgcolor='#F8FAFC', 
            coloraxis_colorbar=dict(title="", thickness=10, len=0.9, y=0.5, yanchor="middle", outlinewidth=0, tickfont=dict(color='#64748B'))
        )
        
        # Actualizamos la key del mapa para forzar la recarga al cambiar el flujo
        map_key = f"mapa_nacional_us__{seccion_sel}__{flujo_sel}__{anio_sel}__{periodo_sel}__{meses_cond}__{subp_sel_code}"
        
        # Desactivamos la capacidad de selección y el recálculo si no estamos en TOTAL
        accion_clic = "rerun" if subp_sel_code == "TOTAL" else "ignore"
        
        map_event = st.plotly_chart(
            fig, 
            use_container_width=True, 
            config={
                'displayModeBar': False, 
                'scrollZoom': False,
                'doubleClick': False
            }, 
            on_select=accion_clic, 
            selection_mode="points", 
            key=map_key
        )
        
        clicked_state = None
        
        # Estandarizamos el objeto de selección de Streamlit a un diccionario nativo
        raw_selection = {}
        if map_event and hasattr(map_event, "selection"):
            raw_selection = map_event.selection
            if not isinstance(raw_selection, dict) and hasattr(raw_selection, "items"):
                raw_selection = dict(raw_selection)
        
        puntos = raw_selection.get("points", []) if isinstance(raw_selection, dict) else []
        
        if puntos:
            punto = puntos[0]
            # 1. Prioridad Máxima: customdata (el anclaje infalible)
            if "customdata" in punto and punto["customdata"]:
                clicked_state = str(punto["customdata"][0])
            # 2. Prioridad Media: location nativo de Plotly
            elif "location" in punto:
                clicked_state = str(punto["location"])
            # 3. Prioridad Respaldo: Intercepción matemática por índice
            else:
                idx = punto.get("point_index") if "point_index" in punto else punto.get("point_number")
                if idx is not None and 0 <= idx < len(df_map):
                    clicked_state = str(df_map.iloc[idx]['STATE'])
        
        # ==========================================
        # TOP 3 SUBPARTIDAS POR ESTADO (AL HACER CLIC EN EL MAPA)
        # ==========================================
        if clicked_state and subp_sel_code == "TOTAL":
            nombre_estado_click = US_STATES.get(clicked_state, clicked_state)
            st.markdown(f"<h3 style='margin-top: 30px; color: #0F172A; text-align: center;'>Top 3 Subpartidas: {nombre_estado_click}</h3>", unsafe_allow_html=True)
            
            # Generador de Tablas HTML estilizadas
            def generar_tabla_html(df, color_tema, total_col, mex_col):
                if df.empty:
                    return "<div style='padding:15px; color:#64748B; font-style:italic;'>No hay operaciones para esta selección.</div>"
                html = f"""
                <div style="background-color: white; border-radius: 10px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                    <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; text-align: left;">
                        <thead>
                            <tr style="background-color: #F8FAFC; border-bottom: 2px solid #E2E8F0; color: #475569; font-size: 0.85rem; text-transform: uppercase;">
                                <th style="padding: 12px 15px; font-weight: 700; width: 55%;">Subpartida</th>
                                <th style="padding: 12px 15px; font-weight: 700; text-align: right; width: 25%;">Total (USD)</th>
                                <th style="padding: 12px 15px; font-weight: 700; text-align: center; width: 20%;">Part. MX</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, row in df.iterrows():
                    subp = str(row['COM_DESC'])
                    tot_val = row[total_col]
                    mex_val = row[mex_col]
                    part_mx = (mex_val / tot_val * 100) if tot_val > 0 else 0
                    html += f"""
                        <tr style="border-bottom: 1px solid #F1F5F9; transition: background-color 0.2s;">
                            <td style="padding: 12px 15px; color: #0F172A; font-size: 0.85rem; font-weight: 600;">{subp}</td>
                            <td style="padding: 12px 15px; color: #0F172A; font-size: 0.9rem; font-weight: 800; text-align: right;">${tot_val:,.0f}</td>
                            <td style="padding: 12px 15px; text-align: center;">
                                <span style="background-color: #F1F5F9; color: {color_tema}; padding: 4px 8px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; border: 1px solid #E2E8F0;">
                                    {part_mx:.1f}%
                                </span>
                            </td>
                        </tr>
                    """
                html += "</tbody></table></div>"
                return html.replace('\n', '')

            col_imp, col_exp = st.columns(2)
            
            with col_imp:
                st.markdown("<h4 style='color: #2596be;'>Importaciones (El Estado Importa)</h4>", unsafe_allow_html=True)
                q_top_imp = f"""
                    WITH top_tot AS (
                        SELECT COMMODITY, MAX(COM_DESC) as COM_DESC, SUM(VALOR) as Tot_Imp 
                        FROM '{RUTA_TOT}' 
                        WHERE STATE='{clicked_state}' AND flow='imports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} 
                        GROUP BY COMMODITY 
                        ORDER BY Tot_Imp DESC 
                        LIMIT 3
                    ),
                    mex_data AS (
                        SELECT COMMODITY, SUM(VALOR) as Mex_Imp 
                        FROM '{RUTA_MEX}' 
                        WHERE STATE='{clicked_state}' AND flow='imports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} 
                          AND COMMODITY IN (SELECT COMMODITY FROM top_tot)
                        GROUP BY COMMODITY
                    )
                    SELECT t.COMMODITY, t.COM_DESC, t.Tot_Imp, COALESCE(m.Mex_Imp, 0) AS Mex_Imp
                    FROM top_tot t LEFT JOIN mex_data m ON t.COMMODITY = m.COMMODITY
                    ORDER BY t.Tot_Imp DESC
                """
                df_ti = duckdb.query(q_top_imp).to_df()
                st.markdown(generar_tabla_html(df_ti, "#2596be", "Tot_Imp", "Mex_Imp"), unsafe_allow_html=True)

            with col_exp:
                st.markdown("<h4 style='color: #008889;'>Exportaciones (El Estado Exporta)</h4>", unsafe_allow_html=True)
                q_top_exp = f"""
                    WITH top_tot AS (
                        SELECT COMMODITY, MAX(COM_DESC) as COM_DESC, SUM(VALOR) as Tot_Exp 
                        FROM '{RUTA_TOT}' 
                        WHERE STATE='{clicked_state}' AND flow='exports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} 
                        GROUP BY COMMODITY 
                        ORDER BY Tot_Exp DESC 
                        LIMIT 3
                    ),
                    mex_data AS (
                        SELECT COMMODITY, SUM(VALOR) as Mex_Exp 
                        FROM '{RUTA_MEX}' 
                        WHERE STATE='{clicked_state}' AND flow='exports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} 
                          AND COMMODITY IN (SELECT COMMODITY FROM top_tot)
                        GROUP BY COMMODITY
                    )
                    SELECT t.COMMODITY, t.COM_DESC, t.Tot_Exp, COALESCE(m.Mex_Exp, 0) AS Mex_Exp
                    FROM top_tot t LEFT JOIN mex_data m ON t.COMMODITY = m.COMMODITY
                    ORDER BY t.Tot_Exp DESC
                """
                df_te = duckdb.query(q_top_exp).to_df()
                st.markdown(generar_tabla_html(df_te, "#008889", "Tot_Exp", "Mex_Exp"), unsafe_allow_html=True)
                
        # ==========================================
        # EVOLUCIÓN HISTÓRICA NACIONAL (NUEVA GRÁFICA)
        # ==========================================
        st.markdown("<hr style='border-color: #E2E8F0; border-width: 2px; margin-top:30px; margin-bottom:20px;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='color: #0F172A; margin-bottom: 20px;'>Evolución Histórica Nacional: Subpartidas Principales</h3>", unsafe_allow_html=True)
        
        col_nh1, col_nh2, col_nh3, col_nh4, col_nh5 = st.columns(5)
        with col_nh1:
            socio_sel_n = st.selectbox("Socio Comercial", ["Mundo", "México"], key="nac_h_socio")
            ruta_hist_n = RUTA_TOT if socio_sel_n == "Mundo" else RUTA_MEX
        with col_nh2:
            flujo_hist_n = st.selectbox("Flujo Comercial", ["Comercio Total", "Importaciones", "Exportaciones"], key="nac_h_flujo")
            flow_cond_hist_n = "1=1" if flujo_hist_n == "Comercio Total" else ("flow = 'imports'" if flujo_hist_n == "Importaciones" else "flow = 'exports'")
        with col_nh3:
            per_hist_n = st.selectbox("Tipo de Periodo", ["YTD", "Anual", "Mensual (Línea de Tiempo)", "Mes Específico", "Acumulado"], key="nac_h_per")
        with col_nh4:
            anio_ini_n = st.selectbox("Año Inicio", sorted(lista_anios), key="nac_h_aini", index=0)
        with col_nh5:
            anio_fin_n = st.selectbox("Año Fin", sorted(lista_anios, reverse=True), key="nac_h_afin", index=0)
            
        meses_cond_hist_n = "1=1"
        todos_los_meses_n = list(range(1, 13))
        
        if per_hist_n in ["Mes Específico", "Acumulado"]:
            col_nhm1, col_nhm2 = st.columns(2)
            
        if per_hist_n == "YTD":
            mes_max_global_n = max(meses_list) if meses_list else 12
            m_sql_n = ", ".join([str(m) for m in todos_los_meses_n if m <= mes_max_global_n])
            meses_cond_hist_n = f"month IN ({m_sql_n})" if m_sql_n else "1=0"
        elif per_hist_n == "Mes Específico":
            with col_nhm1:
                mes_sel_hn = st.selectbox("Mes", todos_los_meses_n, key="nac_h_mes")
                meses_cond_hist_n = f"month = {mes_sel_hn}"
        elif per_hist_n == "Mensual (Línea de Tiempo)":
            meses_cond_hist_n = "1=1"
        elif per_hist_n == "Acumulado":
            with col_nhm1:
                mes_ini_hn = st.selectbox("Mes Inicio", todos_los_meses_n, key="nac_h_mini")
            with col_nhm2:
                mes_fin_hn = st.selectbox("Mes Fin", todos_los_meses_n, index=11, key="nac_h_mfin")
            if mes_ini_hn and mes_fin_hn:
                meses_cond_hist_n = f"month BETWEEN {mes_ini_hn} AND {mes_fin_hn}"

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        q_subs_hist_n = f"SELECT DISTINCT COMMODITY, COM_DESC FROM '{ruta_hist_n}' WHERE STATE='-' AND {caps_cond} AND {flow_cond_hist_n} AND year BETWEEN {anio_ini_n} AND {anio_fin_n} ORDER BY COMMODITY"
        df_subs_hist_n = duckdb.query(q_subs_hist_n).to_df()
        
        dict_subs_hist_n = {}
        if not df_subs_hist_n.empty:
            for _, r in df_subs_hist_n.iterrows():
                dict_subs_hist_n[r['COM_DESC']] = r['COMMODITY']
                
        opciones_especiales_n = ["Total de la Sección", "Top 5 Subpartidas", "Top 10 Subpartidas"]

        # Pre-cálculo dinámico: qué Top (5/10) está activo ahora mismo, para (a) excluir
        # esas subpartidas del resto de la lista (evita seleccionarlas 2 veces) y
        # (b) reutilizar el mismo resultado más abajo sin volver a consultar.
        sel_previa_n = list(st.session_state.get("nac_h_multi", ["Top 5 Subpartidas"]))
        n_lim_previo_n = 10 if "Top 10 Subpartidas" in sel_previa_n else (5 if "Top 5 Subpartidas" in sel_previa_n else 0)

        codigos_top_previos_n = set()
        if n_lim_previo_n > 0:
            q_top_previo_n = f"SELECT COMMODITY FROM '{ruta_hist_n}' WHERE STATE='-' AND {caps_cond} AND {flow_cond_hist_n} AND year={anio_fin_n} AND {meses_cond_hist_n} GROUP BY COMMODITY ORDER BY SUM(VALOR) DESC LIMIT {n_lim_previo_n}"
            df_top_previo_n = duckdb.query(q_top_previo_n).to_df()
            if not df_top_previo_n.empty:
                codigos_top_previos_n.update(df_top_previo_n['COMMODITY'].tolist())

        opciones_todas_n = opciones_especiales_n + [desc for desc, cod in dict_subs_hist_n.items() if cod not in codigos_top_previos_n]

        # Si alguna subpartida manual quedó "cubierta" por el Top activo, la quitamos
        # de la selección guardada para que no se pueda duplicar.
        sel_previa_n_limpia = [s for s in sel_previa_n if s in opciones_especiales_n or dict_subs_hist_n.get(s) not in codigos_top_previos_n]
        if sel_previa_n_limpia != sel_previa_n:
            st.session_state["nac_h_multi"] = sel_previa_n_limpia

        subp_sel_n = st.multiselect(
            "Selecciona las Subpartidas a graficar",
            options=opciones_todas_n,
            default=["Top 5 Subpartidas"],
            key="nac_h_multi",
            on_change=_alternar_top_exclusivo,
            args=("nac_h_multi",)
        )

        if per_hist_n == "Mensual (Línea de Tiempo)":
            x_select_n = "CAST(year AS VARCHAR) || '-' || RIGHT('0' || CAST(month AS VARCHAR), 2)"
            group_cols_n = "year, month"
            order_cols_n = "year, month"
        else:
            x_select_n = "CAST(year AS VARCHAR)"
            group_cols_n = "year"
            order_cols_n = "year"
            
        def _construir_df_hist_nacional(modo_total, codigos_para_query):
            """Arma el df para el modo 'Total de la Sección' o para un set de códigos
            (Top 5/10 + manuales). Se llama hasta 2 veces y se concatena el resultado,
            así ambos modos pueden convivir en la misma gráfica."""
            codigos_txt_n = ", ".join([f"'{c}'" for c in codigos_para_query]) if codigos_para_query else ""
            filtro_cod_n = f"AND COMMODITY IN ({codigos_txt_n})" if (not modo_total and codigos_txt_n) else ""
            comm_select_n = "" if modo_total else "COMMODITY,"
            comm_group_n = "" if modo_total else ", COMMODITY"
            com_desc_expr_n = "'Total de la Sección'" if modo_total else "MAX(COM_DESC)"
            join_comm_ref_n = "" if modo_total else "AND m.COMMODITY = r.COMMODITY"
            join_comm_ts_n = "" if modo_total else "AND m.COMMODITY = ts.COMMODITY"

            if socio_sel_n == "Mundo":
                q_ref_n = f"""
                base_ref AS (
                    SELECT {group_cols_n}, {comm_select_n} SUM(VALOR) as REF_VALOR
                    FROM '{RUTA_MEX}'
                    WHERE STATE='-' AND {caps_cond} AND {flow_cond_hist_n} AND year BETWEEN {anio_ini_n} AND {anio_fin_n} AND {meses_cond_hist_n}
                    {filtro_cod_n}
                    GROUP BY {group_cols_n} {comm_group_n}
                )
                """
                join_ref_n = f"""
                LEFT JOIN base_ref r ON m.year = r.year 
                    { 'AND m.month = r.month' if 'month' in group_cols_n else '' }
                    {join_comm_ref_n}
                """
            else:
                q_ref_n = f"""
                base_ref AS (
                    SELECT {group_cols_n}, SUM(VALOR) as REF_VALOR
                    FROM '{RUTA_MEX}'
                    WHERE STATE='-' AND {caps_cond} AND {flow_cond_hist_n} AND year BETWEEN {anio_ini_n} AND {anio_fin_n} AND {meses_cond_hist_n}
                    GROUP BY {group_cols_n}
                )
                """
                join_ref_n = f"""
                LEFT JOIN base_ref r ON m.year = r.year 
                    { 'AND m.month = r.month' if 'month' in group_cols_n else '' }
                """

            q_line_n = f"""
                WITH state_agg AS (
                    SELECT {group_cols_n}, STATE,
                           {comm_select_n}
                           SUM(VALOR) as state_val
                    FROM '{ruta_hist_n}'
                    WHERE STATE NOT IN ('-', 'US', 'UNKNOWN', '') AND {caps_cond} AND {flow_cond_hist_n} AND year BETWEEN {anio_ini_n} AND {anio_fin_n} AND {meses_cond_hist_n}
                    {filtro_cod_n}
                    GROUP BY {group_cols_n}, STATE {comm_group_n}
                ),
                ranked_states AS (
                    SELECT *, ROW_NUMBER() OVER(PARTITION BY {group_cols_n} {comm_group_n} ORDER BY state_val DESC) as rn
                    FROM state_agg
                ),
                top_states AS (
                    SELECT {group_cols_n}, 
                           {comm_select_n}
                           STRING_AGG(STATE, ', ') as top3_states
                    FROM (SELECT * FROM ranked_states WHERE rn <= 3 ORDER BY rn) sub
                    GROUP BY {group_cols_n} {comm_group_n}
                ),
                base_main AS (
                    SELECT {x_select_n} AS periodo, {group_cols_n},
                           {com_desc_expr_n} as COM_DESC,
                           {comm_select_n}
                           SUM(VALOR) as VALOR
                    FROM '{ruta_hist_n}'
                    WHERE STATE='-' AND {caps_cond} AND {flow_cond_hist_n} AND year BETWEEN {anio_ini_n} AND {anio_fin_n} AND {meses_cond_hist_n}
                    {filtro_cod_n}
                    GROUP BY {group_cols_n} {comm_group_n}
                ),
                {q_ref_n}
                SELECT m.periodo, m.COM_DESC, m.VALOR, COALESCE(r.REF_VALOR, 0) as REF_VALOR, ts.top3_states
                FROM base_main m
                {join_ref_n}
                LEFT JOIN top_states ts ON m.year = ts.year
                    { 'AND m.month = ts.month' if 'month' in group_cols_n else '' }
                    {join_comm_ts_n}
                ORDER BY m.{order_cols_n.replace(', ', ', m.')}
            """
            return duckdb.query(q_line_n).to_df()

        is_total_n = "Total de la Sección" in subp_sel_n
        codigos_finales_n = set(codigos_top_previos_n)
        for s in subp_sel_n:
            if s not in opciones_especiales_n:
                codigos_finales_n.add(dict_subs_hist_n[s])
        hay_codigos_n = len(codigos_finales_n) > 0
        debe_graficar_n = is_total_n or hay_codigos_n
        hover_part_label_n = "Part. MX" if socio_sel_n == "Mundo" else "Part. Interna"

        if debe_graficar_n:
            dfs_hist_n = []
            if hay_codigos_n:
                dfs_hist_n.append(_construir_df_hist_nacional(False, codigos_finales_n))
            if is_total_n:
                dfs_hist_n.append(_construir_df_hist_nacional(True, None))
            df_line_n = pd.concat(dfs_hist_n, ignore_index=True) if dfs_hist_n else pd.DataFrame()
            
            if not df_line_n.empty:
                if socio_sel_n == "Mundo":
                    df_line_n['Participacion'] = (df_line_n['REF_VALOR'] / df_line_n['VALOR']) * 100
                else:
                    df_line_n['Participacion'] = (df_line_n['VALOR'] / df_line_n['REF_VALOR']) * 100
                df_line_n['Participacion'] = df_line_n['Participacion'].fillna(0)
                
                fig_line_n = px.line(df_line_n, x="periodo", y="VALOR", color="COM_DESC", markers=True, custom_data=['Participacion', 'top3_states'], hover_name="COM_DESC")
                
                fig_line_n.update_layout(
                    xaxis_title="", 
                    yaxis_title="Valor Comercial (USD)", 
                    plot_bgcolor='#F8FAFC', 
                    paper_bgcolor='#F8FAFC',
                    legend=dict(orientation="v", yanchor="top", y=-0.08, xanchor="left", x=0, title=None, font=dict(size=11)),
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=500
                )
                
                fig_line_n.update_yaxes(rangemode="tozero", showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1", tickprefix="$")
                
                if per_hist_n != "Mensual (Línea de Tiempo)":
                    fig_line_n.update_xaxes(dtick=1, showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1")
                else:
                    fig_line_n.update_xaxes(showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1")
                
                fig_line_n.update_traces(
                    line=dict(width=3), 
                    marker=dict(size=8), 
                    hovertemplate=(
                        "<span style='color:#7dd3c8; font-weight:700;'>Periodo:</span> %{x}<br>"
                        "<span style='color:#7dd3c8; font-weight:700;'>Valor:</span> $%{y:,.0f} USD<br>"
                        f"<span style='color:#7dd3c8; font-weight:700;'>{hover_part_label_n}:</span> %{{customdata[0]:.1f}}%<br>"
                        "<span style='color:#7dd3c8; font-weight:700;'>Top 3 Estados:</span> %{customdata[1]}<extra></extra>"
                    ),
                    hoverlabel=dict(bgcolor='#0F172A', font_size=13, font_family='sans-serif', font_color='#F8FAFC', bordercolor='#0F172A', align='left')
                )
                
                st.plotly_chart(fig_line_n, use_container_width=True)
            else:
                st.info("No hay operaciones registradas para la configuración temporal seleccionada.")
        else:
            if not subp_sel_n:
                st.warning("Selecciona al menos una opción (Top, Total o subpartidas específicas) para generar la gráfica.")
            else:
                st.info("No se encontraron subpartidas con operaciones para tu combinación de filtros.")
    else:
        st.warning("No hay datos geográficos para esta combinación de filtros.")

else:
    # ==========================================
    # LÓGICA DE ESTADO (ANÁLISIS INDIVIDUAL)
    # ==========================================
    meses_sql = ", ".join([f"'{str(m).zfill(2)}'" for m in meses_list])
    
    query_base = f"""
        SELECT 
            COMMODITY, "DESC", Chapter, STATE, flow, year, month, VALOR
        FROM '%s'
        WHERE STATE = '{selected_state_code}'
          AND {caps_cond}
          AND year IN ({max_year}, {max_year - 1})
          AND month IN ({meses_sql})
    """
    
    df_mex_ytd = duckdb.query(query_base % RUTA_MEX).to_df()
    df_tot_ytd = duckdb.query(query_base % RUTA_TOT).to_df()
    
    MONTH_MAP = {"01":"Ene", "02":"Feb", "03":"Mar", "04":"Abr", "05":"May", "06":"Jun", 
                 "07":"Jul", "08":"Ago", "09":"Sep", "10":"Oct", "11":"Nov", "12":"Dic"}
    
    if len(meses_list) == 12:
        label_curr = str(max_year)
        label_prev = str(max_year - 1)
    else:
        mes_final = str(meses_list[-1]).zfill(2)
        nombre_mes = MONTH_MAP.get(mes_final, mes_final)
        label_curr = f"Ene-{nombre_mes} {max_year}"
        label_prev = f"Ene-{nombre_mes} {max_year - 1}"
    
    def get_full_year_total_bar(flow_type, color_mex):
        query_tot = f"SELECT SUM(CAST(VALOR AS DOUBLE)) FROM '{RUTA_TOT}' WHERE STATE = '{selected_state_code}' AND {caps_cond} AND flow = '{flow_type}' AND year = {max_year - 1}"
        query_mex = f"SELECT SUM(CAST(VALOR AS DOUBLE)) FROM '{RUTA_MEX}' WHERE STATE = '{selected_state_code}' AND {caps_cond} AND flow = '{flow_type}' AND year = {max_year - 1}"
        
        tot_prev_year = duckdb.query(query_tot).fetchone()[0] or 0
        mex_prev_year = duckdb.query(query_mex).fetchone()[0] or 0
    
        pct_mex = (mex_prev_year / tot_prev_year * 100) if tot_prev_year > 0 else 0
    
        html = f"""<div style="background-color: white; padding:20px 25px; border-radius:12px; border:1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.03); width: 100%; margin-bottom: 25px;">
    <div style="display: flex; align-items: center;">
    <div style="flex: 0 0 8%; font-size: 0.85rem; color: #64748B; font-weight: 700; text-transform: uppercase;">TOTAL {max_year - 1}</div>
    <div style="flex: 1; display: flex; align-items: center;">
    <div style="width: 100%; height: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; overflow: hidden; background-color: #CBD5E1;">
    <div style="background-color: {color_mex}; width: {pct_mex}%;"></div>
    </div>
    <span style="margin-left: 10px; white-space: nowrap; font-weight: 800; font-size: 1.1rem; color: #0F172A;">
    ${tot_prev_year:,.0f} <span style="font-size: 0.8rem; color: #64748B; font-weight: 600;">(Part. México: {pct_mex:.1f}%)</span>
    </span>
    </div>
    </div>
    </div>"""
        return html.replace('\n', '')
    
    def get_top_5_total_split(flow_type, color_mex, color_rest):
        df_t_flow = df_tot_ytd[df_tot_ytd['flow'] == flow_type]
        df_m_flow = df_mex_ytd[df_mex_ytd['flow'] == flow_type]
        
        tot_agg = df_t_flow.groupby(['COMMODITY', 'DESC', 'year'])['VALOR'].sum().reset_index()
        mex_agg = df_m_flow.groupby(['COMMODITY', 'DESC', 'year'])['VALOR'].sum().reset_index()
        
        val_total_curr = df_t_flow[df_t_flow['year'] == max_year]['VALOR'].sum()
        val_total_prev = df_t_flow[df_t_flow['year'] == max_year - 1]['VALOR'].sum()
        
        val_mex_curr = df_m_flow[df_m_flow['year'] == max_year]['VALOR'].sum()
        val_mex_prev = df_m_flow[df_m_flow['year'] == max_year - 1]['VALOR'].sum()
    
        max_total_scale = max(val_total_curr, val_total_prev)
        pct_total_prev_scale = max((val_total_prev / max_total_scale) * 85 if max_total_scale > 0 else 0, 0.5)
        pct_total_curr_scale = max((val_total_curr / max_total_scale) * 85 if max_total_scale > 0 else 0, 0.5)
        
        pct_mex_curr_tot = (val_mex_curr / val_total_curr * 100) if val_total_curr > 0 else 0
        pct_mex_prev_tot = (val_mex_prev / val_total_prev * 100) if val_total_prev > 0 else 0
        
        tot_curr = tot_agg[tot_agg['year'] == max_year].rename(columns={'VALOR': 'Tot_Curr'})
        tot_prev = tot_agg[tot_agg['year'] == max_year - 1].rename(columns={'VALOR': 'Tot_Prev'})
        
        mex_curr = mex_agg[mex_agg['year'] == max_year].rename(columns={'VALOR': 'Mex_Curr'})
        mex_prev = mex_agg[mex_agg['year'] == max_year - 1].rename(columns={'VALOR': 'Mex_Prev'})
        
        df_chart = tot_curr.merge(tot_prev[['COMMODITY', 'Tot_Prev']], on='COMMODITY', how='left')
        df_chart = df_chart.merge(mex_curr[['COMMODITY', 'Mex_Curr']], on='COMMODITY', how='left')
        df_chart = df_chart.merge(mex_prev[['COMMODITY', 'Mex_Prev']], on='COMMODITY', how='left')
        cols_numericas = ['Tot_Prev', 'Mex_Curr', 'Mex_Prev']
        df_chart[cols_numericas] = df_chart[cols_numericas].fillna(0)
        
        top5 = df_chart.sort_values('Tot_Curr', ascending=False).head(5).copy()
        if top5.empty: return "<div style='padding:20px; color:#64748B;'>No hay datos para esta selección.</div>"
        
        top5['Part_Mex'] = (top5['Mex_Curr'] / top5['Tot_Curr']) * 100
        top5['Part_Mex'] = top5['Part_Mex'].fillna(0)
        
        top5['Part_Mex_Prev'] = (top5['Mex_Prev'] / top5['Tot_Prev']) * 100
        top5['Part_Mex_Prev'] = top5['Part_Mex_Prev'].fillna(0)
        
        max_scale = max(top5['Tot_Curr'].max(), top5['Tot_Prev'].max())
        
        html = f"""<div style="background-color: white; padding:25px; border-radius:12px; border:1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.03); width: 100%;">
    <div style="margin-bottom:25px; border-bottom: 2px solid #F1F5F9; padding-bottom: 20px;">
    <div style="display: flex; align-items: center; margin-bottom: 12px;">
    <div style="flex: 0 0 12%; font-size: 0.85rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Total {label_prev}</div>
    <div style="flex: 1; display: flex; align-items: center;">
    <div style="width: {pct_total_prev_scale}%; height: 14px; border-radius: 4px; display: flex; overflow: hidden; opacity: 0.7;">
    <div style="background-color: {color_mex}; width: {pct_mex_prev_tot}%;"></div>
    <div style="background-color: {color_rest}; width: {100 - pct_mex_prev_tot}%;"></div>
    </div>
    <span style="margin-left: 10px; white-space: nowrap; font-weight: 800; font-size: 1rem; color: #0F172A;">
    ${val_total_prev:,.0f} <span style="font-size: 0.75rem; color: #64748B; font-weight: 600;">(Part. México: {pct_mex_prev_tot:.1f}%)</span>
    </span>
    </div>
    </div>
    <div style="display: flex; align-items: center;">
    <div style="flex: 0 0 12%; font-size: 0.85rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Total {label_curr}</div>
    <div style="flex: 1; display: flex; align-items: center;">
    <div style="width: {pct_total_curr_scale}%; height: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; overflow: hidden;">
    <div style="background-color: {color_mex}; width: {pct_mex_curr_tot}%;"></div>
    <div style="background-color: {color_rest}; width: {100 - pct_mex_curr_tot}%;"></div>
    </div>
    <span style="margin-left: 10px; white-space: nowrap; font-weight: 800; font-size: 1rem; color: #0F172A;">
    ${val_total_curr:,.0f} <span style="font-size: 0.75rem; color: #64748B; font-weight: 600;">(Part. México: {pct_mex_curr_tot:.1f}%)</span>
    </span>
    </div>
    </div>
    </div>
    
    <div style="display: flex; width: 100%; margin-bottom: 20px; font-weight: 800; font-size: 0.85rem; text-transform:uppercase; color: #64748B; border-bottom:2px solid #F1F5F9; padding-bottom:10px; justify-content: space-between; gap: 15px;">
    <div style="flex: 0 0 20%; text-align: left; padding-left: 5px;">Subpartida (HTS 6)</div>
    <div style="flex: 1; text-align: left; padding-left: 15px;">Valor (Dólares) - <span style="color:{color_mex};">■ México</span> <span style="color:{color_rest};">■ Resto del Mundo</span></div>
    <div style="flex: 0 0 12%; text-align: center; display: flex; flex-direction: column; justify-content: center;">Part. MX<br>(% Total)</div>
    </div>"""
    
        for _, r in top5.iterrows():
            pct_tot_curr_scale = max((r['Tot_Curr'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
            pct_tot_prev_scale = max((r['Tot_Prev'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
            
            pct_mex_curr = (r['Mex_Curr'] / r['Tot_Curr']) * 100 if r['Tot_Curr'] > 0 else 0
            pct_rest_curr = 100 - pct_mex_curr
            
            pct_mex_prev = (r['Mex_Prev'] / r['Tot_Prev']) * 100 if r['Tot_Prev'] > 0 else 0
            pct_rest_prev = 100 - pct_mex_prev
    
            desc_wrapped = f"{r['COMMODITY']} - {r['DESC']}"
            
            html += f"""<div style="display: flex; width: 100%; align-items: stretch; margin-bottom: 18px; justify-content: space-between; gap: 15px;">
    <div style="flex: 0 0 20%; padding-left: 5px; font-size: 0.85rem; display: flex; align-items: center;">
    <span style="display: inline-block; width: 100%; text-align: justify; text-justify: inter-word; hyphens: auto; line-height: 1.3; color: #0F172A; font-weight: 600;">{desc_wrapped}</span>
    </div>
    <div style="flex: 1; border-left: 2px solid #E2E8F0; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; gap: 8px;">
    <div style="display:flex; align-items:center; width: 100%;">
    <div style="width: {pct_tot_prev_scale}%; height: 12px; border-radius: 4px; display: flex; overflow: hidden; opacity: 0.7;">
    <div style="background-color: {color_mex}; width: {pct_mex_prev}%;"></div>
    <div style="background-color: {color_rest}; width: {pct_rest_prev}%;"></div>
    </div>
    <span style="margin-left: 10px; font-weight: 600; font-size: 0.75rem; color: #64748B;">${r['Tot_Prev']:,.0f}</span>
    </div>
    <div style="display:flex; align-items:center; width: 100%;">
    <div style="width: {pct_tot_curr_scale}%; height: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; overflow: hidden;">
    <div style="background-color: {color_mex}; width: {pct_mex_curr}%;"></div>
    <div style="background-color: {color_rest}; width: {pct_rest_curr}%;"></div>
    </div>
    <span style="margin-left: 10px; font-weight: 800; font-size: 0.95rem; color: #0F172A;">${r['Tot_Curr']:,.0f}</span>
    </div>
    </div>
    <div style="flex: 0 0 12%; display: flex; flex-direction: column; justify-content: center; gap: 8px; align-items: center;">
    <div style="background-color: #F1F5F9; border:1px solid #E2E8F0; border-radius: 6px; width: 100%; font-weight: 700; font-size: 0.75rem; color: #64748B; text-align: center; height: 22px; display: flex; align-items: center; justify-content: center;">
    {r['Part_Mex_Prev']:.1f}%
    </div>
    <div style="background-color: #F8FAFC; border:1px solid #E2E8F0; border-radius: 6px; width: 100%; font-weight: 800; font-size: 0.85rem; color: {color_mex}; text-align: center; height: 26px; display: flex; align-items: center; justify-content: center;">
    {r['Part_Mex']:.1f}%
    </div>
    </div>
    </div>"""
        html += "</div>"
        return html.replace('\n', '')
    
    def get_top_5_mexico_base(flow_type, color_mex):
        df_m_flow = df_mex_ytd[df_mex_ytd['flow'] == flow_type]
        
        mex_agg = df_m_flow.groupby(['COMMODITY', 'DESC', 'year'])['VALOR'].sum().reset_index()
        
        val_mex_curr = df_m_flow[df_m_flow['year'] == max_year]['VALOR'].sum()
        val_mex_prev = df_m_flow[df_m_flow['year'] == max_year - 1]['VALOR'].sum()
    
        max_total_scale = max(val_mex_curr, val_mex_prev)
        pct_total_prev_scale = max((val_mex_prev / max_total_scale) * 85 if max_total_scale > 0 else 0, 0.5)
        pct_total_curr_scale = max((val_mex_curr / max_total_scale) * 85 if max_total_scale > 0 else 0, 0.5)
        
        mex_curr = mex_agg[mex_agg['year'] == max_year].rename(columns={'VALOR': 'Mex_Curr'})
        mex_prev = mex_agg[mex_agg['year'] == max_year - 1].rename(columns={'VALOR': 'Mex_Prev'})
        
        df_chart = mex_curr.merge(mex_prev[['COMMODITY', 'Mex_Prev']], on='COMMODITY', how='left')
        df_chart['Mex_Prev'] = df_chart['Mex_Prev'].fillna(0)
        
        top5 = df_chart.sort_values('Mex_Curr', ascending=False).head(5).copy()
        if top5.empty: return "<div style='padding:20px; color:#64748B;'>No hay datos para esta selección.</div>"
        
        total_mex_flow = df_chart['Mex_Curr'].sum()
        top5['Part_Interna'] = (top5['Mex_Curr'] / total_mex_flow) * 100 if total_mex_flow > 0 else 0
        
        total_mex_flow_prev = df_chart['Mex_Prev'].sum()
        top5['Part_Interna_Prev'] = (top5['Mex_Prev'] / total_mex_flow_prev) * 100 if total_mex_flow_prev > 0 else 0
        
        max_scale = max(top5['Mex_Curr'].max(), top5['Mex_Prev'].max())
        
        html = f"""<div style="background-color: white; padding:25px; border-radius:12px; border:1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.03); width: 100%;">
    <div style="margin-bottom:25px; border-bottom: 2px solid #F1F5F9; padding-bottom: 20px;">
    <div style="display: flex; align-items: center; margin-bottom: 12px;">
    <div style="flex: 0 0 12%; font-size: 0.85rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Total {label_prev}</div>
    <div style="flex: 1; display: flex; align-items: center;">
    <div style="background-color: {color_mex}; width: {pct_total_prev_scale}%; height: 14px; border-radius: 4px; opacity: 0.6;"></div>
    <span style="margin-left: 10px; white-space: nowrap; font-weight: 800; font-size: 1rem; color: #0F172A;">
    ${val_mex_prev:,.0f}
    </span>
    </div>
    </div>
    <div style="display: flex; align-items: center;">
    <div style="flex: 0 0 12%; font-size: 0.85rem; color: #64748B; font-weight: 700; text-transform: uppercase;">Total {label_curr}</div>
    <div style="flex: 1; display: flex; align-items: center;">
    <div style="background-color: {color_mex}; width: {pct_total_curr_scale}%; height: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
    <span style="margin-left: 10px; white-space: nowrap; font-weight: 800; font-size: 1rem; color: #0F172A;">
    ${val_mex_curr:,.0f}
    </span>
    </div>
    </div>
    </div>
    
    <div style="display: flex; width: 100%; margin-bottom: 20px; font-weight: 800; font-size: 0.85rem; text-transform:uppercase; color: #64748B; border-bottom:2px solid #F1F5F9; padding-bottom:10px; justify-content: space-between; gap: 15px;">
    <div style="flex: 0 0 20%; text-align: left; padding-left: 5px;">Subpartida (HTS 6)</div>
    <div style="flex: 1; text-align: left; padding-left: 15px;">Valor (Dólares)</div>
    <div style="flex: 0 0 12%; text-align: center; display: flex; flex-direction: column; justify-content: center;">Part.<br>(% Total MX)</div>
    </div>"""
    
        for _, r in top5.iterrows():
            pct_curr_scale = max((r['Mex_Curr'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
            pct_prev_scale = max((r['Mex_Prev'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
            
            desc_wrapped = f"{r['COMMODITY']} - {r['DESC']}"
            
            html += f"""<div style="display: flex; width: 100%; align-items: stretch; margin-bottom: 18px; justify-content: space-between; gap: 15px;">
    <div style="flex: 0 0 20%; padding-left: 5px; font-size: 0.85rem; display: flex; align-items: center;">
    <span style="display: inline-block; width: 100%; text-align: justify; text-justify: inter-word; hyphens: auto; line-height: 1.3; color: #0F172A; font-weight: 600;">{desc_wrapped}</span>
    </div>
    <div style="flex: 1; border-left: 2px solid #E2E8F0; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; gap: 8px;">
    <div style="display:flex; align-items:center; width: 100%;">
    <div style="background-color: {color_mex}; width: {pct_prev_scale}%; height: 12px; border-radius: 4px; opacity: 0.6;"></div>
    <span style="margin-left: 10px; font-weight: 600; font-size: 0.75rem; color: #64748B;">${r['Mex_Prev']:,.0f}</span>
    </div>
    <div style="display:flex; align-items:center; width: 100%;">
    <div style="background-color: {color_mex}; width: {pct_curr_scale}%; height: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
    <span style="margin-left: 10px; font-weight: 800; font-size: 0.95rem; color: #0F172A;">${r['Mex_Curr']:,.0f}</span>
    </div>
    </div>
    <div style="flex: 0 0 12%; display: flex; flex-direction: column; justify-content: center; gap: 8px; align-items: center;">
    <div style="background-color: #F1F5F9; border:1px solid #E2E8F0; border-radius: 6px; width: 100%; font-weight: 700; font-size: 0.75rem; color: #64748B; text-align: center; height: 22px; display: flex; align-items: center; justify-content: center;">
    {r['Part_Interna_Prev']:.1f}%
    </div>
    <div style="background-color: #F8FAFC; border:1px solid #E2E8F0; border-radius: 6px; width: 100%; font-weight: 800; font-size: 0.85rem; color: {color_mex}; text-align: center; height: 26px; display: flex; align-items: center; justify-content: center;">
    {r['Part_Interna']:.1f}%
    </div>
    </div>
    </div>"""
        html += "</div>"
        return html.replace('\n', '')
    
    # ------------------------------------------
    # RENDERIZADO DEL DASHBOARD (ESTADO INDIVIDUAL)
    # ------------------------------------------
    reps = US_FIGURES.get(selected_state_code, "Representantes No Disponibles")
    trade_reps = US_TRADE_REPS.get(selected_state_code, None)
    
    st.markdown(f"<h1 style='color: #2596be; font-size: 2.8rem;'>Análisis Comercial: {selected_state_name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #64748B; margin-top:-15px; margin-bottom:10px; font-weight:600;'>{seccion_sel} | Unidad de Medida: Dólares Estadounidenses</p>", unsafe_allow_html=True)
    
    html_reps = f"<div style='background-color: #E2E8F0; padding: 10px 15px; border-radius: 8px; margin-bottom: 30px; display: inline-block;'><span style='color: #475569; font-size: 0.9rem;'><b>Representación en el Senado:</b> {reps}</span>"
    if trade_reps:
        html_reps += f"<br><span style='color: #475569; font-size: 0.9rem; margin-top: 5px; display: inline-block;'><b>Miembros del Subcomité de Comercio (Cámara de Reps):</b> {trade_reps}</span>"
    html_reps += "</div>"
    
    st.markdown(html_reps, unsafe_allow_html=True)
    
    # ==========================================
    # EVOLUCIÓN HISTÓRICA (NUEVA GRÁFICA)
    # ==========================================
    st.markdown("<hr style='border-color: #E2E8F0; border-width: 2px; margin-top:20px; margin-bottom:20px;'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: #0F172A; margin-bottom: 20px;'>Evolución Histórica: Subpartidas Principales</h3>", unsafe_allow_html=True)
    
    col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns(5)
    with col_h1:
        socio_sel = st.selectbox("Socio Comercial", ["Mundo", "México"], key="est_socio")
        ruta_hist = RUTA_TOT if socio_sel == "Mundo" else RUTA_MEX
    with col_h2:
        flujo_hist = st.selectbox("Flujo Comercial", ["Comercio Total", "Importaciones", "Exportaciones"], key="est_flujo")
        flow_cond_hist = "1=1" if flujo_hist == "Comercio Total" else ("flow = 'imports'" if flujo_hist == "Importaciones" else "flow = 'exports'")
    with col_h3:
        per_hist = st.selectbox("Tipo de Periodo", ["YTD", "Anual", "Mensual", "Mes Específico", "Acumulado"], key="est_per")
    with col_h4:
        anio_ini = st.selectbox("Año Inicio", sorted(lista_anios), key="est_aini", index=0)
    with col_h5:
        anio_fin = st.selectbox("Año Fin", sorted(lista_anios, reverse=True), key="est_afin", index=0)
        
    meses_cond_hist = "1=1"
    todos_los_meses = list(range(1, 13))
    
    # Contenedores para selectores dinámicos de meses
    if per_hist in ["Mes Específico", "Acumulado"]:
        col_hm1, col_hm2 = st.columns(2)
        
    if per_hist == "YTD":
        mes_max_global = max(meses_list) if meses_list else 12
        m_sql = ", ".join([str(m) for m in todos_los_meses if m <= mes_max_global])
        meses_cond_hist = f"month IN ({m_sql})" if m_sql else "1=0"
    elif per_hist == "Mes Específico":
        with col_hm1:
            mes_sel_h = st.selectbox("Mes", todos_los_meses, key="est_mes")
            meses_cond_hist = f"month = {mes_sel_h}"
    elif per_hist == "Mensual":
        meses_cond_hist = "1=1" # Trae todos los meses cronológicamente
    elif per_hist == "Acumulado":
        with col_hm1:
            mes_ini_h = st.selectbox("Mes Inicio", todos_los_meses, key="est_mini")
        with col_hm2:
            mes_fin_h = st.selectbox("Mes Fin", todos_los_meses, index=11, key="est_mfin")
        if mes_ini_h and mes_fin_h:
            meses_cond_hist = f"month BETWEEN {mes_ini_h} AND {mes_fin_h}"
            
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    
    # Pre-calcular subpartidas disponibles en el rango
    q_subs_hist = f"SELECT DISTINCT COMMODITY, COM_DESC FROM '{ruta_hist}' WHERE STATE='{selected_state_code}' AND {caps_cond} AND {flow_cond_hist} AND year BETWEEN {anio_ini} AND {anio_fin} ORDER BY COMMODITY"
    df_subs_hist = duckdb.query(q_subs_hist).to_df()
    
    dict_subs_hist = {}
    if not df_subs_hist.empty:
        for _, r in df_subs_hist.iterrows():
            dict_subs_hist[r['COM_DESC']] = r['COMMODITY']
            
    opciones_especiales = ["Total de la Sección", "Top 5 Subpartidas", "Top 10 Subpartidas"]

    # Pre-cálculo dinámico: qué Top (5/10) está activo ahora mismo, para (a) excluir
    # esas subpartidas del resto de la lista (evita seleccionarlas 2 veces) y
    # (b) reutilizar el mismo resultado más abajo sin volver a consultar.
    sel_previa = list(st.session_state.get("est_multi", ["Top 5 Subpartidas"]))
    n_lim_previo = 10 if "Top 10 Subpartidas" in sel_previa else (5 if "Top 5 Subpartidas" in sel_previa else 0)

    codigos_top_previos = set()
    if n_lim_previo > 0:
        q_top_previo = f"SELECT COMMODITY FROM '{ruta_hist}' WHERE STATE='{selected_state_code}' AND {caps_cond} AND {flow_cond_hist} AND year={anio_fin} AND {meses_cond_hist} GROUP BY COMMODITY ORDER BY SUM(VALOR) DESC LIMIT {n_lim_previo}"
        df_top_previo = duckdb.query(q_top_previo).to_df()
        if not df_top_previo.empty:
            codigos_top_previos.update(df_top_previo['COMMODITY'].tolist())

    opciones_todas = opciones_especiales + [desc for desc, cod in dict_subs_hist.items() if cod not in codigos_top_previos]

    # Si alguna subpartida manual quedó "cubierta" por el Top activo, la quitamos
    # de la selección guardada para que no se pueda duplicar.
    sel_previa_limpia = [s for s in sel_previa if s in opciones_especiales or dict_subs_hist.get(s) not in codigos_top_previos]
    if sel_previa_limpia != sel_previa:
        st.session_state["est_multi"] = sel_previa_limpia
    
    subp_seleccionadas = st.multiselect(
        "Selecciona las Subpartidas a graficar", 
        options=opciones_todas, 
        default=["Top 5 Subpartidas"], 
        key="est_multi",
        on_change=_alternar_top_exclusivo,
        args=("est_multi",)
    )

    # Configuraciones dinámicas de agrupación (SQL)
    if per_hist == "Mensual":
        x_select = "CAST(year AS VARCHAR) || '-' || RIGHT('0' || CAST(month AS VARCHAR), 2)"
        group_cols = "year, month"
        order_cols = "year, month"
    else:
        x_select = "CAST(year AS VARCHAR)"
        group_cols = "year"
        order_cols = "year"
        
    def _construir_df_hist_estatal(modo_total, codigos_para_query):
        """Arma el df para el modo 'Total de la Sección' o para un set de códigos
        (Top 5/10 + manuales). Se llama hasta 2 veces y se concatena el resultado,
        así ambos modos pueden convivir en la misma gráfica."""
        codigos_txt = ", ".join([f"'{c}'" for c in codigos_para_query]) if codigos_para_query else ""
        filtro_cod = f"AND COMMODITY IN ({codigos_txt})" if (not modo_total and codigos_txt) else ""
        sel_comm = "" if modo_total else "COMMODITY,"
        grp_comm = "" if modo_total else ", COMMODITY"
        desc_expr = "'Total de la Sección'" if modo_total else "MAX(COM_DESC)"
        join_comm = "" if modo_total else "AND t.COMMODITY = m.COMMODITY"

        if socio_sel == "Mundo":
            q = f"""
                WITH base_tot AS (
                    SELECT {x_select} AS periodo, {group_cols},
                           {desc_expr} as COM_DESC,
                           {sel_comm}
                           SUM(VALOR) as VALOR
                    FROM '{RUTA_TOT}'
                    WHERE STATE='{selected_state_code}' AND {caps_cond} AND {flow_cond_hist} AND year BETWEEN {anio_ini} AND {anio_fin} AND {meses_cond_hist}
                    {filtro_cod}
                    GROUP BY {group_cols} {grp_comm}
                ),
                base_mex AS (
                    SELECT {group_cols},
                           {sel_comm}
                           SUM(VALOR) as MEX_VALOR
                    FROM '{RUTA_MEX}'
                    WHERE STATE='{selected_state_code}' AND {caps_cond} AND {flow_cond_hist} AND year BETWEEN {anio_ini} AND {anio_fin} AND {meses_cond_hist}
                    {filtro_cod}
                    GROUP BY {group_cols} {grp_comm}
                )
                SELECT t.periodo, t.COM_DESC, t.VALOR, COALESCE(m.MEX_VALOR, 0) as REF_VALOR
                FROM base_tot t
                LEFT JOIN base_mex m ON t.year = m.year 
                    { 'AND t.month = m.month' if 'month' in group_cols else '' }
                    {join_comm}
                ORDER BY t.{order_cols.replace(', ', ', t.')}
            """
        else:
            q = f"""
                WITH base_mex AS (
                    SELECT {x_select} AS periodo, {group_cols},
                           {desc_expr} as COM_DESC,
                           {sel_comm}
                           SUM(VALOR) as VALOR
                    FROM '{RUTA_MEX}'
                    WHERE STATE='{selected_state_code}' AND {caps_cond} AND {flow_cond_hist} AND year BETWEEN {anio_ini} AND {anio_fin} AND {meses_cond_hist}
                    {filtro_cod}
                    GROUP BY {group_cols} {grp_comm}
                ),
                base_mex_total AS (
                    SELECT {group_cols}, SUM(VALOR) as TOTAL_SECCION
                    FROM '{RUTA_MEX}'
                    WHERE STATE='{selected_state_code}' AND {caps_cond} AND {flow_cond_hist} AND year BETWEEN {anio_ini} AND {anio_fin} AND {meses_cond_hist}
                    GROUP BY {group_cols}
                )
                SELECT m.periodo, m.COM_DESC, m.VALOR, COALESCE(mt.TOTAL_SECCION, 0) as REF_VALOR
                FROM base_mex m
                LEFT JOIN base_mex_total mt ON m.year = mt.year 
                    { 'AND m.month = mt.month' if 'month' in group_cols else '' }
                ORDER BY m.{order_cols.replace(', ', ', m.')}
            """
        return duckdb.query(q).to_df()

    is_total = "Total de la Sección" in subp_seleccionadas
    codigos_finales = set(codigos_top_previos)
    for s in subp_seleccionadas:
        if s not in opciones_especiales:
            codigos_finales.add(dict_subs_hist[s])
    hay_codigos = len(codigos_finales) > 0
    debe_graficar = is_total or hay_codigos
    hover_part_label = "Part. MX" if socio_sel == "Mundo" else "Part. Interna"

    if debe_graficar:
        dfs_hist = []
        if hay_codigos:
            dfs_hist.append(_construir_df_hist_estatal(False, codigos_finales))
        if is_total:
            dfs_hist.append(_construir_df_hist_estatal(True, None))
        df_line = pd.concat(dfs_hist, ignore_index=True) if dfs_hist else pd.DataFrame()
        
        if not df_line.empty:
            # Cálculo de Participación
            if socio_sel == "Mundo":
                df_line['Participacion'] = (df_line['REF_VALOR'] / df_line['VALOR']) * 100
            else:
                df_line['Participacion'] = (df_line['VALOR'] / df_line['REF_VALOR']) * 100
            
            df_line['Participacion'] = df_line['Participacion'].fillna(0)
            
            # Construcción de Gráfica Plotly
            fig_line = px.line(df_line, x="periodo", y="VALOR", color="COM_DESC", markers=True, custom_data=['Participacion'], hover_name="COM_DESC")
            
            fig_line.update_layout(
                xaxis_title="", 
                yaxis_title="Dólares", 
                plot_bgcolor='#F8FAFC', 
                paper_bgcolor='#F8FAFC',
                # Orientación vertical; margin_autoexpand evitará huecos en blanco dinámicamente
                legend=dict(orientation="v", yanchor="top", y=-0.08, xanchor="left", x=0, title=None, font=dict(size=11)),
                margin=dict(l=10, r=10, t=30, b=10), # Margen fijo reducido al mínimo
                height=500 # Altura ajustada
            )
            
            # Forzamos el inicio en 0
            fig_line.update_yaxes(rangemode="tozero", showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1", tickprefix="$")
            
            if per_hist != "Mensual":
                fig_line.update_xaxes(dtick=1, showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1")
            else:
                fig_line.update_xaxes(showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1")
            
            fig_line.update_traces(
                line=dict(width=3), 
                marker=dict(size=8), 
                hovertemplate=(
                    "<span style='color:#7dd3c8; font-weight:700;'>Periodo:</span> %{x}<br>"
                    "<span style='color:#7dd3c8; font-weight:700;'>Valor:</span> $%{y:,.0f} USD<br>"
                    f"<span style='color:#7dd3c8; font-weight:700;'>{hover_part_label}:</span> %{{customdata[0]:.1f}}%<extra></extra>"
                ),
                hoverlabel=dict(bgcolor='#0F172A', font_size=13, font_family='sans-serif', font_color='#F8FAFC', bordercolor='#0F172A', align='left')
            )
            
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No hay operaciones registradas para la configuración temporal seleccionada.")
    else:
        if not subp_seleccionadas:
            st.warning("Selecciona al menos una opción (Top, Total o subpartidas específicas) para generar la gráfica.")
        else:
            st.info("No se encontraron subpartidas con operaciones para tu combinación de filtros.")

    # ==========================================
    # IMPORTACIONES DEL ESTADO (CÓDIGO ORIGINAL)
    # ==========================================
    st.markdown("<hr style='border-color: #2596be; border-width: 2px; margin-bottom:0px; margin-top:30px;'>", unsafe_allow_html=True)
    st.header("Importaciones del Estado")
    
    st.markdown(get_full_year_total_bar('imports', color_mex="#2596be"), unsafe_allow_html=True)
    
    st.markdown(f"<h4 style='color:#0F172A; margin-top:15px;'>1. Top 5 Subpartidas Importadas por {selected_state_name} y Participación de México</h4>", unsafe_allow_html=True)
    st.markdown(get_top_5_total_split('imports', color_mex="#2596be", color_rest="#CBD5E1"), unsafe_allow_html=True)
    
    st.markdown(f"<h4 style='color:#0F172A; margin-top:30px;'>2. Top 5 Subpartidas Provenientes de México</h4>", unsafe_allow_html=True)
    st.markdown(get_top_5_mexico_base('imports', color_mex="#2596be"), unsafe_allow_html=True)
    
    st.markdown("<hr style='border-color: #008889; border-width: 2px; margin-top:40px; margin-bottom:0px;'>", unsafe_allow_html=True)
    st.header("Exportaciones del Estado")
    
    st.markdown(get_full_year_total_bar('exports', color_mex="#008889"), unsafe_allow_html=True)
    
    st.markdown(f"<h4 style='color:#0F172A; margin-top:15px;'>3. Top 5 Subpartidas Exportadas por {selected_state_name} y Participación a México</h4>", unsafe_allow_html=True)
    st.markdown(get_top_5_total_split('exports', color_mex="#008889", color_rest="#CBD5E1"), unsafe_allow_html=True)
    
    st.markdown(f"<h4 style='color:#0F172A; margin-top:30px;'>4. Top 5 Subpartidas Destinadas a México</h4>", unsafe_allow_html=True)
    st.markdown(get_top_5_mexico_base('exports', color_mex="#008889"), unsafe_allow_html=True)
    
    del df_mex_ytd
    del df_tot_ytd
    gc.collect()