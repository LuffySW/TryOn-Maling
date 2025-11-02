import os
import shutil
import time

# --- KONFIGURASI ---

# 1. Atur path ke folder LFW Anda yang sudah diekstrak
SOURCE_LFW_DIR = "D:\\SMT5\\PCD\\Try-On\\svm_orb_tshirt\\lfw_funneled"

# 2. Atur folder tujuan
DEST_DIR = "data/faces"

# ---------------------

def flatten_lfw_dataset(source_dir, dest_dir):
    """
    Menyalin semua file .jpg dari subdirektori di source_dir 
    ke satu direktori dest_dir, dengan nama unik baru.
    """
    
    print(f"Mulai memproses dataset dari: {source_dir}")
    print(f"Menyimpan semua gambar ke: {dest_dir}")
    
    # 1. Buat folder tujuan jika belum ada
    os.makedirs(dest_dir, exist_ok=True)
    
    start_time = time.time()
    image_counter = 0
    
    # 2. os.walk() akan menjelajahi setiap folder dan subfolder
    for root, dirs, files in os.walk(source_dir):
            
        for filename in files:
            # 3. Pastikan kita hanya mengambil file gambar
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                
                # 4. Buat nama file baru yang unik
                person_name = os.path.basename(root) 
                base_filename = os.path.splitext(filename)[0]
                new_filename = f"{person_name}_{base_filename}.jpg"
                
                # 5. Tentukan path sumber dan tujuan
                source_path = os.path.join(root, filename)
                dest_path = os.path.join(dest_dir, new_filename)
                
                # 6. Salin file
                try:
                    shutil.copy(source_path, dest_path)
                    image_counter += 1
                    
                    if image_counter % 100 == 0:
                        print(f"  ...berhasil menyalin {image_counter} gambar", end='\r')

                except Exception as e:
                    print(f"Gagal menyalin {source_path}: {e}")

    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n\nSelesai!")
    print(f"Total gambar disalin: {image_counter}")
    print(f"Waktu yang dibutuhkan: {total_time:.2f} detik")

# --- Jalankan Skrip ---
if __name__ == "__main__":
    if not os.path.isdir(SOURCE_LFW_DIR):
        print(f"Error: Folder sumber tidak ditemukan di '{SOURCE_LFW_DIR}'")
        print("Pastikan Anda sudah mengekstrak file .tgz dan mengatur path 'SOURCE_LFW_DIR' dengan benar.")
    else:
        flatten_lfw_dataset(SOURCE_LFW_DIR, DEST_DIR)