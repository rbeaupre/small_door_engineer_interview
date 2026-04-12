-- Staging layer: one-to-one with the source table.
-- Responsible for type casting, column renaming, and data quality flags.
-- All downstream models reference this — raw source types are only handled here.
--
-- Data quality decisions applied here:
--   Age < 0   → keep raw value + age_invalid = true  (flagged)
--   Age = 0   → keep as-is, age_invalid = false  (ambiguous; could be infant)
--   PatientId is DOUBLE in source (CSV inference artifact); CAST to BIGINT is safe as all values fit within BIGINT range.
SELECT
    CAST(AppointmentID AS BIGINT)               AS appointment_id,
    CAST(PatientId AS BIGINT)                   AS patient_id,
    Clinic                                      AS clinic_name,
    Gender                                      AS gender,
    CAST(Age AS INTEGER)                          AS age,
    (Age < 0)                                     AS age_invalid,
    CAST(LowIncome AS INTEGER)                  AS low_income,
    CAST(Hypertension AS INTEGER)               AS hypertension,
    CAST(Diabetes AS INTEGER)                   AS diabetes,
    CAST(SubstanceUseDisorder AS INTEGER)       AS substance_use_disorder,
    CAST(Disability AS INTEGER)                 AS disability,
    CAST(SMSReminder AS BOOLEAN)                AS sms_sent,
    CAST(ScheduledDay AS TIMESTAMPTZ)           AS scheduled_at,
    CAST(AppointmentDay AS TIMESTAMPTZ)         AS appointment_at,
    CAST(NoShow AS BOOLEAN)                     AS no_show
FROM {{ source('clinic', 'clinic_appointments') }}
