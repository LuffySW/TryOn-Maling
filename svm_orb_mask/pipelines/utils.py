import cv2
import numpy as np
import joblib
import os
import time
import logging

# --- SETUP LOGGER ---

def setup_logger(name="SVM-ORB", level=logging.INFO):
    """Membuat logger dengan format standar."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Handler untuk console
    ch = logging.StreamHandler()
    ch.setLevel(level)
    
    # Format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    
    # Tambahkan handler ke logger
    if not logger.handlers:
        logger.addHandler(ch)
    
    return logger

# --- FUNGSI HELPER (duplikat dari server.py, tapi untuk lokal) ---

def load_inference_models(models_dir, nfeatures, logger):
    """Memuat semua model yang diperlukan untuk inference."""
    logger.info("Memuat model...")
    try:
        kmeans = joblib.load(os.path.join(models_dir, "codebook.pkl"))
        scaler = joblib.load(os.path.join(models_dir, "scaler.pkl"))
        svm = joblib.load(os.path.join(models_dir, "svm.pkl"))
    except FileNotFoundError as e:
        logger.error(f"Gagal memuat file model: {e}")
        logger.error("Pastikan Anda sudah menjalankan 'app.py train' terlebih dahulu.")
        return None, None, None, None, None

    orb = cv2.ORB_create(nfeatures=nfeatures)
    
    # Muat Haar Cascade (proposer)
    cascade_path = "assets/haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        logger.error(f"Gagal memuat Haar Cascade dari {cascade_path}")
        return None, None, None, None, None
        
    logger.info("Model berhasil dimuat.")
    return orb, kmeans, scaler, svm, face_cascade

def get_bovw_vector(roi_gray, orb, kmeans, resize_dim):
    """Mengubah ROI grayscale menjadi vektor BoVW."""
    try:
        img_resized = cv2.resize(roi_gray, resize_dim)
        keypoints, descriptors = orb.detectAndCompute(img_resized, None)
        
        if descriptors is None:
            return None
            
        k = kmeans.n_clusters
        histogram = np.zeros(k, dtype=np.float32)
        words = kmeans.predict(descriptors)
        for w in words:
            histogram[w] += 1
            
        if np.sum(histogram) > 0:
            histogram = histogram / np.sum(histogram)
            
        return histogram
    except Exception:
        return None

def overlay_mask(background, mask_png, face_box):
    """Menempelkan masker PNG (dengan alpha) ke frame background."""
    try:
        (x, y, w, h) = face_box
        
        mask_w = int(w * 1.5)
        mask_h = int(mask_w * (mask_png.shape[0] / mask_png.shape[1]))
        mask_resized = cv2.resize(mask_png, (mask_w, mask_h), interpolation=cv2.INTER_AREA)
        
        pos_y = y - int(h * 0.25) 
        pos_x = x - int((mask_w - w) / 2)
        
        y1, y2 = max(0, pos_y), min(background.shape[0], pos_y + mask_h)
        x1, x2 = max(0, pos_x), min(background.shape[1], pos_x + mask_w)
        
        mask_y1 = max(0, -pos_y)
        mask_y2 = mask_y1 + (y2 - y1)
        mask_x1 = max(0, -pos_x)
        mask_x2 = mask_x1 + (x2 - x1)
        
        roi = background[y1:y2, x1:x2]
        mask_roi = mask_resized[mask_y1:mask_y2, mask_x1:mask_x2]
        
        mask_img_bgr = mask_roi[:, :, 0:3]
        alpha_mask = mask_roi[:, :, 3] / 255.0
        alpha_mask_3ch = cv2.cvtColor(alpha_mask, cv2.COLOR_GRAY2BGR)
        
        bg_part = (roi.astype(float) * (1.0 - alpha_mask_3ch)).astype(np.uint8)
        fg_part = (mask_img_bgr.astype(float) * alpha_mask_3ch).astype(np.uint8)
        
        blended_roi = cv2.add(bg_part, fg_part)
        background[y1:y2, x1:x2] = blended_roi
    except Exception:
        pass
    return background

# --- FUNGSI INFERENCE (YANG DIPANGGIL OLEH app.py) ---

def run_inference_on_frame(frame, orb, kmeans, scaler, svm, face_cascade, resize_dim, score_thresh):
    """Menjalankan deteksi + validasi pada satu frame."""
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 1. Proposal (Haar Cascade)
    proposals = face_cascade.detectMultiScale(
        frame_gray, 
        scaleFactor=1.1, 
        minNeighbors=5, 
        minSize=(80, 80)
    )
    
    validated_faces = []
    
    for (x, y, w, h) in proposals:
        roi_gray = frame_gray[y:y+h, x:x+w]
        
        # 2. Ekstraksi Fitur (ORB -> BoVW)
        bovw_vector = get_bovw_vector(roi_gray, orb, kmeans, resize_dim)
        
        if bovw_vector is not None:
            # 3. Scaling & 4. Klasifikasi (Validasi SVM)
            bovw_vector_scaled = scaler.transform(bovw_vector.reshape(1, -1))
            
            # Dapatkan skor kepercayaan
            score = svm.decision_function(bovw_vector_scaled)[0]
            
            if score >= score_thresh:
                validated_faces.append((x, y, w, h))
                
    return validated_faces

def infer_webcam(args, logger):
    """Menjalankan inference pada webcam (tes lokal)."""
    
    # Muat model
    models = load_inference_models(args.models_dir, 500, logger) # 500 = nfeatures
    if models[0] is None: return
    orb, kmeans, scaler, svm, face_cascade = models
    
    # Muat aset masker
    mask_asset = cv2.imread(args.mask, cv2.IMREAD_UNCHANGED)
    if mask_asset is None:
        logger.error(f"Gagal memuat file masker: {args.mask}")
        return
    
    # --- VALIDASI CHANNEL RGBA ---
    if len(mask_asset.shape) < 3 or mask_asset.shape[2] != 4:
        logger.error(f"Error: File masker '{args.mask}' BUKAN PNG 4-channel (BGRA).")
        logger.error("Masker Anda mungkin tidak punya latar belakang transparan.")
        logger.error("Silakan cari file PNG lain yang benar-benar transparan.")
        return
    # -------------------------------
        
    resize_dim = (128, 128) # Sesuai training
    
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        logger.error(f"Gagal membuka kamera {args.camera}")
        return

    logger.info("Memulai webcam... Tekan 'q' untuk keluar.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)
        
        # Jalankan inference
        faces = run_inference_on_frame(
            frame, orb, kmeans, scaler, svm, face_cascade, 
            resize_dim, args.score_thresh
        )
        
        # Overlay
        for (x, y, w, h) in faces:
            frame = overlay_mask(frame, mask_asset, (x, y, w, h))
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
        if args.show:
            cv2.imshow("Webcam (Tes Lokal)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    cap.release()
    cv2.destroyAllWindows()
    logger.info("Webcam ditutup.")

# --- Stub/Placeholder untuk fungsi lain ---

def infer_image(args, logger):
    logger.warning("Fungsi 'infer_image' belum diimplementasi.")
    # TODO:
    # 1. Muat model (panggil load_inference_models)
    # 2. Muat aset masker (cv2.imread)
    # 3. Muat gambar (cv2.imread(args.image))
    # 4. Jalankan inference (panggil run_inference_on_frame)
    # 5. Lakukan overlay (panggil overlay_mask)
    # 6. Simpan gambar (cv2.imwrite(args.out, frame))
    # 7. Jika args.show, tampilkan (cv2.imshow)

def infer_video(args, logger):
    logger.warning("Fungsi 'infer_video' belum diimplementasi.")
    # TODO: Logikanya mirip dengan infer_webcam, tapi
    # cap = cv2.VideoCapture(args.video)