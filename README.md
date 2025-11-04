# Godot Try‑On Mask Overlay (Godot + Python UDP Server)

End‑to‑end try‑on system:
- Python server (`svm_orb_mask/server.py`) menangkap webcam, deteksi wajah (Haar + ORB BoVW + SVM), overlay masker PNG RGBA, dan stream hasil ke Godot via UDP.
- Godot client (`GodotTry-on`) menampilkan stream, tombol pilihan masker (dinamis), dan slider pengaturan overlay (scale/offset) yang dikirim real‑time ke server.

Masker harus PNG 4‑channel (RGBA) dengan background transparan. Lihat `svm_orb_mask/README_MASK_SETUP.md` untuk cara konversi/validasi.

## Setup Guide (Windows)
1.  **Prasyarat**:
  -   Install [Python](https://www.python.org/downloads/) (versi 3.8+ direkomendasikan). Pastikan `pip` terinstall dan ada di PATH.
  -   Install [Godot Engine](https://godotengine.org/download/) (versi 4.x).

2.  **Setup Server Python**:
  -   Buka terminal (misalnya, PowerShell).
  -   Navigasi ke direktori `svm_orb_mask`:
    ```powershell
    cd path\to\your\project\svm_orb_mask
    ```
  -   (Opsional tapi direkomendasikan) Buat dan aktifkan virtual environment:
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
  -   Install semua dependensi yang dibutuhkan:
    ```powershell
    pip install -r requirements.txt
    ```

3.  **Setup Client Godot**:
  -   Buka Godot Engine.
  -   Di Project Manager, klik tombol **Import**.
  -   Navigasi ke folder `GodotTry-on` di dalam proyek Anda, pilih file `project.godot`, lalu klik **Open**.
  -   Proyek akan ditambahkan ke daftar dan siap dibuka.

4.  **Verifikasi File**:
  -   Pastikan folder `svm_orb_mask/models/` berisi file `.pkl` yang diperlukan.
  -   Pastikan folder `svm_orb_mask/assets/` berisi setidaknya satu file masker `.png` dengan format RGBA.

## Quickstart (Windows PowerShell)

1) Jalankan server Python:
```powershell
cd svm_orb_mask
py .\server.py
```

2) Jalankan Godot project:
- Buka `GodotTry-on/project.godot`
- Run scene `MaskTryon.tscn`

3) Di UI:
- Pilih masker dari tombol (server mengirim daftar otomatis)
- Atur Scale / OffsetX / OffsetY via slider
- Gunakan tombol “None” untuk menonaktifkan overlay

Catatan:
- Kotak hijau pada wajah telah dihapus di versi ini (feed bersih)
- Server memuat semua PNG di `svm_orb_mask/assets/` secara otomatis

## Struktur Proyek

```
GodotTry-on/
  MaskTryon.tscn
  MaskTryonController.gd
  WebcamManager.gd
svm_orb_mask/
  server.py
  assets/              # Mask PNG RGBA
  models/              # codebook.pkl, scaler.pkl, svm.pkl
  requirements.txt
```

## Protokol (Godot ↔ Server)

- Godot → Server:
  - `ping` — heartbeat/registrasi
  - `clothing:<mask_key>` — pilih masker atau `none`
  - `settings:scale=<f>;offset_x=<f>;offset_y=<f>` — pengaturan overlay
  - `list_masks` — minta daftar masker
- Server → Godot:
  - Frame JPEG terpaket (UDP, header 12 byte `!III`)
  - JSON balasan untuk `list_masks`: `{ "masks": ["alias", ...] }`

## Tips Masker

- Gunakan PNG RGBA, ukuran ≥ 400×400
- Nama file bebas; server melakukan normalisasi alias (contoh: `ski-mask-removebg-preview.png` → `ski-mask`)
- Tools bantu: `svm_orb_mask/tools/convert_mask_to_png_rgba.py`, `svm_orb_mask/tools/test_mask_validation.py`

## Evaluasi Model (Offline)

Gunakan perintah ini untuk menilai performa model BoVW+SVM pada dataset Anda.

1) Training (menyimpan artefak dan config):
```powershell
cd svm_orb_mask
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

Quick links:
- [models/test_metrics.json](svm_orb_mask/models/test_metrics.json)
- [models/pr_curve.png](svm_orb_mask/models/pr_curve.png)

## Dataset yang digunakan
- [Intel Image Classification (Kaggle)](https://www.kaggle.com/datasets/puneet6060/intel-image-classification) — dataset negatif (non-wajah)
- [LFW – People (Kaggle)](https://www.kaggle.com/datasets/atulanandjha/lfwpeople) — dataset positif (wajah)

## License

MIT.
