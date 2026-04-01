import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- UI CONFIG ---
st.set_page_config(page_title="Quiniela 2026", layout="wide", page_icon="⚽")

# --- DATABASE CONNECTION ---
@st.cache_data(ttl=600)
def load_data():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Cargar credenciales desde el JSON local
        creds = Credentials.from_service_account_file("secretos.json", scopes=scope)
        client = gspread.authorize(creds)
        
        # Abrir el archivo principal
        # IMPORTANTE: Asegúrate de que el archivo en Drive se llame 'wcd' (minúsculas)
        spreadsheet = client.open("wcd")

        # Carga individual con manejo de errores por pestaña
        try:
            p_data = spreadsheet.worksheet("players").get_all_records()
            df_p = pd.DataFrame(p_data)
            
            m_data = spreadsheet.worksheet("matches").get_all_records()
            df_m = pd.DataFrame(m_data)
            
            pr_data = spreadsheet.worksheet("predictions").get_all_records()
            df_pred = pd.DataFrame(pr_data)
            
            return df_p, df_m, df_pred
            
        except gspread.exceptions.WorksheetNotFound as e:
            st.error(f"❌ Error: No se encontró la pestaña '{e}' dentro del archivo 'wcd'.")
            st.info("Revisa que abajo en Google Sheets las pestañas se llamen: players, matches y predictions.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    except FileNotFoundError:
        st.error("Error: No encontré el archivo 'secretos.json' en la carpeta del proyecto.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def calculate_score(row):
    # Validar que existan datos reales antes de calcular
    if pd.isna(row['real_home']) or row['real_home'] == "" or row['real_home'] == None:
        return 0
        
    # Lógica de puntos: 3 pts exacto, 1 pt tendencia
    # Convertimos a int por si acaso vienen como texto desde el Excel
    r_h, r_a = int(row['real_home']), int(row['real_away'])
    p_h, p_a = int(row['predicted_home']), int(row['predicted_away'])

    if r_h == p_h and r_a == p_a:
        return 3
        
    r_diff = r_h - r_a
    p_diff = p_h - p_a
    
    if (r_diff > 0 and p_diff > 0) or (r_diff < 0 and p_diff < 0) or (r_diff == 0 and p_diff == 0):
        return 1
    return 0

# --- LÓGICA PRINCIPAL ---
df_p, df_m, df_pred = load_data()

# Solo mostramos la interfaz si los datos cargaron correctamente
if not df_p.empty and not df_m.empty and not df_pred.empty:
    
    # 1. Cruzar datos (Merge) y calcular puntos
    full = df_pred.merge(df_m, on='match_code')
    full['puntos'] = full.apply(calculate_score, axis=1)

    # 2. Sidebar de navegación
    st.sidebar.title("⚽ Mundial 2026")
    menu = st.sidebar.radio("Menú", ["Ranking", "Reglas", "Jugador"])

    if menu == "Ranking":
        st.header("📊 Tabla General de Posiciones")
        # Agrupar puntos por usuario
        rank = full.groupby('user_id')['puntos'].sum().reset_index()
        # Traer los nombres de los jugadores
        rank = rank.merge(df_p, on='user_id').sort_values('puntos', ascending=False)
        
        # Mostrar tabla limpia
        st.dataframe(rank[['username', 'puntos', 'country']], use_container_width=True, hide_index=True)

    elif menu == "Reglas":
        st.subheader("📝 ¿Cómo sumar puntos?")
        st.info("""
        - **3 Puntos:** Resultado Exacto (ej. Apostaste 2-1 y quedaron 2-1).
        - **1 Punto:** Acertar Ganador o Empate (ej. Apostaste 1-0 y quedaron 3-0).
        - **0 Puntos:** No acertar la tendencia.
        """)

    elif menu == "Jugador":
        st.header("👤 Detalle por Usuario")
        user = st.selectbox("Selecciona un Jugador", df_p['username'].unique())
        
        # Filtrar datos por el usuario elegido
        uid = df_p[df_p['username'] == user]['user_id'].values[0]
        user_data = full[full['user_id'] == uid]
        
        # Mostrar resumen y tabla detallada
        total_p = user_data['puntos'].sum()
        st.metric(label="Puntos Totales", value=total_p)
        
        st.dataframe(
            user_data[['match', 'predicted_home', 'predicted_away', 'real_home', 'real_away', 'puntos']],
            use_container_width=True,
            hide_index=True
        )

else:
    st.warning("Esperando conexión correcta con Google Sheets...")
    st.info("💡 Consejo: Asegúrate de haber compartido el archivo 'wcd' con el email de tu secretos.json.")