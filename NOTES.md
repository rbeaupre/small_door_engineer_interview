# EDA Findings & Open Decisions

## Task 1 Key Findings

### Grain
- AppointmentID is unique — one row per appointment confirmed.
- 62,299 distinct patients across 110,527 appointments.
- 39.1% of patients have >1 appointment; one patient has 88. Patient is NOT an independent unit.

### Date / Lead-time
- **38,568 rows (~35%)** have negative lead-time (ScheduledDay > AppointmentDay).
  - Magnitude is small (max −6.6 days). Likely a timezone parsing artifact: ScheduledDay has a time component (e.g., 18:38 UTC) and AppointmentDay is midnight UTC, so same-day bookings recorded late in the day appear negative.
  - Decision: exclude from lead-time analysis; retain for no-show counts.
- Lead-time monotonically predicts no-show up to ~60 days (same-day ~14% → 31–60d ~34%).

### Age
- 1 row: Age = −1 (impossible)
- 3,539 rows: Age = 0 (ambiguous — infants or NULL sentinel)
- 5 rows: Age > 110 (edge outliers)

### Clinics
- 81 distinct clinics, but volume is extremely skewed (CV ≈ 1.0): Greenwood Village has 7,717 appts; Industrial Park has 1.
- Clinics with <50 appointments (Trindade Shores = 2, Industrial Park = 1) have statistically meaningless rates.

### No-show
- Overall rate: **20.2%**
- Clinic range: 0% (n=1) to 100% (n=2) — small clinics dominate extremes.
- After excluding sub-50 clinics, range is roughly 15%–29%.

### Disability
- Encoded as 0–4, not boolean. Values: 0=108,286 / 1=2,042 / 2=183 / 3=13 / 4=3.
- Treating as binary loses ordinal severity information.

### Condition flags
- LowIncome: modestly higher no-show (23.7% vs 19.8%).
- Hypertension / Diabetes / Disability: slightly LOWER no-show (likely older, more adherent patients).
- SubstanceUseDisorder: nearly identical (20.2% vs 20.1%) — very rare flag.
- **SMSReminder: associated with HIGHER no-show (27.6% vs 16.7%)** — selection bias, not a causal signal.

## Open Decisions for Task 3

1. How to handle negative lead-times.
2. Whether Disability is modeled as ordinal, boolean, or multi-value dimension.
3. Whether SMSReminder lives in the fact table (appointment attribute) or a dim.
4. Minimum clinic size threshold for no-show rate reporting.

## Task Status
- [x] Task 1 — EDA (scripts/eda.py, 9 charts in charts/)
- [ ] Task 2 — Dimensional model (DuckDB)
- [ ] Task 3 — Three hard calls
- [ ] Task 4 — One analytical query
- [ ] Task 5 — Production sketch
