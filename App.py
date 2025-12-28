import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time as dt_time

# ---------------- CONFIGURAZIONE STREAMLIT ----------------
st.set_page_config(page_title="Gestione Autolavaggio", layout="wide")

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
    """
    Usa le credenziali direttamente da st.secrets
    """
    creds_dict = st.secrets["GOOGLE_CREDENTIALS"]  # già dict
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
        df = pd.DataFrame(columns=["Data", "Ora", "Marca", "Tipo", "Orario Consegna", "Prezzo", "Metodo"])
    else:
        df = pd.DataFrame(data)
        if "Prezzo" in df.columns:
            df["Prezzo"] = df["Prezzo"].astype(str).str.replace(r"[^0-9.,]", "", regex=True)
            df["Prezzo"] = df["Prezzo"].str.replace(",", ".").astype(float)
    return df, sheet

# ---------------- CARICAMENTO DATI ----------------
if "df" not in st.session_state:
    df, sheet = load_data()
    st.session_state.df = df
    st.session_state.sheet = sheet
else:
    df = st.session_state.df
    sheet = st.session_state.sheet

# ---------------- LAYOUT ----------------
col_form, col_lista = st.columns([1, 2])

# ===================== FORM NUOVO LAVAGGIO =====================
with col_form:
    st.header("🚿 Nuovo Lavaggio")
    with st.form("form_lavaggio"):
        marca = st.selectbox("Marca Auto", options=MARCHE_AUTO)
        tipo = st.selectbox("Tipo di Lavaggio", TIPI_LAVAGGIO)
        ora_consegna = st.time_input("Orario previsto consegna", value=dt_time(10,0))
        
        prezzo_sel = st.selectbox("Prezzo (€)", OPZIONI_PREZZO)
        if prezzo_sel == "Altro":
            prezzo_finale = st.number_input("Inserisci importo (€)", min_value=0.0, step=1.0)
        else:
            prezzo_finale = float(prezzo_sel.replace(" €",""))
        
        submit = st.form_submit_button("✅ REGISTRA LAVAGGIO")
        if submit:
            nuova_riga = [
                datetime.now().strftime("%d/%m/%Y"),
                datetime.now().strftime("%H:%M"),
                marca,
                tipo,
                ora_consegna.strftime("%H:%M"),
                prezzo_finale,
                ""  # Metodo pagamento vuoto inizialmente
            ]
            sheet.append_row(nuova_riga)
            st.session_state.df = pd.concat([st.session_state.df,
                                             pd.DataFrame([dict(zip(st.session_state.df.columns, nuova_riga))])],
                                            ignore_index=True)
            st.success("Lavaggio registrato!")

# ===================== LISTA AUTO INSERITE OGGI =====================
with col_lista:
    st.header("📋 Auto Inserite Oggi")
    oggi = datetime.now().strftime("%d/%m/%Y")
    df_oggi = st.session_state.df[st.session_state.df["Data"]==oggi]
    if df_oggi.empty:
        st.info("Nessuna auto inserita oggi.")
    else:
        for idx, row in df_oggi.iterrows():
            cols = st.columns([2,2,1.5,1.5,1])
            with cols[0]:
                st.markdown(f"**{row['Marca']}**")
            with cols[1]:
                st.markdown(f"**{row['Tipo']}**")
            with cols[2]:
                key_prezzo = f"prezzo_{idx}"
                if key_prezzo not in st.session_state:
                    st.session_state[key_prezzo] = row['Prezzo']
                
                def aggiorna_prezzo(idx=idx, key_prezzo=key_prezzo):
                    val = st.session_state[key_prezzo]
                    cell_list = sheet.findall(row['Ora'])
                    for cell in cell_list:
                        riga_google = cell.row
                        if sheet.cell(riga_google,3).value==row['Marca'] and sheet.cell(riga_google,4).value==row['Tipo']:
                            sheet.update_cell(riga_google,6,val)
                            st.session_state.df.loc[(st.session_state.df["Marca"]==row['Marca']) &
                                                    (st.session_state.df["Tipo"]==row['Tipo']) &
                                                    (st.session_state.df["Ora"]==row['Ora']), 'Prezzo'] = val
                            break

                st.number_input("Prezzo (€)", min_value=0.0, value=st.session_state[key_prezzo],
                                key=key_prezzo, step=1.0, on_change=aggiorna_prezzo)

            # Metodo pagamento
            with cols[3]:
                key_metodo = f"metodo_{idx}"
                if key_metodo not in st.session_state:
                    st.session_state[key_metodo] = row['Metodo'] if row['Metodo'] in METODI_PAGAMENTO else METODI_PAGAMENTO[0]

                def aggiorna_metodo(idx=idx, key_metodo=key_metodo):
                    val = st.session_state[key_metodo]
                    cell_list = sheet.findall(row['Ora'])
                    for cell in cell_list:
                        riga_google = cell.row
                        if sheet.cell(riga_google,3).value==row['Marca'] and sheet.cell(riga_google,4).value==row['Tipo']:
                            sheet.update_cell(riga_google,7,val)
                            st.session_state.df.loc[(st.session_state.df["Marca"]==row['Marca']) &
                                                    (st.session_state.df["Tipo"]==row['Tipo']) &
                                                    (st.session_state.df["Ora"]==row['Ora']), 'Metodo'] = val
                            break

                st.selectbox("Metodo", METODI_PAGAMENTO, index=METODI_PAGAMENTO.index(st.session_state[key_metodo]),
                             key=key_metodo, on_change=aggiorna_metodo)

# ===================== REGISTRO E CHIUSURA GIORNALIERA =====================
st.sidebar.title("Menu Autolavaggio")
menu = st.sidebar.selectbox("Sezione", ["Registro e Calendario", "Chiusura Giornaliera"])

if menu=="Registro e Calendario":
    st.header("📅 Registro Lavaggi")
    data_selezionata = st.date_input("Seleziona una data", value=date.today())
    df_giorno = st.session_state.df[st.session_state.df["Data"]==data_selezionata.strftime("%d/%m/%Y")]
    if df_giorno.empty:
        st.info("Nessun lavaggio registrato in questa data.")
    else:
        st.dataframe(df_giorno, width='stretch')

elif menu=="Chiusura Giornaliera":
    st.header("📊 Chiusura del Giorno")
    df_oggi_chiusura = st.session_state.df[st.session_state.df["Data"]==datetime.now().strftime("%d/%m/%Y")]
    if df_oggi_chiusura.empty:
        st.warning("Nessun lavaggio registrato oggi.")
    else:
        st.write(f"Auto lavate oggi: {len(df_oggi_chiusura)}")
        st.write(f"Totale incassato: {df_oggi_chiusura['Prezzo'].sum():.2f} €")
        st.subheader("💳 Incasso per metodo di pagamento")
        df_incasso_metodo = df_oggi_chiusura.groupby("Metodo")["Prezzo"].sum().reindex(METODI_PAGAMENTO, fill_value=0)
        st.table(df_incasso_metodo.rename("Totale (€)").to_frame())
