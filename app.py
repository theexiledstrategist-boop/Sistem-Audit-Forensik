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
# 2. MESIN EKSTRAKSI (CORE LOGIC)
# ==========================================

def get_float(val):
    if not val or str(val).strip().lower() in ['none', '']: return 0.0
    try:
        teks = str(val).strip()
        if ',' in teks and '.' in teks: teks = teks.replace('.', '').replace(',', '.')
        elif ',' in teks: teks = teks.replace(',', '.')
        return float(re.sub(r'[^\d\.-]', '', teks))
    except: return 0.0

def detect_madrasah(row_list):
    row_text = " ".join([str(x) for x in row_list if x]).upper()
    match = re.search(r'(MIS|MTSS|MIN|MTSN|MADRASAH\s+TSANAWIYAH|MADRASAH\s+IBTIDAIYAH)\s+[A-Z0-9\s\'\-]+', row_text)
    return match.group(0).strip() if match else None

def get_keywords_list(uraian):
    text = re.sub(r'\(.*?\)', '', str(uraian).upper())
    ignore = {"PEKERJAAN", "PEMASANGAN", "PENGADAAN", "PENYEDIAAN", "PASANGAN", "REHABILITASI", "RENOVASI", "BANGUNAN", "UNTUK", "DAN", "DENGAN", "M2", "M3", "KG", "LITER", "UNIT", "BH", "LOKASI"}
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
    
    # --- FASE 1: TABULASI ---
    with st.spinner("Fase 1: Mengekstrak data kemajuan fisik..."):
        with pdfplumber.open(f_mingguan) as pdf:
            for page in pdf.pages:
                if "KEMAJUAN FISIK" not in (page.extract_text() or "").upper(): continue
                table = page.extract_table()
                if not table: continue
                for row in table:
                    if len(row) < 12: continue
                    lok_baru = detect_madrasah(row)
                    if lok_baru: lokasi_skrg = lok_baru
                    
                    uraian = str(row[1] or row[2]).replace('\n', ' ').strip()
                    b_ini = get_float(row[8])
                    if b_ini > 0:
                        pekerjaan_aktif.append({
                            "Lokasi": lokasi_skrg, "Uraian": uraian,
                            "Lalu": get_float(row[5]), "Ini": b_ini,
                            "Total": get_float(row[11]), "KW": get_keywords_list(uraian)
                        })

    if not pekerjaan_aktif:
        st.error("Gagal mendeteksi progres pada tabel Kemajuan Fisik.")
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
            
            # Fuzzy Matching
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

    # --- FASE 3: KONSTRUKSI RANGKUMAN (OUTPUT BARU) ---
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
    
    # A. DASHBOARD RINGKASAN
    st.header("📊 Ringkasan Eksekutif Audit")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pekerjaan Terdeteksi", len(pekerjaan_aktif))
    c2.metric("Lokasi Terdampak", len(summary_work_loc))
    c3.metric("Tingkat Validitas Foto", f"{(len([x for x in final_report if '✅' in x['Status']]) / len(final_report) * 100):.1f}%")
    
    st.divider()

    # B. OUTPUT 4: RANGKUMAN DETAIL PEKERJAAN & LOKASI
    st.header("📍 Output 4: Resume Pekerjaan per Lokasi")
    st.write("Daftar aktivitas fisik yang diklaim mengalami kemajuan pada minggu laporan ini:")
    for loc, items in summary_work_loc.items():
        with st.expander(f"📌 {loc} ({len(items)} Item Pekerjaan)"):
            for i, task in enumerate(items, 1):
                st.write(f"{i}. {task}")

    # C. OUTPUT 5: RANGKUMAN KECOCOKAN FOTO
    st.header("🔍 Output 5: Analisis Kesesuaian Dokumentasi")
    st.write("Statistik validasi silang antara klaim progres dengan ketersediaan bukti visual:")
    
    stat_data = []
    for loc, stat in summary_stats.items():
        persen = (stat['Valid'] / stat['Total']) * 100
        stat_data.append({
            "Lokasi Madrasah": loc,
            "Total Item Progres": stat['Total'],
            "Item Tervalidasi Foto": stat['Valid'],
            "Persentase Validitas": f"{persen:.1f}%",
            "Status": "✅ AMAN" if persen == 100 else "⚠️ PERIKSA"
        })
    st.table(pd.DataFrame(stat_data))

    # D. DETAIL DATA (TABEL LENGKAP)
    st.header("📝 Matriks Audit Detail")
    df_f = pd.DataFrame(final_report)
    st.dataframe(df_f.style.applymap(
        lambda v: 'background-color: #ffcccc' if "❌" in v else 'background-color: #dff0d8', 
        subset=['Status']
    ), use_container_width=True)

    # E. BERITA ACARA
    st.header("📜 Draft Kesimpulan Audit")
    ba_text = f"Berdasarkan audit sekuensial, ditemukan {len(summary_work_loc)} lokasi aktif. "
    ba_text += f"Dari total {len(final_report)} item klaim, sebanyak {len([x for x in final_report if '❌' in x['Status']])} item TIDAK didukung foto yang sinkron."
    st.code(ba_text)
