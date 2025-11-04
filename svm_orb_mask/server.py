import cv2
import numpy as np
import joblib
import os
import socket
import struct
import time
import threading
import json
import re

# --- KONFIGURASI ---
# Alamat server (harus sama dengan di WebcamManager.gd)
HOST = "127.0.0.1"
PORT = 9999

# Model & Aset (path dibuat relatif ke file ini)
BASE_DIR = os.path.dirname(__file__) or os.getcwd()
MODEL_DIR = os.path.join(BASE_DIR, "models")
ASSET_DIR = os.path.join(BASE_DIR, "assets")
HAAR_CASCADE_PATH = os.path.join(ASSET_DIR, "haarcascade_frontalface_default.xml")
CODEBOOK_PATH = os.path.join(MODEL_DIR, "codebook.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
SVM_PATH = os.path.join(MODEL_DIR, "svm.pkl")

# Pengaturan CV
ORB_FEATURES = 500
RESIZE_W = 128
RESIZE_H = 128
JPEG_QUALITY = 70
MAX_PACKET_SIZE = 1400  # Ukuran aman untuk paket UDP

# Variabel Global
# (ip, port) -> {"last_seen": time, "mask": str|None, "settings": {scale, offset_x, offset_y}}
clients = {}
client_lock = threading.Lock() # Untuk mengamankan akses ke dict 'clients'
global_sequence_number = 0

# Default settings per client
DEFAULT_SETTINGS = {
    "scale": 1.1,
    "offset_x": 0.0,
    "offset_y": -0.35,
}

# Variabel untuk model (diisi saat startup)
orb = None
kmeans = None
scaler = None
svm = None
face_cascade = None
mask_assets = {} # Menyimpan gambar masker yang sudah di-load: "nama_mask" -> img

# --- 1. FUNGSI HELPER: OVERLAY & VALIDASI ---

def overlay_mask(background, mask_png, face_box, settings=None):
    """Menempelkan masker PNG (dengan alpha) ke frame background."""
    try:
        (x, y, w, h) = face_box
        s = settings or DEFAULT_SETTINGS
        scale = float(s.get("scale", DEFAULT_SETTINGS["scale"]))
        offx = float(s.get("offset_x", DEFAULT_SETTINGS["offset_x"]))
        offy = float(s.get("offset_y", DEFAULT_SETTINGS["offset_y"]))

        # --- 1. Penyesuaian Ukuran & Posisi ---
        mask_w = int(w * scale)
        mask_h = int(mask_w * (mask_png.shape[0] / mask_png.shape[1]))
        mask_resized = cv2.resize(mask_png, (mask_w, mask_h), interpolation=cv2.INTER_AREA)

        pos_y = y + int(h * offy)
        pos_x = x + int(w * offx) - int((mask_w - w) / 2)

        # --- 2. Alpha Blending (dengan clipping) ---
        y1, y2 = max(0, pos_y), min(background.shape[0], pos_y + mask_h)
        x1, x2 = max(0, pos_x), min(background.shape[1], pos_x + mask_w)

        mask_y1 = max(0, -pos_y)
        mask_y2 = mask_y1 + (y2 - y1)
        mask_x1 = max(0, -pos_x)
        mask_x2 = mask_x1 + (x2 - x1)

        if y2 <= y1 or x2 <= x1:
            return background

        roi = background[y1:y2, x1:x2]
        mask_roi = mask_resized[mask_y1:mask_y2, mask_x1:mask_x2]

        if mask_roi is None or len(mask_roi.shape) < 3 or mask_roi.shape[2] != 4:
            return background

        mask_img_bgr = mask_roi[:, :, 0:3]
        alpha_mask = mask_roi[:, :, 3] / 255.0  # Normalisasi 0-1
        alpha_mask_3ch = cv2.merge([alpha_mask, alpha_mask, alpha_mask])

        bg_part = (roi.astype(float) * (1.0 - alpha_mask_3ch)).astype(np.uint8)
        fg_part = (mask_img_bgr.astype(float) * alpha_mask_3ch).astype(np.uint8)
        blended_roi = cv2.add(bg_part, fg_part)
        background[y1:y2, x1:x2] = blended_roi

    except Exception as e:
        print(f"Error overlay: {e}")
    return background


def get_bovw_vector(roi_gray):
    """Mengubah ROI grayscale menjadi vektor BoVW."""
    try:
        # Resize agar konsisten
        img_resized = cv2.resize(roi_gray, (RESIZE_W, RESIZE_H))

        # Ekstrak deskriptor
        keypoints, descriptors = orb.detectAndCompute(img_resized, None)
        if descriptors is None:
            return None  # Tidak ada fitur terdeteksi

        # Inisialisasi histogram
        k_bins = getattr(kmeans, "n_clusters", 64)
        histogram = np.zeros(k_bins, dtype=np.float32)

        # Prediksi "kata"
        words = kmeans.predict(descriptors)
        for w in words:
            histogram[int(w)] += 1

        # Normalisasi
        if np.sum(histogram) > 0:
            histogram = histogram / np.sum(histogram)

        return histogram

    except Exception:
        # print(f"Error BoVW: {e}")
        return None

# --- 2. FUNGSI THREAD: LISTENER & STREAMER ---

def _parse_settings(payload: str):
    """Parse payload settings 'scale=..;offset_x=..;offset_y=..'"""
    out = dict(DEFAULT_SETTINGS)
    try:
        parts = payload.split(";")
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                k = k.strip()
                v = float(v.strip())
                if k == "scale":
                    out["scale"] = max(0.5, min(2.5, v))
                elif k == "offset_x":
                    out["offset_x"] = max(-1.0, min(1.0, v))
                elif k == "offset_y":
                    out["offset_y"] = max(-1.0, min(1.0, v))
    except Exception as e:
        print(f"⚠️ Gagal parse settings: {e}")
    return out

def udp_listener():
    """Thread untuk mendengarkan pesan 'ping', 'clothing', dan 'settings' dari Godot."""
    global clients, client_lock
    
    # Buat socket UDP untuk mendengarkan
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))
    print(f"✅ Server UDP mendengarkan di {HOST}:{PORT}")
    
    while True:
        try:
            # Terima data (buffer 1024 bytes)
            data, addr = server_socket.recvfrom(2048)
            
            # Decode pesan
            message = data.decode('utf-8')
            
            with client_lock:
                # Jika klien baru, tambahkan
                if addr not in clients:
                    print(f"🔗 Klien baru terhubung: {addr}")
                    clients[addr] = {"last_seen": time.time(), "mask": None, "settings": dict(DEFAULT_SETTINGS)}
                
                # Perbarui waktu 'last_seen'
                clients[addr]["last_seen"] = time.time()
                
                if message == "ping":
                    pass # Cukup perbarui last_seen
                
                elif message.startswith("clothing:"):
                    # Klien memilih masker
                    mask_name = message.split(":", 1)[1].strip()
                    # Normalisasi dan pencocokan longgar
                    def _norm(s: str) -> str:
                        s = s.strip().lower()
                        s = s.replace(" ", "-").replace("_", "-")
                        s = re.sub(r"-+", "-", s)
                        s = s.replace("-removebg-preview", "").replace("-removebg", "")
                        return s
                    candidates = list(mask_assets.keys())
                    found = None
                    # 1) exact
                    if mask_name in mask_assets:
                        found = mask_name
                    else:
                        nsel = _norm(mask_name)
                        for k in candidates:
                            if k == mask_name or k.lower() == mask_name.lower() or _norm(k) == nsel:
                                found = k
                                break
                    if found:
                        clients[addr]["mask"] = found
                        print(f"👕 Klien {addr} memilih: {found}")
                    elif mask_name.lower() == "none" or mask_name == "T-Shirt": # Handle default
                        clients[addr]["mask"] = None
                        print(f"🚫 Klien {addr} melepas masker.")
                    else:
                        print(f"⚠️ Masker tidak ditemukan: {mask_name}")
                elif message.startswith("settings:"):
                    payload = message.split(":", 1)[1]
                    clients[addr]["settings"] = _parse_settings(payload)
                elif message.strip() == "list_masks":
                    try:
                        masks = list(mask_assets.keys())
                        payload = json.dumps({"masks": masks}).encode("utf-8")
                        server_socket.sendto(payload, addr)
                    except Exception as e:
                        print(f"Error sending mask list: {e}")
                        
        except Exception as e:
            print(f"Error Listener: {e}")

def webcam_streamer():
    """Thread utama untuk memproses webcam dan mengirimkan frame."""
    global clients, client_lock, global_sequence_number
    
    # Socket untuk MENGIRIM data
    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Buka webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Tidak bisa membuka webcam.")
        return
    
    print("📹 Webcam terbuka, memulai stream...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Frame webcam kosong, mencoba lagi...")
            time.sleep(0.1)
            continue
            
        # Balik frame secara horizontal (efek cermin)
        frame = cv2.flip(frame, 1)
        
        # Salin frame untuk diproses
        processed_frame = frame.copy()
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # --- Pipeline CV ---
        
        # 1. Proposal (Haar Cascade)
        proposals = face_cascade.detectMultiScale(
            frame_gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(80, 80)
        )
        
        # Simpan daftar wajah yang sudah divalidasi
        validated_faces = []
        
        for (x, y, w, h) in proposals:
            # Ambil ROI
            roi_gray = frame_gray[y:y+h, x:x+w]
            
            # 2. Ekstraksi Fitur (ORB -> BoVW)
            bovw_vector = get_bovw_vector(roi_gray)
            
            if bovw_vector is not None:
                # 3. Scaling & 4. Klasifikasi (Validasi SVM)
                bovw_vector_scaled = scaler.transform(bovw_vector.reshape(1, -1))
                prediction = svm.predict(bovw_vector_scaled)
                
                if prediction == 1:
                    # SVM setuju ini adalah wajah!
                    validated_faces.append((x, y, w, h))
        
        # Salin daftar klien aktif agar tidak mengunci terlalu lama
        with client_lock:
            now = time.time()
            # Ambil klien yang aktif dalam 10 detik terakhir
            active_clients = {addr: config for addr, config in clients.items() if (now - config["last_seen"]) < 10.0}
        
        if not active_clients:
            time.sleep(0.1) # Hemat CPU jika tidak ada klien
            continue

        # --- Pengiriman Frame ---
        
        # Tingkatkan nomor urut frame
        global_sequence_number = (global_sequence_number + 1) % 1_000_000 
        
        # Kirim frame yang diproses ke setiap klien
        for addr, config in active_clients.items():
            
            # 5. Overlay (sesuai pilihan klien)
            # Kita perlu frame baru untuk setiap klien jika maskernya beda
            # Untuk efisiensi, kita asumsikan semua klien dapat frame yang sama
            # (Modifikasi: kita akan overlay HANYA jika masker dipilih)
            
            client_frame = processed_frame.copy()
            
            if config["mask"] and config["mask"] in mask_assets:
                mask_to_apply = mask_assets[config["mask"]]
                for (x, y, w, h) in validated_faces:
                    # Terapkan overlay dengan settings per-klien (tanpa menggambar kotak)
                    client_frame = overlay_mask(client_frame, mask_to_apply, (x, y, w, h), settings=config.get("settings"))
            
            # 6. Encode ke JPEG
            ret, jpeg_data = cv2.imencode('.jpg', client_frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if not ret:
                continue
                
            jpeg_bytes = jpeg_data.tobytes()
            total_size = len(jpeg_bytes)
            
            # 7. Packetizing (Pecah jadi paket-paket UDP)
            num_packets = (total_size // MAX_PACKET_SIZE) + 1
            
            for i in range(num_packets):
                start = i * MAX_PACKET_SIZE
                end = (i + 1) * MAX_PACKET_SIZE
                chunk = jpeg_bytes[start:end]
                
                try:
                    # Buat header 12-byte (Big-Endian "!" - 3x Unsigned Int "III")
                    # Sesuai dengan parser di WebcamManager.gd
                    header = struct.pack("!III", global_sequence_number, num_packets, i)
                    
                    # Kirim header + chunk
                    send_socket.sendto(header + chunk, addr)
                    
                except Exception as e:
                    print(f"Error mengirim paket ke {addr}: {e}")
                    
        # Tunda sedikit agar tidak membanjiri CPU/jaringan (~30 FPS)
        time.sleep(0.03) 
        
    # Cleanup
    cap.release()
    send_socket.close()

# --- 3. FUNGSI UTAMA ---
def load_models():
    """Memuat semua model & aset ke variabel global."""
    global orb, kmeans, scaler, svm, face_cascade, mask_assets
    
    print("Memuat model dan aset...")
    
    # Model CV
    orb = cv2.ORB_create(nfeatures=ORB_FEATURES)
    face_cascade = cv2.CascadeClassifier(HAAR_CASCADE_PATH)
    if face_cascade.empty():
        print(f"❌ FATAL: Gagal memuat Haar Cascade dari {HAAR_CASCADE_PATH}")
        return False
        
    # Model ML
    try:
        kmeans = joblib.load(CODEBOOK_PATH)
        scaler = joblib.load(SCALER_PATH)
        svm = joblib.load(SVM_PATH)
    except FileNotFoundError as e:
        print(f"❌ FATAL: Gagal memuat file model: {e}")
        print("Pastikan Anda sudah menjalankan 'train_pipeline.py' terlebih dahulu.")
        return False
        
    # Aset Masker (PNG RGBA) - deteksi otomatis berdasarkan file yang ada
    # Kami mencoba mencocokkan alias ke file yang tersedia di folder assets/
    available_files = {f.lower(): f for f in os.listdir(ASSET_DIR) if f.lower().endswith(".png")}

    def _pick_file(candidates):
        # candidates: list of substrings to look for in filenames
        for fname_lower, fname_orig in available_files.items():
            if all(sub in fname_lower for sub in candidates):
                return fname_orig
        return None

    alias_to_candidates = {
        "ski-mask": [["ski", "mask"], ["skimask"], ["ski-mask"]],
        "anonymous-mask": [["anonymous"], ["anon"]],
        "haggus-mask": [["haggus", "mask"], ["haggus", "ski"]],
    }

    resolved = {}
    for alias, cand_lists in alias_to_candidates.items():
        chosen = None
        for cand in cand_lists:
            chosen = _pick_file(cand)
            if chosen:
                break
        if chosen:
            resolved[alias] = chosen

    if not resolved:
        print("⚠️ Tidak ada file masker PNG ditemukan di assets/. Hanya streaming kamera tanpa masker.")
    else:
        for alias, filename in resolved.items():
            path = os.path.join(ASSET_DIR, filename)
            mask = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if mask is not None and len(mask.shape) == 3 and mask.shape[2] == 4:
                # Tambahkan alias utama
                mask_assets[alias] = mask
                # Tambahkan alias berbasis nama file (lebih permisif)
                base = os.path.splitext(filename)[0]
                base_norm = re.sub(r"-+", "-", base.replace(" ", "-").replace("_", "-").lower())
                base_norm = base_norm.replace("-removebg-preview", "").replace("-removebg", "")
                mask_assets.setdefault(base_norm, mask)
                print(f"  > Berhasil memuat aset: {alias} ({filename})")
            else:
                print(f"  > GAGAL memuat aset: {alias} ({filename}). Harus PNG transparan (RGBA).")

        # Info untuk debug
        print("🎭 Alias masker yang tersedia:", ", ".join(mask_assets.keys()) or "(none)")

    print("✅ Semua model dan aset berhasil dimuat.")
    return True

if __name__ == "__main__":
    if load_models():
        # Jalankan listener di thread terpisah
        listener_thread = threading.Thread(target=udp_listener, daemon=True)
        listener_thread.start()
        
        # Jalankan streamer webcam di thread utama
        webcam_streamer()
    else:
        print("Gagal memulai server karena model/aset tidak lengkap.")