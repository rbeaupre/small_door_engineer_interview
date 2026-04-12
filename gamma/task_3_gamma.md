# Task 3 — Three Hard Calls

---

## Decisions 1 & 2

| | Decision 1: OBT vs Star Schema | Decision 2: Patient Attributes on Each Row |
|---|---|---|
| **Decision** | Flat OBT over normalized star schema | Carry patient attrs directly from staging; no `dim_patient_history` |
| **Alternatives** | Star schema with `fct_appointments` + `dim_patient_history` + `dim_clinic` | SCD2 dim with BETWEEN date-range join; or current-state-only dim |
| **Chose because** | Single source; each row is self-contained; simpler to maintain; better BI tool performance | Source already records patient state at scheduling time — SCD2 would reconstruct what's already in the data |
| **Would change if** | Multiple source systems require dimensional integration | Source team confirms attributes are backfilled at extraction (not point-in-time) — then SCD2 becomes mandatory |

---

## Decision 3: Retain Negative Lead Times With a Flag

**38,568 rows (~35%) have `scheduled_at > appointment_at`**

| Option | Problem |
|---|---|
| Drop rows | Silently biases no-show counts — these appointments happened |
| Null out `lead_time_days` | Loses the distribution; can't inspect the artifact |
| Correct by swapping dates | Assumes we know the intent — we don't |
| **Flag and retain** ✓ | `lead_time_valid = FALSE` gives analysts the choice |

**Why it's a timezone artifact, not bad data:**
- Max magnitude: −6.6 days — not random scheduling errors
- Pattern: `ScheduledDay` always carries a time component; `AppointmentDay` is always midnight UTC
- Volume: 35% is too large to be noise

**Would change mind if:** source docs confirm these are genuine errors, or no-show rate for invalid rows differs significantly from valid rows (suggesting a distinct patient population).
