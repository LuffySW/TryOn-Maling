import cv2
import numpy as np
import os
import joblib
import json

# Optimasi Intel
try:
    from sklearnex import patch_sklearn
    patch_sklearn()
    print("Intel(R) Extension for Scikit-learn* diaktifkan.")
except ImportError:
    print("Intel(R) Extension for Scikit-learn* tidak ditemukan. Berjalan dalam mode standar.")

from sklearn.cluster import MiniBatchKMeans
from sklearn.svm import LinearSVC, SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score

# --- FUNGSI HELPER (YANG DIPANGGIL OLEH FUNGSI UTAMA) ---

def load_dataset(pos_dir, neg_dir, logger):
    """Memuat gambar dari folder positif dan negatif."""
    images = []
    labels = []
    
    logger.info(f"Memuat gambar positif dari {pos_dir}...")
    if not os.path.isdir(pos_dir):
        logger.error(f"Folder positif tidak ditemukan: {pos_dir}")
        return None, None
    for filename in os.listdir(pos_dir):
        img_path = os.path.join(pos_dir, filename)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            images.append(img)
            labels.append(1) # 1 = Face

    logger.info(f"Memuat gambar negatif dari {neg_dir}...")
    if not os.path.isdir(neg_dir):
        logger.error(f"Folder negatif tidak ditemukan: {neg_dir}")
        return None, None
    for filename in os.listdir(neg_dir):
        img_path = os.path.join(neg_dir, filename)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            images.append(img)
            labels.append(0) # 0 = Non-Face
            
    logger.info(f"Total gambar dimuat: {len(images)}")
    return images, np.array(labels)

def extract_all_descriptors(images, orb, resize_dim, logger):
    """Mengekstrak deskriptor ORB dari semua gambar."""
    all_descriptors = []
    logger.info("Mengekstrak deskriptor ORB dari semua gambar...")
    for i, img in enumerate(images):
        img_resized = cv2.resize(img, resize_dim)
        keypoints, descriptors = orb.detectAndCompute(img_resized, None)
        
        if descriptors is not None:
            all_descriptors.append(descriptors)
        
        if (i+1) % 200 == 0:
            logger.info(f"  ...diproses {i+1}/{len(images)} gambar")
            
    return np.vstack(all_descriptors)

def build_codebook(descriptors, k, logger):
    """Melatih k-means untuk membuat codebook."""
    logger.info(f"Membangun codebook dengan k={k}...")
    kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=k*10, n_init=3)
    kmeans.fit(descriptors)
    logger.info("Codebook (k-means) berhasil dilatih.")
    return kmeans

def create_bovw_histograms(images, orb, kmeans, resize_dim, logger):
    """Mengubah setiap gambar menjadi vektor histogram BoVW."""
    k = kmeans.n_clusters
    histograms = []
    logger.info("Membuat histogram BoVW untuk setiap gambar...")
    
    for img in images:
        histogram = np.zeros(k, dtype=np.float32)
        img_resized = cv2.resize(img, resize_dim)
        keypoints, descriptors = orb.detectAndCompute(img_resized, None)
        
        if descriptors is not None:
            words = kmeans.predict(descriptors)
            for w in words:
                histogram[w] += 1
            if np.sum(histogram) > 0:
                histogram = histogram / np.sum(histogram)
                
        histograms.append(histogram)
        
    logger.info("Histogram BoVW selesai dibuat.")
    return np.array(histograms)

# --- FUNGSI UTAMA (YANG DIPANGGIL OLEH app.py) ---

def train_pipeline(args, logger):
    """Fungsi utama untuk pipeline training."""
    
    logger.info("--- Memulai Pipeline Training ---")
    
    # 1. Load Dataset
    images, labels = load_dataset(args.pos_dir, args.neg_dir, logger)
    if images is None:
        return

    # 2. Inisialisasi ORB
    orb = cv2.ORB_create(nfeatures=args.nfeatures)
    resize_dim = (args.resize_w, args.resize_h)

    # 3. Ekstrak deskriptor
    all_descriptors = extract_all_descriptors(images, orb, resize_dim, logger)
    
    # 4. Bangun Codebook
    kmeans = build_codebook(all_descriptors, args.k, logger)
    joblib.dump(kmeans, os.path.join(args.models_dir, "codebook.pkl"))
    logger.info(f"Codebook disimpan ke {args.models_dir}/codebook.pkl")

    # 5. Buat Vektor Fitur (X)
    X = create_bovw_histograms(images, orb, kmeans, resize_dim, logger)
    y = labels
    
    # 6. Split Data
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=args.seed, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=args.seed, stratify=y_temp)
    logger.info(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

    # 7. Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    joblib.dump(scaler, os.path.join(args.models_dir, "scaler.pkl"))
    logger.info(f"Scaler disimpan ke {args.models_dir}/scaler.pkl")
    
    # 8. Training SVM
    logger.info(f"Melatih {args.svm} SVM...")
    if args.svm == "linear":
        svm = LinearSVC(C=args.C, dual="auto", random_state=args.seed, max_iter=5000)
    else: # rbf
        svm = SVC(kernel='rbf', C=args.C, random_state=args.seed, probability=True)
        
    svm.fit(X_train_scaled, y_train)
    logger.info("SVM berhasil dilatih.")
    
    # 9. Simpan Model SVM
    joblib.dump(svm, os.path.join(args.models_dir, "svm.pkl"))
    logger.info(f"Model SVM disimpan ke {args.models_dir}/svm.pkl")
    
    # 10. Evaluasi cepat di test set
    logger.info("\n--- Hasil Evaluasi Cepat pada Test Set ---")
    X_test_scaled = scaler.transform(X_test)
    y_pred = svm.predict(X_test_scaled)
    report = classification_report(y_test, y_pred, target_names=["non-face (0)", "face (1)"])
    logger.info("\n" + report)

def eval_pipeline(args, logger):
    """Fungsi untuk evaluasi model (dipanggil oleh app.py eval)."""
    logger.info("--- Memulai Pipeline Evaluasi ---")
    
    # Implementasi evaluasi (jika diperlukan)
    # Saat ini, training sudah melakukan evaluasi dasar.
    # Anda bisa menambahkan logika di sini untuk memuat model dan 
    # menjalankannya pada data tes secara spesifik.
    logger.warning("Fungsi 'eval' belum diimplementasi penuh.")
    logger.info("Silakan merujuk pada hasil evaluasi di akhir proses 'train'.")
    
    # Contoh jika Anda ingin menjalankannya:
    # 1. Load model (kmeans, scaler, svm)
    # 2. Load data tes (atau data dari config)
    # 3. Buat histogram BoVW
    # 4. Scale histogram
    # 5. Jalankan svm.predict
    # 6. Buat laporan