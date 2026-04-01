import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# --- UI CONFIG ---
st.set_page_config(page_title="Quiniela 2026", layout="wide", page_icon="⚽")

# --- 1. DEFINIR FUNCIÓN DE CÁLCULO (DEBE IR AQUÍ ARRIBA) ---
def calculate_score(row):
    try:
        # Validar que existan datos reales (si la celda está vacía, no hay puntos)
        if row['real_home'] == "" or row['real_home'] is None:
            return 0
            
        r_h, r_a = int(row['real_home']), int(row['real_away'])
        p_h, p_a = int(row['predicted_home']), int(row['predicted_away'])

        # 3 Puntos: Resultado exacto
        if r_h == p_h and r_a == p_a:
            return 3
            
        # 1 Punto: Acertar tendencia (Ganador o Empate)
        r_diff = r_h - r_a
        p_diff = p_h - p_a
        
        if (r_diff > 0 and p_diff > 0) or (r_diff < 0 and p_diff < 0) or (r_diff == 0 and p_diff == 0):
            return 1
            
        return 0
    except:
        # Si hay un error de formato en los números, devuelve 0
        return 0

# --- 2. CONEXIÓN A BASE DE DATOS ---
@st.cache_data(ttl=600)
def load_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Verificación híbrida para Local y Nube
        if os.path.exists("secretos.json"):
            creds = Credentials.from_service_account_file("secretos.json", scopes=scope)
        else:
            # Esto se usará cuando lo subas a Streamlit Cloud
            creds_info = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_info, scopes=scope)
            
        client = gspread.authorize(creds)
        spreadsheet = client.open("wcd")
        
        # Carga de pestañas
        p = pd.DataFrame(spreadsheet.worksheet("players").get_all_records())
        m = pd.DataFrame(spreadsheet.worksheet("matches").get_all_records())
        pr = pd.DataFrame(spreadsheet.worksheet("predictions").get_all_records())
        
        return p, m, pr

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# --- 3. LÓGICA DE LA APLICACIÓN ---
df_p, df_m, df_pred = load_data()

# Solo ejecutar si los datos cargaron correctamente
if not df_p.empty and not df_m.empty and not df_pred.empty:
    
    # Unir tablas y aplicar la función de puntos que definimos arriba
    full = df_pred.merge(df_m, on='match_code')
    full['puntos'] = full.apply(calculate_score, axis=1)

    # Sidebar
    st.sidebar.title("⚽ Quiniela Mundial 2026")
    menu = st.sidebar.radio("Ir a:", ["Ranking", "Mis Predicciones"])

    if menu == "Ranking":
        st.header("📊 Tabla General de Posiciones")
        
        # 1. Preparar el Ranking (Igual que antes)
        rank = full.groupby('user_id')['puntos'].sum().reset_index()
        rank = rank.merge(df_p, on='user_id').sort_values('puntos', ascending=False)

        # --- NUEVA SECCIÓN: TOP 3 KPIs (Encima de la tabla) ---
        st.subheader("🏆 Cuadro de Honor")
        col1, col2, col3 = st.columns(3)

        # Extraer los 3 mejores con validación por si hay pocos jugadores
        if len(rank) >= 1:
            col1.metric(label="🥇 1er Lugar", value=rank.iloc[0]['username'], delta=f"{rank.iloc[0]['puntos']} pts")
        
        if len(rank) >= 2:
            col2.metric(label="🥈 2do Lugar", value=rank.iloc[1]['username'], delta=f"{rank.iloc[1]['puntos']} pts")
        
        if len(rank) >= 3:
            col3.metric(label="🥉 3er Lugar", value=rank.iloc[2]['username'], delta=f"{rank.iloc[2]['puntos']} pts")
        
        st.divider() # Línea estética para separar el Top 3 de la tabla
        # -----------------------------------------------------

        # --- TU TABLA ANTIGUA (Se mantiene intacta abajo) ---
        st.write("### Clasificación Completa")
        st.dataframe(
            rank[['username', 'puntos', 'country']], 
            use_container_width=True, 
            hide_index=True
        )

    elif menu == "Mis Predicciones":
        user = st.selectbox("Selecciona tu nombre:", df_p['username'].unique())
        uid = df_p[df_p['username'] == user]['user_id'].values[0]
        user_data = full[full['user_id'] == uid]
        
        st.metric("Tu Puntaje Total", user_data['puntos'].sum())
        st.table(user_data[['match', 'predicted_home', 'predicted_away', 'real_home', 'real_away', 'puntos']])

else:
    st.warning("No se detectaron datos. Revisa la consola o el archivo 'secretos.json'.")
        st.table(user_data[['match', 'predicted_home', 'predicted_away', 'real_home', 'real_away', 'puntos']])

else:
    st.warning("No se detectaron datos. Revisa la consola o el archivo 'secretos.json'.")
