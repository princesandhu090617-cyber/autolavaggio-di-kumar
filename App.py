import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# ---------------- CONFIGURAZIONE STREAMLIT ----------------
st.set_page_config(page_title="Gestione Autolavaggio", layout="wide")

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
    creds_dict = st.secrets["GOOGLE_CREDENTIALS"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@st.cache_resource(ttl=5)
def load_data():
    client = get_google_sheet_client()
    sheet = client.open_by_url(SPREADSHEET_URL).worksheet(TAB_NAME)
    data = sheet.get_all_records()
    if not data:
        df = pd.DataFrame(columns=["Data", "Ora", "Marca", "Tipo", "Prezzo", "Metodo"])
    else:
        df = pd.DataFrame(data)
        df.columns = [col.strip() for col in df.columns]
        # Gestione valori vuoti
        if "Prezzo" in df.columns:
            df["Prezzo"] = df["Prezzo"].replace("", "0")
            df["Prezzo"] = df["Prezzo"].astype(str).str.replace(r"[^0-9.,]", "", regex=True)
            df["Prezzo"] = df["Prezzo"].str.replace(",", ".").astype(float)
        if "Metodo" in df.columns:
            df["Metodo"] = df["Metodo"].replace("", METODI_PAGAMENTO[0])
    return df, sheet

df, sheet = load_data()

# ---------------- FORM NUOVO LAVAGGIO ----------------
st.header("🚿 Nuovo Lavaggio")
with st.form("form_lavaggio"):
    marca = st.selectbox("Marca Auto", MARCHE_AUTO)
    tipo = st.selectbox("Tipo di Lavaggio", TIPI_LAVAGGIO)
    prezzo_sel = st.selectbox("Prezzo (€)", OPZIONI_PREZZO)
    prezzo_finale = st.number_input("Inserisci importo (€)", min_value=0.0, step=1.0) if prezzo_sel=="Altro" else float(prezzo_sel.replace(" €",""))
    metodo = st.selectbox("Metodo Pagamento", METODI_PAGAMENTO)

    submit = st.form_submit_button("✅ REGISTRA LAVAGGIO")
    if submit:
        row = [
            datetime.now().strftime("%d/%m/%Y"),
            datetime.now().strftime("%H:%M"),
            marca,
            tipo,
            prezzo_finale,
            metodo
        ]
        sheet.append_row(row)
        st.success("Lavaggio registrato!")
        df, sheet = load_data()
        st.session_state.rerun_flag = not st.session_state.rerun_flag

# ---------------- AUTO INSERITE OGGI ----------------
st.header("📋 Auto Inserite Oggi")
oggi = datetime.now().strftime("%d/%m/%Y")
df_oggi = df[df["Data"]==oggi] if not df.empty else pd.DataFrame()

if df_oggi.empty:
    st.info("Nessuna auto inserita oggi.")
else:
    df_display = df_oggi[["Marca","Tipo","Prezzo","Metodo"]].copy()
    df_display.index = range(1, len(df_display)+1)
    st.dataframe(df_display, use_container_width=True)

# ---------------- REGISTRO E CHIUSURA GIORNALIERA ----------------
st.sidebar.title("Menu Autolavaggio")
menu = st.sidebar.selectbox("Sezione", ["Registro e Calendario", "Chiusura Giornaliera"])

if menu=="Registro e Calendario":
    st.header("📅 Registro Lavaggi")
    data_selezionata = st.date_input("Seleziona una data", value=date.today())
    data_str = data_selezionata.strftime("%d/%m/%Y")
    df_giorno = df[df["Data"]==data_str] if not df.empty else pd.DataFrame()
    if df_giorno.empty:
        st.info("Nessun lavaggio registrato in questa data.")
    else:
        st.dataframe(df_giorno[["Marca","Tipo","Prezzo","Metodo"]], use_container_width=True)

elif menu=="Chiusura Giornaliera":
    st.header("📊 Chiusura del Giorno")
    df_oggi_chiusura = df[df["Data"]==datetime.now().strftime("%d/%m/%Y")] if not df.empty else pd.DataFrame()
    if df_oggi_chiusura.empty:
        st.warning("Nessun lavaggio registrato oggi.")
    else:
        st.metric("Auto Lavate", len(df_oggi_chiusura))
        st.metric("Totale Incassato", f"{df_oggi_chiusura['Prezzo'].sum():.2f} €")
