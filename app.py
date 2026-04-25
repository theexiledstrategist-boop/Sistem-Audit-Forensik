import streamlit as st
import pdfplumber
import pandas as pd
import fitz  # PyMuPDF
import io
import re
from PIL import Image
from datetime import datetime

# ==========================================
# 1. SETTING UI PROFESIONAL
# ==========================================
st.set_page_config(page_title="Sistem Audit Forensik PHTC", page_icon="🛡️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .report-card { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .status-badge { padding: 5px 10px; border-radius: 15px; font-weight: bold; font-size: 0.8em; }
    .crit-alert { color: #721c24; background-color: #f8d7da; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MESIN ANALITIK (LOGIKA VALIDASI)
# ==========================================

def clean_val(val):
    if not val or str(val).lower() == 'none': return 0.0
    try: 
        # Hanya ambil karakter angka, koma, atau titik
        clean_str = re.sub(r'[^\d,\.]', '', str(val))
        return float(clean_str.replace(',', '.'))
    except: 
        return 0.0

def detect_location(text):
    # Mencari pola nama MIS atau MTSS
    match = re.search(r'(MIS|MTSS)\s+[A-Z\s\'\-]+', str(text).upper())
    return match.group(0).strip() if match else None

def get_building(text):
    match = re.search(r'BANGUNAN\s+[A-Z\d]+', str(text).upper())
    return match.group(0).strip() if match else None

# ==========================================
# 3. HEADER & UPLOAD
# ==========================================
st.title("🛡️ Desk Audit System: Kendali Mutu Prasarana Strategis")
st.caption("Protokol Verifikasi Mutlak - Khusus Pengawasan Jarak Jauh")

with st.sidebar:
    st.header("📥 Input Dokumen")
    f_mingguan = st.file_uploader("Upload Laporan Mingguan", type="pdf")
    f_foto = st.file_uploader("Upload Laporan Dokumentasi", type="pdf")
    st.markdown("---")
    execute = st.button("🚀 EKSEKUSI AUDIT MENYELURUH", use_container_width=True)

if not (f_mingguan and f_foto):
    st.info("Sistem siap. Silakan unggah dokumen PDF di sidebar untuk memulai verifikasi otomatis.")
    st.stop()

# ==========================================
# 4. EKSEKUSI LOGIKA
# ==========================================
if execute:
    # A. PRE-PROCESSING DOKUMENTASI VISUAL
    with st.spinner("Mengekstrak bukti visual dan metadata..."):
        teks_foto_db = ""
        galeri_images = []
        try:
            doc_f = fitz.open(stream=f_foto.read(), filetype="pdf")
            for i in range(len(doc_f)):
                p = doc_f[i]
                teks_foto_db += p.get_text("text").upper() + " "
                for img in p.get_images(full=True):
                    xref = img[0]
                    pix = doc_f.extract_image(xref)
                    image = Image.open(io.BytesIO(pix["image"]))
                    if image.width > 200: # Abaikan logo PU/MK yang kecil
                        galeri_images.append({"img": image, "hal": i+1, "res": f"{image.width}x{image.height}"})
            f_foto.seek(0)
        except Exception as e:
            st.error(f"Gagal membaca PDF Dokumentasi: {e}")

    # B. AUDIT TABEL PROGRES (DENGAN FILTER ISOLASI HALAMAN)
    results_audit = []
    anomali_matematika = []
    lokasi_aktif = "LOKASI BELUM TERDETEKSI"

    with st.spinner("Membedah baris pekerjaan secara presisi..."):
        with pdfplumber.open(f_mingguan) as pdf:
            for page in pdf.pages:
                
                # FILTER ABSOLUT: Hanya proses halaman yang mengandung teks "KEMAJUAN FISIK"
                page_text = page.extract_text()
                if page_text and "KEMAJUAN FISIK" not in page_text.upper():
                    continue # Abaikan halaman tabel bahan, alat, absensi, dll.
                
                tables = page.extract_table()
                if not tables: continue
                
                for row in tables:
                    try:
                        # FILTER ABSOLUT KEDUA: Tabel kemajuan fisik KemenPU wajib punya minimal 12 kolom
                        if len(row) < 12: continue
                        
                        uraian = str(row[1]).replace('\n', ' ').strip()
                        if not uraian or uraian.lower() in ['none', 'uraian pekerjaan', '']: continue

                        # Update Lokasi jika menemukan header Madrasah
                        new_loc = detect_location(uraian)
                        if new_loc: lokasi_aktif = new_loc

                        # Ekstraksi Angka
                        raw_ini = str(row[8])
                        # Jika kolom ke-8 tidak mengandung angka sama sekali, lewati (ini biasanya sub-header)
                        if not any(char.isdigit() for char in raw_ini): continue

                        b_lalu = clean_val(row[5])
                        b_ini = clean_val(raw_ini)
                        b_total_klaim = clean_val(row[11])

                        if b_ini > 0:
                            # 1. Cek Matematika
                            real_calc = round(b_lalu + b_ini, 3)
                            diff = round(b_total_klaim - real_calc, 3)
                            
                            if abs(diff) > 0.001:
                                anomali_matematika.append({
                                    "Lokasi": lokasi_aktif, 
                                    "Item": uraian, 
                                    "Klaim": b_total_klaim, 
                                    "Sistem": real_calc, 
                                    "Selisih": diff
                                })

                            # 2. Cek Visual (Cross-Check)
                            bldg = get_building(uraian)
                            
                            # Ekstrak 1 kata utama dari Madrasah (misal: MIS NURUSSALAM -> NURUSSALAM)
                            loc_kw_list = lokasi_aktif.replace("MIS ", "").replace("MTSS ", "").split()
                            loc_kw = loc_kw_list[0] if loc_kw_list else ""
                            
                            found_loc = loc_kw in teks_foto_db if loc_kw else False
                            found_bldg = (bldg in teks_foto_db) if bldg else True
                            
                            status = "✅ VALID"
                            catatan = "Bukti visual ditemukan."
                            
                            if not found_loc:
                                status = "❌ DITOLAK"
                                catatan = f"Nama Madrasah ({lokasi_aktif}) TIDAK ADA di laporan visual."
                            elif not found_bldg:
                                status = "❌ DITOLAK"
                                catatan = f"Klaim progres {bldg} TIDAK ADA foto dokumentasinya."

                            results_audit.append({
                                "Madrasah": lokasi_aktif,
                                "Pekerjaan": uraian,
                                "Bobot Naik": f"+{b_ini}%",
                                "Status": status,
                                "Penjelasan Analitik": catatan
                            })
                    except Exception as e:
                        continue

    # ==========================================
    # 5. DISPLAY OUTPUT KOMPREHENSIF
    # ==========================================
    
    # --- BAGIAN 1: EXECUTIVE SUMMARY ---
    st.header("📊 Ringkasan Eksekutif Audit")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Item Progres Diperiksa", len(results_audit))
    c2.metric("Anomali Hitungan Angka", len(anomali_matematika))
    c3.metric("Item Progres Tanpa Foto", len([x for x in results_audit if "❌" in x["Status"]]))

    # --- BAGIAN 2: LOG VALIDASI DETAIL ---
    st.header("🔍 Laporan Deteksi Progres vs Bukti Visual")
    if results_audit:
        df_res = pd.DataFrame(results_audit)
        def style_status(v):
            return 'background-color: #ffcccc; color: #a94442; font-weight: bold' if "❌" in v else 'background-color: #dff0d8; color: #3c763d'
        st.dataframe(df_res.style.applymap(style_status, subset=['Status']), use_container_width=True)
    else:
        st.success("Tidak ada penambahan progres minggu ini atau sistem tidak mendeteksi tabel progres yang valid.")

    # --- BAGIAN 3: ANOMALI MATEMATIKA ---
    if anomali_matematika:
        st.header("⚠️ Temuan Kesalahan Hitung (Anomali Desimal)")
        st.markdown('<div class="crit-alert">Sistem mendeteksi ketidaksesuaian antara (Minggu Lalu + Minggu Ini) dengan (Total Kumulatif). Hal ini mengindikasikan mark-up atau kelalaian spreadsheet dari kontraktor.</div>', unsafe_allow_html=True)
        st.table(pd.DataFrame(anomali_matematika))

    # --- BAGIAN 4: FORENSIK VISUAL & METADATA ---
    st.header("🖼️ Galeri Bukti Material & Resolusi")
    if galeri_images:
        cols = st.columns(4)
        for i, img_data in enumerate(galeri_images[:20]): # Tampilkan max 20 foto pertama agar tidak berat
            with cols[i % 4]:
                st.image(img_data["img"], caption=f"Bukti {i+1} (Hal {img_data['hal']})", use_container_width=True)
                st.caption(f"📏 Resolusi Asli: {img_data['res']}")
    
    # --- BAGIAN 5: DRAF BERITA ACARA ---
    st.header("📝 Draf Laporan Hasil Pemeriksaan")
    status_final = "REVISI / DITOLAK" if (anomali_matematika or len([x for x in results_audit if "❌" in x["Status"]]) > 0) else "DISETUJUI"
    ba_text = f"""
    BERITA ACARA DESK AUDIT DOKUMEN
    --------------------------------
    TANGGAL: {datetime.now().strftime('%d %B %Y')}
    PROYEK : REHABILITASI & RENOVASI MADRASAH PHTC
    
    1. HASIL PEMERIKSAAN MATEMATIS (TABEL KEMAJUAN FISIK):
       - {'Ditemukan ' + str(len(anomali_matematika)) + ' kesalahan kalkulasi bobot (Deviasi tidak sinkron).' if anomali_matematika else 'Integritas angka 100% akurat dan logis.'}
    
    2. HASIL VERIFIKASI BUKTI VISUAL:
       - Ditemukan {len([x for x in results_audit if "❌" in x["Status"]])} item klaim progres pekerjaan yang tidak didukung foto dokumentasi dengan keterangan yang linear.
    
    KESIMPULAN:
    Berdasarkan hasil verifikasi sistem mesin ekstraksi, dokumen laporan dinyatakan {status_final}.
    """
    st.code(ba_text, language="text")
