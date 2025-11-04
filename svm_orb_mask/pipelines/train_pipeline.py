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
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, precision_recall_curve, average_precision_score
import matplotlib.pyplot as plt

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

    models_dir = getattr(args, "models_dir", "models")
    report_path = getattr(args, "report", os.path.join(models_dir, "test_metrics.json"))
    pr_path = getattr(args, "pr", os.path.join(models_dir, "pr_curve.png"))

    # 1) Muat config untuk mengetahui sumber data dan parameter resize/nfeatures
    cfg_path = os.path.join(models_dir, "config.json")
    cfg = {}
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            logger.info(f"Config dimuat dari {cfg_path}")
        except Exception as e:
            logger.warning(f"Gagal membaca config.json: {e}")
    else:
        logger.warning(f"Config {cfg_path} tidak ditemukan. Menggunakan nilai default.")

    pos_dir = cfg.get("pos_dir", "data/faces")
    neg_dir = cfg.get("neg_dir", "data/non_faces")
    resize_w = int(cfg.get("resize_w", 128))
    resize_h = int(cfg.get("resize_h", 128))
    nfeatures = int(cfg.get("nfeatures", 500))

    # 2) Muat model (codebook, scaler, svm)
    codebook_path = os.path.join(models_dir, "codebook.pkl")
    scaler_path = os.path.join(models_dir, "scaler.pkl")
    svm_path = os.path.join(models_dir, "svm.pkl")

    if not (os.path.isfile(codebook_path) and os.path.isfile(scaler_path) and os.path.isfile(svm_path)):
        logger.error("Model tidak lengkap. Pastikan codebook.pkl, scaler.pkl, dan svm.pkl ada di models_dir.")
        return

    kmeans = joblib.load(codebook_path)
    scaler = joblib.load(scaler_path)
    svm = joblib.load(svm_path)
    logger.info("Model berhasil dimuat.")

    # 3) Muat data uji (gunakan seluruh dataset sebagai evaluasi jika tidak ada split terpisah)
    images, labels = load_dataset(pos_dir, neg_dir, logger)
    if images is None or labels is None or len(images) == 0:
        logger.error("Dataset kosong atau tidak dapat dimuat.")
        return

    # 4) Siapkan ORB dan buat histogram BoVW
    orb = cv2.ORB_create(nfeatures=nfeatures)
    resize_dim = (resize_w, resize_h)
    X = create_bovw_histograms(images, orb, kmeans, resize_dim, logger)
    y_true = labels

    # 5) Scale fitur dan prediksi
    X_scaled = scaler.transform(X)
    y_pred = svm.predict(X_scaled)

    # 6) Skor kontinu untuk PR curve
    scores = None
    if hasattr(svm, "decision_function"):
        try:
            scores = svm.decision_function(X_scaled)
        except Exception:
            scores = None
    if scores is None and hasattr(svm, "predict_proba"):
        try:
            scores = svm.predict_proba(X_scaled)[:, 1]
        except Exception:
            scores = None

    # 7) Metrik
    cls_report = classification_report(y_true, y_pred, target_names=["non-face (0)", "face (1)"], output_dict=True)
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred).tolist()

    # 8) Simpan report JSON
    out = {
        "accuracy": acc,
        "report": cls_report,
        "confusion_matrix": cm,
        "n_samples": int(len(y_true)),
        "models_dir": models_dir,
        "pos_dir": pos_dir,
        "neg_dir": neg_dir,
    }

    # 9) PR curve jika skor tersedia
    if scores is not None:
        try:
            precision, recall, _ = precision_recall_curve(y_true, scores)
            ap = average_precision_score(y_true, scores)
            out["average_precision"] = float(ap)

            plt.figure(figsize=(5, 4))
            plt.step(recall, precision, where="post", label=f"AP={ap:.3f}")
            plt.xlabel("Recall")
            plt.ylabel("Precision")
            plt.title("Precision-Recall Curve")
            plt.grid(True, alpha=0.3)
            plt.legend()
            os.makedirs(os.path.dirname(pr_path), exist_ok=True)
            plt.tight_layout()
            plt.savefig(pr_path)
            plt.close()
            logger.info(f"PR curve disimpan ke {pr_path}")
        except Exception as e:
            logger.warning(f"Gagal membuat PR curve: {e}")
    else:
        logger.warning("Model tidak menyediakan skor kontinu; PR curve dilewati.")

    try:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        logger.info(f"Laporan evaluasi disimpan ke {report_path}")
    except Exception as e:
        logger.error(f"Gagal menyimpan laporan evaluasi: {e}")