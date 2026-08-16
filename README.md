# Crohn's Disease and IBD Tracker Dashboard

Local Streamlit app for tracking:

- Lab biomarkers
- Daily symptoms
- Food logs and trigger tags
- Uploaded PDFs and images
- Pattern findings and doctor exports

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Storage

- `data/health_data.json` stores all records
- `uploads/` stores uploaded files
- `data/exports/` stores generated doctor export files
