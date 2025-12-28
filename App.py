import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time as dt_time

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
    import json
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
        df.columns = [col.strip() for col in df.columns]  # rimuove spazi extra
        if "Prezzo" in df.columns:
            df["Prezzo"] = df["Prezzo"].astype(str).str.replace(r"[^0-9.,]", "", regex=True)
            df["Prezzo"] = df["Prezzo"].str.replace(",", ".").astype(float)
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

        prezzo_sel = st.selectbox("Prezzo (€)", OPZIONI_PREZZO)
        prezzo_finale = st.number_input("Inserisci importo (€)", min_value=0.0, step=1.0) if prezzo_sel=="Altro" else float(prezzo_sel.replace(" €",""))

        submit = st.form_submit_button("✅ REGISTRA LAVAGGIO")
        if submit:
            row = [
                datetime.now().strftime("%d/%m/%Y"),
                datetime.now().strftime("%H:%M"),
                marca,
                tipo,
                prezzo_finale,
                ""  # Metodo pagamento vuoto
            ]
            sheet.append_row(row)
            st.success("Lavaggio registrato!")
            df, sheet = load_data()
            st.session_state.rerun_flag = not st.session_state.rerun_flag

# ===================== LISTA AUTO INSERITE OGGI =====================
with col_lista:
    st.header("📋 Auto Inserite Oggi")
    oggi = datetime.now().strftime("%d/%m/%Y")
    df_oggi = df[df["Data"]==oggi] if not df.empty else pd.DataFrame()

    if df_oggi.empty:
        st.info("Nessuna auto inserita oggi.")
    else:
        for idx, row in df_oggi.iterrows():
            cols = st.columns([2,2,1.5,1.5,1])
            with cols[0]:
                st.markdown(f"**{row['Marca']}**")
            with cols[1]:
                st.markdown(f"**{row['Tipo']}**")

            # Prezzo
            key_prezzo_sel = f"prezzo_sel_{idx}"
            key_prezzo_custom = f"prezzo_custom_{idx}"
            if key_prezzo_sel not in st.session_state:
                prezzo_val = str(int(row['Prezzo'])) + " €"
                if prezzo_val in OPZIONI_PREZZO:
                    st.session_state[key_prezzo_sel] = prezzo_val
                else:
                    st.session_state[key_prezzo_sel] = "Altro"
                    st.session_state[key_prezzo_custom] = row['Prezzo']

            def aggiorna_prezzo(idx=idx, key_prezzo_sel=key_prezzo_sel, key_prezzo_custom=key_prezzo_custom):
                prezzo_val = st.session_state[key_prezzo_custom] if st.session_state[key_prezzo_sel]=="Altro" else float(st.session_state[key_prezzo_sel].replace(" €",""))
                cell_list = sheet.findall(row['Ora'])
                for cell in cell_list:
                    riga_google = cell.row
                    if sheet.cell(riga_google,3).value==row['Marca'] and sheet.cell(riga_google,4).value==row['Tipo']:
                        sheet.update_cell(riga_google,5,prezzo_val)
                        df.loc[(df["Marca"]==row['Marca']) & (df["Tipo"]==row['Tipo']) & (df["Ora"]==row['Ora']), 'Prezzo'] = prezzo_val
                        st.session_state.rerun_flag = not st.session_state.rerun_flag
                        break

            st.selectbox(f"Prezzo {idx}", OPZIONI_PREZZO,
                         index=OPZIONI_PREZZO.index(st.session_state[key_prezzo_sel]),
                         key=key_prezzo_sel, on_change=aggiorna_prezzo)

            if st.session_state[key_prezzo_sel]=="Altro":
                st.number_input("Importo personalizzato (€)", min_value=0.0, value=st.session_state.get(key_prezzo_custom,0.0),
                                step=1.0, key=key_prezzo_custom, on_change=aggiorna_prezzo)

            # Metodo pagamento
            key_metodo = f"metodo_{idx}"
            if key_metodo not in st.session_state:
                st.session_state[key_metodo] = row['Metodo'] if row['Metodo'] in METODI_PAGAMENTO else METODI_PAGAMENTO[0]

            def aggiorna_metodo(idx=idx, key_metodo=key_metodo):
                metodo_selezionato = st.session_state[key_metodo]
                cell_list = sheet.findall(row['Ora'])
                for cell in cell_list:
                    riga_google = cell.row
                    if sheet.cell(riga_google,3).value==row['Marca'] and sheet.cell(riga_google,4).value==row['Tipo']:
                        sheet.update_cell(riga_google,6,metodo_selezionato)
                        df.loc[(df["Marca"]==row['Marca']) & (df["Tipo"]==row['Tipo']) & (df["Ora"]==row['Ora']), 'Metodo'] = metodo_selezionato
                        st.session_state.rerun_flag = not st.session_state.rerun_flag
                        break

            st.selectbox(f"Metodo {idx}", METODI_PAGAMENTO,
                         index=METODI_PAGAMENTO.index(st.session_state[key_metodo]),
                         key=key_metodo, on_change=aggiorna_metodo)

            # Cancellazione
            with cols[4]:
                cancella = st.button(f"❌ Cancella {idx}")
                if cancella:
                    cell_list = sheet.findall(row['Ora'])
                    for cell in cell_list:
                        riga_google = cell.row
                        if sheet.cell(riga_google,3).value==row['Marca'] and sheet.cell(riga_google,4).value==row['Tipo']:
                            sheet.delete_rows(riga_google)
                            df, sheet = load_data()
                            st.success(f"Cancellato {row['Marca']}")
                            st.session_state.rerun_flag = not st.session_state.rerun_flag
                            break

# ===================== REGISTRO E CALENDARIO =====================
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
        st.dataframe(df_giorno, width='stretch')

elif menu=="Chiusura Giornaliera":
    st.header("📊 Chiusura del Giorno")
    df_oggi_chiusura = df[df["Data"]==datetime.now().strftime("%d/%m/%Y")] if not df.empty else pd.DataFrame()
    if df_oggi_chiusura.empty:
        st.warning("Nessun lavaggio registrato oggi.")
    else:
        st.metric("Auto Lavate", len(df_oggi_chiusura))
        st.metric("Totale Incassato", f"{df_oggi_chiusura['Prezzo'].sum():.2f} €")
