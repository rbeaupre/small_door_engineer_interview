-- Staging layer: one-to-one with the source table.
-- Responsible for type casting and column renaming only.
-- All downstream models reference this — raw source types are only handled here.
-- Data quality flags and derived columns live in int_clinic_appointments.
SELECT
    CAST(AppointmentID AS BIGINT)               AS appointment_id,
    CAST(PatientId AS DOUBLE)                   AS patient_id,
    CAST(Clinic AS VARCHAR)                     AS clinic_name,
    CAST(Gender AS VARCHAR)                     AS gender,
    CAST(Age AS INTEGER)                        AS age,
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
