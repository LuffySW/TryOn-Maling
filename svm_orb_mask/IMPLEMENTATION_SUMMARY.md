# 🎯 Ringkasan Perubahan — Godot + Python UDP Mask Try-On

## 📝 Summary

Sistem diupgrade menjadi arsitektur client–server:

- Python server (`svm_orb_mask/server.py`) melakukan deteksi wajah (Haar + ORB BoVW + SVM), overlay masker PNG RGBA, dan streaming hasil via UDP ke Godot.
- Godot client (`GodotTry-on`) menampilkan stream, menyediakan UI untuk pilih masker (dinamis dari server) dan mengatur Scale/Offset (dikirim real-time ke server).

Perubahan penting: daftar masker dinamis (`list_masks`), normalisasi nama masker, pengaturan per-klien (scale/offset), pengiriman frame via UDP paket 1400B, tombol “None” (tanpa “T‑Shirt”), dan menghapus kotak hijau di wajah.

---

## ✅ File yang Dimodifikasi / Ditambahkan

### Python (server)
- `svm_orb_mask/server.py`
   - UDP listener: `ping`, `clothing:<key>`, `settings:scale=..;offset_x=..;offset_y=..`, `list_masks`
   - Dynamic asset discovery dari `assets/` (PNG RGBA), normalisasi alias
   - Per-klien state: mask terpilih dan settings overlay
   - Overlay RGBA dengan clipping dan alpha blending
   - Streaming JPEG via UDP, header `!III` (sequence, total_packets, packet_index)
   - Hapus gambar rectangle hijau pada wajah

### Godot (client)
- `GodotTry-on/MaskTryon.tscn`
   - UI Controls: tombol masker dinamis, slider Scale/OffsetX/OffsetY, Reset
- `GodotTry-on/MaskTryonController.gd`
   - Membangun tombol dari `list_masks` server; fallback scan lokal `svm_orb_mask/assets`
   - Mengirim pilihan masker (`clothing:<key>`) dan pengaturan overlay (scale/offset)
   - Label “None” untuk tanpa masker
- `GodotTry-on/WebcamManager.gd`
   - UDP client, reassembly frame, heartbeat `ping`
   - `request_masks_list()` + parsing respons JSON; emit `masks_list_received`
   - Validasi header frame agar tidak salah parse kontrol sebagai frame

---

## 🔌 Protokol & Kontrak

Input/Output (antar Godot ↔ server):
- Godot → Server:
   - `ping` (heartbeat; registrasi klien)
   - `clothing:<mask_key>` (pilih masker atau `none`)
   - `settings:scale=<f>;offset_x=<f>;offset_y=<f>` (float; clamp di server)
   - `list_masks` (minta daftar)
- Server → Godot:
   - UDP frame packets (JPEG chunked, header `!III`)
   - JSON `{"masks": ["alias", ...]}` sebagai respons `list_masks`

Sukses kriteria:
- UI menampilkan daftar masker dari server; tombol “None” ada.
- Slider mengubah overlay real-time tanpa restart.
- Tidak ada kotak hijau di feed.

---

## 🧪 Testing/Verifikasi

1) Jalankan server:
```powershell
cd svm_orb_mask
py .\server.py
```
2) Jalankan Godot scene `MaskTryon.tscn`
3) Pilih masker; geser slider Scale/Offset; lihat perubahan di stream
4) Pilih “None” untuk menonaktifkan overlay

Edge cases diuji:
- Tidak ada masker → UI fallback scan lokal (masih tampil “None”)
- Mask key berbeda dengan nama file → server normalisasi alias
- Paket kontrol JSON vs frame biner → validasi header di client

---

## 📁 Struktur Terkait

```
GodotTry-on/
   MaskTryon.tscn
   MaskTryonController.gd
   WebcamManager.gd
svm_orb_mask/
   server.py
   assets/  (PNG RGBA masker)
   models/  (codebook.pkl, scaler.pkl, svm.pkl)
   requirements.txt
```

---

## 📋 Catatan Developer

- Header UDP: gunakan big-endian `!III` (12 byte) dan gabungkan chunks di client.
- Hindari lambda inline langsung di `connect()` (Godot 4: assign ke var dulu).
- Hindari re-declare var lokal berulang (parser error) — gunakan inline check atau nama berbeda.
- Label opsi tanpa masker: “None”.

---

**Last Updated**: November 4, 2025  
**Env**: Windows PowerShell  
**Python**: 3.8+  
**Godot**: 4.x
