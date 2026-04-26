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
st.set_page_config(page_title="Audit Forensik PPSPM", page_icon="🛡️", layout="wide")

# Otentikasi API Key dari Streamlit Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("FATAL ERROR: API Key belum dikonfigurasi di Streamlit Secrets.")
    st.stop()

st.title("🛡️ Sistem Evaluasi Laporan PPSPM")
st.markdown("""
**Protokol Audit:** Menggunakan *Multimodal Vision AI* tingkat tinggi untuk membedah laporan scan, mengekstrak data tanpa typo, dan melakukan validasi silang terhadap bukti fisik lapangan.
""")
st.markdown("---")

# ==========================================
# 2. INPUT OTORITAS & UPLOAD FILE
# ==========================================
st.sidebar.header("⚙️ Parameter Pembayaran")
klaim_progress_total = st.sidebar.number_input("Klaim Progress Diajukan (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
st.sidebar.caption("Input angka klaim dari rekapitulasi halaman depan untuk akurasi matematis.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Data 1: Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah Laporan Mingguan (PDF)", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Data 2: Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah Laporan Dokumentasi (PDF)", type=["pdf"], key="dokumentasi")

# Lapis Pertahanan 1: Mencegah Human Error (Upload File Ganda)
if file_mingguan and file_dokumentasi:
    if file_mingguan.name == file_dokumentasi.name:
        st.error("🚨 PERINGATAN ADMINISTRATIF: Anda mengunggah dokumen yang sama di kedua kolom. Mohon unggah Laporan Mingguan di Kolom 1 dan Laporan Dokumentasi di Kolom 2.")
        st.stop()

# ==========================================
# 3. MESIN EKSTRAKSI VISION AI (ABSOLUTE PRECISION)
# ==========================================
def ekstrak_dengan_vision_ai(file_pdf, tipe_dokumen):
    """
    Mengubah PDF menjadi gambar dan memerintahkan AI untuk mengekstrak data 
    dalam format JSON murni. Dilengkapi dengan Anti-Rate Limit.
    """
    file_bytes = file_pdf.read()
    try:
        images = convert_from_bytes(file_bytes)
    except Exception as e:
        st.error(f"Gagal mengonversi PDF ke Gambar. Pastikan poppler terinstal. Detail: {e}")
        return []
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    hasil_ekstraksi = []
    
    # Prompt Otoriter untuk mencegah halusinasi format
    if tipe_dokumen == "mingguan":
        prompt = """
        Anda adalah auditor sipil. Ini adalah tabel Laporan Kemajuan Fisik proyek konstruksi.
        Abaikan angka progres dan garis tabel. Fokus HANYA pada nama madrasah/lokasi dan nama item pekerjaannya.
        Keluarkan HANYA format array JSON murni (tanpa markdown, tanpa penjelasan apapun) seperti ini:
        [{"lokasi": "nama lokasi", "pekerjaan": "deskripsi pekerjaan dengan ejaan yang benar"}]
        Jika halaman ini bukan tabel kemajuan fisik, wajib kembalikan [].
        """
    else:
        prompt = """
        Anda adalah auditor sipil. Ini adalah Laporan Dokumentasi Foto proyek konstruksi.
        Tugas Anda HANYA membaca teks keterangan (caption) yang ada di bawah, atas, atau samping foto.
        Keluarkan HANYA format array JSON murni (tanpa markdown, tanpa penjelasan apapun) seperti ini:
        [{"keterangan_foto": "teks caption yang ejaannya telah dirapikan"}]
        Jika tidak ada foto atau caption di halaman ini, wajib kembalikan [].
        """

    progress_bar = st.progress(0)
    for i, img in enumerate(images):
        try:
            response = model.generate_content([prompt, img])
            teks_mentah = response.text
            
            # Lapis Pertahanan 2: JSON Armor (Membersihkan format markdown yang membandel)
            teks_bersih = re.sub(r'```json|```', '', teks_mentah).strip()
            
            # Mencari struktur array JSON secara spesifik
            match = re.search(r'\[.*\]', teks_bersih, re.DOTALL)
            if match:
                data_page = json.loads(match.group(0))
                hasil_ekstraksi.extend(data_page)
                
        except json.JSONDecodeError:
            st.toast(f"Halaman {i+1} ({tipe_dokumen}): AI gagal membentuk format JSON yang valid. Dilewati.")
        except Exception as e:
            st.toast(f"Anomali pada Halaman {i+1} ({tipe_dokumen}): {e}")
            
        # Lapis Pertahanan 3: Pacing Strategis (Mencegah blokir API Google)
        time.sleep(4) 
        
        progress_bar.progress((i + 1) / len(images))
        
    progress_bar.empty()
    return hasil_ekstraksi

# ==========================================
# 4. EKSEKUSI AUDIT FORENSIK
# ==========================================
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 EKSEKUSI PEMBEDAHAN & VERIFIKASI", use_container_width=True):
        with st.spinner('Vision AI sedang membedah dokumen dan mengkalibrasi data... Mohon tunggu.'):
            
            # Mendapatkan data terstruktur langsung dari otak AI
            data_mingguan = ekstrak_dengan_vision_ai(file_mingguan, "mingguan")
            data_foto = ekstrak_dengan_vision_ai(file_dokumentasi, "dokumentasi")
            
            if data_mingguan and data_foto:
                st.subheader("📊 Matriks Verifikasi Visual & Administratif")
                
                # Menggabungkan seluruh caption foto sebagai basis data bukti
                teks_bukti_visual = [item.get("keterangan_foto", "") for item in data_foto if isinstance(item, dict)]
                
                audit_results = []
                item_ditolak = 0
                item_valid = 0
                
                for item in data_mingguan:
                    if not isinstance(item, dict):
                        continue
                        
                    pekerjaan = item.get('pekerjaan', '')
                    lokasi = item.get('lokasi', 'Lokasi Tidak Spesifik')
                    
                    if not pekerjaan or len(pekerjaan) < 10:
                        continue
                        
                    # Semantic Matching (Mencocokkan klaim dengan bukti visual)
                    best_match, score = process.extractOne(pekerjaan, teks_bukti_visual, scorer=fuzz.token_set_ratio)
                    status = "✅ VALID" if score >= 75 else "❌ DEFISIT BUKTI"
                    
                    if status == "❌ DEFISIT BUKTI":
                        item_ditolak += 1
                    else:
                        item_valid += 1
                        
                    audit_results.append({
                        "Lokasi (Pin-Point)": lokasi.upper(),
                        "Uraian Pekerjaan": pekerjaan,
                        "Status Kelayakan": status,
                        "Bukti Visual Ditemukan": best_match if score >= 75 else "Tidak Ada Bukti Dokumentasi",
                    })
                
                if audit_results:
                    df = pd.DataFrame(audit_results)
                    total_item = item_valid + item_ditolak
                    
                    # Rendering Tabel Anti-Crash
                    try:
                        st.dataframe(df.style.map(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Status Kelayakan']), use_container_width=True)
                    except AttributeError:
                        st.dataframe(df.style.applymap(lambda x: 'color: red; font-weight: bold' if x == "❌ DEFISIT BUKTI" else '', subset=['Status Kelayakan']), use_container_width=True)
                    
                    # ==========================================
                    # 5. KEPUTUSAN FINAL PPSPM
                    # ==========================================
                    persentase_ditolak = (item_ditolak / total_item) * 100 if total_item > 0 else 0
                    estimasi_potongan = (persentase_ditolak / 100) * klaim_progress_total
                    estimasi_diterima = klaim_progress_total - estimasi_potongan
                    
                    st.markdown("---")
                    st.header("📝 Nota Keputusan PPSPM")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Item Diajukan", f"{total_item} Pekerjaan")
                    c2.metric("Item Defisit Bukti", f"{item_ditolak} Pekerjaan", delta_color="inverse")
                    c3.metric("Rasio Integritas Dokumentasi", f"{(100 - persentase_ditolak):.1f}%")

                    lokasi_bermasalah = df[df['Status Kelayakan'] == '❌ DEFISIT BUKTI']['Lokasi (Pin-Point)'].unique().tolist()
                    teks_lokasi = ", ".join(lokasi_bermasalah) if lokasi_bermasalah else "Nihil"

                    st.warning(f"""
                    **HASIL EVALUASI AUDIT FORENSIK:**
                    Berdasarkan uji petik korelasi silang berbasis AI, klaim progres administratif sebesar **{klaim_progress_total:.3f}%** memiliki rasio cacat visual sebesar **{persentase_ditolak:.1f}%**. Sebanyak **{item_ditolak}** item pekerjaan teridentifikasi diajukan tanpa dukungan empiris yang sah.
                    
                    **ZONA RISIKO AUDIT (PIN-POINT):**
                    Pekerjaan tanpa bukti dokumentasi yang valid terkonsentrasi pada lokasi: **{teks_lokasi}**.
                    
                    **REKOMENDASI PENERBITAN SPM:**
                    Mengingat prinsip kehati-hatian pengelolaan keuangan, **Surat Perintah Membayar (SPM) direkomendasikan untuk DITANGGUHKAN sebagian**. Pemotongan setara rasio deviasi visual sebesar **{estimasi_potongan:.3f}%** harus diberlakukan. Nilai real progres yang aman untuk disetujui saat ini adalah **{estimasi_diterima:.3f}%**.
                    """)
            else:
                st.error("Mesin AI gagal mengekstrak data dari dokumen yang diberikan. Pastikan resolusi dokumen memadai.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem dalam status Stand By. Menunggu komparasi Laporan Mingguan dan Laporan Dokumentasi.")

st.markdown("---")
st.caption("Dikembangkan dengan pendekatan utilitiarian dan standar presisi tingkat tinggi. Otoritas pencairan dana tetap berada pada pejabat terkait.")
