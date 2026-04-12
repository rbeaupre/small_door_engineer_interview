# Task 3 — Three Hard Calls

---

## Decision 1: OBT over star schema

**What was the decision?**
Chose a single flat One Big Table (`appointments`) as the primary analytical model rather than a normalized star schema with separate fact and dimension tables.

**What were the alternatives?**
- Classic star schema: `fct_appointments` joined to `dim_patient_history` (SCD2), `dim_clinic`, and `dim_date` via surrogate keys
- Hybrid: star schema as the intermediate layer with an OBT materialized view on top for BI consumption

**What did we choose and why?**
OBT. The source is a single table — `clinic_appointments` — and each appointment row already carries patient attributes, clinic name, and all fields needed to answer every dashboard question. With a single source there is no integration problem to solve at the dimensional layer; a star schema would add structural overhead without contributing correctness or reusability.

OBT also plays better with free BI tools like Looker Studio, which do not optimize multi-join queries well. Analysts get one table, no joins required.

We still built a standalone `patient_summary` model for patient-level risk profiling — so the patient entity exists, just not as a required join in the main mart.

**What would change our mind?**
- Patient data coming from a separate EHR or registration system with its own update cadence — at that point you need a proper `dim_patient_history` to resolve point-in-time attributes correctly
- Multiple fact types (appointments, billing, lab results) sharing the same patient and clinic dimensions — then a shared dimensional layer pays off
- A BI tool with a strong semantic layer (e.g. Looker with LookML) where a normalized model maps more naturally to the tool's abstractions

---

## Decision 2: Patient attributes carried on each appointment row, not in a separate patient entity

**What was the decision?**
Patient attributes (gender, age, condition flags) are sourced directly from each appointment row rather than resolved through a separate SCD2 `dim_patient_history` table joined at query time.

**What were the alternatives?**
- SCD2 `dim_patient_history` with a BETWEEN date-range join for point-in-time accuracy — we actually built this, ran it, and then removed it
- Current-state-only `dim_patient` with a simple equality join — simpler but loses any history of attribute changes

**What did we choose and why?**
Direct sourcing from the appointment row. The source records patient attributes at the time each appointment is scheduled — that is already the history. Building a SCD2 from this data would reconstruct point-in-time accuracy that the source provides natively on every row. The added join complexity (BETWEEN on date ranges) solves a problem we do not actually have.

This decision rests on Assumption 2: that each row reflects patient state at scheduling time, not current state backfilled at extraction. If that assumption holds — and all evidence suggests it does — the OBT is historically correct without any additional machinery.

**What would change our mind?**
- Confirmation from the source system team that patient attributes are backfilled to current values at extraction time — that would make every historical row in the OBT silently wrong, and a SCD2 with point-in-time resolution would become mandatory
- Integration of a separate patient registration or EHR system where patient attributes live independently of the appointments table and have their own update frequency

---

## Decision 3: Retain negative lead times with a validity flag rather than treating them as errors

**What was the decision?**
Kept all 38,568 rows where `scheduled_at > appointment_at` (negative lead time), setting `lead_time_valid = false` rather than dropping these rows or nulling out the lead time value.

**What were the alternatives?**
- Drop the rows entirely (~35% of the dataset)
- Null out `lead_time_days` for negative values, similar to how some teams handle negative ages
- Attempt to correct them by inferring the "true" scheduling date

**What did we choose and why?**
Flag and retain. These rows have valid appointment data — the appointment happened, the no-show outcome is real — so dropping them would silently bias no-show counts and clinic utilization figures. The pattern is consistent with a timezone artifact: `ScheduledDay` always carries a time component (e.g. 18:38 UTC) while `AppointmentDay` is always midnight UTC, meaning same-day late bookings appear to precede the appointment date. The magnitude is small (max −6.6 days) and the volume (35%) is far too large to be random entry errors.

`lead_time_valid = false` gives analysts a clean, explicit filter: use it for lead-time analysis, ignore it for no-show counts. The raw `lead_time_days` value is retained so analysts can inspect the distribution rather than being handed a sanitized null.

**What would change our mind?**
- Source system documentation confirming these represent genuine scheduling anomalies, not timezone effects
- Evidence that the no-show rate for `lead_time_valid = false` rows differs significantly from valid rows — if it does, they are a behaviorally distinct population that should probably be handled separately rather than silently folded into the overall count
- A meaningful number of rows with magnitudes beyond a few days, which would be harder to explain as timezone drift alone
