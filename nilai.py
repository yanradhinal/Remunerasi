import streamlit as st
import pandas as pd
from PyPDF2 import PdfMerger
import os
import json
import uuid
import requests
import certifi  # Pastikan certifi sudah diinstall

# === SISTEM LISENSI ONLINE PER USER ===
LICENSE_API = "https://script.google.com/macros/s/AKfycbyQFCTS5BbapcZYj86zRLT-pRm4ydg8bD0oXVf8V-x69Dwx1HbLvxr79mkvHalkX_FK/exec"  # GANTI dengan URL Apps Script kamu!
LICENSE_FILE = ".license"

def get_hardware_id():
    return str(uuid.getnode())

def cek_license_online(license_key):
    hardware_id = get_hardware_id()
    payload = {
        "license_key": license_key,
        "hardware_id": hardware_id
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(
            LICENSE_API,
            json=payload,
            headers=headers,
            timeout=10,
            verify=certifi.where()  # Penting untuk SSL di .exe
        )
        logmsg = f"RESPON LISENSI: {r.status_code} | {repr(r.text)}"
        print(logmsg)
        with open("log_license.txt", "a", encoding="utf-8") as f:
            f.write(logmsg + "\n")

        if r.text.strip() == "OK":
            return True, "Lisensi aktif"
        elif r.text.strip() == "USED":
            return False, "Lisensi sudah digunakan di komputer lain!"
        elif r.text.strip() == "NONAKTIF":
            return False, "Lisensi ini dinonaktifkan admin"
        else:
            return False, f"License key tidak ditemukan ({r.status_code} {r.text})"
    except Exception as e:
        errmsg = f"ERROR LISENSI: {e}"
        print(errmsg)
        with open("log_license.txt", "a", encoding="utf-8") as f:
            f.write(errmsg + "\n")
        return False, f"Gagal koneksi ke server lisensi: {e}"

def save_license_file(license_key):
    data = {
        "license_key": license_key,
        "hardware_id": get_hardware_id()
    }
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f)

def cek_license_file():
    if not os.path.exists(LICENSE_FILE):
        return False
    try:
        with open(LICENSE_FILE, "r") as f:
            data = json.load(f)
        is_ok, _ = cek_license_online(data["license_key"])
        return is_ok
    except:
        return False

if "license_ok" not in st.session_state:
    st.session_state.license_ok = cek_license_file()

if not st.session_state.license_ok:
    st.title("🔑 Aktivasi Lisensi Online")
    input_key = st.text_input("Masukkan License Key Anda")
    if st.button("Aktivasi Lisensi"):
        is_ok, msg = cek_license_online(input_key.strip())
        if is_ok:
            save_license_file(input_key.strip())
            st.session_state.license_ok = True
            st.success("Lisensi aktif & terkunci untuk komputer ini.")
            st.rerun()
        else:
            st.error(msg)
    st.stop()

# === APP UTAMA (lanjutkan dengan kode progress, checklist, dsb di bawah ini) ===

# --- Progress File ---
PROGRESS_FILE = "progress.csv"
CHECKLIST_FILE = "progress_checklist.json"
PDF_FOLDER = "uploads"

st.title("Form Penilaian Remunerasi")
RUBRIK_FILE = "Rubrik_Remun.csv"
if not os.path.exists(RUBRIK_FILE):
    st.warning(f"File '{RUBRIK_FILE}' tidak ditemukan! Pastikan file tersedia di folder aplikasi.")
    st.stop()

rubrik = pd.read_csv(RUBRIK_FILE, encoding='latin1')

# --- Load Progress Nilai ---
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        df = pd.read_csv(PROGRESS_FILE)
        return df
    else:
        return None

def save_progress(df):
    df.to_csv(PROGRESS_FILE, index=False)

def load_checklist():
    if os.path.exists(CHECKLIST_FILE):
        with open(CHECKLIST_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_checklist(checklist_dict):
    with open(CHECKLIST_FILE, "w") as f:
        json.dump(checklist_dict, f)

# --- Siapkan Nilai dan Checklist dari Progress ---
progress_df = load_progress()
if progress_df is not None:
    nilai_progress = progress_df['Nilai'].tolist()
else:
    nilai_progress = [0]*len(rubrik)

checklist_progress = load_checklist()

nilai = []
all_uploaded_files = []
all_variabels = rubrik['Variabel'].unique()
expander_status = {}

st.markdown("### Silakan isi nilai dan upload bukti PDF untuk masing-masing indikator:")

# --- FORM EXPANDER PER VARIABEL + SAVE PROGRESS OTOMATIS ---
for var in all_variabels:
    checked = st.checkbox(
        f"Tandai '{var}' sudah diisi",
        key=f"centang_{var}",
        value=checklist_progress.get(var, False),
        on_change=lambda v=var: save_checklist({**load_checklist(), v: st.session_state[f"centang_{v}"]})
    )
    expander_status[var] = checked
    with st.expander(f"{var} {'✅' if checked else ''}", expanded=False):
        subset = rubrik[rubrik['Variabel'] == var]
        for idx, row in subset.iterrows():
            k = len(nilai)
            # Ambil nilai dari progress kalau ada
            prev_nilai = nilai_progress[k] if k < len(nilai_progress) else 0
            n = st.number_input(
                "Nilai (0-100):",
                min_value=0, max_value=100,
                value=int(prev_nilai),
                key=f"nilai_{var}_{idx}",
                on_change=lambda k=k: save_progress(pd.DataFrame({
                    "Variabel": rubrik['Variabel'],
                    "Indikator": rubrik['Indikator'],
                    "Nilai": [st.session_state.get(f"nilai_{v}_{i}", 0) for v in all_variabels for i in range(len(rubrik[rubrik['Variabel'] == v]))]
                }))
            )
            nilai.append(n)
            uploaded_pdfs = st.file_uploader(
                "Upload bukti (bisa multi PDF):",
                type="pdf",
                key=f"pdf_{var}_{idx}",
                accept_multiple_files=True
            )
            all_uploaded_files.append(uploaded_pdfs)
            st.markdown("<hr style='margin:0.5rem 0'>", unsafe_allow_html=True)

# --- Save progress nilai ketika selesai mengisi seluruh indikator
if st.button("Simpan Progress Manual"):
    df_save = pd.DataFrame({
        "Variabel": rubrik['Variabel'],
        "Indikator": rubrik['Indikator'],
        "Nilai": nilai
    })
    save_progress(df_save)
    st.success("Progress berhasil disimpan!")

# --- Proses dan Rekap Nilai ---
st.markdown("""
<style>
div.stButton > button {
    background-color: #1976d2;
    color: white;
    border-radius: 8px;
    padding: 0.6em 2.3em;
    font-size: 1.15rem;
    font-weight: 700;
    margin-top: 1.5em;
    box-shadow: 0 3px 10px rgba(25, 118, 210, 0.17);
    border: none;
    transition: 0.3s;
}
div.stButton > button:hover {
    background-color: #2196f3;
    color: #fff;
    box-shadow: 0 5px 20px rgba(25, 118, 210, 0.28);
    transform: scale(1.045);
}
</style>
""", unsafe_allow_html=True)

if st.button("Proses dan Rekap Nilai"):
    rubrik['Nilai'] = nilai
    skor = []
    for idx, row in rubrik.iterrows():
        if 0 <= idx <= 4:
            skor.append((nilai[idx] / 100) * row['Poin'])
        else:
            skor.append(nilai[idx] * row['Poin'])
    rubrik['Skor'] = skor

    total_skor = rubrik['Skor'].sum()
    st.success(f"**Total Skor Akhir: {total_skor:.2f}**")
    st.markdown("#### Rekap Penilaian")
    st.dataframe(rubrik[['Variabel', 'Indikator', 'Nilai', 'Poin', 'Skor']])

    # Simpan progress terakhir otomatis
    df_save = pd.DataFrame({
        "Variabel": rubrik['Variabel'],
        "Indikator": rubrik['Indikator'],
        "Nilai": nilai
    })
    save_progress(df_save)

    os.makedirs(PDF_FOLDER, exist_ok=True)
    merger = PdfMerger()
    bukti_ada = False
    for i, files in enumerate(all_uploaded_files):
        indikator_paths = []
        if files:
            for j, file in enumerate(files):
                bukti_ada = True
                pdf_path = os.path.join(PDF_FOLDER, f"indikator{i+1}_bukti{j+1}_{file.name}")
                with open(pdf_path, "wb") as fout:
                    fout.write(file.read())
                merger.append(pdf_path)
                indikator_paths.append(pdf_path)
    if bukti_ada:
        gabung_path = os.path.join(PDF_FOLDER, "bukti_gabungan.pdf")
        with open(gabung_path, "wb") as fout:
            merger.write(fout)
        st.success("Semua file PDF berhasil digabung!")
        with open(gabung_path, "rb") as fpdf:
            st.download_button("Download Bukti Gabungan PDF", fpdf, file_name="bukti_gabungan.pdf")
    else:
        st.info("Anda belum mengupload bukti PDF untuk indikator manapun.")

# --- Progress Checklist di BAWAH ---
st.markdown("---")
st.markdown("### Progress Pengisian Penilaian")
for var in all_variabels:
    st.write(f"- {'✅' if st.session_state.get(f'centang_{var}', False) else '⬜️'} {var}")

st.caption("Yan-Dev-GengCer.")
