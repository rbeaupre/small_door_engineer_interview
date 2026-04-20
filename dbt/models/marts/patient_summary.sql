-- Patient-level aggregate with one row per patient.
-- Answers "What is the complete picture of a patient?" — latest known attributes combined with lifetime appointment statistics.
-- Intended as a secondary analytical surface for operational reporting, separate from the appointment grain.
--
-- Mart philosophy: flag and retain in the intermediate layer; filter for polished simplicity here.
-- Data quality filtering is applied upstream in appointments — this model inherits clean rows only.

-- Most recent appointment row per patient — used to source current attribute state.
WITH latest_attrs AS (
    SELECT
        patient_id,
        gender,
        age,
        low_income,
        hypertension,
        diabetes,
        substance_use_disorder,
        disability
    FROM {{ ref('appointments') }}
    QUALIFY CAST(ROW_NUMBER() OVER (
        PARTITION BY patient_id ORDER BY appointment_at DESC
    ) AS INTEGER) = 1
),

stats AS (
    SELECT
        patient_id,
        COUNT(*)                                                        AS total_appointments,
        SUM(CAST(no_show AS INTEGER))                                   AS no_show_count,
        ROUND(SUM(CAST(no_show AS INTEGER)) * 100.0 / COUNT(*), 1)      AS no_show_rate_pct,
        SUM(CAST(sms_sent AS INTEGER))                                  AS sms_count,
        COUNT(DISTINCT clinic_name)                                     AS clinics_visited,
        CAST(MIN(appointment_at) AS DATE)                               AS first_appointment_at,
        CAST(MAX(appointment_at) AS DATE)                               AS last_appointment_at
    FROM {{ ref('appointments') }}
    GROUP BY patient_id
)

SELECT
    s.patient_id,
    l.gender,
    l.age,
    l.low_income,
    l.hypertension,
    l.diabetes,
    l.substance_use_disorder,
    l.disability,
    s.total_appointments,
    s.no_show_count,
    s.no_show_rate_pct,
    s.sms_count,
    s.clinics_visited,
    s.first_appointment_at,
    s.last_appointment_at
FROM stats               s
JOIN latest_attrs        l  ON  s.patient_id = l.patient_id
