# Task 2 — Dimensional Model

---

## What We Built

Single-source dataset → purpose-built OBT stack in dbt + DuckDB

| Model | Layer | Type | Purpose |
|---|---|---|---|
| `stg_clinic_appointments` | staging | view | Type casts, renaming, quality flags |
| `date_spine` | ref | table | Date reference 2015–2030 |
| `appointments` | marts | table | OBT — primary BI surface |
| `patient_summary` | marts | table | Patient-level aggregate, standalone |

**`appointments` answers all four dashboard questions directly — no joins required at query time.**

---

## Why OBT, Not Star Schema

| | Star Schema | OBT (chosen) |
|---|---|---|
| Sources | Multiple — worth normalizing | Single table (`clinic_appointments`) |
| Patient history | Needs SCD2 dim to resolve point-in-time | Each row already carries state at scheduling time |
| BI tool joins | Fan-out at query time | Zero joins — single flat table |
| Maintenance | More models, more tests, more moving parts | 4 models total |

Star schema overhead only pays off when multiple source systems need to be integrated at the dimensional layer. That's not this dataset.

**Production path:** if a separate EHR or registration system is integrated, `dim_patient_history` (SCD2, BETWEEN join) replaces direct attribute sourcing. Pipeline orchestration via Dagster; medallion architecture (bronze/silver/gold).
