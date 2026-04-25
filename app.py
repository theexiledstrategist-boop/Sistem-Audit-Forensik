import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
import re
from PIL import Image
from datetime import datetime

# ==========================================
# 1. KONFIGURASI SISTEM & UI
# ==========================================
st.set_page_config(page_title="Audit Forensik PHTC", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
   .main { background-color: #f0f2f6; }
   .metric-card { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
   .alert-danger { background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; font-weight: bold; border-left: 5px solid #dc3545;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MESIN LOGIKA (AURELIUS VISHVAKARMA PROTOCOL)
# ==========================================

def bersihkan_angka(teks):
    """Konversi format desimal/ribuan laporan (misal: 0,042 atau 1.200,5) ke Float komputasi"""
    if not teks or str(teks).strip().lower() in ['none', '']: return 0.0
    try:
        bersih = re.sub(r'[^\d,\.-]', '', str(teks))
        return float(bersih.replace(',', '.'))
    except:
        return 0.0

def deteksi_lokasi_madrasah(teks):
    """Mendeteksi transisi lokasi (MIS/MTSS) pada baris tabel"""
    match = re.search(r'(MIS|MTSS)\s+[A-Z0-9\s\'\-]+', str(teks).upper())
    return match.group(0).strip() if match else None

def ekstrak_inti_material(uraian):
    """
    NLP Sederhana: Membuang kata kerja administratif agar mesin tidak tertipu 
    oleh kata "Pekerjaan", "Lokasi", atau "Kegiatan". Hanya menyisakan material fisik.
    """
    uraian_bersih = re.sub(r'\(.*?\)', '', str(uraian).upper()) # Hapus teks dalam kurung
    kata_kunci = uraian_bersih.split()
    
    stop_words = {
        "PEKERJAAN", "PEMASANGAN", "PEMBUATAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", 
        "UNTUK", "DAN", "YANG", "DENGAN", "UKURAN", "REHABILITASI", "RENOVASI", 
        "BANGUNAN", "M2", "M3", "KG", "LITER", "UNIT", "BH", "TITIK"
    }
    
    # Ambil kata yang bukan stop words dan memiliki panjang lebih dari 2 huruf
    kata_inti = [w for w in kata_kunci if w not in stop_words and len(w) > 2]
    
    # Kembalikan 2 kata paling spesifik sebagai identitas material (misal: "ATAP METAL", "KERAMIK POLISH")
    return " ".join(kata_inti[:2])

# ==========================================
# 3. ANTARMUKA PENGGUNA (SIDEBAR)
# ==========================================
st.title("⚖️ Sistem Audit Forensik & Verifikasi Material")
st.caption("Protokol Pengawasan Deterministik - Kementerian Pekerjaan Umum")

with st.sidebar:
    st.header("📁 Brankas Dokumen")
    file_mingguan = st.file_uploader("1. Laporan Mingguan (PDF)", type="pdf")
    file_foto = st.file_uploader("2. Laporan Dokumentasi (PDF)", type="pdf")
    st.markdown("---")
    eksekusi = st.button("⚙️ JALANKAN AUDIT ABSOLUT", use_container_width=True)

if not (file_mingguan and file_foto):
    st.info("Sistem dalam posisi siaga. Silakan masukkan Laporan Mingguan dan Laporan Dokumentasi untuk memulai ekstraksi.")
    st.stop()

# ==========================================
# 4. PROSES EKSTRAKSI & AUDIT
# ==========================================
if eksekusi:
    
    # --- FASE 1: MENYADAP BUKTI VISUAL (PDF 2) ---
    with st.spinner("Memindai resolusi asli gambar dan mengekstrak teks dokumentasi per halaman..."):
        teks_dokumentasi_per_halaman = {} # Dictionary untuk menyimpan teks pada setiap indeks halaman
        galeri_foto =
        try:
            doc_foto = fitz.open(stream=file_foto.read(), filetype="pdf")
            for i in range(len(doc_foto)):
                halaman = doc_foto[i]
                # Simpan teks spesifik HANYA pada indeks halaman ini untuk menjaga konteks
                teks_dokumentasi_per_halaman[i+1] = halaman.get_text("text").upper()
                
                # Ekstrak gambar
                for img in halaman.get_images(full=True):
                    xref = img
                    base_img = doc_foto.extract_image(xref)
                    image = Image.open(io.BytesIO(base_img["image"]))
                    if image.width > 200: # Filter logo konsultan
                        galeri_foto.append({
                            "img": image, "hal": i+1, 
                            "res": f"{image.width}x{image.height} px"
                        })
            file_foto.seek(0)
        except Exception as e:
            st.error(f"Gagal membedah PDF Dokumentasi: {e}")
            st.stop()

    # --- FASE 2: MEMBEDAH TABEL PROGRES (PDF 1) ---
    log_validasi =
    log_anomali =
    lokasi_saat_ini = "LOKASI TIDAK TERIDENTIFIKASI"
    
    with st.spinner("Menjalankan filter isolasi halaman dan audit komputasi matematis..."):
        try:
            with pdfplumber.open(file_mingguan) as pdf:
                for page in pdf.pages:
                    teks_halaman = page.extract_text()
                    
                    # FILTER MUTLAK 1: Halaman WAJIB mengandung kata "KEMAJUAN FISIK"
                    if not teks_halaman or "KEMAJUAN FISIK" not in teks_halaman.upper():
                        continue
                    
                    tabel = page.extract_table()
                    if not tabel: continue
                    
                    for row in tabel:
                        # FILTER MUTLAK 2: Tabel progres utama memiliki banyak kolom (biasanya >= 12)
                        if len(row) < 12: continue
                        
                        uraian = str(row[1]).replace('\n', ' ').strip()
                        if not uraian or uraian.lower() == 'none': continue

                        # Konteks Lokasi (Location Awareness)
                        deteksi_lok = deteksi_lokasi_madrasah(uraian)
                        if deteksi_lok:
                            lokasi_saat_ini = deteksi_lok
                            
                        # Ekstraksi Angka
                        raw_ini = str(row[2])
                        if not any(c.isdigit() for c in raw_ini): continue # Lewati baris teks murni
                        
                        b_lalu = bersihkan_angka(row[3])
                        b_ini = bersihkan_angka(raw_ini)
                        b_total = bersihkan_angka(row[4])
                        
                        if b_ini > 0:
                            # 1. Audit Forensik Angka Matematika
                            hitung_sistem = round(b_lalu + b_ini, 3)
                            deviasi = round(b_total - hitung_sistem, 3)
                            
                            if abs(deviasi) > 0.001:
                                log_anomali.append({
                                    "Lokasi": lokasi_saat_ini, "Item Pekerjaan": uraian,
                                    "Klaim Kumulatif": b_total, "Hasil Sistem": hitung_sistem, "Selisih": deviasi
                                })

                            # 2. Validasi Silang Ketat (Anti-Palsu) - Halaman ke Halaman
                            material_spesifik = ekstrak_inti_material(uraian)
                            
                            # Ambil nama lokasi, pastikan tidak terpotong menjadi 1 karakter (misal "MIS A" jadi "A")
                            kata_kunci_lokasi = lokasi_saat_ini.replace("MIS ", "").replace("MTSS ", "").strip()
                            if len(kata_kunci_lokasi) < 3: 
                                kata_kunci_lokasi = lokasi_saat_ini # Gunakan nama utuh jika hasil filter terlalu pendek
                            
                            lokasi_ditemukan = False
                            material_ditemukan = False
                            status_akhir = "❌ BUKTI DITOLAK"
                            alasan = "Lokasi dan Material tidak ditemukan di laporan foto."

                            # Evaluasi Forensik: Lokasi dan Material HARUS ada di DALAM HALAMAN YANG SAMA
                            for hal, teks_hal in teks_dokumentasi_per_halaman.items():
                                match_lokasi = kata_kunci_lokasi in teks_hal if kata_kunci_lokasi else False
                                match_material = material_spesifik in teks_hal if material_spesifik else False
                                
                                if match_lokasi and match_material:
                                    lokasi_ditemukan = True
                                    material_ditemukan = True
                                    status_akhir = "✅ VALID"
                                    alasan = f"Terverifikasi di Hal {hal}: '{material_spesifik}' pada '{kata_kunci_lokasi}'."
                                    break # Langsung berhenti memindai karena bukti sah ditemukan berdampingan
                                elif match_lokasi:
                                    lokasi_ditemukan = True
                                elif match_material:
                                    material_ditemukan = True

                            # Penentuan alasan penolakan spesifik jika gagal
                            if status_akhir!= "✅ VALID":
                                if not lokasi_ditemukan:
                                    alasan = f"Lokasi '{kata_kunci_lokasi}' tidak ditemukan di laporan foto."
                                elif not material_ditemukan:
                                    alasan = f"Material '{material_spesifik}' tidak berdampingan dengan lokasi '{kata_kunci_lokasi}'."
                                    
                            log_validasi.append({
                                "Madrasah": lokasi_saat_ini, "Pekerjaan": uraian, 
                                "Progres": f"+{b_ini}%", "Status": status_akhir, "Analisis Mesin": alasan
                            })
        except Exception as e:
            st.error(f"Gagal memproses tabel Laporan Mingguan: {e}")

    # ==========================================
    # 5. TAMPILAN DASBOR PENGAWASAN
    # ==========================================
    
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.info(f"📊 **Total Item Progres:** {len(log_validasi)}")
    c2.warning(f"⚠️ **Anomali Hitungan:** {len(log_anomali)}")
    c3.error(f"🚨 **Item Tanpa Bukti:** {len(])}")
    st.markdown("---")

    # TABEL UTAMA: VALIDASI SILANG
    st.subheader("🔍 Matriks Validasi Progres vs Bukti Visual")
    if log_validasi:
        df_val = pd.DataFrame(log_validasi)
        
        # Fungsi warna dinamis pada kolom Status
        def pewarnaan_status(v):
            if '❌' in str(v):
                return 'background-color: #ffcccc; color: #a94442; font-weight:bold'
            elif '✅' in str(v):
                return 'background-color: #dff0d8; color: #3c763d'
            return ''

        st.dataframe(df_val.style.map(pewarnaan_status, subset=), use_container_width=True)
    else:
        st.success("Tidak ada item dengan penambahan progres (0%) yang perlu divalidasi silang.")

    # TABEL KEDUA: ANOMALI ANGKA
    if log_anomali:
        st.markdown('<div class="alert-danger">⚠️ TERDETEKSI KESALAHAN PENJUMLAHAN BOBOT PADA DOKUMEN!</div>', unsafe_allow_html=True)
        st.table(pd.DataFrame(log_anomali))

    # GALERI BUKTI FISIK
    st.subheader("🖼️ Ekstraksi Bukti Material & Meta-Resolusi")
    if galeri_foto:
        g_cols = st.columns(4)
        for idx, fto in enumerate(galeri_foto[:16]): # Batasi 16 gambar awal agar render cepat
            with g_cols[idx % 4]:
                st.image(fto["img"], caption=f"Hal {fto['hal']} | {fto['res']}", use_container_width=True)
                if int(fto['res'].split('x')) < 400:
                    st.caption("⚠️ Resolusi Terindikasi Manipulasi (Crop)")
    else:
        st.info("Tidak ada gambar terdeteksi / semua gambar hanyalah logo beresolusi rendah.")

    # BERITA ACARA OTOMATIS
    st.subheader("📝 Draf Keputusan Audit Pejabat Pembuat Komitmen")
    status_dokumen = "DITOLAK / REVISI TOTAL" if (log_anomali or len(]) > 0) else "DISETUJUI"
    
    teks_ba = f"""
MEMO HASIL DESK AUDIT DOKUMEN
--------------------------------------------------
TANGGAL PEMERIKSAAN : {datetime.now().strftime('%d %B %Y')}
LOKASI PROYEK       : MADRASAH PHTC KALSEL
STATUS VERIFIKASI   : {status_dokumen}

EVALUASI KOMPUTASI:
1. Integritas Data Administratif : {'Terdapat ' + str(len(log_anomali)) + ' baris pekerjaan dengan hitungan yang dimanipulasi/salah.' if log_anomali else 'Valid tanpa deviasi angka deterministik.'}
2. Otentikasi Bukti Lapangan     : {'Terdapat ' + str(len(])) + ' item yang diklaim progresnya namun fiktif/tidak memiliki bukti foto pada lokasi yang sesuai.' if] else 'Seluruh progres memiliki dukungan visual yang sesuai.'}

TINDAK LANJUT:
Dokumen ini dikembalikan kepada pihak Kontraktor Pelaksana dan Manajemen Konstruksi. 
Segera perbaiki anomali desimal dan lampirkan bukti material spesifik di lokasi yang benar sebelum proses terminasi dilanjutkan.
--------------------------------------------------
    """
    st.code(teks_ba, language="text")
