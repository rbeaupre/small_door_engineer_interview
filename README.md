# Small Door — Senior Data Engineer Case Study

Take-home case study for a Senior Data Engineer position. The scenario involves building a data model and analytical pipeline for a multi-clinic medical scheduling system, using a real dataset of ~110K appointment records.

The full prompt is in `case_study/Senior_Data_Engineer_Case_Study.md`.

## Getting started

```bash
# Create and activate the virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running the scripts

```bash
# Task 1 — EDA: descriptive stats, data quality flags, and charts
python scripts/eda.py

# Load raw data into DuckDB
python scripts/load_to_duckdb.py

# Explore the database interactively
harlequin data/clinic.duckdb
```

## Repo structure

| Path | Description |
|------|-------------|
| `case_study/` | Original prompt and source CSV |
| `scripts/` | Python scripts, one per task step |
| `charts/` | EDA chart outputs |
| `data/` | DuckDB database |
| `gamma/` | Slide-ready summaries for each task |
| `NOTES.md` | Detailed findings and open decisions |
