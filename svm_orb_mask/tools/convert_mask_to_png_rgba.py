#!/usr/bin/env python3
"""
Script untuk mengkonversi masker JPG/PNG menjadi PNG dengan transparansi RGBA.
Berguna untuk membuat file masker yang kompatibel dengan try-on overlay system.

Usage:
    python convert_mask_to_png_rgba.py --input mask_original.jpg --output mask_transparent.png
    
    atau dengan background color custom:
    python convert_mask_to_png_rgba.py --input mask.jpg --output mask.png --bg-color "255,255,255"
"""

import argparse
import cv2
import numpy as np
from PIL import Image
import os
import sys


def convert_jpg_to_png_rgba(input_path, output_path, bg_color=(255, 255, 255), threshold=240):
    """
    Konversi JPG ke PNG dengan transparansi alpha.
    
    Args:
        input_path: Path ke file masker asli (JPG/PNG)
        output_path: Path untuk menyimpan PNG dengan alpha
        bg_color: Tuple RGB warna background yang akan dijadikan transparan (default: putih)
        threshold: Toleransi warna (0-255, default: 240)
    """
    
    print(f"Loading image: {input_path}")
    
    if not os.path.isfile(input_path):
        print(f"ERROR: File tidak ditemukan: {input_path}")
        return False
    
    # Baca dengan PIL
    try:
        img = Image.open(input_path)
        print(f"Original format: {img.format}, Mode: {img.mode}")
    except Exception as e:
        print(f"ERROR: Gagal membaca file: {e}")
        return False
    
    # Convert ke RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")
        print("Converted to RGBA mode")
    
    # Buat alpha channel berdasarkan background color
    pixels = img.getdata()
    new_data = []
    
    r_bg, g_bg, b_bg = bg_color
    
    for pixel in pixels:
        r, g, b = pixel[:3]
        
        # Cek apakah pixel mirip dengan background color
        if (abs(r - r_bg) <= threshold and 
            abs(g - g_bg) <= threshold and 
            abs(b - b_bg) <= threshold):
            # Jadikan transparan (alpha = 0)
            new_data.append((r, g, b, 0))
        else:
            # Pertahankan opacity penuh (alpha = 255)
            new_data.append((r, g, b, 255))
    
    img.putdata(new_data)
    
    # Buat direktori output jika belum ada
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    # Simpan sebagai PNG
    try:
        img.save(output_path, "PNG")
        print(f"✅ Berhasil menyimpan: {output_path}")
        print(f"   Format: PNG 4-channel RGBA")
        print(f"   Size: {img.size}")
        return True
    except Exception as e:
        print(f"ERROR: Gagal menyimpan file: {e}")
        return False


def verify_png_rgba(file_path):
    """Verifikasi apakah file adalah PNG 4-channel RGBA."""
    try:
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"ERROR: Gagal membaca file: {file_path}")
            return False
        
        print(f"\n📊 Informasi File PNG:")
        print(f"   Ukuran: {img.shape}")
        print(f"   Height: {img.shape[0]}")
        print(f"   Width: {img.shape[1]}")
        print(f"   Channels: {img.shape[2] if len(img.shape) > 2 else 1}")
        
        if len(img.shape) >= 3 and img.shape[2] == 4:
            print(f"   ✅ VALID: 4-channel BGRA (siap untuk try-on overlay)")
            return True
        else:
            print(f"   ❌ INVALID: Bukan 4-channel. Harus konversi ulang.")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Konversi masker JPG ke PNG dengan transparansi RGBA untuk try-on system"
    )
    
    parser.add_argument("--input", type=str, required=True, help="Path ke file masker asli (JPG/PNG)")
    parser.add_argument("--output", type=str, required=True, help="Path untuk menyimpan PNG transparan")
    parser.add_argument("--bg-color", type=str, default="255,255,255", 
                       help="RGB background color yang akan dijadikan transparan (default: 255,255,255 = putih)")
    parser.add_argument("--threshold", type=int, default=240, 
                       help="Toleransi warna untuk mendeteksi background (0-255, default: 240)")
    parser.add_argument("--verify", action="store_true", 
                       help="Verifikasi hasil PNG apakah sudah 4-channel RGBA")
    
    args = parser.parse_args()
    
    # Parse bg_color
    try:
        bg_color = tuple(map(int, args.bg_color.split(",")))
        if len(bg_color) != 3 or any(c > 255 or c < 0 for c in bg_color):
            raise ValueError
        print(f"Background color: RGB{bg_color}")
    except ValueError:
        print(f"ERROR: Format bg-color salah. Gunakan format: '255,255,255' (RGB)")
        return 1
    
    # Convert
    print("\n" + "="*60)
    print("KONVERSI MASKER KE PNG RGBA")
    print("="*60)
    
    success = convert_jpg_to_png_rgba(
        args.input, 
        args.output, 
        bg_color=bg_color,
        threshold=args.threshold
    )
    
    if success and args.verify:
        print("\n" + "="*60)
        print("VERIFIKASI HASIL")
        print("="*60)
        verify_png_rgba(args.output)
    
    print("\n" + "="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
