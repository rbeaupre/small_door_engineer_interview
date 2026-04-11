"""
Loads clinic_appointments.csv into a local DuckDB database (raw, unchanged).
Creates: data/clinic.duckdb  →  table: clinic_appointments

Run:
    python scripts/load_to_duckdb.py

Explore interactively:
    harlequin data/clinic.duckdb
"""

import os
import duckdb

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(SCRIPT_DIR)
CSV_PATH   = os.path.join(ROOT_DIR, "case_study", "clinic_appointments.csv")
DB_DIR     = os.path.join(ROOT_DIR, "data")
DB_PATH    = os.path.join(DB_DIR, "clinic.duckdb")

os.makedirs(DB_DIR, exist_ok=True)

con = duckdb.connect(DB_PATH)

con.execute("DROP TABLE IF EXISTS clinic_appointments")
con.execute(f"""
    CREATE TABLE clinic_appointments AS
    SELECT * FROM read_csv_auto('{CSV_PATH}', header=True)
""")

row_count = con.execute("SELECT COUNT(*) FROM clinic_appointments").fetchone()[0]
cols      = con.execute("DESCRIBE clinic_appointments").fetchdf()

print(f"Loaded {row_count:,} rows into clinic_appointments")
print(f"\nSchema:\n{cols[['column_name', 'column_type']].to_string(index=False)}")
print(f"\nDatabase written to: {DB_PATH}")
print(f"\nTo explore: harlequin {DB_PATH}")

con.close()
