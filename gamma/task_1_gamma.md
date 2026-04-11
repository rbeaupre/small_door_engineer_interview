# Task 1: Explore and Profile the Data

---

## Slide 1 — The Dataset

**110,527 appointments · 81 clinics · 62,299 patients**

One row per appointment (AppointmentID is unique). But 39% of patients appear more than once — one patient has 88 appointments. Patient is not an independent unit of analysis; any patient-level aggregate needs to account for repeated measures.

**Columns:** PatientId, AppointmentID, Gender, ScheduledDay, AppointmentDay, Age, Clinic, LowIncome, Hypertension, Diabetes, SubstanceUseDisorder, Disability, SMSReminder, NoShow

---

## Slide 2 — Data Quality Issues

| Issue | Scale | Action |
|-------|-------|--------|
| Negative lead time (ScheduledDay > AppointmentDay) | 38,568 rows (35%) | Timezone artifact — exclude from lead-time analysis, keep in no-show counts |
| Age = 0 | 3,539 rows | Ambiguous (infants or NULL sentinel) — leave as-is, flag in pipeline |
| Age = −1 | 1 row | Impossible — exclude |
| Disability encoded as 0–4, not boolean | 199 rows > 1 | Ordinal count, not a flag — must not be treated as binary |
| Clinic volume extremely skewed | CV ≈ 1.0; smallest clinic has 1 appt | Enforce minimum volume threshold (n ≥ 50) before reporting rates |

**Principle:** None of these get silently dropped or imputed. Issues are documented in a staging layer where choices are visible and versioned.

---

## Slide 3 — What the Data Actually Shows

**Overall no-show rate: 20.2%** · Clinic range: 15%–29% (after volume filter)

**Lead time predicts no-shows** — rates rise from 14% (same-day) to 34% (booked 31–60 days out), then taper off. This is a first-class signal for any risk model.

**Condition flags show mixed results:**
- LowIncome → higher no-show (23.7% vs. 19.8%) — expected
- Hypertension / Diabetes / Disability → slightly *lower* no-show — likely older, more adherent patients
- SubstanceUseDisorder → no difference (rare flag, ~0.1% of records)

**SMS reminders appear to make things worse (27.6% vs. 16.7%) — but this is selection bias.** Reminders were sent preferentially to higher-risk, longer-lead-time patients. The raw correlation inverts the true effect. Effectiveness cannot be assessed without controlling for lead time and patient risk.

---

## Slide 4 — Key Modeling Implications

- **Grain is appointment-level** — the right unit for a no-show fact table
- **Lead time** should be a first-class derived column, with negative values flagged and excluded from bucketing
- **Disability** needs an explicit modeling decision: ordinal integer, boolean, or a separate dimension with severity levels
- **SMS effectiveness** requires a confounding-aware analysis — a naive dashboard metric will mislead stakeholders
- **Small clinics** need a volume gate in any rate calculation, or noise dominates the leaderboard
