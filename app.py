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
st.markdown("""
**Standard Operating Procedure (SOP):** Mesin verifikasi ini mensinkronkan klaim pada Laporan Mingguan dengan bukti fisik di Laporan Dokumentasi. Sistem dirancang untuk mengeleminasi risiko administratif dengan presisi tinggi.
""")
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
    """
    Ekstraksi dua lapis: Mencoba lapis teks standar (pdfplumber) terlebih dahulu.
    Jika gagal atau terdeteksi sebagai scan murni, mesin OCR (Tesseract) diaktifkan.
    """
    teks_lengkap = ""
    file_bytes = file_pdf.read()
    
    # FASE 1: Uji Ekstraksi Teks Standar
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                teks = page.extract_text(x_tolerance=2, y_tolerance=2)
                if teks:
                    teks_lengkap += teks + "\n"
    except Exception:
        pass

    # FASE 2: Penetrasi OCR jika teks kosong
    if len(teks_lengkap.strip()) < 50:
        st.warning(f"⚠️ [{nama_file}] Menginisiasi Mesin OCR untuk membedah dokumen scan...")
        try:
            images = convert_from_bytes(file_bytes)
            for i, img in enumerate(images):
                page_text = pytesseract.image_to_string(img, lang='ind')
                teks_lengkap += f"\n[HALAMAN_{i+1}]\n" + page_text
        except Exception as e:
            st.error(f"[FATAL ERROR] Kegagalan mesin OCR pada {nama_file}. Pastikan file packages.txt terkonfigurasi di server. Detail: {e}")
            return []
            
    baris_teks = [baris.strip() for baris in teks_lengkap.split('\n') if len(baris.strip()) > 5]
    return baris_teks

def parse_detailed_claims(baris_teks):
    """
    Membedah baris teks untuk mencari: Lokasi, Uraian Pekerjaan, dan Bobot Progress (%).
    """
    items = []
    current_lokasi = "Lokasi Umum / Tidak Terdeteksi"
    
    # Kata kunci forensik untuk mengidentifikasi baris pekerjaan
    keywords_pekerjaan = ["pekerjaan", "pasang", "cor", "fabrikasi", "bekisting", "atap", "keramik", "pondasi"]
    
    for baris in baris_teks:
        # Identifikasi Lokasi Spesifik
        if any(x in baris.upper() for x in ["MIS ", "MTSS "]):
            current_lokasi = baris
            
        # Identifikasi Uraian Pekerjaan
        if any(k in baris.lower() for k in keywords_pekerjaan):
            # Regex untuk menangkap angka desimal progres (misal: 2.45 atau 0,12)
            match_percent = re.findall(r"(\d+[.,]\d+)", baris)
            
            # Mengambil angka desimal terakhir di baris tersebut sebagai asumsi progress minggu ini
            if match_percent:
                progres_str = match_percent[-1].replace(',', '.')
                try:
                    progres = float(progres_str)
                except ValueError:
                    progres = 0.0
            else:
                progres = 0.0
            
            # Memastikan baris cukup panjang untuk disebut sebuah uraian kalimat
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
    if st.button("🚀 JALANKAN AUDIT FORENSIK", use_container_width=True):
        with st.spinner('Menjalankan algoritma pembedahan dan korelasi silang...'):
            
            # Eksekusi Ekstraksi
            raw_mingguan = ekstrak_data_forensik(file_mingguan, "Laporan Mingguan")
            raw_dokumentasi = ekstrak_data_forensik(file_dokumentasi, "Laporan Dokumentasi")
            
            klaim_items = parse_detailed_claims(raw_mingguan)
            
            if klaim_items:
                st.subheader("📊 Matriks Verifikasi & Kalkulasi Lapangan")
                
                audit_results = []
                total_klaim = 0.0
                total_ditolak = 0.0
                strictness = 75 # Presisi kemiripan semantik
                
                for item in klaim_items:
                    # Proses Fuzzy Matching (Pencocokan Semantik)
                    best_match, score = process.extractOne(item['pekerjaan'], raw_dokumentasi, scorer=fuzz.token_set_ratio)
                    
                    status = "✅ SINKRON" if score >= strictness else "❌ TIDAK SINKRON"
                    
                    # Logika Kalkulasi Pemotongan
                    if status == "❌ TIDAK SINKRON":
                        total_ditolak += item['progres_klaim']
                    
                    total_klaim += item['progres_klaim']
                    
                    audit_results.append({
                        "Lokasi": item['lokasi'],
                        "Uraian Pekerjaan": item['pekerjaan'],
                        "Klaim (%)": item['progres_klaim'],
                        "Status": status,
                        "Bukti Visual": best_match if score >= strictness else "Nihil / Celah Ditemukan",
                        "Akurasi": f"{score}%"
                    })
                
                df = pd.DataFrame(audit_results)
                
                # Render Tabel dengan Sabuk Pengaman Versi Pandas (Menghindari AttributeError)
                try:
                    st.dataframe(df.style.map(lambda x: 'color: red; font-weight: bold' if x == "❌ TIDAK SINKRON" else '', subset=['Status']), use_container_width=True)
                except AttributeError:
                    st.dataframe(df.style.applymap(lambda x: 'color: red; font-weight: bold' if x == "❌ TIDAK SINKRON" else '', subset=['Status']), use_container_width=True)
                
                # ==========================================
                # 5. KEPUTUSAN FINAL & NARASI ADMINISTRATIF
                # ==========================================
                total_diterima = total_klaim - total_ditolak
                
                st.markdown("---")
                st.header("📝 Narasi Keputusan Eksekusi")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Progress Diklaim", f"{total_klaim:.3f}%")
                c2.metric("Progress Ditolak (Red Flag)", f"-{total_ditolak:.3f}%", delta_color="inverse")
                c3.metric("Total Real Progress Diterima", f"{total_diterima:.3f}%")

                # Ekstraksi Lokasi Bermasalah
                lokasi_bermasalah = df[df['Status'] == '❌ TIDAK SINKRON']['Lokasi'].unique().tolist()
                teks_lokasi = ", ".join(lokasi_bermasalah) if lokasi_bermasalah else "Tidak ada"

                st.info(f"""
                **HASIL AUDIT FORENSIK:**
                Berdasarkan komparasi data antara dokumen tertulis dan dokumentasi visual, ditemukan bahwa dari total klaim progress sebesar **{total_klaim:.3f}%**, terdapat **{total_ditolak:.3f}%** pekerjaan yang gagal dibuktikan keberadaannya di lapangan (Red Flag).
                
                **LOKASI TERINDIKASI DEVIASI DATA:**
                Ketidaksesuaian administrasi dan visual ditemukan secara spesifik pada lokasi: **{teks_lokasi}**.
                
                **TINDAKAN ADMINISTRATIF:**
                Direkomendasikan untuk menolak persetujuan penuh. Laporan hanya dapat disetujui untuk nilai real progress sebesar **{total_diterima:.3f}%**. Sisa klaim ditangguhkan hingga kontraktor pelaksana dapat menyajikan bukti fisik empiris yang memenuhi standar.
                """)
                
                # Radar Diagnostik Teks Mentah (Untuk pengawasan tambahan)
                with st.expander("🛠️ Radar Diagnostik OCR: Inspeksi Teks Mentah Laporan"):
                    st.write("**Data Ekstraksi Laporan Mingguan:**")
                    st.text("\n".join(raw_mingguan[:50])) 

            else:
                st.error("Mesin tidak dapat mengekstrak pola pekerjaan dan persentase. Pastikan resolusi scan PDF cukup tajam untuk dibaca oleh OCR.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem dalam status Stand By. Silakan unggah Laporan Mingguan dan Dokumentasi untuk memulai.")

st.markdown("---")
st.caption("Sistem dirancang dengan pendekatan utilitaritarian dan presisi absolut. Keputusan akhir tetap berada pada otoritas pejabat berwenang.")
