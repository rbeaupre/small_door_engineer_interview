-- OBT (One Big Table) mart: single table for dashboard use
-- Primary surface for all downstream queries which helps avoid multi-join fan-out at query time.
--
-- Patient attributes (age, gender, condition flags) are carried directly from staging.
-- Each appointment row in the source already records patient state at scheduling time with no separate patient dimension.
-- See NOTES.md for more commentary on this topic
--
-- Date decisions made here:
-- The date_spine model is joined on date value directly to provide added options for dashboard comparisons.
-- The lead_time logic (epoch calculation + validity flag) is directly derived here.
--
-- is_utilized: proxy for clinic utilization at the appointment level (patient attended = slot was used).
-- Note: without capacity data (total available slots per clinic), true utilization rate cannot be computed.
-- Aggregate as SUM(is_utilized) / COUNT(*) per clinic to get the attended-appointment rate.
SELECT
    s.appointment_id,
    s.no_show,
    (NOT s.no_show)                         AS is_utilized,
    s.sms_sent,
    ROUND(
        EXTRACT(EPOCH FROM (s.appointment_at - s.scheduled_at)) / 86400.0,
        2
    )                                       AS lead_time_days,
    (s.appointment_at >= s.scheduled_at)    AS lead_time_valid,
    s.scheduled_at,
    s.appointment_at,
    s.clinic_name,
    d.year,
    d.quarter,
    d.month,
    d.month_name,
    d.week_of_year,
    d.day_of_week,
    d.day_name,
    s.patient_id,
    s.age,
    s.age_invalid,
    s.gender,
    s.low_income,
    s.hypertension,
    s.diabetes,
    s.substance_use_disorder,
    s.disability
FROM      {{ ref('stg_clinic_appointments') }}  s
JOIN      {{ ref('date_spine') }}               d  ON  CAST(s.appointment_at AS DATE) = d.full_date
