# Task 3 — Three Hard Calls

---

## Decision 1: OBT over star schema (including the SCD2 question)

**What was the decision?**
Chose a single flat One Big Table (`appointments`) as the primary analytical model rather than a normalized star schema — including the decision not to build a separate `dim_patient_history` SCD2 table.

**What were the alternatives?**
- Classic star schema: `fct_appointments` joined to `dim_patient_history` (SCD2), `dim_clinic`, and `dim_date` via surrogate keys
- Hybrid: star schema as the intermediate layer with an OBT materialized view on top for BI consumption

**What did we choose and why?**
OBT. The source is a single table — `clinic_appointments` — and each appointment row already carries patient attributes, clinic name, and all fields needed to answer every dashboard question. With a single source there is no integration problem to solve at the dimensional layer; a star schema adds structural overhead without contributing correctness or reusability.

On SCD2 specifically: each appointment row records patient state at scheduling time — that is already the history. Building a SCD2 from this data would reconstruct point-in-time accuracy the source provides natively on every row. We actually built it, ran it, and removed it.

**Empirical validation:** deep-dive analysis of consecutive appointment pairs confirms the decision: only 3.2–3.9% of pairs show any attribute change between visits, and virtually all of that is Age incrementing year-over-year. Condition flags are stable across appointments regardless of the gap between visits. A SCD2 would add significant complexity to track changes that almost never happen.

We still built standalone `patient_summary` and `clinic_summary` models — patient and clinic entities exist, just not as required joins in the main mart.

**What would change our mind?**
- Integration of a separate EHR or patient registration system with its own update cadence — at that point you need a proper `dim_patient_history` SCD2 to resolve point-in-time attributes correctly across sources
- Confirmation from the source team that patient attributes are backfilled to current values at extraction time — that would make every historical row in the OBT silently wrong and SCD2 mandatory

---

## Decision 2: Disability — ordinal severity scale, not specific disability types

**What was the decision?**
Treat `disability` (encoded 0–4) as an ordinal severity scale rather than as an encoding for specific disability types, and retain it as an integer rather than casting to boolean.

**What were the alternatives?**
- Interpret as specific disability types (0 = none, 1 = mobility impairment, 2 = visual impairment, etc.) — would make aggregation across values meaningless
- Cast to boolean — collapses all non-zero values, losing whatever signal the range encodes

**What did we choose and why?**
Treat as ordinal severity, keep as integer. Three pieces of evidence:
1. Distribution shows a sharp drop-off at higher values — most patients are 0, very few reach 3 or 4. Consistent with severity where extreme values are naturally rare.
2. Hypertension and Diabetes rates increase with Disability level — consistent with a sedentary lifestyle effect from progressive physical impairment.
3. Patients with Disability = 2 have zeroes across all other comorbidity flags — rules out the hypothesis that Disability is simply a count of the other four flags.

Interesting wrinkle: Disability = 1 shows *higher* comorbidity rates than Disability = 2. One interpretation — more severely disabled patients have more structured support managing their condition; the sharpest quality-of-life impact falls between 0 and 1.

Keeping it as integer is safe either way: if it turns out to encode specific types, no signal is lost and analysts can bucket as needed. Casting to boolean would irreversibly collapse the encoding.

**What would change our mind?**
- A data dictionary from the source team confirming specific type encoding — at that point aggregating or averaging across values would be meaningless and the column would need to be treated as a categorical

---

## Decision 3: Two populations inside negative lead time — treated differently

**What was the decision?**
The 38,568 rows where `scheduled_at > appointment_at` are not one problem — they are two distinct populations that require different treatment.

**The two populations:**
- **38,563 rows — same-day walk-ins:** AppointmentDay is always stored as midnight UTC; ScheduledDay carries a time component. Same-day bookings made after midnight appear negative at the timestamp level but share the same calendar date. Zero SMS reminders sent to any of them (consistent with drop-in appointments). No-show rate is 4.7% vs ~20% overall — a clinically distinct population. Flagged as `same_day_appointment = true` in the intermediate layer; **retained in the mart**.
- **5 rows — genuinely negative:** Appointment date strictly precedes schedule date across calendar days. All are no-shows. No plausible clinical explanation. Flagged as `lead_time_genuinely_negative = true` in the intermediate layer; **filtered from the mart**.

**What were the alternatives?**
- Drop all 38,568 rows — silently biases no-show counts; the walk-ins are valid appointments
- Treat all as a single population — obscures the meaningful behavioral difference between walk-ins and the 5 genuinely bad rows
- Null out `lead_time_days` — loses the distribution for inspection

**What did we choose and why?**
Flag and retain in the intermediate layer; filter only the 5 genuinely negative rows from the mart. The walk-ins are valid appointments with real no-show outcomes — removing them biases utilization figures. The 5 genuinely negative rows have no analytical value and no plausible interpretation.

This follows the broader mart philosophy: `int_clinic_appointments` retains everything with quality flags for audit purposes; `appointments` (the stakeholder surface) contains only analytically clean rows.

**What would change our mind?**
- Source system documentation confirming the walk-in population represents a different appointment type that should be excluded from all reporting — at that point they belong in a separate mart, not filtered from this one
- Evidence that the 5 genuinely negative rows have a valid explanation (e.g. a known scheduling system bug affecting specific date ranges)
