import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
import re
from PIL import Image
from datetime import datetime

# ==========================================
# 1. INISIALISASI & UI
# ==========================================
st.set_page_config(page_title="Audit Forensik Progres PHTC", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f9f9fb; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-box { padding: 10px; border-radius: 5px; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNGSI PENDUKUNG (LOGIKA PROSES)
# ==========================================

def get_float(val):
    if not val: return 0.0
    try:
        clean = re.sub(r'[^\d,\.-]', '', str(val))
        return float(clean.replace(',', '.'))
    except: return 0.0

def detect_madrasah(text):
    match = re.search(r'(MIS|MTSS)\s+[A-Z0-9\s\'\-]+', str(text).upper())
    return match.group(0).strip() if match else None

def get_material_keyword(uraian):
    """Mengekstrak inti material (misal: 'Kusen Pintu', 'Atap Metal')"""
    text = re.sub(r'\(.*?\)', '', str(uraian).upper())
    words = text.split()
    ignore = {"PEKERJAAN", "PEMASANGAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", "REHABILITASI", "RENOVASI", "BANGUNAN", "UNTUK", "DAN", "DENGAN"}
    clean_words = [w for w in words if w not in ignore and len(w) > 3]
    return " ".join(clean_words[:2]) if clean_words else ""

# ==========================================
# 3. ANTARMUKA UTAMA
# ==========================================
st.title("🛡️ Sistem Audit Forensik PHTC")
st.caption("Metode Audit: Sekuensial (Tabulasi -> Verifikasi Angka -> Verifikasi Visual)")

with st.sidebar:
    st.header("📂 Sumber Data")
    f_mingguan = st.file_uploader("Upload Laporan Mingguan", type="pdf")
    f_foto = st.file_uploader("Upload Laporan Dokumentasi", type="pdf")
    st.markdown("---")
    btn_audit = st.button("⚙️ JALANKAN PROSES AUDIT", use_container_width=True)

if not (f_mingguan and f_foto):
    st.info("Sistem siap. Silakan unggah kedua dokumen untuk memulai verifikasi.")
    st.stop()

# ==========================================
# 4. EKSEKUSI AUDIT SEKUENSIAL
# ==========================================
if btn_audit:
    
    # --- LANGKAH 1: EKSTRAKSI TABEL PEKERJAAN AKTIF ---
    pekerjaan_aktif = []
    lokasi_skrg = "UMUM"
    
    with st.spinner("Langkah 1: Mengidentifikasi item pekerjaan aktif..."):
        with pdfplumber.open(f_mingguan) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # Hanya ambil halaman yang merupakan tabel Kemajuan Fisik
                if not text or "KEMAJUAN FISIK" not in text.upper(): continue
                
                table = page.extract_table()
                if not table: continue
                
                for row in table:
                    if len(row) < 12: continue
                    uraian = str(row[1]).replace('\n', ' ').strip()
                    
                    # Update Konteks Lokasi
                    lok_baru = detect_madrasah(uraian)
                    if lok_baru: lokasi_skrg = lok_baru
                    
                    # Identifikasi Progres Minggu Ini (Kolom 8)
                    b_ini = get_float(row[8])
                    if b_ini > 0:
                        pekerjaan_aktif.append({
                            "Lokasi": lokasi_skrg,
                            "Uraian": uraian,
                            "Lalu": get_float(row[5]),
                            "Ini": b_ini,
                            "Total_Klaim": get_float(row[11]),
                            "Keywords": get_material_keyword(uraian)
                        })

    if not pekerjaan_aktif:
        st.error("Sistem tidak mendeteksi adanya progres fisik (>0%) pada tabel Kemajuan Fisik.")
        st.stop()

    # --- LANGKAH 2: AUDIT MATEMATIS (PENGECEKAN SALDO) ---
    with st.spinner("Langkah 2: Memverifikasi akurasi perhitungan bobot..."):
        anomali_angka = []
        for item in pekerjaan_aktif:
            seharusnya = round(item['Lalu'] + item['Ini'], 3)
            deviasi = round(item['Total_Klaim'] - seharusnya, 3)
            if abs(deviasi) > 0.001:
                anomali_angka.append({
                    "Lokasi": item['Lokasi'],
                    "Pekerjaan": item['Uraian'],
                    "Seharusnya": seharusnya,
                    "Klaim": item['Total_Klaim'],
                    "Selisih": deviasi
                })

    # --- LANGKAH 3: VERIFIKASI VISUAL (MATCHING FOTO) ---
    with st.spinner("Langkah 3: Mencocokkan item aktif dengan bukti foto..."):
        teks_foto_db = ""
        doc_foto = fitz.open(stream=f_foto.read(), filetype="pdf")
        for p in doc_foto:
            teks_foto_db += p.get_text("text").upper() + " "
        
        final_report = []
        for item in pekerjaan_aktif:
            kw = item['Keywords']
            loc_kw = item['Lokasi'].replace("MIS ", "").replace("MTSS ", "").split()[0]
            
            # Verifikasi apakah lokasi dan material ada di laporan foto
            found_loc = loc_kw in teks_foto_db
            found_mat = kw in teks_foto_db if kw else True
            
            status = "✅ VALID"
            catatan = "Bukti visual ditemukan."
            
            if not found_loc:
                status = "❌ TOLAK"
                catatan = f"Lokasi {item['Lokasi']} tidak terdeteksi di laporan foto."
            elif not found_mat:
                status = "❌ TOLAK"
                catatan = f"Material '{kw}' tidak ditemukan pada bukti dokumentasi."
            
            final_report.append({
                "Madrasah": item['Lokasi'],
                "Pekerjaan": item['Uraian'],
                "Bobot (+%)": item['Ini'],
                "Status": status,
                "Analisis": catatan
            })

    # ==========================================
    # 5. PENYAJIAN HASIL (OUTPUT)
    # ==========================================
    
    st.header("📊 Ringkasan Hasil Audit")
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Pekerjaan Diperiksa", len(pekerjaan_aktif))
    c2.metric("Kesalahan Angka", len(anomali_angka))
    c3.metric("Item Tanpa Bukti", len([x for x in final_report if "❌" in x['Status']]))
    
    st.divider()

    # Output Tabel 1: Rangkuman Pekerjaan & Status
    st.subheader("1. Tabel Validasi Progres vs Dokumentasi")
    df_final = pd.DataFrame(final_report)
    def color_status(val):
        color = '#ffcccc' if "❌" in val else '#dff0d8'
        return f'background-color: {color}'
    st.dataframe(df_final.style.applymap(color_status, subset=['Status']), use_container_width=True)

    # Output Tabel 2: Anomali Angka
    if anomali_angka:
        st.subheader("2. Daftar Kesalahan Perhitungan (Anomali)")
        st.warning("Ditemukan ketidaksesuaian antara (Bobot Lalu + Bobot Ini) dengan Bobot Total.")
        st.table(pd.DataFrame(anomali_angka))

    # Output 3: Draf Kesimpulan
    st.subheader("3. Draf Berita Acara Audit")
    has_error = len(anomali_angka) > 0 or len([x for x in final_report if "❌" in x['Status']]) > 0
    kesimpulan = "REVISI TOTAL" if has_error else "DISETUJUI"
    
    ba_text = f"""
    HASIL PEMERIKSAAN DOKUMEN (DESK AUDIT)
    --------------------------------------
    Tanggal Pemeriksaan: {datetime.now().strftime('%d-%m-%Y')}
    Objek Pemeriksaan  : Progres Mingguan PHTC
    Status Dokumen     : {kesimpulan}

    TEMUAN AUDIT:
    1. Perhitungan Angka: {'Ditemukan ketidaksesuaian' if anomali_angka else 'Sinkron dan akurat'}.
    2. Bukti Visual     : {'Ditemukan klaim progres tanpa dukungan foto' if '❌' in str(final_report) else 'Lengkap dan linear'}.

    CATATAN:
    {'Segera perbaiki laporan pada item bertanda merah sebelum pengajuan termin.' if has_error else 'Laporan dapat diproses lebih lanjut.'}
    """
    st.code(ba_text, language="text")
