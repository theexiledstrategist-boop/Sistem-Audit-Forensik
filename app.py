import streamlit as st
import pdfplumber
import pandas as pd
from fuzzywuzzy import fuzz, process

# ==========================================
# 1. KONFIGURASI ANTARMUKA (UI)
# ==========================================
st.set_page_config(page_title="Audit Forensik Proyek", page_icon="🔬", layout="wide")

st.title("🔬 Sistem Audit Forensik: Teks vs Visual")
st.markdown("Alat evaluasi presisi tinggi untuk menyinkronkan klaim Laporan Mingguan dengan Laporan Dokumentasi.")
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
def ekstrak_teks_pdf(file_pdf):
    """Mengekstrak teks kasar dari PDF dengan toleransi spasi tabel."""
    teks_lengkap = ""
    try:
        with pdfplumber.open(file_pdf) as pdf:
            for page in pdf.pages:
                # Menggunakan layout=True untuk menjaga struktur tabel
                teks = page.extract_text(x_tolerance=2, y_tolerance=2)
                if teks:
                    teks_lengkap += teks + "\n"
    except Exception as e:
        st.error(f"Gagal membaca PDF: {e}")
        return []
        
    baris_teks = [baris.strip() for baris in teks_lengkap.split('\n') if len(baris.strip()) > 4]
    return baris_teks

# Tombol Eksekusi
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 EKSEKUSI AUDIT FORENSIK", use_container_width=True):
        with st.spinner('Membedah struktur data... Stand by.'):
            
            # Ekstraksi Teks
            teks_klaim = ekstrak_teks_pdf(file_mingguan)
            teks_bukti = ekstrak_teks_pdf(file_dokumentasi)
            
            # Kata kunci ekstraksi (Case Insensitive)
            keywords = ["pekerjaan", "pasang", "cor", "bekisting", "fabrikasi", "atap", "keramik", "instalasi"]
            
            # Filter klaim: cari baris yang mengandung salah satu kata kunci di atas
            klaim_pekerjaan = [t for t in teks_klaim if any(k in t.lower() for k in keywords)]
            
            st.subheader("📊 Hasil Audit Korelasi Silang")
            
            if klaim_pekerjaan:
                audit_log = []
                strictness = 75 # Presisi tinggi
                
                for klaim in klaim_pekerjaan:
                    # Lewati baris yang terlalu pendek atau sekadar header tabel
                    if len(klaim) < 15:
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
                st.error("Sistem gagal mengekstrak frasa pekerjaan. Kemungkinan PDF berupa hasil Scan (Gambar) murni tanpa teks yang bisa diblok, atau format tabel terlalu terpecah.")
                
                # Radar Diagnostik: Menampilkan apa yang sebenarnya dilihat mesin
                with st.expander("🛠️ Radar Diagnostik: Lihat Teks Mentah yang Terbaca Mesin"):
                    st.write("**Isi Teks Laporan Mingguan yang Terbaca:**")
                    st.write(teks_klaim[:30] if teks_klaim else "KOSONG/GAGAL BACA")

