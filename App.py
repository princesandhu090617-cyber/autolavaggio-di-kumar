import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time as dt_time

# ---------------- CONFIGURAZIONE STREAMLIT ----------------
st.set_page_config(page_title="Gestione Autolavaggio", layout="wide")

# ---------------- GOOGLE SHEETS ----------------
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
    "Toyota","Volkswagen","Volvo","Altro"
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
        df = pd.DataFrame(columns=[
            "Data","Ora","Marca","Tipo","Orario Consegna","Prezzo","Metodo"
        ])
    else:
        df = pd.DataFrame(data)
        df["Prezzo"] = (
            df["Prezzo"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(r"[^0-9.]", "", regex=True)
            .astype(float)
        )
        df["Metodo"] = df["Metodo"].fillna("")

    return df, sheet

df, sheet = load_data()

# ---------------- LAYOUT ----------------
col_form, col_lista = st.columns([1, 2])

# ===================== NUOVO LAVAGGIO =====================
with col_form:
    st.header("🚿 Nuovo Lavaggio")

    with st.form("nuovo_lavaggio"):
        marca = st.selectbox("Marca auto", MARCHE_AUTO)
        tipo = st.selectbox("Tipo lavaggio", TIPI_LAVAGGIO)
        ora_consegna = st.time_input("Orario consegna", value=dt_time(10, 0))
        prezzo = st.number_input("Prezzo (€)", min_value=0.0, step=1.0)

        ok = st.form_submit_button("✅ Registra")

        if ok:
            sheet.append_row([
                datetime.now().strftime("%d/%m/%Y"),
                datetime.now().strftime("%H:%M"),
                marca,
                tipo,
                ora_consegna.strftime("%H:%M"),
                prezzo,
                ""
            ])
            st.success("Lavaggio registrato")
            st.cache_resource.clear()
            st.rerun()

# ===================== AUTO DI OGGI =====================
with col_lista:
    st.header("📋 Auto inserite oggi")

    oggi = datetime.now().strftime("%d/%m/%Y")
    df_oggi = df[df["Data"] == oggi]

    if df_oggi.empty:
        st.info("Nessun lavaggio oggi")
    else:
        df_edit = df_oggi.copy()
        df_edit["Metodo"] = df_edit["Metodo"].replace("", METODI_PAGAMENTO[0])

        edited = st.data_editor(
            df_edit[["Marca","Tipo","Prezzo","Metodo"]],
            num_rows="fixed",
            use_container_width=True
        )

        for i, row in edited.iterrows():
            orig = df_oggi.iloc[i]
            if row["Prezzo"] != orig["Prezzo"] or row["Metodo"] != orig["Metodo"]:
                celle = sheet.findall(orig["Ora"])
                for c in celle:
                    r = c.row
                    if (
                        sheet.cell(r,3).value == orig["Marca"]
                        and sheet.cell(r,4).value == orig["Tipo"]
                    ):
                        sheet.update_cell(r, 6, row["Prezzo"])
                        sheet.update_cell(r, 7, row["Metodo"])
                        st.cache_resource.clear()
                        st.rerun()
                        break

# ===================== MENU LATERALE =====================
st.sidebar.title("Menu")
menu = st.sidebar.selectbox(
    "Sezione",
    ["Registro e Calendario", "Chiusura Giornaliera"]
)

# ===================== REGISTRO =====================
if menu == "Registro e Calendario":
    st.header("📅 Registro lavaggi")
    data_sel = st.date_input("Data", value=date.today())
    data_str = data_sel.strftime("%d/%m/%Y")
    df_giorno = df[df["Data"] == data_str]

    if df_giorno.empty:
        st.info("Nessun lavaggio")
    else:
        st.dataframe(df_giorno, use_container_width=True)

# ===================== CHIUSURA =====================
else:
    st.header("📊 Chiusura giornaliera")
    df_oggi = df[df["Data"] == oggi]

    if df_oggi.empty:
        st.warning("Nessun lavaggio oggi")
    else:
        st.metric("Auto lavate", len(df_oggi))
        st.metric("Totale incasso", f"{df_oggi['Prezzo'].sum():.2f} €")

        st.subheader("💳 Incasso per metodo")
        incasso = (
            df_oggi.groupby("Metodo")["Prezzo"]
            .sum()
            .reindex(METODI_PAGAMENTO, fill_value=0)
        )
        st.table(incasso.to_frame("Totale €"))
