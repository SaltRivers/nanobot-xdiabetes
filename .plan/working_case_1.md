### User Qeury
```
Please check that whether the patient with patient_ids 4 in cohort `Dataset/private_fundus` has diabetes, and what would the probability be?
```

### agent call tool (Whatever tool that reach the same effect, can be html post or python code etc.)
```
curl -X POST http://localhost:8000/predict_csv \
  -H "Content-Type: application/json" \
  -d '{
    "cohort_dir": "Dataset/private_fundus",
    "patient_id": 4,
    "checkpoint_path": "checkpoints/deepdr_ehr_text/best.pt",
    "config_path": "src/configs/deepdr_ehr_text.yaml",
    "output_format": "probabilities"
  }'
```