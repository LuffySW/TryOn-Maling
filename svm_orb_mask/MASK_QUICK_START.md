# 🎭 Try-On Mask Overlay — Quick Start (Godot + Python Server)

## ⚡ TL;DR (2 menit)

1) Jalankan server Python (PowerShell):
```powershell
cd svm_orb_mask
py .\server.py
```

2) Jalankan Godot, open project `GodotTry-on/project.godot`, run scene `MaskTryon.tscn`

3) Pilih masker di UI (tombol dinamis), atau klik “None” untuk tanpa masker. Atur Scale / OffsetX / OffsetY via slider.

Catatan:
- Server otomatis memuat semua PNG di `svm_orb_mask/assets/`
- UI akan minta daftar masker ke server (`list_masks`) dan update tombol secara dinamis
- Tidak ada kotak hijau di wajah (rectangle dihapus)

---

## 🧱 Prasyarat

- Python 3.8+
- Dependencies: install dari `svm_orb_mask/requirements.txt`
- Godot 4.x
- Webcam tersedia

Opsional (untuk memperbaiki masker):
- `tools/convert_mask_to_png_rgba.py` dan `tools/test_mask_validation.py`

---

## 🛠️ Menambahkan Masker Baru

Letakkan file PNG RGBA ke folder:
```
svm_orb_mask/assets/
```

Syarat masker:
- PNG 4-channel (RGBA) — background transparan
- Disarankan ukuran ≥ 400×400

Server akan mendeteksi otomatis saat start dan mengirim daftar ke Godot.

---

## 🔍 Validasi Masker (Opsional tapi disarankan)

Konversi/cek dengan helper script:
```powershell
python tools/convert_mask_to_png_rgba.py `
  --input path\to\old.jpg `
  --output assets\mask_baru.png `
  --verify
```

Atau hanya verifikasi:
```powershell
python tools/test_mask_validation.py
```

Lihat `README_MASK_SETUP.md` untuk detail.

---

## ❓ FAQ Ringkas

Q: Tombol masker tidak muncul semua?
- A: Pastikan server sudah jalan; UI meminta `list_masks` dari server saat terkoneksi.

Q: Tidak ada overlay?
- A: Pilih masker selain “None”. Pastikan masker PNG RGBA (lihat README_MASK_SETUP.md).

Q: Posisi/ukuran masker kurang pas?
- A: Atur slider Scale / OffsetX / OffsetY di UI. Perubahan dikirim ke server real-time.

Q: Ada kotak hijau di wajah?
- A: Sudah dihapus di server terbaru. Restart server.py yang sekarang.

---

## 🧪 Troubleshooting Checklist

- [ ] Server jalan (terminal menampilkan “Server UDP mendengarkan…”)
- [ ] Godot scene `MaskTryon.tscn` running
- [ ] Webcam aktif (status “📹 Live” di UI)
- [ ] Masker PNG RGBA di `assets/`
- [ ] Pilih masker ≠ “None”

---

**Last Updated**: November 4, 2025 | **Status**: ✅ Up-to-date dengan Godot + server
 
## 📊 Evaluasi Model (Offline)

Gunakan perintah ini untuk menilai performa model BoVW+SVM pada dataset Anda.

1) Training (menyimpan artefak dan config):
```powershell
python app.py train --models_dir models
```

2) Evaluasi (membaca models/config.json untuk path data dan parameter):
```powershell
python app.py eval --models_dir models `
  --report models\test_metrics.json `
  --pr models\pr_curve.png
```

Output:
- `test_metrics.json` berisi accuracy, classification report, confusion matrix, dan Average Precision (jika tersedia)
- `pr_curve.png` grafik Precision–Recall (jika model menyediakan skor kontinu)
