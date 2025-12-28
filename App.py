import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time as dt_time

# ---------------- CONFIG STREAMLIT ----------------
st.set_page_config(page_title="Gestione Autolavaggio", layout="wide")

# ---------------- GOOGLE SHEETS ----------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ilp2TuerFsgcbt0qLyMRq7rrmqW5OQQisTj9l4n7-Vw/edit"
TAB_NAME = "Lavaggi"

# ---------------- MARCHE AUTO ----------------
MARCHE_AUTO = [
    "Abarth","Acura","Alfa Romeo","Aston Martin","Audi","Bentley","BMW","Bugatti",
    "Cadillac","Chevrolet","Chrysler","Citroën","Cupra","Dacia","Daewoo","Daihatsu",
    "Dodge","DS","Ferrari","Fiat","Ford","Genesis","GMC","Honda","Hummer","Hyundai",
    "Infiniti","Isuzu","Jaguar","Jeep","Kia","Koenigsegg","Lamborghini","Lancia",
    "Land Rover","Lexus","Lotus","Maserati","Maybach","Mazda","McLaren",
    "Mercedes-Benz","Mini","Mitsubishi","Nissan","Opel","Pagani","Peugeot",
    "Porsche","Ram","Renault","Rolls-Royce","Saab","Seat","Skoda","Smart",
    "SsangYong","Subaru","Suzuki","Tesla","Toyota","Volkswagen","Volvo",
    "BYD","Chery","Geely","Great Wall","MG","Nio","Polestar","Xpeng","Altro"
]

TIPI_LAVAGGIO = ["Solo fuori", "Solo dentro", "Dentro e fuori", "Igienizzazione sedili"]
METODI_PAGAMENTO = ["Contanti", "Satispay", "Carta di Credito"]

# ---------------- FUNZIONI ----------------
def get_google_sheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["GOOGLE_CREDENTIALS"],
        scopes=scopes
    )
    return gspread.authorize(creds)

@st.cache_resource(ttl=5)
def load_data():
    client = get_google_sheet_client()
    sheet = client.open_by_url(SPREADSHEET_URL).worksheet(TAB_NAME)
    data = sheet.get_all_records()

    if not data:
        df = pd.DataFrame(columns=["Data","Ora","Marca","Tipo","Consegna","Prezzo","Metodo"])
    else:
        df = pd.DataFrame(data)
        df["Prezzo"] = (
            df["Prezzo"].astype(str)
            .str.replace(",", ".")
            .str.replace(r"[^0-9.]", "", regex=True)
            .astype(float)
        )
        df["Metodo"] = df["Metodo"].fillna("Contanti")
    return df, sheet

df, sheet = load_data()
oggi = datetime.now().strftime("%d/%m/%Y")

# ---------------- LAYOUT NUOVO LAVAGGIO + AUTO DI OGGI ----------------
col_form, col_lista = st.columns([1, 2])

# ---------------- NUOVO LAVAGGIO ----------------
with col_form:
    st.header("🚿 Nuovo Lavaggio")
    with st.form("lavaggio"):
        marca = st.selectbox("Marca auto", MARCHE_AUTO)
        tipo = st.selectbox("Tipo lavaggio", TIPI_LAVAGGIO)
        consegna = st.time_input("Orario consegna", value=dt_time(10,0))
        prezzo = st.number_input("Prezzo (€)", min_value=0.0, step=1.0)
        metodo = st.selectbox("Metodo pagamento", METODI_PAGAMENTO)

        if st.form_submit_button("✅ Registra"):
            sheet.append_row([
                oggi,
                datetime.now().strftime("%H:%M"),
                marca,
                tipo,
                consegna.strftime("%H:%M"),
                prezzo,
                metodo
            ])
            st.success("Lavaggio registrato")
            st.cache_resource.clear()
            st.experimental_rerun()

# ---------------- AUTO DI OGGI CON MODIFICA E CANCELLAZIONE ----------------
with col_lista:
    st.header("📋 Auto inserite oggi")
    df_oggi = df[df["Data"] == oggi]

    if df_oggi.empty:
        st.info("Nessun lavaggio oggi")
    else:
        for i, r in df_oggi.iterrows():
            cols = st.columns([2, 1, 1, 0.5])
            with cols[0]:
                st.markdown(f"**{r['Marca']}** — {r['Tipo']}")

            # Prezzo modificabile
            with cols[1]:
                key_prezzo = f"prezzo_{i}"
                if key_prezzo not in st.session_state:
                    st.session_state[key_prezzo] = r["Prezzo"]
                prezzo_nuovo = st.number_input(
                    "Prezzo (€)",
                    min_value=0.0,
                    value=float(st.session_state[key_prezzo]),
                    step=1.0,
                    key=key_prezzo
                )
                if prezzo_nuovo != r["Prezzo"]:
                    cell_list = sheet.findall(r["Ora"])
                    for cell in cell_list:
                        riga = cell.row
                        if sheet.cell(riga,3).value == r["Marca"] and sheet.cell(riga,4).value == r["Tipo"]:
                            sheet.update_cell(riga,6,prezzo_nuovo)
                            st.session_state[key_prezzo] = prezzo_nuovo
                            st.cache_resource.clear()
                            st.experimental_rerun()
                            break

            # Metodo pagamento modificabile
            with cols[2]:
                key_metodo = f"metodo_{i}"
                if key_metodo not in st.session_state:
                    st.session_state[key_metodo] = r["Metodo"]
                metodo_nuovo = st.selectbox(
                    "Metodo",
                    METODI_PAGAMENTO,
                    index=METODI_PAGAMENTO.index(st.session_state[key_metodo]),
                    key=key_metodo
                )
                if metodo_nuovo != r["Metodo"]:
                    cell_list = sheet.findall(r["Ora"])
                    for cell in cell_list:
                        riga = cell.row
                        if sheet.cell(riga,3).value == r["Marca"] and sheet.cell(riga,4).value == r["Tipo"]:
                            sheet.update_cell(riga,7,metodo_nuovo)
                            st.session_state[key_metodo] = metodo_nuovo
                            st.cache_resource.clear()
                            st.experimental_rerun()
                            break

            # Pulsante per cancellare la riga
            with cols[3]:
                if st.button("❌", key=f"cancella_{i}"):
                    cell_list = sheet.findall(r["Ora"])
                    for cell in cell_list:
                        riga = cell.row
                        if sheet.cell(riga,3).value == r["Marca"] and sheet.cell(riga,4).value == r["Tipo"]:
                            sheet.delete_row(riga)
                            st.success(f"{r['Marca']} cancellata")
                            st.cache_resource.clear()
                            st.experimental_rerun()
                            break

# ---------------- SIDEBAR MENU ----------------
st.sidebar.title("Menu Autolavaggio")
menu = st.sidebar.selectbox("Sezione", ["Registro", "Chiusura Giornaliera"])

# ---------------- REGISTRO ----------------
if menu == "Registro":
    st.header("📅 Registro Lavaggi")
    data_sel = st.date_input("Seleziona data", value=date.today())
    data_str = data_sel.strftime("%d/%m/%Y")
    df_g = df[df["Data"] == data_str]

    if df_g.empty:
        st.info("Nessun lavaggio")
    else:
        st.dataframe(df_g, use_container_width=True)

# ---------------- CHIUSURA GIORNALIERA ----------------
elif menu == "Chiusura Giornaliera":
    st.header("📊 Chiusura del Giorno")
    df_c = df[df["Data"] == oggi]

    if df_c.empty:
        st.warning("Nessun lavaggio oggi")
    else:
        st.metric("Auto Lavate", len(df_c))
        st.metric("Totale Incasso", f"{df_c['Prezzo'].sum():.2f} €")

        st.subheader("💳 Incasso per metodo")
        incasso = df_c.groupby("Metodo")["Prezzo"].sum().reindex(METODI_PAGAMENTO, fill_value=0)
        st.table(incasso.to_frame("Totale €"))
