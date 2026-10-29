# ML notebooks / training scripts
- `train_early_warning.py`  : XGBoost classifier on tabular hazard data (Kaggle flood/earthquake sets).
- `train_unet.py`           : U-Net segmentation on xBD (xView2) pre/post-disaster imagery.
Save trained weights to `ml/models/` and load them in `prediction/model.py` and `damage/segmentation.py`.
