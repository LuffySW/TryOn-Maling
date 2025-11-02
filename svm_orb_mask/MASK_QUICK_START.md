# 🎭 Try-On Mask Overlay - Quick Reference

## ⚡ TL;DR - Solusi Cepat

Jika melihat error:
```
Error: File masker 'assets/haggus-skimask600x600.png' BUKAN PNG 4-channel (BGRA).
```

**Solusi:**

### Opsi A: Gunakan Script Helper (Tercepat ✨)
```bash
# Konversi masker JPG ke PNG dengan transparansi
python tools/convert_mask_to_png_rgba.py \
    --input mask_original.jpg \
    --output assets/mask_fixed.png \
    --verify

# Kemudian gunakan
python app.py webcam --mask assets/mask_fixed.png --show
```

### Opsi B: Gunakan Online Tool (Tanpa Install)
1. Buka https://www.remove.bg
2. Upload masker Anda
3. Download hasil PNG
4. Simpan ke `assets/` folder
5. Jalankan:
```bash
python app.py webcam --mask assets/mask_dari_remove_bg.png --show
```

### Opsi C: Gunakan GIMP (Manual)
1. Buka GIMP
2. File → Open → pilih masker Anda
3. Layer → Transparency → Add Alpha Channel
4. Select by Color → pilih background → Delete
5. File → Export As → PNG → Save

---

## 🔧 Setup Masker

### Struktur Folder:
```
svm_orb_tshirt/
├── assets/
│   ├── haarcascade_frontalface_default.xml
│   └── haggus-skimask600x600.png  ← Path default (harus RGBA)
├── tools/
│   └── convert_mask_to_png_rgba.py  ← Script helper
└── ...
```

### Test Masker:
```bash
# Cek apakah file masker valid (4-channel RGBA)
python tools/convert_mask_to_png_rgba.py \
    --input assets/mask_Anda.png \
    --verify
```

**Output jika valid:**
```
📊 Informasi File PNG:
   Ukuran: (600, 600, 4)
   Channels: 4
   ✅ VALID: 4-channel BGRA (siap untuk try-on overlay)
```

---

## 🎯 Test Try-On Mask

### Test 1: Webcam (Real-time)
```bash
# Default masker
python app.py webcam --show

# Custom masker
python app.py webcam --mask assets/masker_baru.png --show
```

**Tekan 'q' untuk exit**

### Test 2: Single Image
```bash
python app.py infer --image test_image.jpg --show
```

**Output:** Disimpan ke `out.jpg` (atau custom dengan `--out path/ke/output.jpg`)

### Test 3: Video
```bash
python app.py video --video test_video.mp4 --show
```

**Output:** Disimpan ke `output_video.mp4`

---

## 📋 Checklist Troubleshooting

| ✅ Check | Cara Cek |
|---------|---------|
| Masker file ada? | `ls assets/*.png` |
| Masker adalah PNG? | Cek extension `.png` (bukan `.jpg`) |
| Masker 4-channel RGBA? | Jalankan script verify (lihat di atas) |
| Model sudah trained? | Cek folder `models/` ada `codebook.pkl`, `scaler.pkl`, `svm.pkl` |
| Dataset ada? | Cek `data/faces/` dan `data/non_faces/` ada files |

---

## 🚀 Workflow Lengkap

```bash
# Step 1: Siapkan masker (jika masker asli JPG)
python tools/convert_mask_to_png_rgba.py \
    --input masker_original.jpg \
    --output assets/masker_saya.png \
    --verify

# Step 2: Train model (jika belum)
python app.py train

# Step 3: Test dengan webcam
python app.py webcam --mask assets/masker_saya.png --show

# Step 4: Test dengan gambar
python app.py infer --image test_image.jpg --mask assets/masker_saya.png --show

# Step 5: Test dengan video
python app.py video --video test_video.mp4 --mask assets/masker_saya.png --show
```

---

## 📊 Debug Info

Untuk lihat detail info saat running:
```bash
# Dengan debug verbosity
python app.py webcam --show 2>&1 | tee webcam_debug.log

# Parse log untuk errors
grep -i "error\|warn" webcam_debug.log
```

---

## ❓ FAQ

**Q: Overlay masker tidak muncul**
- A: Cek apakah masker 4-channel RGBA dengan script verify
- A: Cek apakah wajah terdeteksi (harus ada bounding box hijau)
- A: Cek score_thresh tidak terlalu tinggi: `--score_thresh 0.0`

**Q: Masker posisi salah**
- A: Overlay ditaruh berdasarkan face bounding box, ukuran masker harus sesuai (600x600 optimal)

**Q: "BUKAN PNG 4-channel" terus muncul**
- A: Gunakan script convert: `python tools/convert_mask_to_png_rgba.py --input OLD --output NEW --verify`

**Q: Model tidak ada**
- A: Train dulu: `python app.py train`

---

## 💡 Tips

1. **Masker ukuran kecil** (< 300x300): Kurang optimal, resize dengan tool online
2. **Masker background kompleks**: Gunakan remove.bg untuk hasil terbaik
3. **Test realtime**: Webcam mode paling cepat untuk iterasi
4. **Batch processing**: Gunakan video mode untuk proses banyak frame sekaligus

---

**Last Updated**: November 2, 2025 | **Status**: ✅ Production Ready
