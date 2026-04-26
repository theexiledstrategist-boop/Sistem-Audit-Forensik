import streamlit as st
import pdfplumber
import pandas as pd
from fuzzywuzzy import fuzz, process
import pytesseract
from pdf2image import convert_from_bytes
import io
import re

# ==========================================
# 1. KONFIGURASI ANTARMUKA (UI)
# ==========================================
st.set_page_config(page_title="Audit Forensik Proyek V2", page_icon="⚖️", layout="wide")

st.title("⚖️ Sistem Audit Forensik & Verifikator Progress")
st.markdown("Mesin Verifikasi Tanpa Kompromi: Singkronisasi Visual, Lokasi, dan Kalkulasi Real Progress.")
st.markdown("---")

# ==========================================
# 2. MODUL UPLOAD FILE
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Data 1: Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah Laporan Mingguan (PDF Scan/Teks)", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Data 2: Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah Laporan Dokumentasi (PDF Scan)", type=["pdf"], key="dokumentasi")

# ==========================================
# 3. MESIN EKSTRAKSI OCR & TABLE PARSING
# ==========================================
def ekstrak_data_forensik(file_pdf, nama_file):
    """Mengekstrak teks dengan OCR dan mencoba memetakan lokasi serta bobot."""
    teks_lengkap = ""
    file_bytes = file_pdf.read()
    
    # Aktivasi OCR langsung karena data user terdeteksi scan murni
    try:
        images = convert_from_bytes(file_bytes)
        for i, img in enumerate(images):
            # Membaca teks dengan Tesseract
            page_text = pytesseract.image_to_string(img, lang='ind')
            teks_lengkap += f"\n[PAGE_{i+1}]\n" + page_text
    except Exception as e:
        st.error(f"Gagal menjalankan OCR pada {nama_file}: {e}")
        return []
            
    baris_teks = [baris.strip() for baris in teks_lengkap.split('\n') if len(baris.strip()) > 5]
    return baris_teks

def parse_detailed_claims(baris_teks):
    """
    Mencoba mencari pola: [LOKASI] - [PEKERJAAN] - [PROGRESS %]
    Berdasarkan format laporan user (MIS/MTSS).
    """
    items = []
    current_lokasi = "Lokasi Tidak Terdeteksi"
    
    for baris in baris_teks:
        # Deteksi Lokasi (Contoh: MIS DARUL ULUM, MTSS MIFTAHUL)
        if any(x in baris.upper() for x in ["MIS ", "MTSS "]):
            current_lokasi = baris
            
        # Deteksi Item Pekerjaan & Mencoba mengambil angka di akhir baris (asumsi progres minggu ini)
        if any(k in baris.lower() for k in ["pekerjaan", "pasang", "cor", "fabrikasi"]):
            # Cari angka desimal menggunakan regex untuk progres %
            match_percent = re.findall(r"(\d+[.,]\d+)", baris)
            progres = float(match_percent[0].replace(',', '.')) if match_percent else 0.0
            
            if len(baris) > 15:
                items.append({
                    "lokasi": current_lokasi,
                    "pekerjaan": baris,
                    "progres_klaim": progres
                })
    return items

# ==========================================
# 4. EKSEKUSI AUDIT & GENERASI NARASI
# ==========================================
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 JALANKAN AUDIT & HITUNG REAL PROGRESS", use_container_width=True):
        with st.spinner('Sedang membedah ribuan piksel data scan...'):
            
            raw_mingguan = ekstrak_data_forensik(file_mingguan, "Laporan Mingguan")
            raw_dokumentasi = ekstrak_data_forensik(file_dokumentasi, "Laporan Dokumentasi")
            
            klaim_items = parse_detailed_claims(raw_mingguan)
            
            if klaim_items:
                st.subheader("📊 Matriks Verifikasi & Kalkulasi Lapangan")
                
                audit_results = []
                total_klaim = 0.0
                total_ditolak = 0.0
                
                for item in klaim_items:
                    # Forensic Matching
                    best_match, score = process.extractOne(item['pekerjaan'], raw_dokumentasi, scorer=fuzz.token_set_ratio)
                    
                    status = "✅ SINKRON" if score >= 75 else "❌ TIDAK SINKRON"
                    
                    if status == "❌ TIDAK SINKRON":
                        total_ditolak += item['progres_klaim']
                    
                    total_klaim += item['progres_klaim']
                    
                    audit_results.append({
                        "Lokasi": item['lokasi'],
                        "Uraian Pekerjaan": item['pekerjaan'],
                        "Klaim %": item['progres_klaim'],
                        "Status": status,
                        "Bukti Visual": best_match if score >= 75 else "Nihil / Tidak Relevan",
                        "Akurasi": f"{score}%"
                    })
                
                df = pd.DataFrame(audit_results)
                
                # Menampilkan Tabel Utama
                st.dataframe(df.style.applymap(lambda x: 'color: red' if x == "❌ TIDAK SINKRON" else '', subset=['Status']), use_container_width=True)
                
                # --- BAGIAN NARASI & FINAL VERDICT ---
                total_diterima = total_klaim - total_ditolak
                
                st.markdown("---")
                st.header("📝 Narasi Audit & Keputusan Final")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Progress Diklaim", f"{total_klaim:.3f}%")
                c2.metric("Progress Ditolak (Red Flag)", f"-{total_ditolak:.3f}%", delta_color="inverse")
                c3.metric("Total Real Progress Diterima", f"{total_diterima:.3f}%")

                # Narasi Otomatis Berstandar Tinggi
                st.info(f"""
                **KESIMPULAN AUDIT:**
                Berdasarkan audit korelasi silang antara Laporan Mingguan dan Laporan Dokumentasi, ditemukan bahwa dari total klaim progres sebesar **{total_klaim:.3f}%**, terdapat **{total_ditolak:.3f}%** pekerjaan yang tidak didukung oleh bukti visual yang memadai (Red Flag).
                
                **Item Pelanggaran Utama:**
                Terdapat ketidaksesuaian kritis pada lokasi {df[df['Status'] == '❌ TIDAK SINKRON']['Lokasi'].unique().tolist()} terutama pada item pekerjaan yang tercatat sebagai 'Tidak Sinkron' di atas.
                
                **KEPUTUSAN ADMINISTRATIF:**
                Pejabat Pembuat Komitmen (PPK) disarankan hanya menyetujui progres fisik sebesar **{total_diterima:.3f}%** untuk Minggu ke-14 ini. Sisa progres sebesar **{total_ditolak:.3f}%** ditangguhkan hingga kontraktor melampirkan bukti foto yang valid atau dilakukan opname fisik ulang di lapangan.
                """)
                
            else:
                st.error("Gagal mendeteksi uraian pekerjaan. Pastikan kualitas scan PDF cukup jelas.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Silakan unggah kedua file untuk memulai kalkulasi Real Progress.")
