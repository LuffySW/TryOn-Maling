import os
import shutil
import time

# --- KONFIGURASI ---

# 1. Atur path ke folder Intel Image Anda yang sudah diekstrak
SOURCE_DATA_DIRS = [
    "data/Intel-Image-Classification/seg_train",
    "data/Intel-Image-Classification/seg_test"
]

# 2. Atur folder tujuan
DEST_DIR = "data/non_faces"

# ---------------------

def flatten_scene_dataset(source_dirs, dest_dir):
    """
    Menyalin semua file .jpg dari subdirektori di source_dirs 
    ke satu direktori dest_dir, dengan nama unik baru.
    """
    
    print(f"Mulai memproses dataset negatif...")
    print(f"Menyimpan semua gambar ke: {dest_dir}")
    
    # 1. Buat folder tujuan jika belum ada
    os.makedirs(dest_dir, exist_ok=True)
    
    start_time = time.time()
    image_counter = 0
    
    # Loop melalui setiap folder sumber (seg_train, seg_test)
    for source_dir in source_dirs:
        if not os.path.isdir(source_dir):
            print(f"Peringatan: Folder sumber tidak ditemukan di '{source_dir}'. Dilewati.")
            continue
            
        print(f"\nMemproses dari: {source_dir}")
        
        # 2. os.walk() akan menjelajahi setiap subfolder kategori
        for root, dirs, files in os.walk(source_dir):
                
            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    
                    # 4. Buat nama file baru yang unik
                    category_name = os.path.basename(root) 
                    base_filename = os.path.splitext(filename)[0]
                    new_filename = f"{category_name}_{base_filename}.jpg"
                    
                    # 5. Tentukan path sumber dan tujuan
                    source_path = os.path.join(root, filename)
                    dest_path = os.path.join(dest_dir, new_filename)
                    
                    # 6. Salin file
                    try:
                        # Cek agar tidak duplikat jika nama file sama
                        if not os.path.exists(dest_path):
                            shutil.copy(source_path, dest_path)
                            image_counter += 1
                        
                        if image_counter % 100 == 0:
                            print(f"  ...berhasil menyalin {image_counter} gambar", end='\r')

                    except Exception as e:
                        print(f"Gagal menyalin {source_path}: {e}")

    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n\nSelesai!")
    print(f"Total gambar negatif disalin: {image_counter}")
    print(f"Waktu yang dibutuhkan: {total_time:.2f} detik")

# --- Jalankan Skrip ---
if __name__ == "__main__":
    if not any(os.path.isdir(d) for d in SOURCE_DATA_DIRS):
        print("Error: Tidak ada folder sumber yang ditemukan.")
        print(f"Pastikan path di 'SOURCE_DATA_DIRS' sudah benar: {SOURCE_DATA_DIRS}")
    else:
        flatten_scene_dataset(SOURCE_DATA_DIRS, DEST_DIR)