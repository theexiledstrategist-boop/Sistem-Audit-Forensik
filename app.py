import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
from pdf2image import convert_from_bytes
import google.generativeai as genai
import json
import re
import time

# ==========================================
# 1. KONFIGURASI SISTEM & OTORISASI
# ==========================================
st.set_page_config(page_title="Audit Forensik PPSPM", page_icon="🛡️", layout="wide")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except KeyError:
    st.error("FATAL ERROR: API Key belum dikonfigurasi di Streamlit Secrets.")
    st.stop()

st.title("🛡️ Sistem Evaluasi Laporan PPSPM (Absolute Precision)")
st.markdown("Audit forensik yang hanya mengeksekusi item dengan nilai progres aktif. Memastikan pemotongan tagihan didasarkan pada perhitungan matematis yang sah secara hukum.")
st.markdown("---")

# ==========================================
# 2. RADAR MODEL OTOMATIS
# ==========================================
@st.cache_data(ttl=3600)
def dapatkan_daftar_model_sah():
    model_tersedia = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower():
                model_tersedia.append(m.name.replace('models/', ''))
        return model_tersedia
    except Exception as e:
        return ["gemini-1.5-flash"]

daftar_model_resmi = dapatkan_daftar_model_sah()

with st.sidebar:
    st.header("⚙️ Parameter Kontrak Utama")
    klaim_progress_total = st.number_input("Klaim Progress Minggu Ini (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
    
    st.markdown("---")
    st.subheader("🧠 Otak Analitik API")
    target_model = st.selectbox("Versi Mesin:", daftar_model_resmi)

# ==========================================
# 3. MODUL UPLOAD DOKUMEN
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah PDF Progress", type=["pdf"])

with col2:
    st.subheader("📸 Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah PDF Foto", type=["pdf"])

# ==========================================
# 4. MESIN EKSTRAKSI VISION AI (PENGGALI ANGKA)
# ==========================================
def bedah_dokumen_dengan_ai(file_pdf, tipe_dokumen):
    status_placeholder = st.empty()
    try:
        images = convert_from_bytes(file_pdf.read())
    except Exception as e:
        st.error(f"Gagal membedah PDF {tipe_dokumen}: {e}")
        return []

    model = genai.GenerativeModel(target_model)
    results = []
    
    if tipe_dokumen == "mingguan":
        prompt = """
        Sebagai auditor, bedah tabel kemajuan fisik ini secara presisi.
        Ekstrak 3 data: 
        1. Nama Lokasi
        2. Uraian Pekerjaan
        3. Nilai angka pada kolom "Progres Minggu Ini" (ubah koma menjadi titik untuk desimal. Contoh: 2,50 menjadi 2.5). Jika kosong/tidak ada progres, isi 0.0.
        
        WAJIB kembalikan format JSON murni: 
        [{"lokasi": "NAMA", "pekerjaan": "DESKRIPSI", "progres": 0.00}]
        """
    else:
        prompt = """
        Baca keterangan (caption) pada foto dokumentasi proyek ini.
        WAJIB kembalikan format JSON murni: [{"caption": "TEKS KETERANGAN FOTO"}]
        """

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        status_placeholder.info(f"⏳ Mengeksekusi {tipe_dokumen} halaman {i+1}/{len(images)}...")
        try:
            response = model.generate_content([prompt, img])
            clean_text = re.sub(r'```json|```', '', response.text).strip()
            match = re.search(r'\[.*\]', clean_text, re.DOTALL)
            
            if match:
                data = json.loads(match.group(0))
                results.extend(data)
        except Exception as e:
            time.sleep(3) 
            
        time.sleep(2) 
        progress_bar.progress((i + 1) / len(images))
    
    status_placeholder.empty()
    progress_bar.empty()
    return results

# ==========================================
# 5. EKSEKUSI AUDIT EKSKLUSIF (HANYA ITEM AKTIF)
# ==========================================
if file_mingguan and file_dokumentasi:
    if st.button("🚀 EKSEKUSI AUDIT PRESISI", use_container_width=True):
        if file_mingguan.name == file_dokumentasi.name:
            st.error("🚨 BLOKIR: Dokumen di kolom 1 dan 2 sama.")
        else:
            with st.status(f"🔬 Pembedahan Forensik Aktif...", expanded=True) as status:
                st.write("Menarik Rincian Bobot Pekerjaan...")
                data_m = bedah_dokumen_dengan_ai(file_mingguan, "mingguan")
                
                st.write("Mengkompilasi Metadata Visual...")
                data_f = bedah_dokumen_dengan_ai(file_dokumentasi, "foto")
                
                status.update(label="Kalkulasi Matematis Selesai.", state="complete", expanded=False)

            if data_m and data_f:
                st.subheader("📊 Matriks Verifikasi Evaluasi")
                kumpulan_caption = [str(f.get("caption", "")) for f in data_f if isinstance(f, dict)]
                
                laporan_final = []
                jumlah_item_diaudit = 0
                total_potongan_progres = 0.0
                
                for item in data_m:
                    if not isinstance(item, dict): continue
                    
                    deskripsi = str(item.get("pekerjaan", "")).strip()
                    lokasi = str(item.get("lokasi", "TIDAK SPESIFIK")).strip().upper()
                    
                    # Konversi progres dengan aman
                    try:
                        progres = float(item.get("progres", 0.0))
                    except (ValueError, TypeError):
                        progres = 0.0
                    
                    # LOGIKA FILTER ABSOLUT: 
                    # Jika tidak ada pekerjaan atau progresnya 0, abaikan (jangan diaudit)
                    if len(deskripsi) < 10 or progres <= 0.0: 
                        continue
                        
                    jumlah_item_diaudit += 1
                    
                    match, score = process.extractOne(deskripsi, kumpulan_caption, scorer=fuzz.token_set_ratio)
                    status_kelayakan = "✅ VALID" if score >= 75 else "❌ DEFISIT"
                    
                    if status_kelayakan == "❌ DEFISIT":
                        total_potongan_progres += progres
                        
                    laporan_final.append({
                        "Lokasi": lokasi,
                        "Uraian Pekerjaan Aktif": deskripsi,
                        "Klaim (%)": progres,
                        "Status": status_kelayakan,
                        "Bukti Visual": match if score >= 75 else "Nihil"
                    })
                
                if laporan_final:
                    df = pd.DataFrame(laporan_final)
                    
                    try:
                        st.dataframe(df.style.map(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT" else '', subset=['Status']), use_container_width=True)
                    except AttributeError:
                        st.dataframe(df.style.applymap(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT" else '', subset=['Status']), use_container_width=True)

                    # ==========================================
                    # 6. KEPUTUSAN FINAL BERDASARKAN BOBOT EKSAK
                    # ==========================================
                    progres_diterima = klaim_progress_total - total_potongan_progres
                    # Pencegah minus jika potongan OCR salah deteksi angka melebihi klaim total
                    if progres_diterima < 0: progres_diterima = 0.0 
                    
                    st.markdown("---")
                    st.header("📝 Nota Penetapan Pembayaran")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Item Aktif", f"{jumlah_item_diaudit} Item", help="Hanya pekerjaan yang progresnya > 0% minggu ini yang diaudit.")
                    c2.metric("Nilai Progres Ditolak", f"-{total_potongan_progres:.3f}%", delta_color="inverse")
                    c3.metric("Nilai Real Disetujui", f"{progres_diterima:.3f}%")

                    st.info(f"""
                    **ANALISIS UTILITARIAN:**
                    Dari total daftar pekerjaan, sistem hanya mengisolasi **{jumlah_item_diaudit}** item pekerjaan yang secara aktif diklaim mengalami kemajuan pada minggu ini. 
                    
                    **EKSEKUSI PEMOTONGAN:**
                    Ditemukan defisit dokumentasi visual pada item-item aktif tersebut. Berdasarkan perhitungan bobot progres spesifik dari item yang fiktif, ditetapkan bahwa nilai tagihan harus dikurangi sebesar eksak **{total_potongan_progres:.3f}%**.
                    
                    **KEPUTUSAN SPM:**
                    Rekomendasi nilai maksimal Surat Perintah Membayar (SPM) yang memiliki landasan hukum empiris untuk dicairkan adalah sebesar **{progres_diterima:.3f}%**.
                    """)
                else:
                    st.warning("Tidak ditemukan pekerjaan dengan progres > 0% pada laporan ini.")
