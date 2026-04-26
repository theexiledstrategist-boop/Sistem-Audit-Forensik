import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
from pdf2image import convert_from_bytes
import google.generativeai as genai
import json
import re
import time
import io

# ==========================================
# 1. KONFIGURASI SISTEM & API
# ==========================================
st.set_page_config(page_title="Evaluasi Laporan PPSPM", page_icon="🛡️", layout="wide")

# Otentikasi API Key
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("FATAL ERROR: API Key belum dikonfigurasi di Streamlit Secrets.")
    st.stop()

st.title("🛡️ Sistem Evaluasi Laporan PPSPM (Absolute Edition)")
st.markdown("""
Sistem audit digital berbasis **Vision AI** untuk memverifikasi klaim progres fisik konstruksi terhadap bukti dokumentasi lapangan dengan standar ketelitian tanpa kompromi.
""")
st.markdown("---")

# ==========================================
# 2. RADAR SISTEM: DETEKSI MODEL TERBARU
# ==========================================
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    klaim_progress_total = st.number_input("Klaim Progress Minggu Ini (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
    
    with st.expander("🛠️ Radar Sistem: Cek Versi AI"):
        model_names = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    model_names.append(m.name)
            st.write("Model tersedia:")
            st.code("\n".join(model_names))
        except Exception:
            st.write("Gagal menarik daftar model.")
    
    # Pilih Model Tertinggi secara otomatis (Prioritas: 3.1 > 2.0 > 1.5)
    selected_model = "gemini-1.5-flash" # Default
    priorities = ["gemini-3.1-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash"]
    for p in priorities:
        if any(p in name for name in model_names):
            selected_model = p
            break
    
    st.success(f"Menggunakan Otak: {selected_model}")

# ==========================================
# 3. MODUL UPLOAD FILE
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Data 1: Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah PDF Laporan", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Data 2: Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah PDF Foto", type=["pdf"], key="dokumentasi")

if file_mingguan and file_dokumentasi and file_mingguan.name == file_dokumentasi.name:
    st.error("🚨 Kesalahan Input: Anda mengunggah file yang sama di kedua kotak.")
    st.stop()

# ==========================================
# 4. MESIN EVALUASI VISION AI
# ==========================================
def ekstrak_data_vision(file_pdf, tipe):
    images = convert_from_bytes(file_pdf.read())
    model = genai.GenerativeModel(selected_model)
    results = []
    
    if tipe == "mingguan":
        prompt = """Bertindaklah sebagai auditor teknik sipil. Ekstrak rincian pekerjaan dari tabel kemajuan fisik ini. 
        Abaikan angka numerik yang rumit, cukup ambil:
        1. Nama Madrasah/Lokasi (MIS atau MTSS).
        2. Deskripsi Pekerjaan (Gunakan istilah teknis yang baku, perbaiki typo OCR).
        Kembalikan HANYA format JSON: [{"lokasi": "NAMA", "pekerjaan": "DESKRIPSI"}]"""
    else:
        prompt = """Ekstrak teks caption/keterangan yang ada di bawah atau samping foto. 
        Perbaiki ejaan jika ada kesalahan baca.
        Kembalikan HANYA format JSON: [{"caption": "TEKS"}]"""

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        try:
            response = model.generate_content([prompt, img])
            clean_json = re.sub(r'```json|```', '', response.text).strip()
            data = json.loads(re.search(r'\[.*\]', clean_json, re.DOTALL).group(0))
            results.extend(data)
        except Exception:
            pass
        time.sleep(3.5) # Anti-Rate Limit
        progress_bar.progress((i + 1) / len(images))
    progress_bar.empty()
    return results

# ==========================================
# 5. EKSEKUSI AUDIT & NARASI
# ==========================================
if file_mingguan and file_dokumentasi:
    if st.button("🚀 JALANKAN AUDIT FORENSIK", use_container_width=True):
        with st.spinner(f"AI sedang membedah dokumen menggunakan model {selected_model}..."):
            data_m = ekstrak_data_vision(file_mingguan, "mingguan")
            data_f = ekstrak_data_vision(file_dokumentasi, "foto")
            
            if data_m and data_f:
                st.subheader("📊 Matriks Verifikasi Presisi")
                captions = [f.get("caption", "") for f in data_f]
                
                final_report = []
                ditolak = 0
                for item in data_m:
                    desc = item.get("pekerjaan", "")
                    if len(desc) < 10: continue
                    
                    match, score = process.extractOne(desc, captions, scorer=fuzz.token_set_ratio)
                    status = "✅ VALID" if score >= 75 else "❌ DEFISIT BUKTI"
                    if status == "❌ DEFISIT BUKTI": ditolak += 1
                    
                    final_report.append({
                        "Lokasi (Pin-Point)": item.get("lokasi", "").upper(),
                        "Uraian Pekerjaan": desc,
                        "Kelayakan": status,
                        "Bukti di Lapangan": match if score >= 75 else "Tidak Terdokumentasi"
                    })
                
                df = pd.DataFrame(final_report)
                
                # Render Tabel Anti-Error (Pandas 2.x Support)
                try:
                    st.dataframe(df.style.map(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Kelayakan']), use_container_width=True)
                except AttributeError:
                    st.dataframe(df.style.applymap(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Kelayakan']), use_container_width=True)

                # --- NARASI KEPUTUSAN ---
                ratio_fail = (ditolak / len(df)) * 100
                val_accepted = klaim_progress_total * (1 - (ditolak/len(df)))
                
                st.markdown("---")
                st.header("📝 Nota Keputusan PPSPM")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Item Pekerjaan", f"{len(df)}")
                c2.metric("Defisit Visual", f"{ditolak}", delta=f"-{ratio_fail:.1f}%", delta_color="inverse")
                c3.metric("Real Progress Diterima", f"{val_accepted:.3f}%")

                lokasi_merah = df[df['Kelayakan'] == '❌ DEFISIT BUKTI']['Lokasi (Pin-Point)'].unique().tolist()
                
                st.warning(f"""
                **KESIMPULAN EVALUASI:**
                Berdasarkan audit silang, ditemukan tingkat validitas data sebesar **{(100-ratio_fail):.1f}%**. Sebanyak **{ditolak}** item pekerjaan terindikasi fiktif atau tidak memiliki dukungan bukti visual.
                
                **LOKASI PIN-POINT MASALAH:**
                Penyimpangan data terkonsentrasi di: **{", ".join(lokasi_merah) if lokasi_merah else "Nihil"}**.
                
                **KEPUTUSAN ADMINISTRATIF:**
                Surat Perintah Membayar (SPM) disarankan untuk ditangguhkan sebagian. Nilai progres yang aman untuk diakui saat ini hanya **{val_accepted:.3f}%**. Kontraktor wajib melakukan perbaikan laporan atau opname fisik ulang untuk sisa selisihnya.
                """)
