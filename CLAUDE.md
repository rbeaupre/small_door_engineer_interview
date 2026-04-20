# CLAUDE.md — Context for AI-assisted work on this repo

## What this repo is

A take-home case study for a Senior Data Engineer position at Small Door. The dataset is `case_study/clinic_appointments.csv` (~110K appointment records). The task instructions are in `case_study/Senior_Data_Engineer_Case_Study.md`.

## Workflow

Tasks are worked through sequentially (Tasks 1–5). For each task:

1. **Implement** — write scripts under `scripts/`, output artifacts to the appropriate folder (`charts/`, `data/`, etc.)
2. **Document findings** — update `NOTES.md` with key findings, open questions, and decisions worth flagging for the panel
3. **Distill for presentation** — write a condensed, slide-ready version to `gamma/task_N_gamma.md`, which gets pasted into Gamma to generate the deliverable deck

`NOTES.md` is the working scratchpad — detailed, includes remaining work and open decisions.
`gamma/` files are the polished output — audience is the interview panel, not a developer.

## Repo structure

```
case_study/              Source materials (instructions + raw CSV)
charts/                  EDA chart outputs (PNG), named by section number
data/                    DuckDB database file(s)
dbt/                     dbt project — staging, intermediate, ref, marts, and analysis layers
  models/
    staging/             stg_clinic_appointments (view)
    intermediate/        int_clinic_appointments (view)
    ref/                 date_spine (table)
    marts/               appointments OBT, patient_summary, clinic_summary (tables)
    analysis/            no_show_by_lead_time (table)
gamma/                   Slide-ready markdown for Gamma
scripts/                 Python scripts (ingestion, EDA)
TASK_3_HARD_CALLS.md     Task 3 hard design decisions
TASK_5_PROD_DIAGRAM.md   Production pipeline sketch for Task 5
NOTES.md                 Running findings log and open decisions
requirements.txt         Pinned dependencies from the venv
```

## Environment

- Python venv at `venv/` — activate with `source venv/bin/activate`
- Run `pip freeze > requirements.txt` whenever new packages are added
- DuckDB database: `data/clinic.duckdb` — explore interactively with `harlequin data/clinic.duckdb`
- Charts are saved headless — always set `matplotlib.use("Agg")` before any pyplot import

## Preferences

- **Responses should be concise.** No trailing summaries of what was just done.
- **Don't make silent decisions.** If data is excluded from an analysis, the script should print why and how many rows were affected.
- **Don't clean beyond what's asked.** Data quality issues should be flagged and documented, not silently imputed or dropped. That belongs in a staged transformation layer, not a script.
- **Intermediate layer: flag and retain. Mart layer: filter for polished simplicity.** Quality flags live in `int_clinic_appointments` so audit queries are always possible. Mart models filter bad rows out so stakeholders never encounter ambiguous or impossible values.
- **Ask the slides target for Gamma files.** But keep them tight — one strong idea per slide, tables over prose where possible.
- **Prefer editing existing files over creating new ones.** Only create a new file if it clearly belongs to a new concern.
- When charts are added or renamed, keep numbering consistent with the section they belong to (e.g., `05a_`, `05b_` for two charts from section 5).
