import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
from PIL import Image
from datetime import datetime

# Konfigurasi Halaman (Optimasi Handphone)
st.set_page_config(page_title="Audit Forensik PHTC", page_icon="⚖️", layout="wide")

# Tema Profesional
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Sistem Audit Forensik & Verifikasi Material")
st.caption("Standard Operational Protocol: Aurelius Vishvakarma Precision Logic")
st.markdown("---")

# 1. SIDEBAR & INPUT
st.sidebar.header("Pusat Kendali Dokumen")
file_mingguan = st.sidebar.file_uploader("1. Laporan Mingguan (PDF)", type="pdf")
file_dokumentasi = st.sidebar.file_uploader("2. Laporan Dokumentasi (PDF)", type="pdf")

if not (file_mingguan and file_dokumentasi):
    st.info("Silakan unggah kedua dokumen PDF melalui sidebar untuk memulai audit forensik.")
    st.stop()

# 2. EKSEKUSI AUDIT
if st.sidebar.button("⚙️ JALANKAN AUDIT KOMPREHENSIF", use_container_width=True):
    
    # --- OUTPUT 1 & 4: LOG ANOMALI & VALIDASI SILANG ---
    st.header("🔍 Hasil Audit & Validasi Silang")
    
    with st.spinner("Menganalisis integritas data matematis..."):
        temuan_anomali = []
        ringkasan_progres = []
        
        with pdfplumber.open(file_mingguan) as pdf:
            # Iterasi halaman lampiran kemajuan fisik (biasanya di paruh kedua PDF)
            for i in range(len(pdf.pages)):
                tabel = pdf.pages[i].extract_table()
                if not tabel: continue
                
                for row in tabel:
                    try:
                        # Mendeteksi baris pekerjaan berdasarkan pola kolom (Volume/Bobot)
                        if row[1] and row[5] and row[8] and row[11]:
                            uraian = str(row[1]).replace('\n', ' ')
                            b_lalu = float(str(row[5]).replace(',', '.'))
                            b_ini = float(str(row[8]).replace(',', '.'))
                            klaim_total = float(str(row[11]).replace(',', '.'))
                            
                            hitungan_sistem = round(b_lalu + b_ini, 3)
                            deviasi = round(klaim_total - hitungan_sistem, 3)
                            
                            # Simpan untuk ringkasan
                            ringkasan_progres.append({"Pekerjaan": uraian, "Bobot": b_ini})
                            
                            if abs(deviasi) > 0.001:
                                temuan_anomali.append({
                                    "Item Pekerjaan": uraian,
                                    "Klaim Laporan": f"{klaim_total}%",
                                    "Hitungan Sistem": f"{hitungan_sistem}%",
                                    "Selisih desimal": deviasi
                                })
                    except: continue

    # Tampilkan Anomali (Output 1)
    if temuan_anomali:
        st.error(f"🚩 Ditemukan {len(temuan_anomali)} Ketidaksesuaian Perhitungan desimal!")
        st.table(pd.DataFrame(temuan_anomali))
    else:
        st.success("✅ Integritas Matematis: Sempurna (Tidak ditemukan deviasi angka).")

    st.markdown("---")

    # --- OUTPUT 2 & 3: MATRIKS KOMPARASI & METADATA ---
    st.header("🖼️ Analisis Forensik Bukti Material")
    
    with st.spinner("Mengekstrak bukti foto dan metadata asli..."):
        doc_foto = fitz.open(stream=file_dokumentasi.read(), filetype="pdf")
        total_img = 0
        metadata_report = []
        
        # Grid Foto (Output 2)
        cols = st.columns(2)
        
        for p_idx in range(len(doc_foto)):
            page = doc_foto[p_idx]
            img_list = page.get_images(full=True)
            
            for i_idx, img in enumerate(img_list):
                xref = img[0]
                base_img = doc_foto.extract_image(xref)
                img_bytes = base_img["image"]
                img_ext = base_img["ext"]
                
                # Render Foto
                image = Image.open(io.BytesIO(img_bytes))
                w, h = image.size
                
                if w > 150: # Filter logo/icon
                    total_img += 1
                    with cols[total_img % 2]:
                        st.image(image, caption=f"Bukti {total_img} (Hal {p_idx+1})", use_container_width=True)
                    
                    # Metadata Audit (Output 3)
                    metadata_report.append({
                        "ID Bukti": f"IMG_{total_img}",
                        "Sumber": f"Halaman {p_idx+1}",
                        "Dimensi Asli": f"{w}x{h} px",
                        "Format": img_ext.upper(),
                        "Indikasi": "Valid" if w > 500 else "Resolusi Rendah (Risiko Kompresi)"
                    })

    st.subheader("📋 Laporan Audit Metadata & Resolusi")
    st.dataframe(pd.DataFrame(metadata_report), use_container_width=True)

    st.markdown("---")

    # --- OUTPUT 5: DRAF BERITA ACARA TEMUAN ---
    st.header("📝 Draf Nota Dinas / Berita Acara Temuan")
    
    # Logika Rangkuman Eksekutif
    status_audit = "DITOLAK/REVISI" if temuan_anomali else "DISETUJUI"
    
    ba_text = f"""
    BERITA ACARA PEMERIKSAAN DOKUMEN (DESK AUDIT)
    -------------------------------------------
    PROYEK: REHABILITASI DAN RENOVASI MADRASAH PHTC KALSEL 6
    TANGGAL AUDIT: {datetime.now().strftime('%d-%m-%Y')}
    
    HASIL PEMERIKSAAN:
    1. Integritas Angka: {'Ditemukan Anomali desimal' if temuan_anomali else 'Valid'}
    2. Ketersediaan Bukti Fisik: Ditemukan {total_img} foto dokumentasi terekstrak.
    
    KESIMPULAN:
    Berdasarkan hasil audit sistem, laporan ini dinyatakan {status_audit} 
    untuk diproses ke tahap administrasi selanjutnya.
    
    CATATAN:
    - {f'Perbaiki selisih angka pada {len(temuan_anomali)} item pekerjaan.' if temuan_anomali else 'Dokumen konsisten secara matematis.'}
    - Pastikan foto resolusi rendah pada laporan visual diganti dengan file asli.
    """
    st.code(ba_text, language="text")
    st.download_button("📥 Unduh Draf Temuan Audit", ba_text, file_name="Draf_Temuan_Audit.txt")

