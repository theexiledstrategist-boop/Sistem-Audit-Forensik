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
st.markdown("Audit forensik aktif. Dilengkapi dengan **Sistem Pemutus Arus Darurat** dan **Pacing Maksimal (14 RPM)** untuk efisiensi waktu tertinggi di jalur gratis.")
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
        return ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"]

daftar_model_resmi = dapatkan_daftar_model_sah()

with st.sidebar:
    st.header("⚙️ Parameter Kontrak Utama")
    klaim_progress_total = st.number_input("Klaim Progress Minggu Ini (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
    
    st.markdown("---")
    st.subheader("🧠 Otak Analitik API")
    st.caption("PENTING: Gunakan model dengan batas RPD besar (misal: 3.1-flash-lite) untuk dokumen tebal.")
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
# 4. MESIN EKSTRAKSI (14 RPM + CIRCUIT BREAKER)
# ==========================================
def bedah_dokumen_dengan_ai(file_pdf, tipe_dokumen):
    status_placeholder = st.empty()
    log_diagnostik = [] 
    results = []
    
    try:
        images = convert_from_bytes(file_pdf.read())
        log_diagnostik.append(f"[INFO] Berhasil mengonversi PDF {tipe_dokumen} menjadi {len(images)} gambar.")
    except Exception as e:
        st.error(f"Gagal membedah PDF {tipe_dokumen}: {e}")
        return [], [f"[FATAL] Gagal konversi PDF: {e}"], False

    model = genai.GenerativeModel(target_model)
    
    if tipe_dokumen == "mingguan":
        prompt = """
        Anda adalah auditor forensik. Bedah gambar tabel ini.
        Tugas Anda adalah mengekstrak daftar rincian pekerjaan konstruksi.
        
        Aturan Ekstraksi:
        1. "lokasi": Nama madrasah/lokasi (jika tidak ada, isi "TIDAK SPESIFIK").
        2. "pekerjaan": Deskripsi pekerjaan (perbaiki ejaan jika buram).
        3. "progres": Cari angka kemajuan fisik/bobot persentase TERBARU atau MINGGU INI. Jika bentuknya desimal koma (misal 2,45), ubah wajib jadi titik (2.45). Jika kolom progres kosong/tidak terbaca, WAJIB isi 0.0.
        
        Keluarkan HANYA dalam format array JSON murni tanpa teks awalan/akhiran apa pun:
        [
          {"lokasi": "MIS ALAM", "pekerjaan": "Pasang Bata", "progres": 1.25},
          {"lokasi": "MIS ALAM", "pekerjaan": "Plesteran", "progres": 0.0}
        ]
        
        WAJIB kembalikan array JSON. Jangan pernah kembalikan array kosong [] jika ada teks pekerjaan di halaman ini.
        """
    else:
        prompt = """
        Ekstrak semua keterangan teks (caption) yang ada pada foto dokumentasi ini.
        Keluarkan HANYA format array JSON murni:
        [{"caption": "Teks keterangan foto 1"}, {"caption": "Teks keterangan foto 2"}]
        """

    progress_bar = st.progress(0)
    darurat_berhenti = False

    for i, img in enumerate(images):
        status_placeholder.info(f"⏳ Mengeksekusi {tipe_dokumen} halaman {i+1}/{len(images)}... (Memacu di 14 RPM)")
        try:
            response = model.generate_content([prompt, img])
            
            try:
                raw_text = response.text
            except ValueError:
                log_diagnostik.append(f"[WARNING] Halaman {i+1}: Output diblokir oleh Filter Keamanan Google.")
                continue

            clean_text = raw_text.replace('```json', '').replace('```', '').strip()
            start_idx = clean_text.find('[')
            end_idx = clean_text.rfind(']')
            
            if start_idx != -1 and end_idx != -1:
                json_str = clean_text[start_idx:end_idx+1]
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        results.extend(data)
                        log_diagnostik.append(f"[SUKSES] Halaman {i+1}: Terekstrak {len(data)} baris data.")
                except json.JSONDecodeError:
                    log_diagnostik.append(f"[ERROR] Halaman {i+1}: JSON Cacat.")
            else:
                log_diagnostik.append(f"[WARNING] Halaman {i+1}: Tidak ada array [] yang dihasilkan.")

        except Exception as e:
            pesan_error = str(e).lower()
            # SISTEM PEMUTUS ARUS (CIRCUIT BREAKER)
            if "429" in pesan_error or "quota" in pesan_error:
                log_diagnostik.append(f"[FATAL/429] Halaman {i+1}: Kuota API Habis/Terblokir. MENGHENTIKAN SISA HALAMAN SECARA PAKSA.")
                darurat_berhenti = True
                break # LANGSUNG HENTIKAN LOOP, JANGAN DILANJUTKAN
            else:
                log_diagnostik.append(f"[ERROR] Halaman {i+1}: {pesan_error[:50]}")
            
        # MANUVER KECEPATAN MAKSIMAL (Tepat 14 RPM)
        # 60 detik / 14 request = 4.28 detik per request
        time.sleep(4.3) 
        progress_bar.progress((i + 1) / len(images))
    
    status_placeholder.empty()
    progress_bar.empty()
    return results, log_diagnostik, darurat_berhenti

# ==========================================
# 5. EKSEKUSI AUDIT 
# ==========================================
if file_mingguan and file_dokumentasi:
    if st.button("🚀 EKSEKUSI AUDIT PRESISI", use_container_width=True):
        if file_mingguan.name == file_dokumentasi.name:
            st.error("🚨 BLOKIR: Dokumen di kolom 1 dan 2 sama.")
        else:
            with st.status("🔬 Pembedahan Forensik Aktif (Memacu 14 RPM)...", expanded=True) as status:
                st.write("Menarik Rincian Bobot Pekerjaan...")
                data_m, log_m, henti_m = bedah_dokumen_dengan_ai(file_mingguan, "mingguan")
                
                if henti_m:
                    st.error("Sistem Pemutus Arus Aktif: Ekstraksi Laporan Mingguan dihentikan paksa karena Kuota API Habis.")
                    data_f, log_f, henti_f = [], [], True
                else:
                    st.write("Mengkompilasi Metadata Visual...")
                    data_f, log_f, henti_f = bedah_dokumen_dengan_ai(file_dokumentasi, "foto")
                
                status.update(label="Proses Selesai.", state="complete", expanded=False)

            with st.expander("🛠️ Buka Rekam Medis AI (Diagnostik Log)"):
                st.write("**Log Ekstraksi Laporan Mingguan:**")
                for log in log_m: st.caption(log)
                st.write("---")
                st.write("**Log Ekstraksi Dokumentasi:**")
                for log in log_f: st.caption(log)

            if henti_m or henti_f:
                st.error("🚨 OPERASI DIBATALKAN: Anda menabrak batas Kuota Harian (RPD) Google. Silakan ganti Versi Mesin ke model yang kuotanya masih banyak (misal: 3.1 Flash Lite) di panel kiri, lalu coba lagi.")
            elif not data_m:
                st.error("🚨 GAGAL AUDIT: 0 data valid dari Laporan Mingguan.")
            elif not data_f:
                st.error("🚨 GAGAL AUDIT: 0 caption foto ditemukan.")
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
                else:
                    st.warning("⚠️ HASIL NIHIL: Tidak ada pekerjaan dengan progres > 0.0.")
