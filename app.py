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
st.markdown("Menggunakan *Vision AI* dengan ekstraksi model dinamis untuk memastikan stabilitas server dan ketelitian pembacaan dokumen.")
st.markdown("---")

# ==========================================
# 2. RADAR MODEL OTOMATIS (ANTI-404 ERROR)
# ==========================================
@st.cache_data(ttl=3600) # Menyimpan cache selama 1 jam agar tidak memberatkan server
def dapatkan_daftar_model_sah():
    model_tersedia = []
    try:
        for m in genai.list_models():
            # Hanya mengambil model yang bisa menghasilkan teks/baca gambar dan keluarga Gemini
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower():
                # Membersihkan nama model dari awalan 'models/' agar lebih rapi di tampilan
                nama_bersih = m.name.replace('models/', '')
                model_tersedia.append(nama_bersih)
        return model_tersedia
    except Exception as e:
        st.error(f"Gagal menarik daftar model dari Google: {e}")
        return ["gemini-1.5-flash"] # Fallback darurat

daftar_model_resmi = dapatkan_daftar_model_sah()

with st.sidebar:
    st.header("⚙️ Konfigurasi Sistem")
    klaim_progress_total = st.number_input("Klaim Progress Diajukan (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
    
    st.markdown("---")
    st.subheader("🧠 Pilih Otak AI")
    st.caption("Daftar di bawah ini ditarik langsung dari server Google berdasarkan API Key Anda. Bebas error 404.")
    
    # Menjadikan daftar resmi sebagai pilihan dropdown
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
# 4. MESIN EKSTRAKSI VISION AI
# ==========================================
def bedah_dokumen_dengan_ai(file_pdf, tipe_dokumen):
    status_placeholder = st.empty()
    try:
        images = convert_from_bytes(file_pdf.read())
    except Exception as e:
        st.error(f"Gagal membedah PDF {tipe_dokumen}: {e}")
        return []

    # Menggunakan model yang dipilih user dari dropdown
    model = genai.GenerativeModel(target_model)
    results = []
    
    if tipe_dokumen == "mingguan":
        prompt = """
        Sebagai auditor teknik sipil, periksa tabel laporan ini. 
        Abaikan angka dan garis. Ekstrak HANYA nama lokasi dan deskripsi pekerjaannya. 
        Perbaiki ejaan typo jika ada.
        WAJIB kembalikan dalam format JSON murni ini: [{"lokasi": "NAMA", "pekerjaan": "DESKRIPSI"}]
        Jika halaman kosong/bukan tabel, kembalikan []
        """
    else:
        prompt = """
        Sebagai auditor teknik sipil, baca keterangan (caption) pada foto dokumentasi ini.
        WAJIB kembalikan dalam format JSON murni ini: [{"caption": "TEKS KETERANGAN FOTO"}]
        Jika tidak ada keterangan, kembalikan []
        """

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        status_placeholder.info(f"⏳ Mesin {target_model} sedang membedah {tipe_dokumen} halaman {i+1}/{len(images)}...")
        try:
            response = model.generate_content([prompt, img])
            # Regex untuk memastikan AI hanya memberikan JSON
            clean_text = re.sub(r'```json|```', '', response.text).strip()
            match = re.search(r'\[.*\]', clean_text, re.DOTALL)
            
            if match:
                data = json.loads(match.group(0))
                results.extend(data)
            else:
                st.toast(f"Halaman {i+1} ({tipe_dokumen}): Tidak ada data terekstrak.")
        except Exception as e:
            st.warning(f"Resistensi di Halaman {i+1} ({tipe_dokumen}): {e}")
            time.sleep(4) # Jeda pemulihan jika server Google menolak
            
        time.sleep(2.5) # Jeda ritmis untuk mencegah blokir Anti-Spam
        progress_bar.progress((i + 1) / len(images))
    
    status_placeholder.empty()
    progress_bar.empty()
    return results

# ==========================================
# 5. EKSEKUSI AUDIT FORENSIK
# ==========================================
if file_mingguan and file_dokumentasi:
    if st.button("🚀 EKSEKUSI AUDIT SEKARANG", use_container_width=True):
        if file_mingguan.name == file_dokumentasi.name:
            st.error("🚨 BLOKIR ADMINISTRATIF: Dokumen di kolom 1 dan kolom 2 adalah file yang sama.")
        else:
            with st.status(f"🔬 Menjalankan Prosedur Audit dengan {target_model}...", expanded=True) as status:
                st.write("Tahap 1: Mengekstrak Data Teknis Laporan Mingguan...")
                data_m = bedah_dokumen_dengan_ai(file_mingguan, "mingguan")
                
                st.write("Tahap 2: Memverifikasi Metadata Bukti Dokumentasi...")
                data_f = bedah_dokumen_dengan_ai(file_dokumentasi, "foto")
                
                status.update(label="Pembedahan Selesai! Mengkalkulasi Rasio Validitas...", state="complete", expanded=False)

            if not data_m:
                st.error("Gagal menarik data dari Laporan Mingguan. Pastikan resolusi scan dapat dibaca.")
            elif not data_f:
                st.error("Gagal menarik data dari Laporan Dokumentasi.")
            else:
                st.subheader("📊 Matriks Verifikasi Visual & Administratif")
                kumpulan_caption = [str(f.get("caption", "")) for f in data_f if isinstance(f, dict)]
                
                laporan_final = []
                jumlah_ditolak = 0
                
                for item in data_m:
                    if not isinstance(item, dict): continue
                    
                    deskripsi = str(item.get("pekerjaan", "")).strip()
                    lokasi = str(item.get("lokasi", "TIDAK SPESIFIK")).strip().upper()
                    
                    if len(deskripsi) < 10: continue
                    
                    # Logika Korelasi Semantik
                    match, score = process.extractOne(deskripsi, kumpulan_caption, scorer=fuzz.token_set_ratio)
                    status_kelayakan = "✅ VALID" if score >= 75 else "❌ DEFISIT BUKTI"
                    
                    if status_kelayakan == "❌ DEFISIT BUKTI":
                        jumlah_ditolak += 1
                        
                    laporan_final.append({
                        "Lokasi Kritis": lokasi,
                        "Uraian Pekerjaan": deskripsi,
                        "Integritas Data": status_kelayakan,
                        "Kesesuaian": f"{score}%",
                        "Bukti Lapangan": match if score >= 75 else "Nihil / Celah Ditemukan"
                    })
                
                df = pd.DataFrame(laporan_final)
                
                # Rendering Tabel Anti-Crash
                try:
                    st.dataframe(df.style.map(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Integritas Data']), use_container_width=True)
                except AttributeError:
                    st.dataframe(df.style.applymap(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Integritas Data']), use_container_width=True)

                # ==========================================
                # 6. KEPUTUSAN FINAL PPSPM
                # ==========================================
                total_pekerjaan = len(df)
                rasio_gagal = (jumlah_ditolak / total_pekerjaan) * 100 if total_pekerjaan > 0 else 0
                progres_diterima = klaim_progress_total * (1 - (jumlah_ditolak / total_pekerjaan)) if total_pekerjaan > 0 else 0
                
                st.markdown("---")
                st.header("📝 Nota Keputusan Pencairan")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Klaim Pekerjaan", f"{total_pekerjaan} Item")
                c2.metric("Pekerjaan Fiktif/Tanpa Bukti", f"{jumlah_ditolak} Item", delta=f"-{rasio_gagal:.1f}%", delta_color="inverse")
                c3.metric("Batas Aman Progres (Disetujui)", f"{progres_diterima:.3f}%")

                lokasi_bermasalah = df[df['Integritas Data'] == '❌ DEFISIT BUKTI']['Lokasi Kritis'].unique().tolist()
                teks_lokasi = ", ".join(lokasi_bermasalah) if lokasi_bermasalah else "Nihil"

                st.warning(f"""
                **EVALUASI OTORITAS PENUH:**
                Pihak rekanan mengajukan klaim sebesar **{klaim_progress_total:.3f}%**. Berdasarkan uji forensik digital, rasio cacat administratif dan visual mencapai **{rasio_gagal:.1f}%**. 
                
                **ZONA RISIKO:**
                Deviasi antara laporan tertulis dan bukti fisik terkonsentrasi di: **{teks_lokasi}**.
                
                **KEPUTUSAN:**
                Sebagai instrumen pengendalian risiko keuangan negara, persetujuan penuh ditolak. Rekomendasi Surat Perintah Membayar (SPM) hanya dapat diproses untuk nilai riil sebesar **{progres_diterima:.3f}%**. Sisa tagihan ditangguhkan hingga rekanan dapat melampirkan dokumentasi komprehensif yang tidak terbantahkan.
                """)

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem dalam Status Stand By. Menunggu otorisasi dokumen.")
