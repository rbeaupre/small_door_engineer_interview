# Small Door — Senior Data Engineer Case Study

---

## What We Built

Single-source dataset → purpose-built dbt stack on DuckDB

| Model | Layer | Type | Purpose |
|---|---|---|---|
| `stg_clinic_appointments` | staging | view | Type casts and column renaming only |
| `int_clinic_appointments` | intermediate | view | Quality fixes, flags, and derived columns |
| `date_spine` | ref | table | Date reference 2015–2030 |
| `appointments` | marts | table | OBT — primary BI surface |
| `patient_summary` | marts | table | Patient-level aggregate (standalone)|
| `clinic_summary` | marts | table | Clinic-level aggregate (standalone)|
| `no_show_by_lead_time` | analysis | table | No-show × lead-time × SMS |

**All four dashboard questions are answerable from `appointments` with no joins at query time.**

---

## Data Quality

**Principle: flag and retain in the intermediate layer; filter for polished simplicity in the mart.** Quality flags are always available for audit queries. Stakeholders never encounter ambiguous or impossible values in the mart.

| Issue | Volume | Intermediate | Mart |
|---|---|---|---|
| PatientId fractional (e.g. 93779.52927) | 5 rows | Decimal stripped → full-length ID (9377952927) | Retained |
| Age = −1 (impossible) | 1 row | `age_invalid = true` | Filtered out |
| Age = 0 (ambiguous) | 3,539 rows | No flag — likely newborns | Retained |
| Age > 110 | 5 rows | No flag — biologically possible | Retained |
| Same-day walk-ins (midnight UTC artifact) | 38,563 rows | `same_day_appointment = true` | Retained — valid appointments, 4.7% no-show rate |
| Genuinely negative lead time (appt before schedule) | 5 rows | `lead_time_genuinely_negative = true` | Filtered out |
| Small clinics (n=1–2) | ~5 clinics | No flag | Retained — volume filtering belongs at reporting layer |
| Disability encoded 0–4 | 2,241 rows with disability > 0 | Keep as integer | Retained — ordinal severity, collapsing loses signal |

---

## Key Modeling Decisions

| Decision | Chose | Rejected |
|---|---|---|
| Intermediate layer for quality logic | `int_clinic_appointments` owns all fixes, flags, and derived columns | Flags in staging; logic in mart |
| Flag and retain in intermediate; filter in mart | Bad rows flagged and kept in `int_clinic_appointments`; excluded from `appointments` | Drop at ingestion; expose flags to stakeholders |
| No `dim_patient_history` | Attributes carried directly from source row | SCD2 with BETWEEN join |
| `clinic_summary` mart | Dedicated clinic aggregate model | GROUP BY on `appointments` at query time |
| `date_spine` joined on date value | Direct equality join | Compute date attrs inline |
| `sms_sent` as boolean | Flag on OBT | `dim_sms` with one row per message |
| `disability` as integer 0–4 | Raw ordinal value | Cast to boolean |
| Clinic utilization proxy | `is_utilized = NOT no_show` | Capacity-based rate |

---

## Hard Call 1 — Dashboarding - OBT vs Star Schema

**Decision:** flat OBT mart with a medallion architecture over a normalised star schema
| | Star Schema | OBT (chosen) |
|---|---|---|
| Sources | Multiple — worth normalising | Single table (`appointments`) |
| Patient history | SCD2 for point-in-time accuracy | Each row already carries state at scheduling time |
| BI tool joins | Fan-out at query time | Zero joins required |
| Maintenance | More models, more tests, more moving parts | 5 models total |

**Why OBT and Medallion:** star schema solves an integration problem — joining entities across multiple source systems. There is no integration problem here: one source table, one grain, all dashboard questions answerable with no joins at query time.

**On SCD2 specifically:** each appointment row records patient state at scheduling time — that is the history. A SCD2 would reconstruct point-in-time accuracy the source already provides natively. We built it and removed it.

**Empirical validation:** deep-dive analysis of consecutive appointment pairs shows only 3.2–3.9% have any attribute change between visits — virtually all Age incrementing year-over-year. Condition flags are stable regardless of the gap between visits. A SCD2 would add significant complexity to track changes that never happen.

**Alternatives considered:**
- Star schema: `fct_appointments` + `dim_patient_history` (SCD2) + `dim_clinic` + `dim_date`
- Hybrid: star schema intermediate layer with OBT mart on top

**What would change our mind:** Integration of a patient registration system and multiple upstream data domain sources which updates records outside of the appointments dataset which could make Star Schema and SCD2 a better fit.

---

## Hard Call 2 — Disability: Severity Scale or Specific Disability Types?

**The question:** does 0–4 encode severity (0 = healthy, 1 = slightly impaired, 2 = moderately impaired, etc.) or specific disability types (0 = none, 1 = mobility impairment, 2 = visual impairment, etc.)?

**Decision:** treat as an ordinal severity scale and retain as integer.

**Evidence for severity:**
- Distribution shows a sharp drop-off at higher values — most patients are 0, very few reach 3 or 4. Consistent with severity, where extreme values are naturally rare.
- Hypertension and Diabetes rates increase with Disability level — consistent with a sedentary lifestyle effect from progressive physical impairment.
- Patients with Disability = 2 have zeroes across all other comorbidity flags — rules out the hypothesis that Disability is simply counting the other four flags.

**Interesting wrinkle:** Disability = 1 shows *higher* comorbidity rates than Disability = 2. One interpretation: more severely disabled patients have more experience and structured support managing their condition; the sharpest quality-of-life impact falls between 0 and 1, not higher up the scale.

**Why it matters for modelling:** if it is specific disability types, aggregating or averaging across values would be meaningless. Treating it as severity makes aggregation valid. We retain integer to preserve flexibility either way — casting to boolean would irreversibly collapse the encoding.

**What would change our mind:** a data dictionary confirming specific type encoding.

---

## Hard Call 3 — Two Populations Inside "Negative Lead Time"

**38,568 rows (~35%) have `scheduled_at > appointment_at` — but they are not one problem, they are two.**

| Population | Volume | Evidence | Decision |
|---|---|---|---|
| Same-day walk-ins | 38,563 rows | All share the same calendar date on both sides; `AppointmentDay` always midnight UTC; **zero SMS reminders sent**; 4.7% no-show rate vs ~20% overall | `same_day_appointment = true` in intermediate — **retained in mart** |
| Genuinely negative (appt before schedule) | 5 rows | Appointment date strictly precedes schedule date across calendar days; all are no-shows | `lead_time_genuinely_negative = true` in intermediate — **filtered from mart** |

**Why the walk-ins are valid appointments, not bad data:**
- `AppointmentDay` is always stored as midnight UTC; `ScheduledDay` carries a time component — same-day bookings made after midnight appear negative at the timestamp level but are identical at the date level
- Zero SMS reminders sent to any of them — consistent with drop-in appointments that require no advance reminder
- 4.7% no-show rate is the lowest of any population — these patients showed up

**Why the 5 genuinely negative rows are filtered:**
- Appointment date precedes schedule date across calendar days — no plausible clinical explanation
- All are no-shows; no analytical value that would be lost by excluding them
- Retained in `int_clinic_appointments` for audit purposes

**The risk of treating both as one:** blending "walk-ins" with scheduled appointments without acknowledgement produces a misleading overall no-show rate. The two populations must be analysed separately.

---

## Additional Findings

**`low_income` is the strongest single-flag predictor of no-show** — higher than hypertension, diabetes, or substance use disorder. This has a plausible real-world basis: low-income patients face more situational barriers to attendance (transport, work flexibility, competing priorities).

**The Age = 0 + LowIncome interaction reinforces the newborn interpretation.** Despite LowIncome driving higher no-shows overall, Age = 0 patients with the LowIncome flag show a *lower* no-show rate (13.5% vs ~20% overall). The sample size is small though not quite insighificant (s = 52), a likely explanation is that parents are less likely to skip a newborn's appointment regardless of income constraints. This also strengthens the case that these are genuine newborn appointments, not missing data.

---

## Production Architecture — Data Movement & Orchestration

1. **Scheduling Software** — source of truth for appointments and patient state
2. **Cloud Scheduler** → triggers Dagster on a schedule
3. **Dagster** → triggers Cloud Function as an asset op; owns the full pipeline graph
4. **Cloud Function** → extracts from source API, writes raw Parquet to GCS
5. **GCS raw zone** — immutable, append-only; replay buffer if marts need rebuilding
6. **BigQuery raw dataset** — append-only; `updated_at` preserved for incremental runs
7. **dbt on BigQuery** — staging → intermediate / ref → marts / analysis
8. **Cube** — semantic layer; named measures, version-controlled metric definitions
9. **BI tools** — query through Cube; no direct BigQuery access

**What breaks first when source schema changes?** `stg_clinic_appointments` — the only model that references source column names directly. A rename in the source requires a fix in one place. Dagster fails the staging asset and blocks all downstream models automatically.

---

## Production — Testing, Freshness & Metric Governance

**How do you test that the numbers are right?**

| Layer | Mechanism | Catches |
|---|---|---|
| Ingestion | Cloud Function publishes row count to Cloud Monitoring; alert on significant drop vs rolling average | Silent truncations before they reach the warehouse |
| dbt | `unique`, `not_null`, range checks run as Dagster asset checks | Schema errors, constraint violations, out-of-range values |
| Dagster asset checks | Row count assertions between raw and mart layers | Row loss across the pipeline |

**How does an analyst know if today's data is stale?**

dbt source freshness on `updated_at` as `loaded_at_field` — serves double duty as incremental watermark and freshness signal. If source is stale, Dagster aborts before any transforms run.

```yaml
loaded_at_field: updated_at
freshness:
  warn_after:  {count: 12, period: hour}
  error_after: {count: 25, period: hour}
```

**Metric Governance:** Operations and Finance will want different definitions of "no-show rate." Solution: Cube as the semantic layer — all BI tools query through Cube, `no_show_rate` variants are declared as named measures, version-controlled and peer-reviewed. Analysts cannot invent a third definition in a calculated field.

**The principle throughout:** every metric definition has a single owner, a written spec, and a version-controlled implementation — never a spreadsheet or a BI tool calculated field.
