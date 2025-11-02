import cv2
import numpy as np
import joblib
import os
import time

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
        
        mask_w = int(w * 1.1)  
        mask_h = int(mask_w * (mask_png.shape[0] / mask_png.shape[1]))
        mask_resized = cv2.resize(mask_png, (mask_w, mask_h), interpolation=cv2.INTER_AREA)
        
        pos_y = y - int(h * 0.35) #
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
        alpha_mask_3ch = cv2.merge([alpha_mask, alpha_mask, alpha_mask])
        
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
    """Menjalankan inference pada satu file gambar."""
    logger.info(f"Memulai inferensi pada gambar: {args.image}")
    
    # 1. Muat model
    models = load_inference_models(args.models_dir, 500, logger)
    if models[0] is None:
        logger.error("Gagal memuat model. Keluar.")
        return
    orb, kmeans, scaler, svm, face_cascade = models
    
    # 2. Muat aset masker
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
    
    # 3. Muat gambar
    if not os.path.isfile(args.image):
        logger.error(f"File gambar tidak ditemukan: {args.image}")
        return
    
    frame = cv2.imread(args.image)
    if frame is None:
        logger.error(f"Gagal membaca gambar dari: {args.image}")
        return
    
    logger.info(f"Gambar berhasil dimuat. Ukuran: {frame.shape}")
    
    resize_dim = (128, 128)  # Sesuai training
    
    # 4. Jalankan inference
    faces = run_inference_on_frame(
        frame, orb, kmeans, scaler, svm, face_cascade,
        resize_dim, args.score_thresh
    )
    
    logger.info(f"Ditemukan {len(faces)} wajah tervalidasi")
    
    # 5. Lakukan overlay dan annotasi
    for (x, y, w, h) in faces:
        frame = overlay_mask(frame, mask_asset, (x, y, w, h))
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, "Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # 6. Simpan gambar
    output_path = args.out
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    cv2.imwrite(output_path, frame)
    logger.info(f"Gambar hasil simpan ke: {output_path}")
    
    # 7. Tampilkan jika --show flag ada
    if args.show:
        cv2.imshow("Hasil Inferensi", frame)
        logger.info("Tekan tombol apa saja untuk menutup jendela...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    logger.info("Inferensi gambar selesai.")

def infer_video(args, logger):
    """Menjalankan inference pada file video."""
    video_path = args.video if hasattr(args, 'video') else args.image
    logger.info(f"Memulai inferensi pada video: {video_path}")
    
    # 1. Muat model
    models = load_inference_models(args.models_dir, 500, logger)
    if models[0] is None:
        logger.error("Gagal memuat model. Keluar.")
        return
    orb, kmeans, scaler, svm, face_cascade = models
    
    # 2. Muat aset masker
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
    
    # 3. Buka video
    if not os.path.isfile(video_path):
        logger.error(f"File video tidak ditemukan: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Gagal membuka video: {video_path}")
        return
    
    # Dapatkan informasi video
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    logger.info(f"Video info: {width}x{height} @ {fps} fps, total frames: {total_frames}")
    
    # 4. Siapkan video writer untuk output
    output_path = args.out if hasattr(args, 'out') else "output_video.mp4"
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        logger.warning(f"Gagal membuka video writer. Coba format codec lain...")
        # Fallback ke MJPEG
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        output_path = output_path.replace('.mp4', '.avi')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    resize_dim = (128, 128)  # Sesuai training
    frame_count = 0
    
    logger.info("Memproses video... Ini mungkin memakan waktu lama.")
    
    # 5. Proses setiap frame
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Jalankan inference
        faces = run_inference_on_frame(
            frame, orb, kmeans, scaler, svm, face_cascade,
            resize_dim, args.score_thresh
        )
        
        # Overlay dan annotasi
        for (x, y, w, h) in faces:
            frame = overlay_mask(frame, mask_asset, (x, y, w, h))
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, "Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Tambahkan info frame
        cv2.putText(frame, f"Frame: {frame_count}/{total_frames}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Faces: {len(faces)}", (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Tulis frame ke output video
        out.write(frame)
        
        # Tampilkan preview jika --show flag ada
        if args.show:
            cv2.imshow("Video Inference", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                logger.info("User membatalkan proses (tekan 'q')")
                break
        
        # Tampilkan progress setiap 30 frames
        if frame_count % 30 == 0:
            logger.info(f"  ...diproses {frame_count}/{total_frames} frames")
    
    # 6. Bersihkan
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    logger.info(f"Video hasil simpan ke: {output_path}")
    logger.info(f"Total frames diproses: {frame_count}")
    logger.info("Inferensi video selesai.")
