#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

# Impor yang sudah disesuaikan dengan struktur Anda
from pipelines.train_pipeline import train_pipeline, eval_pipeline
from pipelines.infer import infer_image, infer_webcam, infer_video
from pipelines.utils import setup_logger

def main():
    parser = argparse.ArgumentParser(description="SVM+ORB Face Detector with Mask Overlay (BoVW)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # train
    p_train = sub.add_parser("train", help="Train codebook and SVM")
    p_train.add_argument("--pos_dir", type=str, default="data/faces", help="Path to positive face images")
    p_train.add_argument("--neg_dir", type=str, default="data/non_faces", help="Path to negative images")
    p_train.add_argument("--models_dir", type=str, default="models", help="Where to save models")
    p_train.add_argument("--k", type=int, default=256, help="Codebook size")
    p_train.add_argument("--max_desc", type=int, default=200000, help="Max descriptors for k-means")
    p_train.add_argument("--svm", type=str, default="linear", choices=["linear", "rbf"], help="SVM kernel")
    p_train.add_argument("--C", type=float, default=1.0, help="SVM C")
    p_train.add_argument("--seed", type=int, default=42)
    p_train.add_argument("--resize_w", type=int, default=128) # Sesuai training
    p_train.add_argument("--resize_h", type=int, default=128) # Sesuai training
    p_train.add_argument("--nfeatures", type=int, default=500)
    p_train.add_argument("--n_jobs", type=int, default=-1)
    p_train.add_argument("--proposer", type=str, default="face", choices=["face"], help="ROI proposer (default: face Haar cascade)")

    # eval
    p_eval = sub.add_parser("eval", help="Evaluate on test split")
    p_eval.add_argument("--models_dir", type=str, default="models")
    p_eval.add_argument("--report", type=str, default="models/test_metrics.json")
    p_eval.add_argument("--pr", type=str, default="models/pr_curve.png")
    p_eval.add_argument("--proposer", type=str, default="face", choices=["face"])

    # infer image
    p_infer = sub.add_parser("infer", help="Run inference on image (local test)")
    p_infer.add_argument("--image", type=str, required=True)
    p_infer.add_argument("--out", type=str, default="out.jpg")
    p_infer.add_argument("--mask", type=str, default="assets/haggus-skimask600x600.png", help="Path to mask PNG asset")
    p_infer.add_argument("--models_dir", type=str, default="models")
    p_infer.add_argument("--score_thresh", type=float, default=0.0)
    p_infer.add_argument("--nms_iou", type=float, default=0.3)
    p_infer.add_argument("--show", action="store_true")
    p_infer.add_argument("--proposer", type=str, default="face", choices=["face"])

    # webcam
    p_cam = sub.add_parser("webcam", help="Run local webcam demo (local test, not Godot server)")
    p_cam.add_argument("--camera", type=int, default=0)
    p_cam.add_argument("--models_dir", type=str, default="models")
    p_cam.add_argument("--mask", type=str, default="assets/ski-mask-removebg-preview.png", help="Path to mask PNG asset")
    p_cam.add_argument("--score_thresh", type=float, default=0.0)
    p_cam.add_argument("--nms_iou", type=float, default=0.3)
    p_cam.add_argument("--show", action="store_true", help="Show window preview")
    p_cam.add_argument("--proposer", type=str, default="face", choices=["face"])

    # video
    p_vid = sub.add_parser("video", help="Run inference on a video file (local test)")
    p_vid.add_argument("--video", type=str, required=True, help="Path to a video file")
    p_vid.add_argument("--models_dir", type=str, default="models")
    p_vid.add_argument("--mask", type=str, default="assets/ski-mask-removebg-preview.png", help="Path to mask PNG asset")
    p_vid.add_argument("--score_thresh", type=float, default=0.0)
    p_vid.add_argument("--nms_iou", type=float, default=0.3)
    p_vid.add_argument("--show", action="store_true")
    p_vid.add_argument("--proposer", type=str, default="face", choices=["face"])


    args = parser.parse_args()
    logger = setup_logger()

    if args.cmd == "train":
        os.makedirs(args.models_dir, exist_ok=True)
        cfg = vars(args)
        Path(args.models_dir, "config.json").write_text(json.dumps(cfg, indent=2))
        train_pipeline(args, logger) # Memanggil fungsi dari train_pipeline.py
    
    elif args.cmd == "eval":
        eval_pipeline(args, logger) # Memanggil fungsi dari train_pipeline.py
    
    elif args.cmd == "infer":
        infer_image(args, logger) # Memanggil fungsi dari infer.py
    
    elif args.cmd == "webcam":
        infer_webcam(args, logger) # Memanggil fungsi dari infer.py
    
    elif args.cmd == "video":
        setattr(args, "image", args.video) # Ganti nama argumen
        infer_video(args, logger) # Memanggil fungsi dari infer.py
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()