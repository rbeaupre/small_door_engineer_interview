# Small Door — Senior Data Engineer Case Study

Take-home case study for a Senior Data Engineer position. The scenario involves building a data model and analytical pipeline for a multi-clinic medical scheduling system, using a real dataset of ~110K appointment records.

The full prompt is in `case_study/Senior_Data_Engineer_Case_Study.md`.

## Getting started

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the pipeline

```bash
# Step 1 — Load raw CSV into DuckDB
python scripts/load_to_duckdb.py

# Step 2 — Build the dbt models
cd dbt && dbt run --profiles-dir . --full-refresh

# Step 3 — Run schema tests
dbt test --profiles-dir .

# Explore interactively
harlequin ../data/clinic.duckdb
```

## EDA

```bash
python scripts/eda.py    # prints findings to terminal, saves charts to charts/
```

## Repo structure

| Path | Description |
|------|-------------|
| `case_study/` | Original prompt and source CSV |
| `scripts/` | Ingestion and EDA scripts |
| `dbt/` | dbt project — staging, intermediate, and marts (OBT) |
| `charts/` | EDA chart outputs |
| `data/` | DuckDB database (generated — not committed) |
| `gamma/` | Slide-ready summaries for each task |
| `NOTES.md` | Detailed findings, decisions, and open questions |
