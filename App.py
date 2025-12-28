import streamlit as st
import pandas as pd
import gspread
import io
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time as dt_time
from fpdf import FPDF

# ---------------- CONFIG STREAMLIT ----------------
st.set_page_config(page_title="Gestione Autolavaggio", layout="wide")

# ---------------- STILE MOBILE ----------------
st.markdown("""
<style>
button { width: 100%; height: 3em; font-size: 16px; }
div[data-testid="column"] { padding: 0.3rem; }
</style>
""", unsafe_allow_html=True)

# ---------------- GOOGLE SHEETS ----------------
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1ilp2TuerFsgcbt0qLyMRq7rrmqW5OQQisTj9l4n7-Vw/edit"
TAB_NAME = "Lavaggi"

# ---------------- MARCHE AUTO (COMPLETE) ----------------
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

# ---------------- LOGHI AUTO (URL SICURI) ----------------
LOGHI_AUTO = {
    "Abarth": "https://upload.wikimedia.org/wikipedia/commons/7/7f/Abarth-logo.svg",
    "Alfa Romeo": "https://upload.wikimedia.org/wikipedia/commons/2/2b/Alfa_Romeo_Logo.svg",
    "Audi": "https://upload.wikimedia.org/wikipedia/commons/6/6f/Audi_logo.svg",
    "BMW": "https://upload.wikimedia.org/wikipedia/commons/4/44/BMW.svg",
    "Ferrari": "https://upload.wikimedia.org/wikipedia/en/d/d1/Ferrari-Logo.svg",
    "Fiat": "https://upload.wikimedia.org/wikipedia/commons/1/12/Fiat_logo.svg",
    "Ford": "https://upload.wikimedia.org/wikipedia/commons/3/3e/Ford_logo_flat.svg",
    "Lamborghini": "https://upload.wikimedia.org/wikipedia/en/d/df/Lamborghini_Logo.svg",
    "Mercedes-Benz": "https://upload.wikimedia.org/wikipedia/commons/9/90/Mercedes-Logo.svg",
    "Mini": "https://upload.wikimedia.org/wikipedia/commons/1/14/MINI_logo.svg",
    "Peugeot": "https://upload.wikimedia.org/wikipedia/commons/5/5e/Peugeot_Logo.svg",
    "Porsche": "https://upload.wikimedia.org/wikipedia/en/4/4d/Porsche_logo.svg",
    "Renault": "https://upload.wikimedia.org/wikipedia/commons/9/9d/Renault_Logo.svg",
    "Tesla": "https://upload.wikimedia.org/wikipedia/commons/b/bd/Tesla_Motors.svg",
    "Toyota": "https://upload.wikimedia.org/wikipedia/commons/9/9d/Toyota_logo.svg",
    "Volkswagen": "https://upload.wikimedia.org/wikipedia/commons/6/6d/Volkswagen_logo_2019.svg"
}

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

# ---------------- MENU ----------------
st.sidebar.title("Menu")
menu = st.sidebar.selectbox(
    "Sezione",
    [
        "Nuovo Lavaggio",
        "Auto di Oggi",
        "Registro",
        "Chiusura Giornaliera",
        "Statistiche Settimanali"
    ]
)

# ===================== NUOVO LAVAGGIO =====================
if menu == "Nuovo Lavaggio":
    st.header("🚿 Nuovo Lavaggio")

    with st.form("lavaggio"):
        marca = st.selectbox("Marca auto", MARCHE_AUTO)
        tipo = st.selectbox("Tipo lavaggio", TIPI_LAVAGGIO)
        consegna = st.time_input("Orario consegna", value=dt_time(10,0))
        prezzo = st.number_input("Prezzo (€)", min_value=0.0, step=1.0)

        if st.form_submit_button("✅ Registra"):
            sheet.append_row([
                oggi,
                datetime.now().strftime("%H:%M"),
                marca,
                tipo,
                consegna.strftime("%H:%M"),
                prezzo,
                "Contanti"
            ])
            st.success("Lavaggio registrato")
            st.cache_resource.clear()
            st.rerun()

# ===================== AUTO DI OGGI (CON LOGHI) =====================
elif menu == "Auto di Oggi":
    st.header("📋 Auto inserite oggi")

    df_oggi = df[df["Data"] == oggi]

    if df_oggi.empty:
        st.info("Nessun lavaggio oggi")
    else:
        for i, r in df_oggi.iterrows():
            col_logo, col_info = st.columns([1,6])

            with col_logo:
                if r["Marca"] in LOGHI_AUTO:
                    st.image(LOGHI_AUTO[r["Marca"]], width=40)

            with col_info:
                st.markdown(
                    f"**{r['Marca']}** — {r['Tipo']}  \n"
                    f"💰 {r['Prezzo']} € | 💳 {r['Metodo']}"
                )

# ===================== REGISTRO =====================
elif menu == "Registro":
    st.header("📅 Registro Lavaggi")
    data_sel = st.date_input("Seleziona data", value=date.today())
    data_str = data_sel.strftime("%d/%m/%Y")
    df_g = df[df["Data"] == data_str]

    if df_g.empty:
        st.info("Nessun lavaggio")
    else:
        st.dataframe(df_g, use_container_width=True)

# ===================== CHIUSURA GIORNALIERA =====================
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

        st.subheader("📊 Grafici")
        st.bar_chart(incasso, use_container_width=True)
        st.line_chart(df_c.groupby("Ora")["Prezzo"].sum(), use_container_width=True)

        # EXPORT
        buffer = io.BytesIO()
        df_c.to_excel(buffer, index=False)

        st.download_button(
            "⬇️ Scarica Excel",
            buffer.getvalue(),
            file_name=f"chiusura_{oggi}.xlsx"
        )

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0,10,f"Chiusura del {oggi}",ln=True)
        pdf.cell(0,10,f"Totale: {df_c['Prezzo'].sum():.2f} €",ln=True)

        st.download_button(
            "⬇️ Scarica PDF",
            pdf.output(dest="S").encode("latin-1"),
            file_name=f"chiusura_{oggi}.pdf"
        )

# ===================== STATISTICHE SETTIMANALI =====================
else:
    st.header("📈 Statistiche Settimanali")

    df["Data_dt"] = pd.to_datetime(df["Data"], format="%d/%m/%Y")
    settimana = df[df["Data_dt"] >= datetime.now() - pd.Timedelta(days=7)]

    st.metric("Auto lavate", len(settimana))
    st.metric("Incasso settimanale", f"{settimana['Prezzo'].sum():.2f} €")

    st.line_chart(settimana.groupby("Data")["Prezzo"].sum(), use_container_width=True)
