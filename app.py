    # ==========================================
    # TAHAP BARU: EKSTRAKSI TEKS DOKUMENTASI
    # ==========================================
    with st.spinner("Menyadap keterangan visual dari PDF Dokumentasi..."):
        doc_foto = fitz.open(stream=file_dokumentasi.read(), filetype="pdf")
        teks_dokumentasi_full = ""
        
        # Menyedot seluruh teks (terutama kolom "Kegiatan") dari PDF Foto
        for page in doc_foto:
            teks_dokumentasi_full += page.get_text("text").lower()

    # ==========================================
    # TAHAP 1 & VALIDASI SILANG (OUTPUT 4)
    # ==========================================
    st.header("🔍 Hasil Audit & Validasi Silang (Klaim vs Bukti)")
    
    with st.spinner("Melakukan cross-checking antara klaim angka dan bukti di lapangan..."):
        temuan_anomali = []
        laporan_validasi_silang = []
        
        with pdfplumber.open(file_mingguan) as pdf:
            start_page = max(0, len(pdf.pages) - 5) # Fokus ke lampiran progress
            for i in range(start_page, len(pdf.pages)):
                tabel = pdf.pages[i].extract_table()
                if not tabel: continue
                
                for row in tabel:
                    try:
                        if row[1] and row[5] and row[8] and row[11]:
                            uraian = str(row[1]).replace('\n', ' ')
                            b_lalu = float(str(row[5]).replace(',', '.'))
                            b_ini = float(str(row[8]).replace(',', '.')) # PROGRESS MINGGU INI
                            klaim_total = float(str(row[11]).replace(',', '.'))
                            
                            # 1. Cek Anomali Matematis
                            hitungan_sistem = round(b_lalu + b_ini, 3)
                            if hitungan_sistem != round(klaim_total, 3):
                                temuan_anomali.append({
                                    "Pekerjaan": uraian,
                                    "Klaim Kumulatif": klaim_total,
                                    "Sistem Matematika": hitungan_sistem
                                })
                            
                            # 2. LOGIKA VALIDASI SILANG MUTLAK
                            # Jika ada progres minggu ini (> 0%), WAJIB ada di PDF Laporan Dokumentasi
                            if b_ini > 0:
                                # Mengambil 2 kata kunci utama dari uraian (menghindari ketidakcocokan spasi/typo)
                                kata_kunci = uraian.lower().split()[:2] 
                                keyword_pencarian = " ".join(kata_kunci)
                                
                                # Cek apakah keyword pekerjaan ini ada di teks PDF Dokumentasi
                                if keyword_pencarian in teks_dokumentasi_full:
                                    status_bukti = "✅ Bukti Ditemukan"
                                else:
                                    status_bukti = "❌ BUKTI VISUAL TIDAK ADA!"
                                
                                laporan_validasi_silang.append({
                                    "Item Pekerjaan (Progres > 0%)": uraian,
                                    "Klaim Penambahan Bobot": f"+{b_ini}%",
                                    "Status Dokumentasi": status_bukti
                                })
                    except: continue

    # Menampilkan Matriks Validasi Silang
    st.subheader("Rapor Validasi Silang (Kesesuaian Item Pekerjaan & Foto)")
    if laporan_validasi_silang:
        df_validasi = pd.DataFrame(laporan_validasi_silang)
        # Memberikan warna merah pada baris yang tidak ada buktinya
        st.dataframe(df_validasi.style.applymap(lambda x: 'background-color: #ffcccc; color: red' if x == "❌ BUKTI VISUAL TIDAK ADA!" else '', subset=['Status Dokumentasi']), use_container_width=True)
    else:
        st.info("Tidak ada penambahan progres signifikan minggu ini untuk divalidasi.")

