-- Clinic-level aggregate mart: one row per clinic.
-- Enables volume-based filtering at the BI layer without requiring GROUP BY on the appointments OBT.
-- Inherits clean rows from appointments (age_invalid and lead_time_genuinely_negative already excluded).
--
-- avg_scheduled_lead_time_days excludes same-day walk-in appointments (same_day_appointment = true)
-- since their lead time is a midnight UTC artifact, not a real scheduling interval.
SELECT
    clinic_name,
    COUNT(*)                                                                        AS total_appointments,
    COUNT(DISTINCT patient_id)                                                      AS total_patients,
    SUM(CAST(no_show AS INTEGER))                                                   AS no_show_count,
    ROUND(SUM(CAST(no_show AS INTEGER)) * 100.0 / COUNT(*), 1)                      AS no_show_rate_pct,
    ROUND(SUM(CAST(is_utilized AS INTEGER)) * 100.0 / COUNT(*), 1)                  AS utilization_rate_pct,
    ROUND(AVG(CASE WHEN NOT same_day_appointment THEN lead_time_days END), 1)        AS avg_scheduled_lead_time_days
FROM {{ ref('appointments') }}
GROUP BY clinic_name
ORDER BY total_appointments DESC
