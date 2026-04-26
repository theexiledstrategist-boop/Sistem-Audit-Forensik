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
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MESIN EKSTRAKSI (SELF-HEALING LOGIC)
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
st.title("🛡️ Audit Forensik PHTC: Self-Healing Mode")
st.caption("Standard Operational Protocol: Ketahanan Absolut terhadap Anomali Data")

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
    log_error_internal = []
    
    # --- FASE 1: TABULASI DENGAN PERISAI TRY-EXCEPT ---
    with st.spinner("Fase 1: Mengekstrak data dengan sistem proteksi anomali (Self-Healing)..."):
        try:
            with pdfplumber.open(f_mingguan) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Menarik SEMUA tabel di halaman, bukan hanya tabel pertama
                        tables = page.extract_tables()
                        if not tables: continue
                        
                        for table in tables:
                            for row_idx, row in enumerate(table):
                                # PERISAI MIKRO: Jika 1 baris rusak, sistem tidak akan mati
                                try:
                                    if not row or len(row) < 9: continue 
                                    
                                    lok_baru = detect_madrasah(row)
                                    if lok_baru: lokasi_skrg = lok_baru
                                    
                                    uraian = safe_get(row, 1)
                                    if not uraian or len(uraian) < 3: 
                                        uraian = safe_get(row, 2)
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
                                except Exception as e_row:
                                    # Sistem mencatat error secara rahasia dan melanjutkan ke baris berikutnya
                                    log_error_internal.append(f"Hal {page_num}, Baris {row_idx}: {str(e_row)}")
                                    continue 
                    except Exception as e_page:
                        log_error_internal.append(f"Gagal membedah Hal {page_num}: {str(e_page)}")
                        continue
        except Exception as e:
            st.error(f"Sistem gagal mengekstrak file PDF Laporan Mingguan: {e}")
            st.stop()

    if not pekerjaan_aktif:
        st.error("Gagal mendeteksi item progres. PDF Laporan Mingguan ini mungkin berupa gambar hasil 'scan' atau format matriks kolomnya telah diubah total oleh Kontraktor.")
        if log_error_internal:
            with st.expander("Lihat Log Error Internal (Diagnostic)"):
                st.write(log_error_internal[:15])
        st.stop()

    # --- FASE 2: VERIFIKASI VISUAL ---
    with st.spinner("Fase 2: Validasi silang dengan dokumentasi..."):
        teks_foto_db = ""
        try:
            doc_foto = fitz.open(stream=f_foto.read(), filetype="pdf")
            for p in doc_foto: teks_foto_db += p.get_text("text").upper() + " "
            doc_foto.close()
        except Exception as e_foto:
            st.error(f"Gagal membaca PDF Laporan Dokumentasi: {e_foto}")
            st.stop()
        
        final_report = []
        for item in pekerjaan_aktif:
            status = "❌ DITOLAK"
            alasan = "Tidak ditemukan bukti visual yang relevan."
            
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
    
    # Kalkulasi validitas total aman dari error division by zero
    total_valid = sum(s['Valid'] for s in summary_stats.values())
    total_items = sum(s['Total'] for s in summary_stats.values())
    validitas_persen = (total_valid / total_items * 100) if total_items > 0 else 0.0
    c3.metric("Tingkat Validitas Foto", f"{validitas_persen:.1f}%")
    
    st.divider()

    st.header("📍 Output 4: Resume Pekerjaan per Lokasi")
    for loc, items in summary_work_loc.items():
        with st.expander(f"📌 {loc} ({len(items)} Item Pekerjaan)"):
            for i, task in enumerate(items, 1):
                st.write(f"{i}. {task}")

    st.header("🔍 Output 5: Analisis Kesesuaian Dokumentasi")
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

    if log_error_internal:
        st.warning("Peringatan Sistem: Mesin mendeteksi beberapa baris/tabel dengan format cacat pada PDF yang Anda unggah, namun berhasil diisolasi dan dilewati (Self-Healing Mode) tanpa menghentikan audit.")
