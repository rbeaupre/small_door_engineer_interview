-- Intermediate layer: data quality fixes, flags, and derived columns.
-- Refs staging and produces a clean, flagged dataset for all mart and analysis models.
--
-- PatientId fix: 5 rows have fractional values (e.g. 93779.52927) — a CSV read artifact.
-- Stripping the decimal recovers the intended full-length integer (e.g. 9377952927), consistent
-- with the length of all other PatientId values. Simple truncation via BIGINT cast would produce
-- a short ID (e.g. 93779) that is meaningless and could collide with a legitimate patient.
--
-- age_invalid: Age = -1 is the only impossible value in the dataset. Kept raw; flag set to true.
--
-- Lead-time flags:
--   lead_time_valid:             timestamp-level — appointment_at >= scheduled_at
--   same_day_appointment:        same calendar date on both sides — walk-in/drop-in population (38,563 rows)
--   lead_time_genuinely_negative: appointment date strictly before schedule date — 5 rows, likely entry errors
SELECT
    s.appointment_id,
    CASE
        WHEN s.patient_id % 1 != 0
            THEN CAST(REPLACE(CAST(s.patient_id AS VARCHAR), '.', '') AS BIGINT)
        ELSE CAST(s.patient_id AS BIGINT)
    END                                                              AS patient_id,
    s.clinic_name,
    s.gender,
    s.age,
    (s.age < 0)                                                      AS age_invalid,
    s.low_income,
    s.hypertension,
    s.diabetes,
    s.substance_use_disorder,
    s.disability,
    s.sms_sent,
    s.scheduled_at,
    s.appointment_at,
    s.no_show,
    ROUND(
        EXTRACT(EPOCH FROM (s.appointment_at - s.scheduled_at)) / 86400.0,
        2
    )                                                                AS lead_time_days,
    (CAST(s.appointment_at AS DATE) = CAST(s.scheduled_at AS DATE))  AS same_day_appointment,
    (CAST(s.appointment_at AS DATE) < CAST(s.scheduled_at AS DATE))  AS lead_time_genuinely_negative
FROM {{ ref('stg_clinic_appointments') }} s
