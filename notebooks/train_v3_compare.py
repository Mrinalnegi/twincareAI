"""
Model improvement pass:
1. Adds real derived features: pulse pressure, mean arterial pressure
   (deterministic clinical formulas from existing data — not invented values)
2. 5-fold stratified CV comparing: current MLP vs XGBoost vs LightGBM
3. Picks the best family by mean CV AUC
4. Retrains the winner on the full training set, evaluates ONCE on the
   same held-out test set used for v2 (fair comparison, no leakage)
5. Saves the final model + scaler

Run from ~/twincare.
First: pip install xgboost lightgbm -q
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
import joblib
import warnings
warnings.filterwarnings("ignore")

import xgboost as xgb
import lightgbm as lgb

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device for MLP: {device}\n")

# -----------------------------------------------------------------
# 1. Load + clean + feature engineer
# -----------------------------------------------------------------
df = pd.read_csv("framingham.csv")
df = df.dropna()

df = df.rename(columns={
    'male': 'sex', 'totChol': 'total_cholesterol', 'sysBP': 'systolic_bp',
    'diaBP': 'diastolic_bp', 'BMI': 'bmi', 'glucose': 'fasting_glucose',
    'heartRate': 'heart_rate',
})

# Real derived features — deterministic clinical formulas, no random noise,
# no invented values (unlike the old LDL/HDL/triglycerides fabrication)
df['pulse_pressure'] = df['systolic_bp'] - df['diastolic_bp']
df['map'] = df['diastolic_bp'] + (df['systolic_bp'] - df['diastolic_bp']) / 3

FEATURE_NAMES = [
    'age', 'sex', 'education', 'currentSmoker', 'cigsPerDay',
    'BPMeds', 'prevalentStroke', 'prevalentHyp', 'diabetes',
    'total_cholesterol', 'systolic_bp', 'diastolic_bp', 'bmi',
    'heart_rate', 'fasting_glucose', 'pulse_pressure', 'map',
]

X = df[FEATURE_NAMES].values.astype(np.float32)
y = df['TenYearCHD'].values.astype(np.float32)

print(f"Feature matrix: {X.shape} ({len(FEATURE_NAMES)} features)")
print(f"Positive rate: {y.mean():.1%}\n")

# Same split params as v2 -> same rows held out, fair comparison
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# -----------------------------------------------------------------
# 2. Model fit/predict helpers
# -----------------------------------------------------------------
class HeartDiseaseNetV2(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 64), nn.ReLU(), nn.BatchNorm1d(64), nn.Dropout(0.3),
            nn.Linear(64, 32), nn.ReLU(), nn.BatchNorm1d(32), nn.Dropout(0.2),
            nn.Linear(32, 16), nn.ReLU(),
            nn.Linear(16, 1),
        )
    def forward(self, x):
        return self.network(x).squeeze(-1)


def fit_mlp(X_tr, y_tr, epochs=80):
    n_pos, n_neg = y_tr.sum(), len(y_tr) - y_tr.sum()
    pos_weight = torch.tensor([n_neg / n_pos], dtype=torch.float32).to(device)
    train_ds = TensorDataset(torch.FloatTensor(X_tr), torch.FloatTensor(y_tr))
    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    model = HeartDiseaseNetV2(input_size=X_tr.shape[1]).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
    model.train()
    for _ in range(epochs):
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
    return model


def predict_mlp(model, X):
    model.eval()
    with torch.no_grad():
        probs = torch.sigmoid(model(torch.FloatTensor(X).to(device))).cpu().numpy()
    return probs


def fit_xgb(X_tr, y_tr):
    n_pos, n_neg = y_tr.sum(), len(y_tr) - y_tr.sum()
    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        scale_pos_weight=n_neg / n_pos, eval_metric="auc",
        tree_method="hist", random_state=42,
    )
    model.fit(X_tr, y_tr)
    return model


def fit_lgb(X_tr, y_tr):
    n_pos, n_neg = y_tr.sum(), len(y_tr) - y_tr.sum()
    model = lgb.LGBMClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        scale_pos_weight=n_neg / n_pos, min_child_samples=10,
        verbose=-1, random_state=42,
    )
    model.fit(X_tr, y_tr)
    return model


def metrics_at_threshold(y_true, probs, t=0.5):
    preds = (probs > t).astype(int)
    return {
        "auc": roc_auc_score(y_true, probs),
        "precision": precision_score(y_true, preds, zero_division=0),
        "recall": recall_score(y_true, preds, zero_division=0),
        "f1": f1_score(y_true, preds, zero_division=0),
    }


# -----------------------------------------------------------------
# 3. 5-fold stratified CV on the TRAINING set only (test set stays untouched)
# -----------------------------------------------------------------
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
results = {"mlp": [], "xgboost": [], "lightgbm": []}

print("Running 5-fold cross-validation (~1-2 min)...\n")

for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train)):
    X_tr, X_val = X_train[tr_idx], X_train[val_idx]
    y_tr, y_val = y_train[tr_idx], y_train[val_idx]
    y_val_int = y_val.astype(int)

    scaler_fold = StandardScaler()
    X_tr_s = scaler_fold.fit_transform(X_tr)
    X_val_s = scaler_fold.transform(X_val)

    mlp_model = fit_mlp(X_tr_s, y_tr)
    results["mlp"].append(metrics_at_threshold(y_val_int, predict_mlp(mlp_model, X_val_s)))

    xgb_model = fit_xgb(X_tr_s, y_tr)
    results["xgboost"].append(metrics_at_threshold(y_val_int, xgb_model.predict_proba(X_val_s)[:, 1]))

    lgb_model = fit_lgb(X_tr_s, y_tr)
    results["lightgbm"].append(metrics_at_threshold(y_val_int, lgb_model.predict_proba(X_val_s)[:, 1]))

    print(f"Fold {fold + 1}/5 done")

print("\n" + "=" * 72)
print("CROSS-VALIDATION RESULTS (mean ± std across 5 folds, threshold=0.5)")
print("=" * 72)
print(f"{'Model':<12}{'AUC':>18}{'Precision':>18}{'Recall':>18}{'F1':>15}")
mean_auc = {}
for name, folds in results.items():
    aucs = [f["auc"] for f in folds]
    precs = [f["precision"] for f in folds]
    recs = [f["recall"] for f in folds]
    f1s = [f["f1"] for f in folds]
    mean_auc[name] = np.mean(aucs)
    print(f"{name:<12}"
          f"{np.mean(aucs):.3f}±{np.std(aucs):.3f}      "
          f"{np.mean(precs):.3f}±{np.std(precs):.3f}      "
          f"{np.mean(recs):.3f}±{np.std(recs):.3f}      "
          f"{np.mean(f1s):.3f}±{np.std(f1s):.3f}")

best_model = max(mean_auc, key=mean_auc.get)
print(f"\nBest model by mean CV AUC: {best_model}")

# -----------------------------------------------------------------
# 4. Retrain winner on FULL training set, evaluate ONCE on held-out test set
# -----------------------------------------------------------------
print("\n" + "=" * 72)
print(f"FINAL: retraining '{best_model}' on full training set")
print("=" * 72)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

if best_model == "mlp":
    final_model = fit_mlp(X_train_scaled, y_train, epochs=150)
    probs_test = predict_mlp(final_model, X_test_scaled)
    torch.save(final_model.state_dict(), "heart_disease_model_v3.pt")
    joblib.dump(scaler, "scaler_v3.joblib")
    print("Saved: heart_disease_model_v3.pt, scaler_v3.joblib")
elif best_model == "xgboost":
    final_model = fit_xgb(X_train_scaled, y_train)
    probs_test = final_model.predict_proba(X_test_scaled)[:, 1]
    joblib.dump(final_model, "heart_disease_model_v3_xgb.joblib")
    joblib.dump(scaler, "scaler_v3.joblib")
    print("Saved: heart_disease_model_v3_xgb.joblib, scaler_v3.joblib")
else:
    final_model = fit_lgb(X_train_scaled, y_train)
    probs_test = final_model.predict_proba(X_test_scaled)[:, 1]
    joblib.dump(final_model, "heart_disease_model_v3_lgb.joblib")
    joblib.dump(scaler, "scaler_v3.joblib")
    print("Saved: heart_disease_model_v3_lgb.joblib, scaler_v3.joblib")

y_test_int = y_test.astype(int)
print(f"\nHeld-out test set — AUC-ROC: {roc_auc_score(y_test_int, probs_test):.4f}\n")
print(f"{'Threshold':>10}{'Precision':>12}{'Recall':>12}{'F1':>12}")
for t in [0.3, 0.4, 0.5]:
    m = metrics_at_threshold(y_test_int, probs_test, t)
    print(f"{t:>10.2f}{m['precision']:>12.3f}{m['recall']:>12.3f}{m['f1']:>12.3f}")

print(f"\nFeatures used ({len(FEATURE_NAMES)}): {FEATURE_NAMES}")

print("\n=== FEATURE_MEANS / FEATURE_STDS ===")
print("FEATURE_MEANS = {")
for i, name in enumerate(FEATURE_NAMES):
    print(f'    "{name}": {scaler.mean_[i]:.2f},')
print("}")
print("FEATURE_STDS = {")
for i, name in enumerate(FEATURE_NAMES):
    print(f'    "{name}": {scaler.scale_[i]:.2f},')
print("}")