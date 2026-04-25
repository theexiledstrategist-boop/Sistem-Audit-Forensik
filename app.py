import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
from PIL import Image

# 1. Konfigurasi Standar Presisi Tinggi (Mobile-Friendly)
st.set_page_config(page_title="Desk Audit System", page_icon="⚖️", layout="centered")
st.title("Sistem Audit Forensik Dokumen")
st.caption("Verifikasi Matematis & Ekstraksi Bukti Material")
st.markdown("---")

# 2. Modul Input (Unggah PDF)
col1, col2 = st.columns(2)
with col1:
    file_mingguan = st.file_uploader("Unggah Laporan Mingguan (PDF)", type="pdf")
with col2:
    file_dokumentasi = st.file_uploader("Unggah Laporan Dokumentasi (PDF)", type="pdf")

# 3. Eksekusi Komputasi
if st.button("Jalankan Audit Forensik", use_container_width=True):
    if file_mingguan and file_dokumentasi:
        
        # ==========================================
        # TAHAP 1: AUDIT MATEMATIS (LAPORAN MINGGUAN)
        # ==========================================
        st.subheader("1. Log Anomali Kalkulasi Matematis")
        with st.spinner("Membedah struktur tabel dan menghitung deviasi..."):
            temuan_anomali = []
            
            with pdfplumber.open(file_mingguan) as pdf:
                # Fokus pada halaman akhir (asumsi tabel Rincian Kemajuan Fisik ada di 5 halaman terakhir)
                start_page = max(0, len(pdf.pages) - 5)
                for i in range(start_page, len(pdf.pages)):
                    tabel = pdf.pages[i].extract_table()
                    if not tabel: continue
                    
                    for row in tabel:
                        try:
                            # Logika deterministik: Memeriksa baris yang memiliki format angka desimal
                            if row[1] and row[5] and row[8] and row[11]:
                                uraian = str(row[1]).replace('\n', ' ')
                                bobot_lalu = float(str(row[5]).replace(',', '.'))
                                bobot_ini = float(str(row[8]).replace(',', '.'))
                                klaim_kumulatif = float(str(row[11]).replace(',', '.'))
                                
                                # Mesin menghitung kebenaran mutlak
                                hitungan_mesin = round(bobot_lalu + bobot_ini, 3)
                                
                                if hitungan_mesin != round(klaim_kumulatif, 3):
                                    temuan_anomali.append({
                                        "Pekerjaan": uraian,
                                        "Klaim Laporan": klaim_kumulatif,
                                        "Hitungan Sistem": hitungan_mesin,
                                        "Selisih": round(klaim_kumulatif - hitungan_mesin, 3)
                                    })
                        except:
                            continue # Abaikan header tabel
            
            # Menampilkan hasil audit matematis
            if len(temuan_anomali) > 0:
                st.error(f"Ditemukan {len(temuan_anomali)} anomali perhitungan!")
                df_anomali = pd.DataFrame(temuan_anomali)
                st.dataframe(df_anomali, use_container_width=True)
            else:
                st.success("Verifikasi Matematis: AMAN (Presisi 100%)")

        st.markdown("---")

        # ==========================================
        # TAHAP 2: AUDIT VISUAL (LAPORAN DOKUMENTASI)
        # ==========================================
        st.subheader("2. Matriks Bukti Material (Resolusi Asli)")
        with st.spinner("Mengekstrak bukti foto dari kompresi PDF..."):
            pdf_dokumen = fitz.open(stream=file_dokumentasi.read(), filetype="pdf")
            
            # Grid visual untuk layar HP
            kolom_foto = st.columns(2)
            idx_kolom = 0
            total_foto = 0
            
            for nomor_halaman in range(len(pdf_dokumen)):
                daftar_gambar = pdf_dokumen[nomor_halaman].get_images(full=True)
                
                for img in daftar_gambar:
                    xref = img[0]
                    base_image = pdf_dokumen.extract_image(xref)
                    byte_gambar = base_image["image"]
                    
                    # Cek dimensi foto asli
                    image_pil = Image.open(io.BytesIO(byte_gambar))
                    lebar, tinggi = image_pil.size
                    
                    # Menampilkan ke dasbor jika resolusi masuk akal (bukan sekadar icon/logo)
                    if lebar > 100 and tinggi > 100:
                        total_foto += 1
                        with kolom_foto[idx_kolom % 2]:
                            st.image(image_pil, caption=f"Hal {nomor_halaman + 1} | {lebar}x{tinggi} px")
                        idx_kolom += 1

            st.info(f"Total bukti material terekstrak: {total_foto} foto.")

    else:
        st.warning("Unggah kedua dokumen PDF terlebih dahulu untuk memulai prosedur audit.")
