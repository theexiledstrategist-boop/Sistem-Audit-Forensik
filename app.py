import pdfplumber
import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

class ForensicProgressAuditor:
    def __init__(self, strictness_threshold=75):
        """
        Inisialisasi sistem audit.
        strictness_threshold: Batas toleransi kemiripan teks (0-100).
        Angka 75 adalah standar tinggi untuk memastikan akurasi tanpa kompromi.
        """
        self.strictness = strictness_threshold
        self.audit_log = []

    def extract_claims(self, pdf_mingguan_path):
        """
        Modul ekstraksi: Menarik daftar 'Pekerjaan Minggu Ini' dari Laporan Mingguan.
        (Output disimulasikan sebagai dictionary untuk kemudahan integrasi).
        """
        # Dalam implementasi nyata, gunakan pdfplumber untuk membaca tabel/teks.
        # Simulasi output hasil ekstraksi per lokasi:
        laporan_klaim = {
            "MIS NURUL KHAIRAT": [
                "Pekerjaan pasang rangka plafond bangunan A",
                "Pekerjaan instalasi listrik Bangunan A",
                "Pekerjaan pemasangan bekisting balok serta plat lantai 1"
            ],
            "MIS DARUL ULUM PUTERA": [
                "Pekerjaan Pemasangan bekisting Bangunan B & E",
                "Pekerjaan fabrikasi pembesian balok Bangunan B & E",
                "Pekerjaan rangka plafond Bangunan A"
            ]
        }
        return laporan_klaim

    def extract_visual_evidence(self, pdf_dokumentasi_path):
        """
        Modul ekstraksi: Menarik teks 'Kegiatan' dari bawah foto Laporan Dokumentasi.
        """
        # Simulasi output hasil ekstraksi kapsi foto:
        laporan_foto = {
            "MIS NURUL KHAIRAT": [
                "Pekerjaan plamiran dinding Bangunan A",
                "Pekerjaan Pemasangan penutup Atap Bangunan A",
                "Pekerjaan Rangka Plafond Bangunan A",
                "Pekerjaan Pemasangan Bekisting Balok Bangunan B"
            ],
            "MIS DARUL ULUM PUTERA": [
                "Pekerjaan Pemasangan rangka plafond Bangunan A",
                "Pekerjaan Pasang penutup atap teras Bangunan A",
                "Pekerjaan bekisting balok dan plat lantai Bangunan B",
                "Pekerjaan pengecoran Pondasi Telapak Bangunan B",
                "Pekerjaan pengecoran Pondasi Telapak Bangunan E"
            ]
        }
        return laporan_foto

    def execute_cross_audit(self, claims, evidences):
        """
        Mesin Utama Audit Forensik: Mengadu Klaim vs Bukti Visual.
        """
        print("======================================================")
        print("MEMULAI AUDIT FORENSIK: KLAIM VS REALITAS VISUAL")
        print("======================================================\n")

        for lokasi, list_klaim in claims.items():
            print(f"LOKASI: {lokasi}")
            print("-" * 50)
            
            list_bukti = evidences.get(lokasi, [])
            
            if not list_bukti:
                print(f"[FATAL ERROR] Nol bukti visual ditemukan untuk {lokasi}!\n")
                continue

            for klaim in list_klaim:
                # Menggunakan Fuzzy Matching untuk mencari kemiripan teks terbaik
                best_match, score = process.extractOne(klaim, list_bukti, scorer=fuzz.token_set_ratio)

                if score >= self.strictness:
                    status = "TERVERIFIKASI"
                    indikator = "[V]"
                    catatan = f"Terdokumentasi sebagai: '{best_match}' (Akurasi: {score}%)"
                else:
                    status = "TIDAK TERBUKTI (RED FLAG)"
                    indikator = "[X]"
                    catatan = f"Klaim gagal dibuktikan. Kemiripan tertinggi hanya {score}% ('{best_match}')"
                    
                    # Simpan ke daftar pelanggaran untuk eksekusi penolakan
                    self.audit_log.append({
                        "Lokasi": lokasi,
                        "Klaim Fiktif/Tanpa Bukti": klaim,
                        "Rekomendasi": "Coret bobot % item ini. Tolak pembayaran."
                    })

                print(f"{indikator} KLAIM   : {klaim}")
                print(f"    STATUS  : {status}")
                print(f"    CATATAN : {catatan}\n")
            
            # Cek anomali kebalikan (Ada foto, tapi tidak diklaim di laporan)
            self._detect_unclaimed_evidence(list_klaim, list_bukti)

    def _detect_unclaimed_evidence(self, list_klaim, list_bukti):
        """
        Mendeteksi foto pekerjaan yang dikerjakan tapi tidak ada di laporan mingguan (Inkonsistensi Admin).
        """
        print("    [!] AUDIT INKONSISTENSI ADMINISTRASI:")
        for bukti in list_bukti:
            best_match, score = process.extractOne(bukti, list_klaim, scorer=fuzz.token_set_ratio)
            if score < self.strictness:
                print(f"    -> Anomali: Terdapat foto '{bukti}' namun tidak tercatat di Laporan Mingguan.")
        print("\n")

    def generate_verdict(self):
        """
        Menghasilkan Keputusan Eksekusi Final.
        """
        print("======================================================")
        print("REKAPITULASI PELANGGARAN & KEPUTUSAN EKSEKUSI")
        print("======================================================")
        if not self.audit_log:
            print("Status: BERSIH. Seluruh klaim memiliki presisi visual yang dapat dipertanggungjawabkan.")
        else:
            df_log = pd.DataFrame(self.audit_log)
            print(df_log.to_string(index=False))
            print("\nKEPUTUSAN: KEMBALIKAN LAPORAN. Dokumen tidak memenuhi standar presisi minimum.")

# Eksekusi Program
if __name__ == "__main__":
    auditor = ForensicProgressAuditor(strictness_threshold=75)
    
    # Tarik data dari PDF (menggunakan dummy data dari simulasi sebelumnya)
    klaim_mingguan = auditor.extract_claims("laporan_mingguan_ke_14.pdf")
    bukti_foto = auditor.extract_visual_evidence("laporan_dokumentasi_ke_14.pdf")
    
    # Jalankan Audit
    auditor.execute_cross_audit(klaim_mingguan, bukti_foto)
    auditor.generate_verdict()
