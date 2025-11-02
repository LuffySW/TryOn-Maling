#!/usr/bin/env python3
"""
Test script untuk verifikasi implementasi validasi masker RGBA.

Usage:
    python test_mask_validation.py
"""

import cv2
import os
import sys
import logging
from pathlib import Path

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MaskTest")

def test_mask_validation():
    """Test masker validation logic."""
    
    print("\n" + "="*60)
    print("TEST: Masker RGBA Validation")
    print("="*60 + "\n")
    
    test_files = [
        "assets/haggus-skimask600x600.png",
        "assets/haarcascade_frontalface_default.xml",
    ]
    
    results = []
    
    for mask_path in test_files:
        print(f"Testing: {mask_path}")
        
        if not os.path.isfile(mask_path):
            print(f"  ⚠️  File tidak ditemukan: {mask_path}\n")
            results.append((mask_path, "NOT_FOUND"))
            continue
        
        try:
            mask_asset = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
            
            if mask_asset is None:
                print(f"  ❌ ERROR: Gagal membaca file\n")
                results.append((mask_path, "READ_ERROR"))
                continue
            
            # Validation logic
            if len(mask_asset.shape) < 3 or mask_asset.shape[2] != 4:
                logger.error(f"Error: File masker '{mask_path}' BUKAN PNG 4-channel (BGRA).")
                logger.error("Masker Anda mungkin tidak punya latar belakang transparan.")
                logger.error("Silakan cari file PNG lain yang benar-benar transparan.")
                print(f"  ❌ FAILED: Not 4-channel RGBA\n")
                results.append((mask_path, "INVALID_FORMAT"))
            else:
                print(f"  ✅ PASSED: 4-channel RGBA")
                print(f"     Shape: {mask_asset.shape}")
                print(f"     Channels: {mask_asset.shape[2]}\n")
                results.append((mask_path, "VALID"))
        
        except Exception as e:
            print(f"  ❌ ERROR: {e}\n")
            results.append((mask_path, "EXCEPTION"))
    
    print("="*60)
    print("TEST RESULTS")
    print("="*60)
    
    for file_path, status in results:
        status_symbol = "✅" if status == "VALID" else "❌"
        print(f"{status_symbol} {file_path}: {status}")
    
    print("="*60 + "\n")
    
    # Summary
    valid_count = sum(1 for _, s in results if s == "VALID")
    total_count = len(results)
    
    print(f"Summary: {valid_count}/{total_count} files are valid PNG 4-channel RGBA")
    
    if valid_count == total_count and total_count > 0:
        print("✅ All tests PASSED! Mask overlay should work correctly.\n")
        return 0
    else:
        print("⚠️  Some tests failed. Check MASK_REQUIREMENTS.md for solutions.\n")
        return 1

if __name__ == "__main__":
    exit_code = test_mask_validation()
    sys.exit(exit_code)
