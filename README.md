# SVM+ORB Torso Detector with T-shirt Overlay (BoVW, no deep learning)

A classical CV pipeline for upper-body detection and virtual try-on:
- ROI proposals: Haar upper-body cascade (fallback HOG person detector).
- Features: ORB descriptors on resized ROI (128×256 by default).
- Encoding: Bag of Visual Words via MiniBatchKMeans.
- Classifier: LinearSVC (default) or RBF SVM.
- Inference: ROI proposals → ORB → BoVW → SVM → NMS → T-shirt PNG overlay.

## Quickstart

- Python 3.10+
- Install dependencies:

```powershell
pip install -r svm_orb_tshirt/requirements.txt
```

- Prepare data (example folders; you can use your own):
  - Positives in `data/torso/`
  - Negatives in `data/non_torso/`

- Train (fit codebook + SVM and save artifacts to `svm_orb_tshirt/models/`):

```powershell
python svm_orb_tshirt/app.py train --pos_dir data/torso --neg_dir data/non_torso --k 256 --max_desc 200000 --svm linear --C 1.0
```

- Evaluate on held-out test split:

```powershell
python svm_orb_tshirt/app.py eval --report svm_orb_tshirt/models/test_metrics.json --pr svm_orb_tshirt/models/pr_curve.png
```

- Inference on a single image (with overlay):

```powershell
python svm_orb_tshirt/app.py infer --image input.jpg --out out.jpg --tshirt svm_orb_tshirt/assets/tshirt.png --show
```

- Webcam demo (toggle overlay with `t`, quit with `q`):

```powershell
python svm_orb_tshirt/app.py webcam --camera 0 --tshirt svm_orb_tshirt/assets/tshirt.png --show
```

## Project Structure

- CLI: `svm_orb_tshirt/app.py`
- Dataset/ROI: `svm_orb_tshirt/pipelines/dataset.py`
- Features/BoVW: `svm_orb_tshirt/pipelines/features.py`
- Training/Eval: `svm_orb_tshirt/pipelines/train.py`
- Inference/NMS: `svm_orb_tshirt/pipelines/infer.py`
- Overlay: `svm_orb_tshirt/pipelines/overlay.py`
- Utils: `svm_orb_tshirt/pipelines/utils.py`
- Models: `svm_orb_tshirt/models/` (codebook.pkl, scaler.pkl, svm.pkl, splits.json)
- Assets: put `svm_orb_tshirt/assets/tshirt.png` (transparent PNG with alpha)

## Dataset preparation

- If images are full scenes, the pipeline auto-proposes upper-body ROIs; positives/negatives come from proposals.
- Ensure at least ~100 positive and ~100 negative images for a decent toy model.
- Splits use 70/15/15 stratification and are saved to `svm_orb_tshirt/models/splits.json`.

## BoVW + SVM in simple terms

- ORB finds keypoints and descriptors per ROI (local patterns).
- K-means groups descriptor space into K “visual words” (codebook).
- Each ROI is represented by a histogram of visual words (BoVW), L1-normalized.
- Standardize features and train a linear or RBF SVM to classify torso vs non-torso.

## Overlay alignment

- T-shirt width ≈ 1.1 × torso width (configurable), placed near the top of the torso box.
- Optional rotation uses a gradient-based heuristic; disabled by default for speed.
- Alpha blending respects PNG transparency and clamps to frame bounds.

## CLI flags (common)

- `--k`: codebook size (e.g., 128–512). Larger may improve accuracy but costs time.
- `--max_desc`: cap on descriptors used to fit k-means.
- `--svm`: `linear` (fast) or `rbf` (more flexible). Default: `linear`.
- `--C`: regularization strength; try 0.5× and 2× for quick tuning.
- `--score_thresh`: minimum decision score to accept a torso before NMS.
- `--nms_iou`: IoU threshold for NMS (default 0.3).

## Acceptance tests (manual checklist)

1) Training completes on a toy dataset (≥100 pos/neg) in under ~2 minutes with k=256.
2) `app.py infer` produces an output image with at least one torso box and overlay on a suitable input.
3) Webcam mode reaches ~15 FPS on 720p on a mid-range laptop; `t` toggles overlay.
4) Test AP ≥ 0.85 with a reasonable dataset and tuned `k`/`C` (report saved to JSON).
5) Codebase is compact and passes a quick static check (syntax/type only) in editors/linters.

## Known limitations & ideas

- Haar/HOG can miss non-frontal or occluded torsos; try different parameters or add negatives.
- BoVW quality depends on codebook; try BRISK/AKAZE, different `k`, or TF-IDF weighting.
- Rotation is heuristic; classical pose/landmarks would improve alignment.
- Color/lighting mismatch between PNG and scene not corrected (future: color transfer).

## Linear vs RBF SVM

- LinearSVC is faster and usually sufficient with standardized BoVW features.
- RBF can model more complex boundaries; try `--svm rbf` with a small gamma grid (e.g., `scale`, 1e-3, 1e-4).
- Compare AP/ROC-AUC in `val_metrics.json` and `test_metrics.json`.

## License

MIT. See `svm_orb_tshirt/LICENSE`.
