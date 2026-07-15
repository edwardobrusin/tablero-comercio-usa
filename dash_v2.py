import streamlit as st
import pandas as pd
import numpy as np
import os
import textwrap
import gc
import duckdb
import plotly.express as px

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
</style>
""", unsafe_allow_html=True)

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
# Rutas globales a los nuevos archivos completos (no se suben a RAM, solo son referencias)
RUTA_MEX = os.path.join("data", "comercio_mexico.parquet")
RUTA_TOT = os.path.join("data", "comercio_total.parquet")

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
max_year = duckdb.query(f"SELECT MAX(year) FROM '{RUTA_TOT}'").fetchone()[0]
todos_los_anios_query = duckdb.query(f"SELECT DISTINCT year FROM '{RUTA_TOT}' ORDER BY year DESC").fetchall()
lista_anios = [a[0] for a in todos_los_anios_query]
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
                m_sql = ", ".join([f"'{str(m).zfill(2)}'" for m in lista_meses_act if int(m) <= int(mes_max_global)])
                meses_cond = f"month IN ({m_sql})" if m_sql else "1=0"
        elif periodo_sel == "Mensual":
            mes_sel = st.selectbox("Selecciona Mes", lista_meses_act, key="nac_mes")
            meses_cond = f"month = '{str(mes_sel).zfill(2)}'"
        elif periodo_sel == "Acumulado":
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                mes_ini = st.selectbox("Mes Inicio", lista_meses_act, key="nac_mini")
            with col_m2:
                mes_fin = st.selectbox("Mes Fin", lista_meses_act, index=len(lista_meses_act)-1 if lista_meses_act else 0, key="nac_mfin")
            if mes_ini and mes_fin:
                meses_cond = f"CAST(month AS INTEGER) BETWEEN {int(mes_ini)} AND {int(mes_fin)}"

    with col_f3:
        q_subs = f"SELECT DISTINCT CAST(COMMODITY AS VARCHAR) AS COMMODITY, \"DESC\" FROM '{RUTA_TOT}' WHERE {caps_cond} AND {flow_cond} AND year = {anio_sel} AND {meses_cond}"
        df_subs = duckdb.query(q_subs).to_df()
        
        dict_subs = {"Total de la sección": "TOTAL"}
        if not df_subs.empty:
            df_subs = df_subs.sort_values('COMMODITY')
            df_subs['COM_DESC'] = df_subs['COMMODITY'] + " - " + df_subs['DESC']
            for _, r in df_subs.iterrows():
                dict_subs[r['COM_DESC']] = str(r['COMMODITY'])  # blindaje: nunca perder ceros a la izquierda
                
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
        map_event = st.plotly_chart(
            fig, 
            use_container_width=True, 
            config={
                'displayModeBar': False, 
                'scrollZoom': False,
                'doubleClick': False
            }, 
            on_select="rerun", 
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
        
        if clicked_state:
            nombre_estado_click = US_STATES.get(clicked_state, clicked_state)
            st.markdown(f"<h3 style='margin-top: 30px; color: #0F172A; text-align: center;'>Top 3 Subpartidas: {nombre_estado_click}</h3>", unsafe_allow_html=True)
            
            col_imp, col_exp = st.columns(2)
            
            with col_imp:
                st.markdown("<h4 style='color: #2596be;'>Importaciones (El Estado Importa)</h4>", unsafe_allow_html=True)
                q_top_imp_tot = f"SELECT CAST(COMMODITY AS VARCHAR) AS COMMODITY, \"DESC\", SUM(VALOR) as Tot_Imp FROM '{RUTA_TOT}' WHERE STATE='{clicked_state}' AND flow='imports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} GROUP BY COMMODITY, \"DESC\" ORDER BY Tot_Imp DESC LIMIT 3"
                q_top_imp_mex = f"SELECT CAST(COMMODITY AS VARCHAR) AS COMMODITY, SUM(VALOR) as Mex_Imp FROM '{RUTA_MEX}' WHERE STATE='{clicked_state}' AND flow='imports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} GROUP BY COMMODITY"
                
                df_ti_tot = duckdb.query(q_top_imp_tot).to_df()
                df_ti_mex = duckdb.query(q_top_imp_mex).to_df()
                
                if not df_ti_tot.empty:
                    df_ti = df_ti_tot.merge(df_ti_mex, on='COMMODITY', how='left').fillna(0)
                    df_ti['Part_Mex'] = (df_ti['Mex_Imp'] / df_ti['Tot_Imp']) * 100
                    st.dataframe(df_ti[['COMMODITY', 'DESC', 'Tot_Imp', 'Part_Mex']].style.format({'Tot_Imp': '${:,.0f}', 'Part_Mex': '{:.1f}%'}), use_container_width=True, hide_index=True)
                else:
                    st.info("No hay datos de importaciones para esta selección.")

            with col_exp:
                st.markdown("<h4 style='color: #008889;'>Exportaciones (El Estado Exporta)</h4>", unsafe_allow_html=True)
                q_top_exp_tot = f"SELECT CAST(COMMODITY AS VARCHAR) AS COMMODITY, \"DESC\", SUM(VALOR) as Tot_Exp FROM '{RUTA_TOT}' WHERE STATE='{clicked_state}' AND flow='exports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} GROUP BY COMMODITY, \"DESC\" ORDER BY Tot_Exp DESC LIMIT 3"
                q_top_exp_mex = f"SELECT CAST(COMMODITY AS VARCHAR) AS COMMODITY, SUM(VALOR) as Mex_Exp FROM '{RUTA_MEX}' WHERE STATE='{clicked_state}' AND flow='exports' AND {caps_cond} AND year={anio_sel} AND {meses_cond} AND {subp_cond} GROUP BY COMMODITY"
                
                df_te_tot = duckdb.query(q_top_exp_tot).to_df()
                df_te_mex = duckdb.query(q_top_exp_mex).to_df()
                
                if not df_te_tot.empty:
                    df_te = df_te_tot.merge(df_te_mex, on='COMMODITY', how='left').fillna(0)
                    df_te['Part_Mex'] = (df_te['Mex_Exp'] / df_te['Tot_Exp']) * 100
                    st.dataframe(df_te[['COMMODITY', 'DESC', 'Tot_Exp', 'Part_Mex']].style.format({'Tot_Exp': '${:,.0f}', 'Part_Mex': '{:.1f}%'}), use_container_width=True, hide_index=True)
                else:
                    st.info("No hay datos de exportaciones para esta selección.")
    else:
        st.warning("No hay datos geográficos para esta combinación de filtros.")

else:
    # ==========================================
    # LÓGICA DE ESTADO (ANÁLISIS INDIVIDUAL)
    # ==========================================
    meses_sql = ", ".join([str(m) for m in meses_list])
    
    query_base = f"""
        SELECT 
            CAST(COMMODITY AS VARCHAR) AS COMMODITY, 
            "DESC",
            CAST(Chapter AS VARCHAR) AS Chapter,
            STATE, flow, year, month, VALOR
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
        query_tot = f"SELECT SUM(VALOR) FROM '{RUTA_TOT}' WHERE STATE = '{selected_state_code}' AND {caps_cond} AND flow = '{flow_type}' AND year = {max_year - 1}"
        query_mex = f"SELECT SUM(VALOR) FROM '{RUTA_MEX}' WHERE STATE = '{selected_state_code}' AND {caps_cond} AND flow = '{flow_type}' AND year = {max_year - 1}"
        
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
    <div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{max_year - 1}</div>
    <div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{label_curr}</div>
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
    <div style="flex: 0 0 10%; display: flex; justify-content: center; align-items: center;">
    <div style="background-color: #F1F5F9; border:1px solid #E2E8F0; border-radius: 8px; padding: 6px 0; width: 100%; font-weight: 700; font-size: 0.85rem; color: #64748B; text-align: center;">
    {r['Part_Mex_Prev']:.1f}%
    </div>
    </div>
    <div style="flex: 0 0 10%; display: flex; justify-content: center; align-items: center;">
    <div style="background-color: #F8FAFC; border:1px solid #E2E8F0; border-radius: 8px; padding: 6px 0; width: 100%; font-weight: 800; font-size: 0.95rem; color: {color_mex}; text-align: center;">
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
    <div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{max_year - 1}</div>
    <div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{label_curr}</div>
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
    <div style="flex: 0 0 10%; display: flex; justify-content: center; align-items: center;">
    <div style="background-color: #F1F5F9; border:1px solid #E2E8F0; border-radius: 8px; padding: 6px 0; width: 100%; font-weight: 700; font-size: 0.85rem; color: #64748B; text-align: center;">
    {r['Part_Interna_Prev']:.1f}%
    </div>
    </div>
    <div style="flex: 0 0 10%; display: flex; justify-content: center; align-items: center;">
    <div style="background-color: #F8FAFC; border:1px solid #E2E8F0; border-radius: 8px; padding: 6px 0; width: 100%; font-weight: 800; font-size: 0.95rem; color: {color_mex}; text-align: center;">
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
    
    st.markdown("<hr style='border-color: #2596be; border-width: 2px; margin-bottom:0px;'>", unsafe_allow_html=True)
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