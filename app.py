import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
import re
from PIL import Image
from datetime import datetime

# ==========================================
# 1. KONFIGURASI UI (OPTIMASI SMARTPHONE)
# ==========================================
st.set_page_config(page_title="Audit Forensik Lintas Madrasah", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stAlert { border-radius: 10px; }
    .status-ok { background-color: #ccffcc; color: green; padding: 5px; border-radius: 5px; font-weight: bold; }
    .status-fail { background-color: #ffcccc; color: red; padding: 5px; border-radius: 5px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. LOGIKA KRITIS (CONTEXT-AWARE MATCHING)
# ==========================================

def bersihkan_angka(teks):
    if not teks: return 0.0
    try:
        return float(str(teks).strip().replace(' ', '').replace(',', '.'))
    except:
        return 0.0

def cari_lokasi(teks):
    """Mendeteksi Nama Madrasah (MIS/MTSS) sebagai context lokasi."""
    match = re.search(r'(MIS|MTSS)\s+[A-Z\s\']+', teks.upper())
    return match.group(0).strip() if match else None

def ambil_bangunan(teks):
    """Mengekstrak identitas bangunan (misal: Bangunan A, B, E)."""
    match = re.search(r'BANGUNAN\s+[A-Z\d]+', teks.upper())
    return match.group(0).strip() if match else None

# ==========================================
# 3. INTERFACE & INPUT
# ==========================================
st.title("🛡️ Audit Forensik Dokumen PHTC")
st.caption("Validasi Progres Fisik & Bukti Visual Lintas Lokasi")

st.sidebar.header("📁 Upload Dokumen")
file_mingguan = st.sidebar.file_uploader("1. Laporan Mingguan (PDF)", type="pdf")
file_dokumentasi = st.sidebar.file_uploader("2. Laporan Dokumentasi (PDF)", type="pdf")

if not (file_mingguan and file_dokumentasi):
    st.warning("Silakan unggah kedua PDF untuk memulai audit menyeluruh terhadap semua lokasi madrasah.")
    st.stop()

# ==========================================
# 4. PROSES AUDIT TOTAL
# ==========================================
if st.sidebar.button("⚙️ JALANKAN AUDIT SEMUA ITEM", use_container_width=True):
    
    # FASE 1: Membaca Seluruh Teks Dokumentasi
    with st.spinner("Memindai database foto dokumentasi..."):
        teks_foto_full = ""
        doc_foto = fitz.open(stream=file_dokumentasi.read(), filetype="pdf")
        for page in doc_foto:
            teks_foto_full += page.get_text("text").upper() + " "
        file_dokumentasi.seek(0)

    # FASE 2: Iterasi Laporan Mingguan (Semua Halaman)
    st.header("🔍 Hasil Pemeriksaan Lintas Lokasi")
    
    anomali_angka = []
    hasil_validasi = []
    lokasi_sekarang = "LOKASI TIDAK TERDETEKSI"

    with st.spinner("Membedah setiap baris pekerjaan di laporan mingguan..."):
        with pdfplumber.open(file_mingguan) as pdf:
            for page in pdf.pages:
                tabel = page.extract_table()
                if not tabel: continue
                
                for row in tabel:
                    try:
                        uraian = str(row[1]).replace('\n', ' ').strip()
                        
                        # A. Update Lokasi Madrasah jika baris adalah Header Lokasi
                        lokasi_baru = cari_lokasi(uraian)
                        if lokasi_baru:
                            lokasi_sekarang = lokasi_baru
                        
                        # B. Ambil Data Progres (Kolom 5, 8, 11 sesuai format Anda)
                        b_lalu = bersihkan_angka(row[5])
                        b_ini = bersihkan_angka(row[8])
                        b_total = bersihkan_angka(row[11])
                        
                        if b_ini > 0:
                            # 1. Audit Matematika
                            hitungan = round(b_lalu + b_ini, 3)
                            if abs(b_total - hitungan) > 0.001:
                                anomali_angka.append({
                                    "Lokasi": lokasi_sekarang,
                                    "Item": uraian,
                                    "Selisih": round(b_total - hitungan, 3)
                                })
                            
                            # 2. Audit Visual (Matching Madrasah + Bangunan)
                            id_bangunan = ambil_bangunan(uraian)
                            
                            # Kriteria: Madrasah harus ada di teks, dan Bangunan (jika ada) harus ada
                            keyword_lokasi = lokasi_sekarang.replace("MIS ", "").replace("MTSS ", "").split()[0] # Ambil kata depan (e.g. DARUL)
                            
                            if keyword_lokasi in teks_foto_full:
                                if id_bangunan:
                                    if id_bangunan in teks_foto_full:
                                        status = "✅ BUKTI ADA"
                                    else:
                                        status = f"❌ FOTO {id_bangunan} TIDAK ADA"
                                else:
                                    status = "✅ LOKASI TERVERIFIKASI"
                            else:
                                status = "❌ LOKASI TIDAK ADA DI FOTO"
                                
                            hasil_validasi.append({
                                "Lokasi Madrasah": lokasi_sekarang,
                                "Item Pekerjaan": uraian,
                                "Progres": f"+{b_ini}%",
                                "Status Bukti": status
                            })
                    except: continue

    # ==========================================
    # 5. TAMPILAN OUTPUT FINAL
    # ==========================================
    
    # Tabulasi Hasil
    tab1, tab2 = st.tabs(["📊 Rapor Validasi Progres", "⚠️ Log Kesalahan Angka"])
    
    with tab1:
        st.subheader("Kesesuaian Klaim Pekerjaan vs Laporan Visual")
        if hasil_validasi:
            df_v = pd.DataFrame(hasil_validasi)
            def style_row(val):
                color = '#ffcccc' if "❌" in val else '#ccffcc'
                return f'background-color: {color}'
            st.dataframe(df_v.style.applymap(style_row, subset=['Status Bukti']), use_container_width=True)
        else:
            st.info("Tidak ada penambahan progres minggu ini.")

    with tab2:
        st.subheader("Ketidaksesuaian Penjumlahan Bobot")
        if anomali_angka:
            st.error("Ditemukan kesalahan kalkulasi pada item berikut:")
            st.table(pd.DataFrame(anomali_angka))
        else:
            st.success("Seluruh perhitungan bobot sinkron 100%.")

