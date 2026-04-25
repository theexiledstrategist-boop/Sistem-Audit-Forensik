import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
from PIL import Image
from datetime import datetime

# ==========================================
# KONFIGURASI SISTEM
# ==========================================
st.set_page_config(page_title="Audit Forensik PHTC", page_icon="⚖️", layout="wide")

st.title("🛡️ Sistem Audit Forensik & Verifikasi Material")
st.caption("Standard Operational Protocol: Presisi Absolut")
st.markdown("---")

# ==========================================
# MODUL INPUT (SIDEBAR)
# ==========================================
st.sidebar.header("Pusat Kendali Dokumen")
file_mingguan = st.sidebar.file_uploader("1. Laporan Mingguan (PDF)", type="pdf")
file_dokumentasi = st.sidebar.file_uploader("2. Laporan Dokumentasi (PDF)", type="pdf")

if not (file_mingguan and file_dokumentasi):
    st.info("Silakan unggah dokumen PDF Laporan Mingguan dan Dokumentasi melalui menu di samping untuk memulai audit.")
    st.stop()

# ==========================================
# MESIN EKSEKUSI UTAMA
# ==========================================
if st.sidebar.button("⚙️ JALANKAN AUDIT KOMPREHENSIF", use_container_width=True):
    
    # 1. MENYADAP TEKS DOKUMENTASI (UNTUK VALIDASI SILANG)
    teks_dokumentasi_full = ""
    try:
        doc_foto = fitz.open(stream=file_dokumentasi.read(), filetype="pdf")
        for page in doc_foto:
            teks_dokumentasi_full += page.get_text("text").lower()
        # Mengembalikan pointer file stream agar bisa dibaca ulang untuk ekstrak gambar nanti
        file_dokumentasi.seek(0) 
    except Exception as e:
        st.error(f"Gagal membaca PDF Dokumentasi: {e}")

    # 2. AUDIT MATEMATIS & VALIDASI SILANG
    st.header("🔍 Hasil Audit & Validasi Silang (Klaim vs Bukti)")
    
    temuan_anomali = []
    laporan_validasi_silang = []
    
    with st.spinner("Menganalisis integritas angka dan mencocokkan bukti lapangan..."):
        try:
            with pdfplumber.open(file_mingguan) as pdf:
                # Fokus ke lampiran akhir tabel progres
                start_page = max(0, len(pdf.pages) - 10) 
                for i in range(start_page, len(pdf.pages)):
                    tabel = pdf.pages[i].extract_table()
                    if not tabel: continue
                    
                    for row in tabel:
                        try:
                            # Pastikan baris memiliki data di kolom matriks (Uraian, %Lalu, %Ini, %Total)
                            if row[1] and row[5] and row[8] and row[11]:
                                uraian = str(row[1]).replace('\n', ' ').strip()
                                
                                # Membersihkan string angka dan konversi ke format komputasi
                                val_lalu = str(row[5]).replace(',', '.').strip()
                                val_ini = str(row[8]).replace(',', '.').strip()
                                val_total = str(row[11]).replace(',', '.').strip()
                                
                                # Filter validasi: melewati baris header huruf
                                if not val_lalu.replace('.','',1).isdigit(): continue
                                
                                b_lalu = float(val_lalu)
                                b_ini = float(val_ini)
                                klaim_total = float(val_total)
                                
                                # --- A. DETEKSI ANOMALI MATEMATIS ---
                                hitungan_sistem = round(b_lalu + b_ini, 3)
                                deviasi = round(klaim_total - hitungan_sistem, 3)
                                
                                if abs(deviasi) > 0.001:
                                    temuan_anomali.append({
                                        "Pekerjaan": uraian,
                                        "Klaim Laporan": f"{klaim_total}%",
                                        "Hitungan Sistem": f"{hitungan_sistem}%",
                                        "Selisih Deviasi": deviasi
                                    })
                                
                                # --- B. LOGIKA VALIDASI SILANG MUTLAK ---
                                # Jika ada progres minggu ini (> 0%), wajib terlacak di teks PDF Dokumentasi
                                if b_ini > 0:
                                    # Mengambil 2 kata kunci awal (misal: "Pekerjaan Pasangan" -> "pekerjaan pasangan")
                                    kata_kunci = uraian.lower().split()[:2] 
                                    keyword_pencarian = " ".join(kata_kunci)
                                    
                                    if keyword_pencarian in teks_dokumentasi_full:
                                        status_bukti = "✅ Teks Bukti Ditemukan"
                                    else:
                                        status_bukti = "❌ BUKTI LAPANGAN TIDAK ADA!"
                                    
                                    laporan_validasi_silang.append({
                                        "Item Pekerjaan (Progres > 0%)": uraian,
                                        "Klaim Penambahan": f"+{b_ini}%",
                                        "Status Laporan Visual": status_bukti
                                    })
                        except Exception:
                            continue # Mengabaikan error pada baris spesifik dan lanjut ke baris berikutnya
        except Exception as e:
            st.error(f"Gagal membedah matriks tabel Laporan Mingguan: {e}")

    # Render Output 1: Anomali Matematika
    st.subheader("1. Log Anomali Kalkulasi Matematis")
    if temuan_anomali:
        st.error(f"🚩 Ditemukan {len(temuan_anomali)} baris dengan perhitungan desimal yang cacat secara administratif!")
        st.table(pd.DataFrame(temuan_anomali))
    else:
        st.success("✅ Integritas Matematis: Sempurna (Tidak ditemukan deviasi angka di seluruh tabel).")

    # Render Output 4: Validasi Silang
    st.subheader("2. Rapor Validasi Silang (Kesesuaian Item Pekerjaan & Keterangan Laporan Visual)")
    if laporan_validasi_silang:
        df_validasi = pd.DataFrame(laporan_validasi_silang)
        # Mewarnai blok merah absolut untuk pekerjaan tanpa bukti
        st.dataframe(df_validasi.style.applymap(
            lambda x: 'background-color: #ffcccc; color: red' if x == "❌ BUKTI LAPANGAN TIDAK ADA!" else '', 
            subset=['Status Laporan Visual']
        ), use_container_width=True)
    else:
        st.info("Tidak ada penambahan progres (>0%) minggu ini yang perlu divalidasi silang.")

    st.markdown("---")

    # 3. AUDIT FORENSIK VISUAL (FOTO & METADATA)
    st.header("🖼️ 3. Analisis Forensik Bukti Material & Resolusi Asli")
    
    total_img = 0
    metadata_report = []
    
    with st.spinner("Mengekstrak bukti foto dari jerat kompresi PDF..."):
        try:
            doc_foto = fitz.open(stream=file_dokumentasi.read(), filetype="pdf")
            cols = st.columns(2)
            
            for p_idx in range(len(doc_foto)):
                page = doc_foto[p_idx]
                img_list = page.get_images(full=True)
                
                for img in img_list:
                    xref = img[0]
                    base_img = doc_foto.extract_image(xref)
                    img_bytes = base_img["image"]
                    img_ext = base_img["ext"]
                    
                    image = Image.open(io.BytesIO(img_bytes))
                    w, h = image.size
                    
                    # Filter resolusi: Mengabaikan logo PU/MK yang kecil
                    if w > 150: 
                        total_img += 1
                        with cols[total_img % 2]:
                            st.image(image, caption=f"Bukti {total_img} (Halaman {p_idx+1}) | Resolusi Asli: {w}x{h} px", use_container_width=True)
                        
                        metadata_report.append({
                            "ID Bukti Material": f"IMG_{total_img}",
                            "Lokasi Sumber": f"Halaman {p_idx+1}",
                            "Dimensi Piksel Asli": f"{w}x{h} px",
                            "Format": img_ext.upper(),
                            "Indikasi Audit": "Valid" if w > 500 else "⚠️ Peringatan: Resolusi Rendah (Diduga Kompresi/Potongan)"
                        })
        except Exception as e:
            st.error(f"Gagal mengekstrak foto dokumen: {e}")

    # Render Output 3: Tabel Metadata
    if metadata_report:
        st.subheader("📋 Matriks Metadata & Mutu Bukti Visual")
        st.dataframe(pd.DataFrame(metadata_report), use_container_width=True)

    st.markdown("---")

    # 4. DRAF BERITA ACARA OTOMATIS
    st.header("📝 4. Draf Nota Dinas / Berita Acara Temuan Audit")
    
    # Logika status berdasarkan temuan
    ada_pelanggaran_bukti = "❌ BUKTI LAPANGAN TIDAK ADA!" in [x["Status Laporan Visual"] for x in laporan_validasi_silang]
    status_audit = "DITOLAK / HARUS DIREVISI" if (temuan_anomali or ada_pelanggaran_bukti) else "DISETUJUI (VALID ADMINISTRATIF)"
    
    ba_text = f"""
BERITA ACARA PEMERIKSAAN DOKUMEN (DESK AUDIT)
-------------------------------------------
PROYEK          : REHABILITASI DAN RENOVASI MADRASAH PHTC KALSEL 6
TANGGAL AUDIT   : {datetime.now().strftime('%d-%m-%Y')}
SISTEM VALIDASI : Aurelius Vishvakarma Protocol

HASIL PEMERIKSAAN FORENSIK:
1. Integritas Angka Matematis   : {'Ditemukan Anomali Kalkulasi' if temuan_anomali else 'Sempurna / Valid Mutlak'}
2. Validasi Silang Bukti Progres: {'Ditemukan Klaim Progres Fiktif (Tanpa Bukti di Laporan Visual)' if ada_pelanggaran_bukti else 'Linear dengan Laporan Visual'}
3. Kuantitas Bukti Fisik        : Terekstrak {total_img} dokumen foto riil.

KESIMPULAN AUDIT:
Berdasarkan hasil ekstraksi komputasi deterministik, laporan ini dinyatakan:
>> {status_audit} <<

CATATAN TINDAK LANJUT:
- {'Perbaiki perhitungan matematis yang terindikasi mark-up/salah hitung.' if temuan_anomali else 'Dokumen konsisten secara matematis.'}
- {'Segera lampirkan bukti foto dan keterangan untuk pekerjaan yang diklaim naik minggu ini namun tidak ada visualnya.' if ada_pelanggaran_bukti else 'Klaim progres tertulis dan visual sejajar.'}
    """
    
    st.code(ba_text, language="text")
