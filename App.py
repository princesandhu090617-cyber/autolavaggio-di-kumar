import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time as dt_time

# ---------------- CONFIGURAZIONE STREAMLIT ----------------
st.set_page_config(page_title="Gestione Autolavaggio", layout="wide")

# Variabile per simulare il rerun
if "rerun_flag" not in st.session_state:
    st.session_state.rerun_flag = False

# ---------------- CONFIGURAZIONE GOOGLE SHEETS ----------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ilp2TuerFsgcbt0qLyMRq7rrmqW5OQQisTj9l4n7-Vw/edit"
TAB_NAME = "Lavaggi"

# ---------------- DATI STATICI ----------------
MARCHE_AUTO = [
    "Abarth","Acura","Alfa Romeo","Aston Martin","Audi","Bentley","BMW","Bugatti",
    "Cadillac","Chevrolet","Chrysler","Citroën","Cupra","Dacia","Daewoo","Daihatsu",
    "Dodge","DS","Ferrari","Fiat","Ford","Genesis","GMC","Honda","Hummer","Hyundai",
    "Infiniti","Isuzu","Jaguar","Jeep","Kia","Koenigsegg","Lamborghini","Lancia",
    "Land Rover","Lexus","Lotus","Maserati","Maybach","Mazda","McLaren","Mercedes-Benz",
    "Mini","Mitsubishi","Nissan","Opel","Pagani","Peugeot","Porsche","Ram","Renault",
    "Rolls-Royce","Saab","Seat","Skoda","Smart","SsangYong","Subaru","Suzuki","Tesla",
    "Toyota","Volkswagen","Volvo","BYD","Chery","Geely","Great Wall","MG","Nio",
    "Polestar","Xpeng","Altro"
]

TIPI_LAVAGGIO = ["Solo fuori", "Solo dentro", "Dentro e fuori", "Igienizzazione sedili"]
OPZIONI_PREZZO = ["5 €", "8 €", "10 €", "15 €", "17 €", "18 €", "20 €", "25 €", "30 €", "40 €", "80 €", "90 €", "Altro"]
METODI_PAGAMENTO = ["Contanti", "Satispay", "Carta di Credito"]

# ---------------- FUNZIONI ----------------
def get_google_sheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    # Usa st.secrets per le credenziali
    creds_info = st.secrets["GOOGLE_CREDENTIALS"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@st.cache_resource(ttl=5)
def load_data():
    client = get_google_sheet_client()
    sheet = client.open_by_url(SPREADSHEET_URL).worksheet(TAB_NAME)
    data = sheet.get_all_records()

    if not data:
        df = pd.DataFrame(columns=["Data", "Ora", "Marca", "Tipo", "Orario Consegna", "Prezzo", "Metodo"])
    else:
        df = pd.DataFrame(data)
        if "Prezzo" in df.columns:
            df["Prezzo"] = df["Prezzo"].astype(str).str.replace(r"[^0-9.,]", "", regex=True)
            df["Prezzo"] = df["Prezzo"].str.replace(",", ".").astype(float)
        if "Metodo" not in df.columns:
            df["Metodo"] = ""

    return df, sheet

df, sheet = load_data()

# ---------------- LAYOUT ----------------
col_form, col_lista = st.columns([1, 2])

# ===================== FORM NUOVO LAVAGGIO =====================
with col_form:
    st.header("🚿 Nuovo Lavaggio")
    with st.form("form_lavaggio"):
        marca = st.selectbox("Marca Auto", options=MARCHE_AUTO)
        tipo = st.selectbox("Tipo di Lavaggio", TIPI_LAVAGGIO)
        
        # Orario consegna
        ora_consegna = st.time_input("Orario previsto consegna", value=dt_time(10,0))
        orario_min = dt_time(7,30)
        orario_max = dt_time(20,0)
        submit_enabled = orario_min <= ora_consegna <= orario_max
        if not submit_enabled:
            st.warning(f"L'orario deve essere compreso tra {orario_min.strftime('%H:%M')} e {orario_max.strftime('%H:%M')}")
        
        # Prezzo
        prezzo_sel = st.selectbox("Prezzo (€)", OPZIONI_PREZZO)
        prezzo_finale = st.number_input("Inserisci importo (€)", min_value=0.0, step=1.0) if prezzo_sel=="Altro" else float(prezzo_sel.replace(" €",""))
        
        submit = st.form_submit_button("✅ REGISTRA LAVAGGIO", disabled=not submit_enabled)
        
        if submit:
            row = [
                datetime.now().strftime("%d/%m/%Y"),
                datetime.now().strftime("%H:%M"),
                marca,
                tipo,
                ora_consegna.strftime("%H:%M"),
                prezzo_finale,
                ""  # Metodo pagamento vuoto inizialmente
            ]
            sheet.append_row(row)
            st.success("Lavaggio registrato!")
            st.cache_resource.clear()
            st.session_state.rerun_flag = not st.session_state.rerun_flag

# ===================== LISTA AUTO INSERITE OGGI (aggiornamento live) =====================
with col_lista:
    st.header("📋 Auto Inserite Oggi")
    oggi = datetime.now().strftime("%d/%m/%Y")
    df_oggi = df[df["Data"]==oggi] if not df.empty else pd.DataFrame()

    if df_oggi.empty:
        st.info("Nessuna auto inserita oggi.")
    else:
        df_oggi_edit = df_oggi.copy()
        df_oggi_edit["Metodo"] = df_oggi_edit["Metodo"].fillna(METODI_PAGAMENTO[0])
        df_oggi_edit["Prezzo"] = df_oggi_edit["Prezzo"].fillna(0.0)
        
        edited_df = st.experimental_data_editor(df_oggi_edit[["Marca","Tipo","Prezzo","Metodo"]], num_rows="dynamic")
        
        for idx, row in edited_df.iterrows():
            originale = df_oggi.iloc[idx]
            aggiorna = False
            if row["Prezzo"] != originale["Prezzo"] or row["Metodo"] != originale["Metodo"]:
                aggiorna = True
            if aggiorna:
                cell_list = sheet.findall(originale["Ora"])
                for cell in cell_list:
                    riga_google = cell.row
                    if sheet.cell(riga_google,3).value == originale['Marca'] and sheet.cell(riga_google,4).value == originale['Tipo']:
                        sheet.update_cell(riga_google,6,row["Prezzo"])
                        sheet.update_cell(riga_google,7,row["Metodo"])
                        st.cache_resource.clear()
                        st.session_state.rerun_flag = not st.session_state.rerun_flag
                        break

# ===================== REGISTRO E CHIUSURA GIORNALIERA =====================
st.sidebar.title("Menu Autolavaggio")
menu = st.sidebar.selectbox("Sezione", ["Registro e Calendario", "Chiusura Giornaliera"])

if menu == "Registro e Calendario":
    st.header("📅 Registro Lavaggi")
    data_selezionata = st.date_input("Seleziona una data", value=date.today())
    data_str = data_selezionata.strftime("%d/%m/%Y")
    df_giorno = df[df["Data"]==data_str] if not df.empty else pd.DataFrame()
    if df_giorno.empty:
        st.info("Nessun lavaggio registrato in questa data.")
    else:
        st.dataframe(df_giorno, use_container_width=True)

elif menu == "Chiusura Giornaliera":
    st.header("📊 Chiusura del Giorno")
    df_oggi_chiusura = df[df["Data"]==oggi] if not df.empty else pd.DataFrame()
    if df_oggi_chiusura.empty:
        st.warning("Nessun lavaggio registrato oggi.")
    else:
        col1, col2 = st.columns(2)
        col1.metric("Auto Lavate", len(df_oggi_chiusura))
        col2.metric("Totale Incassato", f"{df_oggi_chiusura['Prezzo'].sum():.2f} €")
        
        st.subheader("💳 Incasso per metodo di pagamento")
        df_incasso_metodo = df_oggi_chiusura.groupby("Metodo")["Prezzo"].sum().reindex(METODI_PAGAMENTO, fill_value=0)
        st.table(df_incasso_metodo.rename("Totale (€)").to_frame())
