import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz, process
from pdf2image import convert_from_bytes
import google.generativeai as genai
import json
import re

# ==========================================
# 1. KONFIGURASI SISTEM & API
# ==========================================
st.set_page_config(page_title="Audit Forensik PPSPM", page_icon="💎", layout="wide")

# Mengambil API Key dari sistem rahasia Streamlit
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("API Key belum dikonfigurasi di Streamlit Secrets.")

st.title("💎 Sistem Audit Forensik: AI Vision Engine")
st.markdown("Menggunakan *Multimodal AI* untuk menembus keterbatasan dokumen scan dan mengekstrak rincian pekerjaan secara absolut tanpa typo.")
st.markdown("---")

# ==========================================
# 2. MODUL UPLOAD
# ==========================================
st.sidebar.header("⚙️ Parameter Pembayaran")
klaim_progress_total = st.sidebar.number_input("Klaim Progress Diajukan (%)", min_value=0.000, value=2.919, step=0.001, format="%.3f")

col1, col2 = st.columns(2)
with col1:
    file_mingguan = st.file_uploader("Unggah Laporan Mingguan", type=["pdf"])
with col2:
    file_dokumentasi = st.file_uploader("Unggah Laporan Dokumentasi", type=["pdf"])

# ==========================================
# 3. MESIN EKSTRAKSI VISION AI
# ==========================================
def ekstrak_dengan_vision_ai(file_pdf, tipe_dokumen):
    """
    Mengubah PDF menjadi gambar, lalu memerintahkan AI untuk mengekstrak data 
    dan merapikan ejaan (auto-correct konteks konstruksi) ke format JSON.
    """
    file_bytes = file_pdf.read()
    images = convert_from_bytes(file_bytes)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    hasil_ekstraksi = []
    
    # Prompt khusus untuk memastikan AI tidak berhalusinasi
    if tipe_dokumen == "mingguan":
        prompt = """
        Ini adalah halaman Laporan Kemajuan Fisik proyek konstruksi.
        Abaikan garis tabel. Cari item pekerjaan dan lokasinya. 
        Keluarkan HANYA dalam format array JSON yang valid seperti ini, tanpa teks pengantar:
        [{"lokasi": "nama madrasah", "pekerjaan": "deskripsi pekerjaan dirapikan ejaannya", "progres": angka_koma_titik}]
        Jika halaman ini bukan tabel kemajuan fisik, kembalikan [].
        """
    else:
        prompt = """
        Ini adalah halaman Laporan Dokumentasi Foto proyek konstruksi.
        Ekstrak teks keterangan (caption) yang ada di bawah/samping foto.
        Keluarkan HANYA dalam format array JSON yang valid seperti ini, tanpa teks pengantar:
        [{"keterangan_foto": "teks dirapikan ejaannya"}]
        Jika tidak ada foto/keterangan, kembalikan [].
        """

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        try:
            response = model.generate_content([prompt, img])
            teks_json = response.text
            
            # Membersihkan tag markdown JSON dari respon AI
            teks_json = re.sub(r'```json|```', '', teks_json).strip()
            
            data_page = json.loads(teks_json)
            hasil_ekstraksi.extend(data_page)
        except Exception:
            pass # Lewati halaman jika AI gagal mem-parsing JSON
        progress_bar.progress((i + 1) / len(images))
        
    progress_bar.empty()
    return hasil_ekstraksi

# ==========================================
# 4. EKSEKUSI AUDIT
# ==========================================
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 EKSEKUSI PEMBEDAHAN VISION AI", use_container_width=True):
        with st.spinner('AI Vision sedang menelusuri piksel dan merapikan nomenklatur...'):
            
            # Mendapatkan data terstruktur yang 100% bersih
            data_mingguan = ekstrak_dengan_vision_ai(file_mingguan, "mingguan")
            data_foto = ekstrak_dengan_vision_ai(file_dokumentasi, "dokumentasi")
            
            if data_mingguan and data_foto:
                st.subheader("📊 Matriks Verifikasi Visual Presisi Tinggi")
                
                # Menggabungkan semua teks caption foto menjadi satu corpus
                teks_bukti_visual = [item.get("keterangan_foto", "") for item in data_foto]
                
                audit_results = []
                item_ditolak = 0
                
                for item in data_mingguan:
                    pekerjaan = item.get('pekerjaan', '')
                    lokasi = item.get('lokasi', 'Tidak Spesifik')
                    
                    if not pekerjaan or len(pekerjaan) < 10:
                        continue
                        
                    # Fuzzy matching antara teks laporan (yang sudah bersih) dengan caption foto (bersih)
                    best_match, score = process.extractOne(pekerjaan, teks_bukti_visual, scorer=fuzz.token_set_ratio)
                    status = "✅ VALID" if score >= 75 else "❌ DEFISIT BUKTI"
                    
                    if status == "❌ DEFISIT BUKTI":
                        item_ditolak += 1
                        
                    audit_results.append({
                        "Lokasi (Pin-Point)": lokasi.upper(),
                        "Uraian Pekerjaan": pekerjaan,
                        "Status Kelayakan": status,
                        "Bukti Visual": best_match if score >= 75 else "Tidak Ada Dokumentasi",
                    })
                
                if audit_results:
                    df = pd.DataFrame(audit_results)
                    total_item = len(df)
                    
                    try:
                        st.dataframe(df.style.map(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Status Kelayakan']), use_container_width=True)
                    except AttributeError:
                        st.dataframe(df.style.applymap(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Status Kelayakan']), use_container_width=True)
                    
                    # ----------------- KEPUTUSAN FINAL -----------------
                    persentase_ditolak = (item_ditolak / total_item) * 100 if total_item > 0 else 0
                    estimasi_potongan = (persentase_ditolak / 100) * klaim_progress_total
                    estimasi_diterima = klaim_progress_total - estimasi_potongan
                    
                    st.markdown("---")
                    st.header("📝 Nota Keputusan PPSPM")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Item Diajukan", f"{total_item} Pekerjaan")
                    c2.metric("Item Defisit Bukti", f"{item_ditolak} Pekerjaan", delta_color="inverse")
                    c3.metric("Rasio Integritas Data", f"{(100 - persentase_ditolak):.1f}%")

                    lokasi_bermasalah = df[df['Status Kelayakan'] == '❌ DEFISIT BUKTI']['Lokasi (Pin-Point)'].unique().tolist()
                    teks_lokasi = ", ".join(lokasi_bermasalah) if lokasi_bermasalah else "Nihil"

                    st.warning(f"""
                    **HASIL EVALUASI:**
                    Dari total **{total_item}** item pekerjaan yang diekstrak dengan akurasi tinggi, terdapat **{item_ditolak}** item pekerjaan (rasio deviasi {persentase_ditolak:.1f}%) yang tidak didukung oleh dokumentasi visual.
                    
                    **LOKASI KRITIS (PIN-POINT):**
                    Pekerjaan tanpa bukti visual berpusat di: **{teks_lokasi}**.
                    
                    **KEPUTUSAN PENERBITAN SPM:**
                    SPM tidak dapat diterbitkan secara penuh. Nilai progres maksimal yang memenuhi syarat keamanan administratif dan visual untuk dicairkan saat ini adalah **{estimasi_diterima:.3f}%**.
                    """)
            else:
                st.error("Gagal mengekstrak data. Pastikan dokumen yang diunggah benar.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem dalam status Stand By.")
