# EDA Findings & Open Decisions

## Task 1 Key Findings

### Grain
- AppointmentID is unique — one row per appointment confirmed.
- 62,299 distinct patients across 110,527 appointments.
- 39.1% of patients have >1 appointment; one patient has 88. Patient is NOT an independent unit.

### Date / Lead-time
- **38,568 rows (~35%)** have negative lead-time (ScheduledDay > AppointmentDay) — but this is two distinct populations:
  - **38,563 rows**: same-calendar-day appointments where AppointmentDay is stored as midnight UTC and ScheduledDay carries a time component. Zero SMS reminders sent to any of them. 4.7% no-show rate. These are walk-in/drop-in appointments — retained in mart with `same_day_appointment = true`.
  - **5 rows**: appointment date strictly precedes schedule date across calendar days. All are no-shows. No plausible clinical explanation — filtered from mart, retained in intermediate with `lead_time_genuinely_negative = true`.
- Lead-time monotonically predicts no-show up to ~60 days (same-day ~14% → 31–60d ~34%).

### Age
- 1 row: Age = −1 (impossible)
- 3,539 rows: Age = 0 (ambiguous — infants or NULL sentinel)
- 5 rows: Age > 110 (edge outliers)

### Clinics
- 81 distinct clinics, but volume is extremely skewed (CV ≈ 1.0): Greenwood Village has 7,717 appts; Industrial Park has 1.
- Clinics with <50 appointments (Trindade Shores = 2, Industrial Park = 1) have statistically meaningless rates.

### No-show
- Overall rate: **20.2%** — but this is a blended figure across two distinct populations. Scheduled appointments have ~29% no-show; same-day walk-ins (`same_day_appointment = true`) have ~5%. These populations behave differently and analysts should be explicit about which they are analysing.
- **Caveat:** any no-show analysis should document whether it includes or excludes same-day walk-ins and why. Blending the two without acknowledgement produces a misleading rate.
- Clinic range: 0% (n=1) to 100% (n=2) — small clinics dominate extremes.
- After excluding sub-50 clinics, range is roughly 15%–29%.

### Disability
- Encoded as 0–4, not boolean. Values: 0=108,286 / 1=2,042 / 2=183 / 3=13 / 4=3.
- Treating as binary loses ordinal severity information.

### Condition flags
- LowIncome: modestly higher no-show (23.7% vs 19.8%).
- Hypertension / Diabetes / Disability: slightly LOWER no-show (likely older, more adherent patients).
- SubstanceUseDisorder: nearly identical (20.2% vs 20.1%) — very rare flag.
- **SMSReminder: associated with HIGHER no-show (27.6% vs 16.7%)** — unsure if this is selection bias.

---

## Task 2 — Model Design Decisions

### Design Decisions & Rationale

**OBT over star schema**
The dashboard questions (no-show rates by clinic, lead-time as predictor, SMS confounding, patient risk profile) are all answerable from a single flat table. The source is one table — `clinic_appointments`. An OBT avoids join-time fan-out in BI tools, is simpler to maintain, and is more honest about what the data is. A star schema adds structural overhead that only pays off when multiple source systems need to be integrated at the dimensional layer.

**No dim_patient_history**
Patient attributes (gender, age, condition flags) are already present on every appointment row — each row reflects the patient's state as recorded at scheduling time (see Assumption 2). A separate SCD2 patient dimension would reconstruct point-in-time accuracy that the source already provides natively. The join complexity is not justified for a single-source model.
If patient attributes were sourced from a separate registration or EHR system, a `dim_patient_history` with a BETWEEN join would be the correct approach. In a production medallion architecture (bronze/silver/gold, orchestrated via Dagster), patient history would live in the silver layer as a proper SCD2 sourced from the registration system.

**No dim_clinic**
The only clinic attribute in the source is `clinic_name`. A one-column lookup table adds a join without contributing information. If an operations system is integrated (capacity, location, staffing), a `dim_clinic` should be added at that point.

**date_spine joined on date value**
`appointments` joins to `date_spine` on `CAST(appointment_at AS DATE)` directly rather than via a surrogate integer key. This is simpler and has negligible performance cost at current data volumes.

**sms_sent as a boolean column (no dim_sms)**
SMSReminder is a 0/1 flag stored as `sms_sent BOOLEAN` directly in the OBT. A 2-row lookup dimension adds a join without contributing information. If future data includes multiple SMS messages per appointment (delivery status, campaign IDs, timestamps), promote to a separate table at that point.

**Disability as integer (0–4)**
Kept as the raw integer. The distinct values (0–4) suggest an ordinal severity count, not a boolean flag. Casting to boolean would collapse patients with multiple disabilities into the same category as those with one. No assumption is made about what the values mean — that requires domain input.

**Clinic utilization definition**
Without capacity data (total available slots per clinic), true utilization rate cannot be computed. `is_utilized` on the `appointments` OBT is the closest proxy available: whether a scheduled slot was actually attended (`NOT no_show`). Aggregate as `SUM(is_utilized) / COUNT(*)` per clinic to get an attended-appointment rate.
A historical baseline approach was considered — using a clinic's own appointment volume over a reference period as a capacity proxy, or using the cross-clinic median as a benchmark. Both were rejected because they rely on assumptions that cannot be verified from this data alone: that all clinics operate at similar capacity, have comparable staffing levels, and that volume in the reference period was itself "normal." Given the extreme volume skew across clinics (CV ≈ 1.0), these assumptions are almost certainly wrong. The honest answer is that utilization requires a capacity feed from an operations or scheduling system, and the model is designed to join to one if it becomes available.

**Clinic volume threshold**
No minimum volume filter is encoded into the model. The decision of what constitutes a "statistically meaningful" clinic belongs in dashboard queries or documented conventions, not the DDL.

---

### Data Cleansing Decisions

**Philosophy: flag and retain in intermediate (`int_clinic_appointments`); filter for polished simplicity in the mart (`appointments`).** Bad rows are always available for audit via the intermediate model.

**Age = -1 (1 row)**
Flagged as `age_invalid = true` in intermediate. Filtered out of the mart — the mart is the stakeholder surface and should not expose impossible values.

**Age = 0 (3,539 rows)**
Left as-is, no flag. Likely newborns — deep-dive shows Age = 0 + LowIncome patients have a *lower* no-show rate (13.5% vs ~20% overall), consistent with parents not skipping newborn appointments. Without a data dictionary, flagging would be an unjustified assumption.

**Age > 110 (5 rows)**
No flag. Biologically possible; not worth flagging without domain guidance.

**Negative lead times (38,568 rows)**
Two populations — see Date / Lead-time section above. Walk-ins flagged and retained; 5 genuinely negative rows flagged in intermediate and filtered from mart. Rationale: see Assumption 3.

**Small clinics**
No rows removed. All 81 clinics are in the model. Volume-based filtering belongs at the reporting layer.

---

### Dashboard Q&A (Cube + BI tool against `appointments`)

**Q1 — Which clinics have the highest no-show rates, and is that stable over time?**
Create a calculated metric: `SUM(no_show) / COUNT(appointment_id)` as `no_show_rate`. Build a bar chart ranked by `no_show_rate` with `clinic_name` as the dimension. For stability, add a time series chart with `year` + `quarter` on the x-axis, `no_show_rate` as the metric, and `clinic_name` as a breakdown series. Note: consider applying a minimum volume filter (e.g. `COUNT(appointment_id) >= 50`) as a report-level filter to suppress statistically meaningless rates from small clinics.

**Q2 — Does the gap between scheduling and appointment date predict no-shows?**
Filter to `same_day_appointment = FALSE` to exclude walk-in rows. Create a calculated bucket field:
```
CASE
  WHEN lead_time_days = 0 THEN 'Same day'
  WHEN lead_time_days <= 7 THEN '1–7 days'
  WHEN lead_time_days <= 30 THEN '8–30 days'
  WHEN lead_time_days <= 60 THEN '31–60 days'
  ELSE '60+ days'
END
```
Plot `no_show_rate` by bucket as a bar chart.

**Q3 — Do SMS reminders correlate with lower no-show rates, or is that confounded?**
Simple split: `no_show_rate` segmented by `sms_sent` (true/false) as a scorecard or bar. The raw result will show SMS patients have *higher* no-show rates — a potential selection bias artifact (e.g. "are higher-risk patients preferentially reminded?"). To surface the confounding, we could add a secondary dimension like `low_income`, `hypertension`, or even `lead_time_days` as a filter or breakdown and compare SMS vs no-SMS within the same patient segment.

**Q4 — What does a "patient risk profile" look like across clinics?**
Use `patient_summary` (standalone model) or aggregate `appointments` directly. For each clinic, compute the share of patients with each condition flag: `SUM(low_income) / COUNT(DISTINCT patient_id)`, same for `hypertension`, `diabetes`, etc. A heatmap or stacked bar with `clinic_name` on one axis and condition flags on the other gives a side-by-side risk profile. Can also define a composite risk score in a calculated field (e.g. sum of condition flags) and rank clinics by average patient risk.

---

### Implementation Assumptions

**Assumption 1 — clinic_appointments is the only data source, but it grows continuously**
`clinic_appointments` is treated as the single source of truth for all appointment, patient, and clinic data. No separate patient registration system, EHR feed, or clinic operations table is assumed to exist. However, the table is assumed to be continuously updated — new appointment records are appended over time via a batch or streaming process (e.g. Dagster pipeline). This is why the model is designed to be re-run on a schedule with `--full-refresh` rather than treated as a one-time static extract. If additional source systems were integrated, the architecture would move to a medallion (bronze/silver/gold) approach with a proper `dim_patient_history` SCD2 in the silver layer.

**Assumption 2 — Each appointment row records patient state at scheduling time**
The patient attributes on each row (age, gender, condition flags) are treated as reflecting the patient's state as recorded when the appointment was scheduled, not at time of visit or at time of data extraction. This is the basis for using the appointment row's own attributes directly rather than resolving them through a separate patient dimension. If this assumption is wrong — i.e., attributes are backfilled to current values at extraction time — then the OBT would silently contain incorrect historical values and a proper SCD2 approach would be required.

**Assumption 3 — Negative lead times are a timezone artifact, not scheduling errors**
The 38,568 rows where `scheduled_at > appointment_at` are treated as same-day bookings where the recorded timestamp crossed midnight UTC rather than genuine data entry errors. The evidence: the magnitude is small (max −6.6 days, median close to zero), `ScheduledDay` always carries a time component while `AppointmentDay` is always midnight UTC, and the volume (35% of records) is too large to be explained by random entry errors alone.

However, the `lead_time_valid = FALSE` group has a ~5% no-show rate vs ~29% for valid rows — a material difference that suggests these rows represent a genuinely distinct appointment type (possibly walk-ins or urgent slots), not just timezone-shifted same-day bookings. Analysts should treat them as a separate population and be explicit about which group they are including. Depending on the question, either group — or both separately — may be the right scope.

---

### Implementation

Implemented with dbt + dbt-duckdb. All transformations live in `dbt/models/`.

```
dbt/models/
  staging/       stg_clinic_appointments    ← type casts and renaming only (view)
  intermediate/  int_clinic_appointments    ← quality fixes, flags, derived columns (view)
  ref/           date_spine                 ← date reference table 2015–2030 (table)
  marts/         appointments               ← OBT; primary BI surface (table)
                 patient_summary            ← patient-level aggregate; standalone (table)
                 clinic_summary             ← clinic-level aggregate; enables volume filtering (table)
  analysis/      no_show_by_lead_time       ← no-show rate by lead-time bucket × SMS (table)
```

Run: `cd dbt && dbt run --profiles-dir . --full-refresh`
Test: `cd dbt && dbt test --profiles-dir .`

### Incremental Strategy (production path with Dagster)

Currently all models run as full rebuilds (`--full-refresh`). This is fine for the static case study dataset but does not scale as `clinic_appointments` grows.

**Required source columns (source system must expose these; Cloud Function preserves them on ingestion):**

| Column | Type | Purpose |
|---|---|---|
| `updated_at` | `TIMESTAMPTZ` | Watermark for incremental filtering — set on insert, updated on any change. This is the critical column. |
| `created_at` | `TIMESTAMPTZ` | Distinguishes new records from updates; useful for monitoring pipeline freshness. |
| `is_deleted` | `BOOLEAN` | Soft-delete flag for cancelled appointments. Without it, deletions in the source are invisible to the warehouse. |

`appointment_id` serves as the natural `unique_key` for dbt's upsert/merge behavior.

**`appointments` OBT (incremental)**
Switch to `materialized='incremental'` with `unique_key='appointment_id'` and `updated_at` as the watermark:
```sql
{{ config(materialized='incremental', unique_key='appointment_id') }}
...
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```
New and updated appointment rows are merged; unchanged rows are untouched.

**`patient_summary` (full rebuild or scheduled merge)**
This model aggregates over all appointments per patient, so incremental logic is less straightforward — a patient's summary changes whenever any of their appointments changes. Options: (a) rebuild fully on each Dagster run (acceptable at current scale), or (b) maintain as an incremental model with `unique_key='patient_id'` that recomputes stats for only affected patients each run. Option (b) requires knowing which patients had activity in the current batch, which `updated_at` on the source enables.

**`date_spine` and `stg_clinic_appointments`**
`date_spine` is static reference data — full rebuild is always correct and fast. `stg_clinic_appointments` is a view, so it reflects the current source state on every query automatically.

### Real-time Architecture (if near-real-time is required)

The batch architecture above shifts substantially for real-time ingestion. The dbt model structure and marts stay the same — only the ingestion layer changes.

**What changes:**
- **Pub/Sub replaces Cloud Scheduler as the trigger**: the source system publishes an event to a Pub/Sub topic on every appointment create, update, or cancel. Cloud Scheduler no longer drives the pipeline.
- **Dataflow replaces the Cloud Function**: Cloud Functions work for low-volume batch but lack backpressure handling and exactly-once semantics at scale. Dataflow (Apache Beam) subscribes to Pub/Sub, windows the stream, and writes to GCS (raw archive) and BigQuery (Storage Write API) in parallel.
- **dbt runs on a short cadence**: triggered every 15–30 minutes via a Dagster sensor that fires when new rows appear in the raw BigQuery table. Incremental models become essential — `--full-refresh` on a 15-minute cycle is not viable.
- **Dagster switches from schedule-based to sensor-based**: a sensor watches the raw table for activity and kicks off the asset graph, rather than running on a fixed clock.
- **Cube cache TTL shortens**: Cube's query cache needs a much shorter TTL to serve data that's actually fresh.

**What stays the same:** staging/ref/marts model structure, dbt tests, Cube semantic layer, `updated_at` watermark logic.

---

## Task Status
- [x] Task 1 — EDA (scripts/eda.py, 8 charts in charts/)
- [x] Task 2 — Model design + implementation (dbt project in dbt/)
- [x] Task 3 — Three hard calls (TASK_3_HARD_CALLS.md)
- [x] Task 4 — One analytical query (dbt/models/analysis/no_show_by_lead_time.sql)
- [x] Task 5 — Production sketch (TASK_5_PROD_DIAGRAM.md)
