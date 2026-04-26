import streamlit as st
import pdfplumber
import pandas as pd
from fuzzywuzzy import fuzz, process
import pytesseract
from pdf2image import convert_from_bytes
import io

# ==========================================
# 1. KONFIGURASI ANTARMUKA (UI)
# ==========================================
st.set_page_config(page_title="Audit Forensik Proyek", page_icon="🔬", layout="wide")

st.title("🔬 Sistem Audit Forensik: Teks vs Visual")
st.markdown("Mesin evaluasi presisi tinggi dengan integrasi **OCR** untuk membaca laporan hasil scan.")
st.markdown("---")

# ==========================================
# 2. MODUL UPLOAD FILE
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Data 1: Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah Laporan Mingguan (PDF)", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Data 2: Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah Laporan Dokumentasi (PDF)", type=["pdf"], key="dokumentasi")

# ==========================================
# 3. MESIN EKSTRAKSI & AUDIT (BACKEND)
# ==========================================
def ekstrak_teks_pdf(file_pdf, nama_file):
    """Mengekstrak teks dengan Fallback OCR jika PDF berupa Scan."""
    teks_lengkap = ""
    file_bytes = file_pdf.read()
    
    # FASE 1: Ekstraksi Standar
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                teks = page.extract_text(x_tolerance=2, y_tolerance=2)
                if teks:
                    teks_lengkap += teks + "\n"
    except Exception:
        pass

    # FASE 2: Aktivasi OCR (Jika Teks Kosong/Scan Murni)
    if len(teks_lengkap.strip()) < 50:
        st.warning(f"⚠️ [{nama_file}] Terdeteksi sebagai PDF Scan. Mengaktifkan mesin OCR... (Proses ini memakan waktu beberapa menit).")
        try:
            # Mengubah PDF menjadi deretan gambar
            images = convert_from_bytes(file_bytes)
            for i, img in enumerate(images):
                # Membaca teks dari gambar dengan Tesseract (Bahasa Indonesia)
                teks_lengkap += pytesseract.image_to_string(img, lang='ind') + "\n"
        except Exception as e:
            st.error(f"FATAL ERROR pada OCR: {e}. Pastikan file packages.txt sudah dibuat di GitHub.")
            return []
            
    baris_teks = [baris.strip() for baris in teks_lengkap.split('\n') if len(baris.strip()) > 4]
    return baris_teks

# Tombol Eksekusi
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 EKSEKUSI AUDIT FORENSIK", use_container_width=True):
        with st.spinner('Menjalankan ekstraksi dan korelasi tingkat tinggi...'):
            
            # Ekstraksi Teks dengan OCR
            teks_klaim = ekstrak_teks_pdf(file_mingguan, "Laporan Mingguan")
            teks_bukti = ekstrak_teks_pdf(file_dokumentasi, "Laporan Dokumentasi")
            
            # Kata kunci ekstraksi (Case Insensitive)
            keywords = ["pekerjaan", "pasang", "cor", "bekisting", "fabrikasi", "atap", "keramik", "instalasi"]
            klaim_pekerjaan = [t for t in teks_klaim if any(k in t.lower() for k in keywords)]
            
            st.subheader("📊 Hasil Audit Korelasi Silang")
            
            if klaim_pekerjaan:
                audit_log = []
                strictness = 75 # Toleransi Forensik
                
                for klaim in klaim_pekerjaan:
                    if len(klaim) < 15: # Mengabaikan frasa yang terlalu pendek
                        continue
                        
                    best_match, score = process.extractOne(klaim, teks_bukti, scorer=fuzz.token_set_ratio)
                    
                    if score >= strictness:
                        audit_log.append({"Status": "✅ TERVERIFIKASI", "Klaim di Laporan": klaim, "Bukti Ditemukan": best_match, "Akurasi": f"{score}%"})
                    else:
                        audit_log.append({"Status": "❌ RED FLAG (TIDAK SINKRON)", "Klaim di Laporan": klaim, "Bukti Ditemukan": "Visual Lemah/Nihil", "Akurasi": f"{score}%"})

                if audit_log:
                    df_hasil = pd.DataFrame(audit_log)
                    df_gagal = df_hasil[df_hasil["Status"] == "❌ RED FLAG (TIDAK SINKRON)"]
                    df_lolos = df_hasil[df_hasil["Status"] == "✅ TERVERIFIKASI"]
                    
                    if not df_gagal.empty:
                        st.error(f"🚨 Terdapat {len(df_gagal)} klaim tanpa bukti visual yang absolut.")
                        st.dataframe(df_gagal, use_container_width=True)
                    else:
                        st.success("Seluruh klaim laporan mingguan terverifikasi visual.")
                    
                    if not df_lolos.empty:
                        with st.expander(f"Lihat {len(df_lolos)} Klaim Terverifikasi"):
                            st.dataframe(df_lolos, use_container_width=True)
            else:
                st.error("Sistem tetap gagal menemukan frasa. Kualitas resolusi scan mungkin terlalu rendah untuk dibaca oleh mesin OCR.")
                
                with st.expander("🛠️ Radar Diagnostik OCR: Lihat Teks Mentah"):
                    st.write("**Hasil Ekstraksi OCR Laporan Mingguan:**")
                    st.write(teks_klaim[:50] if teks_klaim else "KOSONG/GAGAL BACA")
