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

st.title("🛡️ Sistem Evaluasi Laporan PPSPM (Full Feedback Edition)")
st.markdown("Mesin verifikasi berbasis Vision AI dengan laporan status *real-time* untuk transparansi audit.")
st.markdown("---")

# ==========================================
# 2. RADAR SISTEM & MODEL SELECTION
# ==========================================
with st.sidebar:
    st.header("⚙️ Konfigurasi")
    klaim_progress_total = st.number_input("Klaim Progress Minggu Ini (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
    
    # Deteksi model secara otomatis
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception as e:
        st.error(f"Gagal akses server Google: {e}")

    # Prioritas model: 3.1 -> 2.0 -> 1.5
    # Kami menggunakan mapping nama resmi API Google
    model_options = [
        "models/gemini-1.5-flash", 
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-pro"
    ]
    
    # Cek apakah 3.1 sudah tersedia di tier akun Anda
    if any("3.1" in m for m in available_models):
        model_options.insert(0, "models/gemini-3.1-flash")

    target_model = st.selectbox("Pilih Otak AI:", model_options)
    st.caption(f"Status: Aktif menggunakan {target_model}")

# ==========================================
# 3. MODUL UPLOAD FILE
# ==========================================
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Data 1: Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah PDF Laporan", type=["pdf"])

with col2:
    st.subheader("📸 Data 2: Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah PDF Foto", type=["pdf"])

# ==========================================
# 4. MESIN EVALUASI VISION AI (DENGAN LOGGING)
# ==========================================
def ekstrak_data_vision(file_pdf, tipe):
    """Fungsi ekstraksi dengan umpan balik visual per halaman."""
    status_placeholder = st.empty()
    try:
        images = convert_from_bytes(file_pdf.read())
    except Exception as e:
        st.error(f"Gagal membaca PDF {tipe}: {e}")
        return []

    model = genai.GenerativeModel(target_model)
    results = []
    
    if tipe == "mingguan":
        prompt = "Ekstrak rincian pekerjaan konstruksi dari tabel ini. Abaikan angka, cukup ambil Lokasi dan Uraian Pekerjaan. Kembalikan HANYA format JSON: [{'lokasi': 'NAMA', 'pekerjaan': 'DESKRIPSI'}]"
    else:
        prompt = "Ekstrak teks keterangan/caption foto pembangunan ini. Kembalikan HANYA format JSON: [{'caption': 'TEKS'}]"

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        status_placeholder.info(f"⏳ Memproses {tipe}: Halaman {i+1} dari {len(images)}...")
        try:
            response = model.generate_content([prompt, img])
            # Membersihkan respon teks agar menjadi JSON murni
            raw_text = response.text
            clean_json = re.sub(r'```json|```', '', raw_text).strip()
            # Mencari pola array [ ... ]
            json_match = re.search(r'\[.*\]', clean_json, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                results.extend(data)
            else:
                st.toast(f"Halaman {i+1} {tipe}: Tidak ditemukan data pekerjaan.")
        except Exception as e:
            st.warning(f"Kendala di Halaman {i+1} {tipe}: {e}")
            time.sleep(5) # Jeda lebih lama jika error untuk reset quota
            
        time.sleep(2) # Anti-Spam API
        progress_bar.progress((i + 1) / len(images))
    
    status_placeholder.empty()
    progress_bar.empty()
    return results

# ==========================================
# 5. EKSEKUSI UTAMA
# ==========================================
if file_mingguan and file_dokumentasi:
    if st.button("🚀 MULAI AUDIT FORENSIK SEKARANG", use_container_width=True):
        if file_mingguan.name == file_dokumentasi.name:
            st.error("Gagal: File 1 dan File 2 tidak boleh sama.")
        else:
            with st.status("🔬 Menjalankan Prosedur Pemeriksaan PPSPM...", expanded=True) as status:
                st.write("Tahap 1: Membedah Laporan Mingguan...")
                data_m = ekstrak_data_vision(file_mingguan, "mingguan")
                
                st.write("Tahap 2: Membedah Laporan Dokumentasi...")
                data_f = ekstrak_data_vision(file_dokumentasi, "foto")
                
                status.update(label="Pembedahan Selesai! Menghitung Sinkronisasi...", state="complete", expanded=False)

            if not data_m:
                st.error("AI gagal mengekstrak data dari Laporan Mingguan. Pastikan PDF tidak diproteksi password.")
            elif not data_f:
                st.error("AI gagal mengekstrak data dari Laporan Dokumentasi.")
            else:
                # --- PROSES MATCHING ---
                st.subheader("📊 Hasil Matriks Verifikasi")
                captions = [str(f.get("caption", "")) for f in data_f]
                
                final_report = []
                ditolak = 0
                
                for item in data_m:
                    desc = str(item.get("pekerjaan", ""))
                    if len(desc) < 8: continue
                    
                    match, score = process.extractOne(desc, captions, scorer=fuzz.token_set_ratio)
                    res_status = "✅ VALID" if score >= 75 else "❌ DEFISIT BUKTI"
                    if res_status == "❌ DEFISIT BUKTI": ditolak += 1
                    
                    final_report.append({
                        "Lokasi": item.get("lokasi", "UMUM").upper(),
                        "Pekerjaan": desc,
                        "Status": res_status,
                        "Kesesuaian": f"{score}%",
                        "Bukti Terdeteksi": match if score >= 75 else "Nihil"
                    })
                
                df = pd.DataFrame(final_report)
                
                # Tampilkan Tabel
                st.dataframe(df, use_container_width=True)

                # --- KALKULASI FINAL ---
                total_item = len(df)
                ratio_fail = (ditolak / total_item) * 100 if total_item > 0 else 0
                val_accepted = klaim_progress_total * (1 - (ditolak/total_item)) if total_item > 0 else 0
                
                st.markdown("---")
                st.header("📝 Nota Keputusan PPSPM")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Item Pekerjaan", f"{total_item}")
                c2.metric("Defisit Bukti", f"{ditolak}", delta=f"-{ratio_fail:.1f}%", delta_color="inverse")
                c3.metric("Real Progress Disetujui", f"{val_accepted:.3f}%")

                st.warning(f"**KESIMPULAN:** Berdasarkan audit fisik digital, klaim progres {klaim_progress_total:.3f}% dikoreksi menjadi **{val_accepted:.3f}%** karena {ditolak} item pekerjaan tidak memiliki dukungan visual yang valid.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem Stand By. Harap unggah kedua dokumen PDF.")
