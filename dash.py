import streamlit as st
import pandas as pd
import numpy as np
import os
import textwrap
import base64
import zipfile
import gc

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
    "Sección I: Animales Vivos y Productos": ["01", "02", "03", "04", "05"],
    "Sección II: Productos Vegetales": [str(i).zfill(2) for i in range(6, 15)]
}

# ==========================================
# 3. CARGA DE DATOS Y SIMULACIÓN
# ==========================================
@st.cache_resource
def load_data():
    try:
        # Cargamos las bases que ya vienen extirpadas y ultra-comprimidas (int16, category)
        df_mex = pd.read_parquet(os.path.join("data", "comercio_mexico_opt.parquet"))
        df_tot = pd.read_parquet(os.path.join("data", "comercio_total_opt.parquet"))
        df_dict = pd.read_parquet(os.path.join("data", "diccionario_desc.parquet"))
        
        # Convertimos la tabla del diccionario a un diccionario nativo de Python (rapidísimo en memoria)
        dict_desc = dict(zip(df_dict['COMMODITY'], df_dict['DESC']))
        
        return df_mex, df_tot, dict_desc
    except Exception as e:
        st.error(f"Error cargando los archivos Parquet: {e}")
        return pd.DataFrame(), pd.DataFrame(), {}

df_mex, df_tot, dict_desc = load_data()
if df_mex.empty: st.stop()

# ==========================================
# 4. LOGOS INSTITUCIONALES & SIDEBAR
# ==========================================
col_logo1, col_logo2 = st.sidebar.columns(2)
try:
    with col_logo1: st.image("logos/logo-01.png", use_container_width=True)
    with col_logo2: st.image("logos/logo-02.png", use_container_width=True)
except: pass
st.sidebar.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# Selector de Sección HTS
st.sidebar.markdown("<h3 style='font-size: 1.1rem; color:#0F172A; margin-bottom: 5px;'>1. Sección Arancelaria</h3>", unsafe_allow_html=True)
seccion_sel = st.sidebar.selectbox("Filtro HTS", list(HTS_SECTIONS.keys()), label_visibility="collapsed")

st.sidebar.markdown("<h3 style='font-size: 1.1rem; color:#0F172A; margin-top: 15px; margin-bottom: 10px;'>2. Selecciona Estado</h3>", unsafe_allow_html=True)

if 'estado_us_sel' not in st.session_state:
    st.session_state['estado_us_sel'] = 'TX'

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
# BOTÓN FLOTANTE DE DESCARGA
# ==========================================
# Extraemos el número romano de la sección para identificar la carpeta (Ej. "Sección I: ..." -> "I")
sec_num = seccion_sel.split(':')[0].split(' ')[1] 
carpeta_pdf = f"comercio_sec_{sec_num}"
nombre_pdf_interno = f"{carpeta_pdf}/{selected_state_name}.pdf"
ruta_zip = "fichas_comercio_us.zip"

html_boton = ""
pdf_encontrado = False
base64_pdf = ""

# 1. Intentamos leer desde el ZIP (si existe)
if os.path.exists(ruta_zip):
    try:
        with zipfile.ZipFile(ruta_zip, 'r') as zf:
            # Verificamos si el archivo existe con / o con \\ (dependiendo del OS que generó el zip)
            posibles_rutas = [nombre_pdf_interno, f"{carpeta_pdf}\\{selected_state_name}.pdf"]
            for ruta in posibles_rutas:
                if ruta in zf.namelist():
                    with zf.open(ruta) as f:
                        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    pdf_encontrado = True
                    break
    except zipfile.BadZipFile:
        st.sidebar.error("El archivo ZIP está corrupto.")

# 2. Fallback: Intentamos leer de la carpeta local directamente si el ZIP no existe o se extrajo
if not pdf_encontrado and os.path.exists(nombre_pdf_interno):
    try:
        with open(nombre_pdf_interno, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_encontrado = True
    except Exception:
        pass

if pdf_encontrado:
    # Ícono SVG estándar universal para descargas
    svg_icon = '''
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" style="width: 24px; height: 24px;">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
    '''
    
    # Nombre de descarga dinámico para saber el Estado y la Sección Arancelaria
    download_name = f"Ficha_Comercio_{selected_state_name.replace(' ', '_')}_Sec_{sec_num}.pdf"

    html_boton = f"""
    <style>
        .floating-download-btn {{
            position: fixed;
            bottom: 50px;
            right: 20px;
            background-color: #2596be;
            color: white !important;
            border-radius: 50%;
            width: 56px;
            height: 56px;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
        }}
        .floating-download-btn:hover {{
            background-color: #1e7a9b;
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }}
    </style>
    <a href="data:application/pdf;base64,{base64_pdf}" download="{download_name}" class="floating-download-btn" title="Descargar Ficha PDF">
        {svg_icon}
    </a>
    """
    st.markdown(html_boton, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .floating-warning {
            position: fixed; bottom: 50px; right: 20px; background-color: #64748B; color: white;
            padding: 10px 20px; border-radius: 20px; font-size: 0.8rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 9999;
        }
    </style>
    <div class="floating-warning">Actualizando PDF...</div>
    """, unsafe_allow_html=True)

# ==========================================
# 5. FILTRADO TEMPORAL (LÓGICA YTD)
# ==========================================
capitulos_validos = HTS_SECTIONS[seccion_sel]

# Calculamos el tiempo base globalmente
max_year = int(df_tot['year'].max())
meses_max_year = df_tot[df_tot['year'] == max_year]['month'].unique()
meses_list = sorted(list(meses_max_year))

# Máscaras de 1 solo paso: Combinamos los filtros para NUNCA instanciar dataframes intermedios y ahorrar RAM
mask_mex_ytd = (
    (df_mex['STATE'] == selected_state_code) & 
    (df_mex['Chapter'].isin(capitulos_validos)) & 
    (df_mex['year'].isin([max_year, max_year - 1])) & 
    (df_mex['month'].isin(meses_max_year))
)
df_mex_ytd = df_mex[mask_mex_ytd]

mask_tot_ytd = (
    (df_tot['STATE'] == selected_state_code) & 
    (df_tot['Chapter'].isin(capitulos_validos)) & 
    (df_tot['year'].isin([max_year, max_year - 1])) & 
    (df_tot['month'].isin(meses_max_year))
)
df_tot_ytd = df_tot[mask_tot_ytd]

# Etiqueta dinámica de periodo
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

# ==========================================
# 6. MOTORES DE GENERACIÓN HTML
# ==========================================

def get_full_year_total_bar(flow_type, color_mex):
    # Calculamos el total de todo el año anterior directamente desde la base limpia para evitar variables
    mask_tot_prev = (df_tot['STATE'] == selected_state_code) & (df_tot['Chapter'].isin(capitulos_validos)) & (df_tot['flow'] == flow_type) & (df_tot['year'] == max_year - 1)
    tot_prev_year = df_tot[mask_tot_prev]['VALOR'].sum()
    
    mask_mex_prev = (df_mex['STATE'] == selected_state_code) & (df_mex['Chapter'].isin(capitulos_validos)) & (df_mex['flow'] == flow_type) & (df_mex['year'] == max_year - 1)
    mex_prev_year = df_mex[mask_mex_prev]['VALOR'].sum()

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
    return html

def get_top_10_total_split(flow_type, color_mex, color_rest):
    """Genera la estructura de la Gráfica 1 y 3 (Top Totales con División México)"""
    
    df_t_flow = df_tot_ytd[df_tot_ytd['flow'] == flow_type]
    df_m_flow = df_mex_ytd[df_mex_ytd['flow'] == flow_type]
    
    # Groupby rápido de enteros (Sin arrastrar columnas de texto gigante)
    tot_agg = df_t_flow.groupby(['COMMODITY', 'year'])['VALOR'].sum().reset_index()
    mex_agg = df_m_flow.groupby(['COMMODITY', 'year'])['VALOR'].sum().reset_index()
    
    # Totales para las barras maestras integradas en la tarjeta
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
    df_chart.fillna(0, inplace=True)
    
    top10 = df_chart.sort_values('Tot_Curr', ascending=False).head(10).copy()
    if top10.empty: return "<div style='padding:20px; color:#64748B;'>No hay datos para esta selección.</div>"
    
    top10['Part_Mex'] = (top10['Mex_Curr'] / top10['Tot_Curr']) * 100
    top10['Part_Mex'] = top10['Part_Mex'].fillna(0)
    
    top10['Part_Mex_Prev'] = (top10['Mex_Prev'] / top10['Tot_Prev']) * 100
    top10['Part_Mex_Prev'] = top10['Part_Mex_Prev'].fillna(0)
    
    # Restauramos la descripción solo para el Top 10 ganador
    top10['DESC'] = top10['COMMODITY'].map(dict_desc).fillna("Desc. no disponible")
    
    max_scale = max(top10['Tot_Curr'].max(), top10['Tot_Prev'].max())
    
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
<div style="flex: 0 0 18%; text-align: left; padding-left: 5px;">Subpartida (HTS 6)</div>
<div style="flex: 1; text-align: left; padding-left: 15px;">Valor Histórico (Dólares) - <span style="color:{color_mex};">■ México</span> <span style="color:{color_rest};">■ Resto del Mundo</span></div>
<div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{max_year - 1}</div>
<div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{label_curr}</div>
</div>"""

    for _, r in top10.iterrows():
        pct_tot_curr_scale = max((r['Tot_Curr'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
        pct_tot_prev_scale = max((r['Tot_Prev'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
        
        pct_mex_curr = (r['Mex_Curr'] / r['Tot_Curr']) * 100 if r['Tot_Curr'] > 0 else 0
        pct_rest_curr = 100 - pct_mex_curr
        
        pct_mex_prev = (r['Mex_Prev'] / r['Tot_Prev']) * 100 if r['Tot_Prev'] > 0 else 0
        pct_rest_prev = 100 - pct_mex_prev

        desc_wrapped = '<br>'.join(textwrap.wrap(f"{r['COMMODITY']} - {r['DESC']}", width=65))
        
        html += f"""<div style="display: flex; width: 100%; align-items: stretch; margin-bottom: 18px; justify-content: space-between; gap: 15px;">
<div style="flex: 0 0 18%; text-align: left; padding-left: 5px; font-size: 0.85rem; display: flex; align-items: center; justify-content: flex-start;">
<span style="display: inline-block; line-height: 1.3; color: #0F172A; font-weight: 600;">{desc_wrapped}</span>
</div>
<div style="flex: 1; border-left: 2px solid #E2E8F0; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; gap: 8px;">
<div style="display:flex; align-items:center; width: 100%;">
<div style="width: {pct_tot_prev_scale}%; height: 12px; border-radius: 4px; display: flex; overflow: hidden; opacity: 0.7;">
<div style="background-color: {color_mex}; width: {pct_mex_prev}%;"></div>
<div style="background-color: {color_rest}; width: {pct_rest_prev}%;"></div>
</div>
<span style="margin-left: 10px; font-weight: 600; font-size: 0.75rem; color: #64748B;">${r['Tot_Prev']:,.0f} <span style="font-size:0.6rem;">({label_prev})</span></span>
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
    return html

def get_top_10_mexico_base(flow_type, color_mex):
    """Genera la estructura de la Gráfica 2 y 4 (Top Base México)"""
    
    df_m_flow = df_mex_ytd[df_mex_ytd['flow'] == flow_type]
    
    # Groupby rápido de enteros
    mex_agg = df_m_flow.groupby(['COMMODITY', 'year'])['VALOR'].sum().reset_index()
    
    # Totales para las barras maestras integradas en la tarjeta (Solo Base México)
    val_mex_curr = df_m_flow[df_m_flow['year'] == max_year]['VALOR'].sum()
    val_mex_prev = df_m_flow[df_m_flow['year'] == max_year - 1]['VALOR'].sum()

    max_total_scale = max(val_mex_curr, val_mex_prev)
    pct_total_prev_scale = max((val_mex_prev / max_total_scale) * 85 if max_total_scale > 0 else 0, 0.5)
    pct_total_curr_scale = max((val_mex_curr / max_total_scale) * 85 if max_total_scale > 0 else 0, 0.5)
    
    mex_curr = mex_agg[mex_agg['year'] == max_year].rename(columns={'VALOR': 'Mex_Curr'})
    mex_prev = mex_agg[mex_agg['year'] == max_year - 1].rename(columns={'VALOR': 'Mex_Prev'})
    
    df_chart = mex_curr.merge(mex_prev[['COMMODITY', 'Mex_Prev']], on='COMMODITY', how='left')
    df_chart.fillna(0, inplace=True)
    
    top10 = df_chart.sort_values('Mex_Curr', ascending=False).head(10).copy()
    if top10.empty: return "<div style='padding:20px; color:#64748B;'>No hay datos para esta selección.</div>"
    
    total_mex_flow = df_chart['Mex_Curr'].sum()
    top10['Part_Interna'] = (top10['Mex_Curr'] / total_mex_flow) * 100 if total_mex_flow > 0 else 0
    
    total_mex_flow_prev = df_chart['Mex_Prev'].sum()
    top10['Part_Interna_Prev'] = (top10['Mex_Prev'] / total_mex_flow_prev) * 100 if total_mex_flow_prev > 0 else 0
    
    # Restauramos la descripción solo para el Top 10 ganador
    top10['DESC'] = top10['COMMODITY'].map(dict_desc).fillna("Desc. no disponible")
    
    max_scale = max(top10['Mex_Curr'].max(), top10['Mex_Prev'].max())
    
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
<div style="flex: 0 0 18%; text-align: left; padding-left: 5px;">Subpartida (HTS 6)</div>
<div style="flex: 1; text-align: left; padding-left: 15px;">Valor desde México (Dólares)</div>
<div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{max_year - 1}</div>
<div style="flex: 0 0 10%; text-align: center;">Part. MX<br>{label_curr}</div>
</div>"""

    for _, r in top10.iterrows():
        pct_curr_scale = max((r['Mex_Curr'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
        pct_prev_scale = max((r['Mex_Prev'] / max_scale) * 85 if max_scale > 0 else 0, 0.5)
        
        desc_wrapped = '<br>'.join(textwrap.wrap(f"{r['COMMODITY']} - {r['DESC']}", width=65))
        
        html += f"""<div style="display: flex; width: 100%; align-items: stretch; margin-bottom: 18px; justify-content: space-between; gap: 15px;">
<div style="flex: 0 0 18%; text-align: left; padding-left: 5px; font-size: 0.85rem; display: flex; align-items: center; justify-content: flex-start;">
<span style="display: inline-block; line-height: 1.3; color: #0F172A; font-weight: 600;">{desc_wrapped}</span>
</div>
<div style="flex: 1; border-left: 2px solid #E2E8F0; padding-left: 15px; display: flex; flex-direction: column; justify-content: center; gap: 8px;">
<div style="display:flex; align-items:center; width: 100%;">
<div style="background-color: {color_mex}; width: {pct_prev_scale}%; height: 12px; border-radius: 4px; opacity: 0.6;"></div>
<span style="margin-left: 10px; font-weight: 600; font-size: 0.75rem; color: #64748B;">${r['Mex_Prev']:,.0f} <span style="font-size:0.6rem;">({label_prev})</span></span>
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
    return html

# ==========================================
# 7. RENDERIZADO DEL DASHBOARD
# ==========================================
reps = US_FIGURES.get(selected_state_code, "Representantes No Disponibles")
trade_reps = US_TRADE_REPS.get(selected_state_code, None)

st.markdown(f"<h1 style='color: #2596be; font-size: 2.8rem;'>Análisis Comercial: {selected_state_name}</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #64748B; margin-top:-15px; margin-bottom:10px; font-weight:600;'>Filtro Activo: {seccion_sel} | Comparativa YTD: {label_curr} vs {label_prev}</p>", unsafe_allow_html=True)

html_reps = f"<div style='background-color: #E2E8F0; padding: 10px 15px; border-radius: 8px; margin-bottom: 30px; display: inline-block;'><span style='color: #475569; font-size: 0.9rem;'><b>Representación en el Senado:</b> {reps}</span>"
if trade_reps:
    html_reps += f"<br><span style='color: #475569; font-size: 0.9rem; margin-top: 5px; display: inline-block;'><b>Miembros del Subcomité de Comercio (Cámara de Reps):</b> {trade_reps}</span>"
html_reps += "</div>"

st.markdown(html_reps, unsafe_allow_html=True)

# ------------------------------------------
# SECCIÓN: IMPORTACIONES (El Estado importa)
# ------------------------------------------
st.markdown("<hr style='border-color: #2596be; border-width: 2px; margin-bottom:0px;'>", unsafe_allow_html=True)
st.header("Importaciones del Estado")

st.markdown(get_full_year_total_bar('imports', color_mex="#2596be"), unsafe_allow_html=True)

st.markdown(f"<h4 style='color:#0F172A; margin-top:15px;'>1. Top 10 Subpartidas Importadas (Global) y Participación de México</h4>", unsafe_allow_html=True)
st.markdown(get_top_10_total_split('imports', color_mex="#2596be", color_rest="#CBD5E1"), unsafe_allow_html=True)

st.markdown(f"<h4 style='color:#0F172A; margin-top:30px;'>2. Top 10 Subpartidas Provenientes de México</h4>", unsafe_allow_html=True)
st.markdown(get_top_10_mexico_base('imports', color_mex="#2596be"), unsafe_allow_html=True)

# ------------------------------------------
# SECCIÓN: EXPORTACIONES (El Estado exporta)
# ------------------------------------------
st.markdown("<hr style='border-color: #008889; border-width: 2px; margin-top:40px; margin-bottom:0px;'>", unsafe_allow_html=True)
st.header("Exportaciones del Estado")

st.markdown(get_full_year_total_bar('exports', color_mex="#008889"), unsafe_allow_html=True)

st.markdown(f"<h4 style='color:#0F172A; margin-top:15px;'>3. Top 10 Subpartidas Exportadas (Global) y Participación a México</h4>", unsafe_allow_html=True)
st.markdown(get_top_10_total_split('exports', color_mex="#008889", color_rest="#CBD5E1"), unsafe_allow_html=True)

st.markdown(f"<h4 style='color:#0F172A; margin-top:30px;'>4. Top 10 Subpartidas Destinadas a México</h4>", unsafe_allow_html=True)
st.markdown(get_top_10_mexico_base('exports', color_mex="#008889"), unsafe_allow_html=True)

# Limpieza final de memoria (Recolección de basura) para entornos limitados (ej. 1GB en Streamlit Cloud)
gc.collect()