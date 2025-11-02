# Persyaratan File Masker (Mask Asset)

## ⚠️ Penting: Format PNG dengan Transparansi Alpha

Untuk fitur **Try-On Mask Overlay** bekerja dengan sempurna, file masker PNG Anda **HARUS** memenuhi persyaratan berikut:

### ✅ Persyaratan Wajib:

1. **Format File**: PNG (bukan JPG, BMP, atau format lainnya)
2. **Channel**: 4-channel BGRA (Blue, Green, Red, Alpha)
3. **Alpha Channel**: Harus memiliki transparansi (background harus transparan)
4. **Tidak Boleh**: PNG RGB 3-channel tanpa alpha

### ❌ Yang Akan Error:

- ❌ File JPG (tidak mendukung transparansi)
- ❌ PNG RGB 3-channel (tanpa alpha transparency)
- ❌ PNG dengan background solid warna (bukan transparan)
- ❌ Format lainnya (BMP, TIFF, GIF)

---

## 🔍 Cara Cek File Masker Anda

### Menggunakan Python:
```python
import cv2

mask = cv2.imread("assets/haggus-skimask600x600.png", cv2.IMREAD_UNCHANGED)
print(f"Shape: {mask.shape}")  # Harus output: (height, width, 4)
print(f"Channels: {mask.shape[2]}")  # Harus output: 4
```

### Menggunakan Command Line (Windows):
```powershell
# Lihat info file dengan ImageMagick (jika terinstall)
identify -verbose assets/haggus-skimask600x600.png
```

---

## 🛠️ Solusi: Cara Membuat PNG dengan Transparansi

### Opsi 1: Gunakan Photoshop/GIMP
1. Buka masker Anda di GIMP
2. Layer → Transparency → Add Alpha Channel
3. Gunakan "Select by Color" untuk hapus background
4. Delete background → background menjadi transparan
5. File → Export As → Format: PNG → Pastikan "Save background color" UNCHECKED
6. Export

### Opsi 2: Gunakan Python (PIL/Pillow)
```python
from PIL import Image
import cv2

# Jika masker Anda sudah ada (JPG dengan background putih)
img = Image.open("mask_original.jpg")

# Convert ke RGBA
img_rgba = img.convert("RGBA")

# Buat mask untuk white background
data = img_rgba.getdata()
new_data = []
for item in data:
    # Jika pixel adalah putih (255, 255, 255), ubah alpha ke 0 (transparan)
    if item[0] > 240 and item[1] > 240 and item[2] > 240:  # Hampir putih
        new_data.append((255, 255, 255, 0))  # Transparan
    else:
        new_data.append(item)

img_rgba.putdata(new_data)
img_rgba.save("mask_transparent.png")
```

### Opsi 3: Gunakan Online Tool
- **Remove.bg** (https://www.remove.bg) - Otomatis hapus background
- **Photopea** (https://www.photopea.com) - Web-based editor seperti Photoshop
- **Pixlr** (https://pixlr.com) - Editor online gratis

---

## ✅ Verifikasi Setelah Dibuat

Setelah membuat PNG dengan transparansi, test dengan:

```bash
# Coba webcam demo
python app.py webcam --show

# Atau coba pada gambar
python app.py infer --image test_image.jpg --show
```

**Expected Output:**
- ✅ Logger message: "Model berhasil dimuat"
- ✅ Masker muncul di atas wajah terdeteksi
- ✅ Bounding box hijau menunjukkan deteksi wajah

**Error Output:**
- ❌ "Error: File masker 'assets/...' BUKAN PNG 4-channel (BGRA)"
  → Berarti file Anda tidak punya channel alpha yang tepat

---

## 📁 Default Path Masker

File masker default dicari di:
```
svm_orb_tshirt/
├── assets/
│   └── haggus-skimask600x600.png  ← Default path
```

Untuk menggunakan masker lain:
```bash
python app.py webcam --mask path/ke/masker_baru.png --show
```

---

## 🎯 Tips & Trik

1. **Ukuran Masker**: 600x600 pixel atau lebih adalah optimal
2. **Quality**: Gunakan PNG lossless untuk hasil terbaik
3. **Background Putih**: Lebih mudah dihapus daripada background kompleks
4. **Test Dulu**: Jangan langsung test dengan video panjang, test dengan webcam atau 1 gambar dulu

---

## 📞 Troubleshooting

| Masalah | Penyebab | Solusi |
|---------|---------|--------|
| "Error: File masker BUKAN PNG 4-channel" | PNG tanpa alpha channel | Export ulang dengan "Add Alpha Channel" di GIMP |
| Masker tidak muncul | File masker path salah | Cek path dengan `--mask path/ke/file.png` |
| Masker muncul tapi area putih terlihat | Background bukan transparan | Hapus background dengan tool online |
| Overlay posisi tidak tepat | Resolusi masker terlalu kecil | Gunakan masker minimal 400x400 pixel |

---

## 📝 Contoh Command

```bash
# Test dengan default masker (assets/haggus-skimask600x600.png)
python app.py webcam --show

# Test dengan masker custom
python app.py webcam --mask my_masks/custom_mask.png --show

# Test pada gambar dengan masker custom
python app.py infer --image test_image.jpg --mask my_masks/custom_mask.png --show

# Test pada video dengan masker custom
python app.py video --video test_video.mp4 --mask my_masks/custom_mask.png --show
```

---

**Terakhir diupdate**: November 2, 2025
