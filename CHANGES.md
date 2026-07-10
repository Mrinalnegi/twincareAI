# TwinCare AI — Heart Disease Model: Changes & Next Steps

_Last updated: July 10, 2026_

## Summary

The original heart disease risk model (trained in `01_heart_disease.ipynb`) had two serious problems that made it unfit to ship. Both are now fixed in a retrained v2 model. This doc records what was wrong, what changed, and what's left to do before this is wired into the app.

---

## What was wrong with v1

### 1. Three input features were fabricated
The dataset used (Framingham Heart Study) does not include LDL cholesterol, HDL cholesterol, or triglycerides. The original notebook invented them with made-up linear formulas plus random noise:

```python
df['ldl_cholesterol'] = df['totChol'] * 0.6 + np.random.normal(0, 10, len(df))
df['hdl_cholesterol'] = 75 - df['totChol'] * 0.15 + np.random.normal(0, 8, len(df))
df['triglycerides'] = df['BMI'] * 5 + df['glucose'] * 0.3 + np.random.normal(0, 20, len(df))
```

This meant the model partly learned from synthetic noise, and any SHAP explanation involving these three features was meaningless.

### 2. The model wasn't actually detecting disease cases
The dataset is imbalanced (15.2% positive / 84.8% negative). Training with a plain, unweighted `BCELoss()` let the model take the easy path of mostly predicting "no disease."

Real evaluation on held-out data confirmed this:

| Metric | v1 result |
|---|---|
| Accuracy | 85.66% |
| Naive baseline accuracy (always predict "no disease") | 84.84% |
| **Recall** | **10.8%** |
| Precision | 66.7% |
| F1 | 0.186 |
| AUC-ROC | 0.723 |

Accuracy looked fine but was nearly identical to guessing the majority class every time. Recall of 10.8% meant the model caught only 12 of 111 real disease cases in the test set — it was missing 89% of the people it was supposed to flag. AUC of 0.723 showed the model *had* learned real signal, it just wasn't being forced to act on it.

---

## What changed in v2

| | v1 | v2 |
|---|---|---|
| Dataset | Framingham | Framingham (same) |
| Features | 10 (3 fabricated) | **15, all real, measured fields** |
| Loss function | `BCELoss()` (no weighting) | `BCEWithLogitsLoss(pos_weight=5.56)` — penalizes missed positives |
| Model selection criterion | lowest val loss | highest val **AUC** (better fit for imbalanced data) |
| Model output | `Sigmoid()` baked into network | raw logits — `sigmoid()` applied at inference time |

### New feature set (real Framingham fields only)
`age, sex, education, currentSmoker, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, total_cholesterol, systolic_bp, diastolic_bp, bmi, heart_rate, fasting_glucose`

### v2 results (threshold = 0.5)

| Metric | v1 | v2 |
|---|---|---|
| Recall | 10.8% | **67.6%** |
| Precision | 66.7% | 28.8% |
| F1 | 0.186 | **0.404** |
| AUC-ROC | 0.723 | 0.730 |
| Fabricated features | 3 of 10 | **0** |

Full threshold sweep for v2:

| Threshold | Precision | Recall | F1 |
|---|---|---|---|
| 0.3 | 0.214 | 0.820 | 0.339 |
| 0.4 | 0.252 | 0.748 | 0.376 |
| 0.5 | 0.288 | 0.676 | 0.404 |

**Precision is still modest (~25–30%)** — expected trade-off for prioritizing recall in a screening context. Roughly 1 in 3–4 people flagged actually has elevated risk, but the model now catches the majority of real cases instead of missing nearly all of them.

### Artifacts produced
- `heart_disease_model_v2.pt` — trained model weights (logits output)
- `scaler_v2.joblib` — fitted `StandardScaler` for the 15-feature input
- `FEATURE_MEANS` / `FEATURE_STDS` — printed at end of training run, needed for inference-time normalization without loading the joblib file

---

## What's left to do

### 1. Update backend inference code (`heart_model.py`)
- [ ] Replace `HeartDiseaseNet` class with `HeartDiseaseNetV2` (no `Sigmoid()` in the network — apply `torch.sigmoid()` after the forward pass instead)
- [ ] Swap in `heart_disease_model_v2.pt`
- [ ] Replace `FEATURE_MEANS` / `FEATURE_STDS` with the new 15-field values
- [ ] Update the feature ordering/list to match the 15 fields above

### 2. Update the app's data collection
The new feature set needs fields the OCR pipeline can't extract from a lab report alone:
- [ ] Add intake questionnaire fields: `education`, `currentSmoker`, `cigsPerDay`, `BPMeds`, `prevalentStroke`, `prevalentHyp`, `diabetes`
- [ ] Confirm `heart_rate` is captured (either from report vitals or intake)
- [ ] Confirm mapping: `total_cholesterol` → OCR'd cholesterol value, `systolic_bp`/`diastolic_bp` → OCR'd or entered BP, `fasting_glucose` → OCR'd glucose

### 3. Decide on production decision threshold
Current recommendation: **0.4** (74.8% recall / 25.2% precision) as a middle ground between 0.3 (higher recall, more false alarms) and 0.5 (fewer false alarms, more missed cases). This is a product decision, not just a technical one — depends on whether a clinician reviews flagged cases before the patient sees them.
- [ ] Confirm threshold with product/clinical stakeholders
- [ ] Hardcode chosen threshold in inference code (not just default 0.5)

### 4. Regenerate SHAP explainability plots
The existing `shap_summary.png` and waterfall plots were generated against the v1 model with fabricated features — they need to be redone against v2.
- [ ] Re-run SHAP `DeepExplainer` against `heart_disease_model_v2.pt` using the 15 real features
- [ ] Update any UI copy/labels that reference the old feature set (e.g. if the dashboard ever displayed "LDL cholesterol" as a factor)

### 5. Known limitations to document/communicate
- [ ] Framingham data is ~35–70 years old, single-population (Framingham, MA), may not generalize well to TwinCare's actual user base
- [ ] Precision (~25–30%) means most flags will be false positives — UI copy and copilot messaging should frame this as "worth a closer look," not "you have heart disease"
- [ ] Consider NHANES as a future upgrade path for a larger, more demographically diverse, lab-value-centric dataset (discussed earlier, not yet started)

---

## Environment notes (for reproducibility)
- Hardware: AMD Instinct MI210 (device ID `0x744b`), via AMD Developer Cloud
- ROCm version: 7.2.1
- PyTorch: 2.9.1+rocm6.4 (installed via `--index-url https://download.pytorch.org/whl/rocm6.4`)
- Dataset: Framingham Heart Study (Kaggle: `aasheesh200/framingham-heart-study-dataset`), 4,240 rows raw, 3,658 after dropping missing values
