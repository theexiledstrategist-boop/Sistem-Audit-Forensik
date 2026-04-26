import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
import re
from datetime import datetime

# ==========================================
# 1. KONFIGURASI UI (SAFE MODE)
# ==========================================
st.set_page_config(page_title="Audit Forensik PHTC", page_icon="⚖️", layout="wide")
st.markdown("<style>.main { background-color: #f4f7f9; }</style>", unsafe_allow_html=True)

# ==========================================
# 2. MESIN EKSTRAKSI KEBANGKITAN
# ==========================================
def get_float(val):
    if val is None: return 0.0
    try:
        teks = str(val).strip()
        if teks.lower() in ['none', '', '-']: return 0.0
        if ',' in teks and '.' in teks: teks = teks.replace('.', '').replace(',', '.')
        elif ',' in teks: teks = teks.replace(',', '.')
        return float(re.sub(r'[^\d\.-]', '', teks))
    except: return 0.0

def safe_get(row_list, index):
    if not row_list or index >= len(row_list): return ""
    val = row_list[index]
    return str(val).strip() if val is not None else ""

def detect_madrasah(row_list):
    if not row_list: return None
    row_text = " ".join([str(x) for x in row_list if x]).upper()
    match = re.search(r'(MIS|MTSS|MIN|MTSN|MADRASAH\s+TSANAWIYAH|MADRASAH\s+IBTIDAIYAH)\s+[A-Z0-9\s\'\-]+', row_text)
    return match.group(0).strip() if match else None

def get_keywords_list(uraian):
    if not uraian: return []
    text = re.sub(r'\(.*?\)', '', str(uraian).upper())
    ignore = {"PEKERJAAN", "PEMASANGAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", "REHABILITASI", "RENOVASI", "BANGUNAN", "UNTUK", "DAN", "DENGAN", "M2", "M3", "KG", "LITER", "UNIT", "BH", "LOKASI", "SUB", "TOTAL"}
    return [w for w in text.split() if w not in ignore and len(w) > 3]

# ==========================================
# 3. INTERFACE PENGAWASAN
# ==========================================
st.title("🛡️ Audit Forensik PHTC (Safe Render Mode)")
st.caption("Mode Anti-Crash: Menonaktifkan rendering gaya untuk kompatibilitas penuh.")

with st.sidebar:
    st.header("📂 Data Proyek")
    f_mingguan = st.file_uploader("Upload Laporan Mingguan", type="pdf")
    f_foto = st.file_uploader("Upload Laporan Dokumentasi", type="pdf")
    btn_audit = st.button("🚀 JALANKAN AUDIT", use_container_width=True)

if not (f_mingguan and f_foto):
    st.info("Sistem stand-by. Unggah dokumen.")
    st.stop()

# ==========================================
# 4. EKSEKUSI AUDIT
# ==========================================
if btn_audit:
    pekerjaan_aktif = []
    lokasi_skrg = "UMUM (TIDAK TERDETEKSI)"
    
    with st.spinner("Fase 1: Mengekstrak tabel kemajuan fisik..."):
        try:
            with pdfplumber.open(f_mingguan) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if not tables: continue
                    for table in tables:
                        for row in table:
                            try:
                                if not row or len(row) < 9: continue 
                                lok_baru = detect_madrasah(row)
                                if lok_baru: lokasi_skrg = lok_baru
                                
                                uraian = safe_get(row, 1)
                                if not uraian or len(uraian) < 3: uraian = safe_get(row, 2)
                                if not uraian or uraian.upper() in ['NONE', '', 'URAIAN PEKERJAAN', 'JENIS PEKERJAAN', 'NO']: continue
                                
                                raw_ini = safe_get(row, 8)
                                if not any(c.isdigit() for c in raw_ini): continue
                                
                                b_ini = get_float(raw_ini)
                                if b_ini > 0:
                                    pekerjaan_aktif.append({
                                        "Lokasi": lokasi_skrg, 
                                        "Uraian": uraian,
                                        "Lalu": get_float(safe_get(row, 5)), 
                                        "Ini": b_ini,
                                        "Total": get_float(safe_get(row, 11)), 
                                        "KW": get_keywords_list(uraian)
                                    })
                            except: continue 
        except Exception as e:
            st.error(f"Gagal membedah PDF Laporan Mingguan: {e}")
            st.stop()

    if not pekerjaan_aktif:
        st.error("Gagal mendeteksi progres. Tabel mungkin tidak sesuai standar KemenPU.")
        st.stop()

    with st.spinner("Fase 2: Validasi silang dengan dokumentasi..."):
        teks_foto_db = ""
        try:
            doc_foto = fitz.open(stream=f_foto.read(), filetype="pdf")
            for p in doc_foto: teks_foto_db += p.get_text("text").upper() + " "
            doc_foto.close()
        except Exception as e:
            st.error(f"Gagal membaca PDF Laporan Foto: {e}")
            st.stop()
        
        final_report = []
        for item in pekerjaan_aktif:
            status = "❌ DITOLAK"
            alasan = "Tidak ditemukan bukti visual yang relevan."
            
            found_kw = [k for k in item['KW'] if k in teks_foto_db]
            if found_kw:
                status = "✅ VALID"
                alasan = f"Kata kunci ditemukan: {', '.join(found_kw)}"
            elif not item['KW']:
                status = "⚠️ MANUAL"
                alasan = "Uraian terlalu umum."
            
            final_report.append({
                "Lokasi": item['Lokasi'], 
                "Item": item['Uraian'],
                "Progres": f"+{item['Ini']}%", 
                "Status": status, 
                "Analisis": alasan
            })

    # ==========================================
    # 5. PENYAJIAN OUTPUT (TANPA KOSMETIK)
    # ==========================================
    
    st.header("📊 Ringkasan Eksekutif")
    c1, c2 = st.columns(2)
    c1.info(f"Pekerjaan Diperiksa: {len(pekerjaan_aktif)}")
    c2.info(f"Item Potensi Ditolak (Tanpa Foto): {len([x for x in final_report if '❌' in x['Status']])}")
    
    st.divider()

    st.header("🔍 Matriks Validasi Detail")
    st.caption("Semua warna dinonaktifkan untuk mencegah error visualisasi sistem.")
    
    # PROTEKSI MUTLAK: Mengubah semua isi DataFrame menjadi string agar tidak diblokir oleh Streamlit/PyArrow
    try:
        df_f = pd.DataFrame(final_report).astype(str)
        st.dataframe(df_f, use_container_width=True)
    except Exception as e:
        st.error("Terjadi kendala saat menggambar tabel interaktif. Menampilkan data dalam format mentah:")
        st.write(final_report)

    st.header("📜 Draf Kesimpulan Audit")
    ba_text = f"Telah diaudit sebanyak {len(pekerjaan_aktif)} item progres. Ditemukan {len([x for x in final_report if '❌' in x['Status']])} klaim tanpa dukungan bukti foto yang sesuai."
    st.code(ba_text)
