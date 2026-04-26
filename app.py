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
   .alert-danger { background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; font-weight: bold; border-left: 5px solid #dc3545;}
   .alert-success { background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; font-weight: bold; border-left: 5px solid #28a745;}
    </style>
    ''', unsafe_allow_html=True)

# ==========================================
# 2. HELPER & NLP SEDERHANA
# ==========================================

def bersihkan_angka(teks):
    """Konversi format angka ke Float."""
    if pd.isna(teks) or teks is None or str(teks).strip().lower() in ('none', '', '-'): 
        return 0.0
    try:
        bersih = re.sub(r'[^\d,\.-]', '', str(teks))
        return float(bersih.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def deteksi_lokasi_madrasah(teks):
    """Mendeteksi lokasi berdasarkan keyword MIS/MTSS."""
    match = re.search(r'(MIS|MTSS)\s+[A-Z0-9\s\'\-]+', str(teks).upper())
    return match.group(0).strip() if match else None

def ekstrak_inti_material(uraian):
    """Filter NLP: menyisakan material benda mati saja."""
    uraian_bersih = re.sub(r'\(.*?\)', '', str(uraian).upper())
    kata_kunci = uraian_bersih.split()
    
    stop_words = set((
        "PEKERJAAN", "PEMASANGAN", "PEMBUATAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", 
        "UNTUK", "DAN", "YANG", "DENGAN", "UKURAN", "REHABILITASI", "RENOVASI", 
        "BANGUNAN", "M2", "M3", "KG", "LITER", "UNIT", "BH", "TITIK", "LOKASI", "KEGIATAN"
    ))
    
    kata_inti = list()
    for w in kata_kunci:
        if w not in stop_words and len(w) > 2:
            kata_inti.append(w)
            
    return " ".join(kata_inti)

# ==========================================
# 3. ANTARMUKA PENGGUNA (SIDEBAR)
# ==========================================
st.title("⚖️ Sistem Audit Forensik Bertahap")
st.caption("Fase 1: Uji Laporan & Matematika | Fase 2: Cross-Check Visual")

with st.sidebar:
    st.header("📁 Brankas Dokumen")
    file_mingguan = st.file_uploader("1. Laporan Mingguan (PDF)", type="pdf")
    file_foto = st.file_uploader("2. Laporan Dokumentasi (PDF)", type="pdf")
    st.markdown("---")
    eksekusi = st.button("⚙️ JALANKAN AUDIT TAHAP DEMI TAHAP", use_container_width=True)

if not (file_mingguan and file_foto):
    st.info("Sistem siaga. Masukkan Laporan Mingguan dan Foto untuk memulai ekstraksi berurutan.")
    st.stop()

# ==========================================
# 4. EKSEKUSI PIPELINE (ALUR BERURUTAN)
# ==========================================
if eksekusi:
    
    # Variabel Penyimpanan Data Tahap 1
    pekerjaan_valid_matematika = list() # Rangkuman progress yang lolos uji angka
    log_anomali_matematika = list()     # Rangkuman progress dengan angka manipulatif
    lokasi_saat_ini = "LOKASI_TIDAK_DIKETAHUI"

    # ------------------------------------------------------------------
    # TAHAP 1: BACA LAPORAN MINGGUAN & BUAT RANGKUMAN (UJI MATEMATIKA)
    # ------------------------------------------------------------------
    st.markdown("### 📊 TAHAP 1: Ekstraksi Rangkuman Pekerjaan & Audit Angka (PDF 1)")
    
    with st.spinner("Membaca Laporan Mingguan dan mengevaluasi kalkulasi matematika..."):
        try:
            with pdfplumber.open(file_mingguan) as pdf:
                for page in pdf.pages:
                    teks_halaman = page.extract_text()
                    
                    if not teks_halaman or "KEMAJUAN FISIK" not in teks_halaman.upper():
                        continue
                    
                    tabel = page.extract_table({"vertical_strategy": "lines", "horizontal_strategy": "lines"})
                    if not tabel: 
                        tabel = page.extract_table()
                    if not tabel: continue
                    
                    for row in tabel:
                        if len(row) < 12: continue
                        
                        # Ambil uraian pekerjaan dengan aman tanpa kurung siku kosong
                        uraian = str(row.__getitem__(1)).replace('\n', ' ').strip()
                        if not uraian or uraian.lower() in ('none', '', 'nan'): continue

                        # Update konteks lokasi jika menemukan header lokasi
                        deteksi_lok = deteksi_lokasi_madrasah(uraian)
                        if deteksi_lok:
                            lokasi_saat_ini = deteksi_lok
                            
                        raw_ini = str(row.__getitem__(8))
                        if not any(c.isdigit() for c in raw_ini): continue 
                        
                        b_lalu = bersihkan_angka(row.__getitem__(5))
                        b_ini = bersihkan_angka(raw_ini)
                        b_total = bersihkan_angka(row.__getitem__(11))
                        
                        # HANYA PROSES YANG ADA KEMAJUAN MINGGU INI (> 0%)
                        if b_ini > 0:
                            hitung_sistem = round(b_lalu + b_ini, 3)
                            deviasi = round(b_total - hitung_sistem, 3)
                            
                            # Jika matematika salah, masukkan ke anomali dan JANGAN dilanjutkan ke uji foto
                            if abs(deviasi) > 0.001:
                                log_anomali_matematika.append({
                                    "Lokasi": lokasi_saat_ini, 
                                    "Item Pekerjaan": uraian,
                                    "Klaim Total (%)": b_total, 
                                    "Hasil Uji Sistem (%)": hitung_sistem, 
                                    "Selisih Deviasi": deviasi
                                })
                            # Jika matematika benar, masukkan ke daftar rangkuman siap divalidasi silang
                            else:
                                pekerjaan_valid_matematika.append({
                                    "Lokasi": lokasi_saat_ini, 
                                    "Pekerjaan": uraian, 
                                    "Progres Minggu Ini": b_ini
                                })
        except Exception as e:
            st.error(f"Gagal membaca PDF Mingguan: {e}")
            st.stop()

    # Tampilkan Hasil Tahap 1
    if log_anomali_matematika:
        st.markdown('<div class="alert-danger">🚨 Peringatan! Ditemukan Pekerjaan dengan Rekayasa/Kesalahan Angka:</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(log_anomali_matematika), use_container_width=True)
    else:
        st.markdown('<div class="alert-success">✅ Laporan Bersih! Tidak ada kesalahan penjumlahan angka matematis.</div>', unsafe_allow_html=True)

    if len(pekerjaan_valid_matematika) == 0:
        st.warning("Tidak ada pekerjaan dengan progres > 0% yang memenuhi syarat untuk divalidasi fotonya. Proses dihentikan.")
        st.stop()
        
    st.info(f"Terdapat **{len(pekerjaan_valid_matematika)}** item pekerjaan dengan angka valid yang akan dilanjutkan ke pengecekan bukti visual.")
    st.dataframe(pd.DataFrame(pekerjaan_valid_matematika), use_container_width=True)
    st.markdown("---")

    # ------------------------------------------------------------------
    # TAHAP 2: VALIDASI SILANG KE BUKTI FOTO (PDF 2)
    # ------------------------------------------------------------------
    st.markdown("### 📸 TAHAP 2: Pencocokan Rangkuman ke Laporan Dokumentasi (PDF 2)")
    
    hasil_validasi_akhir = list()
    galeri_foto = list()
    
    with st.spinner("Mengekstrak dan membedah dokumen foto berdasarkan daftar Rangkuman Tahap 1..."):
        teks_dokumentasi_per_halaman = dict() 
        try:
            doc_foto = fitz.open(stream=file_foto.read(), filetype="pdf")
            for i in range(len(doc_foto)):
                halaman = doc_foto.load_page(i)
                teks_dokumentasi_per_halaman.update({i+1: halaman.get_text("text").upper()})
                
                # Ekstrak Metadata Gambar Resolusi (Sample Visual)
                for img in halaman.get_images(full=True):
                    xref = list(img).pop(0)
                    base_img = doc_foto.extract_image(xref)
                    image = Image.open(io.BytesIO(base_img.get("image")))
                    if image.width > 200: # Buang logo kementerian
                        galeri_foto.append({
                            "img": image, "hal": i+1, "res": f"{image.width}x{image.height}"
                        })
            file_foto.seek(0)
        except Exception as e:
            st.error(f"Gagal membedah PDF Dokumentasi: {e}")
            st.stop()

        # Proses pencocokan (Cross-Validation) dengan data Valid dari Tahap 1
        for pk in pekerjaan_valid_matematika:
            uraian = pk.get("Pekerjaan")
            lokasi = pk.get("Lokasi")
            b_ini = pk.get("Progres Minggu Ini")
            
            material_spesifik = ekstrak_inti_material(uraian)
            
            # Ambil keyword lokasi secara dinamis
            kata_kunci_lokasi = lokasi.replace("MIS ", "").replace("MTSS ", "").strip()
            if len(kata_kunci_lokasi) < 3: 
                kata_kunci_lokasi = lokasi 
            
            lokasi_ditemukan = False
            material_ditemukan = False
            status_akhir = "❌ BUKTI DITOLAK"
            alasan = "Lokasi dan Material tidak ditemukan bersamaan di satu halaman foto."

            material_list = material_spesifik.split()
            
            # Evaluasi per halaman
            for hal, teks_hal in teks_dokumentasi_per_halaman.items():
                match_lokasi = kata_kunci_lokasi in teks_hal if kata_kunci_lokasi else False
                
                match_material = False
                if len(material_list) > 0:
                    match_material = any(m in teks_hal for m in material_list)
                
                if match_lokasi and match_material:
                    lokasi_ditemukan = True
                    material_ditemukan = True
                    status_akhir = "✅ VALID"
                    alasan = f"Ditemukan di Halaman {hal} (Lokasi & Material Cocok)"
                    break 
                elif match_lokasi:
                    lokasi_ditemukan = True
                elif match_material:
                    material_ditemukan = True

            # Alasan kegagalan lebih detail
            if status_akhir!= "✅ VALID":
                if not lokasi_ditemukan:
                    alasan = f"Lokasi '{kata_kunci_lokasi}' tidak ditemukan di PDF foto."
                elif not material_ditemukan:
                    alasan = f"Material '{material_spesifik}' tidak berdampingan dengan lokasi '{kata_kunci_lokasi}'."
                    
            hasil_validasi_akhir.append({
                "Lokasi Proyek": lokasi, 
                "Item Pekerjaan": uraian, 
                "Progres (%)": f"+{b_ini}%", 
                "Status Pembuktian": status_akhir, 
                "Catatan Mesin": alasan
            })

    # Tampilkan Hasil Akhir Validasi
    df_hasil_akhir = pd.DataFrame(hasil_validasi_akhir)
    
    def pewarnaan_status(v):
        if '❌' in str(v):
            return 'background-color: #ffcccc; color: #a94442; font-weight:bold'
        elif '✅' in str(v):
            return 'background-color: #dff0d8; color: #3c763d'
        return ''

    # Gunakan map secara aman untuk pandas dataframe styler
    try:
        styled_df = df_hasil_akhir.style.map(pewarnaan_status, subset="Status Pembuktian")
    except:
        styled_df = df_hasil_akhir.style.applymap(pewarnaan_status, subset=)

    st.dataframe(styled_df, use_container_width=True)

    # ------------------------------------------------------------------
    # GALERI & KESIMPULAN BERITA ACARA
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🖼️ Ekstraksi Metadata & Resolusi Gambar (PDF 2)")
    if galeri_foto:
        batas_render = 8 # Tampilkan max 8 untuk memori
        g_cols = st.columns(4)
        for idx, fto in enumerate(galeri_foto):
            if idx >= batas_render: break
            with g_cols[idx % 4]:
                st.image(fto.get("img"), caption=f"Hal {fto.get('hal')} | {fto.get('res')}", use_container_width=True)
                if int(fto.get('res').split('x').pop(0)) < 400:
                    st.caption("⚠️ Resolusi Terindikasi Crop/Zoom")
    else:
        st.info("Tidak ada gambar terdeteksi / resolusi terlalu rendah.")

    # BERITA ACARA
    st.subheader("📝 Draf Final Nota Dinas Auditor")
    
    item_fiktif = list()
    for x in hasil_validasi_akhir:
        if '❌' in x.get("Status Pembuktian", ""):
            item_fiktif.append(x)
            
    status_dokumen = "DITOLAK / REVISI TOTAL" if (log_anomali_matematika or len(item_fiktif) > 0) else "DISETUJUI & SIAP TERMIN"
    
    teks_ba = f'''
BERITA ACARA AUDIT FORENSIK DIGITAL
--------------------------------------------------
TANGGAL EKSEKUSI    : {datetime.now().strftime('%d %B %Y')}
STATUS HASIL AUDIT  : {status_dokumen}

RINGKASAN PEMERIKSAAN BERTAHAP:
1. Tahap 1 (Audit Angka)  : Ditemukan {len(log_anomali_matematika)} baris item pekerjaan dengan manipulasi atau hitungan deviasi yang salah.
2. Tahap 2 (Audit Foto)   : Dari {len(pekerjaan_valid_matematika)} pekerjaan yang lulus uji angka, terdapat {len(item_fiktif)} item yang tidak bisa dibuktikan fotonya (Indikasi fiktif / foto terpisah).

TINDAKAN:
Laporan ini dikembalikan. Mohon lengkapi perbaikan angka desimal dan pastikan melampirkan keterangan foto yang sesuai dengan nama material dan gedung lokasi.
--------------------------------------------------
    '''
    st.code(teks_ba.strip(), language="text")
