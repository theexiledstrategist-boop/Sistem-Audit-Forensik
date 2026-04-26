import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
import re
from PIL import Image
from datetime import datetime

# ==========================================
# 1. INISIALISASI & UI PROFESIONAL
# ==========================================
st.set_page_config(page_title="Audit Forensik Progres PHTC", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stMetric { background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #0056b3; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .alert-danger { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; font-weight: bold; border-left: 5px solid #dc3545; margin-bottom: 20px;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. FUNGSI PENDUKUNG (MESIN EKSTRAKSI)
# ==========================================

def get_float(val):
    """Membersihkan format angka desimal/ribuan menjadi format komputasi mutlak."""
    if not val or str(val).strip().lower() in ['none', '']: return 0.0
    try:
        clean = re.sub(r'[^\d,\.-]', '', str(val))
        return float(clean.replace(',', '.'))
    except: 
        return 0.0

def detect_madrasah(text):
    """Mendeteksi transisi lokasi dengan jangkauan sensor yang diperluas."""
    match = re.search(r'(MIS|MTSS|MIN|MTSN|MADRASAH\s+TSANAWIYAH|MADRASAH\s+IBTIDAIYAH)\s+[A-Z0-9\s\'\-]+', str(text).upper())
    return match.group(0).strip() if match else None

def get_material_keyword(uraian):
    """Mengekstrak 2 kata benda inti yang menjadi objek fisik pekerjaan."""
    text = re.sub(r'\(.*?\)', '', str(uraian).upper())
    words = text.split()
    ignore = {
        "PEKERJAAN", "PEMASANGAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", 
        "REHABILITASI", "RENOVASI", "BANGUNAN", "UNTUK", "DAN", "DENGAN", 
        "M2", "M3", "KG", "LITER", "UNIT", "BH", "TITIK"
    }
    clean_words = [w for w in words if w not in ignore and len(w) > 3]
    return " ".join(clean_words[:2]) if clean_words else ""

# ==========================================
# 3. ANTARMUKA PENGGUNA (SIDEBAR)
# ==========================================
st.title("⚖️ Sistem Audit Forensik PHTC")
st.caption("Protokol Verifikasi Deterministik (Aurelius Vishvakarma Standard)")

with st.sidebar:
    st.header("📂 Brankas Dokumen")
    f_mingguan = st.file_uploader("1. Upload Laporan Mingguan", type="pdf")
    f_foto = st.file_uploader("2. Upload Laporan Dokumentasi", type="pdf")
    st.markdown("---")
    btn_audit = st.button("🚀 EKSEKUSI AUDIT ABSOLUT", use_container_width=True)

if not (f_mingguan and f_foto):
    st.info("Sistem dalam posisi siaga. Silakan unggah instrumen laporan untuk memulai ekstraksi.")
    st.stop()

# ==========================================
# 4. EKSEKUSI AUDIT SEKUENSIAL
# ==========================================
if btn_audit:
    
    # --- LANGKAH 1: TABULASI PEKERJAAN AKTIF (ISOLASI HALAMAN) ---
    pekerjaan_aktif = []
    lokasi_skrg = "UMUM"
    
    with st.spinner("Langkah 1: Mengisolasi tabel kemajuan fisik dan mengunci item aktif..."):
        try:
            with pdfplumber.open(f_mingguan) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    # Filter Absolut: Lewati halaman tanpa judul Kemajuan Fisik (mengabaikan tabel material/alat)
                    if not text or "KEMAJUAN FISIK" not in text.upper(): continue
                    
                    table = page.extract_table()
                    if not table: continue
                    
                    for row in table:
                        if len(row) < 12: continue # Pastikan format tabel sesuai standar PU
                        
                        uraian = str(row[1]).replace('\n', ' ').strip()
                        if not uraian or uraian.lower() == 'none': continue
                        
                        # Deteksi Konteks Lokasi
                        lok_baru = detect_madrasah(uraian)
                        if lok_baru: lokasi_skrg = lok_baru
                        
                        # Ambil progres minggu ini
                        raw_ini = str(row[8])
                        if not any(c.isdigit() for c in raw_ini): continue
                        
                        b_ini = get_float(raw_ini)
                        if b_ini > 0:
                            pekerjaan_aktif.append({
                                "Lokasi": lokasi_skrg,
                                "Uraian": uraian,
                                "Lalu": get_float(row[5]),
                                "Ini": b_ini,
                                "Total_Klaim": get_float(row[11]),
                                "Keywords": get_material_keyword(uraian)
                            })
        except Exception as e:
            st.error(f"Kegagalan sistem saat membedah Laporan Mingguan: {e}")
            st.stop()

    if not pekerjaan_aktif:
        st.error("🚨 Operasi dihentikan: Tidak ditemukan klaim penambahan bobot (>0%) pada halaman KEMAJUAN FISIK.")
        st.stop()

    # --- LANGKAH 2: AUDIT MATEMATIS (INTEGRITAS ANGKA) ---
    anomali_angka = []
    with st.spinner("Langkah 2: Memverifikasi akurasi perhitungan desimal kumulatif..."):
        for item in pekerjaan_aktif:
            seharusnya = round(item['Lalu'] + item['Ini'], 3)
            deviasi = round(item['Total_Klaim'] - seharusnya, 3)
            
            if abs(deviasi) > 0.001:
                anomali_angka.append({
                    "Lokasi": item['Lokasi'],
                    "Pekerjaan": item['Uraian'],
                    "Seharusnya": seharusnya,
                    "Klaim Pelapor": item['Total_Klaim'],
                    "Deviasi": deviasi
                })

    # --- LANGKAH 3: VALIDASI SILANG BUKTI VISUAL (LOGIKA PEMAAF LOKASI) ---
    final_report = []
    with st.spinner("Langkah 3: Menyelaraskan klaim angka dengan bukti visual dokumentasi..."):
        try:
            teks_foto_db = ""
            doc_foto = fitz.open(stream=f_foto.read(), filetype="pdf")
            for p in doc_foto:
                teks_foto_db += p.get_text("text").upper() + " "
            doc_foto.close()
            
            for item in pekerjaan_aktif:
                kw = item['Keywords']
                
                # Menentukan parameter pencarian lokasi
                if item['Lokasi'] == "UMUM":
                    # Jika mesin gagal mendeteksi madrasah, abaikan lokasi dan langsung cari material
                    found_loc = True 
                    loc_kw = "UMUM"
                else:
                    nama_bersih = item['Lokasi'].upper()
                    for hapus in ["MIS ", "MTSS ", "MIN ", "MTSN ", "MADRASAH TSANAWIYAH ", "MADRASAH IBTIDAIYAH "]:
                        nama_bersih = nama_bersih.replace(hapus, "").strip()
                    
                    loc_kw = nama_bersih.split()[0] if nama_bersih else ""
                    found_loc = loc_kw in teks_foto_db if loc_kw else True
                
                # Verifikasi keberadaan material di foto
                found_mat = kw in teks_foto_db if kw else True
                
                status = "✅ VALID"
                catatan = "Bukti visual sinkron dengan klaim."
                
                if not found_loc:
                    status = "❌ DITOLAK"
                    catatan = f"Lokasi spesifik '{loc_kw}' tidak ada di keterangan foto."
                elif kw and not found_mat:
                    status = "❌ DITOLAK"
                    catatan = f"Objek fisik '{kw}' tidak ditemukan pada bukti dokumentasi."
                elif not kw:
                    catatan = "⚠️ Verifikasi manual (Objek fisik tidak spesifik)."
                
                final_report.append({
                    "Lokasi / Madrasah": item['Lokasi'],
                    "Item Pekerjaan": item['Uraian'],
                    "Klaim (+%)": item['Ini'],
                    "Keputusan Mesin": status,
                    "Analisis Forensik": catatan
                })
        except Exception as e:
            st.error(f"Kegagalan saat membedah Laporan Dokumentasi: {e}")

    # ==========================================
    # 5. RENDER OUTPUT DASBOR PENGAWASAN
    # ==========================================
    
    st.header("📊 Executive Summary")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Klaim Progres", len(pekerjaan_aktif))
    c2.metric("Log Kesalahan Angka", len(anomali_angka))
    c3.metric("Klaim Fiktif / Tanpa Foto", len([x for x in final_report if "❌" in x['Keputusan Mesin']]))
    
    st.divider()

    # OUTPUT 1: TABEL VALIDASI VISUAL
    st.subheader("1. Matriks Kesesuaian Progres vs Realitas Lapangan")
    df_final = pd.DataFrame(final_report)
    def warna_status(val):
        if "❌" in val: return 'background-color: #ffcccc; color: #a94442; font-weight: bold'
        if "✅" in val: return 'background-color: #dff0d8; color: #3c763d'
        return ''
    st.dataframe(df_final.style.applymap(warna_status, subset=['Keputusan Mesin']), use_container_width=True)

    # OUTPUT 2: TABEL ANOMALI MATEMATIS
    if anomali_angka:
        st.subheader("2. Daftar Manipulasi / Kelalaian Kalkulasi")
        st.markdown('<div class="alert-danger">Sistem menemukan deviasi pada penjumlahan bobot progres. Dokumen tidak layak secara administratif.</div>', unsafe_allow_html=True)
        st.table(pd.DataFrame(anomali_angka))

    # OUTPUT 3: DRAF KEPUTUSAN FINAL
    st.subheader("3. Draf Nota Dinas (Berita Acara Audit)")
    dokumen_cacat = len(anomali_angka) > 0 or len([x for x in final_report if "❌" in x['Keputusan Mesin']]) > 0
    keputusan = "DITOLAK / WAJIB REVISI" if dokumen_cacat else "DISETUJUI (VALID ADMINISTRATIF)"
    
    ba_text = f"""
MEMO HASIL DESK AUDIT DOKUMEN (AURELIUS PROTOCOL)
--------------------------------------------------
Tanggal Eksekusi : {datetime.now().strftime('%d %B %Y')}
Objek Verifikasi : Laporan Progres Mingguan PHTC
Status Audit     : {keputusan}

EVALUASI KOMPUTASI:
1. Integritas Data Numerik : {'Ditemukan ' + str(len(anomali_angka)) + ' deviasi pada kalkulasi persentase bobot.' if anomali_angka else 'Kalkulasi desimal sinkron dan presisi.'}
2. Validasi Bukti Material : {'Terdapat ' + str(len([x for x in final_report if "❌" in x['Keputusan Mesin']])) + ' item pekerjaan yang diklaim naik namun tidak didukung dokumentasi visual yang selaras.' if [x for x in final_report if '❌' in x['Keputusan Mesin']] else 'Seluruh klaim progres didukung oleh bukti visual yang relevan.'}

INSTRUKSI TINDAK LANJUT:
{'Segera kembalikan dokumen ini kepada pelapor. Minta koreksi pada penjumlahan matematis dan lengkapi bukti foto yang spesifik sebelum pengajuan termin diproses.' if dokumen_cacat else 'Dokumen telah memenuhi standar ketelitian mutlak dan dapat diproses untuk otorisasi selanjutnya.'}
--------------------------------------------------
    """
    st.code(ba_text, language="text")
