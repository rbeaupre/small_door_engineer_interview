# Small Door — Senior Data Engineer Case Study

---

## What We Built

Single-source dataset → purpose-built dbt stack on DuckDB

| Model | Layer | Type | Purpose |
|---|---|---|---|
| `stg_clinic_appointments` | staging | view | Type casts, renaming, quality flags |
| `date_spine` | ref | table | Date reference 2015–2030 |
| `appointments` | marts | table | OBT — primary BI surface |
| `patient_summary` | marts | table | Patient-level aggregate, standalone |
| `no_show_by_lead_time` | analysis | table | No-show × lead-time × SMS |

**All four dashboard questions are answerable from `appointments` with no joins at query time.**

---

## Data Quality

**Principle: flag and retain, never silently drop or impute.** Issues are surfaced as boolean flag columns — analysts choose whether to filter. Dropping rows hides problems; imputing values invents facts.

| Issue | Volume | Decision | Rationale |
|---|---|---|---|
| Age = −1 (impossible) | 1 row | Keep raw, `age_invalid = true` | Appointment is valid; only the age field is wrong |
| Age = 0 (ambiguous) | 3,539 rows | Keep, no flag | Could be infants or NULL sentinel — no data dictionary to confirm |
| Age > 110 | 5 rows | Keep, no flag | Biologically possible; not worth flagging without domain guidance |
| Negative lead time | 38,568 rows (~35%) | Keep raw, `lead_time_valid = false` | Two distinct populations (29% vs 5% no-show rate) — analysts should be explicit about which they include |
| Small clinics (n=1–2) | ~5 clinics | Keep all rows | Volume filtering belongs at the reporting layer, not the DDL |
| Disability encoded 0–4 | 2,241 rows with disability > 0 | Keep as integer | Ordinal severity count, not boolean; collapsing loses signal |

---

## Key Modeling Decisions

| Decision | Chose | Rejected | Would revisit if… |
|---|---|---|---|
| No `dim_patient_history` | Attributes carried directly from source row | SCD2 with BETWEEN join | Source team confirms attributes are backfilled at extraction time (historical rows silently overwritten with current values) |
| No `dim_clinic` | `clinic_name` direct from staging | 1-column lookup table | Operations system adds capacity/staffing data |
| `date_spine` joined on date value | Direct equality join | Compute date attrs inline | Data volumes grow significantly — drop the join, derive year/month/DOW directly from `appointment_at` |
| `sms_sent` as boolean | Flag on OBT | dim_sms | Multiple SMS messages per appointment with metadata |
| `disability` as integer 0–4 | Raw ordinal value | Cast to boolean | Domain confirms it is a simple flag |
| Clinic utilization proxy | `is_utilized = NOT no_show` | Capacity-based rate | Capacity feed from scheduling system available |

---

## Hard Call 1 — OBT vs Star Schema

**Decision:** flat OBT over a normalised star schema.

| | Star Schema | OBT (chosen) |
|---|---|---|
| Sources | Multiple — worth normalising | Single table (`clinic_appointments`) |
| Patient history | Needs SCD2 for point-in-time accuracy | Each row already carries state at scheduling time |
| BI tool joins | Fan-out at query time | Zero joins required |
| Maintenance | More models, more tests, more moving parts | 4 models total |

**Why OBT:**
Star schema solves an integration problem — joining entities across multiple source systems into a coherent fact table. Here there is no integration problem: one source table, one grain, all dashboard questions answerable with no joins at query time. Normalising a single source into a star schema adds structural overhead without solving anything the source hasn't already solved.

**Alternatives considered:**
- Star schema: `fct_appointments` + `dim_patient_history` (SCD2) + `dim_clinic` + `dim_date`
- Hybrid: star schema intermediate layer with OBT mart on top

**What would change our mind:** integration of a separate EHR or patient registration system — at that point dimensional modelling becomes necessary to resolve patient state correctly across sources. Medallion architecture (bronze/silver/gold), `dim_patient_history` SCD2 in the silver layer.

---

## Hard Call 2 — Patient Attributes on Each Row vs SCD2 Dimension

**Decision:** carry patient attributes (gender, age, condition flags) directly from staging rather than building a separate `dim_patient_history` SCD2 table.

**Alternatives considered:**
- SCD2 with BETWEEN date-range join for point-in-time accuracy *(we built and removed this)*
- Current-state-only `dim_patient` with equality join

**Why direct sourcing:** each appointment row in the source already records patient state at scheduling time — that is the history. A SCD2 would reconstruct point-in-time accuracy the source already provides natively. The join complexity is not justified for a single-source model.

**What would change our mind:** confirmation from the source team that attributes are backfilled to current values at extraction time. If true, every historical row in the OBT is silently wrong and SCD2 becomes mandatory.

---

## Hard Call 3 — Retain Negative Lead Times

**38,568 rows (~35%) have `scheduled_at > appointment_at`**

| Option | Problem |
|---|---|
| Drop rows | Silently biases no-show counts — these appointments happened |
| Null `lead_time_days` | Loses the distribution; can't inspect the artifact |
| Correct by swapping dates | Assumes we know the intent — we don't |
| **Flag and retain** ✓ | `lead_time_valid = false` — excluded from all no-show analysis by default |

**Evidence this is a timezone artifact, not bad data:**
- Max magnitude: −6.6 days — not consistent with random scheduling errors
- Pattern: `ScheduledDay` always carries a time component; `AppointmentDay` is always midnight UTC
- Volume: 35% is far too large to be noise

**Additional finding:** `lead_time_valid = FALSE` rows have a ~5% no-show rate vs ~29% for valid rows — these are two distinct populations, not just timezone-shifted versions of the same thing. Analysts should be explicit about which population they are analysing. Blending both without acknowledgement produces a misleading overall rate.

---


## Production Architecture — Q1: Data Movement & Orchestration

1. **Scheduling Software** — source of truth for appointments and patient state
2. **Cloud Scheduler** → triggers Dagster on a schedule
3. **Dagster** → triggers Cloud Function as an asset op; owns the full pipeline graph
4. **Cloud Function** → extracts from source API, writes raw Parquet to GCS
5. **GCS raw zone** — immutable, append-only; replay buffer if marts need rebuilding
6. **BigQuery raw dataset** — append-only; `updated_at` preserved for incremental runs
7. **dbt on BigQuery** — staging → ref → marts → analysis
8. **Cube** — semantic layer; named measures, version-controlled metric definitions
9. **BI tools** — query through Cube; no direct BigQuery access

**Q3 — What breaks first when source schema changes?** `stg_clinic_appointments` — the only model that references source column names directly. A rename in the source requires a fix in one place. Dagster fails the staging asset and blocks all downstream models automatically.

---

## Production — Q2: Testing + Q4: Freshness

**Q2 — How do you test that the numbers are right?**

| Layer | Mechanism | Catches |
|---|---|---|
| Ingestion | Cloud Function publishes row count to Cloud Monitoring; alert on significant drop vs rolling average | Silent truncations before they reach the warehouse |
| dbt | `unique`, `not_null`, range checks run as Dagster asset checks | Schema errors, constraint violations, out-of-range values |
| Dagster asset checks | Row count assertions between raw and mart layers | Row loss across the pipeline |

**Q4 — How does an analyst know if today's data is stale?**

dbt source freshness configured in `sources.yml` using `updated_at` as `loaded_at_field`. `updated_at` serves double duty: incremental watermark and freshness signal.

```yaml
loaded_at_field: updated_at
freshness:
  warn_after:  {count: 12, period: hour}
  error_after: {count: 25, period: hour}
```

If source is stale, Dagster aborts before any transforms run. Monitoring dashboard built from dbt metadata + Dagster asset materialisation history.

---

## Production — Q5: Metric Governance

**Operations and Finance will want different definitions of "no-show rate."**

**Solution: Cube as the semantic layer in front of BigQuery.**

- All BI tools query through Cube rather than hitting BigQuery tables directly
- `no_show_rate` variants are declared as named measures in Cube's data model — version-controlled, peer-reviewed, one owner per definition
- Analysts cannot invent a third definition in a calculated field
- If definitions diverge at the data level (e.g. Finance needs billing records), a separate dbt mart is built for that domain when the source data is available

**The principle throughout:** every metric definition has a single owner, a written spec, and a version-controlled implementation — never a spreadsheet or a BI tool calculated field.
