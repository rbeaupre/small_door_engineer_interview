-- OBT (One Big Table) mart: single table for dashboard use.
-- Primary surface for all downstream queries — avoids multi-join fan-out at query time.
--
-- Patient attributes (age, gender, condition flags) are carried directly from the intermediate layer.
-- Each appointment row in the source already records patient state at scheduling time.
-- See NOTES.md for more commentary on this topic.
--
-- Date spine is joined on date value to provide calendar attributes for dashboard comparisons.
--
-- is_utilized: proxy for clinic utilization at the appointment level (patient attended = slot was used).
-- Note: without capacity data (total available slots per clinic), true utilization rate cannot be computed.
-- Aggregate as SUM(is_utilized) / COUNT(*) per clinic to get the attended-appointment rate.
--
-- Mart philosophy: flag and retain in the intermediate layer; filter for polished simplicity here.
-- Rows with data quality issues are kept in int_clinic_appointments for audit purposes but excluded
-- from this model so stakeholders never encounter ambiguous or impossible values.
SELECT
    i.appointment_id,
    i.no_show,
    (NOT i.no_show)                         AS is_utilized,
    i.sms_sent,
    i.lead_time_days,
    i.same_day_appointment,
    i.scheduled_at,
    i.appointment_at,
    i.clinic_name,
    d.year,
    d.quarter,
    d.month,
    d.month_name,
    d.week_of_year,
    d.day_of_week,
    d.day_name,
    i.patient_id,
    i.age,
    i.gender,
    i.low_income,
    i.hypertension,
    i.diabetes,
    i.substance_use_disorder,
    i.disability
FROM      {{ ref('int_clinic_appointments') }}  i
JOIN      {{ ref('date_spine') }}               d  ON  CAST(i.appointment_at AS DATE) = d.full_date
WHERE     i.lead_time_genuinely_negative = FALSE  -- exclude 5 rows where appt date < schedule date
  AND     i.age_invalid = FALSE                  -- exclude 1 row with age = -1
