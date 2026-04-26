import streamlit as st
import pdfplumber
import pandas as pd
from fuzzywuzzy import fuzz, process
import pytesseract
from pdf2image import convert_from_bytes
import io

# ==========================================
# 1. KONFIGURASI ANTARMUKA (UI)
# ==========================================
st.set_page_config(page_title="Audit Forensik Proyek V3", page_icon="⚖️", layout="wide")

st.title("⚖️ Sistem Audit Forensik & Verifikator Progress")
st.markdown("Fokus pada validasi eksistensi fisik di lapangan. Hindari bias OCR pada tabel matematis.")
st.markdown("---")

# ==========================================
# 2. INPUT OTORITAS PPK & UPLOAD FILE
# ==========================================
st.sidebar.header("⚙️ Parameter Kontrak")
klaim_progress_total = st.sidebar.number_input("Klaim Progress Minggu Ini (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
st.sidebar.caption("Input angka klaim dari halaman depan laporan mingguan (Bukan Kumulatif).")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Data 1: Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah Laporan Mingguan", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Data 2: Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah Laporan Dokumentasi", type=["pdf"], key="dokumentasi")

# ==========================================
# 3. MESIN EKSTRAKSI OCR
# ==========================================
def ekstrak_data_forensik(file_pdf, nama_file):
    teks_lengkap = ""
    file_bytes = file_pdf.read()
    
    try:
        images = convert_from_bytes(file_bytes)
        for i, img in enumerate(images):
            page_text = pytesseract.image_to_string(img, lang='ind')
            teks_lengkap += f"\n[HALAMAN_{i+1}]\n" + page_text
    except Exception as e:
        st.error(f"Gagal mengekstrak {nama_file}: {e}")
        return []
            
    baris_teks = [baris.strip() for baris in teks_lengkap.split('\n') if len(baris.strip()) > 10]
    return baris_teks

def parse_item_pekerjaan(baris_teks):
    """Fokus HANYA menarik deskripsi pekerjaan, abaikan angka persentase."""
    items = []
    current_lokasi = "Lokasi Tidak Spesifik"
    keywords = ["pekerjaan", "pasang", "cor", "fabrikasi", "bekisting", "atap", "keramik", "pondasi"]
    
    for baris in baris_teks:
        if any(x in baris.upper() for x in ["MIS ", "MTSS "]):
            current_lokasi = baris
            
        if any(k in baris.lower() for k in keywords):
            # Membersihkan angka dan karakter aneh di akhir baris akibat OCR tabel
            baris_bersih = ''.join([i for i in baris if not i.isdigit()]).replace('.', '').replace(',', '').strip()
            
            if len(baris_bersih) > 15:
                items.append({
                    "lokasi": current_lokasi,
                    "pekerjaan": baris_bersih
                })
    return items

# ==========================================
# 4. EKSEKUSI AUDIT
# ==========================================
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 JALANKAN AUDIT FORENSIK", use_container_width=True):
        with st.spinner('Menyinkronkan data teks dengan metadata visual...'):
            
            raw_mingguan = ekstrak_data_forensik(file_mingguan, "Laporan Mingguan")
            raw_dokumentasi = ekstrak_data_forensik(file_dokumentasi, "Laporan Dokumentasi")
            
            klaim_items = parse_item_pekerjaan(raw_mingguan)
            
            if klaim_items:
                st.subheader("📊 Matriks Verifikasi Visual")
                
                audit_results = []
                item_ditolak = 0
                total_item = len(klaim_items)
                strictness = 75
                
                for item in klaim_items:
                    best_match, score = process.extractOne(item['pekerjaan'], raw_dokumentasi, scorer=fuzz.token_set_ratio)
                    status = "✅ SINKRON" if score >= strictness else "❌ TIDAK SINKRON"
                    
                    if status == "❌ TIDAK SINKRON":
                        item_ditolak += 1
                        
                    audit_results.append({
                        "Lokasi": item['lokasi'],
                        "Uraian Pekerjaan": item['pekerjaan'],
                        "Status": status,
                        "Bukti Visual": best_match if score >= strictness else "Tidak Ada Bukti",
                    })
                
                df = pd.DataFrame(audit_results)
                
                try:
                    st.dataframe(df.style.map(lambda x: 'color: red; font-weight: bold' if x == "❌ TIDAK SINKRON" else '', subset=['Status']), use_container_width=True)
                except AttributeError:
                    st.dataframe(df.style.applymap(lambda x: 'color: red; font-weight: bold' if x == "❌ TIDAK SINKRON" else '', subset=['Status']), use_container_width=True)
                
                # ==========================================
                # 5. KEPUTUSAN FINAL BERBASIS RISIKO
                # ==========================================
                persentase_ditolak = (item_ditolak / total_item) * 100 if total_item > 0 else 0
                estimasi_potongan = (persentase_ditolak / 100) * klaim_progress_total
                estimasi_diterima = klaim_progress_total - estimasi_potongan
                
                st.markdown("---")
                st.header("📝 Narasi Keputusan Administratif")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Item Diklaim", f"{total_item} Pekerjaan")
                c2.metric("Item Tanpa Bukti (Red Flag)", f"{item_ditolak} Pekerjaan", delta_color="inverse")
                c3.metric("Rasio Validitas Visual", f"{(100 - persentase_ditolak):.1f}%")

                lokasi_bermasalah = df[df['Status'] == '❌ TIDAK SINKRON']['Lokasi'].unique().tolist()
                teks_lokasi = ", ".join(lokasi_bermasalah) if lokasi_bermasalah else "Tidak ada"

                st.warning(f"""
                **LAPORAN EVALUASI PPK:**
                Pihak kontraktor mengajukan klaim progres minggu ini sebesar **{klaim_progress_total:.3f}%**. Namun, dari total **{total_item}** item pekerjaan yang tertulis, terdapat **{item_ditolak}** item pekerjaan (sekitar {persentase_ditolak:.1f}% dari total aktivitas) yang tidak memiliki bukti dokumentasi visual yang dapat dipertanggungjawabkan.
                
                **LOKASI KRITIS:**
                Pekerjaan fiktif/tidak terdokumentasi ini berpusat di: **{teks_lokasi}**.
                
                **REKOMENDASI PENOLAKAN:**
                Mengingat integritas data yang cacat, direkomendasikan untuk menahan klaim progres sebesar estimasi rasio deviasi visual, yaitu **{estimasi_potongan:.3f}%**. Nilai progres aman yang dapat disetujui sementara waktu sebelum opname lapangan dilakukan adalah **{estimasi_diterima:.3f}%**.
                """)
            else:
                st.error("Gagal mengekstrak teks. Pastikan dokumen dapat dibaca OCR.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem dalam status Stand By.")
