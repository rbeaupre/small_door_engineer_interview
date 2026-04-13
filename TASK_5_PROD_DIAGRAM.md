# Task 5 — Production Pipeline Sketch

---

## Architecture

```
┌─────────────────────────┐
│   Scheduling Software   │  source of truth for appointments + patient state
│                         │  must expose: updated_at, created_at, is_deleted
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Cloud Scheduler       │  triggers Dagster job on a schedule (e.g. nightly)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Dagster               │  owns the full asset graph — triggers Cloud Function,
│                         │  waits for raw load confirmation, then runs dbt
└────────────┬────────────┘
             │  triggers as a Dagster asset op
             ▼
┌─────────────────────────┐
│   Cloud Function        │  extracts from source API,
│   (GCP)                 │  writes raw Parquet to GCS,
│                         │  publishes row count metric to Cloud Monitoring
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│   GCS — raw zone        │  append-only, immutable, partitioned by load date
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│   BigQuery — raw        │  clinic_appointments (append-only, preserves updated_at)
│   dataset               │
└────────────┬────────────┘
             │  Dagster asset checks pass → dbt run kicks off
             ▼
┌─────────────────────────────────────────────────────────┐
│   dbt on BigQuery                                       │
│                                                         │
│   staging/   stg_clinic_appointments  (view)            │
│   ref/       date_spine               (table)           │
│   marts/     appointments             (incremental)     │
│              patient_summary          (table)           │
│   analysis/  no_show_by_lead_time     (table)           │
└────────────┬────────────────────────────────────────────┘
             ▼
┌─────────────────────────┐
│   Cube                  │  semantic layer — named measures, version-controlled
│                         │  metric definitions, sits in front of BigQuery
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│   BI tools              │  query through Cube — Looker Studio, Metabase,
│                         │  or any tool with a SQL or REST interface
└─────────────────────────┘
```

---

## Answering the Five Questions

**Where does data land, how does it move, what orchestrates it?**
Raw data lands in GCS (immutable, append-only) and is loaded into a BigQuery raw
dataset. Cloud Scheduler triggers the Dagster job. Dagster then triggers the Cloud
Function as an asset op — this keeps the full lineage (ingestion → staging → marts)
in one graph. If the Cloud Function fails, Dagster blocks the dbt run automatically.
GCS as the raw zone is intentional: if a dbt bug corrupts the marts, you can
reprocess from GCS without re-pulling from the source system.

**How do you test that the numbers are right?**
Three layers:
1. **Ingestion**: the Cloud Function publishes a row count metric to Cloud Monitoring
   after each run. A Cloud Monitoring alerting policy evaluates the time series and
   fires if today's load is significantly below the rolling average — catching silent
   truncations before they reach the warehouse. Cloud Monitoring stores the metric
   time series natively; no extra data store needed.
2. **dbt tests**: `unique`, `not_null`, and accepted-range tests on key columns. These
   run as Dagster asset checks and block downstream materializations on failure.
3. **Dagster asset checks**: row count assertions between raw and mart layers, and
   spot-checks on stable aggregates (e.g. overall no-show rate shouldn't shift more
   than a few percentage points week-over-week without a known cause).

**What breaks first when a source schema changes upstream?**
`stg_clinic_appointments` breaks first — it is the only model that references source
column names directly. This is intentional: centralising all source references in
the staging layer means a rename in the source requires a fix in one place. The
Dagster run fails at the staging asset, surfaces the error, and blocks all downstream
models. Nothing silently produces wrong numbers.

**How does an analyst know if today's data is stale?**
dbt source freshness is configured in `sources.yml` using `updated_at` as the
`loaded_at_field`:

```yaml
tables:
  - name: clinic_appointments
    loaded_at_field: updated_at
    freshness:
      warn_after:  {count: 12, period: hour}
      error_after: {count: 25, period: hour}
```

dbt runs `SELECT MAX(updated_at) FROM clinic_appointments` and compares to current
time. If the source is stale, the Dagster run aborts before any transforms execute.
`updated_at` serves double duty: it is both the incremental watermark for dbt models
and the freshness signal for source checks.

A monitoring dashboard built off dbt metadata (run results, test results, source
freshness logs) and Dagster's asset materialization history gives ops and data teams
a single place to check pipeline health.

**How do you handle Operations and Finance wanting different definitions of "no-show rate"?**
This is where Cube earns its place. Cube sits in front of BigQuery as the semantic
layer — all BI tools query through it rather than hitting BigQuery tables directly.
Metric definitions (`no_show_rate`, `utilization_rate`) are declared once in Cube's
data model, version-controlled, and peer-reviewed. If Operations and Finance need
different variants (e.g. Operations excludes same-day bookings, Finance includes
them), you define both as named measures in Cube with their respective filters.
BI tools surface those named measures; analysts can't accidentally invent a third
definition in a calculated field.

If the definitions require genuinely different source data (e.g. Finance needs
billing records that don't exist yet), you build a separate mart in dbt for that
domain when the data is available and wire it into Cube alongside the existing
measures. The principle throughout: every definition has a single owner, a written
spec, and a version-controlled implementation — never a spreadsheet.
