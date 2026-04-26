import streamlit as st
import pdfplumber
import pandas as pd
from fuzzywuzzy import fuzz, process
import pytesseract
from pdf2image import convert_from_bytes
import io
import re

# ==========================================
# 1. KONFIGURASI ANTARMUKA (UI)
# ==========================================
st.set_page_config(page_title="Evaluasi Laporan PPSPM", page_icon="🛡️", layout="wide")

st.title("🛡️ Sistem Evaluasi Laporan PPSPM")
st.markdown("""
**SOP Keuangan & Fisik:** Mesin verifikasi silang untuk memastikan setiap klaim progres fisik didukung oleh bukti empiris sebelum **Surat Perintah Membayar (SPM)** diterbitkan.
""")
st.markdown("---")

# ==========================================
# 2. INPUT OTORITAS PPSPM & UPLOAD FILE
# ==========================================
st.sidebar.header("⚙️ Parameter Pembayaran")
klaim_progress_total = st.sidebar.number_input("Klaim Progress Diajukan (%)", min_value=0.000, max_value=100.000, value=2.919, step=0.001, format="%.3f")
st.sidebar.caption("Input angka klaim dari halaman depan laporan untuk validasi pembayaran.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Data 1: Laporan Mingguan")
    file_mingguan = st.file_uploader("Unggah Laporan Mingguan", type=["pdf"], key="mingguan")

with col2:
    st.subheader("📸 Data 2: Laporan Dokumentasi")
    file_dokumentasi = st.file_uploader("Unggah Laporan Dokumentasi", type=["pdf"], key="dokumentasi")

# ==========================================
# 3. MESIN EKSTRAKSI OCR & AUTO-CORRECT
# ==========================================
def koreksi_typo_ocr(teks):
    """Kamus Auto-Correct Forensik untuk nomenklatur proyek."""
    kamus_typo = {
        r'\bOIWOING\b': 'DINDING',
        r'\bAap\b': 'ATAP',
        r'\bFingan\b': 'RINGAN',
        r'\bPernanangan\b': 'PEMASANGAN',
        r'\bmasangan\b': 'PEMASANGAN',
        r'\bLani\b': 'LANTAI',
        r'\bam\b': 'CM',
        r'\bem\b': 'CM',
        r'\bKERJIAN\b': 'PEKERJAAN',
        r'\bDINOING\b': 'DINDING',
        r'\bBesiing\b': 'Bekisting'
    }
    teks_koreksi = teks
    for salah, benar in kamus_typo.items():
        teks_koreksi = re.sub(salah, benar, teks_koreksi, flags=re.IGNORECASE)
    return teks_koreksi

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
    items = []
    current_lokasi = "Lokasi Tidak Spesifik"
    keywords = [
        "pekerjaan", "pasang", "cor", "fabrikasi", "bekisting", "atap", "keramik", 
        "pondasi", "plesteran", "galian", "pembesian", "pengecatan", "instalasi",
        "bongkaran", "struktur", "baja", "beton", "pemancangan", "install", 
        "supply", "fabrication", "casting", "formwork", "structure", "finishing", 
        "painting", "wiring", "plumbing", "foundation", "concrete"
    ]
    
    for baris in baris_teks:
        baris = koreksi_typo_ocr(baris)
        
        jumlah_huruf = sum(c.isalpha() for c in baris)
        rasio_huruf = jumlah_huruf / len(baris) if len(baris) > 0 else 0

        if re.search(r'\b(MIS|MTSS)\b', baris.upper()) and rasio_huruf > 0.5:
            lokasi_bersih = re.sub(r'[\|_\\/\[\]{}<>]', '', baris).strip()
            current_lokasi = lokasi_bersih
            
        if any(k in baris.lower() for k in keywords):
            baris_bersih = re.sub(r'[\|_\\/\[\]{}<>]', '', baris)
            baris_bersih = ''.join([i for i in baris_bersih if not i.isdigit()]).replace('.', '').replace(',', '').strip()
            
            jumlah_huruf_bersih = sum(c.isalpha() for c in baris_bersih)
            rasio_huruf_bersih = jumlah_huruf_bersih / len(baris_bersih) if len(baris_bersih) > 0 else 0
            
            if len(baris_bersih) > 15 and rasio_huruf_bersih > 0.6:
                items.append({
                    "lokasi": current_lokasi,
                    "pekerjaan": baris_bersih
                })
    return items

# ==========================================
# 4. EKSEKUSI AUDIT PPSPM
# ==========================================
if file_mingguan and file_dokumentasi:
    st.markdown("---")
    if st.button("🚀 JALANKAN EVALUASI & VERIFIKASI PPSPM", use_container_width=True):
        with st.spinner('Memverifikasi kelayakan data untuk penerbitan SPM...'):
            
            raw_mingguan = ekstrak_data_forensik(file_mingguan, "Laporan Mingguan")
            raw_dokumentasi = ekstrak_data_forensik(file_dokumentasi, "Laporan Dokumentasi")
            
            klaim_items = parse_item_pekerjaan(raw_mingguan)
            
            if klaim_items:
                st.subheader("📊 Matriks Verifikasi Visual & Administratif")
                
                audit_results = []
                item_ditolak = 0
                total_item = len(klaim_items)
                strictness = 75
                
                for item in klaim_items:
                    best_match, score = process.extractOne(item['pekerjaan'], raw_dokumentasi, scorer=fuzz.token_set_ratio)
                    status = "✅ VALID" if score >= strictness else "❌ DEFISIT BUKTI"
                    
                    if status == "❌ DEFISIT BUKTI":
                        item_ditolak += 1
                        
                    audit_results.append({
                        "Lokasi": item['lokasi'],
                        "Uraian Pekerjaan": item['pekerjaan'],
                        "Status Kelayakan": status,
                        "Dokumentasi Ditemukan": best_match if score >= strictness else "Tidak Memenuhi Standar",
                    })
                
                df = pd.DataFrame(audit_results)
                
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
                c3.metric("Rasio Integritas Data", f"{(100 - persentase_ditolak):.1f}%")

                lokasi_bermasalah = df[df['Status Kelayakan'] == '❌ DEFISIT BUKTI']['Lokasi'].unique().tolist()
                teks_lokasi = ", ".join(lokasi_bermasalah) if lokasi_bermasalah else "Nihil"

                st.warning(f"""
                **HASIL EVALUASI PPSPM:**
                Berdasarkan verifikasi administrasi dan visual, klaim progres sebesar **{klaim_progress_total:.3f}%** memiliki rasio cacat dokumentasi sebesar **{persentase_ditolak:.1f}%**. Terdapat **{item_ditolak}** item pekerjaan yang diajukan untuk pembayaran namun tidak didukung oleh bukti empiris yang sah.
                
                **ZONA RISIKO AUDIT:**
                Defisit bukti terkonsentrasi pada lokasi: **{teks_lokasi}**.
                
                **KEPUTUSAN PENERBITAN SPM:**
                Mengingat prinsip kehati-hatian dalam pengelolaan keuangan negara, **Surat Perintah Membayar (SPM) TIDAK DAPAT DITERBITKAN secara penuh**. Direkomendasikan untuk melakukan pemotongan nilai pembayaran setara dengan rasio deviasi visual (**{estimasi_potongan:.3f}%**). Nilai maksimal yang memenuhi syarat keamanan administratif untuk dicairkan saat ini adalah **{estimasi_diterima:.3f}%**.
                """)
            else:
                st.error("Gagal mengekstrak teks. Pastikan dokumen dapat dibaca oleh OCR.")

elif not file_mingguan or not file_dokumentasi:
    st.info("Sistem dalam status Stand By. Menunggu dokumen pelengkap tagihan.")

st.markdown("---")
st.caption("Sistem dirancang dengan pendekatan presisi absolut. Keputusan pencairan dana tetap berada pada otoritas penuh PPSPM.")
