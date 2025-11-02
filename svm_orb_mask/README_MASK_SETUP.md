# 🎭 Panduan Lengkap - Validasi Masker Try-On Overlay

## 📌 Overview

Untuk fitur **Try-On Mask Overlay** bekerja dengan sempurna, telah ditambahkan **validasi otomatis** yang memastikan file masker PNG memiliki transparansi alpha channel yang benar.

**Jika Anda melihat error:**
```
Error: File masker 'assets/...' BUKAN PNG 4-channel (BGRA).
```

Ini berarti file masker Anda perlu dikonversi. Ikuti panduan di bawah.

---

## 🎯 Solusi Cepat (2 Langkah)

### Langkah 1: Konversi Masker
```bash
python tools/convert_mask_to_png_rgba.py \
    --input path/ke/masker_lama.jpg \
    --output assets/masker_baru.png \
    --verify
```

### Langkah 2: Gunakan Masker Baru
```bash
python app.py webcam --mask assets/masker_baru.png --show
```

**Hasil Expected**: ✅ Masker transparan muncul di wajah terdeteksi

---

## 📚 Dokumentasi Lengkap

### 📄 File Dokumentasi yang Tersedia:

1. **`MASK_REQUIREMENTS.md`** 
   - Penjelasan detail tentang format masker PNG
   - Cara membuat PNG dengan transparansi (3 opsi)
   - Troubleshooting lengkap
   - Contoh Python/GIMP/Online tools

2. **`MASK_QUICK_START.md`**
   - TL;DR solutions
   - Workflow checklist
   - FAQ
   - Tips & tricks

3. **`IMPLEMENTATION_SUMMARY.md`**
   - Ringkasan teknis perubahan kode
   - File yang dimodifikasi
   - Test cases
   - Developer notes

### 🛠️ Tools yang Tersedia:

1. **`tools/convert_mask_to_png_rgba.py`**
   - Konversi JPG/PNG ke PNG 4-channel RGBA
   - Support custom background color
   - Fitur verify hasil konversi
   - Usage: `python tools/convert_mask_to_png_rgba.py --help`

2. **`tools/test_mask_validation.py`**
   - Test validasi masker
   - Check apakah masker sudah valid
   - Usage: `python tools/test_mask_validation.py`

---

## 🔧 Setup Masker - Opsi Tersedia

### ✨ OPSI A: Gunakan Script Helper (RECOMMENDED)
**Pro:** Paling cepat, otomatis
**Waktu:** 1 menit

```bash
python tools/convert_mask_to_png_rgba.py \
    --input mask_lama.jpg \
    --output assets/mask_baru.png \
    --verify
```

### 🌐 OPSI B: Gunakan Online Tool (Tanpa Install)
**Pro:** Gratis, instant, hasil bagus
**Waktu:** 2 menit

1. Buka https://www.remove.bg
2. Upload masker
3. Download hasil PNG
4. Simpan ke `assets/` folder

### 🎨 OPSI C: Gunakan GIMP (Manual Kontrol)
**Pro:** Kontrol penuh, bagus untuk background kompleks
**Waktu:** 5 menit

1. Buka GIMP
2. File → Open → masker Anda
3. **Layer → Transparency → Add Alpha Channel**
4. **Select → By Color** → klik background
5. **Delete**
6. **File → Export As** → PNG
7. Jangan centang "Save background color"

---

## ✅ Verifikasi Masker

### Cara 1: Gunakan Test Script (Tercepat)
```bash
python tools/test_mask_validation.py
```

**Output jika VALID:**
```
✅ PASSED: 4-channel RGBA
   Shape: (600, 600, 4)
   Channels: 4
```

**Output jika INVALID:**
```
❌ FAILED: Not 4-channel RGBA
```

### Cara 2: Gunakan Python Langsung
```python
import cv2

mask = cv2.imread("assets/mask.png", cv2.IMREAD_UNCHANGED)
print(mask.shape)  # Harus output: (height, width, 4)
```

### Cara 3: Konversi Script + Verify
```bash
python tools/convert_mask_to_png_rgba.py \
    --input mask.jpg \
    --output mask_fixed.png \
    --verify
```

---

## 🎬 Test Try-On Overlay

### Test 1: Real-Time dengan Webcam
```bash
python app.py webcam --show
```
Tekan 'q' untuk exit

### Test 2: Single Image
```bash
python app.py infer --image test_image.jpg --show
```

### Test 3: Video
```bash
python app.py video --video test_video.mp4 --show
```

### Test dengan Masker Custom
```bash
python app.py webcam --mask assets/masker_saya.png --show
```

---

## 📊 Informasi Teknis

### Format Masker yang Benar:
```
✅ PNG 4-channel BGRA
   - Blue channel
   - Green channel  
   - Red channel
   - Alpha channel (transparency)
```

### Format yang TIDAK Bisa Digunakan:
```
❌ JPG (tidak support transparansi)
❌ PNG RGB 3-channel (tanpa alpha)
❌ PNG dengan background solid (bukan transparan)
```

### Validasi yang Dilakukan:
```python
# Code validation yang ada di setiap fungsi inference
if len(mask_asset.shape) < 3 or mask_asset.shape[2] != 4:
    logger.error("Error: File masker BUKAN PNG 4-channel (BGRA).")
    return  # Exit gracefully
```

---

## 🚨 Error Messages & Solusi

| Error | Penyebab | Solusi |
|-------|---------|--------|
| `BUKAN PNG 4-channel (BGRA)` | File JPG atau PNG tanpa alpha | Jalankan: `python tools/convert_mask_to_png_rgba.py --input OLD --output NEW --verify` |
| `Gagal memuat file masker` | Path masker salah | Cek path dengan `ls assets/` |
| Overlay tidak muncul | Model tidak terlatih | Jalankan: `python app.py train` |
| Masker posisi salah | Resolusi masker terlalu kecil | Gunakan masker min 400x400 pixel |

---

## 📋 Workflow Lengkap

```bash
# 1. Cek struktur folder
ls -la assets/
ls -la data/faces/
ls -la models/

# 2. Verifikasi masker existing
python tools/test_mask_validation.py

# 3. Jika masker invalid, konversi
python tools/convert_mask_to_png_rgba.py \
    --input assets/old_mask.jpg \
    --output assets/new_mask.png \
    --verify

# 4. Train model (jika belum)
python app.py train

# 5. Test dengan webcam
python app.py webcam --mask assets/new_mask.png --show

# 6. Test dengan gambar
python app.py infer --image test_image.jpg --mask assets/new_mask.png --show

# 7. Test dengan video (untuk production)
python app.py video --video test_video.mp4 --mask assets/new_mask.png --show
```

---

## 💡 Tips & Best Practices

### Masker Ukuran & Resolusi
- **Optimal:** 600x600 pixel
- **Minimum:** 400x400 pixel
- **Maximum:** 1200x1200 pixel (performa)

### Background Masker
- **Best:** Warna solid putih atau transparan
- **Avoid:** Background kompleks/tekstur
- **Tool:** remove.bg untuk hasil sempurna

### Testing Strategi
1. Test dengan webcam dulu (real-time feedback)
2. Jika ok, coba dengan 1 gambar
3. Jika ok, coba dengan video pendek
4. Jika ok, go production

### Performance Tips
- Video resolution ≤ 1080p untuk inference cepat
- Gunakan `--score_thresh 0.0` untuk deteksi maksimal

---

## 🆘 Troubleshooting Checklist

- [ ] Masker file ada di `assets/` folder
- [ ] File extension adalah `.png` (bukan `.jpg`)
- [ ] Jalankan test: `python tools/test_mask_validation.py`
- [ ] Jika invalid, konversi dengan script helper
- [ ] Verifikasi lagi setelah konversi
- [ ] Test dengan webcam: `python app.py webcam --show`
- [ ] Jika tetap error, baca `MASK_REQUIREMENTS.md` detail

---

## 📞 Support Resources

1. **Dokumentasi Detail:**
   - `MASK_REQUIREMENTS.md` - Panduan format & cara membuat
   - `MASK_QUICK_START.md` - Quick reference
   - `IMPLEMENTATION_SUMMARY.md` - Detail teknis

2. **Tools Otomatis:**
   - `tools/convert_mask_to_png_rgba.py` - Konversi masker
   - `tools/test_mask_validation.py` - Test validasi

3. **Online Resources:**
   - https://www.remove.bg - Hapus background otomatis
   - https://www.photopea.com - Web-based image editor
   - https://pixlr.com - Online PNG editor

---

## 🎓 Technical Details

### Implementation Details:

**File yang dimodifikasi:**
- `pipelines/infer.py` - 3 fungsi (infer_webcam, infer_image, infer_video)
- `pipelines/utils.py` - 1 fungsi (infer_webcam)

**Validasi ditambahkan:**
```python
if len(mask_asset.shape) < 3 or mask_asset.shape[2] != 4:
    logger.error(f"Error: File masker '{args.mask}' BUKAN PNG 4-channel (BGRA).")
    logger.error("Masker Anda mungkin tidak punya latar belakang transparan.")
    logger.error("Silakan cari file PNG lain yang benar-benar transparan.")
    return
```

**Timing:** Dilakukan setelah `cv2.imread()` berhasil, sebelum overlay dimulai

---

**Last Updated:** November 2, 2025  
**Status:** ✅ Production Ready  
**Python Version:** 3.8+  
**Tested On:** Windows PowerShell
