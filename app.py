import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
import re
from PIL import Image
from datetime import datetime

# ==========================================
# 1. KONFIGURASI UI & TEMA
# ==========================================
st.set_page_config(page_title="Audit Forensik PHTC Ultimate", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stMetric { background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #0056b3; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .summary-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .loc-header { color: #0056b3; font-weight: bold; border-bottom: 2px solid #0056b3; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MESIN EKSTRAKSI (CORE LOGIC ANTI-BADAI)
# ==========================================

def get_float(val):
    """Memaksa teks apapun menjadi angka desimal yang benar"""
    if not val or str(val).strip().lower() in ['none', '']: return 0.0
    try:
        teks = str(val).strip()
        if ',' in teks and '.' in teks: teks = teks.replace('.', '').replace(',', '.')
        elif ',' in teks: teks = teks.replace(',', '.')
        return float(re.sub(r'[^\d\.-]', '', teks))
    except: return 0.0

def safe_get(row_list, index):
    """Mencegah aplikasi mati jika kolom tabel menyusut (IndexError)"""
    return row_list[index] if index < len(row_list) else ""

def detect_madrasah(row_list):
    """Mendeteksi nama lokasi di sepanjang baris tabel"""
    row_text = " ".join([str(x) for x in row_list if x]).upper()
    match = re.search(r'(MIS|MTSS|MIN|MTSN|MADRASAH\s+TSANAWIYAH|MADRASAH\s+IBTIDAIYAH)\s+[A-Z0-9\s\'\-]+', row_text)
    return match.group(0).strip() if match else None

def get_keywords_list(uraian):
    """Menyaring uraian menjadi kata kunci material fisik"""
    text = re.sub(r'\(.*?\)', '', str(uraian).upper())
    ignore = {"PEKERJAAN", "PEMASANGAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", "REHABILITASI", "RENOVASI", "BANGUNAN", "UNTUK", "DAN", "DENGAN", "M2", "M3", "KG", "LITER", "UNIT", "BH", "LOKASI", "SUB", "TOTAL"}
    return [w for w in text.split() if w not in ignore and len(w) > 3]

# ==========================================
# 3. INTERFACE PENGAWASAN
# ==========================================
st.title("🛡️ Audit Forensik PHTC: Ultimate Oversight")
st.caption("Standard Operational Protocol: Aurelius Vishvakarma Precision Logic")

with st.sidebar:
    st.header("📂 Data Proyek")
    f_mingguan = st.file_uploader("Upload Laporan Mingguan", type="pdf")
    f_foto = st.file_uploader("Upload Laporan Dokumentasi", type="pdf")
    st.markdown("---")
    btn_audit = st.button("🚀 JALANKAN AUDIT TOTAL", use_container_width=True)

if not (f_mingguan and f_foto):
    st.info("Sistem dalam posisi stand-by. Unggah dokumen untuk memicu audit sekuensial.")
    st.stop()

# ==========================================
# 4. EKSEKUSI AUDIT & GENERASI OUTPUT
# ==========================================
if btn_audit:
    pekerjaan_aktif = []
    lokasi_skrg = "UMUM (TIDAK TERDETEKSI)"
    
    # --- FASE 1: TABULASI (PEMBACAAN FLEKSIBEL) ---
    with st.spinner("Fase 1: Mengekstrak data kemajuan fisik tanpa batasan format..."):
        try:
            with pdfplumber.open(f_mingguan) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if not table: continue
                    
                    for row in table:
                        # PERISAI ANTI GHOST-ROW: Pastikan 'row' bukan None sebelum menghitung length-nya
                        if not row or len(row) < 9: continue 
                        
                        lok_baru = detect_madrasah(row)
                        if lok_baru: lokasi_skrg = lok_baru
                        
                        # Ambil uraian dengan aman
                        uraian = str(safe_get(row, 1) or safe_get(row, 2)).replace('\n', ' ').strip()
                        if not uraian or uraian.upper() in ['NONE', '', 'URAIAN PEKERJAAN', 'JENIS PEKERJAAN', 'NO']: continue
                        
                        # Periksa kolom 'Minggu Ini' (Kolom ke-8)
                        raw_ini = str(safe_get(row, 8))
                        if not any(c.isdigit() for c in raw_ini): continue # Pastikan itu angka
                        
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
        except Exception as e:
            st.error(f"Sistem gagal mengekstrak tabel Laporan Mingguan: {e}")
            st.stop()

    if not pekerjaan_aktif:
        st.error("Gagal mendeteksi progres. Pastikan Anda mengunggah dokumen Laporan Mingguan yang memiliki angka kemajuan di kolom matriksnya.")
        st.stop()

    # --- FASE 2: VERIFIKASI VISUAL ---
    with st.spinner("Fase 2: Validasi silang dengan dokumentasi..."):
        teks_foto_db = ""
        doc_foto = fitz.open(stream=f_foto.read(), filetype="pdf")
        for p in doc_foto: teks_foto_db += p.get_text("text").upper() + " "
        doc_foto.close()
        
        final_report = []
        for item in pekerjaan_aktif:
            status = "❌ DITOLAK"
            alasan = "Tidak ditemukan bukti visual yang relevan."
            
            # Fuzzy Matching (Pencocokan Kata Kunci)
            found_kw = [k for k in item['KW'] if k in teks_foto_db]
            if found_kw:
                status = "✅ VALID"
                alasan = f"Terverifikasi melalui kata kunci: {', '.join(found_kw)}"
            elif not item['KW']:
                status = "⚠️ MANUAL"
                alasan = "Uraian terlalu umum, memerlukan cek fisik."
            
            final_report.append({
                "Lokasi": item['Lokasi'], "Item": item['Uraian'],
                "Progres": f"+{item['Ini']}%", "Status": status, "Analisis": alasan
            })

    # --- FASE 3: KONSTRUKSI RANGKUMAN ---
    summary_work_loc = {}
    summary_stats = {}

    for res in final_report:
        loc = res["Lokasi"]
        if loc not in summary_work_loc: summary_work_loc[loc] = []
        if loc not in summary_stats: summary_stats[loc] = {"Total": 0, "Valid": 0}
        
        summary_work_loc[loc].append(res["Item"])
        summary_stats[loc]["Total"] += 1
        if "✅" in res["Status"]: summary_stats[loc]["Valid"] += 1

    # ==========================================
    # 5. PENYAJIAN OUTPUT STRATEGIS
    # ==========================================
    
    st.header("📊 Ringkasan Eksekutif Audit")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pekerjaan Terdeteksi", len(pekerjaan_aktif))
    c2.metric("Lokasi Terdampak", len(summary_work_loc))
    c3.metric("Tingkat Validitas Foto", f"{(summary_stats[list(summary_stats.keys())[0]]['Valid'] / summary_stats[list(summary_stats.keys())[0]]['Total'] * 100 if summary_stats else 0):.1f}%")
    
    st.divider()

    st.header("📍 Output 4: Resume Pekerjaan per Lokasi")
    st.write("Daftar aktivitas fisik yang diklaim mengalami kemajuan pada minggu laporan ini:")
    for loc, items in summary_work_loc.items():
        with st.expander(f"📌 {loc} ({len(items)} Item Pekerjaan)"):
            for i, task in enumerate(items, 1):
                st.write(f"{i}. {task}")

    st.header("🔍 Output 5: Analisis Kesesuaian Dokumentasi")
    st.write("Statistik validasi silang antara klaim progres dengan ketersediaan bukti visual:")
    
    stat_data = []
    for loc, stat in summary_stats.items():
        persen = (stat['Valid'] / stat['Total']) * 100 if stat['Total'] > 0 else 0
        stat_data.append({
            "Lokasi Madrasah": loc,
            "Total Item Progres": stat['Total'],
            "Item Tervalidasi Foto": stat['Valid'],
            "Persentase Validitas": f"{persen:.1f}%",
            "Status": "✅ AMAN" if persen == 100 else "⚠️ PERIKSA"
        })
    st.table(pd.DataFrame(stat_data))

    st.header("📝 Matriks Audit Detail")
    df_f = pd.DataFrame(final_report)
    st.dataframe(df_f.style.applymap(
        lambda v: 'background-color: #ffcccc' if "❌" in v else 'background-color: #dff0d8', 
        subset=['Status']
    ), use_container_width=True)

    st.header("📜 Draft Kesimpulan Audit")
    ba_text = f"Berdasarkan audit sekuensial, ditemukan {len(summary_work_loc)} lokasi aktif. "
    ba_text += f"Dari total {len(final_report)} item klaim, sebanyak {len([x for x in final_report if '❌' in x['Status']])} item TIDAK didukung foto yang sinkron."
    st.code(ba_text)
