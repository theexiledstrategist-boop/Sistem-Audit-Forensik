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

st.markdown('''
    <style>
   .main { background-color: #f0f2f6; }
   .metric-card { background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
   .alert-danger { background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; font-weight: bold; border-left: 5px solid #dc3545;}
    </style>
    ''', unsafe_allow_html=True)

# ==========================================
# 2. MESIN LOGIKA (AURELIUS VISHVAKARMA PROTOCOL)
# ==========================================

def bersihkan_angka(teks):
    if pd.isna(teks) or teks is None or str(teks).strip().lower() in ('none', '', '-'): 
        return 0.0
    try:
        bersih = re.sub(r'[^\d,\.-]', '', str(teks))
        return float(bersih.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def deteksi_lokasi_madrasah(teks):
    match = re.search(r'(MIS|MTSS)\s+[A-Z0-9\s\'\-]+', str(teks).upper())
    return match.group(0).strip() if match else None

def ekstrak_inti_material(uraian):
    uraian_bersih = re.sub(r'\(.*?\)', '', str(uraian).upper())
    kata_kunci = uraian_bersih.split()
    
    stop_words = {
        "PEKERJAAN", "PEMASANGAN", "PEMBUATAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", 
        "UNTUK", "DAN", "YANG", "DENGAN", "UKURAN", "REHABILITASI", "RENOVASI", 
        "BANGUNAN", "M2", "M3", "KG", "LITER", "UNIT", "BH", "TITIK", "LOKASI", "KEGIATAN"
    }
    
    kata_inti = list()
    for w in kata_kunci:
        if w not in stop_words and len(w) > 2:
            kata_inti.append(w)
            
    return " ".join(kata_inti)

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
        teks_dokumentasi_per_halaman = dict() 
        galeri_foto = list()
        try:
            doc_foto = fitz.open(stream=file_foto.read(), filetype="pdf")
            for i in range(len(doc_foto)):
                halaman = doc_foto.load_page(i)
                teks_dokumentasi_per_halaman.update({i+1: halaman.get_text("text").upper()})
                
                for img in halaman.get_images(full=True):
                    # Casting aman untuk menarik id resolusi menghindari kurung siku
                    xref = list(img).pop(0)
                    base_img = doc_foto.extract_image(xref)
                    image = Image.open(io.BytesIO(base_img.get("image")))
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
    log_validasi = list()
    log_anomali = list()
    lokasi_saat_ini = "LOKASI TIDAK TERIDENTIFIKASI"
    
    with st.spinner("Menjalankan filter isolasi halaman dan audit komputasi matematis..."):
        try:
            with pdfplumber.open(file_mingguan) as pdf:
                for page in pdf.pages:
                    teks_halaman = page.extract_text()
                    
                    # FILTER MUTLAK 1
                    if not teks_halaman or "KEMAJUAN FISIK" not in teks_halaman.upper():
                        continue
                    
                    tabel = page.extract_table({"vertical_strategy": "lines", "horizontal_strategy": "lines"})
                    if not tabel: 
                        tabel = page.extract_table()
                        
                    if not tabel: continue
                    
                    for row in tabel:
                        # FILTER MUTLAK 2
                        if len(row) < 12: continue
                        
                        # Menarik data menggunakan getter aman (menghindari kurung siku)
                        uraian = str(row.__getitem__(1)).replace('\n', ' ').strip()
                        if not uraian or uraian.lower() in ('none', '', 'nan'): continue

                        deteksi_lok = deteksi_lokasi_madrasah(uraian)
                        if deteksi_lok:
                            lokasi_saat_ini = deteksi_lok
                            
                        raw_ini = str(row.__getitem__(8))
                        if not any(c.isdigit() for c in raw_ini): continue 
                        
                        b_lalu = bersihkan_angka(row.__getitem__(5))
                        b_ini = bersihkan_angka(raw_ini)
                        b_total = bersihkan_angka(row.__getitem__(11))
                        
                        if b_ini > 0:
                            # 1. Audit Forensik Angka Matematika
                            hitung_sistem = round(b_lalu + b_ini, 3)
                            deviasi = round(b_total - hitung_sistem, 3)
                            
                            if abs(deviasi) > 0.001:
                                log_anomali.append({
                                    "Lokasi": lokasi_saat_ini, "Item Pekerjaan": uraian,
                                    "Klaim Kumulatif": b_total, "Hasil Sistem": hitung_sistem, "Selisih": deviasi
                                })

                            # 2. Validasi Silang Ketat (Anti-Palsu)
                            material_spesifik = ekstrak_inti_material(uraian)
                            
                            kata_kunci_lokasi = lokasi_saat_ini.replace("MIS ", "").replace("MTSS ", "").strip()
                            if len(kata_kunci_lokasi) < 3: 
                                kata_kunci_lokasi = lokasi_saat_ini 
                            
                            lokasi_ditemukan = False
                            material_ditemukan = False
                            status_akhir = "❌ BUKTI DITOLAK"
                            alasan = "Lokasi dan Material tidak ditemukan di laporan foto."

                            material_list = material_spesifik.split()
                            
                            for hal, teks_hal in teks_dokumentasi_per_halaman.items():
                                match_lokasi = kata_kunci_lokasi in teks_hal if kata_kunci_lokasi else False
                                
                                match_material = False
                                if len(material_list) > 0:
                                    match_material = any(m in teks_hal for m in material_list)
                                
                                if match_lokasi and match_material:
                                    lokasi_ditemukan = True
                                    material_ditemukan = True
                                    status_akhir = "✅ VALID"
                                    alasan = f"Terverifikasi di Hal {hal}: Material terkait '{material_spesifik}' pada '{kata_kunci_lokasi}'."
                                    break 
                                elif match_lokasi:
                                    lokasi_ditemukan = True
                                elif match_material:
                                    material_ditemukan = True

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
    
    # Pengumpulan item fiktif secara aman
    item_fiktif = list()
    for x in log_validasi:
        if '❌' in x.get("Status", ""):
            item_fiktif.append(x)
    
    c1, c2, c3 = st.columns(3)
    c1.info(f"📊 **Total Item Progres:** {len(log_validasi)}")
    c2.warning(f"⚠️ **Anomali Hitungan:** {len(log_anomali)}")
    c3.error(f"🚨 **Item Tanpa Bukti:** {len(item_fiktif)}")
    st.markdown("---")

    st.subheader("🔍 Matriks Validasi Progres vs Bukti Visual")
    if log_validasi:
        df_val = pd.DataFrame(log_validasi)
        
        def pewarnaan_status(v):
            if '❌' in str(v):
                return 'background-color: #ffcccc; color: #a94442; font-weight:bold'
            elif '✅' in str(v):
                return 'background-color: #dff0d8; color: #3c763d'
            return ''

        # Parsing warna dengan gaya string untuk menghindari error parser Streamlit
        st.dataframe(df_val.style.map(pewarnaan_status, subset="Status"), use_container_width=True)
    else:
        st.success("Tidak ada item dengan penambahan progres (0%) yang perlu divalidasi silang.")

    if log_anomali:
        st.markdown('<div class="alert-danger">⚠️ TERDETEKSI KESALAHAN PENJUMLAHAN BOBOT PADA DOKUMEN!</div>', unsafe_allow_html=True)
        st.table(pd.DataFrame(log_anomali))

    st.subheader("🖼️ Ekstraksi Bukti Material & Meta-Resolusi")
    if galeri_foto:
        batas_render = 16
        g_cols = st.columns(4)
        for idx, fto in enumerate(galeri_foto):
            if idx >= batas_render:
                break
            with g_cols[idx % 4]:
                st.image(fto.get("img"), caption=f"Hal {fto.get('hal')} | {fto.get('res')}", use_container_width=True)
                # Validasi resolusi crop/fiktif
                if int(fto.get('res').split('x').pop(0)) < 400:
                    st.caption("⚠️ Resolusi Terindikasi Manipulasi (Crop)")
    else:
        st.info("Tidak ada gambar terdeteksi / semua gambar hanyalah logo beresolusi rendah.")

    st.subheader("📝 Draf Keputusan Audit Pejabat Pembuat Komitmen")
    status_dokumen = "DITOLAK / REVISI TOTAL" if (log_anomali or len(item_fiktif) > 0) else "DISETUJUI"
    
    teks_integritas = f"Terdapat {len(log_anomali)} baris pekerjaan dengan hitungan yang dimanipulasi/salah." if log_anomali else "Valid tanpa deviasi angka deterministik."
    teks_otentikasi = f"Terdapat {len(item_fiktif)} item yang diklaim progresnya namun fiktif/tidak memiliki bukti foto pada lokasi yang sesuai." if item_fiktif else "Seluruh progres memiliki dukungan visual yang sesuai."
    
    teks_ba = f'''
MEMO HASIL DESK AUDIT DOKUMEN
--------------------------------------------------
TANGGAL PEMERIKSAAN : {datetime.now().strftime('%d %B %Y')}
LOKASI PROYEK       : MADRASAH PHTC KALSEL
STATUS VERIFIKASI   : {status_dokumen}

EVALUASI KOMPUTASI:
1. Integritas Data Administratif : {teks_integritas}
2. Otentikasi Bukti Lapangan     : {teks_otentikasi}

TINDAK LANJUT:
Dokumen ini dikembalikan kepada pihak Kontraktor Pelaksana dan Manajemen Konstruksi. 
Segera perbaiki anomali desimal dan lampirkan bukti material spesifik di lokasi yang benar sebelum proses terminasi dilanjutkan.
--------------------------------------------------
    '''
    st.code(teks_ba.strip(), language="text")
