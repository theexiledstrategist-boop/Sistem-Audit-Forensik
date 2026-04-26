import streamlit as st
import pdfplumber
import pandas as pd
from fuzzywuzzy import fuzz, process

# ==========================================
# 1. KONFIGURASI ANTARMUKA (UI)
# ==========================================
st.set_page_config(page_title="Audit Forensik Proyek", page_icon="🔬", layout="wide")

st.title("🔬 Sistem Audit Forensik: Teks vs Visual")
st.markdown("""
Alat ini menggunakan algoritma *Fuzzy String Matching* untuk menguji keabsahan klaim pekerjaan di Laporan Mingguan terhadap bukti fisik di Laporan Dokumentasi secara otomatis.
""")
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
    """Mengekstrak teks kasar dari PDF untuk dianalisis."""
    teks_lengkap = ""
    with pdfplumber.open(file_pdf) as pdf:
        for page in pdf.pages:
            teks = page.extract_text()
            if teks:
                teks_lengkap += teks + "\n"
    # Memecah teks menjadi baris/kalimat untuk memudahkan pencarian
    baris_teks = [baris.strip() for baris in teks_lengkap.split('\n') if len(baris.strip()) > 5]
    return baris_teks

# Tombol Eksekusi
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 EKSEKUSI AUDIT FORENSIK", use_container_width=True):
        with st.spinner('Membedah dan menyinkronkan data... Stand by.'):
            
            # Ekstraksi Teks
            teks_klaim = ekstrak_teks_pdf(file_mingguan)
            teks_bukti = ekstrak_teks_pdf(file_dokumentasi)
            
            # Karena ini ekstraksi mentah dari tabel, kita ambil sampel kalimat
            # yang terindikasi sebagai 'Pekerjaan' untuk diadu.
            klaim_pekerjaan = [t for t in teks_klaim if "Pekerjaan" in t or "Pasang" in t or "Cor" in t]
            
            st.subheader("📊 Hasil Audit Korelasi Silang")
            
            audit_log = []
            strictness = 75 # Batas ketat toleransi kemiripan (0-100)
            
            # Membuat container untuk hasil
            hasil_container = st.container()
            
            for klaim in klaim_pekerjaan:
                # Mengadu setiap klaim tertulis dengan seluruh teks di laporan foto
                best_match, score = process.extractOne(klaim, teks_bukti, scorer=fuzz.token_set_ratio)
                
                if score >= strictness:
                    audit_log.append({"Status": "✅ TERVERIFIKASI", "Klaim di Laporan": klaim, "Bukti Ditemukan": best_match, "Akurasi": f"{score}%"})
                else:
                    audit_log.append({"Status": "❌ RED FLAG (TIDAK SINKRON)", "Klaim di Laporan": klaim, "Bukti Ditemukan": "Nihil / Foto tidak relevan", "Akurasi": f"{score}%"})

            # Menampilkan Dataframe
            if audit_log:
                df_hasil = pd.DataFrame(audit_log)
                
                # Memisahkan yang lolos dan gagal untuk visualisasi
                df_gagal = df_hasil[df_hasil["Status"] == "❌ RED FLAG (TIDAK SINKRON)"]
                df_lolos = df_hasil[df_hasil["Status"] == "✅ TERVERIFIKASI"]
                
                st.error(f"🚨 Ditemukan {len(df_gagal)} klaim berisiko (Red Flag) yang visualnya lemah/tidak ada.")
                st.dataframe(df_gagal, use_container_width=True)
                
                st.success(f"✅ Ditemukan {len(df_lolos)} klaim yang tervalidasi dengan dokumentasi.")
                with st.expander("Lihat Detail Klaim Terverifikasi"):
                    st.dataframe(df_lolos, use_container_width=True)
                
                st.warning("**KEPUTUSAN:** Jangan tandatangani progress sebelum item 'RED FLAG' diklarifikasi ulang dengan kondisi fisik di lapangan.")
            else:
                st.info("Tidak ditemukan frasa pekerjaan yang dapat dianalisis dari format tabel PDF ini.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Menunggu input data. Silakan unggah kedua dokumen PDF untuk mengaktifkan mesin audit.")

# Footer utilitarian
st.markdown("---")
st.caption("Sistem dirancang untuk standar presisi absolut. Hasil algoritma adalah rekomendasi administratif.")
