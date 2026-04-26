import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
from pdf2image import convert_from_bytes
import google.generativeai as genai
import json
import re
import time

# ==========================================
# 1. KONFIGURASI SISTEM & OTORISASI
# ==========================================
st.set_page_config(page_title="Audit Forensik PPSPM", page_icon="🛡️", layout="wide")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("FATAL ERROR: API Key belum dikonfigurasi di Streamlit Secrets.")
    st.stop()

st.title("🛡️ Sistem Evaluasi Laporan PPSPM (Absolute Precision)")
st.markdown("Audit forensik aktif. Memastikan pemotongan tagihan didasarkan pada perhitungan matematis yang sah secara hukum.")
st.markdown("---")

# ==========================================
# 2. RADAR MODEL OTOMATIS
# ==========================================
@st.cache_data(ttl=3600)
def dapatkan_daftar_model_sah():
    model_tersedia = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower():
                model_tersedia.append(m.name.replace('models/', ''))
        return model_tersedia
    except Exception as e:
        return ["gemini-2.0-flash", "gemini-1.5-flash"]

daftar_model_resmi = dapatkan_daftar_model_sah()

with st.sidebar:
    st.header("⚙️ Parameter Kontrak Utama")
    klaim_progress_total = st.number_input("Klaim Progress Minggu Ini (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
    
    st.markdown("---")
    st.subheader("🧠 Otak Analitik API")
    target_model = st.selectbox("Versi Mesin:", daftar_model_resmi)

# ==========================================
# 3. MODUL UPLOAD DOKUMEN
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah PDF Progress", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah PDF Foto", type=["pdf"], key="dokumentasi")

# ==========================================
# 4. MESIN EKSTRAKSI VISION AI (FLEXIBLE PARSER)
# ==========================================
def bedah_dokumen_dengan_ai(file_pdf, tipe_dokumen):
    status_placeholder = st.empty()
    try:
        images = convert_from_bytes(file_pdf.read())
    except Exception as e:
        st.error(f"Gagal membedah PDF {tipe_dokumen}: {e}")
        return []

    model = genai.GenerativeModel(target_model)
    results = []
    
    if tipe_dokumen == "mingguan":
        # PROMPT DIPERBARUI: Lebih pintar, fleksibel, dan memaksa AI tetap menjawab meski tabelnya hancur
        prompt = """
        Anda adalah auditor forensik. Bedah gambar tabel ini.
        Tugas Anda adalah mengekstrak daftar rincian pekerjaan konstruksi.
        
        Aturan Ekstraksi:
        1. "lokasi": Nama madrasah/lokasi (jika tidak ada, isi "TIDAK SPESIFIK").
        2. "pekerjaan": Deskripsi pekerjaan (perbaiki ejaan jika buram).
        3. "progres": Cari angka kemajuan fisik/bobot persentase TERBARU atau MINGGU INI. Jika bentuknya desimal koma (misal 2,45), ubah wajib jadi titik (2.45). Jika kolom progres kosong/tidak terbaca, WAJIB isi 0.0.
        
        Keluarkan HANYA dalam format array JSON murni tanpa teks awalan/akhiran apa pun:
        [
          {"lokasi": "MIS ALAM", "pekerjaan": "Pasang Bata", "progres": 1.25},
          {"lokasi": "MIS ALAM", "pekerjaan": "Plesteran", "progres": 0.0}
        ]
        
        WAJIB kembalikan array JSON. Jangan pernah kembalikan array kosong [] jika ada teks pekerjaan di halaman ini.
        """
    else:
        prompt = """
        Ekstrak semua keterangan teks (caption) yang ada pada foto dokumentasi ini.
        Keluarkan HANYA format array JSON murni:
        [{"caption": "Teks keterangan foto 1"}, {"caption": "Teks keterangan foto 2"}]
        """

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        status_placeholder.info(f"⏳ Mengeksekusi {tipe_dokumen} halaman {i+1}/{len(images)}...")
        try:
            response = model.generate_content([prompt, img])
            # Membersihkan Markdown dan menarik JSON
            clean_text = re.sub(r'
http://googleusercontent.com/immersive_entry_chip/0

**Perubahan Kritis pada Prompt:**
Saya telah menambahkan kalimat instruksi: *"Jangan pernah kembalikan array kosong [] jika ada teks pekerjaan di halaman ini."* Ini akan memaksa kecerdasan buatan untuk mengutamakan penarikan nama pekerjaan meskipun ia kesulitan membaca angka progresnya. Silakan *commit* dan jalankan kembali audit presisi tersebut.
