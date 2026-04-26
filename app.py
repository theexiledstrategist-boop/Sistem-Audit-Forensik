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

st.title("🛡️ Sistem Evaluasi Laporan PPSPM (Diagnostic Edition)")
st.markdown("Audit forensik aktif dengan transparansi log penuh. Memastikan tidak ada kegagalan buta tanpa penjelasan.")
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
        return ["gemini-2.0-flash", "gemini-1.5-flash"]

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
    file_mingguan = st.file_uploader("Unggah PDF Progress", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah PDF Foto", type=["pdf"], key="dokumentasi")

# ==========================================
# 4. MESIN EKSTRAKSI VISION AI (DENGAN REKAM MEDIS)
# ==========================================
def bedah_dokumen_dengan_ai(file_pdf, tipe_dokumen):
    status_placeholder = st.empty()
    log_diagnostik = [] # Sistem perekam jejak absolut
    results = []
    
    try:
        images = convert_from_bytes(file_pdf.read())
        log_diagnostik.append(f"[INFO] Berhasil mengonversi PDF {tipe_dokumen} menjadi {len(images)} gambar.")
    except Exception as e:
        st.error(f"Gagal membedah PDF {tipe_dokumen}: {e}")
        return [], [f"[FATAL] Gagal konversi PDF: {e}"]

    model = genai.GenerativeModel(target_model)
    
    if tipe_dokumen == "mingguan":
        prompt = """
        Anda adalah auditor sipil yang presisi. Baca tabel laporan proyek ini.
        Ekstrak HANYA daftar pekerjaan yang MENGALAMI KEMAJUAN (ada angka progresnya).
        
        Keluarkan WAJIB dalam format JSON Array murni seperti ini:
        [{"lokasi": "NAMA MADRASAH", "pekerjaan": "Uraian pekerjaan...", "progres": 2.45}]
        
        Aturan:
        - "progres" harus berupa angka desimal titik (float). Jika kosong, isi 0.0.
        - Jangan berikan penjelasan teks apa pun. Hanya JSON Array.
        - Jika halaman ini tidak berisi tabel, kembalikan: []
        """
    else:
        prompt = """
        Ekstrak teks keterangan (caption) yang menjelaskan foto proyek ini.
        Keluarkan WAJIB dalam format JSON Array murni:
        [{"caption": "Teks keterangan foto"}]
        Jika tidak ada keterangan foto yang relevan, kembalikan: []
        """

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        status_placeholder.info(f"⏳ Mengeksekusi {tipe_dokumen} halaman {i+1}/{len(images)}...")
        try:
            response = model.generate_content([prompt, img])
            
            # Mencegah ValueError jika AI diblokir Google Safety Filter
            try:
                raw_text = response.text
            except ValueError:
                log_diagnostik.append(f"[WARNING] Halaman {i+1}: Output diblokir oleh Filter Keamanan Google (Safety Rating).")
                continue

            # PEMBERSIHAN JSON BERLAPIS BAJA (ANTI HALUSINASI)
            clean_text = raw_text.replace('```json', '').replace('```', '').strip()
            
            # Mencari kurung siku pembuka dan penutup
            start_idx = clean_text.find('[')
            end_idx = clean_text.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = clean_text[start_idx:end_idx+1]
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        results.extend(data)
                        log_diagnostik.append(f"[SUKSES] Halaman {i+1}: Terekstrak {len(data)} baris data.")
                    else:
                        log_diagnostik.append(f"[ERROR] Halaman {i+1}: Format JSON bukan List/Array.")
                except json.JSONDecodeError as e:
                    log_diagnostik.append(f"[ERROR] Halaman {i+1}: JSON Cacat. Raw Output AI: {json_str[:150]}...")
            else:
                log_diagnostik.append(f"[WARNING] Halaman {i+1}: Tidak ada array [] yang dihasilkan. Raw Output AI: {raw_text[:150]}...")

        except Exception as e:
            log_diagnostik.append(f"[ERROR API] Halaman {i+1}: {str(e)}")
            time.sleep(3) 
            
        time.sleep(2) # Ritme Anti-Spam
        progress_bar.progress((i + 1) / len(images))
    
    status_placeholder.empty()
    progress_bar.empty()
    return results, log_diagnostik

# ==========================================
# 5. EKSEKUSI AUDIT (TRANSPARANSI PENUH)
# ==========================================
if file_mingguan and file_dokumentasi:
    if st.button("🚀 EKSEKUSI AUDIT PRESISI", use_container_width=True):
        if file_mingguan.name == file_dokumentasi.name:
            st.error("🚨 BLOKIR: Dokumen di kolom 1 dan 2 sama.")
        else:
            with st.status("🔬 Pembedahan Forensik Aktif...", expanded=True) as status:
                st.write("Menarik Rincian Bobot Pekerjaan...")
                data_m, log_m = bedah_dokumen_dengan_ai(file_mingguan, "mingguan")
                
                st.write("Mengkompilasi Metadata Visual...")
                data_f, log_f = bedah_dokumen_dengan_ai(file_dokumentasi, "foto")
                
                status.update(label="Kalkulasi Matematis Selesai.", state="complete", expanded=False)

            # Fitur Otoritas: Log Diagnostik (Membedah alasan kegagalan)
            with st.expander("🛠️ Buka Rekam Medis AI (Diagnostik Log - Wajib Cek Jika Gagal)"):
                st.write("**Log Ekstraksi Laporan Mingguan:**")
                for log in log_m: st.caption(log)
                st.write("---")
                st.write("**Log Ekstraksi Dokumentasi:**")
                for log in log_f: st.caption(log)

            # Lapis Pertahanan Anti-Bisu
            if not data_m:
                st.error("🚨 GAGAL AUDIT: Mesin AI mengekstrak 0 data valid dari Laporan Mingguan.")
                st.info("💡 SILAKAN BUKA 'REKAM MEDIS AI' DI ATAS. Anda akan melihat langsung alasan mengapa AI gagal: apakah karena dokumen kosong, bentuk tabel yang ditolak AI, atau halusinasi teks.")
            elif not data_f:
                st.error("🚨 GAGAL AUDIT: Mesin AI tidak menemukan caption foto di Laporan Dokumentasi.")
                st.info("💡 SILAKAN BUKA 'REKAM MEDIS AI' DI ATAS untuk melihat detail kendalanya.")
            else:
                st.subheader("📊 Matriks Verifikasi Evaluasi")
                kumpulan_caption = [str(f.get("caption", "")) for f in data_f if isinstance(f, dict)]
                
                laporan_final = []
                jumlah_item_diaudit = 0
                total_potongan_progres = 0.0
                
                for item in data_m:
                    if not isinstance(item, dict): continue
                    
                    deskripsi = str(item.get("pekerjaan", "")).strip()
                    lokasi = str(item.get("lokasi", "TIDAK SPESIFIK")).strip().upper()
                    
                    try:
                        progres = float(item.get("progres", 0.0))
                    except (ValueError, TypeError):
                        progres = 0.0
                    
                    # Logika absolut: hanya audit item yang punya bobot
                    if len(deskripsi) < 5 or progres <= 0.0: 
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

                    progres_diterima = klaim_progress_total - total_potongan_progres
                    if progres_diterima < 0: progres_diterima = 0.0 
                    
                    st.markdown("---")
                    st.header("📝 Nota Penetapan Pembayaran")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Item Aktif", f"{jumlah_item_diaudit} Item")
                    c2.metric("Nilai Progres Ditolak", f"-{total_potongan_progres:.3f}%", delta_color="inverse")
                    c3.metric("Nilai Real Disetujui", f"{progres_diterima:.3f}%")

                    st.info(f"""
                    **ANALISIS UTILITARIAN:**
                    Sistem mengisolasi **{jumlah_item_diaudit}** item pekerjaan yang aktif diklaim minggu ini. 
                    
                    **EKSEKUSI PEMOTONGAN:**
                    Ditemukan defisit dokumentasi visual. Tagihan dikurangi eksak **{total_potongan_progres:.3f}%** sesuai bobot rincian pekerjaan yang fiktif.
                    
                    **KEPUTUSAN SPM:**
                    Surat Perintah Membayar direkomendasikan maksimal sebesar **{progres_diterima:.3f}%**.
                    """)
                else:
                    st.warning("⚠️ HASIL NIHIL: Dokumen berhasil dibedah, namun tidak ada pekerjaan dengan progres > 0.0. Silakan cek 'Rekam Medis AI' untuk memastikan.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem dalam Status Stand By. Menunggu otorisasi dokumen.")
